"""
Demo: End-to-End Execution with Mock LLM

This demo shows how the system works without needing an actual API key.
It mocks the LLM planner to show the complete execution flow.
"""

import sys
from pathlib import Path
from typing import Any, Dict, Optional
import json

sys.path.insert(0, str(Path(__file__).parent))

from app.agents.executor import ExecutorAgent
from app.agents.planner import PlannerAgent
from app.schemas.request_response import ExecutionStep
from app.llm.groq_client import BaseLLMClient, LLMResponse
from app.memory.vector_store import memory_store
from app.memory.schemas import ExecutionContext
from app.tools import initialize_tools
from app.core.logging import logger


class MockLLMClient(BaseLLMClient):
    """Mock LLM that returns predefined plans."""
    
    def call(self, messages, temperature=0.7, max_tokens=None) -> LLMResponse:
        """Return a mock plan for demonstration."""
        # Simulate a planner response that breaks down a goal
        plan = [
            {
                "step_number": 1,
                "description": "Store the goal and parameters in memory for later retrieval",
                "tool_name": "memory",
                "input_data": {
                    "action": "store",
                    "key": "execution_params",
                    "value": {"goal": "Demonstrate system", "ready": True}
                },
                "reasoning": "We need to preserve execution state"
            },
            {
                "step_number": 2,
                "description": "Retrieve the stored parameters from memory",
                "tool_name": "memory",
                "input_data": {
                    "action": "retrieve",
                    "key": "execution_params"
                },
                "reasoning": "Verify that memory operations work correctly"
            }
        ]
        
        return LLMResponse(content=json.dumps(plan))
    
    def parse_json(self, text: str) -> Dict[str, Any]:
        """Parse JSON from text."""
        return json.loads(text)


def demo_execution_flow():
    """Demonstrate complete execution flow."""
    print("\n" + "="*70)
    print("DEMO: End-to-End Agentic System Execution")
    print("="*70)
    
    # Initialize tools
    print("\n1. Initializing tools...")
    registry = initialize_tools()
    print(f"   ✓ {len(registry._tools)} tools registered")
    
    # Create mock planner
    print("\n2. Creating planner with mock LLM...")
    mock_llm = MockLLMClient()
    planner = PlannerAgent(llm_client=mock_llm)
    print("   ✓ Planner ready")
    
    # Generate plan
    print("\n3. Planning goal into steps...")
    goal = "Demonstrate the agentic system with tool execution"
    context = {"demo": True, "step": "planning"}
    
    steps = planner.plan(goal, context)
    print(f"   ✓ Generated {len(steps)} steps")
    for step in steps:
        print(f"      Step {step.step_number}: {step.description}")
    
    # Create execution context
    print("\n4. Creating execution context...")
    exec_context = memory_store.create_execution_context(
        goal=goal,
        user_context=context
    )
    print(f"   ✓ Execution ID: {exec_context.execution_id}")
    
    # Execute steps
    print("\n5. Executing steps...")
    executor = ExecutorAgent()
    exec_context = executor.execute(steps, exec_context)
    
    print(f"   ✓ Execution complete!")
    print(f"     Status: {exec_context.status}")
    print(f"     Steps completed: {len(exec_context.executed_steps)}")
    
    # Show results
    print("\n6. Execution Results:")
    print(f"   Status: {exec_context.status}")
    print(f"   Error: {exec_context.error}")
    print(f"   Final Result: {json.dumps(exec_context.final_result, indent=6)}")
    
    if exec_context.executed_steps:
        print(f"\n   Step Details:")
        for step in exec_context.executed_steps:
            print(f"     Step {step.step_number}:")
            print(f"       Tool: {step.tool_name}")
            print(f"       Success: {step.success}")
            print(f"       Output: {step.output}")


def demo_architecture_overview():
    """Show the system architecture."""
    print("\n" + "="*70)
    print("SYSTEM ARCHITECTURE")
    print("="*70)
    print("""
┌────────────────────────────────────────────────────────┐
│ User Goal: "Demonstrate agentic system"               │
└────────────────┬─────────────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────────────┐
│ PlannerAgent (with LLM)                               │
│ ┌────────────────────────────────────────────────────┐│
│ │ Step 1: Use memory tool to store data             ││
│ │ Step 2: Use memory tool to retrieve data          ││
│ └────────────────────────────────────────────────────┘│
└────────────────┬─────────────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────────────┐
│ ExecutorAgent                                         │
│ ┌────────────────────────────────────────────────────┐│
│ │ For each Step:                                    ││
│ │ 1. Get tool from registry                         ││
│ │ 2. Call tool.execute()                            ││
│ │ 3. Record result in ExecutionContext              ││
│ │ 4. Continue or fail based on success              ││
│ └────────────────────────────────────────────────────┘│
└────────────────┬─────────────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────────────┐
│ Tool Registry / Execution                             │
│ ┌──────────────┐      ┌──────────────┐               │
│ │ HTTPTool     │      │ MemoryTool   │               │
│ └──────────────┘      └──────────────┘               │
└────────────────────────────────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────────────┐
│ ExecutionContext (Memory Store)                       │
│ ├─ Execution ID                                      │
│ ├─ Executed Steps Record                             │
│ ├─ Intermediate Outputs                              │
│ └─ Final Result                                      │
└────────────────────────────────────────────────────────┘
    """)


def demo_tool_capabilities():
    """Show what each tool can do."""
    print("\n" + "="*70)
    print("AVAILABLE TOOLS & CAPABILITIES")
    print("="*70)
    
    registry = initialize_tools()
    
    for tool_name, tool in registry._tools.items():
        print(f"\n{tool_name.upper()}")
        print(f"Description: {tool.description}")
        print(f"Input Schema:")
        
        schema = tool.input_schema
        adapter = __import__('pydantic').TypeAdapter(schema)
        json_schema = adapter.json_schema()
        
        if "properties" in json_schema:
            for field_name, field_info in json_schema["properties"].items():
                required = field_name in json_schema.get("required", [])
                print(f"  • {field_name}: {field_info.get('type', 'object')}", end="")
                if required:
                    print(" [REQUIRED]")
                else:
                    print(f" [optional]")


if __name__ == "__main__":
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*68 + "║")
    print("║" + "  AGENTIC AI SYSTEM - DEMO".center(68) + "║")
    print("║" + "  End-to-End Execution with Mock LLM".center(68) + "║")
    print("║" + " "*68 + "║")
    print("╚" + "="*68 + "╝")
    
    try:
        demo_architecture_overview()
        demo_tool_capabilities()
        demo_execution_flow()
        
        print("\n" + "="*70)
        print("✓ DEMO COMPLETE!")
        print("="*70)
        print("""
Next Steps:
  1. Export your API key: export GROQ_API_KEY=... or OPENAI_API_KEY=...
  2. Run the server: uvicorn app.main:app --reload
  3. Test the /api/execute endpoint with a curl command
  4. Try the examples.py for more detailed examples
""")
    
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
