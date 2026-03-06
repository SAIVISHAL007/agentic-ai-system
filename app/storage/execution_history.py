"""Execution history storage - lightweight JSON-based persistence."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from app.core.logging import logger
from app.schemas.history import ExecutionHistoryRecord, ExecutionHistorySummary


class ExecutionHistoryStore:
    """Lightweight JSON-based execution history storage.
    
    Stores execution records in a JSON file for persistence.
    Provides query and retrieval methods for history access.
    """
    
    def __init__(self, storage_dir: str = "./.execution_history"):
        """Initialize history store.
        
        Args:
            storage_dir: Directory to store history files
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.storage_dir / "executions.jsonl"
        logger.info(f"ExecutionHistoryStore initialized at {self.storage_dir}")
    
    def save_execution(self, record: ExecutionHistoryRecord) -> None:
        """Save an execution record to history.
        
        Args:
            record: ExecutionHistoryRecord to save
        """
        try:
            # Append as JSONL (one JSON object per line)
            with open(self.history_file, "a") as f:
                f.write(record.model_dump_json() + "\n")
            logger.info(f"Saved execution record: {record.execution_id}")
        except Exception as e:
            logger.error(f"Failed to save execution history: {str(e)}")
    
    def get_execution(self, execution_id: str) -> Optional[ExecutionHistoryRecord]:
        """Retrieve a complete execution record by ID.
        
        Args:
            execution_id: ID of execution to retrieve
        
        Returns:
            ExecutionHistoryRecord if found, None otherwise
        """
        try:
            if not self.history_file.exists():
                return None
            
            with open(self.history_file, "r") as f:
                for line in f:
                    if line.strip():
                        try:
                            record_dict = json.loads(line)
                            if record_dict.get("execution_id") == execution_id:
                                return ExecutionHistoryRecord(**record_dict)
                        except json.JSONDecodeError:
                            continue
            
            logger.debug(f"Execution not found: {execution_id}")
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve execution: {str(e)}")
            return None
    
    def list_executions(
        self,
        limit: int = 50,
        offset: int = 0,
        intent_filter: Optional[str] = None,
        status_filter: Optional[str] = None,
    ) -> List[ExecutionHistorySummary]:
        """List execution history with filtering and pagination.
        
        Args:
            limit: Max records to return (default 50)
            offset: Number of records to skip (default 0)
            intent_filter: Filter by intent (optional)
            status_filter: Filter by status (optional)
        
        Returns:
            List of ExecutionHistorySummary records
        """
        try:
            summaries = []
            count = 0
            skipped = 0
            
            if not self.history_file.exists():
                return []
            
            # Read from end for most recent first
            with open(self.history_file, "r") as f:
                lines = f.readlines()
            
            # Process in reverse order (most recent first)
            for line in reversed(lines):
                if not line.strip():
                    continue
                
                try:
                    record_dict = json.loads(line)
                    
                    # Apply filters
                    if intent_filter and record_dict.get("intent") != intent_filter:
                        continue
                    if status_filter and record_dict.get("status") != status_filter:
                        continue
                    
                    # Apply pagination
                    if skipped < offset:
                        skipped += 1
                        continue
                    
                    if count >= limit:
                        break
                    
                    # Create summary (exclude large fields)
                    summary = ExecutionHistorySummary(
                        execution_id=record_dict.get("execution_id"),
                        goal=record_dict.get("goal"),
                        intent=record_dict.get("intent"),
                        status=record_dict.get("status"),
                        timestamp=record_dict.get("timestamp"),
                        duration_ms=record_dict.get("duration_ms"),
                        tools_used=record_dict.get("tools_used", []),
                        success=record_dict.get("status") == "completed",
                    )
                    summaries.append(summary)
                    count += 1
                except json.JSONDecodeError:
                    continue
            
            logger.debug(f"Retrieved {len(summaries)} execution summaries")
            return summaries
        except Exception as e:
            logger.error(f"Failed to list executions: {str(e)}")
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get overall execution statistics.
        
        Returns:
            Dictionary with statistics
        """
        try:
            stats = {
                "total_executions": 0,
                "successful": 0,
                "failed": 0,
                "tools_used": [],
                "avg_duration_ms": 0,
                "intents": {}
            }
            
            if not self.history_file.exists():
                return stats
            
            total_duration = 0
            
            with open(self.history_file, "r") as f:
                for line in f:
                    if not line.strip():
                        continue
                    
                    try:
                        record_dict = json.loads(line)
                        stats["total_executions"] += 1
                        
                        if record_dict.get("status") == "completed":
                            stats["successful"] += 1
                        else:
                            stats["failed"] += 1
                        
                        # Track tools
                        tools = record_dict.get("tools_used", [])
                        for tool in tools:
                            if tool not in stats["tools_used"]:
                                stats["tools_used"].append(tool)
                        
                        # Track duration
                        duration = record_dict.get("duration_ms", 0)
                        total_duration += duration
                        
                        # Track intents
                        intent = record_dict.get("intent", "unknown")
                        stats["intents"][intent] = stats["intents"].get(intent, 0) + 1
                    except json.JSONDecodeError:
                        continue
            
            if stats["total_executions"] > 0:
                stats["avg_duration_ms"] = int(total_duration / stats["total_executions"])
            
            logger.debug(f"Generated statistics from {stats['total_executions']} executions")
            return stats
        except Exception as e:
            logger.error(f"Failed to get statistics: {str(e)}")
            return {}
    
    def cleanup_old_records(self, days: int = 30) -> int:
        """Remove execution records older than specified days.
        
        Args:
            days: Keep records from last N days
        
        Returns:
            Number of records removed
        """
        try:
            from datetime import timedelta
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            removed = 0
            
            if not self.history_file.exists():
                return 0
            
            # Read all records
            records = []
            with open(self.history_file, "r") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        record_dict = json.loads(line)
                        timestamp_str = record_dict.get("timestamp", "")
                        try:
                            record_date = datetime.fromisoformat(timestamp_str)
                            if record_date >= cutoff_date:
                                records.append(record_dict)
                            else:
                                removed += 1
                        except ValueError:
                            records.append(record_dict)
                    except json.JSONDecodeError:
                        continue
            
            # Write back cleaned records
            with open(self.history_file, "w") as f:
                for record in records:
                    f.write(json.dumps(record) + "\n")
            
            logger.info(f"Cleaned up {removed} old execution records")
            return removed
        except Exception as e:
            logger.error(f"Failed to cleanup records: {str(e)}")
            return 0


# Global singleton instance
_history_store: Optional[ExecutionHistoryStore] = None


def get_history_store() -> ExecutionHistoryStore:
    """Get or create the global history store instance."""
    global _history_store
    if _history_store is None:
        _history_store = ExecutionHistoryStore()
    return _history_store
