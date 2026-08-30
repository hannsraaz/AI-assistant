from __future__ import annotations

import threading
import tkinter as tk
from typing import TYPE_CHECKING, Any

from ui.theme import UITheme

if TYPE_CHECKING:
    from assistant_core import VoiceAssistant


class VisionView(tk.Frame):
    """Futuristic Screen Vision, OCR & Visual Coordinate Inspection View."""

    def __init__(self, parent: tk.Widget, assistant: VoiceAssistant) -> None:
        super().__init__(parent, bg=UITheme.BG_DARK)
        self.assistant = assistant

        self._build_ui()

    def _build_ui(self) -> None:
        header = tk.Frame(self, bg=UITheme.BG_SURFACE, padx=16, pady=8)
        header.pack(fill="x")

        tk.Label(
            header,
            text="SCREEN VISION & UI ELEMENT INSPECTOR",
            font=UITheme.FONT_SUBTITLE,
            fg=UITheme.CYAN,
            bg=UITheme.BG_SURFACE,
        ).pack(side="left")

        snap_btn = tk.Button(
            header,
            text="📷 Capture & Analyze Screen",
            font=UITheme.FONT_CAPTION_BOLD,
            fg=UITheme.BG_DARK,
            bg=UITheme.CYAN,
            activebackground=UITheme.TEXT_HIGHLIGHT,
            bd=0,
            padx=10,
            pady=3,
            cursor="hand2",
            command=self._capture_and_analyze,
        )
        snap_btn.pack(side="right")

        content = tk.Frame(self, bg=UITheme.BG_DARK, padx=16, pady=8)
        content.pack(fill="both", expand=True)

        # Vision Output Log
        log_frame = tk.LabelFrame(
            content,
            text="👁️ Vision & Element Detection Log",
            font=UITheme.FONT_BODY_BOLD,
            fg=UITheme.PURPLE,
            bg=UITheme.BG_CARD,
            padx=10,
            pady=10,
        )
        log_frame.pack(fill="both", expand=True)

        self.vision_text = tk.Text(
            log_frame,
            bg=UITheme.BG_SURFACE,
            fg=UITheme.TEXT_PRIMARY,
            font=UITheme.FONT_MONO,
            bd=0,
            wrap="word",
            padx=8,
            pady=8,
        )
        self.vision_text.pack(fill="both", expand=True)
        self.vision_text.insert("end", "[VISION STANDBY] Click 'Capture & Analyze Screen' or say 'Describe what is on my screen'.\n")
        self.vision_text.config(state="disabled")

    def _capture_and_analyze(self) -> None:
        self.vision_text.config(state="normal")
        self.vision_text.insert("end", "\n[VISION] Capturing primary desktop screen...\n")
        self.vision_text.config(state="disabled")
        self.vision_text.see("end")

        def _worker() -> None:
            if hasattr(self.assistant, "desktop") and hasattr(self.assistant.desktop, "registry"):
                res = self.assistant.desktop.registry.execute("vision.describe_screen")
                msg = res.message or (res.data.get("description", "Screen captured successfully."))

                def _update() -> None:
                    self.vision_text.config(state="normal")
                    self.vision_text.insert("end", f"[ANALYSIS RESULT]\n{msg}\n\n")
                    self.vision_text.config(state="disabled")
                    self.vision_text.see("end")

                try:
                    if self.winfo_exists():
                        self.after(0, _update)
                except Exception:
                    pass

        threading.Thread(target=_worker, daemon=True).start()
