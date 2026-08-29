from __future__ import annotations

import pytest

from core.tools.base import RiskLevel
from core.tools.registry import ToolRegistry
from core.tools.windows import register_windows_tools


@pytest.fixture
def registry() -> ToolRegistry:
    reg = ToolRegistry()
    register_windows_tools(reg)
    return reg


def test_system_volume_tools(registry: ToolRegistry) -> None:
    # Set volume
    res_set = registry.execute("system.volume.set", percentage=42)
    assert res_set.success is True
    assert res_set.data["volume"] == 42

    # Get volume
    res_get = registry.execute("system.volume.get")
    assert res_get.success is True
    assert "volume" in res_get.data

    # Volume up
    res_up = registry.execute("system.volume.up", delta=5)
    assert res_up.success is True
    assert res_up.data["volume"] >= 42

    # Mute and Unmute
    res_mute = registry.execute("system.volume.mute")
    assert res_mute.success is True
    assert res_mute.data["muted"] is True

    res_unmute = registry.execute("system.volume.unmute")
    assert res_unmute.success is True
    assert res_unmute.data["muted"] is False


def test_system_brightness_tools(registry: ToolRegistry) -> None:
    res_get = registry.execute("system.brightness.get")
    assert res_get.success is True
    assert "brightness" in res_get.data

    res_set = registry.execute("system.brightness.set", level=80)
    assert res_set.success is True
    assert res_set.data["brightness"] == 80


def test_system_diagnostics_tools(registry: ToolRegistry) -> None:
    # CPU
    cpu_res = registry.execute("system.cpu")
    assert cpu_res.success is True
    assert "cpu_percent" in cpu_res.data

    # RAM
    ram_res = registry.execute("system.ram")
    assert ram_res.success is True
    assert "percent" in ram_res.data
    assert "used_gb" in ram_res.data

    # Disk
    disk_res = registry.execute("system.disk")
    assert disk_res.success is True
    assert "free_gb" in disk_res.data

    # Battery
    bat_res = registry.execute("system.battery")
    assert bat_res.success is True
    assert "has_battery" in bat_res.data

    # Network
    net_res = registry.execute("system.network")
    assert net_res.success is True
    assert "mb_sent" in net_res.data
