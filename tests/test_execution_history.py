"""Tests for execution history storage and API."""
import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from app.storage.execution_history import ExecutionHistoryStore
from app.schemas.history import (
    ExecutionHistoryRecord,
    ExecutionHistoryStep,
    ExecutionHistorySummary,
)


class TestExecutionHistoryStorage:
    """Test execution history storage functionality."""
    
    @pytest.fixture
    def temp_history_store(self):
        """Create a temporary history store for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ExecutionHistoryStore(storage_dir=tmpdir)
            yield store
    
    def test_save_and_retrieve_execution(self, temp_history_store):
        """Test saving and retrieving a complete execution record."""
        record = ExecutionHistoryRecord(
            execution_id="test_001",
            goal="Test goal",
            intent="reasoning_only",
            status="completed",
            steps=[
                ExecutionHistoryStep(
                    step_number=1,
                    tool_name="reasoning",
                    description="Think about it",
                    success=True,
                )
            ],
            tools_used=["reasoning"],
            final_result={
                "success": True,
                "content": "Test result",
                "source": "reasoning",
                "confidence": 0.95,
                "execution_id": "test_001"
            },
            duration_ms=1000,
        )
        
        # Save
        temp_history_store.save_execution(record)
        
        # Retrieve
        retrieved = temp_history_store.get_execution("test_001")
        
        assert retrieved is not None
        assert retrieved.execution_id == "test_001"
        assert retrieved.goal == "Test goal"
        assert retrieved.status == "completed"
        assert retrieved.tools_used == ["reasoning"]
    
    def test_list_executions_most_recent_first(self, temp_history_store):
        """Test that list returns most recent executions first."""
        # Save multiple records
        for i in range(3):
            record = ExecutionHistoryRecord(
                execution_id=f"test_{i:03d}",
                goal=f"Goal {i}",
                intent="tool_required",
                status="completed",
                duration_ms=1000 + i * 100,
            )
            temp_history_store.save_execution(record)
        
        # List
        executions = temp_history_store.list_executions(limit=10)
        
        assert len(executions) == 3
        # Most recent first (reverse order of saved)
        assert executions[0].execution_id == "test_002"
        assert executions[1].execution_id == "test_001"
        assert executions[2].execution_id == "test_000"
    
    def test_list_executions_with_pagination(self, temp_history_store):
        """Test pagination in list_executions."""
        # Save 5 records
        for i in range(5):
            record = ExecutionHistoryRecord(
                execution_id=f"test_{i:03d}",
                goal=f"Goal {i}",
                intent="tool_required",
                status="completed",
            )
            temp_history_store.save_execution(record)
        
        # Test limit
        executions = temp_history_store.list_executions(limit=2)
        assert len(executions) == 2
        
        # Test offset
        executions = temp_history_store.list_executions(limit=2, offset=2)
        assert len(executions) == 2
        assert executions[0].execution_id == "test_002"
    
    def test_list_executions_with_intent_filter(self, temp_history_store):
        """Test filtering by intent."""
        # Save records with different intents
        for intent in ["tool_required", "reasoning_only", "tool_required"]:
            record = ExecutionHistoryRecord(
                execution_id=f"test_{intent}",
                goal=f"Goal",
                intent=intent,
                status="completed",
            )
            temp_history_store.save_execution(record)
        
        # Filter by tool_required
        executions = temp_history_store.list_executions(intent_filter="tool_required", limit=10)
        
        assert len(executions) == 2
        assert all(e.intent == "tool_required" for e in executions)
    
    def test_list_executions_with_status_filter(self, temp_history_store):
        """Test filtering by status."""
        # Save records with different statuses
        for status in ["completed", "failed", "completed"]:
            record = ExecutionHistoryRecord(
                execution_id=f"test_{status}",
                goal=f"Goal",
                status=status,
            )
            temp_history_store.save_execution(record)
        
        # Filter by completed
        executions = temp_history_store.list_executions(status_filter="completed", limit=10)
        
        assert len(executions) == 2
        assert all(e.status == "completed" for e in executions)
    
    def test_get_statistics(self, temp_history_store):
        """Test statistics generation."""
        # Save diverse records
        records = [
            ("completed", "tool_required", ["http", "reasoning"]),
            ("completed", "tool_required", ["http"]),
            ("failed", "tool_required", ["http"]),
            ("completed", "reasoning_only", ["reasoning"]),
        ]
        
        for idx, (status, intent, tools) in enumerate(records):
            record = ExecutionHistoryRecord(
                execution_id=f"test_{idx:03d}",
                goal=f"Goal {idx}",
                intent=intent,
                status=status,
                tools_used=tools,
                duration_ms=1000 + idx * 100,
                tool_failure_count=1 if status == "failed" else 0,
            )
            temp_history_store.save_execution(record)
        
        # Get stats
        stats = temp_history_store.get_statistics()
        
        assert stats["total_executions"] == 4
        assert stats["successful"] == 3
        assert stats["failed"] == 1
        assert "http" in stats["tools_used"]
        assert "reasoning" in stats["tools_used"]
        assert stats["intents"]["tool_required"] == 3
        assert stats["intents"]["reasoning_only"] == 1
    
    def test_cleanup_old_records(self, temp_history_store):
        """Test cleanup of old records."""
        # Save records with old timestamps
        old_date = (datetime.utcnow() - timedelta(days=40)).isoformat()
        new_date = datetime.utcnow().isoformat()
        
        old_record = ExecutionHistoryRecord(
            execution_id="test_old",
            goal="Old goal",
            status="completed",
            timestamp=old_date,
        )
        new_record = ExecutionHistoryRecord(
            execution_id="test_new",
            goal="New goal",
            status="completed",
            timestamp=new_date,
        )
        
        temp_history_store.save_execution(old_record)
        temp_history_store.save_execution(new_record)
        
        # Verify both exist
        assert temp_history_store.get_execution("test_old") is not None
        assert temp_history_store.get_execution("test_new") is not None
        
        # Cleanup (keep only 30 days)
        removed = temp_history_store.cleanup_old_records(days=30)
        
        assert removed == 1
        assert temp_history_store.get_execution("test_old") is None
        assert temp_history_store.get_execution("test_new") is not None
    
    def test_execution_history_record_schema(self):
        """Test that ExecutionHistoryRecord schema is correct."""
        record = ExecutionHistoryRecord(
            execution_id="test_001",
            goal="Test goal",
            intent="tool_required",
            status="completed",
            steps=[
                ExecutionHistoryStep(
                    step_number=1,
                    tool_name="http",
                    description="Fetch data",
                    success=True,
                )
            ],
            tools_used=["http"],
            duration_ms=2000,
            tool_failure_count=0,
            reasoning_step_count=0,
        )
        
        # Verify schema is serializable
        record_dict = record.model_dump()
        assert record_dict["execution_id"] == "test_001"
        assert record_dict["status"] == "completed"
        
        # Verify JSON serialization
        json_str = record.model_dump_json()
        assert "test_001" in json_str
        assert "completed" in json_str
    
    def test_execution_history_summary_schema(self):
        """Test ExecutionHistorySummary lightweight schema."""
        summary = ExecutionHistorySummary(
            execution_id="test_001",
            goal="Test goal",
            intent="tool_required",
            status="completed",
            timestamp="2026-03-06T10:00:00",
            duration_ms=2000,
            tools_used=["http", "reasoning"],
            success=True,
        )
        
        # Verify no large fields
        summary_dict = summary.model_dump()
        assert len(summary_dict) == 8  # Only 8 fields, no large data
        assert "steps" not in summary_dict
        assert "final_result" not in summary_dict
    
    def test_empty_history_returns_empty_list(self, temp_history_store):
        """Test that empty store returns empty list."""
        executions = temp_history_store.list_executions()
        assert executions == []
    
    def test_empty_history_returns_empty_stats(self, temp_history_store):
        """Test that empty store returns empty stats."""
        stats = temp_history_store.get_statistics()
        assert stats["total_executions"] == 0
        assert stats["successful"] == 0
        assert stats["failed"] == 0
    
    def test_non_existent_execution_returns_none(self, temp_history_store):
        """Test retrieving non-existent execution."""
        result = temp_history_store.get_execution("non_existent")
        assert result is None


class TestExecutionHistoryIntegration:
    """Test integration of history with runner."""
    
    def test_runner_saves_execution_to_history(self):
        """Test that runner saves execution to history after running."""
        from app.agents.runner import AgentRunner
        from unittest.mock import Mock, patch
        
        # Create runner
        runner = AgentRunner()
        
        # Mock planner and executor
        with patch.object(runner, "planner") as mock_planner, \
             patch.object(runner, "executor") as mock_executor, \
             patch("app.agents.runner.get_history_store") as mock_get_store:
            
            # Setup plan
            mock_planner.classify_intent.return_value = "reasoning_only"
            mock_planner.plan.return_value = []
            
            # Setup execution context with reasoning output
            from app.memory.schemas import ExecutionContext, ExecutionStep
            exec_context = ExecutionContext(
                execution_id="test_exec_001",
                goal="Test goal",
                user_context={},
            )
            exec_context.intent = "reasoning_only"
            exec_context.status = "completed"
            exec_context.execution_summary = {"tools_used": ["reasoning"], "tool_failures": 0}
            
            step = ExecutionStep(
                step_number=1,
                description="Test",
                tool_name="reasoning",
                input_data={},
                output="Test output",
                success=True
            )
            exec_context.executed_steps = [step]
            
            mock_executor.execute.return_value = exec_context
            
            # Mock history store
            mock_store = Mock()
            mock_get_store.return_value = mock_store
            
            # Run
            runner.run("Test goal")
            
            # Verify history store save was called
            assert mock_store.save_execution.called
            
            # Verify the record that was saved
            call_args = mock_store.save_execution.call_args
            saved_record = call_args[0][0]  # First positional argument
            
            assert saved_record.execution_id == "test_exec_001"
            assert saved_record.goal == "Test goal"
            assert saved_record.intent == "reasoning_only"
