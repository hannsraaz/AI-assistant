# 🎯 FRIDAY ENTERPRISE ASSISTANT - DETAILED TASK BREAKDOWN

**For**: AI Agent (Execute with Precision)  
**Master**: Hans Bhardwaj (QA & Verification)  
**Goal**: Bixby-like performance + Siri/Claude-quality UI/Voice + Enterprise-grade reliability  

---

## 📋 OVERVIEW & PRIORITIES

| Priority | Category | Status | Owner |
| :--- | :--- | :--- | :--- |
| **P0** | Performance Benchmarking | TODO | AI Agent |
| **P0** | Smooth TTS Integration (Claude-quality) | TODO | AI Agent |
| **P1** | LLM Conversation Verification | TODO | AI Agent |
| **P1** | Error Handling & Resilience | TODO | AI Agent |
| **P2** | Type Hints & Code Quality | TODO | AI Agent |
| **P2** | Unit Tests & Coverage | TODO | AI Agent |
| **P3** | Structured Logging & Debugging | TODO | AI Agent |
| **P3** | Documentation & Portfolio | TODO | AI Agent |

---

## 🔥 P0: PERFORMANCE BENCHMARKING (Week 1)

### Task P0.1: Create Comprehensive Benchmark Suite
**File to create**: `benchmark_suite.py`  
**What to do**:
```python
# benchmark_suite.py
import json
import statistics
import time
from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class BenchmarkResult:
    command: str
    latencies: List[float]  # milliseconds
    average: float
    median: float
    p95: float
    p99: float
    success_rate: float


class PerformanceBenchmark:
    """Measure Friday's performance against <1.5s target"""

    def __init__(self, num_runs: int = 10):
        self.num_runs = num_runs
        self.results: Dict[str, BenchmarkResult] = {}

    def benchmark_simple_commands(self) -> None:
        """Test fast-path commands (should be <500ms)"""
        commands = [
            "mute",
            "unmute",
            "what time is it",
            "battery status",
            "system status",
            "show desktop",
            "take a screenshot",
        ]
        for cmd in commands:
            print(f"Benchmarking: {cmd}")
            latencies = []
            for run in range(self.num_runs):
                start = time.perf_counter_ns()
                # Call: main.py --text "{cmd}"
                # Measure: wake_word → STT → intent_router → response_start
                end = time.perf_counter_ns()
                latency_ms = (end - start) / 1_000_000
                latencies.append(latency_ms)

            self.results[cmd] = BenchmarkResult(
                command=cmd,
                latencies=latencies,
                average=statistics.mean(latencies),
                median=statistics.median(latencies),
                p95=sorted(latencies)[int(len(latencies) * 0.95)],
                p99=sorted(latencies)[int(len(latencies) * 0.99)],
                success_rate=1.0,
            )

    def benchmark_llm_commands(self) -> None:
        """Test LLM path (should be <1500ms total)"""
        commands = [
            "tell me a joke",
            "what is machine learning",
            "explain python decorators",
            "how do I optimize code",
        ]
        for cmd in commands:
            print(f"Benchmarking LLM: {cmd}")
            latencies = []
            for run in range(self.num_runs):
                start = time.perf_counter_ns()
                # Measure: wake_word → STT → LLM_start → first_sentence_audio_begins
                end = time.perf_counter_ns()
                latency_ms = (end - start) / 1_000_000
                latencies.append(latency_ms)

            self.results[cmd] = BenchmarkResult(
                command=cmd,
                latencies=latencies,
                average=statistics.mean(latencies),
                median=statistics.median(latencies),
                p95=sorted(latencies)[int(len(latencies) * 0.95)],
                p99=sorted(latencies)[int(len(latencies) * 0.99)],
                success_rate=1.0,
            )

    def benchmark_multi_step_commands(self) -> None:
        """Test complex commands with multiple steps"""
        commands = [
            "set volume to 50 and open VS Code",
            "open Chrome and search for python",
        ]
        for cmd in commands:
            print(f"Benchmarking multi-step: {cmd}")
            latencies = []
            for run in range(self.num_runs):
                start = time.perf_counter_ns()
                # Full end-to-end including all tool execution
                end = time.perf_counter_ns()
                latency_ms = (end - start) / 1_000_000
                latencies.append(latency_ms)

            self.results[cmd] = BenchmarkResult(
                command=cmd,
                latencies=latencies,
                average=statistics.mean(latencies),
                median=statistics.median(latencies),
                p95=sorted(latencies)[int(len(latencies) * 0.95)],
                p99=sorted(latencies)[int(len(latencies) * 0.99)],
                success_rate=1.0,
            )

    def generate_report(self) -> str:
        """Create human-readable benchmark report"""
        report = "=" * 80 + "\n"
        report += "FRIDAY ASSISTANT - PERFORMANCE BENCHMARK REPORT\n"
        report += "=" * 80 + "\n\n"

        for cmd, result in self.results.items():
            status = "✅ PASS" if result.average < 1500 else "❌ FAIL"
            report += f"{status} | {cmd}\n"
            report += (
                f"  Average: {result.average:.0f}ms | "
                f"Median: {result.median:.0f}ms | "
                f"P95: {result.p95:.0f}ms | P99: {result.p99:.0f}ms\n"
            )
            report += f"  Range: {min(result.latencies):.0f}ms - {max(result.latencies):.0f}ms\n\n"

        return report


if __name__ == "__main__":
    bench = PerformanceBenchmark(num_runs=10)
    bench.benchmark_simple_commands()
    bench.benchmark_llm_commands()
    bench.benchmark_multi_step_commands()

    report = bench.generate_report()
    print(report)

    # Save to file
    with open("benchmark_results.txt", "w", encoding="utf-8") as f:
        f.write(report)

    # Save JSON for analysis
    with open("benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump({k: v.__dict__ for k, v in bench.results.items()}, f, indent=2)
```

**Acceptance Criteria**:
- [ ] Runs 10 iterations of simple commands
- [ ] Runs 10 iterations of LLM commands
- [ ] Generates human-readable report
- [ ] Exports JSON for data analysis
- [ ] Shows pass/fail against `< 1500ms` target
- [ ] All simple commands `< 600ms` average
- [ ] All LLM commands `< 1200ms` average
- [ ] Report saved to `benchmark_results.txt`

---

### Task P0.2: Add Performance Profiling to Core Modules
**Files to modify**: `assistant_core.py`, `audio_stt.py`, `audio_tts.py`, `llm_agent.py`, `intent_router.py`

**What to add**:
```python
# In each module, add timing instrumentation
# Example in audio_stt.py:
import logging
import time

logger = logging.getLogger(__name__)


class FastWhisperSTT:
    def transcribe(self, audio_data):
        start_time = time.perf_counter()
        result = self.model.transcribe(audio_data, beam_size=1, vad_filter=True)
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.info(f"STT latency: {elapsed_ms:.1f}ms")
        return result, elapsed_ms


# In llm_agent.py:
def stream_sentences(self, prompt):
    start_time = time.perf_counter()
    for sentence in self._stream_from_ollama(prompt):
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.debug(f"Time to first sentence: {elapsed_ms:.1f}ms")
        start_time = time.perf_counter()  # Reset for next sentence
        yield sentence
```

**Acceptance Criteria**:
- [ ] All critical paths log timing information
- [ ] Logs go to `logs/friday_YYYYMMDD_HHMMSS.log`
- [ ] Format: `[TIMESTAMP] [LEVEL] Component: latency XXXms`
- [ ] No performance regression from logging

---

## 🎙️ P0: SMOOTH TTS INTEGRATION - CLAUDE-QUALITY VOICE (Week 1)

### Task P0.3: Research & Integrate XTTS v2 (Coqui - Claude-like Smoothness)
**Why XTTS v2?**
- Professional, natural-sounding voice (comparable to Claude/Siri/Bixby)
- Multilingual support
- Fast inference (GPU accelerated)
- Voice cloning capability
- Open-source, runs locally
- Better prosody and emotion than standard TTS engines

**File to create**: `audio_tts_xtts.py`
```python
# audio_tts_xtts.py
"""XTTS v2 (Coqui) Text-to-Speech Engine
- Natural prosody and intonation (Claude-quality)
- Faster streaming than Piper
- Better emotional expression
"""

import logging
import time
from queue import Queue
from threading import Thread

import numpy as np
import sounddevice as sd
import torch
from TTS.api import TTS

logger = logging.getLogger(__name__)


class XTTSStreamingTTS:
    def __init__(self, device: str = "cuda", language: str = "en"):
        """Initialize XTTS v2 TTS engine.

        Args:
            device: "cuda" for GPU (recommended) or "cpu"
            language: "en" for English
        """
        logger.info("Loading XTTS v2 model (this takes ~30s on first run)...")
        self.device = device
        self.model = TTS(
            model_name="tts_models/multilingual/multi-dataset/xtts_v2",
            gpu=(device == "cuda"),
            progress_bar=True,
        )

        # Reference audio for voice cloning (optional - uses default if not provided)
        self.speaker_wav = None

        # Streaming queue
        self.audio_queue = Queue()
        self.is_playing = False
        self.stream = None

        # Start playback worker thread
        self.playback_thread = Thread(target=self._playback_worker, daemon=True)
        self.playback_thread.start()
        logger.info("XTTS v2 ready")

    def synthesize_and_stream(self, text: str, language: str = "en") -> None:
        """Synthesize text and stream to audio playback immediately."""
        start_time = time.perf_counter()
        try:
            wav = self.model.tts(
                text=text,
                speaker_wav=self.speaker_wav,
                language=language,
                top_p=0.85,
                temperature=0.75,
            )
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.info(f"XTTS synthesis time: {elapsed_ms:.0f}ms for '{text[:50]}...'")

            self.audio_queue.put((wav, self.model.synthesizer.sample_rate))
        except Exception as e:
            logger.error(f"XTTS synthesis failed: {e}")
            self._fallback_piper(text)

    def _playback_worker(self) -> None:
        """Background thread for audio playback"""
        while True:
            try:
                wav, sample_rate = self.audio_queue.get()
                if wav is None:
                    break

                if isinstance(wav, list):
                    wav = np.array(wav)
                wav = wav / np.max(np.abs(wav))  # Normalize to [-1, 1]

                self.is_playing = True
                sd.play(wav, samplerate=sample_rate, blocking=True)
                self.is_playing = False
            except Exception as e:
                logger.error(f"Playback error: {e}")

    def stop(self) -> None:
        """Stop current playback and clear queue"""
        sd.stop()
        self.is_playing = False
        while not self.audio_queue.empty():
            self.audio_queue.get()
        logger.info("Audio stopped")

    def _fallback_piper(self, text: str) -> None:
        """Fallback to Piper TTS if XTTS fails"""
        logger.warning("Falling back to Piper TTS")
        pass


if __name__ == "__main__":
    tts = XTTSStreamingTTS(device="cuda")
    tts.synthesize_and_stream("This is a smooth, natural voice synthesis using XTTS v2.")
    tts.stop()
```

---

### Task P0.4: Integrate Seamless Hybrid TTS in Assistant Core
**File to modify**: `assistant_core.py`
```python
# In assistant_core.py initialization:
try:
    from audio_tts_xtts import XTTSStreamingTTS

    self.tts = XTTSStreamingTTS(device="cuda")
    logger.info("Using XTTS v2 (Claude-quality voice)")
except Exception as e:
    logger.warning(f"XTTS unavailable, falling back to Piper: {e}")
    from audio_tts import TextToSpeechService

    self.tts = TextToSpeechService(config.tts)
```

---

## 🧠 P1: LLM CONVERSATION VERIFICATION (Week 1-2)

### Task P1.1: Create LLM Conversation Test Suite
**File to create**: `test_llm_conversation.py`
```python
# test_llm_conversation.py
import pytest
from assistant_core import VoiceAssistant
from llm_agent import OllamaClient


class TestLLMConversation:
    @pytest.fixture
    def llm_agent(self):
        from config import LLMConfig

        return OllamaClient(LLMConfig(model="qwen2.5:3b"))

    def test_simple_query(self, llm_agent):
        response = "".join(llm_agent.stream_chat("What is Python?"))
        assert response is not None
        assert len(response) > 10

    def test_sentence_streaming(self, llm_agent):
        sentences = [
            s
            for s, _ in llm_agent.stream_sentences(
                "Tell me three facts. Fact one is interesting. Fact two is amazing. Fact three is cool."
            )
        ]
        assert len(sentences) >= 2
```

---

### Task P1.2: Verify Tool Calling Integration
**File to create**: `test_tool_calling.py`
```python
# test_tool_calling.py
import pytest
from config import DesktopConfig
from desktop_controller import DesktopController


class TestToolCalling:
    @pytest.fixture
    def controller(self):
        return DesktopController(DesktopConfig())

    def test_volume_control(self, controller):
        controller.set_volume(40)
        assert abs(controller.get_volume() - 40) <= 2
```

---

## 🛡️ P1: ERROR HANDLING & RESILIENCE (Week 2)

### Task P1.3: Create Error Handling Test Suite
**File to create**: `test_error_scenarios.py`
- Test Ollama timeout handling.
- Test microphone disconnect handling.
- Test malformed LLM responses.
- Test permission denied and OS exceptions.
- Test audio playback device disconnection.

---

## 📝 P2: TYPE HINTS & CODE QUALITY (Week 2)

### Task P2.1: Add 100% Type Hints to All Modules
- [ ] `assistant_core.py` - 100% type hints
- [ ] `audio_stt.py` - 100% type hints
- [ ] `audio_tts.py` / `audio_tts_xtts.py` - 100% type hints
- [ ] `llm_agent.py` - 100% type hints
- [ ] `intent_router.py` - 100% type hints
- [ ] `desktop_controller.py` - 100% type hints
- [ ] `gui.py` - 100% type hints
- [ ] `config.py` - 100% type hints
- [ ] `wake_word.py` - 100% type hints
- [ ] `main.py` - 100% type hints

**Verification**:
```powershell
pip install mypy
mypy *.py --strict
```

---

## 🧪 P2: UNIT TESTS & COVERAGE (Week 2-3)

### Task P2.2: Test Suite Structure & Target Coverage
```
tests/
├── __init__.py
├── test_desktop_controller.py
├── test_audio_stt.py
├── test_audio_tts.py
├── test_intent_router.py
├── test_llm_agent.py
├── test_assistant_core.py
└── conftest.py
```
**Coverage Targets**:
- Desktop Controller: **90%+**
- Intent Router: **95%+**
- Overall: **80%+**

---

## 📚 P3: LOGGING & DOCUMENTATION (Week 2-4)

### Task P3.1: Structured Rotating Logger (`logger_config.py`)
- Automatic file rotation at 10MB.
- Format: `[TIMESTAMP] [LEVEL] [MODULE] message (latency XXXms)`.

### Task P3.2: Architecture Documentation (`ARCHITECTURE.md`)
- ASCII and Mermaid diagrams of STT ➔ Intent Router ➔ LLM ➔ Desktop Controller ➔ TTS.

### Task P3.3: Production README & Portfolio Assets
- Features, Quickstart, Benchmark numbers, Voice Demo script.

---

## 🚀 ENTERPRISE-GRADE SUCCESS CRITERIA

- ✅ **Performance**:
  - All simple commands: `< 600ms`
  - All LLM commands: `< 1200ms` Time-to-First-Speech
  - Smooth, human-like voice synthesis
- ✅ **Reliability**:
  - Zero crashes on network/device disconnects
  - Graceful fallback on LLM or TTS errors
- ✅ **Code Quality**:
  - `mypy --strict` passes with 0 issues
  - `pytest` coverage `> 80%`
- ✅ **Portfolio-Ready**:
  - Clear benchmarks, clean repository structure, enterprise architecture documentation.
