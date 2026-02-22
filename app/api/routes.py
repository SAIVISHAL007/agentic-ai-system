"""API routes for the agentic system."""

from fastapi import APIRouter, HTTPException
from app.schemas.request_response import ExecuteRequest, ExecuteResponse, StepResult
from app.agents.runner import AgentRunner
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
def execute_goal(request: ExecuteRequest) -> ExecuteResponse:
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
        
        # Run the agentic system
        execution_context = runner.run(
            goal=request.goal,
            context=request.context,
        )
        
        # Convert execution context to response
        steps_result = [
            StepResult(
                step_number=step.step_number,
                tool_name=step.tool_name,
                success=step.success,
                output=step.output,
                error=step.error,
            )
            for step in execution_context.executed_steps
        ]
        
        response = ExecuteResponse(
            execution_id=execution_context.execution_id,
            goal=execution_context.goal,
            status=execution_context.status,
            steps_completed=steps_result,
            final_result=execution_context.final_result,
            error=execution_context.error,
            timestamp=execution_context.created_at.isoformat(),
        )
        
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