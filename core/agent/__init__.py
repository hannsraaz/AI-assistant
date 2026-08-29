"""Agentic Planning & Task Execution for Friday."""
from core.agent.planner import AgenticPlanner
from core.agent.task_manager import (
    TaskCancelTool,
    TaskEvent,
    TaskListTool,
    TaskManager,
    TaskPauseTool,
    TaskRecord,
    TaskResumeTool,
    TaskStartTool,
    TaskStatus,
    TaskStatusTool,
    TaskStep,
    TaskStepStatus,
)
from core.agent.verifier import StepVerifier
from core.tools.registry import ToolRegistry


def register_task_tools(registry: ToolRegistry, task_manager: TaskManager | None = None) -> TaskManager:
    """Register all task management tools."""
    tm = task_manager or TaskManager()
    tools = [
        TaskStartTool(tm),
        TaskStatusTool(tm),
        TaskPauseTool(tm),
        TaskResumeTool(tm),
        TaskCancelTool(tm),
        TaskListTool(tm),
    ]
    registry.register_many(tools)
    return tm


__all__ = [
    "AgenticPlanner",
    "StepVerifier",
    "TaskManager",
    "TaskRecord",
    "TaskStep",
    "TaskStatus",
    "TaskStepStatus",
    "TaskEvent",
    "register_task_tools",
    "TaskStartTool",
    "TaskStatusTool",
    "TaskPauseTool",
    "TaskResumeTool",
    "TaskCancelTool",
    "TaskListTool",
]
