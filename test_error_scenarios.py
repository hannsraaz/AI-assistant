from __future__ import annotations

import logging
from unittest.mock import patch

import pytest

from assistant_core import VoiceAssistant
from config import AppConfig


class TestErrorResilience:
    """Test Friday resilience under error and boundary conditions."""

    @pytest.fixture
    def assistant(self) -> VoiceAssistant:
        config = AppConfig()
        config.speak_responses = False
        logger = logging.getLogger("test_resilience")
        return VoiceAssistant(config=config, logger=logger)

    def test_ollama_timeout_resilience(self, assistant: VoiceAssistant) -> None:
        """Test graceful recovery if LLM raises an error."""
        with patch.object(assistant.llm.session, "post", side_effect=TimeoutError("Ollama Timeout")):
            chunks = list(assistant.llm.stream_chat("Explain astronomy"))
            assert len(chunks) > 0
            # Should not crash

    def test_audio_stt_empty_recording(self, assistant: VoiceAssistant) -> None:
        """Test STT when recording is empty / silence."""
        with patch.object(assistant.stt, "_record_in_memory", return_value=None):
            transcript = assistant.stt.listen_once()
            assert transcript == ""

    def test_permission_denied_power_commands(self, assistant: VoiceAssistant) -> None:
        """Test that destructive power commands are guarded when disabled."""
        assistant.config.desktop.allow_power_commands = False
        res = assistant.desktop.shutdown(restart=False)
        assert "disabled" in res.lower()

    def test_tts_playback_device_error(self, assistant: VoiceAssistant) -> None:
        """Test TTS recovery when audio device throws an error."""
        with patch("sounddevice.play", side_effect=RuntimeError("Audio Device Lost")):
            # Should not raise exception
            try:
                assistant.tts.speak("Testing fallback recovery")
            except Exception as exc:
                pytest.fail(f"TTS crashed on audio device error: {exc}")
