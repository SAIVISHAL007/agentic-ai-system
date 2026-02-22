"""Memory tool for storing and retrieving execution context."""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from app.tools.base import BaseTool, ToolOutput
from app.core.logging import logger


class MemoryToolInput(BaseModel):
    """Input schema for memory tool."""
    action: str = Field(..., description="Action: 'store' or 'retrieve'")
    key: str = Field(..., description="Key to store/retrieve value")
    value: Optional[Any] = Field(default=None, description="Value to store (for 'store' action)")


class MemoryTool(BaseTool):
    """
    Tool for storing and retrieving intermediate execution state.
    
    Use this tool to:
    - Store intermediate results between steps
    - Retrieve data from earlier steps
    - Build context from previous computations
    """
    
    # Shared in-memory store (persists during execution)
    _store: Dict[str, Any] = {}
    
    @property
    def name(self) -> str:
        return "memory"
    
    @property
    def description(self) -> str:
        return "Store and retrieve intermediate execution state"
    
    @property
    def input_schema(self) -> type[BaseModel]:
        return MemoryToolInput
    
    def execute(self, **kwargs) -> ToolOutput:
        """Execute memory operation."""
        try:
            input_data = MemoryToolInput(**kwargs)
            action = input_data.action.lower()
            
            if action == "store":
                self._store[input_data.key] = input_data.value
                logger.debug(f"Memory: stored '{input_data.key}'")
                return ToolOutput(
                    success=True,
                    result={"message": f"Stored value at key '{input_data.key}'"}
                )
            
            elif action == "retrieve":
                if input_data.key in self._store:
                    value = self._store[input_data.key]
                    logger.debug(f"Memory: retrieved '{input_data.key}'")
                    return ToolOutput(
                        success=True,
                        result={"key": input_data.key, "value": value}
                    )
                else:
                    error_msg = f"Key '{input_data.key}' not found in memory"
                    logger.warning(error_msg)
                    return ToolOutput(success=False, result=None, error=error_msg)
            
            else:
                error_msg = f"Unknown action: {action}. Use 'store' or 'retrieve'."
                logger.warning(error_msg)
                return ToolOutput(success=False, result=None, error=error_msg)
        
        except Exception as e:
            error_msg = f"Memory operation failed: {str(e)}"
            logger.error(error_msg)
            return ToolOutput(success=False, result=None, error=error_msg)
    
    @classmethod
    def clear(cls) -> None:
        """Clear all stored memory (useful for testing)."""
        cls._store.clear()
        logger.debug("Memory cleared")
