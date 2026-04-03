/**
 * API Client Service
 * Centralized API calls to backend
 * Treats backend as black-box
 */

import type {
  ExecuteRequest,
  ExecuteResponse,
  StreamProgressEvent,
  ApiError,
  HistoryListResponse,
  HistoryDetailResponse,
  HistoryStatsResponse,
  GitHubRepoInsightsRequest,
  GitHubRepoInsightsResponse,
} from '../types/api';

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  /**
   * Health check endpoint
   */
  async health(): Promise<{ status: string; service: string }> {
    const response = await fetch(`${this.baseUrl}/health`);
    if (!response.ok) {
      throw this.handleError(response);
    }
    return response.json();
  }

  /**
   * Execute a goal end-to-end
   * POST /api/execute
   */
  async executeGoal(request: ExecuteRequest): Promise<ExecuteResponse> {
    const response = await fetch(`${this.baseUrl}/api/execute`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw this.handleError(response);
    }

    return response.json();
  }

  /**
   * Execute a goal with streaming progress events.
   * POST /api/execute/stream (text/event-stream)
   */
  async executeGoalStream(
    request: ExecuteRequest,
    handlers: {
      onProgress?: (event: StreamProgressEvent) => void;
      onCompleted: (response: ExecuteResponse) => void;
      onError: (message: string) => void;
    }
  ): Promise<void> {
    const response = await fetch(`${this.baseUrl}/api/execute/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok || !response.body) {
      handlers.onError(`HTTP ${response.status}`);
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    const processEventBlock = (eventBlock: string) => {
      const normalizedBlock = eventBlock.replace(/\r\n/g, '\n').replace(/\r/g, '\n').trim();
      if (!normalizedBlock) {
        return;
      }

      const lines = normalizedBlock.split('\n');
      let eventName = '';
      let data = '';

      for (const line of lines) {
        if (line.startsWith('event:')) {
          eventName = line.slice(6).trim();
        } else if (line.startsWith('data:')) {
          data += line.slice(5).trim();
        }
      }

      if (!eventName || !data) {
        return;
      }

      try {
        const parsed = JSON.parse(data);
        if (eventName === 'completed') {
          handlers.onCompleted(parsed as ExecuteResponse);
        } else if (eventName === 'error') {
          handlers.onError((parsed?.detail as string) || 'Stream execution failed');
        } else if (eventName === 'progress') {
          handlers.onProgress?.(parsed as StreamProgressEvent);
        }
      } catch {
        if (eventName === 'error') {
          handlers.onError('Stream execution failed');
        }
      }
    };

    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      buffer = buffer.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
      const events = buffer.split('\n\n');
      buffer = events.pop() ?? '';

      for (const eventBlock of events) {
        processEventBlock(eventBlock);
      }
    }

    // Flush any final buffered SSE event that arrived without a trailing delimiter.
    if (buffer.trim()) {
      processEventBlock(buffer);
    }

    const trailing = decoder.decode();
    if (trailing.trim()) {
      processEventBlock(trailing);
    }
  
    if (!response.body.locked) {
      try {
        await reader.cancel();
      } catch {
        // Ignore cancellation errors after the stream is complete.
      }
    }
  }

  /**
   * Get execution history list
   * GET /api/history?limit=50&offset=0&intent=&status=
   */
  async getExecutionHistory(
    limit: number = 50,
    offset: number = 0,
    intent?: string,
    status?: string
  ): Promise<HistoryListResponse> {
    const params = new URLSearchParams();
    params.set('limit', limit.toString());
    params.set('offset', offset.toString());
    if (intent) params.set('intent', intent);
    if (status) params.set('status', status);

    const response = await fetch(`${this.baseUrl}/api/history?${params}`);
    if (!response.ok) {
      throw this.handleError(response);
    }

    return response.json();
  }

  /**
   * Get execution history detail
   * GET /api/history/{execution_id}
   */
  async getExecutionDetail(executionId: string): Promise<HistoryDetailResponse> {
    const response = await fetch(`${this.baseUrl}/api/history/${executionId}`);
    if (!response.ok) {
      throw this.handleError(response);
    }

    return response.json();
  }

  /**
   * Delete a single execution history record.
   * DELETE /api/history/{execution_id}
   */
  async deleteExecutionHistory(executionId: string): Promise<{ success: boolean; execution_id: string }> {
    const response = await fetch(`${this.baseUrl}/api/history/${executionId}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      throw this.handleError(response);
    }

    return response.json();
  }

  /**
   * Get execution history statistics
   * GET /api/history/stats
   */
  async getExecutionStats(): Promise<HistoryStatsResponse> {
    const response = await fetch(`${this.baseUrl}/api/history/stats`);
    if (!response.ok) {
      throw this.handleError(response);
    }

    return response.json();
  }

  /**
   * Run concrete GitHub repository insights workflow.
   * POST /api/workflows/github-repo-insights
   */
  async runGitHubRepoInsights(
    request: GitHubRepoInsightsRequest
  ): Promise<GitHubRepoInsightsResponse> {
    const response = await fetch(`${this.baseUrl}/api/workflows/github-repo-insights`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });
    if (!response.ok) {
      throw this.handleError(response);
    }
    return response.json();
  }

  /**
   * Parse error response from backend
   */
  private async handleError(response: Response): Promise<never> {
    let errorMessage = `HTTP ${response.status}`;

    try {
      const error: ApiError = await response.json();
      errorMessage = error.detail || errorMessage;
    } catch {
      errorMessage = response.statusText || errorMessage;
    }

    const error = new Error(errorMessage);
    throw error;
  }
}

export const apiClient = new ApiClient();
