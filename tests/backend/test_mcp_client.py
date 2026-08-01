"""
Tests for backend/mcp_client.py — MCPClient security boundaries (KAN-63).

Naming follows README.md conventions:
    test_<component>_<scenario>_<expected_behavior>

Covers the two acceptance criteria for KAN-63:
    1. Reading a file inside the workspace succeeds.
    2. Reading a file outside the workspace explicitly fails and is logged.

Run with: poetry run pytest tests/backend/test_mcp_client.py -v
"""
import logging
import os
import shutil

import pytest

from backend.mcp_client import MCPClient


@pytest.fixture
def workspace():
    """Isolated temp workspace, mirroring the fixture style already used in this suite."""
    test_root = "./temp_workspace_security"
    if not os.path.exists(test_root):
        os.makedirs(test_root)
    yield test_root
    if os.path.exists(test_root):
        shutil.rmtree(test_root)


@pytest.fixture
def connected_client(workspace):
    client = MCPClient(server_uri="http://localhost:8080", allowed_root_path=workspace)
    client.connect()
    yield client
    client.disconnect()


# ---------------------------------------------------------------------------
# Acceptance criterion 1: reading a file inside the workspace succeeds
# ---------------------------------------------------------------------------

def test_read_file_inside_workspace_succeeds(connected_client, workspace):
    target = os.path.join(workspace, "legacy_script.py")
    with open(target, "w", encoding="utf-8") as f:
        f.write("print('legacy code')")

    content = connected_client.readFile("legacy_script.py")

    assert content == "print('legacy code')"


def test_read_file_inside_nested_workspace_subdirectory_succeeds(connected_client, workspace):
    nested_dir = os.path.join(workspace, "analytics")
    os.makedirs(nested_dir)
    with open(os.path.join(nested_dir, "model.py"), "w", encoding="utf-8") as f:
        f.write("import numpy as np")

    content = connected_client.readFile("analytics/model.py")

    assert content == "import numpy as np"


# ---------------------------------------------------------------------------
# Acceptance criterion 2: reading outside the workspace fails AND is logged
# ---------------------------------------------------------------------------

def test_read_file_outside_workspace_via_parent_traversal_raises_permission_error(connected_client):
    with pytest.raises(PermissionError, match="Directory traversal attempt blocked"):
        connected_client.readFile("../outside_workspace.py")


def test_read_file_outside_workspace_via_absolute_path_raises_permission_error(connected_client, tmp_path):
    outside_file = tmp_path / "secret.py"
    outside_file.write_text("SECRET = 'do not read'")

    with pytest.raises(PermissionError, match="Directory traversal attempt blocked"):
        connected_client.readFile(str(outside_file))


def test_read_file_outside_workspace_via_nested_traversal_raises_permission_error(connected_client):
    with pytest.raises(PermissionError, match="Directory traversal attempt blocked"):
        connected_client.readFile("subdir/../../outside_workspace.py")


def test_read_file_outside_workspace_blocked_attempt_is_logged_as_warning(connected_client, caplog):
    with caplog.at_level(logging.WARNING, logger="backend.mcp_client"):
        with pytest.raises(PermissionError):
            connected_client.readFile("../outside_workspace.py")

    security_logs = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(security_logs) == 1
    assert "[Security]" in security_logs[0].message
    assert "traversal attempt blocked" in security_logs[0].message.lower()


def test_read_file_outside_workspace_log_includes_requested_path_for_audit(connected_client, caplog):
    with caplog.at_level(logging.WARNING, logger="backend.mcp_client"):
        with pytest.raises(PermissionError):
            connected_client.readFile("../../etc/passwd")

    log_message = caplog.records[0].message
    assert "../../etc/passwd" in log_message


def test_read_file_outside_workspace_log_includes_session_id_for_audit(workspace, caplog):
    client = MCPClient(
        server_uri="http://localhost:8080",
        allowed_root_path=workspace,
        session_id="test-session-abc123",
    )
    client.connect()

    with caplog.at_level(logging.WARNING, logger="backend.mcp_client"):
        with pytest.raises(PermissionError):
            client.readFile("../outside_workspace.py")

    assert "test-session-abc123" in caplog.records[0].message


def test_read_file_inside_workspace_does_not_emit_security_warning(connected_client, workspace, caplog):
    target = os.path.join(workspace, "safe_file.py")
    with open(target, "w", encoding="utf-8") as f:
        f.write("x = 1")

    with caplog.at_level(logging.WARNING, logger="backend.mcp_client"):
        connected_client.readFile("safe_file.py")

    security_warnings = [r for r in caplog.records if "[Security]" in r.message]
    assert security_warnings == []


def test_read_file_nonexistent_file_inside_workspace_raises_file_not_found(connected_client):
    # Not a security boundary case — confirms normal I/O errors aren't
    # accidentally swallowed or misreported as PermissionError.
    with pytest.raises(FileNotFoundError):
        connected_client.readFile("does_not_exist.py")


def test_mcp_client_io_operations(workspace):
    """Verifies standard I/O operations for KAN-61."""
    client = MCPClient(server_uri="http://localhost:8080", allowed_root_path=workspace)
    client.connect()

    # Write file
    assert client.writeFile("test_note.txt", "payload") is True
    assert client.writeFile("logs/log.json", '{"status":"ok"}') is True

    # Read file
    assert client.readFile("test_note.txt") == "payload"

    # List directory
    items = client.listDirectory("")
    assert "test_note.txt" in items
    assert "logs" in items

    client.disconnect()


def test_mcp_client_security_boundary(workspace):
    """Verifies that the client blocks path traversal (KAN-62)."""
    client = MCPClient(server_uri="http://localhost:8080", allowed_root_path=workspace)
    client.connect()

    # Attempt to write to a path outside the allowed_root_path (e.g., parent directory)
    with pytest.raises(PermissionError):
        client.writeFile("../malicious.txt", "hacked")