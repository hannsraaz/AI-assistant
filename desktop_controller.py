from __future__ import annotations

import datetime
import os
import subprocess
import urllib.parse
import webbrowser
from pathlib import Path
from typing import Any

from config import DesktopConfig, resolve_path
from core.response_engine import ResponseEngine
from core.tools.permissions import PermissionManager
from core.tools.registry import ToolRegistry
from core.tools.windows import register_windows_tools


class DesktopController:
    """Windows desktop automation and system control engine for Friday.
    
    Seamlessly integrates Friday's modular tool system while providing
    full backward compatibility for existing assistant components and tests.
    """

    def __init__(self, config: DesktopConfig, registry: ToolRegistry | None = None) -> None:
        self.config = config
        self.screenshot_dir = resolve_path(config.screenshot_directory)
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self.notes_file = resolve_path(config.notes_file)
        self.notes_file.parent.mkdir(parents=True, exist_ok=True)

        self.permissions = PermissionManager()
        self.registry = registry or ToolRegistry(permission_manager=self.permissions)
        register_windows_tools(self.registry, screenshot_dir=str(self.screenshot_dir))

        # Permission overrides based on config
        if self.config.allow_power_commands:
            self.permissions.set_override("system.shutdown", True)
            self.permissions.set_override("system.restart", True)

    # -------------------------------------------------------------------------
    # Audio & Volume Controls
    # -------------------------------------------------------------------------

    def get_volume(self) -> int:
        res = self.registry.execute("system.volume.get")
        return res.data.get("volume", 50)

    def set_volume(self, percentage: int) -> str:
        res = self.registry.execute("system.volume.set", percentage=percentage)
        return ResponseEngine.format_tool_response("system.volume.set", res)

    def change_volume(self, delta: int) -> str:
        tool_name = "system.volume.up" if delta >= 0 else "system.volume.down"
        res = self.registry.execute(tool_name, delta=abs(delta))
        return ResponseEngine.format_tool_response(tool_name, res)

    def mute(self) -> str:
        res = self.registry.execute("system.volume.mute")
        return ResponseEngine.format_tool_response("system.volume.mute", res)

    def unmute(self) -> str:
        res = self.registry.execute("system.volume.unmute")
        return ResponseEngine.format_tool_response("system.volume.unmute", res)

    def toggle_mute(self) -> str:
        status = self.registry.execute("system.volume.get")
        is_muted = status.data.get("muted", False)
        if is_muted:
            return self.unmute()
        return self.mute()

    # -------------------------------------------------------------------------
    # Media Playback Controls
    # -------------------------------------------------------------------------

    def media_play_pause(self) -> str:
        res = self.registry.execute("media.play_pause")
        return ResponseEngine.format_tool_response("media.play_pause", res)

    def media_next(self) -> str:
        res = self.registry.execute("media.next")
        return ResponseEngine.format_tool_response("media.next", res)

    def media_previous(self) -> str:
        res = self.registry.execute("media.previous")
        return ResponseEngine.format_tool_response("media.previous", res)

    def media_stop(self) -> str:
        res = self.registry.execute("media.stop")
        return ResponseEngine.format_tool_response("media.stop", res)

    # -------------------------------------------------------------------------
    # Display & Brightness Controls
    # -------------------------------------------------------------------------

    def get_brightness(self) -> int:
        res = self.registry.execute("system.brightness.get")
        return res.data.get("brightness", 75)

    def set_brightness(self, level: int) -> str:
        res = self.registry.execute("system.brightness.set", level=level)
        return ResponseEngine.format_tool_response("system.brightness.set", res)

    def change_brightness(self, delta: int) -> str:
        curr = self.get_brightness()
        target = max(0, min(100, curr + delta))
        return self.set_brightness(target)

    # -------------------------------------------------------------------------
    # Window & Desktop Management
    # -------------------------------------------------------------------------

    def minimize_all(self) -> str:
        res = self.registry.execute("windows.show_desktop")
        return ResponseEngine.format_tool_response("windows.show_desktop", res)

    def close_active_window(self) -> str:
        res = self.registry.execute("windows.close", confirmed=True)
        return ResponseEngine.format_tool_response("windows.close", res)

    def switch_window(self) -> str:
        import ctypes
        import time
        try:
            # Alt + Tab
            ctypes.windll.user32.keybd_event(0x12, 0, 0, 0)
            ctypes.windll.user32.keybd_event(0x09, 0, 0, 0)
            time.sleep(0.05)
            ctypes.windll.user32.keybd_event(0x09, 0, 2, 0)
            ctypes.windll.user32.keybd_event(0x12, 0, 2, 0)
            return "Switched window."
        except Exception as exc:
            return f"Failed to switch window: {exc}"

    def lock_pc(self) -> str:
        res = self.registry.execute("system.lock")
        return ResponseEngine.format_tool_response("system.lock", res)

    # -------------------------------------------------------------------------
    # Screenshots & Clipboard
    # -------------------------------------------------------------------------

    def take_screenshot(self, name: str | None = None, mode: str = "fullscreen") -> str:
        res = self.registry.execute("screenshot.take", name=name, mode=mode)
        return ResponseEngine.format_tool_response("screenshot.take", res)

    def get_clipboard_text(self) -> str:
        res = self.registry.execute("clipboard.read")
        return ResponseEngine.format_tool_response("clipboard.read", res)

    def set_clipboard_text(self, text: str) -> str:
        res = self.registry.execute("clipboard.write", text=text)
        return ResponseEngine.format_tool_response("clipboard.write", res)

    def type_text(self, text: str) -> str:
        try:
            import pyautogui
            pyautogui.write(text, interval=0.01)
            return "Typed text."
        except Exception as exc:
            return f"Could not type text: {exc}"

    # -------------------------------------------------------------------------
    # System Stats & Diagnostics
    # -------------------------------------------------------------------------

    def get_system_status(self) -> str:
        cpu_res = self.registry.execute("system.cpu")
        ram_res = self.registry.execute("system.ram")
        bat_res = self.registry.execute("system.battery")

        cpu = cpu_res.data.get("cpu_percent", 0)
        ram = ram_res.data.get("percent", 0)
        parts = [f"CPU usage is at {cpu:.0f}%", f"RAM usage is at {ram:.0f}%"]

        if bat_res.data.get("has_battery", False):
            plugged = "plugged in" if bat_res.data.get("charging") else "on battery"
            parts.append(f"Battery is at {bat_res.data.get('percent')}% ({plugged})")

        return ". ".join(parts) + "."

    def get_battery_info(self) -> str:
        res = self.registry.execute("system.battery")
        return ResponseEngine.format_tool_response("system.battery", res)

    def get_disk_info(self) -> str:
        res = self.registry.execute("system.disk")
        return ResponseEngine.format_tool_response("system.disk", res)

    # -------------------------------------------------------------------------
    # Applications & Web Automation
    # -------------------------------------------------------------------------

    def open_app_or_url(self, target: str) -> str:
        # 1. Try apps.open tool
        res = self.registry.execute("apps.open", app_name=target)
        if res.success:
            return ResponseEngine.format_tool_response("apps.open", res)

        # 2. Fallback to web search
        return self.search_web(target)

    def search_web(self, query: str) -> str:
        url = self.config.web_search_template.format(query=urllib.parse.quote_plus(query))
        webbrowser.open_new_tab(url)
        return f"Searching Google for '{query}'."

    def search_youtube(self, query: str) -> str:
        url = self.config.youtube_search_template.format(query=urllib.parse.quote_plus(query))
        webbrowser.open_new_tab(url)
        return f"Searching YouTube for '{query}'."

    def open_folder(self, folder_name: str) -> str:
        home = Path.home()
        candidates = {
            "downloads": home / "Downloads",
            "desktop": home / "Desktop",
            "documents": home / "Documents",
            "pictures": home / "Pictures",
            "music": home / "Music",
            "videos": home / "Videos",
            "screenshots": self.screenshot_dir,
        }
        folder_lower = folder_name.lower().strip()
        if folder_lower in candidates:
            target = candidates[folder_lower]
            if target.exists():
                os.startfile(str(target))
                return f"Opening {folder_name} folder."

        p = Path(folder_name).expanduser()
        if p.exists() and p.is_dir():
            os.startfile(str(p))
            return f"Opening folder {folder_name}."

        return f"Could not find folder '{folder_name}'."

    # -------------------------------------------------------------------------
    # Quick Notes
    # -------------------------------------------------------------------------

    def add_note(self, note: str) -> str:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        with self.notes_file.open("a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {note}\n")
        return f"Saved note: '{note}'."

    def read_notes(self) -> str:
        if not self.notes_file.exists():
            return "You don't have any notes saved yet."
        lines = self.notes_file.read_text(encoding="utf-8").strip().splitlines()
        if not lines:
            return "Your notes file is empty."
        recent = lines[-3:]
        return "Your recent notes: " + " | ".join(recent)

    # -------------------------------------------------------------------------
    # Power Controls (Protected)
    # -------------------------------------------------------------------------

    def shutdown(self, restart: bool = False) -> str:
        if not self.config.allow_power_commands:
            return "Power commands are currently disabled in config.json for safety."
        tool_name = "system.restart" if restart else "system.shutdown"
        res = self.registry.execute(tool_name, confirmed=True)
        return ResponseEngine.format_tool_response(tool_name, res)
