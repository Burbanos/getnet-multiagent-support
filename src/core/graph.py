"""LangGraph Supervisor ReAct workflow with native MemorySaver checkpointer."""
import json
import logging
import time
import uuid
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from src.agents.guardrails import GuardrailAgent
from src.core.llm import get_rules_engine
from src.core.state import AgentRole, AgentState, SupervisorState
from src.tools.agent_tools import TOOLS_BY_NAME

logger = logging.getLogger("multiagent.orchestrator")


class OrchestrationGraph:
    """
    Coordinates execution via LangGraph Supervisor ReAct architecture:
    Guardrails (PII & Injection) -> Supervisor -> [ToolNode -> Supervisor]* -> Response.
    
    Checkpointer:
        Uses native MemorySaver indexed by 'thread_id' (session_id) to persist
        multi-turn conversational context across turns.
    """

    def __init__(self):
        self.guardrail_agent = GuardrailAgent()
        self.supervisor_llm = get_rules_engine()
        self.checkpointer = MemorySaver()
        self.graph = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(SupervisorState)

        # 1. Register Graph Nodes
        builder.add_node("guardrail", self._guardrail_node)
        builder.add_node("supervisor", self._supervisor_node)
        builder.add_node("tools", self._tools_node)

        # 2. Add Edges
        builder.add_edge(START, "guardrail")

        builder.add_conditional_edges(
            "guardrail",
            self._guardrail_condition,
            {
                "continue": "supervisor",
                "stop": END
            }
        )

        builder.add_conditional_edges(
            "supervisor",
            self._supervisor_condition,
            {
                "tools": "tools",
                "end": END
            }
        )

        # ReAct observation loop: from tools back to supervisor
        builder.add_edge("tools", "supervisor")

        return builder.compile(checkpointer=self.checkpointer)

    def _guardrail_node(self, state: SupervisorState) -> dict[str, Any]:
        """Sanitize PII and validate safety of incoming message."""
        raw_msg = ""
        # Find the incoming human input
        if state.get("messages"):
            last_msg = state["messages"][-1]
            if isinstance(last_msg, HumanMessage):
                raw_msg = last_msg.content if isinstance(last_msg.content, str) else str(last_msg.content)

        agent_state = AgentState(user_id=state.get("user_id", "cliente1988"), message=raw_msg)
        evaluated = self.guardrail_agent.evaluate_sync(agent_state)

        if not evaluated.is_safe:
            refusal_content = evaluated.agent_response or "Instrução não permitida pelas políticas de segurança."
            refusal_msg = AIMessage(content=refusal_content)
            return {
                "is_safe": False,
                "safety_violations": evaluated.safety_violations,
                "final_response": refusal_content,
                "messages": [refusal_msg]
            }

        # Message is safe, mask PII in state if applicable
        sanitized_msg = evaluated.message
        human_msg = HumanMessage(content=sanitized_msg)
        return {
            "is_safe": True,
            "safety_violations": [],
            "messages": [human_msg]
        }

    def _guardrail_condition(self, state: SupervisorState) -> str:
        """Route to supervisor if safe, else stop immediately."""
        return "continue" if state.get("is_safe", True) else "stop"

    def _supervisor_node(self, state: SupervisorState) -> dict[str, Any]:
        """
        Supervisor reasoning step: invokes the model / ReAct engine with bound tools.
        Emits an AIMessage with either tool_calls or final synthesized content.
        """
        messages = list(state.get("messages", []))
        user_id = state.get("user_id", "cliente1988")

        ai_message = self.supervisor_llm.decide_or_synthesize(messages, user_id=user_id)

        response_text = ai_message.content if isinstance(ai_message.content, str) else str(ai_message.content)
        tool_calls = getattr(ai_message, "tool_calls", []) or []
        existing_calls = list(state.get("tool_calls", []))
        if tool_calls:
            existing_calls.extend(tool_calls)

        return {
            "messages": [ai_message],
            "final_response": response_text,
            "tool_calls": existing_calls
        }

    def _supervisor_condition(self, state: SupervisorState) -> str:
        """Check if supervisor requested tool execution or finished response."""
        messages = state.get("messages", [])
        if messages:
            last_msg = messages[-1]
            if isinstance(last_msg, AIMessage) and getattr(last_msg, "tool_calls", None):
                return "tools"
        return "end"

    def _tools_node(self, state: SupervisorState) -> dict[str, Any]:
        """
        Tool Execution Node: executes requested tools and produces ToolMessage observations.
        """
        messages = state.get("messages", [])
        if not messages:
            return {}

        last_msg = messages[-1]
        tool_calls = getattr(last_msg, "tool_calls", []) or []

        tool_messages: list[ToolMessage] = []
        tools_used = list(state.get("tools_used", []))
        tool_results = list(state.get("tool_results", []))
        sources = list(state.get("sources", []))
        retrieved_docs = list(state.get("retrieved_docs", []))
        ticket = state.get("ticket")

        for call in tool_calls:
            tool_name = call.get("name")
            tool_args = call.get("args", {})
            call_id = call.get("id", str(uuid.uuid4()))

            tool_fn = TOOLS_BY_NAME.get(tool_name)
            if tool_fn:
                logger.info(f"Executing tool '{tool_name}' with args {tool_args}")
                try:
                    result_str = tool_fn.invoke(tool_args)
                except Exception as e:  # noqa: BLE001 - Dynamic tool invocation must catch all errors
                    logger.error(f"Error executing tool {tool_name}: {e}")
                    result_str = json.dumps({"error": f"Falha na execução da ferramenta {tool_name}: {e}"})

                tools_used.append(tool_name)

                t_msg = ToolMessage(content=result_str, tool_call_id=call_id, name=tool_name)
                tool_messages.append(t_msg)

                # Parse and track telemetry
                try:
                    parsed = json.loads(result_str)
                    tool_results.append(parsed)

                    if tool_name == "search_knowledge_base":
                        docs = parsed.get("documents", [])
                        for d in docs:
                            retrieved_docs.append(d)
                            if d.get("url"):
                                sources.append(d.get("url"))

                    elif tool_name == "search_web":
                        results = parsed.get("results", [])
                        for r in results:
                            if r.get("url"):
                                sources.append(r.get("url"))

                    elif tool_name == "escalate_to_human":
                        ticket = parsed

                except (json.JSONDecodeError, TypeError, KeyError) as e:
                    logger.debug(f"Could not parse telemetry from tool '{tool_name}' result: {e}")
            else:
                logger.warning(f"Tool '{tool_name}' not found in registry.")
                t_msg = ToolMessage(
                    content=json.dumps({"error": f"Ferramenta '{tool_name}' não encontrada."}),
                    tool_call_id=call_id,
                    name=tool_name
                )
                tool_messages.append(t_msg)

        return {
            "messages": tool_messages,
            "tools_used": tools_used,
            "tool_results": tool_results,
            "sources": sources,
            "retrieved_docs": retrieved_docs,
            "ticket": ticket
        }

    def run_sync(
        self,
        user_id: str,
        message: str,
        session_id: str | None = None
    ) -> AgentState:
        """
        Execute the compiled LangGraph workflow synchronously with MemorySaver session persistence.
        """
        start_time = time.perf_counter()
        active_session_id = session_id or str(uuid.uuid4())
        trace_id = f"trc-{uuid.uuid4().hex[:12]}"

        initial_state: SupervisorState = {
            "messages": [HumanMessage(content=message)],
            "user_id": user_id,
            "session_id": active_session_id,
            "trace_id": trace_id,
            "is_safe": True,
            "safety_violations": [],
            "tools_used": [],
            "tool_calls": [],
            "tool_results": [],
            "sources": [],
            "retrieved_docs": [],
            "ticket": None,
            "final_response": "",
            "execution_time_ms": 0.0,
            "tokens": None,
            "estimated_cost_usd": None
        }

        # Checkpointer thread configuration
        config = {"configurable": {"thread_id": active_session_id}}

        logger.info(
            f"Invoking Supervisor ReAct workflow for user '{user_id}' [Session: {active_session_id}]: '{message[:60]}...'"
        )

        try:
            result = self.graph.invoke(initial_state, config=config)
        except Exception:
            logger.exception("Error in LangGraph execution")
            result = initial_state
            result["final_response"] = "Ocorreu uma instabilidade momentânea no atendimento. Por favor, tente novamente."

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Extract final reply
        final_text = result.get("final_response", "")
        if not final_text and result.get("messages"):
            for m in reversed(result["messages"]):
                if isinstance(m, AIMessage) and m.content:
                    final_text = m.content if isinstance(m.content, str) else str(m.content)
                    break

        # Token metrics & cost estimation are unmeasured, set to None
        token_usage = None
        cost_usd = None

        # Map to backward-compatible AgentState
        agent_state = AgentState(
            user_id=user_id,
            message=message,
            session_id=active_session_id,
            trace_id=trace_id,
            is_safe=result.get("is_safe", True),
            safety_violations=result.get("safety_violations", []),
            tools_used=result.get("tools_used", []),
            tool_calls=result.get("tool_calls", []),
            tool_results=result.get("tool_results", []),
            sources=result.get("sources", []),
            retrieved_docs=result.get("retrieved_docs", []),
            context_docs=result.get("retrieved_docs", []),
            ticket=result.get("ticket"),
            agent_response=final_text,
            final_agent=AgentRole.SUPERVISOR,
            escalate_to_human=bool(result.get("ticket")),
            escalation_ticket_id=result.get("ticket", {}).get("ticket_id") if result.get("ticket") else None,
            intent="dynamic_react",
            execution_time_ms=elapsed_ms,
            tokens=token_usage,
            estimated_cost_usd=cost_usd
        )

        logger.info(
            f"Workflow finished in {elapsed_ms}ms. Tools: {agent_state.tools_used}"
        )
        return agent_state

    async def run(
        self,
        user_id: str,
        message: str,
        session_id: str | None = None
    ) -> AgentState:
        """Async compatibility wrapper invoking the compiled LangGraph workflow."""
        return self.run_sync(user_id=user_id, message=message, session_id=session_id)


_orchestrator_instance: OrchestrationGraph | None = None


def get_orchestrator() -> OrchestrationGraph:
    """Dependency getter for singleton OrchestrationGraph."""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = OrchestrationGraph()
    return _orchestrator_instance
