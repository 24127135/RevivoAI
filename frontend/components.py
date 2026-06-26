import time
import html
import streamlit as st
from backend.models import ProjectFile, FileStatus, DiffRow

# --- THINKING INDICATOR LOGIC ---
TRANSLATING_PHASES = {
    "systems_engineer": [
        "Parsing abstract syntax tree of legacy source (FR-2.1)",
        "Injecting Systems Engineering persona prompt",
        "Cross-referencing xv6 inode/block addressing conventions",
        "Drafting modernized patch candidate",
        "Routing patch to Autonomous Sandbox Execution (U003)",
    ],
    "data_scientist": [
        "Parsing abstract syntax tree of legacy source (FR-2.2)",
        "Injecting Quantitative Data Science persona prompt",
        "Mapping legacy lexicon logic to transformer-based TRV scoring",
        "Drafting modernized patch candidate",
        "Routing patch to Autonomous Sandbox Execution (U003)",
    ],
    "general": [
        "Parsing abstract syntax tree of legacy source",
        "Injecting domain-specific system prompt",
        "Drafting modernized patch candidate",
        "Routing patch to Autonomous Sandbox Execution (U003)",
    ],
}

SANDBOX_PHASES = [
    "Invoking Docker Engine API (FR-3.1)",
    "Instantiating ephemeral, non-root container (NFR-SEC-04)",
    "Mounting MCP-bounded workspace volume (read/write scoped)",
    "Executing script against provided test cases",
    "Capturing stdout / stderr / exit code (FR-3.2)",
]

def _phase_progress_index(file_id: str, num_phases: int, seconds_per_phase: float = 2.2) -> int:
    started_at = st.session_state["thinking_started_at"].get(file_id)
    if started_at is None:
        started_at = time.time()
        st.session_state["thinking_started_at"][file_id] = started_at
    elapsed = time.time() - started_at
    idx = int(elapsed // seconds_per_phase)
    return min(idx, num_phases - 1)

def render_thinking_indicator(f: ProjectFile) -> None:
    if f.status == FileStatus.QUEUED:
        st.markdown(
            '<div class="neo-card">'
            '<div class="neo-card-header"><div class="header-left"><div class="neo-card-title-group"><span class="num-badge">02</span><span class="thinking-pulse-dot" style="animation-duration:2.4s;"></span> QUEUED (WORKSPACE ESTABLISHED)</div><div class="header-desc">Use Case 0 complete. Ready for Use Case 1 & 2 AI processing.</div></div><div class="stat-pill yellow">QUEUED</div></div>'
            '<div style="padding:16px;">'
            '<div class="thinking-step step-pending"><span class="step-icon">·</span>Awaiting manual trigger to parse legacy code and generate modern patch.</div>'
            '</div>'
            '</div>', unsafe_allow_html=True
        )
        return

    if f.status == FileStatus.TRANSLATING:
        phases = TRANSLATING_PHASES.get(f.persona, TRANSLATING_PHASES["general"])
        # Explicitly label U001 & U002 here for the loading state!
        title, footer = "🔄 LLM Provider generating patch (U001 & U002)", "Step governed by FR-2.1 / FR-2.2 persona routing"
        pill_color, pill_label = "yellow", "TRANSLATE"
    elif f.status == FileStatus.SANDBOX_TESTING:
        phases = SANDBOX_PHASES
        # Explicitly label U003 here
        title, footer = "⏳ Autonomous Sandbox Execution (U003)", "Resource caps enforced per NFR-RES-01 / NFR-RES-02"
        pill_color, pill_label = "yellow", "SANDBOX"
    else:
        return

    active_idx = _phase_progress_index(f.file_id, len(phases))
    persona_class = f" persona-{f.persona}" if f.persona != "general" else ""
    
    rows_html = []
    for i, phase_text in enumerate(phases):
        if i < active_idx: cls, icon = "step-done", "✅"
        elif i == active_idx: cls, icon = "step-active", "▸"
        else: cls, icon = "step-pending", "·"
        rows_html.append(f'<div class="thinking-step {cls}"><span class="step-icon">{icon}</span>{html.escape(phase_text)}</div>')

    st.markdown(
        f'<div class="neo-card neo-card-spotlight{persona_class}">'
        f'<div class="neo-card-header"><div class="header-left"><div class="neo-card-title-group"><span class="num-badge">02</span><span class="thinking-pulse-dot"></span> {title}</div><div class="header-desc">{footer}</div></div><div class="stat-pill {pill_color}">{pill_label}</div></div>'
        f'<div style="padding:16px 0;">{"".join(rows_html)}</div>'
        f'</div>', unsafe_allow_html=True
    )

# --- DIFF TABLE RENDERER ---
CELL_BG_LEGACY = {"removed": "var(--diff-removed-bg)", "modified": "var(--diff-removed-bg)"}
CELL_BG_AI = {"added": "var(--diff-added-bg)", "modified": "var(--diff-added-bg)"}

def render_diff_table(rows: list[DiffRow]) -> str:
    # 1. Added 'neo-card-spotlight' to turn the card and header yellow
    out = ['<div class="neo-card neo-card-spotlight">']
    
    out.append('<div class="neo-card-header"><div class="header-left"><div class="neo-card-title-group"><span class="num-badge">02</span> DIFF VIEWER</div><div class="header-desc">Comparing legacy AST to AI-generated candidate patch.</div></div><div class="stat-pill green">DIFF</div></div>')
    
    # 2. Added a 3px black top border to perfectly separate the yellow header from the white code scroll area
    out.append('<div class="diff-scroll" style="border-top: 3px solid var(--neo-black);"><table class="diff-table">')
    out.append('<tr class="diff-header-row"><td class="ln-col header-cell">#</td><td class="code-col header-cell">LEGACY</td><td class="ln-col header-cell">#</td><td class="code-col header-cell">AI-GENERATED</td></tr>')
    
    for row in rows:
        leg_bg = CELL_BG_LEGACY.get(row.diff_type, "transparent")
        ai_bg = CELL_BG_AI.get(row.diff_type, "transparent")
        leg_ln, ai_ln = row.legacy_line_no or "", row.ai_line_no or ""
        leg_html, ai_html = row.legacy_html or "", row.ai_html or ""
        leg_filler = "" if row.legacy_html is not None else " filler-cell"
        ai_filler = "" if row.ai_html is not None else " filler-cell"
        out.append(f'<tr class="diff-row" data-line="{leg_ln or ai_ln}"><td class="ln-col">{leg_ln}</td><td class="code-col{leg_filler}" style="background:{leg_bg}">{leg_html}</td><td class="ln-col">{ai_ln}</td><td class="code-col{ai_filler}" style="background:{ai_bg}">{ai_html}</td></tr>')
    
    out.append("</table></div>")
    out.append('</div>')
    return "".join(out)