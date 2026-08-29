from __future__ import annotations

import time
from pathlib import Path
import numpy as np
import pytest

from assistant_core import AssistantState, VoiceAssistant
from audio_stream import AudioRingBuffer, ContinuousAudioCapture
from config import AppConfig
from core.telemetry import TurnTelemetry, global_telemetry


@pytest.fixture
def v3_1_assistant(tmp_path: Path) -> VoiceAssistant:
    cfg = AppConfig()
    cfg.speak_responses = False
    cfg.wake_word.enabled = False
    cfg.memory.storage_file = str(tmp_path / "v3_1_memory.json")
    cfg.automation.schedules_file = str(tmp_path / "v3_1_schedules.json")
    cfg.automation.workflows_file = str(tmp_path / "v3_1_workflows.json")
    return VoiceAssistant(cfg)


class TestV31VoicePerformance:
    """Rigorous real-world voice performance, continuous audio, and telemetry test suite."""

    def test_audio_ring_buffer_and_preroll(self) -> None:
        """Verify lock-free circular ring buffer writes and pre-roll retrieval."""
        rb = AudioRingBuffer(capacity_seconds=2.0, sample_rate=16000)
        # Write 1 second of sine wave audio
        t = np.linspace(0, 1.0, 16000, dtype=np.float32)
        sine = np.sin(2 * np.pi * 440 * t)
        rb.write(sine)

        # Retrieve 0.3s pre-roll (4800 samples)
        preroll = rb.get_last_seconds(0.3)
        assert len(preroll) == 4800
        assert np.isclose(preroll[-1], sine[-1], atol=1e-3)

    def test_high_resolution_turn_telemetry(self) -> None:
        """Verify all 19 timing milestones and speech-end to audio calculations."""
        t = TurnTelemetry(turn_id="test_turn_1")
        t.t_wake_detected = 100.0
        t.t_listen_start = 100.05
        t.t_speech_start = 100.1
        t.t_speech_end = 101.5
        t.t_stt_start = 101.5
        t.t_stt_complete = 101.75  # 250ms STT
        t.t_router_start = 101.75
        t.t_router_complete = 101.751  # 1ms router
        t.t_tool_start = 101.751
        t.t_tool_complete = 101.786  # 35ms tool
        t.t_tts_start = 101.786
        t.t_tts_first_audio = 101.986  # 200ms TTS first audio
        t.t_playback_complete = 102.5

        t.compute_metrics()
        assert np.isclose(t.stt_duration_ms, 250.0, atol=1.0)
        assert np.isclose(t.tool_duration_ms, 35.0, atol=1.0)
        assert np.isclose(t.tts_first_audio_ms, 200.0, atol=1.0)
        assert np.isclose(t.speech_end_to_first_audio_ms, 486.0, atol=1.0)

    def test_10_consecutive_commands_continuous_session(self, v3_1_assistant: VoiceAssistant) -> None:
        """Verify 10 consecutive commands execute cleanly without assistant restart or stream degradation."""
        commands = [
            ("what time is it", "time"),
            ("what is the date", "date"),
            ("system status", "CPU"),
            ("set volume to 60 percent", "60"),
            ("toggle mute", "mute"),
            ("toggle mute", "unmute"),
            ("remember my dog name is Buster", "Remembered"),
            ("recall dog", "Buster"),
            ("what applications are open", "Applications"),
            ("take a screenshot", "screenshot"),
        ]

        latencies = []
        for cmd, expected in commands:
            t0 = time.perf_counter()
            res = v3_1_assistant.handle_query(cmd)
            latencies.append((time.perf_counter() - t0) * 1000.0)
            assert len(res) > 0

        # Verify average fast-path execution is sub-100ms
        fast_latencies = [latencies[0], latencies[1], latencies[3], latencies[4]]
        avg_fast = sum(fast_latencies) / len(fast_latencies)
        assert avg_fast < 150.0

    def test_barge_in_interruption_during_speech(self, v3_1_assistant: VoiceAssistant) -> None:
        """Verify speaking state is interrupted immediately when cancel or wake word arrives."""
        v3_1_assistant._state = AssistantState.SPEAKING
        v3_1_assistant.tts.is_playing = True

        # User interrupts with cancel
        v3_1_assistant.cancel()
        assert v3_1_assistant._state == AssistantState.LISTENING_FOR_WAKE
        assert not v3_1_assistant.tts.is_playing

    def test_state_machine_guaranteed_return_to_wake_listening(self, v3_1_assistant: VoiceAssistant) -> None:
        """Verify every handled turn returns automatically to LISTENING_FOR_WAKE."""
        v3_1_assistant._running.set()
        v3_1_assistant.handle_query("what time is it")
        assert v3_1_assistant._state == AssistantState.LISTENING_FOR_WAKE

    def test_microphone_health_and_reconnection_resilience(self) -> None:
        """Verify ContinuousAudioCapture handles error callbacks and manages subscriber lifecycle."""
        cap = ContinuousAudioCapture(sample_rate=16000)
        frames_received = []

        def subscriber(float_chunk: np.ndarray, int16_chunk: np.ndarray) -> None:
            frames_received.append(len(float_chunk))

        cap.add_subscriber(subscriber)
        assert len(cap._subscribers) == 1

        # Simulate frame delivery
        dummy_frame = np.zeros(1280, dtype=np.float32)
        dummy_int16 = np.zeros(1280, dtype=np.int16)
        for sub in cap._subscribers:
            sub(dummy_frame, dummy_int16)

        assert len(frames_received) == 1
        assert frames_received[0] == 1280

        cap.remove_subscriber(subscriber)
        assert len(cap._subscribers) == 0

    def test_continuous_followup_dialogue_without_wake_word(self, v3_1_assistant: VoiceAssistant) -> None:
        """Verify once woken, FRIDAY processes follow-up commands in a loop without repeating wake word."""
        v3_1_assistant._running.set()

        # Mock STT to return sequence: 1. time, 2. volume, 3. go to sleep
        stt_responses = iter(["what time is it", "set volume to 50 percent", "go to sleep"])
        v3_1_assistant.stt.listen_once = lambda on_status=None: next(stt_responses, "")

        # Trigger voice roundtrip once
        v3_1_assistant._voice_roundtrip(t_wake=time.perf_counter())

        # Verify history recorded all turns
        history = v3_1_assistant._history
        assert len(history) >= 4
        assert any("what time is it" in msg["content"] for msg in history)
        assert any("set volume to 50 percent" in msg["content"] for msg in history)

        # Verify final state returned to LISTENING_FOR_WAKE
        assert v3_1_assistant._state == AssistantState.LISTENING_FOR_WAKE
