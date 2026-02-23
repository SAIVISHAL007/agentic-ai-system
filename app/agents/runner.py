"""Agent runner - orchestrates planning and execution."""

from typing import Any, Dict, Optional
import json
import time
from app.agents.planner import PlannerAgent
from app.agents.executor import ExecutorAgent
from app.memory.vector_store import memory_store
from app.memory.schemas import ExecutionContext
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
        
        try:
            # Phase 1: Planning
            logger.info("Phase 1: Planning")
            steps = self.planner.plan(goal, context)
            logger.info(f"Generated {len(steps)} execution steps")
            
            # Phase 2: Execution
            logger.info("Phase 2: Execution")
            execution_context = self.executor.execute(
                steps=steps,
                execution_context=execution_context,
                max_retries=settings.MAX_RETRIES,
            )
            
            duration_ms = int((time.monotonic() - start_time) * 1000)
            execution_context.execution_summary = self._build_execution_summary(
                execution_context,
                duration_ms,
            )
            self._resolve_final_output(execution_context)

            # Save to memory
            self.memory_store.save_context(execution_context)
            logger.info(f"Execution completed with status: {execution_context.status}")
            
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
            return execution_context

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
        """Ensure a consistent final output for all executions."""
        steps = execution_context.executed_steps
        last_step = steps[-1] if steps else None
        tools_used = execution_context.execution_summary.get("tools_used", []) if execution_context.execution_summary else []

        if execution_context.status == "failed" or any(not step.success for step in steps):
            error_msg = execution_context.error
            if not error_msg and last_step and last_step.error:
                error_msg = last_step.error
            base_message = (
                f"Tool execution failed. {error_msg}"
                if error_msg
                else "Tool execution failed. No additional error details were provided."
            )
            if "http" in tools_used:
                content = f"Unable to fetch live data via HTTP tool. {base_message}"
            else:
                content = base_message
            execution_context.final_result = {
                "content": content,
                "source": "tool-failure",
                "confidence": "low",
                "execution_id": execution_context.execution_id,
            }
            return

        if not steps:
            execution_context.final_result = {
                "content": "No steps were executed for this goal.",
                "source": "tool-failure",
                "confidence": "low",
                "execution_id": execution_context.execution_id,
            }
            return

        content = self._extract_content(last_step)
        source = self._derive_source(tools_used)
        confidence = self._derive_confidence(source, execution_context.goal)

        execution_context.final_result = {
            "content": content,
            "source": source,
            "confidence": confidence,
            "execution_id": execution_context.execution_id,
        }

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
            if "message" in output and output["message"]:
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

    def _derive_source(self, tools_used: list[str]) -> str:
        """Derive final output source label."""
        if tools_used == ["reasoning"]:
            return "reasoning-only"
        if tools_used == ["http"]:
            return "http"
        if "http" in tools_used:
            return "mixed"
        return "mixed"

    def _derive_confidence(self, source: str, goal: str) -> str:
        """Derive confidence label based on source and goal type."""
        if source == "tool-failure":
            return "low"
        if source in {"http", "mixed"}:
            return "high"

        deterministic_keywords = [
            "calculate",
            "sum",
            "add",
            "subtract",
            "multiply",
            "divide",
            "math",
            "code",
        ]
        if any(keyword in goal.lower() for keyword in deterministic_keywords):
            return "high"
        return "medium"
