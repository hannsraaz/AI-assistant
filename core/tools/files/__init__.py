"""File System Agent tools for Friday."""
from core.tools.files.file_ops import (
    FilesCopyTool,
    FilesCreateTool,
    FilesDeleteTool,
    FilesExistsTool,
    FilesListTool,
    FilesMoveTool,
    FilesOpenTool,
    FilesReadTool,
    FilesRenameTool,
    FilesSearchTool,
)
from core.tools.base import BaseTool
from core.tools.registry import ToolRegistry


def register_file_tools(registry: ToolRegistry) -> None:
    """Register all File System Agent tools."""
    tools: list[BaseTool] = [
        FilesSearchTool(),
        FilesListTool(),
        FilesOpenTool(),
        FilesReadTool(),
        FilesCreateTool(),
        FilesCopyTool(),
        FilesMoveTool(),
        FilesRenameTool(),
        FilesDeleteTool(),
        FilesExistsTool(),
    ]
    registry.register_many(tools)


__all__ = [
    "register_file_tools",
    "FilesSearchTool",
    "FilesListTool",
    "FilesOpenTool",
    "FilesReadTool",
    "FilesCreateTool",
    "FilesCopyTool",
    "FilesMoveTool",
    "FilesRenameTool",
    "FilesDeleteTool",
    "FilesExistsTool",
]
