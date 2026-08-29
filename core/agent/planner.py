from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from core.agent.task_manager import TaskEvent, TaskRecord, TaskStatus, TaskStep, TaskStepStatus
from core.agent.verifier import StepVerifier
from core.tools.base import ToolError, ToolResult
from core.tools.registry import ToolRegistry
from llm_agent import OllamaClient

logger = logging.getLogger("planner")


class AgenticPlanner:
    """Unified Agent Execution Loop: Understand -> Plan -> Act -> Observe -> Verify -> Recover -> Report."""

    def __init__(
        self,
        registry: ToolRegistry,
        llm_client: OllamaClient,
        max_retries_per_step: int = 2,
    ) -> None:
        self.registry = registry
        self.llm = llm_client
        self.max_retries = max_retries_per_step
        self.verifier = StepVerifier(registry)

    def plan_and_execute(self, user_goal: str, task: TaskRecord | None = None) -> str:
        """Break down goal, select tools, execute sequentially with active failure diagnosis and recovery."""
        tool_names = self.registry.list_tools()

        # 1. PLAN PHASE
        system_prompt = (
            "You are Friday's autonomous computer agent planner. Given a user goal and available tools, "
            "break the task down into a sequential JSON plan of 1 to 4 logical steps.\n"
            f"Available tools: {json.dumps(tool_names[:40])}\n"
            "Format your response strictly as a JSON array of objects with keys: 'description', 'tool', 'args', 'expected_result'. "
            "Do NOT include conversational explanation outside the JSON array."
        )

        prompt = f"Goal: {user_goal}\nJSON Plan:"
        raw_response = ""
        try:
            for token in self.llm.stream_chat(prompt, history=[{"role": "system", "content": system_prompt}]):
                raw_response += token
        except Exception as exc:
            logger.warning("LLM planning query error: %s", exc)

        steps_data = self._extract_json_array(raw_response)
        if not steps_data:
            steps_data = [{
                "description": "Execute goal",
                "tool": "terminal.execute",
                "args": {"command": f"echo {user_goal}"},
                "expected_result": "Goal executed",
            }]

        if task:
            task.steps = [
                TaskStep(
                    step_id=f"step_{i+1}_{uuid.uuid4().hex[:4]}",
                    description=s.get("description", f"Step {i+1}"),
                    tool=s.get("tool", ""),
                    arguments=s.get("args", {}),
                    expected_result=s.get("expected_result", "Success"),
                )
                for i, s in enumerate(steps_data)
            ]
            task.emit_event(TaskEvent.PLAN_CREATED, f"Generated {len(task.steps)}-step plan for '{user_goal}'.")

        # 2. EXECUTE -> OBSERVE -> VERIFY -> RECOVER LOOP
        results_summary: list[str] = []

        for i, step in enumerate(task.steps if task else [TaskStep("1", s["description"], s["tool"], s.get("args", {})) for s in steps_data]):
            if task and task.stop_event.is_set():
                step.status = TaskStepStatus.CANCELLED
                task.status = TaskStatus.CANCELLED
                task.emit_event(TaskEvent.TASK_CANCELLED, "Task cancelled by user.")
                return "Task cancelled."

            if task:
                task.status = TaskStatus.STEP_EXECUTING
                task.current_step = i + 1
                step.status = TaskStepStatus.RUNNING
                task.emit_event(TaskEvent.STEP_STARTED, f"Starting step {i+1}/{len(task.steps)}: {step.description}")

            # Execute with active repair loop
            step_res = self._execute_step_with_repair(step, task=task)

            if not step_res.success:
                step.status = TaskStepStatus.FAILED
                step.error = step_res.get_error_message()
                if task:
                    task.status = TaskStatus.FAILED
                    task.error = step.error
                    task.emit_event(TaskEvent.STEP_FAILED, f"Step {i+1} failed: {step.error}")
                    task.emit_event(TaskEvent.TASK_FAILED, f"Task halted at step {i+1}: {step.error}")
                return f"Task halted at {step.description}: {step.error}"

            step.status = TaskStepStatus.SUCCESS
            step.actual_result = step_res.message
            if task:
                task.emit_event(TaskEvent.STEP_SUCCEEDED, f"Step {i+1} succeeded: {step_res.message}")
            results_summary.append(f"{step.description}: {step_res.message}")

        if task:
            task.status = TaskStatus.COMPLETED
            task.emit_event(TaskEvent.TASK_COMPLETED, "All task steps completed and verified successfully.")

        return f"Completed: {'; '.join(results_summary)}"

    def _execute_step_with_repair(
        self,
        step: TaskStep,
        task: TaskRecord | None = None,
    ) -> ToolResult:
        """Execute step, observe result, verify, and diagnose/repair if needed."""
        current_tool = step.tool
        current_args = dict(step.arguments)

        for attempt in range(1 + self.max_retries):
            step.attempt_count = attempt + 1
            if task and task.stop_event.is_set():
                return ToolResult(success=False, error=ToolError(code="CANCELLED", message="Task cancelled."))

            if attempt > 0:
                step.status = TaskStepStatus.RETRYING
                if task:
                    task.emit_event(TaskEvent.RETRY_STARTED, f"Retrying step '{step.description}' (attempt {attempt+1})...")

            # 1. ACT
            res = self.registry.execute(current_tool, **current_args)
            if task:
                task.emit_event(TaskEvent.TOOL_EXECUTED, f"Executed tool '{current_tool}' (success={res.success}).")

            # 2. OBSERVE & VERIFY
            if res.success:
                verified, v_msg = self.verifier.verify_step(current_tool, current_args, res)
                step.verification = v_msg
                if verified:
                    return res
                else:
                    res = ToolResult(
                        success=False,
                        error=ToolError(code="VERIFICATION_FAILED", message=v_msg),
                    )

            # 3. RECOVER / DIAGNOSE / REPAIR
            err_msg = res.get_error_message()
            if attempt < self.max_retries:
                if task:
                    task.emit_event(TaskEvent.REPAIR_STARTED, f"Diagnosing failure ({res.get_error_code()}): {err_msg}")
                repaired_args = self._diagnose_and_repair(current_tool, current_args, err_msg)
                if repaired_args:
                    current_args = repaired_args
                else:
                    break

        return res

    def _diagnose_and_repair(self, tool_name: str, failed_args: dict[str, Any], error_message: str) -> dict[str, Any] | None:
        """Query LLM for adjusted arguments or alternative parameter values."""
        prompt = (
            f"Tool '{tool_name}' failed with arguments {json.dumps(failed_args)}.\n"
            f"Error message: {error_message}\n"
            "Return a corrected JSON object of arguments to fix this error, or an empty JSON object {} if unfixable. "
            "Output ONLY the JSON object."
        )
        try:
            raw = ""
            for tok in self.llm.stream_chat(prompt):
                raw += tok
            start = raw.find("{")
            end = raw.rfind("}")
            if start != -1 and end != -1:
                repaired = json.loads(raw[start : end + 1])
                if isinstance(repaired, dict) and repaired:
                    return repaired
        except Exception:
            pass
        return None

    def _extract_json_array(self, text: str) -> list[dict[str, Any]]:
        try:
            start = text.find("[")
            end = text.rfind("]")
            if start != -1 and end != -1:
                data = json.loads(text[start : end + 1])
                if isinstance(data, list):
                    return [item for item in data if isinstance(item, dict)]
        except Exception:
            pass
        return []
