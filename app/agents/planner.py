"""Planner agent for breaking goals into executable steps."""

from typing import Any, Dict, List, Optional
import json

from app.llm.groq_client import get_llm_client, BaseLLMClient
from app.tools.base import tool_registry
from app.schemas.request_response import ExecutionStep
from app.core.logging import logger


class PlannerAgent:
    """
    Agent responsible for planning execution.
    
    Takes a high-level goal and breaks it into concrete,
    ordered steps that can be executed by the Executor Agent.
    """
    
    def __init__(self, llm_client: Optional[BaseLLMClient] = None):
        self.llm_client = llm_client or get_llm_client()
        self.available_tools = tool_registry.list_tools()
        logger.info(f"Planner initialized with LLM client")
    
    def plan(self, goal: str, context: Optional[Dict[str, Any]] = None) -> List[ExecutionStep]:
        """
        Generate an execution plan for the given goal.
        
        Args:
            goal: High-level goal statement
            context: Optional context/parameters for planning
        
        Returns:
            List of ExecutionStep objects in order
        """
        context = context or {}
        
        # Build prompt for the planner
        prompt = self._build_planning_prompt(goal, context)
        
        # Call LLM to generate plan
        messages = [
            {
                "role": "system",
                "content": "You are an AI planning agent. Break complex goals into concrete, ordered steps."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        logger.debug(f"Planning goal: {goal}")
        response = self.llm_client.call(messages, temperature=0.3)  # Lower temp for consistency
        plan_text = response.content
        
        # Parse LLM response into ExecutionStep objects
        steps = self._parse_plan(plan_text)
        
        logger.info(f"Generated plan with {len(steps)} steps for goal: {goal}")
        return steps
    
    def _build_planning_prompt(self, goal: str, context: Dict[str, Any]) -> str:
        """Build the prompt for the planner."""
        
        context_str = ""
        if context:
            context_str = f"\n\nAdditional Context:\n"
            for key, value in context.items():
                context_str += f"- {key}: {value}\n"
        
        tools_description = "\n".join(
            f"- {name}: {description}"
            for name, description in self.available_tools.items()
        )
        
        prompt = f"""You are an AI planning agent. Your task is to break down a user goal into concrete, executable steps.

Available tools:
{tools_description}

Goal: {goal}
{context_str}

Analyze the goal and create a plan. Return your response as a JSON array with this structure:
[
  {{
    "step_number": 1,
    "description": "Clear description of what this step does",
    "tool_name": "name of tool to use (must be from available tools)",
    "input_data": {{"key": "value"}},
    "reasoning": "Why this step is necessary"
  }},
  ...
]

Important:
1. Use only the available tools listed above
2. Each step should be specific and actionable
3. Order steps logically
4. Include reasoning for each step
5. Return ONLY the JSON array, no other text

Generate the plan now:"""
        
        return prompt
    
    def _parse_plan(self, plan_text: str) -> List[ExecutionStep]:
        """Parse LLM response into ExecutionStep objects."""
        try:
            # Try to parse JSON from response
            plan_data = self.llm_client.parse_json(plan_text)
            
            # Handle both list and dict responses
            if isinstance(plan_data, dict):
                plan_data = plan_data.get("steps", [])
            
            steps = []
            for i, step_dict in enumerate(plan_data, 1):
                step = ExecutionStep(
                    step_number=step_dict.get("step_number", i),
                    description=step_dict.get("description", ""),
                    tool_name=step_dict.get("tool_name", ""),
                    input_data=step_dict.get("input_data", {}),
                    reasoning=step_dict.get("reasoning", None),
                )
                steps.append(step)
            
            logger.debug(f"Parsed {len(steps)} steps from plan")
            return steps
        
        except Exception as e:
            logger.error(f"Failed to parse plan: {str(e)}")
            raise ValueError(f"Could not parse execution plan from LLM response: {str(e)}")
