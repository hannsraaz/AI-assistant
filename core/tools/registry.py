from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from typing import Any

from core.tools.base import BaseTool, RiskLevel, ToolResult
from core.tools.permissions import PermissionManager

logger = logging.getLogger("tool_registry")


class ToolRegistry:
    """Central registry and execution dispatcher for all Friday tools."""

    def __init__(self, permission_manager: PermissionManager | None = None) -> None:
        self._tools: dict[str, BaseTool] = {}
        self.permissions = permission_manager or PermissionManager()

    def register(self, tool: BaseTool) -> None:
        """Register a tool instance."""
        if not tool.name:
            raise ValueError(f"Tool {tool.__class__.__name__} must define a unique 'name'.")
        self._tools[tool.name] = tool
        logger.debug("Registered tool: %s (%s)", tool.name, tool.risk_level.value)

    def register_many(self, tools: Sequence[BaseTool]) -> None:
        """Register multiple tools at once."""
        for tool in tools:
            self.register(tool)

    def get(self, name: str) -> BaseTool | None:
        """Retrieve tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> list[str]:
        """List all registered tool names."""
        return sorted(self._tools.keys())

    def find_by_capability(self, capability: str) -> list[BaseTool]:
        """Find all tools declaring a specific capability."""
        cap_clean = capability.lower().strip()
        return [t for t in self._tools.values() if any(cap_clean in c.lower() for c in t.capabilities)]

    def get_schemas(self) -> list[dict[str, Any]]:
        """Get OpenAI / Ollama compatible function calling schemas."""
        return [tool.get_schema() for tool in self._tools.values()]

    def execute(self, tool_name: str, confirmed: bool = False, **kwargs: Any) -> ToolResult:
        """Execute tool with permission checking."""
        tool = self._tools.get(tool_name)
        if not tool:
            return ToolResult(
                success=False,
                error=f"Tool '{tool_name}' is not registered in Friday's tool registry.",
            )

        try:
            return self.permissions.check_and_execute(tool, kwargs, confirmed=confirmed)
        except Exception as exc:
            logger.exception("Error executing tool '%s': %s", tool_name, exc)
            return ToolResult(
                success=False,
                error=f"Execution error in tool '{tool_name}': {exc}",
            )


# Global default registry
default_registry = ToolRegistry()
