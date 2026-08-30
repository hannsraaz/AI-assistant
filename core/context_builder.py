from __future__ import annotations

import logging
import re
from typing import Any

from core.memory.memory_manager import MemoryManager

logger = logging.getLogger("context_builder")


class ContextBuilder:
    """Selectively builds compact, token-bounded, privacy-sanitized context

    combining desktop state, active windows, and relevant memory facts for LLM queries.
    """

    REDACTION_PATTERNS = (
        (r"(?i)\b(password|passwd|secret|api_key|apikey|token)\s*[:=]\s*\S+", r"\1: [REDACTED]"),
        (r"ghp_[0-9a-zA-Z]{30,}", "[REDACTED_GITHUB_TOKEN]"),
        (r"sk-[0-9a-zA-Z]{20,}", "[REDACTED_API_KEY]"),
        (r"(?i)bearer\s+[0-9a-zA-Z._-]+", "Bearer [REDACTED_TOKEN]"),
    )

    def __init__(self, memory_manager: MemoryManager | None = None) -> None:
        self.memory = memory_manager

    def sanitize_text(self, text: str) -> str:
        """Sanitize sensitive credentials and tokens from prompt text."""
        sanitized = text
        for pattern, replacement in self.REDACTION_PATTERNS:
            sanitized = re.sub(pattern, replacement, sanitized)
        return sanitized

    def build_system_context(
        self,
        query: str,
        active_window_title: str = "",
        max_facts: int = 4,
    ) -> str:
        """Assemble relevant semantic memory facts and desktop state."""
        context_parts: list[str] = []

        # 1. Active Window State
        if active_window_title.strip():
            clean_title = self.sanitize_text(active_window_title.strip())
            context_parts.append(f"Active Window: {clean_title}")

        # 2. Relevant Facts from Memory
        if self.memory:
            relevant_memories = self.memory.recall(query)
            if relevant_memories:
                facts = [f"- {m['key']}: {m['value']}" for m in relevant_memories[:max_facts]]
                context_parts.append("Known Facts:\n" + "\n".join(facts))

        if not context_parts:
            return ""

        return "\n\n[Current Environment & Knowledge]\n" + "\n".join(context_parts)
