from __future__ import annotations

import asyncio
from typing import NotRequired, TypedDict

from langgraph.graph import END, START, StateGraph

from backend.llm_client import GeminiClient
from backend.models import ProjectFile
from backend.logger import log_agent_state, map_sandbox_result_to_state
from backend.nodes import LLMPatchNode
from backend.sandbox import DockerSandboxManager


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


async def _llm_patch_node(state: AgentState) -> AgentState:
    patcher = LLMPatchNode(llm_client=GeminiClient())
    patch_result = await asyncio.to_thread(patcher.execute, state)
    merged_state = {**state, **patch_result}
    merged_state["iteration_count"] = state.get("iteration_count", 0) + 1
    return merged_state  # type: ignore[return-value]


async def _sandbox_node(state: AgentState) -> AgentState:
    sandbox = await asyncio.to_thread(DockerSandboxManager)
    script_name = f"iteration_{state.get('iteration_count', 0) or 1}.py"
    patched_code = state.get("patched_code") or ""

    try:
        container_id = await asyncio.to_thread(sandbox.createSandbox)
        if not container_id:
            raise RuntimeError("Sandbox container could not be created")

        await asyncio.to_thread(sandbox.injectCode, f"/workspace/{script_name}", patched_code)
        execution_log = await asyncio.to_thread(sandbox.runScript, script_name)
    except Exception as exc:
        execution_log = {
            "status": "failure",
            "exit_code": -1,
            "stderr_traceback": str(exc),
        }
    finally:
        try:
            await asyncio.to_thread(sandbox.destroySandbox)
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

    return {**state, **mapped_state}  # type: ignore[return-value]


async def _telemetry_node(state: AgentState) -> AgentState:
    session_id = state.get("session_id", "")
    if isinstance(session_id, str) and session_id.strip():
        await log_agent_state(session_id, state)
    return {**state}  # type: ignore[return-value]


def route_after_telemetry(state: AgentState) -> str:
    allowed_iterations = min(state.get("max_iterations", 3), 5)
    docker_exit_code = state.get("docker_exit_code", -1)

    if docker_exit_code == 0:
        return END

    if state.get("iteration_count", 0) < allowed_iterations:
        return "llm_patch_node"

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
