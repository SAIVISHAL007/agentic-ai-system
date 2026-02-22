# Quick Start Guide

## Installation

### 1. Clone and Setup Environment

```bash
cd /workspaces/agentic-ai-system
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure LLM Provider

Choose ONE of the following:

#### Option A: Groq (Recommended)
```bash
export LLM_PROVIDER=groq
export GROQ_API_KEY=your_groq_api_key_here
export GROQ_MODEL=mixtral-8x7b-32768  # Optional, this is default
```

Get API key: https://console.groq.com

#### Option B: OpenAI
```bash
export LLM_PROVIDER=openai
export OPENAI_API_KEY=your_openai_api_key_here
export OPENAI_MODEL=gpt-4-turbo  # Optional
```

#### Option C: OpenAI-Compatible (Local/Custom)
```bash
export LLM_PROVIDER=openai
export OPENAI_API_KEY=anything
export OPENAI_BASE_URL=http://localhost:8001/v1  # Your local API
export OPENAI_MODEL=local-model
```

### 3. Optional Configuration
```bash
export LOG_LEVEL=INFO          # DEBUG | INFO | WARNING | ERROR
export MAX_REASONING_STEPS=10  # Max steps planner can create
export MAX_RETRIES=3           # Retries per failed step
```

## Running

### Option 1: Run Demo (No API Key Needed!)
```bash
python demo.py
```
Shows the complete system working with a mock LLM.

### Option 2: Run Examples
```bash
python examples.py
```
Four detailed examples of system capabilities.

### Option 3: Run Tests
```bash
python test_architecture.py
```
Validates all components work correctly.

### Option 4: Start API Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Then visit: http://localhost:8000/docs

## Using the API

### Example 1: Execute a Goal (via curl)

```bash
curl -X POST http://localhost:8000/api/execute \
  -H "Content-Type: application/json" \
  -d '{
    "goal": "Retrieve information about the Python repository from GitHub",
    "context": {
      "owner": "python",
      "repo": "cpython",
      "details": "stars, forks, language"
    }
  }'
```

### Example 2: Execute a Goal (via Python)

```python
import requests

response = requests.post(
    "http://localhost:8000/api/execute",
    json={
        "goal": "Fetch data from GitHub API for python/cpython",
        "context": {
            "owner": "python",
            "repo": "cpython"
        }
    }
)

result = response.json()
print(f"Execution ID: {result['execution_id']}")
print(f"Status: {result['status']}")
print(f"Steps: {len(result['steps_completed'])}")
print(f"Result: {result['final_result']}")
```

### Example 3: Query API Documentation
```bash
curl http://localhost:8000/docs
```
Visit this URL in your browser for interactive API testing.

### Example 4: Health Check
```bash
curl http://localhost:8000/health
```

## How It Works

### The Flow

```
1. User provides goal
   ↓
2. PlannerAgent (with LLM)
   - Breaks goal into ordered steps
   - Each step specifies: tool_name, input_data
   ↓
3. ExecutorAgent
   - For each step:
     a. Gets tool from registry
     b. Calls tool.execute()
     c. Records result and output
     d. Retries on failure
   ↓
4. ExecutionContext
   - Stores complete execution history
   - Tracks all steps and results
   - Returns final result to user
```

### Available Tools

#### HTTPTool
Make requests to external APIs.

```python
{
  "tool_name": "http",
  "input_data": {
    "method": "GET",
    "url": "https://api.github.com/repos/python/cpython",
    "headers": {"Authorization": "token xxx"},
    "timeout": 30
  }
}
```

#### MemoryTool
Store and retrieve intermediate state.

```python
# Store
{
  "tool_name": "memory",
  "input_data": {
    "action": "store",
    "key": "github_data",
    "value": {"stars": 54000, "forks": 24000}
  }
}

# Retrieve
{
  "tool_name": "memory",
  "input_data": {
    "action": "retrieve",
    "key": "github_data"
  }
}
```

## Troubleshooting

### "GROQ_API_KEY is required"
```bash
export GROQ_API_KEY=your_key
export LLM_PROVIDER=groq
```

### "ImportError: groq package not installed"
```bash
pip install groq
```

### "LLM call failed: Failed to authenticate"
- Check your API key is valid
- Check rate limits
- Try a different model

### "Tool 'http' not found"
Ensure tools are initialized:
```python
from app.tools import initialize_tools
initialize_tools()
```

### Port 8000 Already In Use
```bash
uvicorn app.main:app --port 8001
```

## Next Steps

1. Run the demo: `python demo.py`
2. Start the server: `uvicorn app.main:app --reload`
3. Execute a goal from your application
4. Add custom tools to extend functionality

## Adding Custom Tools

See [README.md](README.md#extending-adding-a-new-tool) for how to create and register your own tools.

## Architecture

Complete architecture and design decisions: See [README.md](README.md)

## Support

- Check logs for detailed error messages
- Run `test_architecture.py` to validate setup
- Review [README.md](README.md) for detailed documentation
