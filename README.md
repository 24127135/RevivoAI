# RevivoAI 🔬 — NiceGUI Architecture Guide

RevivoAI is a legacy code modernization tool that leverages AI to draft patches and an autonomous Docker sandbox to verify them.

This repository currently represents the **frontend wireframe and core architecture** for a NiceGUI-based experience. The app is intentionally structured into a decoupled frontend/backend pattern so the browser UI stays lightweight while heavier background processing (Docker, MCP, LLMs, orchestration) can be added later without changing the presentation layer.

---

## ⚙️ Installation & Running the App

RevivoAI is built with NiceGUI and uses **Poetry** for dependency management. The app runs directly via the Python interpreter.

### Prerequisites
* **Python 3.9+** installed on your machine.
* **Poetry** installed on your machine.
  * If you do not already have Poetry installed, follow the official installation guide:
    https://python-poetry.org/docs/#installation
  * After installation, verify it is available by running:
    ```bash
    poetry --versionGet-Command poetry -All
    ```
* **(Highly Recommended) Nerd Fonts:** To view the code blocks, tracebacks, and UI badges with the intended neobrutalist developer aesthetic, install a Nerd Font such as JetBrainsMono, FiraCode, or Hack.
  * The CSS looks for those fonts first and will safely fall back to standard monospace fonts if they are not available.

### Setup Instructions
Run with Administrator!

1. **Clone or navigate to the repository folder:**
   ```bash
   cd path/to/revivo_ai
   ```

2. **Create a virtual environment (Recommended):**
   ```bash
   python -m venv .venv
   ```

3. **Activate the virtual environment:**
   * **Windows:** `.venv\Scripts\activate`
   * **Mac/Linux:** `source .venv/bin/activate`

4. **Install project dependencies:**

   ```bash
   poetry install
   ```

5. **Run the application:**
   ```bash
   poetry run python app.py
   ```

   NiceGUI will open the application in your default web browser.

6. **Run the tests:**
  ```bash
  poetry run pytest
  ```

  This executes the backend tests under `tests/backend/`.

---

## 📂 Directory Structure

```text
.
├── app.py                  # Main NiceGUI application entry point and routing
├── pyproject.toml          # Project dependencies and tooling
├── backend/                # Pure Python logic with no UI dependencies
│   ├── __init__.py         # Package marker for backend imports
│   ├── import_utils.py     # File ingestion and directory traversal
│   ├── logic.py            # Traceback parsing and error-frame analysis
│   ├── models.py           # Dataclasses, enums, and state contracts
│   ├── nodes.py            # AST / structural parsing nodes for orchestration
│   ├── orchestrator.py     # LangGraph state schema and router wrapper
│   ├── mcp_client.py       # Local MCP-style filesystem client used by the demo
│   └── seed.py             # Hardcoded fixtures and mock data for UI testing
└── frontend/               # NiceGUI presentation layer
    ├── components.py       # Reusable UI widgets, loaders, and diff views
    └── styles.py           # Global neobrutalist CSS design system
└── tests/                  # Pytest-based test suite
    └── README.md           # Development standards and guidelines
    └── backend/            # MCP client and AST parser coverage
```

---

## 📄 File Dictionary

### Root
* **app.py**
  The entry point of the app. It wires together the NiceGUI UI, state management, user interactions, and high-level control flow for transitions such as `QUEUED` → `TRANSLATING` → `SANDBOX_TESTING`.
* **pyproject.toml**
  Dependencies and build configuration managed by Poetry.

### backend/
* **models.py**
  The source of truth for the app. Contains the `ProjectFile` dataclass and `FileStatus` enum. The UI reacts to changes in these objects rather than owning its own separate state model.
* **logic.py**
  Contains traceback parsing and error-frame analysis logic used to render the review experience.
* **import_utils.py**
  Handles reading files from the user. Includes upload-oriented helpers and recursive directory traversal for local project imports.
* **nodes.py**
  Contains the `ASTParserNode` used by the orchestration layer to inspect the current file, extract structural context, and flag parsing errors.
* **orchestrator.py**
  Defines the LangGraph `AgentState` schema and a minimal router wrapper for the backend workflow.
* **mcp_client.py**
  Provides the local MCP-style filesystem client used by the demo/test workflow.
* **seed.py**
  Contains mock legacy code, mock AI outputs, and mock tracebacks used by the demo mode.

### tests/
* **tests/README.md**
  Team Standards: Defines naming conventions, mocking strategies, and CI/CD readiness.
* **tests/backend/**
  Contains the pytest coverage for the backend pieces, including MCP client I/O and AST parser behavior.

### frontend/
* **styles.py**
  Contains the `get_css()` function for the neobrutalist visual system and the CSS overrides used by the NiceGUI layout.
* **components.py**
  Holds reusable NiceGUI renderers for loaders, code viewers, and diff panels.

---

## 🚀 Futureproofing & Backend Transition Guide

The current codebase mocks the AI generation and sandbox testing steps while preserving a clean separation between UI and backend concerns. Because of that decoupled architecture, adding a real backend later should require minimal changes to the presentation layer.

When you are ready to begin the backend engineering phase, follow this roadmap:

### Phase 1: Integrating MCP / LLMs
1. Integrate `backend/mcp_client.py` with the real MCP or LLM backend.
2. Write a function that accepts a `ProjectFile`'s `legacy_source`, communicates with your LLM through the Model Context Protocol, and returns a translated string.
3. In `app.py`, replace the hardcoded mock assignment in the transition flow with your real function.

### Phase 2: Integrating Docker
1. Create `backend/docker_runner.py`.
2. Write a function that takes the generated source, starts an ephemeral Docker container, executes the test suite, and captures `stdout`/`stderr`.
3. Feed that output into the existing traceback parsing logic so the NiceGUI experience can render failures and successes consistently.

### Phase 3: Asynchronous Orchestration
Long-running work should be moved into background workers so the NiceGUI UI stays responsive. A task queue such as Celery, Redis-backed workers, or LangGraph can drive the pipeline while the UI polls for updates or listens for state changes.

The current orchestration state already tracks `current_file`, `current_code`, and an optional `structural_context` payload. The `ASTParserNode` updates that structural context from the selected file and marks `ui_status = PARSING_ERROR` when the file cannot be parsed as Python or R.

The transition pattern is:
1. Trigger a background job from the NiceGUI action handler.
2. Update the relevant `ProjectFile` state as the job progresses.
3. Refresh the UI from the updated state without blocking the main event loop.