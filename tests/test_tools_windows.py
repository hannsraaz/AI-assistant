from __future__ import annotations

import pytest

from core.tools.registry import ToolRegistry
from core.tools.windows import register_windows_tools


@pytest.fixture
def registry() -> ToolRegistry:
    reg = ToolRegistry()
    register_windows_tools(reg)
    return reg


def test_windows_list_tool(registry: ToolRegistry) -> None:
    res = registry.execute("windows.list")
    assert res.success is True
    assert "windows" in res.data
    assert "count" in res.data
    assert isinstance(res.data["windows"], list)


def test_windows_show_desktop(registry: ToolRegistry) -> None:
    res = registry.execute("windows.show_desktop")
    assert res.success is True
    assert "desktop" in res.message.lower()
