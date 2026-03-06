# Reasoning Grounding Fix - Implementation Documentation

## Problem Statement

**Issue**: Reasoning steps were not using fetched data from previous tool executions. Instead, they generated generic explanations.

**Example of Broken Behavior**:
```
User Goal: "Fetch deep learning repository from GitHub and explain it"

Step 1 (HTTP): Fetches TensorFlow repo with details (stars: 185k, language: C++, etc.)
Step 2 (Reasoning): Explains "what deep learning is" (GENERIC) ❌

EXPECTED: Step 2 should explain THE SPECIFIC TensorFlow repository that was fetched ✅
```

**Root Cause**: 
- ExecutorAgent stored tool outputs but didn't extract structured data for reasoning context
- ReasoningTool only accepted string context, not structured data
- No mechanism to ground reasoning in actual fetched results

---

## Solution Architecture

### 1. Context Enrichment in Executor

**File**: [app/agents/executor.py](app/agents/executor.py)

**Changes**:
- Added `_enrich_reasoning_context()` method to detect reasoning steps and inject previous tool outputs
- Added `_extract_structured_context()` method to extract meaningful data from tool outputs
- Added `_extract_http_context()` method to handle GitHub API and other HTTP responses

**Flow**:
```python
# Before executing reasoning tool:
if tool_name == "reasoning":
    resolved_input = self._enrich_reasoning_context(
        resolved_input,
        execution_context,
        step.step_number
    )
```

**Key Logic**:
1. Find the most recent non-reasoning tool execution
2. Extract its output
3. Transform it into structured context
4. Replace/enrich the reasoning tool's `context` parameter

---

### 2. Structured Context Extraction

**GitHub API Response Handling**:
```python
def _extract_http_context(self, http_output: Any) -> Any:
    # Handles GitHub search results with "items" array
    if "items" in http_output and isinstance(http_output["items"], list):
        items = http_output["items"]
        if items:
            first_item = items[0]  # Select first repository
            
            # Extract key metadata
            if "full_name" in first_item:
                return {
                    "name": first_item.get("full_name"),
                    "description": first_item.get("description"),
                    "stars": first_item.get("stargazers_count"),
                    "forks": first_item.get("forks_count"),
                    "language": first_item.get("language"),
                    "url": first_item.get("html_url"),
                    "topics": first_item.get("topics", []),
                    "created_at": first_item.get("created_at"),
                    "updated_at": first_item.get("updated_at"),
                }
```

**Memory Tool Handling**:
```python
def _extract_structured_context(self, tool_output: Any, tool_name: str) -> Any:
    if tool_name == "memory":
        if isinstance(tool_output, dict) and "value" in tool_output:
            return tool_output["value"]  # Extract the stored value
        return tool_output
```

---

### 3. Reasoning Tool Updates

**File**: [app/tools/reasoning_tool.py](app/tools/reasoning_tool.py)

**Changes**:
- Updated `ReasoningToolInput.context` to accept `Union[str, dict, list]`
- Added `_format_context()` method to format structured data for LLM prompts
- Removed generic system message assumptions

**Context Formatting**:
```python
def _format_context(self, context: Union[str, dict, list]) -> str:
    if isinstance(context, dict):
        # Special handling for GitHub repositories
        if "name" in context and "url" in context:
            formatted_lines = ["Context (Structured Data):", "\nGitHub Repository:"]
            if context.get("name"):
                formatted_lines.append(f"  • Name: {context['name']}")
            if context.get("description"):
                formatted_lines.append(f"  • Description: {context['description']}")
            if context.get("stars") is not None:
                formatted_lines.append(f"  • Stars: {context['stars']:,}")
            # ... more fields
```

**LLM Prompt Example** (after grounding):
```
Question: What is this repository about?

Context (Structured Data):

GitHub Repository:
  • Name: tensorflow/tensorflow
  • Description: An Open Source Machine Learning Framework for Everyone
  • Stars: 185,000
  • Forks: 74,000
  • Primary Language: C++
  • URL: https://github.com/tensorflow/tensorflow
  • Topics: machine-learning, deep-learning, tensorflow
```

---

## Execution Flow

### Before Grounding Fix ❌
```
HTTP Tool → Returns GitHub API response → Stored in execution_context
                                                ↓
Reasoning Tool → Receives: {"question": "What is this?", "context": ""}
                            ↓
LLM → Generic explanation about DL concepts
```

### After Grounding Fix ✅
```
HTTP Tool → Returns GitHub API response → Stored in execution_context
                                                ↓
                                    _extract_http_context()
                                                ↓
                        Extracts: {name, description, stars, url, ...}
                                                ↓
Reasoning Tool → Receives: {"question": "What is this?", "context": <repo_dict>}
                                                ↓
                              _format_context()
                                                ↓
                    LLM Prompt with structured GitHub repo data
                                                ↓
                    LLM → SPECIFIC explanation about TensorFlow
```

---

## Test Coverage

**File**: [tests/test_reasoning_grounding.py](tests/test_reasoning_grounding.py)

**7 Tests Implemented**:
1. ✅ `test_reasoning_receives_github_repo_context` - Main grounding behavior
2. ✅ `test_reasoning_without_previous_tool_uses_generic_context` - Pure reasoning still works
3. ✅ `test_extract_structured_context_from_github_response` - GitHub parsing logic
4. ✅ `test_extract_structured_context_from_empty_items` - Edge case handling
5. ✅ `test_format_context_dict_for_reasoning` - Context formatting for dicts
6. ✅ `test_format_context_string_for_reasoning` - Context formatting for strings
7. ✅ `test_reasoning_grounding_with_memory_tool` - Memory tool integration

**All 20 Tests Passing**:
- 13 Agentic Semantics tests (from previous transformation)
- 7 Grounding tests (new)

---

## Key Benefits

### 1. **Data Grounding**
Reasoning is now grounded in actual fetched data, not generic knowledge:
- ✅ Explains THE repository that was fetched
- ✅ Uses actual star counts, descriptions, languages from API
- ✅ Provides specific facts, not general concepts

### 2. **Automatic Context Enrichment**
No manual context passing needed:
- ✅ Executor automatically detects reasoning steps
- ✅ Extracts relevant data from previous tool
- ✅ Formats it appropriately for LLM

### 3. **Tool-Agnostic Design**
Works with multiple tool types:
- ✅ HTTP tool (GitHub API, generic APIs)
- ✅ Memory tool (extracts stored values)
- ✅ Extensible to new tool types

### 4. **Backward Compatible**
Pure reasoning still works:
- ✅ Reasoning-only plans don't require previous tools
- ✅ Manual context strings still supported
- ✅ No breaking changes to API

---

## Logging & Observability

**Grounding events are logged**:
```
[INFO] Grounding reasoning step with data from http output
[DEBUG] Enriched reasoning context: {'name': 'tensorflow/tensorflow', 'description': ...
```

**Execution traces show structured context**:
- Tool outputs include structured data
- Reasoning steps show enriched context
- Easy to debug what data was used

---

## Future Enhancements

### Potential Improvements:
1. **Multi-step context aggregation**: Combine data from multiple previous tools
2. **Context prioritization**: Rank which previous outputs are most relevant
3. **Semantic similarity**: Use embeddings to find relevant past tool outputs
4. **Context summarization**: For very large API responses, summarize key points
5. **Tool-specific extractors**: Specialized logic for different API patterns

---

## Example Usage

### Request:
```json
{
  "goal": "Find the most popular Python ML framework on GitHub and explain it"
}
```

### Execution Plan (Auto-Generated):
```json
{
  "steps": [
    {
      "step_number": 1,
      "tool_name": "http",
      "input_data": {
        "url": "https://api.github.com/search/repositories?q=machine+learning+language:python&sort=stars",
        "method": "GET"
      }
    },
    {
      "step_number": 2,
      "tool_name": "reasoning",
      "input_data": {
        "question": "What is this machine learning framework?",
        "context": ""
      }
    }
  ]
}
```

### Execution Result (With Grounding):
```json
{
  "success": true,
  "content": "TensorFlow is a comprehensive, open-source machine learning framework developed by Google. With over 185,000 stars on GitHub, it's one of the most popular ML libraries in the Python ecosystem. The framework uses C++ for performance-critical operations while providing a Python API for ease of use. It excels at deep learning tasks, neural network training, and production deployments. Key topics include machine-learning, deep-learning, and neural-networks. The framework has been actively maintained since 2015 and is used by major companies worldwide. [GitHub Link: https://github.com/tensorflow/tensorflow]",
  "execution_trace": [
    {
      "step_number": 1,
      "tool_name": "http",
      "success": true,
      "output": {
        "items": [{"full_name": "tensorflow/tensorflow", "stargazers_count": 185000, ...}]
      }
    },
    {
      "step_number": 2,
      "tool_name": "reasoning",
      "success": true,
      "input_data": {
        "question": "What is this machine learning framework?",
        "context": {
          "name": "tensorflow/tensorflow",
          "description": "An Open Source Machine Learning Framework for Everyone",
          "stars": 185000,
          "language": "C++",
          "url": "https://github.com/tensorflow/tensorflow"
        }
      },
      "output": "TensorFlow is a comprehensive..."
    }
  ]
}
```

**Notice**: Step 2's `context` is automatically populated with structured data from Step 1's HTTP response!

---

## Validation

✅ **All tests passing** (20/20)  
✅ **No breaking changes** to existing API contracts  
✅ **Agentic semantics preserved** (hard failures, intent enforcement)  
✅ **Grounding works** for HTTP and Memory tools  
✅ **Backward compatible** with pure reasoning steps  

---

## Summary

**Problem**: Reasoning was disconnected from fetched data  
**Solution**: Automatic context enrichment from previous tool outputs  
**Result**: Reasoning is now grounded in actual fetched facts  

This fix transforms reasoning from **generic explanations** to **data-driven insights**.
