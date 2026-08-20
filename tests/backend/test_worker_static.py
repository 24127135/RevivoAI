"""
tests/backend/test_worker_static.py
------------------------------------
Verify that:
  1. The FastAPI app has a /monaco-workers static mount.
  2. All four required worker proxy files exist on disk.
  3. Each worker file references importScripts() pointing to the Monaco CDN.
  4. MonacoEnvironment getWorkerUrl routing covers the expected labels.
"""
from pathlib import Path
import pytest
from httpx import AsyncClient, ASGITransport


@pytest.mark.asyncio
async def test_monaco_workers_route_is_mounted():
    """The /monaco-workers route must be present in the FastAPI app's routes."""
    from backend.main import app
    route_paths = [getattr(r, "path", None) for r in app.routes]
    assert "/monaco-workers" in route_paths, (
        f"Expected '/monaco-workers' mount, found routes: {route_paths}"
    )


@pytest.mark.asyncio
async def test_worker_proxy_files_exist():
    """All four worker proxy scripts must be present in frontend/monaco_workers/."""
    workers_dir = Path(__file__).parent.parent.parent / "frontend" / "monaco_workers"
    assert workers_dir.is_dir(), f"Worker directory missing: {workers_dir}"

    expected = ["editor.worker.js", "json.worker.js", "css.worker.js", "ts.worker.js"]
    for name in expected:
        path = workers_dir / name
        assert path.exists(), f"Missing worker proxy: {path}"
        assert path.stat().st_size > 0, f"Worker proxy is empty: {path}"


@pytest.mark.asyncio
async def test_worker_proxy_content():
    """Each worker script must call importScripts with a Monaco CDN URL."""
    workers_dir = Path(__file__).parent.parent.parent / "frontend" / "monaco_workers"
    cdn_base    = "cdn.jsdelivr.net/npm/monaco-editor"

    for js_file in workers_dir.glob("*.worker.js"):
        content = js_file.read_text(encoding="utf-8")
        assert "importScripts" in content, (
            f"{js_file.name}: missing importScripts() call"
        )
        assert cdn_base in content, (
            f"{js_file.name}: importScripts URL does not reference Monaco CDN"
        )
        assert "self.MonacoEnvironment" in content, (
            f"{js_file.name}: missing self.MonacoEnvironment baseUrl config"
        )


@pytest.mark.asyncio
async def test_editor_worker_served_via_http():
    """editor.worker.js must be served with 200 and correct content-type."""
    from backend.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/monaco-workers/editor.worker.js")
    assert resp.status_code == 200
    content_type = resp.headers.get("content-type", "")
    # FastAPI StaticFiles sets application/javascript or text/javascript
    assert "javascript" in content_type or "application/octet-stream" in content_type, (
        f"Unexpected content-type: {content_type}"
    )
    assert "importScripts" in resp.text


@pytest.mark.asyncio
async def test_unknown_worker_file_returns_404():
    """A request for a non-existent worker script must return 404."""
    from backend.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/monaco-workers/nonexistent.worker.js")
    assert resp.status_code == 404


def test_monaco_lang_mapping():
    """_monaco_lang must normalise known languages and default to plaintext."""
    from frontend.monaco_editor import _monaco_lang
    assert _monaco_lang("python")     == "python"
    assert _monaco_lang("Python")     == "python"    # case-insensitive
    assert _monaco_lang("js")         == "javascript"
    assert _monaco_lang("ts")         == "typescript"
    assert _monaco_lang("json")       == "json"
    assert _monaco_lang("css")        == "css"
    assert _monaco_lang("unknown")    == "plaintext"
    assert _monaco_lang("")           == "plaintext"


def test_monaco_editor_update_original_value():
    """update_original_value must update the prop without error."""
    from frontend.monaco_editor import MonacoEditor
    editor = MonacoEditor(
        value="new code",
        original_value="old code",
        diff_mode=True,
        debounce_delay=1000,
    )
    assert editor._props["original_value"] == "old code"
    assert editor._props["debounce_delay"] == 1000
    # update_original_value should change the prop
    result = editor.update_original_value("newer old code")
    assert result is editor   # returns self for chaining
    assert editor._props["original_value"] == "newer old code"


def test_monaco_editor_debounced_event_handlers():
    """MonacoEditor must bind change and save callbacks properly."""
    from frontend.monaco_editor import MonacoEditor

    received_change = []
    received_save = []

    editor = MonacoEditor(
        value="initial code",
        on_change=lambda text: received_change.append(text),
        on_save=lambda text: received_save.append(text),
        debounce_delay=1000,
    )

    listener_types = [l.type for l in editor._event_listeners.values()]
    assert "change" in listener_types
    assert "save" in listener_types
    assert editor._props["debounce_delay"] == 1000
