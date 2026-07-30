import os
import shutil
import pytest
from backend.mcp_client import MCPClient

@pytest.fixture
def workspace():
    """Fixture to handle setup and teardown of the workspace."""
    test_root = "./temp_workspace"
    if not os.path.exists(test_root):
        os.makedirs(test_root)
    
    yield test_root
    
    # Teardown: Clean up workspace after test finishes
    if os.path.exists(test_root):
        shutil.rmtree(test_root)

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