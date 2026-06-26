import os
import uuid
from typing import List, Any
from .models import ProjectFile, FileStatus

def _guess_lang(filename: str) -> str:
    """Simple extension checker to route to the correct Pygments lexer."""
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    if ext in ["c", "h", "cpp", "hpp"]: return "c"
    if ext in ["r", "rmd"]: return "r"
    return "python" # Default fallback

def import_from_streamlit_uploads(uploaded_files: List[Any]) -> List[ProjectFile]:
    """Takes files uploaded via Streamlit's UI and converts them to our data model."""
    files = []
    for uf in uploaded_files:
        # Decode bytes to string, ignoring binary garble
        content = uf.read().decode("utf-8", errors="replace")
        files.append(ProjectFile(
            file_id=f"f_{uuid.uuid4().hex[:8]}",
            path=uf.name,  # st.file_uploader just gives the filename, which is fine here
            legacy_source=content,
            ai_source="",  # AI hasn't processed it yet
            status=FileStatus.QUEUED, # Starts in the queue!
            language=_guess_lang(uf.name)
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