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
    log_entry: NotRequired[dict]


_TRACEBACK_MAX_HEAD = 100  # lines kept from start of traceback
_TRACEBACK_MAX_TAIL = 100  # lines kept from end of traceback

# ---------------------------------------------------------------------------
# Fixed-width bracket tags — single source of truth.
# All tags are padded to exactly 4 visible chars (incl. trailing space where
# needed) so pipe-delimited log columns stay aligned regardless of source.
# ---------------------------------------------------------------------------
SOURCE_TAGS: dict[str, str] = {
    "LLM":      "[LLM ]",
    "DKR":      "[DKR ]",
    "TEST":     "[TEST]",
    "TELM":     "[TELM]",
    "SYS":      "[SYS ]",
    # Aliases accepted from legacy call sites (mapped on ingress)
    "DOCKER":   "[DKR ]",
    "PYTEST":   "[TEST]",
    "TELEMETRY":"[TELM]",
    "SYSTEM":   "[SYS ]",
}

# 4-char status labels — column-aligned.
STATUS_LABELS: dict[str, str] = {
    "running": "RUN ",
    "success": "PASS",
    "error":   "FAIL",
    "warning": "WARN",
    "info":    "INFO",
}


def _normalize_source(source: str) -> str:
    """Return the canonical 2-4 char source key (e.g. 'DOCKER' -> 'DKR')."""
    _alias: dict[str, str] = {
        "DOCKER": "DKR", "PYTEST": "TEST", "TELEMETRY": "TELM", "SYSTEM": "SYS",
    }
    upper = source.upper()
    return _alias.get(upper, upper)


def _truncate_traceback(raw: str) -> str:
    """Limit a traceback string to HEAD + TAIL lines to prevent WS frame overflow."""
    lines = raw.splitlines()
    total = len(lines)
    limit = _TRACEBACK_MAX_HEAD + _TRACEBACK_MAX_TAIL
    if total <= limit:
        return raw
    omitted = total - limit
    head = lines[:_TRACEBACK_MAX_HEAD]
    tail = lines[-_TRACEBACK_MAX_TAIL:]
    return "\n".join(head) + f"\n\n... {omitted} lines omitted ...\n\n" + "\n".join(tail)


async def emit_log(
    state: AgentState,
    message: str,
    source: str = "SYS",
    status: str = "info",
    details: dict | None = None
) -> None:
    """Broadcast a single structured log delta over WebSocket.

    The log_entry dict carries pre-normalized, fixed-width fields so the
    frontend can render a strictly columnar, ASCII-only log row without any
    client-side string surgery:

        HH:MM:SS | [SRC] | STAT | message text

    source is normalized to a canonical key (LLM / DKR / TEST / TELM / SYS)
    and status to a 4-char label (RUN  / PASS / FAIL / WARN / INFO).
    """
    canonical_src = _normalize_source(source)
    source_tag    = SOURCE_TAGS.get(canonical_src, f"[{canonical_src[:4]:4s}]")
    status_lower  = status.lower()
    status_label  = STATUS_LABELS.get(status_lower, "INFO")

    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    # Console line — human-readable, no emoji
    formatted_msg = f"{timestamp} | {source_tag} | {status_label} | {message}"
    print(formatted_msg)

    # Truncate any raw traceback in details before packing into JSON
    safe_details: dict = {}
    if details:
        safe_details = dict(details)
        if "raw_output" in safe_details and isinstance(safe_details["raw_output"], str):
            safe_details["raw_output"] = _truncate_traceback(safe_details["raw_output"])
        if "traceback" in safe_details and isinstance(safe_details["traceback"], str):
            safe_details["traceback"] = _truncate_traceback(safe_details["traceback"])

    log_entry = {
        "timestamp":    timestamp,          # HH:MM:SS
        "source":       canonical_src,      # canonical key  e.g. "DKR"
        "source_tag":   source_tag,         # fixed-width tag e.g. "[DKR ]"
        "status":       status_lower,       # raw status key  e.g. "running"
        "status_label": status_label,       # 4-char label    e.g. "RUN "
        "message":      message,
        "details":      safe_details,
    }

    # Minimal delta — keeps WS frame small; frontend appends to its own ring buffer.
    temp_state = {
        "session_id":    state.get("session_id"),
        "target_file":   state.get("target_file"),
        "traceback_log": formatted_msg,
        "log_entry":     log_entry,
    }

    session_id = state.get("session_id")
    if session_id:
        try:
            await manager.broadcast_state(session_id, temp_state)
        except Exception as e:
            print(f"Broadcast failed: {e}")


async def _llm_patch_node(state: AgentState) -> AgentState:
    persona = state.get("persona", "python_modernizer")
    await emit_log(state, f"Prompting model with persona '{persona}'", source="LLM", status="running")
    await emit_log(state, "Analyzing legacy source and generating patch", source="LLM", status="running")

    patcher = LLMPatchNode(llm_client=GeminiClient())
    patch_result = await asyncio.to_thread(patcher.execute, state)

    if patch_result.get("status") == "REFUSED":
        await emit_log(state, f"Model refused request: {patch_result.get('reason')}", source="LLM", status="warning")
    else:
        await emit_log(state, "Patch received. Parsing code blocks.", source="LLM", status="success")

    merged_state = {**state, **patch_result}
    merged_state["iteration_count"] = state.get("iteration_count", 0) + 1
    return merged_state  # type: ignore[return-value]


async def _sandbox_node(state: AgentState) -> AgentState:
    sandbox = await asyncio.to_thread(DockerSandboxManager)
    script_name = f"iteration_{state.get('iteration_count', 0) or 1}.py"
    patched_code = state.get("patched_code") or ""

    await emit_log(state, "Provisioning ephemeral container", source="DKR", status="running")
    try:
        container_id = await asyncio.to_thread(sandbox.createSandbox)
        if not container_id:
            raise RuntimeError("Container creation returned no ID")

        await emit_log(state, f"Injecting patch -> /workspace/{script_name}", source="DKR", status="running")
        await asyncio.to_thread(sandbox.injectCode, f"/workspace/{script_name}", patched_code)

        await emit_log(state, "Executing test suite inside container", source="TEST", status="running")
        execution_log = await asyncio.to_thread(sandbox.runScript, script_name)
    except Exception as exc:
        await emit_log(state, f"Container error: {exc}", source="DKR", status="error")
        execution_log = {
            "status": "failure",
            "exit_code": -1,
            "stderr_traceback": str(exc),
        }
    finally:
        try:
            await asyncio.to_thread(sandbox.destroySandbox)
            await emit_log(state, "Container destroyed", source="DKR", status="info")
        except Exception:
            pass

    mapped_state = map_sandbox_result_to_state(
        {
            "status":   execution_log.get("status", "failure"),
            "exit_code": execution_log.get("exit_code", -1),
            "stderr":   execution_log.get("stderr_traceback", ""),
            "traceback": "",
        }
    )

    new_traceback = mapped_state.get("traceback_log", "")
    exit_code     = execution_log.get("exit_code", -1)

    if new_traceback:
        is_test_output = any(
            k in new_traceback
            for k in ("passed in", "failed in", "ERROR", "FAILURES", "Traceback", "assert", "collected")
        )
        test_details = {
            "exit_code":     exit_code,
            "raw_output":    new_traceback,
            "is_test_suite": is_test_output,
        }
        await emit_log(
            state,
            f"Test run complete (exit {exit_code})",
            source="TEST",
            status="success" if exit_code == 0 else "error",
            details=test_details,
        )

    if exit_code == 0:
        await emit_log(state, "All tests passed", source="TEST", status="success")
    else:
        await emit_log(state, "Tests failed. Queuing AI correction pass.", source="TEST", status="error")

    mapped_state.pop("traceback_log", None)
    return {**state, **mapped_state}  # type: ignore[return-value]


async def _telemetry_node(state: AgentState) -> AgentState:
    await emit_log(state, "Persisting state to Supabase", source="TELM", status="info")
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