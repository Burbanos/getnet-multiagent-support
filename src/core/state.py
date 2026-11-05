"""State and role models for LangGraph orchestration workflow."""
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class AgentRole(str, Enum):
    """Enumeration of agent identifiers in the multi-agent graph."""
    ROUTER = "RouterAgent"
    KNOWLEDGE = "KnowledgeAgent"
    CUSTOMER_SUPPORT = "CustomerSupportAgent"
    ESCALATION = "HumanEscalationAgent"
    GUARDRAIL = "GuardrailAgent"


class RouteDecision(BaseModel):
    """Classification output produced by RouterAgent."""
    target_agent: AgentRole
    intent: str
    confidence: float
    reasoning: str
    extracted_entities: Dict[str, Any] = Field(default_factory=dict)


class AgentState(BaseModel):
    """Immutable state shared across all nodes in the LangGraph workflow."""
    user_id: str
    message: str
    messages: List[Dict[str, Any]] = Field(default_factory=list)

    is_safe: bool = True
    safety_violations: List[str] = Field(default_factory=list)

    route: Optional[RouteDecision] = None
    intent: Optional[str] = None

    context_docs: List[Dict[str, Any]] = Field(default_factory=list)
    retrieved_docs: List[Dict[str, Any]] = Field(default_factory=list)
    tool_results: List[Dict[str, Any]] = Field(default_factory=list)
    tools_used: List[str] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)

    agent_response: Optional[str] = None
    final_agent: Optional[AgentRole] = None
    escalate_to_human: bool = False
    escalation_flag: bool = False
    escalation_ticket_id: Optional[str] = None

    start_time: float = 0.0
    execution_time_ms: float = 0.0

    model_config = {
        "arbitrary_types_allowed": True
    }
