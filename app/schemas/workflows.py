"""Schemas for workflow endpoints."""

from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field


class GitHubRepoInsightsRequest(BaseModel):
    """Request payload for GitHub repository insights workflow."""

    owner: str = Field(..., description="Repository owner/org")
    repo: str = Field(..., description="Repository name")


class GitHubRepoInsightsResponse(BaseModel):
    """Structured response for repository insights workflow."""

    success: bool
    source: str = Field(default="workflow")
    execution_type: str = Field(default="workflow/github-repo-insights")
    insights: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class SupportTicketTriageRequest(BaseModel):
    """Request payload for support ticket triage workflow."""

    ticket_id: str = Field(..., description="Ticket identifier (e.g., TKT-2024-001)")
    customer_id: str = Field(..., description="Customer identifier (e.g., CUST-001)")
    issue_description: str = Field(..., description="Description of the customer's issue")


class SupportTicketTriageResponse(BaseModel):
    """Structured response for support ticket triage workflow."""

    success: bool = True
    ticket_id: str
    customer_id: str
    execution_id: str
    status: str  # completed, failed, partial
    steps_completed: List[Dict[str, Any]] = Field(default_factory=list)
    triage_result: Optional[Dict[str, Any]] = None
    drafted_response: Optional[str] = None
    error: Optional[str] = None
