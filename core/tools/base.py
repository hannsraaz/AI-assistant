from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RiskLevel(str, Enum):
    SAFE = "SAFE"                # Can be executed immediately without prompt
    CONFIRM = "CONFIRM"          # Requires user confirmation (e.g. closing unsaved app, restart, file delete)
    HIGH_RISK = "HIGH_RISK"      # Explicit confirmation required every time (e.g. shutdown, mass kill)


@dataclass(slots=True)
class ToolError:
    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
        }


@dataclass(slots=True)
class ToolResult:
    success: bool
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    error: ToolError | str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    needs_confirmation: bool = False
    confirmation_prompt: str | None = None

    def get_error_message(self) -> str:
        if isinstance(self.error, ToolError):
            return self.error.message
        return self.error or ""

    def get_error_code(self) -> str:
        if isinstance(self.error, ToolError):
            return self.error.code
        return "UNKNOWN_ERROR" if self.error else ""

    def to_dict(self) -> dict[str, Any]:
        err_dict = self.error.to_dict() if isinstance(self.error, ToolError) else ({"message": self.error} if self.error else None)
        return {
            "success": self.success,
            "message": self.message,
            "data": self.data,
            "error": err_dict,
            "metadata": self.metadata,
            "needs_confirmation": self.needs_confirmation,
            "confirmation_prompt": self.confirmation_prompt,
        }


class BaseTool(ABC):
    """Abstract base class for all Friday tools."""

    name: str = ""
    description: str = ""
    risk_level: RiskLevel = RiskLevel.SAFE
    parameters: dict[str, Any] = {}
    capabilities: list[str] = []
    cancellable: bool = True
    reversible: bool = False
    has_side_effects: bool = False

    @abstractmethod
    def execute(self, *args: Any, **kwargs: Any) -> ToolResult:
        """Execute the tool logic and return a structured ToolResult."""
        pass

    def get_schema(self) -> dict[str, Any]:
        """Return OpenAI / Ollama compatible function schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters or {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        }
