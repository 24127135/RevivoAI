import html
from nicegui import ui
from backend.models import ProjectFile, FileStatus
from backend.logic import tokenize_line

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

def render_diff_unified(rows: list[dict]) -> str:
    out = ['<table class="diff-unified-table">']
    for row in rows:
        if row["type"] == "fold":
            out.append(f'<tr><td colspan="3" class="fold-row">⋯ {row["count"]} unchanged lines ⋯</td></tr>')
            continue
            
        marker = {"add": "+", "remove": "-", "context": " "}[row["type"]]
        cls = f'diff-row-{row["type"]}'
        ln = row["new_ln"] if row["type"] != "remove" else row["old_ln"]
        out.append(
            f'<tr class="{cls}">'
            f'<td class="ln-col">{ln or ""}</td>'
            f'<td class="marker-col">{marker}</td>'
            f'<td class="code-col">{row["html"]}</td>'
            f'</tr>'
        )
    out.append("</table>")
    return "".join(out)

def render_diff_split(paired_rows: list[dict]) -> str:
    out = ['<table class="diff-split-table">']
    for row in paired_rows:
        if row["type"] == "fold":
            out.append(f'<tr><td colspan="4" class="fold-row">⋯ {row["count"]} unchanged lines ⋯</td></tr>')
            continue
            
        old_filler = "" if row.get("old_html") is not None else " filler-cell"
        new_filler = "" if row.get("new_html") is not None else " filler-cell"
        
        # Determine background classes based on type
        if row["type"] == "modify":
            old_cls = " modified-side"
        elif row["type"] == "remove":
            old_cls = " removed-side"
        else:
            old_cls = ""
        new_cls = " added-side" if row["type"] in ("add", "modify") else ""
        
        out.append(
            '<tr>'
            f'<td class="ln-col{old_filler}{old_cls}">{row.get("old_ln") or ""}</td>'
            f'<td class="code-col{old_filler}{old_cls}">{row.get("old_html") or ""}</td>'
            f'<td class="ln-col{new_filler}{new_cls}">{row.get("new_ln") or ""}</td>'
            f'<td class="code-col{new_filler}{new_cls}">{row.get("new_html") or ""}</td>'
            '</tr>'
        )
    out.append("</table>")
    return "".join(out)

def get_diff_html(diff_data: dict) -> str:
    """Returns the raw HTML string for the diff table."""
    out = ['<div class="neo-card neo-card-spotlight">']
    title = diff_data.get("title", "DIFF VIEWER")
    desc = diff_data.get("desc", "Comparing legacy AST to AI-generated candidate patch.")
    pill = diff_data.get("pill", "DIFF")
    out.append(f'<div class="neo-card-header compact-header"><div class="header-left"><div class="neo-card-title-group"> {title}</div><div class="header-desc">{desc}</div></div><div class="stat-pill green">{pill}</div></div>')
    out.append('<div class="diff-scroll" style="border-top: 1px solid var(--border-color);">')
    
    if diff_data["mode"] == "inline":
        out.append(render_diff_unified(diff_data["rows"]))
    else:
        out.append(render_diff_split(diff_data["rows"]))
        
    out.append('</div>')
    out.append('</div>')
    return "".join(out)
def get_code_viewer_html(code: str, language: str, title: str = "SOURCE CODE", desc: str = "", pill: str = "VIEWER") -> str:
    """Returns the raw HTML string for a standalone code viewer."""
    out = ['<div class="neo-card neo-card-spotlight">']
    out.append(f'<div class="neo-card-header compact-header"><div class="header-left"><div class="neo-card-title-group"> {title}</div><div class="header-desc">{desc}</div></div><div class="stat-pill green">{pill}</div></div>')
    out.append('<div class="diff-scroll" style="border-top: 1px solid var(--border-color); background: #ffffff;">')
    out.append('<table class="viewer-table">')
    
    lines = code.splitlines()
    for i, line in enumerate(lines):
        ln = i + 1
        html_code = tokenize_line(line, language)
        out.append(
            f'<tr class="viewer-row">'
            f'<td class="viewer-ln-col">{ln}</td>'
            f'<td class="viewer-code-col">{html_code}</td>'
            f'</tr>'
        )
        
    out.append('</table>')
    out.append('</div>')
    out.append('</div>')
    return "".join(out)

def get_code_pane_html(code: str, language: str) -> str:
    """Line-numbered read-only code pane with no card/header chrome, for embedding inside other panels."""
    out = ['<table class="viewer-table">']
    for i, line in enumerate(code.splitlines()):
        ln = i + 1
        html_code = tokenize_line(line, language)
        out.append(f'<tr class="viewer-row"><td class="viewer-ln-col">{ln}</td><td class="viewer-code-col">{html_code}</td></tr>')
    out.append('</table>')
    return "".join(out)