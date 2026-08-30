"""Language detection, Hinglish normalization, and pronunciation layer for FRIDAY V4."""
from __future__ import annotations

from core.language.hinglish_normalizer import (
    AdvancedHinglishNormalizer,
    global_hinglish_normalizer,
)
from core.language.language_detector import LanguageCategory, LanguageDetector
from core.language.pronunciation import PronunciationLayer, global_pronunciation_layer

__all__ = [
    "LanguageCategory",
    "LanguageDetector",
    "PronunciationLayer",
    "global_pronunciation_layer",
    "AdvancedHinglishNormalizer",
    "global_hinglish_normalizer",
]
