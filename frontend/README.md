# Agentic AI System - Frontend

Professional observability layer for the Agentic AI backend.

## Overview

This frontend visualizes agentic system behavior:
- **Goal Input View**: Accept high-level goals
- **Execution Viewer**: Real-time step-by-step execution trace
- **Result Panel**: Final outputs and execution metadata

The frontend treats the backend as a black-box API.

## Tech Stack

- React 18 + Vite
- TypeScript
- Plain CSS (minimal, no frameworks)
- Fetch API

## Setup

### Prerequisites

- Node.js 16+
- npm or yarn

### Installation

```bash
cd frontend
npm install
```

### Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Update `VITE_API_URL` if your backend is running on a different host/port.

## Running

### Development Server

```bash
npm run dev
```

Default: `http://localhost:5173`

### Production Build

```bash
npm run build
```

### Preview Build

```bash
npm run preview
```

## Project Structure

```
src/
├── components/         # Reusable components
│   └── ResultPanel.tsx
├── pages/              # Page components (views)
│   ├── GoalInputPage.tsx
│   └── ExecutionViewerPage.tsx
├── services/           # API client
│   └── apiClient.ts
├── types/              # TypeScript types
│   └── api.ts
├── styles/             # CSS files
│   └── index.css       # Global + view-specific styles
├── App.tsx             # Main app component
├── main.tsx            # Entry point
└── index.html          # HTML template
```

## API Integration

The frontend communicates with the backend via:

- **POST /api/execute** - Execute a goal
- **GET /health** - Health check

See [src/services/apiClient.ts](src/services/apiClient.ts) for implementation.

### Backend Expectations

The backend must return `ExecuteResponse`:

```typescript
interface ExecuteResponse {
  execution_id: string;
  goal: string;
  status: 'completed' | 'failed' | 'partial';
  steps_completed: StepResult[];
  final_result: unknown;
  error: string | null;
  timestamp: string;
}

interface StepResult {
  step_number: number;
  tool_name: string;
  success: boolean;
  output: unknown;
  error: string | null;
}
```

## Styling

All styles are in plain CSS (no Tailwind or UI frameworks).

- **src/index.css** - Global styles + view-specific component styles

Professional color scheme and recruiter-friendly layout.

## Code Quality

- ✓ TypeScript with strict type checking
- ✓ Typed API responses via interfaces
- ✓ Reusable API client service
- ✓ Component-based architecture
- ✓ Clear separation of concerns
- ✓ Responsive design

## Deployment

For production:

```bash
npm run build
# Output: dist/
# Serve dist/ directory with any static server
```

## Troubleshooting

### API Not Found

Ensure backend is running on `http://localhost:8000` or update `VITE_API_URL` in `.env`

### CORS Issues

The Vite dev server proxies `/api` and `/health` to the backend. For production, ensure CORS is configured on the backend:

```python
# In backend's fastapi app
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or specify your frontend URL
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Build Errors

Clear cache and rebuild:

```bash
rm -rf node_modules dist .vite
npm install
npm run build
```

## Architecture Notes

### Backend as Black-Box

The frontend:
- Does NOT know about agent internals
- Does NOT duplicate planning/execution logic
- Only displays what the backend returns
- Is replaceable without changing backend

### Component Design

- **Presentational**: UI components only (ResultPanel, GoalInputPage, ExecutionViewerPage)
- **Container**: App component handles state and async logic
- **Services**: apiClient handles all backend communication

### State Management

Simple React hooks (useState) for phase 1. No Redux, Zustand, or global state management needed.

## Future Enhancements (Out of Scope)

- WebSocket for real-time step execution
- Step cancellation UI
- Execution history/replay
- Advanced filtering and search
- Dark mode toggle
- Keyboard shortcuts
import reactDom from 'eslint-plugin-react-dom'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...
      // Enable lint rules for React
      reactX.configs['recommended-typescript'],
      // Enable lint rules for React DOM
      reactDom.configs.recommended,
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```
