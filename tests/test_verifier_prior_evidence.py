"""Offline tests for prior-turn raw verifier evidence and exclusion of earlier assistant answers."""
from __future__ import annotations

import json
import re
import uuid
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langgraph.checkpoint.memory import MemorySaver

import src.rag.retriever as rag_retriever
from src.config import settings
from src.core.graph import (
    MAX_CONVERSATION_ENTRIES,
    MAX_CONVERSATION_ITEM_CHARS,
    MAX_CONVERSATION_TOTAL_CHARS,
    MAX_EVIDENCE_ITEM_CHARS,
    MAX_EVIDENCE_TOTAL_CHARS,
    VERIFIER_ABSTENTION_MESSAGE,
    OrchestrationGraph,
    build_verifier_conversation,
    build_verifier_evidence,
)
from tests.fakes import ScriptedChatModel


def _tc(name: str, args: dict[str, Any]) -> AIMessage:
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": f"call_{uuid.uuid4().hex[:8]}"}])


def _plan(steps: list[dict[str, str]] | None = None) -> AIMessage:
    return _tc(
        "TurnPlan",
        {
            "reply_language": "pt",
            "scope": "support",
            "escalation_request": "none",
            "action_confirmation": "none",
            "steps": steps if steps is not None else [{"goal": "Answer merchant", "delegate": "knowledge"}],
        },
    )


def _msg_text(m: Any) -> str:
    c = getattr(m, "content", "")
    return c if isinstance(c, str) else json.dumps(c, ensure_ascii=False)


def _oracle_verifier(required_per_call: list[list[str]]) -> ScriptedChatModel:
    class _Oracle(ScriptedChatModel):
        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            idx = len(self.received)
            self.received.append(list(messages))
            req = required_per_call[idx] if idx < len(required_per_call) else []
            body = re.sub(r"(?s)<draft>.*?</draft>", "", _msg_text(messages[-1]))
            body = re.sub(r"(?s)<message>.*?</message>", "", body)
            missing = [s for s in req if s not in body]
            verdict = {
                "step": 1,
                "verdict": "unsupported_claim" if missing else "answered",
                "note": f"missing {missing[0]}" if missing else "",
            }
            return ChatResult(
                generations=[ChatGeneration(message=_tc("Verification", {"verdicts": [verdict]}))]
            )

    return _Oracle()


class _KBStub:
    def __init__(self, text: str) -> None:
        self.text = text

    def search(self, query: str) -> dict[str, Any]:
        return {
            "status": "success",
            "query": query,
            "min_score": 0.61,
            "documents": [
                {
                    "url": "https://site.getnet.com.br/get-tap/",
                    "title": "Get Tap",
                    "chunk_id": "chk-prior-1",
                    "score": 0.92,
                    "fetched_at": "2026-11-18T00:00:00+00:00",
                    "text": self.text,
                }
            ],
        }


def test_follow_up_supported_by_previous_turn_raw_evidence(monkeypatch: Any) -> None:
    monkeypatch.setattr(settings, "LANGUAGE_ENFORCEMENT_ENABLED", False)
    monkeypatch.setattr(
        rag_retriever,
        "get_knowledge_retriever",
        lambda: _KBStub("Get Tap exige Android 12 com NFC e token RAW-PRIOR-8821."),
    )
    chat = ScriptedChatModel(
        responses=[
            _tc("ask_knowledge_agent", {"question": "Get Tap"}),
            _tc("search_knowledge_base", {"query": "Get Tap"}),
            AIMessage(content="Get Tap compatível com Android 12."),
            AIMessage(content="O Get Tap funciona em Android 12 com NFC (resumo anterior)."),
            AIMessage(content="Exige também NFC e RAW-PRIOR-8821, conforme a página oficial."),
        ]
    )
    planner = ScriptedChatModel(
        responses=[
            _plan([{"goal": "Get Tap specs", "delegate": "knowledge"}]),
            _plan([{"goal": "Answer follow-up", "delegate": "none"}]),
        ]
    )
    ver = _oracle_verifier([[], ["RAW-PRIOR-8821"]])
    orch = OrchestrationGraph(
        chat_model=chat,
        planner_model=planner,
        verifier_model=ver,
        checkpointer=MemorySaver(),
    )

    st1 = orch.run_sync("cliente1988", "Como funciona o Get Tap?", session_id="s-prior-ok")
    assert (st1.verification or {}).get("status") == "passed"

    st2 = orch.run_sync("cliente1988", "E qual outro requisito ele pede?", session_id="s-prior-ok")
    assert (st2.verification or {}).get("status") == "passed"
    assert (st2.verification or {}).get("replans") == 0

    in2 = _msg_text(ver.received[1][-1])
    conv_block = in2.split("<conversation>", 1)[-1].split("</conversation>", 1)[0]
    ev_block = in2.split("<evidence>", 1)[-1].split("</evidence>", 1)[0]

    assert "Como funciona o Get Tap?" in conv_block
    assert "resumo anterior" not in conv_block
    assert "[earlier turn: KnowledgeAgent/search_knowledge_base]" in ev_block
    assert "RAW-PRIOR-8821" in ev_block

    snap2 = orch.graph.get_state({"configurable": {"thread_id": "cliente1988:s-prior-ok"}})
    vals2 = snap2.values or {}
    assert vals2.get("turn_evidence") == []
    assert any("RAW-PRIOR-8821" in str(it.get("content", "")) for it in (vals2.get("prior_turn_evidence") or []))


def test_earlier_assistant_answer_without_raw_evidence_is_rejected(monkeypatch: Any) -> None:
    monkeypatch.setattr(settings, "LANGUAGE_ENFORCEMENT_ENABLED", False)
    monkeypatch.setattr(
        rag_retriever,
        "get_knowledge_retriever",
        lambda: _KBStub("Taxa de débito é 1,09% na Get Conta."),
    )
    chat = ScriptedChatModel(
        responses=[
            _tc("ask_knowledge_agent", {"question": "taxa débito"}),
            _tc("search_knowledge_base", {"query": "taxa débito"}),
            AIMessage(content="Taxa de débito é 1,09%."),
            AIMessage(content="Taxa 1,09% e prazo SOMENTE-ASSISTENTE-55 dias."),
            AIMessage(content="O prazo é SOMENTE-ASSISTENTE-55 dias."),
            AIMessage(content="Reforço: SOMENTE-ASSISTENTE-55 dias."),
        ]
    )
    planner = ScriptedChatModel(
        responses=[
            _plan([{"goal": "Explain debit fee", "delegate": "knowledge"}]),
            _plan([{"goal": "Repeat deadline", "delegate": "none"}]),
        ]
    )
    ver = _oracle_verifier([[], ["SOMENTE-ASSISTENTE-55"], ["SOMENTE-ASSISTENTE-55"]])
    orch = OrchestrationGraph(
        chat_model=chat,
        planner_model=planner,
        verifier_model=ver,
        checkpointer=MemorySaver(),
    )

    orch.run_sync("cliente1988", "Qual a taxa de débito?", session_id="s-prior-no")
    st2 = orch.run_sync("cliente1988", "Qual era o prazo mesmo?", session_id="s-prior-no")

    assert (st2.verification or {}).get("status") == "abstained"
    assert (st2.verification or {}).get("replans") == 1
    assert st2.agent_response == VERIFIER_ABSTENTION_MESSAGE["pt"]
    assert len(st2.rejected_drafts) == 2
    assert all("SOMENTE-ASSISTENTE-55" in d for d in st2.rejected_drafts)


def test_build_verifier_conversation_excludes_assistant_messages() -> None:
    msgs = [
        HumanMessage(content="Pergunta 1 do lojista"),
        AIMessage(content="Resposta 1 inventada do assistente"),
        AIMessage(content="", tool_calls=[{"name": "ask_support_agent", "args": {"request": "x"}, "id": "t1"}]),
        ToolMessage(content="TOOL-RAW-NEVER", tool_call_id="t1", name="ask_support_agent"),
        HumanMessage(content="Ajuste feito pelo operador.", additional_kwargs={"origin": "operator"}),
        HumanMessage(content="Pergunta atual"),
    ]
    conv = build_verifier_conversation(msgs, merchant_idx=5)
    assert "merchant: Pergunta 1 do lojista" in conv
    assert "operator: Ajuste feito pelo operador." in conv
    assert "assistant:" not in conv
    assert "Resposta 1 inventada" not in conv
    assert "TOOL-RAW-NEVER" not in conv
    assert "Pergunta atual" not in conv

    many: list[HumanMessage | AIMessage] = []
    for i in range(12):
        many.append(HumanMessage(content=f"Q{i:02d} " + ("m" * 2000)))
        many.append(AIMessage(content=f"A{i:02d} " + ("a" * 2000)))
    many.append(HumanMessage(content="CURR"))
    capped = build_verifier_conversation(many, merchant_idx=len(many) - 1)
    entries = re.findall(r"(?m)^(merchant|operator):", capped)
    assert 0 < len(entries) <= MAX_CONVERSATION_ENTRIES
    assert len(capped) <= MAX_CONVERSATION_TOTAL_CHARS
    assert "assistant:" not in capped and "A11" not in capped
    assert all(
        len(seg.rstrip("\n")) <= MAX_CONVERSATION_ITEM_CHARS + len("operator: ")
        for seg in re.split(r"(?m)^(?=merchant:|operator:)", capped)
        if seg.strip()
    )


def test_build_verifier_evidence_keeps_current_turn_first_and_drops_prior_first() -> None:
    turn_msgs = [
        HumanMessage(content="msg"),
        AIMessage(content="", tool_calls=[{"name": "ask_knowledge_agent", "args": {"question": "q"}, "id": "k1"}]),
        ToolMessage(content="CUR-SUMMARY", tool_call_id="k1", name="ask_knowledge_agent"),
    ]
    cur = [{"agent": "KnowledgeAgent", "tool": "search_knowledge_base", "content": "CUR-RAW"}]
    prior = [{"agent": "SupportAgent", "tool": "get_settlement_status", "content": "PRIOR-RAW " + ("x" * 7000)}]

    ev, trunc = build_verifier_evidence(turn_msgs, 0, cur, prior_evidence=prior)
    assert trunc is True
    assert ev.find("CUR-SUMMARY") < ev.find("CUR-RAW") < ev.find("[earlier turn: SupportAgent/get_settlement_status]")
    run_x = re.search(r"PRIOR-RAW x+", ev)
    assert run_x is not None and len(run_x.group(0)) <= MAX_EVIDENCE_ITEM_CHARS

    huge_cur = [{"agent": "KnowledgeAgent", "tool": "search_knowledge_base", "content": f"BIG{i} " + ("z" * 9000)} for i in range(4)]
    ev_cap, trunc_cap = build_verifier_evidence(turn_msgs, 0, huge_cur, prior_evidence=prior)
    assert trunc_cap is True
    assert len(ev_cap) <= MAX_EVIDENCE_TOTAL_CHARS
    assert "BIG0" in ev_cap
    assert "PRIOR-RAW" not in ev_cap


def test_prior_turn_evidence_persists_even_after_abstained_turn(monkeypatch: Any) -> None:
    monkeypatch.setattr(settings, "LANGUAGE_ENFORCEMENT_ENABLED", False)
    monkeypatch.setattr(
        rag_retriever,
        "get_knowledge_retriever",
        lambda: _KBStub("Dados RAW-AFTER-ABSTAIN-77."),
    )
    chat = ScriptedChatModel(
        responses=[
            _tc("ask_knowledge_agent", {"question": "q"}),
            _tc("search_knowledge_base", {"query": "q"}),
            AIMessage(content="ok"),
            AIMessage(content="Rascunho 1 sem apoio NO-SUPPORT."),
            AIMessage(content="Rascunho 2 sem apoio NO-SUPPORT."),
            AIMessage(content="No segundo turno uso RAW-AFTER-ABSTAIN-77."),
        ]
    )
    planner = ScriptedChatModel(
        responses=[
            _plan([{"goal": "Check info", "delegate": "knowledge"}]),
            _plan([{"goal": "Use prior info", "delegate": "none"}]),
        ]
    )
    ver = _oracle_verifier([["NO-SUPPORT"], ["NO-SUPPORT"], ["RAW-AFTER-ABSTAIN-77"]])
    orch = OrchestrationGraph(
        chat_model=chat,
        planner_model=planner,
        verifier_model=ver,
        checkpointer=MemorySaver(),
    )
    st1 = orch.run_sync("cliente1988", "Pergunta 1?", session_id="s-prior-abstain")
    assert (st1.verification or {}).get("status") == "abstained"

    st2 = orch.run_sync("cliente1988", "Qual o código bruto?", session_id="s-prior-abstain")
    assert (st2.verification or {}).get("status") == "passed"
