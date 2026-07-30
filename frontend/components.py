"""
frontend/components.py
-----------------------
UI-phase constants used by app.py for the animated thinking / sandbox
progress indicators.

All Pygments-based code viewer and diff-table rendering has been removed
and replaced with Monaco Editor (see frontend/monaco_editor.py).
"""

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