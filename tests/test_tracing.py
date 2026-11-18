"""Offline tests for OpenTelemetry tracing, context propagation, allowlist, and PII privacy."""
from __future__ import annotations

import json
import logging
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode

import src.main as app_main
from src.agents.injection_classifier import InjectionClassifier
from src.config import JsonFormatter, settings
from src.core import tracing
from src.core.graph import OrchestrationGraph
from src.core.notifier import OperatorNotifier
from src.core.tickets_db import TicketsRepository, reset_tickets_repository
from src.rag.reranker import LLMReranker
from tests.fakes import ScriptedChatModel


def test_chat_generates_trace_tree_with_nodes_llm_and_tool_calls(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    exporter = InMemorySpanExporter()
    tracing.configure_tracing(exporter, simple=True)
    try:
        model = ScriptedChatModel(
            responses=[
                AIMessage(
                    content="",
                    tool_calls=[{"id": "tc-1", "name": "ask_knowledge_agent", "args": {"question": "Qual o prazo do Pix?"}}],
                ),
                AIMessage(
                    content="",
                    tool_calls=[{"id": "tk-1", "name": "search_knowledge_base", "args": {"query": "pix"}}],
                ),
                AIMessage(content="O Pix na maquininha Getnet cai na hora."),
                AIMessage(content="O Pix cai na hora pela Getnet (https://site.getnet.com.br/pix/)."),
            ]
        )
        orch = OrchestrationGraph(chat_model=model)
        monkeypatch.setattr(app_main, "get_orchestrator", lambda: orch)

        resp = client.post(
            "/chat",
            json={"message": "Como funciona o Pix?", "session_id": "trace-s1"},
            headers={"X-API-Key": "getnet-dev-key"},
        )
        assert resp.status_code == 200
        spans = exporter.get_finished_spans()
        names = [s.name for s in spans]
        assert "chat.request" in names
        assert any(n.startswith("graph.node.") for n in names)
        assert "llm.call" in names
        assert "tool.call" in names
        root = next(s for s in spans if s.name == "chat.request")
        assert root.attributes.get("http.status_code") == 200
        assert root.attributes.get("app.trace_id", "").startswith("trc-")
        assert "traceparent" in resp.headers
    finally:
        tracing.shutdown_tracing()


def test_chat_continues_incoming_traceparent_and_keeps_x_trace_id(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    exporter = InMemorySpanExporter()
    tracing.configure_tracing(exporter, simple=True)
    try:
        incoming_trace = "4bf92f3577b34da6a3ce929d0e0e4736"
        incoming_parent = "00f067aa0ba902b7"
        orch = OrchestrationGraph(chat_model=ScriptedChatModel(responses=[AIMessage(content="Tudo certo.")]))
        monkeypatch.setattr(app_main, "get_orchestrator", lambda: orch)

        resp = client.post(
            "/chat",
            json={"message": "olá", "session_id": "trace-s2"},
            headers={
                "X-API-Key": "getnet-dev-key",
                "traceparent": f"00-{incoming_trace}-{incoming_parent}-01",
            },
        )
        assert resp.status_code == 200
        assert resp.headers.get("X-Trace-Id", "").startswith("trc-")
        assert incoming_trace in resp.headers.get("traceparent", "")

        spans = exporter.get_finished_spans()
        assert spans
        assert all(format(s.context.trace_id, "032x") == incoming_trace for s in spans)
        root = next(s for s in spans if s.name == "chat.request")
        assert root.parent is not None and format(root.parent.span_id, "016x") == incoming_parent
    finally:
        tracing.shutdown_tracing()


def test_logs_correlate_with_otel_trace_id_and_redact_pii(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    exporter = InMemorySpanExporter()
    tracing.configure_tracing(exporter, simple=True)
    captured: list[str] = []

    class CaptureHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            captured.append(JsonFormatter().format(record))

    handler = CaptureHandler()
    lg = logging.getLogger("multiagent")
    lg.addHandler(handler)
    try:
        incoming_trace = "abcdef0123456789abcdef0123456789"
        orch = OrchestrationGraph(chat_model=ScriptedChatModel(responses=[AIMessage(content="Recebido.")]))
        monkeypatch.setattr(app_main, "get_orchestrator", lambda: orch)

        resp = client.post(
            "/chat",
            json={"message": "Meu cartão 4111 1111 1111 1111 e CPF 529.982.247-25"},
            headers={
                "X-API-Key": "getnet-dev-key",
                "traceparent": f"00-{incoming_trace}-1111222233334444-01",
            },
        )
        assert resp.status_code == 200
        records = [json.loads(line) for line in captured if line.startswith("{")]
        assert any(rec.get("otel_trace_id") == incoming_trace for rec in records)
        raw_logs = "\n".join(captured)
        assert "4111111111111111" not in raw_logs
        assert "4111 1111 1111 1111" not in raw_logs
        assert "52998224725" not in raw_logs
        assert "529.982.247-25" not in raw_logs
    finally:
        lg.removeHandler(handler)
        tracing.shutdown_tracing()


def test_span_privacy_allowlist_drops_unknown_keys_and_forbids_pii(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    exporter = InMemorySpanExporter()
    tracing.configure_tracing(exporter, simple=True)
    try:
        marker = "texto-secreto-cliente-99"
        card = "4111 1111 1111 1111"
        cpf = "529.982.247-25"
        orch = OrchestrationGraph(chat_model=ScriptedChatModel(responses=[AIMessage(content="ok")]))
        monkeypatch.setattr(app_main, "get_orchestrator", lambda: orch)

        with tracing.span("custom.outer", {"tool.name": "t1", "forbidden.attr": marker}):
            tracing.set_attributes({"extra.forbidden": card, "agent.name": "TestAgent"})
            client.post(
                "/chat",
                json={"message": f"Cartão {card} CPF {cpf} {marker}", "session_id": "priv-s1"},
                headers={"X-API-Key": "getnet-dev-key"},
            )

        spans = exporter.get_finished_spans()
        assert spans
        for s in spans:
            assert set(s.attributes or {}) <= tracing.ALLOWED_ATTRIBUTES
            serialized = json.dumps(dict(s.attributes or {}), ensure_ascii=False)
            for secret in (marker, card, "4111111111111111", cpf, "52998224725", "cliente1988", "priv-s1"):
                assert secret not in s.name
                assert secret not in serialized
    finally:
        tracing.shutdown_tracing()


def test_span_records_error_class_without_exception_message() -> None:
    exporter = InMemorySpanExporter()
    tracing.configure_tracing(exporter, simple=True)
    try:
        with pytest.raises(RuntimeError), tracing.span("op.fail", {"tool.name": "broken", "ignored.key": "dropme"}):
            raise RuntimeError("sensitive internal detail 12345")

        finished = [s for s in exporter.get_finished_spans() if s.name == "op.fail"]
        assert len(finished) == 1
        sp = finished[0]
        assert sp.status.status_code == StatusCode.ERROR
        assert sp.status.description == "RuntimeError"
        assert "sensitive internal detail" not in (sp.status.description or "")
        assert not sp.events
        assert "ignored.key" not in (sp.attributes or {})
        assert tracing.current_trace_id() is None
    finally:
        tracing.shutdown_tracing()


def test_classifier_reranker_notifier_and_ticket_patch_emit_spans(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    exporter = InMemorySpanExporter()
    tracing.configure_tracing(exporter, simple=True)
    try:
        clf_model = ScriptedChatModel(
            responses=[
                AIMessage(
                    content="",
                    tool_calls=[{"id": "c1", "name": "GuardrailVerdict", "args": {"verdict": "allow", "category": "none"}}],
                    usage_metadata={"input_tokens": 12, "output_tokens": 4, "total_tokens": 16},
                )
            ]
        )
        clf = InjectionClassifier(model=clf_model)
        assert clf.classify("Qual a taxa do Pix?").status == "ok"

        rerank_model = ScriptedChatModel(
            responses=[
                AIMessage(
                    content="",
                    tool_calls=[{"id": "r1", "name": "RerankVerdict", "args": {"scores": [{"index": 0, "relevance": 3}]}}],
                    usage_metadata={"input_tokens": 20, "output_tokens": 6, "total_tokens": 26},
                )
            ]
        )
        reranker = LLMReranker(model=rerank_model)
        assert reranker.rerank("pix", [{"title": "Pix", "text": "Pix na maquininha"}]).status == "ok"

        transport = httpx.MockTransport(lambda req: httpx.Response(200, json={"ok": True}))
        notifier = OperatorNotifier(
            url="https://hooks.example.test/op",
            client=httpx.Client(transport=transport),
        )
        assert notifier.notify({"ticket_id": "GET-TKT-1", "priority": "high", "created_at": "2026-11-18"}).status == "sent"

        monkeypatch.setattr(settings, "TICKETS_DB_PATH", str(tmp_path / "patch_trace.db"))
        reset_tickets_repository()
        repo = TicketsRepository(settings.TICKETS_DB_PATH)
        monkeypatch.setattr(app_main, "get_tickets_repository", lambda: repo)
        t = repo.create_ticket(user_id="cliente1988", reason="ajuda")
        resp = client.patch(
            f"/tickets/{t['ticket_id']}",
            json={"status": "in_progress"},
            headers={"X-API-Key": "getnet-dev-operator"},
        )
        assert resp.status_code == 200

        spans = exporter.get_finished_spans()
        names = [s.name for s in spans]
        assert names.count("llm.call") == 2
        assert "notifier.webhook" in names
        assert "ticket.update" in names
    finally:
        tracing.shutdown_tracing()
