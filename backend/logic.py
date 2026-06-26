import re
import difflib
from typing import Optional
from pygments import highlight
from pygments.lexers import PythonLexer, SLexer, CLexer
from pygments.formatters import HtmlFormatter
from .models import StackFrame, DiffRow

# --- TRACEBACK PARSER ---
def _is_actionable(file_path: str, project_filename: str) -> bool:
    return file_path.endswith(project_filename)

def parse_python_traceback(raw: str, project_filename: str) -> list[StackFrame]:
    frames: list[StackFrame] = []
    pattern = re.compile(r'File "(?P<path>[^"]+)", line (?P<line>\d+), in (?P<func>\S+)')
    lines = raw.splitlines()
    for i, line in enumerate(lines):
        m = pattern.search(line)
        if not m: continue
        snippet = ""
        if i + 1 < len(lines) and not lines[i + 1].strip().startswith("File "):
            candidate = lines[i + 1].strip()
            if candidate and not candidate.startswith("Traceback"):
                snippet = candidate
        path = m.group("path")
        frames.append(StackFrame(
            file_path=path, line_number=int(m.group("line")), function_name=m.group("func"),
            code_snippet=snippet, is_actionable=_is_actionable(path, project_filename)
        ))
    return frames

def parse_r_traceback(raw: str, project_filename: str) -> list[StackFrame]:
    frames: list[StackFrame] = []
    pattern = re.compile(r'^\s*\d+:\s+(?P<func>[\w.:<>]+)\((?P<args>.*?)\)\s*(?:at\s+(?P<path>\S+)#(?P<line>\d+))?')
    raw_frames = []
    for line in raw.splitlines():
        m = pattern.match(line)
        if not m or not m.group("path"): continue
        path = m.group("path")
        raw_frames.append(StackFrame(
            file_path=path, line_number=int(m.group("line")), function_name=m.group("func"),
            code_snippet=f'{m.group("func")}({m.group("args")})', is_actionable=_is_actionable(path, project_filename)
        ))
    raw_frames.reverse()
    frames.extend(raw_frames)
    return frames

def parse_c_traceback(raw: str, project_filename: str) -> list[StackFrame]:
    frames: list[StackFrame] = []
    pattern = re.compile(r'at\s+(?P<path>[\w./\\-]+):(?P<line>\d+)\s+in\s+(?P<func>\w+)\(\)')
    for line in raw.splitlines():
        m = pattern.search(line)
        if not m: continue
        path = m.group("path")
        frames.append(StackFrame(
            file_path=path, line_number=int(m.group("line")), function_name=m.group("func"),
            code_snippet=line.strip(), is_actionable=_is_actionable(path, project_filename)
        ))
    return frames

def parse_traceback(raw: str, language: str, project_filename: str) -> list[StackFrame]:
    if not raw.strip(): return []
    if language == "r": return parse_r_traceback(raw, project_filename)
    if language == "c": return parse_c_traceback(raw, project_filename)
    return parse_python_traceback(raw, project_filename)

def compute_anchors(frames: list[StackFrame]) -> tuple[int | None, list[int]]:
    actionable = [f for f in frames if f.is_actionable]
    if not actionable: return None, []
    primary = actionable[-1].line_number 
    related = sorted({f.line_number for f in actionable[:-1]} - {primary})
    return primary, related

def group_frames_for_disclosure(frames: list[StackFrame]) -> list[dict]:
    groups: list[dict] = []
    noise_buffer: list[StackFrame] = []
    def flush_noise():
        if noise_buffer:
            groups.append({"type": "noise", "frames": list(noise_buffer), "count": len(noise_buffer)})
            noise_buffer.clear()
    for f in frames:
        if f.is_actionable:
            flush_noise()
            groups.append({"type": "actionable", "frame": f})
        else:
            noise_buffer.append(f)
    flush_noise()
    return groups

# --- DIFF ENGINE ---
RENDER_WINDOW_RADIUS = 150
OUT_OF_WINDOW_MARGIN = 150

LEXER_MAP = {"python": PythonLexer(), "r": SLexer(), "c": CLexer()}
_FORMATTER = HtmlFormatter(nowrap=True)

def pygments_style_defs() -> str:
    return HtmlFormatter().get_style_defs(".highlight")

def tokenize_line(raw_line: str, language: str) -> str:
    lexer = LEXER_MAP.get(language, LEXER_MAP["python"])
    if raw_line == "": return ""
    out = highlight(raw_line + "\n", lexer, _FORMATTER)
    return out.rstrip("\n")

def get_render_window(total_lines: int, primary_anchor: Optional[int]) -> tuple[int, int]:
    if primary_anchor is None: return (0, min(total_lines, RENDER_WINDOW_RADIUS * 2))
    start = max(0, primary_anchor - RENDER_WINDOW_RADIUS)
    end = min(total_lines, primary_anchor + RENDER_WINDOW_RADIUS)
    return (start, end)

def expand_window_for_related(window: tuple[int, int], related_lines: list[int], total_lines: int) -> tuple[tuple[int, int], list[int]]:
    start, end = window
    out_of_range: list[int] = []
    for ln in related_lines:
        idx = ln - 1
        if start <= idx < end: continue
        dist = (start - idx) if idx < start else (idx - end + 1)
        if dist <= OUT_OF_WINDOW_MARGIN:
            start = min(start, idx)
            end = max(end, idx + 1)
        else:
            out_of_range.append(ln)
    return (max(0, start), min(total_lines, end)), out_of_range

def _wrap_amber(token_html: str, kind: str) -> str:
    if token_html == "": token_html = "&nbsp;"
    css_class = "amber-primary" if kind == "primary" else "amber-related"
    return f'<span class="{css_class}">{token_html}</span>'

def build_diff_rows(legacy_lines: list[str], ai_lines: list[str], language: str, window: tuple[int, int], primary_error_line: Optional[int], related_error_lines: list[int]) -> list[DiffRow]:
    start, end = window
    leg_slice, ai_slice = legacy_lines[start:end], ai_lines[start:end]
    matcher = difflib.SequenceMatcher(a=leg_slice, b=ai_slice, autojunk=False)
    opcodes = matcher.get_opcodes()
    rows: list[DiffRow] = []

    def make_cell(line_no_0idx: Optional[int], raw: Optional[str]) -> tuple[Optional[int], Optional[str]]:
        if line_no_0idx is None or raw is None: return None, None
        line_no_1idx = line_no_0idx + 1 
        token_html = tokenize_line(raw, language)
        if line_no_1idx == primary_error_line: token_html = _wrap_amber(token_html, "primary")
        elif line_no_1idx in related_error_lines: token_html = _wrap_amber(token_html, "related")
        return line_no_1idx, token_html

    for op, i1, i2, j1, j2 in opcodes:
        if op == "equal":
            for k in range(i2 - i1):
                l_no, l_html = make_cell(start + i1 + k, leg_slice[i1 + k])
                a_no, a_html = make_cell(start + j1 + k, ai_slice[j1 + k])
                rows.append(DiffRow(l_no, l_html, a_no, a_html, "unchanged"))
        elif op == "delete":
            for k in range(i2 - i1):
                l_no, l_html = make_cell(start + i1 + k, leg_slice[i1 + k])
                rows.append(DiffRow(l_no, l_html, None, None, "removed"))
        elif op == "insert":
            for k in range(j2 - j1):
                a_no, a_html = make_cell(start + j1 + k, ai_slice[j1 + k])
                rows.append(DiffRow(None, None, a_no, a_html, "added"))
        elif op == "replace":
            paired = min(i2 - i1, j2 - j1)
            for k in range(paired):
                l_no, l_html = make_cell(start + i1 + k, leg_slice[i1 + k])
                a_no, a_html = make_cell(start + j1 + k, ai_slice[j1 + k])
                rows.append(DiffRow(l_no, l_html, a_no, a_html, "modified"))
            if (i2 - i1) > paired:
                for k in range(paired, i2 - i1):
                    l_no, l_html = make_cell(start + i1 + k, leg_slice[i1 + k])
                    rows.append(DiffRow(l_no, l_html, None, None, "removed"))
            if (j2 - j1) > paired:
                for k in range(paired, j2 - j1):
                    a_no, a_html = make_cell(start + j1 + k, ai_slice[j1 + k])
                    rows.append(DiffRow(None, None, a_no, a_html, "added"))
    return rows