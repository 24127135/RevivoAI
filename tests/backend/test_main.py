import pytest

from backend import main as main_module


class FakeWebSocket:
    def __init__(self):
        self.accepted = False
        self.sent_messages = []
        self.receive_queue = ["keep-alive"]

    async def accept(self):
        self.accepted = True

    async def receive_text(self):
        if self.receive_queue:
            self.receive_queue.pop(0)
            raise main_module.WebSocketDisconnect()
        raise main_module.WebSocketDisconnect()

    async def send_json(self, payload):
        self.sent_messages.append(payload)


@pytest.mark.asyncio
async def test_run_orchestrator_task_merges_streamed_state_and_broadcasts(monkeypatch):
    events = [
        {"llm_patch_node": {"patched_code": "print('hello')", "iteration_count": 1}},
        {"sandbox_node": {"docker_exit_code": 0, "traceback_log": ""}},
    ]

    class FakeOrchestrator:
        async def astream(self, payload):
            for event in events:
                yield event

    broadcast_calls = []

    async def fake_broadcast_state(session_id: str, state: dict):
        broadcast_calls.append((session_id, dict(state)))

    monkeypatch.setattr(main_module, "orchestrator_app", FakeOrchestrator())
    monkeypatch.setattr(main_module.manager, "broadcast_state", fake_broadcast_state)

    valid_payload = {
        "target_file": {
            "file_id": "f_123",
            "path": "x.py",
            "legacy_source": "print('old')",
            "ai_source": "",
            "status": "QUEUED",
            "language": "python"
        }
    }

    await main_module.run_orchestrator_task("session-1", valid_payload)

    assert broadcast_calls[0][0] == "session-1"
    assert broadcast_calls[0][1]["patched_code"] == "print('hello')"
    assert broadcast_calls[0][1]["current_node"] == "llm_patch_node"
    assert broadcast_calls[1][1]["docker_exit_code"] == 0


@pytest.mark.asyncio
async def test_run_orchestrator_endpoint_queues_background_task():
    captured = {}

    class FakeBackgroundTasks:
        def add_task(self, fn, *args, **kwargs):
            captured["fn"] = fn
            captured["args"] = args
            captured["kwargs"] = kwargs

    valid_payload = {
        "target_file": {
            "file_id": "f_123",
            "path": "x.py",
            "legacy_source": "print('old')",
            "ai_source": "",
            "status": "QUEUED",
            "language": "python"
        }
    }

    response = await main_module.run_orchestrator(
        "session-1",
        valid_payload,
        FakeBackgroundTasks(),
    )

    assert response == {"status": "queued", "session_id": "session-1"}
    assert captured["fn"] is main_module.run_orchestrator_task
    assert captured["args"] == ("session-1", valid_payload)


@pytest.mark.asyncio
async def test_websocket_endpoint_disconnects_and_clears_manager(monkeypatch):
    websocket = FakeWebSocket()
    calls = []

    async def fake_connect(ws, session_id):
        calls.append(("connect", session_id))

    def fake_disconnect(ws, session_id):
        calls.append(("disconnect", session_id))

    monkeypatch.setattr(main_module.manager, "connect", fake_connect)
    monkeypatch.setattr(main_module.manager, "disconnect", fake_disconnect)

    await main_module.websocket_endpoint(websocket, "session-1")

    assert calls == [("connect", "session-1"), ("disconnect", "session-1")]