from __future__ import annotations

from enum import Enum
import random
from typing import Any

from core.hinglish_normalizer import UserLanguage
from core.resource_manager import global_resource_manager
from core.tools.base import ToolResult


class ResponseClass(str, Enum):
    FAST = "FAST"              # Short acknowledgments (<10 words), volume, mute, app open
    NORMAL = "NORMAL"          # 1-2 sentence standard conversational / informational responses
    CINEMATIC = "CINEMATIC"    # Long explanations, deep project analysis, complex synthesis
    ALERT = "ALERT"            # Critical battery, build failures, errors, permission prompts


class ResponseEngine:
    """Converts structured tool results into concise, natural spoken responses

    with native Hinglish and English language mirroring.
    """

    @classmethod
    def classify_response(cls, text: str, tool_name: str = "", is_error: bool = False) -> ResponseClass:
        """Classify a response into FAST, NORMAL, CINEMATIC, or ALERT."""
        if is_error or "failed" in text.lower() or "error" in text.lower() or "warning" in text.lower():
            return ResponseClass.ALERT

        word_count = len(text.split())
        if word_count > 35:
            return ResponseClass.CINEMATIC

        if tool_name in {
            "system.volume.set", "system.volume.mute", "system.volume.unmute",
            "system.volume.up", "system.volume.down", "system.brightness.set",
            "windows.minimize", "windows.maximize", "windows.restore", "windows.close",
            "windows.show_desktop", "clipboard.clear", "clipboard.write", "apps.close"
        } or word_count <= 4:
            return ResponseClass.FAST

        return ResponseClass.NORMAL

    @classmethod
    def select_tts_backend(cls, response_class: ResponseClass, preferred_neural: str = "xtts") -> str:
        """Select TTS backend (piper vs neural) based on response priority and VRAM availability."""
        if response_class in (ResponseClass.FAST, ResponseClass.NORMAL, ResponseClass.ALERT):
            return "piper"

        if response_class == ResponseClass.CINEMATIC:
            if global_resource_manager.can_allocate_gpu_model(required_vram_mb=2000):
                return preferred_neural
            return "piper"

        return "piper"

    @classmethod
    def get_acknowledgement(cls, action_type: str = "start", language: UserLanguage | str = UserLanguage.ENGLISH) -> str:
        """Get a concise, natural acknowledgement phrase."""
        is_hinglish = str(language).upper() in ("HINGLISH", "HINDI", "HINDI_ROMAN", "HINDI_DEVANAGARI", "USERLANGUAGE.HINGLISH")

        if is_hinglish:
            if action_type == "start":
                return random.choice(["Haan, ek second.", "Sure, dekh raha hoon.", "Ruko, check karta hoon.", "Haan."])
            if action_type == "done":
                return random.choice(["Done.", "Ho gaya.", "Bilkul."])
            if action_type == "interrupted":
                return "Haan?"
        else:
            if action_type == "start":
                return random.choice(["Sure.", "One moment.", "On it.", "Yeah."])
            if action_type == "done":
                return random.choice(["Done.", "All set.", "Got it."])
            if action_type == "interrupted":
                return "Yes?"

        return "Done."

    @classmethod
    def format_tool_response(
        cls,
        tool_name: str,
        result: ToolResult,
        language: UserLanguage | str = UserLanguage.ENGLISH,
    ) -> str:
        is_hinglish = str(language).upper() in ("HINGLISH", "HINDI", "HINDI_ROMAN", "HINDI_DEVANAGARI", "USERLANGUAGE.HINGLISH")

        if result.needs_confirmation:
            return result.confirmation_prompt or result.message

        if not result.success:
            if result.error:
                err_text = result.get_error_message() if hasattr(result, "get_error_message") else str(result.error)
                return f"Ye nahi ho paya: {err_text}" if is_hinglish else f"I couldn't do that: {err_text}"
            return "Ye action complete nahi ho paya." if is_hinglish else (result.message or "I wasn't able to complete that action.")

        data = result.data

        # --- Apps ---
        if tool_name == "apps.open":
            target = data.get("target", "app")
            if is_hinglish:
                return random.choice([f"Haan, {target} khol raha hoon.", f"Ek second, {target} launch kar raha hoon.", f"Done, {target} open ho gaya."])
            return random.choice([f"Opening {target}.", f"Launching {target} now.", f"Done. Opened {target}."])

        if tool_name == "apps.close":
            app = data.get("app_name", "app")
            return f"{app} band kar diya." if is_hinglish else f"Closed {app}."

        if tool_name == "apps.focus":
            app = data.get("app_name", "window")
            return f"{app} pe switch kar diya." if is_hinglish else f"Switched to {app}."

        if tool_name == "apps.list":
            count = data.get("count", 0)
            names = data.get("summary_names", [])
            if not names:
                return "Abhi koi major app open nahi hai." if is_hinglish else "You don't have any major applications open right now."
            preview = ", ".join(names[:5])
            if is_hinglish:
                return f"Abhi {count} apps chal rahe hain, jaise {preview}." if count > 5 else f"Running apps hain: {preview}."
            return f"You have {count} active apps, including {preview}." if count > 5 else f"Running apps are {preview}."

        # --- Windows ---
        if tool_name == "windows.list":
            count = data.get("count", 0)
            titles = data.get("titles", [])
            if not titles:
                return "Koi visible window open nahi hai." if is_hinglish else "There are no visible windows open."
            preview = ", ".join(f"'{t}'" for t in titles[:4])
            return f"{count} windows khuli hain, jaise {preview}." if is_hinglish else f"You have {count} open windows, including {preview}."

        if tool_name == "windows.focus":
            title = data.get("title", "window")
            return f"{title} ko saamne le aaya." if is_hinglish else f"Brought {title} to the front."

        if tool_name == "windows.minimize":
            return "Minimize kar diya." if is_hinglish else "Minimized."

        if tool_name == "windows.maximize":
            return "Maximize kar diya." if is_hinglish else "Maximized."

        if tool_name == "windows.restore":
            return "Window restore kar di." if is_hinglish else "Restored window."

        if tool_name == "windows.close":
            title = data.get("title", "window")
            return f"{title} band kar di." if is_hinglish else f"Closed {title}."

        if tool_name == "windows.show_desktop":
            return "Desktop dikha diya." if is_hinglish else "Desktop is now visible."

        # --- System - Volume ---
        if tool_name == "system.volume.get":
            vol = data.get("volume", 50)
            muted = data.get("muted", False)
            if is_hinglish:
                return f"Volume {vol} percent hai, par abhi muted hai." if muted else f"Current volume {vol} percent hai."
            return f"Volume is at {vol} percent, but currently muted." if muted else f"The current volume is {vol} percent."

        if tool_name in {"system.volume.set", "system.volume.up", "system.volume.down"}:
            vol = data.get("volume", 50)
            return f"Volume {vol} percent kar diya." if is_hinglish else f"Volume set to {vol} percent."

        if tool_name == "system.volume.mute":
            return "Audio mute kar diya." if is_hinglish else "Audio muted."

        if tool_name == "system.volume.unmute":
            return "Audio unmute kar diya." if is_hinglish else "Audio unmuted."

        # --- System - Brightness ---
        if tool_name in {"system.brightness.set", "system.brightness.get"}:
            bright = data.get("brightness", 75)
            return f"Brightness {bright} percent hai." if is_hinglish else f"Brightness is at {bright} percent."

        # --- System - Stats ---
        if tool_name == "system.battery":
            if not data.get("has_battery", False):
                return "AC desktop power pe chal raha hai, koi battery nahi hai." if is_hinglish else "You're running on AC desktop power, no battery detected."
            percent = data.get("percent", 100)
            charging = data.get("charging", False)
            if charging:
                return f"Battery {percent} percent hai aur charging pe laga hai." if is_hinglish else f"Battery is at {percent} percent and charging."
            return f"Battery {percent} percent hai." if is_hinglish else f"Battery is at {percent} percent."

        if tool_name == "system.cpu":
            cpu = data.get("cpu_percent", 0)
            return f"CPU usage around {cpu:.0f} percent hai." if is_hinglish else f"CPU usage is currently at {cpu:.0f} percent."

        if tool_name == "system.ram":
            pct = data.get("percent", 0)
            used = data.get("used_gb", 0)
            total = data.get("total_gb", 0)
            return f"RAM usage {pct:.0f} percent hai ({used:.1f} of {total:.1f} GB)." if is_hinglish else f"RAM is at {pct:.0f} percent, using {used:.1f} of {total:.1f} gigabytes."

        if tool_name == "system.disk":
            free = data.get("free_gb", 0)
            total = data.get("total_gb", 0)
            pct = data.get("percent", 0)
            drive = data.get("drive", "C:")
            return f"{drive} drive mein {free:.1f} GB free hai (total {total:.1f} GB)." if is_hinglish else f"{drive} drive has {free:.1f} GB free out of {total:.1f} GB ({pct}% used)."

        if tool_name == "system.network":
            sent = data.get("mb_sent", 0)
            recv = data.get("mb_recv", 0)
            return f"Network active hai: {sent:.1f} MB sent, {recv:.1f} MB received." if is_hinglish else f"Network is active: {sent:.1f} MB sent and {recv:.1f} MB received."

        # --- Clipboard ---
        if tool_name == "clipboard.read":
            if data.get("empty", False):
                return "Clipboard abhi empty hai." if is_hinglish else "Your clipboard is currently empty."
            preview = data.get("preview", "")
            return f"Clipboard mein hai: {preview}" if is_hinglish else f"Your clipboard has: {preview}"

        if tool_name == "clipboard.write":
            return "Clipboard pe copy kar diya." if is_hinglish else "Copied to clipboard."

        if tool_name == "clipboard.clear":
            return "Clipboard clear kar diya." if is_hinglish else "Clipboard cleared."

        # --- Screenshot ---
        if tool_name == "screenshot.take":
            fname = data.get("filename", "screenshot.png")
            return f"Done, screenshot save ho gaya ({fname})." if is_hinglish else f"Screenshot saved as {fname}."

        # Default fallback
        return ("Ho gaya." if is_hinglish else "Done.") if not result.message else result.message
