"""
Tests for AGENTIC SEMANTICS - proving the system enforces hard failures
and never generates fallback prose for tool-required goals.

These tests are critical for validating that this is a TRUE agentic system,
not a chatbot with tools.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from app.agents.runner import AgentRunner
from app.agents.planner import PlannerAgent
from app.agents.executor import ExecutorAgent
from app.schemas.request_response import ExecutionStep, FinalResult
from app.memory.schemas import ExecutionContext, ExecutionStep as MemoryExecutionStep


class TestAgenticIntentEnforcement:
    """Test that "tool_required" intent is enforced at planning stage."""

    def test_tool_required_goal_with_only_reasoning_raises_error(self):
        """
        AGENTIC RULE: If intent == "tool_required", plan MUST include non-reasoning tools.
        If plan has ONLY reasoning steps, system should HARD FAIL immediately.
        """
        planner = PlannerAgent()
        goal = "Fetch latest Bitcoin price from API"
        context = {}
        
        # Simulate LLM returning a reasoning-only plan when tool is required
        steps = [
            ExecutionStep(
                step_number=1,
                description="Answer about Bitcoin price",
                tool_name="reasoning",  # WRONG: Should use HTTP tool
                input_data={"question": "What is the current Bitcoin price?"},
                reasoning="Using reasoning tool",
            )
        ]
        
        # This should raise an error
        with pytest.raises(ValueError) as exc_info:
            planner._enforce_intent_requirements(steps, "tool_required", goal)
        
        assert "AGENTIC CONSTRAINT VIOLATION" in str(exc_info.value)
        assert "tool_required" in str(exc_info.value)
        assert "only includes 'reasoning' tool" in str(exc_info.value)

    def test_tool_required_goal_with_http_tool_passes(self):
        """Tool-required goal with HTTP tool should pass validation."""
        planner = PlannerAgent()
        goal = "Fetch latest Bitcoin price from API"
        
        steps = [
            ExecutionStep(
                step_number=1,
                description="Fetch Bitcoin price from CoinGecko",
                tool_name="http",
                input_data={"url": "https://api.coingecko.com/api/v3/simple/price"},
                reasoning="Using HTTP tool for live data",
            )
        ]
        
        # Should not raise - HTTP tool is available
        planner._enforce_intent_requirements(steps, "tool_required", goal)

    def test_mixed_intent_allows_reasoning_plus_tools(self):
        """Mixed intent should allow both reasoning and tools."""
        planner = PlannerAgent()
        goal = "Fetch and analyze Bitcoin price trends"
        
        steps = [
            ExecutionStep(
                step_number=1,
                description="Fetch Bitcoin price",
                tool_name="http",
                input_data={"url": "https://api.coingecko.com/api/v3/simple/price"},
                reasoning="Using HTTP for live data",
            ),
            ExecutionStep(
                step_number=2,
                description="Analyze price trends",
                tool_name="reasoning",
                input_data={"question": "What trends do you see?"},
                reasoning="Using reasoning for analysis",
            ),
        ]
        
        # Should not raise
        planner._enforce_intent_requirements(steps, "mixed", goal)


class TestAgenticHardFailures:
    """Test that tool failures result in hard failures, not fallback prose."""

    def test_tool_failure_returns_structured_failure_not_prose(self):
        """
        AGENTIC RULE: Tool failure → structured failure (no prose explanation).
        
        Proof that system does NOT generate explanations like:
        "Unable to fetch live data: HTTP 422..."
        """
        runner = AgentRunner()
        
        # Create an execution context that has failed
        execution_context = ExecutionContext(
            execution_id="test_001",
            goal="Fetch GitHub repo",
            user_context={},
        )
        execution_context.status = "failed"
        execution_context.error = "HTTP 422: GitHub Search API requires 'q' parameter"
        execution_context.execution_summary = {"tools_used": ["http"], "tool_failures": 1}
        
        # Resolve final output
        runner._resolve_final_output(execution_context)
        
        # Assert: Success is False
        assert execution_context.final_result.success is False
        
        # Assert: Content is None (NO TEXT)
        assert execution_context.final_result.content is None
        
        # Assert: Source is "failed"
        assert execution_context.final_result.source == "failed"
        
        # Assert: Confidence is 0.0 (lowest possible)
        assert execution_context.final_result.confidence == 0.0
        
        # Assert: Error is structured (actual error message, not prose)
        assert execution_context.final_result.error is not None
        assert "HTTP 422" in execution_context.final_result.error

    def test_no_steps_executed_returns_structured_failure(self):
        """If no steps are executed, return structured failure."""
        runner = AgentRunner()
        
        execution_context = ExecutionContext(
            execution_id="test_002",
            goal="Some goal",
            user_context={},
        )
        execution_context.status = "completed"
        execution_context.executed_steps = []  # Empty
        execution_context.execution_summary = {}
        
        runner._resolve_final_output(execution_context)
        
        # Assert: Hard failure structure
        assert execution_context.final_result.success is False
        assert execution_context.final_result.content is None
        assert execution_context.final_result.source == "failed"
        assert execution_context.final_result.confidence == 0.0

    def test_successful_execution_returns_content(self):
        """When execution succeeds, return content with success=True."""
        runner = AgentRunner()
        
        execution_context = ExecutionContext(
            execution_id="test_003",
            goal="What is Python?",
            user_context={},
        )
        execution_context.status = "completed"
        
        # Add a successful reasoning step
        reasoning_step = MemoryExecutionStep(
            step_number=1,
            description="Answer question about Python",
            tool_name="reasoning",
            input_data={"question": "What is Python?"},
            output={"answer": "Python is a programming language..."},
            success=True,
            error=None,
        )
        execution_context.add_step(reasoning_step)
        execution_context.execution_summary = {"tools_used": ["reasoning"]}
        
        runner._resolve_final_output(execution_context)
        
        # Assert: Success structure
        assert execution_context.final_result.success is True
        assert execution_context.final_result.content is not None
        assert execution_context.final_result.source == "reasoning-only"
        assert execution_context.final_result.confidence == 0.75


class TestAgenticNoFallbackBehavior:
    """
    Test that the system does NOT generate fallback explanations.
    
    This is the core distinction between agentic systems and chatbots:
    - Chatbot: Always generates text response, even if action failed
    - Agent: Hard failure when action cannot be completed
    """

    def test_api_call_failure_no_fallback_explanation(self):
        """
        Proof test: HTTP API failure does NOT result in prose explanation.
        
        OLD BEHAVIOR (Chatbot):
        Goal: "Fetch GitHub repo"
        Tool: HTTP fails (422 error)
        Response: "Unable to fetch live data: HTTP 422 Validation Failed..."
        
        NEW BEHAVIOR (Agentic):
        Goal: "Fetch GitHub repo"
        Tool: HTTP fails (422 error)
        Response: { success: false, content: null, error: "HTTP 422..." }
        """
        runner = AgentRunner()
        
        # Simulate failed HTTP execution
        execution_context = ExecutionContext(
            execution_id="test_004",
            goal="Fetch latest GitHub repository",
            user_context={},
            intent="tool_required",
        )
        execution_context.status = "failed"
        execution_context.error = "HTTP 422: Missing required parameter 'q'"
        execution_context.execution_summary = {"tools_used": ["http"]}
        
        # Resolve (would previously generate prose)
        runner._resolve_final_output(execution_context)
        
        # Verify: NO PROSE GENERATION
        assert execution_context.final_result.content is None
        assert execution_context.final_result.success is False
        # Ensure no fallback patterns exist
        assert "Unable to fetch" not in (execution_context.final_result.content or "")
        assert "typically occurs when" not in (execution_context.final_result.content or "")

    def test_method_reason_about_tool_failure_is_removed(self):
        """
        Verify that the fallback prose generation method is removed.
        """
        runner = AgentRunner()
        
        # The method should not exist anymore
        assert not hasattr(runner, '_reason_about_tool_failure'), \
            "CRITICAL: _reason_about_tool_failure() method still exists! " \
            "This method generates fallback prose and violates agentic semantics."


class TestAgenticOutputContract:
    """Test that FinalResult enforces the agentic contract."""

    def test_final_result_success_field_is_boolean(self):
        """FinalResult.success must be a boolean."""
        result = FinalResult(
            success=True,
            content="Some result",
            source="http",
            confidence=0.95,
            execution_id="test_005",
        )
        assert isinstance(result.success, bool)

    def test_final_result_content_can_be_none(self):
        """FinalResult.content must be nullable for hard failures."""
        result = FinalResult(
            success=False,
            content=None,
            source="failed",
            confidence=0.0,
            error="Action failed",
            execution_id="test_006",
        )
        assert result.content is None
        assert result.success is False

    def test_final_result_error_field_exists(self):
        """FinalResult must have error field for structured failures."""
        result = FinalResult(
            success=False,
            content=None,
            source="failed",
            confidence=0.0,
            error="HTTP 422: Missing parameter",
            execution_id="test_007",
        )
        assert result.error == "HTTP 422: Missing parameter"

    def test_final_result_confidence_zero_for_failures(self):
        """Confidence should be 0.0 for hard failures."""
        result = FinalResult(
            success=False,
            content=None,
            source="failed",
            confidence=0.0,
            error="Tool failed",
            execution_id="test_008",
        )
        assert result.confidence == 0.0


class TestAgenticEndToEnd:
    """End-to-end tests proving agentic behavior."""

    def test_tool_required_classification_enforces_tools(self):
        """
        End-to-end: Tool-required intent forces planner to include tools.
        """
        planner = PlannerAgent()
        
        # Goals classified as "tool_required" should get that classification
        goal = "Fetch current Bitcoin price from market data API"
        intent = planner.classify_intent(goal)
        
        # Should be classified as tool_required
        assert intent == "tool_required"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
