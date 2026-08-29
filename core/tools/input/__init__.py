"""Keyboard & Mouse input automation tools for Friday."""
from core.tools.input.input_ops import (
    KeyboardHotkeyTool,
    KeyboardPressTool,
    KeyboardTypeTool,
    MouseClickTool,
    MouseDoubleClickTool,
    MouseMoveTool,
    MouseRightClickTool,
    MouseScrollTool,
)
from core.tools.registry import ToolRegistry


def register_input_tools(registry: ToolRegistry) -> None:
    """Register all keyboard and mouse interaction tools."""
    tools = [
        KeyboardTypeTool(),
        KeyboardPressTool(),
        KeyboardHotkeyTool(),
        MouseMoveTool(),
        MouseClickTool(),
        MouseDoubleClickTool(),
        MouseRightClickTool(),
        MouseScrollTool(),
    ]
    registry.register_many(tools)


__all__ = [
    "register_input_tools",
    "KeyboardTypeTool",
    "KeyboardPressTool",
    "KeyboardHotkeyTool",
    "MouseMoveTool",
    "MouseClickTool",
    "MouseDoubleClickTool",
    "MouseRightClickTool",
    "MouseScrollTool",
]
