# RevivoAI Testing Guide

This document captures the testing conventions used in the current repository. The suite is designed to be fast, deterministic, and friendly to local development, even when optional services such as Supabase or Docker are unavailable.

## Quick start

Run tests from the repository root with Poetry:

```bash
poetry run pytest
```

Useful variants:

```bash
# run all backend tests
poetry run pytest tests/backend/

# run frontend runtime tests
poetry run pytest tests/test_frontend_runtime.py

# verbose output
poetry run pytest -v

# run a single test file (quiet)
poetry run pytest tests/backend/test_nodes.py -q

# run tests matching an expression
poetry run pytest -k "session_handler" -q

# run with coverage (if available)
poetry run pytest --cov=backend --cov-report=term-missing
```

## Test layout

- Root tests cover high-level app and frontend runtime behavior.
- Backend tests live under tests/backend/ and focus on orchestration, sandbox, logger, and session logic.
- The current project does not maintain a separate tests/frontend/ directory; use the root-level frontend runtime tests instead.

## Naming conventions

Mirror the production module names in the test file paths and use descriptive snake_case names:

- backend/module.py -> tests/backend/test_module.py
- app.py -> tests/test_app_payload.py

Prefer this style:

```python
def test_session_handler_initializes_session_with_mock_client():
    ...
```

Avoid vague names such as test_something or test_bug.

## Writing tests

### Prefer real behavior over heavy mocking

Use mocks at the system boundary only. The project already provides local fallbacks for Supabase and related services, so tests should exercise the real logic whenever possible.

Good examples:

- Mock external LLM or Docker calls when testing orchestration flow
- Use temporary directories for file-system work
- Assert on observable behavior such as returned state, emitted logs, or raised exceptions

### Use fixtures for setup and cleanup

```python
import shutil
import pytest

@pytest.fixture
def temp_workspace(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    yield workspace
    shutil.rmtree(workspace, ignore_errors=True)
```

### Keep prompt and output-contract tests explicit

When testing LLM patching or orchestration nodes, assert that the generated prompt or structured response contains the expected contract cues. This keeps the patching protocol intentional and easier to evolve.

## Environment notes

- Set `DISABLE_SUPABASE=true` for local runs that should not rely on remote persistence.
- Avoid requiring Docker during unit tests unless the test is specifically about sandbox behavior.
- If a dependency is not available, prefer a small stub or monkeypatch over a brittle full integration setup.

Tips:

- Run tests with Supabase disabled locally:

```bash
DISABLE_SUPABASE=true poetry run pytest
```

- To run Docker-dependent sandbox integration tests, ensure Docker Desktop and WSL2 (Windows) are running and invoke only those tests.

- Use `tmp_path` / `tmp_path_factory` fixtures to isolate filesystem work and avoid polluting the repo.
