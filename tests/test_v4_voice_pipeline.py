from __future__ import annotations

import queue
import time
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from audio_stt import SpeechToTextService
from audio_stream import AudioRingBuffer, ContinuousAudioCapture
from audio_vad import SileroVADEngine, VADConfig, VADState
from config import AppConfig, STTConfig, WakeWordConfig
from wake_word import WakeWordDetector


class TestContinuousAudioCapture:
    def test_ring_buffer_write_and_read(self) -> None:
        buffer = AudioRingBuffer(capacity_seconds=1.0, sample_rate=16000)
        # Write 8000 samples of ones
        chunk1 = np.ones(8000, dtype=np.float32)
        buffer.write(chunk1)
        samples = buffer.get_last_samples(4000)
        assert len(samples) == 4000
        assert np.allclose(samples, 1.0)

        # Write 10000 samples of twos (overwriting circular buffer)
        chunk2 = np.full(10000, 2.0, dtype=np.float32)
        buffer.write(chunk2)
        recent = buffer.get_last_seconds(0.5)
        assert len(recent) == 8000
        assert np.allclose(recent, 2.0)

    def test_subscriber_queue_dispatch(self) -> None:
        capture = ContinuousAudioCapture(sample_rate=16000, frame_length=512)
        q = capture.create_queue_subscriber(maxsize=10)

        received = []

        def _cb(f: np.ndarray, i: np.ndarray) -> None:
            received.append(len(f))

        capture.add_subscriber(_cb)

        # Directly enqueue frames into dispatch queue to test non-blocking dispatch loop
        capture._running.set()
        dummy_f = np.zeros(512, dtype=np.float32)
        dummy_i = np.zeros(512, dtype=np.int16)
        capture._dispatch_queue.put((dummy_f, dummy_i))

        # Run one dispatch tick
        import threading
        t = threading.Thread(target=capture._dispatch_loop, daemon=True)
        t.start()
        time.sleep(0.1)
        capture._running.clear()

        assert len(received) >= 1
        assert not q.empty()
        item_f, item_i = q.get_nowait()
        assert len(item_f) == 512
        assert len(item_i) == 512

        capture.remove_subscriber(_cb)
        capture.remove_queue_subscriber(q)


class TestSileroVADEngine:
    def test_vad_initialization_and_chunk_inference(self) -> None:
        vad = SileroVADEngine(VADConfig(speech_threshold=0.45))
        # Silence chunk
        silence_chunk = np.zeros(512, dtype=np.float32)
        prob_silence = vad.process_chunk(silence_chunk)
        assert isinstance(prob_silence, float)
        assert 0.0 <= prob_silence <= 1.0
        assert prob_silence < 0.2  # Pure zeros should score close to 0.0

    def test_vad_speech_segment_collection_and_endpointing(self) -> None:
        vad = SileroVADEngine(
            VADConfig(
                speech_threshold=0.4,
                min_speech_duration_ms=50,
                silence_duration_ms=100,
                min_record_seconds=0.1,
                max_record_seconds=3.0,
            )
        )

        # Mock frame sequence: 3 chunks silence, 5 chunks simulated speech, 5 chunks silence
        silence = np.zeros(512, dtype=np.float32)
        speech_synth = (np.sin(np.linspace(0, 20 * np.pi, 512)) * 0.5).astype(np.float32)

        sequence = [silence] * 3 + [speech_synth] * 5 + [silence] * 10
        idx = 0

        def _source() -> np.ndarray | None:
            nonlocal idx
            if idx < len(sequence):
                c = sequence[idx]
                idx += 1
                return c
            return None

        # Mock process_chunk to return high prob for speech and 0 for silence
        original_process = vad.process_chunk

        def _mock_process(chunk: np.ndarray) -> float:
            if np.max(np.abs(chunk)) > 0.1:
                return 0.85
            return 0.05

        vad.process_chunk = _mock_process  # type: ignore[method-assign]

        audio_data, meta = vad.collect_speech_segment(frame_source=_source)
        assert audio_data is not None
        assert len(audio_data) > 0
        assert meta["t_speech_start"] > 0
        assert meta["t_speech_end"] >= meta["t_speech_start"]


class TestWakeWordDetectorV4:
    def test_multi_frame_score_smoothing(self) -> None:
        config = WakeWordConfig(threshold=0.5, debounce_seconds=0.5)
        logger = MagicMock()
        detector = WakeWordDetector(config=config, logger=logger)

        # Mock model predict
        mock_model = MagicMock()
        mock_model.predict.return_value = {"hey_jarvis": 0.48}
        detector._model = mock_model

        callback = MagicMock()
        detector.start(on_detect=callback)

        # Send chunk that produces score 0.48
        frame = np.zeros(1280, dtype=np.int16)
        detector._run_model_prediction(frame)
        assert detector.latest_score == 0.48

        # Next chunk produces 0.55 -> crosses threshold
        mock_model.predict.return_value = {"hey_jarvis": 0.55}
        detector._run_model_prediction(frame)
        assert detector.peak_score >= 0.55
        assert detector.total_detections == 1
        assert callback.call_count == 1

        # Check diagnostics dictionary
        diag = detector.get_diagnostics()
        assert diag["threshold"] == 0.5
        assert diag["total_detections"] == 1
        assert diag["peak_score"] >= 0.55

        detector.stop()


class TestSpeechToTextServiceV4:
    def test_stt_warmup_and_transcribe(self) -> None:
        config = STTConfig(model_size="base.en", device="cpu", compute_type="int8")
        stt = SpeechToTextService(config=config)

        # Mock whisper model transcribe
        mock_whisper = MagicMock()
        mock_segment = MagicMock()
        mock_segment.text = "hello world"
        mock_whisper.transcribe.return_value = ([mock_segment], MagicMock())
        stt._model = mock_whisper

        stt.warmup()
        transcript = stt.transcribe_array(np.zeros(16000, dtype=np.float32))
        assert transcript == "hello world"

    def test_listen_once_with_telemetry(self) -> None:
        config = STTConfig(model_size="base.en")
        capture = ContinuousAudioCapture(sample_rate=16000)
        stt = SpeechToTextService(config=config, audio_capture=capture)

        # Mock whisper model and VAD
        mock_whisper = MagicMock()
        mock_segment = MagicMock()
        mock_segment.text = "what is the time"
        mock_whisper.transcribe.return_value = ([mock_segment], MagicMock())
        stt._model = mock_whisper

        # Mock VAD collect speech
        dummy_audio = np.ones(16000, dtype=np.float32)
        stt._vad.collect_speech_segment = MagicMock(  # type: ignore[method-assign]
            return_value=(
                dummy_audio,
                {
                    "t_listen_start": 100.0,
                    "t_speech_start": 100.2,
                    "t_speech_end": 101.5,
                    "speech_duration_ms": 1300.0,
                },
            )
        )

        transcript, telemetry = stt.listen_once_with_telemetry()
        assert transcript == "what is the time"
        assert telemetry["speech_duration_ms"] == 1300.0
        assert telemetry["stt_duration_ms"] >= 0.0
