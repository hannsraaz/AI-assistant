from __future__ import annotations

import logging
import threading
import time
import uuid
from collections.abc import Callable
from enum import Enum
from typing import Any

from audio_stt import SpeechToTextService
from audio_stream import ContinuousAudioCapture, get_global_audio_capture
from audio_tts_xtts import XTTSStreamingTTS
from config import AppConfig
from core.agent import AgenticPlanner, TaskManager, register_task_tools
from core.automation import (
    PersistentScheduler,
    ProactiveMonitor,
    WorkflowEngine,
    register_automation_tools,
)
from core.memory import MemoryManager, register_memory_tools
from core.response_engine import ResponseEngine
from core.telemetry import TurnTelemetry, global_telemetry
from core.tools.browser import register_browser_tools
from core.tools.developer import register_developer_tools
from core.tools.files import register_file_tools
from core.tools.input import register_input_tools
from core.tools.permissions import PermissionManager
from core.tools.registry import ToolRegistry
from core.tools.vision import register_vision_tools
from core.tools.windows import register_windows_tools
from desktop_controller import DesktopController
from intent_router import IntentRouter
from llm_agent import OllamaClient
from wake_word import WakeWordDetector, WakeWordError


class AssistantState(str, Enum):
    IDLE = "idle"
    LISTENING_FOR_WAKE = "listening_for_wake"
    WAKE_DETECTED = "wake_detected"
    LISTENING_FOR_COMMAND = "listening_for_command"
    TRANSCRIBING = "transcribing"
    THINKING = "thinking"
    EXECUTING = "executing"
    WAITING_FOR_CONFIRMATION = "waiting_for_confirmation"
    SPEAKING = "speaking"
    INTERRUPTED = "interrupted"
    BACKGROUND_TASK = "background_task"
    ERROR = "error"


StatusCallback = Callable[[str], None]
TextCallback = Callable[[str], None]
StateCallback = Callable[[AssistantState], None]


class VoiceAssistant:
    """Core coordinator for Friday V3.1 with continuous audio pipeline and instant wake-word reliability."""

    def __init__(
        self,
        config: AppConfig,
        logger: logging.Logger | None = None,
        on_status: StatusCallback | None = None,
        on_transcript: TextCallback | None = None,
        on_response: TextCallback | None = None,
        on_state: StateCallback | Callable[[str], None] | None = None,
    ) -> None:
        self.config = config
        self.logger = logger or logging.getLogger("friday")
        self.on_status = on_status or (lambda _: None)
        self.on_transcript = on_transcript or (lambda _: None)
        self.on_response = on_response or (lambda _: None)
        self.on_state = on_state or (lambda _: None)

        self._state = AssistantState.IDLE
        self._cancellation_token = threading.Event()

        # 1. Continuous Audio Pipeline (Opened once at startup)
        self.audio_capture = get_global_audio_capture(
            sample_rate=self.config.stt.sample_rate,
            device_index=self.config.wake_word.device_index,
        )

        # 2. Tool Infrastructure & Subsystems
        self.permissions = PermissionManager()
        self.registry = ToolRegistry(permission_manager=self.permissions)

        register_windows_tools(self.registry, screenshot_dir=self.config.desktop.screenshot_directory)
        register_file_tools(self.registry)
        register_vision_tools(self.registry)
        register_input_tools(self.registry)
        register_browser_tools(self.registry)
        register_developer_tools(self.registry)

        self.memory = register_memory_tools(self.registry, MemoryManager(self.config.memory.storage_file))
        self.task_manager = register_task_tools(self.registry, TaskManager(on_task_completed=self._on_task_completed))
        self.scheduler, self.workflows = register_automation_tools(
            self.registry,
            PersistentScheduler(self.config.automation.schedules_file, on_trigger=self._on_scheduled_event),
            WorkflowEngine(self.registry, self.config.automation.workflows_file),
        )

        # 3. Brain & Routing
        self.desktop = DesktopController(config.desktop, registry=self.registry)
        self.router = IntentRouter(config=config, desktop=self.desktop, on_timer_alert=self._on_timer_alert)
        self.llm = OllamaClient(config.llm)
        self.planner = AgenticPlanner(self.registry, self.llm)

        # 4. Speech Pipeline with continuous audio sharing
        self.tts = XTTSStreamingTTS(config.tts)
        self.stt = SpeechToTextService(config.stt, audio_capture=self.audio_capture)
        self.wake_word = WakeWordDetector(config.wake_word, self.logger, audio_capture=self.audio_capture)

        # 5. Proactive Monitor
        self.proactive = ProactiveMonitor(
            on_notification=self._on_proactive_alert,
            check_interval=self.config.proactive.check_interval,
            enabled=self.config.proactive.enabled,
        )

        self._running = threading.Event()
        self._processing = threading.Event()
        self._history: list[dict[str, str]] = []
        self._max_history = self.config.memory.max_history_turns

    def start(self) -> None:
        if self._running.is_set():
            return
        self._running.set()
        self._set_state(AssistantState.IDLE, "Starting Friday V3.1...")

        # Start continuous audio capture stream
        self.audio_capture.start()

        # Background warmup of STT, TTS, and LLM models
        threading.Thread(target=self._warmup, daemon=True).start()

        # Start proactive monitor
        if self.config.proactive.enabled:
            self.proactive.start()

        if self.config.wake_word.enabled:
            try:
                self.wake_word.start(self._on_wake_word)
                self._set_state(AssistantState.LISTENING_FOR_WAKE, f"Listening for '{self.config.wake_word_phrase}'...")
            except WakeWordError as exc:
                self.logger.warning("Wake word error: %s", exc)
                self._set_state(AssistantState.IDLE, "Wake word inactive. Click orb or press Talk Now.")

    def stop(self) -> None:
        self._running.clear()
        self.cancel()
        self.wake_word.stop()
        self.audio_capture.stop()
        self.tts.stop()
        self.proactive.stop()
        self._set_state(AssistantState.IDLE, "Friday stopped.")

    def cancel(self) -> None:
        """Interrupt and cancel any current speech, generation, or processing immediately."""
        self._cancellation_token.set()
        self.tts.stop()
        self._processing.clear()
        self.wake_word.resume()
        self._set_state(AssistantState.LISTENING_FOR_WAKE, f"Ready. Say '{self.config.wake_word_phrase}'.")

    def capture_voice_once(self) -> None:
        """Trigger one voice listening round (e.g. from UI button) without breaking continuous stream."""
        if self._processing.is_set():
            self.cancel()
            return
        threading.Thread(target=self._voice_roundtrip, args=(time.perf_counter(),), daemon=True).start()

    def submit_text(self, query: str) -> None:
        """Process a text prompt."""
        if not query.strip() or self._processing.is_set():
            return
        threading.Thread(target=self._handle_query, args=(query,), daemon=True).start()

    def handle_query(self, query: str) -> str:
        """Synchronously handle a query and return response string."""
        return self._handle_query_sync(query)

    def handle_query_with_timing(self, query: str) -> str:
        return self._handle_query_sync(query)

    def _warmup(self) -> None:
        try:
            self.stt.warmup()
            self.logger.info("STT model warmed up.")
        except Exception as exc:
            self.logger.warning("STT warmup failed: %s", exc)

        try:
            self.tts.warmup()
        except Exception:
            pass

        try:
            self.llm.ensure_ollama_running()
        except Exception:
            pass

    def _on_wake_word(self) -> None:
        t_wake = time.perf_counter()
        if not self._running.is_set():
            return

        # Barge-in: If assistant is speaking or processing, immediately interrupt and switch to new command
        if self._processing.is_set() or self._state == AssistantState.SPEAKING:
            self.logger.info("Barge-in wake word detected while busy. Interrupting current turn.")
            self.cancel()

        threading.Thread(target=self._voice_roundtrip, args=(t_wake,), daemon=True).start()

    def _voice_roundtrip(self, t_wake: float) -> None:
        self._processing.set()
        self.tts.stop()
        self.wake_word.pause()  # Pause wake-word while active in voice dialogue

        self._set_state(AssistantState.WAKE_DETECTED, "Wake word detected!")
        is_first_turn = True

        try:
            while self._running.is_set() and not self._cancellation_token.is_set():
                turn_start = time.perf_counter()
                telemetry = TurnTelemetry(
                    turn_id=f"turn_{uuid.uuid4().hex[:6]}",
                    t_wake_detected=t_wake if is_first_turn else turn_start,
                )
                is_first_turn = False

                telemetry.t_listen_start = time.perf_counter()
                self._set_state(AssistantState.LISTENING_FOR_COMMAND, "Listening for command...")

                telemetry.t_stt_start = time.perf_counter()
                transcript = self.stt.listen_once(on_status=lambda msg: self._set_state(AssistantState.LISTENING_FOR_COMMAND, msg))
                telemetry.t_speech_end = time.perf_counter()
                telemetry.t_stt_complete = time.perf_counter()

                # If no speech was detected during the follow-up window (silence / timeout), smoothly return to wake listening
                if not transcript or not transcript.strip():
                    self.logger.info("Follow-up silence timeout. Returning to wake-word standby.")
                    break

                telemetry.query = transcript

                # Check for explicit sleep, exit, or dismiss phrases
                cleaned = transcript.strip().lower().rstrip(".?!")
                if cleaned in {
                    "stop", "cancel", "stop listening", "go to sleep", "sleep",
                    "goodbye", "bye", "bye friday", "goodbye friday", "that's all",
                    "thats all", "thank you that's all", "thank you thats all", "dismiss", "exit", "quit"
                }:
                    farewell = "Going to standby. Say Hey Jarvis when you need me."
                    self._emit_transcript(transcript)
                    self._emit_response(farewell)
                    self._set_state(AssistantState.SPEAKING, farewell)
                    if self.config.speak_responses:
                        self.tts.speak(farewell)
                        self.tts.wait_until_done()
                    break

                response = self._handle_query_sync(transcript, telemetry=telemetry)

                # If the intent indicated shutting down assistant
                if "Shutting down" in response or "Have a wonderful day" in response:
                    break

                # If continuous follow-up is disabled in config, break after single turn
                if not getattr(self.config.wake_word, "continuous_conversation", True):
                    break

        except Exception as exc:
            self.logger.exception("Voice roundtrip error: %s", exc)
            self._set_state(AssistantState.ERROR, f"Audio input error: {exc}")
        finally:
            self._processing.clear()
            self.wake_word.resume()
            if self._running.is_set():
                self._set_state(AssistantState.LISTENING_FOR_WAKE, f"Listening for '{self.config.wake_word_phrase}'...")

    def _handle_query(self, query: str) -> None:
        if not self._processing.is_set():
            self._processing.set()

        try:
            self._handle_query_sync(query)
        except Exception as exc:
            self.logger.exception("Error processing query: %s", exc)
            err_msg = f"Something went wrong: {exc}"
            self._emit_response(err_msg)
            self._set_state(AssistantState.ERROR, err_msg)
        finally:
            self._processing.clear()
            if self._running.is_set() and self._state != AssistantState.SPEAKING:
                self._set_state(AssistantState.LISTENING_FOR_WAKE, f"Listening for '{self.config.wake_word_phrase}'...")

    def _handle_query_sync(self, query: str, telemetry: TurnTelemetry | None = None) -> str:
        self._cancellation_token.clear()
        t = telemetry or TurnTelemetry(turn_id=f"turn_{uuid.uuid4().hex[:6]}", query=query)
        t.query = query

        self._emit_transcript(query)
        self._set_state(AssistantState.THINKING, "Processing...")

        # 1. Fast-Path Intent Router (<50ms deterministic execution)
        t.t_router_start = time.perf_counter()
        intent = self.router.route(query)
        t.t_router_complete = time.perf_counter()

        if intent.handled:
            t.path_taken = "fast_path"
            t.t_tool_start = t.t_router_start
            t.t_tool_complete = t.t_router_complete
            response = intent.response
            self._emit_response(response)
            self._set_state(AssistantState.SPEAKING, response)

            if self.config.speak_responses and not self._cancellation_token.is_set():
                t.t_tts_start = time.perf_counter()
                self.tts.speak(response)
                t.t_tts_first_audio = time.perf_counter()
                self.tts.wait_until_done()
                t.t_playback_complete = time.perf_counter()

            self._record_turn(query, response)
            t.compute_metrics()
            global_telemetry.record_turn(t)
            self._set_state(AssistantState.LISTENING_FOR_WAKE, f"Ready. Say '{self.config.wake_word_phrase}'.")
            return response

        # 2. Conversational / Agentic LLM Generation with Sentence-Level Streaming
        t.path_taken = "llm_agent"
        full_response_text = ""
        self._emit_response("")
        self._set_state(AssistantState.SPEAKING, "Thinking and speaking...")

        t.t_llm_start = time.perf_counter()
        first_token = True

        for sentence, accumulated in self.llm.stream_sentences(query, history=self._history):
            if self._cancellation_token.is_set():
                self.logger.info("LLM token streaming cancelled.")
                break

            if first_token:
                t.t_llm_first_token = time.perf_counter()
                t.t_tts_start = t.t_llm_first_token
                first_token = False

            full_response_text = accumulated
            self._emit_response(accumulated)
            if self.config.speak_responses and not self._cancellation_token.is_set():
                if t.t_tts_first_audio == 0.0:
                    t.t_tts_first_audio = time.perf_counter()
                self.tts.speak_sentence(sentence)

        t.t_llm_complete = time.perf_counter()

        if not full_response_text.strip() and not self._cancellation_token.is_set():
            full_response_text = "I'm sorry, I could not generate a response from the local model."
            self._emit_response(full_response_text)
            if self.config.speak_responses:
                self.tts.speak(full_response_text)

        if self.config.speak_responses and not self._cancellation_token.is_set():
            self.tts.wait_until_done()
            t.t_playback_complete = time.perf_counter()

        self._record_turn(query, full_response_text)
        t.compute_metrics()
        global_telemetry.record_turn(t)
        self._set_state(AssistantState.LISTENING_FOR_WAKE, f"Ready. Say '{self.config.wake_word_phrase}'.")
        return full_response_text

    def _record_turn(self, user_msg: str, bot_msg: str) -> None:
        self._history.append({"role": "user", "content": user_msg})
        self._history.append({"role": "assistant", "content": bot_msg})
        if len(self._history) > self._max_history * 2:
            self._history = self._history[-(self._max_history * 2) :]

    def _on_timer_alert(self, message: str) -> None:
        self._emit_response(message)
        self._set_state(AssistantState.SPEAKING, message)
        if self.config.speak_responses:
            self.tts.speak(message)
            self.tts.wait_until_done()
        self._set_state(AssistantState.LISTENING_FOR_WAKE, f"Ready. Say '{self.config.wake_word_phrase}'.")

    def _on_scheduled_event(self, event: Any) -> None:
        msg = f"Reminder: {event.message}"
        self._on_timer_alert(msg)

    def _on_task_completed(self, task: Any) -> None:
        msg = f"Task '{task.title}' has {task.status.value.lower()}."
        self._on_timer_alert(msg)

    def _on_proactive_alert(self, message: str) -> None:
        self._on_timer_alert(message)

    def _set_state(self, state: AssistantState, status_msg: str) -> None:
        self._state = state
        try:
            val = state.value if isinstance(state, AssistantState) else str(state)
            self.on_state(val)
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
