from __future__ import annotations

from dataclasses import is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, TYPE_CHECKING

from fastapi import WebSocket

from backend.models import ProjectFile

if TYPE_CHECKING:
    from backend.orchestrator import AgentState


class WebSocketManager:
    def __init__(self) -> None:
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections.setdefault(session_id, []).append(websocket)

    def disconnect(self, websocket: WebSocket, session_id: str):
        connections = self.active_connections.get(session_id)
        if not connections:
            return

        if websocket in connections:
            connections.remove(websocket)

        if not connections:
            self.active_connections.pop(session_id, None)

    def _normalize_value(self, value: Any) -> Any:
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, dict):
            return {key: self._normalize_value(item) for key, item in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [self._normalize_value(item) for item in value]

        if hasattr(value, "model_dump") and callable(value.model_dump):
            dumped = value.model_dump()
            return self._normalize_value(dumped)

        if is_dataclass(value):
            return self._normalize_value(value.__dict__)

        if hasattr(value, "__dict__"):
            return self._normalize_value(value.__dict__)

        return value

    def _serialize_state(self, state: dict) -> dict:
        serialized = {key: self._normalize_value(value) for key, value in state.items()}

        target_file = serialized.get("target_file")
        if isinstance(target_file, ProjectFile):
            serialized["target_file"] = self._normalize_value(target_file)

        return serialized

    async def broadcast_state(self, session_id: str, state: dict):
        connections = self.active_connections.get(session_id)
        if not connections:
            return

        payload = self._serialize_state(state)
        for connection in list(connections):
            await connection.send_json(payload)


manager = WebSocketManager()