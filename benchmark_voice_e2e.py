"""Real Hardware Voice Pipeline Latency Benchmark for FRIDAY V4."""
from __future__ import annotations

import time
import numpy as np

from audio_vad import SileroVADEngine, VADConfig
from audio_stream import AudioRingBuffer, ContinuousAudioCapture
from wake_word import WakeWordDetector
from audio_stt import SpeechToTextService
from config import load_config


def run_benchmark() -> None:
    config = load_config()
    print("=" * 65)
    print("FRIDAY V4 REAL HARDWARE VOICE PIPELINE BENCHMARK")
    print("=" * 65)

    # 1. Silero VAD Inference Benchmark
    print("\n[1/4] Benchmarking Silero VAD ONNX Engine...")
    vad = SileroVADEngine(VADConfig(sample_rate=16000))
    dummy_512 = np.zeros(512, dtype=np.float32)

    # Warmup
    for _ in range(10):
        vad.process_chunk(dummy_512)

    vad_times = []
    for _ in range(100):
        t0 = time.perf_counter()
        vad.process_chunk(dummy_512)
        vad_times.append((time.perf_counter() - t0) * 1000.0)

    p50_vad = np.percentile(vad_times, 50)
    p95_vad = np.percentile(vad_times, 95)
    p99_vad = np.percentile(vad_times, 99)
    print(f" -> Silero VAD 32ms Chunk (512 samples): P50={p50_vad:.3f}ms | P95={p95_vad:.3f}ms | P99={p99_vad:.3f}ms")

    # 2. Audio Ring Buffer Benchmark
    print("\n[2/4] Benchmarking AudioRingBuffer Operations...")
    buf = AudioRingBuffer(capacity_seconds=5.0, sample_rate=16000)
    chunk = np.random.randn(512).astype(np.float32)

    buf_times = []
    for _ in range(1000):
        t0 = time.perf_counter()
        buf.write(chunk)
        _ = buf.get_last_seconds(0.35)
        buf_times.append((time.perf_counter() - t0) * 1000.0)

    p50_buf = np.percentile(buf_times, 50)
    p95_buf = np.percentile(buf_times, 95)
    print(f" -> Ring Buffer Write + 350ms Read: P50={p50_buf:.3f}ms | P95={p95_buf:.3f}ms")

    # 3. openWakeWord Inference Benchmark
    print("\n[3/4] Benchmarking openWakeWord ONNX Engine...")
    import logging
    ww = WakeWordDetector(config.wake_word, logger=logging.getLogger("bench"))
    try:
        ww.warmup()
        dummy_1280 = np.zeros(1280, dtype=np.int16)
        ww_times = []
        for _ in range(50):
            t0 = time.perf_counter()
            ww._run_model_prediction(dummy_1280)
            ww_times.append((time.perf_counter() - t0) * 1000.0)

        p50_ww = np.percentile(ww_times, 50)
        p95_ww = np.percentile(ww_times, 95)
        print(f" -> openWakeWord 80ms Chunk (1280 samples): P50={p50_ww:.2f}ms | P95={p95_ww:.2f}ms")
    except Exception as exc:
        print(f" -> openWakeWord benchmark skipped: {exc}")

    # 4. faster-whisper STT Benchmark
    print("\n[4/4] Benchmarking faster-whisper Transcription...")
    stt = SpeechToTextService(config.stt)
    try:
        stt.warmup()
        # 1.5s audio array of sine wave
        audio_1_5s = (np.sin(np.linspace(0, 300 * np.pi, 24000)) * 0.3).astype(np.float32)
        stt_times = []
        for _ in range(5):
            t0 = time.perf_counter()
            stt.transcribe_array(audio_1_5s)
            stt_times.append((time.perf_counter() - t0) * 1000.0)

        p50_stt = np.percentile(stt_times, 50)
        p95_stt = np.percentile(stt_times, 95)
        print(f" -> faster-whisper 1.5s Audio Array: P50={p50_stt:.1f}ms | P95={p95_stt:.1f}ms")
    except Exception as exc:
        print(f" -> faster-whisper benchmark error: {exc}")

    print("\n" + "=" * 65)
    print("BENCHMARK COMPLETE")
    print("=" * 65)


if __name__ == "__main__":
    run_benchmark()
