from __future__ import annotations

import argparse
import logging
import sys
import threading
import time
from pathlib import Path

from assistant_core import VoiceAssistant
from audio_tts import prepare_tts_assets
from config import AppConfig, load_config, resolve_path
from gui import AssistantWindow
from wake_word import prepare_wake_word_models


def configure_logging(config: AppConfig) -> logging.Logger:
    log_path = resolve_path(config.log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return logging.getLogger("friday")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Friday fast local desktop voice assistant")
    parser.add_argument("--config", default="config.json", help="Path to config JSON file")
    parser.add_argument("--headless", action="store_true", help="Run in headless terminal mode")
    parser.add_argument("--text", help="Send a single text command to Friday")
    parser.add_argument("--check", action="store_true", help="Check local models and services")
    parser.add_argument("--voice-once", action="store_true", help="Capture one voice request")
    parser.add_argument("--prepare-wake-word", action="store_true", help="Download wake word models")
    parser.add_argument("--prepare-tts", action="store_true", help="Download Piper TTS voice models")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_config(args.config)
    logger = configure_logging(config)

    assistant = VoiceAssistant(config=config, logger=logger)

    if args.check:
        print("Checking Friday services...")
        ollama_ok = assistant.llm.check_connection()
        print(f"[*] Ollama ({config.llm.base_url}, model: {config.llm.model}): {'OK' if ollama_ok else 'NOT CONNECTED'}")

        tts_ok = True
        if config.tts.backend == "piper":
            try:
                prepare_tts_assets(config.tts)
            except Exception as e:
                tts_ok = False
                print(f"[!] Piper TTS setup warning: {e}")
        print(f"[*] Text-To-Speech ({config.tts.backend}): {'OK' if tts_ok else 'ERROR'}")

        ww_ok = True
        if config.wake_word.enabled:
            try:
                prepare_wake_word_models(config.wake_word)
            except Exception as e:
                ww_ok = False
                print(f"[!] Wake word warning: {e}")
        print(f"[*] Wake Word (openWakeWord): {'OK' if ww_ok else 'ERROR'}")
        return 0

    if args.prepare_wake_word:
        paths = prepare_wake_word_models(config.wake_word)
        print("Wake word models ready:")
        for p in paths:
            print(f" - {p}")
        return 0

    if args.prepare_tts:
        paths = prepare_tts_assets(config.tts)
        print("TTS assets ready:")
        for p in paths:
            print(f" - {p}")
        return 0

    if args.text:
        finished = threading.Event()
        assistant.on_transcript = lambda t: print(f"[You]: {t}")
        assistant.on_response = lambda r: print(f"\r[Friday]: {r}", end="", flush=True)

        def _runner() -> None:
            assistant.submit_text(args.text)
            time.sleep(0.3)
            while assistant._processing.is_set():
                time.sleep(0.05)
            finished.set()

        threading.Thread(target=_runner, daemon=True).start()
        finished.wait(timeout=config.llm.request_timeout + 5)
        print()
        return 0

    if args.voice_once:
        assistant.on_status = lambda s: print(f"[Status]: {s}")
        assistant.on_transcript = lambda t: print(f"[You]: {t}")
        assistant.on_response = lambda r: print(f"\r[Friday]: {r}", end="", flush=True)
        assistant.capture_voice_once()
        time.sleep(0.3)
        while assistant._processing.is_set():
            time.sleep(0.1)
        print()
        return 0

    if args.headless or not config.ui.enabled:
        assistant.start()
        print(f"Friday running in headless mode. Wake word: '{config.wake_word_phrase}'. Press Ctrl+C to exit.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            assistant.stop()
        return 0

    # Launch Modern GUI Window
    window = AssistantWindow(assistant=assistant, config=config)
    assistant.on_status = window.set_status
    assistant.on_transcript = window.set_transcript
    assistant.on_response = window.set_response
    assistant.on_state = window.set_state
    window.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
