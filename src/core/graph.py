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
from src.core import metrics
from src.core.checkpointer import build_sqlite_checkpointer
from src.core.llm import (
    LLMConfigurationError,
    LLMNotConfiguredError,
    LLMUnavailableError,
    extract_model_name,
    get_chat_model,
    get_fallback_model,
    invoke_model_with_fallback,
)
from src.core.log_context import exc_brief
from src.core.pii import sanitize_pii
from src.core.state import AgentRole, AgentState, SupervisorState
from src.core.tickets_db import get_tickets_repository, transcript_snapshot
from src.tools.agent_tools import (
    TOOLS_BY_NAME,
    diagnose_declined_transaction,
    diagnose_terminal,
    get_settlement_status,
    search_knowledge_base,
    search_web,
)
from src.tools.supervisor_tools import SUPERVISOR_TOOLS

KNOWLEDGE_TOOLS = [search_knowledge_base, search_web]
SUPPORT_TOOLS = [get_settlement_status, diagnose_declined_transaction, diagnose_terminal]

logger = logging.getLogger("multiagent.orchestrator")

HANDOFF_PENDING_MESSAGE = (
    "Seu chamado {ticket_id} está com a equipe de atendimento humano. A resposta aparecerá nesta conversa quando for registrada. / "
    "Your request {ticket_id} is with our human support team. The reply will appear in this conversation when it is recorded."
)
HANDOFF_REPLY_PREFIX = "Resposta da equipe de atendimento humano (chamado {ticket_id}) / Reply from our human support team (request {ticket_id}):\n\n"

AUTO_ESCALATION_NOTE = (
    "Como não encontrei essa informação nas fontes oficiais, registrei o chamado {ticket_id} para a equipe de atendimento humano; "
    "a resposta aparecerá nesta conversa quando for registrada. / I could not find this in the official sources, so I registered "
    "request {ticket_id} for our human support team; the reply will appear in this conversation when it is recorded."
)

INSTABILITY_MESSAGE = (
    "Ocorreu uma instabilidade momentânea no atendimento. Por favor, tente novamente. / "
    "A temporary problem occurred while handling your request. Please try again."
)
FORCED_ESCALATION_MESSAGE = (
    "Não consegui concluir sua solicitação automaticamente. Registrei o chamado {ticket_id} para análise de um "
    "especialista humano. / I could not complete your request automatically. I registered ticket {ticket_id} for "
    "review by a human specialist."
)
FORCED_ESCALATION_FAILED_MESSAGE = (
    "Não consegui concluir sua solicitação automaticamente e não foi possível abrir um chamado agora. Tente "
    "novamente mais tarde. / I could not complete your request automatically and could not open a ticket right now. "
    "Please try again later."
)

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
        checkpointer: Any | None = None,
    ):
        self.guardrail_agent = GuardrailAgent()
        self.chat_model: BaseChatModel | None = chat_model
        self.fallback_model: BaseChatModel | None = fallback_model
        self._bound_model: Any = None
        self._bound_fallback: Any = None

        self.knowledge_agent = SpecialistAgent(
            name="KnowledgeAgent",
            prompt_file="knowledge_agent.md",
            tools=KNOWLEDGE_TOOLS,
            chat_model=chat_model,
            fallback_model=fallback_model,
        )
        self.support_agent = SpecialistAgent(
            name="SupportAgent",
            prompt_file="support_agent.md",
            tools=SUPPORT_TOOLS,
            chat_model=chat_model,
            fallback_model=fallback_model,
        )

        self.checkpointer = checkpointer if checkpointer is not None else MemorySaver()
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

    def _wrap_node(self, node_name: str, fn: Any) -> Any:
        def wrapped(state: SupervisorState) -> dict[str, Any]:
            t0 = time.perf_counter()
            try:
                return fn(state)
            finally:
                ms = round((time.perf_counter() - t0) * 1000, 2)
                logger.info("node finished", extra={"node": node_name, "latency_ms": ms})

        return wrapped

    def _build_graph(self):
        builder = StateGraph(SupervisorState)

        # 1. Register Graph Nodes
        builder.add_node("guardrail", self._wrap_node("guardrail", self._guardrail_node))
        builder.add_node("handoff_gate", self._wrap_node("handoff_gate", self._handoff_gate_node))
        builder.add_node("supervisor", self._wrap_node("supervisor", self._supervisor_node))
        builder.add_node("tools", self._wrap_node("tools", self._tools_node))
        builder.add_node("force_escalation", self._wrap_node("force_escalation", self._force_escalation_node))
        builder.add_node("abstention_check", self._wrap_node("abstention_check", self._abstention_check_node))

        # 2. Add Edges
        builder.add_edge(START, "guardrail")

        builder.add_conditional_edges(
            "guardrail",
            self._guardrail_condition,
            {
                "continue": "handoff_gate",
                "stop": END,
            },
        )

        builder.add_conditional_edges(
            "handoff_gate",
            self._handoff_gate_condition,
            {
                "continue": "supervisor",
                "end": END,
            },
        )

        builder.add_conditional_edges(
            "supervisor",
            self._supervisor_condition,
            {
                "tools": "tools",
                "force_escalation": "force_escalation",
                "end": "abstention_check",
            },
        )

        # ReAct observation loop: from tools back to supervisor
        builder.add_edge("tools", "supervisor")
        builder.add_edge("force_escalation", END)
        builder.add_edge("abstention_check", END)

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

        agent_state = AgentState(user_id=state["user_id"], message=raw_msg)
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
        """Route to handoff_gate if safe, else stop immediately."""
        return "continue" if state.get("is_safe", True) else "stop"

    def _handoff_gate_node(self, state: SupervisorState) -> dict[str, Any]:
        """
        Human handoff gate node: checks if the thread is held by an active human escalation ticket.
        If a ticket is pending, either delivers the operator reply or outputs a fixed waiting notice
        without invoking any LLM.
        """
        pending_id = state.get("pending_ticket_id")
        if not pending_id:
            return {"handoff": None}

        repo = get_tickets_repository()
        ticket = repo.get_ticket(pending_id)

        # 1. Ticket does not exist in DB: clear pending_ticket_id and continue to supervisor
        if not ticket:
            return {
                "pending_ticket_id": None,
                "handoff": None,
            }

        operator_reply = ticket.get("operator_reply")
        delivered_at = ticket.get("delivered_at")

        # 2. Operator replied and reply not yet delivered in chat:
        # (answered, or answered and subsequently closed before delivery)
        if operator_reply and not delivered_at:
            delivered = repo.mark_delivered(pending_id)
            if delivered:
                reply_text = HANDOFF_REPLY_PREFIX.format(ticket_id=pending_id) + operator_reply
                return {
                    "messages": [AIMessage(content=reply_text)],
                    "final_response": reply_text,
                    "pending_ticket_id": None,
                    "handoff": {"ticket_id": pending_id, "status": "delivered"},
                    "agents_used": ["HumanHandoff"],
                    "llm_model": None,
                    "tokens": None,
                }
            # Already delivered by a concurrent request: clear pending_ticket_id and resume
            return {
                "pending_ticket_id": None,
                "handoff": {"ticket_id": pending_id, "status": "resumed"},
            }

        # 3. Closed without reply: resume normal bot assistance
        if ticket.get("status") == "closed":
            return {
                "pending_ticket_id": None,
                "handoff": {"ticket_id": pending_id, "status": "resumed"},
            }

        # 4. Otherwise (status 'open' or 'in_progress'): append customer message to ticket and keep waiting notice
        raw_msg = ""
        for m in reversed(state.get("messages", [])):
            if isinstance(m, HumanMessage) or getattr(m, "type", "") in ("human", "user"):
                raw_msg = m.content if isinstance(m.content, str) else str(m.content)
                break
        if raw_msg:
            repo.append_customer_message(pending_id, raw_msg)

        pending_text = HANDOFF_PENDING_MESSAGE.format(ticket_id=pending_id)
        return {
            "messages": [AIMessage(content=pending_text)],
            "final_response": pending_text,
            "handoff": {"ticket_id": pending_id, "status": "pending"},
            "agents_used": ["HumanHandoff"],
            "llm_model": None,
            "tokens": None,
        }

    def _handoff_gate_condition(self, state: SupervisorState) -> str:
        """Route to END if handoff produced a terminal response, else proceed to supervisor."""
        handoff = state.get("handoff")
        status = handoff.get("status") if handoff else None
        if status in ("pending", "delivered"):
            return "end"
        return "continue"

    def _abstention_check_node(self, state: SupervisorState) -> dict[str, Any]:
        """
        Evaluate consecutive knowledge abstentions and auto-escalate when threshold reached.
        """
        # 1. Ticket created this turn by supervisor -> reset counter to 0
        if state.get("ticket"):
            return {"consecutive_abstentions": 0}

        knowledge_outcomes = state.get("knowledge_outcomes", [])
        # 2. Turn without Knowledge Agent -> unchanged
        if not knowledge_outcomes:
            return {}

        # 3. Any call with sources -> reset counter to 0
        if any(knowledge_outcomes):
            return {"consecutive_abstentions": 0}

        # 4. All calls in this turn abstained -> increment counter
        metrics.inc_abstention()
        current_count = state.get("consecutive_abstentions", 0) + 1
        limit = settings.ESCALATE_AFTER_ABSTENTIONS
        pending_id = state.get("pending_ticket_id")

        if limit > 0 and current_count >= limit and not pending_id:
            escalate_tool = TOOLS_BY_NAME.get("escalate_to_human")
            ticket_obj = None
            if escalate_tool:
                try:
                    reason = f"automatic escalation: {current_count} consecutive questions without official sources"
                    escalate_res = escalate_tool.invoke(
                        {"reason": reason, "priority": "standard"},
                        config={
                            "configurable": {
                                "user_id": state["user_id"],
                                "session_id": state["session_id"],
                                "transcript": transcript_snapshot(state["messages"]),
                            }
                        },
                    )
                    parsed = json.loads(escalate_res) if isinstance(escalate_res, str) else escalate_res
                    if isinstance(parsed, dict) and parsed.get("ticket_id"):
                        ticket_obj = parsed
                except Exception as exc:  # noqa: BLE001
                    logger.error(f"Failed to auto-escalate on repeated abstention: {exc_brief(exc)}")

            if ticket_obj and ticket_obj.get("ticket_id"):
                new_tid = ticket_obj["ticket_id"]
                note = AUTO_ESCALATION_NOTE.format(ticket_id=new_tid)
                orig_final = state.get("final_response") or ""
                new_final = f"{orig_final}\n\n{note}" if orig_final else note
                ai_note_msg = AIMessage(content=note)
                tools_used = list(state.get("tools_used", []))
                tools_used.append("escalate_to_human")
                return {
                    "final_response": new_final,
                    "messages": [ai_note_msg],
                    "ticket": ticket_obj,
                    "pending_ticket_id": new_tid,
                    "tools_used": tools_used,
                    "consecutive_abstentions": 0,
                }
            # If persistence failed, keep counter and do not append note
            return {"consecutive_abstentions": current_count}

        return {"consecutive_abstentions": current_count}

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

        tba = state.get("tokens_by_agent")
        u = getattr(ai_message, "usage_metadata", None)
        if u:
            inp = u.get("input_tokens", 0)
            out = u.get("output_tokens", 0)
            tot = u.get("total_tokens", inp + out)
            tba_dict = dict(tba) if tba is not None else {}
            cur = tba_dict.get("SupervisorAgent", {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0})
            tba_dict["SupervisorAgent"] = {
                "input_tokens": cur["input_tokens"] + inp,
                "output_tokens": cur["output_tokens"] + out,
                "total_tokens": cur["total_tokens"] + tot,
            }
            tba = tba_dict

        tokens = None
        if tba:
            tokens = {
                "input_tokens": sum(v["input_tokens"] for v in tba.values()),
                "output_tokens": sum(v["output_tokens"] for v in tba.values()),
                "total_tokens": sum(v["total_tokens"] for v in tba.values()),
            }

        return {
            "messages": [ai_message],
            "final_response": response_text,
            "tool_calls": existing_calls,
            "supervisor_steps": current_steps,
            "llm_model": model_used,
            "tokens_by_agent": tba,
            "tokens": tokens,
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

        user_id = state["user_id"]
        trace_id = state.get("trace_id", "")
        escalate_tool = TOOLS_BY_NAME["escalate_to_human"]

        ticket_obj: dict[str, Any] | None = None
        try:
            escalate_res = escalate_tool.invoke(
                {"reason": "automatic escalation: supervisor step limit reached"},
                config={
                    "configurable": {
                        "user_id": user_id,
                        "session_id": state["session_id"],
                        "transcript": transcript_snapshot(state["messages"]),
                    }
                },
            )
            parsed = json.loads(escalate_res) if isinstance(escalate_res, str) else escalate_res
            if isinstance(parsed, dict) and parsed.get("ticket_id"):
                ticket_obj = parsed
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Failed to create escalation ticket in force_escalation [trace_id={trace_id}]: {exc_brief(exc)}")

        if ticket_obj and ticket_obj.get("ticket_id"):
            ticket_id = ticket_obj["ticket_id"]
            final_text = FORCED_ESCALATION_MESSAGE.format(ticket_id=ticket_id)
        else:
            ticket_obj = None
            final_text = FORCED_ESCALATION_FAILED_MESSAGE
            logger.error(f"Force escalation could not generate a valid ticket [trace_id={trace_id}]")

        escalation_ai_msg = AIMessage(content=final_text)
        tool_messages.append(escalation_ai_msg)

        tools_used = list(state.get("tools_used", []))
        tools_used.append("escalate_to_human")

        ret: dict[str, Any] = {
            "messages": tool_messages,
            "ticket": ticket_obj,
            "final_response": final_text,
            "tools_used": tools_used,
        }
        if ticket_obj and ticket_obj.get("ticket_id"):
            ret["pending_ticket_id"] = ticket_obj["ticket_id"]
        return ret

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
        web_results = list(state.get("web_results", []))
        ticket = state.get("ticket")
        agents_used = list(state.get("agents_used", ["SupervisorAgent"]))

        user_id = state["user_id"]
        trace_id = state.get("trace_id", "")
        tba = state.get("tokens_by_agent")
        knowledge_outcomes = list(state.get("knowledge_outcomes", []))

        for call in tool_calls:
            tool_name = call.get("name")
            tool_args = call.get("args", {})
            call_id = call.get("id", str(uuid.uuid4()))
            call_start = time.perf_counter()
            call_status = "ok"

            if tool_name == "ask_knowledge_agent":
                if "KnowledgeAgent" not in agents_used:
                    agents_used.append("KnowledgeAgent")
                question = tool_args.get("question") or tool_args.get("query") or tool_args.get("task") or ""
                spec_res = self.knowledge_agent.run(question, user_id=user_id, trace_id=trace_id)
                knowledge_outcomes.append(bool(spec_res.get("sources")))
                if spec_res.get("status") == "error":
                    call_status = "error"

                spec_usage = spec_res.get("usage")
                if spec_usage:
                    inp = spec_usage.get("input_tokens", 0)
                    out = spec_usage.get("output_tokens", 0)
                    tot = spec_usage.get("total_tokens", inp + out)
                    tba_dict = dict(tba) if tba is not None else {}
                    cur = tba_dict.get("KnowledgeAgent", {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0})
                    tba_dict["KnowledgeAgent"] = {
                        "input_tokens": cur["input_tokens"] + inp,
                        "output_tokens": cur["output_tokens"] + out,
                        "total_tokens": cur["total_tokens"] + tot,
                    }
                    tba = tba_dict

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
                if spec_res.get("web_results"):
                    web_results.extend(spec_res["web_results"])

            elif tool_name == "ask_support_agent":
                if "SupportAgent" not in agents_used:
                    agents_used.append("SupportAgent")
                request_text = tool_args.get("request") or tool_args.get("task") or tool_args.get("question") or ""
                spec_res = self.support_agent.run(request_text, user_id=user_id, trace_id=trace_id)
                if spec_res.get("status") == "error":
                    call_status = "error"

                spec_usage = spec_res.get("usage")
                if spec_usage:
                    inp = spec_usage.get("input_tokens", 0)
                    out = spec_usage.get("output_tokens", 0)
                    tot = spec_usage.get("total_tokens", inp + out)
                    tba_dict = dict(tba) if tba is not None else {}
                    cur = tba_dict.get("SupportAgent", {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0})
                    tba_dict["SupportAgent"] = {
                        "input_tokens": cur["input_tokens"] + inp,
                        "output_tokens": cur["output_tokens"] + out,
                        "total_tokens": cur["total_tokens"] + tot,
                    }
                    tba = tba_dict

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
                if spec_res.get("web_results"):
                    web_results.extend(spec_res["web_results"])

            elif tool_name == "escalate_to_human":
                escalate_fn = TOOLS_BY_NAME.get("escalate_to_human")
                if escalate_fn:
                    try:
                        result_str = escalate_fn.invoke(
                            tool_args,
                            config={
                                "configurable": {
                                    "user_id": user_id,
                                    "session_id": state["session_id"],
                                    "transcript": transcript_snapshot(state["messages"]),
                                }
                            },
                        )
                    except Exception as e:  # noqa: BLE001
                        call_status = "error"
                        logger.error(f"Error executing escalate_to_human: {type(e).__name__}")
                        result_str = json.dumps({"status": "error", "error": "ticket_persistence_failed"})

                    tools_used.append("escalate_to_human")
                    t_msg = ToolMessage(content=result_str, tool_call_id=call_id, name=tool_name)
                    tool_messages.append(t_msg)

                    try:
                        parsed = json.loads(result_str) if isinstance(result_str, str) else result_str
                        if isinstance(parsed, dict):
                            if parsed.get("status") == "error" or "error" in parsed:
                                call_status = "error"
                            if parsed.get("ticket_id"):
                                ticket = parsed
                            tool_results.append(parsed)
                    except (json.JSONDecodeError, TypeError):
                        pass

            else:
                call_status = "error"
                logger.warning(f"Tool '{tool_name}' not available to SupervisorAgent.")
                err_payload = json.dumps({"error": f"tool {tool_name} not available to SupervisorAgent"})
                t_msg = ToolMessage(content=err_payload, tool_call_id=call_id, name=tool_name)
                tool_messages.append(t_msg)

            latency_ms = round((time.perf_counter() - call_start) * 1000, 2)
            metrics.inc_tool(tool_name, call_status)
            logger.info(
                "tool finished",
                extra={
                    "tool": tool_name,
                    "agent": "SupervisorAgent",
                    "status": call_status,
                    "latency_ms": latency_ms,
                },
            )

        tokens = None
        if tba:
            tokens = {
                "input_tokens": sum(v["input_tokens"] for v in tba.values()),
                "output_tokens": sum(v["output_tokens"] for v in tba.values()),
                "total_tokens": sum(v["total_tokens"] for v in tba.values()),
            }

        ret: dict[str, Any] = {
            "messages": tool_messages,
            "agents_used": agents_used,
            "tools_used": tools_used,
            "tool_results": tool_results,
            "sources": sources,
            "retrieved_docs": retrieved_docs,
            "web_results": web_results,
            "ticket": ticket,
            "tokens_by_agent": tba,
            "tokens": tokens,
            "knowledge_outcomes": knowledge_outcomes,
        }
        if ticket and ticket.get("ticket_id"):
            ret["pending_ticket_id"] = ticket["ticket_id"]
        return ret

    def _close_dangling_tool_calls(self, config: dict[str, Any], error: str) -> None:
        """
        After a failed turn, answer every tool call left without a ToolMessage in the thread, so the
        next turn never sends an orphan tool call to the provider. Never raises.
        """
        try:
            snapshot = self.graph.get_state(config)
            messages = (snapshot.values or {}).get("messages", []) if snapshot else []
            answered = {m.tool_call_id for m in messages if isinstance(m, ToolMessage)}
            pending = [
                call
                for m in messages
                if isinstance(m, AIMessage)
                for call in (m.tool_calls or [])
                if call.get("id") and call.get("id") not in answered
            ]
            if not pending:
                return
            closing = [
                ToolMessage(
                    content=json.dumps({"status": "error", "error": error}),
                    tool_call_id=call["id"],
                    name=call.get("name"),
                )
                for call in pending
            ]
            # abstention_check leads straight to END, so the thread is not left waiting for a node.
            self.graph.update_state(config, {"messages": closing}, as_node="abstention_check")
            logger.warning(f"Closed {len(closing)} dangling tool call(s) after a failed turn")
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Could not close dangling tool calls: {type(exc).__name__}")

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
        if not user_id or not user_id.strip():
            raise ValueError("user_id is required")

        # Mask card numbers and CPFs before the message enters the graph: the checkpointer writes the
        # input state before any node runs, so masking only inside the guardrail left raw values on disk.
        safe_message, _ = sanitize_pii(message)
        start_time = time.perf_counter()
        active_session_id = session_id or str(uuid.uuid4())
        active_trace_id = trace_id or f"trc-{uuid.uuid4().hex[:12]}"
        msg_id = str(uuid.uuid4())

        from src.core.log_context import bind

        with bind(active_trace_id, active_session_id, user_id):
            initial_state: SupervisorState = {
                "messages": [HumanMessage(content=safe_message, id=msg_id)],
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
                "web_results": [],
                "ticket": None,
                "handoff": None,
                "knowledge_outcomes": [],
                "final_response": "",
                "supervisor_steps": 0,
                "llm_model": None,
                "execution_time_ms": 0.0,
                "tokens": None,
                "tokens_by_agent": None,
                "estimated_cost_usd": None,
            }

            # Checkpointer thread configuration
            config = {"configurable": {"thread_id": f"{user_id}:{active_session_id}"}}

            logger.info("workflow started")

            try:
                result = self.graph.invoke(initial_state, config=config)
            except (LLMNotConfiguredError, LLMConfigurationError, LLMUnavailableError) as exc:
                self._close_dangling_tool_calls(config, type(exc).__name__)
                raise
            except Exception as exc:  # noqa: BLE001
                logger.error(f"Error in LangGraph execution: {exc_brief(exc)}")
                self._close_dangling_tool_calls(config, "internal_error")
                result = initial_state
                result["final_response"] = INSTABILITY_MESSAGE
                result["error"] = "internal_error"

            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

            # Extract final reply
            final_text = result.get("final_response", "")
            if not final_text and result.get("messages"):
                for m in reversed(result["messages"]):
                    if isinstance(m, AIMessage) and m.content:
                        final_text = m.content if isinstance(m.content, str) else str(m.content)
                        break

            tokens_dict = result.get("tokens")
            model_name = result.get("llm_model")
            cost_val = None
            if tokens_dict and isinstance(tokens_dict, dict):
                from src.core.pricing import cost_usd

                cost_val = cost_usd(
                    model_name,
                    tokens_dict.get("input_tokens"),
                    tokens_dict.get("output_tokens"),
                )
                metrics.add_tokens(
                    tokens_dict.get("input_tokens"),
                    tokens_dict.get("output_tokens"),
                )
            else:
                metrics.add_tokens(None, None)

            # Map to backward-compatible AgentState
            agent_state = AgentState(
                user_id=user_id,
                message=safe_message,
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
                web_results=result.get("web_results", []),
                context_docs=result.get("retrieved_docs", []),
                ticket=result.get("ticket"),
                handoff=result.get("handoff"),
                llm_model=model_name,
                agent_response=final_text,
                final_agent=AgentRole.SUPERVISOR,
                escalate_to_human=bool(result.get("ticket")),
                escalation_ticket_id=result.get("ticket", {}).get("ticket_id") if result.get("ticket") else None,
                intent="dynamic_react",
                execution_time_ms=elapsed_ms,
                tokens=tokens_dict,
                tokens_by_agent=result.get("tokens_by_agent"),
                estimated_cost_usd=cost_val,
                error=result.get("error"),
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
        checkpointer = build_sqlite_checkpointer(settings.CHECKPOINT_DB_PATH)
        _orchestrator_instance = OrchestrationGraph(checkpointer=checkpointer)
    return _orchestrator_instance
