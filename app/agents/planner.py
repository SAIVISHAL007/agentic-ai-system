"""Planner agent for breaking goals into executable steps."""

from typing import Any, Dict, List, Optional

from app.llm.groq_client import get_llm_client, BaseLLMClient
from app.tools.base import tool_registry
from app.schemas.request_response import ExecutionStep
from app.agents.validator import ToolInputValidator
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
        self.validator = ToolInputValidator(self.llm_client)
        logger.info(f"Planner initialized with LLM client")
    
    def plan(self, goal: str, context: Optional[Dict[str, Any]] = None) -> List[ExecutionStep]:
        """
        Generate an execution plan for the given goal.
        
        Args:
            goal: High-level goal statement
            context: Optional context/parameters for planning
        
        Returns:
            List of ExecutionStep objects in order
            
        Raises:
            ValueError: If plan violates intent requirements
        """
        context = context or {}
        
        # Determine intent classification
        intent = self.classify_intent(goal, context)
        logger.debug(f"Classified intent: {intent}")
        
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
        steps = self._validate_and_repair_steps(goal, context, steps)
        
        # CRITICAL: Enforce intent requirements
        self._enforce_intent_requirements(steps, intent, goal)
        
        logger.info(f"Generated plan with {len(steps)} steps for goal: {goal}")
        return steps

    def classify_intent(self, goal: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Classify goal intent as reasoning_only, tool_required, or mixed."""
        context = context or {}
        goal_text = goal.lower()
        reasoning_keywords = [
            "explain",
            "define",
            "what is",
            "why",
            "how",
            "summarize",
            "compare",
            "list",
        ]
        tool_keywords = [
            "current",
            "latest",
            "today",
            "price",
            "stock",
            "weather",
            "news",
            "real-time",
            "rate",
            "fetch",
            "lookup",
            "api",
            "http",
            "url",
        ]

        has_reasoning = any(keyword in goal_text for keyword in reasoning_keywords)
        has_tool = any(keyword in goal_text for keyword in tool_keywords)

        context_text = " ".join(str(value).lower() for value in context.values())
        if "http" in context_text or "api" in context_text or "key" in context_text:
            has_tool = True

        if has_tool and has_reasoning:
            return "mixed"
        if has_tool:
            return "tool_required"
        return "reasoning_only"
    
    def _build_planning_prompt(self, goal: str, context: Dict[str, Any]) -> str:
        """Build the prompt for the planner."""
        
        context_str = ""
        if context:
            context_str = f"\n\nAdditional Context:\n"
            for key, value in context.items():
                context_str += f"- {key}: {value}\n"
        
        # Build detailed tool descriptions with schemas
        tools_description = self._build_tools_description()
        
        prompt = f"""You are an AI planning agent. Your task is to break down a user goal into concrete, executable steps.

Available tools and their input schemas:
{tools_description}

**CRITICAL Tool Selection Decision Tree:**

1. Does the goal contain keywords like "fetch", "latest", "current", "repository", "search"?
   → YES: This is LIVE DATA - use 'http' tool with COMPLETE URL including all required query parameters
   → NO: Continue to step 2

2. Is the goal asking for CURRENT/LIVE/REAL-TIME data (e.g., stock prices, weather, news)?
   → YES: Use 'http' tool if you KNOW the public API endpoint
   → NO: Continue to step 3
   → UNSURE OF API: Use 'reasoning' + explicitly state the limitation

3. Is the goal requesting to fetch from a SPECIFIC, KNOWN, PUBLIC API?
   → YES: Use 'http' tool (e.g., https://api.coingecko.com/api/v3/simple/price)
   → NO: Continue to step 4

4. Is the goal a definition, explanation, code generation, summary, or conceptual question?
   → YES: Use 'reasoning' tool
   → NO: Continue to step 5

5. Does the goal require storing/retrieving intermediate state across steps?
   → YES: Use 'memory' tool (in combination with other steps)
   → NO: Use 'reasoning' tool as default

**CRITICAL HTTP Tool Rules (READ CAREFULLY):**
- GitHub Search API: MUST include ?q=<search-term> in the URL
  ✓ CORRECT: https://api.github.com/search/repositories?q=machine-learning&sort=stars
  ✗ WRONG: https://api.github.com/search/repositories (this will FAIL with 422 error!)
- NEVER split "figure out the URL" and "make the request" into separate steps
- Construct the COMPLETE URL with ALL required query parameters in ONE step
- If you don't know the exact API endpoint and its parameters, use 'reasoning' instead and explain the limitation

**Important Rules (ENFORCE STRICTLY):**
- NEVER use 'http' for unknown or unverified APIs
- NEVER guess at endpoint URLs or required parameters
- NEVER fabricate external data - if the API is unknown, use 'reasoning' with a clear explanation
- If a goal says "get current X" but no API is known → use 'reasoning' ONLY + explain that real-time data is not available
- 'reasoning' is the PRIMARY tool for all knowledge-based questions, NOT a fallback
- 'reasoning' includes: definitions, explanations, code generation, summaries, analysis, comparisons, historical context

**Step Description Format:**
Each step description MUST start with the step type and explain WHY:
- "Fetch [data] via API: [reason]" (for http tool)
- "Internal reasoning: [what to figure out]" (for reasoning tool)  
- "Store/retrieve in memory: [what data]" (for memory tool)

Examples:
  ✓ "Fetch Bitcoin price via CoinGecko API: to get current market data"
  ✓ "Internal reasoning: Explain the concept of REST APIs with examples"
  ✓ "Internal reasoning: Analyze the fetched data and summarize key insights"
  ✗ "Get Bitcoin price" (too vague, doesn't explain tool choice)

Goal: {goal}
{context_str}

Analyze the goal and create a plan. Return your response as a JSON array with this structure:
[
  {{
    "step_number": 1,
    "description": "Short, human-readable step name (e.g., Fetch Financial Data)",
    "tool_name": "lowercase name of tool to use (must be from available tools)",
    "input_data": {{"key": "value"}},
    "reasoning": "Why this step is necessary"
  }},
  ...
]

CRITICAL: For input_data, use the EXACT field names and types:
- For 'reasoning' tool: Include 'question' (the question to answer), and optionally 'context'
    Example: {{"question": "Explain the concept of an API"}}
    IMPORTANT: Use 'reasoning' only when no external data or actions are needed.
  
- For 'memory' tool: Include 'action' (either "store" or "retrieve"), 'key', and optionally 'value'
  Example: {{"action": "store", "key": "my_key", "value": "my_value"}}
  
- For 'http' tool: Include 'method' (GET, POST, DELETE, etc), 'url', headers (optional dict), body (optional dict), timeout (optional int)
  Example GET: {{"method": "GET", "url": "https://example.com"}}
  Example GET with query params: {{"method": "GET", "url": "https://api.github.com/search/repositories?q=machine-learning&sort=stars"}}
  Example POST: {{"method": "POST", "url": "https://example.com", "body": {{"key": "value"}}}}
  IMPORTANT: 
  - Never use empty strings for body - omit it or use null. Never use strings for timeout - use numbers.
  - For search/query APIs, include ALL required query parameters directly in the URL (e.g., GitHub search requires ?q=...)
  - DO NOT split "figuring out the URL" and "making the request" into separate steps - construct the COMPLETE URL in one step

Important:
1. Use only lowercase tool names from the list above
2. Each step should be specific and actionable
3. Order steps logically
4. Include reasoning for each step
5. For HTTP requests, construct the COMPLETE URL with all required query parameters in one step (don't use reasoning to figure out the URL first)
6. Return ONLY the JSON array, no other text
7. NEVER include empty strings "" for optional fields - omit them entirely or use null

Generate the plan now:"""
        
        return prompt
    
    def _build_tools_description(self) -> str:
        """Build detailed tool descriptions including their input schemas."""
        descriptions = []
        
        from app.tools.base import tool_registry as registry
        
        # Get all registered tools
        for tool_name in registry._tools.keys():
            tool = registry.get(tool_name)
            if not tool:
                continue
            
            descriptions.append(f"\n{tool_name}: {tool.description}")
            if tool.required_fields:
                descriptions.append(f"  Required fields: {', '.join(tool.required_fields)}")
            
            # Add schema information
            try:
                schema = tool.input_schema
                # Get fields from Pydantic model
                if hasattr(schema, 'model_fields'):
                    descriptions.append("  Input fields:")
                    for field_name, field_info in schema.model_fields.items():
                        required = field_name in tool.required_fields
                        desc = field_info.description or ""
                        required_label = "required" if required else "optional"
                        descriptions.append(f"    - {field_name} ({required_label}): {desc}")
            except Exception as e:
                logger.debug(f"Could not extract schema for {tool_name}: {e}")
        
        return "\n".join(descriptions)
    
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

    def _validate_and_repair_steps(
        self,
        goal: str,
        context: Optional[Dict[str, Any]],
        steps: List[ExecutionStep],
    ) -> List[ExecutionStep]:
        """Validate and repair step inputs against tool required fields."""
        for step in steps:
            tool_name = step.tool_name.lower()
            tool = tool_registry.get(tool_name)
            if not tool:
                logger.warning(f"Unknown tool '{step.tool_name}' in plan")
                continue

            input_data = step.input_data or {}
            repaired_data = self._repair_tool_input(goal, tool_name, input_data)
            step.input_data = repaired_data
            step.input_data = self.validator.validate_and_repair(
                step=step,
                goal=goal,
                context=context,
            )

        return steps

    def _repair_tool_input(self, goal: str, tool_name: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Attempt to repair missing required fields using the goal text."""
        repaired = dict(input_data or {})

        if tool_name == "reasoning":
            if not self._has_value(repaired.get("question")):
                repaired["question"] = goal

        if tool_name == "memory":
            if not self._has_value(repaired.get("action")):
                repaired["action"] = "retrieve" if "retrieve" in goal.lower() else "store"
            if not self._has_value(repaired.get("key")):
                repaired["key"] = self._infer_memory_key(goal)

        return repaired

    def _infer_memory_key(self, goal: str) -> str:
        """Infer a stable memory key from the goal text."""
        cleaned = "".join(char.lower() if char.isalnum() else "_" for char in goal)
        cleaned = "_".join(filter(None, cleaned.split("_")))
        return cleaned[:40] or "result"

    def _enforce_intent_requirements(self, steps: List[ExecutionStep], intent: str, goal: str) -> None:
        """
        CRITICAL: Enforce that plan matches intent requirements.
        
        If intent == "tool_required", plan MUST include at least one non-reasoning tool.
        Otherwise, raise an error immediately (FAIL-FAST).
        
        This prevents the system from generating reasoning-only answers for goals
        that require external data/actions.
        """
        if not steps:
            raise ValueError(f"Plan generated no steps for goal: {goal}")
        
        if intent == "tool_required":
            # Check if plan includes at least one executable (non-reasoning) tool
            tool_names = [step.tool_name.lower() for step in steps]
            non_reasoning_tools = [t for t in tool_names if t != "reasoning"]
            
            if not non_reasoning_tools:
                raise ValueError(
                    f"AGENTIC CONSTRAINT VIOLATION: Goal classified as 'tool_required' "
                    f"but plan only includes 'reasoning' tool. "
                    f"Goal: '{goal}'. "
                    f"Plan: {[s.tool_name for s in steps]}. "
                    f"This goal requires external tools (HTTP, memory, etc.) or should not be classified as 'tool_required'."
                )
            logger.info(f"Intent 'tool_required' enforced: plan includes {non_reasoning_tools}")
        
        elif intent == "reasoning_only":
            # Reasoning-only goals should not use external tools
            tool_names = [step.tool_name.lower() for step in steps]
            external_tools = [t for t in tool_names if t not in ("reasoning", "memory")]
            if external_tools:
                logger.warning(
                    f"Intent mismatch: goal classified as 'reasoning_only' "
                    f"but plan includes external tools: {external_tools}. "
                    f"This may indicate misclassification. Continuing anyway."
                )

    def _has_value(self, value: Any) -> bool:
        """Return True when a value is non-empty and usable."""
        if value is None:
            return False
        if isinstance(value, str):
            return bool(value.strip())
        if isinstance(value, (list, tuple, dict)):
            return len(value) > 0
        return True
