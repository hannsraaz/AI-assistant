# 🎙️ Friday: Fast Local Desktop Voice Assistant (Bixby/Jarvis Style)

Friday is an ultra-fast, local, privacy-first desktop voice assistant built for Windows. It provides **sub-second voice responsiveness** and **complete Windows desktop control**.

---

## ⚡ Key Highlights
- **Sub-Second Voice Responses (< 1.5s TTFA)**: Uses in-memory `faster-whisper base.en` STT with zero disk I/O and sentence-level streaming `piper-tts`.
- **Instant Desktop Automation (< 50ms)**: Fast-path router handles volume, media, brightness, window management, system stats, timers, apps, and notes without waiting for LLM.
- **Local AI Chat**: Optional integration with Ollama (`llama3.2:3b`, `qwen2.5:3b`, `mistral`) for open-ended voice conversation.
- **Sleek Floating Modern HUD**: Dark glassmorphic widget with an animated glowing voice orb that responds to voice state.

---

## 📁 Clean Project Structure

```
├── 00_START_FRIDAY.bat       # One-click desktop launcher
├── main.py                   # Main CLI & application entrypoint
├── assistant_core.py         # Coordinator for STT, TTS, LLM, Router & Wake Word
├── audio_stt.py              # In-memory Speech-to-Text (faster-whisper)
├── audio_tts.py              # Sentence-level streaming Text-to-Speech (Piper)
├── wake_word.py              # openWakeWord wake-word detector ("Hey Jarvis")
├── desktop_controller.py     # Windows system control & desktop automation
├── intent_router.py          # Fast sub-50ms regex/intent dispatcher & timer scheduler
├── llm_agent.py              # Local Ollama client with token & sentence streaming
├── gui.py                    # Glowing dark-mode floating HUD
├── config.py / config.json   # Typed configuration system
└── requirements.txt          # Minimal pinned dependencies
```

---

## 🚀 Quick Start

### 1. Launch Friday
Double-click:
```bat
00_START_FRIDAY.bat
```
Or run via terminal:
```powershell
.venv\Scripts\python.exe main.py
```

### 2. Verify Services
```powershell
.venv\Scripts\python.exe main.py --check
```

---

## 🗣️ Common Voice Commands

- **Audio & Volume**: *"Mute"*, *"Unmute"*, *"Set volume to 50%"*, *"Volume up / down"*, *"What's the volume"*
- **Media Controls**: *"Play / Pause"*, *"Next track"*, *"Previous song"*, *"Stop music"*
- **Display & Brightness**: *"Set brightness to 80%"*, *"Brightness up / down"*
- **Windows & Workspace**: *"Show desktop"*, *"Minimize all"*, *"Close active window"*, *"Switch window"*, *"Lock PC"*
- **System Stats**: *"System status"*, *"Battery percentage"*, *"Free disk space"*
- **Productivity & Timers**: *"Set a timer for 10 minutes"*, *"Take a note: buy groceries"*, *"Read my notes"*
- **Apps & Search**: *"Open Chrome"*, *"Open VS Code"*, *"Open Downloads folder"*, *"Play jazz on YouTube"*, *"Google machine learning"*
- **Time & Date**: *"What time is it?"*, *"What is today's date?"*
