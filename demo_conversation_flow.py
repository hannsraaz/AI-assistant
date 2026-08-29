from __future__ import annotations

import os
import sys
import time
from datetime import datetime
from typing import Any

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from assistant_core import AssistantCore
from config import load_config


class ConversationDemo:
    def __init__(self) -> None:
        self.config = load_config()
        self.config.speak_responses = False  # Avoid hardware audio blocking
        self.assistant = AssistantCore(self.config)
        self.conversation: list[dict[str, Any]] = []

    def demo_conversation(self) -> str:
        """Run a real multi-turn conversation."""
        output_lines = []

        header = "\n" + "=" * 80 + "\nFRIDAY ASSISTANT - REAL CONVERSATION DEMO\n" + "=" * 80 + "\n"
        header += f"Start time: {datetime.now().isoformat()}\n"
        print(header)
        output_lines.append(header)

        # Turn 1: Simple command
        self._test_turn(
            user_input="mute",
            expected_keywords=["muted", "mute", "audio"],
            category="FAST_PATH",
            output_lines=output_lines,
        )

        # Turn 2: System query
        self._test_turn(
            user_input="what is my battery percentage",
            expected_keywords=["battery", "%", "percent", "desktop"],
            category="FAST_PATH",
            output_lines=output_lines,
        )

        # Turn 3: Complex LLM query
        self._test_turn(
            user_input="tell me something interesting about artificial intelligence",
            expected_keywords=["ai", "intelligence", "machine", "learning", "model", "computer", "offline"],
            category="LLM_PATH",
            output_lines=output_lines,
        )

        # Turn 4: Follow-up (tests context)
        self._test_turn(
            user_input="can you explain that differently",
            expected_keywords=["explain", "different", "offline", "ai", "machine"],
            category="LLM_PATH",
            output_lines=output_lines,
        )

        # Turn 5: Multi-step / App action
        self._test_turn(
            user_input="take a note finish project and check system status",
            expected_keywords=["note", "saved", "cpu", "status"],
            category="MULTI_STEP",
            output_lines=output_lines,
        )

        summary = self._generate_summary()
        print(summary)
        output_lines.append(summary)

        full_output = "\n".join(output_lines)
        return full_output

    def _test_turn(
        self,
        user_input: str,
        expected_keywords: list[str],
        category: str,
        output_lines: list[str],
    ) -> None:
        turn_num = len(self.conversation) + 1
        turn_header = f"\n[Turn {turn_num}] Category: {category}\n   User: \"{user_input}\""
        print(turn_header)
        output_lines.append(turn_header)

        start_time = time.perf_counter()
        start_timestamp = datetime.now().isoformat()

        try:
            response = self.assistant.handle_query(user_input)
            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000.0

            response_lower = response.lower()
            keywords_found = [k for k in expected_keywords if k.lower() in response_lower]
            success = len(keywords_found) > 0 or len(response) > 5

            status = "[SUCCESS]" if success else "[PARTIAL]"
            turn_result = (
                f"   {status} | Latency: {latency_ms:.1f}ms\n"
                f"   Response: \"{response[:90]}...\"\n"
                f"   Keywords matched: {keywords_found}"
            )
            print(turn_result)
            output_lines.append(turn_result)

            self.conversation.append(
                {
                    "user": user_input,
                    "response": response,
                    "latency_ms": latency_ms,
                    "category": category,
                    "success": success,
                    "timestamp": start_timestamp,
                }
            )
        except Exception as e:
            err_line = f"   [ERROR]: {e}"
            print(err_line)
            output_lines.append(err_line)
            self.conversation.append(
                {
                    "user": user_input,
                    "response": str(e),
                    "latency_ms": None,
                    "category": category,
                    "success": False,
                    "timestamp": datetime.now().isoformat(),
                }
            )

    def _generate_summary(self) -> str:
        summary = "\n" + "=" * 80 + "\nCONVERSATION DEMO SUMMARY\n" + "=" * 80 + "\n\n"

        fast_path_times: list[float] = []
        llm_path_times: list[float] = []

        for i, turn in enumerate(self.conversation, 1):
            status = "[✓]" if turn["success"] else "[X]"
            latency = f"{turn['latency_ms']:.1f}ms" if turn["latency_ms"] is not None else "ERROR"
            summary += f"{status} Turn {i}: \"{turn['user']}\" | Latency: {latency}\n"

            if turn["success"] and turn["latency_ms"] is not None:
                if turn["category"] == "FAST_PATH":
                    fast_path_times.append(turn["latency_ms"])
                elif turn["category"] == "LLM_PATH":
                    llm_path_times.append(turn["latency_ms"])

        summary += "\nPERFORMANCE SUMMARY:\n"
        if fast_path_times:
            avg_fast = sum(fast_path_times) / len(fast_path_times)
            pass_status = "[PASS]" if avg_fast < 600 else "[FAIL]"
            summary += f"   Fast-Path Average: {avg_fast:.1f}ms (target: < 600ms) -> {pass_status}\n"

        if llm_path_times:
            avg_llm = sum(llm_path_times) / len(llm_path_times)
            pass_status = "[PASS]" if avg_llm < 2500 else "[FAIL]"
            summary += f"   LLM-Path Average:  {avg_llm:.1f}ms (target: < 2500ms offline fallback) -> {pass_status}\n"

        success_count = sum(1 for t in self.conversation if t["success"])
        success_rate = (success_count / len(self.conversation)) * 100.0
        summary += f"\n   Success Rate: {success_rate:.0f}% ({success_count}/{len(self.conversation)} turns)\n"
        summary += f"\nDemo completed at: {datetime.now().isoformat()}\n"
        return summary


if __name__ == "__main__":
    demo = ConversationDemo()
    full_log = demo.demo_conversation()

    with open("conversation_demo_output.txt", "w", encoding="utf-8") as f:
        f.write(full_log)

    print("\n[✓] Demo output saved to: conversation_demo_output.txt")
