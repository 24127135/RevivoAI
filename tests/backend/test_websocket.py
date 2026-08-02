from dataclasses import dataclass

import pytest

from backend.models import FileStatus, ProjectFile
from backend.websocket import WebSocketManager


class FakeWebSocket:
    def __init__(self):
        self.accepted = False
        self.sent_payloads = []

    async def accept(self):
        self.accepted = True

    async def send_json(self, payload):
        self.sent_payloads.append(payload)


@dataclass
class DummyPayload:
    name: str
    count: int


@pytest.mark.asyncio
async def test_connect_adds_websocket_to_session_bucket():
    manager = WebSocketManager()
    websocket = FakeWebSocket()

    await manager.connect(websocket, "session-1")

    assert websocket.accepted is True
    assert manager.active_connections["session-1"] == [websocket]


def test_disconnect_removes_last_websocket_and_clears_session_key():
    manager = WebSocketManager()
    websocket = FakeWebSocket()
    manager.active_connections["session-1"] = [websocket]

    manager.disconnect(websocket, "session-1")

    assert "session-1" not in manager.active_connections


def test_serialize_state_converts_project_file_and_nested_values():
    manager = WebSocketManager()
    project_file = ProjectFile(
        file_id="file-1",
        path="src/example.py",
        legacy_source="print('hello')",
        ai_source="",
        status=FileStatus.QUEUED,
        language="python",
    )

    payload = manager._serialize_state(
        {
            "target_file": project_file,
            "status": FileStatus.TRANSLATING,
            "nested": {"value": FileStatus.PASSED},
            "items": [FileStatus.FAILED, DummyPayload(name="x", count=2)],
        }
    )

    assert payload["target_file"]["file_id"] == "file-1"
    assert payload["target_file"]["status"] == "QUEUED"
    assert payload["status"] == "TRANSLATING"
    assert payload["nested"]["value"] == "PASSED"
    assert payload["items"][0] == "FAILED"
    assert payload["items"][1] == {"name": "x", "count": 2}


@pytest.mark.asyncio
async def test_broadcast_state_sends_serialized_payload_to_all_session_connections():
    manager = WebSocketManager()
    websocket_one = FakeWebSocket()
    websocket_two = FakeWebSocket()
    manager.active_connections["session-1"] = [websocket_one, websocket_two]

    project_file = ProjectFile(
        file_id="file-1",
        path="src/example.py",
        legacy_source="print('hello')",
        ai_source="",
        status=FileStatus.QUEUED,
        language="python",
    )

    await manager.broadcast_state(
        "session-1",
        {
            "target_file": project_file,
            "docker_exit_code": 0,
        },
    )

    assert websocket_one.sent_payloads[0]["docker_exit_code"] == 0
    assert websocket_two.sent_payloads[0]["target_file"]["file_id"] == "file-1"


@pytest.mark.asyncio
async def test_broadcast_state_noops_for_unknown_session():
    manager = WebSocketManager()

    await manager.broadcast_state("missing-session", {"docker_exit_code": 1})

    assert manager.active_connections == {}