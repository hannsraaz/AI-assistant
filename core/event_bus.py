from __future__ import annotations

import logging
import queue
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("event_bus")


@dataclass(slots=True)
class Event:
    topic: str
    payload: dict[str, Any] = field(default_factory=dict)
    source: str = "system"
    timestamp: float = field(default_factory=time.time)


class EventBus:
    """Thread-safe, decoupled Publish-Subscribe event bus for FRIDAY subsystems."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable[[Event], None]]] = {}
        self._lock = threading.Lock()
        self._queue: queue.Queue[Event] = queue.Queue(maxsize=1000)
        self._running = threading.Event()
        self._worker_thread: threading.Thread | None = None

    def start(self) -> None:
        if self._running.is_set():
            return
        self._running.set()
        self._worker_thread = threading.Thread(target=self._dispatch_loop, daemon=True)
        self._worker_thread.start()

    def stop(self) -> None:
        self._running.clear()
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=1.0)

    def subscribe(self, topic: str, callback: Callable[[Event], None]) -> None:
        """Subscribe to a specific topic or wildcard '*' for all events."""
        with self._lock:
            if topic not in self._subscribers:
                self._subscribers[topic] = []
            if callback not in self._subscribers[topic]:
                self._subscribers[topic].append(callback)

    def unsubscribe(self, topic: str, callback: Callable[[Event], None]) -> None:
        with self._lock:
            if topic in self._subscribers and callback in self._subscribers[topic]:
                self._subscribers[topic].remove(callback)

    def publish(self, topic: str, payload: dict[str, Any] | None = None, source: str = "system") -> None:
        """Publish an event asynchronously."""
        evt = Event(topic=topic, payload=payload or {}, source=source)
        try:
            self._queue.put_nowait(evt)
        except queue.Full:
            try:
                self._queue.get_nowait()
                self._queue.put_nowait(evt)
            except Exception:
                pass

    def _dispatch_loop(self) -> None:
        while self._running.is_set():
            try:
                event = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue

            # Gather subscribers
            with self._lock:
                direct_subs = list(self._subscribers.get(event.topic, []))
                wildcard_subs = list(self._subscribers.get("*", []))

            for handler in direct_subs + wildcard_subs:
                try:
                    handler(event)
                except Exception as exc:
                    logger.warning("Event bus handler error for topic %s: %s", event.topic, exc)


global_event_bus = EventBus()
