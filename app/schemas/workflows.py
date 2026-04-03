"""Schemas for workflow endpoints."""

from typing import Any, Dict, Optional
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
