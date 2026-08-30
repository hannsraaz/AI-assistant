from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING, Any

from config import AppConfig
from ui.theme import UITheme

if TYPE_CHECKING:
    from assistant_core import VoiceAssistant


class SettingsView(tk.Frame):
    """Configuration & Assistant Settings Management View."""

    def __init__(self, parent: tk.Widget, assistant: VoiceAssistant) -> None:
        super().__init__(parent, bg=UITheme.BG_DARK)
        self.assistant = assistant
        self.app_config: AppConfig = assistant.config

        self._build_ui()

    def _build_ui(self) -> None:
        header = tk.Frame(self, bg=UITheme.BG_SURFACE, padx=16, pady=8)
        header.pack(fill="x")

        tk.Label(
            header,
            text="SETTINGS & SYSTEM PREFERENCES",
            font=UITheme.FONT_SUBTITLE,
            fg=UITheme.CYAN,
            bg=UITheme.BG_SURFACE,
        ).pack(side="left")

        save_btn = tk.Button(
            header,
            text="💾 Save Preferences",
            font=UITheme.FONT_CAPTION_BOLD,
            fg=UITheme.BG_DARK,
            bg=UITheme.EMERALD,
            activebackground=UITheme.TEXT_HIGHLIGHT,
            bd=0,
            padx=10,
            pady=3,
            cursor="hand2",
            command=self._save_settings,
        )
        save_btn.pack(side="right")

        content = tk.Frame(self, bg=UITheme.BG_DARK, padx=16, pady=8)
        content.pack(fill="both", expand=True)

        # Settings Card
        form = tk.LabelFrame(
            content,
            text="⚙️ Engine & Voice Pipeline Parameters",
            font=UITheme.FONT_BODY_BOLD,
            fg=UITheme.PURPLE,
            bg=UITheme.BG_CARD,
            padx=12,
            pady=12,
        )
        form.pack(fill="both", expand=True)

        self.wake_entry = self._add_field(form, "Wake-Word Trigger Phrase:", getattr(self.app_config, "wake_word_phrase", "hey jarvis"))
        self.stt_entry = self._add_field(form, "Speech-to-Text Model:", getattr(self.app_config.stt, "model_size", "small"))
        self.tts_entry = self._add_field(form, "Text-to-Speech Backend:", getattr(self.app_config.tts, "backend", "piper"))
        self.llm_entry = self._add_field(form, "Ollama LLM Model:", getattr(self.app_config.llm, "model", "llama3.2:3b"))

        # Checkboxes
        self.cont_var = tk.BooleanVar(value=getattr(self.app_config.wake_word, "continuous_conversation", True))
        c1 = tk.Checkbutton(
            form,
            text="Enable Continuous Multi-Turn Voice Follow-Up",
            variable=self.cont_var,
            font=UITheme.FONT_BODY,
            fg=UITheme.TEXT_PRIMARY,
            bg=UITheme.BG_CARD,
            selectcolor=UITheme.BG_SURFACE,
            activebackground=UITheme.BG_CARD,
            activeforeground=UITheme.CYAN,
        )
        c1.pack(anchor="w", pady=4)

        self.top_var = tk.BooleanVar(value=getattr(self.app_config.ui, "always_on_top", True))
        c2 = tk.Checkbutton(
            form,
            text="Keep HUD Always on Top of Other Windows",
            variable=self.top_var,
            font=UITheme.FONT_BODY,
            fg=UITheme.TEXT_PRIMARY,
            bg=UITheme.BG_CARD,
            selectcolor=UITheme.BG_SURFACE,
            activebackground=UITheme.BG_CARD,
            activeforeground=UITheme.CYAN,
        )
        c2.pack(anchor="w", pady=4)

        self.status_lbl = tk.Label(
            form,
            text="Settings loaded from config.py",
            font=UITheme.FONT_CAPTION,
            fg=UITheme.TEXT_SECONDARY,
            bg=UITheme.BG_CARD,
        )
        self.status_lbl.pack(anchor="w", pady=(12, 0))

    def _add_field(self, parent: tk.Widget, label_txt: str, init_val: str) -> tk.Entry:
        frame = tk.Frame(parent, bg=UITheme.BG_CARD, pady=4)
        frame.pack(fill="x")

        tk.Label(frame, text=label_txt, font=UITheme.FONT_BODY, fg=UITheme.TEXT_PRIMARY, bg=UITheme.BG_CARD, width=26, anchor="w").pack(side="left")
        entry = tk.Entry(frame, font=UITheme.FONT_BODY, fg=UITheme.TEXT_PRIMARY, bg=UITheme.BG_INPUT, bd=0, insertbackground=UITheme.CYAN)
        entry.pack(side="right", fill="x", expand=True, ipady=3)
        entry.insert(0, str(init_val) if not isinstance(init_val, str) else init_val)
        return entry

    def _save_settings(self) -> None:
        self.app_config.wake_word_phrase = self.wake_entry.get().strip()
        self.app_config.stt.model_size = self.stt_entry.get().strip()
        self.app_config.tts.backend = self.tts_entry.get().strip()
        self.app_config.llm.model = self.llm_entry.get().strip()
        self.app_config.wake_word.continuous_conversation = self.cont_var.get()
        self.app_config.ui.always_on_top = self.top_var.get()

        self.status_lbl.config(text="✓ Preferences updated for current session.", fg=UITheme.EMERALD)
