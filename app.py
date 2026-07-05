import time
import html
import streamlit as st

# Import from backend
from backend.models import FileStatus, STATUS_META, WARNING_STATUSES, ProjectFile
from backend.logic import (
    parse_traceback, compute_anchors, group_frames_for_disclosure, 
    get_render_window, expand_window_for_related, build_diff_rows, pygments_style_defs
)
from backend.seed import build_seed_files
from backend.import_utils import import_from_streamlit_uploads, import_local_project

# Import from frontend
from frontend.styles import get_css
from frontend.components import render_diff_table, render_langgraph_status, render_terminal_logs

st.set_page_config(page_title="RevivoAI", page_icon="🔬", layout="wide")
st.markdown(get_css(pygments_style_defs()), unsafe_allow_html=True)

# ============================================================================
# STATE INIT
# ============================================================================
def init_state():
    if "files" not in st.session_state:
        st.session_state["files"] = {}
        st.session_state["active_buffer"] = None
        st.session_state["batch_selection"] = set()
        st.session_state["expanded_folders"] = {"controllers", "models", "views", "analytics"}
        st.session_state["diff_state"] = {}        
        st.session_state["edit_buffer"] = {}        
        st.session_state["trace_expanded"] = {}     
        st.session_state["show_full_trace"] = {}    
        st.session_state["load_full_file"] = {}     
        st.session_state["confirm_load_full"] = {}  
        st.session_state["batch_feedback"] = None   
        st.session_state["rejecting"] = {}          
        st.session_state["scroll_pulse"] = None     
        st.session_state["import_notice"] = None
        st.session_state["import_mode"] = None

def load_demo_project():
    """Loads seed data. Everything starts as QUEUED now."""
    files = build_seed_files()
    st.session_state["files"] = {f.file_id: f for f in files}
    st.session_state["active_buffer"] = files[0].file_id

init_state()
FILES: dict[str, ProjectFile] = st.session_state["files"]

# ============================================================================
# STATE HELPERS
# ============================================================================
def get_file(file_id: str) -> ProjectFile: return FILES[file_id]
def folder_tree() -> dict[str, list[ProjectFile]]:
    tree: dict[str, list[ProjectFile]] = {}
    for f in FILES.values(): tree.setdefault(f.folder, []).append(f)
    for folder in tree: tree[folder].sort(key=lambda f: f.filename)
    return dict(sorted(tree.items()))
def folder_has_warning(folder_files: list[ProjectFile]) -> int: return sum(1 for f in folder_files if f.status in WARNING_STATUSES)
def set_active_buffer(file_id: str): st.session_state["active_buffer"] = file_id

def clear_batch_selection():
    st.session_state["batch_selection"] = set()
    st.session_state["_pending_checkbox_reset"] = True

def toggle_batch_selection(file_id: str, checked: bool):
    sel = st.session_state["batch_selection"]
    if checked:
        sel.add(file_id)
    else:
        sel.discard(file_id)
    for key in list(st.session_state.keys()):
        if key.startswith("folder_chk__"):
            del st.session_state[key]

def toggle_folder_selection(folder_files: list[ProjectFile], checked: bool):
    sel = st.session_state["batch_selection"]
    for f in folder_files: 
        if checked:
            sel.add(f.file_id)
        else:
            sel.discard(f.file_id)
        st.session_state[f"sel__{f.file_id}"] = checked

def start_translation(file_id: str):
    f = get_file(file_id)
    f.status = FileStatus.TRANSLATING

def transition_to_sandbox(file_id: str):
    f = get_file(file_id)
    f.status = FileStatus.SANDBOX_TESTING
    
    # Reveal the target AI code if it exists (Demo mode)
    if f.target_ai_source:
        f.ai_source = f.target_ai_source
    # Otherwise mock a generic rewrite (Real Upload Mode)
    elif not f.ai_source:
        f.ai_source = f"# [AI TRANSLATION COMPLETE - U001/U002]\n" + f.legacy_source.replace("class ", "class Modern")

def start_sandbox(file_id: str):
    f = get_file(file_id)
    f.status = FileStatus.SANDBOX_TESTING

def resolve_sandbox_now(file_id: str):
    f = get_file(file_id)
    edited = file_id in st.session_state["edit_buffer"] and st.session_state["edit_buffer"][file_id]
    
    if edited:
        f.status = FileStatus.PASSED
        f.raw_traceback = ""
        f.primary_error_line = None
        f.related_error_lines = []
    else:
        # If this is a demo file, reveal its target status and tracebacks
        if f.target_status:
            f.status = f.target_status
            f.raw_traceback = f.target_traceback
            # Parse the traceback now that it has been revealed
            if f.raw_traceback:
                frames = parse_traceback(f.raw_traceback, f.language, f.filename)
                primary, related = compute_anchors(frames)
                f.primary_error_line = primary
                f.related_error_lines = related
        else:
            # Fallback for real files
            f.status = FileStatus.FAILED if f.raw_traceback else FileStatus.PASSED

def run_sandbox_simulation(file_id: str):
    start_sandbox(file_id)

def approve_file(file_id: str):
    f = get_file(file_id)
    if f.status == FileStatus.PASSED: f.status = FileStatus.APPROVED
def reject_file(file_id: str, note: str):
    f = get_file(file_id)
    f.status, f.rejection_note, st.session_state["rejecting"][file_id] = FileStatus.REJECTED, note, False
def start_edit(file_id: str): st.session_state["diff_state"][file_id] = "editing"
def mark_dirty(file_id: str):
    f = get_file(file_id)
    if f.status != FileStatus.EDITED_PENDING: f.status = FileStatus.EDITED_PENDING
def save_and_retest(file_id: str, widget_value: str):
    f = get_file(file_id)
    st.session_state["edit_buffer"][file_id] = widget_value
    f.ai_source = widget_value
    st.session_state["diff_state"][file_id] = "readonly"
    start_sandbox(file_id)
def export_approved(): return [f for f in FILES.values() if f.status == FileStatus.APPROVED]

# ============================================================================
# WELCOME SCREEN (NO FILES LOADED)
# ============================================================================
if not FILES:
    st.markdown(
        '''
        <div class="welcome-screen">
            <div class="welcome-kicker">⚙️ LEGACY CODE MODERNIZATION TOOL</div>
            <div class="welcome-title">REVIVO<span class="welcome-title-accent">AI</span></div>
            <div class="welcome-desc">
                Turn brittle legacy systems into modern, sandbox-verified code.<br>
                AI drafts the patch. The sandbox proves it works. You stay in control.
            </div>
        </div>
        ''',
        unsafe_allow_html=True
    )
    st.markdown('<div style="margin-top: -32px;"></div>', unsafe_allow_html=True)
    
    wcol1, wcol2, wcol3 = st.columns([1, 3, 1])
    with wcol2:
        if st.session_state["import_mode"] == "FILES":
            st.markdown("### Upload Files")
            uploaded = st.file_uploader("Select one or more legacy files", accept_multiple_files=True)
            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                if st.button("🚀 Process Files", type="primary", use_container_width=True, disabled=not uploaded):
                    imported_files = import_from_streamlit_uploads(uploaded)
                    st.session_state["files"] = {f.file_id: f for f in imported_files}
                    st.session_state["active_buffer"] = imported_files[0].file_id
                    st.session_state["import_mode"] = None
                    st.rerun()
            with btn_col2:
                if st.button("Cancel", use_container_width=True):
                    st.session_state["import_mode"] = None
                    st.rerun()

        elif st.session_state["import_mode"] == "PROJECT":
            st.markdown("### Scan Local Directory")
            path = st.text_input("Absolute Path", placeholder="e.g., C:/Projects/legacy_app or /Users/name/repo")
            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                if st.button("🚀 Scan Directory", type="primary", use_container_width=True, disabled=not path):
                    try:
                        imported_files = import_local_project(path)
                        if imported_files:
                            st.session_state["files"] = {f.file_id: f for f in imported_files}
                            st.session_state["active_buffer"] = imported_files[0].file_id
                            st.session_state["import_mode"] = None
                            st.rerun()
                        else:
                            st.warning("No readable source files found in that directory.")
                    except ValueError:
                        st.error("Directory not found. Check the path and try again.")
            with btn_col2:
                if st.button("Cancel", use_container_width=True):
                    st.session_state["import_mode"] = None
                    st.rerun()

        else:
            bcol1, bcol2 = st.columns(2)
            with bcol1:
                with st.container(key="welcome_card_files"):
                    st.markdown(
                        '<div class="welcome-import-card">'
                        '<div class="welcome-import-title">IMPORT FILES</div>'
                        '<div class="welcome-import-desc">Pick one or more individual source files to translate.</div>'
                        '</div>',
                        unsafe_allow_html=True
                    )
                    if st.button("invisible_btn", key="welcome_btn_files"):
                        st.session_state["import_mode"] = "FILES"
                        st.rerun()
            with bcol2:
                with st.container(key="welcome_card_project"):
                    st.markdown(
                        '<div class="welcome-import-card">'
                        '<div class="welcome-import-title">IMPORT PROJECT</div>'
                        '<div class="welcome-import-desc">Scans local directory trees directly from disk.</div>'
                        '</div>',
                        unsafe_allow_html=True
                    )
                    if st.button("invisible_btn", key="welcome_btn_project"):
                        st.session_state["import_mode"] = "PROJECT"
                        st.rerun()
            
            st.markdown("<br><center><small>or</small></center>", unsafe_allow_html=True)
            if st.button("Load Demo Project (Mock Data)", use_container_width=True):
                load_demo_project()
                st.rerun()
                
    st.stop()

if st.session_state.get("_pending_checkbox_reset"):
    for key in list(st.session_state.keys()):
        if key.startswith("sel__") or key.startswith("folder_chk__"):
            st.session_state[key] = False
    st.session_state["_pending_checkbox_reset"] = False

# ============================================================================
# SIDEBAR
# ============================================================================
with st.sidebar:
    st.markdown(
        '<div class="sidebar-brand">&nbsp;REVIVOAI</div>',
        unsafe_allow_html=True
    )
    
    col_imp1, col_imp2 = st.columns(2)
    with col_imp1:
        if st.button("📁 Import Files", use_container_width=True, key="import_files_btn"):
            st.session_state["import_mode"] = "FILES"
            FILES.clear()
            st.rerun()
    with col_imp2:
        if st.button("📦 Import Project", use_container_width=True, key="import_project_btn"):
            st.session_state["import_mode"] = "PROJECT"
            FILES.clear()
            st.rerun()
    
    st.markdown("---")

    batch_mode = st.toggle("☑️ Enable Batch Selection", key="batch_mode_toggle")
    
    search_query = st.text_input("🔍 Search filename", value="", placeholder="search filename...", label_visibility="collapsed")
    fcol1, fcol2 = st.columns(2)
    status_options = ["All"] + [s.value for s in FileStatus]
    with fcol1: status_filter = st.selectbox("Status", status_options, label_visibility="collapsed")
    with fcol2: module_filter = st.selectbox("Module", ["All"] + sorted({f.folder for f in FILES.values()}), label_visibility="collapsed")

    counts = {s: 0 for s in FileStatus}
    for f in FILES.values(): counts[f.status] += 1
    st.markdown(f'<div class="summary-strip">📊 {counts[FileStatus.PASSED]} passed · {counts[FileStatus.FAILED]} failed</div>', unsafe_allow_html=True)

    st.markdown(
        '<div class="icon-legend">'
        '<span>✅ Passed/Approved</span>'
        '<span>❌ Failed</span>'
        '<span>🔄 Translating</span>'
        '<span>⏳ Sandbox testing</span>'
        '<span>✏️ Edited, pending</span>'
        '<span>🚫 Rejected</span>'
        '<span>⬜ Queued</span>'
        '</div>',
        unsafe_allow_html=True
    )

    def matches_filters(f: ProjectFile) -> bool:
        if search_query and search_query.lower() not in f.filename.lower(): return False
        if status_filter != "All" and f.status.value != status_filter: return False
        if module_filter != "All" and f.folder != module_filter: return False
        return True

    for folder, folder_files in folder_tree().items():
        visible = [f for f in folder_files if matches_filters(f)]
        if not visible: continue
        
        warn_count = folder_has_warning(folder_files)
        warn_badge = f'&nbsp;&nbsp;<span class="warn-badge"> ⚠️ </span>' if warn_count else f"&nbsp;&nbsp;({len(folder_files)})"
        
        state_key = f"folder_expanded_{folder}"
        if state_key not in st.session_state:
            st.session_state[state_key] = folder in st.session_state.get("expanded_folders", set())
            
        icon = "▼" if st.session_state[state_key] else "▶"
        
        with st.container(key=f"folder_group_{folder}"):
            with st.container(key=f"folder_header_{folder}"):
                st.markdown(f'<div class="sidebar-folder">{icon}&nbsp; 📂 {folder}{warn_badge}</div>', unsafe_allow_html=True)
                if st.button("invisible_toggle", key=f"toggle_{folder}"):
                    st.session_state[state_key] = not st.session_state[state_key]
                    st.rerun()
            
            if st.session_state[state_key]:
                if batch_mode:
                    folder_checked = all(f.file_id in st.session_state["batch_selection"] for f in visible)
                    new_folder_checked = st.checkbox(f"Select all in '{folder}'", value=folder_checked, key=f"folder_chk__{folder}")
                    if new_folder_checked != folder_checked:
                        toggle_folder_selection(visible, new_folder_checked)
                        st.rerun()

                for f in visible:
                    meta = STATUS_META[f.status]
                    is_active = st.session_state["active_buffer"] == f.file_id
                    
                    prefix = "└─" if f is visible[-1] else "├─"
                    button_label = f'{prefix} {meta["icon"]} {f.filename}'
                    
                    if batch_mode:
                        row_cols = st.columns([1, 8])
                        with row_cols[0]:
                            checked = f.file_id in st.session_state["batch_selection"]
                            new_checked = st.checkbox("select", value=checked, key=f"sel__{f.file_id}", label_visibility="collapsed")
                            if new_checked != checked:
                                toggle_batch_selection(f.file_id, new_checked)
                                st.rerun()
                        with row_cols[1]:
                            if st.button(button_label, key=f"filerow__{f.file_id}__{f.status.name.lower()}", use_container_width=True, type="primary" if is_active else "secondary"):
                                set_active_buffer(f.file_id)
                                st.rerun()
                    else:
                        if st.button(button_label, key=f"filerow__{f.file_id}__{f.status.name.lower()}", use_container_width=True, type="primary" if is_active else "secondary"):
                            set_active_buffer(f.file_id)
                            st.rerun()

    st.markdown("---")
    
    sel = st.session_state["batch_selection"]
    if not batch_mode and not sel:
        if st.button("⬇ Export All Approved", use_container_width=True, key="export_approved_btn"):
            approved = export_approved()
            if approved: st.success(f"Exported {len(approved)} approved file(s): " + ", ".join(f.filename for f in approved))
            else: st.warning("No approved files to export yet.")
    elif batch_mode:
        st.markdown(f"**{len(sel)} file(s) selected**")
        bcol1, bcol2, bcol3, bcol4 = st.columns(4)
        
        def execute_batch_translate(selected_ids):
            translated, skipped = [], []
            for fid in selected_ids:
                f = get_file(fid)
                if f.status == FileStatus.QUEUED:
                    f.status = FileStatus.TRANSLATING
                    translated.append(fid)
                else: skipped.append((fid, f.status))
            return translated, skipped

        def execute_batch_approve(selected_ids):
            approved, skipped = [], []
            for fid in selected_ids:
                f = get_file(fid)
                if f.status == FileStatus.PASSED:
                    f.status = FileStatus.APPROVED
                    approved.append(fid)
                else: skipped.append((fid, f.status))
            return approved, skipped

        def execute_batch_rerun(selected_ids):
            rerun, skipped = [], []
            for fid in selected_ids:
                f = get_file(fid)
                if f.status in (FileStatus.FAILED, FileStatus.EDITED_PENDING):
                    run_sandbox_simulation(fid)
                    rerun.append(fid)
                else: skipped.append((fid, f.status))
            return rerun, skipped

        with bcol1:
            if st.button("🚀 Translate", use_container_width=True, key="batch_translate_btn", disabled=len(sel)==0):
                translated, skipped = execute_batch_translate(list(sel))
                st.session_state["batch_feedback"] = {"action": "translate", "ok": translated, "skipped": skipped}
                clear_batch_selection()
                st.rerun()
        with bcol2:
            if st.button("✅ Approve", use_container_width=True, key="batch_approve_btn", disabled=len(sel)==0):
                approved, skipped = execute_batch_approve(list(sel))
                st.session_state["batch_feedback"] = {"action": "approve", "ok": approved, "skipped": skipped}
                clear_batch_selection()
                st.rerun()
        with bcol3:
            if st.button("🔄 Re-run", use_container_width=True, key="batch_rerun_btn", disabled=len(sel)==0):
                rerun, skipped = execute_batch_rerun(list(sel))
                st.session_state["batch_feedback"] = {"action": "rerun", "ok": rerun, "skipped": skipped}
                clear_batch_selection()
                st.rerun()
        with bcol4:
            if st.button("✕ Clear", use_container_width=True, key="batch_clear_btn", disabled=len(sel)==0):
                clear_batch_selection()
                st.rerun()

# ============================================================================
# MAIN CONTENT VIEWER
# ============================================================================
active_id = st.session_state["active_buffer"]
f = get_file(active_id)
meta = STATUS_META[f.status]
f_color = meta["color"]

fb = st.session_state["batch_feedback"]
if fb:
    if fb["action"] == "translate": verb = "queued for AI translation"
    elif fb["action"] == "approve": verb = "approved"
    else: verb = "queued for re-run"
    
    lines = [f'✅ {len(fb["ok"])} files {verb}.']
    if fb["skipped"]:
        lines.append(f'⚠️ {len(fb["skipped"])} skipped — not eligible:')
        for fid, status in fb["skipped"]:
            sf = get_file(fid)
            lines.append(f'&nbsp;&nbsp;&nbsp;• {sf.filename} ({STATUS_META[status]["icon"]} {STATUS_META[status]["label"]})')
    bcol, dcol = st.columns([10, 1])
    with bcol: st.markdown('<div class="feedback-banner">' + "<br>".join(lines) + "</div>", unsafe_allow_html=True)
    with dcol:
        if st.button("Dismiss", key="dismiss_feedback"):
            st.session_state["batch_feedback"] = None
            st.rerun()

persona_badge_html = f'<span class="persona-badge">{f.persona_label}</span>' if f.persona_label else ""
usecase_badge_html = f'<span class="usecase-badge">{html.escape(f.use_case)}</span>' if f.use_case else ""

st.markdown(f'''
<div class="neo-card neo-card-light">
    <div class="neo-card-header">
        <div class="header-left">
            <div class="neo-card-title-group">
                <span class="num-badge">01</span>
                📄 {f.path}{persona_badge_html}{usecase_badge_html}
            </div>
            <div class="header-desc">Current active file context and status overview.</div>
        </div>
        <div class="stat-pill {f_color}">
            {meta["icon"]} {meta["label"]}
        </div>
    </div>
</div>
''', unsafe_allow_html=True)

btn_col1, btn_col2 = st.columns([8, 2])
with btn_col2:
    if st.button("🔄 Re-run Sandbox", disabled=f.status not in (FileStatus.FAILED, FileStatus.EDITED_PENDING), use_container_width=True, key="single_rerun"):
        run_sandbox_simulation(active_id)
        st.rerun()


# ============================================================================
# SPINNING LOADERS (U001, U002, U003)
# ============================================================================
TRANSLATING_PHASES = {
    "systems_engineer": [
        "Parsing abstract syntax tree of legacy source (FR-2.1)",
        "Injecting Systems Engineering persona prompt",
        "Cross-referencing xv6 inode/block addressing conventions",
        "Drafting modernized patch candidate",
    ],
    "data_scientist": [
        "Parsing abstract syntax tree of legacy source (FR-2.2)",
        "Injecting Quantitative Data Science persona prompt",
        "Mapping legacy lexicon logic to transformer-based TRV scoring",
        "Drafting modernized patch candidate",
    ],
    "general": [
        "Parsing abstract syntax tree of legacy source",
        "Injecting domain-specific system prompt",
        "Drafting modernized patch candidate",
    ],
}

SANDBOX_PHASES = [
    "Invoking Docker Engine API (FR-3.1)",
    "Instantiating ephemeral, non-root container (NFR-SEC-04)",
    "Mounting MCP-bounded workspace volume (read/write scoped)",
    "Executing script against provided test cases",
    "Capturing stdout / stderr / exit code (FR-3.2)",
]

diff_state = st.session_state["diff_state"].get(active_id, "readonly")
skip_to_action_bar = False

if f.status == FileStatus.QUEUED:
    st.markdown(
        '<div class="neo-card">'
        '<div class="neo-card-header"><div class="header-left"><div class="neo-card-title-group"><span class="num-badge">02</span> ⬜ QUEUED (WORKSPACE ESTABLISHED)</div><div class="header-desc">Use Case 0 complete. Awaiting manual trigger for AI processing.</div></div><div class="stat-pill yellow">QUEUED</div></div>'
        '</div>', unsafe_allow_html=True
    )
    skip_to_action_bar = True

elif f.status == FileStatus.TRANSLATING:
    skip_to_action_bar = True
    phases = TRANSLATING_PHASES.get(f.persona, TRANSLATING_PHASES["general"])
    placeholder = st.empty()
    
    for i in range(len(phases) + 1):
        current_node = "analyze" if i < len(phases) / 2 else "propose"
        
        with placeholder.container():
            st.markdown(render_langgraph_status(current_node), unsafe_allow_html=True)
            
            rows_html = []
            for j, p in enumerate(phases):
                if j < i: rows_html.append(f'<div class="thinking-step step-done" style="color: var(--neo-black); font-weight: 900;"><span class="step-icon">·</span>{html.escape(p)}</div>')
                elif j == i: rows_html.append(f'<div class="thinking-step step-active"><span class="step-icon">▸</span>{html.escape(p)}</div>')
                else: rows_html.append(f'<div class="thinking-step step-pending"><span class="step-icon">·</span>{html.escape(p)}</div>')
            
            st.markdown(
                f'<div class="neo-card neo-card-spotlight">'
                f'<div class="neo-card-header"><div class="header-left"><div class="neo-card-title-group"><span class="num-badge">02</span> 🔄 GENERATING PATCH (U001 & U002)</div><div class="header-desc">LLM is parsing legacy code and writing modern replacement.</div></div><div class="stat-pill yellow">TRANSLATING</div></div>'
                f'<div style="padding:16px 0;">{"".join(rows_html)}</div>'
                f'</div>', unsafe_allow_html=True
            )
            
        if i < len(phases):
            time.sleep(1.2)
            
    transition_to_sandbox(active_id)
    st.rerun()

elif f.status == FileStatus.SANDBOX_TESTING:
    skip_to_action_bar = True
    placeholder = st.empty()
    
    mock_logs = [
        ("info", "Invoking Docker Engine API (FR-3.1)..."),
        ("info", "Instantiating ephemeral, non-root container (NFR-SEC-04)..."),
        ("info", "Mounting MCP-bounded workspace volume (read/write scoped)..."),
        ("warn", "Starting execution of script against provided test cases..."),
    ]
    
    trace_lines = []
    if f.target_status == FileStatus.FAILED or f.target_traceback:
        for line in (f.target_traceback or "Traceback: unknown error").strip().split('\n'):
            trace_lines.append(("error", line))
    elif f.raw_traceback:
        for line in f.raw_traceback.strip().split('\n'):
            trace_lines.append(("error", line))
    else:
        trace_lines.append(("success", "Execution completed successfully. Exit code 0."))
    
    mock_logs.extend(trace_lines)
    
    current_logs = []
    for i in range(len(mock_logs) + 1):
        # We consider it "evaluate" phase once the logs start outputting the test results/traceback.
        # This roughly starts at index 4 (after the setup logs)
        current_node = "execute" if i <= 4 else "evaluate"
        
        with placeholder.container():
            st.markdown(render_langgraph_status(current_node), unsafe_allow_html=True)
            
            st.markdown(
                f'<div class="neo-card neo-card-spotlight">'
                f'<div class="neo-card-header"><div class="header-left"><div class="neo-card-title-group"><span class="num-badge">03</span> ⏳ SANDBOX EXECUTION (U003)</div><div class="header-desc">Executing containerized test suite against generated patch.</div></div><div class="stat-pill yellow">SANDBOX</div></div>'
                f'{render_terminal_logs(current_logs)}'
                f'</div>', unsafe_allow_html=True
            )
            
        if i < len(mock_logs):
            current_logs.append(mock_logs[i])
            time.sleep(0.6)
            
    time.sleep(0.5)
    resolve_sandbox_now(active_id)
    st.rerun()

# ============================================================================
# DIFF VIEWER & EDITOR
# ============================================================================
if not skip_to_action_bar and f.status not in (FileStatus.TRANSLATING, FileStatus.SANDBOX_TESTING):
    legacy_lines, ai_lines = f.legacy_source.splitlines(), f.ai_source.splitlines()
    total_lines = max(len(legacy_lines), len(ai_lines))
    load_full = st.session_state["load_full_file"].get(active_id, False)

    if load_full:
        window, out_of_range = (0, total_lines), []
    else:
        window = get_render_window(total_lines, f.primary_error_line)
        window, out_of_range = expand_window_for_related(window, f.related_error_lines, total_lines)

    if (window[0] > 0 or window[1] < total_lines) and not load_full:
        anchor_note = f" (centered on error at line {f.primary_error_line})" if f.primary_error_line else ""
        tcol1, tcol2 = st.columns([5, 1])
        with tcol1: st.markdown(f'<div class="truncation-banner">⚠️ Showing lines {window[0]+1:,}–{window[1]:,} of {total_lines:,}{anchor_note}</div>', unsafe_allow_html=True)
        with tcol2:
            if st.button("Load Full File ↓", key=f"load_full_btn__{active_id}", use_container_width=True):
                st.session_state["confirm_load_full"][active_id] = True
                st.rerun()
        if st.session_state["confirm_load_full"].get(active_id):
            st.warning(f"This file has {total_lines:,} lines and may slow down your browser. Continue?")
            ccol1, ccol2 = st.columns(2)
            with ccol1:
                if st.button("Yes, load full file", key=f"confirm_yes__{active_id}"):
                    st.session_state["load_full_file"][active_id] = True
                    st.session_state["confirm_load_full"][active_id] = False
                    st.rerun()
            with ccol2:
                if st.button("Cancel", key=f"confirm_no__{active_id}"):
                    st.session_state["confirm_load_full"][active_id] = False
                    st.rerun()

    for ln in out_of_range: st.caption(f"ℹ️ Related frame at line {ln} is outside the displayed range.")

    diff_state = st.session_state["diff_state"].get(active_id, "readonly")
    if diff_state == "editing":
        with st.container(key="edit_mode_box"):
            st.markdown("""
            <div class="neo-card-header bleed">
                <div class="header-left">
                    <div class="neo-card-title-group"><span class="num-badge">02</span> MANUAL EDIT MODE</div>
                    <div class="header-desc">Manually override AI-generated patch before re-testing.</div>
                </div>
                <div class="stat-pill yellow">EDIT</div>
            </div>
            """, unsafe_allow_html=True)

            ecol1, ecol2 = st.columns(2)
            with ecol1: 
                st.markdown("**LEGACY (READ-ONLY)**")
                st.code(f.legacy_source, language="python" if f.language == "python" else "r", line_numbers=True)
            with ecol2:
                st.markdown("**AI-GENERATED (EDITABLE)**")
                current_draft = st.session_state["edit_buffer"].get(active_id, f.ai_source)
                dynamic_height = max(200, min(800, len(current_draft.splitlines()) * 24))
                new_text = st.text_area("AI-generated source", value=current_draft, height=dynamic_height, key=f"textarea_widget__{active_id}", label_visibility="collapsed")
                if new_text != current_draft:
                    st.session_state["edit_buffer"][active_id] = new_text
                    mark_dirty(active_id)
                    st.rerun()
                
            save_col, cancel_col, _ = st.columns([2, 2, 6])
            with save_col:
                if st.button("💾 Save & Re-test", key=f"save_retest__{active_id}", use_container_width=True, type="primary"):
                    save_and_retest(active_id, st.session_state["edit_buffer"].get(active_id, f.ai_source))
                    st.rerun()
            with cancel_col:
                if st.button("Cancel", key=f"cancel_edit__{active_id}", use_container_width=True):
                    st.session_state["diff_state"][active_id] = "readonly"
                    st.rerun()
    else:
        rows = build_diff_rows(legacy_lines, ai_lines, f.language, window, f.primary_error_line, f.related_error_lines)
        st.markdown(render_diff_table(rows), unsafe_allow_html=True)
        editcol1, editcol2 = st.columns([5, 1])
        with editcol2:
            if f.status == FileStatus.FAILED:
                if st.button("✏️ Edit AI code", key=f"edit_retry__{active_id}", use_container_width=True):
                    start_edit(active_id)
                    st.rerun()

    # --- TRACEBACK CONSOLE ---
    if f.raw_traceback:
        frames = parse_traceback(f.raw_traceback, f.language, f.filename)
        groups = group_frames_for_disclosure(frames)
    
        tcol1, tcol2 = st.columns([8, 2])
        with tcol2:
            show_full = st.session_state["show_full_trace"].get(active_id, False)
            if st.button("Show full trace" if not show_full else "Collapse trace", key=f"toggle_full_trace__{active_id}", use_container_width=True):
                st.session_state["show_full_trace"][active_id] = not show_full
                st.rerun()

        with st.container(key="traceback_box"):
            st.markdown("""
            <div class="neo-card-header bleed">
                <div class="header-left">
                    <div class="neo-card-title-group"><span class="num-badge">03</span> TRACEBACK CONSOLE</div>
                    <div class="header-desc">Sandbox execution failed. See actionable frames above.</div>
                </div>
                <div class="stat-pill red">ERROR</div>
            </div>
            """, unsafe_allow_html=True)

            for gi, group in enumerate(groups):
                if group["type"] == "actionable":
                    fr = group["frame"]
                    jcol1, jcol2 = st.columns([8, 2])
                    with jcol1: 
                        st.markdown(f'<div class="trace-frame-row">▸ {fr.file_path.split("/")[-1]} : line {fr.line_number} : {fr.function_name}()</div>', unsafe_allow_html=True)
                    with jcol2:
                        if st.button("Jump ↑", key=f"jump__{active_id}__{gi}", use_container_width=True):
                            st.session_state["scroll_pulse"] = (active_id, fr.line_number)
                            st.toast(f"Jumped to line {fr.line_number} — pulsing amber in diff pane above.")
                else:
                    key = f"{active_id}__{gi}"
                    label = f'▶ {group["count"]} internal frame(s) hidden'
                    if st.session_state["show_full_trace"].get(active_id, False):
                        for nf in group["frames"]: 
                            st.markdown(f'<div class="trace-noise-row">　 {nf.file_path.split("/")[-1]} : line {nf.line_number} : {nf.function_name}()</div>', unsafe_allow_html=True)
                    else:
                        ncol1, ncol2 = st.columns([8, 2])
                        with ncol1: 
                            st.markdown(f'<div class="trace-noise-row">{label}</div>', unsafe_allow_html=True)
                        with ncol2:
                            if st.button("Expand", key=f"expand_noise__{key}", use_container_width=True):
                                st.session_state["trace_expanded"][key] = True
                                st.rerun()
                        if st.session_state["trace_expanded"].get(key, False):
                            for nf in group["frames"]: 
                                st.markdown(f'<div class="trace-noise-row">　 {nf.file_path.split("/")[-1]} : line {nf.line_number} : {nf.function_name}()</div>', unsafe_allow_html=True)
                            
        pulse = st.session_state.get("scroll_pulse")
        if pulse and pulse[0] == active_id: 
            st.info(f"🟠 Diff pane line {pulse[1]} highlighted (spatial link established).")

if st.session_state["rejecting"].get(active_id, False):
    st.markdown("**Rejection note**")
    note = st.text_area("Reason for rejection", value=f.rejection_note, key=f"reject_note__{active_id}", height=80)
    rcol1, rcol2 = st.columns(2)
    with rcol1:
        if st.button("Confirm Reject", key=f"confirm_reject__{active_id}", type="primary"):
            reject_file(active_id, note)
            st.rerun()
    with rcol2:
        if st.button("Cancel", key=f"cancel_reject__{active_id}"):
            st.session_state["rejecting"][active_id] = False
            st.rerun()

if f.status == FileStatus.REJECTED and f.rejection_note and not st.session_state["rejecting"].get(active_id, False):
    st.caption(f"🚫 Rejection note: {f.rejection_note}")

# ============================================================================
# STICKY ACTION BAR
# ============================================================================
action_bar = st.container(key="action_bar")

with action_bar:
    st.markdown("""
    <div class="neo-card-header bleed">
        <div class="header-left">
            <div class="neo-card-title-group"><span class="num-badge">04</span> ACTION CENTER</div>
            <div class="header-desc">Review complete? Commit or reject the patch.</div>
        </div>
        <div class="stat-pill blue">READY</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    acol1, acol2, acol3 = st.columns(3)
    approve_eligible = f.status == FileStatus.PASSED
    reject_eligible = f.status in (FileStatus.FAILED, FileStatus.PASSED, FileStatus.EDITED_PENDING)

    with acol1:
        if st.button("✅ Approve", key=f"approve__{active_id}", use_container_width=True, disabled=not approve_eligible, help=None if approve_eligible else "Manual edits must pass sandbox verification before approval."):
            approve_file(active_id)
            st.rerun()
    
    with acol2:
        if f.status == FileStatus.QUEUED:
            if st.button("🚀 Start AI Translation", key=f"start_trans__{active_id}", use_container_width=True, type="primary"):
                start_translation(active_id)
                st.rerun()
        else:
            save_retest_primary = f.status == FileStatus.EDITED_PENDING
            if st.button("🔄 Save & Re-test" if save_retest_primary else "🔄 Re-test", key=f"action_bar_retest__{active_id}", use_container_width=True, disabled=f.status not in (FileStatus.FAILED, FileStatus.EDITED_PENDING), type="primary" if save_retest_primary else "secondary"):
                if diff_state == "editing": save_and_retest(active_id, st.session_state["edit_buffer"].get(active_id, f.ai_source))
                else: run_sandbox_simulation(active_id)
                st.rerun()
                
    with acol3:
        if st.button("❌ Reject", key=f"reject_btn__{active_id}", use_container_width=True, disabled=not reject_eligible):
            st.session_state["rejecting"][active_id] = True
            st.rerun()