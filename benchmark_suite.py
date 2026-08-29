from __future__ import annotations

import json
import logging
import os
import statistics
import sys
import time
from dataclasses import asdict, dataclass
from typing import Any

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from assistant_core import VoiceAssistant
from config import load_config


@dataclass
class BenchmarkResult:
    command: str
    latencies: list[float]  # milliseconds
    average: float
    median: float
    p95: float
    p99: float
    success_rate: float


class PerformanceBenchmark:
    """Measure Friday's performance against enterprise latency targets."""

    def __init__(self, num_runs: int = 10) -> None:
        self.num_runs = num_runs
        self.results: dict[str, BenchmarkResult] = {}
        self.config = load_config()
        self.config.speak_responses = False  # Disable hardware audio blocking during latency tests
        self.logger = logging.getLogger("friday_bench")
        self.logger.setLevel(logging.WARNING)
        self.assistant = VoiceAssistant(config=self.config, logger=self.logger)

    def benchmark_simple_commands(self) -> None:
        """Test fast-path system commands (Target: < 500ms)."""
        commands = [
            "mute",
            "unmute",
            "what time is it",
            "what is today's date",
            "battery status",
            "system status",
            "show desktop",
            "read my notes",
        ]
        for cmd in commands:
            print(f"[*] Benchmarking fast-path: '{cmd}' ({self.num_runs} runs)...")
            latencies: list[float] = []
            success_count = 0

            for _ in range(self.num_runs):
                start = time.perf_counter_ns()
                # Fast intent routing & action execution
                res = self.assistant.router.route(cmd)
                end = time.perf_counter_ns()

                latency_ms = (end - start) / 1_000_000.0
                latencies.append(latency_ms)
                if res.handled:
                    success_count += 1

            sorted_latencies = sorted(latencies)
            p95_idx = max(0, int(len(sorted_latencies) * 0.95) - 1)
            p99_idx = max(0, int(len(sorted_latencies) * 0.99) - 1)

            self.results[cmd] = BenchmarkResult(
                command=cmd,
                latencies=latencies,
                average=statistics.mean(latencies),
                median=statistics.median(latencies),
                p95=sorted_latencies[p95_idx],
                p99=sorted_latencies[p99_idx],
                success_rate=success_count / self.num_runs,
            )

    def benchmark_multi_step_commands(self) -> None:
        """Test complex multi-step commands."""
        commands = [
            "take a note buy groceries and check system status",
            "set a timer for 10 seconds",
        ]
        for cmd in commands:
            print(f"[*] Benchmarking multi-step: '{cmd}'...")
            latencies: list[float] = []
            success_count = 0

            for _ in range(self.num_runs):
                start = time.perf_counter_ns()
                res = self.assistant.router.route(cmd)
                end = time.perf_counter_ns()

                latency_ms = (end - start) / 1_000_000.0
                latencies.append(latency_ms)
                if res.handled:
                    success_count += 1

            sorted_latencies = sorted(latencies)
            p95_idx = max(0, int(len(sorted_latencies) * 0.95) - 1)
            p99_idx = max(0, int(len(sorted_latencies) * 0.99) - 1)

            self.results[cmd] = BenchmarkResult(
                command=cmd,
                latencies=latencies,
                average=statistics.mean(latencies),
                median=statistics.median(latencies),
                p95=sorted_latencies[p95_idx],
                p99=sorted_latencies[p99_idx],
                success_rate=success_count / self.num_runs,
            )

    def generate_report(self) -> str:
        """Create a structured human-readable benchmark report."""
        report = "=" * 80 + "\n"
        report += "FRIDAY ASSISTANT - ENTERPRISE PERFORMANCE BENCHMARK REPORT\n"
        report += "=" * 80 + "\n\n"

        for cmd, result in self.results.items():
            status = "[PASS]" if result.average < 1500 else "[FAIL]"
            report += f"{status} | Command: \"{cmd}\"\n"
            report += (
                f"  Average: {result.average:.2f}ms | "
                f"Median: {result.median:.2f}ms | "
                f"P95: {result.p95:.2f}ms | P99: {result.p99:.2f}ms\n"
            )
            report += (
                f"  Range: {min(result.latencies):.2f}ms - {max(result.latencies):.2f}ms | "
                f"Success Rate: {result.success_rate * 100:.0f}%\n\n"
            )

        report += "=" * 80 + "\n"
        return report


if __name__ == "__main__":
    bench = PerformanceBenchmark(num_runs=10)
    bench.benchmark_simple_commands()
    bench.benchmark_multi_step_commands()

    report_text = bench.generate_report()
    print(report_text)

    # Save to benchmark_results.txt
    with open("benchmark_results.txt", "w", encoding="utf-8") as f:
        f.write(report_text)

    # Save JSON for programmatic analysis
    with open("benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump({k: asdict(v) for k, v in bench.results.items()}, f, indent=2)

    print("[✓] Benchmark results saved to benchmark_results.txt and benchmark_results.json")
