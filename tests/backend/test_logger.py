import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-key")

from backend import logger as logger_module


def test_map_sandbox_result_to_state_combines_stderr_and_traceback_and_preserves_shape():
    result = logger_module.map_sandbox_result_to_state(
        {
            "exit_code": 7,
            "status": "failure",
            "stderr": "  warning line  ",
            "traceback": "  ValueError: bad input  ",
        }
    )

    assert result == {
        "docker_exit_code": 7,
        "traceback_log": "warning line\nValueError: bad input",
    }


def test_map_sandbox_result_to_state_defaults_exit_code_and_uses_fallback_message():
    result = logger_module.map_sandbox_result_to_state(
        {
            "status": "failed",
            "stderr": "   ",
            "traceback": "",
        }
    )

    assert result == {
        "docker_exit_code": -1,
        "traceback_log": "[Sandbox Error] Execution failed with status 'failed', but no traceback was provided.",
    }


def test_map_sandbox_result_to_state_prefixes_timeout_tracebacks():
    result = logger_module.map_sandbox_result_to_state(
        {
            "status": "timeout",
            "stderr": "",
            "traceback": "  RuntimeError: execution timed out  ",
        }
    )

    assert result == {
        "docker_exit_code": -1,
        "traceback_log": (
            "[Sandbox Timeout] The execution exceeded the allotted time limit.\n"
            "RuntimeError: execution timed out"
        ),
    }


def test_map_sandbox_result_to_state_timeout_combines_stderr_and_traceback():
    result = logger_module.map_sandbox_result_to_state(
        {
            "status": "timeout",
            "stderr": "  warning: slow path  ",
            "traceback": "  RuntimeError: execution timed out  ",
        }
    )

    assert result == {
        "docker_exit_code": -1,
        "traceback_log": (
            "[Sandbox Timeout] The execution exceeded the allotted time limit.\n"
            "warning: slow path\n"
            "RuntimeError: execution timed out"
        ),
    }


def test_map_sandbox_result_to_state_success_with_no_traceback_returns_empty_log():
    result = logger_module.map_sandbox_result_to_state(
        {
            "status": "success",
            "stderr": "   ",
            "traceback": "",
        }
    )

    assert result == {
        "docker_exit_code": -1,
        "traceback_log": "",
    }


def test_map_sandbox_result_to_state_returns_only_expected_keys():
    result = logger_module.map_sandbox_result_to_state({"status": "failed"})

    assert set(result.keys()) == {"docker_exit_code", "traceback_log"}


@pytest.mark.asyncio
async def test_log_agent_state_inserts_expected_payload_and_returns_true():
    response = MagicMock()
    response.data = [{"id": "log-1"}]

    query = MagicMock()
    query.execute.return_value = response

    table = MagicMock()
    table.insert.return_value = query

    with patch.object(logger_module, "supabase_db") as mock_supabase, patch.object(
        logger_module.asyncio,
        "to_thread",
        new=AsyncMock(side_effect=lambda fn, *args, **kwargs: fn(*args, **kwargs)),
    ) as mock_to_thread:
        mock_supabase.table.return_value = table

        result = await logger_module.log_agent_state(
            "session-123",
            {
                "iteration_count": 3,
                "status": "PATCH_GENERATED",
                "patched_code": "print('ok')",
                "error_trace": "Traceback...",
                "invariants": ["must preserve imports"],
                "assumptions": ["single-file change"],
                "characterization": "### CHARACTERIZATION:\n- INVARIANT: preserve imports",
                "raw": "full raw model output",
            },
        )

    assert result is True
    mock_supabase.table.assert_called_once_with("execution_logs")
    table.insert.assert_called_once()
    payload = table.insert.call_args[0][0]
    assert payload["session_id"] == "session-123"
    assert payload["iteration"] == 3
    assert payload["status"] == "PATCH_GENERATED"
    assert payload["patched_code"] == "print('ok')"
    assert payload["error_trace"] == "Traceback..."
    assert payload["llm_metadata"] == {
        "invariants": ["must preserve imports"],
        "assumptions": ["single-file change"],
        "characterization": "### CHARACTERIZATION:\n- INVARIANT: preserve imports",
        "raw": "full raw model output",
    }
    mock_to_thread.assert_awaited_once_with(query.execute)


@pytest.mark.asyncio
async def test_log_agent_state_returns_false_when_insert_raises_exception():
    query = MagicMock()
    query.execute.side_effect = RuntimeError("db down")

    table = MagicMock()
    table.insert.return_value = query

    with patch.object(logger_module, "supabase_db") as mock_supabase, patch.object(
        logger_module.asyncio,
        "to_thread",
        new=AsyncMock(side_effect=lambda fn, *args, **kwargs: fn(*args, **kwargs)),
    ):
        mock_supabase.table.return_value = table

        result = await logger_module.log_agent_state(
            "session-123",
            {"status": "FAILED", "patched_code": "", "error_trace": "boom"},
        )

    assert result is False