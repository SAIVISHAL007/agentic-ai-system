"""API routes for the agentic system."""

import asyncio
import json
from queue import Empty, Queue
from threading import Event, Thread
from fastapi import APIRouter, HTTPException, Query, Request
from typing import Optional
from sse_starlette.sse import EventSourceResponse
from app.schemas.request_response import ExecuteRequest, ExecuteResponse, StepResult
from app.schemas.history import HistoryListResponse, HistoryDetailResponse, HistoryStatsResponse
from app.schemas.workflows import GitHubRepoInsightsRequest, GitHubRepoInsightsResponse
from app.agents.runner import AgentRunner
from app.memory.schemas import ExecutionContext
from app.storage.execution_history import get_history_store
from app.workflows.github_repo_insights import run_github_repo_insights
from app.core.config import settings
from app.core.logging import logger

router = APIRouter(prefix="/api", tags=["agents"])

# Lazy initialization of runner
_runner: AgentRunner | None = None


def get_runner() -> AgentRunner:
    """Get or create the agent runner (lazy initialization)."""
    global _runner
    if _runner is None:
        try:
            _runner = AgentRunner()
        except ValueError as e:
            if "API_KEY" in str(e):
                raise ValueError(
                    f"{str(e)}. "
                    "Please set your LLM API key as an environment variable."
                ) from e
            raise
    return _runner


@router.post("/execute", response_model=ExecuteResponse)
def execute_goal(request: ExecuteRequest, http_request: Request) -> ExecuteResponse:
    """
    Execute a high-level goal end-to-end.
    
    The system will:
    1. Plan the goal into concrete steps
    2. Execute steps sequentially using available tools
    3. Return complete execution record
    """
    try:
        logger.info(f"Received execution request for goal: {request.goal}")
        
        # Get runner (lazy initialization)
        runner = get_runner()
        run_context = _merge_request_context(request.context, http_request)
        
        # Run the agentic system
        execution_context = runner.run(
            goal=request.goal,
            context=run_context,
        )
        
        response = _build_execute_response(execution_context)

        logger.info(f"Execution completed: {execution_context.execution_id}")
        return response
    
    except ValueError as e:
        error_msg = f"Configuration error: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)
    
    except Exception as e:
        error_msg = f"Execution failed: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


@router.post("/execute/stream")
async def execute_goal_stream(request: ExecuteRequest, http_request: Request):
    """Execute goal and stream lifecycle events (start, completed, error).

    This endpoint is additive and does not change existing `/api/execute` behavior.
    """

    async def event_generator():
        event_queue: Queue[dict] = Queue()
        done = Event()
        run_context = _merge_request_context(request.context, http_request)

        def on_event(event: dict) -> None:
            event_queue.put(event)

        def run_agent() -> None:
            try:
                runner = get_runner()
                execution_context = runner.run(
                    goal=request.goal,
                    context=run_context,
                    event_callback=on_event,
                )
                response = _build_execute_response(execution_context)
                event_queue.put({
                    "type": "completed",
                    "payload": response.model_dump(),
                })
            except Exception as exc:
                event_queue.put({
                    "type": "error",
                    "detail": str(exc),
                })
            finally:
                done.set()

        Thread(target=run_agent, daemon=True).start()

        yield {
            "event": "started",
            "data": json.dumps({"goal": request.goal}),
        }

        while not done.is_set() or not event_queue.empty():
            try:
                event = event_queue.get_nowait()
            except Empty:
                await asyncio.sleep(0.05)
                continue

            event_type = event.get("type", "progress")
            if event_type == "completed":
                yield {
                    "event": "completed",
                    "data": json.dumps(event.get("payload", {})),
                }
            elif event_type == "error":
                yield {
                    "event": "error",
                    "data": json.dumps({"detail": event.get("detail", "Unknown stream error")}),
                }
            else:
                yield {
                    "event": "progress",
                    "data": json.dumps(event),
                }

    return EventSourceResponse(event_generator())


def _build_execute_response(execution_context: ExecutionContext) -> ExecuteResponse:
    """Convert ExecutionContext to API response model."""
    steps_result = [
        StepResult(
            step_number=step.step_number,
            description=step.description,
            tool_name=step.tool_name,
            success=step.success,
            input=step.input_data,
            output=step.output,
            error=step.error,
        )
        for step in execution_context.executed_steps
    ]

    return ExecuteResponse(
        execution_id=execution_context.execution_id,
        goal=execution_context.goal,
        status=execution_context.status,
        intent=execution_context.intent,
        decision_rationale=execution_context.decision_rationale,
        steps_completed=steps_result,
        final_result=execution_context.final_result,
        execution_summary=execution_context.execution_summary,
        error=execution_context.error,
        timestamp=execution_context.created_at.isoformat(),
    )


# ============================================================================
# HISTORY ENDPOINTS - Access execution history and statistics
# ============================================================================

@router.get("/history", response_model=HistoryListResponse)
def list_execution_history(
    limit: int = Query(50, ge=1, le=500, description="Max records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    intent: Optional[str] = Query(None, description="Filter by intent (tool_required, reasoning_only, mixed)"),
    status: Optional[str] = Query(None, description="Filter by status (completed, failed, partial)"),
) -> HistoryListResponse:
    """
    List execution history with optional filtering and pagination.
    
    Returns most recent executions first.
    
    Query parameters:
    - limit: Max records (1-500, default 50)
    - offset: Pagination offset (default 0)
    - intent: Filter by intent classification
    - status: Filter by execution status
    """
    try:
        logger.info(f"Listing execution history: limit={limit}, offset={offset}")
        
        history_store = get_history_store()
        executions = history_store.list_executions(
            limit=limit,
            offset=offset,
            intent_filter=intent,
            status_filter=status,
        )
        
        # Get total count (without pagination filters)
        all_executions = history_store.list_executions(limit=10000, offset=0)
        total_count = len(all_executions)
        
        return HistoryListResponse(
            executions=executions,
            total_count=total_count,
            offset=offset,
            limit=limit,
        )
    except Exception as e:
        error_msg = f"Failed to retrieve execution history: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


@router.get("/history/stats", response_model=HistoryStatsResponse)
def get_execution_statistics(
) -> HistoryStatsResponse:
    """
    Get overall execution statistics across all records.
    
    Returns counts by status, intent, tools used, and average performance.
    """
    try:
        logger.info("Retrieving execution statistics")
        
        history_store = get_history_store()
        stats = history_store.get_statistics()
        
        return HistoryStatsResponse(
            total_executions=stats.get("total_executions", 0),
            successful=stats.get("successful", 0),
            failed=stats.get("failed", 0),
            tools_used=stats.get("tools_used", []),
            avg_duration_ms=stats.get("avg_duration_ms", 0),
            intents=stats.get("intents", {}),
        )
    except Exception as e:
        error_msg = f"Failed to retrieve statistics: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


@router.get("/history/{execution_id}", response_model=HistoryDetailResponse)
def get_execution_detail(execution_id: str) -> HistoryDetailResponse:
    """
    Get complete details for a specific execution.
    
    Includes all steps, tool outputs, final result, and metadata.
    """
    try:
        logger.info(f"Retrieving execution detail: {execution_id}")
        
        history_store = get_history_store()
        execution = history_store.get_execution(execution_id)
        
        if not execution:
            raise HTTPException(
                status_code=404,
                detail=f"Execution not found: {execution_id}"
            )
        
        return HistoryDetailResponse(execution=execution)
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Failed to retrieve execution: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


@router.delete("/history/{execution_id}")
def delete_execution_history(execution_id: str) -> dict:
    """Delete a single execution history record."""
    try:
        logger.info("Deleting execution history: %s", execution_id)

        history_store = get_history_store()
        deleted = history_store.delete_execution(execution_id)

        if not deleted:
            raise HTTPException(
                status_code=404,
                detail=f"Execution not found: {execution_id}",
            )

        return {"success": True, "execution_id": execution_id}
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Failed to delete execution: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


@router.post("/workflows/github-repo-insights", response_model=GitHubRepoInsightsResponse)
def github_repo_insights_workflow(request: GitHubRepoInsightsRequest) -> GitHubRepoInsightsResponse:
    """Run concrete business workflow for repository intelligence."""
    try:
        result = run_github_repo_insights(request.owner, request.repo)
        if not result.get("success"):
            return GitHubRepoInsightsResponse(
                success=False,
                error=result.get("error") or "Workflow failed",
            )

        return GitHubRepoInsightsResponse(
            success=True,
            insights=result.get("insights"),
        )
    except Exception as exc:
        logger.error("GitHub insights workflow failed: %s", str(exc))
        return GitHubRepoInsightsResponse(
            success=False,
            error=str(exc),
        )


def _merge_request_context(
    context: Optional[dict],
    request: Request,
) -> dict:
    """Merge request context with tenant metadata."""
    merged = dict(context or {})
    tenant_id = request.headers.get("X-Tenant-ID") or settings.DEFAULT_TENANT_ID
    merged["_tenant_id"] = tenant_id
    return merged