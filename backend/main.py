from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

from backend.models import ProjectFile
from backend.orchestrator import orchestrator_app
from backend.websocket import manager

app = FastAPI(title="RevivoAI Backend")

# ---------------------------------------------------------------------------
# Static files — Monaco Web Worker proxy scripts
# ---------------------------------------------------------------------------
# Worker scripts are fetched by the browser as same-origin URLs
# (/monaco-workers/editor.worker.js, etc.) which satisfies the browser's
# "same-origin or CORS" constraint for Web Workers.  Each proxy script in
# frontend/monaco_workers/ calls importScripts() to load the real Monaco
# worker bundle from the CDN inside the worker scope.
_WORKERS_DIR = Path(__file__).parent.parent / "frontend" / "monaco_workers"
app.mount("/monaco-workers", StaticFiles(directory=str(_WORKERS_DIR)), name="monaco-workers")


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

    target_data = current_state.get("target_file")
    if isinstance(target_data, dict):
        current_state["target_file"] = ProjectFile(**target_data)

    async for event in orchestrator_app.astream(current_state):
        if isinstance(event, dict):
            for node_name, state_chunk in event.items():
                if isinstance(state_chunk, dict):
                    current_state.update(state_chunk)
                current_state["current_node"] = node_name
        await manager.broadcast_state(session_id, current_state)


@app.post("/api/run/{session_id}")
async def run_orchestrator(session_id: str, payload: dict, background_tasks: BackgroundTasks):
    api_key = payload.get("api_key")
    if api_key:
        os.environ["GEMINI_API_KEY"] = api_key

    background_tasks.add_task(run_orchestrator_task, session_id, payload)
    return {"status": "queued", "session_id": session_id}