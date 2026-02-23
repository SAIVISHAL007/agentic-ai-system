"""Base tool interface for agentic system."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel


class ToolInput(BaseModel):
    """Base input schema for tools - override in subclasses."""
    pass


class ToolOutput(BaseModel):
    """Output from tool execution."""
    success: bool
    result: Any
    error: Optional[str] = None


class BaseTool(ABC):
    """
    Abstract base class for all tools.
    
    Tools are modular, reusable components that agents can invoke to:
    - Call external APIs
    - Execute code
    - Store/retrieve data
    - Perform computations
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the tool (used by agents to call it)."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Clear description of what the tool does and when to use it."""
        pass
    
    @property
    def input_schema(self) -> type[BaseModel]:
        """
        Pydantic model defining the input schema for this tool.
        Agents will use this to structure input before calling execute().
        """
        return ToolInput

    @property
    def required_fields(self) -> list[str]:
        """Return minimal required fields for this tool's input."""
        required: list[str] = []
        schema = self.input_schema
        if hasattr(schema, "model_fields"):
            for field_name, field_info in schema.model_fields.items():
                is_required = False
                if hasattr(field_info, "is_required"):
                    is_required = field_info.is_required()
                if is_required:
                    required.append(field_name)
        return required
    
    @abstractmethod
    def execute(self, **kwargs) -> ToolOutput:
        """
        Execute the tool with given arguments.
        
        Args match the fields in input_schema.
        Should always return ToolOutput with success flag.
        """
        pass
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name})"


class ToolRegistry:
    """Registry to manage available tools for the agentic system."""
    
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
    
    def register(self, tool: BaseTool) -> None:
        """Register a tool."""
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' already registered")
        self._tools[tool.name] = tool
    
    def get(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name."""
        return self._tools.get(name)
    
    def list_tools(self) -> Dict[str, str]:
        """Return dict of {tool_name: description}."""
        return {name: tool.description for name, tool in self._tools.items()}
    
    def __contains__(self, name: str) -> bool:
        """Check if tool is registered."""
        return name in self._tools
    
    def __repr__(self) -> str:
        return f"ToolRegistry({len(self._tools)} tools)"


# Global tool registry
tool_registry = ToolRegistry()
