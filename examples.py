"""
Example: End-to-End Agentic System Usage

This example demonstrates how to use the agentic system to plan and execute
a goal using the available tools.

Note: Requires GROQ_API_KEY or OPENAI_API_KEY environment variable.
"""

import sys
import json
from pathlib import Path

# Add workspace to path
sys.path.insert(0, str(Path(__file__).parent))


def example_1_tool_registry():
    """Example 1: Explore available tools."""
    print("\n" + "="*70)
    print("EXAMPLE 1: Tool Registry")
    print("="*70)
    
    from app.tools import initialize_tools
    
    # Initialize tools
    registry = initialize_tools()
    
    # List available tools
    print("\nAvailable Tools:")
    for tool_name, description in registry.list_tools().items():
        print(f"  • {tool_name:15} - {description}")


def example_2_memory_operations():
    """Example 2: Store and retrieve from memory."""
    print("\n" + "="*70)
    print("EXAMPLE 2: Memory Tool Operations")
    print("="*70)
    
    from app.tools import initialize_tools
    
    registry = initialize_tools()
    memory_tool = registry.get("memory")
    
    # Store data
    print("\n1. Storing data in memory...")
    result = memory_tool.execute(
        action="store",
        key="user_data",
        value={"name": "Alice", "email": "alice@example.com", "role": "admin"}
    )
    print(f"   Result: {result.result}")
    
    # Retrieve data
    print("\n2. Retrieving data from memory...")
    result = memory_tool.execute(
        action="retrieve",
        key="user_data"
    )
    print(f"   Retrieved: {json.dumps(result.result, indent=2)}")


def example_3_execution_context():
    """Example 3: Create and track execution context."""
    print("\n" + "="*70)
    print("EXAMPLE 3: Execution Context Management")
    print("="*70)
    
    from app.memory.vector_store import memory_store
    from app.memory.schemas import ExecutionStep
    from datetime import datetime
    
    # Create context
    print("\n1. Creating execution context...")
    ctx = memory_store.create_execution_context(
        goal="Fetch public API data",
        user_context={"api": "github", "repo": "python/cpython"}
    )
    print(f"   Execution ID: {ctx.execution_id}")
    print(f"   Goal: {ctx.goal}")
    
    # Simulate adding steps
    print("\n2. Recording step execution...")
    step = ExecutionStep(
        step_number=1,
        tool_name="http",
        input_data={"method": "GET", "url": "https://api.github.com/repos/python/cpython"},
        output={"status_code": 200, "data": "..."},
        success=True
    )
    ctx.add_step(step)
    print(f"   Added step: {step.tool_name}")
    
    # Store output
    ctx.set_output(1, {"stars": 54000, "forks": 24000}, key="repo_stats")
    
    # Complete
    ctx.complete({"summary": "Successfully fetched repo stats"})
    memory_store.save_context(ctx)
    
    print(f"\n3. Context saved:")
    print(f"   Status: {ctx.status}")
    print(f"   Steps: {len(ctx.executed_steps)}")
    print(f"   Final Result: {ctx.final_result}")


def example_4_tool_input_schemas():
    """Example 4: Understand tool input schemas."""
    print("\n" + "="*70)
    print("EXAMPLE 4: Tool Input Schemas (for AI Planning)")
    print("="*70)
    
    from app.tools import initialize_tools
    from pydantic import TypeAdapter
    
    registry = initialize_tools()
    
    print("\nTool Input Specifications (what LLM can plan):\n")
    
    for tool_name, tool in registry._tools.items():
        schema = tool.input_schema
        print(f"Tool: {tool_name}")
        print(f"Description: {tool.description}")
        print(f"Input Schema:")
        
        # Print field information
        adapter = TypeAdapter(schema)
        json_schema = adapter.json_schema()
        
        if "properties" in json_schema:
            for field_name, field_info in json_schema["properties"].items():
                required = field_name in json_schema.get("required", [])
                print(f"  - {field_name}: {field_info.get('type', 'object')}", end="")
                if required:
                    print(" (REQUIRED)")
                else:
                    print(f" (optional, default: {field_info.get('default', 'N/A')})")
        print()


def example_5_planning_process():
    """Example 5: Show how planning works (requires API key)."""
    print("\n" + "="*70)
    print("EXAMPLE 5: Planning Process (Breakdown Goal → Steps)")
    print("="*70)
    
    try:
        from app.agents.planner import PlannerAgent
        
        print("\nInitializing Planner...")
        planner = PlannerAgent()
        
        goal = "Fetch public repository information from GitHub API"
        context = {"owner": "python", "repo": "cpython"}
        
        print(f"\nGoal: {goal}")
        print(f"Context: {context}")
        print("\nCalling LLM to generate execution plan...")
        
        steps = planner.plan(goal, context)
        
        print(f"\n✓ Generated {len(steps)} execution steps:\n")
        for step in steps:
            print(f"Step {step.step_number}: {step.description}")
            print(f"  Tool: {step.tool_name}")
            print(f"  Input: {step.input_data}")
            if step.reasoning:
                print(f"  Reasoning: {step.reasoning}")
            print()
    
    except ValueError as e:
        if "API_KEY" in str(e):
            print(f"\n⚠️  Skipped (no API key configured)")
            print(f"   To run this example, set:")
            print(f"   export GROQ_API_KEY=<your_key>")
            print(f"   OR")
            print(f"   export OPENAI_API_KEY=<your_key>")
        else:
            raise
    except Exception as e:
        print(f"\n✗ Error: {e}")


def example_6_execution_flow():
    """Example 6: Show complete execution flow (requires API key)."""
    print("\n" + "="*70)
    print("EXAMPLE 6: End-to-End Execution Flow")
    print("="*70)
    
    try:
        from app.agents.runner import AgentRunner
        from app.tools.memory_tool import MemoryTool
        
        print("\nInitializing Agent Runner...")
        runner = AgentRunner()
        
        # Clear memory to start fresh
        MemoryTool.clear()
        
        goal = "Fetch and store data from a public API"
        context = {
            "api_url": "https://api.github.com/repos/python/cpython",
            "method": "GET"
        }
        
        print(f"\nGoal: {goal}")
        print(f"Context: {context}")
        print("\n" + "-"*70)
        print("Executing (Plan → Execute)...")
        print("-"*70)
        
        execution_context = runner.run(goal, context)
        
        print(f"\n✓ Execution Complete!")
        print(f"  ID: {execution_context.execution_id}")
        print(f"  Status: {execution_context.status}")
        print(f"  Steps executed: {len(execution_context.executed_steps)}")
        
        if execution_context.error:
            print(f"  Error: {execution_context.error}")
        else:
            print(f"  Final Result: {json.dumps(execution_context.final_result, indent=4)}")
    
    except ValueError as e:
        if "API_KEY" in str(e):
            print(f"\n⚠️  Skipped (no API key configured)")
            print(f"   To run end-to-end execution, set environment variables:")
            print(f"   export GROQ_API_KEY=<your_key>")
            print(f"   OR")
            print(f"   export OPENAI_API_KEY=<your_key>")
        else:
            raise
    except Exception as e:
        print(f"\n✗ Error during execution: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*68 + "║")
    print("║" + "  AGENTIC AI SYSTEM - EXAMPLES".center(68) + "║")
    print("║" + " "*68 + "║")
    print("╚" + "="*68 + "╝")
    
    # Run examples
    example_1_tool_registry()
    example_2_memory_operations()
    example_3_execution_context()
    example_4_tool_input_schemas()
    example_5_planning_process()
    example_6_execution_flow()
    
    print("\n" + "="*70)
    print("✓ Examples Complete!")
    print("="*70)
    print("\nNext Steps:")
    print("  1. Set your LLM API key: export GROQ_API_KEY=... or OPENAI_API_KEY=...")
    print("  2. Start the server: uvicorn app.main:app --reload")
    print("  3. Try: curl -X POST http://localhost:8000/api/execute ...")
    print()
