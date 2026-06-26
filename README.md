# RevivoAI 🔬 — UI Wireframe & Architecture Guide

RevivoAI is a legacy code modernization tool that leverages AI to draft patches and an autonomous Docker sandbox to verify them. 

This repository currently represents the **Frontend Wireframe and Core Architecture**. It has been intentionally structured into a decoupled Frontend/Backend pattern to ensure that the Streamlit UI remains lightweight and completely agnostic to the heavy background processing (Docker, MCP, LLMs) that will be implemented in the next phase.

---

## ⚙️ Installation & Running the App

Since RevivoAI is built with Streamlit, it does not need to be compiled. It runs directly via the Python interpreter.

### Prerequisites
* **Python 3.9+** installed on your machine.
* **(Highly Recommended) Nerd Fonts:** To view the code blocks, tracebacks, and UI badges with the intended Neobrutalist developer aesthetic, you should have a "Nerd Font" installed on your system. 
  * The CSS specifically looks for **JetBrainsMono Nerd Font**, **FiraCode Nerd Font**, or **Hack Nerd Font**.
  * You can download them for free from [nerdfonts.com](https://www.nerdfonts.com/font-downloads). 
  * *Note: If you do not have one installed, the UI will safely fall back to standard system monospace fonts (like Consolas) without breaking.*

### Setup Instructions

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

4. **Install the dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

5. **Run the Application:**
   ```bash
   streamlit run app.py
   ```
   *Streamlit will automatically compile the UI and open the application in your default web browser at `http://localhost:8501`.*

---

## 📂 Directory Structure

```text
.
├── app.py                  # Main Streamlit application & routing
├── requirements.txt        # Minimal Python dependencies
├── backend/                # Pure Python logic (Zero Streamlit dependencies)
│   ├── import_utils.py     # File ingestion and directory traversal
│   ├── logic.py            # AST parsing, Traceback parsing, and Diff Engine
│   ├── models.py           # Dataclasses, Enums, and State contracts
│   └── seed.py             # Hardcoded fixtures and mock data for UI testing
└── frontend/               # Streamlit-specific presentation layers
    ├── components.py       # Reusable UI widgets (Loaders, Diff tables)
    └── styles.py           # Global Neobrutalism CSS design system
```

---

## 📄 File Dictionary

### Root
* **`app.py`** 
  The entry point of the application. It handles Streamlit state management (`st.session_state`), user interactions (button clicks, batch actions), and high-level control flow (e.g., routing a file from `QUEUED` ➡️ `TRANSLATING` ➡️ `SANDBOX_TESTING`). 

### `backend/` (Data & Logic Layer)
* **`models.py`**
  The absolute source of truth for the app. Contains the `ProjectFile` dataclass and the `FileStatus` enum. **Rule of thumb:** The UI simply reacts to changes in `ProjectFile`. 
* **`logic.py`**
  The "brain" of the wireframe. Contains the `difflib` sequence matching for generating code comparisons, Pygments tokenization for syntax highlighting, and regex parsers for extracting actionable stack frames from Python/C/R tracebacks.
* **`import_utils.py`**
  Handles reading files from the user. Includes `import_from_streamlit_uploads` (for isolated file inputs) and `import_local_project` (for recursive OS directory tree mapping).
* **`seed.py`**
  Contains mock legacy code, mock AI outputs, and mock tracebacks. Used strictly for the "Load Demo Project" mode to test UI styling and transitions without needing an active LLM.

### `frontend/` (Presentation Layer)
* **`styles.py`**
  Contains the `get_css()` function. This encapsulates the entire **Neobrutalism Design System** (fonts, colors, hard shadows, thick borders) and targeted Streamlit DOM overrides to prevent CSS bleed in the main `app.py` file.
* **`components.py`**
  Contains reusable HTML/Streamlit renderers. Most notably, it houses the animated logic for the pulsing UI loading states.

---

## 🚀 Futureproofing & Backend Transition Guide

The codebase currently mocks the AI generation (U001/U002) and Sandbox testing (U003) using `time.sleep()` and `st.spinner()`. 

Because of the decoupled architecture, transitioning to the real backend requires **zero changes to the UI presentation files (`frontend/`)**. The UI only cares about the properties inside the `ProjectFile` object.

When you are ready to begin the backend engineering phase, follow this roadmap:

### Phase 1: Integrating MCP / LLMs (Replacing U001 & U002)
1. Create `backend/mcp_client.py`.
2. Write a function that accepts a `ProjectFile`'s `legacy_source`, communicates with your LLM via the Model Context Protocol to understand the workspace, and returns a translated string.
3. In `app.py`, locate the `transition_to_sandbox()` function. Replace the hardcoded mock assignment with your real function:
   ```python
   # BEFORE (Mock)
   f.ai_source = "# AI Translated...\n" + f.legacy_source
   
   # AFTER (Real)
   f.ai_source = mcp_client.generate_patch(f.legacy_source, context=workspace_context)
   ```

### Phase 2: Integrating Docker (Replacing U003)
1. Create `backend/docker_runner.py`.
2. Write a function that takes the `ai_source`, spins up an ephemeral, non-root Docker container, mounts the workspace volume, executes the test suite, and captures `stdout`/`stderr`.
3. In `app.py`, locate `resolve_sandbox_now()`. Replace the mock logic by feeding the real Docker output into the existing `logic.py` traceback parser:
   ```python
   # Real Docker Execution
   exit_code, stderr = docker_runner.execute_tests(f.ai_source)
   
   if exit_code != 0:
       f.status = FileStatus.FAILED
       f.raw_traceback = stderr  # The UI will automatically parse and render this!
   else:
       f.status = FileStatus.PASSED
   ```

### Phase 3: Asynchronous Orchestration (LangGraph / Celery)
Currently, `app.py` uses `st.spinner()` and `time.sleep()`, which blocks the Streamlit main thread. When moving to production, LLM generation and Docker builds will take minutes, meaning the UI would completely freeze if left this way. 

To fix this, we decouple the execution from the UI using a background worker:

1. **Create `backend/orchestrator.py`**
   This file will use a task queue (like Celery, Redis, or LangGraph). It receives a file ID, runs `mcp_client` and `docker_runner` in the background, and updates a database/state store with the status.
   
2. **Update UI Dispatch (`app.py`)**
   Instead of running the translation directly, the button click simply hands the job to the orchestrator and updates the UI state.
   ```python
   # BEFORE (Blocking)
   transition_to_sandbox(active_id)
   
   # AFTER (Fire and Forget)
   orchestrator.trigger_pipeline_async(active_id)
   f.status = FileStatus.TRANSLATING
   ```
   
3. **Update UI Polling (`app.py`)**
   While the file is processing, the UI will just "poll" the backend database every few seconds to see if the background worker finished, keeping the UI completely responsive.
   ```python
   # Inside the TRANSLATING / SANDBOX_TESTING block
   if f.status in (FileStatus.TRANSLATING, FileStatus.SANDBOX_TESTING):
       
       # Check the database to see what the background worker is doing
       latest_backend_state = orchestrator.check_job_status(active_id)
       
       # If the background worker moved to the next step, update the UI!
       if latest_backend_state.status != f.status:
           f.status = latest_backend_state.status
           f.ai_source = latest_backend_state.ai_source
           f.raw_traceback = latest_backend_state.raw_traceback
           st.rerun() 
       
       # If it's still working, wait 2 seconds and check again
       else:
           time.sleep(2)
           st.rerun()
   ```