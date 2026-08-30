# FRIDAY TTS Models & Offline Setup

---

## 1. Supported Model Families

### A. Piper ONNX Engine (Default Local Engine)
- **Model:** `en_US-lessac-medium.onnx` (~60MB)
- **Sample Rate:** 22050 Hz
- **Compute:** CPU ONNX runtime (Zero VRAM footprint)
- **Latency:** ~0.015 RTF (Time-to-first-audio: ~200ms)
- **Enhancement:** Enhanced with `HinglishPhoneticEngine` for accurate Indian English & Roman Hindi phonology.

### B. Hinglish Neural Engine (`harrrshall/hinglish-tts`)
- **Target:** Hindi-English code-mixed phonology
- **VRAM:** ~800 MB
- **Offline Setup:** Model checkpoints stored in `data/models/hinglish_tts/`

### C. Indic Voice (`Bindkushal/indic-voice`)
- **Target:** Kokoro-82M Indic G2P
- **VRAM:** ~350 MB
- **Offline Setup:** Weights stored in `data/models/indic_voice/`

### D. Windows SAPI5 (Native Driver)
- **Target:** Microsoft Ravi / Microsoft Heera / Microsoft David
- **VRAM:** 0 MB
- **Offline Setup:** Built into Windows 10/11

---

## 2. Hardware Resource Matrix (6GB VRAM Constraint)

| Subsystem | Model | VRAM Usage | CPU / RAM |
| :--- | :--- | :--- | :--- |
| **STT** | Faster-Whisper base.en | 0 MB (CPU INT8) | ~350 MB RAM |
| **LLM** | Ollama (qwen2.5 / llama3.2) | ~3.8 GB VRAM | ~1.2 GB RAM |
| **Vision** | Moondream / Florence-2 | ~1.4 GB VRAM (on-demand) | ~800 MB RAM |
| **TTS (Piper + G2P)** | Piper ONNX | **0 MB VRAM** | **~150 MB RAM** |
| **Total Headroom** | — | **~0.8 GB VRAM Free** | **~10 GB RAM Free** |
