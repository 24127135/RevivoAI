"""
Tests for backend/docker_sandbox_manager.py

Naming follows README.md conventions:
    test_<component>_<scenario>_<expected_behavior>

Docker is fully mocked - no real Docker daemon is required to run this suite.
Run with: poetry run pytest tests/backend/test_docker_sandbox_manager.py -v
"""
import tarfile
import time
from unittest.mock import MagicMock, patch

import pytest
from docker.errors import APIError, DockerException

from backend.execution.sandbox import DockerSandboxManager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_docker_client():
    """
    Patches docker.from_env() so no real Docker daemon connection is attempted.
    Yields the MagicMock client so tests can configure/inspect calls.
    """
    with patch("backend.execution.sandbox.docker.from_env") as mock_from_env:
        client = MagicMock()
        mock_from_env.return_value = client
        yield client


@pytest.fixture
def mock_container():
    """
    A MagicMock standing in for a docker-py Container object, wired with the
    attributes DockerSandboxManager touches (id, client.api.*, exec_run, etc).
    """
    container = MagicMock()
    container.id = "container-abc123"
    return container


@pytest.fixture
def sandbox_manager(mock_docker_client):
    """
    A DockerSandboxManager constructed against the mocked Docker client.
    Teardown ensures no test leaves a dangling in-memory container reference.
    """
    manager = DockerSandboxManager()
    yield manager
    manager._container = None


@pytest.fixture
def running_sandbox(sandbox_manager, mock_docker_client, mock_container):
    """
    A sandbox_manager with a container already "created" (mocked), ready for
    injectCode()/runScript()/destroySandbox() tests.
    """
    mock_docker_client.containers.run.return_value = mock_container
    sandbox_manager.createSandbox()
    return sandbox_manager


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------

def test_docker_sandbox_manager_daemon_available_initializes_defaults(mock_docker_client):
    manager = DockerSandboxManager()

    assert manager._container is None
    assert manager._image_name == "python:3.10-slim"
    assert manager._memory_limit_mb == 4096
    assert manager._cpu_quota == 100000
    assert manager._cpu_period == 100000
    assert manager._run_as_non_root is True
    assert manager._volume_mounts == []


def test_docker_sandbox_manager_daemon_unavailable_raises_runtime_error():
    with patch("backend.execution.sandbox.docker.from_env") as mock_from_env:
        mock_from_env.side_effect = DockerException("daemon not reachable")

        with pytest.raises(RuntimeError, match="Cannot connect to Docker Daemon"):
            DockerSandboxManager()


# ---------------------------------------------------------------------------
# mountVolume
# ---------------------------------------------------------------------------

def test_mount_volume_default_readonly_appends_ro_bind_string(sandbox_manager):
    sandbox_manager.mountVolume("/host/legacy", "/workspace")

    assert sandbox_manager._volume_mounts == ["/host/legacy:/workspace:ro"]


def test_mount_volume_explicit_readwrite_appends_rw_bind_string(sandbox_manager):
    sandbox_manager.mountVolume("/host/legacy", "/workspace", readOnly=False)

    assert sandbox_manager._volume_mounts == ["/host/legacy:/workspace:rw"]


def test_mount_volume_called_twice_accumulates_both_mounts(sandbox_manager):
    sandbox_manager.mountVolume("/host/a", "/workspace/a")
    sandbox_manager.mountVolume("/host/b", "/workspace/b", readOnly=False)

    assert sandbox_manager._volume_mounts == [
        "/host/a:/workspace/a:ro",
        "/host/b:/workspace/b:rw",
    ]


# ---------------------------------------------------------------------------
# createSandbox
# ---------------------------------------------------------------------------

def test_create_sandbox_success_applies_resource_and_security_constraints(
    sandbox_manager, mock_docker_client, mock_container
):
    mock_docker_client.containers.run.return_value = mock_container

    container_id = sandbox_manager.createSandbox()

    assert container_id == "container-abc123"
    assert sandbox_manager._container_id == "container-abc123"

    _, kwargs = mock_docker_client.containers.run.call_args
    assert kwargs["mem_limit"] == "4096m"          # NFR-RES-01
    assert kwargs["cpu_quota"] == 100000            # NFR-RES-02
    assert kwargs["cpu_period"] == 100000           # NFR-RES-02
    assert kwargs["user"] == "1000:1000"            # NFR-SEC-04 (non-root)
    assert kwargs["network_mode"] == "none"         # NFR-SEC-03 (network isolation)
    assert kwargs["detach"] is True


def test_create_sandbox_run_as_non_root_false_uses_root_user(sandbox_manager, mock_docker_client, mock_container):
    sandbox_manager._run_as_non_root = False
    mock_docker_client.containers.run.return_value = mock_container

    sandbox_manager.createSandbox()

    _, kwargs = mock_docker_client.containers.run.call_args
    assert kwargs["user"] == "root"


def test_create_sandbox_with_registered_mounts_passes_them_to_docker_run(
    sandbox_manager, mock_docker_client, mock_container
):
    sandbox_manager.mountVolume("/host/legacy", "/workspace", readOnly=True)
    mock_docker_client.containers.run.return_value = mock_container

    sandbox_manager.createSandbox()

    _, kwargs = mock_docker_client.containers.run.call_args
    assert kwargs["volumes"] == ["/host/legacy:/workspace:ro"]


def test_create_sandbox_no_mounts_passes_none_for_volumes(sandbox_manager, mock_docker_client, mock_container):
    mock_docker_client.containers.run.return_value = mock_container

    sandbox_manager.createSandbox()

    _, kwargs = mock_docker_client.containers.run.call_args
    assert kwargs["volumes"] is None


def test_create_sandbox_custom_image_overrides_default(sandbox_manager, mock_docker_client, mock_container):
    mock_docker_client.containers.run.return_value = mock_container

    sandbox_manager.createSandbox(image="python:3.12-slim")

    assert sandbox_manager._image_name == "python:3.12-slim"
    _, kwargs = mock_docker_client.containers.run.call_args
    assert kwargs["image"] == "python:3.12-slim"


def test_create_sandbox_docker_api_error_returns_empty_string(sandbox_manager, mock_docker_client):
    mock_docker_client.containers.run.side_effect = APIError("image pull failed")

    container_id = sandbox_manager.createSandbox()

    assert container_id == ""
    assert sandbox_manager._container is None


# ---------------------------------------------------------------------------
# injectCode
# ---------------------------------------------------------------------------

def test_inject_code_without_container_raises_runtime_error(sandbox_manager):
    with pytest.raises(RuntimeError, match="Sandbox has not been initialized"):
        sandbox_manager.injectCode("/workspace/script.py", "print('hello')")


def test_create_sandbox_performs_one_time_root_chown_of_workspace(sandbox_manager, mock_docker_client, mock_container):
    mock_docker_client.containers.run.return_value = mock_container

    sandbox_manager.createSandbox()

    mock_container.exec_run.assert_called_once_with(
        "mkdir -p /workspace && chown -R 1000:1000 /workspace", user="root"
    )


def test_inject_code_creates_parent_directory_as_non_root_user(running_sandbox, mock_container):
    # createSandbox() already fired one root exec_run (the one-time /workspace chown),
    # so injectCode's own mkdir call is the second call and must run as the non-root user.
    running_sandbox.injectCode("/workspace/nested/script.py", "print('hello')")

    mock_container.exec_run.assert_called_with("mkdir -p /workspace/nested", user="1000:1000")
    assert mock_container.exec_run.call_count == 2
    mock_container.put_archive.assert_called_once()

    call_args, _ = mock_container.put_archive.call_args
    assert call_args[0] == "/workspace/nested"


def test_inject_code_relative_path_resolves_under_workspace_root(running_sandbox, mock_container):
    # A bare relative filename must be anchored under /workspace, not container root.
    running_sandbox.injectCode("script.py", "print('hello')")

    mock_container.exec_run.assert_called_with("mkdir -p /workspace", user="1000:1000")
    call_args, _ = mock_container.put_archive.call_args
    assert call_args[0] == "/workspace"


def test_inject_code_relative_traversal_outside_workspace_is_rejected(running_sandbox, mock_container):
    with pytest.raises(PermissionError, match="outside the sandbox workspace"):
        running_sandbox.injectCode("../../etc/passwd", "malicious content")

    mock_container.put_archive.assert_not_called()


def test_inject_code_absolute_path_outside_workspace_is_rejected(running_sandbox, mock_container):
    with pytest.raises(PermissionError, match="outside the sandbox workspace"):
        running_sandbox.injectCode("/etc/passwd", "malicious content")

    mock_container.put_archive.assert_not_called()


def test_inject_code_absolute_path_traversal_via_dotdot_is_rejected(running_sandbox, mock_container):
    with pytest.raises(PermissionError, match="outside the sandbox workspace"):
        running_sandbox.injectCode("/workspace/../../etc/passwd", "malicious content")

    mock_container.put_archive.assert_not_called()


def test_inject_code_workspace_root_itself_is_rejected(running_sandbox, mock_container):
    # A path resolving to the workspace directory itself has no filename target.
    with pytest.raises(PermissionError, match="outside the sandbox workspace"):
        running_sandbox.injectCode("/workspace", "malicious content")

    mock_container.put_archive.assert_not_called()


def test_inject_code_empty_path_raises_value_error(running_sandbox, mock_container):
    with pytest.raises(ValueError, match="must not be empty"):
        running_sandbox.injectCode("", "print('hello')")

    mock_container.put_archive.assert_not_called()


def test_inject_code_absolute_path_already_under_workspace_is_accepted(running_sandbox, mock_container):
    running_sandbox.injectCode("/workspace/analytics/model.py", "print('ok')")

    mock_container.exec_run.assert_called_with("mkdir -p /workspace/analytics", user="1000:1000")
    call_args, _ = mock_container.put_archive.call_args
    assert call_args[0] == "/workspace/analytics"


def test_inject_code_non_root_sandbox_writes_file_owned_by_non_root_uid(running_sandbox, mock_container):
    # Guards against tarfile.TarInfo's uid=0/gid=0 default silently making every
    # injected file root-owned even inside a chowned, non-root workspace dir.
    running_sandbox.injectCode("/workspace/model.py", "print('ok')")

    _, tar_stream = mock_container.put_archive.call_args[0]
    tar_stream.seek(0)
    with tarfile.open(fileobj=tar_stream, mode='r') as tar:
        member = tar.getmembers()[0]
        assert member.name == "model.py"
        assert member.uid == 1000
        assert member.gid == 1000


def test_inject_code_root_sandbox_keeps_root_owned_file(sandbox_manager, mock_docker_client, mock_container):
    sandbox_manager._run_as_non_root = False
    mock_docker_client.containers.run.return_value = mock_container
    sandbox_manager.createSandbox()

    sandbox_manager.injectCode("/workspace/model.py", "print('ok')")

    _, tar_stream = mock_container.put_archive.call_args[0]
    tar_stream.seek(0)
    with tarfile.open(fileobj=tar_stream, mode='r') as tar:
        member = tar.getmembers()[0]
        assert member.uid == 0
        assert member.gid == 0


# ---------------------------------------------------------------------------
# runScript
# ---------------------------------------------------------------------------

def test_run_script_without_container_returns_failure_log(sandbox_manager):
    log = sandbox_manager.runScript("script.py")

    assert log["status"] == "FAILURE"
    assert log["exit_code"] == -1
    assert log["stderr_traceback"] == "Container not running"


def test_run_script_success_returns_success_log_with_captured_output(running_sandbox, mock_container):
    mock_container.client.api.exec_create.return_value = {"Id": "exec-1"}
    mock_container.client.api.exec_start.return_value = (b"result: 42\n", b"")
    mock_container.client.api.exec_inspect.return_value = {"ExitCode": 0}

    log = running_sandbox.runScript("script.py", timeout_sec=2)

    assert log["status"] == "SUCCESS"
    assert log["exit_code"] == 0
    assert log["stdout_buffer"] == "result: 42\n"
    assert log["stderr_traceback"] == ""  # must be empty string on SUCCESS, not None
    assert log["patch_id"] is None
    assert log["execution_time_ms"] >= 0


def test_run_script_nonzero_exit_returns_failure_log_with_traceback(running_sandbox, mock_container):
    mock_container.client.api.exec_create.return_value = {"Id": "exec-2"}
    mock_container.client.api.exec_start.return_value = (b"", b"ZeroDivisionError: division by zero")
    mock_container.client.api.exec_inspect.return_value = {"ExitCode": 1}

    log = running_sandbox.runScript("script.py", timeout_sec=2)

    assert log["status"] == "FAILURE"
    assert log["exit_code"] == 1
    assert log["stderr_traceback"] == "ZeroDivisionError: division by zero"


def test_run_script_success_status_clears_stray_stderr_output(running_sandbox, mock_container):
    # Even if the process printed a benign warning to stderr, SUCCESS must clear it
    # per the Execution_log schema constraint (stderr must be "" on SUCCESS).
    mock_container.client.api.exec_create.return_value = {"Id": "exec-3"}
    mock_container.client.api.exec_start.return_value = (b"ok\n", b"DeprecationWarning: ...")
    mock_container.client.api.exec_inspect.return_value = {"ExitCode": 0}

    log = running_sandbox.runScript("script.py", timeout_sec=2)

    assert log["status"] == "SUCCESS"
    assert log["stderr_traceback"] == ""


def test_run_script_exceeding_timeout_kills_container_and_returns_timeout_log(running_sandbox, mock_container):
    mock_container.client.api.exec_create.return_value = {"Id": "exec-4"}

    def _slow_exec_start(*args, **kwargs):
        time.sleep(0.5)
        return (b"partial output", b"")

    mock_container.client.api.exec_start.side_effect = _slow_exec_start

    log = running_sandbox.runScript("infinite_loop.py", timeout_sec=0.1)

    mock_container.kill.assert_called_once()
    assert log["status"] == "TIMEOUT"
    assert log["exit_code"] is None
    assert log["stdout_buffer"] == ""  # must not fabricate partial output
    assert "SIGKILL" in log["stderr_traceback"]


def test_run_script_unexpected_exception_returns_failure_log(running_sandbox, mock_container):
    mock_container.client.api.exec_create.side_effect = RuntimeError("socket closed")

    log = running_sandbox.runScript("script.py", timeout_sec=2)

    assert log["status"] == "FAILURE"
    assert log["exit_code"] == -1
    assert "socket closed" in log["stderr_traceback"]


def test_run_script_every_call_generates_a_unique_execution_id(running_sandbox, mock_container):
    mock_container.client.api.exec_create.return_value = {"Id": "exec-5"}
    mock_container.client.api.exec_start.return_value = (b"", b"")
    mock_container.client.api.exec_inspect.return_value = {"ExitCode": 0}

    first_log = running_sandbox.runScript("script.py", timeout_sec=2)
    second_log = running_sandbox.runScript("script.py", timeout_sec=2)

    assert first_log["execution_id"] != second_log["execution_id"]


# ---------------------------------------------------------------------------
# destroySandbox
# ---------------------------------------------------------------------------

def test_destroy_sandbox_removes_container_and_resets_state(running_sandbox, mock_container):
    running_sandbox.destroySandbox()

    mock_container.remove.assert_called_once_with(force=True)
    assert running_sandbox._container is None
    assert running_sandbox._container_id is None


def test_destroy_sandbox_swallows_api_error_on_remove(running_sandbox, mock_container):
    mock_container.remove.side_effect = APIError("container already gone")

    running_sandbox.destroySandbox()  # must not raise

    assert running_sandbox._container is None
    assert running_sandbox._container_id is None


def test_destroy_sandbox_without_active_container_is_a_noop(sandbox_manager):
    sandbox_manager.destroySandbox()  # must not raise even if nothing was created

    assert sandbox_manager._container is None