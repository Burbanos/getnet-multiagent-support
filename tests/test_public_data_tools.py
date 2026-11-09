"""Offline unit and integration tests for weather and exchange-rate tools in KnowledgeAgent."""
from __future__ import annotations

import datetime as dt
import json
import logging
from pathlib import Path
from typing import Any

import httpx
import pytest
from langchain_core.messages import AIMessage

import src.core.graph as graph_mod
from src.agents.specialists import SpecialistAgent
from src.core import metrics
from src.tools import agent_tools as at
from src.tools import public_data as pd
from tests.fakes import ScriptedChatModel

FIXTURES_DIR = Path("tests/fixtures/public_data")


class _TransportState:
    def __init__(self) -> None:
        self.handler: Any = None


_transport_state = _TransportState()


def _default_fixtures_handler(request: httpx.Request) -> httpx.Response:
    manifest_path = FIXTURES_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))["files"]
    by_url = {httpx.URL(v["url"]): (name, v["status_code"]) for name, v in manifest.items()}
    hit = by_url.get(request.url)
    if hit is None:
        return httpx.Response(404, json={"error": "unexpected url in fixture transport"})
    name, status = hit
    content = (FIXTURES_DIR / f"{name}.json").read_bytes()
    return httpx.Response(status, content=content)


_transport_state.handler = _default_fixtures_handler


class _PatchedClient(httpx.Client):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.pop("transport", None)
        super().__init__(*args, transport=httpx.MockTransport(lambda r: _transport_state.handler(r)), **kwargs)


@pytest.fixture(autouse=True)
def _patch_httpx_client(monkeypatch: pytest.MonkeyPatch) -> None:
    _transport_state.handler = _default_fixtures_handler
    monkeypatch.setattr(httpx, "Client", _PatchedClient)


def test_tools_registered_for_knowledge_agent() -> None:
    expected_all = [
        "get_settlement_status",
        "diagnose_declined_transaction",
        "diagnose_terminal",
        "search_knowledge_base",
        "get_weather_forecast",
        "get_exchange_rate",
        "search_web",
        "escalate_to_human",
    ]
    expected_k = [
        "search_knowledge_base",
        "get_weather_forecast",
        "get_exchange_rate",
        "search_web",
    ]
    assert [t.name for t in at.ALL_TOOLS] == expected_all
    assert [t.name for t in graph_mod.KNOWLEDGE_TOOLS] == expected_k

    for t in at.ALL_TOOLS:
        assert "user_id" not in t.args
        assert "config" not in t.args

    assert sorted(at.TOOLS_BY_NAME["get_weather_forecast"].args) == ["city", "country_code", "days"]
    assert sorted(at.TOOLS_BY_NAME["get_exchange_rate"].args) == ["currency", "date"]
    assert "get_weather_forecast" in metrics.KNOWN_TOOLS
    assert "get_exchange_rate" in metrics.KNOWN_TOOLS


def test_weather_tool_returns_module_result() -> None:
    tool_raw = at.TOOLS_BY_NAME["get_weather_forecast"].invoke({"city": "Porto Alegre", "country_code": "BR"})
    tool_res = json.loads(tool_raw)
    mod_res = pd.fetch_weather("Porto Alegre", "BR")

    assert tool_res["status"] == "success"

    def strip_time(d: dict[str, Any]) -> dict[str, Any]:
        return {k: v for k, v in d.items() if k != "retrieved_at"}

    assert strip_time(tool_res) == strip_time(mod_res)


def test_exchange_rate_tool_parses_date() -> None:
    # ISO date returns success with closing PTAX
    tool_raw = at.TOOLS_BY_NAME["get_exchange_rate"].invoke({"currency": "EUR", "date": "2026-11-06"})
    tool_res = json.loads(tool_raw)
    mod_res = pd.fetch_exchange_rate("EUR", dt.date(2026, 11, 6))

    assert tool_res["status"] == "success"
    assert tool_res["buy"] == mod_res["buy"]

    # Invalid date string returns invalid_request without performing any HTTP calls
    seen_urls: list[str] = []
    orig_handler = _transport_state.handler

    def tracking_handler(req: httpx.Request) -> httpx.Response:
        seen_urls.append(str(req.url))
        return orig_handler(req)

    _transport_state.handler = tracking_handler
    try:
        bad_raw = at.TOOLS_BY_NAME["get_exchange_rate"].invoke({"currency": "EUR", "date": "06/11/2026"})
        bad_res = json.loads(bad_raw)
        assert bad_res == {
            "status": "invalid_request",
            "source": pd.FX_SOURCE,
            "source_url": None,
            "error": "invalid_date",
        }
        assert len(seen_urls) == 0
    finally:
        _transport_state.handler = orig_handler


def test_knowledge_agent_records_api_results_and_source() -> None:
    def call(name: str, args: dict[str, Any], cid: str = "c1") -> AIMessage:
        return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": cid}])

    agent = SpecialistAgent(
        name="KnowledgeAgent",
        prompt_file="knowledge_agent.md",
        tools=graph_mod.KNOWLEDGE_TOOLS,
        chat_model=ScriptedChatModel(responses=[
            call("get_exchange_rate", {"currency": "EUR", "date": "2026-11-06"}),
            AIMessage(content="O euro em 06/11/2026 fechou em R$ 6,05."),
        ]),
    )
    res = agent.run("Qual o euro em 06/11/2026?", user_id="cliente1988", trace_id="trc-test-fx")

    assert res["status"] == "ok"
    assert "get_exchange_rate" in res["tools_used"]

    manifest = json.loads((FIXTURES_DIR / "manifest.json").read_text(encoding="utf-8"))["files"]
    expected_url = manifest["ptax_eur_20261106"]["url"]
    assert res["sources"] == [expected_url]

    api_results = res.get("api_results", [])
    assert len(api_results) == 1
    assert api_results[0]["tool"] == "get_exchange_rate"
    assert api_results[0]["status"] == "success"
    assert "buy" in api_results[0]


def test_failed_api_call_adds_no_source() -> None:
    def call(name: str, args: dict[str, Any], cid: str = "c1") -> AIMessage:
        return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": cid}])

    orig_handler = _transport_state.handler
    _transport_state.handler = lambda req: httpx.Response(503)
    try:
        agent = SpecialistAgent(
            name="KnowledgeAgent",
            prompt_file="knowledge_agent.md",
            tools=graph_mod.KNOWLEDGE_TOOLS,
            chat_model=ScriptedChatModel(responses=[
                call("get_weather_forecast", {"city": "Porto Alegre", "country_code": "BR"}),
                AIMessage(content="Serviço indisponível."),
            ]),
        )
        res = agent.run("Como está o tempo em Porto Alegre?", user_id="cliente1988", trace_id="trc-test-fail")

        assert res["sources"] == []
        api_results = res.get("api_results", [])
        assert len(api_results) == 1
        assert api_results[0]["status"] == "unavailable"
        assert api_results[0]["error"] == "http_503"
    finally:
        _transport_state.handler = orig_handler


def test_graph_and_api_expose_api_results() -> None:
    def call(name: str, args: dict[str, Any], cid: str) -> AIMessage:
        return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": cid}])

    def script_model() -> ScriptedChatModel:
        return ScriptedChatModel(responses=[
            call("ask_knowledge_agent", {"question": "Previsão para Porto Alegre amanhã"}, "s1"),
            call("get_weather_forecast", {"city": "Porto Alegre", "country_code": "BR"}, "k1"),
            AIMessage(content="Previsão obtida."),
            AIMessage(content="Amanhã em Porto Alegre teremos sol entre nuvens."),
        ])

    manifest = json.loads((FIXTURES_DIR / "manifest.json").read_text(encoding="utf-8"))["files"]
    expected_url = manifest["forecast_porto_alegre"]["url"]

    g = graph_mod.OrchestrationGraph(chat_model=script_model())
    state = g.run_sync("cliente1988", "Previsão para Porto Alegre amanhã?")

    assert state.agent_response == "Amanhã em Porto Alegre teremos sol entre nuvens."
    assert len(state.api_results) == 1
    assert state.api_results[0]["tool"] == "get_weather_forecast"
    assert state.api_results[0]["status"] == "success"
    assert expected_url in state.sources

    from fastapi.testclient import TestClient

    import src.main as app_main

    g2 = graph_mod.OrchestrationGraph(chat_model=script_model())
    orig_orch = app_main.get_orchestrator
    app_main.get_orchestrator = lambda: g2
    try:
        with TestClient(app_main.app) as client:
            resp = client.post(
                "/chat",
                json={"message": "Previsão para Porto Alegre amanhã?"},
                headers={"X-API-Key": "getnet-dev-key"},
            )
            assert resp.status_code == 200
            data = resp.json()
            meta = data.get("metadata", {})
            api_meta = meta.get("api_results", [])
            assert len(api_meta) == 1
            assert api_meta[0]["status"] == "success"
            assert "days" in api_meta[0]
            assert expected_url in meta.get("sources", [])
    finally:
        app_main.get_orchestrator = orig_orch


def test_api_tool_logs_have_no_city_or_currency(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)
    marker = "Zqxmarkville10F"
    orig_handler = _transport_state.handler

    def unknown_city_handler(req: httpx.Request) -> httpx.Response:
        if req.url.host == "geocoding-api.open-meteo.com":
            content = (FIXTURES_DIR / "geocoding_unknown.json").read_bytes()
            return httpx.Response(200, content=content)
        return orig_handler(req)

    _transport_state.handler = unknown_city_handler
    try:
        at.TOOLS_BY_NAME["get_weather_forecast"].invoke({"city": marker})
        at.TOOLS_BY_NAME["get_exchange_rate"].invoke({"currency": "JPY", "date": "2026-11-06"})
        logs = caplog.text
        assert marker not in logs
        assert "JPY" not in logs
        assert "olinda" not in logs
        assert "open-meteo" not in logs
        assert "[Tool: get_weather_forecast] invoked (status=not_found)" in logs
        assert "[Tool: get_exchange_rate] invoked (status=success)" in logs
    finally:
        _transport_state.handler = orig_handler
