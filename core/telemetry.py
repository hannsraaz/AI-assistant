from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("friday.telemetry")


@dataclass
class TurnTelemetry:
    """High-resolution monotonic timing telemetry for an assistant turn."""

    turn_id: str
    query: str = ""
    path_taken: str = "fast_path"  # 'fast_path' or 'llm_agent'

    # Monotonic timestamps (seconds)
    t_wake_detected: float = 0.0
    t_listen_start: float = 0.0
    t_speech_start: float = 0.0
    t_speech_end: float = 0.0
    t_stt_start: float = 0.0
    t_stt_complete: float = 0.0
    t_router_start: float = 0.0
    t_router_complete: float = 0.0
    t_tool_start: float = 0.0
    t_tool_complete: float = 0.0
    t_llm_start: float = 0.0
    t_llm_first_token: float = 0.0
    t_llm_complete: float = 0.0
    t_tts_start: float = 0.0
    t_tts_first_audio: float = 0.0
    t_playback_complete: float = 0.0

    # Calculated durations in milliseconds
    wake_latency_ms: float = 0.0
    stt_duration_ms: float = 0.0
    router_duration_ms: float = 0.0
    tool_duration_ms: float = 0.0
    llm_first_token_ms: float = 0.0
    llm_total_ms: float = 0.0
    tts_first_audio_ms: float = 0.0
    speech_end_to_first_audio_ms: float = 0.0  # Crucial metric: Speech End -> First Sound
    total_latency_ms: float = 0.0

    def compute_metrics(self) -> None:
        """Compute all relative duration metrics."""
        if self.t_stt_complete > 0 and self.t_stt_start > 0:
            self.stt_duration_ms = (self.t_stt_complete - self.t_stt_start) * 1000.0
        if self.t_router_complete > 0 and self.t_router_start > 0:
            self.router_duration_ms = (self.t_router_complete - self.t_router_start) * 1000.0
        if self.t_tool_complete > 0 and self.t_tool_start > 0:
            self.tool_duration_ms = (self.t_tool_complete - self.t_tool_start) * 1000.0
        if self.t_llm_first_token > 0 and self.t_llm_start > 0:
            self.llm_first_token_ms = (self.t_llm_first_token - self.t_llm_start) * 1000.0
        if self.t_llm_complete > 0 and self.t_llm_start > 0:
            self.llm_total_ms = (self.t_llm_complete - self.t_llm_start) * 1000.0
        if self.t_tts_first_audio > 0 and self.t_tts_start > 0:
            self.tts_first_audio_ms = (self.t_tts_first_audio - self.t_tts_start) * 1000.0

        # Critical User-Perceived Latency: Speech End -> First Audible Sound
        if self.t_tts_first_audio > 0 and self.t_speech_end > 0:
            self.speech_end_to_first_audio_ms = (self.t_tts_first_audio - self.t_speech_end) * 1000.0
        elif self.t_tts_first_audio > 0 and self.t_stt_complete > 0:
            self.speech_end_to_first_audio_ms = (self.t_tts_first_audio - self.t_stt_complete) * 1000.0

        # Total turn time
        start_anchor = self.t_wake_detected or self.t_stt_start or self.t_router_start
        end_anchor = self.t_playback_complete or self.t_tts_first_audio or self.t_tool_complete or time.perf_counter()
        if end_anchor > start_anchor > 0:
            self.total_latency_ms = (end_anchor - start_anchor) * 1000.0

    def summary(self) -> str:
        self.compute_metrics()
        return (
            f"[{self.path_taken.upper()}] Speech-to-Audio: {self.speech_end_to_first_audio_ms:.1f}ms | "
            f"STT: {self.stt_duration_ms:.1f}ms | Router: {self.router_duration_ms:.2f}ms | "
            f"Tool: {self.tool_duration_ms:.1f}ms | LLM TTFT: {self.llm_first_token_ms:.1f}ms | "
            f"TTS Gen: {self.tts_first_audio_ms:.1f}ms | Total: {self.total_latency_ms:.1f}ms"
        )


class TelemetryTracker:
    """Tracks latency metrics across voice, routing, agent planning, and speech generation."""

    def __init__(self) -> None:
        self._history: list[TurnTelemetry] = []

    def record_turn(self, telemetry: TurnTelemetry) -> None:
        telemetry.compute_metrics()
        self._history.append(telemetry)
        if len(self._history) > 100:
            self._history.pop(0)
        logger.info(telemetry.summary())

    def get_latest(self) -> TurnTelemetry | None:
        return self._history[-1] if self._history else None

    def get_recent_metrics(self) -> list[dict[str, Any]]:
        return [
            {
                "query": t.query,
                "path": t.path_taken,
                "speech_to_audio_ms": round(t.speech_end_to_first_audio_ms, 1),
                "total_ms": round(t.total_latency_ms, 1),
                "stt_ms": round(t.stt_duration_ms, 1),
                "router_ms": round(t.router_duration_ms, 2),
                "tool_ms": round(t.tool_duration_ms, 1),
                "tts_ms": round(t.tts_first_audio_ms, 1),
            }
            for t in self._history[-10:]
        ]


global_telemetry = TelemetryTracker()
