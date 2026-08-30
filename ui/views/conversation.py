from __future__ import annotations

import datetime
import tkinter as tk
from typing import TYPE_CHECKING, Any

from ui.theme import UITheme

if TYPE_CHECKING:
    from assistant_core import VoiceAssistant


class ConversationView(tk.Frame):
    """Futuristic scrollable conversation & streaming dialogue history panel."""

    def __init__(self, parent: tk.Widget, assistant: VoiceAssistant) -> None:
        super().__init__(parent, bg=UITheme.BG_DARK)
        self.assistant = assistant

        self._build_ui()

    def _build_ui(self) -> None:
        # Header Controls
        header = tk.Frame(self, bg=UITheme.BG_SURFACE, padx=16, pady=8)
        header.pack(fill="x")

        tk.Label(
            header,
            text="CONVERSATION LOG",
            font=UITheme.FONT_SUBTITLE,
            fg=UITheme.CYAN,
            bg=UITheme.BG_SURFACE,
        ).pack(side="left")

        clear_btn = tk.Button(
            header,
            text="🗑 Clear History",
            font=UITheme.FONT_CAPTION_BOLD,
            fg=UITheme.TEXT_SECONDARY,
            bg=UITheme.BG_CARD,
            activebackground=UITheme.BG_CARD_HOVER,
            bd=0,
            padx=8,
            pady=3,
            cursor="hand2",
            command=self._clear_history,
        )
        clear_btn.pack(side="right")

        # Scrollable Text Container
        container = tk.Frame(self, bg=UITheme.BG_DARK, padx=16, pady=8)
        container.pack(fill="both", expand=True)

        self.scrollbar = tk.Scrollbar(container)
        self.scrollbar.pack(side="right", fill="y")

        self.text_area = tk.Text(
            container,
            bg=UITheme.BG_SURFACE,
            fg=UITheme.TEXT_PRIMARY,
            font=UITheme.FONT_BODY,
            bd=0,
            padx=12,
            pady=12,
            wrap="word",
            yscrollcommand=self.scrollbar.set,
            highlightthickness=1,
            highlightbackground=UITheme.BORDER_MUTED,
        )
        self.text_area.pack(side="left", fill="both", expand=True)
        self.scrollbar.config(command=self.text_area.yview)

        # Configure color tags
        self.text_area.tag_config("user_tag", foreground=UITheme.CYAN, font=UITheme.FONT_BODY_BOLD)
        self.text_area.tag_config("friday_tag", foreground=UITheme.EMERALD, font=UITheme.FONT_BODY_BOLD)
        self.text_area.tag_config("time_tag", foreground=UITheme.TEXT_MUTED, font=UITheme.FONT_CAPTION)
        self.text_area.tag_config("content_tag", foreground=UITheme.TEXT_PRIMARY, font=UITheme.FONT_BODY)
        self.text_area.tag_config("system_tag", foreground=UITheme.AMBER, font=UITheme.FONT_CAPTION)

        self.text_area.insert("end", "[SYSTEM] Session initialized. Friday is ready.\n\n", "system_tag")
        self.text_area.config(state="disabled")

    def append_user_message(self, text: str) -> None:
        now = datetime.datetime.now().strftime("%H:%M:%S")
        self.text_area.config(state="normal")
        self.text_area.insert("end", f"[{now}] ", "time_tag")
        self.text_area.insert("end", "YOU: ", "user_tag")
        self.text_area.insert("end", f"{text}\n", "content_tag")
        self.text_area.see("end")
        self.text_area.config(state="disabled")

    def append_friday_message(self, text: str) -> None:
        now = datetime.datetime.now().strftime("%H:%M:%S")
        self.text_area.config(state="normal")
        self.text_area.insert("end", f"[{now}] ", "time_tag")
        self.text_area.insert("end", "FRIDAY: ", "friday_tag")
        self.text_area.insert("end", f"{text}\n\n", "content_tag")
        self.text_area.see("end")
        self.text_area.config(state="disabled")

    def _clear_history(self) -> None:
        self.text_area.config(state="normal")
        self.text_area.delete("1.0", "end")
        self.text_area.insert("end", "[SYSTEM] History cleared.\n\n", "system_tag")
        self.text_area.config(state="disabled")
