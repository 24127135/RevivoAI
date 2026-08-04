"""Stateless AST parsing nodes for the LangGraph orchestration engine."""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Protocol
import re

from backend.models import ProjectFile
from backend.personas import get_persona

if TYPE_CHECKING:
    from backend.orchestrator import AgentState


class _LLMClient(Protocol):
    def generate(self, prompt: str) -> str: ...


class ASTParserNode:
    """Parse source files into a compact structural summary."""

    def extract_tree(self, state: AgentState | str) -> dict[str, object] | str:
        """Parse the current file and return structural context.

        The method supports both the newer LangGraph state-dict contract and the
        older path-string contract used by existing tests.
        """
        if isinstance(state, str):
            path = Path(state)
            result = self._build_summary(path)
            if result is None:
                return "PARSING_ERROR"
            return self._summary_to_text(result)

        file_path = state.get("current_file", "")
        if not isinstance(file_path, str) or not file_path.strip():
            return {"ui_status": "PARSING_ERROR"}

        path = Path(file_path)
        result = self._build_summary(path)
        if result is None:
            return {"ui_status": "PARSING_ERROR"}

        return {"structural_context": result}

    def _build_summary(self, path: Path) -> dict[str, object] | None:
        """Build a structural summary for Python or R source files."""
        try:
            source = path.read_text(encoding="utf-8")
        except (FileNotFoundError, OSError, UnicodeDecodeError):
            return None

        suffix = path.suffix.lower()
        if suffix in {".r", ".rscript"}:
            return self._extract_r_context(source)

        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError:
            return None

        functions: list[str] = []
        classes: list[str] = []
        imports: list[str] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append(node.name)
            elif isinstance(node, ast.FunctionDef):
                functions.append(node.name)
            elif isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                module = self._format_import_from(node)
                if module:
                    imports.append(module)

        return {
            "current_file": str(path),
            "functions": self._dedupe(functions),
            "classes": self._dedupe(classes),
            "imports": self._dedupe(imports),
            "language": "python",
        }

    def _summary_to_text(self, structural_context: dict[str, object]) -> str:
        """Render a legacy text summary for older callers."""
        functions = ", ".join(structural_context.get("functions", []))
        classes = ", ".join(structural_context.get("classes", []))
        imports = ", ".join(structural_context.get("imports", []))

        parts = []
        if classes:
            parts.append(f"Classes: [{classes}]")
        if functions:
            parts.append(f"Functions: [{functions}]")
        if imports:
            parts.append(f"Imports: [{imports}]")

        return "; ".join(parts) if parts else "No parseable structure found."

    def _extract_r_context(self, source: str) -> dict[str, object] | None:
        """Extract a lightweight structural summary from R source."""
        function_names = self._dedupe(
            match.group("name")
            for match in re.finditer(r"(?m)^\s*(?P<name>[A-Za-z.][A-Za-z0-9._]*)\s*<-\s*function\s*\(", source)
        )
        class_names = self._dedupe(
            match.group("name")
            for match in re.finditer(r"(?m)\b(?:R6Class|setClass)\s*\(\s*['\"](?P<name>[^'\"]+)['\"]", source)
        )
        imports = self._dedupe(
            match.group("name")
            for match in re.finditer(r"(?m)\b(?:library|require)\s*\(\s*['\"]?(?P<name>[A-Za-z0-9._-]+)['\"]?\s*\)", source)
        )

        if not (function_names or class_names or imports):
            return None

        return {
            "functions": function_names,
            "classes": class_names,
            "imports": imports,
            "language": "r",
        }

    def _format_import_from(self, node: ast.ImportFrom) -> str:
        """Format a from-import statement into its module path."""
        module = node.module or ""
        if node.level:
            module = f"{'.' * node.level}{module}"
        return module

    def _dedupe(self, values) -> list[str]:
        """Remove duplicates while preserving order."""
        seen: dict[str, None] = {}
        for value in values:
            if value and value not in seen:
                seen[value] = None
        return list(seen.keys())


class LLMPatchNode: 
    """Generate refactored Python code for the orchestration workflow."""

    def __init__(self, llm_client: _LLMClient | None = None) -> None:
        """Create the patch node.

        Args:
            llm_client: Optional object with a ``generate(prompt)`` method.
        """
        self.llm_client = llm_client

    def execute(self, state: dict) -> dict:
        """Generate a patch for the current target file using the injected LLM client."""
        target_file = state.get("target_file")
        error_trace = state.get("error_trace", "")
        
        # Prefer an explicit system_prompt if provided; otherwise resolve persona-based prompt
        explicit = state.get("system_prompt")
        if isinstance(explicit, str) and explicit.strip():
            system_prompt = explicit
        else:
            persona_key = state.get("persona", "generalist")
            system_prompt = get_persona(persona_key)

        if not isinstance(target_file, ProjectFile):
            raise TypeError("state must contain a ProjectFile under 'target_file'")
        if not isinstance(error_trace, str):
            raise TypeError("state must contain a string under 'error_trace'")
        if self.llm_client is None:
            raise ValueError("llm_client must be provided")

        prompt = self._construct_prompt(target_file, error_trace, system_prompt)
        raw = self.llm_client.generate(prompt)

        print("\n=== RAW LLM OUTPUT ===")
        print(raw)
        print("======================\n")

        # Bulletproof parsing: Use regex to find headers regardless of markdown bolding (** or __)
        # or conversational filler text outside the blocks.
        if isinstance(raw, str):
            sections: dict[str, str] = {}
            
            # This regex looks for ### followed by optional bolding, the header name, optional bolding, and an optional colon.
            pattern = r"###\s*(?:\*\*|__)?([A-Z_]+)(?:\*\*|__)?\s*:?"
            parts = re.split(pattern, raw)
            
            # re.split returns [filler_text, HEADER_1, content_1, HEADER_2, content_2, ...]
            if len(parts) > 1:
                for i in range(1, len(parts), 2):
                    header_name = parts[i].strip().upper()
                    content = parts[i+1].strip()
                    
                    # Clean up any stray '---' delimiters Gemini might have left inside the content body
                    content = re.sub(r"(?m)^\s*---\s*$", "", content).strip()
                    sections[header_name] = content

                # Required headers
                required = {"CHARACTERIZATION", "REASONING", "CODE", "VERIFY", "ASSUMPTIONS", "ACTION"}
                if not required.issubset(set(sections.keys())):
                    return {"status": "REFUSED", "reason": f"Missing required sections. Found: {list(sections.keys())}", "raw": raw}

                # Enforce safety valve: CHARACTERIZATION must list at least one INVARIANT
                char = sections.get("CHARACTERIZATION", "")
                invariant_lines = [
                    line.strip() for line in char.splitlines() if "INVARIANT:" in line.strip().upper()
                ]
                if not invariant_lines:
                    return {"status": "REFUSED", "reason": "CHARACTERIZATION must include at least one INVARIANT entry", "raw": raw}

                action = sections.get("ACTION", "").strip().upper()
                if "REFUSE" in action:
                    return {"status": "REFUSED", "reason": sections.get("REASONING", ""), "assumptions": sections.get("ASSUMPTIONS", ""), "raw": raw}

                # ACTION indicates APPLY; extract code block from CODE section
                code_section = sections.get("CODE", "")
                code_match = re.search(r"```(?:[a-zA-Z0-9_+-]*)\n([\s\S]*?)\n```", code_section)
                if code_match:
                    code_text = code_match.group(1).rstrip() + "\n"
                else:
                    # If no fenced block, use the full CODE section
                    code_text = code_section.strip() + "\n"

                return {
                    "patched_code": code_text,
                    "status": "PATCH_GENERATED",
                    "characterization": sections.get("CHARACTERIZATION", ""),
                    "invariants": invariant_lines,
                    "assumptions": sections.get("ASSUMPTIONS", ""),
                    "raw": raw,
                }

        # Fallback: legacy unstructured response - pass through as patch
        return {"patched_code": raw, "status": "PATCH_GENERATED"}

    def _construct_prompt(self, file: ProjectFile, error: str, system_prompt: str | None = None) -> str:
        """Build the instruction prompt for the LLM."""
        source_code = file.legacy_source or file.ai_source
        first_line = system_prompt.strip() if isinstance(system_prompt, str) and system_prompt.strip() else "You are a senior code modernization assistant."
        return (
            f"{first_line}\n"
            "Review the source file and the runtime error trace.\n\n"
            f"File path: {file.path}\n"
            f"Language: {file.language}\n\n"
            "Source code:\n"
            f"{source_code}\n\n"
            "Error trace:\n"
            f"{error}\n\n"
            "You must follow the output protocol exactly, ensuring you use the '---' delimiter "
            "between sections and provide all required headers (CHARACTERIZATION, REASONING, CODE, "
            "VERIFY, ASSUMPTIONS, ACTION).\n"
        )
