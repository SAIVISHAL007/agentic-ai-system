# Agentic AI System

A production-style agentic AI system built with Python 3.11 and FastAPI. This system accepts high-level goals, autonomously plans and executes steps using available tools, and returns structured results.

## Architecture Overview

The system is built on a clean, modular architecture:

```
┌─────────────────────────────────────────┐
│         FastAPI Routes & API            │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────┬──────────────────┐
│  PlannerAgent       │  ExecutorAgent   │
│  (Goal → Steps)     │  (Execute Steps) │
└─────────────────────┴──────────────────┘
             │
             ▼
┌──────────────────────────────────────────┐
│        Tool System (Extensible)          │
│  ├─ HTTP Tool (API calls)               │
│  ├─ Memory Tool (State management)      │
│  └─ [Future tools...]                   │
└──────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────┐
│    In-Memory Execution Store            │
│    (Upgradeable to Vector DB)           │
└──────────────────────────────────────────┘
```

## Phase 1: Core Components ✓

### ✓ Agent Architecture
- **PlannerAgent**: Converts goals into ordered steps
- **ExecutorAgent**: Executes steps sequentially using tools
- **AgentRunner**: Orchestrates planning + execution

### ✓ Tool System
- **BaseTool Interface**: Extensible base for all tools
- **HTTPTool**: Call external APIs and services
- **MemoryTool**: Store and retrieve intermediate state
- **ToolRegistry**: Manage available tools

### ✓ Memory System
- **ExecutionContext**: Track goal, steps, and results
- **In-Memory Store**: Phase 1 storage (upgradeable to vector DB)
- **ExecutionHistory**: Complete audit trail of all steps

### ✓ Backend
- **FastAPI**: Clean API layer
- **Pydantic Schemas**: Request/response validation
- **Config Management**: Environment-based configuration

### ✓ LLM Integration
- **GroqClient**: Integration with Groq API
- **OpenAIClient**: OpenAI and compatible APIs
- **JSON Parsing**: Reliable extraction from LLM responses

## Setup

### Prerequisites
- Python 3.11+
- pip or uv package manager

### Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Set environment variables:

```bash
# Required: Choose one LLM provider
export LLM_PROVIDER=groq
export GROQ_API_KEY=your_groq_api_key
# OR
export LLM_PROVIDER=openai
export OPENAI_API_KEY=your_openai_api_key

# Optional: Additional settings
export GROQ_MODEL=mixtral-8x7b-32768
export LOG_LEVEL=INFO
export MAX_REASONING_STEPS=10
export MAX_RETRIES=3
```

## Running the System

### Start the API Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

- **Docs**: http://localhost:8000/docs (Swagger UI)
- **Health**: http://localhost:8000/health

### Execute a Goal

**HTTP Request:**

```bash
curl -X POST http://localhost:8000/api/execute \
  -H "Content-Type: application/json" \
  -d {
    "goal": "Fetch data from the public GitHub API for the python/cpython repository",
    "context": {
      "owner": "python",
      "repo": "cpython"
    }
  }
```

**Python Client Example:**

```python
import requests

response = requests.post(
    "http://localhost:8000/api/execute",
    json={
        "goal": "Fetch GitHub repository information for python/cpython",
        "context": {
            "owner": "python",
            "repo": "cpython"
        }
    }
)

result = response.json()
print(f"Status: {result['status']}")
print(f"Final Result: {result['final_result']}")
```

## Testing

### Run Architecture Tests

```bash
python test_architecture.py
```

This validates:
- ✓ Module imports
- ✓ Tool registry
- ✓ Memory system
- ✓ Tool execution

### Run Tests Suite

```bash
pytest tests/
```

## Project Structure

```
app/
├── core/              # Configuration, logging
│   ├── config.py      # Environment settings
│   └── logging.py     # Logger setup
├── llm/               # LLM integrations
│   └── groq_client.py # Groq and OpenAI clients
├── tools/             # Tool system
│   ├── base.py        # BaseTool interface
│   ├── http_tool.py   # HTTP/API tool
│   ├── memory_tool.py # Memory tool
│   └── __init__.py    # Tool registry
├── agents/            # Agent implementations
│   ├── planner.py     # Planning agent
│   ├── executor.py    # Execution agent
│   └── runner.py      # Orchestrator
├── memory/            # Execution state
│   ├── schemas.py     # Data models
│   └── vector_store.py # Memory store
├── schemas/           # API schemas
│   └── request_response.py # Pydantic models
├── api/               # FastAPI routes
│   └── routes.py      # API endpoints
└── main.py            # Application entry point
```

## How It Works

### 1. Planning Phase
- User provides a high-level goal
- **PlannerAgent** calls LLM with:
  - Goal description
  - List of available tools
  - Instructions to break down into steps
- LLM returns ordered ExecutionStep objects
- Each step specifies: tool_name, input_data, and reasoning

### 2. Execution Phase
- **ExecutorAgent** iterates through steps
- For each step:
  1. Loads the specified tool from registry
  2. Calls tool.execute() with step input_data
  3. Records result in ExecutionContext
  4. Stores intermediate output for next steps
  5. Retries on failure (up to max_retries)
- On success: continues to next step
- On failure: stops and reports error

### 3. Result Storage
- Complete execution history in ExecutionContext
- Intermediate outputs available for inspection
- Can be queried by execution_id

## Extending: Adding a New Tool

### Step 1: Create Tool Class

```python
# app/tools/my_tool.py
from pydantic import BaseModel
from app.tools.base import BaseTool, ToolOutput

class MyToolInput(BaseModel):
    param1: str
    param2: int = 10

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
The planner will now see `my_tool` in available tools and can schedule its execution.

## Key Design Decisions

### 1. In-Memory Storage (Phase 1)
- Simple, no external dependencies
- Fast for development and testing
- Upgradeable to vector DB or persistent storage later
- Interface doesn't change during upgrade

### 2. Sequential Execution
- Steps execute in order
- Simpler than parallel execution
- Better for dependency management
- Can be upgraded to parallel in future phases

### 3. Tool-Based Architecture
- Agents don't write code; they use tools
- Clear separation of concerns
- Easy to audit execution flow
- Simple to add new capabilities

### 4. Structured Memory
- ExecutionContext tracks everything
- Every step recorded with input/output
- Retry logic at executor level
- Easy debugging and auditing

## Limitations & Future Work

### Phase 2 (NOT YET): Advanced Planning
- Multi-goal decomposition
- Tool chaining optimization
- Error recovery strategies

### Phase 3 (NOT YET): Memory Upgrades
- Vector database integration (Chroma, Weaviate)
- Embeddings for semantic search
- Long-term context retention

### Phase 4 (NOT YET): Multi-Agent Collaboration
- Agent-to-agent communication
- Task delegation
- Distributed execution

### Out of Scope (Phase 1+)
- Frontend UI
- Workflow orchestration platforms
- Browser automation
- Docker/K8s deployment

## API Reference

### POST /api/execute

Execute a goal end-to-end.

**Request:**
```json
{
  "goal": "string - high-level goal",
  "context": {
    "key": "value - optional parameters"
  }
}
```

**Response:**
```json
{
  "execution_id": "uuid",
  "goal": "string",
  "status": "completed|failed|partial",
  "steps_completed": [
    {
      "step_number": 1,
      "tool_name": "string",
      "success": true,
      "output": {},
      "error": null
    }
  ],
  "final_result": {},
  "error": null,
  "timestamp": "2026-02-22T..."
}
```

## Troubleshooting

### "GROQ_API_KEY is required"
Set environment variable: `export GROQ_API_KEY=your_key`

### "Tool 'X' not found"
Check that tool is registered via `ToolRegistry`

### "Could not parse JSON from LLM response"
Refine the planning prompt for more consistent JSON output

### LLM API Errors
Check API key validity and rate limits

## Contributing

When adding features:
1. Maintain backward compatibility
2. Keep code readable (junior developer friendly)
3. Add tests for new components
4. Update documentation
5. Avoid external dependencies for Phase 1

## License

[TBD]
