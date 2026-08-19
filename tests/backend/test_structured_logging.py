import pytest
from backend.orchestrator import (
    AgentState, emit_log,
    _truncate_traceback, _normalize_source,
    _TRACEBACK_MAX_HEAD, _TRACEBACK_MAX_TAIL,
    SOURCE_TAGS, STATUS_LABELS,
)


# ── SOURCE_TAGS / STATUS_LABELS contract ─────────────────────────────────────

def test_source_tags_are_fixed_width():
    """Every source tag must be exactly 7 chars: '[XXXX]' with padding."""
    for key, tag in SOURCE_TAGS.items():
        assert tag.startswith('[') and tag.endswith(']'), (
            f"SOURCE_TAGS['{key}'] = {tag!r} — must be wrapped in [ ]"
        )
        inner = tag[1:-1]  # strip brackets
        assert len(inner) == 4, (
            f"SOURCE_TAGS['{key}'] inner width {len(inner)} != 4  ({tag!r})"
        )


def test_status_labels_are_fixed_width():
    """Every status label must be exactly 4 chars."""
    for key, label in STATUS_LABELS.items():
        assert len(label) == 4, (
            f"STATUS_LABELS['{key}'] width {len(label)} != 4  ({label!r})"
        )


def test_normalize_source_aliases():
    """Legacy source strings must map to canonical short keys."""
    assert _normalize_source("DOCKER")    == "DKR"
    assert _normalize_source("docker")    == "DKR"  # case-insensitive
    assert _normalize_source("PYTEST")    == "TEST"
    assert _normalize_source("TELEMETRY") == "TELM"
    assert _normalize_source("SYSTEM")    == "SYS"
    assert _normalize_source("LLM")       == "LLM"   # pass-through
    assert _normalize_source("DKR")       == "DKR"   # already canonical


# ── emit_log payload shape ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_emit_log_constructs_structured_payload(monkeypatch):
    broadcasted_payloads = []

    class FakeManager:
        async def broadcast_state(self, session_id: str, state: dict):
            broadcasted_payloads.append((session_id, state))

    monkeypatch.setattr("backend.orchestrator.manager", FakeManager())

    state: AgentState = {
        "session_id": "test-session-123",
        "status": "TRANSLATING",
    }

    await emit_log(
        state,
        "Analyzing legacy source",
        source="LLM",
        status="running",
        details={"model": "gemini-1.5-pro"},
    )

    assert len(broadcasted_payloads) == 1
    session_id, payload = broadcasted_payloads[0]
    assert session_id == "test-session-123"
    assert "log_entry" in payload

    entry = payload["log_entry"]
    # canonical source key
    assert entry["source"] == "LLM"
    # fixed-width tag
    assert entry["source_tag"] == "[LLM ]"
    assert entry["status"]       == "running"
    # 4-char label
    assert entry["status_label"] == "RUN "
    assert entry["message"]      == "Analyzing legacy source"
    assert entry["details"]      == {"model": "gemini-1.5-pro"}
    assert "timestamp"           in entry

    # Console line uses the new pipe format (no square-bracket wrapping ts)
    log_line = payload["traceback_log"]
    assert "[LLM ]"  in log_line
    assert "RUN "    in log_line
    assert "|"       in log_line

    # Delta payload must NOT carry large agent state fields
    assert "patched_code"  not in payload
    assert "system_prompt" not in payload


@pytest.mark.asyncio
async def test_emit_log_legacy_source_aliases_normalized(monkeypatch):
    """DOCKER / PYTEST / TELEMETRY / SYSTEM must be normalized in the payload."""
    broadcasted_payloads = []

    class FakeManager:
        async def broadcast_state(self, session_id: str, state: dict):
            broadcasted_payloads.append((session_id, state))

    monkeypatch.setattr("backend.orchestrator.manager", FakeManager())

    state: AgentState = {"session_id": "norm-test"}

    for legacy, expected_canon, expected_tag in [
        ("DOCKER",    "DKR",  "[DKR ]"),
        ("PYTEST",    "TEST", "[TEST]"),
        ("TELEMETRY", "TELM", "[TELM]"),
        ("SYSTEM",    "SYS",  "[SYS ]"),
    ]:
        broadcasted_payloads.clear()
        await emit_log(state, "test message", source=legacy, status="info")
        entry = broadcasted_payloads[0][1]["log_entry"]
        assert entry["source"]     == expected_canon, f"source mismatch for {legacy}"
        assert entry["source_tag"] == expected_tag,   f"source_tag mismatch for {legacy}"


@pytest.mark.asyncio
async def test_emit_log_with_pytest_details(monkeypatch):
    broadcasted_payloads = []

    class FakeManager:
        async def broadcast_state(self, session_id: str, state: dict):
            broadcasted_payloads.append((session_id, state))

    monkeypatch.setattr("backend.orchestrator.manager", FakeManager())

    state: AgentState = {"session_id": "session-pytest-1"}

    test_output = "=== test session starts ===\n3 passed, 1 failed in 0.42s"
    await emit_log(
        state,
        "Test run complete (exit 1)",
        source="TEST",
        status="error",
        details={"exit_code": 1, "raw_output": test_output, "is_test_suite": True},
    )

    assert len(broadcasted_payloads) == 1
    entry = broadcasted_payloads[0][1]["log_entry"]
    assert entry["source"]       == "TEST"
    assert entry["source_tag"]   == "[TEST]"
    assert entry["status"]       == "error"
    assert entry["status_label"] == "FAIL"
    assert entry["details"]["is_test_suite"] is True
    assert entry["details"]["exit_code"]     == 1
    assert "3 passed" in entry["details"]["raw_output"]


# ── Traceback truncation (unchanged) ─────────────────────────────────────────

def test_truncate_traceback_short_unchanged():
    short = "\n".join(f"line {i}" for i in range(50))
    assert _truncate_traceback(short) == short


def test_truncate_traceback_long_is_truncated():
    total_lines = _TRACEBACK_MAX_HEAD + _TRACEBACK_MAX_TAIL + 200
    long_tb     = "\n".join(f"line {i}" for i in range(total_lines))
    result      = _truncate_traceback(long_tb)
    result_lines = result.splitlines()

    assert "200 lines omitted" in result
    assert result_lines[0] == "line 0"
    assert result_lines[_TRACEBACK_MAX_HEAD] == ""  # blank separator after head
    assert f"line {total_lines - 1}" in result
    assert len(result) < len(long_tb)


@pytest.mark.asyncio
async def test_emit_log_truncates_long_raw_output(monkeypatch):
    broadcasted_payloads = []

    class FakeManager:
        async def broadcast_state(self, session_id: str, state: dict):
            broadcasted_payloads.append((session_id, state))

    monkeypatch.setattr("backend.orchestrator.manager", FakeManager())

    total_lines   = 500
    huge_traceback = "\n".join(f"traceback line {i}" for i in range(total_lines))

    state: AgentState = {"session_id": "session-truncate-1"}
    await emit_log(
        state,
        "Tests failed with huge traceback",
        source="TEST",
        status="error",
        details={"exit_code": 1, "raw_output": huge_traceback, "is_test_suite": True},
    )

    entry   = broadcasted_payloads[0][1]["log_entry"]
    raw_out = entry["details"]["raw_output"]

    assert len(raw_out.splitlines()) < total_lines
    assert "lines omitted"              in raw_out
    assert "traceback line 0"           in raw_out
    assert f"traceback line {total_lines - 1}" in raw_out
