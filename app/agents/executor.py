"""Executor agent for executing planned steps."""

from typing import Any, Callable, Dict, List, Optional
from pydantic import ValidationError
from app.schemas.request_response import ExecutionStep
from app.tools.base import tool_registry
from app.memory.schemas import ExecutionStep as MemoryExecutionStep, ExecutionContext
from app.core.logging import logger


class ExecutorAgent:
    """
    Agent responsible for executing planned steps.
    
    Takes a list of ExecutionStep objects and executes them sequentially,
    managing tool invocations, error handling, and state tracking.
    """
    
    def __init__(self):
        self.tool_registry = tool_registry
        logger.info("Executor initialized")
    
    def execute(
        self,
        steps: List[ExecutionStep],
        execution_context: ExecutionContext,
        max_retries: int = 3,
        step_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> ExecutionContext:
        """
        Execute a list of planned steps.
        
        Args:
            steps: List of ExecutionStep objects to execute
            execution_context: ExecutionContext to track progress
            max_retries: Max retries for failed steps
        
        Returns:
            Updated ExecutionContext with results
        """
        logger.info(f"Starting execution of {len(steps)} steps")
        
        for step in steps:
            self._emit_step_event(step_callback, {
                "type": "step_started",
                "step_number": step.step_number,
                "description": step.description,
                "tool_name": step.tool_name.lower(),
            })
            success = False
            retry_count = 0
            last_error = None
            max_attempts_for_tool = self._get_max_attempts(step.tool_name)
            
            while not success and retry_count < max_attempts_for_tool:
                try:
                    logger.debug(f"Executing step {step.step_number}: {step.description}")
                    
                    # Get the tool (case-insensitive lookup)
                    tool_name = step.tool_name.lower()
                    tool = self.tool_registry.get(tool_name)
                    if not tool:
                        raise ValueError(f"Tool '{step.tool_name}' not found in registry")

                    try:
                        tool.input_schema.model_validate(step.input_data or {})
                    except ValidationError as exc:
                        error_msg = f"Invalid tool input for '{tool_name}': {exc}"
                        logger.error(error_msg)
                        execution_context.fail(error_msg)
                        return execution_context
                    
                    # Resolve memory variables before tool execution
                    resolved_input = self._resolve_memory_variables(
                        step.input_data or {},
                        execution_context,
                        tool_name,
                    )
                    
                    # GROUNDING: If this is a reasoning step, enrich context with previous tool outputs
                    if tool_name == "reasoning":
                        resolved_input = self._enrich_reasoning_context(
                            resolved_input,
                            execution_context,
                            step.step_number
                        )
                    
                    logger.debug(f"Resolved input for {tool_name}: {resolved_input}")
                    
                    # Execute the tool
                    result = tool.execute(**resolved_input)
                    
                    # Record the step execution
                    memory_step = MemoryExecutionStep(
                        step_number=step.step_number,
                        description=step.description,
                        tool_name=tool_name,
                        input_data=resolved_input,  # Use resolved input for audit trail
                        output=result.result,
                        success=result.success,
                        error=result.error,
                    )
                    execution_context.add_step(memory_step)
                    
                    # Store intermediate output
                    execution_context.set_output(
                        step.step_number,
                        result.result,
                        key=tool_name
                    )
                    
                    if result.success:
                        logger.info(f"Step {step.step_number} succeeded")
                        self._emit_step_event(step_callback, {
                            "type": "step_completed",
                            "step_number": step.step_number,
                            "description": step.description,
                            "tool_name": tool_name,
                            "success": True,
                        })
                        success = True
                    else:
                        last_error = result.error or "Tool returned no error details"
                        logger.warning(f"Step {step.step_number} failed: {result.error}")
                        self._emit_step_event(step_callback, {
                            "type": "step_retry",
                            "step_number": step.step_number,
                            "description": step.description,
                            "tool_name": tool_name,
                            "retry_count": retry_count + 1,
                            "error": last_error,
                        })
                        retry_count += 1
                
                except Exception as e:
                    last_error = str(e)
                    logger.error(f"Step {step.step_number} error: {last_error}")
                    retry_count += 1
            
            if not success:
                error_details = last_error or "No error details were provided"
                error_msg = f"Step {step.step_number} ({step.tool_name}): {error_details}"
                logger.error(error_msg)
                memory_step = MemoryExecutionStep(
                    step_number=step.step_number,
                    description=step.description,
                    tool_name=step.tool_name,
                    input_data=step.input_data,
                    output=None,
                    success=False,
                    error=error_details,
                )
                execution_context.add_step(memory_step)
                execution_context.fail(f"Tool execution failed: {error_msg}")
                self._emit_step_event(step_callback, {
                    "type": "step_completed",
                    "step_number": step.step_number,
                    "description": step.description,
                    "tool_name": step.tool_name.lower(),
                    "success": False,
                    "error": error_details,
                })
                return execution_context  # Stop immediately on tool failure
        
        # All steps completed successfully
        logger.info("All steps executed successfully")
        
        # Extract final result from last step
        last_step = execution_context.executed_steps[-1] if execution_context.executed_steps else None
        if last_step and last_step.tool_name == "reasoning" and last_step.success:
            answer_content = None
            if isinstance(last_step.output, dict):
                answer_content = last_step.output.get("answer")
            final_result = {
                "content": answer_content or last_step.output,
                "source": "reasoning-only",
                "note": "No external tools used",
            }
            execution_context.complete(final_result)
        else:
            last_output = execution_context.intermediate_outputs.get(
                f"step_{steps[-1].step_number}", None
            )
            execution_context.complete(last_output)
        
        return execution_context

    def _emit_step_event(
        self,
        step_callback: Optional[Callable[[Dict[str, Any]], None]],
        event: Dict[str, Any],
    ) -> None:
        """Emit step-level event to callback if provided."""
        if not step_callback:
            return
        try:
            step_callback(event)
        except Exception as exc:
            logger.debug("Step callback error: %s", str(exc))
    
    def _get_max_attempts(self, tool_name: str) -> int:
        """Get max retry attempts per tool type.
        
        Limit HTTP to 1 attempt (no retries to avoid loops).
        Limit other tools to 2 attempts.
        """
        if tool_name.lower() == "http":
            return 1  # No retries for HTTP; fail fast and fallback to reasoning
        return 2
    
    def _resolve_memory_variables(
        self,
        input_data: Dict[str, Any],
        execution_context: ExecutionContext,
        tool_name: str,
    ) -> Dict[str, Any]:
        """Resolve memory placeholders like {key} in input data.
        
        Supports both:
        - Full placeholder: value = "{api_key}"
        - Embedded placeholder: value = "{endpoint}/path/to/resource"
        """
        import re
        
        resolved = dict(input_data or {})
        placeholder_pattern = re.compile(r'\{([^}]+)\}')
        
        def resolve_string(text: str) -> str:
            """Replace all {placeholder} patterns in a string."""
            if not isinstance(text, str):
                return text
            
            def replacer(match):
                key = match.group(1)
                value = execution_context.intermediate_outputs.get(key)
                if value is not None:
                    logger.debug(f"Resolved placeholder '{{{key}}}' to '{value}'")
                    return str(value)
                else:
                    logger.warning(f"Memory key '{key}' not found; keeping placeholder")
                    return match.group(0)  # Keep original placeholder
            
            return placeholder_pattern.sub(replacer, text)
        
        # Resolve placeholders in all string values
        for key, value in resolved.items():
            if isinstance(value, str):
                resolved[key] = resolve_string(value)
            elif isinstance(value, dict):
                # Handle nested dictionaries (e.g., headers)
                for nested_key, nested_value in value.items():
                    if isinstance(nested_value, str):
                        resolved[key][nested_key] = resolve_string(nested_value)
        
        # AFTER resolution, validate HTTP URLs
        if tool_name.lower() == "http":
            url = resolved.get("url")
            if url and isinstance(url, str):
                # Check if there are still unresolved placeholders
                if "{" in url or "}" in url:
                    raise ValueError(f"URL contains unresolved placeholder: {url}")
                if not url.startswith(("http://", "https://")):
                    raise ValueError(f"Invalid URL after resolution: {url} - must start with http:// or https://")
                logger.debug(f"Validated HTTP URL: {url[:80]}...")
        
        return resolved
    
    def _format_tool_error(self, error: str) -> str:
        """Format tool error message."""
        return f"Tool execution error: {error}"
    
    def _enrich_reasoning_context(
        self,
        reasoning_input: Dict[str, Any],
        execution_context: ExecutionContext,
        current_step_number: int,
    ) -> Dict[str, Any]:
        """Enrich reasoning input with structured data from previous tool outputs.
        
        This grounds reasoning steps in actual fetched data instead of generic explanations.
        
        Args:
            reasoning_input: Original reasoning tool input
            execution_context: Current execution context with previous step outputs
            current_step_number: Current step number
        
        Returns:
            Enriched reasoning input with structured context
        """
        # Find the most recent non-reasoning step
        previous_steps = [s for s in execution_context.executed_steps if s.step_number < current_step_number]
        if not previous_steps:
            return reasoning_input
        
        # Get the last successful tool step (HTTP, memory, etc.)
        last_tool_step = None
        for step in reversed(previous_steps):
            if step.success and step.tool_name != "reasoning":
                last_tool_step = step
                break
        
        if not last_tool_step or not last_tool_step.output:
            return reasoning_input
        
        logger.info(f"Grounding reasoning step with data from {last_tool_step.tool_name} output")
        
        # Extract structured context from previous tool output
        structured_context = self._extract_structured_context(last_tool_step.output, last_tool_step.tool_name)
        
        if structured_context:
            # Replace or enrich the context field
            reasoning_input["context"] = structured_context
            logger.debug(f"Enriched reasoning context: {str(structured_context)[:200]}...")
        
        return reasoning_input
    
    def _extract_structured_context(self, tool_output: Any, tool_name: str) -> Any:
        """Extract structured context from tool output.
        
        Args:
            tool_output: Output from a tool execution
            tool_name: Name of the tool that produced the output
        
        Returns:
            Structured context suitable for reasoning, or None
        """
        if not tool_output:
            return None
        
        # Handle HTTP tool outputs (especially GitHub API)
        if tool_name == "http":
            return self._extract_http_context(tool_output)
        
        # Handle memory tool outputs
        if tool_name == "memory":
            if isinstance(tool_output, dict) and "value" in tool_output:
                return tool_output["value"]
            return tool_output
        
        # Default: return output as-is if it's structured
        if isinstance(tool_output, (dict, list)):
            return tool_output
        
        return None
    
    def _extract_http_context(self, http_output: Any) -> Any:
        """Extract structured context from HTTP tool output.
        
        Handles common API response patterns, especially GitHub API.
        
        Args:
            http_output: Output from HTTP tool
        
        Returns:
            Structured context or None
        """
        if not isinstance(http_output, dict):
            return http_output
        
        # Check for GitHub API search results
        if "items" in http_output and isinstance(http_output["items"], list):
            items = http_output["items"]
            if items:
                # Select first item and extract key metadata
                first_item = items[0]
                
                # Extract GitHub repository metadata
                if "full_name" in first_item or "name" in first_item:
                    return {
                        "name": first_item.get("full_name") or first_item.get("name"),
                        "description": first_item.get("description"),
                        "stars": first_item.get("stargazers_count"),
                        "forks": first_item.get("forks_count"),
                        "language": first_item.get("language"),
                        "url": first_item.get("html_url"),
                        "topics": first_item.get("topics", []),
                        "created_at": first_item.get("created_at"),
                        "updated_at": first_item.get("updated_at"),
                    }
                
                # Generic first item extraction
                return first_item
        
        # Check for "body" wrapper (common HTTP response pattern)
        if "body" in http_output:
            body = http_output["body"]
            if isinstance(body, dict) and "items" in body:
                return self._extract_http_context(body)
            return body
        
        # Return as-is if already structured
        return http_output
