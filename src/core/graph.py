"""State-based orchestration graph managing workflow between agents using LangGraph."""
import logging
import time

from langgraph.graph import StateGraph, START, END

from src.core.state import AgentState, AgentRole
from src.agents.guardrails import GuardrailAgent
from src.agents.router import RouterAgent
from src.agents.knowledge import KnowledgeAgent
from src.agents.support import CustomerSupportAgent
from src.agents.escalation import HumanEscalationAgent

logger = logging.getLogger("multiagent.orchestrator")


class OrchestrationGraph:
    """Coordinates execution pipeline: Guardrails -> Router -> Worker Nodes -> Response."""

    def __init__(self):
        self.guardrail_agent = GuardrailAgent()
        self.router_agent = RouterAgent()
        self.knowledge_agent = KnowledgeAgent()
        self.support_agent = CustomerSupportAgent()
        self.escalation_agent = HumanEscalationAgent()

        self.graph = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(AgentState)

        builder.add_node("guardrail", self._guardrail_node)
        builder.add_node("router", self._router_node)
        builder.add_node("knowledge", self._knowledge_node)
        builder.add_node("support", self._support_node)
        builder.add_node("escalation", self._escalation_node)

        builder.add_edge(START, "guardrail")

        builder.add_conditional_edges(
            "guardrail",
            self._guardrail_condition,
            {
                "continue": "router",
                "stop": END
            }
        )

        builder.add_conditional_edges(
            "router",
            self._router_condition,
            {
                "knowledge": "knowledge",
                "support": "support",
                "escalation": "escalation"
            }
        )

        builder.add_edge("knowledge", END)
        builder.add_edge("support", END)
        builder.add_edge("escalation", END)

        return builder.compile()

    async def _guardrail_node(self, state: AgentState) -> AgentState:
        return await self.guardrail_agent.evaluate(state)

    def _guardrail_condition(self, state: AgentState) -> str:
        return "continue" if state.is_safe else "stop"

    async def _router_node(self, state: AgentState) -> AgentState:
        state = self.router_agent.route(state)
        if state.route:
            state.intent = state.route.intent
        return state

    def _router_condition(self, state: AgentState) -> str:
        if not state.route:
            return "knowledge"

        target = state.route.target_agent
        if target == AgentRole.CUSTOMER_SUPPORT:
            return "support"
        elif target == AgentRole.ESCALATION:
            return "escalation"
        return "knowledge"

    async def _knowledge_node(self, state: AgentState) -> AgentState:
        return await self.knowledge_agent.execute(state)

    async def _support_node(self, state: AgentState) -> AgentState:
        return await self.support_agent.execute(state)

    async def _escalation_node(self, state: AgentState) -> AgentState:
        return await self.escalation_agent.execute(state)

    async def run(self, user_id: str, message: str) -> AgentState:
        """Execute the compiled LangGraph workflow for an incoming user query."""
        start_time = time.perf_counter()
        initial_state = AgentState(
            user_id=user_id,
            message=message,
            start_time=start_time
        )

        logger.info(f"Running LangGraph workflow for user '{user_id}' with message: '{message[:60]}...'")

        result = await self.graph.ainvoke(initial_state)

        if isinstance(result, AgentState):
            state = result
        elif isinstance(result, dict):
            state = AgentState.model_validate(result)
        else:
            state = initial_state

        state.execution_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.info(
            f"LangGraph execution finished in {state.execution_time_ms}ms by '{state.final_agent}'. "
            f"Tools: {state.tools_used}"
        )
        return state


_orchestrator_instance = None


def get_orchestrator() -> OrchestrationGraph:
    """Dependency getter for singleton Orchestrator."""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = OrchestrationGraph()
    return _orchestrator_instance
