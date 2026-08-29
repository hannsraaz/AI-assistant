from __future__ import annotations

import pytest

from core.tools.registry import ToolRegistry
from core.tools.windows import register_windows_tools


@pytest.fixture
def registry() -> ToolRegistry:
    reg = ToolRegistry()
    register_windows_tools(reg)
    return reg


def test_clipboard_lifecycle(registry: ToolRegistry) -> None:
    # 1. Write to clipboard
    write_res = registry.execute("clipboard.write", text="Friday Mark 2 Test String")
    assert write_res.success is True

    # 2. Read from clipboard
    read_res = registry.execute("clipboard.read")
    assert read_res.success is True
    assert "Friday Mark 2 Test String" in read_res.data["text"]

    # 3. Clear clipboard
    clear_res = registry.execute("clipboard.clear")
    assert clear_res.success is True

    # 4. Read empty clipboard
    empty_res = registry.execute("clipboard.read")
    assert empty_res.success is True
    assert empty_res.data["text"] == ""
