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
from core.hinglish_normalizer import HinglishNormalizer, UserLanguage
from core.response_engine import ResponseEngine
from desktop_controller import DesktopController


@dataclass(slots=True)
class IntentResult:
    handled: bool
    response: str = ""
    should_exit: bool = False
    custom_action: Callable[[], None] | None = None
    language: UserLanguage = UserLanguage.ENGLISH


class IntentRouter:
    """Fast-path sub-50ms intent router for desktop commands, windows, apps, timers,

    system actions, and native Hinglish command normalization.
    """

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
        # Pre-process Hinglish commands to canonical forms while preserving detected language
        normalized_cmd, is_hinglish, lang = HinglishNormalizer.normalize_hinglish_command(query)
        cleaned = normalized_cmd.strip()
        lowered = cleaned.lower()

        # 1. Volume & Audio
        if self._matches(lowered, [r"\bmute\b", r"\bsilence audio\b"]):
            res = self.desktop.registry.execute("system.volume.mute")
            return IntentResult(handled=True, response=ResponseEngine.format_tool_response("system.volume.mute", res, language=lang), language=lang)

        if self._matches(lowered, [r"\bunmute\b"]):
            res = self.desktop.registry.execute("system.volume.unmute")
            return IntentResult(handled=True, response=ResponseEngine.format_tool_response("system.volume.unmute", res, language=lang), language=lang)

        if self._matches(lowered, [r"\btoggle mute\b"]):
            return IntentResult(handled=True, response=self.desktop.toggle_mute(), language=lang)

        vol_match = re.search(r"\b(?:set|turn|change)?\s*volume\s*(?:to|at)?\s*(\d{1,3})\s*(?:%|percent)?\b", lowered)
        if vol_match:
            val = int(vol_match.group(1))
            res = self.desktop.registry.execute("system.volume.set", percentage=val)
            return IntentResult(handled=True, response=ResponseEngine.format_tool_response("system.volume.set", res, language=lang), language=lang)

        if self._matches(lowered, [r"\bvolume up\b", r"\bturn up the volume\b", r"\bincrease volume\b", r"\blouder\b"]):
            res = self.desktop.registry.execute("system.volume.up", delta=10)
            return IntentResult(handled=True, response=ResponseEngine.format_tool_response("system.volume.up", res, language=lang), language=lang)

        if self._matches(lowered, [r"\bvolume down\b", r"\bturn down the volume\b", r"\bdecrease volume\b", r"\bsofter\b", r"\bquieter\b"]):
            res = self.desktop.registry.execute("system.volume.down", delta=10)
            return IntentResult(handled=True, response=ResponseEngine.format_tool_response("system.volume.down", res, language=lang), language=lang)

        if self._matches(lowered, [r"\bwhat(?:'s| is) the volume\b", r"\bcurrent volume\b"]):
            res = self.desktop.registry.execute("system.volume.get")
            return IntentResult(handled=True, response=ResponseEngine.format_tool_response("system.volume.get", res, language=lang), language=lang)

        # 2. Media Controls
        if self._matches(lowered, [r"\bplay(?:/|\s*)pause\b", r"\bpause music\b", r"\bresume music\b", r"\bplay music\b", r"\bpause\b", r"\bresume\b"]):
            return IntentResult(handled=True, response=self.desktop.media_play_pause(), language=lang)
        if self._matches(lowered, [r"\bnext track\b", r"\bnext song\b", r"\bskip song\b", r"\bskip track\b"]):
            return IntentResult(handled=True, response=self.desktop.media_next(), language=lang)
        if self._matches(lowered, [r"\bprevious track\b", r"\bprevious song\b", r"\blast song\b"]):
            return IntentResult(handled=True, response=self.desktop.media_previous(), language=lang)
        if self._matches(lowered, [r"\bstop music\b", r"\bstop playback\b"]):
            return IntentResult(handled=True, response=self.desktop.media_stop(), language=lang)

        # 3. Brightness Controls
        bright_match = re.search(r"\b(?:set|turn|change)?\s*brightness\s*(?:to|at)?\s*(\d{1,3})\s*(?:%|percent)?\b", lowered)
        if bright_match:
            val = int(bright_match.group(1))
            res = self.desktop.registry.execute("system.brightness.set", level=val)
            return IntentResult(handled=True, response=ResponseEngine.format_tool_response("system.brightness.set", res, language=lang), language=lang)

        if self._matches(lowered, [r"\bbrightness up\b", r"\bincrease brightness\b", r"\bbrighter\b"]):
            res = self.desktop.registry.execute("system.brightness.set", level=min(100, self.desktop.get_brightness() + 15))
            return IntentResult(handled=True, response=ResponseEngine.format_tool_response("system.brightness.set", res, language=lang), language=lang)

        if self._matches(lowered, [r"\bbrightness down\b", r"\bdecrease brightness\b", r"\bdimmer\b", r"\bdim screen\b"]):
            res = self.desktop.registry.execute("system.brightness.set", level=max(0, self.desktop.get_brightness() - 15))
            return IntentResult(handled=True, response=ResponseEngine.format_tool_response("system.brightness.set", res, language=lang), language=lang)

        if self._matches(lowered, [r"\bwhat(?:'s| is) the brightness\b"]):
            res = self.desktop.registry.execute("system.brightness.get")
            return IntentResult(handled=True, response=ResponseEngine.format_tool_response("system.brightness.get", res, language=lang), language=lang)

        # 4. Windows & Window Management
        if self._matches(lowered, [r"\bshow desktop\b", r"\bminimize all\b", r"\bminimize windows\b", r"\bminimize everything\b"]):
            res = self.desktop.registry.execute("windows.show_desktop")
            return IntentResult(handled=True, response=ResponseEngine.format_tool_response("windows.show_desktop", res, language=lang), language=lang)

        if self._matches(lowered, [r"\bwhat windows are open\b", r"\blist windows\b", r"\bshow open windows\b"]):
            res = self.desktop.registry.execute("windows.list")
            return IntentResult(handled=True, response=ResponseEngine.format_tool_response("windows.list", res, language=lang), language=lang)

        if self._matches(lowered, [r"\bwhat applications are open\b", r"\bwhat apps are open\b", r"\blist applications\b", r"\blist apps\b"]):
            res = self.desktop.registry.execute("apps.list")
            return IntentResult(handled=True, response=ResponseEngine.format_tool_response("apps.list", res, language=lang), language=lang)

        # Focus / Switch to app
        switch_app_match = re.search(r"\b(?:switch to|focus|bring up|bring)\s+(.+?)(?:\s+to the front|\s+window)?$", cleaned, re.IGNORECASE)
        if switch_app_match:
            target_app = switch_app_match.group(1).strip()
            if target_app.lower() not in {"desktop", "the desktop", "window", "tab"}:
                res = self.desktop.registry.execute("apps.focus", app_name=target_app)
                if res.success:
                    return IntentResult(handled=True, response=ResponseEngine.format_tool_response("apps.focus", res, language=lang), language=lang)

        if self._matches(lowered, [r"\bmaximize (?:active |this )?window\b", r"\bmaximize\b"]):
            res = self.desktop.registry.execute("windows.maximize")
            return IntentResult(handled=True, response=ResponseEngine.format_tool_response("windows.maximize", res, language=lang), language=lang)

        if self._matches(lowered, [r"\bminimize (?:active |this )?window\b", r"\bminimize this\b"]):
            res = self.desktop.registry.execute("windows.minimize")
            return IntentResult(handled=True, response=ResponseEngine.format_tool_response("windows.minimize", res, language=lang), language=lang)

        if self._matches(lowered, [r"\brestore window\b", r"\bunmaximize\b"]):
            res = self.desktop.registry.execute("windows.restore")
            return IntentResult(handled=True, response=ResponseEngine.format_tool_response("windows.restore", res, language=lang), language=lang)

        if self._matches(lowered, [r"\bclose active window\b", r"\bclose window\b", r"\bclose this\b", r"\bclose this window\b"]):
            res = self.desktop.registry.execute("windows.close")
            return IntentResult(handled=True, response=ResponseEngine.format_tool_response("windows.close", res, language=lang), language=lang)

        # Close specific app
        close_app_match = re.search(r"\bclose\s+([a-zA-Z0-9\s]+)$", cleaned, re.IGNORECASE)
        if close_app_match:
            app_to_close = close_app_match.group(1).strip()
            if app_to_close.lower() not in {"window", "this", "active window", "assistant"}:
                res = self.desktop.registry.execute("apps.close", app_name=app_to_close, confirmed=True)
                if res.success:
                    return IntentResult(handled=True, response=ResponseEngine.format_tool_response("apps.close", res, language=lang), language=lang)

        if self._matches(lowered, [r"\bswitch window\b", r"\balt tab\b"]):
            return IntentResult(handled=True, response=self.desktop.switch_window(), language=lang)

        if self._matches(lowered, [r"\block (?:pc|computer|workstation)\b"]):
            return IntentResult(handled=True, response=self.desktop.lock_pc(), language=lang)

        # 5. Screenshots & Clipboard
        if self._matches(lowered, [r"\btake a screenshot of (?:the )?active window\b", r"\bcapture active window\b", r"\bwindow screenshot\b"]):
            res = self.desktop.registry.execute("screenshot.take", mode="active_window")
            return IntentResult(handled=True, response=ResponseEngine.format_tool_response("screenshot.take", res, language=lang), language=lang)

        if self._matches(lowered, [r"\btake a screenshot\b", r"\bcapture screen\b", r"\bscreenshot\b"]):
            res = self.desktop.registry.execute("screenshot.take", mode="fullscreen")
            return IntentResult(handled=True, response=ResponseEngine.format_tool_response("screenshot.take", res, language=lang), language=lang)

        copy_match = re.search(r"\bcopy\s+(?:\"|')?(.+?)(?:\"|')?\s+to (?:the )?clipboard\b", cleaned, re.IGNORECASE)
        if copy_match:
            text_to_copy = copy_match.group(1).strip()
            res = self.desktop.registry.execute("clipboard.write", text=text_to_copy)
            return IntentResult(handled=True, response=ResponseEngine.format_tool_response("clipboard.write", res, language=lang), language=lang)

        if self._matches(lowered, [r"\bclear (?:the )?clipboard\b", r"\bempty clipboard\b"]):
            res = self.desktop.registry.execute("clipboard.clear")
            return IntentResult(handled=True, response=ResponseEngine.format_tool_response("clipboard.clear", res, language=lang), language=lang)

        if self._matches(lowered, [r"\bread clipboard\b", r"\bwhat(?:'s| is) on (?:my )?clipboard\b", r"\bpaste clipboard\b"]):
            res = self.desktop.registry.execute("clipboard.read")
            return IntentResult(handled=True, response=ResponseEngine.format_tool_response("clipboard.read", res, language=lang), language=lang)

        # 6. System Diagnostics
        if self._matches(lowered, [r"\bsystem status\b", r"\bpc status\b", r"\bcomputer status\b", r"\bperformance\b"]):
            return IntentResult(handled=True, response=self.desktop.get_system_status(), language=lang)

        if self._matches(lowered, [r"\bbattery\b", r"\bbattery level\b", r"\bhow much battery\b"]):
            res = self.desktop.registry.execute("system.battery")
            return IntentResult(handled=True, response=ResponseEngine.format_tool_response("system.battery", res, language=lang), language=lang)

        if self._matches(lowered, [r"\bdisk space\b", r"\bfree storage\b", r"\bstorage\b", r"\bhard drive\b"]):
            res = self.desktop.registry.execute("system.disk")
            return IntentResult(handled=True, response=ResponseEngine.format_tool_response("system.disk", res, language=lang), language=lang)

        if self._matches(lowered, [r"\bcpu usage\b", r"\bhow is the cpu\b"]):
            res = self.desktop.registry.execute("system.cpu")
            return IntentResult(handled=True, response=ResponseEngine.format_tool_response("system.cpu", res, language=lang), language=lang)

        if self._matches(lowered, [r"\bram usage\b", r"\bmemory usage\b", r"\bhow much ram\b"]):
            res = self.desktop.registry.execute("system.ram")
            return IntentResult(handled=True, response=ResponseEngine.format_tool_response("system.ram", res, language=lang), language=lang)

        if self._matches(lowered, [r"\bnetwork status\b", r"\bnetwork stats\b", r"\binternet status\b"]):
            res = self.desktop.registry.execute("system.network")
            return IntentResult(handled=True, response=ResponseEngine.format_tool_response("system.network", res, language=lang), language=lang)

        # 7. Time & Date
        if self._matches(lowered, [r"\bwhat.*time\b", r"\btell.*time\b", r"\bcurrent time\b", r"\btime right now\b", r"^time$"]):
            now = datetime.datetime.now()
            time_str = now.strftime("%I:%M %p")
            resp = f"Abhi {time_str} ho rahe hain." if is_hinglish else f"It is {time_str}."
            return IntentResult(handled=True, response=resp, language=lang)

        if self._matches(lowered, [r"\bwhat.*date\b", r"\btell.*date\b", r"\btoday.*date\b", r"\bwhat day\b", r"^date$"]):
            now = datetime.datetime.now()
            date_str = now.strftime("%A, %B %d, %Y")
            resp = f"Aaj {date_str} hai." if is_hinglish else f"Today is {date_str}."
            return IntentResult(handled=True, response=resp, language=lang)

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
            alert_msg = f"{duration_val} {unit} ka timer poora ho gaya!" if is_hinglish else f"Timer for {duration_val} {unit} has finished!"
            self._start_timer(seconds, alert_msg)
            resp = f"{duration_val} {unit} ka timer laga diya." if is_hinglish else f"Timer set for {duration_val} {unit}."
            return IntentResult(handled=True, response=resp, language=lang)

        # 9. Notes & Quick Memos
        note_match = re.search(r"\b(?:take a note|save note|note down|add note)\s*[:]?\s*(.+)", cleaned, re.IGNORECASE)
        if note_match:
            note_text = note_match.group(1).strip()
            return IntentResult(handled=True, response=self.desktop.add_note(note_text), language=lang)

        if self._matches(lowered, [r"\bread (?:my )?notes\b", r"\bwhat are my notes\b", r"\bshow notes\b"]):
            return IntentResult(handled=True, response=self.desktop.read_notes(), language=lang)

        # 10. YouTube & Web Search
        yt_match = re.search(r"\b(?:play|search)\s+(.+?)\s+on youtube\b", cleaned, re.IGNORECASE)
        if yt_match:
            return IntentResult(handled=True, response=self.desktop.search_youtube(yt_match.group(1)), language=lang)

        google_match = re.search(r"\b(?:search (?:the web|google) for|google)\s+(.+)", cleaned, re.IGNORECASE)
        if google_match:
            return IntentResult(handled=True, response=self.desktop.search_web(google_match.group(1)), language=lang)

        # 11. Weather
        if "weather" in lowered:
            return self._handle_weather(cleaned, is_hinglish=is_hinglish, lang=lang)

        # 12. Open Applications or Folders
        app_match = re.search(r"\b(?:open|launch|start)\s+(.+)", cleaned, re.IGNORECASE)
        if app_match:
            target = app_match.group(1).strip()
            if "folder" in target.lower():
                folder_name = target.lower().replace("folder", "").strip()
                return IntentResult(handled=True, response=self.desktop.open_folder(folder_name), language=lang)
            res = self.desktop.registry.execute("apps.open", app_name=target)
            return IntentResult(handled=True, response=ResponseEngine.format_tool_response("apps.open", res, language=lang), language=lang)

        # 13. Assistant Lifecycle
        if lowered in {"exit", "quit", "shutdown assistant", "stop assistant", "goodbye friday", "bye friday"}:
            resp = "Theek hai, main standby pe ja raha hoon. Alvida!" if is_hinglish else "Shutting down. Have a wonderful day!"
            return IntentResult(handled=True, response=resp, should_exit=True, language=lang)

        return IntentResult(handled=False, language=lang)

    def _matches(self, text: str, patterns: list[str]) -> bool:
        return any(re.search(pat, text) for pat in patterns)

    def _start_timer(self, seconds: int, message: str) -> None:
        def _worker() -> None:
            time.sleep(seconds)
            self.on_timer_alert(message)

        t = threading.Thread(target=_worker, daemon=True)
        t.start()

    def _handle_weather(self, query: str, is_hinglish: bool = False, lang: UserLanguage = UserLanguage.ENGLISH) -> IntentResult:
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
                if is_hinglish:
                    return IntentResult(
                        handled=True,
                        response=f"{location} mein mausam {desc} hai aur temperature {temp}°C hai (feels like {feels}°C).",
                        language=lang,
                    )
                return IntentResult(
                    handled=True,
                    response=f"The weather in {location} is {desc} at {temp}°C, feels like {feels}°C.",
                    language=lang,
                )
        except Exception:
            pass
        err_msg = f"{location} ka weather update abhi fetch nahi ho paya." if is_hinglish else f"Could not fetch weather update for {location} right now."
        return IntentResult(handled=True, response=err_msg, language=lang)
