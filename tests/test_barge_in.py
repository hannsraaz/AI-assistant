from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from assistant_core import AssistantState, VoiceAssistant
from config import AppConfig


class TestBargeIn:
    def test_barge_in_stops_tts_and_resets_state(self) -> None:
        config = AppConfig()
        assistant = VoiceAssistant(config=config)
        assistant._running.set()

        # Mock TTS to appear busy
        mock_tts = MagicMock()
        mock_tts.is_busy.return_value = True
        assistant.tts = mock_tts

        assistant._state = AssistantState.SPEAKING
        assistant._processing.set()

        # Trigger barge-in
        assistant.barge_in()

        assert not assistant._processing.is_set()
        assert assistant._cancellation_token.is_set()
        assert mock_tts.stop.called
        assert assistant._state == AssistantState.INTERRUPTED

    def test_wake_word_during_speech_triggers_barge_in(self) -> None:
        config = AppConfig()
        assistant = VoiceAssistant(config=config)
        assistant._running.set()

        mock_tts = MagicMock()
        mock_tts.is_busy.return_value = True
        assistant.tts = mock_tts

        assistant._state = AssistantState.SPEAKING
        assistant._processing.set()

        # Wake word triggers
        assistant._on_wake_word()

        assert mock_tts.stop.called
        assert assistant._cancellation_token.is_set()
