"""LangGraph Supervisor ReAct workflow with native MemorySaver checkpointer."""
import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from src.agents.guardrails import GuardrailAgent
from src.agents.specialists import SpecialistAgent
from src.config import settings
from src.core.llm import (
    LLMConfigurationError,
    LLMNotConfiguredError,
    LLMUnavailableError,
    extract_model_name,
    get_chat_model,
    get_fallback_model,
    invoke_model_with_fallback,
)
from src.core.state import AgentRole, AgentState, SupervisorState
from src.tools.agent_tools import (
    TOOLS_BY_NAME,
    diagnose_declined_transaction,
    diagnose_terminal,
    get_settlement_status,
    search_knowledge_base,
    search_web,
)
from src.tools.supervisor_tools import SUPERVISOR_TOOLS

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

    def __init__(
        self,
        chat_model: BaseChatModel | None = None,
        fallback_model: BaseChatModel | None = None,
    ):
        self.guardrail_agent = GuardrailAgent()
        self.chat_model: BaseChatModel | None = chat_model
        self.fallback_model: BaseChatModel | None = fallback_model
        self._bound_model: Any = None
        self._bound_fallback: Any = None

        self.knowledge_agent = SpecialistAgent(
            name="KnowledgeAgent",
            prompt_file="knowledge_agent.md",
            tools=[search_knowledge_base, search_web],
            chat_model=chat_model,
            fallback_model=fallback_model,
        )
        self.support_agent = SpecialistAgent(
            name="SupportAgent",
            prompt_file="support_agent.md",
            tools=[get_settlement_status, diagnose_declined_transaction, diagnose_terminal],
            chat_model=chat_model,
            fallback_model=fallback_model,
        )

        self.checkpointer = MemorySaver()
        self.graph = self._build_graph()

    def _get_bound_models(self) -> tuple[Any, Any]:
        if self._bound_model is None:
            if self.chat_model is not None:
                primary = self.chat_model
                fallback = self.fallback_model
            else:
                primary = get_chat_model()
                fallback = get_fallback_model()
            self._bound_model = primary.bind_tools(SUPERVISOR_TOOLS)
            self._bound_fallback = fallback.bind_tools(SUPERVISOR_TOOLS) if fallback is not None else None
        return self._bound_model, self._bound_fallback

    def _get_bound_model(self) -> Any:
        bound_primary, _ = self._get_bound_models()
        return bound_primary

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
        bound_model, bound_fallback = self._get_bound_models()
        system_prompt = load_supervisor_prompt()
        full_messages = [SystemMessage(content=system_prompt)] + list(state.get("messages", []))
        trace_id = state.get("trace_id", "")

        ai_message, active_model = invoke_model_with_fallback(
            bound_model,
            bound_fallback,
            full_messages,
            trace_id=trace_id,
            caller_name="Supervisor",
        )

        model_used = extract_model_name(active_model)

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
            "llm_model": model_used,
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
        trace_id = state.get("trace_id", "")
        escalate_tool = TOOLS_BY_NAME["escalate_to_human"]

        ticket_obj: dict[str, Any] | None = None
        try:
            escalate_res = escalate_tool.invoke(
                {"reason": "automatic escalation: supervisor step limit reached"},
                config={"configurable": {"user_id": user_id}},
            )
            parsed = json.loads(escalate_res) if isinstance(escalate_res, str) else escalate_res
            if isinstance(parsed, dict) and parsed.get("ticket_id"):
                ticket_obj = parsed
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Failed to create escalation ticket in force_escalation [trace_id={trace_id}]: {exc}")

        if ticket_obj and ticket_obj.get("ticket_id"):
            ticket_id = ticket_obj["ticket_id"]
            final_text = (
                f"Não consegui concluir sua solicitação automaticamente. "
                f"Registrei o chamado {ticket_id} para análise de um especialista humano."
            )
        else:
            ticket_obj = None
            final_text = (
                "Não consegui concluir sua solicitação automaticamente e não foi possível abrir um chamado agora. "
                "Tente novamente mais tarde."
            )
            logger.error(f"Force escalation could not generate a valid ticket [trace_id={trace_id}]")

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
        Tool Execution Node: delegates to specialists or executes supervisor tools.
        Produces ToolMessage observations for the supervisor model.
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
        agents_used = list(state.get("agents_used", ["SupervisorAgent"]))

        user_id = state.get("user_id", "cliente1988")
        trace_id = state.get("trace_id", "")

        for call in tool_calls:
            tool_name = call.get("name")
            tool_args = call.get("args", {})
            call_id = call.get("id", str(uuid.uuid4()))

            if tool_name == "ask_knowledge_agent":
                if "KnowledgeAgent" not in agents_used:
                    agents_used.append("KnowledgeAgent")
                question = tool_args.get("question") or tool_args.get("query") or tool_args.get("task") or ""
                spec_res = self.knowledge_agent.run(question, user_id=user_id, trace_id=trace_id)

                payload = {
                    "agent": spec_res["agent"],
                    "status": spec_res["status"],
                    "answer": spec_res["answer"],
                    "tools_used": spec_res["tools_used"],
                    "sources": spec_res["sources"],
                }
                payload_str = json.dumps(payload, ensure_ascii=False)
                t_msg = ToolMessage(content=payload_str, tool_call_id=call_id, name=tool_name)
                tool_messages.append(t_msg)
                tool_results.append(payload)

                tools_used.extend(spec_res["tools_used"])
                sources.extend(spec_res["sources"])
                retrieved_docs.extend(spec_res["retrieved_docs"])

            elif tool_name == "ask_support_agent":
                if "SupportAgent" not in agents_used:
                    agents_used.append("SupportAgent")
                request_text = tool_args.get("request") or tool_args.get("task") or tool_args.get("question") or ""
                spec_res = self.support_agent.run(request_text, user_id=user_id, trace_id=trace_id)

                payload = {
                    "agent": spec_res["agent"],
                    "status": spec_res["status"],
                    "answer": spec_res["answer"],
                    "tools_used": spec_res["tools_used"],
                    "sources": spec_res["sources"],
                }
                payload_str = json.dumps(payload, ensure_ascii=False)
                t_msg = ToolMessage(content=payload_str, tool_call_id=call_id, name=tool_name)
                tool_messages.append(t_msg)
                tool_results.append(payload)

                tools_used.extend(spec_res["tools_used"])
                sources.extend(spec_res["sources"])
                retrieved_docs.extend(spec_res["retrieved_docs"])

            elif tool_name == "escalate_to_human":
                escalate_fn = TOOLS_BY_NAME.get("escalate_to_human")
                if escalate_fn:
                    try:
                        result_str = escalate_fn.invoke(
                            tool_args,
                            config={"configurable": {"user_id": user_id}},
                        )
                    except Exception as e:  # noqa: BLE001
                        logger.error(f"Error executing escalate_to_human: {e}")
                        result_str = json.dumps({"error": f"Falha na execução de escalate_to_human: {e}"})

                    tools_used.append("escalate_to_human")
                    t_msg = ToolMessage(content=result_str, tool_call_id=call_id, name=tool_name)
                    tool_messages.append(t_msg)

                    try:
                        parsed = json.loads(result_str) if isinstance(result_str, str) else result_str
                        if isinstance(parsed, dict):
                            ticket = parsed
                            tool_results.append(parsed)
                    except (json.JSONDecodeError, TypeError):
                        pass

            else:
                logger.warning(f"Tool '{tool_name}' not available to SupervisorAgent.")
                err_payload = json.dumps({"error": f"tool {tool_name} not available to SupervisorAgent"})
                t_msg = ToolMessage(content=err_payload, tool_call_id=call_id, name=tool_name)
                tool_messages.append(t_msg)

        return {
            "messages": tool_messages,
            "agents_used": agents_used,
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
            "agents_used": ["SupervisorAgent"],
            "tools_used": [],
            "tool_calls": [],
            "tool_results": [],
            "sources": [],
            "retrieved_docs": [],
            "ticket": None,
            "final_response": "",
            "supervisor_steps": 0,
            "llm_model": None,
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
            agents_used=result.get("agents_used", ["SupervisorAgent"]),
            tools_used=result.get("tools_used", []),
            tool_calls=result.get("tool_calls", []),
            tool_results=result.get("tool_results", []),
            sources=result.get("sources", []),
            retrieved_docs=result.get("retrieved_docs", []),
            context_docs=result.get("retrieved_docs", []),
            ticket=result.get("ticket"),
            llm_model=result.get("llm_model"),
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
