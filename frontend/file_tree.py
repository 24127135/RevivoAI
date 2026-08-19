"""
frontend/file_tree.py
---------------------
NiceGUI Element wrapping a lazy-loaded, virtualized Quasar QTree via
frontend/file_tree.js.

Loads only the root directory on initial render and queries direct children
asynchronously when folders are expanded.
"""

from __future__ import annotations

import inspect
from typing import Any, Callable, Coroutine, Optional, Union
from nicegui.element import Element
from backend.import_utils import get_directory_children, get_root_nodes


class LazyFileTree(Element, component="file_tree.js"):
    """
    A lazy-loaded, high-performance file tree component built on Quasar's QTree.

    Parameters
    ----------
    nodes : list[dict], optional
        Initial top-level tree nodes. If omitted and ``root_path`` is given,
        the root directory will be automatically scanned for top-level entries.
    root_path : str, optional
        Filesystem root path for directory-based tree navigation.
    tick_strategy : str
        Quasar tick strategy: ``'none'``, ``'strict'``, or ``'leaf'``.
    initial_ticked : list[str], optional
        Initial ticked node IDs.
    initial_expanded : list[str], optional
        Initial expanded node IDs.
    height : str
        Height of the scrollable tree container (default ``'300px'``).
    lazy_loader : callable, optional
        Custom async or sync callable ``(dir_path, root_path) -> list[dict]``.
        Defaults to ``backend.import_utils.get_directory_children``.
    on_ticked_change : callable, optional
        Callback invoked when checked nodes change. Receives ``list[str]``.
    on_selected_change : callable, optional
        Callback invoked when active node changes. Receives ``str | None``.
    """

    def __init__(
        self,
        nodes: Optional[list[dict[str, Any]]] = None,
        root_path: Optional[str] = None,
        tick_strategy: str = "none",
        initial_ticked: Optional[list[str]] = None,
        initial_selected: Optional[str] = None,
        initial_expanded: Optional[list[str]] = None,
        height: str = "300px",
        lazy_loader: Optional[Callable[[str, Optional[str]], Union[list[dict], Coroutine[Any, Any, list[dict]]]]] = None,
        on_ticked_change: Optional[Callable[[list[str]], None]] = None,
        on_selected_change: Optional[Callable[[Optional[str]], None]] = None,
        on_expanded_change: Optional[Callable[[list[str]], None]] = None,
    ) -> None:
        super().__init__()

        self._root_path = root_path
        self._lazy_loader = lazy_loader
        self._ticked_keys: list[str] = list(initial_ticked or [])
        self._selected_key: Optional[str] = initial_selected
        self._expanded_keys: list[str] = list(initial_expanded or [])

        # Auto-populate root nodes if root_path is provided and nodes is None
        if nodes is None and root_path:
            initial_nodes = get_root_nodes(root_path)
        else:
            initial_nodes = list(nodes or [])

        self._props["nodes"] = initial_nodes
        self._props["tick_strategy"] = tick_strategy
        self._props["initial_ticked"] = self._ticked_keys
        self._props["initial_selected"] = initial_selected
        self._props["initial_expanded"] = self._expanded_keys
        self._props["height"] = height

        if on_ticked_change:
            self.on("ticked_change", lambda e: self._on_ticked(e, on_ticked_change))
        else:
            self.on("ticked_change", self._on_ticked_internal)

        if on_selected_change:
            self.on("selected_change", lambda e: self._on_selected(e, on_selected_change))
        else:
            self.on("selected_change", self._on_selected_internal)

        if on_expanded_change:
            self.on("expanded_change", lambda e: self._on_expanded(e, on_expanded_change))
        else:
            self.on("expanded_change", self._on_expanded_internal)

        self.on("lazy_load", self._handle_lazy_load)

    def _on_ticked(self, e: Any, callback: Callable[[list[str]], None]) -> None:
        args = e.args if isinstance(e.args, list) else []
        self._ticked_keys = args
        callback(args)

    def _on_ticked_internal(self, e: Any) -> None:
        args = e.args if isinstance(e.args, list) else []
        self._ticked_keys = args

    def _on_selected(self, e: Any, callback: Callable[[Optional[str]], None]) -> None:
        self._selected_key = e.args if isinstance(e.args, str) else None
        callback(self._selected_key)

    def _on_selected_internal(self, e: Any) -> None:
        self._selected_key = e.args if isinstance(e.args, str) else None

    def _on_expanded(self, e: Any, callback: Callable[[list[str]], None]) -> None:
        args = e.args if isinstance(e.args, list) else []
        self._expanded_keys = args
        callback(args)

    def _on_expanded_internal(self, e: Any) -> None:
        args = e.args if isinstance(e.args, list) else []
        self._expanded_keys = args

    async def _handle_lazy_load(self, e: Any) -> None:
        req = e.args if isinstance(e.args, dict) else {}
        key = req.get("key")
        path = req.get("path") or key

        try:
            if self._lazy_loader:
                res = self._lazy_loader(path, self._root_path)
                if inspect.isawaitable(res):
                    children = await res
                else:
                    children = res
            else:
                children = get_directory_children(path, base_root=self._root_path)

            self.resolve_lazy_load(key, children or [])
        except Exception:
            self.fail_lazy_load(key)

    def resolve_lazy_load(self, key: str, children: list[dict]) -> None:
        """Deliver loaded children back to Quasar's QTree done() callback."""
        self.run_method("resolveLazyLoad", key, children)

    def fail_lazy_load(self, key: str) -> None:
        """Notify Quasar QTree that lazy loading failed."""
        self.run_method("failLazyLoad", key)

    def set_ticked(self, keys: list[str]) -> "LazyFileTree":
        """Programmatically tick/check nodes in the tree."""
        self._ticked_keys = list(keys)
        self.run_method("setTicked", self._ticked_keys)
        return self

    def select_all(self, keys: Optional[list[str]] = None) -> "LazyFileTree":
        """Select all provided keys, or collect all leaf keys currently in nodes."""
        if keys is not None:
            return self.set_ticked(keys)

        all_keys: list[str] = []
        def _collect(nodes_list: list[dict]):
            for n in nodes_list:
                if not n.get("is_dir") and not n.get("lazy"):
                    all_keys.append(n["id"])
                if n.get("children"):
                    _collect(n["children"])

        _collect(self._props.get("nodes", []))
        return self.set_ticked(all_keys)

    def clear_all(self) -> "LazyFileTree":
        """Clear all ticked/checked nodes."""
        return self.set_ticked([])

    def update_nodes(self, nodes: list[dict]) -> "LazyFileTree":
        """Update top-level nodes."""
        self._props["nodes"] = nodes
        self.update()
        return self

    def collapse_all(self) -> "LazyFileTree":
        """Collapse all expanded folders."""
        self._expanded_keys = []
        self.run_method("collapseAll")
        return self

    def expand_all(self) -> "LazyFileTree":
        """Expand all folders."""
        self.run_method("expandAll")
        return self

    @property
    def ticked(self) -> list[str]:
        """Return currently ticked node keys."""
        return self._ticked_keys

    @property
    def expanded(self) -> list[str]:
        """Return currently expanded folder keys."""
        return self._expanded_keys
