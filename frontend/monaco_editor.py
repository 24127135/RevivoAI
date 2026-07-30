"""
frontend/monaco_editor.py
--------------------------
NiceGUI 3.x custom Element that wraps Monaco Editor via a local Vue 3
component file (monaco_editor.js in the same directory).

NiceGUI's ``component='monaco_editor.js'`` mechanism serves the JS file
from NiceGUI's static server and registers it as a Vue component
automatically — no build step required.

Usage
-----
    from frontend.monaco_editor import MonacoEditor

    # Read-only viewer
    MonacoEditor(value=code, language="python", readonly=True)
        .classes("w-full").style("height:520px;")

    # Monaco diff editor (side-by-side)
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
        language="python",
        readonly=False,
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

    Parameters
    ----------
    value : str
        Source code content (the "modified" side in diff mode).
    language : str
        Syntax highlighting language.  Accepts ``'python'``, ``'r'``,
        ``'c'``, ``'cpp'``, ``'javascript'``, ``'typescript'``, etc.
    readonly : bool
        When ``True`` the editor is non-editable.
    diff_mode : bool
        When ``True`` renders a side-by-side Monaco diff editor.
        ``original_value`` is used as the left (legacy) side.
    original_value : str
        The "original" (left) content shown in diff mode.
    primary_line : int | None
        If provided, the editor scrolls to this line and applies an
        amber highlight decoration (used to surface sandbox error lines).
    on_change : callable | None
        Python callback invoked on every content change in write mode.
        Receives the new text as a ``str`` argument.
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
        on_change: Optional[Callable[[str], None]] = None,
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

        if on_change:
            # Vue emits: this.$emit('change', editor.getValue())
            # NiceGUI delivers e.args as [value]
            self.on("change", lambda e: on_change(
                e.args[0] if isinstance(e.args, (list, tuple)) and e.args else ""
            ))

    # ------------------------------------------------------------------
    # Programmatic update helpers (call .update() to push to client)
    # ------------------------------------------------------------------

    def update_value(self, value: str) -> "MonacoEditor":
        """Replace editor content from Python without re-rendering."""
        self._props["value"] = value
        self.update()
        return self

    def update_language(self, language: str) -> "MonacoEditor":
        self._props["language"] = _monaco_lang(language)
        self.update()
        return self

    def update_readonly(self, readonly: bool) -> "MonacoEditor":
        self._props["readonly"] = readonly
        self.update()
        return self
