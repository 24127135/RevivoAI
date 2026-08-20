import pytest
from unittest.mock import patch
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

        expected_target = {
            **project_file.__dict__,
            "status": project_file.status.value,
        }
        assert payload == {
            "session_id": "session-1",
            "target_file": expected_target,
            "file_path": str(source_file),
            "workspace_dir": str(tmp_path),
            "system_prompt": "",
            "persona": project_file.persona,
            "patched_code": "",
            "iteration_count": 0,
            "max_iterations": 3,
            "api_key": "",
        }
    finally:
        app_module.state.files = original_files
        app_module.state.project_root = original_project_root
        app_module.state.session_id = None


def test_build_orchestrator_payload_includes_user_feedback(tmp_path):
    source_file = tmp_path / "calc.py"
    source_file.write_text("def add(a, b): return a - b\n", encoding="utf-8")

    project_file = ProjectFile(
        file_id="calc-1",
        path=str(source_file),
        legacy_source="def add(a, b): return a - b\n",
        ai_source="",
        status=FileStatus.FAILED,
        language="python",
    )

    original_files = app_module.state.files
    original_feedback = app_module.state.user_feedback

    try:
        app_module.state.files = {project_file.file_id: project_file}
        app_module.state.user_feedback = {"calc-1": "Use addition + instead of subtraction -"}

        payload = app_module.build_orchestrator_payload("calc-1")

        assert "USER FEEDBACK / INSTRUCTIONS FOR PATCH REFACTORING:" in payload["system_prompt"]
        assert "Use addition + instead of subtraction -" in payload["system_prompt"]
    finally:
        app_module.state.files = original_files
        app_module.state.user_feedback = original_feedback


def test_get_staging_summary_counts_sums_statuses():
    original_staging_files = app_module.state.staging_files

    try:
        app_module.state.staging_files = [
            {"status": "done", "pct": 100},
            {"status": "failed", "pct": 62},
            {"status": "uploading", "pct": 45},
            {"status": "done", "pct": 100},
        ]

        assert app_module.get_staging_summary_counts() == {
            "total": 4,
            "done": 2,
            "failed": 1,
            "uploading": 1,
        }
    finally:
        app_module.state.staging_files = original_staging_files


@pytest.mark.asyncio
async def test_load_demo_project_loads_test_scripts():
    original_files = app_module.state.files
    original_root = app_module.state.project_root
    try:
        app_module.state.files = {}
        await app_module.load_demo_project()
        assert len(app_module.state.files) >= 3
        file_paths = [f.path for f in app_module.state.files.values()]
        assert any("01_Global_State_Encapsulation.py" in p for p in file_paths)
    finally:
        app_module.state.files = original_files
        app_module.state.project_root = original_root


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
@patch("nicegui.ui.notify")
def test_run_translation_simulation_sets_busy_state_without_backend_session(mock_notify):
    project_file = ProjectFile(
        file_id="file-2",
        path="sample.py",
        legacy_source="print('hello')\n",
        ai_source="",
        status=FileStatus.QUEUED,
        language="python",
    )

    original_files = app_module.state.files
    original_active_buffer = app_module.state.active_buffer
    original_is_thinking = app_module.state.is_thinking
    original_session_id = app_module.state.session_id

    try:
        app_module.state.files = {project_file.file_id: project_file}
        app_module.state.active_buffer = project_file.file_id
        app_module.state.is_thinking = False
        app_module.state.session_id = None

        app_module.run_translation_simulation(project_file.file_id)

        assert app_module.state.is_thinking is True
        assert project_file.status == FileStatus.TRANSLATING
        assert app_module.state.agent_state[project_file.file_id] == "Starting"
    finally:
        app_module.state.files = original_files
        app_module.state.active_buffer = original_active_buffer
        app_module.state.is_thinking = original_is_thinking
        app_module.state.session_id = original_session_id


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
@patch("nicegui.ui.notify")
def test_merge_project_files_into_workspace_adds_unique_files(mock_notify):
    existing_file = ProjectFile(
        file_id="file-existing",
        path="/tmp/existing.py",
        legacy_source="print('existing')\n",
        ai_source="",
        status=FileStatus.QUEUED,
        language="python",
    )
    new_file = ProjectFile(
        file_id="file-new",
        path="/tmp/new.py",
        legacy_source="print('new')\n",
        ai_source="",
        status=FileStatus.QUEUED,
        language="python",
    )
    duplicate_file = ProjectFile(
        file_id="file-duplicate",
        path="/tmp/existing.py",
        legacy_source="print('duplicate')\n",
        ai_source="",
        status=FileStatus.QUEUED,
        language="python",
    )

    original_files = app_module.state.files
    original_project_root = app_module.state.project_root
    original_active_buffer = app_module.state.active_buffer

    try:
        app_module.state.files = {existing_file.file_id: existing_file}
        app_module.state.project_root = None
        app_module.state.active_buffer = None

        result = app_module.merge_project_files_into_workspace([new_file, duplicate_file], source_root="/tmp/project")

        assert result == {"added": 1, "skipped": 1}
        assert app_module.state.files[new_file.file_id] is new_file
        assert app_module.state.project_root == "/tmp/project"
        assert app_module.state.active_buffer == new_file.file_id
    finally:
        app_module.state.files = original_files
        app_module.state.project_root = original_project_root
        app_module.state.active_buffer = original_active_buffer