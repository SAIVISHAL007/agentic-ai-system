"""Schemas for execution history storage."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ExecutionHistoryStep(BaseModel):
    """Simplified step record for history storage."""
    step_number: int
    tool_name: str
    description: str
    success: bool
    error: Optional[str] = None


class ExecutionHistoryRecord(BaseModel):
    """Complete execution record for persistent storage.
    
    This is saved to history - includes full details but excludes
    unnecessarily large raw API responses.
    """
    execution_id: str = Field(..., description="Unique execution ID")
    goal: str = Field(..., description="The goal that was executed")
    intent: Optional[str] = Field(None, description="Intent classification")
    status: str = Field(..., description="execution status: completed, failed, partial")
    steps: List[ExecutionHistoryStep] = Field(default_factory=list, description="Steps that were executed")
    tools_used: List[str] = Field(default_factory=list, description="List of tools used")
    final_result: Optional[Dict[str, Any]] = Field(None, description="Final result (structured)")
    error_summary: Optional[str] = Field(None, description="Error summary if execution failed")
    duration_ms: int = Field(default=0, description="Total execution time in milliseconds")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="When execution started")
    tool_failure_count: int = Field(default=0, description="Number of tool failures")
    reasoning_step_count: int = Field(default=0, description="Number of reasoning steps executed")
    
    class Config:
        json_schema_extra = {
            "example": {
                "execution_id": "exec_12345",
                "goal": "Fetch and explain TensorFlow repository",
                "intent": "tool_required",
                "status": "completed",
                "steps": [
                    {
                        "step_number": 1,
                        "tool_name": "http",
                        "description": "Fetch repo from GitHub",
                        "success": True,
                        "error": None
                    }
                ],
                "tools_used": ["http", "reasoning"],
                "final_result": {
                    "success": True,
                    "content": "TensorFlow is...",
                    "source": "reasoning",
                    "confidence": 0.95
                },
                "duration_ms": 2500,
                "timestamp": "2026-03-06T04:30:00.000000"
            }
        }


class ExecutionHistorySummary(BaseModel):
    """Lightweight summary for list view (no large payloads)."""
    execution_id: str = Field(..., description="Unique execution ID")
    goal: str = Field(..., description="The goal that was executed")
    intent: Optional[str] = Field(None, description="Intent classification")
    status: str = Field(..., description="execution status")
    timestamp: str = Field(..., description="When execution started")
    duration_ms: int = Field(default=0, description="Execution time in milliseconds")
    tools_used: List[str] = Field(default_factory=list, description="Tools that were used")
    success: bool = Field(..., description="Whether execution succeeded")
    
    class Config:
        json_schema_extra = {
            "example": {
                "execution_id": "exec_12345",
                "goal": "Fetch and explain TensorFlow repository",
                "intent": "tool_required",
                "status": "completed",
                "timestamp": "2026-03-06T04:30:00.000000",
                "duration_ms": 2500,
                "tools_used": ["http", "reasoning"],
                "success": True
            }
        }


class HistoryListResponse(BaseModel):
    """Response for listing execution history."""
    executions: List[ExecutionHistorySummary] = Field(..., description="List of execution summaries")
    total_count: int = Field(..., description="Total number of executions in history")
    offset: int = Field(default=0, description="Pagination offset")
    limit: int = Field(default=50, description="Pagination limit")


class HistoryDetailResponse(BaseModel):
    """Response for fetching individual execution detail."""
    execution: ExecutionHistoryRecord = Field(..., description="Complete execution record")


class HistoryStatsResponse(BaseModel):
    """Response for execution statistics."""
    total_executions: int = Field(..., description="Total number of execution records")
    successful: int = Field(..., description="Number of successful executions")
    failed: int = Field(..., description="Number of failed executions")
    tools_used: List[str] = Field(..., description="All tools used across executions")
    avg_duration_ms: int = Field(..., description="Average execution duration")
    intents: Dict[str, int] = Field(..., description="Count of executions by intent")
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_executions": 42,
                "successful": 38,
                "failed": 4,
                "tools_used": ["http", "reasoning", "memory"],
                "avg_duration_ms": 2100,
                "intents": {
                    "tool_required": 28,
                    "reasoning_only": 10,
                    "mixed": 4
                }
            }
        }
