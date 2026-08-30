from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING, Any

from ui.theme import UITheme

if TYPE_CHECKING:
    from assistant_core import VoiceAssistant


class TasksView(tk.Frame):
    """Live Planner, Multi-Step Execution & Background Task Management View."""

    def __init__(self, parent: tk.Widget, assistant: VoiceAssistant) -> None:
        super().__init__(parent, bg=UITheme.BG_DARK)
        self.assistant = assistant

        self._build_ui()

    def _build_ui(self) -> None:
        # 1. Header
        header = tk.Frame(self, bg=UITheme.BG_SURFACE, padx=16, pady=8)
        header.pack(fill="x")

        tk.Label(
            header,
            text="AUTONOMOUS TASK MANAGER & PLANNER",
            font=UITheme.FONT_SUBTITLE,
            fg=UITheme.CYAN,
            bg=UITheme.BG_SURFACE,
        ).pack(side="left")

        refresh_btn = tk.Button(
            header,
            text="🔄 Refresh",
            font=UITheme.FONT_CAPTION_BOLD,
            fg=UITheme.TEXT_SECONDARY,
            bg=UITheme.BG_CARD,
            activebackground=UITheme.BG_CARD_HOVER,
            bd=0,
            padx=8,
            pady=3,
            cursor="hand2",
            command=self.refresh_tasks,
        )
        refresh_btn.pack(side="right")

        # Main Split Container
        main_frame = tk.Frame(self, bg=UITheme.BG_DARK, padx=16, pady=8)
        main_frame.pack(fill="both", expand=True)

        # Left Column: Active Multi-Step Plan Breakdown
        left_col = tk.LabelFrame(
            main_frame,
            text="⚡ Current Plan & Live Execution Steps",
            font=UITheme.FONT_BODY_BOLD,
            fg=UITheme.CYAN,
            bg=UITheme.BG_CARD,
            padx=10,
            pady=10,
        )
        left_col.pack(side="left", fill="both", expand=True, padx=(0, 8))

        self.plan_title_lbl = tk.Label(
            left_col,
            text="No active multi-step task running.",
            font=UITheme.FONT_BODY_BOLD,
            fg=UITheme.TEXT_PRIMARY,
            bg=UITheme.BG_CARD,
            anchor="w",
        )
        self.plan_title_lbl.pack(fill="x", pady=(0, 4))

        self.plan_progress = ttk.Progressbar(left_col, mode="determinate", maximum=100, value=0)
        self.plan_progress.pack(fill="x", pady=(0, 8))

        # Steps Treeview / List
        self.steps_listbox = tk.Listbox(
            left_col,
            bg=UITheme.BG_SURFACE,
            fg=UITheme.TEXT_PRIMARY,
            font=UITheme.FONT_MONO,
            bd=0,
            highlightthickness=1,
            highlightbackground=UITheme.BORDER_MUTED,
            selectbackground=UITheme.BG_CARD_HOVER,
        )
        self.steps_listbox.pack(fill="both", expand=True)
        self.steps_listbox.insert("end", "  ○ Standby: Waiting for plan...")

        # Right Column: Background Task Queue
        right_col = tk.LabelFrame(
            main_frame,
            text="📋 Background Task Queue",
            font=UITheme.FONT_BODY_BOLD,
            fg=UITheme.PURPLE,
            bg=UITheme.BG_CARD,
            padx=10,
            pady=10,
        )
        right_col.pack(side="right", fill="both", expand=True, padx=(8, 0))

        self.tasks_listbox = tk.Listbox(
            right_col,
            bg=UITheme.BG_SURFACE,
            fg=UITheme.TEXT_PRIMARY,
            font=UITheme.FONT_MONO,
            bd=0,
            highlightthickness=1,
            highlightbackground=UITheme.BORDER_MUTED,
            selectbackground=UITheme.BG_CARD_HOVER,
        )
        self.tasks_listbox.pack(fill="both", expand=True, pady=(0, 8))

        task_btn_bar = tk.Frame(right_col, bg=UITheme.BG_CARD)
        task_btn_bar.pack(fill="x")

        cancel_task_btn = tk.Button(
            task_btn_bar,
            text="✕ Cancel Task",
            font=UITheme.FONT_CAPTION_BOLD,
            fg=UITheme.RED,
            bg=UITheme.BG_SURFACE,
            activebackground=UITheme.BG_CARD_HOVER,
            bd=0,
            padx=8,
            pady=4,
            cursor="hand2",
            command=self._cancel_selected_task,
        )
        cancel_task_btn.pack(side="right")

    def update_live_plan(self, task: Any, event_name: str, message: str) -> None:
        self.plan_title_lbl.config(text=f"ACTIVE: {task.title}")
        total = len(task.steps) or 1
        cur = task.current_step or (total if event_name == "TASK_COMPLETED" else 0)
        pct = int((cur / total) * 100) if total else 0
        self.plan_progress["value"] = pct

        self.steps_listbox.delete(0, "end")
        for i, step in enumerate(task.steps):
            if i < cur:
                icon = "✓"
                status_txt = "DONE"
            elif i == cur:
                icon = "●"
                status_txt = "RUNNING" if event_name != "TASK_FAILED" else "FAILED"
            else:
                icon = "○"
                status_txt = "PENDING"
            self.steps_listbox.insert("end", f"  {icon} [{status_txt:7}] Step {i+1}: {step.description[:38]}")

        self.refresh_tasks()

    def refresh_tasks(self) -> None:
        if not getattr(self.assistant, "task_manager", None):
            return
        tasks = self.assistant.task_manager.list_tasks()
        self.tasks_listbox.delete(0, "end")
        if not tasks:
            self.tasks_listbox.insert("end", "  No background tasks in queue.")
            return

        for t in tasks:
            status_val = t.status.value if hasattr(t.status, "value") else str(t.status)
            self.tasks_listbox.insert("end", f"  [{status_val.upper():9}] {t.task_id[:6]} - {t.title[:24]}")

    def _cancel_selected_task(self) -> None:
        sel = self.tasks_listbox.curselection()
        if not sel:
            return
        tasks = self.assistant.task_manager.list_tasks()
        idx = sel[0]
        if idx < len(tasks):
            t = tasks[idx]
            self.assistant.task_manager.cancel_task(t.task_id)
            self.refresh_tasks()
