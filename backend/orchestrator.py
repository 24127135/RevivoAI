from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, StateGraph

class AgentState(TypedDict):
    """State schema for the LangGraph-based orchestration workflow."""

    session_active: bool
    ui_status: str
    file_queue: list[str]
    current_file: str
    iteration_count: int
    original_code: str
    current_code: str
    docker_exit_code: int
    traceback_log: list[str]


class StateGraphRouter:
    """Simple LangGraph router wrapper for the RevivoAI orchestration flow."""

    def __init__(self) -> None:
        self.graph = StateGraph(AgentState)
        self.execution_graph = None

        self.graph.add_node("router", self._router_node)
        self.graph.set_entry_point("router")
        self.graph.add_edge("router", END)

    def _router_node(self, state: AgentState) -> AgentState:
        """Placeholder routing node that preserves the incoming state."""
        return state

    def compile_graph(self) -> None:
        """Compile the configured graph and store it on the instance."""
        self.execution_graph = self.graph.compile()
