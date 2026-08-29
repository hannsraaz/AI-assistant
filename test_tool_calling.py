from __future__ import annotations

import pytest

from config import DesktopConfig
from desktop_controller import DesktopController
from intent_router import IntentRouter, IntentResult
from config import AppConfig


class TestToolCalling:
    """Test desktop tool calling and action routing."""

    @pytest.fixture
    def controller(self) -> DesktopController:
        return DesktopController(DesktopConfig())

    @pytest.fixture
    def router(self, controller: DesktopController) -> IntentRouter:
        config = AppConfig(desktop=DesktopConfig())
        return IntentRouter(config=config, desktop=controller)

    def test_volume_tool_execution(self, controller: DesktopController) -> None:
        """Test setting volume levels."""
        res = controller.set_volume(45)
        assert "45" in res
        assert abs(controller.get_volume() - 45) <= 5

    def test_mute_unmute_tool_execution(self, controller: DesktopController) -> None:
        """Test mute and unmute actions."""
        mute_res = controller.mute()
        assert "muted" in mute_res.lower()
        unmute_res = controller.unmute()
        assert "unmuted" in unmute_res.lower()

    def test_system_diagnostics_tool(self, controller: DesktopController) -> None:
        """Test fetching CPU, RAM, and Battery stats."""
        status = controller.get_system_status()
        assert "CPU" in status
        assert "RAM" in status

    def test_router_fast_dispatch(self, router: IntentRouter) -> None:
        """Test that intent router matches voice queries to tools."""
        res = router.route("set volume to 60 percent")
        assert res.handled is True
        assert "60" in res.response

        time_res = router.route("what time is it")
        assert time_res.handled is True
        assert "It is" in time_res.response

        date_res = router.route("what is today's date")
        assert date_res.handled is True
        assert "Today is" in date_res.response
