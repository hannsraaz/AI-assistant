from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from core.tools.base import ToolResult

logger = logging.getLogger("context")


@dataclass
class UnifiedContext:
    """Unified context object providing filtered, relevant context to the planner and LLM."""

    conversation_history: list[dict[str, str]] = field(default_factory=list)
    current_goal: str | None = None
    current_task_id: str | None = None
    assistant_state: str = "idle"
    active_application: str = ""
    active_window_title: str = ""
    recent_tool_results: list[ToolResult] = field(default_factory=list)
    relevant_memories: list[dict[str, Any]] = field(default_factory=list)
    screen_summary: str | None = None
    pending_permission: dict[str, Any] | None = None

    def get_prompt_context(self, max_history_turns: int = 4) -> list[dict[str, str]]:
        """Return selective, token-efficient context messages for LLM reasoning."""
        context_messages: list[dict[str, str]] = []

        # System background context
        context_lines: list[str] = []
        if self.active_application or self.active_window_title:
            context_lines.append(f"Active App: {self.active_application} (Window: '{self.active_window_title}')")
        if self.screen_summary:
            context_lines.append(f"Screen: {self.screen_summary}")
        if self.relevant_memories:
            mem_str = "; ".join([f"{m.get('key', '')}: {m.get('value', '')}" for m in self.relevant_memories[:3]])
            context_lines.append(f"User Knowledge: {mem_str}")

        if context_lines:
            context_messages.append({
                "role": "system",
                "content": f"[Desktop Environment Context]\n" + "\n".join(context_lines),
            })

        # Recent conversation history
        sliced_history = self.conversation_history[-(max_history_turns * 2) :]
        context_messages.extend(sliced_history)
        return context_messages
