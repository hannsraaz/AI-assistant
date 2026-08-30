from __future__ import annotations

import json
import os
import platform
import shutil
import sys
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


def _app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


APP_DIR = _app_dir()
DATA_DIR = APP_DIR / "data"
DEFAULT_CONFIG_PATH = APP_DIR / "config.json"
DEFAULT_ENV_PATH = APP_DIR / ".env"


def _default_search_paths() -> list[str]:
    home = Path.home()
    candidates = [home / "Desktop", home / "Documents", home / "Downloads"]
    return [str(path) for path in candidates if path.exists()]


@dataclass(slots=True)
class WakeWordConfig:
    enabled: bool = True
    model_names: list[str] = field(default_factory=lambda: ["hey_jarvis"])
    custom_model_paths: list[str] = field(default_factory=list)
    model_directory: str = "data/openwakeword_models"
    inference_framework: str = "onnx"
    threshold: float = 0.5
    vad_threshold: float = 0.0
    debounce_seconds: float = 1.0
    enable_noise_suppression: bool = False
    sample_rate: int = 16_000
    frame_length: int = 1_280
    device_index: int = -1
    continuous_conversation: bool = True  # Keep listening for follow-ups without repeating wake word
    conversation_timeout_seconds: float = 10.0  # Return to wake listening after silence


@dataclass(slots=True)
class STTConfig:
    model_size: str = "base.en"  # base.en is ~250ms latency vs 2500ms on small
    device: str = "cpu"
    compute_type: str = "int8"
    language: str = "en"
    sample_rate: int = 16_000
    block_duration: float = 0.2
    silence_threshold: float = 0.015
    silence_duration: float = 0.5  # Snappy 500ms post-speech silence cutoff
    min_record_seconds: float = 0.5
    max_record_seconds: float = 12.0


@dataclass(slots=True)
class VADConfig:
    enabled: bool = True
    model_path: str = "data/openwakeword_models/silero_vad.onnx"
    speech_threshold: float = 0.45
    min_speech_duration_ms: int = 120
    silence_duration_ms: int = 450
    min_record_seconds: float = 0.5
    max_record_seconds: float = 12.0
    pre_roll_seconds: float = 0.35
    sample_rate: int = 16_000



@dataclass(slots=True)
class LLMConfig:
    base_url: str = "http://127.0.0.1:11434"
    model: str = "llama3.2:3b"  # Fast 3B model (or qwen2.5:3b / mistral)
    temperature: float = 0.3
    keep_alive: str = "30m"
    request_timeout: int = 60
    system_prompt: str = (
        "You are Friday, a lightning-fast Jarvis-style local Windows personal assistant. "
        "Language policy: Match the user's language naturally. If the user speaks Hinglish or Hindi, respond in natural, friendly Roman Hinglish (e.g. 'Haan, main check karta hoon', 'VS Code khol raha hoon'). "
        "If the user speaks English, respond in English. "
        "Never translate technical terms (keep VS Code, Android Studio, Git, build, commit, push, RAM, CPU, GPU, browser, download, file, folder, screenshot, terminal, project in English). "
        "Keep spoken answers concise, confident, and crisp (1-2 sentences usually)."
    )


@dataclass(slots=True)
class TTSConfig:
    backend: str = "auto"  # 'auto', 'piper', 'hinglish', 'indicvoice', 'pyttsx3'
    engine: str = "auto"   # Alias for pluggable TTSEngine selection
    language: str = "auto" # 'auto', 'hinglish', 'hi', 'en'
    hinglish_enabled: bool = True
    hindi_enabled: bool = True
    fallback_enabled: bool = True
    voice_name: str = ""
    rate: int = 195
    volume: float = 1.0
    piper_voice: str = "en_US-lessac-medium"
    piper_voice_directory: str = "data/piper"
    piper_speaker_id: int = -1
    piper_length_scale: float = 1.0
    piper_noise_scale: float = 0.667
    piper_noise_w_scale: float = 0.8
    stream_sentences: bool = True  # Stream audio per-sentence for instant voice response


@dataclass(slots=True)
class DesktopConfig:
    allow_power_commands: bool = False
    search_paths: list[str] = field(default_factory=_default_search_paths)
    screenshot_directory: str = "data/screenshots"
    notes_file: str = "data/notes.txt"
    default_browser: str = "chrome"
    web_search_template: str = "https://www.google.com/search?q={query}"
    youtube_search_template: str = "https://www.youtube.com/results?search_query={query}"


@dataclass(slots=True)
class UIConfig:
    enabled: bool = True
    always_on_top: bool = True
    theme_color: str = "#00d2ff"  # Modern cyan glow
    bg_color: str = "#0d1117"
    enable_tray: bool = True


@dataclass(slots=True)
class MemoryConfig:
    enabled: bool = True
    storage_file: str = "data/memory.json"
    max_history_turns: int = 8


@dataclass(slots=True)
class VisionConfig:
    enabled: bool = True
    vision_model: str = "llama3.2-vision:latest"
    fallback_model: str = "llava:latest"


@dataclass(slots=True)
class AutomationConfig:
    enabled: bool = True
    schedules_file: str = "data/schedules.json"
    workflows_file: str = "data/workflows.json"


@dataclass(slots=True)
class ProactiveConfig:
    enabled: bool = True
    check_interval: float = 30.0
    battery_alert_threshold: int = 15


@dataclass(slots=True)
class AppConfig:
    name: str = "Friday"
    wake_word_phrase: str = "Hey Jarvis"
    default_location: str = "New Delhi"
    speak_responses: bool = True
    log_file: str = "data/friday.log"
    wake_word: WakeWordConfig = field(default_factory=WakeWordConfig)
    stt: STTConfig = field(default_factory=STTConfig)
    vad: VADConfig = field(default_factory=VADConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    tts: TTSConfig = field(default_factory=TTSConfig)
    desktop: DesktopConfig = field(default_factory=DesktopConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    vision: VisionConfig = field(default_factory=VisionConfig)
    automation: AutomationConfig = field(default_factory=AutomationConfig)
    proactive: ProactiveConfig = field(default_factory=ProactiveConfig)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def resolve_path(path_str: str | Path) -> Path:
    path = Path(path_str).expanduser()
    if path.is_absolute():
        return path
    return (APP_DIR / path).resolve()


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _filter_known_fields(cls: Any, payload: dict[str, Any]) -> dict[str, Any]:
    known = {f.name for f in fields(cls)}
    return {k: v for k, v in payload.items() if k in known}


def load_config(config_path: str | Path | None = None) -> AppConfig:
    load_dotenv(DEFAULT_ENV_PATH)
    path = resolve_path(config_path or DEFAULT_CONFIG_PATH)

    data: dict[str, Any] = {}
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}

    default_config = AppConfig()
    merged = _deep_merge(default_config.to_dict(), data)

    wake_word = WakeWordConfig(**_filter_known_fields(WakeWordConfig, merged.get("wake_word", {})))
    stt = STTConfig(**_filter_known_fields(STTConfig, merged.get("stt", {})))
    vad = VADConfig(**_filter_known_fields(VADConfig, merged.get("vad", {})))
    llm = LLMConfig(**_filter_known_fields(LLMConfig, merged.get("llm", {})))
    tts = TTSConfig(**_filter_known_fields(TTSConfig, merged.get("tts", {})))
    desktop = DesktopConfig(**_filter_known_fields(DesktopConfig, merged.get("desktop", {})))
    ui = UIConfig(**_filter_known_fields(UIConfig, merged.get("ui", {})))

    top_level = _filter_known_fields(AppConfig, merged)
    top_level["wake_word"] = wake_word
    top_level["stt"] = stt
    top_level["vad"] = vad
    top_level["llm"] = llm
    top_level["tts"] = tts
    top_level["desktop"] = desktop
    top_level["ui"] = ui
    top_level["memory"] = MemoryConfig(**_filter_known_fields(MemoryConfig, merged.get("memory", {})))
    top_level["vision"] = VisionConfig(**_filter_known_fields(VisionConfig, merged.get("vision", {})))
    top_level["automation"] = AutomationConfig(**_filter_known_fields(AutomationConfig, merged.get("automation", {})))
    top_level["proactive"] = ProactiveConfig(**_filter_known_fields(ProactiveConfig, merged.get("proactive", {})))

    return AppConfig(**top_level)


def save_config(config: AppConfig, path: str | Path | None = None) -> None:
    target_path = resolve_path(path or DEFAULT_CONFIG_PATH)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with target_path.open("w", encoding="utf-8") as f:
        json.dump(config.to_dict(), f, indent=2)
