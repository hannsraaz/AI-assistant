from __future__ import annotations

import logging
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from core.tools.base import BaseTool, RiskLevel, ToolResult

logger = logging.getLogger("task_manager")


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STEP_EXECUTING = "STEP_EXECUTING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class TaskStepStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    RETRYING = "RETRYING"
    WAITING_CONFIRMATION = "WAITING_CONFIRMATION"
    CANCELLED = "CANCELLED"
    SKIPPED = "SKIPPED"


class TaskEvent(str, Enum):
    PLAN_CREATED = "PLAN_CREATED"
    STEP_STARTED = "STEP_STARTED"
    TOOL_EXECUTED = "TOOL_EXECUTED"
    STEP_SUCCEEDED = "STEP_SUCCEEDED"
    STEP_FAILED = "STEP_FAILED"
    REPAIR_STARTED = "REPAIR_STARTED"
    RETRY_STARTED = "RETRY_STARTED"
    WAITING_CONFIRMATION = "WAITING_CONFIRMATION"
    TASK_COMPLETED = "TASK_COMPLETED"
    TASK_FAILED = "TASK_FAILED"
    TASK_CANCELLED = "TASK_CANCELLED"


@dataclass
class TaskStep:
    step_id: str
    description: str
    tool: str
    arguments: dict[str, Any] = field(default_factory=dict)
    expected_result: str = ""
    actual_result: str = ""
    status: TaskStepStatus = TaskStepStatus.PENDING
    attempt_count: int = 0
    verification: str = ""
    error: str | None = None


@dataclass
class TaskRecord:
    task_id: str
    title: str
    status: TaskStatus = TaskStatus.PENDING
    steps: list[TaskStep] = field(default_factory=list)
    current_step: int = 0
    logs: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    result: str | None = None
    error: str | None = None
    stop_event: threading.Event = field(default_factory=threading.Event)
    pause_event: threading.Event = field(default_factory=threading.Event)
    on_event: Callable[[TaskEvent, str], None] | None = None

    def emit_event(self, event: TaskEvent, message: str) -> None:
        entry = f"[{time.strftime('%H:%M:%S')}] [{event.value}] {message}"
        self.logs.append(entry)
        try:
            from core.event_bus import global_event_bus
            global_event_bus.publish(
                "task.event",
                {
                    "task_id": self.task_id,
                    "title": self.title,
                    "event": event.value if hasattr(event, "value") else str(event),
                    "message": message,
                    "status": self.status.value if hasattr(self.status, "value") else str(self.status),
                    "current_step": self.current_step,
                    "total_steps": len(self.steps),
                },
            )
        except Exception:
            pass

        if self.on_event:
            try:
                self.on_event(event, message)
            except Exception:
                pass

    def log(self, message: str) -> None:
        entry = f"[{time.strftime('%H:%M:%S')}] {message}"
        self.logs.append(entry)


class TaskManager:
    """Manages asynchronous autonomous background tasks with real progress events."""

    def __init__(
        self,
        on_task_completed: Callable[[TaskRecord], None] | None = None,
        on_task_event: Callable[[TaskRecord, TaskEvent, str], None] | None = None,
    ) -> None:
        self._tasks: dict[str, TaskRecord] = {}
        self._lock = threading.Lock()
        self.on_task_completed = on_task_completed or (lambda _: None)
        self.on_task_event = on_task_event or (lambda _t, _e, _m: None)

    def create_task(self, title: str, steps: list[TaskStep] | None = None) -> TaskRecord:
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        task = TaskRecord(
            task_id=task_id,
            title=title,
            steps=steps or [],
            on_event=lambda ev, msg: self.on_task_event(task, ev, msg),
        )
        with self._lock:
            self._tasks[task_id] = task
        return task

    def start_task_async(self, task: TaskRecord, executor_fn: Callable[[TaskRecord], None]) -> None:
        thread = threading.Thread(target=self._run_task_wrapper, args=(task, executor_fn), daemon=True)
        thread.start()

    def _run_task_wrapper(self, task: TaskRecord, executor_fn: Callable[[TaskRecord], None]) -> None:
        task.status = TaskStatus.RUNNING
        task.emit_event(TaskEvent.STEP_STARTED, f"Started task '{task.title}'.")
        try:
            executor_fn(task)
            if not task.stop_event.is_set() and task.status != TaskStatus.FAILED:
                task.status = TaskStatus.COMPLETED
                task.emit_event(TaskEvent.TASK_COMPLETED, "Task completed successfully.")
        except Exception as exc:
            task.status = TaskStatus.FAILED
            task.error = str(exc)
            task.emit_event(TaskEvent.TASK_FAILED, f"Task failed: {exc}")
        finally:
            task.finished_at = time.time()
            self.on_task_completed(task)

    def pause_task(self, task_id: str) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if task and task.status in (TaskStatus.RUNNING, TaskStatus.STEP_EXECUTING):
                task.pause_event.set()
                task.status = TaskStatus.PAUSED
                task.log("Task paused by user.")
                return True
        return False

    def resume_task(self, task_id: str) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if task and task.status == TaskStatus.PAUSED:
                task.pause_event.clear()
                task.status = TaskStatus.RUNNING
                task.log("Task resumed by user.")
                return True
        return False

    def cancel_task(self, task_id: str) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if task and task.status in (TaskStatus.RUNNING, TaskStatus.STEP_EXECUTING, TaskStatus.PENDING, TaskStatus.PAUSED):
                task.stop_event.set()
                task.status = TaskStatus.CANCELLED
                task.emit_event(TaskEvent.TASK_CANCELLED, "Task cancelled by user.")
                return True
        return False

    def get_task(self, task_id: str) -> TaskRecord | None:
        with self._lock:
            return self._tasks.get(task_id)

    def list_tasks(self) -> list[dict[str, Any]]:
        with self._lock:
            return [
                {
                    "task_id": t.task_id,
                    "title": t.title,
                    "status": t.status.value,
                    "steps_total": len(t.steps),
                    "current_step": t.current_step,
                    "error": t.error,
                    "result": t.result,
                }
                for t in self._tasks.values()
            ]


# --- Task Management Tools ---

class TaskStartTool(BaseTool):
    name = "task.start"
    description = "Start a background asynchronous task (e.g. build, download, test)."
    risk_level = RiskLevel.SAFE
    capabilities = ["task_management", "background_execution"]
    parameters = {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Title or summary of task."}
        },
        "required": ["title"],
    }

    def __init__(self, task_manager: TaskManager) -> None:
        self.tm = task_manager

    def execute(self, title: str, **kwargs: Any) -> ToolResult:
        task = self.tm.create_task(title, steps=[])
        return ToolResult(
            success=True,
            message=f"Started background task: {title} (ID: {task.task_id}).",
            data={"task_id": task.task_id, "title": title},
        )


class TaskStatusTool(BaseTool):
    name = "task.status"
    description = "Get the current execution status, step progress, and logs of a background task."
    risk_level = RiskLevel.SAFE
    capabilities = ["task_management", "status_check"]
    parameters = {
        "type": "object",
        "properties": {
            "task_id": {"type": "string", "description": "Task ID."}
        },
        "required": ["task_id"],
    }

    def __init__(self, task_manager: TaskManager) -> None:
        self.tm = task_manager

    def execute(self, task_id: str, **kwargs: Any) -> ToolResult:
        task = self.tm.get_task(task_id)
        if not task:
            return ToolResult(success=False, error=f"Task '{task_id}' not found.")
        return ToolResult(
            success=True,
            message=f"Task '{task.title}' is {task.status.value} (Step {task.current_step}/{len(task.steps)}).",
            data={
                "task_id": task.task_id,
                "title": task.title,
                "status": task.status.value,
                "current_step": task.current_step,
                "total_steps": len(task.steps),
                "logs": task.logs[-6:],
                "error": task.error,
                "result": task.result,
            },
        )


class TaskPauseTool(BaseTool):
    name = "task.pause"
    description = "Pause a currently executing background task."
    risk_level = RiskLevel.SAFE
    capabilities = ["task_management"]
    parameters = {
        "type": "object",
        "properties": {"task_id": {"type": "string", "description": "Task ID to pause."}},
        "required": ["task_id"],
    }

    def __init__(self, task_manager: TaskManager) -> None:
        self.tm = task_manager

    def execute(self, task_id: str, **kwargs: Any) -> ToolResult:
        ok = self.tm.pause_task(task_id)
        return ToolResult(success=ok, message=f"Task '{task_id}' paused." if ok else f"Could not pause task '{task_id}'.")


class TaskResumeTool(BaseTool):
    name = "task.resume"
    description = "Resume a paused background task."
    risk_level = RiskLevel.SAFE
    capabilities = ["task_management"]
    parameters = {
        "type": "object",
        "properties": {"task_id": {"type": "string", "description": "Task ID to resume."}},
        "required": ["task_id"],
    }

    def __init__(self, task_manager: TaskManager) -> None:
        self.tm = task_manager

    def execute(self, task_id: str, **kwargs: Any) -> ToolResult:
        ok = self.tm.resume_task(task_id)
        return ToolResult(success=ok, message=f"Task '{task_id}' resumed." if ok else f"Could not resume task '{task_id}'.")


class TaskCancelTool(BaseTool):
    name = "task.cancel"
    description = "Cancel a currently running background task."
    risk_level = RiskLevel.SAFE
    capabilities = ["task_management", "cancellation"]
    parameters = {
        "type": "object",
        "properties": {
            "task_id": {"type": "string", "description": "Task ID to cancel."}
        },
        "required": ["task_id"],
    }

    def __init__(self, task_manager: TaskManager) -> None:
        self.tm = task_manager

    def execute(self, task_id: str, **kwargs: Any) -> ToolResult:
        success = self.tm.cancel_task(task_id)
        if success:
            return ToolResult(success=True, message=f"Task '{task_id}' has been cancelled.")
        return ToolResult(success=False, error=f"Could not cancel task '{task_id}'.")


class TaskListTool(BaseTool):
    name = "task.list"
    description = "List all active and recent background tasks."
    risk_level = RiskLevel.SAFE
    capabilities = ["task_management"]
    parameters = {"type": "object", "properties": {}}

    def __init__(self, task_manager: TaskManager) -> None:
        self.tm = task_manager

    def execute(self, **kwargs: Any) -> ToolResult:
        tasks = self.tm.list_tasks()
        return ToolResult(
            success=True,
            message=f"Total {len(tasks)} task(s).",
            data={"count": len(tasks), "tasks": tasks},
        )
