from __future__ import annotations

import time
import pytest

from assistant_core import AssistantState, VoiceAssistant
from config import AppConfig


def test_stop_restart_lifecycle() -> None:
    config = AppConfig()
    config.wake_word.enabled = False
    config.speak_responses = False

    assistant = VoiceAssistant(config=config)

    # 1. Start assistant
    assistant.start()
    assert assistant._running.is_set()
    assert not assistant._cancellation_token.is_set()

    # 2. Cancel a turn
    assistant.cancel()
    assert assistant._cancellation_token.is_set()

    # 3. Handle query after cancellation
    resp1 = assistant.handle_query("time")
    assert len(resp1) > 0
    assert not assistant._cancellation_token.is_set()

    # 4. Stop assistant completely
    assistant.stop()
    assert not assistant._running.is_set()

    # 5. Restart assistant
    assistant.start()
    assert assistant._running.is_set()
    assert not assistant._cancellation_token.is_set()

    # 6. Verify query works after complete restart
    resp2 = assistant.handle_query("date")
    assert len(resp2) > 0

    assistant.stop()
