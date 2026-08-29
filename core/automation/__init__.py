"""Automation, scheduling, and proactive monitoring for Friday."""
from core.automation.proactive_agent import ProactiveMonitor
from core.automation.scheduler import (
    PersistentScheduler,
    ReminderSetTool,
    ScheduledEvent,
    SchedulerCancelTool,
    SchedulerListTool,
    TimerSetTool,
)
from core.automation.workflow_engine import (
    WorkflowEngine,
    WorkflowListTool,
    WorkflowRunTool,
)
from core.tools.registry import ToolRegistry


def register_automation_tools(
    registry: ToolRegistry,
    scheduler: PersistentScheduler | None = None,
    workflow_engine: WorkflowEngine | None = None,
) -> tuple[PersistentScheduler, WorkflowEngine]:
    """Register all automation and scheduling tools."""
    sch = scheduler or PersistentScheduler()
    we = workflow_engine or WorkflowEngine(registry)

    tools = [
        TimerSetTool(sch),
        ReminderSetTool(sch),
        SchedulerListTool(sch),
        SchedulerCancelTool(sch),
        WorkflowRunTool(we),
        WorkflowListTool(we),
    ]
    registry.register_many(tools)
    return sch, we


__all__ = [
    "PersistentScheduler",
    "ScheduledEvent",
    "WorkflowEngine",
    "ProactiveMonitor",
    "register_automation_tools",
    "TimerSetTool",
    "ReminderSetTool",
    "SchedulerListTool",
    "SchedulerCancelTool",
    "WorkflowRunTool",
    "WorkflowListTool",
]
