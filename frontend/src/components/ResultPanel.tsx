/**
 * Result Panel Component
 * Displays final output and execution metadata
 * Shown at the bottom of execution viewer
 */

import React from 'react';
import type { ExecuteResponse } from '../types/api';

interface ResultPanelProps {
  execution: ExecuteResponse;
}

export const ResultPanel: React.FC<ResultPanelProps> = ({ execution }) => {
  const formatOutput = (output: unknown): string => {
    if (output === null || output === undefined) {
      return 'null';
    }
    if (typeof output === 'string') {
      return output;
    }
    return JSON.stringify(output, null, 2);
  };

  const successCount = execution.steps_completed.filter(
    (s) => s.success
  ).length;
  const failureCount = execution.steps_completed.length - successCount;
  const executionTime = execution.timestamp
    ? new Date(execution.timestamp).toLocaleString()
    : 'Unknown';

  return (
    <div className="result-panel">
      <div className="container">
        <h2>Execution Result</h2>

        <div className="result-metadata">
          <div className="metadata-grid">
            <div className="metadata-card">
              <div className="metadata-label">Total Steps</div>
              <div className="metadata-value">
                {execution.steps_completed.length}
              </div>
            </div>

            <div className="metadata-card">
              <div className="metadata-label">Successful</div>
              <div className="metadata-value success">
                {successCount}
              </div>
            </div>

            <div className="metadata-card">
              <div className="metadata-label">Failed</div>
              <div className="metadata-value error">
                {failureCount}
              </div>
            </div>

            <div className="metadata-card">
              <div className="metadata-label">Status</div>
              <div className={`metadata-value status-${execution.status}`}>
                {execution.status.toUpperCase()}
              </div>
            </div>
          </div>
        </div>

        <div className="result-output">
          <h3>Final Output</h3>
          <pre className="result-code">
            <code>{formatOutput(execution.final_result)}</code>
          </pre>
        </div>

        {execution.execution_summary && (
          <div className="result-metadata mt-lg">
            <div className="metadata-grid">
              <div className="metadata-card">
                <div className="metadata-label">Tools Used</div>
                <div className="metadata-value">
                  {execution.execution_summary.tools_used.join(', ') || 'None'}
                </div>
              </div>

              <div className="metadata-card">
                <div className="metadata-label">Tool Failures</div>
                <div className="metadata-value error">
                  {execution.execution_summary.tool_failures}
                </div>
              </div>

              <div className="metadata-card">
                <div className="metadata-label">Reasoning Steps</div>
                <div className="metadata-value">
                  {execution.execution_summary.reasoning_steps}
                </div>
              </div>

              <div className="metadata-card">
                <div className="metadata-label">Duration (ms)</div>
                <div className="metadata-value">
                  {execution.execution_summary.duration_ms}
                </div>
              </div>
            </div>
          </div>
        )}

        {execution.error && (
          <div className="alert error">
            <strong>Error Summary:</strong> {execution.error}
          </div>
        )}

        <div className="result-footer text-small text-secondary">
          <p>
            <strong>Execution ID:</strong> {execution.execution_id}
          </p>
          <p>
            <strong>Timestamp:</strong> {executionTime}
          </p>
        </div>
      </div>
    </div>
  );
};
