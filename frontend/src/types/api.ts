/**
 * API Type Definitions
 * Mirrors backend response schemas (from app/schemas/request_response.py)
 */

/**
 * Request to execute a goal end-to-end
 */
export interface ExecuteRequest {
  goal: string;
  context?: Record<string, unknown>;
}

/**
 * Result of a single execution step
 */
export interface StepResult {
  step_number: number;
  description: string;
  tool_name: string;
  success: boolean;
  input?: unknown;  // Tool input parameters
  output: unknown;
  error: string | null;
}

export interface FinalResult {
  success: boolean;  // Whether the intended action completed successfully
  content: string | null;  // Result content (null if action failed)
  source: 'reasoning' | 'http' | 'memory' | 'failed';  // AGENTIC: 'failed' is a legitimate source
  confidence: number;  // 0.0-1.0 float from backend (0.0 for hard failures)
  error?: string;  // Structured error message if action failed
  execution_id: string;
}

export interface ExecutionSummary {
  tools_used: string[];
  tool_failures: number;
  reasoning_steps: number;
  duration_ms: number;
}

/**
 * Final response from end-to-end execution
 */
export interface ExecuteResponse {
  execution_id: string;
  goal: string;
  status: 'completed' | 'failed' | 'partial';
  intent?: 'reasoning_only' | 'tool_required' | 'mixed';
  decision_rationale?: string;  // Explanation of why that intent was chosen
  steps_completed: StepResult[];
  final_result: FinalResult;
  execution_summary?: ExecutionSummary;
  error: string | null;
  timestamp: string;
}

export interface StreamProgressEvent {
  type:
    | 'planning_started'
    | 'plan_created'
    | 'step_started'
    | 'step_retry'
    | 'step_completed'
    | 'execution_completed'
    | 'execution_failed';
  step_number?: number;
  description?: string;
  tool_name?: string;
  success?: boolean;
  error?: string;
  retry_count?: number;
  step_count?: number;
}

/**
 * API error response
 */
export interface ApiError {
  detail: string;
}

/**
 * Loading/execution state for UI
 */
export type ExecutionState = 'idle' | 'loading' | 'success' | 'error';

/**
 * Execution history types (from app/schemas/history.py)
 */
export interface HistoryStep {
  step_number: number;
  tool_name: string;
  description: string;
  success: boolean;
  error: string | null;
}

export interface HistoryRecord {
  execution_id: string;
  tenant_id?: string | null;
  goal: string;
  intent: string | null;
  status: string;
  steps: HistoryStep[];
  tools_used: string[];
  final_result: Record<string, unknown> | null;
  error_summary: string | null;
  duration_ms: number;
  timestamp: string;
  tool_failure_count: number;
  reasoning_step_count: number;
}

export interface HistorySummary {
  execution_id: string;
  tenant_id?: string | null;
  goal: string;
  intent: string | null;
  status: string;
  tools_used: string[];
  timestamp: string;
  duration_ms: number;
}

export interface HistoryListResponse {
  executions: HistorySummary[];
  total_count: number;
  offset: number;
  limit: number;
}

export interface HistoryDetailResponse {
  execution: HistoryRecord;
}

export interface DeleteHistoryResponse {
  success: boolean;
  execution_id: string;
}

export interface HistoryStatsResponse {
  total_executions: number;
  successful: number;
  failed: number;
  tools_used: string[];
  avg_duration_ms: number;
  intents: Record<string, number>;
}

export interface GitHubRepoInsightsRequest {
  owner: string;
  repo: string;
}

export interface GitHubRepoInsightsResponse {
  success: boolean;
  source: string;
  execution_type: string;
  insights?: Record<string, unknown>;
  error?: string;
}
