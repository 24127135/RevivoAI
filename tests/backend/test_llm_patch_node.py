from backend.models import FileStatus, ProjectFile
from backend.nodes import LLMPatchNode


class MockLLMClient:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return "patched result"


def test_llm_patch_node_execute_generates_patch_and_status():
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

    result = node.execute({"target_file": file, "error_trace": "NameError: x is not defined"})

    assert result == {"patched_code": "patched result", "status": "PATCH_GENERATED"}
    assert len(llm_client.prompts) == 1
    prompt = llm_client.prompts[0]
    assert "src/example.py" in prompt
    assert "print('hello')" in prompt
    assert "NameError: x is not defined" in prompt
    assert "### CHARACTERIZATION:\n- INVARIANT:" in prompt
    assert "### ACTION:\nAPPLY or REFUSE" in prompt