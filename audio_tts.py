from __future__ import annotations

import queue
import re
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

import numpy as np
import sounddevice as sd

from config import TTSConfig, resolve_path
from core.language.hinglish_normalizer import global_hinglish_normalizer
from core.voice.prosody_engine import ProsodySegment, global_prosody_engine
from core.voice.tts_engine import (
    AutoRoutingTTSEngine,
    BaseTTSEngine,
    HinglishNeuralTTSEngine,
    IndicVoiceTTSEngine,
    PiperTTSEngine,
    SAPI5TTSEngine,
)


class TTSError(RuntimeError):
    pass


def prepare_tts_assets(config: TTSConfig) -> list[Path]:
    backend = config.backend.lower()
    if backend not in ("piper", "auto", "hinglish", "indicvoice"):
        return []

    try:
        from piper.download_voices import download_voice
    except Exception as exc:
        raise TTSError(f"Piper is not installed or available: {exc}") from exc

    voice_directory = resolve_path(config.piper_voice_directory)
    voice_directory.mkdir(parents=True, exist_ok=True)

    model_path = voice_directory / f"{config.piper_voice}.onnx"
    config_path = voice_directory / f"{config.piper_voice}.onnx.json"

    if (not model_path.exists()) or (model_path.stat().st_size == 0):
        try:
            download_voice(config.piper_voice, voice_directory)
        except Exception as exc:
            raise TTSError(f"Failed to download Piper voice '{config.piper_voice}': {exc}") from exc

    return [model_path, config_path]


@dataclass
class _TTSPlaybackItem:
    audio: np.ndarray | None
    sample_rate: int = 22050
    text: str = ""
    pause_after_ms: int = 80
    is_sentinel: bool = False


class TextToSpeechService:
    """High-speed sentence-level streaming TTS engine supporting Piper and SAPI5."""

    def __init__(self, config: TTSConfig) -> None:
        self.config = config
        self.engine_router = AutoRoutingTTSEngine(config)
        self._piper_voice: Any = None
        self._pyttsx3_engine: Any = None
        self._lock = threading.Lock()

        self._play_queue: queue.Queue[_TTSPlaybackItem] = queue.Queue()
        self._stop_event = threading.Event()
        self._is_speaking = threading.Event()

        # Dedicated worker thread for playing audio chunks smoothly
        self._playback_thread = threading.Thread(target=self._playback_loop, daemon=True)
        self._playback_thread.start()

    def warmup(self) -> None:
        """Pre-warm Piper model and SAPI5 fallback engine."""
        try:
            if self.config.backend.lower() in ("piper", "auto", "hinglish", "indicvoice"):
                self._get_piper_voice()
        except Exception:
            pass
        try:
            self._init_pyttsx3_engine()
        except Exception:
            pass

    def _init_pyttsx3_engine(self) -> Any:
        if self._pyttsx3_engine is None:
            try:
                import pythoncom
                pythoncom.CoInitialize()
            except Exception:
                pass
            try:
                import pyttsx3
                self._pyttsx3_engine = pyttsx3.init()
                self._pyttsx3_engine.setProperty("rate", self.config.rate)
                self._pyttsx3_engine.setProperty("volume", self.config.volume)
            except Exception:
                pass
        return self._pyttsx3_engine

    def speak(self, text: str) -> None:
        """Speak a complete string, automatically applying prosody analysis and streaming."""
        if not text.strip():
            return
        segments = global_prosody_engine.segment_speech_with_prosody(text)
        if not segments:
            segments = [ProsodySegment(text=text.strip())]

        for seg in segments:
            if self._stop_event.is_set():
                break
            self._synthesize_and_queue(
                seg.text,
                rate_multiplier=seg.rate_multiplier,
                pause_after_ms=seg.pause_after_ms,
            )

    def speak_sentence(self, sentence: str) -> None:
        """Speak a single sentence immediately with prosody."""
        clean = sentence.strip()
        if clean:
            segments = global_prosody_engine.segment_speech_with_prosody(clean, enable_fillers=False)
            if segments:
                for seg in segments:
                    self._synthesize_and_queue(
                        seg.text,
                        rate_multiplier=seg.rate_multiplier,
                        pause_after_ms=seg.pause_after_ms,
                    )
            else:
                self._synthesize_and_queue(clean)

    def stop(self) -> None:
        """Interrupt and stop all current and queued speech immediately."""
        self._stop_event.set()
        sd.stop()
        if hasattr(self, "engine_router"):
            self.engine_router.stop()
        # Drain play queue
        while not self._play_queue.empty():
            try:
                self._play_queue.get_nowait()
            except queue.Empty:
                break
        self._stop_event.clear()
        self._is_speaking.clear()

    def is_busy(self) -> bool:
        return self._is_speaking.is_set() or not self._play_queue.empty()

    def wait_until_done(self, timeout: float = 30.0) -> None:
        """Wait until all queued audio finishes playing."""
        import time

        start = time.monotonic()
        while self.is_busy():
            if time.monotonic() - start > timeout:
                break
            time.sleep(0.05)

    def split_sentences(self, text: str) -> list[str]:
        """Split text into spoken sentence fragments by punctuation."""
        raw_parts = re.split(r"(?<=[.?!;:\n])\s+", text)
        sentences = []
        for part in raw_parts:
            cleaned = part.strip()
            if cleaned:
                sentences.append(cleaned)
        return sentences

    def _synthesize_and_queue(
        self, sentence: str, rate_multiplier: float = 1.0, pause_after_ms: int = 80
    ) -> None:
        normalized = global_hinglish_normalizer.normalize_for_tts(sentence)
        try:
            audio, sample_rate = self.engine_router.synthesize(normalized, rate_multiplier=rate_multiplier)
            if audio is not None:
                self._play_queue.put(
                    _TTSPlaybackItem(
                        audio=audio,
                        sample_rate=sample_rate,
                        text=sentence,
                        pause_after_ms=pause_after_ms,
                    )
                )
        except Exception as exc:
            pass

    def _get_piper_voice(self) -> Any:
        if self._piper_voice is None:
            with self._lock:
                if self._piper_voice is None:
                    from piper import PiperVoice

                    model_path, config_path = prepare_tts_assets(self.config)
                    self._piper_voice = PiperVoice.load(model_path, config_path)
        return self._piper_voice

    def _speak_with_pyttsx3(self, text: str) -> None:
        try:
            import pythoncom

            pythoncom.CoInitialize()
        except Exception:
            pass

        try:
            import pyttsx3

            engine = pyttsx3.init()
            engine.setProperty("rate", self.config.rate)
            engine.setProperty("volume", self.config.volume)
            if self.config.voice_name:
                for v in engine.getProperty("voices"):
                    if self.config.voice_name.lower() in v.name.lower():
                        engine.setProperty("voice", v.id)
                        break
            engine.say(text)
            engine.runAndWait()
        except Exception:
            pass

    def _playback_loop(self) -> None:
        import time

        while True:
            item = self._play_queue.get()
            if item.is_sentinel:
                break
            if item.audio is not None and not self._stop_event.is_set():
                self._is_speaking.set()
                try:
                    sd.play(item.audio, samplerate=item.sample_rate)
                    # Responsive check every 15ms so barge-in cancels audio instantly
                    while not self._stop_event.is_set():
                        stream = sd.get_stream()
                        if stream is None or not stream.active:
                            break
                        time.sleep(0.015)
                    if self._stop_event.is_set():
                        sd.stop()
                    elif item.pause_after_ms > 0 and not self._play_queue.empty():
                        time.sleep(min(0.25, item.pause_after_ms / 1000.0))
                except Exception:
                    pass
                finally:
                    if self._play_queue.empty() or self._stop_event.is_set():
                        self._is_speaking.clear()
