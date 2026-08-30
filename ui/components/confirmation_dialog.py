from __future__ import annotations

import tkinter as tk
from typing import Callable

from ui.theme import UITheme


class ConfirmationDialog(tk.Toplevel):
    """Futuristic modal dialog for approving high-risk operations and system actions."""

    def __init__(
        self,
        parent: tk.Tk,
        title: str,
        message: str,
        tool_name: str,
        risk_level: str = "HIGH",
        on_approve: Callable[[], None] | None = None,
        on_deny: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.title("SECURITY AUTHORIZATION REQUIRED")
        self.geometry("440x260")
        self.resizable(False, False)
        self.configure(bg=UITheme.BG_SURFACE)
        self.attributes("-topmost", True)
        self.transient(parent)
        self.grab_set()

        self.on_approve = on_approve or (lambda: None)
        self.on_deny = on_deny or (lambda: None)

        # Center on parent
        x = parent.winfo_x() + (parent.winfo_width() // 2) - 220
        y = parent.winfo_y() + (parent.winfo_height() // 2) - 130
        self.geometry(f"+{max(0, x)}+{max(0, y)}")

        # 1. Header Banner
        header = tk.Frame(self, bg=UITheme.BG_DARK, pady=8, padx=16)
        header.pack(fill="x")

        risk_color = UITheme.RED if "HIGH" in risk_level.upper() else UITheme.AMBER
        tk.Label(
            header,
            text=f"⚠ {risk_level.upper()} RISK ACTION",
            font=UITheme.FONT_SUBTITLE,
            fg=risk_color,
            bg=UITheme.BG_DARK,
        ).pack(side="left")

        tk.Label(
            header,
            text=f"Tool: {tool_name}",
            font=UITheme.FONT_CAPTION,
            fg=UITheme.TEXT_SECONDARY,
            bg=UITheme.BG_DARK,
        ).pack(side="right")

        # 2. Content Frame
        content = tk.Frame(self, bg=UITheme.BG_SURFACE, padx=16, pady=12)
        content.pack(fill="both", expand=True)

        tk.Label(
            content,
            text=title,
            font=UITheme.FONT_BODY_BOLD,
            fg=UITheme.TEXT_PRIMARY,
            bg=UITheme.BG_SURFACE,
            anchor="w",
            wraplength=400,
        ).pack(fill="x", pady=(0, 4))

        msg_box = tk.Label(
            content,
            text=message,
            font=UITheme.FONT_MONO,
            fg=UITheme.CYAN,
            bg=UITheme.BG_CARD,
            padx=8,
            pady=6,
            anchor="w",
            justify="left",
            wraplength=390,
            relief="solid",
            bd=1,
        )
        msg_box.pack(fill="both", expand=True, pady=4)

        # 3. Action Buttons
        btn_frame = tk.Frame(self, bg=UITheme.BG_SURFACE, pady=10, padx=16)
        btn_frame.pack(fill="x")

        deny_btn = tk.Button(
            btn_frame,
            text="✕ DENY / CANCEL",
            font=UITheme.FONT_BODY_BOLD,
            fg=UITheme.TEXT_PRIMARY,
            bg=UITheme.BG_CARD,
            activebackground=UITheme.BG_CARD_HOVER,
            bd=0,
            padx=16,
            pady=6,
            cursor="hand2",
            command=self._handle_deny,
        )
        deny_btn.pack(side="left", padx=(0, 8))

        allow_btn = tk.Button(
            btn_frame,
            text="✓ AUTHORIZE & EXECUTE",
            font=UITheme.FONT_BODY_BOLD,
            fg=UITheme.BG_DARK,
            bg=risk_color,
            activebackground=UITheme.TEXT_HIGHLIGHT,
            bd=0,
            padx=16,
            pady=6,
            cursor="hand2",
            command=self._handle_approve,
        )
        allow_btn.pack(side="right")

    def _handle_approve(self) -> None:
        self.destroy()
        self.on_approve()

    def _handle_deny(self) -> None:
        self.destroy()
        self.on_deny()
