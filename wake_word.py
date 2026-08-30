from __future__ import annotations

import logging
import queue
import threading
import time
from collections import deque
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np

from audio_stream import ContinuousAudioCapture, get_global_audio_capture
from config import WakeWordConfig, resolve_path


class WakeWordError(RuntimeError):
    pass


def prepare_wake_word_models(config: WakeWordConfig) -> list[Path]:
    import openwakeword.utils

    model_dir = resolve_path(config.model_directory)
    model_dir.mkdir(parents=True, exist_ok=True)

    prepared: list[Path] = []
    for custom_path in config.custom_model_paths:
        p = resolve_path(custom_path)
        if not p.exists():
            raise WakeWordError(f"Custom model path not found: {p}")
        prepared.append(p)

    names_to_download = []
    for name in config.model_names:
        clean_name = name.strip()
        if not clean_name:
            continue
        dest = model_dir / f"{clean_name}.onnx"
        if not dest.exists() or dest.stat().st_size == 0:
            names_to_download.append(clean_name)
        else:
            prepared.append(dest)

    if names_to_download:
        try:
            openwakeword.utils.download_models(model_names=names_to_download, target_directory=str(model_dir))
        except Exception:
            openwakeword.utils.download_models(target_directory=str(model_dir))

        for name in names_to_download:
            dest = model_dir / f"{name}.onnx"
            if dest.exists():
                prepared.append(dest)

    return prepared


class WakeWordDetector:
    """High-reliability continuous wake-word detector with multi-frame score smoothing,

    asynchronous worker thread execution, and diagnostic telemetry.
    """

    def __init__(
        self,
        config: WakeWordConfig,
        logger: logging.Logger,
        audio_capture: ContinuousAudioCapture | None = None,
    ) -> None:
        self.config = config
        self.logger = logger
        self.audio_capture = audio_capture
        self._model: Any = None
        self._on_detect_callback: Callable[[], None] | None = None
        self._last_detection_time = 0.0
        self._active = threading.Event()
        self._is_paused = False

        # Async audio processing queue
        self._audio_queue: queue.Queue[tuple[np.ndarray, np.ndarray]] = queue.Queue(maxsize=100)
        self._worker_thread: threading.Thread | None = None

        # PCM accumulator for 1280-sample openWakeWord frames
        self._accumulated_int16: list[np.ndarray] = []
        self._accumulated_samples = 0
        self._target_frame_size = getattr(config, "frame_length", 1280)

        # Multi-frame score smoothing (sliding window over last 3 frames)
        self._score_history: deque[float] = deque(maxlen=3)

        # Diagnostics
        self.total_detections = 0
        self.latest_score = 0.0
        self.peak_score = 0.0
        self.frames_processed = 0

    def warmup(self) -> None:
        self._get_model()

    def start(self, on_detect: Callable[[], None]) -> None:
        self._on_detect_callback = on_detect
        self._active.set()
        self._is_paused = False
        self._score_history.clear()
        self._accumulated_int16.clear()
        self._accumulated_samples = 0

        if self.audio_capture is None:
            self.audio_capture = get_global_audio_capture(
                sample_rate=self.config.sample_rate,
                device_index=self.config.device_index,
            )

        # Start background inference worker if not already running
        if self._worker_thread is None or not self._worker_thread.is_alive():
            self._worker_thread = threading.Thread(target=self._inference_loop, daemon=True)
            self._worker_thread.start()

        self.audio_capture.add_subscriber(self._on_audio_frame)
        self.audio_capture.start()
        self.logger.info("Wake word detector started with multi-frame score smoothing.")

    def stop(self) -> None:
        self._active.clear()
        if self.audio_capture:
            self.audio_capture.remove_subscriber(self._on_audio_frame)
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=1.0)

    def pause(self) -> None:
        """Temporarily mute wake word callback (e.g. while user is talking in active turn)."""
        self._is_paused = True

    def resume(self) -> None:
        """Resume wake word detection seamlessly."""
        self._is_paused = False
        self._score_history.clear()
        if self._model:
            try:
                self._model.reset()
            except Exception:
                pass

    def get_diagnostics(self) -> dict[str, Any]:
        """Return diagnostic health and score metrics."""
        return {
            "enabled": self.config.enabled,
            "threshold": self.config.threshold,
            "latest_score": round(self.latest_score, 3),
            "peak_score": round(self.peak_score, 3),
            "total_detections": self.total_detections,
            "frames_processed": self.frames_processed,
            "is_paused": self._is_paused,
        }

    def _on_audio_frame(self, float_chunk: Any, int16_chunk: Any) -> None:
        if not self._active.is_set() or not self.config.enabled:
            return

        try:
            self._audio_queue.put_nowait((float_chunk, int16_chunk))
        except queue.Full:
            try:
                self._audio_queue.get_nowait()
                self._audio_queue.put_nowait((float_chunk, int16_chunk))
            except Exception:
                pass

    def _inference_loop(self) -> None:
        """Dedicated background inference worker preventing audio capture stutter."""
        while self._active.is_set():
            try:
                _, int16_chunk = self._audio_queue.get(timeout=0.2)
            except queue.Empty:
                continue

            if self._is_paused:
                self._accumulated_int16.clear()
                self._accumulated_samples = 0
                continue

            flat_int16 = np.squeeze(int16_chunk).astype(np.int16)
            self._accumulated_int16.append(flat_int16)
            self._accumulated_samples += len(flat_int16)

            if self._accumulated_samples >= self._target_frame_size:
                combined = np.concatenate(self._accumulated_int16)
                process_chunk = combined[: self._target_frame_size]
                remainder = combined[self._target_frame_size :]

                self._accumulated_int16 = [remainder] if len(remainder) > 0 else []
                self._accumulated_samples = len(remainder)

                self._run_model_prediction(process_chunk)

    def _run_model_prediction(self, int16_frame: np.ndarray) -> None:
        model = self._get_model()
        if model is None:
            return

        try:
            self.frames_processed += 1
            predictions = model.predict(int16_frame)
            label, raw_score = _top_prediction(predictions)

            self.latest_score = raw_score
            self._score_history.append(raw_score)

            # Multi-frame smoothed score (maximum over sliding window to catch fast phoneme transitions)
            smoothed_score = max(self._score_history) if self._score_history else raw_score
            if smoothed_score > self.peak_score:
                self.peak_score = smoothed_score

            if not label or smoothed_score < self.config.threshold:
                return

            now = time.monotonic()
            if now - self._last_detection_time < self.config.debounce_seconds:
                return

            self._last_detection_time = now
            self.total_detections += 1
            self.logger.info("Wake word '%s' detected (raw: %.2f, smoothed: %.2f)", label, raw_score, smoothed_score)
            model.reset()
            self._score_history.clear()

            if self._on_detect_callback and not self._is_paused:
                self._on_detect_callback()
        except Exception as exc:
            self.logger.warning("Wake word prediction error: %s", exc)

    def _get_model(self) -> Any:
        if self._model is None and self.config.enabled:
            try:
                from openwakeword.model import Model

                model_paths = prepare_wake_word_models(self.config)
                models_arg = [str(p) for p in model_paths] if model_paths else self.config.model_names

                self._model = Model(
                    wakeword_models=models_arg,
                    enable_speex_noise_suppression=self.config.enable_noise_suppression,
                    vad_threshold=self.config.vad_threshold,
                    inference_framework=self.config.inference_framework,
                )
                self.logger.info("Wake-word openWakeWord model loaded.")
            except Exception as exc:
                self.logger.error("Failed to load wake word model: %s", exc)
                self._model = None
        return self._model


def _top_prediction(predictions: dict[str, float] | list[dict[str, float]]) -> tuple[str, float]:
    if isinstance(predictions, list):
        if not predictions:
            return "", 0.0
        predictions = predictions[0]

    best_label = ""
    best_score = 0.0
    for label, score in predictions.items():
        if score > best_score:
            best_label = label
            best_score = float(score)
    return best_label, best_score
