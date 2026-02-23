# Agentic AI System

**A production-grade autonomous agent system** that accepts high-level goals, plans concrete execution steps, and autonomously runs them using a modular tool system.

## What Makes This "Agentic AI" (Not a Chatbot)

| Aspect | Chatbot | Agentic AI |
|--------|---------|-----------|
| **Interaction** | Chat-first, reactive | Goal-driven, autonomous |
| **Execution** | Returns text | Executes steps with tools |
| **Memory** | Stateless turns | Persistent execution context |
| **Planning** | Ad-hoc responses | Structured step decomposition |
| **Auditing** | Hard to trace | Complete step-by-step audit trail |
| **Reliability** | Single-shot | Retry logic, error handling |

This system **plans before executing**, **tracks every step**, and **provides full auditability** — making it suitable for production use cases like data processing, API orchestration, and autonomous workflows.

---

## Quick Start (2 Minutes)

### 1. Backend Setup

```bash
# Create environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set LLM API key
export GROQ_API_KEY=your_groq_api_key

# Start server
uvicorn app.main:app --reload --port 8000
```

API available at: http://localhost:8000/docs

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend available at: http://localhost:5173

### 3. Run Your First Goal

```bash
curl -X POST http://localhost:8000/api/execute \
  -H "Content-Type: application/json" \
  -d '{
    "goal": "What is an API? Find a definition and store it",
    "context": {}
  }'
```

Or use the frontend UI: visit http://localhost:5173 and submit a goal.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│              Frontend (React + TypeScript)          │
│     - Goal Input Form                               │
│     - Real-time Execution Viewer                    │
│     - Results Panel with Step Details               │
└────────────────────┬────────────────────────────────┘
                     │ HTTP
                     ▼
┌─────────────────────────────────────────────────────┐
│         FastAPI Routes (/api/execute)               │
│     - Request validation (Pydantic)                 │
│     - Response formatting                           │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
        ┌────────────────────────────┐
        │   AgentRunner Orchestrator  │
        │   (Planning + Execution)    │
        └────────┬──────────┬─────────┘
                 │          │
        ┌────────▼─┐  ┌────▼──────┐
        │ Planner  │  │ Executor  │
        │ (LLM)    │  │ (Tools)   │
        └────────┬─┘  └────┬──────┘
                 │         │
                 └────┬────┘
                      ▼
        ┌────────────────────────────┐
        │   Tool System (Extensible) │
        │  ├─ HTTP Tool              │
        │  ├─ Memory Tool            │
        │  └─ [Add custom tools]     │
        └────────┬──────────────────┘
                 │
                 ▼
        ┌────────────────────────────┐
        │  Execution Context Store   │
        │  (In-memory, v1)           │
        │  [Upgradeable to VectorDB] │
        └────────────────────────────┘
```

---

## How It Works: The Execution Flow

### Phase 1: Planning (LLM)
1. User submits: `"What is an API?"`
2. **PlannerAgent** asks LLM: *"Break this into steps using these tools: [http, memory]"*
3. LLM returns structured plan:
   ```json
   [
     {"step_number": 1, "tool": "http", "input": {"url": "...", "method": "GET"}},
     {"step_number": 2, "tool": "memory", "input": {"action": "store", "key": "api_def", "value": "..."}}
   ]
   ```

### Phase 2: Execution (Tools)
1. **ExecutorAgent** processes each step sequentially
2. Step 1: Calls HTTP tool → fetches page
3. Step 2: Calls Memory tool → stores result
4. On failure: Retries (up to 3 attempts) before stopping
5. Records every step: input, output, success/failure, error

### Phase 3: Response
- Returns complete execution record with all steps
- Frontend displays:
  - Which tool ran
  - What inputs it received
  - What it returned
  - Any errors encountered
  - Retry attempts

---

## Project Structure

```
agentic-ai-system/
├── README.md                          # This file
├── requirements.txt                   # Python dependencies
│
├── app/                               # Backend (Python)
│   ├── main.py                       # FastAPI entrypoint
│   ├── core/
│   │   ├── config.py                 # Environment settings
│   │   └── logging.py                # Logger setup
│   ├── agents/
│   │   ├── planner.py                # Goal → Steps (LLM)
│   │   ├── executor.py               # Execute steps with tools
│   │   └── runner.py                 # Orchestrator
│   ├── tools/
│   │   ├── base.py                   # BaseTool interface
│   │   ├── http_tool.py              # HTTP/API calls
│   │   ├── memory_tool.py            # State management
│   │   └── __init__.py               # Tool registry
│   ├── llm/
│   │   └── groq_client.py            # LLM integration (Groq + OpenAI)
│   ├── schemas/
│   │   └── request_response.py       # Pydantic models (validation)
│   ├── memory/
│   │   ├── schemas.py                # Data structures
│   │   └── vector_store.py           # Execution storage
│   └── api/
│       └── routes.py                 # FastAPI endpoints
│
└── frontend/                          # Frontend (React + TypeScript)
    ├── src/
    │   ├── App.tsx                   # Main component (state machine)
    │   ├── types/
    │   │   └── api.ts                # Type definitions
    │   ├── services/
    │   │   └── apiClient.ts          # Backend communication
    │   ├── pages/
    │   │   ├── GoalInputPage.tsx     # Goal submission form
    │   │   └── ExecutionViewerPage.tsx # Step-by-step display
    │   ├── components/
    │   │   └── ResultPanel.tsx       # Final results display
    │   └── index.css                 # Styling
    └── vite.config.ts                # Build config
```

---

## Configuration

### Environment Variables

**Required (choose one):**
```bash
# Groq (recommended for demos)
export LLM_PROVIDER=groq
export GROQ_API_KEY=your_key_here
export GROQ_MODEL=llama-3.1-70b-versatile

# OR OpenAI-compatible
export LLM_PROVIDER=openai
export OPENAI_API_KEY=your_key_here
```

**Optional:**
```bash
export LOG_LEVEL=INFO              # DEBUG, INFO, WARNING, ERROR
export MAX_REASONING_STEPS=10      # Max planning steps
export MAX_RETRIES=3               # Retries per failed step
```

---

## API Reference

### POST /api/execute

Execute a goal end-to-end with planning and execution.

**Request:**
```json
{
  "goal": "Your high-level goal here",
  "context": {
    "optional_param": "value"
  }
}
```

**Response:**
```json
{
  "execution_id": "550e8400-e29b-41d4-a716-446655440000",
  "goal": "What is an API?",
  "status": "completed",
  "steps_completed": [
    {
      "step_number": 1,
      "tool_name": "http",
      "success": true,
      "input": {
        "method": "GET",
        "url": "https://...",
        "timeout": 10
      },
      "output": { "status_code": 200, "body": "..." },
      "error": null
    }
  ],
  "final_result": "An API is...",
  "error": null,
  "timestamp": "2026-02-23T14:34:07.123Z"
}
```

---

## Adding Custom Tools

### 1. Create Tool Class

```python
# app/tools/my_tool.py
from pydantic import BaseModel, Field
from app.tools.base import BaseTool, ToolOutput

class MyToolInput(BaseModel):
    """Input schema for validation."""
    param1: str = Field(..., description="First parameter")
    param2: int = Field(default=10, description="Second parameter")

class MyTool(BaseTool):
    """Your custom tool implementation."""
    
    @property
    def name(self) -> str:
        return "my_tool"
    
    @property
    def description(self) -> str:
        return "What this tool does"
    
    @property
    def input_schema(self) -> type[BaseModel]:
        return MyToolInput
    
    def execute(self, **kwargs) -> ToolOutput:
        input_data = MyToolInput(**kwargs)
        try:
            result = do_work(input_data.param1, input_data.param2)
            return ToolOutput(success=True, result=result)
        except Exception as e:
            return ToolOutput(success=False, error=str(e))
```

### 2. Register in Tool Registry

```python
# app/tools/__init__.py
from app.tools.my_tool import MyTool

def initialize_tools() -> ToolRegistry:
    # ... existing registrations ...
    if "my_tool" not in tool_registry:
        tool_registry.register(MyTool())
    return tool_registry
```

### 3. Use It

The planner will now see `my_tool` and can schedule its execution.

---

## Example Workflows

### Example 1: Fetch and Store Data

**Goal:** "Fetch GitHub repo info for python/cpython and store it"

**Execution:**
```
Step 1: HTTP GET https://api.github.com/repos/python/cpython
        → Returns repo metadata
Step 2: Memory STORE key=repo value={...}
        → Stores result for later use
```

### Example 2: Multi-Step Processing

**Goal:** "Get today's date, convert to timestamp, store both"

**Execution:**
```
Step 1: HTTP GET https://worldtimeapi.org/api/timezone/etc/utc
        → Returns date/time
Step 2: Memory STORE key=current_date value={...}
Step 3: Memory STORE key=timestamp value={...}
```

---

## Testing

### Run Architecture Tests

```bash
python tests/test_agents.py
```

### Run Full Suite

```bash
pytest tests/
```

### Manual Testing

```bash
# Health check
curl http://localhost:8000/health

# Execute a goal
curl -X POST http://localhost:8000/api/execute \
  -H "Content-Type: application/json" \
  -d '{"goal":"What is SQL?"}'
```

---

## Key Design Decisions

### 1. Sequential Execution
- Steps run in order, not parallel
- Simpler state management
- Better for dependency tracking
- Easier to debug

### 2. Tool-Based (Not Code-Generating)
- Agents use tools, don't write code
- Clear security boundary
- Auditable execution
- Easy to add new capabilities

### 3. In-Memory Storage (v1)
- No external dependencies
- Fast for development
- Upgradeable to VectorDB in v2
- Clean interface for migration

### 4. Structured Audit Trail
- Every step recorded: input, output, error
- Complete execution history
- Retry attempts tracked
- Perfect for debugging and compliance

### 5. Frontend Observability
- Real-time step display
- Clear error messages
- Input/output inspection
- Execution timing

---

## Limitations & Future Work

### Current Scope (Phase 1: ✓ Complete)
- ✓ Goal planning with LLM
- ✓ Sequential tool execution
- ✓ Memory management
- ✓ HTTP/API tool
- ✓ Frontend UI

### Phase 2 (Future)
- Parallel step execution
- Complex goal decomposition
- Tool chaining optimization
- Improved error recovery

### Phase 3 (Future)
- Vector database integration (Chroma, Weaviate)
- Semantic memory search
- Long-term context retention

### Phase 4 (Future)
- Multi-agent collaboration
- Agent-to-agent communication
- Distributed execution

### Out of Scope
- Browser automation (Selenium, Playwright)
- Code generation/execution
- Docker/K8s container management
- CI/CD orchestration (use dedicated tools)

---

## Troubleshooting

### "API_KEY is required"
```bash
export GROQ_API_KEY=your_api_key
```

### "Tool 'X' not found"
Check tool is registered in `app/tools/__init__.py`

### "Could not parse JSON from LLM"
Refine the planner prompt or check LLM output format

### Frontend shows blank screen
- Check backend is running: `curl http://localhost:8000/health`
- Check browser console for errors
- Verify CORS is working

### "Connection refused" errors
- Backend: Run `uvicorn app.main:app --reload --port 8000`
- Frontend: Run `npm run dev`
- Check ports 8000 and 5173 are free

---

## Performance & Scalability

- **Single execution:** ~2-5 seconds (LLM planning + tool execution)
- **In-memory storage:** ~10GB for ~100k executions
- **Recommended upgrade:** Vector DB (Weaviate, Chroma) for production
- **Parallel scaling:** Run multiple instances with shared database

---

## Code Quality

- **TypeScript:** Strict mode enabled (`noImplicitAny`, etc.)
- **Python:** Type hints on all functions
- **Testing:** Unit tests for agents and tools
- **Logging:** Structured logging (DEBUG → ERROR levels)
- **Documentation:** Inline comments on complex logic

---

## Contributing

When adding features:
1. Maintain backward-compatible API contracts
2. Write tests for new components
3. Update documentation
4. Follow existing code style
5. Avoid external dependencies in Phase 1

---

## License

[To be determined]

---

## Questions?

See the architecture overview above or check individual module docstrings for detailed explanations.

