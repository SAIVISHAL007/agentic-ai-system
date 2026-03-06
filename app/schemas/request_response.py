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
    description: str
    tool_name: str
    success: bool
    input: Any = Field(default=None, description="Input parameters sent to the tool")
    output: Any
    error: Optional[str] = None


class FinalResult(BaseModel):
    """Strictly-typed final output from execution.
    
    AGENTIC SEMANTICS:
    - success = true  : action was completed; content contains result
    - success = false : action could not be completed; content is null; error contains reason
    """
    success: bool = Field(
        ...,
        description="Whether the intended action completed successfully"
    )
    content: Optional[str] = Field(
        None,
        description="Result content (null if action failed or not applicable)"
    )
    source: str = Field(
        ...,
        description="Where content came from: 'reasoning', 'http', 'memory', or 'failed'"
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence level (0.0-1.0). 0.0 for hard failures."
    )
    error: Optional[str] = Field(
        None,
        description="Structured error message if action failed"
    )
    execution_id: str = Field(
        ...,
        description="Unique execution trace identifier"
    )


class ExecuteResponse(BaseModel):
    """Final response from end-to-end execution."""
    execution_id: str
    goal: str
    status: str  # completed, failed, partial
    intent: Optional[str] = None
    decision_rationale: Optional[str] = None  # Explanation of why reasoning vs tool was chosen
    steps_completed: List[StepResult]
    final_result: FinalResult = Field(
        ...,
        description="Structured final output with content, source, confidence, and execution_id"
    )
    execution_summary: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: str
