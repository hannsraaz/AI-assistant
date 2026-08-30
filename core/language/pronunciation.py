from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger("friday.language.pronunciation")


class PronunciationLayer:
    """Configurable pronunciation and technical vocabulary correction layer."""

    DEFAULT_DICT_PATH = Path("data/language/pronunciation_dictionary.json")

    def __init__(self, dict_path: str | Path | None = None) -> None:
        self.dict_path = Path(dict_path) if dict_path else self.DEFAULT_DICT_PATH
        self._rules: dict[str, str] = self._load_dictionary()

    def _load_dictionary(self) -> dict[str, str]:
        if self.dict_path.exists():
            try:
                with self.dict_path.open("r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as exc:
                logger.warning("Failed to load pronunciation dictionary from %s: %s", self.dict_path, exc)
        return {}

    def reload(self) -> None:
        self._rules = self._load_dictionary()

    def add_override(self, word: str, phonetic_spelling: str) -> None:
        """Add or update a pronunciation override."""
        self._rules[word] = phonetic_spelling
        try:
            self.dict_path.parent.mkdir(parents=True, exist_ok=True)
            with self.dict_path.open("w", encoding="utf-8") as f:
                json.dump(self._rules, f, indent=2)
        except Exception as exc:
            logger.error("Failed to save pronunciation dictionary: %s", exc)

    def apply(self, text: str) -> str:
        """Apply pronunciation overrides to text."""
        if not text.strip() or not self._rules:
            return text

        result = text
        # Match multi-word overrides first (e.g. "VS Code" before "VS")
        sorted_keys = sorted(self._rules.keys(), key=len, reverse=True)
        for key in sorted_keys:
            replacement = self._rules[key]
            # Word boundary regex with case-preservation
            pattern = re.compile(rf"\b{re.escape(key)}\b", re.IGNORECASE)
            result = pattern.sub(replacement, result)

        return result


# Global singleton pronunciation layer
global_pronunciation_layer = PronunciationLayer()
