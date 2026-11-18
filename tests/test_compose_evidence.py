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
