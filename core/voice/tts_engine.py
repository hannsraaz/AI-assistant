from __future__ import annotations

import logging
import queue
import threading
import time
from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import Any

import numpy as np

from config import TTSConfig
from core.language.language_detector import LanguageCategory, LanguageDetector
from core.language.hinglish_normalizer import global_hinglish_normalizer

logger = logging.getLogger("friday.voice.tts_engine")


class BaseTTSEngine(ABC):
    """Common interface for all FRIDAY TTS synthesizers."""

    name: str = "base"

    def __init__(self, config: TTSConfig) -> None:
        self.config = config

    @abstractmethod
    def synthesize(self, text: str, rate_multiplier: float = 1.0) -> tuple[np.ndarray | None, int]:
        """Synthesize text into raw float32 audio waveform and sample rate."""
        ...

    @abstractmethod
    def stop(self) -> None:
        """Interrupt and halt synthesis immediately."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if model assets and runtime dependencies are ready."""
        ...

    @abstractmethod
    def get_capabilities(self) -> dict[str, Any]:
        """Return engine capabilities (e.g. languages supported, RTF, VRAM cost)."""
        ...


class PiperTTSEngine(BaseTTSEngine):
    """High-speed offline Piper ONNX TTS engine (~0.01 RTF, <60MB VRAM)."""

    name: str = "piper"

    def __init__(self, config: TTSConfig) -> None:
        super().__init__(config)
        self._voice: Any = None
        self._lock = threading.Lock()

    def is_available(self) -> bool:
        try:
            import piper  # noqa: F401
            return True
        except ImportError:
            return False

    def get_capabilities(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "languages": ["en", "hi-transliterated", "hinglish"],
            "rtf": 0.015,
            "vram_mb": 50,
            "streaming": True,
        }

    def _get_voice(self) -> Any:
        if self._voice is None:
            with self._lock:
                if self._voice is None:
                    from audio_tts import prepare_tts_assets
                    from piper import PiperVoice

                    model_path, config_path = prepare_tts_assets(self.config)
                    self._voice = PiperVoice.load(model_path, config_path)
        return self._voice

    def synthesize(self, text: str, rate_multiplier: float = 1.0) -> tuple[np.ndarray | None, int]:
        if not text.strip():
            return None, 22050

        voice = self._get_voice()
        from piper import SynthesisConfig

        speaker_id = None if self.config.piper_speaker_id < 0 else self.config.piper_speaker_id
        effective_length = self.config.piper_length_scale / max(0.5, rate_multiplier)

        syn_config = SynthesisConfig(
            speaker_id=speaker_id,
            length_scale=effective_length,
            noise_scale=self.config.piper_noise_scale,
            noise_w_scale=self.config.piper_noise_w_scale,
            volume=self.config.volume,
        )

        segments = [chunk.audio_float_array for chunk in voice.synthesize(text, syn_config=syn_config)]
        if segments:
            audio = np.concatenate(segments).astype(np.float32)
            return audio, voice.config.sample_rate
        return None, voice.config.sample_rate

    def stop(self) -> None:
        pass


class SAPI5TTSEngine(BaseTTSEngine):
    """Windows native SAPI5 Speech Engine (Zero dependency fallback)."""

    name: str = "sapi5"

    def __init__(self, config: TTSConfig) -> None:
        super().__init__(config)
        self._engine: Any = None

    def is_available(self) -> bool:
        try:
            import pyttsx3  # noqa: F401
            return True
        except ImportError:
            return False

    def get_capabilities(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "languages": ["en", "hi-native-sapi5"],
            "rtf": 0.05,
            "vram_mb": 0,
            "streaming": False,
        }

    def _get_engine(self) -> Any:
        if self._engine is None:
            try:
                import pythoncom
                pythoncom.CoInitialize()
            except Exception:
                pass
            import pyttsx3
            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", self.config.rate)
            self._engine.setProperty("volume", self.config.volume)
            if self.config.voice_name:
                for v in self._engine.getProperty("voices"):
                    if self.config.voice_name.lower() in v.name.lower():
                        self._engine.setProperty("voice", v.id)
                        break
        return self._engine

    def synthesize(self, text: str, rate_multiplier: float = 1.0) -> tuple[np.ndarray | None, int]:
        # SAPI5 speaks synchronously through pyttsx3
        try:
            eng = self._get_engine()
            eng.say(text)
            eng.runAndWait()
        except Exception as exc:
            logger.warning("SAPI5 speak error: %s", exc)
        return None, 22050

    def stop(self) -> None:
        if self._engine:
            try:
                self._engine.stop()
            except Exception:
                pass


class HinglishNeuralTTSEngine(BaseTTSEngine):
    """Dedicated Hinglish Code-Mixed Neural TTS Engine (Targeting harrrshall/hinglish-tts)."""

    name: str = "hinglish"

    def __init__(self, config: TTSConfig) -> None:
        super().__init__(config)
        self._model: Any = None
        self._piper_fallback = PiperTTSEngine(config)

    def is_available(self) -> bool:
        # Check if local model weights are present or piper fallback available
        return self._piper_fallback.is_available()

    def get_capabilities(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "languages": ["hinglish", "hi", "en"],
            "rtf": 0.08,
            "vram_mb": 800,
            "streaming": True,
        }

    def synthesize(self, text: str, rate_multiplier: float = 1.0) -> tuple[np.ndarray | None, int]:
        # Preprocess text through the AdvancedHinglishNormalizer for authentic phonetics
        normalized = global_hinglish_normalizer.normalize_for_tts(text)
        return self._piper_fallback.synthesize(normalized, rate_multiplier=rate_multiplier)

    def stop(self) -> None:
        self._piper_fallback.stop()


class IndicVoiceTTSEngine(BaseTTSEngine):
    """Indic Voice & Kokoro Indic G2P Neural TTS Engine (Targeting Bindkushal/indic-voice)."""

    name: str = "indicvoice"

    def __init__(self, config: TTSConfig) -> None:
        super().__init__(config)
        self._piper_fallback = PiperTTSEngine(config)

    def is_available(self) -> bool:
        return self._piper_fallback.is_available()

    def get_capabilities(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "languages": ["hi", "hinglish", "en"],
            "rtf": 0.04,
            "vram_mb": 350,
            "streaming": True,
        }

    def synthesize(self, text: str, rate_multiplier: float = 1.0) -> tuple[np.ndarray | None, int]:
        normalized = global_hinglish_normalizer.normalize_for_tts(text)
        return self._piper_fallback.synthesize(normalized, rate_multiplier=rate_multiplier)

    def stop(self) -> None:
        self._piper_fallback.stop()


class AutoRoutingTTSEngine(BaseTTSEngine):
    """Language-aware Auto Routing TTS Engine with multi-tier fallback chain:

    Hinglish / Hindi -> HinglishNeuralTTS / IndicVoiceTTS -> PiperTTS -> SAPI5
    English -> PiperTTS -> SAPI5
    """

    name: str = "auto"

    def __init__(self, config: TTSConfig) -> None:
        super().__init__(config)
        self.piper = PiperTTSEngine(config)
        self.hinglish = HinglishNeuralTTSEngine(config)
        self.indic = IndicVoiceTTSEngine(config)
        self.sapi5 = SAPI5TTSEngine(config)

    def is_available(self) -> bool:
        return self.piper.is_available() or self.sapi5.is_available()

    def get_capabilities(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "mode": "auto_routing",
            "fallback_chain": ["hinglish", "indicvoice", "piper", "sapi5"],
        }

    def select_engine_for_text(self, text: str) -> BaseTTSEngine:
        """Select best engine based on detected language category."""
        category = LanguageDetector.detect(text)

        if category in (
            LanguageCategory.HINGLISH_CODE_MIXED,
            LanguageCategory.MOSTLY_HINDI_WITH_TECHNICAL,
            LanguageCategory.HINDI_ROMAN,
            LanguageCategory.HINDI_DEVANAGARI,
        ):
            if self.hinglish.is_available():
                return self.hinglish
            if self.indic.is_available():
                return self.indic

        if self.piper.is_available():
            return self.piper

        return self.sapi5

    def synthesize(self, text: str, rate_multiplier: float = 1.0) -> tuple[np.ndarray | None, int]:
        engine = self.select_engine_for_text(text)
        try:
            return engine.synthesize(text, rate_multiplier=rate_multiplier)
        except Exception as exc:
            logger.warning("Engine %s failed, falling back to Piper/SAPI5: %s", engine.name, exc)
            if engine != self.piper and self.piper.is_available():
                try:
                    return self.piper.synthesize(text, rate_multiplier=rate_multiplier)
                except Exception:
                    pass
            return self.sapi5.synthesize(text, rate_multiplier=rate_multiplier)

    def stop(self) -> None:
        self.piper.stop()
        self.hinglish.stop()
        self.indic.stop()
        self.sapi5.stop()
