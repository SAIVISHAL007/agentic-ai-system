# Agentic AI Execution System

**Real Problem Solved**: Safely execute multi-step AI-driven workflows without hidden failures.

Instead of delegating entire workflows to an LLM (which can fail silently or hallucinate), this system **plans steps explicitly**, **validates tool inputs before execution**, and **records every decision** so you know exactly what happened.

**Tech Stack**: Python 3.12 • FastAPI • React 18 • TypeScript • Google Gemini 3.1 Flash

**Production Design**: Strict planner → validator → executor separation with deterministic audit trails, schema-enforced tool contracts, and anti-hallucination patterns.

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
- Run concrete workflow endpoints for support-ticket triage and GitHub repository insights.

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

## Production-Ready Design Patterns

### Deterministic Model Identity (Prevents LLM Hallucination)

Problem solved in this project: model-identity questions were previously delegated to the LLM, which can answer with the wrong model name.

Current behavior: identity is served from configuration, not from LLM generation.

Implementation references:
- [app/tools/reasoning_tool.py](app/tools/reasoning_tool.py)
- [app/api/routes.py](app/api/routes.py)
- [app/core/config.py](app/core/config.py)

How to verify:

```bash
curl http://localhost:8000/api/model-info
```

Expected shape:

```json
{"provider":"gemini","model":"gemini-3.1-flash-lite-preview"}
```

### Schema-Enforced Tool Contracts (Prevents Silent Failures)

Problem solved in this project: planner output can be malformed or missing tool fields.

Current behavior:
- Planner output is validated and repaired before execution.
- Executor validates tool input schema again before running tool logic.
- Invalid input is returned as structured failure, not hidden text.

Implementation references:
- [app/agents/validator.py](app/agents/validator.py)
- [app/agents/executor.py](app/agents/executor.py)
- [app/tools/base.py](app/tools/base.py)

### Single LLM Provider (Gemini) - Intentional Consolidation

Why multi-provider support was removed in this version:
- Simpler debugging and reproducibility across environments.
- Fewer code paths and integration edge-cases to maintain.
- More stable behavior for tests and demos.

Honest tradeoff: this improves consistency, but reduces provider flexibility.

## Architecture & Design Patterns

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

## Real-World Workflow Example: Support Ticket Triage

Business problem: support teams lose time triaging repeated tickets and can miss customer context.

What this workflow does now:
- Accepts ticket details.
- Runs a multi-step triage through the planner-validator-executor flow.
- Uses in-project knowledge-base and customer-history data (demo dataset).
- Returns draft response plus full execution trace.

Implementation references:
- [app/workflows/support_ticket_triage.py](app/workflows/support_ticket_triage.py)
- [app/api/routes.py](app/api/routes.py)
- [app/schemas/workflows.py](app/schemas/workflows.py)

**Request**:
```bash
curl -X POST http://localhost:8000/api/workflows/support-ticket-triage \
  -H "Content-Type: application/json" \
  -d '{
    "ticket_id": "TKT-2024-001",
    "customer_id": "CUST-001",
    "issue_description": "I cannot log into my account with OAuth. I keep getting an error saying invalid_client"
  }'
```

**Workflow Steps (Typical)**:
1. Analyze ticket and infer likely category/severity.
2. Retrieve relevant KB snippets from the in-project dataset.
3. Pull customer context from the in-project dataset.
4. Draft a response in a support-friendly format.
5. Return execution trace (per-step success, output, and errors).

**Response Shape Includes**:
```json
{
  "ticket_id": "TKT-2024-001",
  "customer_id": "CUST-001",
  "execution_id": "uuid",
  "status": "completed",
  "steps_completed": [
    {
      "step_number": 1,
      "description": "...",
      "tool_name": "reasoning|memory|http",
      "success": true,
      "output": {}
    }
  ],
  "drafted_response": "Hi Acme Corp, your OAuth issue is commonly resolved by clearing browser cache. Here's how to do that [links]. If you still see the error, please reply with your browser version."
}
```

**Why This Matters**:
- No hidden failures (every step is recorded)
- Transparent process (you can inspect what each step did)
- Extensible (add new steps: ticket urgency alert, Slack notification, etc.)
- Recoverable (if one step fails, you know exactly which one and why)

Important scope note: this workflow currently uses local demo KB/customer datasets, not live helpdesk integrations.

## Current API Endpoints

Core execution:

- `POST /api/execute` - Execute goal with plan, validate, execute
- `POST /api/execute/stream` - Same as above with SSE lifecycle events
- `POST /api/workflows/support-ticket-triage` - **Support ticket triage and response drafting** ⭐ NEW
- `POST /api/workflows/github-repo-insights` - Fetch and summarize repository metrics
- `GET /api/model-info` - Deterministic provider/model info (no LLM call)
- `GET /health` - Health check
- `GET /` - Root

History endpoints:

- `GET /api/history` - List execution history (paginated)
- `GET /api/history/{execution_id}` - Single execution details
- `GET /api/history/stats` - History statistics

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

## Available Workflows (Templates)

The system includes composable workflow templates using the core tools:

**Included Workflows**:
- `support-ticket-triage`: Analyze tickets and draft responses using a simulated KB and customer history dataset
- `github-repo-insights`: Fetch repository data and summarize metrics

**Future Workflow Ideas**: DevOps incident response, meeting-to-task automation, research report generation, invoice processing

Workflows are built by composing the 3 core tools in different sequences. This demonstrates extensibility without changing the core orchestration engine.

## Interview Defense: Claims Mapped to Code

If asked to defend key claims during interview, use these concrete pointers:

- "How does validator repair tool input?"
  - [app/agents/validator.py](app/agents/validator.py)
- "Why validate twice?"
  - [app/agents/validator.py](app/agents/validator.py)
  - [app/agents/executor.py](app/agents/executor.py)
- "Where is deterministic model identity implemented?"
  - [app/tools/reasoning_tool.py](app/tools/reasoning_tool.py)
  - [app/api/routes.py](app/api/routes.py)
- "How are step traces persisted?"
  - [app/storage/execution_history.py](app/storage/execution_history.py)
  - [app/memory/schemas.py](app/memory/schemas.py)

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

# Create .env with Gemini API key (from https://aistudio.google.com)
echo "GEMINI_API_KEY=your_api_key_here" > .env
echo "GEMINI_MODEL=gemini-3.1-flash-lite-preview" >> .env

uvicorn app.main:app --reload --port 8000
```

Visit `http://localhost:8000` for health check, or use `/api/execute` endpoint.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:5173` (Vite dev server).

### Quick Test

```bash
# Test deterministic model-info endpoint
curl http://localhost:8000/api/model-info

# Execute a reasoning-only goal
curl -X POST http://localhost:8000/api/execute \
  -H "Content-Type: application/json" \
  -d '{"goal":"List the top 3 Python packages by download count"}' 
```

## Recommended Resume Pitch (Accurate)

> "Built a production-style agentic execution system with strict planner-validator-executor separation, Pydantic-based tool schema contracts, deterministic audit trails, and structured error handling. Implemented anti-hallucination patterns (config-based model identity), schema-aware plan repair, persistent history, and observability dashboard. Recently consolidated LLM provider to Gemini for focus and reduced complexity. All decisions defend against production failure modes: schema validation (double-checked), planning failures (deterministic), execution failures (step-level structured errors), and LLM hallucination (config-not-LLM for identity). Deployed with optional security (API auth, rate limiting, tenant isolation)."

**Concrete Evidence**:
- Multi-step planning and execution with structured audit trails
- Tool schema validation (Pydantic) enforced at planning and execution boundaries
- Deterministic model-identity answering prevents LLM hallucination
- Persistent execution history with filtering, search, and statistics
- Frontend observability dashboard with real-time progress (SSE)
- GitHub API workflow demonstrates real tool integration
- Starter framework for custom domain workflows

## Suggested Next Improvements

**Near-term (Low Risk)**:
1. Add more domain-specific workflow templates (finance, support automation, DevOps).
2. Implement telemetry: OpenTelemetry traces, metrics, and observability dashboards.
3. Add PostgreSQL persistence option for execution history (beyond JSONL/SQLite).
4. Extend CI with load testing and security scanning.

**Medium-term (Architectural)**:
1. Implement RBAC authorization layer (beyond API key auth).
2. Add multi-tenant context propagation across execution.
3. Extend tool registry: file I/O, browser automation, database connectors.

**Optional High-Value**:
1. Add Gemini model fallback logic for quota/rate-limit resilience.
2. Implement long-term semantic memory with vector DB (Chroma integration ready).

Current CI/CD pipeline: `.github/workflows/ci.yml` (backend tests, frontend lint/build, type checking)
