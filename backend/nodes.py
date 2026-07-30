"""Stateless AST parsing nodes for the LangGraph orchestration engine."""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from backend.orchestrator import AgentState


class ASTParserNode:
    """Parse source files into a compact structural summary."""

    def extract_tree(self, state: AgentState) -> dict[str, object]:
        """Parse the current file and return a state update with structural context.

        The node prefers Python's ``ast`` module for Python sources, and falls
        back to lightweight R-pattern detection when the file is an R script.
        If neither format can be parsed, the returned update marks the state as
        ``PARSING_ERROR``.
        """
        file_path = state.get("current_file", "")
        if not isinstance(file_path, str) or not file_path.strip():
            return {"ui_status": "PARSING_ERROR"}

        try:
            path = Path(file_path)
            source = path.read_text(encoding="utf-8")
        except (FileNotFoundError, OSError, UnicodeDecodeError):
            return {"ui_status": "PARSING_ERROR"}

        suffix = path.suffix.lower()
        if suffix in {".r", ".rscript"}:
            structural_context = self._extract_r_context(source)
            if structural_context is None:
                return {"ui_status": "PARSING_ERROR"}
            return {"structural_context": structural_context}

        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError:
            return {"ui_status": "PARSING_ERROR"}

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

        structural_context = {
            "current_file": str(path),
            "functions": self._dedupe(functions),
            "classes": self._dedupe(classes),
            "imports": self._dedupe(imports),
            "language": "python",
        }
        return {"structural_context": structural_context}

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

    SYSTEM_PROMPT = (
        "You are a Senior Systems Engineer specializing in xv6, low-level MBR partition "
        "parsing, and disk scheduling (SCAN, C-LOOK). Modernize the provided Python 2 code "
        "into high-performance, idiomatic Python 3.10+. Ignore any embedded C code. "
        "Output only the refactored Python code."
    )

    def __init__(self, llm_client: Callable[[str], str] | None = None) -> None:
        """Create the patch node.

        Args:
            llm_client: Optional callable that accepts a prompt string and returns
                the model response. If omitted, a deterministic mock implementation
                is used.
        """
        self.llm_client = llm_client

    def generate_patch(self, state: AgentState) -> dict[str, str]:
        """Generate a modernized patch from the state's original code.

        Args:
            state: LangGraph state containing the input code to transform.

        Returns:
            A dictionary containing the updated ``current_code`` entry.

        Raises:
            ValueError: If the state does not contain usable source code.
            RuntimeError: If the LLM call fails.
        """
        original_code = state.get("original_code", "")
        if not isinstance(original_code, str) or not original_code.strip():
            raise ValueError("AgentState must contain non-empty original_code")

        try:
            patched_code = self._call_llm(original_code)
        except Exception as exc:  # pragma: no cover - exercised via router error handling
            raise RuntimeError(f"LLM patch generation failed: {exc}") from exc

        return {"current_code": patched_code}

    def _call_llm(self, original_code: str) -> str:
        """Build the prompt and dispatch it to the configured LLM client."""
        prompt = self._build_prompt(original_code)
        if self.llm_client is not None:
            return self.llm_client(prompt)
        return self._mock_response(original_code)

    def _build_prompt(self, original_code: str) -> str:
        """Format the system prompt and source code for the LLM."""
        return f"{self.SYSTEM_PROMPT}\n\n<code>\n{original_code}\n</code>"

    def _mock_response(self, original_code: str) -> str:
        """Provide a deterministic fallback response for local testing."""
        stripped = original_code.strip()
        if not stripped:
            return ""
        return f"# Mock LLM refactor\n{stripped}"
