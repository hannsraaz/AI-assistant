# FRIDAY TTS Architecture Specification

---

## 1. Pipeline Diagram

```
       [ User Voice / Text Query ]
                   │
                   ▼
      [ Faster-Whisper STT (base.en) ]
                   │
                   ▼
     [ Fast-Path Router / Ollama LLM ]
                   │
                   ▼
       [ Sentence Streaming Loop ]
                   │
                   ▼
    ┌─────────────────────────────┐
    │  core/language/             │
    │  ├─ LanguageDetector        │
    │  ├─ PronunciationLayer      │
    │  └─ HinglishNormalizer      │
    └──────────────┬──────────────┘
                   │
                   ▼
    ┌─────────────────────────────┐
    │  core/voice/                │
    │  ├─ ProsodyEngine           │
    │  └─ AutoRoutingTTSEngine    │
    └──────────────┬──────────────┘
                   │
                   ▼
        [ Audio Playback Queue ]
                   │
                   ▼
        [ sounddevice (Speaker) ]
```

---

## 2. Pluggable TTS Engine Interface

All synthesizers implement `BaseTTSEngine` (`core/voice/tts_engine.py`):

```python
class BaseTTSEngine(ABC):
    @abstractmethod
    def synthesize(self, text: str, rate_multiplier: float = 1.0) -> tuple[np.ndarray | None, int]:
        """Synthesize text into raw float32 audio waveform and sample rate."""
        ...

    @abstractmethod
    def stop(self) -> None:
        """Interrupt and halt synthesis immediately."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if model assets and runtime dependencies are ready."""
        ...

    @abstractmethod
    def get_capabilities(self) -> dict[str, Any]:
        """Return engine capabilities (languages, RTF, VRAM)."""
        ...
```

---

## 3. Fallback Hierarchy

```
Preferred Hinglish Neural TTS
        │ (on missing weights or failure)
        ▼
Indic Voice / Kokoro G2P Engine
        │ (on missing weights or failure)
        ▼
Piper ONNX Engine (en_US-lessac-medium + G2P Transliterator)
        │ (on failure)
        ▼
Windows Native SAPI5 Engine (pyttsx3)
```

---

## 4. Cancellation & Barge-In Guarantees
- `stop()` halts `sounddevice` playback and flushes the queue within **<50ms**.
- Audio playback thread checks `_stop_event` every **15ms**.
