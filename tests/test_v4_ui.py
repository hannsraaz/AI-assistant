from __future__ import annotations

import os
import tkinter as tk
from unittest.mock import MagicMock
import pytest

from config import AppConfig
from core.agent.task_manager import TaskEvent, TaskRecord, TaskStatus, TaskStep
from gui import AssistantWindow
from ui.components.confirmation_dialog import ConfirmationDialog
from ui.core_canvas import FridayCoreCanvas
from ui.theme import UITheme


@pytest.fixture
def mock_assistant() -> MagicMock:
    asst = MagicMock()
    asst.config = AppConfig()
    asst.task_manager = MagicMock()
    asst.task_manager.list_tasks.return_value = []
    asst.memory = MagicMock()
    asst.memory.list_memories.return_value = [{"category": "fact", "content": "Friday is offline AI", "id": "m1"}]
    asst.desktop = MagicMock()
    asst.desktop.registry = MagicMock()
    asst.desktop.registry.list_tools.return_value = []
    return asst


class TestUITheme:
    def test_theme_constants(self) -> None:
        assert UITheme.BG_DARK == "#080b10"
        assert UITheme.CYAN == "#00d2ff"
        assert "idle" in UITheme.STATE_CONFIG
        assert "speaking" in UITheme.STATE_CONFIG
        assert "listening_for_command" in UITheme.STATE_CONFIG


class TestFridayUIComponents:
    def test_core_canvas_and_window_integration(self, mock_assistant: MagicMock) -> None:
        config = AppConfig()
        win = AssistantWindow(assistant=mock_assistant, config=config)
        win.root.withdraw()
        try:
            # 1. Test Canvas Rendering across states
            core = win.views["home"].core  # type: ignore
            core.set_state("idle")
            core.update_frame(0.05)

            core.set_state("listening_for_command")
            core.set_audio_amplitude(0.75)
            core.update_frame(0.05)

            core.set_state("thinking")
            core.update_frame(0.05)

            core.set_state("speaking")
            core.update_frame(0.05)

            # 2. Check all 10 views are initialized
            expected_views = ["home", "chat", "tasks", "system", "memory", "tools", "vision", "dev", "auto", "settings"]
            for v in expected_views:
                assert v in win.views

            # 3. Test tab switching
            win.switch_view("chat")
            assert win.current_view_name == "chat"
            win.switch_view("system")
            assert win.current_view_name == "system"
            win.switch_view("home")
            assert win.current_view_name == "home"

            # 4. Test state change
            win.set_state("listening_for_command", "Listening for your instruction...")
            win.root.update()
            assert "LISTENING" in win.state_badge.cget("text")

            # 5. Test transcript & response dispatch
            win.set_transcript("open vs code")
            win.set_response("Opening VS Code.")
            win.root.update()

            # 6. Test task event dispatch
            dummy_task = TaskRecord(
                task_id="t_001",
                title="Build APK",
                status=TaskStatus.RUNNING,
                steps=[TaskStep("s1", "Step 1", "tool1"), TaskStep("s2", "Step 2", "tool2")],
                current_step=1,
            )
            win._on_task_event(dummy_task, TaskEvent.STEP_STARTED, "Building Gradle...")
            win.root.update()

            # 7. Test compact mode toggle
            win._toggle_compact_mode()
            assert win._is_compact
            win._toggle_compact_mode()
            assert not win._is_compact

            # 8. Test confirmation modal dialog on window root
            approved = [False]
            def on_approve():
                approved[0] = True

            dlg = ConfirmationDialog(
                win.root,
                title="Delete temporary files",
                message="C:\\temp\\build\\ (12 files)",
                tool_name="files.delete",
                risk_level="HIGH",
                on_approve=on_approve,
            )
            dlg._handle_approve()
            assert approved[0] is True
        finally:
            if win._after_id:
                try:
                    win.root.after_cancel(win._after_id)
                except Exception:
                    pass
            win.root.destroy()
