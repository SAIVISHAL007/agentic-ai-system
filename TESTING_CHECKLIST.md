# 🧪 Pre-Interview Testing Checklist

**Run these tests 24 hours before your interview to ensure everything works perfectly.**

---

## ✅ Backend Validation

### 1. Start Backend Server
```bash
cd /workspaces/agentic-ai-system
source .venv/bin/activate
export LLM_PROVIDER=gemini
export GEMINI_API_KEY=<your-gemini-api-key>
python app/main.py
```

**Expected Output**:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**✅ Success**: Server starts without errors  
**❌ Failure**: If import errors → run `pip install -r requirements.txt`

---

### 2. Test API Health
```bash
curl http://localhost:8000/api/health
```

**Expected**: `{"status": "healthy"}`

---

### 3. Test Tool Selection: Reasoning-Only
```bash
curl -X POST http://localhost:8000/api/execute \
  -H "Content-Type: application/json" \
  -d '{"goal": "What is Python?"}'
```

**Expected Result**:
```json
{
  "execution_id": "...",
  "status": "completed",
  "intent": "reasoning_only",
  "final_result": {
    "content": "Python is...",
    "source": "reasoning" or "reasoning-only",
    "confidence": 0.75,
    "execution_id": "..."
  }
}
```

**✅ Success Criteria**:
- `intent` == `"reasoning_only"`
- `steps_completed` has exactly 1 step with `tool_name` == `"reasoning"`
- `final_result.confidence` is a float between 0.0-1.0
- `final_result.content` is not empty

---

### 4. Test Tool Selection: HTTP Tool (Valid GitHub URL)
```bash
curl -X POST http://localhost:8000/api/execute \
  -H "Content-Type: application/json" \
  -d '{"goal": "Fetch one machine learning repository from GitHub"}'
```

**Expected Result**:
```json
{
  "execution_id": "...",
  "status": "completed",
  "intent": "tool_required",
  "steps_completed": [
    {
      "step_number": 1,
      "tool_name": "http",
      "success": true,
      "output": {
        "status_code": 200,
        "body": {...}
      }
    }
  ],
  "final_result": {
    "content": "... repository ...",
    "source": "http",
    "confidence": 0.95,
    "execution_id": "..."
  }
}
```

**✅ Success Criteria**:
- `intent` == `"tool_required"`
- `steps_completed[0].tool_name` == `"http"`
- `steps_completed[0].input` contains GitHub URL with `?q=` parameter
- `final_result.source` == `"http"`
- `final_result.confidence` >= 0.9

**❌ Common Failure**: If HTTP step fails with 422, check that the URL includes `?q=machine-learning`

---

### 5. Test API Validation (Expect Graceful Failure)

This test should produce a clear error message (not a crash):

```bash
curl -X POST http://localhost:8000/api/execute \
  -H "Content-Type: application/json" \
  -d '{"goal": "Test GitHub validation", "context": {"test_url": "https://api.github.com/search/repositories"}}'
```

**Expected**: System should handle incomplete URLs gracefully with fallback reasoning.

---

## ✅ Frontend Validation

### 1. Start Frontend Dev Server
```bash
cd /workspaces/agentic-ai-system/frontend
npm install
npm run dev
```

**Expected Output**:
```
VITE v5.x.x  ready in xxx ms

➜  Local:   http://localhost:5173/
➜  Network: use --host to expose
```

**✅ Success**: Dev server starts, no TypeScript errors  
**❌ Failure**: If type errors → check that `api.ts` matches backend schema

---

### 2. Test Goal Input Page
1. Open `http://localhost:5173`
2. Enter goal: `"What is an API?"`
3. Click "Execute"

**Expected**:
- Loading spinner appears
- Redirects to execution viewer
- Shows 1 step (reasoning tool)
- Final output displays with:
  - Content (explanation)
  - Source: `reasoning` or `reasoning-only`
  - Confidence: percentage (e.g., 75%)

---

### 3. Test Execution Viewer (HTTP Tool)
1. Enter goal: `"Fetch a Python repository from GitHub"`
2. Click "Execute"

**Expected**:
- Shows intent: `TOOL REQUIRED`
- Shows 1+ steps
- At least one step uses `http` tool
- Step details show:
  - Input (GitHub URL with `?q=`)
  - Output (API response)
  - Success status (✓)
- Final output shows:
  - Content (repository info)
  - Source: `http`
  - Confidence: 95% (high)

---

### 4. Test Error Handling
1. Enter goal: `"Fetch from invalid API"`
2. Click "Execute"

**Expected**:
- System doesn't crash
- Shows error in execution trace
- Final output has:
  - Source: `fallback`
  - Confidence: 60% (low)
  - Content: Explanation of what failed

---

## 🎯 Quick Smoke Test (5 minutes before interview)

### Backend:
```bash
cd /workspaces/agentic-ai-system
source .venv/bin/activate
python -c "
from app.agents.runner import AgentRunner
import os
os.environ['LLM_PROVIDER'] = 'gemini'
os.environ['GEMINI_API_KEY'] = '${GEMINI_API_KEY}'
runner = AgentRunner()
ctx = runner.run('What is REST?')
assert ctx.final_result is not None
assert ctx.final_result.confidence >= 0.0
assert ctx.final_result.confidence <= 1.0
print('✅ Backend working')
"
```

### Frontend:
```bash
cd frontend
npm run build
# Should complete without errors
echo "✅ Frontend working"
```

---

## 🚨 Troubleshooting Guide

### Issue: "Import Error" when starting backend
**Fix**:
```bash
pip install -r requirements.txt
```

### Issue: HTTP tool returns 422 for GitHub
**Root Cause**: URL missing `?q=` parameter  
**Fix**: Check planner prompt emphasizes including query params

### Issue: Frontend shows "Type Error"
**Root Cause**: Frontend types don't match backend schema  
**Fix**: Verify `frontend/src/types/api.ts` matches `app/schemas/request_response.py`

### Issue: "No API key" error
**Fix**:
```bash
export LLM_PROVIDER=gemini
export GEMINI_API_KEY=<your-key>
# Or add to .env file
```

### Issue: Frontend can't connect to backend
**Fix**: Verify backend is running on `http://localhost:8000`  
Check CORS settings allow `http://localhost:5173`

---

## 📊 Expected Test Results Summary

| Test | Expected Intent | Expected Tool | Expected Confidence | Expected Status |
|------|----------------|--------------|-------------------|----------------|
| "What is Python?" | `reasoning_only` | `reasoning` | 0.75 | `completed` |
| "Fetch GitHub repo" | `tool_required` | `http` | 0.95 | `completed` |
| "Invalid API" | `tool_required` | `http` (fails) | 0.6 | `failed` |

---

## ✅ Final Checklist (Night Before Interview)

- [ ] Backend starts without errors
- [ ] API returns structured FinalResult with float confidence
- [ ] GitHub URL validation works (catches missing `?q=`)
- [ ] Frontend shows execution trace correctly
- [ ] Frontend displays confidence percentage
- [ ] Error messages are clear and helpful
- [ ] All demos load in <3 seconds
- [ ] Git repo is clean (no `.env` committed)
- [ ] README.md is up-to-date

---

## 🎯 Demo Script (2 minutes)

### Setup (10 seconds)
"Let me show you the system. Backend is running on FastAPI, frontend on React."

### Demo 1: Tool Selection (30 seconds)
"Watch how the system decides between reasoning and tools:"
- Enter: "What is Python?" → Shows `reasoning_only`
- Enter: "Fetch GitHub repo" → Shows `tool_required`

### Demo 2: HTTP Safety (30 seconds)
"The system validates API calls before execution. If I try an incomplete GitHub URL, watch what happens..."
- Shows clear validation error

### Demo 3: Observability (50 seconds)
"Every execution has a full trace. Let me fetch a real repository..."
- Shows step-by-step execution
- Shows input/output per step
- Shows final output with confidence and source

### Wrap-up (10 seconds)
"This demonstrates autonomous planning, tool safety, and complete transparency—key differences from chatbots."

---

**Last Check**: Run through this entire checklist 24 hours before demo to catch any issues.
