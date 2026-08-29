from __future__ import annotations

import pytest
from intent_router import IntentRouter


class TestIntentRouter:
    """Test suite for fast-path regex intent router."""

    def test_volume_intent_matching(self, intent_router: IntentRouter) -> None:
        res1 = intent_router.route("set volume to 75 percent")
        assert res1.handled is True
        assert "75" in res1.response

        res2 = intent_router.route("mute")
        assert res2.handled is True

        res3 = intent_router.route("unmute")
        assert res3.handled is True

    def test_time_and_date_matching(self, intent_router: IntentRouter) -> None:
        time_res = intent_router.route("what time is it")
        assert time_res.handled is True
        assert "It is" in time_res.response

        date_res = intent_router.route("tell me today's date")
        assert date_res.handled is True
        assert "Today is" in date_res.response

    def test_system_status_matching(self, intent_router: IntentRouter) -> None:
        res = intent_router.route("system status")
        assert res.handled is True
        assert "CPU" in res.response

    def test_timer_matching(self, intent_router: IntentRouter) -> None:
        res = intent_router.route("set a timer for 5 seconds")
        assert res.handled is True
        assert "Timer set" in res.response

    def test_unhandled_routes_to_llm(self, intent_router: IntentRouter) -> None:
        res = intent_router.route("Explain the theory of relativity")
        assert res.handled is False
