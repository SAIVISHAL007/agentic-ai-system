"""Agent runner - orchestrates planning and execution."""

from typing import Any, Callable, Dict, Optional
import json
import time
from app.agents.planner import PlannerAgent
from app.agents.executor import ExecutorAgent
from app.memory.vector_store import memory_store
from app.memory.schemas import ExecutionContext
from app.schemas.request_response import FinalResult
from app.storage.execution_history import get_history_store
from app.schemas.history import ExecutionHistoryRecord, ExecutionHistoryStep
from app.core.config import settings
from app.core.logging import logger


class AgentRunner:
    """
    High-level orchestrator for the agentic system.
    
    Coordinates:
    1. Planning: Breaking goal into steps
    2. Execution: Running steps with tools
    3. Memory: Tracking progress and state
    """
    
    def __init__(self):
        self.planner = PlannerAgent()
        self.executor = ExecutorAgent()
        self.memory_store = memory_store
        logger.info("AgentRunner initialized")
    
    def run(
        self,
        goal: str,
        context: Optional[Dict[str, Any]] = None,
        event_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> ExecutionContext:
        """
        Run the agentic system end-to-end.
        
        Args:
            goal: High-level goal to achieve
            context: Optional context and parameters
        
        Returns:
            ExecutionContext with complete execution record
        """
        logger.info(f"Starting agent run for goal: {goal}")
        
        start_time = time.monotonic()

        # Create execution context
        execution_context = self.memory_store.create_execution_context(
            goal=goal,
            user_context=context or {}
        )
        logger.debug(f"Created execution context: {execution_context.execution_id}")

        # Intent classification (metadata only)
        execution_context.intent = self.planner.classify_intent(goal, context)
        execution_context.decision_rationale = self._get_decision_rationale(
            execution_context.intent, goal
        )


        try:
            # Phase 1: Planning
            self._emit_event(event_callback, {
                "type": "planning_started",
                "goal": goal,
            })
            logger.info("Phase 1: Planning")
            steps = self.planner.plan(goal, context)
            logger.info(f"Generated {len(steps)} execution steps")
            self._emit_event(event_callback, {
                "type": "plan_created",
                "step_count": len(steps),
                "steps": [
                    {
                        "step_number": step.step_number,
                        "description": step.description,
                        "tool_name": step.tool_name,
                    }
                    for step in steps
                ],
            })
            
            # Phase 2: Execution
            logger.info("Phase 2: Execution")
            execution_context = self.executor.execute(
                steps=steps,
                execution_context=execution_context,
                max_retries=settings.MAX_RETRIES,
                step_callback=event_callback,
            )
            
            duration_ms = int((time.monotonic() - start_time) * 1000)
            execution_context.execution_summary = self._build_execution_summary(
                execution_context,
                duration_ms,
            )
            self._resolve_final_output(execution_context)

            # Save to memory
            self.memory_store.save_context(execution_context)
            
            # Save to execution history
            self._save_execution_to_history(execution_context, duration_ms)
            logger.info(f"Execution completed with status: {execution_context.status}")
            self._emit_event(event_callback, {
                "type": "execution_completed",
                "execution_id": execution_context.execution_id,
                "status": execution_context.status,
            })
            
            return execution_context
        
        except Exception as e:
            error_msg = f"Agent run failed: {str(e)}"
            logger.error(error_msg)
            execution_context.fail(error_msg)
            duration_ms = int((time.monotonic() - start_time) * 1000)
            execution_context.execution_summary = self._build_execution_summary(
                execution_context,
                duration_ms,
            )
            self._resolve_final_output(execution_context)
            self.memory_store.save_context(execution_context)
            
            # Save to execution history even on failure
            self._save_execution_to_history(execution_context, duration_ms)
            self._emit_event(event_callback, {
                "type": "execution_failed",
                "execution_id": execution_context.execution_id,
                "status": execution_context.status,
                "error": execution_context.error,
            })
            return execution_context



    def _get_decision_rationale(self, intent: str, goal: str) -> str:
        """Explain why the system chose reasoning-only vs tool execution."""
        if intent == "reasoning_only":
            return "Goal is definitional/explanatory and does not require live data or external APIs."
        elif intent == "tool_required":
            return "Goal requires fetching live/real-time data from external sources."
        elif intent == "mixed":
            return "Goal requires both reasoning steps and external data retrieval."
        else:
            return "Unknown intent classification."

    def _build_execution_summary(
        self,
        execution_context: ExecutionContext,
        duration_ms: int,
    ) -> Dict[str, Any]:
        """Build execution summary metadata."""
        tools_used: list[str] = []
        tool_failures = 0
        reasoning_steps = 0

        for step in execution_context.executed_steps:
            if step.tool_name not in tools_used:
                tools_used.append(step.tool_name)
            if not step.success:
                tool_failures += 1
            if step.tool_name == "reasoning":
                reasoning_steps += 1

        return {
            "tools_used": tools_used,
            "tool_failures": tool_failures,
            "reasoning_steps": reasoning_steps,
            "duration_ms": duration_ms,
        }

    def _resolve_final_output(self, execution_context: ExecutionContext) -> None:
        """Resolve final output with STRICT AGENTIC SEMANTICS.
        
        AGENTIC RULE: If action fails, return structured failure (no prose).
        
        - success = true  : action completed; content has result
        - success = false : action failed; content = null; error has reason
        """
        steps = execution_context.executed_steps
        last_step = steps[-1] if steps else None
        tools_used = execution_context.execution_summary.get("tools_used", []) if execution_context.execution_summary else []


        # HARD FAILURE: Execution status is "failed"
        if execution_context.status == "failed":
            error_msg = execution_context.error or (last_step.error if last_step else "Unknown error")
            logger.warning(f"AGENTIC HARD FAILURE: {error_msg}")
            execution_context.final_result = FinalResult(
                success=False,
                content=None,  # NO TEXT GENERATION
                source="failed",
                confidence=0.0,
                error=error_msg,
                execution_id=execution_context.execution_id,
            )
            return

        # HARD FAILURE: No steps executed
        if not steps:
            error_msg = "No execution steps were generated or executed"
            logger.warning(f"AGENTIC HARD FAILURE: {error_msg}")
            execution_context.final_result = FinalResult(
                success=False,
                content=None,  # NO TEXT GENERATION
                source="failed",
                confidence=0.0,
                error=error_msg,
                execution_id=execution_context.execution_id,
            )
            return

        # SUCCESS: Extract output from best available step (not just last step).
        best_step = self._select_best_output_step(steps)
        content = self._extract_content(best_step)
        source = self._derive_source(tools_used)
        confidence = self._derive_confidence(source, execution_context.goal, content)

        execution_context.final_result = FinalResult(
            success=True,
            content=content,
            source=source,
            confidence=confidence,
            error=None,
            execution_id=execution_context.execution_id,
        )


    def _select_best_output_step(self, steps: list[Any]) -> Any:
        """Choose the most user-meaningful step output.

        Prefer reasoning/http steps over memory-store acknowledgements.
        """
        if not steps:
            return None

        for step in reversed(steps):
            if not step.success:
                continue
            if step.tool_name == "memory" and self._is_memory_ack(step.output):
                continue
            return step

        return steps[-1]

    def _extract_content(self, last_step: Any) -> str:
        """Extract a human-readable content string from the last step output."""
        if not last_step:
            return "No output available."

        output = last_step.output
        if output is None or output == "":
            return "Tool completed but returned no data."
        if isinstance(output, dict):
            if "answer" in output and output["answer"]:
                return str(output["answer"])
            if "message" in output and output["message"] and not self._is_memory_ack(output):
                return str(output["message"])
            if "body" in output:
                body = output.get("body")
                if body is None or body == "":
                    return "Tool completed but returned no data."
                if isinstance(body, (dict, list)):
                    return json.dumps(body, indent=2)
                return str(body)
            return json.dumps(output, indent=2)
        if isinstance(output, str):
            return output
        return json.dumps(output, indent=2)

    def _is_memory_ack(self, output: Any) -> bool:
        """Return True if output is a memory acknowledgement rather than user-facing data."""
        if not isinstance(output, dict):
            return False
        message = str(output.get("message", "")).lower()
        return message.startswith("stored value at key")

    def _derive_source(self, tools_used: list[str]) -> str:
        """Derive final output source label."""
        if tools_used == ["reasoning"]:
            return "reasoning-only"
        if tools_used == ["http"]:
            return "http"
        if "http" in tools_used:
            return "mixed"
        return "mixed"

    def _derive_confidence(self, source: str, goal: str, content: str = "") -> float:
        """Derive confidence score (0.0-1.0) based on source, goal type, and content."""
        if source == "fallback":
            return 0.6
        if source in {"http", "mixed"}:
            return 0.95
        if source == "timeout":
            return 0.5
        if source == "reasoning":
            # Higher confidence for deterministic queries
            deterministic_keywords = [
                "calculate",
                "sum",
                "add",
                "subtract",
                "multiply",
                "divide",
                "math",
                "code",
                "explain",
                "define",
            ]
            if any(keyword in goal.lower() for keyword in deterministic_keywords):
                return 0.9
            return 0.75
        if source == "reasoning-only":
            return 0.75
        return 0.7
    
    def _save_execution_to_history(
        self,
        execution_context: ExecutionContext,
        duration_ms: int,
    ) -> None:
        """Save execution record to persistent history storage.
        
        Args:
            execution_context: The execution context to save
            duration_ms: Total execution duration in milliseconds
        """
        try:
            # Convert execution steps to history steps (simplified)
            history_steps = []
            for step in execution_context.executed_steps:
                history_steps.append(
                    ExecutionHistoryStep(
                        step_number=step.step_number,
                        tool_name=step.tool_name,
                        description=step.description,
                        success=step.success,
                        error=step.error,
                    )
                )
            
            # Extract summary fields
            execution_summary = execution_context.execution_summary or {}
            tools_used = execution_summary.get("tools_used", [])
            tool_failure_count = execution_summary.get("tool_failures", 0)
            
            # Count reasoning steps
            reasoning_step_count = sum(
                1 for step in execution_context.executed_steps
                if step.tool_name == "reasoning"
            )
            
            # Build final result dict (structured)
            final_result = None
            if execution_context.final_result:
                final_result = {
                    "success": execution_context.final_result.success,
                    "source": execution_context.final_result.source,
                    "confidence": execution_context.final_result.confidence,
                    "execution_id": execution_context.final_result.execution_id,
                    # content and error excluded if None (no need to store)
                }
                if execution_context.final_result.content:
                    final_result["content"] = execution_context.final_result.content
                if execution_context.final_result.error:
                    final_result["error"] = execution_context.final_result.error
            
            # Create history record
            history_record = ExecutionHistoryRecord(
                execution_id=execution_context.execution_id,
                goal=execution_context.goal,
                intent=execution_context.intent,
                status=execution_context.status,
                steps=history_steps,
                tools_used=tools_used,
                final_result=final_result,
                error_summary=execution_context.error,
                duration_ms=duration_ms,
                timestamp=execution_context.created_at.isoformat(),
                tool_failure_count=tool_failure_count,
                reasoning_step_count=reasoning_step_count,
            )
            
            # Save to history store
            history_store = get_history_store()
            history_store.save_execution(history_record)
            logger.info(f"Saved execution to history: {execution_context.execution_id}")
        except Exception as e:
            # Don't fail the execution if history save fails
            logger.error(f"Failed to save execution to history: {str(e)}")

    def _emit_event(
        self,
        event_callback: Optional[Callable[[Dict[str, Any]], None]],
        event: Dict[str, Any],
    ) -> None:
        """Emit event to callback if provided."""
        if not event_callback:
            return
        try:
            event_callback(event)
        except Exception as exc:
            logger.debug("Event callback error: %s", str(exc))
