from __future__ import annotations

import asyncio
import base64
import json
import logging
import threading
from collections.abc import Callable
from typing import Any

logger = logging.getLogger("friday.voice.gemini_live")

# Gemini 2.0 Flash Multimodal Live Endpoint
GEMINI_LIVE_WS_URL = (
    "wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent"
)


class GeminiLiveAdapter:
    """High-Performance Bidirectional Streaming Client for Google Gemini 2.0 Flash Multimodal Live API.

    Implements:
    1. Full-duplex WebSocket communication (16kHz PCM In -> 24kHz PCM Out).
    2. Zero-latency Speech-to-Speech audio streaming with native barge-in.
    3. In-line tool calling bridge connecting Gemini to FRIDAY's local ToolRegistry.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str = "models/gemini-2.0-flash-exp",
        voice_name: str = "Puck",  # Options: Aoede, Charon, Fenrir, Kore, Puck
        on_audio_chunk: Callable[[bytes], None] | None = None,
        on_transcript_chunk: Callable[[str], None] | None = None,
        on_tool_call: Callable[[str, dict[str, Any]], Any] | None = None,
    ) -> None:
        self.api_key = api_key or ""
        self.model_name = model_name
        self.voice_name = voice_name
        self.on_audio_chunk = on_audio_chunk
        self.on_transcript_chunk = on_transcript_chunk
        self.on_tool_call = on_tool_call

        self._ws: Any = None
        self._connected = threading.Event()
        self._stop_event = threading.Event()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None

    @property
    def is_connected(self) -> bool:
        return self._connected.is_set()

    def build_setup_message(self, tools_schema: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        """Construct the initial bidirectional handshake payload."""
        setup: dict[str, Any] = {
            "setup": {
                "model": self.model_name,
                "generation_config": {
                    "response_modalities": ["AUDIO"],
                    "speech_config": {
                        "voice_config": {
                            "prebuilt_voice_config": {
                                "voice_name": self.voice_name
                            }
                        }
                    },
                },
            }
        }
        if tools_schema:
            setup["setup"]["tools"] = [{"function_declarations": tools_schema}]
        return setup

    def format_audio_chunk_message(self, pcm_bytes: bytes) -> dict[str, Any]:
        """Wrap raw 16kHz 16-bit mono PCM into base64 realtimeInput payload."""
        b64_data = base64.b64encode(pcm_bytes).decode("utf-8")
        return {
            "realtime_input": {
                "media_chunks": [
                    {
                        "mime_type": "audio/pcm;rate=16000",
                        "data": b64_data,
                    }
                ]
            }
        }

    def format_tool_response_message(self, call_id: str, tool_name: str, result_data: dict[str, Any]) -> dict[str, Any]:
        """Send local tool execution results back to Gemini Live."""
        return {
            "tool_response": {
                "function_responses": [
                    {
                        "response": {"output": result_data},
                        "id": call_id,
                    }
                ]
            }
        }

    def parse_server_message(self, raw_json: str | dict[str, Any]) -> dict[str, Any]:
        """Parse incoming server event into structured audio/text/tool payloads."""
        msg = raw_json if isinstance(raw_json, dict) else json.loads(raw_json)
        result: dict[str, Any] = {
            "audio_pcm_24k": b"",
            "transcript": "",
            "tool_calls": [],
            "turn_complete": False,
            "interrupted": False,
        }

        # Server Content (Model Turn)
        server_content = msg.get("serverContent", {})
        if "modelTurn" in server_content:
            parts = server_content["modelTurn"].get("parts", [])
            for part in parts:
                # 24kHz Audio Output
                if "inlineData" in part:
                    data_b64 = part["inlineData"].get("data", "")
                    if data_b64:
                        result["audio_pcm_24k"] += base64.b64decode(data_b64)

                # Text/Transcript chunk
                if "text" in part:
                    result["transcript"] += part["text"]

        if server_content.get("turnComplete"):
            result["turn_complete"] = True

        if server_content.get("interrupted"):
            result["interrupted"] = True

        # Tool Call Requests
        tool_call_obj = msg.get("toolCall", {})
        if "functionCalls" in tool_call_obj:
            for call in tool_call_obj["functionCalls"]:
                result["tool_calls"].append({
                    "id": call.get("id", ""),
                    "name": call.get("name", ""),
                    "args": call.get("args", {}),
                })

        return result
