/**
 * Execution History Page
 * View all past executions with filtering and statistics
 */

import { useEffect, useState } from 'react';
import type { HistorySummary, HistoryRecord, HistoryStatsResponse } from '../types/api';
import { apiClient } from '../services/apiClient';

type SortField = 'timestamp' | 'duration' | 'status';
type SortOrder = 'asc' | 'desc';

interface HistoryFilter {
  intent?: string;
  status?: string;
}

export function HistoryPage({ onBack, preselectedExecutionId }: { onBack: () => void; preselectedExecutionId?: string }) {
  const [executions, setExecutions] = useState<HistorySummary[]>([]);
  const [stats, setStats] = useState<HistoryStatsResponse | null>(null);
  const [selectedExecution, setSelectedExecution] = useState<HistoryRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [filter, setFilter] = useState<HistoryFilter>({});
  const [sortField, setSortField] = useState<SortField>('timestamp');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');
  const [limit] = useState(50);
  const [offset, setOffset] = useState(0);

  const handleDelete = async (executionId: string) => {
    const confirmed = window.confirm('Delete this execution from history? This cannot be undone.');
    if (!confirmed) {
      return;
    }

    try {
      await apiClient.deleteExecutionHistory(executionId);
      if (selectedExecution?.execution_id === executionId) {
        setSelectedExecution(null);
      }
      await loadHistory();
      await loadStats();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete execution');
    }
  };

  useEffect(() => {
    loadHistory();
    loadStats();
  }, [filter, sortField, sortOrder, limit, offset]);

  /**
   * If a specific execution is preselected (from sidebar click),
   * fetch and display it immediately
   */
  useEffect(() => {
    if (preselectedExecutionId) {
      const loadPreselected = async () => {
        try {
          setLoading(true);
          const response = await apiClient.getExecutionDetail(preselectedExecutionId);
          setSelectedExecution(response.execution);
        } catch (err) {
          console.error('Failed to load selected execution:', err);
          setError(err instanceof Error ? err.message : 'Failed to load execution');
        } finally {
          setLoading(false);
        }
      };

      loadPreselected();
    }
  }, [preselectedExecutionId]);

  const loadHistory = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await apiClient.getExecutionHistory(limit, offset, filter.intent, filter.status);
      let sorted = [...response.executions];

      // Sort by selected field
      sorted.sort((a, b) => {
        let aVal: unknown;
        let bVal: unknown;

        if (sortField === 'timestamp') {
          aVal = new Date(a.timestamp).getTime();
          bVal = new Date(b.timestamp).getTime();
        } else if (sortField === 'duration') {
          aVal = a.duration_ms;
          bVal = b.duration_ms;
        } else {
          aVal = a.status;
          bVal = b.status;
        }

        if ((aVal as any) < (bVal as any)) return sortOrder === 'asc' ? -1 : 1;
        if ((aVal as any) > (bVal as any)) return sortOrder === 'asc' ? 1 : -1;
        return 0;
      });

      setExecutions(sorted);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load history');
    } finally {
      setLoading(false);
    }
  };

  const loadStats = async () => {
    try {
      const response = await apiClient.getExecutionStats();
      setStats(response);
    } catch (err) {
      console.error('Failed to load stats:', err);
    }
  };

  const loadDetail = async (executionId: string) => {
    try {
      const response = await apiClient.getExecutionDetail(executionId);
      setSelectedExecution(response.execution);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load execution detail');
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      case 'partial':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getIntentColor = (intent: string | null) => {
    switch (intent) {
      case 'tool_required':
        return 'bg-blue-100 text-blue-800';
      case 'reasoning_only':
        return 'bg-purple-100 text-purple-800';
      case 'mixed':
        return 'bg-indigo-100 text-indigo-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  if (selectedExecution) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
        <div className="max-w-4xl mx-auto px-4 py-8">
          <button
            onClick={() => setSelectedExecution(null)}
            className="mb-6 px-4 py-2 bg-slate-600 text-white rounded-lg hover:bg-slate-700 transition"
          >
            ← Back to History
          </button>

          <button
            onClick={() => handleDelete(selectedExecution.execution_id)}
            className="mb-6 ml-3 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition"
          >
            Delete Execution
          </button>

          <div className="bg-white rounded-lg shadow-lg p-8">
            <h1 className="text-3xl font-bold mb-6">{selectedExecution.goal}</h1>

            <div className="grid grid-cols-2 gap-4 mb-8">
              <div>
                <p className="text-sm text-gray-600">Execution ID</p>
                <p className="font-mono text-sm">{selectedExecution.execution_id}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Status</p>
                <span className={`inline-block px-3 py-1 rounded-full text-sm font-semibold ${getStatusColor(selectedExecution.status)}`}>
                  {selectedExecution.status}
                </span>
              </div>
              <div>
                <p className="text-sm text-gray-600">Intent</p>
                <span className={`inline-block px-3 py-1 rounded-full text-sm font-semibold ${getIntentColor(selectedExecution.intent)}`}>
                  {selectedExecution.intent || 'N/A'}
                </span>
              </div>
              <div>
                <p className="text-sm text-gray-600">Duration</p>
                <p className="font-mono">{selectedExecution.duration_ms}ms</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Timestamp</p>
                <p className="text-sm">{new Date(selectedExecution.timestamp).toLocaleString()}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Tools Used</p>
                <p className="text-sm">{selectedExecution.tools_used.join(', ') || 'None'}</p>
              </div>
            </div>

            <div className="mb-8">
              <h2 className="text-xl font-bold mb-4">Execution Steps</h2>
              <div className="space-y-3">
                {selectedExecution.steps.map((step) => (
                  <div key={step.step_number} className="border border-gray-200 rounded p-4">
                    <div className="flex items-start justify-between mb-2">
                      <div>
                        <p className="font-semibold">Step {step.step_number}: {step.tool_name}</p>
                        <p className="text-sm text-gray-600">{step.description}</p>
                      </div>
                      <span className={`px-2 py-1 rounded text-xs font-semibold ${step.success ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                        {step.success ? 'Success' : 'Failed'}
                      </span>
                    </div>
                    {step.error && <p className="text-sm text-red-600 mt-2">Error: {step.error}</p>}
                  </div>
                ))}
              </div>
            </div>

            {selectedExecution.final_result && (
              <div className="mb-8">
                <h2 className="text-xl font-bold mb-4">Final Result</h2>
                <div className="bg-gray-50 rounded p-4 overflow-auto max-h-64">
                  <pre className="text-sm">{JSON.stringify(selectedExecution.final_result, null, 2)}</pre>
                </div>
              </div>
            )}

            {selectedExecution.error_summary && (
              <div className="mb-8 p-4 bg-red-50 border border-red-200 rounded">
                <h2 className="text-lg font-bold text-red-800 mb-2">Error Summary</h2>
                <p className="text-red-700">{selectedExecution.error_summary}</p>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-4xl font-bold">Execution History</h1>
          <button
            onClick={onBack}
            className="px-4 py-2 bg-slate-600 text-white rounded-lg hover:bg-slate-700 transition"
          >
            ← Back
          </button>
        </div>

        {/* Statistics */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
              <p className="text-sm text-blue-600 font-semibold">Total Executions</p>
              <p className="text-3xl font-bold text-blue-900">{stats.total_executions}</p>
            </div>
            <div className="bg-green-50 border border-green-200 rounded-lg p-6">
              <p className="text-sm text-green-600 font-semibold">Successful</p>
              <p className="text-3xl font-bold text-green-900">{stats.successful}</p>
            </div>
            <div className="bg-orange-50 border border-orange-200 rounded-lg p-6">
              <p className="text-sm text-orange-600 font-semibold">Failed</p>
              <p className="text-3xl font-bold text-orange-900">{stats.failed}</p>
            </div>
          </div>
        )}

        {/* Filters */}
        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <h2 className="text-lg font-bold mb-4">Filters</h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Intent</label>
              <select
                value={filter.intent || ''}
                onChange={(e) => setFilter({ ...filter, intent: e.target.value || undefined })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">All</option>
                <option value="reasoning_only">Reasoning Only</option>
                <option value="tool_required">Tool Required</option>
                <option value="mixed">Mixed</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Status</label>
              <select
                value={filter.status || ''}
                onChange={(e) => setFilter({ ...filter, status: e.target.value || undefined })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">All</option>
                <option value="completed">Completed</option>
                <option value="failed">Failed</option>
                <option value="partial">Partial</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Sort By</label>
              <select
                value={sortField}
                onChange={(e) => setSortField(e.target.value as SortField)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="timestamp">Timestamp</option>
                <option value="duration">Duration</option>
                <option value="status">Status</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Order</label>
              <select
                value={sortOrder}
                onChange={(e) => setSortOrder(e.target.value as SortOrder)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="desc">Descending</option>
                <option value="asc">Ascending</option>
              </select>
            </div>
          </div>
        </div>

        {/* History List */}
        <div className="bg-white rounded-lg shadow overflow-hidden">
          {loading ? (
            <div className="p-8 text-center">
              <p className="text-gray-600">Loading history...</p>
            </div>
          ) : error ? (
            <div className="p-8 text-center text-red-600">
              <p>Error: {error}</p>
            </div>
          ) : executions.length === 0 ? (
            <div className="p-8 text-center text-gray-600">
              <p>No executions found</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Goal</th>
                    <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Intent</th>
                    <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Status</th>
                    <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Duration</th>
                    <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Timestamp</th>
                    <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {executions.map((execution) => (
                    <tr key={execution.execution_id} className="hover:bg-gray-50 transition">
                      <td className="px-6 py-4 text-sm truncate max-w-md text-gray-900">{execution.goal}</td>
                      <td className="px-6 py-4 text-sm">
                        <span className={`inline-block px-3 py-1 rounded-full text-xs font-semibold ${getIntentColor(execution.intent)}`}>
                          {execution.intent || '—'}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm">
                        <span className={`inline-block px-3 py-1 rounded-full text-xs font-semibold ${getStatusColor(execution.status)}`}>
                          {execution.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600">{execution.duration_ms}ms</td>
                      <td className="px-6 py-4 text-sm text-gray-600">{new Date(execution.timestamp).toLocaleString()}</td>
                      <td className="px-6 py-4 text-sm">
                        <button
                          onClick={() => loadDetail(execution.execution_id)}
                          className="text-blue-600 hover:text-blue-800 font-semibold transition"
                        >
                          View
                        </button>
                        <button
                          onClick={() => handleDelete(execution.execution_id)}
                          className="ml-4 text-red-600 hover:text-red-800 font-semibold transition"
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination */}
          <div className="px-6 py-4 border-t border-gray-200 flex justify-between items-center">
            <button
              onClick={() => setOffset(Math.max(0, offset - limit))}
              disabled={offset === 0}
              className="px-4 py-2 bg-slate-600 text-white rounded-lg hover:bg-slate-700 disabled:opacity-50 transition"
            >
              ← Previous
            </button>
            <span className="text-sm text-gray-600">
              Showing {offset + 1} to {offset + executions.length}
            </span>
            <button
              onClick={() => setOffset(offset + limit)}
              disabled={executions.length < limit}
              className="px-4 py-2 bg-slate-600 text-white rounded-lg hover:bg-slate-700 disabled:opacity-50 transition"
            >
              Next →
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
