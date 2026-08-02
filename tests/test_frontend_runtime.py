import json

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

    async def post(self, url, json=None):
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
async def test_simulate_translation_posts_payload_to_backend(monkeypatch, tmp_path):
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

        payload = json.dumps(
            {
                "target_file": {"file_id": project_file.file_id, "path": str(source_file)},
                "current_node": "sandbox_node",
                "docker_exit_code": 1,
                "traceback_log": "Traceback: boom",
                "patched_code": "print('patched')",
            }
        )

        fake_websocket = FakeWebSocket([payload])
        monkeypatch.setattr(app_module.websockets, "connect", FakeWebSocketConnect(fake_websocket))
        monkeypatch.setattr(app_module.render_main, "refresh", lambda: None)
        monkeypatch.setattr(app_module.render_sidebar, "refresh", lambda: None)

        await app_module.websocket_listener("session-1")

        assert app_module.state.agent_state[project_file.file_id] == "sandbox_node"
        assert app_module.state.files[project_file.file_id].status == FileStatus.FAILED
        assert app_module.state.files[project_file.file_id].ai_source == "print('patched')"
        assert any("Traceback: boom" in log for log in app_module.state.execution_logs[project_file.file_id])
    finally:
        app_module.state.files = original_files
        app_module.state.active_buffer = original_active_buffer
        app_module.state.execution_logs = original_execution_logs
        app_module.state.agent_state = original_agent_state