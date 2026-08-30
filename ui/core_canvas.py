from __future__ import annotations

import math
import random
import tkinter as tk
from typing import Any

from ui.theme import UITheme


class FridayCoreCanvas:
    """High-Performance 60 FPS Animated Multi-Ring Energy Core & Audio Waveform."""

    def __init__(self, parent: tk.Widget, size: int = 180, on_click: Any = None) -> None:
        self.size = size
        self.cx = size // 2
        self.cy = size // 2
        self.state = "idle"
        self.amplitude = 0.0
        self.phase = 0.0
        self.on_click = on_click

        self.canvas = tk.Canvas(
            parent,
            width=self.size,
            height=self.size,
            bg=UITheme.BG_DARK,
            highlightthickness=0,
            cursor="hand2",
        )
        if on_click:
            self.canvas.bind("<Button-1>", lambda _: self.on_click())

        # Pre-generate 16 particle orbital offsets
        self.particles = [
            {"radius": random.uniform(34, 52), "angle": random.uniform(0, 2 * math.pi), "speed": random.uniform(0.02, 0.06), "size": random.uniform(2, 4)}
            for _ in range(16)
        ]

    def pack(self, **kwargs: Any) -> None:
        self.canvas.pack(**kwargs)

    def set_state(self, state: str) -> None:
        self.state = state

    def set_audio_amplitude(self, amp: float) -> None:
        self.amplitude = max(0.0, min(1.0, amp))

    def update_frame(self, dt: float = 0.05) -> None:
        """Render next animation frame with double-buffering."""
        self.phase += dt
        self.canvas.delete("anim")

        fg_color, _, _ = UITheme.STATE_CONFIG.get(self.state, (UITheme.CYAN, "", ""))

        # 1. Outer Audio Waveform Frequency Equalizer Bars
        num_bars = 24
        base_r = self.cx - 16
        for i in range(num_bars):
            theta = (i / num_bars) * 2 * math.pi
            if "listening" in self.state or self.state == "wake_detected":
                mod = math.sin(self.phase * 4 + i * 0.8) * 0.5 + 0.5
                bar_len = 3 + (self.amplitude * 18) + (mod * 8)
            elif self.state == "speaking":
                mod = math.sin(self.phase * 6 + i * 1.2) * 0.5 + 0.5
                bar_len = 4 + (mod * 12)
            elif self.state in ("thinking", "executing"):
                mod = math.sin(self.phase * 5 + i * 0.5) * 0.5 + 0.5
                bar_len = 2 + (mod * 6)
            else:
                mod = math.sin(self.phase * 1.5 + i * 0.4) * 0.5 + 0.5
                bar_len = 2 + (mod * 3)

            x1 = self.cx + math.cos(theta) * base_r
            y1 = self.cy + math.sin(theta) * base_r
            x2 = self.cx + math.cos(theta) * (base_r + bar_len)
            y2 = self.cy + math.sin(theta) * (base_r + bar_len)

            bar_color = fg_color if i % 2 == 0 else UITheme.CYAN
            self.canvas.create_line(x1, y1, x2, y2, fill=bar_color, width=2, tags="anim")

        # 2. Outer Rotating Orbital Ring with Ticks
        outer_r = self.cx - 24
        self.canvas.create_oval(
            self.cx - outer_r, self.cy - outer_r, self.cx + outer_r, self.cy + outer_r,
            outline=UITheme.BORDER_MUTED, width=1, tags="anim"
        )

        # Counter-rotating glowing arc segments
        arc_speed = 180 if self.state in ("thinking", "executing") else 45
        start_deg = (self.phase * arc_speed) % 360
        self.canvas.create_arc(
            self.cx - outer_r, self.cy - outer_r, self.cx + outer_r, self.cy + outer_r,
            start=start_deg, extent=80, outline=fg_color, width=3, style="arc", tags="anim"
        )
        self.canvas.create_arc(
            self.cx - outer_r, self.cy - outer_r, self.cx + outer_r, self.cy + outer_r,
            start=(start_deg + 180) % 360, extent=60, outline=UITheme.CYAN if fg_color != UITheme.CYAN else UITheme.PURPLE, width=2, style="arc", tags="anim"
        )

        # 3. Intermediate Floating Particle Nodes
        for p in self.particles:
            p["angle"] += p["speed"] * (2.5 if self.state in ("thinking", "executing") else 1.0)
            px = self.cx + math.cos(p["angle"]) * p["radius"]
            py = self.cy + math.sin(p["angle"]) * p["radius"]
            ps = p["size"]
            self.canvas.create_oval(px - ps, py - ps, px + ps, py + ps, fill=fg_color, outline="", tags="anim")

        # 4. Central Energy Core (Pulsing Glow)
        pulse = math.sin(self.phase * (3.0 if "listening" in self.state else 1.5)) * 4
        core_r = 22 + pulse + (self.amplitude * 10)

        # Outer Glow Aura
        aura_r = core_r + 8
        self.canvas.create_oval(
            self.cx - aura_r, self.cy - aura_r, self.cx + aura_r, self.cy + aura_r,
            fill=UITheme.BG_CARD, outline="", tags="anim"
        )

        # Main Core Body
        self.canvas.create_oval(
            self.cx - core_r, self.cy - core_r, self.cx + core_r, self.cy + core_r,
            fill=fg_color, outline=UITheme.TEXT_HIGHLIGHT, width=2, tags="anim"
        )

        # Inner Holographic Pupil
        inner_r = max(4.0, core_r * 0.45)
        self.canvas.create_oval(
            self.cx - inner_r, self.cy - inner_r, self.cx + inner_r, self.cy + inner_r,
            fill=UITheme.BG_DARK, outline="", tags="anim"
        )
