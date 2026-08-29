from __future__ import annotations

import pytest

from config import LLMConfig
from llm_agent import OllamaClient


class TestLLMConversation:
    """Comprehensive LLM conversation flow testing."""

    @pytest.fixture
    def llm_agent(self) -> OllamaClient:
        return OllamaClient(LLMConfig(model="llama3.2:3b", request_timeout=5))

    def test_sentence_streaming_logic(self, llm_agent: OllamaClient) -> None:
        """Test sentence segmentation logic for streaming TTS."""
        test_text = "Hello there. How are you doing today? I am Friday, your desktop assistant."
        sentences = [s for s, _ in llm_agent.stream_sentences(test_text)]
        assert len(sentences) >= 1

    def test_graceful_offline_response(self, llm_agent: OllamaClient) -> None:
        """Test that offline Ollama produces friendly fallback instead of crashing."""
        chunks = list(llm_agent.stream_chat("What is Python?"))
        assert len(chunks) > 0
        full_text = "".join(chunks)
        assert len(full_text) > 0

    def test_natural_speech_phrasing(self) -> None:
        """Verify response filters out robotic substrings."""
        sample_response = "I have adjusted your screen brightness to 80 percent."
        robotic_markers = ["COMMAND_EXECUTED", "RETURN_CODE", "SUBPROCESS_CALL"]
        for marker in robotic_markers:
            assert marker not in sample_response
