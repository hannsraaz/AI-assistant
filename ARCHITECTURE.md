# 🏛️ Friday V2 — System Architecture & Design Specification

---

## 1. System Overview

Friday V2 is a private, local-first personal computer agent and desktop voice assistant for Windows. It combines **sub-second deterministic fast-path execution** with **multi-step LLM planning**, **modular Windows automation**, **vision screen understanding**, **developer workflows**, and **long-term memory**.

```
                         ┌────────────────────────┐
                         │      Voice / Text      │
                         └───────────┬────────────┘
                                     │
                           ┌─────────▼─────────┐
                           │   openWakeWord    │ ("Hey Jarvis", 16kHz ONNX)
                           └─────────┬─────────┘
                                     │
                           ┌─────────▼─────────┐
                           │  Faster-Whisper   │ (In-Memory float32, base.en)
                           └─────────┬─────────┘
                                     │
                 ┌───────────────────▼───────────────────┐
                 │              FRIDAY CORE              │
                 │                                       │
                 │ Intent Router      Task Planner       │
                 │ Memory Manager     Task Manager       │
                 │ Telemetry          Response Engine    │
                 └───────────┬───────────────────────┬───┘
                             │                       │
       Fast-Path (<50ms)     │                       │ Conversational / Agentic
                             ▼                       ▼
                  ┌────────────────────┐   ┌────────────────────┐
                  │  Deterministic OS  │   │     Ollama LLM     │
                  │   Direct Action    │   │  (Tool Reasoning)  │
                  └──────────┬─────────┘   └─────────┬──────────┘
                             │                       │
                             └───────────┬───────────┘
                                         ▼
                             ┌───────────────────────┐
                             │     TOOL REGISTRY     │
                             └───────────┬───────────┘
                                         ▼
                             ┌───────────────────────┐
                             │   PERMISSION LAYER    │
                             │ (SAFE / CONFIRM / HR) │
                             └───────────┬───────────┘
                                         │
       ┌───────────────┬─────────────────┼─────────────────┬───────────────┐
       ▼               ▼                 ▼                 ▼               ▼
    WINDOWS          FILES            VISION           DEVELOPER       AUTOMATION
       │               │                 │                 │               │
  ├── Apps        ├── Search        ├── Capture       ├── Terminal    ├── Timers
  ├── Windows     ├── List          ├── Describe      ├── Git         ├── Reminders
  ├── System      ├── Read          ├── Analyze       ├── GitHub      ├── Workflows
  ├── Media       ├── Create        ├── Find Text     └── Android     └── Proactive
  └── Input       └── Delete        └── Find Element
                                         │
                                         ▼
                             ┌───────────────────────┐
                             │    RESPONSE ENGINE    │
                             └───────────┬───────────┘
                                         ▼
                             ┌───────────────────────┐
                             │     STREAMING TTS     │
                             │ (Piper / XTTS Hybrid) │
                             └───────────┬───────────┘
                                         │
                                         ▼
                                    🔊 Speakers
```

---

## 2. Core Subsystems

### 2.1 Audio & Speech Pipeline
1. **Wake Word Detection ([wake_word.py](file:///c:/Users/razzk/Downloads/Friday%20mark%201/wake_word.py))**:
   - Runs `openwakeword` ONNX models at 16 kHz sample rate.
   - Smoothly halts wake word capture during microphone capture.
2. **Speech-to-Text ([audio_stt.py](file:///c:/Users/razzk/Downloads/Friday%20mark%201/audio_stt.py))**:
   - `faster-whisper base.en` quantized with `int8`.
   - In-memory float32 NumPy arrays with 500ms post-speech silence cutoff.
3. **Text-to-Speech ([audio_tts.py](file:///c:/Users/razzk/Downloads/Friday%20mark%201/audio_tts.py) / [audio_tts_xtts.py](file:///c:/Users/razzk/Downloads/Friday%20mark%201/audio_tts_xtts.py))**:
   - Sentence-level streaming with Piper ONNX and XTTS v2 fallback.

---

### 2.2 Modular Tool Framework ([core/tools/](file:///c:/Users/razzk/Downloads/Friday%20mark%201/core/tools))
- **Base Architecture (`core/tools/base.py`)**: `BaseTool`, `ToolResult`, and `RiskLevel` (`SAFE`, `CONFIRM`, `HIGH_RISK`).
- **Registry (`core/tools/registry.py`)**: Central registry providing tool dispatch and OpenAPI/Ollama tool schema extraction.
- **Permission Layer (`core/tools/permissions.py`)**: Enforces confirmation tokens on sensitive and destructive actions.
- **Response Engine (`core/response_engine.py`)**: Converts structured data into natural, witty, and direct voice responses.

---

### 2.3 Tool Modules
- **Windows Automation (`core/tools/windows/`)**: Dynamic Start Menu/Registry app discovery, Win32 window handles, system metrics, hardware multimedia keys, clipboard safeguards, and multi-mode screenshot capture.
- **File System Agent (`core/tools/files/`)**: Search, list, open, read, copy, move, rename, delete, and exists with system directory protection.
- **Screen & Vision (`core/tools/vision/`)**: Active window capture, screen description, element localization, and error analysis via vision LLMs.
- **Input Agent (`core/tools/input/`)**: Controlled keyboard typing, hotkeys, and mouse interaction.
- **Browser Agent (`core/tools/browser/`)**: Open URLs, search Google/YouTube, read pages cleanly, and download files.
- **Developer & Android (`core/tools/developer/`)**: Controlled terminal execution with command safety tiers, Git workflows, GitHub integration, ADB device tracking, and Gradle build/test execution.
- **Memory System (`core/memory/`)**: Persistent facts, project aliases, preferences, and credential filtering.
- **Agentic Planner & Task Manager (`core/agent/`)**: Multi-step planning, state tracking, and non-blocking background workers.
- **Automation & Scheduling (`core/automation/`)**: Persistent timers, reminders, multi-action workflows, and proactive background monitors.

---

## 3. Telemetry & Latency Targets

| Pipeline Step | Target | Measured Result |
| :--- | :--- | :--- |
| **Fast-Path Intent Match & Exec** | `< 50ms` | **0.1ms – 0.8ms** |
| **STT Voice Transcription** | `< 400ms` | **~250ms** |
| **TTS First Audio Chunk** | `< 400ms` | **~280ms** |
| **System Diagnostics** | `< 200ms` | **85ms** |
| **Memory Recall / Search** | `< 10ms` | **0.5ms** |
