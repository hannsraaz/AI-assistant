from __future__ import annotations

import logging
import time
from typing import Any

from core.tools.base import BaseTool, RiskLevel, ToolError, ToolResult

logger = logging.getLogger("permissions")


class PermissionManager:
    """Centralized security and permission manager for Friday tools.
    
    Ensures that tools requiring confirmation cannot be executed
    silently by the LLM or direct invocations without approval.
    """

    def __init__(self, auto_confirm_safe: bool = True) -> None:
        self.auto_confirm_safe = auto_confirm_safe
        self._pending_confirmations: dict[str, dict[str, Any]] = {}
        self._allowed_overrides: set[str] = set()

    def set_override(self, tool_name: str, allowed: bool = True) -> None:
        """Allow whitelisting specific tools if desired by user configuration."""
        if allowed:
            self._allowed_overrides.add(tool_name)
        else:
            self._allowed_overrides.discard(tool_name)

    # Parameter aliases for flexible execution
    PARAM_ALIASES: dict[str, list[str]] = {
        "app_name": ["target", "name", "app", "application", "path"],
        "query": ["q", "search_query", "search", "text"],
        "path": ["file_path", "filepath", "target", "file"],
        "message": ["text", "msg", "content", "prompt"],
        "command": ["cmd"],
        "text": ["content", "message"],
        "percentage": ["percent", "level", "value"],
        "level": ["percentage", "percent", "value"],
    }

    def check_and_execute(
        self,
        tool: BaseTool,
        kwargs: dict[str, Any],
        confirmed: bool = False,
    ) -> ToolResult:
        """Evaluate tool execution safety and execute if authorized."""
        # 1. Normalize parameter aliases and validate required parameters
        schema = tool.parameters or {}
        required_fields = schema.get("required", [])
        for field in required_fields:
            if field not in kwargs:
                # Check for aliases
                for alias in self.PARAM_ALIASES.get(field, []):
                    if alias in kwargs and kwargs[alias] is not None:
                        kwargs[field] = kwargs[alias]
                        break

            if field not in kwargs:
                return ToolResult(
                    success=False,
                    error=ToolError(
                        code="MISSING_ARGUMENT",
                        message=f"Missing required argument '{field}' for tool '{tool.name}'.",
                        details={"required": required_fields, "provided": list(kwargs.keys())},
                    ),
                )

        # 2. Safe tools or whitelisted overrides execute immediately
        if tool.risk_level == RiskLevel.SAFE or tool.name in self._allowed_overrides:
            return tool.execute(**kwargs)

        # 3. If confirmed by user, execute directly
        if confirmed:
            logger.info("Executing confirmed action: %s", tool.name)
            return tool.execute(**kwargs)

        # 4. Requires confirmation -> Generate token
        confirmation_token = f"{tool.name}_{int(time.time())}_{id(tool)}"
        prompt = self._build_prompt(tool, kwargs)

        self._pending_confirmations[confirmation_token] = {
            "tool": tool,
            "kwargs": kwargs,
            "timestamp": time.time(),
        }

        return ToolResult(
            success=False,
            message=f"Action '{tool.name}' requires confirmation. {prompt}",
            data={"confirmation_token": confirmation_token, "tool_name": tool.name},
            error=ToolError(
                code="PERMISSION_REQUIRED",
                message=prompt,
                details={"risk_level": tool.risk_level.value, "token": confirmation_token},
            ),
            needs_confirmation=True,
            confirmation_prompt=prompt,
        )

    def confirm_token(self, token: str) -> ToolResult:
        """Confirm and execute a pending tokenized action."""
        entry = self._pending_confirmations.pop(token, None)
        if not entry:
            return ToolResult(
                success=False,
                error=ToolError(
                    code="INVALID_TOKEN",
                    message="Confirmation token expired, invalid, or already consumed.",
                ),
            )

        if time.time() - entry["timestamp"] > 60:
            return ToolResult(
                success=False,
                error=ToolError(
                    code="TOKEN_TIMEOUT",
                    message="Confirmation token timed out (60-second window exceeded).",
                ),
            )

        tool: BaseTool = entry["tool"]
        kwargs: dict[str, Any] = entry["kwargs"]
        return tool.execute(**kwargs)

    def cancel_pending(self, token: str | None = None) -> None:
        """Cancel all or specific pending confirmations."""
        if token:
            self._pending_confirmations.pop(token, None)
        else:
            self._pending_confirmations.clear()

    def _build_prompt(self, tool: BaseTool, kwargs: dict[str, Any]) -> str:
        if tool.risk_level == RiskLevel.HIGH_RISK:
            return f"High-risk action '{tool.name}' requires explicit confirmation. Arguments: {kwargs}."
        return f"Please confirm execution of '{tool.name}' with arguments: {kwargs}."
