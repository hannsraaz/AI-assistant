from __future__ import annotations

import re
from enum import Enum


class LanguageCategory(str, Enum):
    ENGLISH = "ENGLISH"
    HINDI_DEVANAGARI = "HINDI_DEVANAGARI"
    HINDI_ROMAN = "HINDI_ROMAN"
    HINGLISH_CODE_MIXED = "HINGLISH_CODE_MIXED"
    MOSTLY_ENGLISH_WITH_HINDI = "MOSTLY_ENGLISH_WITH_HINDI"
    MOSTLY_HINDI_WITH_TECHNICAL = "MOSTLY_HINDI_WITH_TECHNICAL"


class LanguageDetector:
    """Intelligent language classifier for English, Hindi (Devanagari/Roman), and code-mixed Hinglish."""

    HINDI_MARKER_WORDS = {
        "mera", "meri", "mere", "tera", "teri", "tere", "khol", "kholo", "kholna",
        "chalao", "chala", "chalu", "kar", "karo", "karna", "karein", "karen",
        "karoon", "karta", "karti", "karte", "hai", "hain", "hoon", "hun", "tha",
        "thi", "thay", "kya", "kyun", "kyu", "kaise", "kaisa", "kaisi", "kab",
        "kahan", "yahan", "wahan", "jahan", "batao", "bata", "batana", "bataiye",
        "mein", "mai", "ruko", "ruk", "suno", "dhoond", "dhoondo", "dikhao", "dikha",
        "badhao", "ghatao", "band", "chup", "kitna", "kitni", "kitne",
        "aaj", "kal", "parso", "thoda", "thodi", "zyada", "jyada", "bhai", "yaar",
        "sahab", "kuch", "abhi", "kabhi", "theek", "thik", "achha",
        "accha", "achhi", "acchi", "bilkul", "zaroor", "jarur", "matlab", "lekin",
        "magar", "shandaar", "badhiya", "namaste", "shukriya", "dhanyawad", "dhanyavaad",
        "arre", "waise", "bolo", "rakho", "milte",
        "tum", "hum", "aap", "kaha", "jao", "jaate", "aata", "aati",
        "aate", "hoga", "hogi", "hoge", "gaya", "gayi", "gaye",
    }

    TECHNICAL_ENGLISH_WORDS = {
        "vs", "code", "studio", "android", "chrome", "spotify", "git", "github",
        "branch", "commit", "push", "pull", "merge", "build", "gradle", "apk",
        "terminal", "command", "powershell", "python", "pytest", "ram", "cpu",
        "gpu", "vram", "disk", "battery", "percent", "volume", "brightness",
        "wifi", "bluetooth", "windows", "youtube", "google", "browser", "search",
        "screenshot", "camera", "desktop", "folder", "file", "files", "app",
        "application", "task", "planner", "status", "error", "warning", "success",
        "note", "notes", "clock", "timer", "alarm", "reminder", "system", "setting",
        "settings", "mode", "device", "keyboard", "mouse", "screen", "monitor",
        "audio", "video", "network", "ping", "server", "client", "ollama", "llm",
    }

    @classmethod
    def detect(cls, text: str) -> LanguageCategory:
        """Classify input text into LanguageCategory."""
        clean = text.strip()
        if not clean:
            return LanguageCategory.ENGLISH

        # 1. Check for Devanagari Unicode
        if re.search(r"[\u0900-\u097F]", clean):
            return LanguageCategory.HINDI_DEVANAGARI

        # 2. Tokenize lowercase words
        words = re.findall(r"\b[a-zA-Z]+\b", clean.lower())
        if not words:
            return LanguageCategory.ENGLISH

        word_set = set(words)
        hindi_count = len(word_set.intersection(cls.HINDI_MARKER_WORDS))
        tech_count = len(word_set.intersection(cls.TECHNICAL_ENGLISH_WORDS))
        total_unique = len(word_set)

        if hindi_count == 0:
            return LanguageCategory.ENGLISH

        hindi_ratio = hindi_count / total_unique

        if tech_count > 0 and hindi_count > 0:
            if hindi_ratio >= 0.5:
                return LanguageCategory.MOSTLY_HINDI_WITH_TECHNICAL
            return LanguageCategory.HINGLISH_CODE_MIXED

        if hindi_ratio >= 0.7:
            return LanguageCategory.HINDI_ROMAN

        if hindi_ratio >= 0.3:
            return LanguageCategory.HINGLISH_CODE_MIXED

        return LanguageCategory.MOSTLY_ENGLISH_WITH_HINDI

    @classmethod
    def is_hinglish_or_hindi(cls, text: str) -> bool:
        """Convenience method returning whether text requires Hindi/Hinglish speech processing."""
        cat = cls.detect(text)
        return cat != LanguageCategory.ENGLISH
