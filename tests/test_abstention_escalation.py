"""Unit and integration tests for Phase 5C repeated-abstention auto-escalation and handoff gate fixes."""
from __future__ import annotations

import json
from pathlib import Path

from langchain_core.messages import AIMessage

import src.core.graph as graph_mod
import src.core.tickets_db as tdb
import src.rag.retriever as rag_retriever
from src.config import settings
from src.core.graph import OrchestrationGraph
from src.tools import agent_tools
from tests.fakes import ScriptedChatModel

CARD_PAN = "4111 1111 1111 1111"


class FakeKnowledgeRetriever:
    """Mock retriever returning either abstain or grounded result."""

    def __init__(self, found: bool = False):
        self.found = found

    def search(self, query: str):
        if not self.found:
            return {"status": "abstain", "query": query, "documents": [], "min_score": 0.61}
        return {
            "status": "success",
            "query": query,
            "min_score": 0.61,
            "documents": [{
                "url": "https://site.getnet.com.br/crediario/",
                "title": "Crediário Getnet",
                "fetched_at": "2026-11-06T00:00:00+00:00",
                "market": "BR",
                "chunk_id": "c1",
                "score": 0.85,
                "text": "Crediário Getnet parcelado em até 48x.",
            }],
        }


def _knowledge_turn(final_response: str = "Não encontrei nas fontes.") -> list[AIMessage]:
    return [
        AIMessage(content="", tool_calls=[{"name": "ask_knowledge_agent", "args": {"question": "q"}, "id": "k1"}]),
        AIMessage(content="", tool_calls=[{"name": "search_knowledge_base", "args": {"query": "q"}, "id": "k2"}]),
        AIMessage(content="Resposta do especialista"),
        AIMessage(content=final_response),
    ]


def test_abstention_counter_increments_on_first_abstention(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "tickets.db"
    monkeypatch.setattr(settings, "TICKETS_DB_PATH", str(db_path))
    monkeypatch.setattr(rag_retriever, "get_knowledge_retriever", lambda: FakeKnowledgeRetriever(found=False))
    tdb.reset_tickets_repository()

    model = ScriptedChatModel(responses=_knowledge_turn("RESPOSTA-1"))
    graph = OrchestrationGraph(chat_model=model)

    res = graph.run_sync(user_id="user_abs", message="Pergunta sem resposta 1", session_id="s1")

    assert res.ticket is None
    state_values = graph.graph.get_state({"configurable": {"thread_id": "user_abs:s1"}}).values
    assert state_values.get("consecutive_abstentions") == 1
    assert state_values.get("pending_ticket_id") is None


def test_auto_escalation_on_second_abstention_with_note_and_pending_ticket(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "tickets.db"
    monkeypatch.setattr(settings, "TICKETS_DB_PATH", str(db_path))
    monkeypatch.setattr(rag_retriever, "get_knowledge_retriever", lambda: FakeKnowledgeRetriever(found=False))
    tdb.reset_tickets_repository()
    repo = tdb.get_tickets_repository()

    model = ScriptedChatModel(responses=_knowledge_turn("R1") + _knowledge_turn("R2"))
    graph = OrchestrationGraph(chat_model=model)

    # First turn: counter becomes 1
    graph.run_sync(user_id="user_abs", message="Pergunta 1", session_id="s2")

    # Second turn: reaches threshold 2 -> auto-escalates
    res2 = graph.run_sync(user_id="user_abs", message="Pergunta 2", session_id="s2")

    tid = res2.escalation_ticket_id
    assert tid is not None
    assert res2.agent_response.startswith("R2")
    assert res2.agent_response.endswith(graph_mod.AUTO_ESCALATION_NOTE.format(ticket_id=tid))
    assert "escalate_to_human" in res2.tools_used

    state_values = graph.graph.get_state({"configurable": {"thread_id": "user_abs:s2"}}).values
    assert state_values.get("consecutive_abstentions") == 0
    assert state_values.get("pending_ticket_id") == tid

    # Verify ticket in DB
    ticket_row = repo.get_ticket(tid)
    assert ticket_row is not None
    assert ticket_row["session_id"] == "s2"
    transcript_str = json.dumps(ticket_row["transcript"], ensure_ascii=False)
    assert "Pergunta 2" in transcript_str


def test_grounded_answer_resets_abstention_counter(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "tickets.db"
    monkeypatch.setattr(settings, "TICKETS_DB_PATH", str(db_path))
    tdb.reset_tickets_repository()

    retriever_mode = {"found": False}
    monkeypatch.setattr(rag_retriever, "get_knowledge_retriever", lambda: FakeKnowledgeRetriever(found=retriever_mode["found"]))

    model = ScriptedChatModel(responses=_knowledge_turn("R1") + _knowledge_turn("R2") + _knowledge_turn("R3"))
    graph = OrchestrationGraph(chat_model=model)

    # Turn 1: abstains -> counter=1
    graph.run_sync(user_id="user_abs", message="Pergunta 1", session_id="s3")
    assert graph.graph.get_state({"configurable": {"thread_id": "user_abs:s3"}}).values.get("consecutive_abstentions") == 1

    # Turn 2: grounded answer with sources -> counter resets to 0
    retriever_mode["found"] = True
    graph.run_sync(user_id="user_abs", message="Pergunta com resposta", session_id="s3")
    assert graph.graph.get_state({"configurable": {"thread_id": "user_abs:s3"}}).values.get("consecutive_abstentions") == 0

    # Turn 3: abstains again -> counter becomes 1, no escalation
    retriever_mode["found"] = False
    res3 = graph.run_sync(user_id="user_abs", message="Pergunta sem resposta de novo", session_id="s3")
    assert res3.ticket is None
    assert graph.graph.get_state({"configurable": {"thread_id": "user_abs:s3"}}).values.get("consecutive_abstentions") == 1


def test_small_talk_does_not_reset_abstention_counter(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "tickets.db"
    monkeypatch.setattr(settings, "TICKETS_DB_PATH", str(db_path))
    monkeypatch.setattr(rag_retriever, "get_knowledge_retriever", lambda: FakeKnowledgeRetriever(found=False))
    tdb.reset_tickets_repository()

    model = ScriptedChatModel(responses=_knowledge_turn("R1") + [AIMessage(content="Olá, bom dia!")] + _knowledge_turn("R2"))
    graph = OrchestrationGraph(chat_model=model)

    # Turn 1: abstains -> counter=1
    graph.run_sync(user_id="user_abs", message="Pergunta 1", session_id="s4")

    # Turn 2: small talk (no Knowledge Agent call) -> counter unchanged
    graph.run_sync(user_id="user_abs", message="Bom dia", session_id="s4")
    assert graph.graph.get_state({"configurable": {"thread_id": "user_abs:s4"}}).values.get("consecutive_abstentions") == 1

    # Turn 3: second abstention -> counter reaches 2 and triggers auto-escalation
    res3 = graph.run_sync(user_id="user_abs", message="Pergunta 2", session_id="s4")
    assert res3.escalation_ticket_id is not None


def test_zero_limit_disables_auto_escalation(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "tickets.db"
    monkeypatch.setattr(settings, "TICKETS_DB_PATH", str(db_path))
    monkeypatch.setattr(settings, "ESCALATE_AFTER_ABSTENTIONS", 0)
    monkeypatch.setattr(rag_retriever, "get_knowledge_retriever", lambda: FakeKnowledgeRetriever(found=False))
    tdb.reset_tickets_repository()

    model = ScriptedChatModel(responses=_knowledge_turn("R1") + _knowledge_turn("R2") + _knowledge_turn("R3"))
    graph = OrchestrationGraph(chat_model=model)

    for i in range(3):
        res = graph.run_sync(user_id="user_abs", message=f"Q{i}", session_id="s5")
        assert res.ticket is None


def test_turn_with_supervisor_escalation_does_not_create_double_ticket(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "tickets.db"
    monkeypatch.setattr(settings, "TICKETS_DB_PATH", str(db_path))
    monkeypatch.setattr(rag_retriever, "get_knowledge_retriever", lambda: FakeKnowledgeRetriever(found=False))
    tdb.reset_tickets_repository()
    repo = tdb.get_tickets_repository()

    both_calls = [
        AIMessage(content="", tool_calls=[{"name": "ask_knowledge_agent", "args": {"question": "q"}, "id": "k1"}]),
        AIMessage(content="", tool_calls=[{"name": "search_knowledge_base", "args": {"query": "q"}, "id": "k2"}]),
        AIMessage(content="não encontrei"),
        AIMessage(content="", tool_calls=[{"name": "escalate_to_human", "args": {"reason": "cliente pediu"}, "id": "e1"}]),
        AIMessage(content="CHAMADO-ABERTO-MANUAL"),
    ]

    model = ScriptedChatModel(responses=_knowledge_turn("R1") + both_calls)
    graph = OrchestrationGraph(chat_model=model)

    # Turn 1: 1 abstention
    graph.run_sync(user_id="user_abs", message="P1", session_id="s6")

    before = len(repo.list_tickets(user_id="user_abs", limit=200))
    # Turn 2: abstention + explicit escalation
    res2 = graph.run_sync(user_id="user_abs", message="P2 e quero falar com atendente", session_id="s6")
    after = len(repo.list_tickets(user_id="user_abs", limit=200))

    # Exactly one ticket created this turn
    assert after == before + 1
    assert res2.agent_response == "CHAMADO-ABERTO-MANUAL"


def test_failed_ticket_creation_does_not_append_note_and_keeps_counter(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "tickets.db"
    monkeypatch.setattr(settings, "TICKETS_DB_PATH", str(db_path))
    monkeypatch.setattr(rag_retriever, "get_knowledge_retriever", lambda: FakeKnowledgeRetriever(found=False))
    tdb.reset_tickets_repository()

    class BrokenRepo:
        def create_ticket(self, *args, **kwargs):
            raise OSError("simulated disk full")

    model = ScriptedChatModel(responses=_knowledge_turn("R1") + _knowledge_turn("SEM-NOTA"))
    graph = OrchestrationGraph(chat_model=model)

    # Turn 1: 1st abstention
    graph.run_sync(user_id="user_abs", message="P1", session_id="s7")

    # In turn 2: persistence fails
    monkeypatch.setattr(agent_tools, "get_tickets_repository", lambda: BrokenRepo())
    res2 = graph.run_sync(user_id="user_abs", message="P2", session_id="s7")

    assert res2.agent_response == "SEM-NOTA"
    assert res2.ticket is None
    state_values = graph.graph.get_state({"configurable": {"thread_id": "user_abs:s7"}}).values
    assert state_values.get("consecutive_abstentions") == 2
    assert state_values.get("pending_ticket_id") is None


def test_abstention_counter_isolated_per_user(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "tickets.db"
    monkeypatch.setattr(settings, "TICKETS_DB_PATH", str(db_path))
    monkeypatch.setattr(rag_retriever, "get_knowledge_retriever", lambda: FakeKnowledgeRetriever(found=False))
    tdb.reset_tickets_repository()

    model_a = ScriptedChatModel(responses=_knowledge_turn("A1"))
    model_b = ScriptedChatModel(responses=_knowledge_turn("B1"))
    graph_a = OrchestrationGraph(chat_model=model_a)
    graph_b = OrchestrationGraph(chat_model=model_b, checkpointer=graph_a.checkpointer)

    # User A has 1st abstention
    graph_a.run_sync(user_id="user_a", message="Q", session_id="shared_session")

    # User B has 1st abstention
    res_b = graph_b.run_sync(user_id="user_b", message="Q", session_id="shared_session")
    assert res_b.ticket is None


def test_followup_message_while_waiting_appended_to_ticket_transcript_masked(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "tickets.db"
    monkeypatch.setattr(settings, "TICKETS_DB_PATH", str(db_path))
    tdb.reset_tickets_repository()
    repo = tdb.get_tickets_repository()

    esc_model = ScriptedChatModel(responses=[
        AIMessage(content="", tool_calls=[{"name": "escalate_to_human", "args": {"reason": "atendente"}, "id": "e1"}]),
        AIMessage(content="Chamado registrado"),
    ])
    graph = OrchestrationGraph(chat_model=esc_model)

    res1 = graph.run_sync(user_id="user_w", message="Quero atendente", session_id="sw")
    tid = res1.escalation_ticket_id
    assert tid is not None

    # Customer writes followup while waiting with card number
    graph.run_sync(user_id="user_w", message=f"Mensagem de espera com cartão {CARD_PAN}", session_id="sw")

    ticket_row = repo.get_ticket(tid)
    transcript_str = json.dumps(ticket_row["transcript"], ensure_ascii=False)
    assert "Mensagem de espera" in transcript_str
    assert CARD_PAN not in transcript_str
    assert "4111111111111111" not in transcript_str


def test_mark_delivered_false_does_not_deliver_again_and_resumes(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "tickets.db"
    monkeypatch.setattr(settings, "TICKETS_DB_PATH", str(db_path))
    tdb.reset_tickets_repository()
    repo = tdb.get_tickets_repository()

    esc_model = ScriptedChatModel(responses=[
        AIMessage(content="", tool_calls=[{"name": "escalate_to_human", "args": {"reason": "atendente"}, "id": "e1"}]),
        AIMessage(content="Chamado registrado"),
        AIMessage(content="RESPOSTA-SUPERVISOR-RESUMED"),
    ])
    graph = OrchestrationGraph(chat_model=esc_model)

    res1 = graph.run_sync(user_id="user_race", message="Quero atendente", session_id="sr")
    tid = res1.escalation_ticket_id
    assert tid is not None

    repo.update_ticket(tid, reply="RESPOSTA-DO-OPERADOR", operator_id="ops")

    # Simulate mark_delivered returning False (already delivered concurrently)
    monkeypatch.setattr(tdb.TicketsRepository, "mark_delivered", lambda self, t: False)

    res2 = graph.run_sync(user_id="user_race", message="E aí?", session_id="sr")

    assert "RESPOSTA-DO-OPERADOR" not in res2.agent_response
    assert res2.agent_response == "RESPOSTA-SUPERVISOR-RESUMED"
    state_values = graph.graph.get_state({"configurable": {"thread_id": "user_race:sr"}}).values
    assert state_values.get("pending_ticket_id") is None
