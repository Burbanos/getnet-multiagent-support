"""LangGraph Supervisor ReAct workflow with native MemorySaver checkpointer."""
import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any

from langchain_core.exceptions import (
    ModelAuthenticationError,
    ModelInvalidRequestError,
    ModelNotFoundError,
    ModelPermissionDeniedError,
)
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from src.agents.guardrails import GuardrailAgent
from src.config import settings
from src.core.llm import (
    LLMConfigurationError,
    LLMNotConfiguredError,
    LLMUnavailableError,
    get_chat_model,
)
from src.core.state import AgentRole, AgentState, SupervisorState
from src.tools.agent_tools import ALL_TOOLS, TOOLS_BY_NAME

logger = logging.getLogger("multiagent.orchestrator")

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "supervisor.md"


def load_supervisor_prompt() -> str:
    """Load supervisor system prompt from markdown file."""
    if PROMPT_PATH.exists():
        return PROMPT_PATH.read_text(encoding="utf-8")
    return "You are the support supervisor for Getnet merchants."


class OrchestrationGraph:
    """
    Coordinates execution via LangGraph Supervisor ReAct architecture:
    Guardrails (PII & Injection) -> Supervisor -> [ToolNode -> Supervisor]* -> Response.

    Checkpointer:
        Uses native MemorySaver indexed by 'thread_id' (session_id) to persist
        multi-turn conversational context across turns.
    """

    def __init__(self, chat_model: BaseChatModel | None = None):
        self.guardrail_agent = GuardrailAgent()
        self.chat_model: BaseChatModel | None = chat_model
        self._bound_model: Any = None
        self.checkpointer = MemorySaver()
        self.graph = self._build_graph()

    def _get_bound_model(self) -> Any:
        if self._bound_model is None:
            model = self.chat_model if self.chat_model is not None else get_chat_model()
            self._bound_model = model.bind_tools(ALL_TOOLS)
        return self._bound_model

    def _build_graph(self):
        builder = StateGraph(SupervisorState)

        # 1. Register Graph Nodes
        builder.add_node("guardrail", self._guardrail_node)
        builder.add_node("supervisor", self._supervisor_node)
        builder.add_node("tools", self._tools_node)
        builder.add_node("force_escalation", self._force_escalation_node)

        # 2. Add Edges
        builder.add_edge(START, "guardrail")

        builder.add_conditional_edges(
            "guardrail",
            self._guardrail_condition,
            {
                "continue": "supervisor",
                "stop": END,
            },
        )

        builder.add_conditional_edges(
            "supervisor",
            self._supervisor_condition,
            {
                "tools": "tools",
                "force_escalation": "force_escalation",
                "end": END,
            },
        )

        # ReAct observation loop: from tools back to supervisor
        builder.add_edge("tools", "supervisor")
        builder.add_edge("force_escalation", END)

        return builder.compile(checkpointer=self.checkpointer)

    def _guardrail_node(self, state: SupervisorState) -> dict[str, Any]:
        """Sanitize PII and validate safety of incoming message."""
        raw_msg = ""
        orig_id = None
        if state.get("messages"):
            last_msg = state["messages"][-1]
            if isinstance(last_msg, HumanMessage):
                orig_id = getattr(last_msg, "id", None)
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
                "messages": [refusal_msg],
            }

        # Replace incoming HumanMessage with sanitized message having the same id
        sanitized_msg = evaluated.message
        human_msg = HumanMessage(content=sanitized_msg, id=orig_id)
        return {
            "is_safe": True,
            "safety_violations": [],
            "messages": [human_msg],
        }

    def _guardrail_condition(self, state: SupervisorState) -> str:
        """Route to supervisor if safe, else stop immediately."""
        return "continue" if state.get("is_safe", True) else "stop"

    def _supervisor_node(self, state: SupervisorState) -> dict[str, Any]:
        """
        Supervisor reasoning step: invokes the model with supervisor prompt and bound tools.
        Emits an AIMessage with either tool_calls or final synthesized content.
        """
        try:
            bound_model = self._get_bound_model()
            system_prompt = load_supervisor_prompt()
            full_messages = [SystemMessage(content=system_prompt)] + list(state.get("messages", []))
            ai_message = bound_model.invoke(full_messages)
        except (LLMNotConfiguredError, LLMConfigurationError, LLMUnavailableError):
            raise
        except (
            ModelNotFoundError,
            ModelAuthenticationError,
            ModelPermissionDeniedError,
            ModelInvalidRequestError,
        ) as exc:
            logger.exception("Supervisor model configuration error")
            raise LLMConfigurationError(str(exc)) from exc
        except Exception as exc:
            logger.exception("Supervisor model invocation failed")
            raise LLMUnavailableError(str(exc)) from exc

        response_text = str(ai_message.text) if hasattr(ai_message, "text") else (
            ai_message.content if isinstance(ai_message.content, str) else str(ai_message.content)
        )
        tool_calls = getattr(ai_message, "tool_calls", []) or []
        existing_calls = list(state.get("tool_calls", []))
        if tool_calls:
            existing_calls.extend(tool_calls)

        current_steps = state.get("supervisor_steps", 0) + 1

        return {
            "messages": [ai_message],
            "final_response": response_text,
            "tool_calls": existing_calls,
            "supervisor_steps": current_steps,
        }

    def _supervisor_condition(self, state: SupervisorState) -> str:
        """Check if supervisor requested tool execution, reached step limit, or finished response."""
        messages = state.get("messages", [])
        if messages:
            last_msg = messages[-1]
            if isinstance(last_msg, AIMessage) and getattr(last_msg, "tool_calls", None):
                current_steps = state.get("supervisor_steps", 0)
                if current_steps >= settings.MAX_SUPERVISOR_STEPS:
                    return "force_escalation"
                return "tools"
        return "end"

    def _force_escalation_node(self, state: SupervisorState) -> dict[str, Any]:
        """
        Forced escalation node triggered when MAX_SUPERVISOR_STEPS is reached.
        Closes pending tool calls and creates a ticket in tickets.db.
        """
        messages = state.get("messages", [])
        last_msg = messages[-1] if messages else None
        pending_calls = getattr(last_msg, "tool_calls", []) or []

        tool_messages: list[BaseMessage] = []
        for tc in pending_calls:
            call_id = tc.get("id", "")
            tool_name = tc.get("name", "unknown")
            t_msg = ToolMessage(
                content=json.dumps({"error": "not executed: step limit reached"}),
                tool_call_id=call_id,
                name=tool_name,
            )
            tool_messages.append(t_msg)

        user_id = state.get("user_id", "cliente1988")
        escalate_tool = TOOLS_BY_NAME["escalate_to_human"]
        escalate_res = escalate_tool.invoke(
            {"reason": "automatic escalation: supervisor step limit reached"},
            config={"configurable": {"user_id": user_id}},
        )

        ticket_obj: dict[str, Any] | None = None
        try:
            parsed = json.loads(escalate_res) if isinstance(escalate_res, str) else escalate_res
            if isinstance(parsed, dict):
                ticket_obj = parsed
        except (json.JSONDecodeError, TypeError):
            logger.warning("Failed to parse ticket result from force_escalation")

        ticket_id = (ticket_obj or {}).get("ticket_id", "GET-TKT-PENDING")
        final_text = (
            f"Não consegui concluir sua solicitação automaticamente. "
            f"Registrei o chamado {ticket_id} para análise de um especialista humano."
        )
        escalation_ai_msg = AIMessage(content=final_text)
        tool_messages.append(escalation_ai_msg)

        tools_used = list(state.get("tools_used", []))
        tools_used.append("escalate_to_human")

        return {
            "messages": tool_messages,
            "ticket": ticket_obj,
            "final_response": final_text,
            "tools_used": tools_used,
        }

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
                    result_str = tool_fn.invoke(
                        tool_args,
                        config={"configurable": {"user_id": state["user_id"]}},
                    )
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
                    name=tool_name,
                )
                tool_messages.append(t_msg)

        return {
            "messages": tool_messages,
            "tools_used": tools_used,
            "tool_results": tool_results,
            "sources": sources,
            "retrieved_docs": retrieved_docs,
            "ticket": ticket,
        }

    def run_sync(
        self,
        user_id: str,
        message: str,
        session_id: str | None = None,
        trace_id: str | None = None,
    ) -> AgentState:
        """
        Execute the compiled LangGraph workflow synchronously with MemorySaver session persistence.
        """
        start_time = time.perf_counter()
        active_session_id = session_id or str(uuid.uuid4())
        active_trace_id = trace_id or f"trc-{uuid.uuid4().hex[:12]}"
        msg_id = str(uuid.uuid4())

        initial_state: SupervisorState = {
            "messages": [HumanMessage(content=message, id=msg_id)],
            "user_id": user_id,
            "session_id": active_session_id,
            "trace_id": active_trace_id,
            "is_safe": True,
            "safety_violations": [],
            "tools_used": [],
            "tool_calls": [],
            "tool_results": [],
            "sources": [],
            "retrieved_docs": [],
            "ticket": None,
            "final_response": "",
            "supervisor_steps": 0,
            "execution_time_ms": 0.0,
            "tokens": None,
            "estimated_cost_usd": None,
        }

        # Checkpointer thread configuration
        config = {"configurable": {"thread_id": active_session_id}}

        logger.info(
            f"Invoking Supervisor ReAct workflow for user '{user_id}' [Session: {active_session_id}]: '{message[:60]}...'"
        )

        try:
            result = self.graph.invoke(initial_state, config=config)
        except (LLMNotConfiguredError, LLMConfigurationError, LLMUnavailableError):
            raise
        except Exception:
            logger.exception("Error in LangGraph execution")
            result = initial_state
            result["final_response"] = (
                "Ocorreu uma instabilidade momentânea no atendimento. Por favor, tente novamente."
            )

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
            trace_id=active_trace_id,
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
            estimated_cost_usd=cost_usd,
        )

        logger.info(
            f"Workflow finished in {elapsed_ms}ms. Tools: {agent_state.tools_used}"
        )
        return agent_state

    async def run(
        self,
        user_id: str,
        message: str,
        session_id: str | None = None,
        trace_id: str | None = None,
    ) -> AgentState:
        """Async compatibility wrapper invoking the compiled LangGraph workflow."""
        return self.run_sync(user_id=user_id, message=message, session_id=session_id, trace_id=trace_id)


_orchestrator_instance: OrchestrationGraph | None = None


def get_orchestrator() -> OrchestrationGraph:
    """Dependency getter for singleton OrchestrationGraph."""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = OrchestrationGraph()
    return _orchestrator_instance
