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
    light = HtmlFormatter(style="default").get_style_defs(".code-col")
    viewer_light = HtmlFormatter(style="default").get_style_defs(".viewer-code-col")
    return light + "\n" + viewer_light

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

INLINE_LINE_THRESHOLD = 150

def choose_diff_mode(total_lines: int, viewport_narrow: bool = False, user_override: Optional[str] = None) -> str:
    if user_override in ("inline", "split"):
        return user_override
    if viewport_narrow:
        return "inline"
    return "inline" if total_lines <= INLINE_LINE_THRESHOLD else "split"

def inline_word_diff(old_line: str, new_line: str) -> tuple[str, str]:
    import html
    sm = difflib.SequenceMatcher(None, old_line, new_line)
    old_html, new_html = [], []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        old_seg = html.escape(old_line[i1:i2])
        new_seg = html.escape(new_line[j1:j2])
        if tag == "equal":
            old_html.append(old_seg)
            new_html.append(new_seg)
        else:
            if old_seg:
                old_html.append(f'<mark class="diff-char-removed">{old_seg}</mark>')
            if new_seg:
                new_html.append(f'<mark class="diff-char-added">{new_seg}</mark>')
    return "".join(old_html), "".join(new_html)

FOLD_THRESHOLD = 6

def fold_context_runs(rows: list[dict]) -> list[dict]:
    out, run = [], []
    def flush():
        if len(run) > FOLD_THRESHOLD:
            out.append({"type": "fold", "count": len(run), "rows": list(run)})
        else:
            out.extend(run)
        run.clear()
    for row in rows:
        if row["type"] == "context":
            run.append(row)
        else:
            flush()
            out.append(row)
    flush()
    return out

def build_diff_rows(legacy_lines: list[str], ai_lines: list[str], language: str, window: tuple[int, int], primary_error_line: Optional[int], related_error_lines: list[int], disable_folding: bool = False, mode_override: Optional[str] = None) -> dict:
    start, end = window
    leg_slice, ai_slice = legacy_lines[start:end], ai_lines[start:end]
    matcher = difflib.SequenceMatcher(a=leg_slice, b=ai_slice, autojunk=False)
    opcodes = matcher.get_opcodes()
    
    total_lines = max(len(legacy_lines), len(ai_lines))
    mode = choose_diff_mode(total_lines, user_override=mode_override)
    
    def _wrap_if_needed(line_no_1idx: int, html_str: str) -> str:
        if line_no_1idx == primary_error_line: return _wrap_amber(html_str, "primary")
        elif line_no_1idx in related_error_lines: return _wrap_amber(html_str, "related")
        return html_str

    if mode == "inline":
        rows = []
        for op, i1, i2, j1, j2 in opcodes:
            if op == "equal":
                for k in range(i2 - i1):
                    l_no = start + i1 + k + 1
                    a_no = start + j1 + k + 1
                    h = tokenize_line(leg_slice[i1 + k], language)
                    h = _wrap_if_needed(a_no, h)
                    rows.append({"type": "context", "old_ln": l_no, "new_ln": a_no, "html": h})
            elif op == "delete":
                for k in range(i2 - i1):
                    l_no = start + i1 + k + 1
                    import html
                    h = html.escape(leg_slice[i1 + k])
                    h = _wrap_if_needed(l_no, h)
                    rows.append({"type": "remove", "old_ln": l_no, "new_ln": None, "html": h})
            elif op == "insert":
                for k in range(j2 - j1):
                    a_no = start + j1 + k + 1
                    import html
                    h = html.escape(ai_slice[j1 + k])
                    h = _wrap_if_needed(a_no, h)
                    rows.append({"type": "add", "old_ln": None, "new_ln": a_no, "html": h})
            elif op == "replace":
                paired = min(i2 - i1, j2 - j1)
                for k in range(paired):
                    l_no = start + i1 + k + 1
                    a_no = start + j1 + k + 1
                    o_html, n_html = inline_word_diff(leg_slice[i1 + k], ai_slice[j1 + k])
                    rows.append({"type": "remove", "old_ln": l_no, "new_ln": None, "html": _wrap_if_needed(l_no, o_html)})
                    rows.append({"type": "add", "old_ln": None, "new_ln": a_no, "html": _wrap_if_needed(a_no, n_html)})
                if (i2 - i1) > paired:
                    for k in range(paired, i2 - i1):
                        l_no = start + i1 + k + 1
                        import html
                        h = html.escape(leg_slice[i1 + k])
                        rows.append({"type": "remove", "old_ln": l_no, "new_ln": None, "html": _wrap_if_needed(l_no, h)})
                if (j2 - j1) > paired:
                    for k in range(paired, j2 - j1):
                        a_no = start + j1 + k + 1
                        import html
                        h = html.escape(ai_slice[j1 + k])
                        rows.append({"type": "add", "old_ln": None, "new_ln": a_no, "html": _wrap_if_needed(a_no, h)})
        return {"mode": "inline", "rows": rows if disable_folding else fold_context_runs(rows)}
        
    else: # split
        rows = []
        for op, i1, i2, j1, j2 in opcodes:
            if op == "equal":
                for k in range(i2 - i1):
                    l_no = start + i1 + k + 1
                    a_no = start + j1 + k + 1
                    h = tokenize_line(leg_slice[i1 + k], language)
                    l_h = _wrap_if_needed(l_no, h)
                    a_h = _wrap_if_needed(a_no, h)
                    rows.append({"type": "context", "old_ln": l_no, "old_html": l_h, "new_ln": a_no, "new_html": a_h})
            elif op == "delete":
                for k in range(i2 - i1):
                    l_no = start + i1 + k + 1
                    import html
                    h = html.escape(leg_slice[i1 + k])
                    rows.append({"type": "remove", "old_ln": l_no, "old_html": _wrap_if_needed(l_no, h), "new_ln": None, "new_html": None})
            elif op == "insert":
                for k in range(j2 - j1):
                    a_no = start + j1 + k + 1
                    import html
                    h = html.escape(ai_slice[j1 + k])
                    rows.append({"type": "add", "old_ln": None, "old_html": None, "new_ln": a_no, "new_html": _wrap_if_needed(a_no, h)})
            elif op == "replace":
                paired = min(i2 - i1, j2 - j1)
                for k in range(paired):
                    l_no = start + i1 + k + 1
                    a_no = start + j1 + k + 1
                    o_html, n_html = inline_word_diff(leg_slice[i1 + k], ai_slice[j1 + k])
                    rows.append({"type": "modify", "old_ln": l_no, "old_html": _wrap_if_needed(l_no, o_html), "new_ln": a_no, "new_html": _wrap_if_needed(a_no, n_html)})
                if (i2 - i1) > paired:
                    for k in range(paired, i2 - i1):
                        l_no = start + i1 + k + 1
                        import html
                        h = html.escape(leg_slice[i1 + k])
                        rows.append({"type": "remove", "old_ln": l_no, "old_html": _wrap_if_needed(l_no, h), "new_ln": None, "new_html": None})
                if (j2 - j1) > paired:
                    for k in range(paired, j2 - j1):
                        a_no = start + j1 + k + 1
                        import html
                        h = html.escape(ai_slice[j1 + k])
                        rows.append({"type": "add", "old_ln": None, "old_html": None, "new_ln": a_no, "new_html": _wrap_if_needed(a_no, h)})
        return {"mode": "split", "rows": rows if disable_folding else fold_context_runs(rows)}