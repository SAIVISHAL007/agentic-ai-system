"""Executor agent for executing planned steps."""

from typing import List
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
            success = False
            retry_count = 0
            last_error = None
            
            while not success and retry_count < max_retries:
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
                    
                    # Execute the tool
                    result = tool.execute(**step.input_data)
                    
                    # Record the step execution
                    memory_step = MemoryExecutionStep(
                        step_number=step.step_number,
                        description=step.description,
                        tool_name=tool_name,
                        input_data=step.input_data,
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
                        success = True
                    else:
                        last_error = result.error or "Tool returned no error details"
                        logger.warning(f"Step {step.step_number} failed: {result.error}")
                        retry_count += 1
                
                except Exception as e:
                    last_error = str(e)
                    logger.error(f"Step {step.step_number} error: {last_error}")
                    retry_count += 1
            
            if not success:
                error_details = last_error or "No error details were provided"
                error_msg = f"Step {step.step_number} failed after {max_retries} attempts: {error_details}"
                logger.error(error_msg)
                execution_context.fail(error_msg)
                return execution_context
        
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
    
    def _format_tool_error(self, error: str) -> str:
        """Format tool error message."""
        return f"Tool execution error: {error}"
