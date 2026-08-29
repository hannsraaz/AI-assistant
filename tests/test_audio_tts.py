from __future__ import annotations

import pytest
from audio_tts import TextToSpeechService
from config import TTSConfig


class TestAudioTTS:
    """Test suite for Text-to-Speech service."""

    @pytest.fixture
    def tts_service(self) -> TextToSpeechService:
        return TextToSpeechService(TTSConfig(backend="piper"))

    def test_sentence_splitting(self, tts_service: TextToSpeechService) -> None:
        text = "Hello world! How are you today? This is Friday speaking."
        sentences = tts_service.split_sentences(text)
        assert len(sentences) == 3
        assert sentences[0] == "Hello world!"
        assert sentences[1] == "How are you today?"
        assert sentences[2] == "This is Friday speaking."

    def test_empty_string_handling(self, tts_service: TextToSpeechService) -> None:
        sentences = tts_service.split_sentences("   ")
        assert len(sentences) == 0

    def test_stop_clears_state(self, tts_service: TextToSpeechService) -> None:
        tts_service.stop()
        assert tts_service.is_busy() is False
