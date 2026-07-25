import asyncio
import html
import time
from pathlib import Path

from nicegui import ui, app, events, background_tasks

# Import from backend
from backend.models import FileStatus, STATUS_META, WARNING_STATUSES, ProjectFile
from backend.logic import (
    parse_traceback, compute_anchors, group_frames_for_disclosure, 
    get_render_window, expand_window_for_related, build_diff_rows, pygments_style_defs
)
from backend.seed import build_seed_files
from backend.import_utils import import_from_uploads, import_local_project

# Import from frontend
from frontend.styles import get_css
from frontend.components import get_diff_html, get_code_viewer_html, get_code_pane_html, TRANSLATING_PHASES, SANDBOX_PHASES

# ============================================================================
# STATE INIT
# ============================================================================
class AppState:
    def __init__(self):
        self.files: dict[str, ProjectFile] = {}
        self.drawer = None
        self.active_buffer: str | None = None
        self.batch_selection: set[str] = set()
        self.expanded_folders: set[str] = {"controllers", "models", "views", "analytics", "FS"}
        self.diff_state: dict[str, str] = {}        
        self.edit_buffer: dict[str, str] = {}        
        self.trace_expanded: dict[str, bool] = {}     
        self.show_full_trace: dict[str, bool] = {}    
        self.load_full_file: dict[str, bool] = {}     
        self.confirm_load_full: dict[str, bool] = {}  
        self.batch_feedback: dict | None = None   
        self.rejecting: dict[str, bool] = {}          
        self.import_mode: str | None = None
        
        # Sidebar filters
        self.batch_mode: bool = False
        self.search_query: str = ""
        self.status_filter: str = "All"
        self.module_filter: str = "All"
        
        # Execution states & logs
        self.is_thinking: bool = False
        self.thinking_phase: int = 0  # <--- ADD THIS FIX
        self.agent_state: dict[str, str] = {}         
        self.execution_logs: dict[str, list[str]] = {} 
        self.current_terminal = None

state = AppState()

def load_demo_project():
    """Loads seed data. Everything starts as QUEUED now."""
    files = build_seed_files()
    state.files = {f.file_id: f for f in files}
    state.active_buffer = files[0].file_id
    state.import_mode = None
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
    ui.notify(html_content, html=True, position='top-right', close_button=False)

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
    refresh_all()

def clear_batch_selection():
    state.batch_selection = set()

def toggle_batch_selection(file_id: str, checked: bool):
    if checked: state.batch_selection.add(file_id)
    else: state.batch_selection.discard(file_id)

def toggle_folder_selection(folder_files: list[ProjectFile], checked: bool):
    for f in folder_files: 
        if checked: state.batch_selection.add(f.file_id)
        else: state.batch_selection.discard(f.file_id)
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
    if f.status == FileStatus.PASSED: 
        f.status = FileStatus.APPROVED
        show_alert(f"MCP Action: Overwriting local host file '{f.path}' with verified AI patch...", alert_type='positive')
        push_log(file_id, f"[MCP] 🟢 Local file '{f.path}' successfully overwritten.")

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

def export_approved(): 
    return [f for f in state.files.values() if f.status == FileStatus.APPROVED]

def refresh_all():
    if getattr(state, 'drawer', None) is not None:
        if state.files or state.import_mode:
            state.drawer.set_visibility(True)
            state.drawer.show()  # <-- Forces the layout to expand
        else:
            state.drawer.set_visibility(False)
            state.drawer.hide()  # <-- Reclaims the sidebar space
            
    render_sidebar.refresh()
    render_main.refresh()

# ============================================================================
# ASYNC SIMULATIONS (LANGGRAPH NODES)
# ============================================================================
async def simulate_translation(file_id: str):
    f = get_file(file_id)
    f.status = FileStatus.TRANSLATING
    state.is_thinking = True
    state.thinking_phase = 0  # Reset phase
    
    state.agent_state[file_id] = "Analyze"
    refresh_all()
    push_log(file_id, "[LangGraph] Entering Node: 🔍 Analyze")
    push_log(file_id, f"Parsing legacy code for {f.filename}...")
    push_log(file_id, "Building Abstract Syntax Tree and resolving dependencies.")
    
    await asyncio.sleep(1.2)
    if not getattr(state, 'is_thinking', False): return
    
    state.thinking_phase = 1  # Move to next phase
    state.agent_state[file_id] = "Propose"
    refresh_all()
    push_log(file_id, "[LangGraph] Entering Node: 💡 Propose")
    push_log(file_id, f"Generating AI patch utilizing persona: '{f.persona_label}'")
    
    await asyncio.sleep(1.5)
    if not getattr(state, 'is_thinking', False): return
    
    push_log(file_id, "Patch generated successfully. Handing off to execution environment.")
    transition_to_sandbox(file_id)
    state.is_thinking = False
    await simulate_sandbox(file_id, is_chained=True)

async def simulate_sandbox(file_id: str, is_chained: bool = False):
    f = get_file(file_id)
    f.status = FileStatus.SANDBOX_TESTING
    state.is_thinking = True
    state.thinking_phase = 0  # Reset phase
    
    state.agent_state[file_id] = "Execute"
    refresh_all()
    push_log(file_id, "[LangGraph] Entering Node: ⚡ Execute")
    push_log(file_id, "Spinning up isolated Docker Sandbox...")
    
    await asyncio.sleep(1.0)
    if not getattr(state, 'is_thinking', False): return
    
    state.thinking_phase = 1  # Move to next phase
    refresh_all()
    push_log(file_id, "Running test suite against generated patch. Capturing stdout/stderr...")
    
    await asyncio.sleep(1.2)
    if not getattr(state, 'is_thinking', False): return
    
    state.thinking_phase = 2  # Move to next phase
    state.agent_state[file_id] = "Evaluate"
    refresh_all()
    push_log(file_id, "[LangGraph] Entering Node: ⚖️ Evaluate")
    push_log(file_id, "Evaluating test execution results and parsing logs...")
    
    await asyncio.sleep(1.0)
    if not getattr(state, 'is_thinking', False): return
    
    resolve_sandbox_now(file_id)
    state.is_thinking = False
    
    if f.status == FileStatus.PASSED:
        push_log(file_id, "Evaluation Complete: Execution passed. No tracebacks found.")
    else:
        push_log(file_id, f"Evaluation Complete: Traceback captured at line {f.primary_error_line}.")
        push_log(file_id, "Awaiting developer intervention or auto-retry.")
        
    state.agent_state[file_id] = "Done"
    refresh_all()

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
        
        with ui.row().classes('w-full max-w-4xl justify-center gap-8 px-4'):
            if state.import_mode == "FILES":
                with ui.column().classes('w-full max-w-lg'):
                    ui.markdown("### Upload Files")
                    def handle_upload(e: events.UploadEventArguments):
                        imported_files = import_from_uploads([e])
                        if imported_files:
                            for f in imported_files:
                                state.files[f.file_id] = f
                            state.active_buffer = imported_files[0].file_id
                            state.import_mode = None
                            refresh_all()
                    ui.upload(on_upload=handle_upload, multiple=True, auto_upload=True).classes('w-full')
                    with ui.row().classes('w-full gap-4 mt-4'):
                        ui.button("Cancel", on_click=lambda: (setattr(state, 'import_mode', None), refresh_all())).classes('flex-1')
                        
            elif state.import_mode == "PROJECT":
                with ui.column().classes('w-full max-w-lg'):
                    ui.markdown("### Scan Local Directory")
                    path_input = ui.input("Absolute Path").props('placeholder="e.g., C:/Projects/legacy_app"').classes('w-full')
                    
                    def handle_scan():
                        try:
                            imported_files = import_local_project(path_input.value)
                            if imported_files:
                                state.files = {f.file_id: f for f in imported_files}
                                state.active_buffer = imported_files[0].file_id
                                state.import_mode = None
                                refresh_all()
                            else:
                                show_alert("No readable source files found in that directory.", alert_type='warning')
                        except ValueError:
                            show_alert("Directory not found. Check the path and try again.", alert_type='negative')
                            
                    with ui.row().classes('w-full gap-4 mt-4'):
                        ui.button("🚀 Scan Directory", on_click=handle_scan).props('color=primary').classes('flex-1')
                        ui.button("Cancel", on_click=lambda: (setattr(state, 'import_mode', None), refresh_all())).classes('flex-1')
                        
            else:
                with ui.column().classes('w-full items-center pt-16'):
                    with ui.row().classes('w-full max-w-5xl justify-center items-stretch gap-8 mb-8'):
                        
                        # Added `welcome-import-card` for our aggressive CSS override target
                        with ui.card().classes(
                            'welcome-import-card flex-1 cursor-pointer flex flex-col items-center justify-center text-center '
                            'border-4 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] p-8'
                        ) as card1:
                            ui.html('<div class="font-black whitespace-nowrap text-2xl">IMPORT FILES</div><div class="text-sm mt-4 font-bold">Pick one or more individual source files to translate.</div>')
                            card1.on('click', lambda: (setattr(state, 'import_mode', "FILES"), refresh_all()))
                            
                        with ui.card().classes(
                            'welcome-import-card flex-1 cursor-pointer flex flex-col items-center justify-center text-center '
                            'border-4 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] p-8'
                        ) as card2:
                            ui.html('<div class="font-black whitespace-nowrap text-2xl">IMPORT PROJECT</div><div class="text-sm mt-4 font-bold">Scans local directory trees directly from disk.</div>')
                            card2.on('click', lambda: (setattr(state, 'import_mode', "PROJECT"), refresh_all()))
                            
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
                
                f_btn = ui.element('div').classes(btn_cls).on('click', lambda: (setattr(state, 'import_mode', "FILES"), state.files.clear(), refresh_all()))
                with f_btn:
                    ui.label('+ Files').classes('relative z-10 pointer-events-none block group-hover:text-white transition-colors duration-200')
                    
                p_btn = ui.element('div').classes(btn_cls).on('click', lambda: (setattr(state, 'import_mode', "PROJECT"), state.files.clear(), refresh_all()))
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
                                if state.batch_mode:
                                    folder_checked = all(f.file_id in state.batch_selection for f in visible)
                                    def on_folder_check(e, f_list=visible):
                                        toggle_folder_selection(f_list, e.value)
                                        render_sidebar.refresh()
                                    ui.checkbox(f"Select all in '{folder}'", value=folder_checked, on_change=on_folder_check).classes('ml-2')

                                for i, f in enumerate(visible):
                                    meta = STATUS_META.get(f.status, {"icon": "❓", "label": "UNKNOWN", "color": "gray"})
                                    is_active = state.active_buffer == f.file_id
                                    
                                    prefix = "└─" if i == len(visible)-1 else "├─"
                                    button_label = f'{prefix} {meta["icon"]} {f.filename}'
                                    
                                    bg_props = 'unelevated color="grey-4"' if is_active else 'flat'
                                    text_color = 'black' if is_active else 'grey-8'
                                    font_weight = 'font-bold' if is_active else 'font-normal'
                                    
                                    with ui.row().classes('w-full items-center wrap-none gap-0'):
                                        if state.batch_mode:
                                            checked = f.file_id in state.batch_selection
                                            def on_file_check(e, fid=f.file_id):
                                                toggle_batch_selection(fid, e.value)
                                                render_sidebar.refresh()
                                            ui.checkbox(value=checked, on_change=on_file_check).classes('mr-2')
                                        
                                        btn = ui.button(button_label, on_click=lambda e, fid=f.file_id: set_active_buffer(fid))
                                        btn.props(f'{bg_props} align="left" text-color="{text_color}" no-caps dense').classes(f'flex-1 truncate {font_weight}')

        # 3. FIXED FOOTER
        with ui.column().classes('w-full p-4 border-t border-gray-200 bg-gray-50 mt-auto'):
            if not state.batch_mode and not state.batch_selection:
                def on_export():
                    approved = export_approved()
                    if approved: show_alert(f"Exported {len(approved)} approved file(s)", alert_type='positive')
                    else: show_alert("No approved files to export yet.", alert_type='warning')
                btn = ui.element('div').classes(
                    'group relative w-full bg-white px-5 py-3 font-semibold text-black text-center cursor-pointer '
                    'after:absolute after:inset-x-0 after:bottom-0 after:h-1 after:bg-black '
                    'transition-all duration-200 after:transition-all after:duration-200 '
                    'hover:after:h-full focus:ring-2 focus:ring-yellow-300 focus:outline-0 border border-gray-300 hover:border-black'
                ).on('click', on_export)
                with btn:
                    ui.label('⬇ Export All Approved').classes('relative z-10 pointer-events-none block group-hover:text-white transition-colors duration-200')
            elif state.batch_mode:
                ui.markdown(f"**{len(state.batch_selection)} file(s) selected**")
                with ui.row().classes('w-full gap-2'):
                    ui.button("🚀 Trans.", on_click=lambda: execute_batch("translate")).classes('flex-1').props('size=sm')
                    ui.button("✅ Appr.", on_click=lambda: execute_batch("approve")).classes('flex-1').props('size=sm')
                with ui.row().classes('w-full gap-2 mt-2'):
                    ui.button("🔄 Re-run", on_click=lambda: execute_batch("rerun")).classes('flex-1').props('size=sm')
                    ui.button("✕ Clear", on_click=lambda: (clear_batch_selection(), render_sidebar.refresh())).classes('flex-1').props('size=sm')

def execute_batch(action: str):
    sel = list(state.batch_selection)
    ok, skipped = [], []
    for fid in sel:
        f = get_file(fid)
        if action == "translate":
            if f.status == FileStatus.QUEUED:
                run_translation_simulation(fid)
                ok.append(fid)
            else: skipped.append((fid, f.status))
        elif action == "approve":
            if f.status == FileStatus.PASSED:
                f.status = FileStatus.APPROVED
                ok.append(fid)
            else: skipped.append((fid, f.status))
        elif action == "rerun":
            if f.status in (FileStatus.FAILED, FileStatus.EDITED_PENDING):
                f.status = FileStatus.SANDBOX_TESTING
                resolve_sandbox_now(fid)
                ok.append(fid)
            else: skipped.append((fid, f.status))
            
    state.batch_feedback = {"action": action, "ok": ok, "skipped": skipped}
    clear_batch_selection()
    refresh_all()

# ============================================================================
# STATE MACHINE TRACKER (UI COMPONENT)
# ============================================================================
def render_state_machine_tracker(current_state: str, show_rerun: bool = False, rerun_callback=None):
    nodes = ["Analyze", "Propose", "Execute", "Evaluate"]
    
    # Compact, single-line stepper layout
    with ui.row().classes('w-full items-center justify-between bg-white py-2 px-6 border-t-2 border-black overflow-hidden flex-nowrap'):
        with ui.row().classes('items-center gap-3 sm:gap-4 overflow-hidden'):
            for i, node in enumerate(nodes):
                node_idx = nodes.index(node)
                
                if current_state in nodes:
                    curr_idx = nodes.index(current_state)
                elif current_state == "Done":
                    curr_idx = 999 
                else:
                    curr_idx = -1  
                    
                if node_idx < curr_idx:
                    color = "bg-green-500 text-white border-green-700"
                    icon = "✓"
                elif node_idx == curr_idx:
                    color = "bg-yellow-400 text-black border-yellow-600 animate-pulse"
                    icon = "▶"
                else:
                    color = "bg-gray-100 text-gray-400 border-gray-300"
                    icon = "·"
                
                with ui.row().classes('items-center gap-2 wrap-none m-0 p-0'):
                    ui.label(icon).classes(f'flex items-center justify-center w-5 h-5 rounded-full font-bold border-2 text-xs {color}')
                    text_color = "text-black" if node_idx <= curr_idx else "text-gray-400"
                    ui.label(node).classes(f'font-bold text-xs uppercase tracking-wide {text_color} m-0 p-0')
                
                # Simple arrow separator instead of large progress bars
                if i < len(nodes) - 1:
                    ui.label("→").classes('text-gray-300 font-bold text-xs m-0 p-0')
                
        if show_rerun and rerun_callback:
            ui.button("Re-run Sandbox", on_click=rerun_callback).props('color=blue').classes('w-auto flex-shrink-0')

# ============================================================================
# MAIN CONTENT VIEWER
# ============================================================================
@ui.refreshable
def render_main():
    if not state.files:
        render_welcome()
        return
        
    active_id = state.active_buffer
    if not active_id or active_id not in state.files:
        ui.label("Select a file from the sidebar.")
        return
        
    f = get_file(active_id)
    
    meta = STATUS_META.get(f.status, {"icon": "❓", "label": "UNKNOWN", "color": "gray"})
    f_color = meta["color"]
    
    if state.batch_feedback:
        fb = state.batch_feedback
        verb = "queued for AI translation" if fb["action"] == "translate" else "approved" if fb["action"] == "approve" else "queued for re-run"
        lines = [f'✅ {len(fb["ok"])} files {verb}.']
        if fb["skipped"]:
            lines.append(f'⚠️ {len(fb["skipped"])} skipped - not eligible:')
            for fid, st_val in fb["skipped"]:
                sf = get_file(fid)
                lines.append(f'&nbsp;&nbsp;&nbsp;• {sf.filename} ({STATUS_META.get(st_val, {}).get("icon", "")} {STATUS_META.get(st_val, {}).get("label", "")})')
        
        with ui.row().classes('w-full mb-6 items-start feedback-banner justify-between'):
            ui.html("<br>".join(lines))
            ui.button("Dismiss", on_click=lambda: (setattr(state, 'batch_feedback', None), render_main.refresh())).props('flat')

    # CARD 1: File Overview & Pipeline State (Merged, standard neo-card style)
    with ui.column().classes('w-full neo-card neo-card-light p-0 mb-6 overflow-hidden'):
        ui.html(f'''
        <div class="neo-card-header bleed border-b-0">
            <div class="header-left">
                <div class="neo-card-title-group">
                    {f.path}
                </div>
                <div class="header-desc">Current active file context, execution status overview, and pipeline state.</div>
            </div>
            <div class="stat-pill {f_color}">
                {meta["label"]}
            </div>
        </div>
        ''').classes('w-full')

        # Embedded LANGGRAPH TRACKER
        curr_state = state.agent_state.get(active_id, "Done" if f.status != FileStatus.QUEUED else "Idle")
        show_rerun = f.status in (FileStatus.FAILED, FileStatus.EDITED_PENDING)
        render_state_machine_tracker(
            current_state=curr_state, 
            show_rerun=show_rerun, 
            rerun_callback=lambda: run_sandbox_simulation(active_id)
        )

    skip_to_action_bar = False
    
    def render_terminal(is_half=False):
        width_class = "w-full" if not is_half else "flex-1"
        margin_class = "mt-2" if not is_half else "m-0"
        height_class = "h-80" if is_half else "h-96"
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
        html_str = get_code_viewer_html(
            code=f.legacy_source,
            language=f.language,
            title="LEGACY SOURCE CODE",
            desc="",  # Removed the description text
            pill="VIEWER"
        )
                # Inject inline CSS to trim the header height and hide any residual description space
        styled_html = f"""
            <style>
                .legacy-slim-header .neo-card-header {{
                    padding-top: 3px !important;
                    padding-bottom: 3px !important;
                    min-height: auto !important;
                }}
                .legacy-slim-header .header-desc {{
                    display: none !important;
                    margin: 0 !important;
                }}
            </style>
            <div class="legacy-slim-header">
                {html_str}
            </div>
        """
        ui.html(html_str).classes('w-full mb-6')
        skip_to_action_bar = True
        
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
            with ui.column().classes('flex-1 h-80 neo-card neo-card-spotlight p-0 mb-0'):
                ui.html('''
                    <div class="neo-card-header bleed">
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
            with ui.column().classes('flex-1 h-80 neo-card neo-card-spotlight p-0 mb-0'):
                ui.html('''
                    <div class="neo-card-header bleed">
                        <div class="header-left">
                            <div class="neo-card-title-group"><span class="thinking-pulse-dot"></span> SANDBOX EXECUTION</div>
                            <div class="header-desc">Executing containerized test suite against generated patch.</div>
                        </div>
                    </div>
                ''').classes('w-full')
                ui.html(f'<div class="px-6 py-4">{"".join(rows_html)}</div>').classes('w-full')
                
            render_terminal(is_half=True)

    # Diff Viewer
    if not skip_to_action_bar and f.status not in (FileStatus.TRANSLATING, FileStatus.SANDBOX_TESTING):
        legacy_lines, ai_lines = f.legacy_source.splitlines(), f.ai_source.splitlines()
        total_lines = max(len(legacy_lines), len(ai_lines))
        load_full = state.load_full_file.get(active_id, False)

        if load_full:
            window, out_of_range = (0, total_lines), []
        else:
            window = get_render_window(total_lines, f.primary_error_line)
            window, out_of_range = expand_window_for_related(window, f.related_error_lines, total_lines)

        if (window[0] > 0 or window[1] < total_lines) and not load_full:
            anchor_note = f" (centered on error at line {f.primary_error_line})" if f.primary_error_line else ""
            with ui.row().classes('w-full justify-between items-center mb-4'):
                ui.html(f'<div class="truncation-banner mb-0">⚠️ Showing lines {window[0]+1:,}-{window[1]:,} of {total_lines:,}{anchor_note}</div>').classes('flex-1 mr-4')
                ui.button("Load Full File ↓", on_click=lambda: (state.confirm_load_full.update({active_id: True}), render_main.refresh())).classes('w-48')
            
            if state.confirm_load_full.get(active_id):
                with ui.row().classes('w-full bg-yellow-900/30 p-4 rounded mb-4 items-center gap-4'):
                    ui.label(f"This file has {total_lines:,} lines and may slow down your browser. Continue?")
                    ui.button("Yes", on_click=lambda: (state.load_full_file.update({active_id: True}), state.confirm_load_full.update({active_id: False}), render_main.refresh()))
                    ui.button("Cancel", on_click=lambda: (state.confirm_load_full.update({active_id: False}), render_main.refresh()))

        for ln in out_of_range: ui.label(f"ℹ️ Related frame at line {ln} is outside the displayed range.").classes('text-gray-400 text-sm')

        diff_state_val = state.diff_state.get(active_id, "readonly")
        if diff_state_val == "editing":
            with ui.column().classes('w-full neo-card p-0 mb-6'):
                ui.html("""
                <div class="neo-card-header bleed compact-header">
                    <div class="header-left">
                        <div class="neo-card-title-group">MANUAL EDIT MODE</div>
                        <div class="header-desc">Manually override AI-generated patch before re-testing.</div>
                    </div>
                    <div class="stat-pill yellow">EDIT</div>
                </div>
                """).classes('w-full')
                with ui.row().classes('w-full p-4 gap-4'):
                    with ui.column().classes('flex-1'):
                        ui.html('<div class="pane-label">LEGACY (READ-ONLY)</div>')
                        ui.html(f'<div class="pane-code-frame">{get_code_pane_html(f.legacy_source, f.language)}</div>').classes('w-full')
                    with ui.column().classes('flex-1'):
                        ui.html('<div class="pane-label">AI-GENERATED (EDITABLE)</div>')
                        current_draft = state.edit_buffer.get(active_id, f.ai_source)
                        text_area = ui.textarea(value=current_draft).classes('w-full font-mono').props('rows=20 spellcheck=false')
                        def on_change(e):
                            state.edit_buffer[active_id] = e.value
                            mark_dirty(active_id)
                        text_area.on('change', on_change)
                
                with ui.row().classes('w-full p-4 gap-4'):
                    ui.button("💾 Save & Re-test", on_click=lambda: (save_and_retest(active_id, state.edit_buffer.get(active_id, f.ai_source)), refresh_all())).props('color=primary')
                    ui.button("Cancel", on_click=lambda: (state.diff_state.update({active_id: "readonly"}), refresh_all()))
        else:
            diff_data = build_diff_rows(legacy_lines, ai_lines, f.language, window, f.primary_error_line, f.related_error_lines, mode_override="split", disable_folding=True)
            ui.html(get_diff_html(diff_data)).classes('w-full mb-6')

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
                <div class="neo-card-header bleed compact-header">
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

    if state.rejecting.get(active_id, False):
        ui.markdown("**Rejection note**").classes('mt-8')
        note_input = ui.textarea(value=f.rejection_note).classes('w-full').props('rows=3')
        with ui.row().classes('w-full gap-4 mt-2'):
            ui.button("Confirm Reject", on_click=lambda: (reject_file(active_id, note_input.value), refresh_all())).props('color=negative')
            ui.button("Cancel", on_click=lambda: (state.rejecting.update({active_id: False}), render_main.refresh()))

    if f.status == FileStatus.REJECTED and f.rejection_note and not state.rejecting.get(active_id, False):
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
                    
                    btn4 = ui.button("Reject", on_click=lambda: (state.rejecting.update({active_id: True}), render_main.refresh())).props('unelevated rounded color=negative' if reject_eligible else 'flat rounded color=grey-8').classes('action-pill-btn')
                    if not reject_eligible: btn4.disable()

# ============================================================================
# MAIN PAGE
# ============================================================================
@ui.page('/')
def index():
    ui.add_head_html(get_css(pygments_style_defs()))
    
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