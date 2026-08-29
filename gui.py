from __future__ import annotations

import math
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING, Any

from core.telemetry import global_telemetry

if TYPE_CHECKING:
    from assistant_core import VoiceAssistant
    from config import AppConfig


class AssistantWindow:
    """Modern glowing dark-mode HUD & Control Center for Friday V3.1 with Developer Diagnostics."""

    def __init__(self, assistant: VoiceAssistant, config: AppConfig) -> None:
        self.assistant = assistant
        self.config = config

        self.root = tk.Tk()
        self.root.title(f"{config.name} V3.1 — Voice Assistant")
        self.root.geometry("500x700")
        self.root.minsize(460, 600)
        self.root.configure(bg="#0d1117")

        if config.ui.always_on_top:
            self.root.attributes("-topmost", True)

        self._state = "idle"  # listening_for_wake, wake_detected, listening_for_command, transcribing, thinking, executing, speaking, error
        self._anim_phase = 0.0
        self._after_id: str | None = None
        self._show_diag = tk.BooleanVar(value=True)

        # Hook task events to GUI
        self.assistant.task_manager.on_task_event = self._on_task_event

        self._build_ui()
        self._start_animation()
        self._start_telemetry_polling()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        # 1. Header Bar
        header = tk.Frame(self.root, bg="#0d1117", pady=8)
        header.pack(fill="x", padx=16)

        title_lbl = tk.Label(
            header,
            text=f"{self.config.name.upper()} V3.1",
            font=("Segoe UI", 15, "bold"),
            fg="#00d2ff",
            bg="#0d1117",
        )
        title_lbl.pack(side="left")

        self.state_badge = tk.Label(
            header,
            text="WAKE READY",
            font=("Segoe UI", 9, "bold"),
            fg="#00ffa3",
            bg="#161b22",
            padx=8,
            pady=2,
        )
        self.state_badge.pack(side="right")

        # 2. Animated Voice Orb Canvas
        self.canvas = tk.Canvas(
            self.root,
            width=100,
            height=100,
            bg="#0d1117",
            highlightthickness=0,
        )
        self.canvas.pack(pady=2)
        self.canvas.bind("<Button-1>", lambda _: self._on_orb_click())

        # 3. Status Label
        self.status_lbl = tk.Label(
            self.root,
            text=f"Say '{self.config.wake_word_phrase}' or click orb",
            font=("Segoe UI", 9),
            fg="#8b949e",
            bg="#0d1117",
            wraplength=440,
        )
        self.status_lbl.pack(pady=2)

        # 4. Live Task & Progress Frame
        self.task_frame = tk.Frame(self.root, bg="#161b22", padx=10, pady=6)
        self.task_frame.pack(fill="x", padx=16, pady=4)

        self.task_title_lbl = tk.Label(
            self.task_frame,
            text="Active Task: None",
            font=("Segoe UI", 9, "bold"),
            fg="#79c0ff",
            bg="#161b22",
            anchor="w",
        )
        self.task_title_lbl.pack(fill="x")

        self.progress_bar = ttk.Progressbar(self.task_frame, mode="determinate", maximum=100, value=0)
        self.progress_bar.pack(fill="x", pady=3)

        self.task_step_lbl = tk.Label(
            self.task_frame,
            text="Ready for voice or text instruction.",
            font=("Segoe UI", 8),
            fg="#8b949e",
            bg="#161b22",
            anchor="w",
        )
        self.task_step_lbl.pack(fill="x")

        # 5. Chat & Response Container
        chat_frame = tk.Frame(self.root, bg="#161b22", bd=0, padx=10, pady=6)
        chat_frame.pack(fill="both", expand=True, padx=16, pady=4)

        self.user_lbl = tk.Label(
            chat_frame,
            text="You: ...",
            font=("Segoe UI", 9, "italic"),
            fg="#79c0ff",
            bg="#161b22",
            anchor="w",
            wraplength=440,
        )
        self.user_lbl.pack(fill="x", pady=(0, 2))

        self.resp_box = tk.Text(
            chat_frame,
            font=("Segoe UI", 10),
            fg="#f0f6fc",
            bg="#161b22",
            bd=0,
            wrap="word",
            height=4,
            highlightthickness=0,
        )
        self.resp_box.pack(fill="both", expand=True)
        self.resp_box.insert("1.0", "Friday V3.1 is listening.")
        self.resp_box.config(state="disabled")

        # 6. Developer Diagnostics Panel (Phase 16)
        self.diag_frame = tk.LabelFrame(
            self.root,
            text="⚙️ Latency & Audio Health Diagnostics",
            font=("Segoe UI", 8, "bold"),
            fg="#8b949e",
            bg="#0d1117",
            padx=8,
            pady=4,
        )
        self.diag_frame.pack(fill="x", padx=16, pady=2)

        health_row = tk.Frame(self.diag_frame, bg="#0d1117")
        health_row.pack(fill="x")

        self.mic_health_lbl = tk.Label(health_row, text="Mic: ● CONNECTED", font=("Segoe UI", 8, "bold"), fg="#00ffa3", bg="#0d1117")
        self.mic_health_lbl.pack(side="left", padx=4)

        self.wake_health_lbl = tk.Label(health_row, text="Wake: ● LISTENING", font=("Segoe UI", 8, "bold"), fg="#00d2ff", bg="#0d1117")
        self.wake_health_lbl.pack(side="left", padx=8)

        self.latency_lbl = tk.Label(
            self.diag_frame,
            text="Latency: STT --ms | Router --ms | Tool --ms | TTS --ms | E2E --ms",
            font=("Segoe UI", 8),
            fg="#c9d1d9",
            bg="#0d1117",
            anchor="w",
        )
        self.latency_lbl.pack(fill="x", pady=2)

        # 7. Quick Actions
        quick_frame = tk.Frame(self.root, bg="#0d1117")
        quick_frame.pack(fill="x", padx=16, pady=2)

        quick_actions = [
            ("Mute", lambda: self.assistant.submit_text("toggle mute")),
            ("Vision", lambda: self.assistant.submit_text("describe what is on my screen")),
            ("Stats", lambda: self.assistant.submit_text("system status")),
            ("Cancel / Stop", lambda: self.assistant.cancel()),
        ]

        for text, cmd in quick_actions:
            btn = tk.Button(
                quick_frame,
                text=text,
                font=("Segoe UI", 8, "bold"),
                fg="#c9d1d9" if "Cancel" not in text else "#ff7b72",
                bg="#21262d",
                activebackground="#30363d",
                activeforeground="#ffffff",
                bd=0,
                padx=8,
                pady=2,
                cursor="hand2",
                command=cmd,
            )
            btn.pack(side="left", padx=2)

        # 8. Bottom Input Bar
        input_frame = tk.Frame(self.root, bg="#0d1117", pady=6)
        input_frame.pack(fill="x", padx=16)

        self.mic_btn = tk.Button(
            input_frame,
            text="🎙️ Talk",
            font=("Segoe UI", 9, "bold"),
            fg="#0d1117",
            bg="#00d2ff",
            activebackground="#79c0ff",
            bd=0,
            padx=8,
            pady=3,
            cursor="hand2",
            command=self._on_orb_click,
        )
        self.mic_btn.pack(side="left", padx=(0, 6))

        self.entry = tk.Entry(
            input_frame,
            font=("Segoe UI", 10),
            fg="#f0f6fc",
            bg="#21262d",
            insertbackground="#00d2ff",
            bd=0,
            highlightthickness=1,
            highlightcolor="#00d2ff",
            highlightbackground="#30363d",
        )
        self.entry.pack(side="left", fill="x", expand=True, ipady=4, padx=(0, 6))
        self.entry.bind("<Return>", lambda _: self._on_send())

        send_btn = tk.Button(
            input_frame,
            text="➤",
            font=("Segoe UI", 9, "bold"),
            fg="#ffffff",
            bg="#238636",
            activebackground="#2ea043",
            bd=0,
            padx=10,
            pady=3,
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

    def _on_task_event(self, task: Any, event: Any, message: str) -> None:
        def _update() -> None:
            self.task_title_lbl.config(text=f"Active Task: {task.title}")
            total = len(task.steps) or 1
            cur = task.current_step or (1 if event.value == "TASK_COMPLETED" else 0)
            pct = int((cur / total) * 100) if total else 0
            self.progress_bar["value"] = pct
            self.task_step_lbl.config(text=message)

        self.root.after(0, _update)

    def _start_telemetry_polling(self) -> None:
        def _poll() -> None:
            # Check mic connection
            if getattr(self.assistant, "audio_capture", None):
                conn = self.assistant.audio_capture.is_connected
                self.mic_health_lbl.config(
                    text="Mic: ● CONNECTED" if conn else "Mic: ● DISCONNECTED",
                    fg="#00ffa3" if conn else "#ff7b72",
                )

            # Check latest turn telemetry
            latest = global_telemetry.get_latest()
            if latest:
                self.latency_lbl.config(
                    text=(
                        f"Speech-to-Audio: {latest.speech_end_to_first_audio_ms:.0f}ms | "
                        f"STT: {latest.stt_duration_ms:.0f}ms | Router: {latest.router_duration_ms:.1f}ms | "
                        f"Tool: {latest.tool_duration_ms:.0f}ms | TTS: {latest.tts_first_audio_ms:.0f}ms | "
                        f"Total: {latest.total_latency_ms:.0f}ms"
                    )
                )

            self.root.after(1000, _poll)

        self.root.after(1000, _poll)

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
            "listening_for_wake": ("#00ffa3", "WAKE LISTENING"),
            "wake_detected": ("#ff0055", "WAKE DETECTED"),
            "listening_for_command": ("#ff0055", "LISTENING"),
            "transcribing": ("#e3b341", "TRANSCRIBING"),
            "thinking": ("#e3b341", "THINKING"),
            "executing": ("#bc8cff", "EXECUTING"),
            "speaking": ("#00d2ff", "SPEAKING"),
            "interrupted": ("#ff7b72", "INTERRUPTED"),
            "error": ("#ff7b72", "ERROR"),
        }
        fg, label = badge_colors.get(state, ("#8b949e", state.upper()))
        self.root.after(0, lambda: self.state_badge.config(text=label, fg=fg))

    def _start_animation(self) -> None:
        def _animate() -> None:
            self._anim_phase += 0.1
            self.canvas.delete("all")
            cx, cy = 50, 50

            if "listening" in self._state or self._state == "wake_detected":
                radius = 26 + math.sin(self._anim_phase * 2) * 5
                self.canvas.create_oval(cx - radius - 7, cy - radius - 7, cx + radius + 7, cy + radius + 7, fill="#381018", outline="")
                self.canvas.create_oval(cx - radius, cy - radius, cx + radius, cy + radius, fill="#ff0055", outline="#ff7b72", width=2)
            elif self._state in ("thinking", "executing", "transcribing"):
                radius = 28
                start_angle = (self._anim_phase * 150) % 360
                self.canvas.create_oval(cx - radius, cy - radius, cx + radius, cy + radius, fill="#251e10", outline="")
                self.canvas.create_arc(cx - radius, cy - radius, cx + radius, cy + radius, start=start_angle, extent=120, outline="#e3b341" if self._state != "executing" else "#bc8cff", width=4, style="arc")
            elif self._state == "speaking":
                radius = 26 + math.sin(self._anim_phase * 3) * 5
                self.canvas.create_oval(cx - radius - 5, cy - radius - 5, cx + radius + 5, cy + radius + 5, fill="#0d2838", outline="")
                self.canvas.create_oval(cx - radius, cy - radius, cx + radius, cy + radius, fill="#00d2ff", outline="#79c0ff", width=2)
            else:
                radius = 24 + math.sin(self._anim_phase) * 2
                self.canvas.create_oval(cx - radius - 4, cy - radius - 4, cx + radius + 4, cy + radius + 4, fill="#12202e", outline="")
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
