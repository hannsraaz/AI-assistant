from __future__ import annotations

import logging
import queue
import threading
import time
from typing import TYPE_CHECKING, Any

import numpy as np
import sounddevice as sd

from audio_tts import TextToSpeechService
from config import TTSConfig

logger = logging.getLogger(__name__)


class XTTSStreamingTTS:
    """XTTS v2 (Coqui) Neural Text-to-Speech Engine with smooth prosody

    and fallback to Piper/SAPI5.
    """

    def __init__(self, config: TTSConfig, device: str = "auto") -> None:
        self.config = config
        self._fallback_engine = TextToSpeechService(config)
        self.model: Any = None
        self.is_xtts_active = False

        if device == "auto":
            try:
                import torch

                self.device = "cuda" if torch.cuda.is_available() else "cpu"
            except Exception:
                self.device = "cpu"
        else:
            self.device = device

        self.audio_queue: queue.Queue[tuple[np.ndarray | None, int]] = queue.Queue()
        self.is_playing = False
        self._stop_event = threading.Event()

        # Dedicated audio worker thread
        self.playback_thread = threading.Thread(target=self._playback_worker, daemon=True)
        self.playback_thread.start()

        # Attempt background load of XTTS v2
        threading.Thread(target=self._load_xtts_model, daemon=True).start()

    def _load_xtts_model(self) -> None:
        try:
            from TTS.api import TTS

            logger.info("Initializing XTTS v2 model on %s...", self.device)
            self.model = TTS(
                model_name="tts_models/multilingual/multi-dataset/xtts_v2",
                gpu=(self.device == "cuda"),
                progress_bar=False,
            )
            self.is_xtts_active = True
            logger.info("XTTS v2 ready for high-fidelity voice synthesis.")
        except Exception as exc:
            logger.info("XTTS v2 not loaded (%s). Using high-speed Piper/SAPI5 engine.", exc)
            self.is_xtts_active = False

    def speak(self, text: str) -> None:
        """Speak a complete string."""
        if not text.strip():
            return
        if self.is_xtts_active and self.model is not None:
            sentences = self._fallback_engine.split_sentences(text)
            for sentence in sentences:
                if self._stop_event.is_set():
                    break
                self.speak_sentence(sentence)
        else:
            self._fallback_engine.speak(text)

    def speak_sentence(self, sentence: str, language: str = "en") -> None:
        """Synthesize and stream a single sentence immediately."""
        clean = sentence.strip()
        if not clean:
            return

        if self.is_xtts_active and self.model is not None:
            start_time = time.perf_counter()
            try:
                wav = self.model.tts(
                    text=clean,
                    language=language,
                    top_p=0.85,
                    temperature=0.75,
                )
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                logger.debug("XTTS latency: %.1fms for '%s'", elapsed_ms, clean[:30])

                wav_arr = np.array(wav, dtype=np.float32)
                max_val = np.max(np.abs(wav_arr))
                if max_val > 0:
                    wav_arr = wav_arr / max_val  # Normalize to [-1.0, 1.0]

                sample_rate = getattr(getattr(self.model, "synthesizer", None), "output_sample_rate", 24000)
                self.audio_queue.put((wav_arr, sample_rate))
                return
            except Exception as exc:
                logger.warning("XTTS synthesis failed (%s), falling back to Piper.", exc)

        # Fallback to Piper / pyttsx3
        self._fallback_engine.speak_sentence(clean)

    def stop(self) -> None:
        """Stop current playback and drain queue."""
        self._stop_event.set()
        sd.stop()
        self.is_playing = False
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break
        self._fallback_engine.stop()
        self._stop_event.clear()

    def is_busy(self) -> bool:
        return self.is_playing or not self.audio_queue.empty() or self._fallback_engine.is_busy()

    def wait_until_done(self, timeout: float = 30.0) -> None:
        start = time.monotonic()
        while self.is_busy():
            if time.monotonic() - start > timeout:
                break
            time.sleep(0.05)

    def _playback_worker(self) -> None:
        while True:
            try:
                item = self.audio_queue.get()
                wav, sample_rate = item
                if wav is None:
                    break
                if not self._stop_event.is_set():
                    self.is_playing = True
                    sd.play(wav, samplerate=sample_rate)
                    sd.wait()
                    self.is_playing = False
            except Exception as exc:
                logger.error("XTTS playback error: %s", exc)
                self.is_playing = False
