from backend.models import FileStatus, ProjectFile
from backend.orchestrator import orchestrator_app


def test_orchestrator_app_flow(tmp_path):
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
    initial_state = {
        "target_file": project_file,
        "error_trace": "Traceback (most recent call last):\nValueError: boom",
        "system_prompt": "You are a tester.",
    }

    final_state = orchestrator_app.invoke(initial_state)

    assert "structural_context" in final_state
    assert "patched_code" in final_state
