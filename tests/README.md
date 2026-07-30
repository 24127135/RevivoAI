# RevivoAI: Testing & Development Guidelines

Welcome to the RevivoAI test suite. This document serves as the source of truth for all testing standards, naming conventions, and environment configurations. 

## 🎯 Our Philosophy
We aim for **high test coverage** and **low friction**. Tests should be fast, reliable, and descriptive. If you are blocked by an incomplete module, do not wait—use a Mock.

---

## 🚀 Quick Start
All tests must be executed via `poetry` to ensure the correct virtual environment and path resolutions are used.

### Basic Commands
| Action | Command |
| :--- | :--- |
| **Run all tests** | `poetry run pytest` |
| **Run Backend tests** | `poetry run pytest tests/backend/` |
| **Run Frontend tests** | `poetry run pytest tests/frontend/` |
| **Run with Verbose Logs** | `poetry run pytest -v` |

---

## 📝 Naming Conventions (The Contract)
Consistent naming allows us to understand failure logs without opening the file.

### File Naming
Mirror the source directory.
*   `backend/module.py` ➔ `tests/backend/test_module.py`
*   `frontend/components.py` ➔ `tests/frontend/test_components.py`

### Test Function Naming
Use the `Given_When_Then` pattern in `snake_case`.
*   **Pattern:** `test_<component>_<scenario>_<expected_behavior>`
*   **Good:** `test_mcp_client_invalid_path_raises_permission_error()`
*   **Bad:** `test_mcp_error()`

---

## 🛠 Writing Tests: Best Practices

### 1. Use Fixtures
For setup/teardown (e.g., creating/deleting temporary workspaces), use `pytest.fixture`. This prevents "zombie files" from cluttering your disk.
```python
@pytest.fixture
def temp_workspace():
    # Setup
    os.makedirs("./temp")
    yield "./temp"
    # Teardown
    shutil.rmtree("./temp")