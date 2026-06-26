from dataclasses import dataclass, field
from enum import Enum
from typing import Literal, Optional

class FileStatus(str, Enum):
    QUEUED = "QUEUED"
    TRANSLATING = "TRANSLATING"
    SANDBOX_TESTING = "SANDBOX_TESTING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    EDITED_PENDING = "EDITED_PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

STATUS_META = {
    FileStatus.QUEUED:          {"icon": "⬜", "label": "Queued",          "color": "yellow", "approve_eligible": False},
    FileStatus.TRANSLATING:     {"icon": "🔄", "label": "Translating",     "color": "yellow", "approve_eligible": False},
    FileStatus.SANDBOX_TESTING: {"icon": "⏳", "label": "Sandbox Testing", "color": "yellow", "approve_eligible": False},
    FileStatus.PASSED:          {"icon": "✅", "label": "Passed",          "color": "green",  "approve_eligible": True},
    FileStatus.FAILED:          {"icon": "❌", "label": "Failed",          "color": "red",    "approve_eligible": False},
    FileStatus.EDITED_PENDING:  {"icon": "✏️", "label": "Edited, Pending", "color": "yellow", "approve_eligible": False},
    FileStatus.APPROVED:        {"icon": "✅", "label": "Approved",        "color": "green",  "approve_eligible": None},  
    FileStatus.REJECTED:        {"icon": "🚫", "label": "Rejected",        "color": "red",    "approve_eligible": False},
}

WARNING_STATUSES = {FileStatus.FAILED, FileStatus.EDITED_PENDING}

@dataclass
class StackFrame:
    file_path: str
    line_number: int
    function_name: str
    code_snippet: str
    is_actionable: bool 

@dataclass
class DiffRow:
    legacy_line_no: Optional[int]
    legacy_html: Optional[str]
    ai_line_no: Optional[int]
    ai_html: Optional[str]
    diff_type: Literal["unchanged", "added", "removed", "modified"]

@dataclass
class ProjectFile:
    file_id: str
    path: str 
    legacy_source: str
    ai_source: str
    status: FileStatus
    language: Literal["python", "r", "c"]
    raw_traceback: str = ""
    rejection_note: str = ""
    primary_error_line: Optional[int] = None
    related_error_lines: list = field(default_factory=list)
    persona: Literal["systems_engineer", "data_scientist", "general"] = "general"
    use_case: str = ""  
    
    # --- NEW: Hidden target fields to mock the async workflow ---
    target_ai_source: str = ""
    target_traceback: str = ""
    target_status: Optional[FileStatus] = None

    @property
    def persona_label(self) -> str:
        return {
            "systems_engineer": "⚙️ Systems Engineering persona",
            "data_scientist": "📊 Quantitative Data Science persona",
            "general": "",
        }[self.persona]

    @property
    def folder(self) -> str:
        return "/".join(self.path.split("/")[:-1]) or "(root)"

    @property
    def filename(self) -> str:
        return self.path.split("/")[-1]
    
    