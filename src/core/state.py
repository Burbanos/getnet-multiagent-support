"""State, message, and schema definitions for the LangGraph Supervisor workflow."""
from collections.abc import Sequence
from enum import Enum
from typing import Annotated, Any

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field
from typing_extensions import TypedDict


class AgentRole(str, Enum):
    """Enumeration of agent roles in the LangGraph orchestration."""
    SUPERVISOR = "SupervisorAgent"
    TOOL_NODE = "ToolNode"
    GUARDRAIL = "GuardrailAgent"


class SupervisorState(TypedDict):
    """
    Standard LangGraph State schema with conversational memory.
    
    The 'messages' key uses 'add_messages' reducer so the checkpointer
    automatically appends HumanMessage, AIMessage, and ToolMessage across turns.
    """
    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_id: str
    session_id: str
    trace_id: str
    is_safe: bool
    safety_violations: list[str]
    agents_used: list[str]
    tools_used: list[str]
    tool_calls: list[dict[str, Any]]
    tool_results: list[dict[str, Any]]
    sources: list[str]
    retrieved_docs: list[dict[str, Any]]
    web_results: list[dict[str, Any]]
    ticket: dict[str, Any] | None
    pending_ticket_id: str | None
    handoff: dict[str, Any] | None
    consecutive_abstentions: int
    knowledge_outcomes: list[bool]
    final_response: str
    supervisor_steps: int
    llm_model: str | None
    execution_time_ms: float
    tokens: dict[str, int] | None
    tokens_by_agent: dict[str, dict[str, int]] | None
    estimated_cost_usd: float | None


class AgentState(BaseModel):
    """
    Adapter model providing backward-compatible interface for integration tests
    and telemetry inspection.
    """
    user_id: str = "cliente1988"
    message: str = ""
    session_id: str | None = None
    trace_id: str | None = None
    messages: list[Any] = Field(default_factory=list)

    is_safe: bool = True
    safety_violations: list[str] = Field(default_factory=list)

    intent: str | None = None

    context_docs: list[dict[str, Any]] = Field(default_factory=list)
    retrieved_docs: list[dict[str, Any]] = Field(default_factory=list)
    web_results: list[dict[str, Any]] = Field(default_factory=list)
    tool_results: list[dict[str, Any]] = Field(default_factory=list)
    agents_used: list[str] = Field(default_factory=lambda: ["SupervisorAgent"])
    tools_used: list[str] = Field(default_factory=list)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    ticket: dict[str, Any] | None = None
    handoff: dict[str, Any] | None = None
    llm_model: str | None = None

    agent_response: str | None = None
    final_agent: AgentRole | None = AgentRole.SUPERVISOR
    escalate_to_human: bool = False
    escalation_flag: bool = False
    escalation_ticket_id: str | None = None

    start_time: float = 0.0
    execution_time_ms: float = 0.0
    tokens: dict[str, int] | None = None
    tokens_by_agent: dict[str, dict[str, int]] | None = None
    estimated_cost_usd: float | None = None
    error: str | None = None

    model_config = {
        "arbitrary_types_allowed": True
    }


class ChatRequest(BaseModel):
    """Incoming chat message request schema."""
    message: str
    user_id: str = "cliente1988"
    session_id: str | None = None


class AgentMetadata(BaseModel):
    """Operational telemetry and execution audit trail."""
    agent: str = "SupervisorAgent"
    agent_type: str = "SupervisorAgent"
    routed_by: str = "SupervisorAgent"
    session_id: str
    user_id: str
    trace_id: str = ""
    agents_used: list[str] = Field(default_factory=lambda: ["SupervisorAgent"])
    tools_used: list[str] = Field(default_factory=list)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    retrieved_docs: list[dict[str, Any]] = Field(default_factory=list)
    ticket: dict[str, Any] | None = None
    handoff: dict[str, Any] | None = None
    llm_model: str | None = None
    is_safe: bool = True
    safety_violations: list[str] = Field(default_factory=list)
    execution_time_ms: float = 0.0
    tokens: dict[str, int] | None = None
    tokens_by_agent: dict[str, dict[str, int]] | None = None
    estimated_cost_usd: float | None = None
    error: str | None = None
    debug_details: dict[str, Any] = Field(default_factory=dict)

    model_config = {
        "extra": "allow",
    }


class ChatResponse(BaseModel):
    """Unified API response schema."""
    response: str
    agent: str = "SupervisorAgent"
    user_id: str | None = None
    metadata: AgentMetadata

    model_config = {
        "extra": "allow",
    }
