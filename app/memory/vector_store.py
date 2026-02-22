"""Memory storage - in-memory store for Phase 1."""

from typing import Dict, Optional
import uuid

from app.memory.schemas import ExecutionContext
from app.core.logging import logger


class MemoryStore:
    """
    In-memory store for execution contexts.
    
    In future phases, this interface can be replaced with:
    - vector databases (Chroma, Weaviate)
    - persistent storage (PostgreSQL + embeddings)
    - distributed caches (Redis)
    
    The interface stays the same; only implementation changes.
    """
    
    def __init__(self):
        self._contexts: Dict[str, ExecutionContext] = {}
    
    def create_execution_context(
        self,
        goal: str,
        user_context: Optional[Dict] = None,
    ) -> ExecutionContext:
        """Create a new execution context."""
        context = ExecutionContext(
            execution_id=str(uuid.uuid4()),
            goal=goal,
            user_context=user_context or {},
        )
        self._contexts[context.execution_id] = context
        logger.debug(f"Created execution context: {context.execution_id}")
        return context
    
    def get_context(self, execution_id: str) -> Optional[ExecutionContext]:
        """Retrieve an execution context."""
        return self._contexts.get(execution_id)
    
    def save_context(self, context: ExecutionContext) -> None:
        """Save/update an execution context."""
        self._contexts[context.execution_id] = context
        logger.debug(f"Saved execution context: {context.execution_id}")
    
    def list_contexts(self, limit: int = 10) -> list[ExecutionContext]:
        """List recent execution contexts."""
        # Return in reverse order (most recent first)
        return list(self._contexts.values())[-limit:][::-1]
    
    def clear(self) -> None:
        """Clear all contexts (for testing)."""
        self._contexts.clear()
        logger.debug("Memory store cleared")
    
    def __len__(self) -> int:
        return len(self._contexts)


# Global memory store instance
memory_store = MemoryStore()
