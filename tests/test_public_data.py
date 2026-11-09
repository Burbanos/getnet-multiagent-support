"""Offline unit and acceptance tests for Open-Meteo and Banco Central PTAX public data client."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from src.config import settings
from src.tools import public_data as pd

FIXTURES_DIR = Path("tests/fixtures/public_data")


def _fixture_client() -> httpx.Client:
    manifest_path = FIXTURES_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))["files"]
    by_url = {httpx.URL(v["url"]): (name, v["status_code"]) for name, v in manifest.items()}

    def handler(request: httpx.Request) -> httpx.Response:
        hit = by_url.get(request.url)
        if hit is None:
            return httpx.Response(404, json={"error": "unexpected url in fixture transport"})
        name, status = hit
        content = (FIXTURES_DIR / f"{name}.json").read_bytes()
        return httpx.Response(status, content=content)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_urls_match_captured_fixtures() -> None:
    manifest = json.loads((FIXTURES_DIR / "manifest.json").read_text(encoding="utf-8"))["files"]
    poa_geo = json.loads((FIXTURES_DIR / "geocoding_porto_alegre.json").read_text(encoding="utf-8"))["results"][0]

    assert pd.geocoding_url("Porto Alegre", "BR") == manifest["geocoding_porto_alegre"]["url"]
    assert pd.geocoding_url("São Paulo", "BR") == manifest["geocoding_sao_paulo"]["url"]
    assert pd.geocoding_url("Xqzvbnm Nowhereville") == manifest["geocoding_unknown"]["url"]
    assert (
        pd.forecast_request_url(poa_geo["latitude"], poa_geo["longitude"], 3)
        == manifest["forecast_porto_alegre"]["url"]
    )
    assert pd.moedas_url() == manifest["ptax_moedas"]["url"]
    assert (
        pd.ptax_period_url("EUR", dt.date(2026, 11, 6), dt.date(2026, 11, 6))
        == manifest["ptax_eur_20261106"]["url"]
    )
    assert (
        pd.ptax_period_url("USD", dt.date(2026, 11, 6), dt.date(2026, 11, 6))
        == manifest["ptax_usd_20261106"]["url"]
    )
    assert (
        pd.ptax_period_url("JPY", dt.date(2026, 11, 6), dt.date(2026, 11, 6))
        == manifest["ptax_jpy_20261106"]["url"]
    )
    assert (
        pd.ptax_period_url("EUR", dt.date(2026, 11, 7), dt.date(2026, 11, 7))
        == manifest["ptax_eur_20261107"]["url"]
    )
    assert (
        pd.ptax_period_url("EUR", dt.date(2026, 10, 30), dt.date(2026, 11, 9))
        == manifest["ptax_eur_20261030_20261109"]["url"]
    )
    assert (
        pd.ptax_period_url("XYZ", dt.date(2026, 11, 6), dt.date(2026, 11, 6))
        == manifest["ptax_xyz_20261106"]["url"]
    )


def test_weather_success_from_fixtures() -> None:
    client = _fixture_client()
    res = pd.fetch_weather("Porto Alegre", "BR", forecast_days=3, client=client)

    assert res["status"] == "success"
    assert res["source"] == "Open-Meteo"
    assert res["attribution"] == pd.WEATHER_ATTRIBUTION
    assert "geocoding_url" in res
    assert "source_url" in res
    assert res["location"]["name"] == "Porto Alegre"
    assert res["location"]["country_code"] == "BR"
    assert res["current"] is not None
    assert "temperature" in res["current"]
    assert "weather_description" in res["current"]

    assert len(res["days"]) == 3
    day1 = res["days"][0]
    assert day1["weather_description"] == pd.WMO_CODES.get(day1["weather_code"])
    assert day1["temperature_max"]["unit"] == "°C"
    assert day1["temperature_min"]["unit"] == "°C"
    assert day1["precipitation_sum"]["unit"] == "mm"


def test_weather_unknown_city_not_found() -> None:
    client = _fixture_client()
    res = pd.fetch_weather("Xqzvbnm Nowhereville", client=client)

    assert res["status"] == "not_found"
    assert res["source"] == "Open-Meteo"
    assert res["city"] == "Xqzvbnm Nowhereville"
    assert "source_url" in res


def test_weather_invalid_requests() -> None:
    client = _fixture_client()

    cases = [
        ("", None, 3, "invalid_city"),
        ("   ", None, 3, "invalid_city"),
        ("a" * 101, None, 3, "invalid_city"),
        ("Porto Alegre", "BRA", 3, "invalid_country_code"),
        ("Porto Alegre", "B1", 3, "invalid_country_code"),
        ("Porto Alegre", None, 0, "invalid_forecast_days"),
        ("Porto Alegre", None, 8, "invalid_forecast_days"),
    ]

    for city, cc, days, expected_err in cases:
        res = pd.fetch_weather(city, cc, days, client=client)
        assert res["status"] == "invalid_request"
        assert res["source_url"] is None
        assert res["error"] == expected_err


@pytest.mark.parametrize(
    ("handler", "expected_error"),
    [
        (lambda r: (_ for _ in ()).throw(httpx.ReadTimeout("timeout", request=r)), "timeout"),
        (lambda r: (_ for _ in ()).throw(httpx.ConnectError("network", request=r)), "network_error"),
        (lambda r: httpx.Response(500, text="internal error"), "http_500"),
        (lambda r: httpx.Response(200, text="<html>invalid"), "invalid_payload"),
        (lambda r: httpx.Response(200, json={"results": [{"name": "NoCoords"}]}), "invalid_payload"),
    ],
)
def test_weather_unavailable_errors(handler: Any, expected_error: str) -> None:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    res = pd.fetch_weather("Porto Alegre", "BR", client=client)

    assert res["status"] == "unavailable"
    assert res["source"] == "Open-Meteo"
    assert res["error"] == expected_error
    assert "days" not in res
    assert "current" not in res


@pytest.mark.parametrize("currency", ["EUR", "USD", "JPY"])
def test_fx_closing_rate_on_business_day(currency: str) -> None:
    client = _fixture_client()
    req_date = dt.date(2026, 11, 6)
    ref_today = dt.date(2026, 11, 9)

    res = pd.fetch_exchange_rate(currency, req_date, client=client, today=ref_today)

    assert res["status"] == "success"
    assert res["currency"] == currency
    assert res["bulletin"] == "Fechamento"
    assert res["reference_date"] == "2026-11-06"
    assert res["requested_date"] == "2026-11-06"
    assert res["buy"]["unit"] == f"BRL per 1 {currency}"
    assert res["sell"]["unit"] == f"BRL per 1 {currency}"
    assert isinstance(res["buy"]["value"], (int, float))
    assert isinstance(res["sell"]["value"], (int, float))
    assert res["buy"]["value"] <= res["sell"]["value"]


def test_fx_saturday_no_data() -> None:
    client = _fixture_client()
    sat_date = dt.date(2026, 11, 7)
    ref_today = dt.date(2026, 11, 9)

    res = pd.fetch_exchange_rate("EUR", sat_date, client=client, today=ref_today)

    assert res["status"] == "no_data"
    assert res["currency"] == "EUR"
    assert res["requested_date"] == "2026-11-07"
    assert "buy" not in res
    assert "sell" not in res


def test_fx_latest_uses_last_closing_in_period() -> None:
    client = _fixture_client()
    ref_today = dt.date(2026, 11, 9)

    res = pd.fetch_exchange_rate("EUR", client=client, today=ref_today)

    assert res["status"] == "success"
    assert res["currency"] == "EUR"
    assert res["bulletin"] == "Fechamento"
    assert res["reference_date"] == "2026-11-06"
    assert res["requested_date"] is None
    assert "buy" in res
    assert "sell" in res


def test_fx_unknown_currency_not_found() -> None:
    client = _fixture_client()
    ref_today = dt.date(2026, 11, 9)

    res = pd.fetch_exchange_rate("XYZ", client=client, today=ref_today)

    assert res["status"] == "not_found"
    assert res["source"] == pd.FX_SOURCE
    assert res["currency"] == "XYZ"


def test_fx_invalid_requests() -> None:
    client = _fixture_client()
    ref_today = dt.date(2026, 11, 9)

    invalid_cases = [
        ("BRL", None, "invalid_currency"),
        ("US", None, "invalid_currency"),
        ("usd1", None, "invalid_currency"),
        ("", None, "invalid_currency"),
        ("USD", dt.date(2026, 11, 10), "future_date"),
    ]

    for curr, qdate, expected_err in invalid_cases:
        res = pd.fetch_exchange_rate(curr, qdate, client=client, today=ref_today)
        assert res["status"] == "invalid_request"
        assert res["source_url"] is None
        assert res["error"] == expected_err


@pytest.mark.parametrize(
    ("moedas_resp", "period_resp", "expected_error"),
    [
        (
            lambda r: (_ for _ in ()).throw(httpx.ReadTimeout("timeout", request=r)),
            None,
            "timeout",
        ),
        (
            lambda r: httpx.Response(503, text="Service Unavailable"),
            None,
            "http_503",
        ),
        (
            lambda r: httpx.Response(200, json={"value": "not-a-list"}),
            None,
            "invalid_payload",
        ),
        (
            lambda r: httpx.Response(200, json={"value": [{"simbolo": "EUR", "nomeFormatado": "Euro"}]}),
            lambda r: (_ for _ in ()).throw(httpx.ConnectError("conn", request=r)),
            "network_error",
        ),
        (
            lambda r: httpx.Response(200, json={"value": [{"simbolo": "EUR", "nomeFormatado": "Euro"}]}),
            lambda r: httpx.Response(503, text="Service Unavailable"),
            "http_503",
        ),
        (
            lambda r: httpx.Response(200, json={"value": [{"simbolo": "EUR", "nomeFormatado": "Euro"}]}),
            lambda r: httpx.Response(200, text="not json"),
            "invalid_payload",
        ),
    ],
)
def test_fx_unavailable_errors(moedas_resp: Any, period_resp: Any, expected_error: str) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if "Moedas" in url_str:
            return moedas_resp(request)
        if period_resp is not None:
            return period_resp(request)
        return httpx.Response(404)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    res = pd.fetch_exchange_rate("EUR", dt.date(2026, 11, 6), client=client, today=dt.date(2026, 11, 9))

    assert res["status"] == "unavailable"
    assert res["source"] == pd.FX_SOURCE
    assert res["error"] == expected_error


def test_default_client_uses_timeout_and_user_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    created_configs: list[dict[str, Any]] = []
    instances: list[httpx.Client] = []
    real_client_cls = httpx.Client

    class SpyClient(real_client_cls):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            created_configs.append(dict(kwargs))
            kwargs.pop("transport", None)
            manifest_path = FIXTURES_DIR / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))["files"]
            by_url = {httpx.URL(v["url"]): (name, v["status_code"]) for name, v in manifest.items()}

            def handler(request: httpx.Request) -> httpx.Response:
                hit = by_url.get(request.url)
                if hit is None:
                    return httpx.Response(404, json={"error": "not found"})
                name, status = hit
                content = (FIXTURES_DIR / f"{name}.json").read_bytes()
                return httpx.Response(status, content=content)

            super().__init__(*args, transport=httpx.MockTransport(handler), **kwargs)
            instances.append(self)

    monkeypatch.setattr(httpx, "Client", SpyClient)

    w_res = pd.fetch_weather("Porto Alegre", "BR")
    fx_res = pd.fetch_exchange_rate("EUR", dt.date(2026, 11, 6), today=dt.date(2026, 11, 9))

    assert w_res["status"] == "success"
    assert fx_res["status"] == "success"
    assert len(created_configs) == 2
    assert all(cfg.get("timeout") == settings.PUBLIC_DATA_TIMEOUT_S for cfg in created_configs)
    assert all((cfg.get("headers") or {}).get("User-Agent") == pd.USER_AGENT for cfg in created_configs)
    assert all(inst.is_closed for inst in instances)
