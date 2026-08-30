from __future__ import annotations

import pytest

from core.language.language_detector import LanguageCategory, LanguageDetector
from core.language.hinglish_normalizer import AdvancedHinglishNormalizer, global_hinglish_normalizer
from core.language.pronunciation import PronunciationLayer, global_pronunciation_layer
from core.voice.tts_engine import AutoRoutingTTSEngine
from config import TTSConfig


class TestHinglishVoiceEngineSuite:
    """Comprehensive test suite for English, Hindi, Roman Hindi, Hinglish, and Technical Vocabulary."""

    def test_english_detection_and_normalization(self) -> None:
        texts = [
            "Open Chrome.",
            "Check my CPU usage.",
            "Build the Android project.",
        ]
        for t in texts:
            cat = LanguageDetector.detect(t)
            assert cat == LanguageCategory.ENGLISH
            norm = global_hinglish_normalizer.normalize_for_tts(t)
            if "Chrome" in t:
                assert "Chrome" in norm or "chrome" in norm.lower()
            if "CPU" in t:
                assert "CPU" in norm or "C P U" in norm

    def test_hindi_devanagari_detection_and_transliteration(self) -> None:
        texts = [
            "हाँ, मैं अभी आता हूँ।",
            "तुम कहाँ जा रहे हो?",
            "कंप्यूटर बंद कर दो।",
        ]
        for t in texts:
            cat = LanguageDetector.detect(t)
            assert cat == LanguageCategory.HINDI_DEVANAGARI
            norm = global_hinglish_normalizer.normalize_for_tts(t)
            assert len(norm) > 0

    def test_roman_hindi_detection_and_phonetics(self) -> None:
        texts = [
            "Haan main abhi aata hoon.",
            "Tum kaha ja rahe ho?",
            "Computer band kar do.",
        ]
        for t in texts:
            assert LanguageDetector.is_hinglish_or_hindi(t) is True
            norm = global_hinglish_normalizer.normalize_for_tts(t)
            assert len(norm) > 0

    def test_hinglish_code_mixing(self) -> None:
        texts = [
            ("Main abhi Android project build kar raha hoon.", "android", "build"),
            ("Chrome open kar do.", "chrome", "open"),
            ("GPU temperature check karo.", "gpu", "check"),
            ("GitHub pe latest changes push kar do.", "git", "push"),
        ]
        for text, tech1, tech2 in texts:
            cat = LanguageDetector.detect(text)
            assert cat in (
                LanguageCategory.HINGLISH_CODE_MIXED,
                LanguageCategory.MOSTLY_HINDI_WITH_TECHNICAL,
                LanguageCategory.MOSTLY_ENGLISH_WITH_HINDI,
            )
            norm = global_hinglish_normalizer.normalize_for_tts(text)
            norm_clean = norm.lower().replace("-", "").replace(" ", "")
            # Verify technical English terms are preserved accurately
            assert tech1 in norm_clean
            assert tech2 in norm_clean

    def test_technical_vocabulary_preservation(self) -> None:
        tech_cases = [
            "Open VS Code.",
            "Run the Gradle build.",
            "Check the GPU.",
            "Open GitHub.",
            "Start the Python script.",
        ]
        for case in tech_cases:
            norm = global_hinglish_normalizer.normalize_for_tts(case)
            if "VS Code" in case:
                assert "V S Code" in norm or "VS Code" in norm
            if "Gradle" in case:
                assert "Gradle" in norm or "Gray-dl" in norm
            if "GitHub" in case:
                assert "Git Hub" in norm or "GitHub" in norm
            if "Python" in case:
                assert "Python" in norm or "Pie-thon" in norm

    def test_pronunciation_layer_custom_override(self) -> None:
        layer = PronunciationLayer()
        layer._rules["K8s"] = "Kubernetes"
        res = layer.apply("Deploy this container on K8s cluster")
        assert "Kubernetes" in res

    def test_auto_routing_engine_selection(self) -> None:
        router = AutoRoutingTTSEngine(TTSConfig(engine="auto"))
        eng_en = router.select_engine_for_text("Open Chrome and check battery.")
        assert eng_en.name in ("piper", "sapi5")

        eng_hi = router.select_engine_for_text("Haan bhai, main VS Code khol deta hoon.")
        assert eng_hi.name in ("hinglish", "indicvoice", "piper")
