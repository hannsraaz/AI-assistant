from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING, Any

from ui.theme import UITheme

if TYPE_CHECKING:
    from assistant_core import VoiceAssistant


class AutomationView(tk.Frame):
    """Automation, Scheduled Timers, Recurring Reminders & Routines View."""

    def __init__(self, parent: tk.Widget, assistant: VoiceAssistant) -> None:
        super().__init__(parent, bg=UITheme.BG_DARK)
        self.assistant = assistant

        self._build_ui()
        self.refresh_jobs()

    def _build_ui(self) -> None:
        header = tk.Frame(self, bg=UITheme.BG_SURFACE, padx=16, pady=8)
        header.pack(fill="x")

        tk.Label(
            header,
            text="AUTOMATION, TIMERS & REMINDERS",
            font=UITheme.FONT_SUBTITLE,
            fg=UITheme.CYAN,
            bg=UITheme.BG_SURFACE,
        ).pack(side="left")

        refresh_btn = tk.Button(
            header,
            text="🔄 Refresh Jobs",
            font=UITheme.FONT_CAPTION_BOLD,
            fg=UITheme.TEXT_SECONDARY,
            bg=UITheme.BG_CARD,
            activebackground=UITheme.BG_CARD_HOVER,
            bd=0,
            padx=8,
            pady=3,
            cursor="hand2",
            command=self.refresh_jobs,
        )
        refresh_btn.pack(side="right")

        content = tk.Frame(self, bg=UITheme.BG_DARK, padx=16, pady=8)
        content.pack(fill="both", expand=True)

        # Active Schedule List
        sched_frame = tk.LabelFrame(
            content,
            text="⏰ Active Scheduled Routines & Timers",
            font=UITheme.FONT_BODY_BOLD,
            fg=UITheme.EMERALD,
            bg=UITheme.BG_CARD,
            padx=10,
            pady=10,
        )
        sched_frame.pack(fill="both", expand=True)

        self.jobs_listbox = tk.Listbox(
            sched_frame,
            bg=UITheme.BG_SURFACE,
            fg=UITheme.TEXT_PRIMARY,
            font=UITheme.FONT_MONO,
            bd=0,
            highlightthickness=1,
            highlightbackground=UITheme.BORDER_MUTED,
            selectbackground=UITheme.BG_CARD_HOVER,
            selectforeground=UITheme.CYAN,
        )
        self.jobs_listbox.pack(fill="both", expand=True, pady=(0, 8))

        btn_bar = tk.Frame(sched_frame, bg=UITheme.BG_CARD)
        btn_bar.pack(fill="x")

        cancel_job_btn = tk.Button(
            btn_bar,
            text="✕ Cancel Selected Routine",
            font=UITheme.FONT_CAPTION_BOLD,
            fg=UITheme.RED,
            bg=UITheme.BG_SURFACE,
            activebackground=UITheme.BG_CARD_HOVER,
            bd=0,
            padx=8,
            pady=4,
            cursor="hand2",
            command=self._cancel_selected_job,
        )
        cancel_job_btn.pack(side="right")

    def refresh_jobs(self) -> None:
        self.jobs_listbox.delete(0, "end")
        if hasattr(self.assistant, "desktop") and hasattr(self.assistant.desktop, "registry"):
            res = self.assistant.desktop.registry.execute("automation.list_jobs")
            jobs = res.data.get("jobs", [])
            if not jobs:
                self.jobs_listbox.insert("end", "  No active automated routines scheduled.")
                return
            for j in jobs:
                jid = j.get("job_id", "")[:8]
                action = j.get("action", "")[:28]
                nxt = j.get("next_run", "Scheduled")
                self.jobs_listbox.insert("end", f"  [{jid}] Next: {nxt} | Action: {action}")
        else:
            self.jobs_listbox.insert("end", "  Automation scheduler standby.")

    def _cancel_selected_job(self) -> None:
        sel = self.jobs_listbox.curselection()
        if not sel:
            return
        line = self.jobs_listbox.get(sel[0])
        if "[" in line and "]" in line:
            jid = line.split("[")[1].split("]")[0]
            if hasattr(self.assistant, "desktop") and hasattr(self.assistant.desktop, "registry"):
                self.assistant.desktop.registry.execute("automation.cancel_job", job_id=jid)
                self.refresh_jobs()
