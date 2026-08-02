from __future__ import annotations

from typing import Any

from fastapi import BackgroundTasks, FastAPI, WebSocket, WebSocketDisconnect

from backend.orchestrator import orchestrator_app
from backend.websocket import manager

app = FastAPI(title="RevivoAI Backend")


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await manager.connect(websocket, session_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket, session_id)


async def run_orchestrator_task(session_id: str, payload: dict):
    current_state: dict[str, Any] = dict(payload)

    async for event in orchestrator_app.astream(payload):
        if isinstance(event, dict):
            for node_name, state_chunk in event.items():
                if isinstance(state_chunk, dict):
                    current_state.update(state_chunk)
                current_state["current_node"] = node_name
        await manager.broadcast_state(session_id, current_state)


@app.post("/api/run/{session_id}")
async def run_orchestrator(session_id: str, payload: dict, background_tasks: BackgroundTasks):
    background_tasks.add_task(run_orchestrator_task, session_id, payload)
    return {"status": "queued", "session_id": session_id}