"""Execution history storage with pluggable JSONL and SQLite backends."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional, Protocol

from app.core.config import settings
from app.core.logging import logger
from app.schemas.history import ExecutionHistoryRecord, ExecutionHistorySummary


class HistoryStore(Protocol):
    def save_execution(self, record: ExecutionHistoryRecord) -> None: ...

    def get_execution(self, execution_id: str) -> Optional[ExecutionHistoryRecord]: ...

    def delete_execution(self, execution_id: str) -> bool: ...

    def list_executions(
        self,
        limit: int = 50,
        offset: int = 0,
        intent_filter: Optional[str] = None,
        status_filter: Optional[str] = None,
    ) -> List[ExecutionHistorySummary]: ...

    def get_statistics(self) -> Dict[str, Any]: ...

    def cleanup_old_records(self, days: int = 30) -> int: ...


class JSONLExecutionHistoryStore:
    """JSONL-based execution history storage."""

    def __init__(self, storage_dir: str = "./.execution_history"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.storage_dir / "executions.jsonl"
        logger.info("JSONLExecutionHistoryStore initialized at %s", self.storage_dir)

    def save_execution(self, record: ExecutionHistoryRecord) -> None:
        try:
            with open(self.history_file, "a", encoding="utf-8") as file_handle:
                file_handle.write(record.model_dump_json() + "\n")
            logger.info("Saved execution record: %s", record.execution_id)
        except Exception as exc:
            logger.error("Failed to save execution history: %s", str(exc))

    def get_execution(self, execution_id: str) -> Optional[ExecutionHistoryRecord]:
        try:
            if not self.history_file.exists():
                return None

            with open(self.history_file, "r", encoding="utf-8") as file_handle:
                for line in file_handle:
                    if not line.strip():
                        continue
                    try:
                        record_dict = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if record_dict.get("execution_id") == execution_id:
                        return ExecutionHistoryRecord(**record_dict)

            return None
        except Exception as exc:
            logger.error("Failed to retrieve execution: %s", str(exc))
            return None

    def delete_execution(self, execution_id: str) -> bool:
        try:
            if not self.history_file.exists():
                return False

            with open(self.history_file, "r", encoding="utf-8") as file_handle:
                lines = file_handle.readlines()

            kept_lines: List[str] = []
            removed = False

            for line in lines:
                if not line.strip():
                    continue
                try:
                    record_dict = json.loads(line)
                except json.JSONDecodeError:
                    kept_lines.append(line)
                    continue

                if record_dict.get("execution_id") == execution_id:
                    removed = True
                    continue

                kept_lines.append(line)

            if not removed:
                return False

            with open(self.history_file, "w", encoding="utf-8") as file_handle:
                file_handle.writelines(kept_lines)

            return True
        except Exception as exc:
            logger.error("Failed to delete execution history: %s", str(exc))
            return False

    def list_executions(
        self,
        limit: int = 50,
        offset: int = 0,
        intent_filter: Optional[str] = None,
        status_filter: Optional[str] = None,
    ) -> List[ExecutionHistorySummary]:
        try:
            if not self.history_file.exists():
                return []

            with open(self.history_file, "r", encoding="utf-8") as file_handle:
                lines = file_handle.readlines()

            summaries: List[ExecutionHistorySummary] = []
            skipped = 0

            for line in reversed(lines):
                if not line.strip():
                    continue
                try:
                    record_dict = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if intent_filter and record_dict.get("intent") != intent_filter:
                    continue
                if status_filter and record_dict.get("status") != status_filter:
                    continue
                if skipped < offset:
                    skipped += 1
                    continue

                if len(summaries) >= limit:
                    break

                summaries.append(
                    ExecutionHistorySummary(
                        execution_id=record_dict.get("execution_id"),
                        goal=record_dict.get("goal"),
                        intent=record_dict.get("intent"),
                        status=record_dict.get("status"),
                        timestamp=record_dict.get("timestamp"),
                        duration_ms=record_dict.get("duration_ms", 0),
                        tools_used=record_dict.get("tools_used", []),
                        success=record_dict.get("status") == "completed",
                    )
                )

            return summaries
        except Exception as exc:
            logger.error("Failed to list executions: %s", str(exc))
            return []

    def get_statistics(self) -> Dict[str, Any]:
        stats = {
            "total_executions": 0,
            "successful": 0,
            "failed": 0,
            "tools_used": [],
            "avg_duration_ms": 0,
            "intents": {},
        }
        try:
            if not self.history_file.exists():
                return stats

            total_duration = 0
            with open(self.history_file, "r", encoding="utf-8") as file_handle:
                for line in file_handle:
                    if not line.strip():
                        continue
                    try:
                        record_dict = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    stats["total_executions"] += 1
                    if record_dict.get("status") == "completed":
                        stats["successful"] += 1
                    else:
                        stats["failed"] += 1

                    for tool_name in record_dict.get("tools_used", []):
                        if tool_name not in stats["tools_used"]:
                            stats["tools_used"].append(tool_name)

                    duration = int(record_dict.get("duration_ms", 0) or 0)
                    total_duration += duration

                    intent = record_dict.get("intent", "unknown")
                    stats["intents"][intent] = stats["intents"].get(intent, 0) + 1

            if stats["total_executions"] > 0:
                stats["avg_duration_ms"] = int(total_duration / stats["total_executions"])

            return stats
        except Exception as exc:
            logger.error("Failed to get statistics: %s", str(exc))
            return stats

    def cleanup_old_records(self, days: int = 30) -> int:
        try:
            if not self.history_file.exists():
                return 0

            cutoff_date = datetime.utcnow() - timedelta(days=days)
            records_to_keep: List[Dict[str, Any]] = []
            removed = 0

            with open(self.history_file, "r", encoding="utf-8") as file_handle:
                for line in file_handle:
                    if not line.strip():
                        continue
                    try:
                        record_dict = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    timestamp_str = record_dict.get("timestamp", "")
                    try:
                        record_date = datetime.fromisoformat(timestamp_str)
                    except ValueError:
                        records_to_keep.append(record_dict)
                        continue

                    if record_date >= cutoff_date:
                        records_to_keep.append(record_dict)
                    else:
                        removed += 1

            with open(self.history_file, "w", encoding="utf-8") as file_handle:
                for record in records_to_keep:
                    file_handle.write(json.dumps(record) + "\n")

            return removed
        except Exception as exc:
            logger.error("Failed to cleanup records: %s", str(exc))
            return 0


class SQLiteExecutionHistoryStore:
    """SQLite-backed execution history storage."""

    def __init__(self, sqlite_path: str = "./.execution_history/executions.db"):
        self.sqlite_path = Path(sqlite_path)
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._initialize_schema()
        logger.info("SQLiteExecutionHistoryStore initialized at %s", self.sqlite_path)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.sqlite_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS executions (
                    execution_id TEXT PRIMARY KEY,
                    goal TEXT NOT NULL,
                    intent TEXT,
                    status TEXT NOT NULL,
                    steps_json TEXT NOT NULL,
                    tools_used_json TEXT NOT NULL,
                    final_result_json TEXT,
                    error_summary TEXT,
                    duration_ms INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    tool_failure_count INTEGER NOT NULL,
                    reasoning_step_count INTEGER NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_executions_timestamp ON executions(timestamp DESC)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_executions_status ON executions(status)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_executions_intent ON executions(intent)"
            )

    def save_execution(self, record: ExecutionHistoryRecord) -> None:
        try:
            with self._lock, self._connect() as connection:
                connection.execute(
                    """
                    INSERT OR REPLACE INTO executions (
                        execution_id, goal, intent, status,
                        steps_json, tools_used_json, final_result_json,
                        error_summary, duration_ms, timestamp,
                        tool_failure_count, reasoning_step_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.execution_id,
                        record.goal,
                        record.intent,
                        record.status,
                        json.dumps([step.model_dump() for step in record.steps]),
                        json.dumps(record.tools_used),
                        json.dumps(record.final_result) if record.final_result is not None else None,
                        record.error_summary,
                        record.duration_ms,
                        record.timestamp,
                        record.tool_failure_count,
                        record.reasoning_step_count,
                    ),
                )
        except Exception as exc:
            logger.error("Failed to save execution history to sqlite: %s", str(exc))

    def get_execution(self, execution_id: str) -> Optional[ExecutionHistoryRecord]:
        try:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT * FROM executions WHERE execution_id = ?",
                    (execution_id,),
                ).fetchone()

            if row is None:
                return None

            return self._row_to_record(row)
        except Exception as exc:
            logger.error("Failed to retrieve execution from sqlite: %s", str(exc))
            return None

    def delete_execution(self, execution_id: str) -> bool:
        try:
            with self._lock, self._connect() as connection:
                cursor = connection.execute(
                    "DELETE FROM executions WHERE execution_id = ?",
                    (execution_id,),
                )
                return int(cursor.rowcount or 0) > 0
        except Exception as exc:
            logger.error("Failed to delete execution from sqlite: %s", str(exc))
            return False

    def list_executions(
        self,
        limit: int = 50,
        offset: int = 0,
        intent_filter: Optional[str] = None,
        status_filter: Optional[str] = None,
    ) -> List[ExecutionHistorySummary]:
        try:
            clauses: List[str] = []
            values: List[Any] = []

            if intent_filter:
                clauses.append("intent = ?")
                values.append(intent_filter)
            if status_filter:
                clauses.append("status = ?")
                values.append(status_filter)
            where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""
            query = (
                "SELECT execution_id, goal, intent, status, timestamp, duration_ms, tools_used_json "
                "FROM executions "
                f"{where_clause} "
                "ORDER BY timestamp DESC LIMIT ? OFFSET ?"
            )
            values.extend([limit, offset])

            with self._connect() as connection:
                rows = connection.execute(query, values).fetchall()

            summaries: List[ExecutionHistorySummary] = []
            for row in rows:
                summaries.append(
                    ExecutionHistorySummary(
                        execution_id=row["execution_id"],
                        goal=row["goal"],
                        intent=row["intent"],
                        status=row["status"],
                        timestamp=row["timestamp"],
                        duration_ms=int(row["duration_ms"] or 0),
                        tools_used=json.loads(row["tools_used_json"] or "[]"),
                        success=row["status"] == "completed",
                    )
                )
            return summaries
        except Exception as exc:
            logger.error("Failed to list executions from sqlite: %s", str(exc))
            return []

    def get_statistics(self) -> Dict[str, Any]:
        stats = {
            "total_executions": 0,
            "successful": 0,
            "failed": 0,
            "tools_used": [],
            "avg_duration_ms": 0,
            "intents": {},
        }
        try:
            clauses: List[str] = []
            values: List[Any] = []
            where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""

            with self._connect() as connection:
                rows = connection.execute(
                    f"SELECT status, intent, duration_ms, tools_used_json FROM executions {where_clause}",
                    values,
                ).fetchall()

            total_duration = 0
            for row in rows:
                stats["total_executions"] += 1
                if row["status"] == "completed":
                    stats["successful"] += 1
                else:
                    stats["failed"] += 1

                for tool_name in json.loads(row["tools_used_json"] or "[]"):
                    if tool_name not in stats["tools_used"]:
                        stats["tools_used"].append(tool_name)

                duration = int(row["duration_ms"] or 0)
                total_duration += duration

                intent = row["intent"] or "unknown"
                stats["intents"][intent] = stats["intents"].get(intent, 0) + 1

            if stats["total_executions"] > 0:
                stats["avg_duration_ms"] = int(total_duration / stats["total_executions"])

            return stats
        except Exception as exc:
            logger.error("Failed to get sqlite statistics: %s", str(exc))
            return stats

    def cleanup_old_records(self, days: int = 30) -> int:
        try:
            cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
            with self._lock, self._connect() as connection:
                cursor = connection.execute(
                    "DELETE FROM executions WHERE timestamp < ?",
                    (cutoff_date,),
                )
                return int(cursor.rowcount or 0)
        except Exception as exc:
            logger.error("Failed to cleanup sqlite records: %s", str(exc))
            return 0

    def _row_to_record(self, row: sqlite3.Row) -> ExecutionHistoryRecord:
        steps = json.loads(row["steps_json"] or "[]")
        final_result = json.loads(row["final_result_json"]) if row["final_result_json"] else None
        return ExecutionHistoryRecord(
            execution_id=row["execution_id"],
            goal=row["goal"],
            intent=row["intent"],
            status=row["status"],
            steps=steps,
            tools_used=json.loads(row["tools_used_json"] or "[]"),
            final_result=final_result,
            error_summary=row["error_summary"],
            duration_ms=int(row["duration_ms"] or 0),
            timestamp=row["timestamp"],
            tool_failure_count=int(row["tool_failure_count"] or 0),
            reasoning_step_count=int(row["reasoning_step_count"] or 0),
        )


_history_store: Optional[HistoryStore] = None


class ExecutionHistoryStore(JSONLExecutionHistoryStore):
    """Backward-compatible alias for tests/imports expecting JSONL store class name."""

    pass


def get_history_store() -> HistoryStore:
    """Get or create the global history store instance based on configured backend."""
    global _history_store
    if _history_store is None:
        if settings.HISTORY_BACKEND == "sqlite":
            _history_store = SQLiteExecutionHistoryStore(settings.HISTORY_SQLITE_PATH)
        else:
            _history_store = JSONLExecutionHistoryStore(settings.HISTORY_STORAGE_DIR)
    return _history_store
