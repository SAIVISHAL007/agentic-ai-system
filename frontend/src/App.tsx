/**
 * Main App Component
 * Handles state management and view routing
 * Flow: GoalInputPage → ExecutionViewerPage → ResultPanel
 */

import { useState } from 'react';
import type { ExecuteRequest, ExecuteResponse, ExecutionState } from './types/api';
import { apiClient } from './services/apiClient';
import { GoalInputPage } from './pages/GoalInputPage';
import { ExecutionViewerPage } from './pages/ExecutionViewerPage';
import { ResultPanel } from './components/ResultPanel';

type ViewType = 'input' | 'execution';

interface AppState {
  currentView: ViewType;
  execution: ExecuteResponse | null;
  executionState: ExecutionState;
  error: string | null;
}

function App() {
  const [state, setState] = useState<AppState>({
    currentView: 'input',
    execution: null,
    executionState: 'idle',
    error: null,
  });

  /**
   * Handle goal submission
   * POST to backend and show execution viewer
   */
  const handleGoalSubmit = async (request: ExecuteRequest) => {
    setState((prev) => ({
      ...prev,
      executionState: 'loading',
      error: null,
      currentView: 'execution',
    }));

    try {
      const response = await apiClient.executeGoal(request);
      setState((prev) => ({
        ...prev,
        execution: response,
        executionState: 'success',
        error: null,
      }));
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setState((prev) => ({
        ...prev,
        executionState: 'error',
        error: errorMessage,
      }));
    }
  };

  /**
   * Reset to goal input view
   */
  const handleReset = () => {
    setState({
      currentView: 'input',
      execution: null,
      executionState: 'idle',
      error: null,
    });
  };

  return (
    <div className="app">
      {state.currentView === 'input' && (
        <GoalInputPage
          onSubmit={handleGoalSubmit}
          isLoading={state.executionState === 'loading'}
        />
      )}

      {state.currentView === 'execution' && (
        <>
          <ExecutionViewerPage
            execution={state.execution}
            isLoading={state.executionState === 'loading'}
            error={state.error}
            onReset={handleReset}
          />

          {state.execution && state.executionState === 'success' && (
            <ResultPanel execution={state.execution} />
          )}
        </>
      )}
    </div>
  );
}

export default App;
