from __future__ import annotations

import asyncio
import datetime
from typing import NotRequired, TypedDict

from langgraph.graph import END, START, StateGraph

from backend.llm_client import GeminiClient
from backend.models import ProjectFile
from backend.logger import log_agent_state, map_sandbox_result_to_state
from backend.nodes import LLMPatchNode
from backend.sandbox import DockerSandboxManager
from backend.websocket import manager  # <--- Import the WebSocket manager


class AgentState(TypedDict):
    """State schema for the LangGraph orchestration workflow."""

    target_file: NotRequired[ProjectFile]
    workspace_dir: NotRequired[str]
    file_path: NotRequired[str]
    session_id: NotRequired[str]
    error_trace: NotRequired[str]
    system_prompt: NotRequired[str]
    persona: NotRequired[str]
    patched_code: NotRequired[str]
    docker_exit_code: NotRequired[int]
    traceback_log: NotRequired[str]
    iteration_count: NotRequired[int]
    max_iterations: NotRequired[int]
    raw: NotRequired[str]
    status: NotRequired[str]


async def emit_log(state: AgentState, message: str) -> None:
    """Helper to broadcast a single log instantly without duplicating history."""
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    formatted_msg = f"[{timestamp}] {message}"
    
    # Still print to the backend console for debugging
    print(formatted_msg)
    
    # Create a temporary copy of the state to send to the UI.
    # We ONLY send the newest message so the UI can append it cleanly once.
    temp_state = dict(state)
    temp_state["traceback_log"] = formatted_msg
        
    # Force an immediate WebSocket broadcast mid-node execution
    session_id = state.get("session_id")
    if session_id:
        try:
            await manager.broadcast_state(session_id, temp_state)
        except Exception as e:
            print(f"Broadcast failed: {e}")


async def _llm_patch_node(state: AgentState) -> AgentState:
    persona = state.get("persona", "python_modernizer")
    await emit_log(state, f"[LLM Engine] Prompting AI with '{persona}' persona...")
    await emit_log(state, "[LLM Engine] Analyzing legacy source code and generating refactor (this may take a moment)...")
    
    patcher = LLMPatchNode(llm_client=GeminiClient())
    patch_result = await asyncio.to_thread(patcher.execute, state)
    
    if patch_result.get("status") == "REFUSED":
        await emit_log(state, f"[LLM Engine] Safety trigger: AI Refused. Reason: {patch_result.get('reason')}")
    else:   
        await emit_log(state, "[LLM Engine] Response received. Parsing structured code blocks...")
        
    merged_state = {**state, **patch_result}
    merged_state["iteration_count"] = state.get("iteration_count", 0) + 1
    return merged_state  # type: ignore[return-value]


async def _sandbox_node(state: AgentState) -> AgentState:
    sandbox = await asyncio.to_thread(DockerSandboxManager)
    script_name = f"iteration_{state.get('iteration_count', 0) or 1}.py"
    patched_code = state.get("patched_code") or ""

    await emit_log(state, "[Sandbox] Provisioning secure ephemeral container...")
    try:
        container_id = await asyncio.to_thread(sandbox.createSandbox)
        if not container_id:
            raise RuntimeError("Sandbox container could not be created")

        await emit_log(state, f"[Sandbox] Injecting AI-generated code into /workspace/{script_name}...")
        await asyncio.to_thread(sandbox.injectCode, f"/workspace/{script_name}", patched_code)
        
        await emit_log(state, "[Sandbox] Executing isolated test suite...")
        execution_log = await asyncio.to_thread(sandbox.runScript, script_name)
    except Exception as exc:
        await emit_log(state, f"[Sandbox] System Error: {str(exc)}")
        execution_log = {
            "status": "failure",
            "exit_code": -1,
            "stderr_traceback": str(exc),
        }
    finally:
        try:
            await asyncio.to_thread(sandbox.destroySandbox)
            await emit_log(state, "[Sandbox] Container destroyed. Workspace cleaned.")
        except Exception:
            pass

    mapped_state = map_sandbox_result_to_state(
        {
            "status": execution_log.get("status", "failure"),
            "exit_code": execution_log.get("exit_code", -1),
            "stderr": execution_log.get("stderr_traceback", ""),
            "traceback": "",
        }
    )
    
    # Safely extract sandbox output without overwriting our beautiful terminal history
    new_traceback = mapped_state.get("traceback_log", "")
    if new_traceback:
        await emit_log(state, f"[Sandbox Output]\n{new_traceback}")
        
    if execution_log.get("exit_code") == 0:
        await emit_log(state, "[Sandbox] Verification successful. All tests passed!")
    else:
        await emit_log(state, "[Sandbox] Verification failed. Collecting error traces for AI correction...")

    # Remove the mapped traceback_log so it doesn't overwrite the state when merged
    mapped_state.pop("traceback_log", None)
    return {**state, **mapped_state}  # type: ignore[return-value]


async def _telemetry_node(state: AgentState) -> AgentState:
    await emit_log(state, "[Telemetry] Syncing execution state to Supabase...")
    session_id = state.get("session_id", "")
    if isinstance(session_id, str) and session_id.strip():
        await log_agent_state(session_id, state)
    return {**state}  # type: ignore[return-value]


def route_after_telemetry(state: AgentState) -> str:
    allowed_iterations = min(state.get("max_iterations", 3), 5)
    docker_exit_code = state.get("docker_exit_code", -1)

    if docker_exit_code == 0:
        print("[Orchestrator] Pipeline completed successfully. Outputting to Diff Viewer.")
        return END

    if state.get("iteration_count", 0) < allowed_iterations:
        print(f"[Orchestrator] Routing back to AI for correction (Iteration {state.get('iteration_count', 0) + 1})...")
        return "llm_patch_node"

    print("[Orchestrator] Max iterations reached. Halting pipeline.")
    return END


graph = StateGraph(AgentState)
graph.add_node("llm_patch_node", _llm_patch_node)
graph.add_node("sandbox_node", _sandbox_node)
graph.add_node("telemetry_node", _telemetry_node)
graph.add_edge(START, "llm_patch_node")
graph.add_edge("llm_patch_node", "sandbox_node")
graph.add_edge("sandbox_node", "telemetry_node")
graph.add_conditional_edges(
    "telemetry_node",
    route_after_telemetry,
    {END: END, "llm_patch_node": "llm_patch_node"},
)

orchestrator_app = graph.compile()