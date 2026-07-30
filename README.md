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

---

## 📂 Directory Structure

```text
.
├── app.py                  # Main NiceGUI application entry point and routing
├── pyproject.toml          # Project dependencies and tooling
├── backend/                # Pure Python logic with no UI dependencies
│   ├── import_utils.py     # File ingestion and directory traversal
│   ├── logic.py            # AST parsing, traceback parsing, and diff generation
│   ├── models.py           # Dataclasses, enums, and state contracts
│   └── seed.py             # Hardcoded fixtures and mock data for UI testing
└── frontend/               # NiceGUI presentation layer
    ├── components.py       # Reusable UI widgets, loaders, and diff views
    └── styles.py           # Global neobrutalist CSS design system
```

---

## 📄 File Dictionary

### Root
* **app.py**
  The entry point of the app. It wires together the NiceGUI UI, state management, user interactions, and high-level control flow for transitions such as `QUEUED` → `TRANSLATING` → `SANDBOX_TESTING`.

### backend/
* **models.py**
  The source of truth for the app. Contains the `ProjectFile` dataclass and `FileStatus` enum. The UI reacts to changes in these objects rather than owning its own separate state model.
* **logic.py**
  Contains the diff engine, syntax-highlighting helpers, and traceback parsing logic used to render the review experience.
* **import_utils.py**
  Handles reading files from the user. Includes upload-oriented helpers and recursive directory traversal for local project imports.
* **seed.py**
  Contains mock legacy code, mock AI outputs, and mock tracebacks used by the demo mode.

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
1. Create `backend/mcp_client.py`.
2. Write a function that accepts a `ProjectFile`'s `legacy_source`, communicates with your LLM through the Model Context Protocol, and returns a translated string.
3. In `app.py`, replace the hardcoded mock assignment in the transition flow with your real function.

### Phase 2: Integrating Docker
1. Create `backend/docker_runner.py`.
2. Write a function that takes the generated source, starts an ephemeral Docker container, executes the test suite, and captures `stdout`/`stderr`.
3. Feed that output into the existing traceback parsing logic so the NiceGUI experience can render failures and successes consistently.

### Phase 3: Asynchronous Orchestration
Long-running work should be moved into background workers so the NiceGUI UI stays responsive. A task queue such as Celery, Redis-backed workers, or LangGraph can drive the pipeline while the UI polls for updates or listens for state changes.

The transition pattern is:
1. Trigger a background job from the NiceGUI action handler.
2. Update the relevant `ProjectFile` state as the job progresses.
3. Refresh the UI from the updated state without blocking the main event loop.