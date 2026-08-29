"""Memory Subsystem for Friday."""
from core.memory.memory_manager import (
    MemoryForgetTool,
    MemoryListTool,
    MemoryManager,
    MemoryRecallTool,
    MemoryRememberTool,
)
from core.tools.registry import ToolRegistry


def register_memory_tools(registry: ToolRegistry, memory_manager: MemoryManager | None = None) -> MemoryManager:
    """Register all memory tools."""
    mm = memory_manager or MemoryManager()
    tools = [
        MemoryRememberTool(mm),
        MemoryRecallTool(mm),
        MemoryForgetTool(mm),
        MemoryListTool(mm),
    ]
    registry.register_many(tools)
    return mm


__all__ = [
    "MemoryManager",
    "register_memory_tools",
    "MemoryRememberTool",
    "MemoryRecallTool",
    "MemoryForgetTool",
    "MemoryListTool",
]
