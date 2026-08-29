from __future__ import annotations

import datetime
import re
import threading
import time
import urllib.parse
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import requests

from config import AppConfig
from desktop_controller import DesktopController


@dataclass(slots=True)
class IntentResult:
    handled: bool
    response: str = ""
    should_exit: bool = False
    custom_action: Callable[[], None] | None = None


class IntentRouter:
    """Fast-path sub-50ms intent router for desktop commands, timers, and system actions."""

    def __init__(
        self,
        config: AppConfig,
        desktop: DesktopController,
        on_timer_alert: Callable[[str], None] | None = None,
    ) -> None:
        self.config = config
        self.desktop = desktop
        self.on_timer_alert = on_timer_alert or (lambda _: None)

    def route(self, query: str) -> IntentResult:
        cleaned = query.strip()
        lowered = cleaned.lower()

        # 1. Volume & Audio
        if self._matches(lowered, [r"\bmute\b", r"\bsilence audio\b"]):
            return IntentResult(handled=True, response=self.desktop.mute())
        if self._matches(lowered, [r"\bunmute\b"]):
            return IntentResult(handled=True, response=self.desktop.unmute())
        if self._matches(lowered, [r"\btoggle mute\b"]):
            return IntentResult(handled=True, response=self.desktop.toggle_mute())

        vol_match = re.search(r"\b(?:set|turn|change)?\s*volume\s*(?:to|at)?\s*(\d{1,3})\s*(?:%|percent)?\b", lowered)
        if vol_match:
            val = int(vol_match.group(1))
            return IntentResult(handled=True, response=self.desktop.set_volume(val))

        if self._matches(lowered, [r"\bvolume up\b", r"\bturn up the volume\b", r"\bincrease volume\b", r"\blouder\b"]):
            return IntentResult(handled=True, response=self.desktop.change_volume(10))
        if self._matches(lowered, [r"\bvolume down\b", r"\bturn down the volume\b", r"\bdecrease volume\b", r"\bsofter\b", r"\bquieter\b"]):
            return IntentResult(handled=True, response=self.desktop.change_volume(-10))
        if self._matches(lowered, [r"\bwhat(?:'s| is) the volume\b", r"\bcurrent volume\b"]):
            return IntentResult(handled=True, response=f"The current volume is {self.desktop.get_volume()} percent.")

        # 2. Media Controls
        if self._matches(lowered, [r"\bplay(?:/|\s*)pause\b", r"\bpause music\b", r"\bresume music\b", r"\bplay music\b", r"\bpause\b", r"\bresume\b"]):
            return IntentResult(handled=True, response=self.desktop.media_play_pause())
        if self._matches(lowered, [r"\bnext track\b", r"\bnext song\b", r"\bskip song\b", r"\bskip track\b"]):
            return IntentResult(handled=True, response=self.desktop.media_next())
        if self._matches(lowered, [r"\bprevious track\b", r"\bprevious song\b", r"\blast song\b"]):
            return IntentResult(handled=True, response=self.desktop.media_previous())
        if self._matches(lowered, [r"\bstop music\b", r"\bstop playback\b"]):
            return IntentResult(handled=True, response=self.desktop.media_stop())

        # 3. Brightness Controls
        bright_match = re.search(r"\b(?:set|turn|change)?\s*brightness\s*(?:to|at)?\s*(\d{1,3})\s*(?:%|percent)?\b", lowered)
        if bright_match:
            val = int(bright_match.group(1))
            return IntentResult(handled=True, response=self.desktop.set_brightness(val))

        if self._matches(lowered, [r"\bbrightness up\b", r"\bincrease brightness\b", r"\bbrighter\b"]):
            return IntentResult(handled=True, response=self.desktop.change_brightness(15))
        if self._matches(lowered, [r"\bbrightness down\b", r"\bdecrease brightness\b", r"\bdimmer\b", r"\bdim screen\b"]):
            return IntentResult(handled=True, response=self.desktop.change_brightness(-15))
        if self._matches(lowered, [r"\bwhat(?:'s| is) the brightness\b"]):
            return IntentResult(handled=True, response=f"Brightness is set to {self.desktop.get_brightness()} percent.")

        # 4. Windows & Desktop Management
        if self._matches(lowered, [r"\bshow desktop\b", r"\bminimize all\b", r"\bminimize windows\b"]):
            return IntentResult(handled=True, response=self.desktop.minimize_all())
        if self._matches(lowered, [r"\bclose active window\b", r"\bclose window\b", r"\bclose this\b", r"\bclose app\b"]):
            return IntentResult(handled=True, response=self.desktop.close_active_window())
        if self._matches(lowered, [r"\bswitch window\b", r"\bswitch app\b", r"\balt tab\b"]):
            return IntentResult(handled=True, response=self.desktop.switch_window())
        if self._matches(lowered, [r"\block pc\b", r"\block computer\b", r"\block workstation\b"]):
            return IntentResult(handled=True, response=self.desktop.lock_pc())

        # 5. Screenshots & Clipboard
        if self._matches(lowered, [r"\btake a screenshot\b", r"\bcapture screen\b", r"\bscreenshot\b"]):
            return IntentResult(handled=True, response=self.desktop.take_screenshot())
        if self._matches(lowered, [r"\bread clipboard\b", r"\bwhat(?:'s| is) on (?:my )?clipboard\b", r"\bpaste clipboard\b"]):
            return IntentResult(handled=True, response=self.desktop.get_clipboard_text())

        # 6. System Diagnostics
        if self._matches(lowered, [r"\bsystem status\b", r"\bpc status\b", r"\bcomputer status\b", r"\bperformance\b"]):
            return IntentResult(handled=True, response=self.desktop.get_system_status())
        if self._matches(lowered, [r"\bbattery\b", r"\bbattery level\b", r"\bhow much battery\b"]):
            return IntentResult(handled=True, response=self.desktop.get_battery_info())
        if self._matches(lowered, [r"\bdisk space\b", r"\bfree storage\b", r"\bstorage\b", r"\bhard drive\b"]):
            return IntentResult(handled=True, response=self.desktop.get_disk_info())

        # 7. Time & Date
        if self._matches(lowered, [r"\bwhat.*time\b", r"\btell.*time\b", r"\bcurrent time\b", r"\btime right now\b", r"^time$"]):
            now = datetime.datetime.now()
            return IntentResult(handled=True, response=f"It is {now.strftime('%I:%M %p')}.")
        if self._matches(lowered, [r"\bwhat.*date\b", r"\btell.*date\b", r"\btoday.*date\b", r"\bwhat day\b", r"^date$"]):
            now = datetime.datetime.now()
            return IntentResult(handled=True, response=f"Today is {now.strftime('%A, %B %d, %Y')}.")

        # 8. Timers & Alarms
        timer_match = re.search(r"\bset (?:a )?timer for (\d+)\s*(seconds?|secs?|minutes?|mins?|hours?)\b", lowered)
        if timer_match:
            duration_val = int(timer_match.group(1))
            unit = timer_match.group(2)
            seconds = duration_val
            if "min" in unit:
                seconds = duration_val * 60
            elif "hour" in unit:
                seconds = duration_val * 3600
            self._start_timer(seconds, f"Timer for {duration_val} {unit} has finished!")
            return IntentResult(handled=True, response=f"Timer set for {duration_val} {unit}.")

        # 9. Notes & Quick Memos
        note_match = re.search(r"\b(?:take a note|save note|note down|add note)\s*[:]?\s*(.+)", cleaned, re.IGNORECASE)
        if note_match:
            note_text = note_match.group(1).strip()
            return IntentResult(handled=True, response=self.desktop.add_note(note_text))
        if self._matches(lowered, [r"\bread (?:my )?notes\b", r"\bwhat are my notes\b", r"\bshow notes\b"]):
            return IntentResult(handled=True, response=self.desktop.read_notes())

        # 10. YouTube & Web Search
        yt_match = re.search(r"\b(?:play|search)\s+(.+?)\s+on youtube\b", cleaned, re.IGNORECASE)
        if yt_match:
            return IntentResult(handled=True, response=self.desktop.search_youtube(yt_match.group(1)))

        google_match = re.search(r"\b(?:search (?:the web|google) for|google)\s+(.+)", cleaned, re.IGNORECASE)
        if google_match:
            return IntentResult(handled=True, response=self.desktop.search_web(google_match.group(1)))

        # 11. Weather
        if "weather" in lowered:
            return self._handle_weather(cleaned)

        # 12. Open Applications or Folders
        app_match = re.search(r"\b(?:open|launch|start)\s+(.+)", cleaned, re.IGNORECASE)
        if app_match:
            target = app_match.group(1).strip()
            # Check if opening a folder
            if "folder" in target.lower():
                folder_name = target.lower().replace("folder", "").strip()
                return IntentResult(handled=True, response=self.desktop.open_folder(folder_name))
            return IntentResult(handled=True, response=self.desktop.open_app_or_url(target))

        # 13. Assistant Lifecycle
        if lowered in {"exit", "quit", "shutdown assistant", "stop assistant", "goodbye friday", "bye friday"}:
            return IntentResult(handled=True, response="Shutting down. Have a wonderful day!", should_exit=True)

        return IntentResult(handled=False)

    def _matches(self, text: str, patterns: list[str]) -> bool:
        return any(re.search(pat, text) for pat in patterns)

    def _start_timer(self, seconds: int, message: str) -> None:
        def _worker() -> None:
            time.sleep(seconds)
            self.on_timer_alert(message)

        t = threading.Thread(target=_worker, daemon=True)
        t.start()

    def _handle_weather(self, query: str) -> IntentResult:
        match = re.search(r"weather(?: in| for)?\s+(.+)", query, re.IGNORECASE)
        location = match.group(1).strip() if match else self.config.default_location
        try:
            res = requests.get(f"https://wttr.in/{urllib.parse.quote(location)}?format=j1", timeout=4)
            if res.status_code == 200:
                data = res.json()
                current = data.get("current_condition", [{}])[0]
                desc = current.get("weatherDesc", [{}])[0].get("value", "Clear")
                temp = current.get("temp_C", "?")
                feels = current.get("FeelsLikeC", "?")
                return IntentResult(
                    handled=True,
                    response=f"The weather in {location} is {desc} at {temp}°C, feels like {feels}°C.",
                )
        except Exception:
            pass
        return IntentResult(handled=True, response=f"Could not fetch weather update for {location} right now.")
