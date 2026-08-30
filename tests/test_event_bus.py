from __future__ import annotations

import time
import pytest
from core.event_bus import Event, EventBus


class TestEventBus:
    def test_publish_and_subscribe(self) -> None:
        bus = EventBus()
        bus.start()

        received = []

        def _handler(evt: Event) -> None:
            received.append(evt)

        bus.subscribe("assistant.state_change", _handler)
        bus.publish("assistant.state_change", {"state": "speaking", "status": "talking"})

        time.sleep(0.15)
        assert len(received) == 1
        assert received[0].topic == "assistant.state_change"
        assert received[0].payload["state"] == "speaking"

        bus.stop()

    def test_wildcard_subscriber(self) -> None:
        bus = EventBus()
        bus.start()

        all_events = []

        def _all_handler(evt: Event) -> None:
            all_events.append(evt.topic)

        bus.subscribe("*", _all_handler)
        bus.publish("topic.a", {"val": 1})
        bus.publish("topic.b", {"val": 2})

        time.sleep(0.15)
        assert "topic.a" in all_events
        assert "topic.b" in all_events

        bus.stop()
