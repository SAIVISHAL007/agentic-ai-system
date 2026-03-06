# Execution History Storage - Implementation Guide

## Overview

Execution history storage is a **lightweight, JSON-based persistence layer** for the agentic AI system. It automatically saves all executions (successful and failed) for audit trails, analytics, and debugging.

**Key Design Principles**:
- ✅ **Lightweight**: JSON files, no database needed
- ✅ **Non-intrusive**: Transparently integrated into runner
- ✅ **Data-aware**: Excludes unnecessary large API payloads
- ✅ **Query-rich**: List, filter, search execution history
- ✅ **Preserves Architecture**: No changes to core agentic system

---

## Architecture

### Components

```
ExecutionHistoryStore (Storage Layer)
  ├── save_execution() → Save record to JSONL file
  ├── get_execution() → Retrieve full record by ID
  ├── list_executions() → List with filtering/pagination
  ├── get_statistics() → Aggregate stats
  └── cleanup_old_records() → Data hygiene

AgentRunner (Integration Point)
  └── _save_execution_to_history() → Called after each run

API Routes (Access Layer)
  ├── GET /api/history → List summaries
  ├── GET /api/history/{id} → Full details
  └── GET /api/history/stats → Aggregate stats
```

### Data Flow

```
User Request → Runner.run() → Planning → Execution
                                            ↓
                                        Completed
                                            ↓
                    _save_execution_to_history()
                                            ↓
                    ExecutionHistoryRecord created
                                            ↓
                    history_store.save_execution()
                                            ↓
                    Appended to executions.jsonl
```

---

## Storage Format

### ExecutionHistoryRecord (Full Storage)

```json
{
  "execution_id": "exec_abc123",
  "goal": "Fetch TensorFlow repo and explain it",
  "intent": "tool_required",
  "status": "completed",
  "steps": [
    {
      "step_number": 1,
      "tool_name": "http",
      "description": "Fetch repository from GitHub",
      "success": true,
      "error": null
    },
    {
      "step_number": 2,
      "tool_name": "reasoning",
      "description": "Explain the repository",
      "success": true,
      "error": null
    }
  ],
  "tools_used": ["http", "reasoning"],
  "final_result": {
    "success": true,
    "source": "reasoning",
    "confidence": 0.95,
    "execution_id": "exec_abc123",
    "content": "TensorFlow is..."
  },
  "error_summary": null,
  "duration_ms": 2500,
  "timestamp": "2026-03-06T10:30:00.000000",
  "tool_failure_count": 0,
  "reasoning_step_count": 1
}
```

**Storage Location**: `.execution_history/executions.jsonl`
- One JSON object per line (JSONL format)
- Append-only for performance
- Most recent records at end

### ExecutionHistorySummary (API List View - Lightweight)

```json
{
  "execution_id": "exec_abc123",
  "goal": "Fetch TensorFlow repo and explain it",
  "intent": "tool_required",
  "status": "completed",
  "timestamp": "2026-03-06T10:30:00.000000",
  "duration_ms": 2500,
  "tools_used": ["http", "reasoning"],
  "success": true
}
```

**Used in**: `GET /api/history` (keeps payload lean)

---

## API Endpoints

### 1. List Execution History

```bash
GET /api/history?limit=50&offset=0&intent=tool_required&status=completed
```

**Query Parameters**:
- `limit` (1-500, default 50): Results per page
- `offset` (default 0): Pagination offset
- `intent` (optional): Filter by `tool_required`, `reasoning_only`, `mixed`
- `status` (optional): Filter by `completed`, `failed`, `partial`

**Response**:
```json
{
  "executions": [
    {
      "execution_id": "exec_abc123",
      "goal": "Fetch TensorFlow repo...",
      "intent": "tool_required",
      "status": "completed",
      "timestamp": "2026-03-06T10:30:00",
      "duration_ms": 2500,
      "tools_used": ["http", "reasoning"],
      "success": true
    }
  ],
  "total_count": 42,
  "offset": 0,
  "limit": 50
}
```

### 2. Get Execution Detail

```bash
GET /api/history/exec_abc123
```

**Response** (Complete ExecutionHistoryRecord):
```json
{
  "execution": {
    "execution_id": "exec_abc123",
    "goal": "Fetch TensorFlow repo...",
    "intent": "tool_required",
    "status": "completed",
    "steps": [...],
    "tools_used": ["http", "reasoning"],
    "final_result": {...},
    "duration_ms": 2500,
    "timestamp": "2026-03-06T10:30:00",
    "tool_failure_count": 0,
    "reasoning_step_count": 1
  }
}
```

### 3. Get Statistics

```bash
GET /api/history/stats
```

**Response**:
```json
{
  "total_executions": 42,
  "successful": 38,
  "failed": 4,
  "tools_used": ["http", "reasoning", "memory"],
  "avg_duration_ms": 2100,
  "intents": {
    "tool_required": 28,
    "reasoning_only": 10,
    "mixed": 4
  }
}
```

---

## Integration with Runner

### Automatic Persistence

The runner automatically saves history after each execution:

```python
# In AgentRunner.run()
try:
    # ... execution logic ...
    
    # Save to history (always called, even on failure)
    self._save_execution_to_history(execution_context, duration_ms)
    return execution_context
except Exception as e:
    # ... error handling ...
    
    # Still saves history on failure
    self._save_execution_to_history(execution_context, duration_ms)
    return execution_context
```

### What Gets Saved

✅ **Always saved**:
- execution_id, goal, intent, status
- All executed steps (simplified)
- Tools used, duration, timestamp
- Final result (structured)
- Error summary (if failed)

❌ **NOT saved** (data hygiene):
- Raw HTTP response bodies (unless essential)
- Large serialized objects
- Sensitive credentials or tokens
- Intermediate tool inputs/outputs (only final results)

---

## Data Management

### Storage Directory

Default location: `./.execution_history/`

Change location:
```python
from app.storage.execution_history import ExecutionHistoryStore

store = ExecutionHistoryStore(storage_dir="/custom/path")
```

### Cleanup Old Records

```python
# Remove records older than 30 days
removed = history_store.cleanup_old_records(days=30)
print(f"Removed {removed} old records")
```

### Database-like Queries

```python
# List with filtering
executions = history_store.list_executions(
    limit=50,
    offset=0,
    intent_filter="tool_required",
    status_filter="completed"
)

# Get statistics
stats = history_store.get_statistics()
print(f"Total: {stats['total_executions']}")
print(f"Success rate: {stats['successful'] / stats['total_executions']}")

# Retrieve single execution
record = history_store.get_execution("exec_abc123")
```

---

## Usage Examples

### Example 1: Track Success Rate

```bash
# Get stats
curl http://localhost:8000/api/history/stats

# Response:
{
  "total_executions": 100,
  "successful": 92,
  "failed": 8,
  "tools_used": ["http", "reasoning", "memory"],
  "avg_duration_ms": 2340,
  "intents": {
    "tool_required": 60,
    "reasoning_only": 30,
    "mixed": 10
  }
}

# Success rate = 92/100 = 92%
```

### Example 2: Find Failed Executions

```bash
# List failed executions
curl "http://localhost:8000/api/history?status=failed&limit=10"

# Response shows recent failures:
{
  "executions": [
    {
      "execution_id": "exec_xyz789",
      "goal": "Fetch non-existent API...",
      "status": "failed",
      "timestamp": "2026-03-06T09:15:00",
      "duration_ms": 1200
    }
  ],
  "total_count": 8
}

# Get full details of failed execution
curl http://localhost:8000/api/history/exec_xyz789
```

### Example 3: Audit Trail for Specific Goal

```bash
# List all executions (filter by goal in post-processing)
curl "http://localhost:8000/api/history?limit=100"

# Find all with goal containing "GitHub"
# Extract execution_id for each match
# Retrieve full details with /api/history/{id}

# Use in frontend: filter by goal text, sort by timestamp
```

---

## Testing

### Storage Tests (13 tests)

```bash
pytest tests/test_execution_history.py -v
```

Tests cover:
- ✅ Save and retrieve records
- ✅ List with most recent first
- ✅ Pagination (limit/offset)
- ✅ Filtering by intent and status
- ✅ Statistics generation
- ✅ Cleanup old records
- ✅ Schema validation
- ✅ Empty state handling

### All Tests Pass

```
33 passed (agentic + grounding + history)
```

---

## Performance & Scalability

### Current Approach (JSON JSONL)

**Pros**:
- ✅ Simple, no dependencies
- ✅ Human-readable
- ✅ Easy to inspect/debug
- ✅ Append-only = fast writes
- ✅ Portable

**Limits**:
- ~100k records before noticeable slowdown
- Filtering is O(n) - read entire file
- Not suitable for 10M+ records

### Future Optimization

When needed (>100k records):
1. **SQLite**: Built-in, no external deps
2. **Parquet**: Columnar compression
3. **ElasticSearch**: Full-text search

Current implementation supports future migration:
- Clean storage interface
- Swappable backends
- No tight coupling to JSONL

---

## Architecture Decisions

### Why JSON JSONL?

1. **No External Dependencies**: Works out-of-box
2. **Lightweight**: ~1KB per record
3. **Portable**: Easy to inspect, backup, archive
4. **Append-Only**: O(1) writes
5. **Standard Format**: Easy integration with other tools

### Why Append Instead of Overwrite?

- Concurrent access safety
- No data loss on corruption
- Natural audit trail (chronological)
- Simple cleanup (remove old lines)

### Why Exclude Large Payloads?

- Keep records lean (1-5KB vs 100KB+ per record)
- Faster retrieval
- Easier pagination
- Focus on what matters (steps, result, metadata)

---

## Error Handling

### History Failures Don't Break Execution

```python
try:
    history_store.save_execution(record)
except Exception as e:
    # Log but don't raise
    logger.error(f"Failed to save to history: {str(e)}")
    # Execution continues normally
```

**Rationale**: History is ancillary. Core execution must never fail due to history problems.

---

## Future Enhancements

### Phase 2 (Optional)

1. **Retention Policies**
   - Auto-cleanup based on age or size
   - Configurable retention

2. **Search Features**
   - Full-text search on goals
   - Regex pattern matching
   - Time range filtering

3. **Export/Reporting**
   - CSV export
   - JSON export
   - HTML reports

4. **Analytics Dashboard**
   - Success trends
   - Tool usage patterns
   - Performance metrics

---

## Files Added/Modified

### New Files

```
app/storage/
  ├── __init__.py (new)
  └── execution_history.py (new)

app/schemas/
  └── history.py (new)

tests/
  └── test_execution_history.py (new - 13 tests)
```

### Modified Files

```
app/agents/runner.py
  └── Added _save_execution_to_history() method
  └── Added history store integration

app/api/routes.py
  └── Added /api/history endpoints
  └── Added /api/history/{id} endpoint
  └── Added /api/history/stats endpoint
```

---

## Summary

**What was added**:
- ✅ JSON-based persistent history storage
- ✅ Query and filtering capabilities
- ✅ Automatic integration with runner
- ✅ 3 new API endpoints
- ✅ 13 comprehensive tests
- ✅ Clean, minimal implementation

**No breaking changes**:
- ✅ Core agentic system untouched
- ✅ All existing tests still pass (33/33)
- ✅ Pure extension, no architecture changes

**Production ready**:
- ✅ Error handling
- ✅ Data hygiene
- ✅ Typed schemas
- ✅ Well-tested
- ✅ Documented
