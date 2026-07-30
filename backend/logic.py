"""
backend/logic.py
-----------------
Core backend logic: traceback parsing and error-frame analysis.

All Pygments-based tokenization, diff-row building, and render-window
helpers have been removed — Monaco Editor handles all of that in the
frontend now.
"""

import re
from .models import StackFrame

# ---------------------------------------------------------------------------
# TRACEBACK PARSER
# ---------------------------------------------------------------------------

def _is_actionable(file_path: str, project_filename: str) -> bool:
    return file_path.endswith(project_filename)


def parse_python_traceback(raw: str, project_filename: str) -> list[StackFrame]:
    frames: list[StackFrame] = []
    pattern = re.compile(
        r'File "(?P<path>[^"]+)", line (?P<line>\d+), in (?P<func>\S+)'
    )
    lines = raw.splitlines()
    for i, line in enumerate(lines):
        m = pattern.search(line)
        if not m:
            continue
        snippet = ""
        if i + 1 < len(lines) and not lines[i + 1].strip().startswith("File "):
            candidate = lines[i + 1].strip()
            if candidate and not candidate.startswith("Traceback"):
                snippet = candidate
        path = m.group("path")
        frames.append(StackFrame(
            file_path=path,
            line_number=int(m.group("line")),
            function_name=m.group("func"),
            code_snippet=snippet,
            is_actionable=_is_actionable(path, project_filename),
        ))
    return frames


def parse_r_traceback(raw: str, project_filename: str) -> list[StackFrame]:
    frames: list[StackFrame] = []
    pattern = re.compile(
        r'^\s*\d+:\s+(?P<func>[\w.:<>]+)\((?P<args>.*?)\)\s*'
        r'(?:at\s+(?P<path>\S+)#(?P<line>\d+))?'
    )
    raw_frames = []
    for line in raw.splitlines():
        m = pattern.match(line)
        if not m or not m.group("path"):
            continue
        path = m.group("path")
        raw_frames.append(StackFrame(
            file_path=path,
            line_number=int(m.group("line")),
            function_name=m.group("func"),
            code_snippet=f'{m.group("func")}({m.group("args")})',
            is_actionable=_is_actionable(path, project_filename),
        ))
    raw_frames.reverse()
    frames.extend(raw_frames)
    return frames


def parse_c_traceback(raw: str, project_filename: str) -> list[StackFrame]:
    frames: list[StackFrame] = []
    pattern = re.compile(
        r'at\s+(?P<path>[\w./\\-]+):(?P<line>\d+)\s+in\s+(?P<func>\w+)\(\)'
    )
    for line in raw.splitlines():
        m = pattern.search(line)
        if not m:
            continue
        path = m.group("path")
        frames.append(StackFrame(
            file_path=path,
            line_number=int(m.group("line")),
            function_name=m.group("func"),
            code_snippet=line.strip(),
            is_actionable=_is_actionable(path, project_filename),
        ))
    return frames


def parse_traceback(raw: str, language: str, project_filename: str) -> list[StackFrame]:
    if not raw.strip():
        return []
    if language == "r":
        return parse_r_traceback(raw, project_filename)
    if language == "c":
        return parse_c_traceback(raw, project_filename)
    return parse_python_traceback(raw, project_filename)


# ---------------------------------------------------------------------------
# ERROR FRAME ANALYSIS
# ---------------------------------------------------------------------------

def compute_anchors(frames: list[StackFrame]) -> tuple[int | None, list[int]]:
    actionable = [f for f in frames if f.is_actionable]
    if not actionable:
        return None, []
    primary = actionable[-1].line_number
    related = sorted({f.line_number for f in actionable[:-1]} - {primary})
    return primary, related


def group_frames_for_disclosure(frames: list[StackFrame]) -> list[dict]:
    groups: list[dict] = []
    noise_buffer: list[StackFrame] = []

    def flush_noise():
        if noise_buffer:
            groups.append({
                "type":   "noise",
                "frames": list(noise_buffer),
                "count":  len(noise_buffer),
            })
            noise_buffer.clear()

    for f in frames:
        if f.is_actionable:
            flush_noise()
            groups.append({"type": "actionable", "frame": f})
        else:
            noise_buffer.append(f)
    flush_noise()
    return groups