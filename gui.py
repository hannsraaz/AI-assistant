from __future__ import annotations

import math
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from assistant_core import VoiceAssistant
    from config import AppConfig


class AssistantWindow:
    """Modern glowing dark-mode HUD interface for Friday desktop assistant."""

    def __init__(self, assistant: VoiceAssistant, config: AppConfig) -> None:
        self.assistant = assistant
        self.config = config

        self.root = tk.Tk()
        self.root.title(f"{config.name} Assistant")
        self.root.geometry("460x580")
        self.root.minsize(400, 520)
        self.root.configure(bg="#0d1117")

        if config.ui.always_on_top:
            self.root.attributes("-topmost", True)

        self._state = "idle"  # idle, listening, thinking, speaking
        self._anim_phase = 0.0
        self._after_id: str | None = None

        self._build_ui()
        self._start_animation()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        # Header Bar
        header = tk.Frame(self.root, bg="#0d1117", pady=10)
        header.pack(fill="x", padx=16)

        title_lbl = tk.Label(
            header,
            text=self.config.name.upper(),
            font=("Segoe UI", 16, "bold"),
            fg="#00d2ff",
            bg="#0d1117",
        )
        title_lbl.pack(side="left")

        self.state_badge = tk.Label(
            header,
            text="ONLINE",
            font=("Segoe UI", 9, "bold"),
            fg="#00ffa3",
            bg="#161b22",
            padx=8,
            pady=2,
        )
        self.state_badge.pack(side="right")

        # Animated Glowing Voice Orb Canvas
        self.canvas = tk.Canvas(
            self.root,
            width=140,
            height=140,
            bg="#0d1117",
            highlightthickness=0,
        )
        self.canvas.pack(pady=4)
        self.canvas.bind("<Button-1>", lambda _: self._on_orb_click())

        # Status Label
        self.status_lbl = tk.Label(
            self.root,
            text=f"Say '{self.config.wake_word_phrase}' or click orb",
            font=("Segoe UI", 10),
            fg="#8b949e",
            bg="#0d1117",
            wraplength=400,
        )
        self.status_lbl.pack(pady=4)

        # Chat Bubble Container
        chat_frame = tk.Frame(self.root, bg="#161b22", bd=0, padx=12, pady=10)
        chat_frame.pack(fill="both", expand=True, padx=16, pady=8)

        # User transcript
        self.user_lbl = tk.Label(
            chat_frame,
            text="You: ...",
            font=("Segoe UI", 10, "italic"),
            fg="#79c0ff",
            bg="#161b22",
            anchor="w",
            justify="left",
            wraplength=400,
        )
        self.user_lbl.pack(fill="x", pady=(0, 6))

        # Friday response text
        self.resp_box = tk.Text(
            chat_frame,
            font=("Segoe UI", 11),
            fg="#f0f6fc",
            bg="#161b22",
            bd=0,
            wrap="word",
            height=6,
            highlightthickness=0,
        )
        self.resp_box.pack(fill="both", expand=True)
        self.resp_box.insert("1.0", "Friday is ready to assist you.")
        self.resp_box.config(state="disabled")

        # Quick Action Pills
        quick_frame = tk.Frame(self.root, bg="#0d1117")
        quick_frame.pack(fill="x", padx=16, pady=4)

        quick_actions = [
            ("Mute", lambda: self.assistant.submit_text("toggle mute")),
            ("Screenshot", lambda: self.assistant.submit_text("take a screenshot")),
            ("PC Stats", lambda: self.assistant.submit_text("system status")),
            ("Stop Audio", lambda: self.assistant.cancel()),
        ]

        for text, cmd in quick_actions:
            btn = tk.Button(
                quick_frame,
                text=text,
                font=("Segoe UI", 8, "bold"),
                fg="#c9d1d9",
                bg="#21262d",
                activebackground="#30363d",
                activeforeground="#ffffff",
                bd=0,
                padx=8,
                pady=4,
                cursor="hand2",
                command=cmd,
            )
            btn.pack(side="left", padx=3)

        # Bottom Input Area
        input_frame = tk.Frame(self.root, bg="#0d1117", pady=10)
        input_frame.pack(fill="x", padx=16)

        self.mic_btn = tk.Button(
            input_frame,
            text="🎙️ Talk",
            font=("Segoe UI", 10, "bold"),
            fg="#0d1117",
            bg="#00d2ff",
            activebackground="#79c0ff",
            bd=0,
            padx=12,
            pady=6,
            cursor="hand2",
            command=self._on_orb_click,
        )
        self.mic_btn.pack(side="left", padx=(0, 8))

        self.entry = tk.Entry(
            input_frame,
            font=("Segoe UI", 11),
            fg="#f0f6fc",
            bg="#21262d",
            insertbackground="#00d2ff",
            bd=0,
            highlightthickness=1,
            highlightcolor="#00d2ff",
            highlightbackground="#30363d",
        )
        self.entry.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 8))
        self.entry.bind("<Return>", lambda _: self._on_send())

        send_btn = tk.Button(
            input_frame,
            text="➤",
            font=("Segoe UI", 11, "bold"),
            fg="#ffffff",
            bg="#238636",
            activebackground="#2ea043",
            bd=0,
            padx=12,
            pady=5,
            cursor="hand2",
            command=self._on_send,
        )
        send_btn.pack(side="right")

    def _on_orb_click(self) -> None:
        if self._state == "speaking":
            self.assistant.cancel()
        else:
            self.assistant.capture_voice_once()

    def _on_send(self) -> None:
        text = self.entry.get().strip()
        if text:
            self.entry.delete(0, "end")
            self.assistant.submit_text(text)

    def set_status(self, text: str) -> None:
        self.root.after(0, lambda: self.status_lbl.config(text=text))

    def set_transcript(self, text: str) -> None:
        self.root.after(0, lambda: self.user_lbl.config(text=f"You: {text}"))

    def set_response(self, text: str) -> None:
        def _update() -> None:
            self.resp_box.config(state="normal")
            self.resp_box.delete("1.0", "end")
            self.resp_box.insert("1.0", text)
            self.resp_box.config(state="disabled")
            self.resp_box.see("end")

        self.root.after(0, _update)

    def set_state(self, state: str) -> None:
        self._state = state
        badge_colors = {
            "idle": ("#00ffa3", "READY"),
            "listening": ("#ff0055", "LISTENING"),
            "thinking": ("#e3b341", "THINKING"),
            "speaking": ("#00d2ff", "SPEAKING"),
        }
        fg, label = badge_colors.get(state, ("#8b949e", state.upper()))
        self.root.after(0, lambda: self.state_badge.config(text=label, fg=fg))

    def _start_animation(self) -> None:
        def _animate() -> None:
            self._anim_phase += 0.1
            self.canvas.delete("all")
            cx, cy = 70, 70

            if self._state == "listening":
                # Red pulse
                radius = 35 + math.sin(self._anim_phase * 2) * 8
                self.canvas.create_oval(cx - radius - 10, cy - radius - 10, cx + radius + 10, cy + radius + 10, fill="#381018", outline="")
                self.canvas.create_oval(cx - radius, cy - radius, cx + radius, cy + radius, fill="#ff0055", outline="#ff7b72", width=2)
            elif self._state == "thinking":
                # Amber spinning arc
                radius = 38
                start_angle = (self._anim_phase * 150) % 360
                self.canvas.create_oval(cx - radius, cy - radius, cx + radius, cy + radius, fill="#251e10", outline="")
                self.canvas.create_arc(cx - radius, cy - radius, cx + radius, cy + radius, start=start_angle, extent=120, outline="#e3b341", width=4, style="arc")
            elif self._state == "speaking":
                # Cyan wave expansion
                radius = 36 + math.sin(self._anim_phase * 3) * 6
                self.canvas.create_oval(cx - radius - 8, cy - radius - 8, cx + radius + 8, cy + radius + 8, fill="#0d2838", outline="")
                self.canvas.create_oval(cx - radius, cy - radius, cx + radius, cy + radius, fill="#00d2ff", outline="#79c0ff", width=2)
            else:
                # Idle subtle breathing cyan
                radius = 32 + math.sin(self._anim_phase) * 3
                self.canvas.create_oval(cx - radius - 6, cy - radius - 6, cx + radius + 6, cy + radius + 6, fill="#12202e", outline="")
                self.canvas.create_oval(cx - radius, cy - radius, cx + radius, cy + radius, fill="#1f6feb", outline="#00d2ff", width=2)

            self._after_id = str(self.root.after(40, _animate))

        _animate()

    def run(self) -> None:
        self.assistant.start()
        self.root.mainloop()

    def _on_close(self) -> None:
        if self._after_id:
            self.root.after_cancel(self._after_id)
        self.assistant.stop()
        self.root.destroy()
