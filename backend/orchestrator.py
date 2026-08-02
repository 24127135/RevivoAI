from __future__ import annotations

from typing import NotRequired, TypedDict

from langgraph.graph import END, START, StateGraph

from backend.llm_client import GeminiClient
from backend.models import ProjectFile
from backend.nodes import ASTParserNode, LLMPatchNode


class AgentState(TypedDict):
    """State schema for the initial LangGraph orchestration workflow."""

    target_file: NotRequired[ProjectFile]
    structural_context: NotRequired[dict]
    error_trace: NotRequired[str]
    system_prompt: NotRequired[str]
    persona: NotRequired[str]
    patched_code: NotRequired[str]
    docker_exit_code: NotRequired[int]
    iteration_count: NotRequired[int]
    traceback_log: NotRequired[list[str]]


def _parse_node(state: AgentState) -> AgentState:
    parser = ASTParserNode()
    target_file = state.get("target_file")
    if target_file is None:
        return state

    parsed_state = parser.extract_tree({"current_file": target_file.path})
    if not isinstance(parsed_state, dict):
        return state
    return parsed_state  # type: ignore[return-value]


def _patch_node(state: AgentState) -> AgentState:
    patcher = LLMPatchNode(llm_client=GeminiClient())
    patch_result = patcher.execute(state)
    patch_result["iteration_count"] = state.get("iteration_count", 0) + 1
    return patch_result  # type: ignore[return-value]


def _check_execution_status(state: AgentState) -> str:
    docker_exit_code = state.get("docker_exit_code")
    if docker_exit_code == 0:
        return "end"

    iteration_count = state.get("iteration_count", 0)
    if iteration_count >= 3:
        return "end"

    return "patch"


graph = StateGraph(AgentState)
graph.add_node("parse", _parse_node)
graph.add_node("patch", _patch_node)
graph.add_edge(START, "parse")
graph.add_edge("parse", "patch")
graph.add_conditional_edges("patch", _check_execution_status, {"end": END, "patch": "patch"})

orchestrator_app = graph.compile()
