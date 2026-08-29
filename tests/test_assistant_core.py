from __future__ import annotations

import logging
import pytest
from assistant_core import VoiceAssistant
from config import AppConfig


class TestAssistantCore:
    """Test suite for VoiceAssistant coordinator."""

    @pytest.fixture
    def assistant(self) -> VoiceAssistant:
        config = AppConfig()
        config.speak_responses = False
        config.wake_word.enabled = False
        logger = logging.getLogger("test_core")
        return VoiceAssistant(config=config, logger=logger)

    def test_lifecycle_start_stop(self, assistant: VoiceAssistant) -> None:
        assistant.start()
        assert assistant._running.is_set() is True
        assistant.stop()
        assert assistant._running.is_set() is False

    def test_cancel_execution(self, assistant: VoiceAssistant) -> None:
        assistant.cancel()
        assert assistant._processing.is_set() is False
