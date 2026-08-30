from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class UITheme:
    """Futuristic Glassmorphism & Cyberpunk Command Center Color Palette."""

    # Backgrounds
    BG_DARK = "#080b10"
    BG_SURFACE = "#0f141d"
    BG_CARD = "#151c28"
    BG_CARD_HOVER = "#1c2536"
    BG_INPUT = "#1a2232"
    BG_SIDEBAR = "#0a0e16"

    # Borders & Dividers
    BORDER_MUTED = "#222c3c"
    BORDER_ACCENT = "#00d2ff"
    BORDER_GLOW = "#1f6feb"

    # Typography Colors
    TEXT_PRIMARY = "#f0f6fc"
    TEXT_SECONDARY = "#8b949e"
    TEXT_MUTED = "#545d68"
    TEXT_HIGHLIGHT = "#ffffff"

    # Futuristic Accents
    CYAN = "#00d2ff"          # Primary AI Glow
    EMERALD = "#00ffa3"       # Ready / Success / Safe
    RUBY = "#ff0055"          # Listening / Active Wake
    AMBER = "#e3b341"         # Thinking / Warning
    PURPLE = "#bc8cff"        # Executing / Tool Action
    BLUE = "#58a6ff"          # Informational
    RED = "#ff7b72"           # Danger / Error / Cancel

    # Fonts
    FONT_TITLE = ("Segoe UI", 14, "bold")
    FONT_SUBTITLE = ("Segoe UI", 11, "bold")
    FONT_BODY = ("Segoe UI", 10)
    FONT_BODY_BOLD = ("Segoe UI", 10, "bold")
    FONT_CAPTION = ("Segoe UI", 8)
    FONT_CAPTION_BOLD = ("Segoe UI", 8, "bold")
    FONT_MONO = ("Consolas", 9)
    FONT_MONO_BOLD = ("Consolas", 9, "bold")

    # State Colors & Display Names
    STATE_CONFIG = {
        "idle": (EMERALD, "● READY", "#06231a"),
        "listening_for_wake": (EMERALD, "● WAKE STANDBY", "#06231a"),
        "wake_detected": (RUBY, "● WAKE DETECTED", "#381018"),
        "listening_for_command": (RUBY, "● LISTENING", "#381018"),
        "transcribing": (AMBER, "● TRANSCRIBING", "#281e0a"),
        "thinking": (AMBER, "● THINKING", "#281e0a"),
        "executing": (PURPLE, "● EXECUTING", "#221438"),
        "speaking": (CYAN, "● SPEAKING", "#0a2638"),
        "awaiting_confirmation": (AMBER, "⚠ CONFIRMATION NEEDED", "#38240a"),
        "interrupted": (RED, "■ INTERRUPTED", "#381018"),
        "error": (RED, "✕ ERROR", "#381018"),
    }
