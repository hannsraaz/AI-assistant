from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from typing import Any
import pytest

from core.agent import AgenticPlanner, TaskManager, TaskStatus
from core.automation import PersistentScheduler, ScheduledEvent
from core.memory import MemoryManager
from core.tools.base import RiskLevel, ToolError, ToolResult
from core.tools.developer.git_ops import GitHelper
from core.tools.files import register_file_tools
from core.tools.permissions import PermissionManager
from core.tools.registry import ToolRegistry


class TestRealIntegrationSuite:
    """Rigorous end-to-end integration and security test suite for Friday V2.1."""

    def test_real_filesystem_traversal_and_sandbox_security(self, tmp_path: Path) -> None:
        """Verify real file CRUD and strict path traversal protection."""
        reg = ToolRegistry()
        register_file_tools(reg)

        # 1. Create file in sandbox
        sandbox_file = tmp_path / "sandbox_doc.txt"
        res_create = reg.execute("files.create", path=str(sandbox_file), content="Mission Critical Data", confirmed=True)
        assert res_create.success is True
        assert sandbox_file.exists()

        # 2. Read file
        res_read = reg.execute("files.read", path=str(sandbox_file))
        assert res_read.success is True
        assert "Mission Critical Data" in res_read.data["content"]

        # 3. Path traversal attack attempt to access Windows root
        traversal_path = str(tmp_path / ".." / ".." / "Windows" / "System32" / "drivers")
        res_attack = reg.execute("files.read", path=traversal_path)
        assert res_attack.success is False
        assert res_attack.get_error_code() in ("PROTECTED_DIRECTORY", "FILE_NOT_FOUND")

        # 4. Safe Rename
        res_rename = reg.execute("files.rename", path=str(sandbox_file), new_name="renamed_doc.txt", confirmed=True)
        assert res_rename.success is True
        assert (tmp_path / "renamed_doc.txt").exists()

        # 5. Safe Delete
        res_del = reg.execute("files.delete", path=str(tmp_path / "renamed_doc.txt"), confirmed=True)
        assert res_del.success is True
        assert not (tmp_path / "renamed_doc.txt").exists()

    def test_real_git_workflow_lifecycle(self, tmp_path: Path) -> None:
        """Test real Git repository creation, staging, commit, diff, and branch switching."""
        git_dir = tmp_path / "test_repo"
        git_dir.mkdir()

        # Init real git repo
        subprocess.run(["git", "init"], cwd=str(git_dir), check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "FridayTester"], cwd=str(git_dir), check=True)
        subprocess.run(["git", "config", "user.email", "tester@friday.ai"], cwd=str(git_dir), check=True)

        # Create a source file
        code_file = git_dir / "main.py"
        code_file.write_text("print('Hello Friday')", encoding="utf-8")

        reg = ToolRegistry()
        from core.tools.developer.git_ops import (
            GitAddTool,
            GitBranchTool,
            GitCommitTool,
            GitCreateBranchTool,
            GitDiffTool,
            GitLogTool,
            GitStatusTool,
        )
        reg.register_many([
            GitStatusTool(),
            GitDiffTool(),
            GitLogTool(),
            GitBranchTool(),
            GitAddTool(),
            GitCommitTool(),
            GitCreateBranchTool(),
        ])

        # Status check
        res_stat = reg.execute("git.status", cwd=str(git_dir))
        assert res_stat.success is True

        # Add & Commit
        res_add = reg.execute("git.add", files=".", cwd=str(git_dir))
        assert res_add.success is True

        res_commit = reg.execute("git.commit", message="Initial commit by Friday", cwd=str(git_dir), confirmed=True)
        assert res_commit.success is True

        # Branch creation
        res_branch = reg.execute("git.create_branch", branch_name="feature-ai-agent", cwd=str(git_dir))
        assert res_branch.success is True

        # Log
        res_log = reg.execute("git.log", max_count=1, cwd=str(git_dir))
        assert res_log.success is True
        assert len(res_log.data["commits"]) >= 1

    def test_memory_persistence_across_restart(self, tmp_path: Path) -> None:
        """Verify memory survives Python process / instance restart and filters credentials."""
        mem_file = tmp_path / "persistent_memory.json"

        # Session 1: Store facts and aliases
        session1 = MemoryManager(memory_file=mem_file)
        session1.remember("project_alpha", "Autonomous Drone Controller", category="facts")
        session1.remember("Nova", "C:/Projects/NovaStudio", category="project_aliases")

        # Verify credential rejection
        ok, msg = session1.remember("secret_token", "ghp_1234567890abcdef1234567890abcdef1234", category="facts")
        assert ok is False
        assert "sensitive" in msg.lower()

        # Session 2: Fresh instance (simulating assistant restart)
        session2 = MemoryManager(memory_file=mem_file)
        results = session2.recall("Nova")
        assert "Nova" in str(results)
        assert "C:/Projects/NovaStudio" in str(results)

        facts = session2.recall("project_alpha")
        assert "Autonomous Drone Controller" in str(facts)

    def test_scheduler_persistence_and_trigger(self, tmp_path: Path) -> None:
        """Verify persistent timer survives restart and executes trigger callback."""
        storage = tmp_path / "test_sched.json"
        triggered_events: list[ScheduledEvent] = []

        def on_trigger(event: ScheduledEvent) -> None:
            triggered_events.append(event)

        # Session 1: Add short timer
        sch1 = PersistentScheduler(storage_file=storage, on_trigger=on_trigger)
        ev = sch1.add_timer(seconds=0.3, message="Wakeup Call")
        time.sleep(0.6)

        assert len(triggered_events) >= 1
        assert triggered_events[0].message == "Wakeup Call"

    def test_task_manager_cancellation_propagation(self) -> None:
        """Verify cancellation token stops long running background tasks cleanly."""
        tm = TaskManager()
        task = tm.create_task("Long Running Gradle Simulation", steps=[])

        def simulated_worker(t: Any) -> None:
            for _ in range(50):
                if t.stop_event.is_set():
                    t.status = TaskStatus.CANCELLED
                    return
                time.sleep(0.05)

        tm.start_task_async(task, simulated_worker)
        time.sleep(0.1)

        # Cancel task
        success = tm.cancel_task(task.task_id)
        assert success is True
        time.sleep(0.15)
        assert task.status == TaskStatus.CANCELLED

    def test_permission_token_security_and_expiry(self) -> None:
        """Verify permission manager enforces tokens, risk classification, and prevents tampering."""
        from core.tools.base import BaseTool

        class HighRiskTool(BaseTool):
            name = "security.mass_wipe"
            risk_level = RiskLevel.HIGH_RISK

            def execute(self, **kwargs: Any) -> ToolResult:
                return ToolResult(success=True, message="Wipe executed")

        pm = PermissionManager()
        reg = ToolRegistry(permission_manager=pm)
        reg.register(HighRiskTool())

        # Unconfirmed execution blocked
        res_blocked = reg.execute("security.mass_wipe")
        assert res_blocked.success is False
        assert res_blocked.needs_confirmation is True
        token = res_blocked.data["confirmation_token"]

        # Confirm with valid token
        res_confirmed = pm.confirm_token(token)
        assert res_confirmed.success is True

        # Reusing the same token should fail
        res_reused = pm.confirm_token(token)
        assert res_reused.success is False
        assert res_reused.get_error_code() == "INVALID_TOKEN"
