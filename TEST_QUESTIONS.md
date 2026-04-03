# Agentic AI System - Test Suite

Test these questions in the UI at http://localhost:5173/ and report the results.

## 1. **Reasoning-Only (Baseline)**
**Question:** "What is the capital of France?"

**Expected Result:**
- Status: `completed`
- Tools used: `["reasoning"]`
- Final answer contains concrete city name (e.g., "Paris"), NOT a template variable
- Confidence: 0.75+

---

## 2. **Live Data - Bitcoin (Tool Required)**
**Question:** "What is the current Bitcoin price in USD?"

**Expected Result:**
- Status: `completed`
- Tools used: `["http", "reasoning"]` (both steps should succeed)
- Final answer contains actual USD price (e.g., "$66,750"), NOT a placeholder like `$bitcoin_price`
- Confidence: 0.95+

---

## 3. **Live Data - Weather (Tool Required)**
**Question:** "What is the current weather in London?"

**Expected Result:**
- Status: `completed`
- Tools used: `["http", "reasoning"]`
- Final answer describes actual weather conditions (clouds, temperature, etc.), NOT template text
- Confidence: 0.95+

---

## 4. **Mixed Workflow - Fetch and Store (Tool Required)**
**Question:** "Fetch the current Bitcoin price, store it in memory, and tell me what you stored."

**Expected Result:**
- Status: `completed`
- Tools used: `["http", "memory", "reasoning"]` (all three should be present)
- Final answer reflects the actual stored price, NOT a memory acknowledgement like "Stored value at key..."
- Confidence: 0.95+

---

## 5. **GitHub Repo (Tool Required)**
**Question:** "Get details for github.com/torvalds/linux and summarize the key metrics."

**Expected Result:**
- Status: `completed`
- Tools used: `["http", "reasoning"]`
- Final answer contains concrete repo info (stars, language, URL), NOT generic explanation
- Confidence: 0.95+

---

## 6. **Rate Limiting (Expected Failure Recovery)**
**Question:** "With rate limiting enabled, what happens if you send 3 rapid requests within 10 seconds for the current Bitcoin price in USD?"

**Expected Result:**
- Status: `completed`
- Tools used: `["http", "reasoning"]`
- Final answer explains rate limit behavior AND includes the actual Bitcoin price fetched
- Confidence: 0.95+

---

## 7. **Invalid Location - Weather (Fallback)**
**Question:** "What is the weather in XYZNowherePlace?"

**Expected Result:**
- Status: `failed` (acceptable) OR `completed` with a clear error message
- If failed: error message is clear (no hallucination)
- If completed: final answer honestly states the location could not be found
- Confidence: 0.0-0.6 (appropriate for failure)

---

## 8. **History Persistence (Observability)**
**Question:** "Check the history page - do the 5 previous executions appear there with their steps and final results?"

**Expected Result:**
- History page loads without error
- Each execution shows: goal, status, tools used, duration, and final answer
- Clicking an execution shows full step-by-step trace
- At least 5 rows visible

---

## Scoring

| Test | Pass Criteria |
|------|---------------|
| 1    | Reasoning works, no template variables |
| 2    | Bitcoin price fetched live, no `$bitcoin_price` placeholder |
| 3    | Weather fetched live, concrete description |
| 4    | Mixed workflow uses all 3 tools, final answer is grounded |
| 5    | GitHub repo data fetched live, concrete metrics |
| 6    | Rate limit behavior demonstrated with actual price |
| 7    | Invalid input fails cleanly or explains the issue |
| 8    | History persists and displays correctly |

**Overall Success:** All 8 tests pass cleanly → Ready to commit.
**Issues Found:** Document which tests failed and we'll iterate.
