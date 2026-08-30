from __future__ import annotations

import base64
import json
import pytest

from core.voice.gemini_live_adapter import GeminiLiveAdapter
from core.voice.prosody_engine import DialogueEmotion, ProsodyEngine, global_prosody_engine


class TestProsodyEngine:
    def test_emotion_detection(self) -> None:
        engine = ProsodyEngine()
        assert engine.detect_emotion("Kya tum mere files search kar sakte ho?") == DialogueEmotion.CURIOUS
        assert engine.detect_emotion("VS Code khol raha hoon") == DialogueEmotion.CONFIDENT
        assert engine.detect_emotion("Shandaar kaam kiya!") == DialogueEmotion.EXCITED
        assert engine.detect_emotion("Ruko, ye command dangerous hai") == DialogueEmotion.URGENT
        assert engine.detect_emotion("Maaf karna, internet connect nahi hua") == DialogueEmotion.EMPATHETIC
        assert engine.detect_emotion("Battery 85 percent hai") == DialogueEmotion.NEUTRAL

    def test_discourse_marker_injection(self) -> None:
        engine = ProsodyEngine()
        # Hinglish action acknowledgement
        assert engine.add_conversational_discourse_markers("VS Code open kar raha hoon", is_hinglish=True).startswith("Haan, ")
        # Hinglish info explanation
        assert engine.add_conversational_discourse_markers("battery 85 percent bata raha hoon", is_hinglish=True).startswith("Dekho, ")
        # English action
        assert engine.add_conversational_discourse_markers("Opening Visual Studio Code", is_hinglish=False).startswith("Sure, ")
        # Already starts with conversational token
        assert engine.add_conversational_discourse_markers("Haan, ho gaya", is_hinglish=True) == "Haan, ho gaya"

    def test_prosody_segmentation(self) -> None:
        engine = ProsodyEngine()
        text = "Haan, VS Code open kar diya hai. Ab batao, kya main tests run karoon?"
        segments = engine.segment_speech_with_prosody(text, is_hinglish=True)

        assert len(segments) >= 2
        # Question segment should have positive pitch offset
        q_seg = [s for s in segments if "?" in s.text]
        assert len(q_seg) > 0
        assert q_seg[0].pitch_offset > 0

    def test_markdown_and_code_sanitization(self) -> None:
        engine = ProsodyEngine()
        dirty = "Check this path: `C:\\Users\\admin\\file.txt` and run **pytest** on ```python\nprint('hello')\n```"
        clean = engine._clean_for_speech(dirty)
        assert "```" not in clean
        assert "**" not in clean
        assert "`" not in clean


class TestGeminiLiveAdapter:
    def test_setup_message_building(self) -> None:
        adapter = GeminiLiveAdapter(api_key="test_key", voice_name="Puck")
        tools_schema = [
            {
                "name": "system_volume_set",
                "description": "Set system volume",
                "parameters": {"type": "object", "properties": {"percentage": {"type": "integer"}}},
            }
        ]
        msg = adapter.build_setup_message(tools_schema=tools_schema)
        assert msg["setup"]["model"] == "models/gemini-2.0-flash-exp"
        assert msg["setup"]["generation_config"]["speech_config"]["voice_config"]["prebuilt_voice_config"]["voice_name"] == "Puck"
        assert len(msg["setup"]["tools"][0]["function_declarations"]) == 1

    def test_audio_chunk_message_formatting(self) -> None:
        adapter = GeminiLiveAdapter(api_key="test_key")
        pcm_bytes = b"\x00\x00\x01\x00" * 100
        msg = adapter.format_audio_chunk_message(pcm_bytes)
        assert msg["realtime_input"]["media_chunks"][0]["mime_type"] == "audio/pcm;rate=16000"
        decoded = base64.b64decode(msg["realtime_input"]["media_chunks"][0]["data"])
        assert decoded == pcm_bytes

    def test_parse_server_audio_and_tools(self) -> None:
        adapter = GeminiLiveAdapter(api_key="test_key")
        dummy_audio = b"\x12\x34\x56\x78" * 50
        server_payload = {
            "serverContent": {
                "modelTurn": {
                    "parts": [
                        {"text": "Haan, "},
                        {"inlineData": {"mimeType": "audio/pcm;rate=24000", "data": base64.b64encode(dummy_audio).decode("utf-8")}},
                    ]
                },
                "turnComplete": True,
            },
            "toolCall": {
                "functionCalls": [
                    {
                        "id": "call_123",
                        "name": "windows_app_launch",
                        "args": {"app_name": "code"},
                    }
                ]
            },
        }
        parsed = adapter.parse_server_message(server_payload)
        assert parsed["transcript"] == "Haan, "
        assert parsed["audio_pcm_24k"] == dummy_audio
        assert parsed["turn_complete"] is True
        assert len(parsed["tool_calls"]) == 1
        assert parsed["tool_calls"][0]["name"] == "windows_app_launch"
