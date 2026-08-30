from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from core.language.language_detector import LanguageCategory, LanguageDetector
from core.language.pronunciation import global_pronunciation_layer
from core.voice.hinglish_phonetics import HinglishPhoneticEngine

logger = logging.getLogger("friday.language.normalizer")


class AdvancedHinglishNormalizer:
    """Context-aware Hinglish, Hindi, and English text normalizer for FRIDAY V4."""

    HINDI_DICT_PATH = Path("data/language/hindi_dictionary.json")
    HINGLISH_DICT_PATH = Path("data/language/hinglish_dictionary.json")

    def __init__(self) -> None:
        self.hindi_dict: dict[str, str] = self._load_json(self.HINDI_DICT_PATH)
        self.hinglish_dict: dict[str, str] = self._load_json(self.HINGLISH_DICT_PATH)

    def _load_json(self, path: Path) -> dict[str, str]:
        if path.exists():
            try:
                with path.open("r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as exc:
                logger.warning("Failed to load dictionary from %s: %s", path, exc)
        return {}

    def reload_dictionaries(self) -> None:
        self.hindi_dict = self._load_json(self.HINDI_DICT_PATH)
        self.hinglish_dict = self._load_json(self.HINGLISH_DICT_PATH)
        global_pronunciation_layer.reload()

    def normalize_for_tts(self, text: str) -> str:
        """Complete multi-stage speech normalization pipeline."""
        if not text.strip():
            return text

        formatted = text

        # 1. Expand numbers and symbols
        formatted = re.sub(r"(\d+)\s*%", r"\1 percent", formatted)
        formatted = re.sub(r"(\d+)\s*°\s*C", r"\1 degree celsius", formatted)
        formatted = re.sub(r"https?://\S+", "link", formatted)
        formatted = re.sub(r"[\\/][a-zA-Z0-9_\-./\\]+", "file path", formatted)

        # 2. Apply pronunciation layer (handles VS Code, Ollama, GPU, Wi-Fi, etc.)
        formatted = global_pronunciation_layer.apply(formatted)

        # 3. Apply compound Hinglish phrase substitutions
        for phrase, phon in self.hinglish_dict.items():
            pattern = re.compile(rf"\b{re.escape(phrase)}\b", re.IGNORECASE)
            formatted = pattern.sub(phon, formatted)

        # 4. Apply word-level phonetic transliteration (with technical word protection)
        formatted = HinglishPhoneticEngine.transliterate_for_tts(formatted)

        # 5. Clean extra spaces
        formatted = re.sub(r"\s+", " ", formatted).strip()
        return formatted

    def to_devanagari_words(self, text: str) -> str:
        """Convert Roman Hindi words into Devanagari while leaving technical English words intact."""
        words = text.split()
        result = []
        for w in words:
            clean_w = w.lower().strip(".,!?:;")
            punct_suffix = w[len(clean_w):] if len(w) > len(clean_w) else ""
            if clean_w in HinglishPhoneticEngine.PROTECTED_TECHNICAL_WORDS:
                result.append(w)
            elif clean_w in self.hindi_dict:
                result.append(self.hindi_dict[clean_w] + punct_suffix)
            else:
                result.append(w)
        return " ".join(result)


# Global singleton normalizer
global_hinglish_normalizer = AdvancedHinglishNormalizer()
