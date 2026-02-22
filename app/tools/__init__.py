"""Tools package - initialization and registry."""

from app.tools.base import BaseTool, ToolRegistry, tool_registry
from app.tools.http_tool import HTTPTool
from app.tools.memory_tool import MemoryTool

__all__ = [
    "BaseTool",
    "ToolRegistry",
    "tool_registry",
    "HTTPTool",
    "MemoryTool",
]


_initialized = False


def initialize_tools() -> ToolRegistry:
    """Initialize and register all available tools."""
    global _initialized
    
    if _initialized:
        return tool_registry
    
    # Register HTTP tool (if not already registered)
    if "http" not in tool_registry:
        tool_registry.register(HTTPTool())
    
    # Register Memory tool (if not already registered)
    if "memory" not in tool_registry:
        tool_registry.register(MemoryTool())
    
    _initialized = True
    return tool_registry
