from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.tools.base import BaseTool, RiskLevel, ToolResult
from core.tools.registry import ToolRegistry


class WorkflowEngine:
    """Stores and executes automated multi-action routines."""

    def __init__(self, registry: ToolRegistry, workflows_file: str | Path = "data/workflows.json") -> None:
        self.registry = registry
        self.workflows_file = Path(workflows_file)
        self.workflows_file.parent.mkdir(parents=True, exist_ok=True)
        self._workflows: dict[str, list[dict[str, Any]]] = self._load()

    def _load(self) -> dict[str, list[dict[str, Any]]]:
        if self.workflows_file.exists():
            try:
                with self.workflows_file.open("r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        # Default built-in routines
        return {
            "morning_routine": [
                {"tool": "system.brightness.set", "args": {"level": 80}},
                {"tool": "system.volume.set", "args": {"percentage": 50}},
                {"tool": "apps.open", "args": {"app_name": "chrome"}},
                {"tool": "apps.open", "args": {"app_name": "code"}},
            ],
            "focus_mode": [
                {"tool": "system.volume.set", "args": {"percentage": 30}},
                {"tool": "windows.show_desktop", "args": {}},
                {"tool": "apps.open", "args": {"app_name": "code"}},
            ],
        }

    def _save(self) -> None:
        with self.workflows_file.open("w", encoding="utf-8") as f:
            json.dump(self._workflows, f, indent=2)

    def run_workflow(self, name: str) -> tuple[bool, str]:
        clean = name.lower().strip().replace(" ", "_")
        steps = self._workflows.get(clean)
        if not steps:
            return False, f"Workflow '{name}' not found."

        executed = 0
        for step in steps:
            tool_name = step.get("tool", "")
            args = step.get("args", {})
            res = self.registry.execute(tool_name, **args)
            if res.success:
                executed += 1

        return True, f"Executed workflow '{name}' ({executed}/{len(steps)} steps successful)."

    def save_workflow(self, name: str, steps: list[dict[str, Any]]) -> None:
        clean = name.lower().strip().replace(" ", "_")
        self._workflows[clean] = steps
        self._save()

    def list_workflows(self) -> list[str]:
        return list(self._workflows.keys())


# --- Workflow Tools ---

class WorkflowRunTool(BaseTool):
    name = "workflow.run"
    description = "Run a saved automation workflow or routine (e.g. 'morning_routine', 'focus_mode')."
    risk_level = RiskLevel.SAFE
    parameters = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Name of the workflow to run."}
        },
        "required": ["name"],
    }

    def __init__(self, engine: WorkflowEngine) -> None:
        self.engine = engine

    def execute(self, name: str, **kwargs: Any) -> ToolResult:
        success, msg = self.engine.run_workflow(name)
        return ToolResult(
            success=success,
            message=msg if success else "",
            error=None if success else msg,
            data={"workflow": name},
        )


class WorkflowListTool(BaseTool):
    name = "workflow.list"
    description = "List all available automation workflows."
    risk_level = RiskLevel.SAFE
    parameters = {"type": "object", "properties": {}}

    def __init__(self, engine: WorkflowEngine) -> None:
        self.engine = engine

    def execute(self, **kwargs: Any) -> ToolResult:
        names = self.engine.list_workflows()
        return ToolResult(
            success=True,
            message=f"Available workflows: {', '.join(names)}.",
            data={"workflows": names},
        )
