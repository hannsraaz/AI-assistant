from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from pathlib import Path

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
    """Threaded openWakeWord detector with smooth lifecycle control."""

    def __init__(self, config: WakeWordConfig, logger: logging.Logger) -> None:
        self.config = config
        self.logger = logger
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._model_paths: list[Path] = []

    def start(self, on_detect: Callable[[], None]) -> None:
        if self._thread and self._thread.is_alive():
            return
        if self.config.enabled:
            self._model_paths = prepare_wake_word_models(self.config)
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, args=(on_detect,), daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.5)

    def _run(self, on_detect: Callable[[], None]) -> None:
        if not self.config.enabled:
            return

        try:
            import numpy as np
            import sounddevice as sd
            from openwakeword.model import Model

            models_arg = [str(p) for p in self._model_paths] if self._model_paths else self.config.model_names

            model = Model(
                wakeword_models=models_arg,
                enable_speex_noise_suppression=self.config.enable_noise_suppression,
                vad_threshold=self.config.vad_threshold,
                inference_framework=self.config.inference_framework,
            )
            device = None if self.config.device_index < 0 else self.config.device_index
            last_detection_time = 0.0

            with sd.InputStream(
                samplerate=self.config.sample_rate,
                channels=1,
                dtype="int16",
                blocksize=self.config.frame_length,
                device=device,
            ) as stream:
                self.logger.info("Wake word detector active.")

                while not self._stop_event.is_set():
                    chunk, _ = stream.read(self.config.frame_length)
                    pcm = np.squeeze(chunk.copy()).astype(np.int16)
                    predictions = model.predict(pcm)
                    label, score = _top_prediction(predictions)

                    if not label or score < self.config.threshold:
                        continue
                    if time.monotonic() - last_detection_time < self.config.debounce_seconds:
                        continue

                    last_detection_time = time.monotonic()
                    self.logger.info("Wake word '%s' detected (confidence: %.2f)", label, score)
                    model.reset()
                    on_detect()
        except Exception as exc:
            self.logger.exception("Wake word detector stopped: %s", exc)


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
