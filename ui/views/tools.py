from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING, Any

from ui.theme import UITheme

if TYPE_CHECKING:
    from assistant_core import VoiceAssistant


class ToolsView(tk.Frame):
    """Visual Toolbox & Capability Explorer for registered tools."""

    def __init__(self, parent: tk.Widget, assistant: VoiceAssistant) -> None:
        super().__init__(parent, bg=UITheme.BG_DARK)
        self.assistant = assistant
        self.tools_list: list[dict[str, Any]] = []

        self._build_ui()
        self.refresh_tools()

    def _build_ui(self) -> None:
        header = tk.Frame(self, bg=UITheme.BG_SURFACE, padx=16, pady=8)
        header.pack(fill="x")

        tk.Label(
            header,
            text="TOOLBOX & CAPABILITIES EXPLORER",
            font=UITheme.FONT_SUBTITLE,
            fg=UITheme.CYAN,
            bg=UITheme.BG_SURFACE,
        ).pack(side="left")

        # Split pane
        content = tk.Frame(self, bg=UITheme.BG_DARK, padx=16, pady=8)
        content.pack(fill="both", expand=True)

        # Left list
        self.listbox = tk.Listbox(
            content,
            bg=UITheme.BG_SURFACE,
            fg=UITheme.TEXT_PRIMARY,
            font=UITheme.FONT_MONO,
            bd=0,
            highlightthickness=1,
            highlightbackground=UITheme.BORDER_MUTED,
            selectbackground=UITheme.BG_CARD_HOVER,
            selectforeground=UITheme.CYAN,
            width=32,
        )
        self.listbox.pack(side="left", fill="both", expand=True, padx=(0, 8))
        self.listbox.bind("<<ListboxSelect>>", self._on_select_tool)

        # Right Detail Card
        detail_card = tk.LabelFrame(
            content,
            text="🔧 Tool Specification",
            font=UITheme.FONT_BODY_BOLD,
            fg=UITheme.EMERALD,
            bg=UITheme.BG_CARD,
            padx=10,
            pady=10,
        )
        detail_card.pack(side="right", fill="both", expand=True)

        self.tool_name_lbl = tk.Label(
            detail_card,
            text="Tool: Select a tool",
            font=UITheme.FONT_BODY_BOLD,
            fg=UITheme.CYAN,
            bg=UITheme.BG_CARD,
            anchor="w",
        )
        self.tool_name_lbl.pack(fill="x", pady=(0, 2))

        self.tool_risk_lbl = tk.Label(
            detail_card,
            text="Risk Level: N/A",
            font=UITheme.FONT_CAPTION_BOLD,
            fg=UITheme.TEXT_MUTED,
            bg=UITheme.BG_CARD,
            anchor="w",
        )
        self.tool_risk_lbl.pack(fill="x", pady=(0, 4))

        self.detail_box = tk.Text(
            detail_card,
            bg=UITheme.BG_SURFACE,
            fg=UITheme.TEXT_PRIMARY,
            font=UITheme.FONT_MONO,
            bd=0,
            wrap="word",
            height=8,
            padx=8,
            pady=8,
        )
        self.detail_box.pack(fill="both", expand=True, pady=(0, 8))

        btn_bar = tk.Frame(detail_card, bg=UITheme.BG_CARD)
        btn_bar.pack(fill="x")

        self.exec_btn = tk.Button(
            btn_bar,
            text="▶ Execute Tool",
            font=UITheme.FONT_CAPTION_BOLD,
            fg=UITheme.TEXT_HIGHLIGHT,
            bg=UITheme.CYAN,
            activebackground=UITheme.TEXT_HIGHLIGHT,
            bd=0,
            padx=12,
            pady=4,
            cursor="hand2",
            command=self._execute_selected,
        )
        self.exec_btn.pack(side="right")

    def refresh_tools(self) -> None:
        if not hasattr(self.assistant, "desktop") or not hasattr(self.assistant.desktop, "registry"):
            return

        registry = self.assistant.desktop.registry
        raw_tools = registry.list_tools()

        self.tools_list = []
        for item in raw_tools:
            if isinstance(item, str):
                tool_name = item
                tool_obj = registry.get(item) if hasattr(registry, "get") else None
            else:
                tool_name = getattr(item, "name", str(item))
                tool_obj = item

            risk = getattr(tool_obj, "risk_level", "NORMAL")
            risk_val = risk.value if hasattr(risk, "value") else str(risk)
            desc = getattr(tool_obj, "description", "No description available.")
            params = getattr(tool_obj, "parameters", {})

            self.tools_list.append({
                "name": tool_name,
                "risk_level": risk_val,
                "description": desc,
                "parameters": params,
                "obj": tool_obj,
            })

        self.tools_list.sort(key=lambda t: t["name"])

        self.listbox.delete(0, "end")
        for t in self.tools_list:
            r = t["risk_level"][:4].upper()
            self.listbox.insert("end", f"  [{r:4}] {t['name']}")

    def _on_select_tool(self, _: Any) -> None:
        sel = self.listbox.curselection()
        if not sel or sel[0] >= len(self.tools_list):
            return

        t = self.tools_list[sel[0]]
        risk_val = t["risk_level"]
        risk_color = UITheme.RED if "HIGH" in risk_val.upper() else (UITheme.AMBER if "CONFIRM" in risk_val.upper() else UITheme.EMERALD)

        self.tool_name_lbl.config(text=f"Tool: {t['name']}")
        self.tool_risk_lbl.config(text=f"Risk Level: {risk_val.upper()}", fg=risk_color)

        self.detail_box.delete("1.0", "end")
        self.detail_box.insert("end", f"Description:\n{t['description']}\n\nParameters Schema:\n")
        params = t.get("parameters", {})
        if params:
            for k, v in params.items():
                self.detail_box.insert("end", f" - {k}: {v}\n")
        else:
            self.detail_box.insert("end", " None (No required arguments)\n")

    def _execute_selected(self) -> None:
        sel = self.listbox.curselection()
        if not sel or sel[0] >= len(self.tools_list):
            return

        t = self.tools_list[sel[0]]
        tool_name = t["name"]
        if hasattr(self.assistant.desktop.registry, "execute"):
            res = self.assistant.desktop.registry.execute(tool_name)
            self.detail_box.insert("end", f"\nExecution Result:\nSuccess: {res.success}\nMessage: {res.message}\nData: {res.data}\n")
            self.detail_box.see("end")
