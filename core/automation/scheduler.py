from __future__ import annotations

import json
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from core.tools.base import BaseTool, RiskLevel, ToolResult


@dataclass
class ScheduledEvent:
    event_id: str
    message: str
    trigger_time: float
    is_recurring: bool = False
    interval_seconds: float = 0.0
    created_at: float = field(default_factory=time.time)


class PersistentScheduler:
    """Manages persistent timers, reminders, and recurring schedules."""

    def __init__(
        self,
        storage_file: str | Path = "data/schedules.json",
        on_trigger: Callable[[ScheduledEvent], None] | None = None,
    ) -> None:
        self.storage_file = Path(storage_file)
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)
        self.on_trigger = on_trigger or (lambda _: None)
        self._events: dict[str, ScheduledEvent] = {}
        self._lock = threading.Lock()
        self._stop_event = threading.Event()

        self._load()
        self._worker_thread = threading.Thread(target=self._loop, daemon=True)
        self._worker_thread.start()

    def _load(self) -> None:
        if self.storage_file.exists():
            try:
                with self.storage_file.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data:
                        event = ScheduledEvent(**item)
                        # Keep future events
                        if event.trigger_time > time.time() or event.is_recurring:
                            self._events[event.event_id] = event
            except Exception:
                pass

    def _save(self) -> None:
        with self.storage_file.open("w", encoding="utf-8") as f:
            json.dump([asdict(e) for e in self._events.values()], f, indent=2)

    def add_timer(self, seconds: float, message: str) -> ScheduledEvent:
        event_id = f"timer_{uuid.uuid4().hex[:6]}"
        event = ScheduledEvent(
            event_id=event_id,
            message=message,
            trigger_time=time.time() + seconds,
        )
        with self._lock:
            self._events[event_id] = event
            self._save()
        return event

    def add_reminder(self, timestamp: float, message: str) -> ScheduledEvent:
        event_id = f"rem_{uuid.uuid4().hex[:6]}"
        event = ScheduledEvent(
            event_id=event_id,
            message=message,
            trigger_time=timestamp,
        )
        with self._lock:
            self._events[event_id] = event
            self._save()
        return event

    def cancel(self, event_id: str) -> bool:
        with self._lock:
            if event_id in self._events:
                del self._events[event_id]
                self._save()
                return True
        return False

    def list_all(self) -> list[dict[str, Any]]:
        now = time.time()
        with self._lock:
            return [
                {
                    "event_id": e.event_id,
                    "message": e.message,
                    "seconds_remaining": max(0, int(e.trigger_time - now)),
                    "trigger_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(e.trigger_time)),
                }
                for e in self._events.values()
            ]

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            now = time.time()
            triggered = []
            with self._lock:
                for eid, ev in list(self._events.items()):
                    if now >= ev.trigger_time:
                        triggered.append(ev)
                        if ev.is_recurring and ev.interval_seconds > 0:
                            ev.trigger_time = now + ev.interval_seconds
                        else:
                            del self._events[eid]
                if triggered:
                    self._save()

            for ev in triggered:
                try:
                    self.on_trigger(ev)
                except Exception:
                    pass

            time.sleep(0.5)


# --- Scheduler Tools ---

class TimerSetTool(BaseTool):
    name = "timer.set"
    description = "Set a timer for a given duration in seconds or minutes."
    risk_level = RiskLevel.SAFE
    parameters = {
        "type": "object",
        "properties": {
            "seconds": {"type": "number", "description": "Duration in seconds."},
            "label": {"type": "string", "description": "Optional label for the timer.", "default": "Timer finished!"},
        },
        "required": ["seconds"],
    }

    def __init__(self, scheduler: PersistentScheduler) -> None:
        self.scheduler = scheduler

    def execute(self, seconds: float, label: str = "Timer finished!", **kwargs: Any) -> ToolResult:
        ev = self.scheduler.add_timer(seconds=seconds, message=label)
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        dur_str = f"{mins} min {secs} sec" if mins > 0 else f"{secs} seconds"
        return ToolResult(
            success=True,
            message=f"Timer set for {dur_str}.",
            data={"event_id": ev.event_id, "duration": dur_str},
        )


class ReminderSetTool(BaseTool):
    name = "reminder.set"
    description = "Set a reminder message for a future time."
    risk_level = RiskLevel.SAFE
    parameters = {
        "type": "object",
        "properties": {
            "message": {"type": "string", "description": "Reminder text."},
            "delay_seconds": {"type": "number", "description": "Delay in seconds from now."},
        },
        "required": ["message", "delay_seconds"],
    }

    def __init__(self, scheduler: PersistentScheduler) -> None:
        self.scheduler = scheduler

    def execute(self, message: str, delay_seconds: float, **kwargs: Any) -> ToolResult:
        ev = self.scheduler.add_timer(seconds=delay_seconds, message=message)
        return ToolResult(
            success=True,
            message=f"Reminder set: '{message}'.",
            data={"event_id": ev.event_id, "message": message},
        )


class SchedulerListTool(BaseTool):
    name = "scheduler.list"
    description = "List all currently active timers and reminders."
    risk_level = RiskLevel.SAFE
    parameters = {"type": "object", "properties": {}}

    def __init__(self, scheduler: PersistentScheduler) -> None:
        self.scheduler = scheduler

    def execute(self, **kwargs: Any) -> ToolResult:
        items = self.scheduler.list_all()
        return ToolResult(
            success=True,
            message=f"You have {len(items)} active timer/reminder(s).",
            data={"count": len(items), "items": items},
        )


class SchedulerCancelTool(BaseTool):
    name = "scheduler.cancel"
    description = "Cancel an active timer or reminder by ID."
    risk_level = RiskLevel.SAFE
    parameters = {
        "type": "object",
        "properties": {
            "event_id": {"type": "string", "description": "Timer or reminder ID to cancel."}
        },
        "required": ["event_id"],
    }

    def __init__(self, scheduler: PersistentScheduler) -> None:
        self.scheduler = scheduler

    def execute(self, event_id: str, **kwargs: Any) -> ToolResult:
        success = self.scheduler.cancel(event_id)
        if success:
            return ToolResult(success=True, message=f"Cancelled {event_id}.")
        return ToolResult(success=False, error=f"Event '{event_id}' not found.")
