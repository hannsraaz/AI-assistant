from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING, Any

from ui.core_canvas import FridayCoreCanvas
from ui.theme import UITheme

if TYPE_CHECKING:
    from assistant_core import VoiceAssistant


class HomeView(tk.Frame):
    """Command Center Home Screen with Central Energy Core, Status Cards, and Quick Controls."""

    def __init__(self, parent: tk.Widget, assistant: VoiceAssistant, on_navigate: Any = None) -> None:
        super().__init__(parent, bg=UITheme.BG_DARK)
        self.assistant = assistant
        self.on_navigate = on_navigate

        self._build_ui()

    def _build_ui(self) -> None:
        # 1. Central Orb & Interactive Energy Core
        core_container = tk.Frame(self, bg=UITheme.BG_DARK, pady=4)
        core_container.pack(fill="x")

        self.core = FridayCoreCanvas(
            core_container,
            size=150,
            on_click=self._on_core_click,
        )
        self.core.pack(pady=2)

        # 2. Main State & Spoken Prompt Label
        self.status_title_lbl = tk.Label(
            self,
            text="FRIDAY READY",
            font=UITheme.FONT_SUBTITLE,
            fg=UITheme.EMERALD,
            bg=UITheme.BG_DARK,
        )
        self.status_title_lbl.pack(pady=(0, 2))

        self.status_sub_lbl = tk.Label(
            self,
            text=f"Say '{self.assistant.config.wake_word_phrase}' or click the core",
            font=UITheme.FONT_CAPTION,
            fg=UITheme.TEXT_SECONDARY,
            bg=UITheme.BG_DARK,
            wraplength=480,
        )
        self.status_sub_lbl.pack(pady=(0, 6))

        # 3. Active Task Card (if task is in progress)
        self.task_card = tk.Frame(self, bg=UITheme.BG_CARD, padx=12, pady=8, highlightthickness=1, highlightbackground=UITheme.BORDER_MUTED)
        self.task_card.pack(fill="x", padx=16, pady=4)

        task_header = tk.Frame(self.task_card, bg=UITheme.BG_CARD)
        task_header.pack(fill="x")

        self.task_name_lbl = tk.Label(
            task_header,
            text="CURRENT TASK: Standby",
            font=UITheme.FONT_BODY_BOLD,
            fg=UITheme.CYAN,
            bg=UITheme.BG_CARD,
            anchor="w",
        )
        self.task_name_lbl.pack(side="left")

        self.task_step_count_lbl = tk.Label(
            task_header,
            text="0/0 Steps",
            font=UITheme.FONT_CAPTION_BOLD,
            fg=UITheme.TEXT_MUTED,
            bg=UITheme.BG_CARD,
        )
        self.task_step_count_lbl.pack(side="right")

        self.progress_bar = ttk.Progressbar(self.task_card, mode="determinate", maximum=100, value=0)
        self.progress_bar.pack(fill="x", pady=4)

        self.task_detail_lbl = tk.Label(
            self.task_card,
            text="System is idle. Ready for voice or text instruction.",
            font=UITheme.FONT_CAPTION,
            fg=UITheme.TEXT_SECONDARY,
            bg=UITheme.BG_CARD,
            anchor="w",
        )
        self.task_detail_lbl.pack(fill="x")

        # 4. Recent Command / Response Preview Card
        history_card = tk.Frame(self, bg=UITheme.BG_CARD, padx=12, pady=8, highlightthickness=1, highlightbackground=UITheme.BORDER_MUTED)
        history_card.pack(fill="both", expand=True, padx=16, pady=4)

        self.user_bubble_lbl = tk.Label(
            history_card,
            text="YOU: ...",
            font=UITheme.FONT_BODY_BOLD,
            fg=UITheme.CYAN,
            bg=UITheme.BG_CARD,
            anchor="w",
            wraplength=460,
        )
        self.user_bubble_lbl.pack(fill="x", pady=(0, 2))

        self.friday_bubble_box = tk.Text(
            history_card,
            font=UITheme.FONT_BODY,
            fg=UITheme.TEXT_PRIMARY,
            bg=UITheme.BG_CARD,
            bd=0,
            wrap="word",
            height=3,
            highlightthickness=0,
        )
        self.friday_bubble_box.pack(fill="both", expand=True)
        self.friday_bubble_box.insert("1.0", "FRIDAY is standing by.")
        self.friday_bubble_box.config(state="disabled")

        # 5. Quick Command Shortcuts Bar
        quick_bar = tk.Frame(self, bg=UITheme.BG_DARK, pady=4)
        quick_bar.pack(fill="x", padx=16)

        shortcuts = [
            ("🎙️ Speak", lambda: self.assistant.capture_voice_once(), UITheme.CYAN),
            ("📷 Vision", lambda: self.assistant.submit_text("describe what is on my screen"), UITheme.PURPLE),
            ("⚡ Status", lambda: self.assistant.submit_text("system status"), UITheme.EMERALD),
            ("⏹ Stop", lambda: self.assistant.cancel(), UITheme.RED),
        ]

        for label, cmd, color in shortcuts:
            btn = tk.Button(
                quick_bar,
                text=label,
                font=UITheme.FONT_CAPTION_BOLD,
                fg=UITheme.TEXT_HIGHLIGHT if color == UITheme.RED else UITheme.BG_DARK,
                bg=color,
                activebackground=UITheme.TEXT_HIGHLIGHT,
                bd=0,
                padx=10,
                pady=4,
                cursor="hand2",
                command=cmd,
            )
            btn.pack(side="left", padx=2, expand=True, fill="x")

    def _on_core_click(self) -> None:
        if self.core.state == "speaking":
            self.assistant.cancel()
        else:
            self.assistant.capture_voice_once()

    def set_state(self, state: str, status_msg: str = "") -> None:
        self.core.set_state(state)
        fg_color, label, _ = UITheme.STATE_CONFIG.get(state, (UITheme.CYAN, state.upper(), ""))
        self.status_title_lbl.config(text=label, fg=fg_color)
        if status_msg:
            self.status_sub_lbl.config(text=status_msg)

    def set_transcript(self, text: str) -> None:
        self.user_bubble_lbl.config(text=f"YOU: {text}")

    def set_response(self, text: str) -> None:
        self.friday_bubble_box.config(state="normal")
        self.friday_bubble_box.delete("1.0", "end")
        self.friday_bubble_box.insert("1.0", text)
        self.friday_bubble_box.config(state="disabled")
        self.friday_bubble_box.see("end")

    def update_task_progress(self, title: str, step_msg: str, current_step: int, total_steps: int, pct: int) -> None:
        self.task_name_lbl.config(text=f"TASK: {title}")
        self.task_step_count_lbl.config(text=f"{current_step}/{total_steps} Steps")
        self.progress_bar["value"] = pct
        self.task_detail_lbl.config(text=step_msg)
