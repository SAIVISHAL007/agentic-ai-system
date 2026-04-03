# Agentic AI Execution System

A production-style agentic execution system that takes a high-level goal, plans tool-usable steps, executes them, and returns a full step-by-step audit trail.

Built with Python 3.11, FastAPI, React, and TypeScript.

## What This Project Is

This project is an execution-oriented agent backend and observability UI, not a chat interface.

Flow:

1. User submits a goal.
2. Planner generates ordered execution steps.
3. Validator checks and repairs tool input against schema.
4. Executor runs tools step-by-step.
5. API returns structured final result plus full trace.

## What It Can Do Today

- Plan and execute multi-step tasks using registered tools.
- Validate and auto-repair planned tool inputs before execution.
- Enforce schema validation in executor (invalid input is blocked).
- Call live external APIs through `http` tool.
- Store and retrieve intermediate values through `memory` tool.
- Use `reasoning` tool for non-live explanatory tasks.
- Persist execution history via pluggable backend (`jsonl` or `sqlite`).
- Show execution timeline and history in frontend dashboard.
- Stream planning/execution progress events from backend to frontend.
- Run a concrete business workflow endpoint for GitHub repository insights.

## Why This Is More Than "LLM + Wrapper"

This repository enforces clear boundaries:

- Planning: [app/agents/planner.py](app/agents/planner.py)
- Validation/repair: [app/agents/validator.py](app/agents/validator.py)
- Execution: [app/agents/executor.py](app/agents/executor.py)
- Tool contracts/registry: [app/tools/base.py](app/tools/base.py)
- API orchestration: [app/agents/runner.py](app/agents/runner.py)

Hard checks in the flow:

- Planner output is parsed into typed execution steps.
- Tool inputs are validated and repaired before executor receives them.
- Executor validates input schema again before running tool logic.
- Failures are surfaced as structured execution failures, not hidden text.
- Every step is recorded with input, output, success, and error fields.

## Architecture

```text
Goal Input (Frontend)
    -> POST /api/execute
FastAPI Router
    -> AgentRunner
       -> PlannerAgent
       -> ToolInputValidator
       -> ExecutorAgent
          -> ToolRegistry
             -> http
             -> memory
             -> reasoning
       -> ExecutionContext + FinalResult
       -> ExecutionHistoryStore (JSONL)
Response
    -> Execution timeline + result in frontend
```

## Concrete End-to-End Demo (Real)

Use case: fetch GitHub repository metadata, then summarize.

Example request:

```json
{
  "goal": "Fetch details for github.com/python/cpython and summarize key metrics",
  "context": {
    "owner": "python",
    "repo": "cpython"
  }
}
```

Typical planned steps (shape):

```json
[
  {
    "step_number": 1,
    "description": "Fetch repository metadata via API",
    "tool_name": "http",
    "input_data": {
      "method": "GET",
      "url": "https://api.github.com/repos/python/cpython"
    }
  },
  {
    "step_number": 2,
    "description": "Summarize fetched repository data",
    "tool_name": "reasoning",
    "input_data": {
      "question": "Summarize the repository metrics",
      "context": "...tool output..."
    }
  }
]
```

What is returned:

- step-by-step `steps_completed`
- per-step success/failure
- final structured result (`success`, `content`, `source`, `confidence`, `execution_id`)
- summary metrics (`tools_used`, `duration_ms`, failures)

## Current API Endpoints

Core execution:

- `POST /api/execute`
- `POST /api/execute/stream` (SSE lifecycle events)
- `POST /api/workflows/github-repo-insights`
- `GET /health`
- `GET /`

History endpoints:

- `GET /api/history`
- `GET /api/history/{execution_id}`
- `GET /api/history/stats`

Implementation reference: [app/api/routes.py](app/api/routes.py)

## Response Shape (Current)

`POST /api/execute` returns:

```json
{
  "execution_id": "uuid",
  "goal": "string",
  "status": "completed|failed|partial",
  "intent": "reasoning_only|tool_required|mixed",
  "decision_rationale": "string|null",
  "steps_completed": [
    {
      "step_number": 1,
      "description": "string",
      "tool_name": "http|memory|reasoning",
      "success": true,
      "input": {},
      "output": {},
      "error": null
    }
  ],
  "final_result": {
    "success": true,
    "content": "string|null",
    "source": "string",
    "confidence": 0.95,
    "error": null,
    "execution_id": "uuid"
  },
  "execution_summary": {
    "tools_used": ["http", "reasoning"],
    "tool_failures": 0,
    "reasoning_steps": 1,
    "duration_ms": 1800
  },
  "error": null,
  "timestamp": "ISO-8601"
}
```

Schemas: [app/schemas/request_response.py](app/schemas/request_response.py)

## Frontend (Observability Dashboard)

Frontend provides:

- Goal input page
- Execution timeline with step cards
- Result panel
- History list, filters, statistics, and detail view

Relevant files:

- [frontend/src/pages/GoalInputPage.tsx](frontend/src/pages/GoalInputPage.tsx)
- [frontend/src/pages/ExecutionViewerPage.tsx](frontend/src/pages/ExecutionViewerPage.tsx)
- [frontend/src/components/ResultPanel.tsx](frontend/src/components/ResultPanel.tsx)
- [frontend/src/pages/HistoryPage.tsx](frontend/src/pages/HistoryPage.tsx)

Important honesty note:

- The UI now consumes SSE progress events from `/api/execute/stream`.
- WebSocket transport is not implemented yet (SSE is currently used).

## Tools (Current)

- `http`: external HTTP requests ([app/tools/http_tool.py](app/tools/http_tool.py))
- `memory`: temporary key-value storage ([app/tools/memory_tool.py](app/tools/memory_tool.py))
- `reasoning`: LLM reasoning/explanation ([app/tools/reasoning_tool.py](app/tools/reasoning_tool.py))

Tool registry and contracts: [app/tools/base.py](app/tools/base.py), [app/tools/__init__.py](app/tools/__init__.py)

## Honest Scope and Limitations

Current limitations (intentional for this phase):

- Auth/rate limit are optional and disabled by default.
- No multi-tenant isolation.
- No distributed task queue.
- No browser automation tool.
- No filesystem tool.
- No long-term semantic memory/vector DB yet.
- History persistence is JSONL, not enterprise database.

This is a strong production-style architecture and a real working system, but not a fully production-hardened platform yet.

## Optional Security Controls

These controls are implemented and can be enabled without code changes:

- `API_AUTH_ENABLED=true` enables API key auth for `/api/*` routes.
- `API_AUTH_TOKEN=<token>` expected via `X-API-Key` header.
- `RATE_LIMIT_ENABLED=true` enables in-memory IP rate limiting.
- `RATE_LIMIT_REQUESTS_PER_MINUTE=60` sets request quota.
- `REQUIRE_TENANT_HEADER=true` requires `X-Tenant-ID` on `/api/*` routes.
- `HISTORY_BACKEND=sqlite` enables sqlite persistence.
- `HISTORY_SQLITE_PATH=./.execution_history/executions.db` configures sqlite file location.

Defaults keep current behavior unchanged, preserving existing local performance and developer workflow.

## Quick Start

### Backend

```bash
git clone https://github.com/SAIVISHAL007/agentic-ai-system
cd agentic-ai-system

python -m venv venv
source venv/bin/activate

pip install -r requirements.txt

echo "GROQ_API_KEY=your_api_key_here" > .env
echo "LLM_PROVIDER=groq" >> .env
echo "GROQ_MODEL=llama-3.3-70b-versatile" >> .env

uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Recommended Resume Pitch (Accurate)

"Built an agentic execution system with strict planner-validator-executor separation, typed tool contracts, schema-aware plan repair, execution audit trail, and observability dashboard with persistent history endpoints."

## Suggested Next Improvements

1. Add PostgreSQL persistence option for execution history.
2. Add tenant-aware RBAC authorization layer (beyond API key).
3. Add OpenTelemetry traces and metrics dashboards.
4. Add more domain workflows (finance, support ops, DevOps automation).
5. Extend CI with load-testing and security scans.

Current CI pipeline is available at `.github/workflows/ci.yml` and runs backend tests plus frontend lint/build.
