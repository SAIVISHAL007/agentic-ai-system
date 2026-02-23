/**
 * Execution Viewer Page
 * Displays ordered planned steps and their execution status
 * Shows tool name, input, output, and errors per step
 */

import React from 'react';
import type { ExecuteResponse } from '../types/api';

interface ExecutionViewerPageProps {
  execution: ExecuteResponse | null;
  isLoading: boolean;
  error: string | null;
  onReset: () => void;
}

export const ExecutionViewerPage: React.FC<ExecutionViewerPageProps> = ({
  execution,
  isLoading,
  error,
  onReset,
}) => {
  if (isLoading) {
    return (
      <div className="execution-viewer-page">
        <div className="container">
          <div className="loading-state flex-center">
            <div className="flex-column-center gap-md">
              <span className="spinner"></span>
              <p>Planning and executing steps...</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error && !execution) {
    return (
      <div className="execution-viewer-page">
        <div className="container">
          <div className="alert error">
            <strong>Execution Failed:</strong> {error}
          </div>
          <button onClick={onReset} className="secondary">
            ← Back to Goal Input
          </button>
        </div>
      </div>
    );
  }

  if (!execution) {
    return null;
  }

  const getStatusClass = (success: boolean): string => {
    return success ? 'status-success' : 'status-error';
  };

  const formatOutput = (output: unknown): string => {
    if (output === null || output === undefined) {
      return 'null';
    }
    if (typeof output === 'string') {
      return output;
    }
    return JSON.stringify(output, null, 2);
  };

  return (
    <div className="execution-viewer-page">
      <div className="container">
        <div className="execution-header">
          <div className="header-title">
            <h1>Execution Trace</h1>
            <p className="goal-summary">{execution.goal}</p>
          </div>

          <div className="header-metadata">
            <div className="metadata-item">
              <span className="metadata-label">Execution ID:</span>
              <code className="metadata-value">{execution.execution_id}</code>
            </div>
            <div className="metadata-item">
              <span className="metadata-label">Status:</span>
              <span
                className={`status-badge status-${execution.status}`}
              >
                {execution.status.toUpperCase()}
              </span>
            </div>
            {execution.intent && (
              <div className="metadata-item">
                <span className="metadata-label">Intent:</span>
                <span className="metadata-value">
                  {execution.intent.replace('_', ' ').toUpperCase()}
                </span>
              </div>
            )}
            <div className="metadata-item">
              <span className="metadata-label">Steps:</span>
              <span className="metadata-value">
                {execution.steps_completed.length}
              </span>
            </div>
            <div className="metadata-item">
              <span className="metadata-label">Time:</span>
              <span className="metadata-value text-small">
                {new Date(execution.timestamp).toLocaleString()}
              </span>
            </div>
          </div>
        </div>

        {execution.error && (
          <div className="alert error mt-lg mb-lg">
            <strong>Error:</strong> {execution.error}
          </div>
        )}

        <div className="steps-container mt-lg mb-lg">
          <h2>Execution Steps</h2>

          {execution.steps_completed.length === 0 ? (
            <p className="text-secondary">No steps were executed</p>
          ) : (
            <div className="steps-list">
              {execution.steps_completed.map((step, index) => (
                <div key={index} className="step-card">
                  <div className="step-header">
                    <div className="step-number">
                      <span>Step {step.step_number}</span>
                    </div>
                    {step.description && (
                      <div className="step-name">
                        <strong>{step.description}</strong>
                      </div>
                    )}
                    <div className="step-tool">
                      <strong>Tool:</strong> <code>{step.tool_name}</code>
                    </div>
                    <div className={`step-status ${getStatusClass(step.success)}`}>
                      {step.success ? '✓ Success' : '✗ Failed'}
                    </div>
                  </div>

                  <div className="step-body">
                    <div className="step-section">
                      <h4>Input</h4>
                      <pre>
                        <code>{formatOutput(step.input)}</code>
                      </pre>
                    </div>

                    <div className="step-section">
                      <h4>Output</h4>
                      <pre>
                        <code>{formatOutput(step.output)}</code>
                      </pre>
                    </div>

                    {step.error && (
                      <div className="step-section">
                        <h4>Error</h4>
                        <p className="error-text">{step.error}</p>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="actions">
          <button onClick={onReset} className="secondary">
            ← New Goal
          </button>
        </div>
      </div>
    </div>
  );
};
