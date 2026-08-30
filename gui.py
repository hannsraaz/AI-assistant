from __future__ import annotations

import math
import threading
import time
import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING, Any

from core.event_bus import Event, global_event_bus
from core.telemetry import global_telemetry
from ui.components.confirmation_dialog import ConfirmationDialog
from ui.theme import UITheme
from ui.views.automation import AutomationView
from ui.views.conversation import ConversationView
from ui.views.developer import DeveloperView
from ui.views.home import HomeView
from ui.views.memory import MemoryView
from ui.views.settings import SettingsView
from ui.views.system_hud import SystemHudView
from ui.views.tasks import TasksView
from ui.views.tools import ToolsView
from ui.views.vision import VisionView

if TYPE_CHECKING:
    from assistant_core import VoiceAssistant
    from config import AppConfig


class AssistantWindow:
    """Futuristic Personal AI Command Center, HUD & Autonomous Desktop OS for FRIDAY V4."""

    def __init__(self, assistant: VoiceAssistant, config: AppConfig) -> None:
        self.assistant = assistant
        self.config = config

        self.root = tk.Tk()
        self.root.title(f"{config.name} V4 — Futuristic AI Command Center")
        self.root.geometry("680x760")
        self.root.minsize(580, 640)
        self.root.configure(bg=UITheme.BG_DARK)

        if getattr(config.ui, "always_on_top", True):
            self.root.attributes("-topmost", True)

        self._state = "idle"
        self._after_id: str | None = None
        self._is_compact = False
        self._saved_geometry = "680x760"

        # Initialize Views Container
        self.views: dict[str, tk.Frame] = {}
        self.current_view_name = "home"

        # Wire task events and Event Bus
        self.assistant.task_manager.on_task_event = self._on_task_event
        self._subscribe_event_bus()

        self._build_ui()
        self._start_animation_loop()
        self._start_metrics_worker()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _subscribe_event_bus(self) -> None:
        def _on_bus_event(evt: Event) -> None:
            if evt.topic == "assistant.state_change":
                state = evt.payload.get("state", "idle")
                status = evt.payload.get("status", "")
                self.set_state(state, status)
            elif evt.topic == "stt.transcript":
                self.set_transcript(evt.payload.get("transcript", ""))
            elif evt.topic == "assistant.response":
                self.set_response(evt.payload.get("response", ""))

        global_event_bus.subscribe("*", _on_bus_event)

    def _build_ui(self) -> None:
        # 1. Top Title & Quick Telemetry HUD Bar
        self.top_bar = tk.Frame(self.root, bg=UITheme.BG_SURFACE, padx=14, pady=6)
        self.top_bar.pack(fill="x")

        # Brand / Title
        brand_frame = tk.Frame(self.top_bar, bg=UITheme.BG_SURFACE)
        brand_frame.pack(side="left")

        tk.Label(
            brand_frame,
            text=f"◈ {self.config.name.upper()} V4",
            font=UITheme.FONT_TITLE,
            fg=UITheme.CYAN,
            bg=UITheme.BG_SURFACE,
        ).pack(side="left")

        # Live State Badge
        self.state_badge = tk.Label(
            self.top_bar,
            text="● READY",
            font=UITheme.FONT_CAPTION_BOLD,
            fg=UITheme.EMERALD,
            bg=UITheme.BG_CARD,
            padx=8,
            pady=3,
        )
        self.state_badge.pack(side="left", padx=12)

        # Quick System Hardware Badges
        stats_frame = tk.Frame(self.top_bar, bg=UITheme.BG_SURFACE)
        stats_frame.pack(side="right")

        self.quick_cpu_lbl = tk.Label(stats_frame, text="CPU: --%", font=UITheme.FONT_MONO, fg=UITheme.TEXT_SECONDARY, bg=UITheme.BG_SURFACE)
        self.quick_cpu_lbl.pack(side="left", padx=4)

        self.quick_ram_lbl = tk.Label(stats_frame, text="RAM: --%", font=UITheme.FONT_MONO, fg=UITheme.TEXT_SECONDARY, bg=UITheme.BG_SURFACE)
        self.quick_ram_lbl.pack(side="left", padx=4)

        self.compact_btn = tk.Button(
            stats_frame,
            text="🗕 Pill",
            font=UITheme.FONT_CAPTION_BOLD,
            fg=UITheme.TEXT_PRIMARY,
            bg=UITheme.BG_CARD,
            activebackground=UITheme.BG_CARD_HOVER,
            bd=0,
            padx=6,
            pady=2,
            cursor="hand2",
            command=self._toggle_compact_mode,
        )
        self.compact_btn.pack(side="left", padx=(8, 0))

        # 2. Futuristic Horizontal Navigation Deck
        self.nav_frame = tk.Frame(self.root, bg=UITheme.BG_DARK, pady=4, padx=8)
        self.nav_frame.pack(fill="x")

        nav_items = [
            ("🏠 Home", "home"),
            ("💬 Chat", "chat"),
            ("⚡ Tasks", "tasks"),
            ("📊 System", "system"),
            ("🧠 Memory", "memory"),
            ("🔧 Tools", "tools"),
            ("👁️ Vision", "vision"),
            ("💻 Dev", "dev"),
            ("⏰ Auto", "auto"),
            ("⚙️ Config", "settings"),
        ]

        self.nav_buttons: dict[str, tk.Button] = {}
        for label, view_name in nav_items:
            btn = tk.Button(
                self.nav_frame,
                text=label,
                font=UITheme.FONT_CAPTION_BOLD,
                fg=UITheme.CYAN if view_name == "home" else UITheme.TEXT_SECONDARY,
                bg=UITheme.BG_CARD if view_name == "home" else UITheme.BG_DARK,
                activebackground=UITheme.BG_CARD_HOVER,
                activeforeground=UITheme.CYAN,
                bd=0,
                padx=8,
                pady=4,
                cursor="hand2",
                command=lambda vn=view_name: self.switch_view(vn),
            )
            btn.pack(side="left", padx=1, expand=True, fill="x")
            self.nav_buttons[view_name] = btn

        # 3. Central View Deck Container
        self.view_container = tk.Frame(self.root, bg=UITheme.BG_DARK)
        self.view_container.pack(fill="both", expand=True)

        # Instantiate View Subcomponents
        self.views["home"] = HomeView(self.view_container, self.assistant, on_navigate=self.switch_view)
        self.views["chat"] = ConversationView(self.view_container, self.assistant)
        self.views["tasks"] = TasksView(self.view_container, self.assistant)
        self.views["system"] = SystemHudView(self.view_container, self.assistant)
        self.views["memory"] = MemoryView(self.view_container, self.assistant)
        self.views["tools"] = ToolsView(self.view_container, self.assistant)
        self.views["vision"] = VisionView(self.view_container, self.assistant)
        self.views["dev"] = DeveloperView(self.view_container, self.assistant)
        self.views["auto"] = AutomationView(self.view_container, self.assistant)
        self.views["settings"] = SettingsView(self.view_container, self.assistant)

        # Show Home View
        self.views["home"].pack(fill="both", expand=True)

        # 4. Bottom Unified Voice & Text Command Bar
        self.bottom_bar = tk.Frame(self.root, bg=UITheme.BG_SURFACE, padx=16, pady=8)
        self.bottom_bar.pack(fill="x")

        self.mic_btn = tk.Button(
            self.bottom_bar,
            text="🎙️ Talk",
            font=UITheme.FONT_BODY_BOLD,
            fg=UITheme.BG_DARK,
            bg=UITheme.CYAN,
            activebackground=UITheme.TEXT_HIGHLIGHT,
            bd=0,
            padx=12,
            pady=4,
            cursor="hand2",
            command=self._on_mic_click,
        )
        self.mic_btn.pack(side="left", padx=(0, 8))

        self.entry = tk.Entry(
            self.bottom_bar,
            font=UITheme.FONT_BODY,
            fg=UITheme.TEXT_PRIMARY,
            bg=UITheme.BG_INPUT,
            insertbackground=UITheme.CYAN,
            bd=0,
            highlightthickness=1,
            highlightcolor=UITheme.CYAN,
            highlightbackground=UITheme.BORDER_MUTED,
        )
        self.entry.pack(side="left", fill="x", expand=True, ipady=5, padx=(0, 8))
        self.entry.bind("<Return>", lambda _: self._on_send())

        self.send_btn = tk.Button(
            self.bottom_bar,
            text="➤ Send",
            font=UITheme.FONT_BODY_BOLD,
            fg=UITheme.BG_DARK,
            bg=UITheme.EMERALD,
            activebackground=UITheme.TEXT_HIGHLIGHT,
            bd=0,
            padx=12,
            pady=4,
            cursor="hand2",
            command=self._on_send,
        )
        self.send_btn.pack(side="right")

    def switch_view(self, view_name: str) -> None:
        if view_name not in self.views or view_name == self.current_view_name:
            return

        # Hide current
        self.views[self.current_view_name].pack_forget()
        self.nav_buttons[self.current_view_name].config(fg=UITheme.TEXT_SECONDARY, bg=UITheme.BG_DARK)

        # Show target
        self.views[view_name].pack(fill="both", expand=True)
        self.nav_buttons[view_name].config(fg=UITheme.CYAN, bg=UITheme.BG_CARD)
        self.current_view_name = view_name

    def _on_mic_click(self) -> None:
        if self._state == "speaking":
            self.assistant.cancel()
        else:
            self.assistant.capture_voice_once()

    def _on_send(self) -> None:
        text = self.entry.get().strip()
        if text:
            self.entry.delete(0, "end")
            self.assistant.submit_text(text)

    def _on_task_event(self, task: Any, event: Any, message: str) -> None:
        def _update() -> None:
            event_name = event.value if hasattr(event, "value") else str(event)
            total = len(task.steps) or 1
            cur = task.current_step or (total if event_name == "TASK_COMPLETED" else 0)
            pct = int((cur / total) * 100) if total else 0

            # Update Home Card
            home_view: HomeView = self.views["home"]  # type: ignore
            home_view.update_task_progress(task.title, message, cur, total, pct)

            # Update Tasks View
            tasks_view: TasksView = self.views["tasks"]  # type: ignore
            tasks_view.update_live_plan(task, event_name, message)

        self.root.after(0, _update)

    def set_status(self, text: str) -> None:
        def _update() -> None:
            home_view: HomeView = self.views.get("home")  # type: ignore
            if home_view and hasattr(home_view, "status_sub_lbl"):
                home_view.status_sub_lbl.config(text=text)

        self.root.after(0, _update)

    def set_state(self, state: Any, status_msg: str = "") -> None:
        state_str = state.value if hasattr(state, "value") else str(state)
        self._state = state_str
        fg_color, label, _ = UITheme.STATE_CONFIG.get(state_str, (UITheme.CYAN, state_str.upper(), ""))

        def _update() -> None:
            self.state_badge.config(text=label, fg=fg_color)
            home_view: HomeView = self.views.get("home")  # type: ignore
            if home_view:
                home_view.set_state(state_str, status_msg)

        self.root.after(0, _update)

    def set_transcript(self, text: str) -> None:
        def _update() -> None:
            home_view: HomeView = self.views["home"]  # type: ignore
            home_view.set_transcript(text)
            chat_view: ConversationView = self.views["chat"]  # type: ignore
            chat_view.append_user_message(text)

        self.root.after(0, _update)

    def set_response(self, text: str) -> None:
        def _update() -> None:
            home_view: HomeView = self.views["home"]  # type: ignore
            home_view.set_response(text)
            chat_view: ConversationView = self.views["chat"]  # type: ignore
            chat_view.append_friday_message(text)

        self.root.after(0, _update)

    def show_confirmation(self, title: str, message: str, tool_name: str, on_approve: Any, on_deny: Any) -> None:
        def _show() -> None:
            ConfirmationDialog(
                self.root,
                title=title,
                message=message,
                tool_name=tool_name,
                on_approve=on_approve,
                on_deny=on_deny,
            )

        self.root.after(0, _show)

    def _toggle_compact_mode(self) -> None:
        self._is_compact = not self._is_compact
        if self._is_compact:
            self._saved_geometry = self.root.geometry()
            self.nav_frame.pack_forget()
            self.bottom_bar.pack_forget()
            self.switch_view("home")
            self.root.geometry("380x320")
            self.compact_btn.config(text="🗖 Expand", fg=UITheme.CYAN)
        else:
            self.top_bar.pack(fill="x")
            self.nav_frame.pack(fill="x", after=self.top_bar)
            self.view_container.pack(fill="both", expand=True, after=self.nav_frame)
            self.bottom_bar.pack(fill="x")
            self.root.geometry(self._saved_geometry)
            self.compact_btn.config(text="🗕 Pill", fg=UITheme.TEXT_PRIMARY)

    def _start_animation_loop(self) -> None:
        def _tick() -> None:
            home_view: HomeView = self.views["home"]  # type: ignore
            home_view.core.update_frame(dt=0.05)
            self._after_id = str(self.root.after(16, _tick))  # ~60 FPS

        _tick()

    def _start_metrics_worker(self) -> None:
        def _poll() -> None:
            while True:
                time.sleep(1.5)
                try:
                    import psutil
                    cpu = psutil.cpu_percent()
                    ram = psutil.virtual_memory().percent

                    def _update(c=cpu, r=ram) -> None:
                        self.quick_cpu_lbl.config(text=f"CPU: {c:.0f}%")
                        self.quick_ram_lbl.config(text=f"RAM: {r:.0f}%")

                    self.root.after(0, _update)
                except Exception:
                    pass

        threading.Thread(target=_poll, daemon=True).start()

    def run(self) -> None:
        self.assistant.start()
        self.root.mainloop()

    def _on_close(self) -> None:
        if self._after_id:
            try:
                self.root.after_cancel(self._after_id)
            except Exception:
                pass
        self.assistant.stop()
        self.root.destroy()
