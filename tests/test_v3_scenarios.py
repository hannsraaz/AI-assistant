from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Any
import pytest

from assistant_core import VoiceAssistant
from config import AppConfig
from core.agent import AgenticPlanner, TaskEvent, TaskManager, TaskStatus, TaskStepStatus
from core.agent.verifier import StepVerifier
from core.automation import PersistentScheduler, ScheduledEvent
from core.memory import MemoryManager
from core.tools.base import RiskLevel, ToolError, ToolResult
from core.tools.registry import ToolRegistry


@pytest.fixture
def v3_assistant(tmp_path: Path) -> VoiceAssistant:
    cfg = AppConfig()
    cfg.speak_responses = False
    cfg.wake_word.enabled = False
    cfg.memory.storage_file = str(tmp_path / "v3_memory.json")
    cfg.automation.schedules_file = str(tmp_path / "v3_schedules.json")
    cfg.automation.workflows_file = str(tmp_path / "v3_workflows.json")
    return VoiceAssistant(cfg)


class TestV3AutonomousScenarios:
    """10 End-to-End Autonomous Scenarios and Failure Recovery Simulations."""

    # Scenario 1: "Open VS Code"
    def test_scenario_1_open_app(self, v3_assistant: VoiceAssistant) -> None:
        res = v3_assistant.registry.execute("apps.find", query="code")
        assert res.success is True
        assert "path" in res.data or "matches" in res.data

    # Scenario 2: "Find my Android project"
    def test_scenario_2_find_android_project(self, v3_assistant: VoiceAssistant, tmp_path: Path) -> None:
        proj_dir = tmp_path / "NovaAndroidApp"
        proj_dir.mkdir()
        (proj_dir / "build.gradle").write_text("// Gradle file", encoding="utf-8")

        v3_assistant.memory.remember("Nova", str(proj_dir), category="project_alias")
        recalled = v3_assistant.memory.recall("Nova")
        assert len(recalled) >= 1
        assert str(proj_dir) in recalled[0]["value"]

    # Scenario 3: "Build my Android project"
    def test_scenario_3_build_android_project(self, v3_assistant: VoiceAssistant, tmp_path: Path) -> None:
        proj_dir = tmp_path / "DummyAndroid"
        proj_dir.mkdir()
        (proj_dir / "gradlew.bat").write_text("@echo off\necho BUILD SUCCESSFUL\nexit /b 0", encoding="utf-8")

        res = v3_assistant.registry.execute("android.build", project_path=str(proj_dir))
        assert res.success is True
        assert res.data["exit_code"] == 0

    # Scenario 4: "Build Android project with failure diagnosis & recovery"
    def test_scenario_4_build_failure_recovery(self, v3_assistant: VoiceAssistant, tmp_path: Path) -> None:
        planner = v3_assistant.planner
        step_verifier = StepVerifier(v3_assistant.registry)

        # Simulation: Tool initially reports failure, then verifier/repair evaluates
        fail_res = ToolResult(
            success=False,
            error=ToolError(code="BUILD_FAILED", message="Missing SDK location"),
        )
        verified, msg = step_verifier.verify_step("android.build", {"project_path": str(tmp_path)}, fail_res)
        assert verified is False
        assert "BUILD_FAILED" in msg or "failure" in msg

    # Scenario 5: "Find the error on my screen"
    def test_scenario_5_screen_error_detection(self, v3_assistant: VoiceAssistant) -> None:
        res = v3_assistant.registry.execute("screen.capture", mode="fullscreen")
        assert res.success is True
        assert "image_path" in res.data

    # Scenario 6: "Open YouTube and search for Java tutorials"
    def test_scenario_6_youtube_search(self, v3_assistant: VoiceAssistant) -> None:
        res = v3_assistant.registry.execute("browser.search", query="Java tutorials", engine="youtube")
        assert res.success is True
        assert "youtube.com" in res.data["url"]

    # Scenario 7: "Find the PDF invoice in Downloads"
    def test_scenario_7_find_pdf_invoice(self, v3_assistant: VoiceAssistant, tmp_path: Path) -> None:
        downloads = tmp_path / "Downloads"
        downloads.mkdir()
        invoice = downloads / "invoice_august_2026.pdf"
        invoice.write_text("Dummy Invoice PDF content", encoding="utf-8")

        res = v3_assistant.registry.execute("files.search", query="invoice", directory=str(downloads))
        assert res.success is True
        assert res.data["count"] >= 1
        assert "invoice_august_2026.pdf" in res.data["files"][0]["name"]

    # Scenario 8: "Set a reminder for 30 minutes"
    def test_scenario_8_set_reminder(self, v3_assistant: VoiceAssistant) -> None:
        res = v3_assistant.registry.execute("reminder.set", message="Review PR", delay_seconds=1800.0)
        assert res.success is True
        assert "event_id" in res.data

    # Scenario 9: "Check Git status and tell me what changed"
    def test_scenario_9_git_status_diff(self, v3_assistant: VoiceAssistant, tmp_path: Path) -> None:
        git_dir = tmp_path / "scenario_repo"
        git_dir.mkdir()
        subprocess.run(["git", "init"], cwd=str(git_dir), check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Tester"], cwd=str(git_dir), check=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(git_dir), check=True)

        new_file = git_dir / "feature.py"
        new_file.write_text("x = 42", encoding="utf-8")

        res = v3_assistant.registry.execute("git.status", cwd=str(git_dir))
        assert res.success is True
        assert "feature.py" in res.data["status"]

    # Scenario 10: "Build the project in the background and notify when complete"
    def test_scenario_10_background_task_progress(self, v3_assistant: VoiceAssistant) -> None:
        tm = v3_assistant.task_manager
        events_emitted: list[TaskEvent] = []

        def on_ev(task: Any, ev: TaskEvent, msg: str) -> None:
            events_emitted.append(ev)

        tm.on_task_event = on_ev
        task = tm.create_task("Autonomous Background Android Build")

        def background_job(t: Any) -> None:
            t.emit_event(TaskEvent.TOOL_EXECUTED, "Running gradle assembleDebug...")
            time.sleep(0.1)

        tm.start_task_async(task, background_job)
        time.sleep(0.2)

        assert task.status == TaskStatus.COMPLETED
        assert TaskEvent.TOOL_EXECUTED in events_emitted

    # --- Failure Simulation Tests ---
    def test_failure_simulation_path_traversal(self, v3_assistant: VoiceAssistant) -> None:
        res = v3_assistant.registry.execute("files.read", path=r"C:\Windows\System32\drivers\etc\hosts")
        assert res.success is False
        assert res.get_error_code() == "PROTECTED_DIRECTORY"

    def test_failure_simulation_unconfirmed_high_risk(self, v3_assistant: VoiceAssistant) -> None:
        res = v3_assistant.registry.execute("system.shutdown")
        assert res.success is False
        assert res.needs_confirmation is True

    def test_failure_simulation_cancellation(self, v3_assistant: VoiceAssistant) -> None:
        tm = v3_assistant.task_manager
        task = tm.create_task("Long Running Job")

        def long_job(t: Any) -> None:
            for _ in range(20):
                if t.stop_event.is_set():
                    t.status = TaskStatus.CANCELLED
                    return
                time.sleep(0.05)

        tm.start_task_async(task, long_job)
        time.sleep(0.05)
        tm.cancel_task(task.task_id)
        time.sleep(0.1)
        assert task.status == TaskStatus.CANCELLED
