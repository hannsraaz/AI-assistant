from __future__ import annotations

import time
from typing import Any

from core.tools.base import BaseTool, RiskLevel, ToolResult


class KeyboardTypeTool(BaseTool):
    name = "keyboard.type"
    description = "Type text into the currently active window or input field."
    risk_level = RiskLevel.SAFE
    parameters = {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text to type."},
            "interval": {"type": "number", "description": "Delay between keystrokes in seconds.", "default": 0.01},
        },
        "required": ["text"],
    }

    def execute(self, text: str, interval: float = 0.01, **kwargs: Any) -> ToolResult:
        try:
            import pyautogui

            pyautogui.write(text, interval=interval)
            return ToolResult(
                success=True,
                message=f"Typed {len(text)} characters.",
                data={"length": len(text)},
            )
        except Exception as exc:
            return ToolResult(success=False, error=f"Typing error: {exc}")


class KeyboardPressTool(BaseTool):
    name = "keyboard.press"
    description = "Press a single special key (e.g. 'enter', 'escape', 'tab', 'space', 'backspace', 'up', 'down')."
    risk_level = RiskLevel.SAFE
    parameters = {
        "type": "object",
        "properties": {
            "key": {"type": "string", "description": "Key name to press (e.g. 'enter', 'esc', 'tab')."}
        },
        "required": ["key"],
    }

    def execute(self, key: str, **kwargs: Any) -> ToolResult:
        try:
            import pyautogui

            clean_key = key.strip().lower()
            pyautogui.press(clean_key)
            return ToolResult(success=True, message=f"Pressed {clean_key}.", data={"key": clean_key})
        except Exception as exc:
            return ToolResult(success=False, error=f"Key press error: {exc}")


class KeyboardHotkeyTool(BaseTool):
    name = "keyboard.hotkey"
    description = "Execute a keyboard shortcut / hotkey combination (e.g. 'ctrl, shift, p' or 'ctrl, c')."
    risk_level = RiskLevel.SAFE
    parameters = {
        "type": "object",
        "properties": {
            "keys": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of keys in combination (e.g. ['ctrl', 'shift', 'p'] or ['alt', 'tab']).",
            }
        },
        "required": ["keys"],
    }

    def execute(self, keys: list[str], **kwargs: Any) -> ToolResult:
        try:
            import pyautogui

            clean_keys = [k.strip().lower() for k in keys]
            pyautogui.hotkey(*clean_keys)
            combo = "+".join(clean_keys)
            return ToolResult(
                success=True,
                message=f"Pressed shortcut {combo}.",
                data={"hotkey": combo, "keys": clean_keys},
            )
        except Exception as exc:
            return ToolResult(success=False, error=f"Hotkey error: {exc}")


class MouseMoveTool(BaseTool):
    name = "mouse.move"
    description = "Move mouse cursor to specific screen coordinates (x, y)."
    risk_level = RiskLevel.SAFE
    parameters = {
        "type": "object",
        "properties": {
            "x": {"type": "integer", "description": "X coordinate on screen."},
            "y": {"type": "integer", "description": "Y coordinate on screen."},
            "duration": {"type": "number", "description": "Movement duration in seconds.", "default": 0.2},
        },
        "required": ["x", "y"],
    }

    def execute(self, x: int, y: int, duration: float = 0.2, **kwargs: Any) -> ToolResult:
        try:
            import pyautogui

            pyautogui.moveTo(x, y, duration=duration)
            return ToolResult(
                success=True,
                message=f"Moved mouse to ({x}, {y}).",
                data={"x": x, "y": y},
            )
        except Exception as exc:
            return ToolResult(success=False, error=f"Mouse move error: {exc}")


class MouseClickTool(BaseTool):
    name = "mouse.click"
    description = "Click mouse button at current position or specified coordinates (x, y)."
    risk_level = RiskLevel.SAFE
    parameters = {
        "type": "object",
        "properties": {
            "x": {"type": "integer", "description": "Optional X coordinate."},
            "y": {"type": "integer", "description": "Optional Y coordinate."},
            "button": {"type": "string", "enum": ["left", "right", "middle"], "default": "left"},
        },
    }

    def execute(self, x: int | None = None, y: int | None = None, button: str = "left", **kwargs: Any) -> ToolResult:
        try:
            import pyautogui

            if x is not None and y is not None:
                pyautogui.click(x=x, y=y, button=button)
            else:
                pyautogui.click(button=button)
            pos = pyautogui.position()
            return ToolResult(
                success=True,
                message=f"Clicked {button} button at ({pos.x}, {pos.y}).",
                data={"x": pos.x, "y": pos.y, "button": button},
            )
        except Exception as exc:
            return ToolResult(success=False, error=f"Click error: {exc}")


class MouseDoubleClickTool(BaseTool):
    name = "mouse.double_click"
    description = "Double-click the left mouse button at current position or specified coordinates."
    risk_level = RiskLevel.SAFE
    parameters = {
        "type": "object",
        "properties": {
            "x": {"type": "integer", "description": "Optional X coordinate."},
            "y": {"type": "integer", "description": "Optional Y coordinate."},
        },
    }

    def execute(self, x: int | None = None, y: int | None = None, **kwargs: Any) -> ToolResult:
        try:
            import pyautogui

            if x is not None and y is not None:
                pyautogui.doubleClick(x=x, y=y)
            else:
                pyautogui.doubleClick()
            pos = pyautogui.position()
            return ToolResult(
                success=True,
                message=f"Double-clicked at ({pos.x}, {pos.y}).",
                data={"x": pos.x, "y": pos.y},
            )
        except Exception as exc:
            return ToolResult(success=False, error=f"Double-click error: {exc}")


class MouseRightClickTool(BaseTool):
    name = "mouse.right_click"
    description = "Right-click mouse button to open context menu."
    risk_level = RiskLevel.SAFE
    parameters = {
        "type": "object",
        "properties": {
            "x": {"type": "integer", "description": "Optional X coordinate."},
            "y": {"type": "integer", "description": "Optional Y coordinate."},
        },
    }

    def execute(self, x: int | None = None, y: int | None = None, **kwargs: Any) -> ToolResult:
        try:
            import pyautogui

            if x is not None and y is not None:
                pyautogui.rightClick(x=x, y=y)
            else:
                pyautogui.rightClick()
            pos = pyautogui.position()
            return ToolResult(
                success=True,
                message=f"Right-clicked at ({pos.x}, {pos.y}).",
                data={"x": pos.x, "y": pos.y},
            )
        except Exception as exc:
            return ToolResult(success=False, error=f"Right-click error: {exc}")


class MouseScrollTool(BaseTool):
    name = "mouse.scroll"
    description = "Scroll the mouse wheel up (positive value) or down (negative value)."
    risk_level = RiskLevel.SAFE
    parameters = {
        "type": "object",
        "properties": {
            "clicks": {"type": "integer", "description": "Number of scroll clicks (positive for up, negative for down)."}
        },
        "required": ["clicks"],
    }

    def execute(self, clicks: int, **kwargs: Any) -> ToolResult:
        try:
            import pyautogui

            pyautogui.scroll(clicks)
            direction = "up" if clicks > 0 else "down"
            return ToolResult(
                success=True,
                message=f"Scrolled {direction} {abs(clicks)} ticks.",
                data={"clicks": clicks},
            )
        except Exception as exc:
            return ToolResult(success=False, error=f"Scroll error: {exc}")
