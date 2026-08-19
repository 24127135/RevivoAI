"""
frontend/structured_terminal.py
-------------------------------
NiceGUI custom element wrapping frontend/structured_terminal.js.

Architecture:
- Logs are rendered client-side by q-virtual-scroll for zero DOM bloat.
- `push()` sends a single log delta via run_method — no NiceGUI reactive state sync.
- `initial_logs` are passed only once at mount time (from the ring buffer in state.execution_logs)
  so navigation between files restores recent history without re-broadcasting the full array.
"""

from __future__ import annotations

from typing import Any, Callable, Optional, Union
from nicegui.element import Element


class StructuredTerminal(Element, component="structured_terminal.js"):
    """
    A structured terminal with q-virtual-scroll for efficient rendering of
    thousands of log entries without DOM bloat.

    Parameters
    ----------
    logs : list[dict | str], optional
        Initial log entries (ring buffer snapshot). Passed once at mount.
    max_logs : int
        Client-side ring buffer cap (default 1000).
    on_cleared : callable, optional
        Callback when user clicks the clear button.
    """

    def __init__(
        self,
        logs: Optional[list[Union[dict[str, Any], str]]] = None,
        max_logs: int = 1000,
        on_cleared: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__()
        self._props["initial_logs"] = list(logs or [])
        self._props["max_logs"] = max_logs
        self._on_cleared = on_cleared

        if on_cleared:
            self.on("cleared", lambda _: self._on_cleared())

    def push(self, log_entry: Union[dict[str, Any], str]) -> None:
        """Push a single structured log delta to the Vue component.

        This calls run_method which sends a targeted JS call directly to the
        component instance — it does NOT trigger NiceGUI's reactive state sync
        or serialize any other part of the application state.
        """
        self.run_method("pushLog", log_entry)

    def clear(self) -> None:
        """Clear all terminal logs client-side."""
        self.run_method("clearLogs")
