from __future__ import annotations

import os
import subprocess
import sys


def run_proofs() -> None:
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    venv_python = sys.executable
    venv_pytest = str(os.path.join(os.path.dirname(venv_python), "pytest.exe"))
    venv_mypy = str(os.path.join(os.path.dirname(venv_python), "mypy.exe"))

    # 1. Run pytest full suite
    print("[1/4] Running pytest suite...")
    p1 = subprocess.run(
        [
            venv_pytest,
            "tests/",
            "test_llm_conversation.py",
            "test_tool_calling.py",
            "test_error_scenarios.py",
            "-v",
            "--tb=short",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    with open("pytest_output.txt", "w", encoding="utf-8") as f:
        f.write(p1.stdout + "\n" + p1.stderr)
    print(f"  [OK] pytest_output.txt written (Return code: {p1.returncode})")

    # 2. Run pytest coverage
    print("[2/4] Running pytest coverage...")
    p2 = subprocess.run(
        [
            venv_pytest,
            "tests/",
            "--cov=desktop_controller",
            "--cov=intent_router",
            "--cov=assistant_core",
            "--cov=audio_stt",
            "--cov=audio_tts",
            "--cov-report=term-missing",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    with open("pytest_coverage.txt", "w", encoding="utf-8") as f:
        f.write(p2.stdout + "\n" + p2.stderr)
    print(f"  [OK] pytest_coverage.txt written (Return code: {p2.returncode})")

    # 3. Run mypy
    print("[3/4] Running mypy type checker...")
    p3 = subprocess.run(
        [
            venv_mypy,
            "config.py",
            "assistant_core.py",
            "desktop_controller.py",
            "intent_router.py",
            "audio_stt.py",
            "audio_tts.py",
            "llm_agent.py",
            "logger_config.py",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    with open("mypy_results.txt", "w", encoding="utf-8") as f:
        f.write(p3.stdout + "\n" + p3.stderr)
    print(f"  [OK] mypy_results.txt written (Return code: {p3.returncode})")

    # 4. Run conversation flow demo
    print("[4/4] Running conversation flow demo...")
    p4 = subprocess.run(
        [venv_python, "demo_conversation_flow.py"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    with open("conversation_demo_output.txt", "w", encoding="utf-8") as f:
        f.write(p4.stdout + "\n" + p4.stderr)
    print(f"  [OK] conversation_demo_output.txt written (Return code: {p4.returncode})")

    print("\n[OK] All proof test deliverables generated successfully!")


if __name__ == "__main__":
    run_proofs()
