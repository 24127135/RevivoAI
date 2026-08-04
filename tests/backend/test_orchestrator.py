import pytest

from backend.models import FileStatus, ProjectFile
from backend import orchestrator as orchestrator_module
from backend.orchestrator import orchestrator_app, route_after_telemetry


def test_route_after_telemetry_clamps_retry_limit_to_five():
    assert route_after_telemetry({"docker_exit_code": 0, "iteration_count": 1, "max_iterations": 99}) == "__end__"
    assert route_after_telemetry({"docker_exit_code": 1, "iteration_count": 4, "max_iterations": 99}) == "llm_patch_node"
    assert route_after_telemetry({"docker_exit_code": 1, "iteration_count": 5, "max_iterations": 99}) == "__end__"


@pytest.mark.asyncio
async def test_orchestrator_app_flow_success_path(monkeypatch, tmp_path):
    source_file = tmp_path / "sample.py"
    source_file.write_text("def hello():\n    pass\n", encoding="utf-8")

    project_file = ProjectFile(
        file_id="file_1",
        path=str(source_file),
        legacy_source=source_file.read_text(encoding="utf-8"),
        ai_source="",
        status=FileStatus.QUEUED,
        language="python",
    )

    class FakePatchNode:
        def __init__(self, llm_client=None):
            self.llm_client = llm_client

        def execute(self, state: dict) -> dict:
            return {
                "patched_code": "def hello():\n    return 'hi'\n",
                "status": "PATCH_GENERATED",
                "raw": "fake raw output",
            }

    class FakeSandbox:
        last_instance = None

        def __init__(self):
            FakeSandbox.last_instance = self
            self.created = False
            self.destroyed = False

        def createSandbox(self, image: str = "python:3.10-slim") -> str:
            self.created = True
            return "container-1"

        def injectCode(self, containerPath: str, content: str) -> None:
            self.injected_path = containerPath
            self.injected_content = content

        def runScript(self, scriptPath: str, timeout_sec: int = 30) -> dict:
            return {
                "status": "SUCCESS",
                "exit_code": 0,
                "stdout_buffer": "ok\n",
                "stderr_traceback": "",
            }

        def destroySandbox(self) -> None:
            self.destroyed = True

    telemetry_calls = []

    async def fake_log_agent_state(session_id: str, state: dict) -> bool:
        telemetry_calls.append((session_id, state))
        return True

    monkeypatch.setattr(orchestrator_module, "LLMPatchNode", FakePatchNode)
    monkeypatch.setattr(orchestrator_module, "DockerSandboxManager", FakeSandbox)
    monkeypatch.setattr(orchestrator_module, "log_agent_state", fake_log_agent_state)

    initial_state = {
        "target_file": project_file,
        "error_trace": "Traceback (most recent call last):\nValueError: boom",
        "system_prompt": "You are a tester.",
        "session_id": "session-123",
        "max_iterations": 3,
    }

    final_state = await orchestrator_app.ainvoke(initial_state)

    assert final_state["iteration_count"] == 1
    assert final_state["docker_exit_code"] == 0
    assert "return 'hi'" in FakeSandbox.last_instance.injected_content
    assert FakeSandbox.last_instance.destroyed is True
    assert telemetry_calls[0][0] == "session-123"


@pytest.mark.asyncio
async def test_orchestrator_app_flow_failure_path_records_traceback_and_stops(monkeypatch, tmp_path):
    source_file = tmp_path / "sample.py"
    source_file.write_text("def hello():\n    pass\n", encoding="utf-8")

    project_file = ProjectFile(
        file_id="file_2",
        path=str(source_file),
        legacy_source=source_file.read_text(encoding="utf-8"),
        ai_source="",
        status=FileStatus.QUEUED,
        language="python",
    )

    class FakePatchNode:
        def __init__(self, llm_client=None):
            self.llm_client = llm_client

        def execute(self, state: dict) -> dict:
            return {
                "patched_code": "def hello():\n    raise RuntimeError('boom')\n",
                "status": "PATCH_GENERATED",
                "raw": "fake raw output",
            }

    class FakeSandbox:
        def createSandbox(self, image: str = "python:3.10-slim") -> str:
            return "container-2"

        def injectCode(self, containerPath: str, content: str) -> None:
            return None

        def runScript(self, scriptPath: str, timeout_sec: int = 30) -> dict:
            return {
                "status": "FAILURE",
                "exit_code": 2,
                "stdout_buffer": "",
                "stderr_traceback": "Traceback: boom",
            }

        def destroySandbox(self) -> None:
            return None

    telemetry_calls = []

    async def fake_log_agent_state(session_id: str, state: dict) -> bool:
        telemetry_calls.append((session_id, state))
        return True

    monkeypatch.setattr(orchestrator_module, "LLMPatchNode", FakePatchNode)
    monkeypatch.setattr(orchestrator_module, "DockerSandboxManager", FakeSandbox)
    monkeypatch.setattr(orchestrator_module, "log_agent_state", fake_log_agent_state)

    final_state = await orchestrator_app.ainvoke(
        {
            "target_file": project_file,
            "error_trace": "Traceback (most recent call last):\nValueError: boom",
            "system_prompt": "You are a tester.",
            "session_id": "session-456",
            "max_iterations": 1,
        }
    )

    assert final_state["iteration_count"] == 1
    assert final_state["docker_exit_code"] == 2
    assert len(telemetry_calls) == 1