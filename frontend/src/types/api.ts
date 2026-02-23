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
  content: string;
  source: 'reasoning-only' | 'http' | 'mixed' | 'tool-failure';
  confidence: 'high' | 'medium' | 'low';
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
  steps_completed: StepResult[];
  final_result: FinalResult;
  execution_summary?: ExecutionSummary;
  error: string | null;
  timestamp: string;
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
