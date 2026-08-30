"""Backward compatibility alias for core.language.hinglish_normalizer and core.hinglish_normalizer."""
from __future__ import annotations

import re
from enum import Enum
from typing import Any

from core.language.hinglish_normalizer import AdvancedHinglishNormalizer, global_hinglish_normalizer
from core.language.language_detector import LanguageCategory, LanguageDetector
from core.voice.hinglish_phonetics import HinglishPhoneticEngine


class UserLanguage(str, Enum):
    ENGLISH = "ENGLISH"
    HINGLISH = "HINGLISH"
    HINDI_ROMAN = "HINDI_ROMAN"
    HINDI_DEVANAGARI = "HINDI_DEVANAGARI"


class HinglishNormalizer:
    """High-speed native Hinglish language detector, command normalizer, and TTS phonetics preprocessor."""

    HINDI_MARKER_WORDS = LanguageDetector.HINDI_MARKER_WORDS

    BACKCHANNEL_PHRASES = {
        "yeah", "yeh", "yep", "uh-huh", "uh huh", "uh-huh.", "okay", "ok",
        "hmm", "hmmm", "haan", "han", "ha", "theek hai", "thik hai",
        "achha", "accha", "sahi hai", "right", "sure", "got it",
    }

    INTERRUPTION_PHRASES = {
        "stop", "wait", "ruko", "ruk ja", "ruk jao", "band karo", "band kar",
        "bas", "actually", "cancel", "friday", "hey friday", "jarvis", "hey jarvis",
        "sun", "suno", "chup", "chup ho jao", "hold on", "pause",
    }

    @classmethod
    def detect_language(cls, text: str) -> UserLanguage:
        cat = LanguageDetector.detect(text)
        if cat == LanguageCategory.HINDI_DEVANAGARI:
            return UserLanguage.HINDI_DEVANAGARI
        if cat == LanguageCategory.HINDI_ROMAN:
            return UserLanguage.HINDI_ROMAN
        if cat in (LanguageCategory.HINGLISH_CODE_MIXED, LanguageCategory.MOSTLY_HINDI_WITH_TECHNICAL, LanguageCategory.MOSTLY_ENGLISH_WITH_HINDI):
            return UserLanguage.HINGLISH
        return UserLanguage.ENGLISH

    @classmethod
    def is_backchannel(cls, text: str) -> bool:
        clean = text.strip().lower().rstrip(".?!,")
        return clean in cls.BACKCHANNEL_PHRASES

    @classmethod
    def is_interruption(cls, text: str) -> bool:
        clean = text.strip().lower().rstrip(".?!,")
        if clean in cls.INTERRUPTION_PHRASES:
            return True
        return any(clean.startswith(prefix) for prefix in ["wait", "stop", "ruko", "band kar", "actually", "cancel"])

    @classmethod
    def normalize_hinglish_command(cls, query: str) -> tuple[str, bool, UserLanguage]:
        raw = query.strip()
        lowered = raw.lower().rstrip(".?!")
        lang = cls.detect_language(raw)
        is_hinglish = lang in (UserLanguage.HINGLISH, UserLanguage.HINDI_ROMAN, UserLanguage.HINDI_DEVANAGARI)

        # 1. App Launch / Open Patterns
        open_match = re.search(
            r"^(?:mera|meri|mere)?\s*(.+?)\s*(?:open kar(?: do|o)?|khol(?: do| de|na|o)?|kholo|chalao|chala do|launch kar(?: do|o)?)$",
            lowered,
            re.IGNORECASE,
        )
        if open_match:
            target = open_match.group(1).strip()
            target = re.sub(r"^(?:mera|meri|mere|ko|pe)\s+", "", target).strip()
            return f"open {target}", True, lang

        # 2. App Close / Kill Patterns
        close_match = re.search(
            r"^(?:mera|meri|mere)?\s*(.+?)\s*(?:close kar(?: do|o)?|band kar(?: do|o)?|band karo|kill kar(?: do|o)?|hata do)$",
            lowered,
            re.IGNORECASE,
        )
        if close_match:
            target = close_match.group(1).strip()
            target = re.sub(r"^(?:mera|meri|mere|ko|pe)\s+", "", target).strip()
            return f"close {target}", True, lang

        # 3. Audio & Volume Patterns
        if re.search(r"\b(?:aawaz badhao|volume badha(?: do)?|volume up kar(?: do)?|sound badhao)\b", lowered):
            return "volume up", True, lang

        if re.search(r"\b(?:aawaz kam karo|volume kam kar(?: do)?|volume down kar(?: do)?|sound kam karo|dheemi karo)\b", lowered):
            return "volume down", True, lang

        if re.search(r"\b(?:chup ho jao|mute kar(?: do)?|aawaz band kar(?: do)?|sound band karo)\b", lowered):
            return "mute", True, lang

        if re.search(r"\b(?:unmute kar(?: do)?|aawaz chalu karo|sound chalu karo)\b", lowered):
            return "unmute", True, lang

        vol_set_match = re.search(
            r"\b(?:volume|aawaz)\s*(?:ko)?\s*(\d{1,3})\s*(?:percent|pe)?\s*(?:kar(?: do)?|set karo|rakho)\b",
            lowered,
        )
        if vol_set_match:
            percent = vol_set_match.group(1)
            return f"set volume {percent}", True, lang

        # 4. Brightness Patterns
        if re.search(r"\b(?:brightness badhao|screen bright karo|roshni badhao)\b", lowered):
            return "brightness up", True, lang

        if re.search(r"\b(?:brightness kam karo|screen dim karo|roshni kam karo)\b", lowered):
            return "brightness down", True, lang

        bright_set_match = re.search(
            r"\bbrightness\s*(?:ko)?\s*(\d{1,3})\s*(?:percent|pe)?\s*(?:kar(?: do)?|set karo|rakho)\b",
            lowered,
        )
        if bright_set_match:
            percent = bright_set_match.group(1)
            return f"set brightness {percent}", True, lang

        # 5. Screenshot & Screen
        if re.search(r"\b(?:screenshot le(?: lo| lena)?|screen capture kar(?: do)?|screenshot khinch(?: lo)?)\b", lowered):
            return "take a screenshot", True, lang

        # 6. Windows & Desktop Management
        if re.search(r"\b(?:desktop dikhao|sab minimize kar(?: do)?|sab hata do)\b", lowered):
            return "show desktop", True, lang

        if re.search(r"\b(?:kaun kaun si window khuli hai|open windows dikhao|windows list kar)\b", lowered):
            return "what windows are open", True, lang

        if re.search(r"\b(?:kaun kaun se app khule hain|open apps dikhao|apps list kar)\b", lowered):
            return "what applications are open", True, lang

        # 7. Time & Date
        if re.search(r"\b(?:time kya hua(?: hai)?|kitne baje hain|time batao|kitna time ho raha hai)\b", lowered):
            return "time", True, lang

        if re.search(r"\b(?:aaj kya date hai|aaj ki date|aaj kaun sa din hai|tarikh kya hai)\b", lowered):
            return "date", True, lang

        # 8. Notes
        read_notes = re.search(r"\b(?:notes padho|mere notes batao|notes dikhao)\b", lowered)
        if read_notes:
            return "read notes", True, lang

        add_note = re.search(r"\b(?:note likho|likh lo|yaad rakhna)\s*[:]?\s*(.+)", raw, re.IGNORECASE)
        if add_note:
            return f"take a note: {add_note.group(1).strip()}", True, lang

        # 9. Search & YouTube
        yt_match = re.search(r"\b(.+?)\s*(?:youtube pe (?:chalao|search kar|play karo)|pe chalao)\b", raw, re.IGNORECASE)
        if yt_match:
            return f"play {yt_match.group(1).strip()} on youtube", True, lang

        return raw, is_hinglish, lang

    @classmethod
    def normalize_for_tts(cls, text: str) -> str:
        return global_hinglish_normalizer.normalize_for_tts(text)
