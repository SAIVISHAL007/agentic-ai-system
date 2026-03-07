/**
 * Main App Component
 * Handles state management and view routing
 * Flow: GoalInputPage → ExecutionViewerPage → ResultPanel
 *       Or: History button → HistoryPage
 */

import { useState, useEffect } from 'react';
import type { ExecuteRequest, ExecuteResponse, ExecutionState, HistorySummary } from './types/api';
import { apiClient } from './services/apiClient';
import { GoalInputPage } from './pages/GoalInputPage';
import { ExecutionViewerPage } from './pages/ExecutionViewerPage';
import { HistoryPage } from './pages/HistoryPage';
import { ResultPanel } from './components/ResultPanel';

type ViewType = 'input' | 'execution' | 'history';

interface AppState {
  currentView: ViewType;
  execution: ExecuteResponse | null;
  executionState: ExecutionState;
  error: string | null;
  sidebarOpen: boolean;
  historyItems: HistorySummary[];
  historyLoading: boolean;
  preselectedExecutionId?: string;
}

function App() {
  const [state, setState] = useState<AppState>({
    currentView: 'input',
    execution: null,
    executionState: 'idle',
    error: null,
    sidebarOpen: false,
    historyItems: [],
    historyLoading: false,
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
    setState((prev) => ({
      ...prev,
      currentView: 'input',
      execution: null,
      executionState: 'idle',
      error: null,
      sidebarOpen: false,
    }));
  };

  /**
   * Navigate to history view
   */
  const goToHistory = () => {
    setState((prev) => ({
      ...prev,
      currentView: 'history',
      execution: null,
      executionState: 'idle',
      error: null,
      sidebarOpen: false,
    }));
  };

  /**
   * Navigate back from history
   */
  const backFromHistory = () => {
    setState((prev) => ({
      ...prev,
      currentView: 'input',
      execution: null,
      executionState: 'idle',
      error: null,
      preselectedExecutionId: undefined,
    }));
  };

  /**
   * Toggle sidebar open/closed - triggered by hamburger menu or similar
   */
  // const toggleSidebar = () => {
  //   setState((prev) => ({
  //     ...prev,
  //     sidebarOpen: !prev.sidebarOpen,
  //   }));
  // };

  /**
   * Close sidebar
   */
  const closeSidebar = () => {
    setState((prev) => ({
      ...prev,
      sidebarOpen: false,
    }));
  };

  /**
   * Load history items
   */
  useEffect(() => {
    const loadHistory = async () => {
      setState((prev) => ({
        ...prev,
        historyLoading: true,
      }));
      try {
        const response = await apiClient.getExecutionHistory(10, 0);
        setState((prev) => ({
          ...prev,
          historyItems: response.executions,
          historyLoading: false,
        }));
      } catch (err) {
        console.error('Failed to load history:', err);
        setState((prev) => ({
          ...prev,
          historyLoading: false,
        }));
      }
    };

    loadHistory();
  }, []);

  /**
   * Handle sidebar item click - show full history page
   */
  const handleSidebarHistoryClick = () => {
    goToHistory();
    closeSidebar();
  };

  return (
    <div className="app-layout">
      <div className="app-main">
        <div className="app-content">
          {state.currentView === 'input' && (
            <GoalInputPage
              onSubmit={handleGoalSubmit}
              isLoading={state.executionState === 'loading'}
              onHistoryClick={goToHistory}
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

          {state.currentView === 'history' && (
            <HistoryPage onBack={backFromHistory} preselectedExecutionId={state.preselectedExecutionId} />
          )}
        </div>
      </div>

      {state.sidebarOpen && <div className="sidebar-backdrop" onClick={closeSidebar} />}

      <aside className={`sidebar ${state.sidebarOpen ? 'open' : ''}`}>
        <div className="sidebar-header">
          <div className="sidebar-icon">H</div>
          <div className="sidebar-title">History</div>
          <button
            className="sidebar-close"
            onClick={closeSidebar}
            style={{
              background: 'none',
              border: 'none',
              color: '#6b7280',
              fontSize: '20px',
              cursor: 'pointer',
              padding: '0 8px',
              display: 'none',
            }}
          >
            ×
          </button>
        </div>
        <div className="sidebar-content">
          <div className="sidebar-section">
            <div className="sidebar-section-title">Recent Executions</div>
            <div className="sidebar-list">
              {state.historyLoading && (
                <div className="sidebar-item">
                  <div className="sidebar-item-icon">...</div>
                  <div className="sidebar-item-content">
                    <div className="sidebar-item-title">Loading...</div>
                  </div>
                </div>
              )}
              {!state.historyLoading && state.historyItems.length === 0 && (
                <div className="sidebar-item">
                  <div className="sidebar-item-icon">-</div>
                  <div className="sidebar-item-content">
                    <div className="sidebar-item-title">No executions yet</div>
                    <div className="sidebar-item-meta">Run an analysis to see it here</div>
                  </div>
                </div>
              )}
              {!state.historyLoading && state.historyItems.length > 0 && (
                <>
                  {state.historyItems.map((item) => {
                    const displayStatus = item.status === 'success' ? '✓' : item.status === 'error' ? '✗' : '⟳';
                    const statusColor = item.status === 'success' ? '#10a37f' : item.status === 'error' ? '#dc3545' : '#6b7280';
                    return (
                      <div
                        key={item.execution_id}
                        className="sidebar-item"
                        style={{ cursor: 'pointer' }}
                        onClick={() => {
                          setState((prev) => ({
                            ...prev,
                            currentView: 'history',
                            preselectedExecutionId: item.execution_id,
                            sidebarOpen: false,
                          }));
                        }}
                      >
                        <div className="sidebar-item-icon" style={{ color: statusColor }}>
                          {displayStatus}
                        </div>
                        <div className="sidebar-item-content">
                          <div className="sidebar-item-title">{item.goal.substring(0, 40)}{item.goal.length > 40 ? '...' : ''}</div>
                          <div className="sidebar-item-meta">
                            {new Date(item.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                  <div
                    className="sidebar-item"
                    style={{ cursor: 'pointer', borderTop: '1px solid #e5e7eb', marginTop: '8px', paddingTop: '8px' }}
                    onClick={handleSidebarHistoryClick}
                  >
                    <div className="sidebar-item-icon">→</div>
                    <div className="sidebar-item-content">
                      <div className="sidebar-item-title">View all history</div>
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </aside>
    </div>
  );
}

export default App;
