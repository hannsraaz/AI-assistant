from __future__ import annotations

import threading
import tkinter as tk
from typing import TYPE_CHECKING, Any

from ui.theme import UITheme

if TYPE_CHECKING:
    from assistant_core import VoiceAssistant


class DeveloperView(tk.Frame):
    """Developer Command Center: Git Status, Android ADB, and Terminal Runner."""

    def __init__(self, parent: tk.Widget, assistant: VoiceAssistant) -> None:
        super().__init__(parent, bg=UITheme.BG_DARK)
        self.assistant = assistant

        self._build_ui()
        self.refresh_git()

    def _build_ui(self) -> None:
        header = tk.Frame(self, bg=UITheme.BG_SURFACE, padx=16, pady=8)
        header.pack(fill="x")

        tk.Label(
            header,
            text="DEVELOPER COMMAND HUB (GIT / ANDROID / TERMINAL)",
            font=UITheme.FONT_SUBTITLE,
            fg=UITheme.CYAN,
            bg=UITheme.BG_SURFACE,
        ).pack(side="left")

        refresh_btn = tk.Button(
            header,
            text="🔄 Refresh Git & ADB",
            font=UITheme.FONT_CAPTION_BOLD,
            fg=UITheme.TEXT_SECONDARY,
            bg=UITheme.BG_CARD,
            activebackground=UITheme.BG_CARD_HOVER,
            bd=0,
            padx=8,
            pady=3,
            cursor="hand2",
            command=self.refresh_git,
        )
        refresh_btn.pack(side="right")

        content = tk.Frame(self, bg=UITheme.BG_DARK, padx=16, pady=8)
        content.pack(fill="both", expand=True)

        # 1. Git Status Card
        git_card = tk.LabelFrame(
            content,
            text="🌿 Git Version Control Status",
            font=UITheme.FONT_BODY_BOLD,
            fg=UITheme.EMERALD,
            bg=UITheme.BG_CARD,
            padx=10,
            pady=10,
        )
        git_card.pack(fill="x", pady=(0, 8))

        self.git_info_lbl = tk.Label(
            git_card,
            text="Git Status: Polling repository...",
            font=UITheme.FONT_MONO,
            fg=UITheme.TEXT_PRIMARY,
            bg=UITheme.BG_SURFACE,
            padx=8,
            pady=6,
            anchor="w",
            justify="left",
        )
        self.git_info_lbl.pack(fill="x")

        # 2. Terminal Quick Execution Card
        term_card = tk.LabelFrame(
            content,
            text="💻 Developer Terminal Quick Runner",
            font=UITheme.FONT_BODY_BOLD,
            fg=UITheme.PURPLE,
            bg=UITheme.BG_CARD,
            padx=10,
            pady=10,
        )
        term_card.pack(fill="both", expand=True)

        input_bar = tk.Frame(term_card, bg=UITheme.BG_CARD)
        input_bar.pack(fill="x", pady=(0, 6))

        self.term_entry = tk.Entry(
            input_bar,
            font=UITheme.FONT_MONO,
            fg=UITheme.TEXT_PRIMARY,
            bg=UITheme.BG_INPUT,
            bd=0,
            insertbackground=UITheme.CYAN,
        )
        self.term_entry.pack(side="left", fill="x", expand=True, ipady=3, padx=(0, 6))
        self.term_entry.insert(0, "git status")
        self.term_entry.bind("<Return>", lambda _: self._run_terminal_cmd())

        run_btn = tk.Button(
            input_bar,
            text="▶ Run",
            font=UITheme.FONT_CAPTION_BOLD,
            fg=UITheme.BG_DARK,
            bg=UITheme.CYAN,
            activebackground=UITheme.TEXT_HIGHLIGHT,
            bd=0,
            padx=10,
            pady=3,
            cursor="hand2",
            command=self._run_terminal_cmd,
        )
        run_btn.pack(side="right")

        self.term_output = tk.Text(
            term_card,
            bg=UITheme.BG_SURFACE,
            fg=UITheme.TEXT_PRIMARY,
            font=UITheme.FONT_MONO,
            bd=0,
            wrap="word",
            padx=8,
            pady=8,
        )
        self.term_output.pack(fill="both", expand=True)
        self.term_output.insert("end", "[TERMINAL READY] Type command and press Enter.\n")
        self.term_output.config(state="disabled")

    def refresh_git(self) -> None:
        def _worker() -> None:
            if hasattr(self.assistant, "desktop") and hasattr(self.assistant.desktop, "registry"):
                res = self.assistant.desktop.registry.execute("git.status")
                msg = res.message or "Clean working tree."
                branch = res.data.get("branch", "main")
                changes = res.data.get("changes_count", 0)
                status_txt = f"Branch: {branch} | Modified/Untracked Files: {changes}\nStatus: {msg}"
                try:
                    if self.winfo_exists():
                        self.after(0, lambda: self.git_info_lbl.config(text=status_txt))
                except Exception:
                    pass

        threading.Thread(target=_worker, daemon=True).start()

    def _run_terminal_cmd(self) -> None:
        cmd = self.term_entry.get().strip()
        if not cmd:
            return

        self.term_output.config(state="normal")
        self.term_output.insert("end", f"\n> {cmd}\n")
        self.term_output.config(state="disabled")
        self.term_output.see("end")

        def _worker() -> None:
            if hasattr(self.assistant, "desktop") and hasattr(self.assistant.desktop, "registry"):
                res = self.assistant.desktop.registry.execute("developer.terminal_exec", command=cmd)
                out = res.data.get("stdout", "") or res.message or res.error or "Executed."

                def _update() -> None:
                    self.term_output.config(state="normal")
                    self.term_output.insert("end", f"{out}\n")
                    self.term_output.config(state="disabled")
                    self.term_output.see("end")

                self.after(0, _update)

        threading.Thread(target=_worker, daemon=True).start()
