"""Test script to verify the agentic system architecture."""

import sys
import os
from pathlib import Path

# Add the workspace to Path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all modules can be imported."""
    try:
        print("Testing imports...")
        
        # Core imports
        from app.core.config import settings
        print("✓ Config loaded")
        
        from app.core.logging import logger
        print("✓ Logging initialized")
        
        # Schema imports
        from app.schemas.request_response import ExecuteRequest, ExecuteResponse
        print("✓ Schemas imported")
        
        # Memory imports
        from app.memory.schemas import ExecutionContext
        from app.memory.vector_store import memory_store
        print("✓ Memory system initialized")
        
        # Tools imports
        from app.tools import initialize_tools, tool_registry
        tools = initialize_tools()
        print(f"✓ Tools initialized ({len(tools._tools)} tools registered)")
        print(f"  Available tools: {list(tools.list_tools().keys())}")
        
        # Agent imports
        from app.agents.planner import PlannerAgent
        from app.agents.executor import ExecutorAgent
        from app.agents.runner import AgentRunner
        print("✓ Agents initialized")
        
        # LLM imports
        from app.llm.groq_client import get_llm_client
        print("✓ LLM client available")
        
        return True
    
    except Exception as e:
        print(f"✗ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_tool_registry():
    """Test tool registry functionality."""
    try:
        print("\nTesting tool registry...")
        from app.tools import initialize_tools
        
        registry = initialize_tools()
        
        # Test HTTP tool
        http_tool = registry.get("http")
        if http_tool:
            print(f"✓ HTTP tool available: {http_tool.description}")
        
        # Test Memory tool
        memory_tool = registry.get("memory")
        if memory_tool:
            print(f"✓ Memory tool available: {memory_tool.description}")
        
        return True
    
    except Exception as e:
        print(f"✗ Tool registry test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_memory_system():
    """Test memory system."""
    try:
        print("\nTesting memory system...")
        from app.memory.vector_store import memory_store
        
        # Create context
        ctx = memory_store.create_execution_context(
            goal="Test goal",
            user_context={"test": True}
        )
        print(f"✓ Created execution context: {ctx.execution_id}")
        
        # Verify storage
        retrieved = memory_store.get_context(ctx.execution_id)
        if retrieved and retrieved.goal == "Test goal":
            print(f"✓ Context successfully stored and retrieved")
        
        return True
    
    except Exception as e:
        print(f"✗ Memory system test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_tool_execution():
    """Test tool execution."""
    try:
        print("\nTesting tool execution...")
        from app.tools import initialize_tools
        
        registry = initialize_tools()
        
        # Test memory tool store
        memory_tool = registry.get("memory")
        result = memory_tool.execute(
            action="store",
            key="test_key",
            value={"test": "data"}
        )
        
        if result.success:
            print(f"✓ Memory tool store succeeded")
        else:
            print(f"✗ Memory tool store failed: {result.error}")
            return False
        
        # Test memory tool retrieve
        result = memory_tool.execute(
            action="retrieve",
            key="test_key"
        )
        
        if result.success and result.result["value"]["test"] == "data":
            print(f"✓ Memory tool retrieve succeeded")
        else:
            print(f"✗ Memory tool retrieve failed: {result.error}")
            return False
        
        return True
    
    except Exception as e:
        print(f"✗ Tool execution test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("AGENTIC AI SYSTEM - ARCHITECTURE TEST")
    print("=" * 60)
    
    all_passed = True
    all_passed &= test_imports()
    all_passed &= test_tool_registry()
    all_passed &= test_memory_system()
    all_passed &= test_tool_execution()
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ ALL TESTS PASSED")
    else:
        print("✗ SOME TESTS FAILED")
    print("=" * 60)
    
    sys.exit(0 if all_passed else 1)
