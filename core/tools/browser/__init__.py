"""Browser Agent tools for Friday."""
from core.tools.browser.browser_ops import (
    BrowserClickTool,
    BrowserDownloadTool,
    BrowserOpenTool,
    BrowserReadTool,
    BrowserSearchTool,
    BrowserTypeTool,
)
from core.tools.registry import ToolRegistry


def register_browser_tools(registry: ToolRegistry) -> None:
    """Register all Browser Agent tools."""
    tools = [
        BrowserOpenTool(),
        BrowserSearchTool(),
        BrowserReadTool(),
        BrowserDownloadTool(),
        BrowserClickTool(),
        BrowserTypeTool(),
    ]
    registry.register_many(tools)


__all__ = [
    "register_browser_tools",
    "BrowserOpenTool",
    "BrowserSearchTool",
    "BrowserReadTool",
    "BrowserDownloadTool",
    "BrowserClickTool",
    "BrowserTypeTool",
]
