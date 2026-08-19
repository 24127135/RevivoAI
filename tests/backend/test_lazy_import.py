import os
from pathlib import Path
from backend.import_utils import get_directory_children, get_root_nodes


def test_get_directory_children_returns_immediate_children(tmp_path: Path):
    # Setup test folder structure:
    # tmp_path/
    #   ├── src/
    #   │   └── main.py
    #   ├── tests/
    #   ├── .git/ (should be ignored)
    #   ├── README.md
    #   └── .hidden_file (should be ignored)
    
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "main.py").write_text("print('hello')", encoding="utf-8")

    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()

    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text("git config", encoding="utf-8")

    (tmp_path / "README.md").write_text("# Project", encoding="utf-8")
    (tmp_path / ".hidden_file").write_text("secret", encoding="utf-8")

    # Fetch root children
    children = get_directory_children(str(tmp_path))

    labels = [c["label"] for c in children]
    assert "src" in labels
    assert "tests" in labels
    assert "README.md" in labels
    assert ".git" not in labels
    assert ".hidden_file" not in labels

    # Directories must be first and have lazy=True and children=[]
    src_node = next(c for c in children if c["label"] == "src")
    assert src_node["is_dir"] is True
    assert src_node["lazy"] is True
    assert src_node["children"] == []

    # Files must have is_dir=False, lazy=False, and ext detected
    readme_node = next(c for c in children if c["label"] == "README.md")
    assert readme_node["is_dir"] is False
    assert readme_node["lazy"] is False
    assert readme_node["ext"] == "md"


def test_get_directory_children_lazy_fetch_subfolder(tmp_path: Path):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "main.py").write_text("print('hi')", encoding="utf-8")
    (src_dir / "utils.py").write_text("def util(): pass", encoding="utf-8")

    sub_children = get_directory_children(str(src_dir), base_root=str(tmp_path))
    labels = [c["label"] for c in sub_children]
    assert "main.py" in labels
    assert "utils.py" in labels
    for c in sub_children:
        assert c["is_dir"] is False
        assert c["ext"] == "py"
