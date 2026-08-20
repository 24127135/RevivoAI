import json
from unittest.mock import patch

import pytest

import app as app_module
from backend.models import FileStatus, ProjectFile


class FakeAsyncClient:
    def __init__(self):
        self.requests = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    # FIX: Added **kwargs so the mock can accept timeout=10.0 without crashing!
    async def post(self, url, json=None, **kwargs):
        self.requests.append((url, json))
        return type("Response", (), {"status_code": 200})()


class FakeWebSocket:
    def __init__(self, messages):
        self.messages = list(messages)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def recv(self):
        if self.messages:
            return self.messages.pop(0)
        raise RuntimeError("listener complete")


class FakeWebSocketConnect:
    def __init__(self, websocket):
        self.websocket = websocket

    def __call__(self, url):
        return self.websocket


@pytest.mark.asyncio
@patch("app.refresh_all")
@patch("app.show_alert")
async def test_simulate_translation_posts_payload_to_backend(mock_alert, mock_refresh, monkeypatch, tmp_path):
    source_file = tmp_path / "sample.py"
    source_file.write_text("print('hello')\n", encoding="utf-8")

    project_file = ProjectFile(
        file_id="file-1",
        path=str(source_file),
        legacy_source="print('hello')\n",
        ai_source="",
        status=FileStatus.QUEUED,
        language="python",
    )

    original_files = app_module.state.files
    original_session_id = app_module.state.session_id
    original_project_root = app_module.state.project_root

    try:
        app_module.state.files = {project_file.file_id: project_file}
        app_module.state.session_id = "session-123"
        app_module.state.project_root = str(tmp_path)

        client = FakeAsyncClient()

        class ClientFactory:
            async def __aenter__(self_inner):
                return client

            async def __aexit__(self_inner, exc_type, exc, tb):
                return False

        monkeypatch.setattr(app_module.httpx, "AsyncClient", lambda: ClientFactory())

        await app_module.simulate_translation(project_file.file_id)

        assert client.requests[0][0] == "http://localhost:8000/api/run/session-123"
        assert client.requests[0][1]["session_id"] == "session-123"
        assert client.requests[0][1]["file_path"] == str(source_file)
    finally:
        app_module.state.files = original_files
        app_module.state.session_id = original_session_id
        app_module.state.project_root = original_project_root


@pytest.mark.asyncio
async def test_websocket_listener_updates_ui_state_from_backend_payload(monkeypatch, tmp_path):
    source_file = tmp_path / "sample.py"
    source_file.write_text("print('hello')\n", encoding="utf-8")

    project_file = ProjectFile(
        file_id="file-1",
        path=str(source_file),
        legacy_source="print('hello')\n",
        ai_source="",
        status=FileStatus.TRANSLATING,
        language="python",
    )

    original_files = app_module.state.files
    original_active_buffer = app_module.state.active_buffer
    original_execution_logs = dict(app_module.state.execution_logs)
    original_agent_state = dict(app_module.state.agent_state)

    try:
        app_module.state.files = {project_file.file_id: project_file}
        app_module.state.active_buffer = project_file.file_id
        app_module.state.execution_logs.clear()
        app_module.state.agent_state.clear()
        app_module.state.is_thinking = True

        payload = json.dumps(
            {
                "target_file": {"file_id": project_file.file_id, "path": str(source_file)},
                "current_node": "sandbox_node",
                "docker_exit_code": 1,
                "iteration_count": 3,
                "max_iterations": 3,
                "traceback_log": "[Sandbox] Provisioning\nTraceback: boom",
                "patched_code": "print('patched')",
            }
        )

        fake_websocket = FakeWebSocket([payload])
        monkeypatch.setattr(app_module.websockets, "connect", FakeWebSocketConnect(fake_websocket))
        monkeypatch.setattr(app_module.render_main, "refresh", lambda: None)
        monkeypatch.setattr(app_module.render_sidebar, "refresh", lambda: None)

        await app_module.websocket_listener("session-1")

        assert app_module.state.agent_state[project_file.file_id] == "Done"
        assert app_module.state.files[project_file.file_id].status == FileStatus.FAILED
        assert app_module.state.files[project_file.file_id].ai_source == "print('patched')"
        assert any("Traceback: boom" in log for log in app_module.state.execution_logs[project_file.file_id])
    finally:
        app_module.state.files = original_files
        app_module.state.active_buffer = original_active_buffer
        app_module.state.execution_logs = original_execution_logs
        app_module.state.agent_state = original_agent_state


def test_find_file_id_by_tree_key():
    f1 = ProjectFile(file_id="f_alpha", path="analytics/model.py", legacy_source="", ai_source="", status=FileStatus.QUEUED, language="python")
    f2 = ProjectFile(file_id="f_beta", path="utils/helper.py", legacy_source="", ai_source="", status=FileStatus.QUEUED, language="python")

    original_files = app_module.state.files
    original_root = app_module.state.project_root
    try:
        app_module.state.files = {"f_alpha": f1, "f_beta": f2}
        app_module.state.project_root = "/workspace/root"

        # Direct file_id lookup
        assert app_module._find_file_id_by_tree_key("f_alpha") == "f_alpha"
        assert app_module._find_file_id_by_tree_key("f_beta") == "f_beta"

        # Relative path lookup
        assert app_module._find_file_id_by_tree_key("analytics/model.py") == "f_alpha"
        assert app_module._find_file_id_by_tree_key("utils/helper.py") == "f_beta"

        # None / invalid lookup
        assert app_module._find_file_id_by_tree_key(None) is None
        assert app_module._find_file_id_by_tree_key("nonexistent.py") is None
    finally:
        app_module.state.files = original_files
        app_module.state.project_root = original_root


@pytest.mark.asyncio
async def test_websocket_listener_selective_refresh(monkeypatch):
    project_file = ProjectFile(
        file_id="file-1",
        path="test.py",
        legacy_source="x = 1",
        ai_source="",
        status=FileStatus.TRANSLATING,
        language="python"
    )

    original_files = app_module.state.files
    original_active_buffer = app_module.state.active_buffer
    original_thinking = app_module.state.is_thinking
    original_phase = app_module.state.thinking_phase

    main_refreshes = 0
    sidebar_refreshes = 0

    def fake_render_main_refresh():
        nonlocal main_refreshes
        main_refreshes += 1

    def fake_render_sidebar_refresh():
        nonlocal sidebar_refreshes
        sidebar_refreshes += 1

    try:
        app_module.state.files = {"file-1": project_file}
        app_module.state.active_buffer = "file-1"
        app_module.state.is_thinking = True
        app_module.state.thinking_phase = 0
        app_module.state.agent_state = {"file-1": "llm_patch_node"}
        app_module.state.execution_logs.clear()

        monkeypatch.setattr(app_module.render_main, "refresh", fake_render_main_refresh)
        monkeypatch.setattr(app_module.render_sidebar, "refresh", fake_render_sidebar_refresh)

        # Message 1: Pure log stream (status and phase unchanged)
        log_payload = json.dumps({
            "target_file": {"file_id": "file-1"},
            "log_entry": {"message": "Streaming LLM tokens...", "source": "LLM"}
        })

        fake_ws_1 = FakeWebSocket([log_payload])
        monkeypatch.setattr(app_module.websockets, "connect", FakeWebSocketConnect(fake_ws_1))
        await app_module.websocket_listener("session-1")

        # No full UI refreshes should occur for pure log deltas!
        assert main_refreshes == 0
        assert sidebar_refreshes == 0
        assert len(app_module.state.execution_logs["file-1"]) >= 1

        # Message 2: Terminal exit code event (status changes to PASSED)
        exit_payload = json.dumps({
            "target_file": {"file_id": "file-1"},
            "current_node": "sandbox_node",
            "docker_exit_code": 0
        })
        fake_ws_2 = FakeWebSocket([exit_payload])
        monkeypatch.setattr(app_module.websockets, "connect", FakeWebSocketConnect(fake_ws_2))
        await app_module.websocket_listener("session-1")

        # Both main and sidebar should refresh on status transition
        assert main_refreshes >= 1
        assert sidebar_refreshes >= 1
        assert app_module.state.files["file-1"].status == FileStatus.PASSED
    finally:
        app_module.state.files = original_files
        app_module.state.active_buffer = original_active_buffer
        app_module.state.is_thinking = original_thinking
        app_module.state.thinking_phase = original_phase


@pytest.mark.asyncio
async def test_process_batch_queue_execution(monkeypatch):
    f1 = ProjectFile(file_id="f_1", path="a.py", legacy_source="a=1", ai_source="", status=FileStatus.QUEUED, language="python")
    f2 = ProjectFile(file_id="f_2", path="b.py", legacy_source="b=2", ai_source="", status=FileStatus.QUEUED, language="python")

    original_files = app_module.state.files
    original_session_id = app_module.state.session_id
    original_is_batch = app_module.state.is_batch_running

    processed_files = []

    async def fake_ensure_session():
        app_module.state.session_id = "mock-session"
        return "mock-session"

    def fake_run_translation(file_id):
        processed_files.append(file_id)
        # Simulate instant completion to PASSED
        app_module.state.files[file_id].status = FileStatus.PASSED

    monkeypatch.setattr(app_module, "ensure_session_initialized", fake_ensure_session)
    monkeypatch.setattr(app_module, "run_translation_simulation", fake_run_translation)
    monkeypatch.setattr(app_module.render_main, "refresh", lambda: None)
    monkeypatch.setattr(app_module.render_sidebar, "refresh", lambda: None)
    monkeypatch.setattr(app_module, "show_alert", lambda *args, **kwargs: None)

    try:
        app_module.state.files = {"f_1": f1, "f_2": f2}
        app_module.state.is_batch_running = False
        app_module.state.cancel_batch_flag = False

        await app_module.process_batch_queue(["f_1", "f_2"])

        assert processed_files == ["f_1", "f_2"]
        assert app_module.state.is_batch_running is False
    finally:
        app_module.state.files = original_files
        app_module.state.session_id = original_session_id
        app_module.state.is_batch_running = original_is_batch


@pytest.mark.asyncio
async def test_process_batch_queue_pause_and_resume(monkeypatch):
    f1 = ProjectFile(file_id="f_1", path="a.py", legacy_source="a=1", ai_source="", status=FileStatus.QUEUED, language="python")
    f2 = ProjectFile(file_id="f_2", path="b.py", legacy_source="b=2", ai_source="", status=FileStatus.QUEUED, language="python")

    original_files = app_module.state.files
    original_session_id = app_module.state.session_id
    original_is_batch = app_module.state.is_batch_running
    original_is_paused = app_module.state.is_batch_paused

    processed_files = []

    async def fake_ensure_session():
        app_module.state.session_id = "mock-session"
        return "mock-session"

    def fake_run_translation(file_id):
        processed_files.append(file_id)
        app_module.state.files[file_id].status = FileStatus.PASSED

    monkeypatch.setattr(app_module, "ensure_session_initialized", fake_ensure_session)
    monkeypatch.setattr(app_module, "run_translation_simulation", fake_run_translation)
    monkeypatch.setattr(app_module.render_main, "refresh", lambda: None)
    monkeypatch.setattr(app_module.render_sidebar, "refresh", lambda: None)
    monkeypatch.setattr(app_module, "show_alert", lambda *args, **kwargs: None)

    try:
        app_module.state.files = {"f_1": f1, "f_2": f2}
        app_module.state.is_batch_running = False
        app_module.state.is_batch_paused = False

        app_module.pause_batch()
        assert app_module.state.is_batch_paused is True

        # Unpause and run
        app_module.state.is_batch_paused = False
        await app_module.process_batch_queue(["f_1", "f_2"])

        assert processed_files == ["f_1", "f_2"]
        assert app_module.state.is_batch_running is False
    finally:
        app_module.state.files = original_files
        app_module.state.session_id = original_session_id
        app_module.state.is_batch_running = original_is_batch
        app_module.state.is_batch_paused = original_is_paused