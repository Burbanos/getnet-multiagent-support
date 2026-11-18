"""Offline tests for scripts/compose_evidence.py pure helpers and CLI."""
from __future__ import annotations

import os
import subprocess
import sys

import scripts.compose_evidence as ce


def test_scan_pii_counts_all_card_and_cpf_formats() -> None:
    text = (
        f"a {ce.TEST_CARD_SPACED} b {ce.TEST_CARD_DIGITS}{ce.TEST_CARD_DIGITS} "
        f"c {ce.TEST_CPF_FORMATTED} d {ce.TEST_CPF_DIGITS}"
    )
    counts = ce.scan_pii(text)
    assert counts == {
        "card_spaced": 1,
        "card_digits": 2,
        "cpf_formatted": 1,
        "cpf_digits": 1,
    }


def test_summarize_trace_handles_marker_presence_and_empty_payload() -> None:
    payload = {
        "data": [
            {
                "traceID": "abc123",
                "spans": [
                    {
                        "operationName": "graph.node.supervisor",
                        "tags": [{"key": "graph.node", "value": "supervisor"}],
                    },
                    {
                        "operationName": "chat.request",
                        "tags": [
                            {"key": "http.route", "value": "/chat"},
                            {"key": "graph.node", "value": "entry"},
                        ],
                    },
                ],
                "processes": {
                    "p1": {"serviceName": "getnet-multiagent"},
                    "p2": {"serviceName": "getnet-worker"},
                },
            }
        ]
    }
    with_marker = ce.summarize_trace(payload, "supervisor")
    assert with_marker == {
        "trace_id": "abc123",
        "span_count": 2,
        "span_names": ["chat.request", "graph.node.supervisor"],
        "attribute_keys": ["graph.node", "http.route"],
        "services": ["getnet-multiagent", "getnet-worker"],
        "marker_in_attributes": True,
    }
    without_marker = ce.summarize_trace(payload, "missing-marker")
    assert without_marker["marker_in_attributes"] is False
    empty = ce.summarize_trace({"data": []}, "missing-marker")
    assert empty["span_count"] == 0 and empty["trace_id"] is None


def test_compose_evidence_cli_help_and_missing_key() -> None:
    top_help = subprocess.run(
        [sys.executable, "scripts/compose_evidence.py", "--help"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    run_help = subprocess.run(
        [sys.executable, "scripts/compose_evidence.py", "run", "--help"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    env = dict(os.environ, GEMINI_API_KEY="")
    no_key = subprocess.run(
        [sys.executable, "scripts/compose_evidence.py", "run", "--run-id", "test-run"],
        check=False,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert top_help.returncode == 0
    assert run_help.returncode == 0 and "--run-id" in run_help.stdout
    assert no_key.returncode != 0 and "GEMINI_API_KEY" in no_key.stderr


def test_scan_dump_decodes_pg_dump_bytea_hex_blobs_and_plain_text() -> None:
    bs = "\\"
    hex_blob = "92a4" + f"Cartão {ce.TEST_CARD_SPACED} marcador zq-99".encode().hex() + "00ff"
    dirty_dump = (
        "COPY public.checkpoint_blobs (thread_id, blob) FROM stdin;\n"
        f"cliente1988:s1\t{bs}{bs}x{hex_blob}\n"
        f"{bs}.\n"
        "COPY public.tickets (ticket_id, reason) FROM stdin;\n"
        f"GET-TKT-1\tCPF {ce.TEST_CPF_DIGITS} zq-99\n"
        f"{bs}.\n"
    )
    res_dirty = ce.scan_dump(dirty_dump, "zq-99")
    assert res_dirty == {
        "pii": {"card_spaced": 1, "card_digits": 0, "cpf_formatted": 0, "cpf_digits": 1},
        "marker": 2,
        "bytea_values": 1,
    }

    clean_hex = "a1" + "Cartão [CARTAO_OCULTO] ref zq-99".encode().hex()
    clean_dump = (
        "COPY public.checkpoint_blobs (thread_id, blob) FROM stdin;\n"
        f"cliente1988:s1\t{bs}{bs}x{clean_hex}\n"
        f"{bs}.\n"
    )
    res_clean = ce.scan_dump(clean_dump, "zq-99")
    assert res_clean == {
        "pii": {"card_spaced": 0, "card_digits": 0, "cpf_formatted": 0, "cpf_digits": 0},
        "marker": 1,
        "bytea_values": 1,
    }


def test_make_api_keys_and_render_env_isolate_scenarios_without_gemini_key() -> None:
    keys, spec = ce.make_api_keys()
    assert set(keys) == {"conversation", "ticket", "pii", "rate_limit", "operator"}
    assert len(set(keys.values())) == 5
    entries = spec.split(";")
    assert len(entries) == 5
    assert all(raw not in spec for raw in keys.values())
    assert sum(e.endswith(":cliente1988:customer") for e in entries) == 3
    assert sum(e.endswith(":cliente_rl:customer") for e in entries) == 1
    assert sum(e.endswith(":operador_evidencia:operator") for e in entries) == 1

    env_text = ce.render_env("pg-secret-pw", spec)
    assert "GEMINI_API_KEY" not in env_text
    assert "POSTGRES_PASSWORD=pg-secret-pw" in env_text
    assert f"API_KEYS={spec}" in env_text
    assert "RATE_LIMIT_PER_MINUTE=6" in env_text
    assert "TRACING_EXPORTER=otlp" in env_text


def test_ticket_checks_evaluates_delivery_at_patch() -> None:
    msgs = [
        {"role": "customer", "content": "Quero falar com atendente."},
        {"role": "assistant", "content": "Abri o chamado GET-TKT-1."},
        {"role": "assistant", "content": "Resposta do atendente entregue."},
    ]
    ok = ce.ticket_checks(
        200,
        {"status": "answered", "resume": {"status": "resumed"}},
        msgs,
        ["ticket_created", "ticket_updated", "ticket_replied", "ticket_reply_delivered"],
    )
    assert ok == {"ticket_across_replicas": True, "reply_delivered": True}

    failed_resume = ce.ticket_checks(
        200,
        {"status": "answered", "resume": {"status": "failed"}},
        msgs,
        ["ticket_created", "ticket_updated", "ticket_replied", "ticket_reply_delivered"],
    )
    assert failed_resume == {"ticket_across_replicas": True, "reply_delivered": False}

    missing_msg = ce.ticket_checks(
        200,
        {"status": "answered", "resume": {"status": "resumed"}},
        msgs[:2],
        ["ticket_created", "ticket_updated", "ticket_replied", "ticket_reply_delivered"],
    )
    assert missing_msg == {"ticket_across_replicas": True, "reply_delivered": False}

    no_patch = ce.ticket_checks(404, {}, msgs[:2], ["ticket_created"])
    assert no_patch == {"ticket_across_replicas": False, "reply_delivered": False}
