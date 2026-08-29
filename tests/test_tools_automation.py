from __future__ import annotations

from pathlib import Path
import pytest

from core.automation import (
    PersistentScheduler,
    WorkflowEngine,
    register_automation_tools,
)
from core.tools.registry import ToolRegistry


@pytest.fixture
def automation_system(tmp_path: Path) -> ToolRegistry:
    reg = ToolRegistry()
    sch = PersistentScheduler(storage_file=tmp_path / "test_schedules.json")
    we = WorkflowEngine(registry=reg, workflows_file=tmp_path / "test_workflows.json")
    register_automation_tools(reg, scheduler=sch, workflow_engine=we)
    return reg


def test_scheduler_and_timer_tools(automation_system: ToolRegistry) -> None:
    # 1. Set timer
    res = automation_system.execute("timer.set", seconds=30.0, label="Test 30s timer")
    assert res.success is True
    assert "event_id" in res.data

    # 2. List schedules
    list_res = automation_system.execute("scheduler.list")
    assert list_res.success is True
    assert list_res.data["count"] >= 1

    # 3. Cancel schedule
    eid = res.data["event_id"]
    cancel_res = automation_system.execute("scheduler.cancel", event_id=eid)
    assert cancel_res.success is True


def test_workflow_list_and_run(automation_system: ToolRegistry) -> None:
    res = automation_system.execute("workflow.list")
    assert res.success is True
    assert "morning_routine" in res.data["workflows"]
