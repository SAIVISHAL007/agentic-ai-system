/**
 * API Client Service
 * Centralized API calls to backend
 * Treats backend as black-box
 */

import type {
  ExecuteRequest,
  ExecuteResponse,
  ApiError,
  HistoryListResponse,
  HistoryDetailResponse,
  HistoryStatsResponse,
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
