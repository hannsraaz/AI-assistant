from __future__ import annotations

import random
from typing import Any

from core.tools.base import ToolResult


class ResponseEngine:
    """Converts structured tool results into concise, natural spoken responses.
    
    Adheres to Friday's personality: calm, intelligent, confident, concise, and slightly witty.
    """

    @staticmethod
    def format_tool_response(tool_name: str, result: ToolResult) -> str:
        if result.needs_confirmation:
            return result.confirmation_prompt or result.message

        if not result.success:
            if result.error:
                return f"I couldn't do that: {result.error}"
            return result.message or "I wasn't able to complete that action."

        data = result.data

        # --- Apps ---
        if tool_name == "apps.open":
            target = data.get("target", "it")
            templates = [f"Opening {target}.", f"Launching {target} now.", f"Done. Opened {target}."]
            return random.choice(templates)

        if tool_name == "apps.close":
            app = data.get("app_name", "the application")
            return f"Closed {app}."

        if tool_name == "apps.focus":
            app = data.get("app_name", "the window")
            return f"Switched to {app}."

        if tool_name == "apps.list":
            count = data.get("count", 0)
            names = data.get("summary_names", [])
            if not names:
                return "You don't have any major applications open right now."
            preview = ", ".join(names[:5])
            if count > 5:
                return f"You have {count} active apps, including {preview}."
            return f"Running apps are {preview}."

        # --- Windows ---
        if tool_name == "windows.list":
            count = data.get("count", 0)
            titles = data.get("titles", [])
            if not titles:
                return "There are no visible windows open."
            preview = ", ".join(f"'{t}'" for t in titles[:4])
            return f"You have {count} open windows, including {preview}."

        if tool_name == "windows.focus":
            title = data.get("title", "window")
            return f"Brought {title} to the front."

        if tool_name == "windows.minimize":
            return "Minimized."

        if tool_name == "windows.maximize":
            return "Maximized."

        if tool_name == "windows.restore":
            return "Restored window."

        if tool_name == "windows.close":
            title = data.get("title", "window")
            return f"Closed {title}."

        if tool_name == "windows.show_desktop":
            return "Desktop is now visible."

        # --- System - Volume ---
        if tool_name == "system.volume.get":
            vol = data.get("volume", 50)
            muted = data.get("muted", False)
            if muted:
                return f"Volume is at {vol} percent, but currently muted."
            return f"The current volume is {vol} percent."

        if tool_name in {"system.volume.set", "system.volume.up", "system.volume.down"}:
            vol = data.get("volume", 50)
            return f"Volume set to {vol} percent."

        if tool_name == "system.volume.mute":
            return "Audio muted."

        if tool_name == "system.volume.unmute":
            return "Audio unmuted."

        # --- System - Brightness ---
        if tool_name in {"system.brightness.set", "system.brightness.get"}:
            bright = data.get("brightness", 75)
            return f"Brightness is at {bright} percent."

        # --- System - Stats ---
        if tool_name == "system.battery":
            if not data.get("has_battery", False):
                return "You're running on AC desktop power, no battery detected."
            percent = data.get("percent", 100)
            charging = data.get("charging", False)
            if charging:
                return f"Battery is at {percent} percent and charging."
            return f"You're at {percent} percent on battery."

        if tool_name == "system.cpu":
            cpu = data.get("cpu_percent", 0)
            return f"CPU usage is currently at {cpu:.0f} percent."

        if tool_name == "system.ram":
            pct = data.get("percent", 0)
            used = data.get("used_gb", 0)
            total = data.get("total_gb", 0)
            return f"RAM is at {pct:.0f} percent, using {used:.1f} of {total:.1f} gigabytes."

        if tool_name == "system.disk":
            free = data.get("free_gb", 0)
            total = data.get("total_gb", 0)
            pct = data.get("percent", 0)
            drive = data.get("drive", "C:")
            return f"{drive} drive has {free:.1f} GB free out of {total:.1f} GB ({pct}% used)."

        if tool_name == "system.network":
            sent = data.get("mb_sent", 0)
            recv = data.get("mb_recv", 0)
            return f"Network is active: {sent:.1f} MB sent and {recv:.1f} MB received."

        # --- Clipboard ---
        if tool_name == "clipboard.read":
            if data.get("empty", False):
                return "Your clipboard is currently empty."
            preview = data.get("preview", "")
            return f"Your clipboard has: {preview}"

        if tool_name == "clipboard.write":
            return "Copied to clipboard."

        if tool_name == "clipboard.clear":
            return "Clipboard cleared."

        # --- Screenshot ---
        if tool_name == "screenshot.take":
            fname = data.get("filename", "screenshot.png")
            return f"Screenshot saved as {fname}."

        # Default fallback to message
        return result.message or "Done."
