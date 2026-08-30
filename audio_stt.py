from __future__ import annotations

import logging
import queue
import time
from collections.abc import Callable
from typing import Any

import numpy as np

from audio_stream import ContinuousAudioCapture, get_global_audio_capture
from audio_vad import SileroVADEngine, VADConfig
from config import STTConfig

logger = logging.getLogger("audio_stt")


class SpeechToTextService:
    """High-speed in-memory Speech-to-Text using faster-whisper and Silero VAD endpointing."""

    def __init__(
        self,
        config: STTConfig,
        audio_capture: ContinuousAudioCapture | None = None,
        vad_engine: SileroVADEngine | None = None,
    ) -> None:
        self.config = config
        self.audio_capture = audio_capture
        self._vad = vad_engine or SileroVADEngine(
            VADConfig(
                speech_threshold=getattr(config, "silence_threshold", 0.45) if getattr(config, "silence_threshold", 0.45) > 0.1 else 0.45,
                silence_duration_ms=int(getattr(config, "silence_duration", 0.45) * 1000),
                min_record_seconds=config.min_record_seconds,
                max_record_seconds=config.max_record_seconds,
                sample_rate=config.sample_rate,
            )
        )
        self._model: Any = None
        self._last_telemetry: dict[str, float] = {}

    def warmup(self) -> None:
        self._get_model()
        try:
            self._vad.process_chunk(np.zeros(512, dtype=np.float32))
        except Exception:
            pass

    def listen_once(self, on_status: Callable[[str], None] | None = None) -> str:
        transcript, telemetry = self.listen_once_with_telemetry(on_status=on_status)
        self._last_telemetry = telemetry
        return transcript

    def listen_once_with_telemetry(
        self,
        on_status: Callable[[str], None] | None = None,
    ) -> tuple[str, dict[str, float]]:
        audio_data, telemetry = self._record_in_memory_with_vad(on_status=on_status)
        self._last_telemetry = telemetry

        if audio_data is None or len(audio_data) == 0:
            return "", telemetry

        t_stt_start = time.perf_counter()
        transcript = self.transcribe_array(audio_data)
        t_stt_end = time.perf_counter()

        telemetry["t_stt_start"] = t_stt_start
        telemetry["t_stt_complete"] = t_stt_end
        telemetry["stt_duration_ms"] = (t_stt_end - t_stt_start) * 1000.0
        return transcript, telemetry

    def transcribe_array(self, audio: np.ndarray) -> str:
        model = self._get_model()
        language = self.config.language if self.config.language != "auto" else None

        flat_audio = np.squeeze(audio).astype(np.float32)
        if len(flat_audio) == 0:
            return ""

        try:
            segments, _ = model.transcribe(
                flat_audio,
                language=language,
                beam_size=1,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=200),
            )
            transcript = " ".join(segment.text.strip() for segment in segments).strip()
            return transcript
        except Exception as exc:
            logger.warning("Transcription error: %s", exc)
            return ""

    def _record_in_memory_with_vad(
        self,
        on_status: Callable[[str], None] | None = None,
    ) -> tuple[np.ndarray | None, dict[str, float]]:
        if self.audio_capture is None:
            self.audio_capture = get_global_audio_capture(sample_rate=self.config.sample_rate)
            self.audio_capture.start()

        # 1. Grab 350ms pre-roll from continuous ring buffer
        pre_roll = self.audio_capture.ring_buffer.get_last_seconds(0.35)

        # 2. Subscribe a real-time queue to the audio capture stream
        frame_queue = self.audio_capture.create_queue_subscriber(maxsize=150)

        def _frame_source() -> np.ndarray | None:
            try:
                float_chunk, _ = frame_queue.get(timeout=0.15)
                return float_chunk
            except queue.Empty:
                return None

        try:
            audio_data, telemetry = self._vad.collect_speech_segment(
                frame_source=_frame_source,
                on_status=on_status,
                initial_pre_roll=pre_roll,
            )
            return audio_data, telemetry
        finally:
            self.audio_capture.remove_queue_subscriber(frame_queue)

    def _record_in_memory(self, on_status: Callable[[str], None] | None = None) -> np.ndarray | None:
        audio_data, _ = self._record_in_memory_with_vad(on_status=on_status)
        return audio_data

    def _get_model(self) -> Any:
        if self._model is None:
            from faster_whisper import WhisperModel

            target_device = self.config.device
            target_compute = self.config.compute_type

            # Check if CUDA is available
            if target_device == "cuda":
                try:
                    self._model = WhisperModel(
                        self.config.model_size,
                        device="cuda",
                        compute_type="float16" if target_compute in ("float16", "default") else target_compute,
                    )
                    logger.info("faster-whisper model loaded on CUDA (%s)", self.config.model_size)
                    return self._model
                except Exception as exc:
                    logger.info("CUDA not available for faster-whisper (%s). Falling back to CPU int8.", exc)

            try:
                self._model = WhisperModel(
                    self.config.model_size,
                    device="cpu",
                    compute_type="int8",
                )
                logger.info("faster-whisper model loaded on CPU (%s)", self.config.model_size)
            except Exception as exc:
                logger.error("Failed to load faster-whisper model: %s", exc)
                raise
        return self._model
