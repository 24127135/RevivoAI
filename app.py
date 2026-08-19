import asyncio
import json
import html
import logging
import os
import time
import uuid
from dataclasses import asdict, is_dataclass
from pathlib import Path
import tkinter as tk
from tkinter import filedialog

import httpx
import websockets
from nicegui import ui, app, events, background_tasks

logger = logging.getLogger(__name__)

# Import from backend
from backend.mcp_client import MCPClient
from backend.models import FileStatus, STATUS_META, WARNING_STATUSES, ProjectFile
from backend.logic import (
    parse_traceback, compute_anchors, group_frames_for_disclosure,
)
from backend.import_utils import import_from_uploads, import_local_project
from backend.session_handler import SessionHandler

# Import from frontend
from frontend.styles import get_css
from frontend.components import TRANSLATING_PHASES, SANDBOX_PHASES, LazyFileTree, StructuredTerminal
from frontend.monaco_editor import MonacoEditor

# ============================================================================
# STRUCTURED LOG DATA WRAPPER
# ============================================================================
class StructuredLog(dict):
    """Structured log dictionary that also supports substring searching for string compatibility in tests."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __contains__(self, item):
        if super().__contains__(item):
            return True
        if isinstance(item, str):
            msg = str(self.get("message", ""))
            raw = str(self.get("details", {}).get("raw_output", ""))
            formatted = f"[{self.get('timestamp')}] [{self.get('source')}] {msg} {raw}"
            return item in formatted or item in msg or item in raw
        return False

    def __str__(self):
        msg = str(self.get("message", ""))
        raw = str(self.get("details", {}).get("raw_output", ""))
        return f"[{self.get('timestamp', '')}] [{self.get('source', '')}] {msg} {raw}".strip()


# ============================================================================
# STATE INIT
# ============================================================================
SIDEBAR_WIDTH_PX = 350

class AppState:
    def __init__(self):
        self.files: dict[str, ProjectFile] = {}
        self.drawer = None
        self.active_buffer: str | None = None
        self.expanded_folders: set[str] = {"controllers", "models", "views", "analytics", "FS"}
        self.diff_state: dict[str, str] = {}        
        self.edit_buffer: dict[str, str] = {}        
        self.trace_expanded: dict[str, bool] = {}     
        self.show_full_trace: dict[str, bool] = {}    
        self.rejecting: dict[str, bool] = {}          
        self.import_mode: str | None = None
        self.project_root: str | None = None
        self.session_id: str | None = None
        self.mcp_client: MCPClient | None = None
        self.session_handler: SessionHandler | None = None
        
        # Sidebar filters
        self.search_query: str = ""
        self.status_filter: str = "All"
        self.module_filter: str = "All"
        
        # Execution states & logs
        self.is_thinking: bool = False
        self.thinking_phase: int = 0  # <--- ADD THIS FIX
        self.agent_state: dict[str, str] = {}         
        # Ring buffer for initial mount only — NOT synced via NiceGUI reactive state.
        # Logs are pushed directly to Vue component via run_method (delta push).
        # Max 1000 entries per file to cap memory.
        self.execution_logs: dict[str, list[StructuredLog]] = {}
        self._MAX_LOG_BUFFER = 1000
        self.current_terminal = None
        self.fullscreen_mode: str | None = None  # None, 'diff', 'source', 'edit_legacy', 'edit_ai'

        # Staging screen — files waiting for user confirmation before entering workspace
        # Each entry: {name, size_str, pct, status, project_file}
        #   status: 'uploading' | 'done' | 'failed'
        self.staging_files: list[dict] = []
        self.temp_project_root: str | None = None

        # --- User Configurable Settings ---
        self.api_key: str = ""
        self.max_iterations: int = 3
        self.model_temperature: float = 0.2 # Example of another useful variable
        self.is_batch_running: bool = False
        self.is_batch_paused: bool = False
        self.cancel_batch_flag: bool = False
        self.batch_queue: list[str] = []
        self.batch_current_idx: int = 0
        self.user_feedback: dict[str, str] = {}

state = AppState()

async def load_demo_project():
    """Loads real test scripts from test_scripts directory directly into the workspace."""
    candidate_paths = [
        Path.cwd() / "test_scripts",
        Path(__file__).resolve().parent / "test_scripts",
        Path.cwd() / "test_scritps",
        Path(__file__).resolve().parent / "test_scritps",
    ]
    project_root = next((p for p in candidate_paths if p.exists() and p.is_dir()), None)
    
    if not project_root:
        show_alert("Test scripts folder not found.", alert_type='warning')
        return

    try:
        imported_files = import_local_project(str(project_root))
    except Exception as e:
        show_alert(f"Failed to scan test scripts: {e}", alert_type='negative')
        return

    if not imported_files:
        show_alert("No test script files found in test_scripts directory.", alert_type='warning')
        return

    state.staging_files = []
    state.temp_project_root = str(project_root.resolve())

    for f in imported_files:
        size_bytes = len(f.legacy_source.encode('utf-8'))
        size_str = f'{size_bytes / 1024:.1f} KB' if size_bytes >= 1024 else f'{size_bytes} B'
        state.staging_files.append({
            'name': f.path,
            'size_str': size_str,
            'pct': 100,
            'status': 'done',
            'project_file': f,
        })

    await commit_staging_to_workspace()

async def commit_staging_to_workspace():
    """User clicked Proceed — move staging files into the workspace."""
    ready = [e for e in state.staging_files if e['status'] == 'done']
    if not ready:
        show_alert("No files ready to proceed. Upload or retry failed files first.", alert_type='warning')
        return
    for entry in ready:
        pf = entry['project_file']
        state.files[pf.file_id] = pf
    state.active_buffer = ready[0]['project_file'].file_id
    if state.temp_project_root:
        state.project_root = state.temp_project_root
        state.temp_project_root = None
        state.mcp_client = MCPClient(server_uri="local://revivoai", allowed_root_path=state.project_root)
        async def connect_mcp():
            await asyncio.sleep(0.1)
            state.mcp_client.connect()
        asyncio.create_task(connect_mcp())
    
    state.staging_files = []
    state.import_mode = None
    state.is_batch_running = False
    state.cancel_batch_flag = False
    state.is_thinking = False
    try:
        state.session_handler = SessionHandler()
        session_id = await state.session_handler.initialize_session(user_id=str(uuid.uuid4()))
        state.session_id = session_id
        if session_id:
            background_tasks.create(websocket_listener(session_id))
    except Exception as e:
        logger.warning(f"Could not initialize remote session: {e}")
    refresh_all()
    try:
        render_sidebar.refresh()
    except Exception:
        pass

async def pick_directory_async():
    def pick():
        root = tk.Tk()
        root.attributes("-topmost", True)
        root.withdraw()
        folder = filedialog.askdirectory()
        root.destroy()
        return folder
    return await asyncio.to_thread(pick)

async def handle_native_import_project():
    folder = await pick_directory_async()
    if folder:
        try:
            imported_files = import_local_project(folder)
            if imported_files:
                skipped = 0
                for f in imported_files:
                    if any(entry.get('name') == f.path for entry in state.staging_files):
                        skipped += 1
                        continue

                    size_bytes = len(f.legacy_source.encode('utf-8'))
                    size_str = f'{size_bytes / 1024:.1f} KB' if size_bytes >= 1024 else f'{size_bytes} B'
                    state.staging_files.append({
                        'name': f.path,
                        'size_str': size_str,
                        'pct': 100,
                        'status': 'done',
                        'project_file': f,
                    })
                
                if skipped > 0:
                    show_alert(f"Skipped {skipped} duplicate file(s).", alert_type='warning')
                
                if state.staging_files:
                    state.temp_project_root = folder
                    state.import_mode = "STAGING"
                    refresh_all()
            else:
                show_alert("No readable source files found in that directory.", alert_type='warning')
        except Exception as e:
            show_alert(f"Failed to import project: {e}", alert_type='negative')
    try:
        render_sidebar.refresh()
    except Exception:
        pass

async def open_file_picker():
    def pick():
        import tkinter as _tk
        from tkinter import filedialog as _fd
        root = _tk.Tk()
        root.attributes('-topmost', True)
        root.withdraw()
        paths = _fd.askopenfilenames(
            title='Select source files',
            filetypes=[
                ('Source files', '*.py *.c *.cpp *.h *.hpp *.r *.rmd'),
                ('All files', '*.*'),
            ]
        )
        root.destroy()
        return list(paths)
    paths = await asyncio.to_thread(pick)
    if paths:
        from backend.import_utils import _guess_lang
        skipped = 0
        for p in paths:
            fname = Path(p).name
            if any(entry.get('name') == fname for entry in state.staging_files):
                skipped += 1
                continue

            try:
                with open(p, 'r', encoding='utf-8', errors='replace') as fh:
                    content = fh.read()
                pf = ProjectFile(
                    file_id=f'f_{uuid.uuid4().hex[:8]}',
                    path=p,
                    legacy_source=content,
                    ai_source='',
                    status=FileStatus.QUEUED,
                    language=_guess_lang(fname),
                )
                size_bytes = len(content.encode('utf-8'))
                size_str = f'{size_bytes / 1024:.1f} KB' if size_bytes >= 1024 else f'{size_bytes} B'
                state.staging_files.append({
                    'name': fname, 'size_str': size_str,
                    'pct': 100, 'status': 'done', 'project_file': pf,
                })
            except Exception:
                pass
        
        if skipped > 0:
            show_alert(f"Skipped {skipped} duplicate file(s).", alert_type='warning')

        if state.staging_files:
            state.import_mode = "STAGING"
            refresh_all()

# ============================================================================
# STATE HELPERS
# ============================================================================
def get_file(fid: str) -> ProjectFile: return state.files[fid]

def show_alert(message: str, alert_type: str = 'info'):
    bg = 'bg-blue-100'
    text = 'text-blue-900'
    title = 'Info'
    icon = '<svg viewBox="0 0 16 16" fill="currentColor" class="mt-0.5 size-4"><path d="M8 15A7 7 0 1 0 8 1a7 7 0 0 0 0 14ZM8 4a1 1 0 1 1 0-2 1 1 0 0 1 0 2Zm0 7a1 1 0 0 1-1-1V7a1 1 0 0 1 2 0v3a1 1 0 0 1-1 1Z"/></svg>'
    
    if alert_type == 'positive':
        bg, text, title = 'bg-green-100', 'text-green-900', 'Success'
        icon = '<svg viewBox="0 0 16 16" fill="currentColor" class="mt-0.5 size-4"><path fill-rule="evenodd" d="M8 15A7 7 0 1 0 8 1a7 7 0 0 0 0 14Zm3.844-8.791a.75.75 0 0 0-1.188-.918l-3.7 4.79-1.649-1.833a.75.75 0 1 0-1.114 1.004l2.25 2.5a.75.75 0 0 0 1.15-.043l4.25-5.5Z" clip-rule="evenodd"/></svg>'
    elif alert_type in ('negative', 'warning'):
        bg = 'bg-red-100' if alert_type == 'negative' else 'bg-yellow-100'
        text = 'text-red-900' if alert_type == 'negative' else 'text-yellow-900'
        title = 'Error' if alert_type == 'negative' else 'Warning'
        icon = '<svg viewBox="0 0 16 16" fill="currentColor" class="mt-0.5 size-4"><path fill-rule="evenodd" d="M6.701 2.25c.577-1 2.02-1 2.598 0l5.196 9a1.5 1.5 0 0 1-1.299 2.25H2.804a1.5 1.5 0 0 1-1.3-2.25l5.197-9ZM8 4a.75.75 0 0 1 .75.75v3a.75.75 0 1 1-1.5 0v-3A.75.75 0 0 1 8 4Zm0 8a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z" clip-rule="evenodd"/></svg>'
        
    html_content = f"""
    <div role="alert" class="border-2 {bg} p-4 {text} shadow-[4px_4px_0_0] shadow-black w-[350px]">
      <div class="flex items-start gap-3">
        {icon}
        <strong class="block flex-1 leading-tight font-semibold">
          <span class="sr-only">{title}: </span>
          {html.escape(message)}
        </strong>
      </div>
    </div>
    """
    try:
        ui.notify(html_content, html=True, position='top-right', close_button=False)
    except Exception:
        # Safe fallback when invoked from background tasks without slot context
        pass


def get_staging_summary_counts() -> dict[str, int]:
    counts = {"total": 0, "done": 0, "failed": 0, "uploading": 0}
    for entry in state.staging_files:
        status = str(entry.get("status", "done")).lower()
        counts["total"] += 1
        if status == "done":
            counts["done"] += 1
        elif status == "failed":
            counts["failed"] += 1
        elif status == "uploading":
            counts["uploading"] += 1
    return counts


def _canonical_fs_path(path: str | None, root_path: str | None = None) -> str:
    if not path:
        return ""
    candidate = Path(str(path).replace("\\", "/"))
    if candidate.is_absolute():
        return candidate.resolve().as_posix()
    if root_path:
        return (Path(root_path) / candidate).resolve().as_posix()
    return candidate.as_posix()


def _find_file_id_by_tree_key(tree_key: str | None) -> str | None:
    if not tree_key:
        return None
    if tree_key in state.files:
        return tree_key

    clean_tree_key = str(tree_key).replace("\\", "/").rstrip("/")
    canonical_key = _canonical_fs_path(tree_key, state.project_root)

    for file_id, project_file in state.files.items():
        if file_id == tree_key:
            return file_id
        pf_path = str(getattr(project_file, "path", "")).replace("\\", "/").rstrip("/")
        if not pf_path:
            continue
        if pf_path == clean_tree_key or clean_tree_key.endswith("/" + pf_path) or pf_path.endswith("/" + clean_tree_key):
            return file_id
        file_key = _canonical_fs_path(pf_path, state.project_root)
        if file_key and (file_key == canonical_key or file_key == clean_tree_key):
            return file_id
    return None


def merge_project_files_into_workspace(imported_files: list[ProjectFile], source_root: str | None = None) -> dict[str, int]:
    existing_paths = {f.path for f in state.files.values() if getattr(f, 'path', None)}
    added_files: list[ProjectFile] = []
    skipped = 0

    for f in imported_files:
        if not getattr(f, 'path', None) or f.path in existing_paths:
            skipped += 1
            continue

        state.files[f.file_id] = f
        existing_paths.add(f.path)
        added_files.append(f)

    if added_files:
        if not state.project_root and source_root:
            state.project_root = source_root
        if not state.active_buffer and state.files:
            state.active_buffer = added_files[0].file_id
        refresh_all()
        try:
            render_sidebar.refresh()
        except Exception:
            pass

    return {"added": len(added_files), "skipped": skipped}


async def open_workspace_file_picker():
    def pick():
        import tkinter as _tk
        from tkinter import filedialog as _fd
        root = _tk.Tk()
        root.attributes('-topmost', True)
        root.withdraw()
        paths = _fd.askopenfilenames(
            title='Select files to add to the workspace',
            filetypes=[
                ('Source files', '*.py *.c *.cpp *.h *.hpp *.r *.rmd'),
                ('All files', '*.*'),
            ],
        )
        root.destroy()
        return list(paths)

    paths = await asyncio.to_thread(pick)
    if not paths:
        return

    from backend.import_utils import _guess_lang
    imported_files: list[ProjectFile] = []
    skipped = 0

    for p in paths:
        fname = Path(p).name
        if any(existing.path == p for existing in state.files.values()):
            skipped += 1
            continue

        try:
            with open(p, 'r', encoding='utf-8', errors='replace') as fh:
                content = fh.read()
            pf = ProjectFile(
                file_id=f'f_{uuid.uuid4().hex[:8]}',
                path=p,
                legacy_source=content,
                ai_source='',
                status=FileStatus.QUEUED,
                language=_guess_lang(fname),
            )
            imported_files.append(pf)
        except Exception:
            continue

    result = merge_project_files_into_workspace(imported_files)
    if skipped:
        show_alert(f"Skipped {skipped} duplicate file(s).", alert_type='warning')
    if not imported_files and not skipped:
        show_alert('No readable files were selected.', alert_type='warning')
    elif result['added'] and skipped:
        show_alert(f"Added {result['added']} file(s) to the workspace. Skipped {skipped} duplicate file(s).", alert_type='positive')
    elif result['added']:
        show_alert(f"Added {result['added']} file(s) to the workspace.", alert_type='positive')


async def add_project_to_workspace_from_dialog():
    def pick():
        root = tk.Tk()
        root.attributes('-topmost', True)
        root.withdraw()
        folder = filedialog.askdirectory(title='Select project folder to add to the workspace')
        root.destroy()
        return folder

    folder = await asyncio.to_thread(pick)
    if not folder:
        return

    try:
        imported_files = import_local_project(folder)
    except Exception as exc:
        show_alert(f'Failed to import project: {exc}', alert_type='negative')
        return

    if not imported_files:
        show_alert('No readable source files found in that directory.', alert_type='warning')
        return

    result = merge_project_files_into_workspace(imported_files, source_root=folder)
    if result['added']:
        if result['skipped']:
            show_alert(f"Added {result['added']} file(s) from the selected project. Skipped {result['skipped']} duplicate file(s).", alert_type='positive')
        else:
            show_alert(f"Added {result['added']} file(s) from the selected project.", alert_type='positive')
    elif result['skipped']:
        show_alert('All selected files were already present in the workspace.', alert_type='warning')


def _make_structured_log(
    message_or_entry: Union[str, dict[str, Any]],
    source: str = "SYSTEM",
    status: str = "info",
    details: Optional[dict] = None,
) -> StructuredLog:
    """Normalize a raw string or dict into a StructuredLog."""
    if isinstance(message_or_entry, dict):
        raw_msg = str(message_or_entry.get("message", ""))
        entry_source = str(message_or_entry.get("source", source)).upper()
        entry_status = str(message_or_entry.get("status", status)).lower()
        entry_ts = str(message_or_entry.get("timestamp", time.strftime('%H:%M:%S')))
        entry_details = dict(message_or_entry.get("details", details or {}))
        return StructuredLog(
            timestamp=entry_ts,
            source=entry_source,
            status=entry_status,
            message=raw_msg,
            details=entry_details,
        )

    raw_str = str(message_or_entry)
    timestamp = time.strftime('%H:%M:%S')
    parsed_source = source.upper()
    parsed_status = status.lower()

    # Auto-detect source prefix if present in legacy string format
    if raw_str.startswith("[LLM"):
        parsed_source = "LLM"
    elif raw_str.startswith("[Sandbox") or raw_str.startswith("[Docker") or "[AI Sandbox Crash]" in raw_str:
        parsed_source = "DOCKER"
    elif raw_str.startswith("[Pytest") or "Pytest" in raw_str:
        parsed_source = "PYTEST"
    elif raw_str.startswith("[Telemetry") or "Supabase" in raw_str:
        parsed_source = "TELEMETRY"
    elif raw_str.startswith("[User Action") or raw_str.startswith("[MCP") or raw_str.startswith("[System"):
        parsed_source = "SYSTEM"

    if "Error" in raw_str or "failed" in raw_str or "🔴" in raw_str or "Crash" in raw_str or "Exception" in raw_str:
        parsed_status = "error"
    elif "warning" in raw_str.lower() or "Refused" in raw_str:
        parsed_status = "warning"
    elif "successful" in raw_str or "passed" in raw_str or "🟢" in raw_str:
        parsed_status = "success"
    elif "Executing" in raw_str or "Analyzing" in raw_str or "Provisioning" in raw_str or "Starting" in raw_str:
        parsed_status = "running"

    return StructuredLog(
        timestamp=timestamp,
        source=parsed_source,
        status=parsed_status,
        message=raw_str,
        details=details or {},
    )


def push_log(
    file_id: str,
    message_or_entry: Union[str, dict[str, Any]],
    source: str = "SYSTEM",
    status: str = "info",
    details: Optional[dict] = None
):
    """Push a structured log delta directly to the Vue StructuredTerminal component.
    
    Architecture note: Logs are NOT stored in NiceGUI's reactive state to avoid
    serializing the full log array on every state update. Instead:
    - The log is pushed directly to the Vue component via run_method() (delta only).
    - A lightweight ring buffer in state.execution_logs (max 1000) is maintained
      only for re-mounting the terminal when the user navigates between files.
    """
    log_entry = _make_structured_log(message_or_entry, source, status, details)

    # --- Ring buffer (for initial mount when terminal is re-rendered) ---
    buf = state.execution_logs.setdefault(file_id, [])
    buf.append(log_entry)
    if len(buf) > state._MAX_LOG_BUFFER:
        buf.pop(0)  # Drop oldest to keep memory bounded

    # --- Delta push directly to Vue component (no state serialization overhead) ---
    if state.active_buffer == file_id and state.current_terminal:
        try:
            state.current_terminal.push(log_entry)
        except Exception:
            pass

def folder_tree() -> dict[str, list[ProjectFile]]:
    tree: dict[str, list[ProjectFile]] = {}
    for f in state.files.values(): 
        folder_name = str(f.folder) if f.folder else "Root"
        tree.setdefault(folder_name, []).append(f)
        
    for folder in tree: 
        tree[folder].sort(key=lambda f: str(f.filename) if f.filename else "")
        
    return dict(sorted(tree.items(), key=lambda item: item[0]))

def folder_has_warning(folder_files: list[ProjectFile]) -> int: 
    return sum(1 for f in folder_files if f.status in WARNING_STATUSES)

def build_hierarchical_file_tree(
    files: dict[str, ProjectFile],
    search_query: str = "",
    status_filter: str = "All",
    module_filter: str = "All"
) -> tuple[list[dict], list[str]]:
    """
    Builds a full N-level hierarchical tree structure from workspace files.
    Returns (tree_nodes, default_expanded_folder_ids).
    """
    filtered: list[ProjectFile] = []
    for f in files.values():
        fname = str(f.filename).lower() if f.filename else ""
        if search_query and search_query.lower() not in fname:
            continue
        status_val = getattr(f.status, 'value', str(f.status))
        if status_filter != "All" and status_val != status_filter:
            continue
        folder_name = str(f.folder) if f.folder else "Root"
        if module_filter != "All" and folder_name != module_filter:
            continue
        filtered.append(f)

    root_path = Path(state.project_root).resolve() if state.project_root else None
    root_label = root_path.name if root_path else "Root"

    def _relative_path(path: str | None) -> str:
        if not path:
            return ""
        candidate = Path(str(path).replace("\\", "/"))
        if root_path:
            try:
                if candidate.is_absolute():
                    return candidate.resolve().relative_to(root_path).as_posix()
            except ValueError:
                pass
        return candidate.as_posix().strip("/")

    def _absolute_key(path: str | None) -> str:
        if not path:
            return ""
        candidate = Path(str(path).replace("\\", "/"))
        if root_path and not candidate.is_absolute():
            candidate = root_path / candidate
        return candidate.resolve().as_posix()

    root_dict: dict = {}
    for f in filtered:
        clean_path = _relative_path(f.path).strip("/")
        parts = clean_path.split("/")
        curr = root_dict
        for part in parts[:-1]:
            if part not in curr:
                curr[part] = {"__type": "folder", "__children": {}}
            curr = curr[part]["__children"]
        
        file_part = parts[-1] if parts else f.filename
        curr[file_part] = {"__type": "file", "__file": f}

    expanded_folders: list[str] = []

    def _collect_files(node_dict: dict) -> list[ProjectFile]:
        collected = []
        for v in node_dict.values():
            if v.get("__type") == "file":
                collected.append(v["__file"])
            elif v.get("__type") == "folder":
                collected.extend(_collect_files(v["__children"]))
        return collected

    def convert(node_dict: dict, current_path: str = "") -> list[dict]:
        res = []
        folders = [k for k, v in node_dict.items() if v.get("__type") == "folder"]
        files_in_dir = [k for k, v in node_dict.items() if v.get("__type") == "file"]

        folders.sort(key=str.lower)
        files_in_dir.sort(key=str.lower)

        for folder_name in folders:
            sub_path = f"{current_path}/{folder_name}".lstrip("/")
            sub_dict = node_dict[folder_name]["__children"]
            sub_children = convert(sub_dict, sub_path)
            
            sub_files = _collect_files(sub_dict)
            warn_count = sum(1 for sf in sub_files if sf.status in WARNING_STATUSES)
            folder_key = _absolute_key(sub_path)
            expanded_folders.append(folder_key)

            res.append({
                "id": folder_key,
                "label": folder_name,
                "path": folder_key,
                "is_dir": True,
                "badge": f"⚠️ {warn_count}" if warn_count else None,
                "children": sub_children,
            })

        for file_name in files_in_dir:
            pf: ProjectFile = node_dict[file_name]["__file"]
            has_warn = pf.status in WARNING_STATUSES
            
            status_badge = None
            if pf.status in (FileStatus.PASSED, FileStatus.APPROVED):
                status_badge = "✓"
            elif pf.status in (FileStatus.FAILED, FileStatus.REJECTED):
                status_badge = "!"
            elif pf.status in (FileStatus.TRANSLATING, FileStatus.SANDBOX_TESTING):
                status_badge = "⚡"
            elif pf.status == FileStatus.EDITED_PENDING:
                status_badge = "✎"

            res.append({
                "id": _absolute_key(pf.path),
                "file_id": pf.file_id,
                "label": pf.filename,
                "path": _absolute_key(pf.path),
                "is_dir": False,
                "has_warning": has_warn,
                "status": getattr(pf.status, 'value', str(pf.status)),
                "status_badge": status_badge,
                "ext": str(pf.filename).split(".")[-1].lower() if "." in str(pf.filename) else "",
            })
        return res

    tree_nodes = [{
        "id": _absolute_key(state.project_root),
        "label": root_label,
        "path": _absolute_key(state.project_root),
        "is_dir": True,
        "children": convert(root_dict),
    }]
    expanded_folders.insert(0, _absolute_key(state.project_root))
    return tree_nodes, expanded_folders

def set_active_buffer(file_id: str): 
    state.active_buffer = file_id
    state.fullscreen_mode = None
    try:
        render_main.refresh()
    except Exception:
        pass

def transition_to_sandbox(file_id: str):
    f = get_file(file_id)
    f.status = FileStatus.SANDBOX_TESTING
    
    if f.target_ai_source:
        f.ai_source = f.target_ai_source
    elif not f.ai_source:
        f.ai_source = f"# [AI TRANSLATION COMPLETE]\n" + f.legacy_source.replace("class ", "class Modern")

def resolve_sandbox_now(file_id: str):
    f = get_file(file_id)
    edited = file_id in state.edit_buffer and state.edit_buffer[file_id]
    
    if edited:
        f.status = FileStatus.PASSED
        f.raw_traceback = ""
        f.primary_error_line = None
        f.related_error_lines = []
    else:
        if f.target_status:
            f.status = f.target_status
            f.raw_traceback = f.target_traceback
            if f.raw_traceback:
                frames = parse_traceback(f.raw_traceback, f.language, f.filename)
                primary, related = compute_anchors(frames)
                f.primary_error_line = primary
                f.related_error_lines = related
                
                if getattr(f, 'iteration', 0) < 1 and f.status == FileStatus.FAILED:
                    f.iteration += 1
                    # Removed show_alert to prevent "slot stack empty" background task crashes
                    push_log(file_id, f"Auto-retry triggered based on traceback at line {f.primary_error_line}.")
                    async def retry_task():
                        await asyncio.sleep(1.0)
                        await simulate_translation(file_id)
                    background_tasks.create(retry_task())
                    return
        else:
            f.status = FileStatus.FAILED if f.raw_traceback else FileStatus.PASSED

def approve_file(file_id: str):
    f = get_file(file_id)
    if f.status != FileStatus.PASSED:
        return

    # Use the file's actual parent directory as the allowed root if project_root is missing
    # This prevents the MCP Client from throwing a Path Traversal security error.
    root = state.project_root or str(Path(f.path).parent.resolve())
    os.makedirs(root, exist_ok=True)

    client = MCPClient(server_uri="local://revivoai", allowed_root_path=root)
    client.connect()
    push_log(file_id, f"[MCP] Writing to '{f.path}' under '{root}'...")

    try:
        success = client.writeFile(f.path, f.ai_source)
    except PermissionError as e:
        show_alert(f"MCP write blocked: {e}", alert_type='negative')
        push_log(file_id, f"[MCP] 🔴 Write blocked — {e}")
        client.disconnect()
        return
        
    client.disconnect()

    if success:
        f.status = FileStatus.APPROVED
        show_alert(f"MCP Action: Wrote verified patch to '{f.path}'", alert_type='positive')
        push_log(file_id, f"[MCP] 🟢 Local file '{f.path}' successfully overwritten.")
    else:
        show_alert(f"MCP write failed for '{f.path}'. See logs.", alert_type='negative')
        push_log(file_id, f"[MCP] 🔴 writeFile() returned False for '{f.path}'.")

def reject_file(file_id: str, note: str):
    f = get_file(file_id)
    f.status, f.rejection_note, state.rejecting[file_id] = FileStatus.REJECTED, note, False
    push_log(file_id, f"[User Action] 🔴 Patch rejected. Note: {note}")

def open_reject_dialog(file_id: str):
    f = get_file(file_id)
    if not f:
        return
    with ui.dialog() as reject_dialog, ui.card().classes('w-[440px] border-4 border-black shadow-[8px_8px_0_0_rgba(0,0,0,1)] p-6 bg-white'):
        ui.label("Reject Patch").classes('text-xl font-black mb-1 tracking-tight')
        ui.label("Provide a reason for rejecting this AI patch:").classes('text-sm text-gray-600 mb-3')
        note_input = ui.textarea(value=f.rejection_note or "", placeholder="Enter reason for rejection...").classes('w-full mb-4 font-mono text-sm').props('rows=4 autofocus borderless')
        with ui.row().classes('w-full justify-end gap-3'):
            ui.button("Cancel", on_click=reject_dialog.close).props('flat text-color=black').classes('border-2 border-black font-black px-4 py-1')
            def do_reject():
                reject_file(file_id, note_input.value or "")
                reject_dialog.close()
                refresh_all()
            ui.button("Confirm Reject", on_click=do_reject).props('color=negative').classes('border-2 border-black font-black px-6 py-1 text-white shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]')
    reject_dialog.open()

def open_retest_dialog(file_id: str):
    f = get_file(file_id)
    if not f:
        return

    with ui.dialog() as retest_dialog, ui.card().classes('w-[90vw] max-w-[540px] border-4 border-black shadow-[8px_8px_0_0_rgba(0,0,0,1)] p-6 bg-white flex flex-col gap-4'):
        with ui.row().classes('w-full justify-between items-start mb-0'):
            with ui.column().classes('gap-0.5'):
                ui.label("Re-test with Feedback").classes('text-xl font-black tracking-tight text-black')
                ui.label(f"Target File: {f.filename}").classes('text-xs font-mono font-bold text-gray-500 truncate max-w-[420px]')
            ui.button(icon='close', on_click=retest_dialog.close).props('flat round dense size=sm text-color=black')

        ui.label("Provide optional instructions or feedback for the AI agent before re-testing:").classes('text-xs text-gray-700 font-sans')
        
        existing_fb = state.user_feedback.get(file_id, "")
        feedback_input = ui.textarea(
            value=existing_fb,
            placeholder='e.g., Fix the off-by-one error in binary search, preserve existing exception handlers...'
        ).props('rows=4 autofocus borderless').classes('w-full font-mono text-sm')

        with ui.row().classes('w-full justify-end items-center gap-3 pt-2'):
            ui.button("Cancel", on_click=retest_dialog.close).props('flat text-color=black size=sm').classes('border-2 border-black font-bold text-xs px-4 py-1.5 shadow-[2px_2px_0_0_rgba(0,0,0,1)]')
            
            def do_confirm_retest():
                fb_text = (feedback_input.value or "").strip()
                state.user_feedback[file_id] = fb_text
                retest_dialog.close()
                if fb_text:
                    push_log(file_id, f"[User Feedback] Developer note: {fb_text}")
                else:
                    push_log(file_id, "[User Action] Retrying AI translation...")
                run_translation_simulation(file_id)

            ui.button("Confirm Re-test", icon='replay', on_click=do_confirm_retest) \
                .props('color=primary text-color=white size=sm') \
                .classes('border-2 border-black font-black text-xs px-5 py-1.5 shadow-[2px_2px_0_0_rgba(0,0,0,1)] text-white')

    retest_dialog.open()

def start_edit(file_id: str): 
    state.diff_state[file_id] = "editing"
    
def mark_dirty(file_id: str):
    f = get_file(file_id)
    if f.status != FileStatus.EDITED_PENDING: f.status = FileStatus.EDITED_PENDING
    
def save_and_retest(file_id: str, widget_value: str):
    f = get_file(file_id)
    state.edit_buffer[file_id] = widget_value
    f.ai_source = widget_value
    state.diff_state[file_id] = "readonly"
    push_log(file_id, "[User Action] Manual patch edit submitted. Restarting execution...")
    state.is_thinking = True 
    asyncio.create_task(simulate_sandbox(file_id))

def refresh_all():
    try:
        if getattr(state, 'drawer', None) is not None:
            if state.files and not state.import_mode:
                state.drawer.value = True
                state.drawer.show()
            else:
                state.drawer.value = False
                state.drawer.hide()
    except Exception:
        pass

    try:
        render_sidebar.refresh()
    except Exception:
        pass

    try:
        render_main.refresh()
    except Exception:
        pass

def build_orchestrator_payload(file_id: str) -> dict:
    f = get_file(file_id)
    import dataclasses
    f_dict = dataclasses.asdict(f)
    f_dict['status'] = f.status.value if hasattr(f.status, 'value') else f.status
    
    feedback = state.user_feedback.get(file_id, "").strip()
    system_prompt = f"USER FEEDBACK / INSTRUCTIONS FOR PATCH REFACTORING:\n{feedback}\n" if feedback else ""

    return {
        "session_id": state.session_id,
        "target_file": f_dict,
        "file_path": f.path,
        "workspace_dir": state.project_root,
        "system_prompt": system_prompt,
        "persona": f.persona,
        "patched_code": "",
        "iteration_count": 0,
        "max_iterations": int(state.max_iterations) if state.max_iterations is not None else 3,
        "api_key": state.api_key
    }

def translate_error_for_user(raw_log: str) -> str:
    """Translates scary Python tracebacks into user-friendly explanations."""
    # If it's a standard system log and not a crash, leave it alone!
    if not "Traceback (most recent call last)" in raw_log and not "Error:" in raw_log:
        return raw_log

    friendly_msg = "Runtime Error: The sandbox encountered an error while executing the patch."
    
    if "ModuleNotFoundError" in raw_log:
        try:
            module = raw_log.split("named ")[-1].splitlines()[0].strip().strip("'\"")
            friendly_msg = f"Missing Dependency: The AI tried to use a package ('{module}') that isn't installed in the secure sandbox."
        except:
            friendly_msg = "Missing Dependency: The AI tried to use an uninstalled package."
    elif "SyntaxError" in raw_log:
        friendly_msg = "Syntax Error: The AI generated invalid code with a typo."
    elif "TimeoutError" in raw_log:
        friendly_msg = "Timeout: The test took too long to run and was terminated to prevent an infinite loop."
    elif "NameError" in raw_log:
        friendly_msg = "Name Error: The AI tried to use a variable or function before defining it."
        
    return f"🔴 [AI Sandbox Crash] {friendly_msg}"

async def ensure_session_initialized() -> str | None:
    if not state.session_id:
        if not state.session_handler:
            state.session_handler = SessionHandler()
        session_id = await state.session_handler.initialize_session(user_id=str(uuid.uuid4()))
        state.session_id = session_id
        if session_id:
            background_tasks.create(websocket_listener(session_id))
    return state.session_id

async def websocket_listener(session_id: str):
    websocket_url = f"ws://localhost:8000/ws/{session_id}"
    try:
        async with websockets.connect(websocket_url) as websocket:
            while True:
                message = await websocket.recv()
                payload = json.loads(message) if isinstance(message, str) else message

                target_file = payload.get("target_file") if isinstance(payload, dict) else None
                file_id = None
                if isinstance(target_file, dict):
                    file_id = target_file.get("file_id")
                if not file_id:
                    file_id = state.active_buffer

                if not file_id or file_id not in state.files:
                    continue

                prev_status = state.files[file_id].status
                prev_phase = state.thinking_phase
                prev_thinking = state.is_thinking
                prev_agent_state = state.agent_state.get(file_id)

                if isinstance(payload, dict):
                    log_entry = payload.get("log_entry")
                    if log_entry and isinstance(log_entry, dict):
                        entry = dict(log_entry)
                        entry["message"] = translate_error_for_user(entry.get("message", ""))
                        push_log(file_id, entry)
                    elif "traceback_log" in payload and payload["traceback_log"]:
                        log_msg = str(payload["traceback_log"])
                        friendly_log = translate_error_for_user(log_msg)
                        push_log(file_id, friendly_log)
                        
                    raw_log_msg = str(payload.get("traceback_log", "")) + " " + str(payload.get("log_entry", {}).get("message", ""))
                    src = str(payload.get("log_entry", {}).get("source", "")).upper()
                    node_key = str(payload.get("current_node", "")).lstrip("_")

                    if node_key:
                        state.agent_state[file_id] = node_key

                    # Map incoming states and logs to active UI phases
                    if state.is_thinking:
                        if src == "LLM" or node_key == "llm_patch_node" or "Prompting" in raw_log_msg or "Analyzing" in raw_log_msg or "Patch" in raw_log_msg:
                            state.files[file_id].status = FileStatus.TRANSLATING
                            state.agent_state[file_id] = "llm_patch_node"
                            if "Prompting" in raw_log_msg or "Generating" in raw_log_msg:
                                state.thinking_phase = 0
                            elif "Analyzing" in raw_log_msg:
                                state.thinking_phase = 1
                            elif "Patch received" in raw_log_msg or "Response" in raw_log_msg or "Parsing" in raw_log_msg:
                                state.thinking_phase = 2

                        elif src in ("DKR", "TEST", "DOCKER", "PYTEST") or node_key in ("sandbox_node", "telemetry_node") or "Provisioning" in raw_log_msg or "Injecting" in raw_log_msg or "Executing" in raw_log_msg or "container" in raw_log_msg:
                            state.files[file_id].status = FileStatus.SANDBOX_TESTING
                            state.agent_state[file_id] = "sandbox_node"
                            if "Provisioning" in raw_log_msg:
                                state.thinking_phase = 0
                            elif "Injecting" in raw_log_msg:
                                state.thinking_phase = 1
                            elif "Executing" in raw_log_msg or "Test run" in raw_log_msg or "tests" in raw_log_msg:
                                state.thinking_phase = 2

                    if "patched_code" in payload and payload["patched_code"]:
                        state.files[file_id].ai_source = payload["patched_code"]

                    # Terminal state resolution from websocket exit_code or log completion
                    if "docker_exit_code" in payload or node_key in ("sandbox_node", "telemetry_node"):
                        exit_code = payload.get("docker_exit_code")
                        try:
                            iteration = int(payload.get("iteration_count", 1) or 1)
                        except (ValueError, TypeError):
                            iteration = 1
                        try:
                            max_iters = int(payload.get("max_iterations", 3) or 3)
                        except (ValueError, TypeError):
                            max_iters = 3

                        if exit_code == 0 or "All tests passed" in raw_log_msg:
                            state.files[file_id].status = FileStatus.PASSED
                            state.is_thinking = False
                            state.agent_state[file_id] = "Done"
                        elif exit_code is not None and exit_code != 0:
                            if iteration >= max_iters or "Max iterations reached" in raw_log_msg:
                                state.files[file_id].status = FileStatus.FAILED
                                state.is_thinking = False
                                state.agent_state[file_id] = "Done"
                                state.files[file_id].raw_traceback = str(payload.get("traceback_log", "")) or str(payload.get("log_entry", {}).get("details", {}).get("raw_output", ""))
                            else:
                                state.files[file_id].raw_traceback = str(payload.get("traceback_log", "")) or str(payload.get("log_entry", {}).get("details", {}).get("raw_output", ""))

                new_status = state.files[file_id].status
                new_phase = state.thinking_phase
                new_thinking = state.is_thinking
                new_agent_state = state.agent_state.get(file_id)

                status_changed = (new_status != prev_status)
                phase_changed = (new_phase != prev_phase)
                thinking_changed = (new_thinking != prev_thinking)
                agent_state_changed = (new_agent_state != prev_agent_state)

                if status_changed:
                    try:
                        render_sidebar.refresh()
                    except Exception:
                        pass

                if status_changed or phase_changed or thinking_changed or agent_state_changed:
                    try:
                        render_main.refresh()
                    except Exception:
                        pass
    except Exception as exc:
        if session_id:
            push_log(state.active_buffer or "", f"[WebSocket] Listener stopped for session {session_id}: {exc}")

async def _trigger_backend_run(file_id: str):
    await ensure_session_initialized()
    if not state.session_id:
        raise RuntimeError("Session has not been initialized.")

    payload = build_orchestrator_payload(file_id)

    target_file = payload.get("target_file")
    if target_file is not None and not isinstance(target_file, dict):
        from dataclasses import asdict, is_dataclass
        if hasattr(target_file, "model_dump"):
            payload["target_file"] = target_file.model_dump(mode="json")
        elif hasattr(target_file, "dict"):
            payload["target_file"] = target_file.dict()
        elif is_dataclass(target_file):
            payload["target_file"] = asdict(target_file)
        else:
            payload["target_file"] = vars(target_file)

    async with httpx.AsyncClient() as client:
        try:
            # Restore the standard 10-second timeout since it returns immediately
            await client.post(f"http://localhost:8000/api/run/{state.session_id}", json=payload, timeout=10.0)
        except Exception as exc:
            raise RuntimeError(f"Backend request failed: {exc}") from exc
            
    return True
# ============================================================================
# ASYNC SIMULATIONS (LANGGRAPH NODES)
# ============================================================================
async def simulate_translation(file_id: str):
    if file_id not in state.files:
        return

    state.is_thinking = True
    state.agent_state[file_id] = "Starting"
    state.files[file_id].status = FileStatus.TRANSLATING
    push_log(file_id, f"Initializing AgentState with workspace: {state.project_root}")

    try:
        # Just fire the API request! The WebSocket will handle ALL terminal state logic.
        await _trigger_backend_run(file_id)
    except Exception as exc:
        state.files[file_id].status = FileStatus.FAILED
        state.agent_state[file_id] = "Failed"
        state.is_thinking = False
        push_log(file_id, f"[System] Translation failed: {exc}")
        show_alert(f"Translation could not start: {exc}", alert_type='warning')
    finally:
        refresh_all()

async def simulate_sandbox(file_id: str, is_chained: bool = False):
    push_log(file_id, f"Initializing AgentState with workspace: {state.project_root}")
    state.is_thinking = True
    
    state.files[file_id].status = FileStatus.SANDBOX_TESTING
    state.agent_state[file_id] = "sandbox_node"
    state.thinking_phase = 0
    refresh_all()
    
    try:
        await _trigger_backend_run(file_id)
    except Exception as exc:
        state.files[file_id].status = FileStatus.FAILED
        state.agent_state[file_id] = "Failed"
        state.is_thinking = False
        push_log(file_id, f"[System] Sandbox run failed: {exc}")
    finally:
        refresh_all()

def run_translation_simulation(file_id: str):
    if file_id not in state.files:
        return

    state.is_thinking = True
    state.agent_state[file_id] = "Starting"
    state.files[file_id].status = FileStatus.TRANSLATING

    try:
        render_sidebar.refresh()
        render_main.refresh()
    except Exception:
        pass

    async def _runner():
        await ensure_session_initialized()
        if not state.session_id:
            state.agent_state[file_id] = "Starting"
            show_alert("Translation started locally; backend session is not ready yet.", alert_type='warning')
            return
        await simulate_translation(file_id)

    try:
        background_tasks.create(_runner())
    except Exception:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is not None:
            loop.create_task(_runner())

def run_sandbox_simulation(file_id: str):
    background_tasks.create(simulate_sandbox(file_id))

def pause_batch():
    state.is_batch_paused = True
    push_log(state.active_buffer, "[Batch] Batch processing paused. You can now review, edit, or re-test files.")
    show_alert("Batch paused. You can now edit/re-test files, then click Resume.", alert_type='warning')
    refresh_all()

def resume_batch():
    state.is_batch_paused = False
    push_log(state.active_buffer, "[Batch] Resuming batch queue execution...")
    show_alert("Resuming batch processing...", alert_type='info')
    if not state.is_batch_running and state.batch_queue:
        background_tasks.create(process_batch_queue(state.batch_queue[state.batch_current_idx:]))
    refresh_all()

def stop_batch():
    state.cancel_batch_flag = True
    state.is_batch_paused = False
    state.is_batch_running = False
    state.batch_queue = []
    state.batch_current_idx = 0
    show_alert("Batch processing stopped.", alert_type='warning')
    refresh_all()

async def process_batch_queue(selected_file_ids: list[str]):
    """Sequentially processes a specific list of files with pause/resume support."""
    if state.is_batch_running and not state.is_batch_paused:
        show_alert("Batch processing is already running!", alert_type='warning')
        return

    state.is_batch_running = True
    state.is_batch_paused = False
    state.cancel_batch_flag = False
    state.batch_queue = list(selected_file_ids)
    state.batch_current_idx = 0
    state.last_batch_report = {"file_ids": list(selected_file_ids)}
    show_alert(f"Starting batch process for {len(selected_file_ids)} files...", alert_type='info')
    refresh_all()

    try:
        await ensure_session_initialized()
        while state.batch_current_idx < len(state.batch_queue):
            if state.cancel_batch_flag:
                show_alert("Batch processing stopped by user.", alert_type='warning')
                break

            # Handle Pause state
            while state.is_batch_paused and not state.cancel_batch_flag:
                await asyncio.sleep(0.5)

            if state.cancel_batch_flag:
                break

            fid = state.batch_queue[state.batch_current_idx]
            f = state.files.get(fid)
            if not f or f.status in (FileStatus.TRANSLATING, FileStatus.SANDBOX_TESTING):
                state.batch_current_idx += 1
                continue

            set_active_buffer(fid)
            run_translation_simulation(fid)

            # Wait for file to reach a terminal or ready state
            wait_time = 0.0
            while state.files.get(fid) and state.files[fid].status in (FileStatus.TRANSLATING, FileStatus.SANDBOX_TESTING) and not state.cancel_batch_flag:
                if state.is_batch_paused:
                    break
                await asyncio.sleep(0.5)
                wait_time += 0.5
                if wait_time > 180.0:  # 3 minutes safety timeout per file
                    push_log(fid, "[Batch] File processing timed out.")
                    break
                
            if state.is_batch_paused:
                while state.is_batch_paused and not state.cancel_batch_flag:
                    await asyncio.sleep(0.5)
                if state.cancel_batch_flag:
                    break

            state.batch_current_idx += 1
            await asyncio.sleep(0.5)

        if not state.cancel_batch_flag and not state.is_batch_paused:
            show_alert("Batch queue completed!", alert_type='positive')
    except Exception as exc:
        show_alert(f"Batch processing encountered an issue: {exc}", alert_type='negative')
    finally:
        if state.batch_current_idx >= len(state.batch_queue) or state.cancel_batch_flag or not state.is_batch_paused:
            state.is_batch_running = False
            state.is_batch_paused = False
            state.cancel_batch_flag = False
            state.batch_queue = []
            state.batch_current_idx = 0
        refresh_all()

def open_batch_dialog():
    if state.is_batch_running:
        show_alert("Batch is currently running. Click Stop Batch in the sidebar if you wish to cancel.", alert_type='warning')
        return

    valid_files = [f for f in state.files.values() if f.status in (FileStatus.QUEUED, FileStatus.FAILED, FileStatus.EDITED_PENDING, FileStatus.REJECTED)]
    if not valid_files:
        show_alert("No eligible files to batch process (all files are either Done or Running).", alert_type='warning')
        return

    valid_file_ids = {f.file_id for f in valid_files}
    valid_files_map = {fid: f for fid, f in state.files.items() if fid in valid_file_ids}

    # Build hierarchical tree nodes for the valid files
    nodes, expanded_folders = build_hierarchical_file_tree(
        valid_files_map,
        search_query="",
        status_filter="All",
        module_filter="All"
    )

    with ui.dialog() as dlg, ui.card().classes('w-[520px] border-4 border-black shadow-[8px_8px_0_0_rgba(0,0,0,1)] p-6 bg-white'):
        ui.label('📦 BATCH PROCESSING').classes('text-xl font-black mb-1 tracking-tight')
        ui.label('Select the folders or individual files you want to modernize.').classes('text-sm text-gray-600 mb-4')
        
        with ui.row().classes('w-full justify-end gap-2 mb-2'):
            ui.button('Select All', on_click=lambda: tree.select_all()).props('flat size=sm text-color=blue').classes('font-bold')
            ui.button('Clear', on_click=lambda: tree.clear_all()).props('flat size=sm text-color=gray').classes('font-bold')
        
        selected_ticked_keys: list[str] = []
        def _on_ticked_change(ticked: list[str]):
            nonlocal selected_ticked_keys
            selected_ticked_keys = list(ticked)

        tree = LazyFileTree(
            nodes=nodes,
            root_path=state.project_root,
            tick_strategy='leaf',
            initial_expanded=expanded_folders,
            height='300px',
            on_ticked_change=_on_ticked_change,
        ).classes('w-full border-2 border-black p-2 bg-gray-50')

        with ui.row().classes('w-full justify-end gap-4 mt-6'):
            ui.button('Cancel', on_click=dlg.close).props('flat text-color=black font-bold').classes('border-2 border-black font-black px-6 py-2')
            
            def start_batch():
                selected = []
                keys_to_check = list(tree.ticked) if tree.ticked else list(selected_ticked_keys)
                for key in keys_to_check:
                    file_id = _find_file_id_by_tree_key(key)
                    if file_id and file_id in valid_file_ids and file_id not in selected:
                        selected.append(file_id)
                if not selected:
                    show_alert("Please select at least one file.", alert_type='warning')
                    return
                dlg.close()
                background_tasks.create(process_batch_queue(selected))
                
            ui.button('Start Batch', on_click=start_batch).props('color=blue').classes('border-2 border-black shadow-[4px_4px_0_0_rgba(0,0,0,1)] font-black px-8 py-2 text-white hover:-translate-y-px hover:-translate-x-px hover:shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] transition-all')
            
    dlg.open()

# ============================================================================
# WELCOME SCREEN
# ============================================================================
def render_welcome():
    ui.add_css('''
        body .welcome-import-card {
            background-color: #ffffff !important;
            transition: all 0.15s ease-in-out !important;
        }
        body .welcome-import-card:hover {
            background-color: #3b82f6 !important;
            transform: translate(-2px, -2px);
            box-shadow: 6px 6px 0px 0px #101010 !important;
        }
        body .welcome-import-card:hover,
        body .welcome-import-card:hover * {
            color: #ffffff !important;
        }
    ''')

    async def handle_upload(e: events.UploadEventArguments):
        try:
            from backend.import_utils import import_from_uploads
            imported_files = await import_from_uploads([e])
            for f in imported_files:
                name = f.path or e.name
                if any(entry.get('name') == name for entry in state.staging_files):
                    show_alert(f"Skipped duplicate file: {name}", alert_type='warning')
                    continue

                size_bytes = len(f.legacy_source.encode('utf-8'))
                size_str = f'{size_bytes / 1024:.1f} KB' if size_bytes >= 1024 else f'{size_bytes} B'
                state.staging_files.append({
                    'name': name,
                    'size_str': size_str,
                    'pct': 100,
                    'status': 'done',
                    'project_file': f,
                })
        except Exception:
            e_name = getattr(e, 'name', getattr(getattr(e, 'file', None), 'name', getattr(getattr(e, 'file', None), 'filename', 'unknown_file')))
            state.staging_files.append({
                'name': e_name, 'size_str': '?', 'pct': 100, 'status': 'failed', 'project_file': None,
            })

    def finish_upload(e=None):
        if state.staging_files:
            state.import_mode = "STAGING"
        refresh_all()

    # ================================================================
    # STAGING SCREEN — file review before entering workspace
    # ================================================================
    if state.import_mode == "STAGING":
        summary = get_staging_summary_counts()
        total = summary["total"]
        done = summary["done"]
        failed = summary["failed"]
        uploading = summary["uploading"]

        with ui.column().classes('w-full items-center justify-center pt-8 pb-8 gap-0'):
            ui.html('''
                <div class="welcome-screen">
                    <div class="welcome-kicker">📋 REVIEW YOUR FILES</div>
                    <div style="font-family:'Archivo Black',sans-serif;font-weight:900;font-size:3rem;
                                color:#101010;text-transform:uppercase;margin-bottom:8px;">
                        STAGING AREA
                    </div>
                    <div class="welcome-desc">
                        Verify your files below. Remove unwanted files, retry failures, then proceed.
                    </div>
                </div>
            ''')

            with ui.column().classes('w-full max-w-4xl px-4 gap-0 items-center'):

                # ── Summary bar & Add Files ─────────────────────────
                with ui.row().classes('w-full justify-center items-center gap-6 mb-4'):
                    ui.html(f'''
                        <div style="display:flex;gap:12px;align-items:center;">
                            <div class="dz-status-badge">\U0001f4c1 {total} files</div>
                            <div class="dz-status-badge" style="background:#00c853;color:#101010;">\u2705 {done} ready</div>
                            {'<div class="dz-status-badge" style="background:#ff3333;color:#101010;">\u274c ' + str(failed) + ' failed</div>' if failed else ''}
                            {'<div class="dz-status-badge" style="background:#f5c518;color:#101010;">\u23f3 ' + str(uploading) + ' uploading</div>' if uploading else ''}
                        </div>
                    ''')
                    ui.html('<div style="width:2px; height:28px; background:#101010; opacity:0.2;"></div>')
                    with ui.row().classes('gap-4'):
                        ui.button('+ Files', on_click=open_file_picker).props('color=white text-color=black flat').classes(
                            'border-2 border-black font-black px-4 py-1 hover:-translate-y-px hover:-translate-x-px hover:shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] transition-all'
                        )
                        ui.button('+ Project', on_click=handle_native_import_project).props('color=white text-color=black flat').classes(
                            'border-2 border-black font-black px-4 py-1 hover:-translate-y-px hover:-translate-x-px hover:shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] transition-all'
                        )

                # ── File list ───────────────────────────────────────
                with ui.element('div').classes('dz-file-list-container mb-4').style('display: flex; flex-direction: column;'):
                    if not state.staging_files:
                        ui.html('<div style="text-align:center; padding: 40px; font-weight:bold; color:#666;">Staging area empty. Click "+ Files" or "+ Project" above to import.</div>')
                    else:
                        with ui.element('div').classes('w-full relative'):
                            with ui.column().classes('w-full gap-2 dz-file-list'):
                                for entry in state.staging_files:
                                    pct  = entry.get('pct', 100)
                                    stat = entry.get('status', 'done')
                                    name = entry.get('name', '?')
                                    size = entry.get('size_str', '?')

                                    if stat == 'done':
                                        status_html = '<div class="dz-file-status-icon done">&#10004;</div>'
                                    elif stat == 'failed':
                                        status_html = '<div class="dz-file-status-icon" style="color:#ff3333;">&#10008;</div>'
                                    else:
                                        status_html = f'<div class="dz-file-status-icon" style="font-size:10px;">{pct}%</div>'

                                    with ui.element('div').classes('dz-file-row'):
                                        ui.html(f'<div class="dz-merged-icon">{status_html}<div class="dz-file-icon">\U0001f4c4</div></div>')
                                        ui.html(f'<div class="dz-file-name-container"><span class="dz-file-name">{name}</span><span class="dz-file-size">{size}</span></div>')
                                        
                                        if stat == 'done':
                                            ui.html('<div></div>')
                                        else:
                                            ui.html(f'''
                                                <div class="dz-file-progress-wrapper">
                                                    <div class="dz-file-progress-bar {'failed' if stat == 'failed' else 'uploading' if stat == 'uploading' else ''}" style="width:{pct}%;"></div>
                                                </div>
                                            ''')

                                        if stat == 'failed':
                                            def do_retry(ent=entry):
                                                ent['status'] = 'done'
                                                ent['pct'] = 100
                                                refresh_all()
                                            ui.button('Retry', on_click=lambda _, ent=entry: do_retry(ent)).classes('dz-action-btn')
                                        else:
                                            def do_replace(ent=entry):
                                                import time
                                                
                                                # Discard queued clicks that happened while we were blocked
                                                last_pick = getattr(state, '_last_pick_end', 0)
                                                if time.time() - last_pick < 0.5:
                                                    return
                                                    
                                                if getattr(state, '_is_picking', False):
                                                    return
                                                    
                                                state._is_picking = True
                                                try:
                                                    def pick():
                                                        import tkinter as _tk
                                                        from tkinter import filedialog as _fd
                                                        root = _tk.Tk()
                                                        root.attributes('-topmost', True)
                                                        root.withdraw()
                                                        path = _fd.askopenfilename(title='Replace file')
                                                        root.destroy()
                                                        return path
                                                        
                                                    path = pick()
                                                    if path:
                                                        try:
                                                            with open(path, 'r', encoding='utf-8', errors='replace') as fh:
                                                                content = fh.read()
                                                            from backend.import_utils import _guess_lang
                                                            fname = Path(path).name
                                                            pf = ProjectFile(
                                                                file_id=f'f_{uuid.uuid4().hex[:8]}',
                                                                path=path,
                                                                legacy_source=content,
                                                                ai_source='',
                                                                status=FileStatus.QUEUED,
                                                                language=_guess_lang(fname),
                                                            )
                                                            ent['name'] = fname
                                                            ent['size_str'] = f'{len(content.encode("utf-8")) / 1024:.1f} KB'
                                                            ent['pct'] = 100
                                                            ent['status'] = 'done'
                                                            ent['project_file'] = pf
                                                            refresh_all()
                                                        except Exception:
                                                            pass
                                                finally:
                                                    state._is_picking = False
                                                    state._last_pick_end = time.time()
                                            btn_replace = ui.button('Replace', on_click=lambda _, ent=entry: do_replace(ent)).props('color=white text-color=black').classes('dz-action-btn dz-replace-btn')
                                            if stat == 'uploading':
                                                btn_replace.props('disable')

                                        def do_remove(ent=entry):
                                            if ent in state.staging_files:
                                                state.staging_files.remove(ent)
                                                refresh_all()
                                        ui.button('Remove', on_click=lambda _, ent=entry: do_remove(ent)).props('color=white text-color=red').classes('dz-action-btn dz-remove-btn')

                # ── Proceed / Cancel ────────────────────────────────
                with ui.row().classes('w-full justify-center gap-4 mt-2'):
                    def cancel_staging():
                        state.staging_files = []
                        state.import_mode = None
                        refresh_all()

                    ui.button('Cancel', on_click=cancel_staging).props('color=white text-color=red').classes(
                        'dz-cancel-btn border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] font-black px-8 py-2 hover:-translate-y-px hover:-translate-x-px hover:shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] transition-all'
                    )
                    ui.button(
                        f'Proceed with {done} file{"s" if done != 1 else ""}',
                        on_click=commit_staging_to_workspace,
                    ).props('color=blue').classes(
                        'border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] font-black px-8 py-2 hover:-translate-y-px hover:-translate-x-px hover:shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] transition-all'
                    )
        return

    # ================================================================
    # WELCOME SCREEN — initial landing page
    # ================================================================
    with ui.column().classes('w-full items-center justify-center pt-8 pb-8 gap-0'):
        ui.html('''
            <div class="welcome-screen">
                <div class="welcome-kicker">\u2699\ufe0f LEGACY CODE MODERNIZATION TOOL</div>
                <div class="welcome-title">REVIVO<span class="welcome-title-accent">AI</span></div>
                <div class="welcome-desc">
                    Turn brittle legacy systems into modern, sandbox-verified code.
                </div>
            </div>
        ''')

        with ui.column().classes('w-full max-w-6xl px-4 gap-4 items-center'):

            # ── Import buttons ────────────────────────────────────────────
            with ui.row().classes('w-full justify-center items-stretch gap-8 mt-8'):

                with ui.card().classes(
                    'welcome-import-card flex-1 cursor-pointer flex flex-col items-center justify-center text-center '
                    'border-4 border-black shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] p-12 min-h-[200px]'
                ) as card1:
                    ui.html('<div class="welcome-import-title" style="font-size:2.5rem;margin-bottom:16px;">IMPORT FILES</div>'
                            '<div class="welcome-import-desc" style="font-size:1.25rem;">Select individual source files to translate.<br>Best for targeting a few specific files.</div>')
                    card1.on('click', open_file_picker)

                with ui.card().classes(
                    'welcome-import-card flex-1 cursor-pointer flex flex-col items-center justify-center text-center '
                    'border-4 border-black shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] p-12 min-h-[200px]'
                ) as card2:
                    ui.html('<div class="welcome-import-title" style="font-size:2.5rem;margin-bottom:16px;">IMPORT PROJECT</div>'
                            '<div class="welcome-import-desc" style="font-size:1.25rem;">Scan a local directory tree for source files.<br>Best for translating an entire codebase.</div>')
                    card2.on('click', handle_native_import_project)

            # ── Demo button ───────────────────────────────────────────────
            ui.html('<div style="color:#888;font-weight:700;font-size:0.9rem;margin:8px 0;">\u2500\u2500\u2500 OR \u2500\u2500\u2500</div>')
            ui.button('Load Test Scripts', on_click=load_demo_project).props('color=blue').classes(
                'w-full max-w-md border-4 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] font-black py-2'
            )



# ============================================================================
# SIDEBAR
# ============================================================================
def open_settings_dialog():
    with ui.dialog() as settings_dialog, ui.card().classes('w-[400px] border-4 border-black shadow-[8px_8px_0_0_rgba(0,0,0,1)] p-6 bg-white'):
        ui.label('⚙️ SYSTEM SETTINGS').classes('text-xl font-black mb-4 tracking-tight')
        
        # API Key Input
        ui.label('Gemini API Key').classes('text-sm font-bold text-gray-700 uppercase')
        ui.input(placeholder='AIzaSy...', password=True, password_toggle_button=True) \
            .bind_value(state, 'api_key') \
            .classes('w-full mb-4') \
            .props('outlined dense')
        
        # Max Iterations Input
        ui.label('Max Sandbox Iterations').classes('text-sm font-bold text-gray-700 uppercase')
        def _on_max_iter_change(e):
            try:
                state.max_iterations = int(e.value) if e.value is not None else 3
            except (ValueError, TypeError):
                state.max_iterations = 3
        ui.number(min=1, max=10, step=1, precision=0, format='%d', value=int(state.max_iterations or 3), on_change=_on_max_iter_change) \
            .classes('w-full mb-6') \
            .props('outlined dense')
            
        with ui.row().classes('w-full justify-end mt-2'):
            ui.button('Save & Close', on_click=settings_dialog.close) \
                .props('color=black text-color=white unelevated') \
                .classes('font-bold px-6 py-2 hover:-translate-y-px hover:shadow-[2px_2px_0px_0px_rgba(0,0,0,0.5)] transition-all')
            
    settings_dialog.open()

def open_clear_workspace_dialog():
    with ui.dialog() as confirm_dialog, ui.card().classes('w-[420px] border-4 border-black shadow-[8px_8px_0_0_rgba(0,0,0,1)] p-6 bg-white'):
        ui.label('Clear Workspace?').classes('text-xl font-black mb-2 tracking-tight')
        ui.label('This will remove all files from the current session. Unsaved changes will be lost.').classes('text-sm text-gray-600 mb-4')
        with ui.row().classes('w-full justify-end gap-3'):
            ui.button('Cancel', on_click=confirm_dialog.close).props('flat text-color=black').classes('border-2 border-black font-black px-4 py-1')
            def do_clear():
                state.files.clear()
                state.active_buffer = None
                state.project_root = None
                state.import_mode = None
                state.is_batch_running = False
                state.cancel_batch_flag = False
                state.is_thinking = False
                confirm_dialog.close()
                refresh_all()
            ui.button('Clear', on_click=do_clear).props('color=negative').classes('border-2 border-black font-black px-6 py-1 text-white shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]')
    confirm_dialog.open()

@ui.refreshable
def render_sidebar():
    with ui.column().classes('relative w-full h-full p-0 m-0 bg-white select-none overflow-hidden flex flex-col'):
        
        # 1. CLEAN IDE EXPLORER HEADER (2 non-overlapping rows)
        with ui.column().classes('w-full p-0 m-0 border-b-2 border-black flex-shrink-0'):
            # Row 1: Brand & Batch Action
            with ui.row().classes('w-full px-3 py-2 bg-yellow-50 items-center justify-between flex-nowrap border-b border-gray-300'):
                ui.label('REVIVOAI').classes('font-black text-xs tracking-wider text-black bg-yellow-300 px-2 py-0.5 border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]')
                
                if state.is_batch_running:
                    with ui.row().classes('items-center gap-1'):
                        if state.is_batch_paused:
                            ui.button('▶️ Resume', on_click=resume_batch) \
                                .props('size=xs color=green text-color=white unelevated') \
                                .classes('font-bold border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] text-[11px] px-2 py-0.5') \
                                .tooltip('Resume Paused Batch')
                        else:
                            ui.button('⏸️ Pause', on_click=pause_batch) \
                                .props('size=xs color=warning text-color=black unelevated') \
                                .classes('font-bold border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] text-[11px] px-2 py-0.5') \
                                .tooltip('Pause Batch to inspect/edit')
                        ui.button('🛑 Stop', on_click=stop_batch) \
                            .props('size=xs color=red text-color=white unelevated') \
                            .classes('font-bold border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] text-[11px] px-2 py-0.5') \
                            .tooltip('Stop Active Batch')
                else:
                    ui.button('📦 Run Batch', on_click=open_batch_dialog) \
                        .props('size=xs color=blue text-color=white unelevated') \
                        .classes('font-bold border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] hover:-translate-y-px text-[11px] px-2.5 py-0.5') \
                        .tooltip('Run Batch Processing')

            # Row 2: Workspace Explorer title & Action Icons
            project_name = Path(state.project_root).name if state.project_root else "WORKSPACE"
            with ui.row().classes('w-full px-3 py-1 bg-gray-50 items-center justify-between flex-nowrap'):
                with ui.row().classes('items-center gap-1 min-w-0 flex-1'):
                    ui.label('EXPLORER:').classes('text-[10px] font-black tracking-widest text-gray-500 uppercase flex-shrink-0')
                    ui.label(project_name).classes('text-[10px] font-black text-gray-800 uppercase truncate max-w-[130px]')
                
                with ui.row().classes('items-center gap-0.5 flex-shrink-0'):
                    ui.button(icon='note_add', on_click=open_workspace_file_picker) \
                        .props('flat round dense size=xs text-color=black') \
                        .tooltip('Add Files to Workspace')
                    ui.button(icon='create_new_folder', on_click=add_project_to_workspace_from_dialog) \
                        .props('flat round dense size=xs text-color=black') \
                        .tooltip('Open Folder / Project')
                    ui.button(icon='unfold_less', on_click=lambda: tree_ref.collapse_all() if 'tree_ref' in locals() else None) \
                        .props('flat round dense size=xs text-color=black') \
                        .tooltip('Collapse All Folders')

        # 2. FULL-HEIGHT HIERARCHICAL IDE FILE TREE (Maximized Space)
        sidebar_nodes, expanded_folders = build_hierarchical_file_tree(
            state.files,
            search_query="",
            status_filter="All",
            module_filter="All"
        )

        with ui.column().classes('flex-1 w-full px-1 py-1 overflow-hidden min-h-0'):
            def on_file_selected(selected_key: str | None):
                file_id = _find_file_id_by_tree_key(selected_key)
                if file_id:
                    set_active_buffer(file_id)

            tree_ref = LazyFileTree(
                nodes=sidebar_nodes,
                initial_selected=_canonical_fs_path(state.files[state.active_buffer].path, state.project_root) if state.active_buffer and state.active_buffer in state.files else None,
                initial_expanded=expanded_folders,
                height='100%',
                on_selected_change=on_file_selected,
            ).classes('w-full h-full')

        # 3. SLIM FOOTER STATUS BAR
        total_files = len(state.files)
        passed_count = sum(1 for f in state.files.values() if f.status in (FileStatus.PASSED, FileStatus.APPROVED))
        failed_count = sum(1 for f in state.files.values() if f.status in (FileStatus.FAILED, FileStatus.REJECTED))
        queued_count = sum(1 for f in state.files.values() if f.status in (FileStatus.QUEUED, FileStatus.TRANSLATING, FileStatus.SANDBOX_TESTING))

        with ui.row().classes('w-full px-2.5 py-1.5 border-t-2 border-black bg-gray-100 items-center justify-between flex-shrink-0 text-[10px] font-mono'):
            with ui.row().classes('items-center gap-2 font-bold text-gray-700'):
                ui.label(f'📁 {total_files}')
                if passed_count:
                    ui.label(f'✓ {passed_count}').classes('text-green-700')
                if failed_count:
                    ui.label(f'! {failed_count}').classes('text-red-600 font-black')
                if queued_count:
                    ui.label(f'⏳ {queued_count}').classes('text-blue-600')

            with ui.row().classes('items-center gap-1'):
                ui.button(icon='settings', on_click=open_settings_dialog) \
                    .props('flat round dense size=xs text-color=black') \
                    .tooltip('Configuration & API Key')

                ui.button(icon='delete_outline', on_click=open_clear_workspace_dialog) \
                    .props('flat round dense size=xs text-color=red') \
                    .tooltip('Clear Workspace')

        # 4. DRAGGABLE RESIZER HANDLE
        ui.element('div').classes('sidebar-resizer').props('title="Drag to resize sidebar • Double-click to reset"')

# ============================================================================
# STATE MACHINE TRACKER (UI COMPONENT)
# ============================================================================
def render_segmented_status_header(f: ProjectFile, current_state: str, progress: int = 50, show_rerun: bool = False, rerun_callback=None):
    nodes = ["ANALYZE", "PROPOSE", "EXECUTE", "EVALUATE"]

    state_map = {
        "Starting": "ANALYZE",
        "llm_patch_node": "PROPOSE",
        "_llm_patch_node": "PROPOSE",
        "sandbox_node": "EXECUTE",
        "_sandbox_node": "EXECUTE",
        "telemetry_node": "EVALUATE",
        "_telemetry_node": "EVALUATE",
        "Done": "Done"
    }
    mapped_state = state_map.get(current_state, current_state)
    
    if mapped_state == "ANALYZE" or (mapped_state == "PROPOSE" and getattr(state, 'thinking_phase', 0) == 0):
        currentStep = 0
    elif mapped_state == "PROPOSE":
        currentStep = 1
    elif mapped_state == "EXECUTE":
        currentStep = 2
    elif mapped_state == "EVALUATE":
        currentStep = 3
    elif mapped_state == "Done" or f.status in (FileStatus.PASSED, FileStatus.APPROVED, FileStatus.FAILED, FileStatus.REJECTED):
        currentStep = 4
    elif mapped_state in nodes:
        currentStep = nodes.index(mapped_state)
    else:
        currentStep = -1

    # 1. Workspace Name
    workspace_name = Path(state.project_root).name if state.project_root else "WORKSPACE"
    
    # 2. File Name (formatted and truncated if too long)
    raw_name = f.filename if f.filename else (Path(f.path).name if f.path else "Untitled")
    max_len = 38
    if len(raw_name) > max_len:
        truncated_name = raw_name[:max_len - 3] + "..."
    else:
        truncated_name = raw_name

    # 3. Iteration counts
    try:
        curr_iter = int(getattr(f, 'iteration', 1) or 1)
    except (ValueError, TypeError):
        curr_iter = 1
    try:
        max_iter = int(getattr(state, 'max_iterations', 3) or 3)
    except (ValueError, TypeError):
        max_iter = 3

    # 4. Generate step items
    steps_html = []
    for i, name in enumerate(nodes):
        step_num = i + 1
        if i < currentStep:
            # Completed step: solid gold box, solid gold label, solid gold bar
            step_box = f'<span class="bg-[#ffc700] text-black font-mono font-black text-xs px-2 py-0.5 border border-[#ffc700] mr-2 flex-shrink-0">{step_num}</span>'
            step_label = f'<span class="font-mono font-black text-xs sm:text-sm tracking-wider text-[#ffc700] uppercase truncate">{name}</span>'
            progress_bar = '<div class="w-full h-2.5 bg-[#ffc700] mt-2.5"></div>'
        elif i == currentStep:
            # Active step: gold box, gold label, partial gold progress bar
            fill_pct = max(progress, 20)
            step_box = f'<span class="bg-[#ffc700] text-black font-mono font-black text-xs px-2 py-0.5 border border-[#ffc700] mr-2 flex-shrink-0">{step_num}</span>'
            step_label = f'<span class="font-mono font-black text-xs sm:text-sm tracking-wider text-[#ffc700] uppercase truncate">{name}</span>'
            progress_bar = f'''
            <div class="w-full h-2.5 bg-[#333333] mt-2.5 overflow-hidden relative">
                <div class="h-full bg-[#ffc700] transition-all duration-300" style="width: {fill_pct}%;"></div>
            </div>
            '''
        else:
            # Pending step: dark gray box with border, muted gray label, dark bar
            step_box = f'<span class="border border-[#555555] text-[#999999] font-mono font-bold text-xs px-2 py-0.5 mr-2 flex-shrink-0">{step_num}</span>'
            step_label = f'<span class="font-mono font-bold text-xs sm:text-sm tracking-wider text-[#999999] uppercase truncate">{name}</span>'
            progress_bar = '<div class="w-full h-2.5 bg-[#333333] mt-2.5"></div>'

        steps_html.append(f'''
        <div class="flex-1 flex flex-col min-w-0">
            <div class="flex items-center no-wrap">
                {step_box}
                {step_label}
            </div>
            {progress_bar}
        </div>
        ''')

    step_display_num = min(currentStep + 1, 4) if currentStep >= 0 else 1
    
    # Sub-footer text
    if f.status in (FileStatus.TRANSLATING, FileStatus.SANDBOX_TESTING):
        status_text = '<span class="text-[#ffc700] font-mono font-bold">~ RUNNING AGENTIC PIPELINE</span>'
    elif f.status in (FileStatus.PASSED, FileStatus.APPROVED):
        status_text = '<span class="text-[#22c55e] font-mono font-bold">✓ PIPELINE PASSED</span>'
    elif f.status in (FileStatus.FAILED, FileStatus.REJECTED):
        status_text = '<span class="text-[#ef4444] font-mono font-bold">✗ TEST FAILED</span>'
    else:
        status_text = '<span class="text-[#999999] font-mono">READY</span>'

    footer_left = f"step {step_display_num} of 4 · attempt {curr_iter} of {max_iter} · halts after {max_iter} failed patches"

    with ui.column().classes('w-full p-0 mb-6 border-2 border-black shadow-[4px_4px_0_0_rgba(0,0,0,1)] bg-[#1e1e1e] overflow-hidden'):
        # 1. Top Yellow Banner
        ui.html(f'''
        <div class="w-full bg-[#ffc700] p-4 sm:p-5 flex items-center justify-between border-b-2 border-black flex-nowrap gap-4">
            <div class="flex flex-col min-w-0 flex-1">
                <div class="font-mono font-bold text-xs sm:text-sm tracking-widest text-black/80 uppercase truncate">
                    WORKSPACE: {html.escape(workspace_name)}
                </div>
                <div class="font-mono font-black text-2xl sm:text-3xl text-black uppercase tracking-tight truncate mt-0.5" title="{html.escape(raw_name)}">
                    {html.escape(truncated_name)}
                </div>
            </div>
            <div class="flex-shrink-0 flex items-center gap-3">
                <div class="bg-[#1e1e1e] text-white px-5 py-2 border-2 border-black flex flex-col items-center justify-center shadow-[2px_2px_0_0_rgba(0,0,0,0.4)]">
                    <div class="text-[10px] font-mono font-bold tracking-widest text-[#ffc700] uppercase">ITERATION</div>
                    <div class="text-xl sm:text-2xl font-mono font-black text-white leading-none mt-0.5">{curr_iter} / {max_iter}</div>
                </div>
            </div>
        </div>
        ''').classes('w-full')

        # 2. Bottom Dark Step & Progress Panel
        with ui.column().classes('w-full bg-[#1e1e1e] p-4 sm:p-5 gap-4'):
            # Steps row
            ui.html(f'''
            <div class="flex items-center gap-4 sm:gap-6 w-full flex-nowrap">
                {''.join(steps_html)}
            </div>
            ''').classes('w-full')

            # Footer row (with optional rerun button if show_rerun)
            with ui.row().classes('w-full items-center justify-between pt-1 text-xs font-mono flex-nowrap'):
                ui.html(f'<span class="text-[#999999] truncate">{footer_left}</span>')
                
                with ui.row().classes('items-center gap-3 flex-shrink-0'):
                    ui.html(status_text)
                    if show_rerun and rerun_callback:
                        ui.button("Re-run", on_click=rerun_callback).props('size=xs color=warning text-color=black').classes('font-black px-3 py-1 border border-black shadow-[2px_2px_0_0_rgba(0,0,0,1)]')

# ============================================================================
# MAIN CONTENT VIEWER
# ============================================================================
@ui.refreshable
def render_main():
    if not state.files or state.import_mode:
        render_welcome()
        return
        
    active_id = state.active_buffer
    if not active_id or active_id not in state.files:
        ui.label("Select a file from the sidebar.")
        return
        
    f = get_file(active_id)
    
    meta = STATUS_META.get(f.status, {"icon": "❓", "label": "UNKNOWN", "color": "gray"})
    f_color = meta["color"]

    if state.fullscreen_mode:
        _fs_titles = {
            'diff': 'Expanded Diff Viewer',
            'source': 'Expanded Source Viewer',
            'edit': 'Expanded Editor (Diff Mode)',
        }
        _fs_title = _fs_titles.get(state.fullscreen_mode, 'Expanded Viewer')

        def _close_expand():
            state.fullscreen_mode = None
            render_main.refresh()

        with ui.element('div').classes('fixed z-40 bg-[#1e1e1e]').style(
            'top:0; right:0; bottom:0; left:var(--sidebar-width, 350px); overflow:hidden;'
        ):
            with ui.row().classes('w-full justify-between items-center p-2').style('height:56px; flex-shrink:0;'):
                ui.label(_fs_title).classes('text-white text-lg font-bold')
                ui.button(icon='close', on_click=_close_expand).props('flat round text-white')

            if state.fullscreen_mode == 'diff':
                MonacoEditor(
                    value=f.ai_source,
                    original_value=f.legacy_source,
                    language=f.language,
                    readonly=True,
                    diff_mode=True,
                    primary_line=f.primary_error_line,
                    height='calc(100vh - 56px)'
                ).classes('w-full').style('height:calc(100vh - 56px); overflow:hidden;')
            elif state.fullscreen_mode == 'source':
                MonacoEditor(
                    value=f.legacy_source,
                    language=f.language,
                    readonly=True,
                    height='calc(100vh - 56px)'
                ).classes('w-full').style('height:calc(100vh - 56px); overflow:hidden;')
            elif state.fullscreen_mode == 'edit':
                current_draft = state.edit_buffer.get(active_id, f.ai_source)
                def _on_fs_change(new_val: str, fid=active_id):
                    state.edit_buffer[fid] = new_val
                    mark_dirty(fid)
                MonacoEditor(
                    value=current_draft,
                    original_value=f.legacy_source,
                    language=f.language,
                    readonly=False,
                    diff_mode=True,
                    on_change=_on_fs_change,
                    height='calc(100vh - 56px)'
                ).classes('w-full').style('height:calc(100vh - 56px); overflow:hidden;')
        return

    # Embedded LANGGRAPH TRACKER (Segmented Bar) - only shown during active translation / testing
    curr_state = state.agent_state.get(active_id, "Done" if f.status != FileStatus.QUEUED else "Idle")
    show_rerun = f.status in (FileStatus.FAILED, FileStatus.EDITED_PENDING)
    
    # Calculate simulated progress based on internal states if translating
    total_phases = len(TRANSLATING_PHASES.get(f.persona, TRANSLATING_PHASES["general"]))
    simulated_progress = int((state.thinking_phase / total_phases) * 100) if total_phases > 0 and f.status == FileStatus.TRANSLATING else 50
    
    if f.status in (FileStatus.TRANSLATING, FileStatus.SANDBOX_TESTING):
        render_segmented_status_header(
            f=f,
            current_state=curr_state,
            progress=simulated_progress,
            show_rerun=show_rerun, 
            rerun_callback=lambda: open_retest_dialog(active_id)
        )

    skip_to_action_bar = False
    
    def render_terminal(is_half=False):
        width_class = "w-full" if not is_half else "flex-1"
        margin_class = "mt-4 mb-4" if not is_half else "m-0"
        height_class = "h-[500px]" if is_half else "h-[600px]"
        with ui.column().classes(f'{width_class} {margin_class} {height_class} p-0 overflow-hidden flex flex-col flex-nowrap'):
            terminal = StructuredTerminal(
                logs=state.execution_logs.get(active_id, []),
                max_logs=1000,
                on_cleared=lambda: state.execution_logs.update({active_id: []}),
            ).classes('w-full h-full')
            state.current_terminal = terminal

    workspace_name = Path(state.project_root).name if state.project_root else "WORKSPACE"
    raw_name = f.filename if f.filename else (Path(f.path).name if f.path else "Untitled")
    truncated_name = (raw_name[:35] + "...") if len(raw_name) > 38 else raw_name

    # CARD 2: Progress / Action State
    if f.status == FileStatus.QUEUED:
        skip_to_action_bar = True
        with ui.column().classes('w-full neo-card p-0 mb-6 gap-0 overflow-hidden border-2 border-black shadow-[4px_4px_0_0_rgba(0,0,0,1)]'):
            with ui.row().classes('w-full bg-[#ffc700] p-4 sm:p-5 flex items-center justify-between border-b-2 border-black flex-nowrap gap-4'):
                ui.html(f'''
                <div class="flex flex-col min-w-0 flex-1">
                    <div class="font-mono font-bold text-xs sm:text-sm tracking-widest text-black/80 uppercase truncate">
                        WORKSPACE: {html.escape(workspace_name)}
                    </div>
                    <div class="flex items-center gap-3 mt-0.5">
                        <div class="font-mono font-black text-2xl sm:text-3xl text-black uppercase tracking-tight truncate mt-0.5" title="{html.escape(raw_name)}">
                            {html.escape(truncated_name)}
                        </div>
                        <div class="stat-pill green font-mono font-bold text-[10px]">VIEW-ONLY</div>
                    </div>
                </div>
                ''')
                with ui.row().classes('items-center gap-2 flex-shrink-0'):
                    ui.button('Fullscreen', icon='fullscreen', on_click=lambda: (setattr(state, 'fullscreen_mode', 'source'), render_main.refresh())) \
                        .props('size=sm') \
                        .classes('bg-white text-black font-mono font-black text-xs px-3.5 py-1.5 border-2 border-black shadow-[2px_2px_0_0_rgba(0,0,0,1)] hover:bg-gray-100 transition-all cursor-pointer')
            MonacoEditor(
                value=f.legacy_source,
                language=f.language,
                readonly=True,
            ).classes('w-full').style('height:725px;')
        
    elif f.status == FileStatus.TRANSLATING:
        skip_to_action_bar = True
        phases = TRANSLATING_PHASES.get(f.persona, TRANSLATING_PHASES["general"])
        i = state.thinking_phase
        
        rows_html = []
        for j, p in enumerate(phases):
            if j < i: rows_html.append(f'<div class="thinking-step step-done"><span class="step-icon">·</span>{html.escape(p)}</div>')
            elif j == i: rows_html.append(f'<div class="thinking-step step-active"><span class="step-icon">▸</span>{html.escape(p)}</div>')
            else: rows_html.append(f'<div class="thinking-step step-pending"><span class="step-icon">·</span>{html.escape(p)}</div>')
            
        with ui.row().classes('w-full items-stretch gap-4 sm:gap-6 mb-6 flex-wrap xl:flex-nowrap min-w-0'):
            with ui.column().classes('flex-1 min-w-[320px] h-[500px] neo-card neo-card-spotlight p-0 mb-0'):
                ui.html('''
                    <div class="neo-card-header">
                        <div class="header-left">
                            <div class="neo-card-title-group"><span class="thinking-pulse-dot"></span> GENERATING PATCH</div>
                            <div class="header-desc">LLM is parsing legacy code and writing modern replacement.</div>
                        </div>
                    </div>
                ''').classes('w-full')
                ui.html(f'<div class="px-6 py-4">{"".join(rows_html)}</div>').classes('w-full')
                
            render_terminal(is_half=True)
            
    elif f.status == FileStatus.SANDBOX_TESTING:
        skip_to_action_bar = True
        phases = SANDBOX_PHASES
        i = state.thinking_phase
        
        rows_html = []
        for j, p in enumerate(phases):
            if j < i: rows_html.append(f'<div class="thinking-step step-done"><span class="step-icon">·</span>{html.escape(p)}</div>')
            elif j == i: rows_html.append(f'<div class="thinking-step step-active"><span class="step-icon">▸</span>{html.escape(p)}</div>')
            else: rows_html.append(f'<div class="thinking-step step-pending"><span class="step-icon">·</span>{html.escape(p)}</div>')
            
        with ui.row().classes('w-full items-stretch gap-4 sm:gap-6 mb-6 flex-wrap xl:flex-nowrap min-w-0'):
            with ui.column().classes('flex-1 min-w-[320px] h-[500px] neo-card neo-card-spotlight p-0 mb-0'):
                ui.html('''
                    <div class="neo-card-header">
                        <div class="header-left">
                            <div class="neo-card-title-group"><span class="thinking-pulse-dot"></span> SANDBOX EXECUTION</div>
                            <div class="header-desc">Executing containerized test suite against generated patch.</div>
                        </div>
                    </div>
                ''').classes('w-full')
                ui.html(f'<div class="px-6 py-4">{"".join(rows_html)}</div>').classes('w-full')
                
            render_terminal(is_half=True)

    # Monaco Diff Viewer / Edit Mode
    if not skip_to_action_bar and f.status not in (FileStatus.TRANSLATING, FileStatus.SANDBOX_TESTING):
        diff_state_val = state.diff_state.get(active_id, "readonly")
        if diff_state_val == "editing":
            with ui.column().classes('w-full neo-card p-0 mb-6 gap-0 overflow-hidden border-2 border-black shadow-[4px_4px_0_0_rgba(0,0,0,1)]'):
                with ui.row().classes('w-full bg-[#ffc700] p-4 sm:p-5 flex items-center justify-between border-b-2 border-black flex-nowrap gap-4'):
                    ui.html(f'''
                    <div class="flex flex-col min-w-0 flex-1">
                        <div class="font-mono font-bold text-xs sm:text-sm tracking-widest text-black/80 uppercase truncate">
                            WORKSPACE: {html.escape(workspace_name)}
                        </div>
                        <div class="font-mono font-black text-2xl sm:text-3xl text-black uppercase tracking-tight truncate mt-0.5" title="{html.escape(raw_name)}">
                            {html.escape(truncated_name)}
                        </div>
                    </div>
                    ''')
                    with ui.row().classes('items-center gap-2 flex-shrink-0'):
                        ui.button('Cancel', icon='close', on_click=lambda: (state.diff_state.update({active_id: "readonly"}), refresh_all())) \
                            .props('size=sm') \
                            .classes('bg-white text-black font-mono font-black text-xs px-3.5 py-1.5 border-2 border-black shadow-[2px_2px_0_0_rgba(0,0,0,1)] hover:bg-gray-100 transition-all cursor-pointer')

                        ui.button('Save & Retest', icon='save', on_click=lambda: (save_and_retest(active_id, state.edit_buffer.get(active_id, f.ai_source)), refresh_all())) \
                            .props('size=sm') \
                            .classes('bg-black text-white font-mono font-black text-xs px-3.5 py-1.5 border-2 border-black shadow-[2px_2px_0_0_rgba(0,0,0,1)] hover:bg-[#22c55e] hover:text-black transition-all cursor-pointer')

                        ui.button('Fullscreen', icon='fullscreen', on_click=lambda: (setattr(state, 'fullscreen_mode', 'edit'), render_main.refresh())) \
                            .props('size=sm') \
                            .classes('bg-white text-black font-mono font-black text-xs px-3.5 py-1.5 border-2 border-black shadow-[2px_2px_0_0_rgba(0,0,0,1)] hover:bg-gray-100 transition-all cursor-pointer')

                current_draft = state.edit_buffer.get(active_id, f.ai_source)

                def on_monaco_change(new_val: str, fid=active_id):
                    state.edit_buffer[fid] = new_val
                    mark_dirty(fid)

                MonacoEditor(
                    value=current_draft,
                    original_value=f.legacy_source,
                    language=f.language,
                    readonly=False,
                    diff_mode=True,
                    on_change=on_monaco_change,
                ).classes('w-full').style('height:725px;')
        else:
            with ui.column().classes('w-full neo-card p-0 mb-6 gap-0 overflow-hidden border-2 border-black shadow-[4px_4px_0_0_rgba(0,0,0,1)]'):
                with ui.row().classes('w-full bg-[#ffc700] p-4 sm:p-5 flex items-center justify-between border-b-2 border-black flex-nowrap gap-4'):
                    ui.html(f'''
                    <div class="flex flex-col min-w-0 flex-1">
                        <div class="font-mono font-bold text-xs sm:text-sm tracking-widest text-black/80 uppercase truncate">
                            WORKSPACE: {html.escape(workspace_name)}
                        </div>
                        <div class="flex items-center gap-3 mt-0.5">
                            <div class="font-mono font-black text-2xl sm:text-3xl text-black uppercase tracking-tight truncate mt-0.5" title="{html.escape(raw_name)}">
                                {html.escape(truncated_name)}
                            </div>
                            <div class="stat-pill green font-mono font-bold text-[10px]">VIEW-ONLY</div>
                        </div>
                    </div>
                    ''')
                    with ui.row().classes('items-center gap-2 flex-shrink-0'):
                        ui.button('Edit', icon='edit', on_click=lambda: (start_edit(active_id), render_main.refresh())) \
                            .props('size=sm') \
                            .classes('bg-white text-black font-mono font-black text-xs px-3.5 py-1.5 border-2 border-black shadow-[2px_2px_0_0_rgba(0,0,0,1)] hover:bg-[#ff5fd1] hover:text-white transition-all cursor-pointer')

                        ui.button('Retest', icon='replay', on_click=lambda: open_retest_dialog(active_id)) \
                            .props('size=sm') \
                            .classes('bg-black text-white font-mono font-black text-xs px-3.5 py-1.5 border-2 border-black shadow-[2px_2px_0_0_rgba(0,0,0,1)] hover:bg-[#22c55e] hover:text-black transition-all cursor-pointer')

                        ui.button('Fullscreen', icon='fullscreen', on_click=lambda: (setattr(state, 'fullscreen_mode', 'diff'), render_main.refresh())) \
                            .props('size=sm') \
                            .classes('bg-white text-black font-mono font-black text-xs px-3.5 py-1.5 border-2 border-black shadow-[2px_2px_0_0_rgba(0,0,0,1)] hover:bg-gray-100 transition-all cursor-pointer')

                MonacoEditor(
                    value=f.ai_source,
                    original_value=f.legacy_source,
                    language=f.language,
                    readonly=True,
                    diff_mode=True,
                    primary_line=f.primary_error_line,
                ).classes('w-full').style('height:725px;')

        if f.raw_traceback:
            frames = parse_traceback(f.raw_traceback, f.language, f.filename)
            groups = group_frames_for_disclosure(frames)
            
            show_full = state.show_full_trace.get(active_id, False)
            with ui.row().classes('w-full justify-end mt-[-1rem] mb-2 gap-2'):
                if f.status == FileStatus.FAILED and diff_state_val != "editing":
                    ui.button("Edit AI code", icon='edit', on_click=lambda: (start_edit(active_id), render_main.refresh())).props('color=blue size=sm').classes('w-44 font-bold')
                
                btn_label = "Collapse trace" if show_full else "Show full trace"
                ui.button(btn_label, on_click=lambda: (state.show_full_trace.update({active_id: not show_full}), render_main.refresh())).props('color=blue size=sm').classes('w-44 font-bold')

            with ui.column().classes('w-full neo-card p-0 mb-6'):
                ui.html("""
                <div class="neo-card-header compact-header">
                    <div class="header-left">
                        <div class="neo-card-title-group">TRACEBACK CONSOLE</div>
                        <div class="header-desc">Sandbox execution failed. See actionable frames above.</div>
                    </div>
                    <div class="stat-pill red">ERROR</div>
                </div>
                """).classes('w-full')
                
                with ui.column().classes('w-full p-4 gap-2 bg-gray-100 rounded'):
                    for gi, group in enumerate(groups):
                        if group["type"] == "actionable":
                            fr = group["frame"]
                            with ui.row().classes('w-full items-center justify-between trace-frame-row m-0'):
                                ui.html(f'▸ {fr.file_path.split("/")[-1]} : line {fr.line_number} : {fr.function_name}()')
                                ui.button("Jump ↑", on_click=lambda ln=fr.line_number: ui.notify(f"Jumped to line {ln} (simulated)")).props('flat size=sm text-color=black')
                        else:
                            key = f"{active_id}__{gi}"
                            label = f'▶ {group["count"]} internal frame(s) hidden'
                            if state.show_full_trace.get(active_id, False):
                                for nf in group["frames"]: 
                                    ui.html(f'<div class="trace-noise-row">　 {nf.file_path.split("/")[-1]} : line {nf.line_number} : {nf.function_name}()</div>')
                            else:
                                with ui.row().classes('w-full items-center justify-between'):
                                    ui.html(f'<div class="trace-noise-row m-0 p-0">{label}</div>')
                                    ui.button("Expand", on_click=lambda k=key: (state.trace_expanded.update({k: True}), render_main.refresh())).props('flat size=sm text-color=gray-600')
                                
                                if state.trace_expanded.get(key, False):
                                    for nf in group["frames"]: 
                                        ui.html(f'<div class="trace-noise-row">　 {nf.file_path.split("/")[-1]} : line {nf.line_number} : {nf.function_name}()</div>')

    # TERMINAL UI (For states other than TRANSLATING/SANDBOX where it's already rendered inline)
    if active_id in state.execution_logs and f.status not in (FileStatus.TRANSLATING, FileStatus.SANDBOX_TESTING):
        render_terminal(is_half=False)

    if f.status == FileStatus.REJECTED and f.rejection_note:
        ui.label(f"🚫 Rejection note: {f.rejection_note}").classes('text-gray-400 mt-8 font-bold')

    # Whitespace spacer below the terminal to prevent overlap with floating action bar
    ui.element('div').classes('w-full h-[60px] flex-shrink-0')

    # Embedded the Action Center directly in the page flow
    render_action_bar()

# ============================================================================
# ACTION BAR (Embedded)
# ============================================================================
def render_action_bar():
    if not state.files or not state.active_buffer: return
    active_id = state.active_buffer
    if active_id not in state.files: return
    
    f = get_file(active_id)
    
    pill_classes = 'bg-white px-6 py-3 rounded-full shadow-[0_8px_30px_rgb(0,0,0,0.12)] items-center gap-4'
    if f.status == FileStatus.QUEUED and not getattr(state, 'is_thinking', False):
        pill_classes += ' animate-action-float'
        
    with ui.element('div').classes('fixed z-50').style('bottom: 24px; left: calc(50% + var(--sidebar-width, 350px) / 2); transform: translateX(-50%);'):
        with ui.row().classes(pill_classes):
            if getattr(state, 'is_thinking', False):
                with ui.row().classes('items-center gap-4'):
                    ui.html('<div class="thinking-pulse-dot"></div><span style="color: var(--text-primary); font-weight: 500;">Executing...</span>')
                    
                    def cancel_execution():
                        state.is_thinking = False
                        state.agent_state[active_id] = "Done"
                        if active_id and active_id in state.files:
                            f_to_cancel = state.files[active_id]
                            if f_to_cancel.status in (FileStatus.TRANSLATING, FileStatus.SANDBOX_TESTING):
                                f_to_cancel.status = FileStatus.FAILED
                        show_alert("Execution cancelled by user. Bypassing System Cleanup as per state diagram.", alert_type='warning')
                        push_log(active_id, "[System] Execution manually aborted by QA reviewer.")
                        refresh_all()
                        
                    ui.button("Cancel / Timeout", on_click=cancel_execution).props('flat size=sm color=negative').classes('action-pill-btn')
            else:
                approve_eligible = f.status == FileStatus.PASSED
                reject_eligible = f.status in (FileStatus.FAILED, FileStatus.PASSED, FileStatus.EDITED_PENDING)
                
                btn1 = ui.button("Approve", on_click=lambda: (approve_file(active_id), refresh_all())).props('unelevated rounded color=positive' if approve_eligible else 'flat rounded color=grey-8').classes('action-pill-btn')
                if not approve_eligible: btn1.disable()
                
                if f.status == FileStatus.QUEUED:
                    btn2 = ui.button("Start AI Translation", on_click=lambda: run_translation_simulation(active_id)).props('unelevated rounded color=blue').classes('action-pill-btn')
                    if state.is_thinking: btn2.disable()
                else:
                    if state.diff_state.get(active_id) == "editing":
                        ui.button("Cancel Edit", on_click=lambda: (state.diff_state.update({active_id: "readonly"}), refresh_all())).props('flat rounded color=grey-8').classes('action-pill-btn')
                        ui.button("Save & Re-test", icon='save', on_click=lambda: (save_and_retest(active_id, state.edit_buffer.get(active_id, f.ai_source)), refresh_all())).props('unelevated rounded color=primary').classes('action-pill-btn')
                    else:
                        ui.button("Re-test", icon='replay', on_click=lambda: open_retest_dialog(active_id)).props('unelevated rounded color=blue').classes('action-pill-btn')
                        btn4 = ui.button("Reject", on_click=lambda: open_reject_dialog(active_id)).props('unelevated rounded color=negative' if reject_eligible else 'flat rounded color=grey-8').classes('action-pill-btn')
                        if not reject_eligible: btn4.disable()

# ============================================================================
# MAIN PAGE
# ============================================================================
@ui.page('/')
def index():
    ui.add_head_html(get_css())
    
    ui.colors(primary='#ff5fd1', secondary='#fdfbf7', accent='#f5c518', dark='#101010', positive='#00c853', negative='#ff3333', info='#33ccff', warning='#f5c518')
    
    is_workspace_active = bool(state.files and not state.import_mode)
    drawer = ui.left_drawer(value=is_workspace_active).props(
        'width=350 behavior="desktop" :breakpoint="0" no-swipe-open no-swipe-close bordered'
    ).classes('relative border-r border-gray-200 overflow-visible')
    state.drawer = drawer
    
    if not is_workspace_active:
        drawer.hide()
        
    with drawer:
        render_sidebar()
        
    with ui.column().classes('w-full h-full p-4 sm:p-6 lg:p-8 max-w-[1750px] mx-auto min-w-0 box-border'):
        render_main()


if __name__ in {'__main__', '__mp_main__'}:
    ui.run(title="RevivoAI", favicon="🔬", dark=False, port=8501, storage_secret='revivo-ai-secret', reload=False)