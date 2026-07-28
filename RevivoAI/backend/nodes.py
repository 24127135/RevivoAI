"""Stateless AST parsing nodes for the LangGraph orchestration engine."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Callable

from backend.orchestrator import AgentState


class ASTParserNode:
    """Parse Python source files into a compact structural summary."""

    def extract_tree(self, file_path: str) -> str:
        """Parse a Python source file and summarize its top-level structure.

        The summary includes discovered class definitions, their methods,
        top-level function signatures, and global imports. If parsing fails,
        a descriptive error message is returned so higher-level orchestration
        logic can decide whether to retry.
        """
        try:
            path = Path(file_path)
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(path))
        except (FileNotFoundError, OSError, SyntaxError, UnicodeDecodeError) as exc:
            return f"Parsing failed: {exc}"

        classes: list[str] = []
        functions: list[str] = []
        imports: list[str] = []

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                methods = [
                    child.name
                    for child in node.body
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                ]
                classes.append(f"{node.name} (methods: {', '.join(methods) if methods else 'none'})")
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(self._format_function_signature(node))
            elif isinstance(node, ast.Import):
                imports.extend(self._format_import(node))
            elif isinstance(node, ast.ImportFrom):
                imports.extend(self._format_import_from(node))

        sections: list[str] = []
        if classes:
            sections.append(f"Classes: [{', '.join(classes)}]")
        if functions:
            sections.append(f"Functions: [{', '.join(functions)}]")
        if imports:
            sections.append(f"Imports: [{', '.join(imports)}]")

        return "; ".join(sections) if sections else "No parseable structure found."

    def _format_function_signature(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
        """Build a readable signature for a function or async function node."""
        args = [arg.arg for arg in node.args.posonlyargs + node.args.args + node.args.kwonlyargs]
        if node.args.vararg:
            args.append(f"*{node.args.vararg.arg}")
        if node.args.kwarg:
            args.append(f"**{node.args.kwarg.arg}")

        return f"{node.name}({', '.join(args)})"

    def _format_import(self, node: ast.Import) -> list[str]:
        """Format import statements into concise strings."""
        return [alias.name + (f" as {alias.asname}" if alias.asname else "") for alias in node.names]

    def _format_import_from(self, node: ast.ImportFrom) -> list[str]:
        """Format from-import statements into concise strings."""
        module = node.module or ""
        formatted: list[str] = []
        for alias in node.names:
            imported = alias.name
            if alias.name != "*":
                imported = f"{module}.{alias.name}" if module else alias.name
            else:
                imported = f"{module}.*" if module else "*"
            if alias.asname:
                imported = f"{imported} as {alias.asname}"
            formatted.append(imported)
        return formatted


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
