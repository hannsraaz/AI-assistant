from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger("friday.voice.prosody")


class DialogueEmotion(str, Enum):
    NEUTRAL = "neutral"
    CONFIDENT = "confident"
    CURIOUS = "curious"
    URGENT = "urgent"
    RELAXED = "relaxed"
    EMPATHETIC = "empathetic"
    EXCITED = "excited"


@dataclass
class ProsodySegment:
    """A distinct phrase chunk with acoustic prosody parameters."""

    text: str
    rate_multiplier: float = 1.0
    pitch_offset: float = 0.0
    pause_after_ms: int = 100
    emotion: DialogueEmotion = DialogueEmotion.NEUTRAL
    is_filler: bool = False


class ProsodyEngine:
    """Conversational Prosody & Acoustic Expressiveness Engine.

    Transforms cold flat text into dynamic, human-like expressive speech:
    1. Detects dialogue sentiment, intent, and sentence mood.
    2. Modulates speaking rate, pitch inflection, and cadence.
    3. Injects realistic discourse markers and breathing micro-pauses.
    4. Formats acoustic tokens for local neural TTS (Piper/Kokoro/XTTS).
    """

    def __init__(self, default_rate: float = 1.0) -> None:
        self.default_rate = default_rate

    def detect_emotion(self, text: str) -> DialogueEmotion:
        """Heuristic acoustic emotion classifier based on syntax and vocabulary."""
        t = text.lower().strip()

        if t.endswith("?") or any(w in t for w in ("kya", "kaise", "kab", "how", "what", "why", "who", "where")):
            return DialogueEmotion.CURIOUS
        if "!" in text or any(w in t for w in ("awesome", "great", "shandaar", "badhiya", "ho gaya", "done!", "success")):
            return DialogueEmotion.EXCITED
        if any(w in t for w in ("error", "failed", "warning", "ruko", "stop", "danger", "critical")):
            return DialogueEmotion.URGENT
        if any(w in t for w in ("haan", "sure", "khol raha hoon", "launching", "opening", "bilkul")):
            return DialogueEmotion.CONFIDENT
        if any(w in t for w in ("sorry", "maaf", "issue", "problem", "cannot", "nahin ho paya")):
            return DialogueEmotion.EMPATHETIC
        return DialogueEmotion.NEUTRAL

    def add_conversational_discourse_markers(self, text: str, is_hinglish: bool = True) -> str:
        """Inject natural conversational openers if the sentence is too dry/formal."""
        clean = text.strip()
        if not clean:
            return clean

        # Do not add if already has conversational starter or is short
        first_word = clean.split()[0].lower().rstrip(",.!")
        starters = {"haan", "dekho", "achha", "well", "sure", "look", "okay", "alright", "yes", "no", "nahi"}
        if first_word in starters:
            return clean

        # Natural injection for action acknowledgements
        if is_hinglish:
            if any(w in clean.lower() for w in ("kar raha hoon", "khol raha", "ho gaya", "chalu kar")):
                return f"Haan, {clean}"
            if any(w in clean.lower() for w in ("bata raha hoon", "ye raha", "check kar")):
                return f"Dekho, {clean}"
        else:
            if clean.startswith("Opening") or clean.startswith("Launching"):
                return f"Sure, {clean}"
            if clean.startswith("Here is") or clean.startswith("I found"):
                return f"Well, {clean}"

        return clean

    def segment_speech_with_prosody(
        self, text: str, is_hinglish: bool = False, enable_fillers: bool = True
    ) -> list[ProsodySegment]:
        """Split text into acoustic segments with natural breathing pauses and rate variations."""
        if not text.strip():
            return []

        # 1. Clean markdown & code formatting
        cleaned = self._clean_for_speech(text)

        # 2. Add conversational opener if enabled
        if enable_fillers:
            cleaned = self.add_conversational_discourse_markers(cleaned, is_hinglish=is_hinglish)

        # 3. Detect dominant emotion
        emotion = self.detect_emotion(cleaned)

        # Base rate according to emotion
        rate_map = {
            DialogueEmotion.CONFIDENT: 1.05,
            DialogueEmotion.EXCITED: 1.10,
            DialogueEmotion.URGENT: 1.15,
            DialogueEmotion.CURIOUS: 1.00,
            DialogueEmotion.EMPATHETIC: 0.92,
            DialogueEmotion.RELAXED: 0.95,
            DialogueEmotion.NEUTRAL: 1.00,
        }
        base_rate = rate_map.get(emotion, 1.0) * self.default_rate

        # 4. Split by clause and punctuation boundaries
        # Split on commas, semicolons, dashes, periods, question marks
        raw_clauses = re.split(r"(?<=[.!?,;:])\s+", cleaned)
        segments: list[ProsodySegment] = []

        for i, clause in enumerate(raw_clauses):
            c = clause.strip()
            if not c:
                continue

            # Determine pause duration
            if c.endswith("?"):
                pause_ms = 220
                pitch_off = 0.08  # Rising question intonation
            elif c.endswith("!"):
                pause_ms = 180
                pitch_off = 0.05
            elif c.endswith((".", ":")):
                pause_ms = 150
                pitch_off = -0.03  # Falling terminal pitch
            elif c.endswith((",", ";")):
                pause_ms = 80  # Short clause micro-pause
                pitch_off = 0.01
            else:
                pause_ms = 100
                pitch_off = 0.0

            segments.append(
                ProsodySegment(
                    text=c,
                    rate_multiplier=round(base_rate, 2),
                    pitch_offset=pitch_off,
                    pause_after_ms=pause_ms,
                    emotion=emotion,
                )
            )

        return segments

    def _clean_for_speech(self, text: str) -> str:
        """Strip technical markup, markdown asterisks, backticks, and raw code."""
        t = re.sub(r"```[\s\S]*?```", " [code snippet omitted] ", text)
        t = re.sub(r"`([^`]+)`", r"\1", t)
        t = re.sub(r"\*\*([^*]+)\*\*", r"\1", t)
        t = re.sub(r"\*([^*]+)\*", r"\1", t)
        t = re.sub(r"#+\s*", "", t)
        t = re.sub(r"https?://\S+", "link", t)
        t = re.sub(r"[\\/][a-zA-Z0-9_\-./\\]+", "file path", t)
        t = re.sub(r"\s+", " ", t)
        return t.strip()


# Global Singleton Prosody Engine
global_prosody_engine = ProsodyEngine()
