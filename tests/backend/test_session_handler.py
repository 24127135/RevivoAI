"""
Tests for backend/session_handler.py

Naming follows README.md conventions:
    test_<component>_<scenario>_<expected_behavior>

Supabase is fully mocked - no real database connection is required to run
this suite. Run with: poetry run pytest -m tests/backend/test_session_handler.py
"""
import os
from unittest.mock import MagicMock, patch

import pytest

from backend.session_handler import SessionHandler, VALID_STATUSES


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_response(data):
    """Builds a fake Supabase response object exposing .data like the real client."""
    response = MagicMock()
    response.data = data
    return response


@pytest.fixture
def mock_supabase():
    """Patches the module-level supabase_db client used by SessionHandler."""
    with patch("backend.session_handler.supabase_db") as mock_db:
        yield mock_db


@pytest.fixture
def workspace_root(tmp_path, monkeypatch):
    """Redirects BASE_WORKSPACE_DIR to a pytest-managed temp dir for isolation."""
    monkeypatch.setattr("backend.session_handler.BASE_WORKSPACE_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture
def handler(mock_supabase, workspace_root):
    """A SessionHandler wired to the mocked Supabase client and temp workspace root."""
    h = SessionHandler()
    return h


# ---------------------------------------------------------------------------
# initialize_session
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_initialize_session_success_provisions_workspace_and_returns_uuid(
    handler, mock_supabase, workspace_root
):
    mock_supabase.table.return_value.insert.return_value.execute.return_value = make_response(
        [{"session_id": "whatever", "user_id": "user-1", "is_active": True}]
    )

    session_id = await handler.initialize_session(user_id="user-1")

    assert session_id is not None
    assert os.path.isdir(os.path.join(str(workspace_root), session_id))

    _, kwargs = mock_supabase.table.return_value.insert.call_args
    payload = mock_supabase.table.return_value.insert.call_args[0][0]
    assert payload["session_id"] == session_id
    assert payload["user_id"] == "user-1"
    assert payload["is_active"] is True
    assert "created_at" in payload
    assert "expires_at" in payload


@pytest.mark.asyncio
async def test_initialize_session_rls_blocks_insert_cleans_up_workspace_returns_none(
    handler, mock_supabase, workspace_root
):
    # Supabase can return HTTP 200 with zero rows when Row Level Security blocks
    # the write silently, without raising an exception.
    mock_supabase.table.return_value.insert.return_value.execute.return_value = make_response([])

    session_id = await handler.initialize_session(user_id="user-1")

    assert session_id is None
    # No leftover directories should remain under the workspace root.
    assert os.listdir(str(workspace_root)) == []


@pytest.mark.asyncio
async def test_initialize_session_db_error_cleans_up_workspace_and_reraises(
    handler, mock_supabase, workspace_root
):
    mock_supabase.table.return_value.insert.return_value.execute.side_effect = RuntimeError("connection refused")

    with pytest.raises(RuntimeError, match="connection refused"):
        await handler.initialize_session(user_id="user-1")

    assert os.listdir(str(workspace_root)) == []


@pytest.mark.asyncio
async def test_initialize_session_workspace_creation_failure_raises_without_calling_db(
    handler, mock_supabase, monkeypatch
):
    def _boom(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr("backend.session_handler.os.makedirs", _boom)

    with pytest.raises(OSError, match="disk full"):
        await handler.initialize_session(user_id="user-1")

    mock_supabase.table.return_value.insert.assert_not_called()


# ---------------------------------------------------------------------------
# get_session
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_session_found_returns_row_with_workspace_path_attached(
    handler, mock_supabase, workspace_root
):
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = make_response(
        [{"session_id": "sess-1", "user_id": "user-1", "is_active": True}]
    )

    result = await handler.get_session("sess-1")

    assert result["session_id"] == "sess-1"
    assert result["workspace_path"] == os.path.join(str(workspace_root), "sess-1")


@pytest.mark.asyncio
async def test_get_session_not_found_returns_none(handler, mock_supabase):
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = make_response([])

    result = await handler.get_session("missing-id")

    assert result is None


@pytest.mark.asyncio
async def test_get_session_db_error_propagates(handler, mock_supabase):
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.side_effect = RuntimeError("timeout")

    with pytest.raises(RuntimeError, match="timeout"):
        await handler.get_session("sess-1")


# ---------------------------------------------------------------------------
# update_session_status
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_session_status_invalid_value_raises_value_error(handler):
    with pytest.raises(ValueError, match="Invalid status"):
        await handler.update_session_status("sess-1", "closed")


@pytest.mark.asyncio
@pytest.mark.parametrize("status", sorted(VALID_STATUSES))
async def test_update_session_status_valid_values_are_accepted(handler, mock_supabase, status):
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = make_response(
        [{"session_id": "sess-1", "is_active": status == "active"}]
    )

    result = await handler.update_session_status("sess-1", status)

    assert result is not None
    call_args, _ = mock_supabase.table.return_value.update.call_args
    assert call_args[0] == {"is_active": status == "active"}


@pytest.mark.asyncio
async def test_update_session_status_not_found_returns_none(handler, mock_supabase):
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = make_response([])

    result = await handler.update_session_status("missing-id", "active")

    assert result is None


# ---------------------------------------------------------------------------
# destroy_session
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_destroy_session_not_found_returns_false_without_touching_delete(handler, mock_supabase):
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = make_response([])

    result = await handler.destroy_session("missing-id")

    assert result is False
    mock_supabase.table.return_value.delete.assert_not_called()


@pytest.mark.asyncio
async def test_destroy_session_hard_deletes_row_not_soft_updates(handler, mock_supabase, workspace_root):
    session_id = "sess-1"
    workspace_path = os.path.join(str(workspace_root), session_id)
    os.makedirs(workspace_path)

    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = make_response(
        [{"session_id": session_id, "is_active": True}]
    )
    mock_supabase.table.return_value.delete.return_value.eq.return_value.execute.return_value = make_response(
        [{"session_id": session_id}]
    )

    result = await handler.destroy_session(session_id)

    assert result is True
    assert not os.path.exists(workspace_path)
    mock_supabase.table.return_value.delete.assert_called_once()
    mock_supabase.table.return_value.update.assert_not_called()


@pytest.mark.asyncio
async def test_destroy_session_workspace_cleanup_failure_still_deletes_db_row(
    handler, mock_supabase, workspace_root, monkeypatch
):
    session_id = "sess-1"
    workspace_path = os.path.join(str(workspace_root), session_id)
    os.makedirs(workspace_path)

    def _boom(*args, **kwargs):
        raise OSError("permission denied")

    monkeypatch.setattr("backend.session_handler.shutil.rmtree", _boom)

    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = make_response(
        [{"session_id": session_id, "is_active": True}]
    )
    mock_supabase.table.return_value.delete.return_value.eq.return_value.execute.return_value = make_response(
        [{"session_id": session_id}]
    )

    result = await handler.destroy_session(session_id)

    # DB is the source of truth: a filesystem cleanup failure must not block the delete.
    assert result is True
    mock_supabase.table.return_value.delete.assert_called_once()


@pytest.mark.asyncio
async def test_destroy_session_delete_returns_empty_data_returns_false(handler, mock_supabase, workspace_root):
    session_id = "sess-1"
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = make_response(
        [{"session_id": session_id, "is_active": True}]
    )
    mock_supabase.table.return_value.delete.return_value.eq.return_value.execute.return_value = make_response([])

    result = await handler.destroy_session(session_id)

    assert result is False


@pytest.mark.asyncio
async def test_destroy_session_db_delete_error_returns_false(handler, mock_supabase, workspace_root):
    session_id = "sess-1"
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = make_response(
        [{"session_id": session_id, "is_active": True}]
    )
    mock_supabase.table.return_value.delete.return_value.eq.return_value.execute.side_effect = RuntimeError("db down")

    result = await handler.destroy_session(session_id)

    assert result is False


# ---------------------------------------------------------------------------
# reap_expired_sessions
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reap_expired_sessions_none_expired_returns_zero(handler, mock_supabase):
    mock_supabase.table.return_value.select.return_value.lte.return_value.execute.return_value = make_response([])

    count = await handler.reap_expired_sessions()

    assert count == 0


@pytest.mark.asyncio
async def test_reap_expired_sessions_query_does_not_filter_by_is_active(handler, mock_supabase):
    # Regression guard: a session deactivated long before expiry must still be
    # reaped once expires_at passes, so is_active must NOT be part of the filter.
    mock_supabase.table.return_value.select.return_value.lte.return_value.execute.return_value = make_response([])

    await handler.reap_expired_sessions()

    mock_supabase.table.return_value.select.return_value.eq.assert_not_called()


@pytest.mark.asyncio
async def test_reap_expired_sessions_destroys_each_expired_session_and_counts_successes(
    handler, mock_supabase, workspace_root
):
    mock_supabase.table.return_value.select.return_value.lte.return_value.execute.return_value = make_response(
        [{"session_id": "expired-1"}, {"session_id": "expired-2"}]
    )

    async def fake_destroy(session_id):
        return session_id == "expired-1"  # simulate one success, one failure

    handler.destroy_session = fake_destroy

    count = await handler.reap_expired_sessions()

    assert count == 1


@pytest.mark.asyncio
async def test_reap_expired_sessions_query_error_returns_zero(handler, mock_supabase):
    mock_supabase.table.return_value.select.return_value.lte.return_value.execute.side_effect = RuntimeError("db down")

    count = await handler.reap_expired_sessions()

    assert count == 0