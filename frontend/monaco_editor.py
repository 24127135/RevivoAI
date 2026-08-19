"""
frontend/monaco_editor.py
--------------------------
NiceGUI 3.x custom Element that wraps Monaco Editor via a local Vue 3
component (monaco_editor.js in the same directory).

Web Worker Architecture
-----------------------
Monaco offloads CPU-intensive language processing (diff computation, syntax
tokenization, bracket matching) to dedicated Web Workers.  Because browsers
enforce a same-origin policy for workers, we cannot point directly at CDN
worker URLs.

Solution implemented in monaco_editor.js:
  1. ``window.MonacoEnvironment.getWorkerUrl()`` is installed before AMD
     ``require(['vs/editor/editor.main'])`` fires.
  2. The function returns a FastAPI-served URL:
     ``http://localhost:8000/monaco-workers/<type>.worker.js``
  3. Each proxy file at that URL calls ``importScripts()`` to fetch the real
     Monaco worker bundle from the CDN — importScripts is permitted inside
     a Worker context regardless of origin.

FastAPI serves the proxy scripts via:
    app.mount("/monaco-workers", StaticFiles(directory="frontend/monaco_workers"))

Diff Editor
-----------
When ``diff_mode=True``, Monaco creates a ``DiffEditor`` with two models:
  * **original** model  ← ``original_value``  (legacy / left pane)
  * **modified** model  ← ``value``            (AI patch / right pane)

Monaco computes the unified diff natively inside the diff worker — no
Python calculation needed.  Watchers on both ``value`` and ``original_value``
props push updates to the client-side models without re-mounting the editor.

Usage
-----
    from frontend.monaco_editor import MonacoEditor

    # Read-only viewer
    MonacoEditor(value=code, language="python", readonly=True)
        .classes("w-full").style("height:520px;")

    # Monaco diff editor (side-by-side, read-only)
    MonacoEditor(
        value=ai_code,
        original_value=legacy_code,
        language="python",
        readonly=True,
        diff_mode=True,
        primary_line=42,        # optional: scroll & highlight error line
    ).classes("w-full").style("height:600px;")

    # Writable editor — receive changes in Python
    def handle_change(new_text: str):
        state.edit_buffer[file_id] = new_text

    MonacoEditor(
        value=current_draft,
        original_value=original_draft,
        language="python",
        readonly=False,
        diff_mode=True,
        on_change=handle_change,
    ).classes("w-full").style("height:480px;")
"""

from __future__ import annotations

from typing import Callable, Optional
from nicegui.element import Element

# ---------------------------------------------------------------------------
# Language normalisation
# ---------------------------------------------------------------------------

_LANG_MAP: dict[str, str] = {
    "python":     "python",
    "r":          "r",
    "c":          "c",
    "cpp":        "cpp",
    "js":         "javascript",
    "javascript": "javascript",
    "ts":         "typescript",
    "typescript": "typescript",
    "json":       "json",
    "css":        "css",
    "html":       "html",
}


def _monaco_lang(language: str) -> str:
    """Map internal language codes to Monaco language identifiers."""
    return _LANG_MAP.get((language or "").lower(), "plaintext")


# ---------------------------------------------------------------------------
# MonacoEditor NiceGUI Element
# ---------------------------------------------------------------------------

class MonacoEditor(Element, component="monaco_editor.js"):
    """
    A Monaco Editor embedded in NiceGUI via a Vue 3 component.

    Language-specific Web Workers are routed through FastAPI's
    ``/monaco-workers/`` static endpoint so they satisfy the browser's
    same-origin constraint for workers.

    Parameters
    ----------
    value : str
        Source code content (the "modified" / AI side in diff mode).
    language : str
        Syntax highlighting language. Accepts ``'python'``, ``'r'``,
        ``'c'``, ``'cpp'``, ``'javascript'``, ``'typescript'``, ``'json'``,
        ``'css'``, ``'html'``, etc.
    readonly : bool
        When ``True`` the editor is non-editable.
    diff_mode : bool
        When ``True`` renders a side-by-side Monaco diff editor.
        ``original_value`` is used as the left (legacy) side.
        Monaco computes the diff natively client-side.
    original_value : str
        The "original" (left/legacy) content shown in diff mode.
    primary_line : int | None
        If provided, the editor scrolls to this line and applies an
        amber highlight decoration (used to surface sandbox error lines).
    height : str
        CSS height for the editor container (default ``'600px'``).
    debounce_delay : int
        Local millisecond delay for debouncing text changes before pushing
        canonical updates back to Python over WebSocket (default ``1000``).
    on_change : callable | None
        Python callback invoked when content changes after the 1000ms debounce
        or on editor blur. Receives the updated code ``str``.
    on_save : callable | None
        Python callback invoked when user triggers a manual save (Ctrl+S / Cmd+S).
    """

    def __init__(
        self,
        value: str = "",
        language: str = "python",
        readonly: bool = True,
        diff_mode: bool = False,
        original_value: str = "",
        primary_line: Optional[int] = None,
        height: str = "600px",
        debounce_delay: int = 1000,
        on_change: Optional[Callable[[str], None]] = None,
        on_save: Optional[Callable[[str], None]] = None,
    ) -> None:
        super().__init__()

        lang = _monaco_lang(language)

        # These map directly to the Vue component's `props`
        self._props["value"]          = value
        self._props["language"]       = lang
        self._props["readonly"]       = readonly
        self._props["diff_mode"]      = diff_mode
        self._props["original_value"] = original_value
        self._props["primary_line"]   = primary_line or 0
        self._props["height"]         = height
        self._props["debounce_delay"] = debounce_delay

        if on_change:
            # Vue emits: this.$emit('change', editor.getValue())
            # NiceGUI delivers e.args as [value] or dict
            self.on("change", lambda e: on_change(
                e.args[0] if isinstance(e.args, (list, tuple)) and e.args else (e.args if isinstance(e.args, str) else "")
            ))

        if on_save:
            # Vue emits: this.$emit('save', editor.getValue())
            self.on("save", lambda e: on_save(
                e.args[0] if isinstance(e.args, (list, tuple)) and e.args else (e.args if isinstance(e.args, str) else "")
            ))

    # ------------------------------------------------------------------
    # Programmatic update helpers — push property updates to the client
    # without destroying and re-creating the editor instance.
    # ------------------------------------------------------------------

    def update_value(self, value: str) -> "MonacoEditor":
        """Replace the modified (AI) side content from Python."""
        self._props["value"] = value
        self.update()
        return self

    def update_original_value(self, original_value: str) -> "MonacoEditor":
        """Replace the original (legacy) side content in diff mode."""
        self._props["original_value"] = original_value
        self.update()
        return self

    def update_language(self, language: str) -> "MonacoEditor":
        """Switch the syntax highlighting language."""
        self._props["language"] = _monaco_lang(language)
        self.update()
        return self

    def update_readonly(self, readonly: bool) -> "MonacoEditor":
        """Toggle editor read-only state."""
        self._props["readonly"] = readonly
        self.update()
        return self

    async def flush(self) -> None:
        """Trigger immediate client-side flush of pending debounced changes."""
        self.run_method("flush")

    async def save(self) -> None:
        """Trigger client-side manual save action."""
        self.run_method("save")
