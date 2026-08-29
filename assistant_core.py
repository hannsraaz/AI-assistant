from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from typing import Any

from audio_stt import SpeechToTextService
from audio_tts_xtts import XTTSStreamingTTS
from config import AppConfig
from desktop_controller import DesktopController
from intent_router import IntentRouter
from llm_agent import OllamaClient
from wake_word import WakeWordDetector, WakeWordError


StatusCallback = Callable[[str], None]
TextCallback = Callable[[str], None]


class VoiceAssistant:
    """Core coordinator for Friday voice assistant."""

    def __init__(
        self,
        config: AppConfig,
        logger: logging.Logger | None = None,
        on_status: StatusCallback | None = None,
        on_transcript: TextCallback | None = None,
        on_response: TextCallback | None = None,
        on_state: StatusCallback | None = None,
    ) -> None:
        self.config = config
        self.logger = logger or logging.getLogger("friday")
        self.on_status = on_status or (lambda _: None)
        self.on_transcript = on_transcript or (lambda _: None)
        self.on_response = on_response or (lambda _: None)
        self.on_state = on_state or (lambda _: None)

        self.desktop = DesktopController(config.desktop)
        self.router = IntentRouter(config=config, desktop=self.desktop, on_timer_alert=self._on_timer_alert)
        self.llm = OllamaClient(config.llm)
        self.tts = XTTSStreamingTTS(config.tts)
        self.stt = SpeechToTextService(config.stt)
        self.wake_word = WakeWordDetector(config.wake_word, self.logger)

        self._running = threading.Event()
        self._processing = threading.Event()
        self._history: list[dict[str, str]] = []
        self._max_history = 6

    def start(self) -> None:
        if self._running.is_set():
            return
        self._running.set()
        self._set_state("idle", "Starting Friday...")

        # Background warmup of STT and TTS models
        threading.Thread(target=self._warmup, daemon=True).start()

        if self.config.wake_word.enabled:
            try:
                self.wake_word.start(self._on_wake_word)
                self._set_state("idle", f"Listening for '{self.config.wake_word_phrase}'...")
            except WakeWordError as exc:
                self.logger.warning("Wake word error: %s", exc)
                self._set_state("idle", "Wake word inactive. Click orb or press Talk Now.")

    def stop(self) -> None:
        self._running.clear()
        self.wake_word.stop()
        self.tts.stop()
        self._set_state("idle", "Friday stopped.")

    def cancel(self) -> None:
        """Interrupt and cancel any current speech or processing."""
        self.tts.stop()
        self._processing.clear()
        self._set_state("idle", f"Ready. Say '{self.config.wake_word_phrase}'.")

    def capture_voice_once(self) -> None:
        """Manually trigger one voice listening round (e.g. from UI button)."""
        if self._processing.is_set():
            return
        threading.Thread(target=self._voice_roundtrip, daemon=True).start()

    def submit_text(self, query: str) -> None:
        """Process a text prompt."""
        if not query.strip() or self._processing.is_set():
            return
        threading.Thread(target=self._handle_query, args=(query,), daemon=True).start()

    def handle_query(self, query: str) -> str:
        """Synchronously handle a query and return response string."""
        return self._handle_query_sync(query)

    def handle_query_with_timing(self, query: str) -> str:
        """Synchronously handle a query, synthesize speech, and return response."""
        return self._handle_query_sync(query)

    def _handle_query_sync(self, query: str) -> str:
        self._emit_transcript(query)
        self._set_state("thinking", "Processing...")

        # 1. Fast-Path Intent Router (<50ms execution)
        intent = self.router.route(query)
        if intent.handled:
            response = intent.response
            self._emit_response(response)
            self._set_state("speaking", response)
            if self.config.speak_responses:
                self.tts.speak(response)
                self.tts.wait_until_done()
            self._record_turn(query, response)
            self._set_state("idle", f"Ready. Say '{self.config.wake_word_phrase}'.")
            return response

        # 2. Local LLM Generation with Real-Time Sentence-Level TTS Streaming
        full_response_text = ""
        self._emit_response("")
        self._set_state("speaking", "Thinking and speaking...")

        for sentence, accumulated in self.llm.stream_sentences(query, history=self._history):
            full_response_text = accumulated
            self._emit_response(accumulated)
            if self.config.speak_responses:
                self.tts.speak_sentence(sentence)

        if not full_response_text.strip():
            full_response_text = "I'm sorry, I could not generate a response from the local model."
            self._emit_response(full_response_text)
            if self.config.speak_responses:
                self.tts.speak(full_response_text)

        if self.config.speak_responses:
            self.tts.wait_until_done()

        self._record_turn(query, full_response_text)
        self._set_state("idle", f"Ready. Say '{self.config.wake_word_phrase}'.")
        return full_response_text

    def _warmup(self) -> None:
        try:
            self.stt.warmup()
            self.logger.info("STT model warmed up.")
        except Exception as exc:
            self.logger.warning("STT warmup failed: %s", exc)

        try:
            self.llm.ensure_ollama_running()
        except Exception:
            pass

    def _on_wake_word(self) -> None:
        if not self._running.is_set() or self._processing.is_set():
            return
        threading.Thread(target=self._voice_roundtrip, daemon=True).start()

    def _voice_roundtrip(self) -> None:
        self._processing.set()
        self.tts.stop()

        # Stop wake word during microphone capture to release device cleanly
        if self._running.is_set() and self.config.wake_word.enabled:
            self.wake_word.stop()

        try:
            self._set_state("listening", "Listening for your command...")
            transcript = self.stt.listen_once(on_status=lambda msg: self._set_state("listening", msg))

            if not transcript:
                self._set_state("idle", f"Didn't catch that. Say '{self.config.wake_word_phrase}'.")
                return

            self._handle_query(transcript)
        except Exception as exc:
            self.logger.exception("Voice capture failed: %s", exc)
            self._set_state("idle", f"Audio input error: {exc}")
        finally:
            self._processing.clear()
            if self._running.is_set() and self.config.wake_word.enabled:
                try:
                    self.wake_word.start(self._on_wake_word)
                except Exception:
                    pass

    def _handle_query(self, query: str) -> None:
        if not self._processing.is_set():
            self._processing.set()

        self._emit_transcript(query)
        self._set_state("thinking", "Processing...")

        try:
            # 1. Fast-Path Intent Router (<50ms execution)
            intent = self.router.route(query)
            if intent.handled:
                response = intent.response
                self._emit_response(response)
                self._set_state("speaking", response)
                if self.config.speak_responses:
                    self.tts.speak(response)
                    self.tts.wait_until_done()

                self._record_turn(query, response)
                if intent.should_exit:
                    self.stop()
                    return

                self._set_state("idle", f"Ready. Say '{self.config.wake_word_phrase}'.")
                return

            # 2. Local LLM Generation with Real-Time Sentence-Level TTS Streaming
            full_response_text = ""
            self._emit_response("")
            self._set_state("speaking", "Thinking and speaking...")

            for sentence, accumulated in self.llm.stream_sentences(query, history=self._history):
                full_response_text = accumulated
                self._emit_response(accumulated)
                if self.config.speak_responses:
                    self.tts.speak_sentence(sentence)

            if not full_response_text.strip():
                full_response_text = "I'm sorry, I could not generate a response from the local model."
                self._emit_response(full_response_text)
                if self.config.speak_responses:
                    self.tts.speak(full_response_text)

            if self.config.speak_responses:
                self.tts.wait_until_done()

            self._record_turn(query, full_response_text)
            self._set_state("idle", f"Ready. Say '{self.config.wake_word_phrase}'.")
        except Exception as exc:
            self.logger.exception("Error processing query: %s", exc)
            err_msg = f"Something went wrong: {exc}"
            self._emit_response(err_msg)
            self._set_state("idle", err_msg)
        finally:
            self._processing.clear()

    def _record_turn(self, user_msg: str, bot_msg: str) -> None:
        self._history.append({"role": "user", "content": user_msg})
        self._history.append({"role": "assistant", "content": bot_msg})
        if len(self._history) > self._max_history * 2:
            self._history = self._history[-(self._max_history * 2) :]

    def _on_timer_alert(self, message: str) -> None:
        self._emit_response(message)
        self._set_state("speaking", message)
        if self.config.speak_responses:
            self.tts.speak(message)
            self.tts.wait_until_done()
        self._set_state("idle", f"Ready. Say '{self.config.wake_word_phrase}'.")

    def _set_state(self, state: str, status_msg: str) -> None:
        try:
            self.on_state(state)
            self.on_status(status_msg)
        except Exception:
            pass

    def _emit_transcript(self, text: str) -> None:
        try:
            self.on_transcript(text)
        except Exception:
            pass

    def _emit_response(self, text: str) -> None:
        try:
            self.on_response(text)
        except Exception:
            pass


AssistantCore = VoiceAssistant

