from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from core.context_builder import ContextBuilder
from core.memory.memory_manager import MemoryManager


class TestContextBuilder:
    def test_credential_sanitization(self) -> None:
        cb = ContextBuilder()
        raw = "User password: MySecretPassword123 and ghp_abcdefghijklmnopqrstuvwxyz1234567890"
        sanitized = cb.sanitize_text(raw)
        assert "MySecretPassword123" not in sanitized
        assert "[REDACTED]" in sanitized
        assert "ghp_abcdef" not in sanitized

    def test_build_system_context(self, tmp_path) -> None:
        mem_file = tmp_path / "test_mem.json"
        mem = MemoryManager(memory_file=mem_file)
        mem.remember("favorite editor", "VS Code")
        mem.remember("current project", "Friday V4")

        cb = ContextBuilder(memory_manager=mem)
        ctx = cb.build_system_context("what is my current project?", active_window_title="Visual Studio Code - Friday V4")

        assert "Active Window: Visual Studio Code - Friday V4" in ctx
        assert "Friday V4" in ctx
