import pytest
from pathlib import Path
from frontend.file_tree import LazyFileTree


def test_lazy_file_tree_initialization():
    nodes = [
        {"id": "folder_1", "label": "controllers", "is_dir": True, "lazy": True, "children": []},
        {"id": "f_1", "label": "main.py", "is_dir": False, "lazy": False, "ext": "py"},
    ]
    tree = LazyFileTree(nodes=nodes, tick_strategy="leaf", initial_ticked=["f_1"])
    assert tree._props["nodes"] == nodes
    assert tree._props["tick_strategy"] == "leaf"
    assert tree.ticked == ["f_1"]


def test_lazy_file_tree_select_all_and_clear():
    nodes = [
        {"id": "folder_1", "label": "models", "is_dir": True, "children": [
            {"id": "f_1", "label": "user.py", "is_dir": False},
            {"id": "f_2", "label": "order.py", "is_dir": False},
        ]},
        {"id": "f_3", "label": "app.py", "is_dir": False},
    ]
    tree = LazyFileTree(nodes=nodes, tick_strategy="leaf")
    
    # Programmatic select_all
    tree.select_all()
    assert set(tree.ticked) == {"f_1", "f_2", "f_3"}

    # Programmatic clear_all
    tree.clear_all()
    assert tree.ticked == []


from nicegui import Client, ui


@pytest.mark.asyncio
async def test_lazy_file_tree_handle_lazy_load_event(tmp_path: Path):
    sub = tmp_path / "subfolder"
    sub.mkdir()
    (sub / "test.c").write_text("int main(){}", encoding="utf-8")

    @ui.page('/test_tree_page')
    def _dummy():
        pass

    with Client(_dummy):
        tree = LazyFileTree(root_path=str(tmp_path), tick_strategy="leaf")

    resolved_payloads = []
    tree.run_method = lambda method_name, key, children: resolved_payloads.append((method_name, key, children))

    class FakeEvent:
        args = {"key": "subfolder", "path": str(sub)}

    await tree._handle_lazy_load(FakeEvent())

    assert len(resolved_payloads) == 1
    method_name, key, children = resolved_payloads[0]
    assert method_name == "resolveLazyLoad"
    assert key == "subfolder"
    assert len(children) == 1
    assert children[0]["label"] == "test.c"
    assert children[0]["ext"] == "c"


def test_lazy_file_tree_expanded_state_and_collapse():
    nodes = [
        {"id": "folder_1", "label": "models", "is_dir": True, "children": [
            {"id": "f_1", "label": "user.py", "is_dir": False},
        ]},
        {"id": "folder_2", "label": "views", "is_dir": True, "children": [
            {"id": "f_2", "label": "index.py", "is_dir": False},
        ]},
    ]
    expanded_changes = []
    tree = LazyFileTree(
        nodes=nodes,
        initial_expanded=["folder_1"],
        on_expanded_change=lambda exp: expanded_changes.append(list(exp))
    )
    assert tree.expanded == ["folder_1"]

    # Test collapse_all
    tree.collapse_all()
    assert tree.expanded == []

    # Test expand event handling
    tree._on_expanded(type("Event", (), {"args": ["folder_1", "folder_2"]})(), lambda exp: expanded_changes.append(list(exp)))
    assert tree.expanded == ["folder_1", "folder_2"]
    assert expanded_changes[-1] == ["folder_1", "folder_2"]
