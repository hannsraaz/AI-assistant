"""Screen Understanding and Vision Tools for Friday."""
from core.tools.registry import ToolRegistry
from core.tools.vision.screen_vision import (
    ScreenAnalyzeTool,
    ScreenCaptureTool,
    ScreenDescribeTool,
    ScreenFindElementTool,
    ScreenFindTextTool,
)


def register_vision_tools(registry: ToolRegistry) -> None:
    """Register all vision and screen understanding tools."""
    tools = [
        ScreenCaptureTool(),
        ScreenDescribeTool(),
        ScreenAnalyzeTool(),
        ScreenFindTextTool(),
        ScreenFindElementTool(),
    ]
    registry.register_many(tools)


__all__ = [
    "register_vision_tools",
    "ScreenCaptureTool",
    "ScreenDescribeTool",
    "ScreenAnalyzeTool",
    "ScreenFindTextTool",
    "ScreenFindElementTool",
]
