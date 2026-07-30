import os
import shutil

try:
    from .mcp_client import MCPClient
except ImportError:
    from mcp_client import MCPClient


def test_kan61_core_io():
    print("--- STARTING KAN-61 TEST (CORE I/O) ---")

    # 1. Set up the root workspace directory for the test.
    test_root_path = "./temp_workspace"
    if not os.path.exists(test_root_path):
        os.makedirs(test_root_path)

    print(f"[*] Created mock root directory at: {test_root_path}")

    try:
        # 2. Initialize the client.
        client = MCPClient(server_uri="http://localhost:8080", allowed_root_path=test_root_path)

        # 3. Test connect().
        print("\n[Test 1] Connecting client...")
        client.connect()

        # 4. Test writeFile().
        print("\n[Test 2] Writing file...")
        file_path = "test_note.txt"
        content_to_write = "This is a test payload for RevivoAI."

        is_written = client.writeFile(file_path, content_to_write)
        assert is_written == True, "Error: writeFile returned False"
        print("  -> OK: writeFile succeeded.")

        # Try writing to a subdirectory that does not yet exist (to test os.makedirs).
        client.writeFile("logs/execution_log.json", '{"status": "success"}')
        print("  -> OK: writeFile (auto-create subdirectory) succeeded.")

        # 5. Test readFile().
        print("\n[Test 3] Reading file...")
        read_content = client.readFile(file_path)
        assert read_content == content_to_write, "Error: Read content does not match written content!"
        print("  -> OK: readFile read the expected content.")

        # 6. Test listDirectory().
        print("\n[Test 4] Listing directory...")
        # List the root directory (pass the current directory "." or "").
        dir_items = client.listDirectory("")
        print(f"  -> Items found: {dir_items}")
        assert "test_note.txt" in dir_items, "Error: Missing test_note.txt from directory listing"
        assert "logs" in dir_items, "Error: Missing 'logs' directory from directory listing"
        print("  -> OK: listDirectory returned the correct file/folder listing.")

        # 7. Test disconnect().
        print("\n[Test 5] Disconnecting...")
        client.disconnect()

        print("\n--- ✅ ALL KAN-61 TESTS PASSED! ---")

    except Exception as e:
        print(f"\n❌ TEST FAILED WITH ERROR: {e}")

    finally:
        # 8. Clean up - remove the test workspace.
        print("\n[*] Cleaning up the mock workspace...")
        if os.path.exists(test_root_path):
            shutil.rmtree(test_root_path)
            print("  -> Test directory removed.")


if __name__ == "__main__":
    test_kan61_core_io()