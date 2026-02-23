"""Memory schemas for execution tracking."""

from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class ExecutionStep(BaseModel):
    """Record of a single executed step."""
    step_number: int
    description: str
    tool_name: str
    input_data: Dict[str, Any]
    output: Any
    success: bool
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ExecutionContext(BaseModel):
    """Complete execution context for a single goal."""
    execution_id: str
    goal: str
    user_context: Dict[str, Any] = Field(default_factory=dict)
    intent: Optional[str] = None  # reasoning_only, tool_required, mixed
    executed_steps: List[ExecutionStep] = Field(default_factory=list)
    intermediate_outputs: Dict[str, Any] = Field(default_factory=dict)
    final_result: Optional[Any] = None
    execution_summary: Optional[Dict[str, Any]] = None
    status: str = "running"  # running, completed, failed
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    
    def add_step(self, step: ExecutionStep) -> None:
        """Add a step to the execution record."""
        self.executed_steps.append(step)
    
    def set_output(self, step_number: int, output: Any, key: Optional[str] = None) -> None:
        """Store output from a step."""
        if key:
            self.intermediate_outputs[key] = output
        else:
            self.intermediate_outputs[f"step_{step_number}"] = output
    
    def complete(self, final_result: Any) -> None:
        """Mark execution as completed."""
        self.status = "completed"
        self.final_result = final_result
        self.completed_at = datetime.utcnow()
    
    def fail(self, error: str) -> None:
        """Mark execution as failed."""
        self.status = "failed"
        self.error = error
        self.completed_at = datetime.utcnow()
