"""Agent runner - orchestrates planning and execution."""

from typing import Any, Dict, Optional
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
        
        # Create execution context
        execution_context = self.memory_store.create_execution_context(
            goal=goal,
            user_context=context or {}
        )
        logger.debug(f"Created execution context: {execution_context.execution_id}")
        
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
            
            # Save to memory
            self.memory_store.save_context(execution_context)
            logger.info(f"Execution completed with status: {execution_context.status}")
            
            return execution_context
        
        except Exception as e:
            error_msg = f"Agent run failed: {str(e)}"
            logger.error(error_msg)
            execution_context.fail(error_msg)
            self.memory_store.save_context(execution_context)
            return execution_context
