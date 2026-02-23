# Agentic AI Execution System

A production-grade agentic AI system that autonomously plans and executes multi-step tasks using available tools. Built with Python 3.11, FastAPI, and React.

## What is This? (Not a Chatbot!)

This is an **Agentic AI System** — not a conversational chatbot. Here's the difference:

**Traditional Chatbot (Like ChatGPT):**
- You ask → It responds
- Single-turn conversation
- No autonomous action

**Agentic AI System (This Project):**
- You give a goal → It plans steps → It executes with tools → Returns results
- Multi-step autonomous execution
- Takes actions via tools (API calls, data storage, computations)
- Full audit trail of every step

**Example:**
- ❌ Chatbot: "Tell me about Python" → Responds with text
- ✅ Agentic: "Summarize Python" → Plans a reasoning-only step when no external data is needed → Returns structured result with audit trail

Reasoning-only steps are supported but are a secondary fallback when no external tools apply.
This system never fabricates external data; if live data is required, it will attempt tool execution and fail safely when APIs are unavailable.
Every execution returns a structured final result with a clear source and confidence level.

## Architecture

```
User Goal
    ↓
┌─────────────────────────────────────────┐
│     Frontend (React + TypeScript)      │
│   - Goal Input                          │
│   - Execution Viewer (Real-time)       │
│   - Result Panel                        │
└──────────────┬──────────────────────────┘
               │ HTTP POST /api/execute
               ↓
┌─────────────────────────────────────────┐
│         FastAPI Backend                 │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│        AgentRunner (Orchestrator)       │
└──────────────┬──────────────────────────┘
               │
    ┌──────────┴──────────┐
    ↓                     ↓
┌─────────┐         ┌─────────┐
│ Planner │         │Executor │
│ Agent   │────────▶│ Agent   │
└─────────┘         └────┬────┘
   (LLM)                 │
                         ↓
              ┌──────────────────┐
              │   Tool System    │
              │ ┌──────────────┐ │
              │ │ Reasoning Tool│ │  ← Reasoning-only fallback
              │ └──────────────┘ │
              │ ┌──────────────┐ │
              │ │  HTTP Tool   │ │  ← API Calls
              │ └──────────────┘ │
              │ ┌──────────────┐ │
              │ │ Memory Tool  │ │  ← State Storage
              │ └──────────────┘ │
              └──────────────────┘
                       │
                       ↓
              ┌──────────────────┐
              │ Execution Context│
              │ (In-Memory Store)│
              └──────────────────┘
```

## Key Features

✅ **Autonomous Planning**: LLM breaks goals into executable steps  
✅ **Tool-Based Execution**: Agents use tools (not generate code)  
✅ **Full Observability**: Complete audit trail of every step  
✅ **Error Handling**: Automatic retries with intelligent fallback  
✅ **Real-Time UI**: Watch execution unfold step-by-step  
✅ **Extensible**: Add new tools without changing core logic  

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+ (for frontend)
- Groq API key (free at [console.groq.com](https://console.groq.com))

### Backend Setup

```bash
# Clone repository
git clone https://github.com/SAIVISHAL007/agentic-ai-system
cd agentic-ai-system

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
echo "GROQ_API_KEY=your_api_key_here" > .env
echo "LLM_PROVIDER=groq" >> .env
echo "GROQ_MODEL=llama-3.3-70b-versatile" >> .env

# Start backend
uvicorn app.main:app --reload --port 8000
```

Backend will be at: http://localhost:8000  
API docs at: http://localhost:8000/docs

### Frontend Setup

```bash
# In a new terminal
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

Frontend will be at: http://localhost:5173

## Example Goals

### ✅ Informational (Reasoning-Only, Fallback) Goals
```json
{"goal": "What is Python?"}
{"goal": "Explain what an API is"}
{"goal": "What is machine learning?"}
```

### ✅ API Data Fetching
```json
{
  "goal": "Fetch current Bitcoin price from CoinGecko API",
  "context": {"currency": "usd"}
}
```

### ✅ Multi-Step Workflows
```json
{
  "goal": "Get GitHub repository info for python/cpython and store the star count",
  "context": {"owner": "python", "repo": "cpython"}
}
```

### ❌ Tasks This System Cannot Do
- ❌ Browse the web (no browser automation)
- ❌ Execute arbitrary Python code (uses predefined tools only)
- ❌ Real-time data without APIs (LLM has knowledge cutoff)
- ❌ File system operations (not implemented yet)

## How It Works

### 1. Planning Phase (PlannerAgent)
- Receives your goal
- Analyzes available tools
- Calls LLM to generate ordered execution steps
- Each step specifies: `tool_name`, `input_data`, `reasoning`
- Classifies intent as `reasoning_only`, `tool_required`, or `mixed` (metadata only)

### 2. Execution Phase (ExecutorAgent)
- Executes steps sequentially
- For each step:
  - Loads tool from registry
  - Calls `tool.execute()` with step inputs
  - Records result (success/failure, output, error)
  - Retries on failure (max 3 attempts)
- Stops if any step fails after retries

### 3. Result Storage
- Complete execution history in `ExecutionContext`
- Full audit trail: inputs, outputs, errors, retries
- Accessible via execution_id
- Always resolves a consistent final output object

### 4. Frontend Display
- Real-time execution viewer
- Step-by-step progress
- Input/output inspection
- Error visualization

## Available Tools

### 1. HTTP Tool (`http`)
**Purpose**: Make HTTP requests to external APIs

**When to use:**
- Fetch data from REST APIs
- POST/PUT/DELETE to endpoints
- Web data retrieval

**Example:**
```json
{
  "tool_name": "http",
  "input_data": {
    "method": "GET",
    "url": "https://api.github.com/repos/python/cpython"
  }
}
```

### 2. Memory Tool (`memory`)
**Purpose**: Store and retrieve intermediate data during execution

**When to use:**
- Multi-step workflows requiring state
- Passing data between steps
- Temporary storage during execution

**Example (Store):**
```json
{
  "tool_name": "memory",
  "input_data": {
    "action": "store",
    "key": "user_age",
    "value": 25
  }
}
```

**Example (Retrieve):**
```json
{
  "tool_name": "memory",
  "input_data": {
    "action": "retrieve",
    "key": "user_age"
  }
}
```

### 3. Reasoning Tool (`reasoning`)
**Purpose**: Reasoning-only fallback when no external tools are applicable

**When to use (fallback only):**
- Informational questions that do not require external data
- Conceptual explanations and definitions
- No real-world actions or API calls needed

**Example:**
```json
{
  "tool_name": "reasoning",
  "input_data": {
    "question": "What is Python?"
  }
}
```

## API Reference

### POST /api/execute

Execute a goal end-to-end.

**Request:**
```json
{
  "goal": "string - high-level goal description",
  "context": {
    "optional_key": "optional_value"
  }
}
```

**Response:**
```json
{
  "execution_id": "uuid",
  "goal": "string",
  "status": "completed|failed|partial",
  "intent": "reasoning_only|tool_required|mixed",
  "steps_completed": [
    {
      "step_number": 1,
      "description": "Provide a reasoning-only explanation",
      "tool_name": "reasoning",
      "success": true,
      "input": {"question": "What is Python?"},
      "output": {
        "answer": "Python is a high-level...",
        "note": "Reasoning-only step; no external tools used"
      },
      "error": null
    }
  ],
  "final_result": {
    "content": "Python is a high-level...",
    "source": "reasoning-only",
    "confidence": "medium",
    "execution_id": "uuid"
  },
  "execution_summary": {
    "tools_used": ["reasoning"],
    "tool_failures": 0,
    "reasoning_steps": 1,
    "duration_ms": 1234
  },
  "error": null,
  "timestamp": "2026-02-23T..."
}
```

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "service": "agentic-ai-system"
}
```

## Project Structure

```
app/
├── core/               # Configuration and logging
│   ├── config.py       # Environment settings
│   └── logging.py      # Logger setup
├── llm/                # LLM integrations
│   └── groq_client.py  # Groq API client
├── tools/              # Tool system
│   ├── base.py         # BaseTool interface + registry
│   ├── reasoning_tool.py # Reasoning-only tool
│   ├── http_tool.py    # HTTP/API tool
│   └── memory_tool.py  # State storage tool
├── agents/             # Agent implementations
│   ├── planner.py      # Planning agent
│   ├── executor.py     # Execution agent
│   └── runner.py       # Orchestrator
├── memory/             # Execution state
│   ├── schemas.py      # Data models
│   └── vector_store.py # In-memory store
├── schemas/            # API schemas
│   └── request_response.py # Pydantic models
├── api/                # FastAPI routes
│   └── routes.py       # API endpoints
└── main.py             # Application entry point

frontend/
├── src/
│   ├── pages/
│   │   ├── GoalInputPage.tsx
│   │   └── ExecutionViewerPage.tsx
│   ├── components/
│   │   └── ResultPanel.tsx
│   ├── services/
│   │   └── apiClient.ts
│   ├── types/
│   │   └── api.ts
│   └── App.tsx
├── index.css           # Styles
└── vite.config.ts      # Build config
```

## Extending: Add a New Tool

### Step 1: Create Tool Class

```python
# app/tools/my_tool.py
from pydantic import BaseModel, Field
from app.tools.base import BaseTool, ToolOutput

class MyToolInput(BaseModel):
    param1: str
    param2: int = Field(default=10, description="Optional parameter")

class MyTool(BaseTool):
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
            result = do_something(input_data.param1, input_data.param2)
            return ToolOutput(success=True, result=result)
        except Exception as e:
            return ToolOutput(success=False, result=None, error=str(e))
```

### Step 2: Register Tool

```python
# In app/tools/__init__.py
from app.tools.my_tool import MyTool

def initialize_tools() -> ToolRegistry:
    # ... existing registrations ...
    if "my_tool" not in tool_registry:
        tool_registry.register(MyTool())
    return tool_registry
```

### Step 3: Use It!
The planner will automatically see `my_tool` and can schedule it in execution plans.

## Design Decisions

### Why Tool-Based (Not Code Generation)?
- **Safety**: Controlled execution environment
- **Auditability**: Every action is logged
- **Reliability**: No syntax errors or runtime failures
- **Extensibility**: Add capabilities without retraining

### Why Sequential Execution?
- **Simplicity**: Easier to debug and understand
- **Dependencies**: Natural step ordering
- **Observability**: Clear execution flow
- **Upgradeable**: Can add parallel execution later

### Why In-Memory Storage?
- **Phase 1 Focus**: No external dependencies
- **Performance**: Fast for development/testing
- **Upgradeable**: Interface supports vector DB swap
- **Simplicity**: Easy to understand and maintain

## Troubleshooting

### Backend Issues

**"GROQ_API_KEY is required"**
```bash
export GROQ_API_KEY=your_key_here
```

**"Tool 'X' not found"**
- Check tool is registered in `app/tools/__init__.py`
- Verify tool name is lowercase

**Model Errors**
- Ensure model name is current (check Groq deprecations)
- Current working model: `llama-3.3-70b-versatile`

### Frontend Issues

**"Cannot connect to backend"**
- Verify backend is running: `curl http://localhost:8000/health`
- Check Vite proxy settings in `vite.config.ts`

**TypeScript Errors**
```bash
cd frontend
npm run build  # Check for type errors
```

## Testing

### Backend
```bash
# Quick validation
curl -X POST http://localhost:8000/api/execute \
  -H "Content-Type: application/json" \
  -d '{"goal":"What is Python?"}'
```

### Frontend
```bash
cd frontend
npm run build  # Validates TypeScript types
npm run preview  # Test production build
```

### End-to-End
1. Start backend: `uvicorn app.main:app --port 8000`
2. Start frontend: `cd frontend && npm run dev`
3. Open http://localhost:5173
4. Submit goal: "What is Python?"
5. Watch execution unfold

## Performance

- **Planning**: ~2-3 seconds (LLM call)
- **Execution**: Depends on tools used
  - Reasoning tool: ~2-5 seconds
  - HTTP tool: Network latency
  - Memory tool: <100ms
- **Total**: Most goals complete in <10 seconds

## Limitations & Future Work

### Current Limitations
- No parallel execution (sequential only)
- In-memory storage (resets on restart)
- No browser automation
- No file system operations
- LLM knowledge cutoff applies

### Planned Enhancements
- Vector database integration (Chroma, Weaviate)
- Parallel execution for independent steps
- File system tool
- Browser automation tool
- Multi-agent collaboration
- Long-term memory with embeddings
- Docker deployment

## License

MIT License

## Credits

Built with:
- **Backend**: Python 3.11, FastAPI, Pydantic
- **LLM**: Groq API (llama-3.3-70b-versatile)
- **Frontend**: React 18, TypeScript, Vite
- **Styling**: Plain CSS (no frameworks)

---

**Why This Project Matters for Recruitment:**

This demonstrates:
- ✅ Clean architecture (separation of concerns)
- ✅ Production-grade error handling
- ✅ Full-stack development (Python + React + TypeScript)
- ✅ AI/LLM integration
- ✅ Real-world problem solving
- ✅ Professional documentation
- ✅ Extensible design patterns

**Not just a chatbot clone — a real agentic AI execution system!**

