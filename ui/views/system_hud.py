from __future__ import annotations

import threading
import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING, Any

from core.resource_manager import global_resource_manager
from core.telemetry import global_telemetry
from ui.theme import UITheme

if TYPE_CHECKING:
    from assistant_core import VoiceAssistant


class SystemHudView(tk.Frame):
    """Futuristic real-time system hardware telemetry and E2E voice latency HUD."""

    def __init__(self, parent: tk.Widget, assistant: VoiceAssistant) -> None:
        super().__init__(parent, bg=UITheme.BG_DARK)
        self.assistant = assistant

        self._build_ui()
        self.refresh_metrics()

    def _build_ui(self) -> None:
        # Header
        header = tk.Frame(self, bg=UITheme.BG_SURFACE, padx=16, pady=8)
        header.pack(fill="x")

        tk.Label(
            header,
            text="SYSTEM TELEMETRY & HARDWARE HUD",
            font=UITheme.FONT_SUBTITLE,
            fg=UITheme.CYAN,
            bg=UITheme.BG_SURFACE,
        ).pack(side="left")

        refresh_btn = tk.Button(
            header,
            text="⚡ Poll Telemetry",
            font=UITheme.FONT_CAPTION_BOLD,
            fg=UITheme.TEXT_SECONDARY,
            bg=UITheme.BG_CARD,
            activebackground=UITheme.BG_CARD_HOVER,
            bd=0,
            padx=8,
            pady=3,
            cursor="hand2",
            command=self.refresh_metrics,
        )
        refresh_btn.pack(side="right")

        content = tk.Frame(self, bg=UITheme.BG_DARK, padx=16, pady=8)
        content.pack(fill="both", expand=True)

        # 1. Hardware Grid Cards
        hw_frame = tk.LabelFrame(
            content,
            text="💻 Host Hardware Compute & Memory",
            font=UITheme.FONT_BODY_BOLD,
            fg=UITheme.EMERALD,
            bg=UITheme.BG_CARD,
            padx=10,
            pady=10,
        )
        hw_frame.pack(fill="x", pady=(0, 8))

        grid = tk.Frame(hw_frame, bg=UITheme.BG_CARD)
        grid.pack(fill="x")

        # CPU Card
        self.cpu_lbl = self._create_metric_tile(grid, "CPU USAGE", "0%", 0, 0, UITheme.CYAN)
        # GPU Card
        self.gpu_lbl = self._create_metric_tile(grid, "GPU VRAM", "0 MB", 0, 1, UITheme.PURPLE)
        # RAM Card
        self.ram_lbl = self._create_metric_tile(grid, "RAM USAGE", "0 GB", 1, 0, UITheme.EMERALD)
        # Battery Card
        self.bat_lbl = self._create_metric_tile(grid, "BATTERY", "100%", 1, 1, UITheme.AMBER)

        # 2. Audio & Latency Telemetry Breakdown Card
        lat_frame = tk.LabelFrame(
            content,
            text="⏱️ E2E Voice Roundtrip Latency Telemetry (Latest Turn)",
            font=UITheme.FONT_BODY_BOLD,
            fg=UITheme.CYAN,
            bg=UITheme.BG_CARD,
            padx=10,
            pady=10,
        )
        lat_frame.pack(fill="both", expand=True)

        self.stt_lat_lbl = self._create_latency_row(lat_frame, "1. Speech-To-Text (Whisper):", "-- ms")
        self.router_lat_lbl = self._create_latency_row(lat_frame, "2. Fast-Path Intent Router:", "-- ms")
        self.llm_lat_lbl = self._create_latency_row(lat_frame, "3. LLM First Token Streaming:", "-- ms")
        self.tts_lat_lbl = self._create_latency_row(lat_frame, "4. TTS First Audio Output:", "-- ms")
        self.total_lat_lbl = self._create_latency_row(lat_frame, "⚡ Total Turn Latency (E2E):", "-- ms", bold=True, fg=UITheme.EMERALD)

    def _create_metric_tile(self, parent: tk.Widget, title: str, init_val: str, row: int, col: int, color: str) -> tk.Label:
        tile = tk.Frame(parent, bg=UITheme.BG_SURFACE, padx=12, pady=8, highlightthickness=1, highlightbackground=UITheme.BORDER_MUTED)
        tile.grid(row=row, column=col, sticky="nsew", padx=4, pady=4)
        parent.grid_columnconfigure(col, weight=1)

        tk.Label(tile, text=title, font=UITheme.FONT_CAPTION_BOLD, fg=UITheme.TEXT_MUTED, bg=UITheme.BG_SURFACE).pack(anchor="w")
        lbl = tk.Label(tile, text=init_val, font=UITheme.FONT_TITLE, fg=color, bg=UITheme.BG_SURFACE)
        lbl.pack(anchor="w", pady=(2, 0))
        return lbl

    def _create_latency_row(self, parent: tk.Widget, label_text: str, init_val: str, bold: bool = False, fg: str = UITheme.TEXT_PRIMARY) -> tk.Label:
        row = tk.Frame(parent, bg=UITheme.BG_CARD, pady=2)
        row.pack(fill="x")

        tk.Label(row, text=label_text, font=UITheme.FONT_BODY_BOLD if bold else UITheme.FONT_BODY, fg=UITheme.TEXT_SECONDARY if not bold else UITheme.TEXT_PRIMARY, bg=UITheme.BG_CARD).pack(side="left")
        lbl = tk.Label(row, text=init_val, font=UITheme.FONT_MONO_BOLD if bold else UITheme.FONT_MONO, fg=fg, bg=UITheme.BG_CARD)
        lbl.pack(side="right")
        return lbl

    def refresh_metrics(self) -> None:
        def _worker() -> None:
            # Poll GPU & CPU
            gpu_info = global_resource_manager.get_gpu_memory_status()
            sys_info = global_resource_manager.get_system_memory_status()

            cpu_pct = 0.0
            try:
                import psutil
                cpu_pct = psutil.cpu_percent()
            except Exception:
                pass

            cpu_txt = f"{cpu_pct:.0f}%"
            gpu_txt = f"{gpu_info.get('allocated_mb', 0):.0f} / {gpu_info.get('total_mb', 0):.0f} MB" if gpu_info.get("available") else "CPU Standby"
            ram_txt = f"{sys_info.get('used_gb', 0):.1f} / {sys_info.get('total_gb', 0):.1f} GB ({sys_info.get('percent', 0)}%)"

            # Battery info
            bat_txt = "AC Desktop"
            if hasattr(self.assistant, "desktop"):
                bat_res = self.assistant.desktop.registry.execute("system.battery")
                if bat_res.success and bat_res.data.get("has_battery"):
                    bat_txt = f"{bat_res.data.get('percent', 100)}% {'⚡' if bat_res.data.get('charging') else ''}"

            # Turn Telemetry
            latest = global_telemetry.get_latest()

            def _update_ui() -> None:
                self.cpu_lbl.config(text=cpu_txt)
                self.gpu_lbl.config(text=gpu_txt)
                self.ram_lbl.config(text=ram_txt)
                self.bat_lbl.config(text=bat_txt)

                if latest:
                    self.stt_lat_lbl.config(text=f"{latest.stt_duration_ms:.0f} ms")
                    self.router_lat_lbl.config(text=f"{latest.router_duration_ms:.1f} ms")
                    self.llm_lat_lbl.config(text=f"{latest.llm_first_token_ms:.0f} ms")
                    self.tts_lat_lbl.config(text=f"{latest.tts_first_audio_ms:.0f} ms")
                    self.total_lat_lbl.config(text=f"{latest.total_latency_ms:.0f} ms")

            try:
                if self.winfo_exists():
                    self.after(0, _update_ui)
            except Exception:
                pass

        threading.Thread(target=_worker, daemon=True).start()
