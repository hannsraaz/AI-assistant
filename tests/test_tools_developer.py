from __future__ import annotations

import pytest

from core.tools.developer import register_developer_tools
from core.tools.registry import ToolRegistry


@pytest.fixture
def dev_registry() -> ToolRegistry:
    reg = ToolRegistry()
    register_developer_tools(reg)
    return reg


def test_terminal_execute_safe_command(dev_registry: ToolRegistry) -> None:
    res = dev_registry.execute("terminal.execute", command="python --version")
    assert res.success is True
    assert "Python" in res.data["stdout"] or "Python" in res.data["stderr"] or "Python" in res.data["output"]


def test_terminal_blocked_destructive_command(dev_registry: ToolRegistry) -> None:
    res = dev_registry.execute("terminal.execute", command="rmdir /s /q C:\\Windows")
    assert res.success is False
    assert "Blocked high-risk" in res.get_error_message()
    assert res.get_error_code() == "HIGH_RISK_BLOCKED"


def test_git_status_tool(dev_registry: ToolRegistry) -> None:
    res = dev_registry.execute("git.status")
    assert res.success is True
    assert "status" in res.data


def test_git_log_tool(dev_registry: ToolRegistry) -> None:
    res = dev_registry.execute("git.log", max_count=3)
    assert res.success is True
    assert "commits" in res.data


def test_android_devices_tool(dev_registry: ToolRegistry) -> None:
    res = dev_registry.execute("android.devices")
    assert res.success is True
    assert "devices" in res.data
