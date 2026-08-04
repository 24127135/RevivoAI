# RevivoAI

RevivoAI is an autonomous, agentic modernization pipeline. It reads legacy code, securely provisions isolated Docker sandboxes, leverages Large Language Models (LLMs) to refactor and modernize the syntax, and verifies the safety of the output through automated testing before presenting the results in a real-time reactive UI.

---

## Part 1: Quick Start (Zero-to-Hero Setup)

If you are setting this up for the first time, follow these steps to get the pipeline running locally.

### Prerequisites

1. Docker Desktop
   - Docker must be installed and running in the background for the sandbox environment to work.
   - Windows users should enable WSL2 integration in Docker Desktop settings.
2. Python and Poetry
   - Install Python 3.10 or newer.
   - Install Poetry from https://python-poetry.org/docs/.

### Installation

1. Clone the repository and navigate into the project folder.
2. Install the project dependencies with Poetry:

```bash
poetry install
```

3. Create a .env file in the repository root with the required environment variables:

```bash
GEMINI_API_KEY=your_google_gemini_api_key
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key
```

If you do not need remote persistence, you can also set:

```bash
DISABLE_SUPABASE=true
```

### Running the application

Start the app with:

```bash
poetry run python app.py
```

If you want to run the backend API explicitly, you can also start it with:

```bash
poetry run python -m uvicorn backend.main:app --port 8000 --reload
```

Once the server starts, open http://localhost:8501/ in your browser to access the UI.

---

## Part 2: Developer Architecture & Mechanics Reference

RevivoAI is intentionally decoupled into a frontend layer, backend orchestration layer, and isolated execution environment.

### Core tech stack

- Frontend: NiceGUI for the reactive browser-based UI
- Backend: FastAPI for API routing and WebSocket management
- Database: Supabase (PostgreSQL) for session persistence and execution logging
- Orchestrator: LangGraph for the AgentState state machine that coordinates the LLM, sandbox, and telemetry nodes

### Crucial server-side mechanics

#### Docker permission handshake

To prevent permission errors when AI-generated code writes files into the host-mounted workspace, the sandbox container is started as root initially so the daemon can run the workspace ownership fix. The untrusted generated code is then executed as a restricted user inside an isolated, network-disabled environment.

#### WebSocket telemetry loop

LangGraph waits for a node to finish before updating the global state, which can make the UI appear frozen during long-running LLM or sandbox operations. The backend uses an emit_log helper to push fresh log events into a temporary state object and broadcast them over WebSockets mid-execution so the UI remains responsive.

#### Bulletproof parsing

The patching node uses flexible substring matching for contract checks instead of relying on brittle exact-prefix logic. This avoids false refusals caused by common AI markdown artifacts such as extra whitespace or bullet formatting.

#### Strict time synchronization

The host machine running the backend should have its system clock synchronized with NTP. A clock that is even a minute ahead can cause the Supabase PostgREST gateway to reject JWT tokens with a PGRST303 / 401 Unauthorized error, breaking session persistence.

#### Persona enforcement and global directives

The AI engine defaults to a strict python_modernizer persona. The global refactoring directives instruct the model to modernize the full file aggressively while preserving the original invariants and public APIs rather than making a single minimal edit.

### Project layout

```text
.
├── app.py                  # NiceGUI entry point and main UI state
├── pyproject.toml          # Poetry dependencies and pytest settings
├── backend/                # FastAPI, orchestration, session, and sandbox logic
├── core/                   # Shared database helpers
├── frontend/               # UI components, Monaco editor, and styling
├── revivo_workspace/       # Legacy parser and type-sorting utilities
├── sql/                    # SQL seeds and execution log references
├── tests/                  # Pytest suite and contributor guidelines
└── tmp/                    # Temporary workspace for local experiments
```

### Testing

Run the suite from the repository root:

```bash
poetry run pytest
```

Useful variants:

```bash
poetry run pytest tests/backend/
poetry run pytest tests/test_frontend_runtime.py
```

If Supabase is not configured, the app and tests will fall back to local mock clients automatically.

### Notes for contributors

- Keep UI code in the frontend layer and orchestration logic in the backend layer.
- Prefer small, focused changes and add or update tests when behavior changes.
- For local development, set DISABLE_SUPABASE=true unless you specifically need remote persistence.
