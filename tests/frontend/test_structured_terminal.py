import pytest
from frontend.structured_terminal import StructuredTerminal
from app import StructuredLog, push_log, _make_structured_log, state


# ── StructuredLog dict/contains interface ─────────────────────────────────────

def test_structured_log_dict_and_contains():
    log = StructuredLog(
        timestamp="12:34:56",
        source="DKR",
        status="error",
        message="Container memory limit exceeded",
        details={"exit_code": 137, "raw_output": "OOM killed\nTraceback: memory error"},
    )

    assert log["source"]             == "DKR"
    assert log["status"]             == "error"
    assert log["details"]["exit_code"] == 137

    # Substring contains compatibility
    assert "source"              in log
    assert "status"              in log
    assert "Container memory"    in log
    assert "Traceback: memory error" in log
    assert "OOM"                 in log


# ── StructuredTerminal element ────────────────────────────────────────────────

def test_structured_terminal_element_init():
    initial = [
        {"timestamp": "10:00:00", "source": "LLM", "status": "info", "message": "Starting patch"},
        "[10:00:01] [DKR] Container created",
    ]
    term = StructuredTerminal(logs=initial, max_logs=500)
    assert len(term._props["initial_logs"]) == 2
    assert term._props["max_logs"]          == 500


# ── push_log + ring buffer ────────────────────────────────────────────────────

def test_push_log_stores_structured_log_objects():
    state.execution_logs.clear()
    fid = "test_file_id_1"

    push_log(fid, "[Sandbox] Provisioning secure container...")
    assert len(state.execution_logs[fid]) == 1
    log1 = state.execution_logs[fid][0]
    assert log1["source"] == "DOCKER"   # legacy string → auto-tagged as DOCKER by app.py
    assert log1["status"] == "running"
    assert "Provisioning" in log1

    push_log(
        fid,
        {
            "timestamp": "10:05:00",
            "source":    "PYTEST",
            "status":    "success",
            "message":   "All 12 tests passed",
            "details":   {"passed": 12, "failed": 0, "is_test_suite": True},
        },
    )
    assert len(state.execution_logs[fid]) == 2
    log2 = state.execution_logs[fid][1]
    assert log2["source"]           == "PYTEST"
    assert log2["status"]           == "success"
    assert log2["details"]["passed"] == 12


def test_push_log_ring_buffer_cap():
    """Ring buffer must not exceed _MAX_LOG_BUFFER entries."""
    state.execution_logs.clear()
    fid = "ring_buffer_test"
    cap = state._MAX_LOG_BUFFER

    for i in range(cap + 50):
        push_log(fid, f"log line {i}")

    assert len(state.execution_logs[fid]) == cap
    assert "log line" in str(state.execution_logs[fid][-1])


# ── _make_structured_log ──────────────────────────────────────────────────────

def test_make_structured_log_string_auto_detect_sources():
    """Auto-detection from legacy bracket prefixes in string messages."""
    llm_log = _make_structured_log("[LLM Engine] Analyzing source code...")
    assert llm_log["source"] == "LLM"

    docker_log = _make_structured_log("[Sandbox] Provisioning container...")
    assert docker_log["source"] == "DOCKER"
    assert docker_log["status"] == "running"

    error_log = _make_structured_log("[AI Sandbox Crash] RuntimeError: memory Error")
    assert error_log["source"] == "DOCKER"
    assert error_log["status"] == "error"

    telemetry_log = _make_structured_log("[Telemetry] Syncing to Supabase...")
    assert telemetry_log["source"] == "TELEMETRY"


def test_make_structured_log_dict_passthrough():
    """Structured dicts passed to _make_structured_log must be preserved as-is."""
    entry = {
        "timestamp": "15:30:00",
        "source":    "PYTEST",
        "status":    "success",
        "message":   "3 passed in 0.42s",
        "details":   {"is_test_suite": True, "exit_code": 0},
    }
    log = _make_structured_log(entry)
    assert log["source"]                  == "PYTEST"
    assert log["status"]                  == "success"
    assert log["details"]["is_test_suite"] is True
    assert log["timestamp"]               == "15:30:00"


def test_make_structured_log_no_emoji_in_source():
    """Source field must never contain emoji characters after normalization."""
    for src_key in ("LLM", "DOCKER", "PYTEST", "TELEMETRY", "SYSTEM"):
        log = _make_structured_log({"source": src_key, "status": "info", "message": "test"})
        source_val = log["source"]
        # No char with ordinal > 127 allowed in source
        assert all(ord(c) < 128 for c in source_val), (
            f"source={source_val!r} contains non-ASCII (possible emoji) for key {src_key}"
        )
