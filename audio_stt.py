from __future__ import annotations

import queue
import time
from collections.abc import Callable
from typing import Any

import numpy as np

from audio_stream import ContinuousAudioCapture, get_global_audio_capture
from config import STTConfig


class SpeechToTextService:
    """High-speed in-memory Speech-to-Text using faster-whisper with continuous ring-buffer streaming."""

    def __init__(
        self,
        config: STTConfig,
        audio_capture: ContinuousAudioCapture | None = None,
    ) -> None:
        self.config = config
        self.audio_capture = audio_capture
        self._model = None

    def warmup(self) -> None:
        self._get_model()

    def listen_once(self, on_status: Callable[[str], None] | None = None) -> str:
        audio_data = self._record_in_memory(on_status=on_status)
        if audio_data is None or len(audio_data) == 0:
            return ""
        return self.transcribe_array(audio_data)

    def _record_in_memory(self, on_status: Callable[[str], None] | None = None) -> np.ndarray | None:
        return self._record_from_continuous_stream(on_status=on_status)

    def transcribe_array(self, audio: np.ndarray) -> str:
        model = self._get_model()
        language = self.config.language if self.config.language != "auto" else None

        # faster-whisper accepts a 1D float32 numpy array directly at 16kHz
        segments, _ = model.transcribe(
            audio,
            language=language,
            beam_size=1,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=250),
        )
        transcript = " ".join(segment.text.strip() for segment in segments).strip()
        return transcript

    def _record_from_continuous_stream(
        self,
        on_status: Callable[[str], None] | None = None,
    ) -> np.ndarray | None:
        if self.audio_capture is None:
            self.audio_capture = get_global_audio_capture(sample_rate=self.config.sample_rate)
            self.audio_capture.start()

        if on_status:
            on_status("Listening...")

        # 1. Grab 300ms pre-roll buffer from ring buffer
        pre_roll = self.audio_capture.ring_buffer.get_last_seconds(0.3)
        collected_frames: list[np.ndarray] = [pre_roll] if len(pre_roll) > 0 else []

        frame_queue: queue.Queue[np.ndarray] = queue.Queue()

        def _on_frame(float_chunk: np.ndarray, _: np.ndarray) -> None:
            frame_queue.put(float_chunk.copy())

        self.audio_capture.add_subscriber(_on_frame)

        heard_speech = False
        silence_started = 0.0
        start_time = time.monotonic()
        silence_cutoff = getattr(self.config, "silence_duration", 0.4)

        try:
            while True:
                try:
                    chunk = frame_queue.get(timeout=0.2)
                except queue.Empty:
                    if time.monotonic() - start_time >= self.config.max_record_seconds:
                        break
                    continue

                collected_frames.append(chunk)

                # Root-mean-square audio energy calculation
                energy = float(np.sqrt(np.mean(np.square(chunk))))
                elapsed = time.monotonic() - start_time

                if energy >= self.config.silence_threshold:
                    heard_speech = True
                    silence_started = 0.0
                elif heard_speech:
                    if silence_started == 0.0:
                        silence_started = time.monotonic()
                    elif time.monotonic() - silence_started >= silence_cutoff:
                        if elapsed >= self.config.min_record_seconds:
                            break

                if elapsed >= self.config.max_record_seconds:
                    break
        finally:
            self.audio_capture.remove_subscriber(_on_frame)

        if not heard_speech or not collected_frames:
            # Check if standalone sounddevice fallback needed if stream produced nothing
            if not collected_frames or len(collected_frames) <= 1:
                return self._record_standalone_fallback(on_status)
            return None

        return np.concatenate(collected_frames).astype(np.float32)

    def _record_standalone_fallback(self, on_status: Callable[[str], None] | None = None) -> np.ndarray | None:
        import sounddevice as sd

        block_size = int(self.config.sample_rate * self.config.block_duration)
        frames: list[np.ndarray] = []
        heard_speech = False
        silence_started = 0.0
        start_time = time.monotonic()

        try:
            with sd.InputStream(
                samplerate=self.config.sample_rate,
                channels=1,
                dtype="float32",
                blocksize=block_size,
            ) as stream:
                while True:
                    block, _ = stream.read(block_size)
                    flattened = np.squeeze(block.copy())
                    frames.append(flattened)

                    energy = float(np.sqrt(np.mean(np.square(flattened))))
                    elapsed = time.monotonic() - start_time

                    if energy >= self.config.silence_threshold:
                        heard_speech = True
                        silence_started = 0.0
                    elif heard_speech:
                        if silence_started == 0.0:
                            silence_started = time.monotonic()
                        elif time.monotonic() - silence_started >= self.config.silence_duration:
                            if elapsed >= self.config.min_record_seconds:
                                break

                    if elapsed >= self.config.max_record_seconds:
                        break
        except Exception:
            return None

        if not heard_speech or not frames:
            return None
        return np.concatenate(frames).astype(np.float32)

    def _get_model(self) -> Any:
        if self._model is None:
            from faster_whisper import WhisperModel

            target_device = self.config.device
            target_compute = self.config.compute_type

            try:
                self._model = WhisperModel(
                    self.config.model_size,
                    device=target_device,
                    compute_type=target_compute,
                )
            except Exception:
                self._model = WhisperModel(
                    self.config.model_size,
                    device="cpu",
                    compute_type="int8",
                )
        return self._model
