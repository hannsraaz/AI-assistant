from __future__ import annotations

import time
from typing import Any, Callable

import numpy as np

from config import STTConfig


class SpeechToTextService:
    """High-speed in-memory Speech-to-Text using faster-whisper."""

    def __init__(self, config: STTConfig) -> None:
        self.config = config
        self._model = None

    def warmup(self) -> None:
        self._get_model()

    def listen_once(self, on_status: Callable[[str], None] | None = None) -> str:
        audio_data = self._record_in_memory(on_status=on_status)
        if audio_data is None or len(audio_data) == 0:
            return ""
        return self.transcribe_array(audio_data)

    def transcribe_array(self, audio: np.ndarray) -> str:
        model = self._get_model()
        language = self.config.language if self.config.language != "auto" else None

        # faster-whisper accepts a 1D float32 numpy array directly at 16kHz
        segments, _ = model.transcribe(
            audio,
            language=language,
            beam_size=1,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=300),
        )
        transcript = " ".join(segment.text.strip() for segment in segments).strip()
        return transcript

    def _record_in_memory(self, on_status: Callable[[str], None] | None = None) -> np.ndarray | None:
        import sounddevice as sd

        block_size = int(self.config.sample_rate * self.config.block_duration)
        frames: list[np.ndarray] = []
        heard_speech = False
        silence_started = 0.0
        start_time = time.monotonic()

        if on_status:
            on_status("Listening...")

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

                # Root-mean-square audio energy calculation
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

        if not heard_speech or not frames:
            return None

        # Concatenate audio frames directly into a single 1D numpy array
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
            except Exception as exc:
                # If CUDA runtime DLLs (cublas64_12.dll, etc.) are missing, cleanly fallback to CPU
                self._model = WhisperModel(
                    self.config.model_size,
                    device="cpu",
                    compute_type="int8",
                )
        return self._model
