# RevivoAI

RevivoAI is an autonomous, agentic modernization pipeline. It reads legacy code (Python, C, R), leverages Large Language Models to refactor and modernize the syntax, securely provisions isolated Docker sandboxes to verify the output through automated testing, and presents the results in a real-time reactive UI with side-by-side diff viewing, structured telemetry, and session persistence.

---

## Part 1: Quick Start (Zero-to-Hero Setup)

If you are setting this up for the first time, follow these steps to get the pipeline running locally.

### Prerequisites

1. **Docker Desktop**
   - Docker must be installed and running in the background for the sandbox environment to work.
   - Windows users should enable WSL2 integration in Docker Desktop settings.
2. **Python and Poetry**
   - Install Python 3.10 or newer.
   - Install Poetry from https://python-poetry.org/docs/.

### Installation

1. Clone the repository and navigate into the project folder.
2. Install the project dependencies with Poetry:

```bash
poetry install
```

3. Create a `.env` file in the repository root with the required environment variables:

```bash
# .env (example)
GEMINI_API_KEY=your_google_gemini_api_key
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key
```

If you do not need remote persistence for local development or CI, set:

```bash
DISABLE_SUPABASE=true
```

### Running the application

RevivoAI runs two processes: a **NiceGUI frontend** (port 8501) and a **FastAPI backend** (port 8000). Start them in two separate terminals:

```bash
# Terminal 1 — Frontend (NiceGUI reactive UI)
poetry run python app.py

# Terminal 2 — Backend API (FastAPI + WebSocket + orchestrator)
poetry run python -m uvicorn backend.main:app --port 8000 --reload
```

Once both servers start, open **http://localhost:8501/** in your browser to access the UI.

---

## Part 2: Developer Architecture & Mechanics Reference

RevivoAI is intentionally decoupled into a frontend layer, backend orchestration layer, and isolated execution environment.

### Core tech stack

| Layer         | Technology                                                                        |
|---------------|-----------------------------------------------------------------------------------|
| Frontend      | NiceGUI 3.x — reactive browser-based UI with Quasar components                   |
| Code Editor   | Monaco Editor — side-by-side diff viewer, syntax highlighting, debounced editing  |
| Terminal      | Custom Vue 3 structured terminal — btop-inspired, q-virtual-scroll, delta log push|
| File Tree     | Lazy-loaded Quasar QTree — ephemeral UI state, async directory scanning, search   |
| Backend API   | FastAPI — REST endpoints, WebSocket management, static file serving               |
| Orchestrator  | LangGraph StateGraph — cyclic state machine (LLM → Sandbox → Telemetry → retry)  |
| LLM Provider  | Google Gemini (via `google-genai` SDK, default model: `gemini-3.5-flash-lite`)    |
| Sandbox       | Docker — ephemeral, network-disabled, non-root containers with memory/CPU limits  |
| Database      | Supabase (PostgreSQL) — session persistence, execution logging (with mock fallback)|
| File I/O      | MCP Client — path-validated filesystem operations with traversal protection       |
| Design System | Neo-brutalist CSS design system with Quasar overrides                             |

### Key backend modules

| Module                | Purpose                                                                  |
|-----------------------|--------------------------------------------------------------------------|
| `backend/main.py`     | FastAPI app, route mounting, WebSocket endpoint, orchestrator dispatch    |
| `backend/orchestrator.py` | LangGraph state machine: `llm_patch_node` → `sandbox_node` → `telemetry_node` with conditional retry routing |
| `backend/nodes.py`    | Stateless AST parsing nodes, LLM patch node, import validation           |
| `backend/sandbox.py`  | Docker sandbox lifecycle: create → inject → run → destroy                |
| `backend/llm_client.py` | Gemini client wrapper implementing the `generate` protocol             |
| `backend/session_handler.py` | Session creation, persistence, workspace provisioning, expiry reaping |
| `backend/reaper.py`   | Background task with exponential backoff for expired session cleanup      |
| `backend/logger.py`   | Execution log persistence to Supabase `execution_logs` table             |
| `backend/websocket.py`| WebSocket manager with deep state serialization (dataclass, enum, Pydantic) |
| `backend/mcp_client.py` | Model Context Protocol client: path-validated `readFile`, `writeFile`, `listDirectory` |
| `backend/models.py`   | Data models: `ProjectFile`, `FileStatus` (8-state enum), `StackFrame`, `DiffRow` |
| `backend/personas.py` | Persona prompt composition: global refactoring directive + domain-specific roles  |
| `backend/logic.py`    | Traceback parsers (Python, R, C) and error-frame analysis helpers        |
| `backend/import_utils.py` | File import (upload & local project scan), lazy directory tree helpers |
| `backend/seed.py`     | Seed data: 11 demo files across Python, C, and R with pre-computed AI patches |

### LangGraph orchestration flow

```text
START → llm_patch_node → sandbox_node → telemetry_node
                                              │
                                   ┌──────────┴──────────┐
                                   │ route_after_telemetry│
                                   └──────┬───────────────┘
                              exit_code == 0?
                                  │           │
                                 yes          no (& iterations < max)
                                  │           │
                                 END    llm_patch_node (retry)
```

The orchestrator supports up to 5 correction iterations (default 3). Each iteration broadcasts structured log deltas over WebSocket so the UI remains responsive during long-running LLM or sandbox operations.

### File status lifecycle

```text
QUEUED → TRANSLATING → SANDBOX_TESTING → PASSED ──→ APPROVED
                                       → FAILED ──→ (retry or manual edit)
                                                  → EDITED_PENDING → (re-test)
                                                  → REJECTED
```

### Crucial server-side mechanics

#### Docker permission handshake

To prevent permission errors when AI-generated code writes files into the host-mounted workspace, the sandbox container is started as root initially so the daemon can run the workspace ownership fix. The untrusted generated code is then executed as a restricted user (UID 1000) inside an isolated, network-disabled environment with configurable memory (4 GB) and CPU limits.

#### WebSocket telemetry loop

LangGraph waits for a node to finish before updating the global state, which can make the UI appear frozen during long-running LLM or sandbox operations. The backend uses an `emit_log` helper to push structured log deltas into a temporary state object and broadcast them over WebSockets mid-execution. Log entries carry pre-normalized, fixed-width fields for strictly columnar rendering:

```
HH:MM:SS | [SRC ] | STAT | message text
```

Source tags: `[LLM ]`, `[DKR ]`, `[TEST]`, `[TELM]`, `[SYS ]`. Status labels: `RUN `, `PASS`, `FAIL`, `WARN`, `INFO`.

#### Bulletproof parsing

The patching node uses flexible substring matching for contract checks instead of relying on brittle exact-prefix logic. This avoids false refusals caused by common AI markdown artifacts such as extra whitespace or bullet formatting.

#### Import validation

All AI-generated patches are validated at the AST level before sandbox execution. The `validate_patch_imports` function checks that only standard library and explicitly whitelisted packages are imported, preventing supply-chain injection from LLM hallucinations.

#### Strict time synchronization

The host machine running the backend should have its system clock synchronized with NTP. A clock that is even a minute ahead can cause the Supabase PostgREST gateway to reject JWT tokens with a PGRST303 / 401 Unauthorized error, breaking session persistence.

#### Persona enforcement and global directives

The AI engine defaults to a strict `python_modernizer` persona. Three built-in personas are available:

| Persona              | Domain                     | Key Rules                                             |
|----------------------|----------------------------|-------------------------------------------------------|
| `python_modernizer`  | Legacy Python codebases    | f-strings, enumerate, context managers, PEP 484 hints |
| `systems`            | xv6 kernel                 | `bread`/`bwrite`/`bmap`, `BSIZE` bound checks         |
| `data_science`       | Scikit-Learn / HuggingFace | Pipeline usage, vectorization                          |

All personas share a global refactoring directive that enforces invariant preservation, idiomatic modernization, a structured output protocol (`CHARACTERIZATION → REASONING → CODE → VERIFY → ASSUMPTIONS → ACTION`), and environment restrictions limiting imports to a whitelisted package set.

#### Session management

Sessions are backed by Supabase with automatic workspace provisioning, 2-hour expiry, and a background reaper task that runs every 5 minutes with exponential backoff and jitter to prevent thundering herd on the database.

#### MCP Client security

The Model Context Protocol client validates all filesystem paths against a configurable root, blocking directory traversal attacks with `Path.is_relative_to()` checks before any read, write, or list operation.

### Project layout

```text
.
├── .env                   # Local environment overrides (not checked in)
├── .gitignore
├── app.py                 # NiceGUI entry point (2300 lines) — UI state, rendering, WebSocket listener
├── pyproject.toml         # Poetry dependencies and pytest settings
├── poetry.lock
├── README.md
├── backend/               # FastAPI, orchestration, session, and sandbox logic
│   ├── __init__.py
│   ├── import_utils.py    # File import (upload/local scan) and lazy tree helpers
│   ├── llm_client.py      # Gemini API client wrapper
│   ├── logger.py          # Execution log persistence and sandbox result mapping
│   ├── logic.py           # Traceback parsers (Python/R/C) and error-frame analysis
│   ├── main.py            # FastAPI app, routes, WebSocket endpoint
│   ├── mcp_client.py      # MCP file I/O with path traversal protection
│   ├── models.py          # ProjectFile, FileStatus, StackFrame, DiffRow dataclasses
│   ├── nodes.py           # AST parser and LLM patch nodes, import validation
│   ├── orchestrator.py    # LangGraph state machine and emit_log telemetry
│   ├── personas.py        # Persona prompts and global refactoring directive
│   ├── reaper.py          # Background session cleanup with exponential backoff
│   ├── sandbox.py         # Docker sandbox lifecycle (create/inject/run/destroy)
│   ├── seed.py            # 11 demo files (Python, C, R) with pre-computed patches
│   ├── session_handler.py # Session CRUD, workspace provisioning, Supabase persistence
│   └── websocket.py       # WebSocket manager with deep state serialization
├── core/                  # Shared infrastructure
│   └── database.py        # Supabase client singleton with automatic mock fallback
├── frontend/              # UI components, Monaco editor, and styling
│   ├── components.py      # Phase constants for translating/sandbox progress indicators
│   ├── file_tree.py       # Custom NiceGUI element for hierarchical lazy file tree
│   ├── file_tree.js       # Vue 3 component with ephemeral UI state & search filter
│   ├── monaco_editor.py   # Monaco editor NiceGUI element with debounced event binding
│   ├── monaco_editor.js   # Vue 3 Monaco wrapper with 1000ms debouncing & diff support
│   ├── monaco_workers/    # Same-origin proxy scripts for Monaco Web Workers
│   │   ├── css.worker.js
│   │   ├── editor.worker.js
│   │   ├── json.worker.js
│   │   └── ts.worker.js
│   ├── structured_terminal.py  # Structured terminal NiceGUI element with delta log push
│   ├── structured_terminal.js  # Vue 3 btop-inspired terminal with q-virtual-scroll
│   └── styles.py          # Neo-brutalist design system & Quasar overrides (~1900 lines)
├── sql/                   # Database schema
│   └── execution_logs.sql # execution_logs table DDL (UUID PK, session FK, JSONB metadata)
├── tests/                 # Comprehensive pytest test suite (138 tests)
│   ├── README.md          # Testing conventions and guide
│   ├── backend/           # 13 test files
│   │   ├── test_lazy_import.py
│   │   ├── test_llm_patch_node.py
│   │   ├── test_logger.py
│   │   ├── test_main.py
│   │   ├── test_mcp_client.py
│   │   ├── test_nodes.py
│   │   ├── test_orchestrator.py
│   │   ├── test_reaper.py
│   │   ├── test_sandbox.py
│   │   ├── test_session_handler.py
│   │   ├── test_structured_logging.py
│   │   ├── test_websocket.py
│   │   └── test_worker_static.py
│   └── frontend/          # 4 test files
│       ├── test_app_payload.py
│       ├── test_frontend_runtime.py
│       ├── test_lazy_file_tree.py
│       └── test_structured_terminal.py
└── test_scripts/          # Real modernization test cases
    ├── 01_Global_State_Encapsulation.py
    ├── 02_Decoupling_The_God_Function.py
    └── 03_Synchronous_To_Asynchronous_Modernization.py
```

### Testing

Run the full suite (138 tests) from the repository root:

```bash
poetry run pytest
```

Useful variants:

```bash
# Backend tests only
poetry run pytest tests/backend/

# Frontend runtime tests only
poetry run pytest tests/frontend/

# Verbose output
poetry run pytest -v

# Run a single test file
poetry run pytest tests/backend/test_nodes.py -q

# Run tests matching a keyword
poetry run pytest -k "session_handler" -q

# Run with Supabase disabled (local mock fallback)
DISABLE_SUPABASE=true poetry run pytest
```

If Supabase is not configured, the app and tests will fall back to local mock clients automatically.

### Environment variables

| Variable                      | Required | Description                                         |
|-------------------------------|----------|-----------------------------------------------------|
| `GEMINI_API_KEY`              | Yes      | Google Gemini API key for LLM calls                 |
| `SUPABASE_URL`                | No       | Supabase project URL (mock fallback if missing)     |
| `SUPABASE_KEY`                | No       | Supabase anon key (also accepts `SUPABASE_SECRET_KEY` or `SUPABASE_SERVICE_ROLE_KEY`) |
| `DISABLE_SUPABASE`            | No       | Set to `true` to force mock client                  |
| `WORKSPACE_BASE_PATH`         | No       | Base directory for session workspaces (default: `/tmp/revivoai_workspaces`) |

### Notes for contributors

- Keep UI code in the `frontend/` layer and orchestration logic in the `backend/` layer.
- `app.py` is the main NiceGUI entry point and contains all UI rendering, state management, and WebSocket listener logic.
- Prefer small, focused changes and add or update tests when behavior changes.
- For local development, set `DISABLE_SUPABASE=true` unless you specifically need remote persistence.
- Run both the frontend (`app.py`) and backend (`uvicorn`) processes when testing the full pipeline.
- Use `tmp_path` / `tmp_path_factory` pytest fixtures to isolate filesystem work and avoid polluting the repo.
