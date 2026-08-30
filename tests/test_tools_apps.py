from __future__ import annotations

import pytest

from core.tools.registry import ToolRegistry
from core.tools.windows import register_windows_tools
from core.tools.windows.apps import AppDiscovery


@pytest.fixture
def registry() -> ToolRegistry:
    reg = ToolRegistry()
    register_windows_tools(reg)
    return reg


def test_app_discovery_cache() -> None:
    apps = AppDiscovery.get_installed_apps()
    assert isinstance(apps, dict)
    assert len(apps) > 0
    assert "calc" in apps or "notepad" in apps or "cmd" in apps


def test_apps_list_tool(registry: ToolRegistry) -> None:
    res = registry.execute("apps.list")
    assert res.success is True
    assert "apps" in res.data
    assert "count" in res.data


def test_apps_find_tool(registry: ToolRegistry) -> None:
    res = registry.execute("apps.find", query="notepad")
    assert res.success is True
    assert "path" in res.data


def test_apps_open_tool(registry: ToolRegistry) -> None:
    # Test standard execution with app_name
    res = registry.execute("apps.open", app_name="calc")
    assert res.success is True

    # Test alias execution with target
    res_alias = registry.execute("apps.open", target="calc")
    assert res_alias.success is True

