from __future__ import annotations

import json
import statistics
import time
from pathlib import Path

from assistant_core import VoiceAssistant
from config import AppConfig


def run_benchmarks() -> dict[str, dict[str, float]]:
    config = AppConfig()
    config.speak_responses = False
    config.wake_word.enabled = False
    assistant = VoiceAssistant(config)

    metrics: dict[str, list[float]] = {
        "fast_path_volume": [],
        "fast_path_system_stats": [],
        "fast_path_time_date": [],
        "file_search_real": [],
        "memory_recall_real": [],
        "llm_chat_first_token": [],
        "llm_chat_total": [],
    }

    # 1. Fast-Path Benchmarks (30 rounds each)
    for _ in range(30):
        t0 = time.perf_counter()
        assistant.handle_query("set volume to 55 percent")
        metrics["fast_path_volume"].append((time.perf_counter() - t0) * 1000.0)

        t0 = time.perf_counter()
        assistant.handle_query("system status")
        metrics["fast_path_system_stats"].append((time.perf_counter() - t0) * 1000.0)

        t0 = time.perf_counter()
        assistant.handle_query("what time is it")
        metrics["fast_path_time_date"].append((time.perf_counter() - t0) * 1000.0)

    # 2. File search & memory benchmarks (20 rounds)
    for _ in range(20):
        t0 = time.perf_counter()
        assistant.registry.execute("files.search", query="*.py", directory=str(Path.cwd()))
        metrics["file_search_real"].append((time.perf_counter() - t0) * 1000.0)

        t0 = time.perf_counter()
        assistant.registry.execute("memory.recall", query="project")
        metrics["memory_recall_real"].append((time.perf_counter() - t0) * 1000.0)

    # 3. LLM latency benchmark (5 rounds)
    for _ in range(5):
        t0 = time.perf_counter()
        first_token = True
        t_first = 0.0
        for chunk in assistant.llm.stream_chat("Give a one sentence greeting."):
            if first_token:
                t_first = (time.perf_counter() - t0) * 1000.0
                first_token = False
        t_total = (time.perf_counter() - t0) * 1000.0
        if t_first > 0:
            metrics["llm_chat_first_token"].append(t_first)
        metrics["llm_chat_total"].append(t_total)

    results: dict[str, dict[str, float]] = {}
    print("=" * 65)
    print(f"{'Operation':<30} | {'P50 (ms)':<10} | {'P95 (ms)':<10} | {'P99 (ms)':<10}")
    print("-" * 65)

    for op, data in metrics.items():
        if not data:
            continue
        sorted_d = sorted(data)
        n = len(sorted_d)
        p50 = statistics.median(sorted_d)
        p95 = sorted_d[int(0.95 * n) - 1] if n >= 20 else sorted_d[-1]
        p99 = sorted_d[int(0.99 * n) - 1] if n >= 20 else sorted_d[-1]
        results[op] = {"p50": round(p50, 2), "p95": round(p95, 2), "p99": round(p99, 2)}
        print(f"{op:<30} | {p50:<10.2f} | {p95:<10.2f} | {p99:<10.2f}")

    print("=" * 65)
    return results


if __name__ == "__main__":
    res = run_benchmarks()
    with open("benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
