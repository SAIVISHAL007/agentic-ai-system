"""Pydantic models for API requests and responses."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ExecutionStep(BaseModel):
    """Represents a planned execution step."""
    step_number: int
    description: str
    tool_name: str
    input_data: Dict[str, Any] = Field(default_factory=dict)
    reasoning: Optional[str] = None


class PlanRequest(BaseModel):
    """Request to plan a goal into steps."""
    goal: str = Field(..., description="High-level goal to achieve")
    context: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Optional context for planning"
    )


class PlanResponse(BaseModel):
    """Response from planner with execution steps."""
    plan_id: str
    goal: str
    steps: List[ExecutionStep]
    reasoning: Optional[str] = None
    timestamp: str


class ExecuteRequest(BaseModel):
    """Request to execute a goal end-to-end."""
    goal: str = Field(..., description="High-level goal to achieve")
    context: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Optional context and parameters"
    )


class StepResult(BaseModel):
    """Result of a single execution step."""
    step_number: int
    tool_name: str
    success: bool
    output: Any
    error: Optional[str] = None


class ExecuteResponse(BaseModel):
    """Final response from end-to-end execution."""
    execution_id: str
    goal: str
    status: str  # completed, failed, partial
    steps_completed: List[StepResult]
    final_result: Any
    error: Optional[str] = None
    timestamp: str
