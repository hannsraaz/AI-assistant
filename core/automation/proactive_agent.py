from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from typing import Any

import psutil

logger = logging.getLogger("proactive")


class ProactiveMonitor:
    """Monitors system events (critical battery, disk warnings, long task completions)
    
    and delivers context-aware, non-intrusive voice/UI notifications.
    """

    def __init__(
        self,
        on_notification: Callable[[str], None] | None = None,
        check_interval: float = 30.0,
        enabled: bool = True,
    ) -> None:
        self.on_notification = on_notification or (lambda _: None)
        self.check_interval = check_interval
        self.enabled = enabled

        self._stop_event = threading.Event()
        self._last_battery_alert = 0.0
        self._last_disk_alert = 0.0
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            if self.enabled:
                self._check_battery()
                self._check_disk()
            time.sleep(self.check_interval)

    def _check_battery(self) -> None:
        try:
            battery = psutil.sensors_battery()
            if battery and not battery.power_plugged:
                if battery.percent <= 15:
                    now = time.time()
                    # Alert at most once every 15 minutes
                    if now - self._last_battery_alert > 900:
                        self._last_battery_alert = now
                        self.on_notification(f"Warning: Battery is low at {int(battery.percent)} percent. Please plug in your charger.")
        except Exception:
            pass

    def _check_disk(self) -> None:
        try:
            usage = psutil.disk_usage("C:\\")
            free_gb = usage.free / (1024**3)
            if free_gb < 5.0:  # Less than 5 GB free
                now = time.time()
                if now - self._last_disk_alert > 3600:  # Alert at most once per hour
                    self._last_disk_alert = now
                    self.on_notification(f"Storage warning: C drive has only {free_gb:.1f} GB free.")
        except Exception:
            pass
