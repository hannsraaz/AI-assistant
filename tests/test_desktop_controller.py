from __future__ import annotations

import pytest
from desktop_controller import DesktopController


class TestDesktopController:
    """Test suite for DesktopController actions and metrics."""

    def test_volume_clamping_and_get(self, desktop_controller: DesktopController) -> None:
        desktop_controller.set_volume(50)
        vol = desktop_controller.get_volume()
        assert 0 <= vol <= 100

        # Boundary checks
        desktop_controller.set_volume(150)
        assert desktop_controller.get_volume() <= 100

        desktop_controller.set_volume(-50)
        assert desktop_controller.get_volume() >= 0

    def test_mute_and_unmute(self, desktop_controller: DesktopController) -> None:
        mute_res = desktop_controller.mute()
        assert "muted" in mute_res.lower()

        unmute_res = desktop_controller.unmute()
        assert "unmuted" in unmute_res.lower()

    def test_system_stats(self, desktop_controller: DesktopController) -> None:
        status = desktop_controller.get_system_status()
        assert "CPU" in status
        assert "RAM" in status

        battery = desktop_controller.get_battery_info()
        assert isinstance(battery, str)
        assert len(battery) > 0

        disk = desktop_controller.get_disk_info()
        assert "GB" in disk

    def test_notes_crud(self, desktop_controller: DesktopController) -> None:
        add_res = desktop_controller.add_note("pytest note test item")
        assert "Saved note" in add_res

        read_res = desktop_controller.read_notes()
        assert "pytest note test item" in read_res
