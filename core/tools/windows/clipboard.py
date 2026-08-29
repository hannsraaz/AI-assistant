from __future__ import annotations

from typing import Any

from core.tools.base import BaseTool, RiskLevel, ToolResult


class ClipboardReadTool(BaseTool):
    name = "clipboard.read"
    description = "Read the current text content from the Windows clipboard."
    risk_level = RiskLevel.SAFE
    parameters = {"type": "object", "properties": {}}

    def execute(self, **kwargs: Any) -> ToolResult:
        try:
            import pyperclip

            text = pyperclip.paste()
            if not text or not text.strip():
                return ToolResult(
                    success=True,
                    message="The clipboard is currently empty.",
                    data={"empty": True, "text": ""},
                )
            preview = text[:150] + ("..." if len(text) > 150 else "")
            return ToolResult(
                success=True,
                message=f"Clipboard contains: {preview}",
                data={"text": text, "preview": preview, "length": len(text)},
            )
        except Exception as exc:
            return ToolResult(success=False, error=f"Failed to read clipboard: {exc}")


class ClipboardWriteTool(BaseTool):
    name = "clipboard.write"
    description = "Copy text to the Windows clipboard."
    risk_level = RiskLevel.SAFE
    parameters = {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text to write to clipboard."}
        },
        "required": ["text"],
    }

    def execute(self, text: str, **kwargs: Any) -> ToolResult:
        try:
            import pyperclip

            pyperclip.copy(text)
            return ToolResult(
                success=True,
                message="Copied text to clipboard.",
                data={"length": len(text)},
            )
        except Exception as exc:
            return ToolResult(success=False, error=f"Failed to write clipboard: {exc}")


class ClipboardClearTool(BaseTool):
    name = "clipboard.clear"
    description = "Clear all contents from the Windows clipboard."
    risk_level = RiskLevel.SAFE
    parameters = {"type": "object", "properties": {}}

    def execute(self, **kwargs: Any) -> ToolResult:
        try:
            import pyperclip

            pyperclip.copy("")
            return ToolResult(success=True, message="Clipboard cleared.")
        except Exception as exc:
            return ToolResult(success=False, error=f"Failed to clear clipboard: {exc}")
