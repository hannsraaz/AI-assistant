from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING, Any

from ui.theme import UITheme

if TYPE_CHECKING:
    from assistant_core import VoiceAssistant


class MemoryView(tk.Frame):
    """Semantic Memory Explorer & Knowledge Base Management View."""

    def __init__(self, parent: tk.Widget, assistant: VoiceAssistant) -> None:
        super().__init__(parent, bg=UITheme.BG_DARK)
        self.assistant = assistant
        self.memories: list[dict[str, Any]] = []

        self._build_ui()
        self.refresh_memories()

    def _build_ui(self) -> None:
        # Header & Search Bar
        header = tk.Frame(self, bg=UITheme.BG_SURFACE, padx=16, pady=8)
        header.pack(fill="x")

        tk.Label(
            header,
            text="PERSISTENT KNOWLEDGE & MEMORY",
            font=UITheme.FONT_SUBTITLE,
            fg=UITheme.CYAN,
            bg=UITheme.BG_SURFACE,
        ).pack(side="left")

        search_frame = tk.Frame(header, bg=UITheme.BG_SURFACE)
        search_frame.pack(side="right")

        self.search_entry = tk.Entry(
            search_frame,
            font=UITheme.FONT_BODY,
            fg=UITheme.TEXT_PRIMARY,
            bg=UITheme.BG_INPUT,
            bd=0,
            insertbackground=UITheme.CYAN,
            width=20,
        )
        self.search_entry.pack(side="left", padx=(0, 6), ipady=2)
        self.search_entry.bind("<Return>", lambda _: self._on_search())

        search_btn = tk.Button(
            search_frame,
            text="🔍 Search",
            font=UITheme.FONT_CAPTION_BOLD,
            fg=UITheme.TEXT_PRIMARY,
            bg=UITheme.BG_CARD,
            activebackground=UITheme.BG_CARD_HOVER,
            bd=0,
            padx=8,
            pady=3,
            cursor="hand2",
            command=self._on_search,
        )
        search_btn.pack(side="left")

        # Content Split Pane
        content = tk.Frame(self, bg=UITheme.BG_DARK, padx=16, pady=8)
        content.pack(fill="both", expand=True)

        # Left Listbox
        self.listbox = tk.Listbox(
            content,
            bg=UITheme.BG_SURFACE,
            fg=UITheme.TEXT_PRIMARY,
            font=UITheme.FONT_BODY,
            bd=0,
            highlightthickness=1,
            highlightbackground=UITheme.BORDER_MUTED,
            selectbackground=UITheme.BG_CARD_HOVER,
            selectforeground=UITheme.CYAN,
            width=36,
        )
        self.listbox.pack(side="left", fill="both", expand=True, padx=(0, 8))
        self.listbox.bind("<<ListboxSelect>>", self._on_select_memory)

        # Right Detail Card
        detail_card = tk.LabelFrame(
            content,
            text="📖 Memory Record Details",
            font=UITheme.FONT_BODY_BOLD,
            fg=UITheme.EMERALD,
            bg=UITheme.BG_CARD,
            padx=10,
            pady=10,
        )
        detail_card.pack(side="right", fill="both", expand=True)

        self.detail_key_lbl = tk.Label(
            detail_card,
            text="Category / Key: None selected",
            font=UITheme.FONT_BODY_BOLD,
            fg=UITheme.CYAN,
            bg=UITheme.BG_CARD,
            anchor="w",
        )
        self.detail_key_lbl.pack(fill="x", pady=(0, 4))

        self.detail_text = tk.Text(
            detail_card,
            bg=UITheme.BG_SURFACE,
            fg=UITheme.TEXT_PRIMARY,
            font=UITheme.FONT_BODY,
            bd=0,
            wrap="word",
            height=8,
            padx=8,
            pady=8,
        )
        self.detail_text.pack(fill="both", expand=True, pady=(0, 8))

        forget_btn = tk.Button(
            detail_card,
            text="🗑 Delete / Forget Memory",
            font=UITheme.FONT_CAPTION_BOLD,
            fg=UITheme.RED,
            bg=UITheme.BG_SURFACE,
            activebackground=UITheme.BG_CARD_HOVER,
            bd=0,
            padx=8,
            pady=4,
            cursor="hand2",
            command=self._forget_selected,
        )
        forget_btn.pack(side="right")

    def refresh_memories(self, query: str = "") -> None:
        if not getattr(self.assistant, "memory", None):
            return

        if hasattr(self.assistant.memory, "list_memories"):
            all_mems = self.assistant.memory.list_memories(category="all", limit=50)
        elif hasattr(self.assistant.memory, "list_all"):
            all_mems = self.assistant.memory.list_all()
        else:
            all_mems = []

        if query:
            q_lower = query.lower()
            self.memories = [
                m for m in all_mems
                if q_lower in str(m.get("content", "")).lower()
                or q_lower in str(m.get("value", "")).lower()
                or q_lower in str(m.get("key", "")).lower()
                or q_lower in str(m.get("category", "")).lower()
                or q_lower in str(m.get("type", "")).lower()
            ]
        else:
            self.memories = all_mems

        self.listbox.delete(0, "end")
        if not self.memories:
            self.listbox.insert("end", "  No memories found.")
            return

        for m in self.memories:
            cat = str(m.get("category") or m.get("type") or "FACT").upper()
            k = m.get("key", "")
            v = m.get("value") or m.get("content") or ""
            display_str = f"{k}: {v}" if k else str(v)
            content_prev = display_str[:28]
            self.listbox.insert("end", f"  [{cat:8}] {content_prev}...")

    def _on_search(self) -> None:
        q = self.search_entry.get().strip()
        self.refresh_memories(query=q)

    def _on_select_memory(self, _: Any) -> None:
        sel = self.listbox.curselection()
        if not sel or sel[0] >= len(self.memories):
            return

        mem = self.memories[sel[0]]
        cat = str(m_cat := mem.get("category") or mem.get("type") or "FACT").upper()
        k = mem.get("key", "")
        mem_id = mem.get("memory_id") or mem.get("id") or k or "N/A"
        self.detail_key_lbl.config(text=f"[{cat}] {k if k else 'Key'} | ID: {str(mem_id)[:8]}")
        self.detail_text.delete("1.0", "end")
        self.detail_text.insert("1.0", str(mem.get("value") or mem.get("content") or ""))

    def _forget_selected(self) -> None:
        sel = self.listbox.curselection()
        if not sel or sel[0] >= len(self.memories):
            return

        mem = self.memories[sel[0]]
        mem_id = mem.get("memory_id") or mem.get("id") or mem.get("key")
        if mem_id and hasattr(self.assistant.memory, "delete_memory"):
            self.assistant.memory.delete_memory(mem_id)
            self.refresh_memories()
            self.detail_key_lbl.config(text="Memory removed.")
            self.detail_text.delete("1.0", "end")
        elif mem_id and hasattr(self.assistant.memory, "forget"):
            self.assistant.memory.forget(str(mem.get("key") or mem_id))
            self.refresh_memories()
            self.detail_key_lbl.config(text="Memory removed.")
            self.detail_text.delete("1.0", "end")
