from __future__ import annotations

import time
import pytest

from core.agent import TaskManager, TaskStatus, register_task_tools
from core.tools.registry import ToolRegistry


@pytest.fixture
def task_system() -> tuple[ToolRegistry, TaskManager]:
    reg = ToolRegistry()
    tm = TaskManager()
    register_task_tools(reg, task_manager=tm)
    return reg, tm


def test_task_manager_async_lifecycle(task_system: tuple[ToolRegistry, TaskManager]) -> None:
    reg, tm = task_system

    # 1. Start background task
    start_res = reg.execute("task.start", title="Compile demo background build")
    assert start_res.success is True
    task_id = start_res.data["task_id"]

    # 2. Check status
    stat_res = reg.execute("task.status", task_id=task_id)
    assert stat_res.success is True
    assert stat_res.data["task_id"] == task_id

    # 3. List tasks
    list_res = reg.execute("task.list")
    assert list_res.success is True
    assert list_res.data["count"] >= 1

    # 4. Cancel task
    cancel_res = reg.execute("task.cancel", task_id=task_id)
    assert cancel_res.success is True
