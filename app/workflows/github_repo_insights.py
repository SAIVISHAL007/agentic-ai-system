"""Concrete business workflow: GitHub repository insights."""

from __future__ import annotations

from typing import Any, Dict

from app.tools.http_tool import HTTPTool
from app.core.logging import logger


def run_github_repo_insights(owner: str, repo: str) -> Dict[str, Any]:
    """Fetch GitHub repository metadata and produce actionable metrics.

    This deterministic workflow demonstrates API orchestration + analysis
    as a concrete business-style use case.
    """
    http_tool = HTTPTool()
    url = f"https://api.github.com/repos/{owner}/{repo}"

    response = http_tool.execute(method="GET", url=url)
    if not response.success:
        return {
            "success": False,
            "error": response.error or "Failed to fetch repository metadata",
            "raw": response.result,
        }

    body = (response.result or {}).get("body", {})
    if not isinstance(body, dict):
        return {
            "success": False,
            "error": "Unexpected repository payload format",
            "raw": response.result,
        }

    stars = int(body.get("stargazers_count") or 0)
    forks = int(body.get("forks_count") or 0)
    open_issues = int(body.get("open_issues_count") or 0)
    watchers = int(body.get("subscribers_count") or 0)
    language = body.get("language") or "unknown"

    engagement_ratio = round(stars / max(forks, 1), 2)
    issue_pressure = round(open_issues / max(stars, 1), 4)

    health_score = 100
    if issue_pressure > 0.01:
        health_score -= 20
    if engagement_ratio < 1.5:
        health_score -= 20
    if stars < 1000:
        health_score -= 10
    health_score = max(0, health_score)

    insights = {
        "repository": f"{owner}/{repo}",
        "description": body.get("description"),
        "html_url": body.get("html_url"),
        "primary_language": language,
        "stars": stars,
        "forks": forks,
        "watchers": watchers,
        "open_issues": open_issues,
        "engagement_ratio_stars_to_forks": engagement_ratio,
        "issue_pressure_ratio": issue_pressure,
        "health_score": health_score,
        "summary": (
            f"{owner}/{repo} shows {'strong' if health_score >= 70 else 'moderate'} project health "
            f"with {stars} stars, {forks} forks, and language {language}."
        ),
    }

    logger.info("Generated GitHub insights workflow for %s/%s", owner, repo)
    return {
        "success": True,
        "insights": insights,
    }
