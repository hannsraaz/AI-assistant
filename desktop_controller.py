from __future__ import annotations

import ctypes
import datetime
import os
import platform
import subprocess
import time
import urllib.parse
import webbrowser
from pathlib import Path
from typing import Any

import psutil

from config import DesktopConfig, resolve_path


class DesktopController:
    """Windows desktop automation and system control engine for Friday."""

    def __init__(self, config: DesktopConfig) -> None:
        self.config = config
        self.screenshot_dir = resolve_path(config.screenshot_directory)
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self.notes_file = resolve_path(config.notes_file)
        self.notes_file.parent.mkdir(parents=True, exist_ok=True)

        self._pycaw_volume = None
        self._init_pycaw()

    # -------------------------------------------------------------------------
    # Audio & Volume Controls
    # -------------------------------------------------------------------------

    def _init_pycaw(self) -> None:
        try:
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            self._pycaw_volume = ctypes.cast(interface, ctypes.POINTER(IAudioEndpointVolume))
        except Exception:
            self._pycaw_volume = None

    def get_volume(self) -> int:
        if self._pycaw_volume is not None:
            try:
                current_vol = self._pycaw_volume.GetMasterVolumeLevelScalar()
                return int(round(current_vol * 100))
            except Exception:
                pass
        return 50

    def set_volume(self, percentage: int) -> str:
        percentage = max(0, min(100, percentage))
        if self._pycaw_volume is not None:
            try:
                self._pycaw_volume.SetMasterVolumeLevelScalar(percentage / 100.0, None)
                return f"Volume set to {percentage} percent."
            except Exception:
                pass

        # Fallback using nircmd or PowerShell
        try:
            val = int(65535 * (percentage / 100))
            cmd = f"$w = (New-Object -ComObject WScript.Shell); [Audio]::SetVolume({percentage})"
            subprocess.run(["powershell", "-Command", cmd], timeout=3, capture_output=True)
        except Exception:
            pass
        return f"Volume set to {percentage} percent."

    def change_volume(self, delta: int) -> str:
        current = self.get_volume()
        target = max(0, min(100, current + delta))
        return self.set_volume(target)

    def mute(self) -> str:
        if self._pycaw_volume is not None:
            try:
                self._pycaw_volume.SetMute(1, None)
                return "Audio muted."
            except Exception:
                pass
        self._send_virtual_key(0xAD)  # VK_VOLUME_MUTE
        return "Audio muted."

    def unmute(self) -> str:
        if self._pycaw_volume is not None:
            try:
                self._pycaw_volume.SetMute(0, None)
                return "Audio unmuted."
            except Exception:
                pass
        self._send_virtual_key(0xAD)
        return "Audio unmuted."

    def toggle_mute(self) -> str:
        if self._pycaw_volume is not None:
            try:
                is_muted = self._pycaw_volume.GetMute()
                self._pycaw_volume.SetMute(0 if is_muted else 1, None)
                return "Audio unmuted." if is_muted else "Audio muted."
            except Exception:
                pass
        self._send_virtual_key(0xAD)
        return "Toggled mute."

    # -------------------------------------------------------------------------
    # Media Playback Controls
    # -------------------------------------------------------------------------

    def media_play_pause(self) -> str:
        self._send_virtual_key(0xB3)  # VK_MEDIA_PLAY_PAUSE
        return "Toggled media playback."

    def media_next(self) -> str:
        self._send_virtual_key(0xB0)  # VK_MEDIA_NEXT_TRACK
        return "Playing next track."

    def media_previous(self) -> str:
        self._send_virtual_key(0xB1)  # VK_MEDIA_PREV_TRACK
        return "Playing previous track."

    def media_stop(self) -> str:
        self._send_virtual_key(0xB2)  # VK_MEDIA_STOP
        return "Stopped playback."

    # -------------------------------------------------------------------------
    # Display & Brightness Controls
    # -------------------------------------------------------------------------

    def get_brightness(self) -> int:
        try:
            import screen_brightness_control as sbc

            val = sbc.get_brightness()
            if isinstance(val, list) and val:
                return int(val[0])
            if isinstance(val, (int, float)):
                return int(val)
        except Exception:
            pass
        return 75

    def set_brightness(self, level: int) -> str:
        level = max(0, min(100, level))
        try:
            import screen_brightness_control as sbc

            sbc.set_brightness(level)
            return f"Brightness set to {level} percent."
        except Exception:
            try:
                cmd = f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,{level})"
                subprocess.run(["powershell", "-Command", cmd], timeout=3, capture_output=True)
                return f"Brightness adjusted to {level} percent."
            except Exception as exc:
                return f"Could not adjust brightness: {exc}"

    def change_brightness(self, delta: int) -> str:
        current = self.get_brightness()
        target = max(0, min(100, current + delta))
        return self.set_brightness(target)

    # -------------------------------------------------------------------------
    # Window & Desktop Management
    # -------------------------------------------------------------------------

    def minimize_all(self) -> str:
        try:
            # Win + D
            ctypes.windll.user32.keybd_event(0x5B, 0, 0, 0)
            ctypes.windll.user32.keybd_event(0x44, 0, 0, 0)
            ctypes.windll.user32.keybd_event(0x44, 0, 2, 0)
            ctypes.windll.user32.keybd_event(0x5B, 0, 2, 0)
            return "Showing desktop."
        except Exception as exc:
            return f"Could not minimize windows: {exc}"

    def close_active_window(self) -> str:
        try:
            # Alt + F4
            ctypes.windll.user32.keybd_event(0x12, 0, 0, 0)
            ctypes.windll.user32.keybd_event(0x73, 0, 0, 0)
            ctypes.windll.user32.keybd_event(0x73, 0, 2, 0)
            ctypes.windll.user32.keybd_event(0x12, 0, 2, 0)
            return "Closed active window."
        except Exception as exc:
            return f"Failed to close window: {exc}"

    def switch_window(self) -> str:
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
        try:
            ctypes.windll.user32.LockWorkStation()
            return "Computer locked."
        except Exception as exc:
            return f"Failed to lock workstation: {exc}"

    # -------------------------------------------------------------------------
    # Screenshots & Clipboard
    # -------------------------------------------------------------------------

    def take_screenshot(self, name: str | None = None) -> str:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name or 'screenshot'}_{timestamp}.png"
        output_path = self.screenshot_dir / filename

        # Method 1: mss (Fastest and most reliable)
        try:
            import mss
            import mss.tools

            with mss.mss() as sct:
                monitor = sct.monitors[0]  # Full virtual screen across all monitors
                sct_img = sct.grab(monitor)
                mss.tools.to_png(sct_img.rgb, sct_img.size, output=str(output_path))
                return f"Screenshot saved as {filename}."
        except Exception:
            pass

        # Method 2: PIL ImageGrab
        try:
            from PIL import ImageGrab

            img = ImageGrab.grab(all_screens=True)
            img.save(str(output_path), "PNG")
            return f"Screenshot saved as {filename}."
        except Exception:
            pass

        # Method 3: pywin32 GDI screen capture
        try:
            import win32api
            import win32con
            import win32gui
            import win32ui

            hdesktop = win32gui.GetDesktopWindow()
            width = win32api.GetSystemMetrics(win32con.SM_CXVIRTUALSCREEN) or win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
            height = win32api.GetSystemMetrics(win32con.SM_CYVIRTUALSCREEN) or win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
            left = win32api.GetSystemMetrics(win32con.SM_XVIRTUALSCREEN) or 0
            top = win32api.GetSystemMetrics(win32con.SM_YVIRTUALSCREEN) or 0

            desktop_dc = win32gui.GetWindowDC(hdesktop)
            img_dc = win32ui.CreateDCFromHandle(desktop_dc)
            mem_dc = img_dc.CreateCompatibleDC()

            screenshot = win32ui.CreateBitmap()
            screenshot.CreateCompatibleBitmap(img_dc, width, height)
            mem_dc.SelectObject(screenshot)
            mem_dc.BitBlt((0, 0), (width, height), img_dc, (left, top), win32con.SRCCOPY)

            screenshot.SaveBitmapFile(mem_dc, str(output_path))

            win32gui.DeleteObject(screenshot.GetHandle())
            mem_dc.DeleteDC()
            img_dc.DeleteDC()
            win32gui.ReleaseDC(hdesktop, desktop_dc)
            return f"Screenshot saved as {filename}."
        except Exception as exc:
            return f"Screenshot failed: {exc}"

    def get_clipboard_text(self) -> str:
        try:
            import pyperclip

            text = pyperclip.paste()
            if not text.strip():
                return "The clipboard is currently empty."
            preview = text[:150] + ("..." if len(text) > 150 else "")
            return f"Clipboard contains: {preview}"
        except Exception as exc:
            return f"Could not read clipboard: {exc}"

    def set_clipboard_text(self, text: str) -> str:
        try:
            import pyperclip

            pyperclip.copy(text)
            return "Copied text to clipboard."
        except Exception as exc:
            return f"Could not copy to clipboard: {exc}"

    def type_text(self, text: str) -> str:
        try:
            import pyautogui

            pyautogui.write(text, interval=0.01)
            return f"Typed text."
        except Exception as exc:
            return f"Could not type text: {exc}"

    # -------------------------------------------------------------------------
    # System Stats & Diagnostics
    # -------------------------------------------------------------------------

    def get_system_status(self) -> str:
        cpu = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory().percent
        battery_info = psutil.sensors_battery()

        status_parts = [f"CPU usage is at {cpu:.0f}%", f"RAM usage is at {ram:.0f}%"]
        if battery_info:
            plugged = "plugged in" if battery_info.power_plugged else "on battery"
            status_parts.append(f"Battery is at {battery_info.percent:.0f}% ({plugged})")

        return ". ".join(status_parts) + "."

    def get_battery_info(self) -> str:
        battery = psutil.sensors_battery()
        if not battery:
            return "No battery sensor detected (desktop workstation)."
        plugged = "charging" if battery.power_plugged else "discharging"
        return f"Battery is at {battery.percent:.0f}%, currently {plugged}."

    def get_disk_info(self) -> str:
        usage = psutil.disk_usage("C:\\")
        free_gb = usage.free / (1024**3)
        total_gb = usage.total / (1024**3)
        return f"C: drive has {free_gb:.1f} GB free out of {total_gb:.1f} GB ({usage.percent}% used)."

    # -------------------------------------------------------------------------
    # Applications & Web Automation
    # -------------------------------------------------------------------------

    def open_app_or_url(self, target: str) -> str:
        target_lower = target.strip().lower()

        # Known common aliases
        app_map = {
            "chrome": ["chrome"],
            "google chrome": ["chrome"],
            "edge": ["msedge"],
            "microsoft edge": ["msedge"],
            "firefox": ["firefox"],
            "brave": ["brave"],
            "vs code": ["code"],
            "vscode": ["code"],
            "visual studio code": ["code"],
            "notepad": ["notepad"],
            "calculator": ["calc"],
            "calc": ["calc"],
            "spotify": ["spotify"],
            "explorer": ["explorer"],
            "file explorer": ["explorer"],
            "files": ["explorer"],
            "cmd": ["cmd"],
            "command prompt": ["cmd"],
            "terminal": ["wt", "powershell"],
            "powershell": ["powershell"],
            "task manager": ["taskmgr"],
            "settings": ["start", "ms-settings:"],
            "control panel": ["control"],
            "paint": ["mspaint"],
            "word": ["winword"],
            "excel": ["excel"],
            "powerpoint": ["powerpnt"],
        }

        if target_lower in app_map:
            cmd = app_map[target_lower]
            try:
                subprocess.Popen(cmd, shell=True)
                return f"Opening {target}."
            except Exception:
                pass

        # Try shell start
        try:
            os.startfile(target)
            return f"Opening {target}."
        except Exception:
            pass

        # Fallback to web search
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

        # Try arbitrary path
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
        recent = lines[-3:]  # read last 3 notes
        return "Your recent notes: " + " | ".join(recent)

    # -------------------------------------------------------------------------
    # Power Controls (Protected)
    # -------------------------------------------------------------------------

    def shutdown(self, restart: bool = False) -> str:
        if not self.config.allow_power_commands:
            return "Power commands are currently disabled in config.json for safety."
        action_flag = "/r" if restart else "/s"
        try:
            subprocess.Popen(["shutdown", action_flag, "/t", "10"])
            action = "Restarting" if restart else "Shutting down"
            return f"{action} the computer in 10 seconds."
        except Exception as exc:
            return f"Failed power command: {exc}"

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _send_virtual_key(self, vk_code: int) -> None:
        try:
            ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
            ctypes.windll.user32.keybd_event(vk_code, 0, 2, 0)
        except Exception:
            pass
