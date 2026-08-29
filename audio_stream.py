from __future__ import annotations

import collections
import logging
import threading
import time
from collections.abc import Callable
from typing import Any

import numpy as np

logger = logging.getLogger("audio_stream")


class AudioRingBuffer:
    """Thread-safe circular ring buffer holding recent audio frames."""

    def __init__(self, capacity_seconds: float = 5.0, sample_rate: int = 16000) -> None:
        self.capacity_samples = int(capacity_seconds * sample_rate)
        self.sample_rate = sample_rate
        self._buffer = np.zeros(self.capacity_samples, dtype=np.float32)
        self._write_pos = 0
        self._lock = threading.Lock()
        self._total_samples_written = 0

    def write(self, chunk: np.ndarray) -> None:
        """Write 1D float32 chunk into circular ring buffer."""
        chunk_flat = np.squeeze(chunk).astype(np.float32)
        chunk_len = len(chunk_flat)
        if chunk_len == 0:
            return

        with self._lock:
            if chunk_len >= self.capacity_samples:
                self._buffer[:] = chunk_flat[-self.capacity_samples:]
                self._write_pos = 0
            else:
                end_pos = self._write_pos + chunk_len
                if end_pos <= self.capacity_samples:
                    self._buffer[self._write_pos : end_pos] = chunk_flat
                else:
                    first_part = self.capacity_samples - self._write_pos
                    self._buffer[self._write_pos :] = chunk_flat[:first_part]
                    self._buffer[: chunk_len - first_part] = chunk_flat[first_part:]
                self._write_pos = (self._write_pos + chunk_len) % self.capacity_samples
            self._total_samples_written += chunk_len

    def get_last_samples(self, num_samples: int) -> np.ndarray:
        """Get the most recent num_samples from the ring buffer."""
        num_samples = min(num_samples, self.capacity_samples)
        with self._lock:
            if self._total_samples_written < num_samples:
                return self._buffer[: self._write_pos].copy()
            if self._write_pos >= num_samples:
                return self._buffer[self._write_pos - num_samples : self._write_pos].copy()
            else:
                part2 = self._buffer[: self._write_pos]
                part1_len = num_samples - len(part2)
                part1 = self._buffer[self.capacity_samples - part1_len :]
                return np.concatenate([part1, part2])

    def get_last_seconds(self, seconds: float) -> np.ndarray:
        return self.get_last_samples(int(seconds * self.sample_rate))


class ContinuousAudioCapture:
    """Single persistent microphone listener continuously feeding ring buffer and subscribers."""

    def __init__(
        self,
        sample_rate: int = 16000,
        frame_length: int = 1280,
        device_index: int = -1,
        on_error: Callable[[str], None] | None = None,
    ) -> None:
        self.sample_rate = sample_rate
        self.frame_length = frame_length
        self.device_index = None if device_index < 0 else device_index
        self.on_error = on_error or (lambda _: None)

        self.ring_buffer = AudioRingBuffer(capacity_seconds=5.0, sample_rate=sample_rate)
        self._subscribers: list[Callable[[np.ndarray, np.ndarray], None]] = []
        self._sub_lock = threading.Lock()

        self._running = threading.Event()
        self._stream = None
        self._thread: threading.Thread | None = None
        self._last_frame_time = 0.0
        self.is_connected = False

    def add_subscriber(self, callback: Callable[[np.ndarray, np.ndarray], None]) -> None:
        """Subscribe to raw audio frames: callback(pcm_float32, pcm_int16)."""
        with self._sub_lock:
            if callback not in self._subscribers:
                self._subscribers.append(callback)

    def remove_subscriber(self, callback: Callable[[np.ndarray, np.ndarray], None]) -> None:
        with self._sub_lock:
            if callback in self._subscribers:
                self._subscribers.remove(callback)

    def start(self) -> None:
        if self._running.is_set():
            return
        self._running.set()
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running.clear()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.5)

    def _capture_loop(self) -> None:
        import sounddevice as sd

        while self._running.is_set():
            try:
                self.is_connected = False
                with sd.InputStream(
                    samplerate=self.sample_rate,
                    channels=1,
                    dtype="float32",
                    blocksize=self.frame_length,
                    device=self.device_index,
                ) as stream:
                    self._stream = stream
                    self.is_connected = True
                    logger.info("Continuous audio stream established on device %s", self.device_index)

                    while self._running.is_set():
                        chunk, overflowed = stream.read(self.frame_length)
                        self._last_frame_time = time.monotonic()
                        float_chunk = np.squeeze(chunk).astype(np.float32)

                        # Write to ring buffer
                        self.ring_buffer.write(float_chunk)

                        # Prepare int16 for wake-word models
                        int16_chunk = np.clip(float_chunk * 32767.0, -32768, 32767).astype(np.int16)

                        # Dispatch to subscribers
                        with self._sub_lock:
                            subs = list(self._subscribers)
                        for sub in subs:
                            try:
                                sub(float_chunk, int16_chunk)
                            except Exception as exc:
                                logger.warning("Subscriber callback error: %s", exc)

            except Exception as exc:
                self.is_connected = False
                logger.warning("Microphone stream error: %s. Attempting reconnection in 2s...", exc)
                self.on_error(f"Microphone error: {exc}")
                time.sleep(2.0)


# Global singleton continuous capture
global_audio_capture: ContinuousAudioCapture | None = None


def get_global_audio_capture(sample_rate: int = 16000, device_index: int = -1) -> ContinuousAudioCapture:
    global global_audio_capture
    if global_audio_capture is None:
        global_audio_capture = ContinuousAudioCapture(sample_rate=sample_rate, device_index=device_index)
    return global_audio_capture
