from __future__ import annotations

import logging
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np

from config import resolve_path

logger = logging.getLogger("audio_vad")


class VADState(str, Enum):
    IDLE = "idle"
    WAITING_FOR_SPEECH = "waiting_for_speech"
    SPEECH_ACTIVE = "speech_active"
    SPEECH_ENDED = "speech_ended"
    TIMEOUT = "timeout"


@dataclass
class VADConfig:
    enabled: bool = True
    model_path: str = "data/openwakeword_models/silero_vad.onnx"
    speech_threshold: float = 0.45
    min_speech_duration_ms: int = 120
    silence_duration_ms: int = 450
    min_record_seconds: float = 0.5
    max_record_seconds: float = 12.0
    pre_roll_seconds: float = 0.35
    sample_rate: int = 16000
    chunk_size: int = 512  # 32ms at 16kHz


class SileroVADEngine:
    """Ultra-low latency Neural Voice Activity Detector powered by Silero VAD (ONNX Runtime).

    Provides sub-1ms per-frame speech inference with stateful RNN memory cells,
    pre-roll audio buffering, and dynamic endpointing for natural conversation turns.
    """

    def __init__(
        self,
        config: VADConfig | None = None,
        model_path: str | Path | None = None,
    ) -> None:
        self.config = config or VADConfig()
        if model_path:
            self.config.model_path = str(model_path)

        self._session: Any = None
        self._lock = threading.Lock()

        # Recurrent state for Silero VAD
        self._h = np.zeros((2, 1, 64), dtype=np.float32)
        self._c = np.zeros((2, 1, 64), dtype=np.float32)
        self._sr = np.array(self.config.sample_rate, dtype=np.int64)

        # Pre-roll ring buffer holding recent raw float32 frames
        pre_roll_capacity = int((self.config.pre_roll_seconds * self.config.sample_rate) / self.config.chunk_size) + 1
        self._pre_roll_queue: deque[np.ndarray] = deque(maxlen=max(2, pre_roll_capacity))

        self.reset_state()

    def reset_state(self) -> None:
        """Reset the recurrent RNN state and pre-roll buffers."""
        with self._lock:
            self._h.fill(0.0)
            self._c.fill(0.0)
            self._pre_roll_queue.clear()

    def _get_session(self) -> Any:
        if self._session is None:
            with self._lock:
                if self._session is None:
                    try:
                        import onnxruntime as ort

                        path = resolve_path(self.config.model_path)
                        if not path.exists():
                            # Search fallbacks in common locations
                            fallbacks = [
                                Path("data/openwakeword_models/silero_vad.onnx"),
                                resolve_path("data/openwakeword_models/silero_vad.onnx"),
                            ]
                            for fb in fallbacks:
                                if fb.exists():
                                    path = fb
                                    break

                        opts = ort.SessionOptions()
                        opts.inter_op_num_threads = 1
                        opts.intra_op_num_threads = 1
                        opts.log_severity_level = 3  # Quiet logs

                        self._session = ort.InferenceSession(
                            str(path),
                            sess_options=opts,
                            providers=["CPUExecutionProvider"],
                        )
                        logger.info("Silero VAD ONNX engine loaded from %s", path)
                    except Exception as exc:
                        logger.warning("Failed to initialize Silero VAD ONNX session: %s. Using energy fallback.", exc)
                        self._session = None
        return self._session

    def process_chunk(self, chunk: np.ndarray) -> float:
        """Process a 512-sample float32 PCM chunk and return the speech probability [0.0, 1.0]."""
        flat = np.squeeze(chunk).astype(np.float32)

        # Normalize length to 512 samples
        if len(flat) < self.config.chunk_size:
            flat = np.pad(flat, (0, self.config.chunk_size - len(flat)))
        elif len(flat) > self.config.chunk_size:
            flat = flat[: self.config.chunk_size]

        # Keep in pre-roll buffer
        self._pre_roll_queue.append(flat.copy())

        session = self._get_session()
        if session is None:
            # Fallback to RMS energy if ONNX is unavailable
            energy = float(np.sqrt(np.mean(np.square(flat))))
            return 1.0 if energy >= 0.015 else 0.0

        try:
            tensor = np.expand_dims(flat, axis=0)  # Shape (1, 512)
            with self._lock:
                ort_inputs = {
                    "input": tensor,
                    "sr": self._sr,
                    "h": self._h,
                    "c": self._c,
                }
                out, hn, cn = session.run(None, ort_inputs)
                self._h = hn
                self._c = cn

            prob = float(out[0][0])
            return prob
        except Exception as exc:
            logger.warning("Silero VAD inference error: %s", exc)
            return 0.0

    def collect_speech_segment(
        self,
        frame_source: Callable[[], np.ndarray | None],
        on_status: Callable[[str], None] | None = None,
        initial_pre_roll: np.ndarray | None = None,
        stop_event: threading.Event | None = None,
    ) -> tuple[np.ndarray | None, dict[str, float]]:
        """Collect a full speech turn using neural VAD endpointing.

        Returns (audio_data, telemetry_dict).
        """
        self.reset_state()

        collected_chunks: list[np.ndarray] = []
        if initial_pre_roll is not None and len(initial_pre_roll) > 0:
            collected_chunks.append(np.squeeze(initial_pre_roll).astype(np.float32))

        # Include accumulated pre-roll queue
        for pr_chunk in list(self._pre_roll_queue):
            collected_chunks.append(pr_chunk)

        is_speech_active = False
        speech_start_time = 0.0
        silence_start_time = 0.0
        listen_start_time = time.perf_counter()

        ms_per_chunk = (self.config.chunk_size / self.config.sample_rate) * 1000.0
        consecutive_speech_ms = 0.0
        consecutive_silence_ms = 0.0

        silence_cutoff_ms = float(self.config.silence_duration_ms)
        min_speech_ms = float(self.config.min_speech_duration_ms)

        if on_status:
            on_status("Listening...")

        t_first_speech = 0.0
        t_speech_end = 0.0

        try:
            while True:
                if stop_event and stop_event.is_set():
                    break

                elapsed_total = time.perf_counter() - listen_start_time
                if elapsed_total >= self.config.max_record_seconds:
                    break

                chunk = frame_source()
                if chunk is None:
                    time.sleep(0.01)
                    continue

                flat = np.squeeze(chunk).astype(np.float32)
                if len(flat) == 0:
                    continue

                prob = self.process_chunk(flat)
                collected_chunks.append(flat)

                if prob >= self.config.speech_threshold:
                    consecutive_speech_ms += ms_per_chunk
                    consecutive_silence_ms = 0.0
                    silence_start_time = 0.0

                    if consecutive_speech_ms >= min_speech_ms and not is_speech_active:
                        is_speech_active = True
                        t_first_speech = time.perf_counter()
                        if on_status:
                            on_status("Hearing speech...")
                else:
                    consecutive_silence_ms += ms_per_chunk
                    consecutive_speech_ms = 0.0

                    if is_speech_active:
                        if silence_start_time == 0.0:
                            silence_start_time = time.perf_counter()

                        if consecutive_silence_ms >= silence_cutoff_ms:
                            elapsed_speech = time.perf_counter() - (t_first_speech or listen_start_time)
                            if elapsed_speech >= self.config.min_record_seconds:
                                t_speech_end = time.perf_counter()
                                break
                    else:
                        # Prune excessive leading silence while waiting for speech
                        # Keep only recent pre-roll window to avoid memory bloat
                        max_leading_chunks = int((self.config.pre_roll_seconds * self.config.sample_rate) / self.config.chunk_size) + 2
                        if len(collected_chunks) > max_leading_chunks:
                            collected_chunks = collected_chunks[-max_leading_chunks:]

        except Exception as exc:
            logger.exception("VAD audio collection error: %s", exc)

        if not is_speech_active or not collected_chunks:
            return None, {
                "t_listen_start": listen_start_time,
                "t_speech_start": 0.0,
                "t_speech_end": 0.0,
                "speech_duration_ms": 0.0,
            }

        concatenated = np.concatenate(collected_chunks).astype(np.float32)
        speech_dur = (t_speech_end - t_first_speech) * 1000.0 if (t_speech_end and t_first_speech) else 0.0

        telemetry = {
            "t_listen_start": listen_start_time,
            "t_speech_start": t_first_speech or listen_start_time,
            "t_speech_end": t_speech_end or time.perf_counter(),
            "speech_duration_ms": max(0.0, speech_dur),
        }
        return concatenated, telemetry
