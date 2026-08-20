import os
import uuid
from pathlib import Path
from typing import List, Any
from .models import ProjectFile, FileStatus

def _guess_lang(filename: str) -> str:
    """Simple extension checker to route to the correct Monaco Editor language."""
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    if ext in ["c", "h", "cpp", "hpp"]: return "c"
    if ext in ["r", "rmd"]: return "r"
    return "python" # Default fallback

async def import_from_uploads(upload_events: List[Any]) -> List[ProjectFile]:
    """Takes files uploaded via NiceGUI's ui.upload and converts them to our data model."""
    import inspect
    files = []
    for uf in upload_events:
        # Support both older NiceGUI (uf.content/uf.name) and newer NiceGUI (uf.name / uf.file)
        if hasattr(uf, 'content'):
            res = uf.content.read()
        else:
            res = uf.file.read()
            
        if inspect.isawaitable(res):
            raw_bytes = await res
        else:
            raw_bytes = res
            
        content = raw_bytes.decode("utf-8", errors="replace")
        
        fname = getattr(uf, 'name', getattr(getattr(uf, 'file', None), 'name', getattr(getattr(uf, 'file', None), 'filename', 'unknown_file')))
        
        files.append(ProjectFile(
            file_id=f"f_{uuid.uuid4().hex[:8]}",
            path=fname,
            legacy_source=content,
            ai_source="",  # AI hasn't processed it yet
            status=FileStatus.QUEUED, # Starts in the queue!
            language=_guess_lang(fname)
        ))
    return files

def import_local_project(root_path: str) -> List[ProjectFile]:
    """Recursively scans a local directory on your machine."""
    files = []
    if not os.path.isdir(root_path):
        raise ValueError(f"Directory not found: {root_path}")
    
    for dirpath, _, filenames in os.walk(root_path):
        # Skip hidden directories like .git or .venv
        if "/." in dirpath.replace("\\", "/") or ".venv" in dirpath: continue 
        
        for f in filenames:
            if f.startswith("."): continue # Skip hidden files like .DS_Store
            
            full_path = os.path.join(dirpath, f)
            # Create a clean relative path (e.g. "models/Order.py")
            rel_path = os.path.relpath(full_path, root_path).replace("\\", "/")
            
            try:
                with open(full_path, "r", encoding="utf-8") as fh:
                    content = fh.read()
            except UnicodeDecodeError:
                continue # Skip binary files (images, pyc, etc.)
            
            files.append(ProjectFile(
                file_id=f"f_{uuid.uuid4().hex[:8]}",
                path=rel_path,
                legacy_source=content,
                ai_source="",
                status=FileStatus.QUEUED,
                language=_guess_lang(f)
            ))
    return files


IGNORE_DIRS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".idea", ".vscode", "node_modules", ".agents"}

def get_directory_children(dir_path: str, base_root: str | None = None) -> list[dict]:
    """
    Returns only the DIRECT children (files and immediate subfolders) of a directory
    for lazy-loaded tree rendering. Subfolders are flagged with lazy=True and children=[].
    """
    if not os.path.isdir(dir_path):
        return []

    root_for_rel = Path(base_root).resolve() if base_root and os.path.isdir(base_root) else Path(dir_path).resolve()
    entries: list[dict] = []
    
    try:
        with os.scandir(dir_path) as it:
            for entry in it:
                name = entry.name
                if name.startswith(".") or name in IGNORE_DIRS:
                    continue

                full_path = Path(entry.path).resolve().as_posix()
                rel_path = os.path.relpath(entry.path, root_for_rel).replace("\\", "/")

                if entry.is_dir(follow_symlinks=False):
                    entries.append({
                        "id": full_path,
                        "label": name,
                        "path": full_path,
                        "rel_path": rel_path,
                        "is_dir": True,
                        "lazy": True,
                        "children": [],
                    })
                elif entry.is_file(follow_symlinks=False):
                    ext = name.split(".")[-1].lower() if "." in name else ""
                    entries.append({
                        "id": full_path,
                        "label": name,
                        "path": full_path,
                        "rel_path": rel_path,
                        "is_dir": False,
                        "lazy": False,
                        "ext": ext,
                    })
    except (PermissionError, OSError):
        return []

    # Sort: directories first (A-Z), then files (A-Z)
    entries.sort(key=lambda x: (not x["is_dir"], x["label"].lower()))
    return entries

def get_root_nodes(root_path: str) -> list[dict]:
    """Returns the top-level nodes for a given project/workspace root."""
    return get_directory_children(root_path, base_root=root_path)
