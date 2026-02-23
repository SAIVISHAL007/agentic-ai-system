/**
 * Goal Input Page
 * Accepts goal and optional JSON context
 * Submits to backend for execution
 */

import { useState } from 'react';
import type { FC, FormEvent } from 'react';
import type { ExecuteRequest } from '../types/api';

interface GoalInputPageProps {
  onSubmit: (request: ExecuteRequest) => void;
  isLoading: boolean;
}

export const GoalInputPage: FC<GoalInputPageProps> = ({
  onSubmit,
  isLoading,
}) => {
  const [goal, setGoal] = useState('');
  const [contextJson, setContextJson] = useState('');
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!goal.trim()) {
      setError('Please enter a goal');
      return;
    }

    let context: Record<string, unknown> = {};
    if (contextJson.trim()) {
      try {
        context = JSON.parse(contextJson);
      } catch {
        setError('Invalid JSON in context field');
        return;
      }
    }

    const request: ExecuteRequest = {
      goal: goal.trim(),
      context,
    };

    onSubmit(request);
  };

  return (
    <div className="goal-input-page">
      <div className="container">
        <div className="goal-input-header">
          <h1>Agentic AI Execution</h1>
          <p className="text-secondary">
            Enter a high-level goal. The system will plan and execute steps to
            achieve it.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="goal-input-form">
          <div className="form-group">
            <label htmlFor="goal">Goal *</label>
            <textarea
              id="goal"
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              placeholder="Example: Fetch GitHub repository statistics for python/cpython"
              disabled={isLoading}
            />
            <p className="help-text">
              Describe what you want the system to achieve
            </p>
          </div>

          <div className="form-group">
            <label htmlFor="context">Context (JSON, optional)</label>
            <textarea
              id="context"
              value={contextJson}
              onChange={(e) => setContextJson(e.target.value)}
              placeholder='Example: {"owner": "python", "repo": "cpython"}'
              disabled={isLoading}
              style={{ minHeight: '80px' }}
            />
            <p className="help-text">
              Provide additional context as JSON (optional)
            </p>
          </div>

          {error && (
            <div className="alert error">
              <strong>Error:</strong> {error}
            </div>
          )}

          <div className="form-actions">
            <button
              type="submit"
              disabled={isLoading || !goal.trim()}
              className="submit-btn"
            >
              {isLoading ? (
                <>
                  <span className="spinner"></span> Executing...
                </>
              ) : (
                'Execute Goal'
              )}
            </button>
          </div>
        </form>

        <div className="info-section">
          <h3>How it Works</h3>
          <ol>
            <li>
              <strong>Planning:</strong> The system uses LLM to break down your
              goal into ordered steps
            </li>
            <li>
              <strong>Execution:</strong> Each step is executed sequentially
              using available tools
            </li>
            <li>
              <strong>Results:</strong> Complete execution trace with all steps,
              outputs, and errors
            </li>
          </ol>
        </div>
      </div>
    </div>
  );
};
