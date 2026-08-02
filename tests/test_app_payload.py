from backend.models import FileStatus, ProjectFile

import app as app_module


def test_build_orchestrator_payload_includes_workspace_and_file_context(tmp_path):
    source_file = tmp_path / "sample.py"
    source_file.write_text("print('hello')\n", encoding="utf-8")

    project_file = ProjectFile(
        file_id="file-1",
        path=str(source_file),
        legacy_source="print('hello')\n",
        ai_source="",
        status=FileStatus.QUEUED,
        language="python",
    )

    original_files = app_module.state.files
    original_project_root = app_module.state.project_root

    try:
        app_module.state.files = {project_file.file_id: project_file}
        app_module.state.project_root = str(tmp_path)
        app_module.state.session_id = "session-1"

        payload = app_module.build_orchestrator_payload(project_file.file_id)

        assert payload == {
            "session_id": "session-1",
            "target_file": project_file,
            "file_path": str(source_file),
            "workspace_dir": str(tmp_path),
            "system_prompt": "",
            "persona": project_file.persona,
            "patched_code": "",
            "iteration_count": 0,
            "max_iterations": 3,
        }
    finally:
        app_module.state.files = original_files
        app_module.state.project_root = original_project_root
        app_module.state.session_id = None