"""State, message, and schema definitions for the LangGraph Supervisor workflow."""
from enum import Enum
from typing import Sequence, List, Dict, Any, Optional, Annotated
from typing_extensions import TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


class AgentRole(str, Enum):
    """Enumeration of agent roles in the LangGraph orchestration."""
    SUPERVISOR = "SupervisorAgent"
    TOOL_NODE = "ToolNode"
    GUARDRAIL = "GuardrailAgent"
    # Legacy identifiers kept for backward introspection compatibility
    ROUTER = "SupervisorAgent"
    KNOWLEDGE = "SupervisorAgent"
    CUSTOMER_SUPPORT = "SupervisorAgent"
    ESCALATION = "SupervisorAgent"


class RouteDecision(BaseModel):
    """Routing decision produced by the Supervisor."""
    target_agent: AgentRole = AgentRole.SUPERVISOR
    intent: str = "dynamic_react"
    confidence: float = 1.0
    reasoning: str = "Decisão dinâmica guiada por Tool Calling."


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
    safety_violations: List[str]
    tools_used: List[str]
    tool_calls: List[Dict[str, Any]]
    tool_results: List[Dict[str, Any]]
    sources: List[str]
    retrieved_docs: List[Dict[str, Any]]
    ticket: Optional[Dict[str, Any]]
    final_response: str
    execution_time_ms: float
    tokens: Dict[str, int]
    estimated_cost_usd: float


class AgentState(BaseModel):
    """
    Adapter model providing backward-compatible interface for integration tests
    and telemetry inspection.
    """
    user_id: str = "cliente1988"
    message: str = ""
    session_id: Optional[str] = None
    trace_id: Optional[str] = None
    messages: List[Any] = Field(default_factory=list)

    is_safe: bool = True
    safety_violations: List[str] = Field(default_factory=list)

    route: Optional[RouteDecision] = None
    intent: Optional[str] = None

    context_docs: List[Dict[str, Any]] = Field(default_factory=list)
    retrieved_docs: List[Dict[str, Any]] = Field(default_factory=list)
    tool_results: List[Dict[str, Any]] = Field(default_factory=list)
    tools_used: List[str] = Field(default_factory=list)
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)
    ticket: Optional[Dict[str, Any]] = None

    agent_response: Optional[str] = None
    final_agent: Optional[AgentRole] = AgentRole.SUPERVISOR
    escalate_to_human: bool = False
    escalation_flag: bool = False
    escalation_ticket_id: Optional[str] = None

    start_time: float = 0.0
    execution_time_ms: float = 0.0
    tokens: Dict[str, int] = Field(default_factory=lambda: {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})
    estimated_cost_usd: float = 0.0

    model_config = {
        "arbitrary_types_allowed": True
    }


class ChatRequest(BaseModel):
    """Incoming chat message request schema."""
    message: str
    user_id: str = "cliente1988"
    session_id: Optional[str] = None


class AgentMetadata(BaseModel):
    """Operational telemetry and execution audit trail."""
    agent: str = "SupervisorAgent"
    session_id: str
    user_id: str
    trace_id: str = ""
    tools_used: List[str] = Field(default_factory=list)
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)
    retrieved_docs: List[Dict[str, Any]] = Field(default_factory=list)
    ticket: Optional[Dict[str, Any]] = None
    is_safe: bool = True
    safety_violations: List[str] = Field(default_factory=list)
    execution_time_ms: float = 0.0
    tokens: Dict[str, int] = Field(default_factory=lambda: {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})
    estimated_cost_usd: float = 0.0


class ChatResponse(BaseModel):
    """Unified API response schema."""
    response: str
    agent: str = "SupervisorAgent"
    metadata: AgentMetadata
