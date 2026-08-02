from backend.models import FileStatus, ProjectFile
from backend.nodes import ASTParserNode, LLMPatchNode


class MockLLMClient:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return "patched result"


def test_extract_tree_structure_with_valid_python_returns_structure(tmp_path):
    """
    Happy Path: Verify that the parser correctly extracts 
    class, function, and import signatures.
    """
    parser = ASTParserNode()
    sample_file = tmp_path / "test_sample.py"
    sample_file.write_text("import os\n\nclass DiskScheduler:\n    def scan(self):\n        pass", encoding="utf-8")

    result = parser.extract_tree(str(sample_file))

    # Assertions
    assert "DiskScheduler" in result
    assert "scan" in result
    assert "os" in result


def test_extract_tree_with_syntax_error_returns_parsing_error(tmp_path):
    """
    Robustness Path: Verify that the parser handles broken code 
    gracefully by returning the specific PARSING_ERROR status.
    """
    parser = ASTParserNode()
    broken_file = tmp_path / "broken.py"
    broken_file.write_text("def invalid_syntax(self: ...", encoding="utf-8")  # Deliberately incomplete

    result = parser.extract_tree(str(broken_file))
    assert "PARSING_ERROR" in result


def test_llm_patch_node_uses_injected_system_prompt():
    file = ProjectFile(
        file_id="file_1",
        path="src/example.py",
        legacy_source="print('hello')",
        ai_source="",
        status=FileStatus.QUEUED,
        language="python",
    )
    llm_client = MockLLMClient()
    node = LLMPatchNode(llm_client=llm_client)

    result = node.execute(
        {
            "target_file": file,
            "error_trace": "NameError: x is not defined",
            "system_prompt": "You are an expert Data Scientist modernizing statistical models.",
        }
    )

    assert result == {"patched_code": "patched result", "status": "PATCH_GENERATED"}
    assert len(llm_client.prompts) == 1
    prompt = llm_client.prompts[0]
    assert "You are an expert Data Scientist modernizing statistical models." in prompt