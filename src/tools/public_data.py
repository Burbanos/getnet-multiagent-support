"""Public data client for Open-Meteo weather and Banco Central do Brasil PTAX exchange rates."""
from __future__ import annotations

import datetime as dt
from datetime import UTC, datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote, urlencode

import httpx

from src.config import settings

USER_AGENT = "getnet-multiagent-support/1.0 (+https://github.com/Burbanos/getnet-multiagent-support)"
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
OLINDA = "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
WEATHER_SOURCE = "Open-Meteo"
WEATHER_ATTRIBUTION = "Weather data by Open-Meteo.com (CC BY 4.0)"
FX_SOURCE = "Banco Central do Brasil (PTAX)"
FX_RATE_NOTE = "PTAX closing rate published by the Central Bank of Brazil: a reference rate, not a retail or tourism rate."
CLOSING_BULLETIN = "Fechamento"
LATEST_LOOKBACK_DAYS = 10
BRT = timezone(timedelta(hours=-3))
DAILY_VARS = (
    "weather_code",
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_probability_max",
    "precipitation_sum",
)

WMO_CODES: dict[int, str] = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snowfall",
    73: "Moderate snowfall",
    75: "Heavy snowfall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def geocoding_url(city: str, country_code: str | None = None) -> str:
    """Construct Open-Meteo geocoding search URL."""
    params: dict[str, Any] = {"name": city, "count": 1, "language": "pt", "format": "json"}
    if country_code is not None:
        params["countryCode"] = country_code
    return GEOCODING_URL + "?" + urlencode(params, quote_via=quote)


def forecast_request_url(latitude: float, longitude: float, forecast_days: int) -> str:
    """Construct Open-Meteo forecast URL."""
    return (
        f"{FORECAST_URL}?latitude={latitude}&longitude={longitude}"
        f"&current=temperature_2m,weather_code"
        f"&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum"
        f"&timezone=auto&forecast_days={forecast_days}"
    )


def moedas_url() -> str:
    """Construct Banco Central Olinda Moedas catalog URL."""
    return OLINDA + "Moedas?$format=json"


def ptax_period_url(currency: str, start: dt.date, end: dt.date) -> str:
    """Construct Banco Central Olinda PTAX CotacaoMoedaPeriodo URL."""
    start_str = start.strftime("%m-%d-%Y")
    end_str = end.strftime("%m-%d-%Y")
    return (
        OLINDA
        + "CotacaoMoedaPeriodo(moeda=@moeda,dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)?@moeda='"
        + currency
        + "'&@dataInicial='"
        + start_str
        + "'&@dataFinalCotacao='"
        + end_str
        + "'&$format=json"
    )


def _get_json(client: httpx.Client, url: str) -> tuple[Any, str | None]:
    """Execute GET request and return parsed JSON or an error code."""
    try:
        resp = client.get(url)
    except httpx.TimeoutException:
        return None, "timeout"
    except httpx.HTTPError:
        return None, "network_error"

    if resp.status_code != 200:
        return None, f"http_{resp.status_code}"

    try:
        return resp.json(), None
    except Exception:  # noqa: BLE001
        return None, "invalid_payload"


def fetch_weather(
    city: str,
    country_code: str | None = None,
    forecast_days: int = 3,
    *,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """Fetch current weather and daily forecast for a city via Open-Meteo."""
    if not isinstance(city, str):
        return {"status": "invalid_request", "source": WEATHER_SOURCE, "source_url": None, "error": "invalid_city"}
    city_clean = city.strip()
    if not (1 <= len(city_clean) <= 100):
        return {"status": "invalid_request", "source": WEATHER_SOURCE, "source_url": None, "error": "invalid_city"}

    cc_clean: str | None = None
    if country_code is not None:
        if (
            not isinstance(country_code, str)
            or len(country_code) != 2
            or not country_code.isascii()
            or not country_code.isalpha()
        ):
            return {
                "status": "invalid_request",
                "source": WEATHER_SOURCE,
                "source_url": None,
                "error": "invalid_country_code",
            }
        cc_clean = country_code.upper()

    if isinstance(forecast_days, bool) or not isinstance(forecast_days, int) or not (1 <= forecast_days <= 7):
        return {
            "status": "invalid_request",
            "source": WEATHER_SOURCE,
            "source_url": None,
            "error": "invalid_forecast_days",
        }

    manage_client = client is None
    c = client or httpx.Client(
        timeout=settings.PUBLIC_DATA_TIMEOUT_S,
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
    )
    try:
        geo_url = geocoding_url(city_clean, cc_clean)
        geo_json, geo_err = _get_json(c, geo_url)
        if geo_err is not None:
            return {"status": "unavailable", "source": WEATHER_SOURCE, "source_url": geo_url, "error": geo_err}

        results = geo_json.get("results") if isinstance(geo_json, dict) else None
        if not results or not isinstance(results, list):
            return {"status": "not_found", "source": WEATHER_SOURCE, "source_url": geo_url, "city": city_clean}

        first_res = results[0] if isinstance(results[0], dict) else {}
        lat = first_res.get("latitude")
        lon = first_res.get("longitude")
        if (
            lat is None
            or lon is None
            or isinstance(lat, bool)
            or isinstance(lon, bool)
            or not isinstance(lat, (int, float))
            or not isinstance(lon, (int, float))
        ):
            return {
                "status": "unavailable",
                "source": WEATHER_SOURCE,
                "source_url": geo_url,
                "error": "invalid_payload",
            }

        fc_url = forecast_request_url(lat, lon, forecast_days)
        fc_json, fc_err = _get_json(c, fc_url)
        if fc_err is not None:
            return {"status": "unavailable", "source": WEATHER_SOURCE, "source_url": fc_url, "error": fc_err}

        if not isinstance(fc_json, dict):
            return {"status": "unavailable", "source": WEATHER_SOURCE, "source_url": fc_url, "error": "invalid_payload"}

        daily = fc_json.get("daily")
        daily_units = fc_json.get("daily_units")
        if not isinstance(daily, dict) or not isinstance(daily_units, dict):
            return {"status": "unavailable", "source": WEATHER_SOURCE, "source_url": fc_url, "error": "invalid_payload"}

        times = daily.get("time")
        if not isinstance(times, list):
            return {"status": "unavailable", "source": WEATHER_SOURCE, "source_url": fc_url, "error": "invalid_payload"}

        n_times = len(times)
        for var_name in DAILY_VARS:
            var_list = daily.get(var_name)
            if not isinstance(var_list, list) or len(var_list) != n_times:
                return {
                    "status": "unavailable",
                    "source": WEATHER_SOURCE,
                    "source_url": fc_url,
                    "error": "invalid_payload",
                }

        location = {
            k: first_res.get(k)
            for k in ("name", "admin1", "country", "country_code", "latitude", "longitude", "timezone")
        }

        current_raw = fc_json.get("current")
        current_units_raw = fc_json.get("current_units")
        if isinstance(current_raw, dict):
            c_code = current_raw.get("weather_code")
            cu_temp = current_units_raw.get("temperature_2m") if isinstance(current_units_raw, dict) else None
            current = {
                "time": current_raw.get("time"),
                "temperature": {"value": current_raw.get("temperature_2m"), "unit": cu_temp},
                "weather_code": c_code,
                "weather_description": WMO_CODES.get(c_code) if c_code is not None else None,
            }
        else:
            current = None

        days: list[dict[str, Any]] = []
        for i, t in enumerate(times):
            wc = daily["weather_code"][i]
            days.append(
                {
                    "date": t,
                    "weather_code": wc,
                    "weather_description": WMO_CODES.get(wc) if wc is not None else None,
                    "temperature_max": {
                        "value": daily["temperature_2m_max"][i],
                        "unit": daily_units.get("temperature_2m_max"),
                    },
                    "temperature_min": {
                        "value": daily["temperature_2m_min"][i],
                        "unit": daily_units.get("temperature_2m_min"),
                    },
                    "precipitation_probability_max": {
                        "value": daily["precipitation_probability_max"][i],
                        "unit": daily_units.get("precipitation_probability_max"),
                    },
                    "precipitation_sum": {
                        "value": daily["precipitation_sum"][i],
                        "unit": daily_units.get("precipitation_sum"),
                    },
                }
            )

        return {
            "status": "success",
            "source": WEATHER_SOURCE,
            "source_url": fc_url,
            "geocoding_url": geo_url,
            "attribution": WEATHER_ATTRIBUTION,
            "retrieved_at": datetime.now(UTC).isoformat(),
            "location": location,
            "timezone": fc_json.get("timezone"),
            "current": current,
            "days": days,
        }
    finally:
        if manage_client:
            c.close()


def fetch_exchange_rate(
    currency: str,
    date: dt.date | None = None,
    *,
    client: httpx.Client | None = None,
    today: dt.date | None = None,
) -> dict[str, Any]:
    """Fetch official PTAX exchange rate for a currency against BRL via Banco Central."""
    today_val = today if today is not None else datetime.now(BRT).date()

    if not isinstance(currency, str):
        return {"status": "invalid_request", "source": FX_SOURCE, "source_url": None, "error": "invalid_currency"}
    cur_clean = currency.strip().upper()
    if len(cur_clean) != 3 or not cur_clean.isascii() or not cur_clean.isalpha() or cur_clean == "BRL":
        return {"status": "invalid_request", "source": FX_SOURCE, "source_url": None, "error": "invalid_currency"}

    if date is not None:
        if not isinstance(date, dt.date):
            return {"status": "invalid_request", "source": FX_SOURCE, "source_url": None, "error": "invalid_date"}
        if date > today_val:
            return {"status": "invalid_request", "source": FX_SOURCE, "source_url": None, "error": "future_date"}

    manage_client = client is None
    c = client or httpx.Client(
        timeout=settings.PUBLIC_DATA_TIMEOUT_S,
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
    )
    try:
        m_url = moedas_url()
        m_json, m_err = _get_json(c, m_url)
        if m_err is not None:
            return {"status": "unavailable", "source": FX_SOURCE, "source_url": m_url, "error": m_err}

        m_val = m_json.get("value") if isinstance(m_json, dict) else None
        if not isinstance(m_val, list):
            return {"status": "unavailable", "source": FX_SOURCE, "source_url": m_url, "error": "invalid_payload"}

        currency_entry = next((item for item in m_val if isinstance(item, dict) and item.get("simbolo") == cur_clean), None)
        if currency_entry is None:
            return {"status": "not_found", "source": FX_SOURCE, "source_url": m_url, "currency": cur_clean}
        currency_name = currency_entry.get("nomeFormatado")

        if date is not None:
            start_d, end_d = date, date
        else:
            start_d = today_val - timedelta(days=LATEST_LOOKBACK_DAYS)
            end_d = today_val

        p_url = ptax_period_url(cur_clean, start_d, end_d)
        p_json, p_err = _get_json(c, p_url)
        if p_err is not None:
            return {"status": "unavailable", "source": FX_SOURCE, "source_url": p_url, "error": p_err}

        p_val = p_json.get("value") if isinstance(p_json, dict) else None
        if not isinstance(p_val, list):
            return {"status": "unavailable", "source": FX_SOURCE, "source_url": p_url, "error": "invalid_payload"}

        matching: list[dict[str, Any]] = []
        for row in p_val:
            if not isinstance(row, dict) or row.get("tipoBoletim") != CLOSING_BULLETIN:
                continue
            quoted_str = str(row.get("dataHoraCotacao", ""))
            if date is not None and not quoted_str.startswith(date.isoformat()):
                continue
            matching.append(row)

        if not matching:
            return {
                "status": "no_data",
                "source": FX_SOURCE,
                "source_url": p_url,
                "currency": cur_clean,
                "requested_date": date.isoformat() if date is not None else None,
                "period_start": start_d.isoformat(),
                "period_end": end_d.isoformat(),
            }

        best = max(matching, key=lambda x: str(x.get("dataHoraCotacao", "")))
        buy_val = best.get("cotacaoCompra")
        sell_val = best.get("cotacaoVenda")
        if (
            buy_val is None
            or sell_val is None
            or isinstance(buy_val, bool)
            or isinstance(sell_val, bool)
            or not isinstance(buy_val, (int, float))
            or not isinstance(sell_val, (int, float))
        ):
            return {
                "status": "unavailable",
                "source": FX_SOURCE,
                "source_url": p_url,
                "error": "invalid_payload",
            }

        quoted_at = str(best.get("dataHoraCotacao"))
        ref_date = quoted_at[:10]
        unit_str = f"BRL per 1 {cur_clean}"

        return {
            "status": "success",
            "source": FX_SOURCE,
            "source_url": p_url,
            "currency": cur_clean,
            "currency_name": currency_name,
            "rate_note": FX_RATE_NOTE,
            "bulletin": CLOSING_BULLETIN,
            "quoted_at": quoted_at,
            "reference_date": ref_date,
            "requested_date": date.isoformat() if date is not None else None,
            "buy": {"value": buy_val, "unit": unit_str},
            "sell": {"value": sell_val, "unit": unit_str},
            "retrieved_at": datetime.now(UTC).isoformat(),
        }
    finally:
        if manage_client:
            c.close()
