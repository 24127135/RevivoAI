import asyncio
import json
import html
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

# Import from backend
from backend.mcp_client import MCPClient
from backend.models import FileStatus, STATUS_META, WARNING_STATUSES, ProjectFile
from backend.logic import (
    parse_traceback, compute_anchors, group_frames_for_disclosure,
)
from backend.seed import build_seed_files
from backend.import_utils import import_from_uploads, import_local_project
from backend.session_handler import SessionHandler

# Import from frontend
from frontend.styles import get_css
from frontend.components import TRANSLATING_PHASES, SANDBOX_PHASES
from frontend.monaco_editor import MonacoEditor

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
        self.execution_logs: dict[str, list[str]] = {} 
        self.current_terminal = None
        self.fullscreen_mode: str | None = None  # None, 'diff', 'source', 'edit_legacy', 'edit_ai'

state = AppState()

async def load_demo_project():
    """Loads seed data. Everything starts as QUEUED now."""
    files = build_seed_files()
    state.files = {f.file_id: f for f in files}
    state.active_buffer = files[0].file_id
    state.import_mode = None
    state.session_handler = SessionHandler()
    session_id = await state.session_handler.initialize_session(user_id=str(uuid.uuid4()))
    state.session_id = session_id
    if session_id:
        background_tasks.create(websocket_listener(session_id))
    refresh_all()

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
                for f in imported_files:
                    state.files[f.file_id] = f
                state.active_buffer = imported_files[0].file_id
                state.project_root = folder
                state.import_mode = None
                
                # Asynchronously pass the path to SessionHandler
                state.session_handler = SessionHandler()
                session_id = await state.session_handler.initialize_session(user_id=str(uuid.uuid4()))
                state.session_id = session_id
                if session_id:
                    background_tasks.create(websocket_listener(session_id))
                
                # Asynchronously pass the path to MCPClient
                state.mcp_client = MCPClient(server_uri="local://revivoai", allowed_root_path=folder)
                async def connect_mcp():
                    await asyncio.sleep(0.1) # Simulate async delay
                    state.mcp_client.connect()
                asyncio.create_task(connect_mcp())
                
                refresh_all()
            else:
                show_alert("No readable source files found in that directory.", alert_type='warning')
        except ValueError:
            show_alert("Directory not found. Check the path and try again.", alert_type='negative')

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
    except RuntimeError:
        # The UI element was destroyed before the notification could render.
        # This is safe to ignore.
        pass

def push_log(file_id: str, message: str):
    if file_id not in state.execution_logs:
        state.execution_logs[file_id] = []
    timestamp = time.strftime('%H:%M:%S')
    log_line = f"[{timestamp}] {message}"
    state.execution_logs[file_id].append(log_line)
    
    if state.active_buffer == file_id and state.current_terminal:
        try:
            state.current_terminal.push(log_line)
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

def set_active_buffer(file_id: str): 
    state.active_buffer = file_id
    state.fullscreen_mode = None
    refresh_all()

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

    # FILES-mode imports have no directory root — fall back to a local output folder.
    root = state.project_root or str(Path.cwd() / "revivo_workspace")
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
    asyncio.create_task(simulate_sandbox(file_id))

def refresh_all():
    if getattr(state, 'drawer', None) is not None:
        if state.files and not state.import_mode:
            state.drawer.set_visibility(True)
            state.drawer.show()  # <-- Forces the layout to expand
        else:
            state.drawer.set_visibility(False)
            state.drawer.hide()  # <-- Reclaims the sidebar space
            
    render_sidebar.refresh()
    render_main.refresh()

def build_orchestrator_payload(file_id: str) -> dict:
    f = get_file(file_id)
    return {
        "session_id": state.session_id,
        "target_file": f,
        "file_path": f.path,
        "workspace_dir": state.project_root,
        "system_prompt": "",
        "persona": f.persona,
        "patched_code": "",
        "iteration_count": 0,
        "max_iterations": 3,
    }


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

                if not file_id:
                    continue

                if isinstance(payload, dict):
                    if "docker_exit_code" in payload:
                        state.agent_state[file_id] = payload.get("current_node", state.agent_state.get(file_id, "Done"))
                    if "traceback_log" in payload and payload["traceback_log"]:
                        push_log(file_id, str(payload["traceback_log"]))
                    if "patched_code" in payload and payload["patched_code"]:
                        state.files[file_id].ai_source = payload["patched_code"]
                    if "docker_exit_code" in payload:
                        state.files[file_id].status = FileStatus.PASSED if payload["docker_exit_code"] == 0 else FileStatus.FAILED
                        if payload["docker_exit_code"] != 0:
                            state.files[file_id].raw_traceback = str(payload.get("traceback_log", ""))

                render_sidebar.refresh()
                render_main.refresh()
    except Exception as exc:
        if session_id:
            push_log(state.active_buffer or "", f"[WebSocket] Listener stopped for session {session_id}: {exc}")


async def _trigger_backend_run(file_id: str):
    if not state.session_id:
        raise RuntimeError("Session has not been initialized.")

    payload = build_orchestrator_payload(file_id)

    target_file = payload.get("target_file")
    if target_file is not None:
        if hasattr(target_file, "model_dump"):
            payload["target_file"] = target_file.model_dump(mode="json")
        elif hasattr(target_file, "dict"):
            payload["target_file"] = target_file.dict()
        elif is_dataclass(target_file):
            payload["target_file"] = asdict(target_file)
        else:
            payload["target_file"] = vars(target_file)

    async with httpx.AsyncClient() as client:
        await client.post(f"http://localhost:8000/api/run/{state.session_id}", json=payload)

# ============================================================================
# ASYNC SIMULATIONS (LANGGRAPH NODES)
# ============================================================================
async def simulate_translation(file_id: str):
    push_log(file_id, f"Initializing AgentState with workspace: {state.project_root}")
    await _trigger_backend_run(file_id)

async def simulate_sandbox(file_id: str, is_chained: bool = False):
    push_log(file_id, f"Initializing AgentState with workspace: {state.project_root}")
    await _trigger_backend_run(file_id)

def run_translation_simulation(file_id: str):
    background_tasks.create(simulate_translation(file_id))

def run_sandbox_simulation(file_id: str):
    background_tasks.create(simulate_sandbox(file_id))

# ============================================================================
# WELCOME SCREEN
# ============================================================================
def render_welcome():
    # Forceful CSS injected directly into the head to override Quasar defaults
    ui.add_css('''
        body .welcome-import-card {
            background-color: #ffffff !important;
            transition: all 0.2s ease-in-out !important;
        }
        body .welcome-import-card:hover {
            background-color: #3b82f6 !important; /* Blue background on hover */
        }
        body .welcome-import-card:hover, 
        body .welcome-import-card:hover * {
            color: #ffffff !important; /* Force all internal text to white on hover */
        }
    ''')

    with ui.column().classes('w-full items-center justify-center pt-20 pb-10'):
        ui.html('''
            <div class="welcome-screen">
                <div class="welcome-kicker">⚙️ LEGACY CODE MODERNIZATION TOOL</div>
                <div class="welcome-title">REVIVO<span class="welcome-title-accent">AI</span></div>
                <div class="welcome-desc">
                    Turn brittle legacy systems into modern, sandbox-verified code.<br>
                    AI drafts the patch. The sandbox proves it works. You stay in control.
                </div>
            </div>
        ''')
        
        with ui.row().classes('w-full max-w-5xl justify-center gap-8 px-4'):
            if state.import_mode == "FILES":
                with ui.column().classes('w-full max-w-lg'):
                    ui.markdown("### Upload Files")
                    async def handle_upload(e: events.UploadEventArguments):
                        imported_files = await import_from_uploads([e])
                        if imported_files:
                            for f in imported_files:
                                state.files[f.file_id] = f
                            state.active_buffer = imported_files[0].file_id
                            if not state.project_root:
                                state.project_root = str(Path.cwd() / "revivo_workspace")
                                os.makedirs(state.project_root, exist_ok=True)

                            # Ensure uploaded files are tied to an active backend session.
                            if not state.session_handler or not state.session_id:
                                state.session_handler = SessionHandler()
                                session_id = await state.session_handler.initialize_session(user_id="ea3491cd-7390-4c8f-a420-e15aa731b29a")
                                state.session_id = session_id
                                if session_id:
                                    background_tasks.create(websocket_listener(session_id))

                            # Ensure MCP client is available for later file write operations.
                            if not state.mcp_client and state.project_root:
                                state.mcp_client = MCPClient(server_uri="local://revivoai", allowed_root_path=state.project_root)

                                async def connect_mcp_upload():
                                    await asyncio.sleep(0.1)
                                    state.mcp_client.connect()

                                asyncio.create_task(connect_mcp_upload())

                            state.import_mode = None
                            show_alert("Upload complete. You can now start AI translation.", alert_type='positive')
                            refresh_all()
                        else:
                            show_alert("Upload failed or file type is unsupported.", alert_type='warning')
                    ui.upload(on_upload=handle_upload, multiple=True, auto_upload=True).classes('w-full')
                    with ui.row().classes('w-full gap-4 mt-4'):
                        ui.button("Cancel", on_click=lambda: (setattr(state, 'import_mode', None), refresh_all())).classes('flex-1')
                        
            else:
                with ui.column().classes('w-full items-center pt-16'):
                    with ui.row().classes('w-full max-w-7xl justify-center items-stretch gap-8 mb-8'):
                        
                        # Added `welcome-import-card` for our aggressive CSS override target
                        with ui.card().classes(
                            'welcome-import-card flex-1 cursor-pointer flex flex-col items-center justify-center text-center '
                            'border-4 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] p-8'
                        ) as card1:
                            ui.html('<div class="welcome-import-title">IMPORT FILES</div><div class="welcome-import-desc">Select individual source files to translate. Best for targeting a few specific files.</div>')
                            card1.on('click', lambda: (setattr(state, 'import_mode', "FILES"), refresh_all()))
                            
                        with ui.card().classes(
                            'welcome-import-card flex-1 cursor-pointer flex flex-col items-center justify-center text-center '
                            'border-4 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] p-8'
                        ) as card2:
                            ui.html('<div class="welcome-import-title">IMPORT PROJECT</div><div class="welcome-import-desc">Scan a local directory tree for source files. Best for translating an entire codebase.</div>')
                            card2.on('click', handle_native_import_project)
                            
                    ui.html('<div class="text-gray-400 font-bold mb-8">--- OR ---</div>')
                    
                    # Passed Quasar's native color prop `color=blue` 
                    ui.button("Load Demo Project (Mock Data)", on_click=load_demo_project).props('color=blue').classes(
                        'w-full max-w-lg mt-8 border-4 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] font-black py-4 text-lg'
                    )

# ============================================================================
# SIDEBAR
# ============================================================================
@ui.refreshable
def render_sidebar():
    with ui.column().classes('w-full h-full p-0 m-0 bg-white'):
        
        # 1. FIXED HEADER
        with ui.row().classes('w-full p-4 pb-2 gap-2 items-center justify-between flex-nowrap'):
            ui.html('<div class="sidebar-brand text-2xl font-black truncate tracking-tighter">REVIVOAI</div>')
            
            with ui.column().classes('gap-1 items-stretch flex-shrink-0 w-24'):
                btn_cls = (
                    'group relative bg-white py-1.5 px-3 text-xs font-semibold text-black text-center cursor-pointer '
                    'after:absolute after:inset-x-0 after:bottom-0 after:h-[2px] after:bg-black '
                    'transition-all duration-200 after:transition-all after:duration-200 '
                    'hover:after:h-full focus:ring-2 focus:ring-yellow-300 focus:outline-0 border border-gray-300 hover:border-black'
                )
                
                f_btn = ui.element('div').classes(btn_cls).on('click', lambda: (setattr(state, 'import_mode', "FILES"), refresh_all()))
                with f_btn:
                    ui.label('+ Files').classes('relative z-10 pointer-events-none block group-hover:text-white transition-colors duration-200')
                    
                p_btn = ui.element('div').classes(btn_cls).on('click', handle_native_import_project)
                with p_btn:
                    ui.label('+ Project').classes('relative z-10 pointer-events-none block group-hover:text-white transition-colors duration-200')
            

        # 2. SCROLLABLE FILE TREE
        with ui.scroll_area().classes('flex-1 w-full px-2 mt-2'):
            with ui.column().classes('w-full gap-1 pb-4'):
                
                def matches_filters(f: ProjectFile) -> bool:
                    fname = str(f.filename).lower() if f.filename else ""
                    if state.search_query and state.search_query.lower() not in fname: 
                        return False
                    status_val = getattr(f.status, 'value', str(f.status))
                    if state.status_filter != "All" and status_val != state.status_filter: 
                        return False
                    folder_name = str(f.folder) if f.folder else "Root"
                    if state.module_filter != "All" and folder_name != state.module_filter: 
                        return False
                    return True

                for folder, folder_files in folder_tree().items():
                    visible = [f for f in folder_files if matches_filters(f)]
                    if not visible: continue
                    
                    warn_count = folder_has_warning(folder_files)
                    warn_badge = f'&nbsp;&nbsp;<span class="warn-badge"> ⚠️ </span>' if warn_count else ""
                    
                    is_expanded = folder in state.expanded_folders
                    icon = "▼" if is_expanded else "▶"
                    
                    with ui.column().classes('w-full mb-1'):
                        with ui.row().classes('w-full items-center cursor-pointer sidebar-folder') as folder_row:
                            ui.html(f'{icon}&nbsp; 📂 {folder}{warn_badge}')
                            def toggle_folder(e, fld=folder):
                                if fld in state.expanded_folders: state.expanded_folders.remove(fld)
                                else: state.expanded_folders.add(fld)
                                render_sidebar.refresh()
                            folder_row.on('click', toggle_folder)
                        
                        if is_expanded:
                            with ui.column().classes('w-full pl-2 gap-0'):
                                for i, f in enumerate(visible):
                                    meta = STATUS_META.get(f.status, {"icon": "❓", "label": "UNKNOWN", "color": "gray"})
                                    is_active = state.active_buffer == f.file_id
                                    
                                    prefix = "└─" if i == len(visible)-1 else "├─"
                                    button_label = f'{prefix} {meta["icon"]} {f.filename}'
                                    
                                    bg_props = 'unelevated color="grey-4"' if is_active else 'flat'
                                    text_color = 'black' if is_active else 'grey-8'
                                    font_weight = 'font-bold' if is_active else 'font-normal'
                                    
                                    with ui.row().classes('w-full items-center wrap-none gap-0'):
                                        btn = ui.button(button_label, on_click=lambda e, fid=f.file_id: set_active_buffer(fid))
                                        btn.props(f'{bg_props} align="left" text-color="{text_color}" no-caps dense').classes(f'flex-1 truncate {font_weight}')

        # 3. FIXED FOOTER
        with ui.column().classes('w-full p-4 border-t border-gray-200 bg-gray-50 mt-auto'):
            with ui.dialog() as confirm_dialog, ui.card():
                ui.label('Clear Workspace?').classes('text-lg font-bold')
                ui.label('This will remove all files from the current session. Unsaved changes will be lost.')
                with ui.row().classes('w-full justify-end mt-4'):
                    ui.button('Cancel', on_click=confirm_dialog.close).props('flat')
                    def do_clear():
                        state.files.clear()
                        state.active_buffer = None
                        state.project_root = None
                        state.import_mode = None
                        confirm_dialog.close()
                        refresh_all()
                    ui.button('Clear', on_click=do_clear).props('color=negative')

            btn = ui.element('div').classes(
                'group relative w-full bg-white px-4 py-2 font-semibold text-red-500 text-center cursor-pointer '
                'after:absolute after:inset-x-0 after:bottom-0 after:h-[2px] after:bg-red-500 '
                'transition-all duration-200 after:transition-all after:duration-200 '
                'hover:after:h-full focus:ring-2 focus:ring-red-300 focus:outline-0 border border-gray-300 hover:border-red-500 mt-2'
            ).on('click', confirm_dialog.open)
            with btn:
                ui.label('🗑️ Clear Workspace').classes('relative z-10 pointer-events-none block group-hover:text-black transition-colors duration-200')

# ============================================================================
# STATE MACHINE TRACKER (UI COMPONENT)
# ============================================================================
def render_segmented_status_header(f: ProjectFile, current_state: str, progress: int = 50, show_rerun: bool = False, rerun_callback=None):
    nodes = ["Analyze", "Propose", "Execute", "Evaluate"]
    
    if current_state in nodes:
        currentStep = nodes.index(current_state)
    elif current_state == "Done":
        currentStep = 4
    else:
        currentStep = -1

    if f.status in (FileStatus.QUEUED, FileStatus.EDITED_PENDING):
        theme_color = "#d1d5db"
        text_color = "var(--neo-black)"
        badge_label = "QUEUED" if f.status == FileStatus.QUEUED else "EDITED"
    elif f.status in (FileStatus.TRANSLATING, FileStatus.SANDBOX_TESTING):
        theme_color = "var(--neo-green)"
        text_color = "var(--neo-black)"
        badge_label = "RUNNING"
    elif f.status in (FileStatus.PASSED, FileStatus.APPROVED):
        theme_color = "var(--neo-green)"
        text_color = "var(--neo-black)"
        badge_label = "DONE"
    elif f.status in (FileStatus.FAILED, FileStatus.REJECTED):
        theme_color = "var(--neo-red)"
        text_color = "var(--neo-white)"
        badge_label = "FAILED"
    else:
        theme_color = "#d1d5db"
        text_color = "var(--neo-black)"
        badge_label = "UNKNOWN"

    segments_html = ""
    for i, node in enumerate(nodes):
        if i < currentStep:
            # Done
            dot = f'<div class="w-2 h-2 rounded-full mx-auto" style="background-color: {theme_color}; border: 1.5px solid var(--neo-black);"></div>'
            label_class = "font-bold text-black"
            fill = 100
        elif i == currentStep:
            # Active
            dot = f'<div class="w-2 h-2 rounded-full mx-auto" style="background-color: {theme_color}; border: 1.5px solid var(--neo-black);"></div>'
            label_class = "font-bold text-black"
            fill = progress
        else:
            # Pending
            dot = ""
            label_class = "font-medium text-gray-400"
            fill = 0
            
        segments_html += f'''
        <div class="flex flex-col flex-1 relative">
            <div class="h-2 mb-2">{dot}</div>
            <div class="text-center font-mono text-sm uppercase mb-2 {label_class}">{node}</div>
            <div class="w-full h-4 overflow-hidden bg-gray-200" style="border: 2px solid var(--neo-black); border-radius: 6px;">
                <div class="h-full transition-all duration-300" style="background-color: {theme_color}; width: {fill}%; border-right: 2px solid var(--neo-black);"></div>
            </div>
        </div>
        '''

    with ui.column().classes('w-full border-[3px] border-black bg-[#fafafa] p-4 mb-6 gap-0'):
        if show_rerun and rerun_callback:
            with ui.row().classes('w-full justify-end items-center mb-2 flex-nowrap'):
                ui.button("Re-run", on_click=rerun_callback).props('outline size=sm').classes('mr-1')
        
        ui.html(f'''
        <div class="flex w-full gap-4 mt-2">
            {segments_html}
        </div>
        ''').classes('w-full')

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
            f'top:0; right:0; bottom:0; left:{SIDEBAR_WIDTH_PX}px; overflow:hidden;'
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

    # Embedded LANGGRAPH TRACKER (Segmented Bar)
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
            rerun_callback=lambda: run_sandbox_simulation(active_id)
        )

    skip_to_action_bar = False
    
    def render_terminal(is_half=False):
        width_class = "w-full" if not is_half else "flex-1"
        margin_class = "mt-2" if not is_half else "m-0"
        height_class = "h-[500px]" if is_half else "h-[600px]"
        with ui.column().classes(f'{width_class} {margin_class} {height_class} border-4 border-black shadow-[4px_4px_0_0] shadow-black bg-gray-900 rounded-lg overflow-hidden flex flex-col flex-nowrap'):
            with ui.row().classes('w-full bg-black px-4 py-2 items-center justify-between border-b-2 border-gray-700 flex-shrink-0 flex-nowrap'):
                ui.label("▶ LANGGRAPH EXECUTION TERMINAL").classes('text-green-400 font-mono text-sm font-bold truncate')
                ui.label("STDOUT / STDERR").classes('text-gray-500 font-mono text-xs flex-shrink-0')
                
            terminal = ui.log(max_lines=1000).classes('w-full flex-1 bg-gray-900 text-green-400 p-4 font-mono text-xs outline-none border-none min-h-0 overflow-y-auto')
            state.current_terminal = terminal
            for line in state.execution_logs.get(active_id, []):
                terminal.push(line)

    # CARD 2: Progress / Action State
    if f.status == FileStatus.QUEUED:
        skip_to_action_bar = True
        with ui.column().classes('w-full neo-card neo-card-spotlight p-0 mb-6 overflow-hidden'):
            with ui.row().classes('neo-card-header compact-header w-full justify-between items-center'):
                ui.html('''
                <div class="flex items-center">
                    <div class="header-left">
                        <div class="neo-card-title-group">LEGACY SOURCE CODE</div>
                    </div>
                    <div class="stat-pill green">VIEWER</div>
                </div>
                ''')
                ui.button('Expand', icon='fullscreen', on_click=lambda: (setattr(state, 'fullscreen_mode', 'source'), render_main.refresh())).props('flat dense size=sm').classes('font-bold')
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
            
        with ui.row().classes('w-full items-stretch gap-6 mb-6 flex-nowrap'):
            with ui.column().classes('flex-1 h-[500px] neo-card neo-card-spotlight p-0 mb-0'):
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
            
        with ui.row().classes('w-full items-stretch gap-6 mb-6 flex-nowrap'):
            with ui.column().classes('flex-1 h-[500px] neo-card neo-card-spotlight p-0 mb-0'):
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
            with ui.column().classes('w-full neo-card neo-card-spotlight p-0 mb-6 overflow-hidden'):
                with ui.row().classes('neo-card-header compact-header w-full justify-between items-center'):
                    ui.html('''
                    <div class="flex items-center">
                        <div class="header-left">
                            <div class="neo-card-title-group">MANUAL EDIT MODE</div>
                            <div class="header-desc">Manually override AI-generated patch before re-testing.</div>
                        </div>
                        <div class="stat-pill yellow">EDIT</div>
                    </div>
                    ''')
                    ui.button('Expand', icon='fullscreen', on_click=lambda: (setattr(state, 'fullscreen_mode', 'edit'), render_main.refresh())).props('flat dense size=sm').classes('font-bold')
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
                ).classes('w-full').style('height:710px; border-top: 3px solid var(--neo-black);')
                
                with ui.row().classes('w-full p-4 gap-4 justify-end bg-white').style('border-top: 3px solid var(--neo-black);'):
                    ui.button("Cancel", on_click=lambda: (state.diff_state.update({active_id: "readonly"}), refresh_all())).props('outline')
                    ui.button("💾 Save & Re-test", on_click=lambda: (save_and_retest(active_id, state.edit_buffer.get(active_id, f.ai_source)), refresh_all())).props('color=primary')
        else:
            with ui.column().classes('w-full neo-card neo-card-spotlight p-0 mb-6 overflow-hidden'):
                with ui.row().classes('neo-card-header compact-header w-full justify-between items-center'):
                    ui.html('''
                    <div class="flex items-center">
                        <div class="header-left">
                            <div class="neo-card-title-group">DIFF VIEWER</div>
                        </div>
                        <div class="stat-pill blue">DIFF</div>
                    </div>
                    ''')
                    ui.button('Expand', icon='fullscreen', on_click=lambda: (setattr(state, 'fullscreen_mode', 'diff'), render_main.refresh())).props('flat dense size=sm').classes('font-bold')

                MonacoEditor(
                    value=f.ai_source,
                    original_value=f.legacy_source,
                    language=f.language,
                    readonly=True,
                    diff_mode=True,
                    primary_line=f.primary_error_line,
                ).classes('w-full').style('height:710px; border-top: 3px solid var(--neo-black);')

        if f.raw_traceback:
            frames = parse_traceback(f.raw_traceback, f.language, f.filename)
            groups = group_frames_for_disclosure(frames)
            
            show_full = state.show_full_trace.get(active_id, False)
            with ui.row().classes('w-full justify-end mt-[-1rem] mb-2 gap-2'):
                if f.status == FileStatus.FAILED and diff_state_val != "editing":
                    ui.button("✏️ Edit AI code", on_click=lambda: (start_edit(active_id), render_main.refresh())).props('color=blue').classes('w-48')
                
                btn_label = "Collapse trace" if show_full else "Show full trace"
                ui.button(btn_label, on_click=lambda: (state.show_full_trace.update({active_id: not show_full}), render_main.refresh())).props('color=blue').classes('w-48')

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
        
    with ui.element('div').classes('fixed z-50').style('bottom: 24px; left: calc(50% + 175px); transform: translateX(-50%);'):
        with ui.dialog() as reject_dialog, ui.card().classes('w-[400px]'):
            ui.label("Reject Patch").classes('text-xl font-bold')
            ui.label("Provide a reason for rejecting this AI patch:").classes('text-sm text-gray-500 mb-2')
            note_input = ui.textarea(value=f.rejection_note, placeholder="Rejection note...").classes('w-full').props('rows=4 autofocus')
            with ui.row().classes('w-full justify-end gap-2 mt-4'):
                ui.button("Cancel", on_click=reject_dialog.close).props('flat')
                ui.button("Confirm Reject", on_click=lambda: (reject_file(active_id, note_input.value), reject_dialog.close(), refresh_all())).props('color=negative')

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
                    save_retest_primary = f.status == FileStatus.EDITED_PENDING
                    btn_text = "Save & Re-test" if save_retest_primary else "Re-test"
                    disabled = f.status not in (FileStatus.FAILED, FileStatus.EDITED_PENDING) or state.is_thinking
                    
                    def do_retest():
                        if state.diff_state.get(active_id) == "editing":
                            save_and_retest(active_id, state.edit_buffer.get(active_id, f.ai_source))
                        else:
                            push_log(active_id, "[System] Developer requested sandbox re-run.")
                            run_sandbox_simulation(active_id)
                    
                    btn3 = ui.button(btn_text, on_click=do_retest).props('unelevated rounded color=primary' if save_retest_primary else 'flat rounded color=grey-8').classes('action-pill-btn')
                    if disabled: btn3.disable()
                    
                    btn4 = ui.button("Reject", on_click=reject_dialog.open).props('unelevated rounded color=negative' if reject_eligible else 'flat rounded color=grey-8').classes('action-pill-btn')
                    if not reject_eligible: btn4.disable()

# ============================================================================
# MAIN PAGE
# ============================================================================
@ui.page('/')
def index():
    ui.add_head_html(get_css())
    
    ui.colors(primary='#ff5fd1', secondary='#fdfbf7', accent='#f5c518', dark='#101010', positive='#00c853', negative='#ff3333', info='#33ccff', warning='#f5c518')
    
    # REMOVED 'show-if-above' so we can actually collapse the drawer
    drawer = ui.left_drawer(value=True).props(':breakpoint="0" :width="350"').classes('border-r border-gray-200')
    state.drawer = drawer
    
    # Sidebar stays hidden on the pure Welcome Screen (no files, no import active)
    if not state.files and not state.import_mode:
        drawer.set_visibility(False)
        drawer.hide()
        
    with drawer:
        render_sidebar()
        
    with ui.column().classes('w-full h-full p-8 pb-10 max-w-[1600px] mx-auto'):
        render_main()


if __name__ in {'__main__', '__mp_main__'}:
    ui.run(title="RevivoAI", favicon="🔬", dark=False, port=8501, storage_secret='revivo-ai-secret')