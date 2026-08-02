import asyncio
import logging
from typing import Any, Dict

from core.database import supabase_db

logger = logging.getLogger(__name__)


def map_sandbox_result_to_state(execution_log: dict) -> dict:
    """Map a Docker sandbox execution log into an AgentState update payload."""
    exit_code = execution_log.get("exit_code", -1)
    status = str(execution_log.get("status", "")).strip().lower()

    stderr = str(execution_log.get("stderr", "")).strip()
    traceback = str(execution_log.get("traceback", "")).strip()

    trace_parts = [part for part in (stderr, traceback) if part]
    traceback_log = "\n".join(trace_parts)

    if status == "timeout":
        timeout_prefix = "[Sandbox Timeout] The execution exceeded the allotted time limit."
        traceback_log = f"{timeout_prefix}\n{traceback_log}" if traceback_log else timeout_prefix
    elif status != "success" and not traceback_log:
        traceback_log = (
            f"[Sandbox Error] Execution failed with status '{status}', but no traceback was provided."
        )

    return {
        "docker_exit_code": exit_code,
        "traceback_log": traceback_log,
    }


async def log_agent_state(session_id: str, state: Dict[str, Any]) -> bool:
    """Persist an AgentState snapshot to the execution_logs table."""
    iteration_count = state.get("iteration_count", 1)
    status = state.get("status", "UNKNOWN")
    patched_code = state.get("patched_code")
    error_trace = state.get("error_trace")

    payload: Dict[str, Any] = {
        "session_id": session_id,
        "iteration": iteration_count,
        "status": status,
        "patched_code": patched_code,
        "error_trace": error_trace,
        "llm_metadata": {
            "invariants": state.get("invariants"),
            "assumptions": state.get("assumptions"),
            "characterization": state.get("characterization"),
            "raw": state.get("raw"),
        },
    }

    try:
        query = supabase_db.table("execution_logs").insert(payload)
        response = await asyncio.to_thread(query.execute)

        if not getattr(response, "data", None):
            logger.warning("Execution log insert returned empty data for session %s", session_id)
            return False

        logger.info("Execution log inserted for session %s", session_id)
        return True

    except Exception as exc:
        logger.error("Failed to insert execution log for session %s: %s", session_id, exc)
        return False