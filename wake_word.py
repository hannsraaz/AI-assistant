from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

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
    """High-reliability continuous wake-word detector consuming frames from ContinuousAudioCapture."""

    def __init__(
        self,
        config: WakeWordConfig,
        logger: logging.Logger,
        audio_capture: ContinuousAudioCapture | None = None,
    ) -> None:
        self.config = config
        self.logger = logger
        self.audio_capture = audio_capture
        self._model = None
        self._on_detect_callback: Callable[[], None] | None = None
        self._last_detection_time = 0.0
        self._active = threading.Event()
        self._is_paused = False

    def warmup(self) -> None:
        self._get_model()

    def start(self, on_detect: Callable[[], None]) -> None:
        self._on_detect_callback = on_detect
        self._active.set()
        self._is_paused = False

        if self.audio_capture is None:
            self.audio_capture = get_global_audio_capture(
                sample_rate=self.config.sample_rate,
                device_index=self.config.device_index,
            )

        self.audio_capture.add_subscriber(self._on_audio_frame)
        self.audio_capture.start()
        self.logger.info("Wake word detector subscribed to continuous audio stream.")

    def stop(self) -> None:
        self._active.clear()
        if self.audio_capture:
            self.audio_capture.remove_subscriber(self._on_audio_frame)

    def pause(self) -> None:
        """Temporarily ignore wake word (e.g. while actively recording command)."""
        self._is_paused = True

    def resume(self) -> None:
        """Resume wake word detection seamlessly."""
        self._is_paused = False
        if self._model:
            try:
                self._model.reset()
            except Exception:
                pass

    def _on_audio_frame(self, float_chunk: Any, int16_chunk: Any) -> None:
        if not self._active.is_set() or self._is_paused or not self.config.enabled:
            return

        model = self._get_model()
        if model is None:
            return

        try:
            predictions = model.predict(int16_chunk)
            label, score = _top_prediction(predictions)

            if not label or score < self.config.threshold:
                return

            now = time.monotonic()
            if now - self._last_detection_time < self.config.debounce_seconds:
                return

            self._last_detection_time = now
            self.logger.info("Wake word '%s' detected (confidence: %.2f)", label, score)
            model.reset()

            if self._on_detect_callback:
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
