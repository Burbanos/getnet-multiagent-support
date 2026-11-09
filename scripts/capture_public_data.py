"""Capture real public API responses from Open-Meteo and Banco Central PTAX as test fixtures."""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

USER_AGENT = "getnet-multiagent-support/1.0 (+https://github.com/Burbanos/getnet-multiagent-support)"
OUT_DIR = Path("tests/fixtures/public_data")
OLINDA = "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"


def ptax_period_url(currency: str, start: str, end: str) -> str:
    """Construct Banco Central Olinda PTAX CotacaoMoedaPeriodo URL."""
    return (
        OLINDA
        + "CotacaoMoedaPeriodo(moeda=@moeda,dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)?@moeda='"
        + currency
        + "'&@dataInicial='"
        + start
        + "'&@dataFinalCotacao='"
        + end
        + "'&$format=json"
    )


def forecast_url(latitude: float, longitude: float) -> str:
    """Construct Open-Meteo 3-day forecast URL for given coordinates."""
    return (
        f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}"
        "&current=temperature_2m,weather_code"
        "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum"
        "&timezone=auto&forecast_days=3"
    )


def capture(client: httpx.Client, out_dir: Path) -> dict[str, Any]:
    """Execute GET requests sequentially, save raw responses and manifest."""
    files_meta: dict[str, dict[str, Any]] = {}

    # 1. geocoding_porto_alegre
    url_geo_poa = (
        "https://geocoding-api.open-meteo.com/v1/search?name=Porto%20Alegre&count=1&language=pt&format=json&countryCode=BR"
    )
    resp_geo_poa = client.get(url_geo_poa)
    content_geo_poa = resp_geo_poa.content
    (out_dir / "geocoding_porto_alegre.json").write_bytes(content_geo_poa)
    files_meta["geocoding_porto_alegre"] = {
        "url": url_geo_poa,
        "status_code": resp_geo_poa.status_code,
        "content_type": resp_geo_poa.headers.get("content-type"),
        "bytes": len(content_geo_poa),
        "sha256": hashlib.sha256(content_geo_poa.replace(b"\r\n", b"\n")).hexdigest(),
    }

    # Parse coordinates for Porto Alegre forecast
    poa_data = resp_geo_poa.json()
    poa_results = poa_data.get("results") if isinstance(poa_data, dict) else None
    if not poa_results:
        raise RuntimeError("geocoding returned no result for Porto Alegre")
    lat_poa = poa_results[0]["latitude"]
    lon_poa = poa_results[0]["longitude"]

    # 2. geocoding_sao_paulo
    url_geo_sp = (
        "https://geocoding-api.open-meteo.com/v1/search?name=S%C3%A3o%20Paulo&count=1&language=pt&format=json&countryCode=BR"
    )
    resp_geo_sp = client.get(url_geo_sp)
    content_geo_sp = resp_geo_sp.content
    (out_dir / "geocoding_sao_paulo.json").write_bytes(content_geo_sp)
    files_meta["geocoding_sao_paulo"] = {
        "url": url_geo_sp,
        "status_code": resp_geo_sp.status_code,
        "content_type": resp_geo_sp.headers.get("content-type"),
        "bytes": len(content_geo_sp),
        "sha256": hashlib.sha256(content_geo_sp.replace(b"\r\n", b"\n")).hexdigest(),
    }

    # 3. geocoding_unknown
    url_geo_unk = (
        "https://geocoding-api.open-meteo.com/v1/search?name=Xqzvbnm%20Nowhereville&count=1&language=pt&format=json"
    )
    resp_geo_unk = client.get(url_geo_unk)
    content_geo_unk = resp_geo_unk.content
    (out_dir / "geocoding_unknown.json").write_bytes(content_geo_unk)
    files_meta["geocoding_unknown"] = {
        "url": url_geo_unk,
        "status_code": resp_geo_unk.status_code,
        "content_type": resp_geo_unk.headers.get("content-type"),
        "bytes": len(content_geo_unk),
        "sha256": hashlib.sha256(content_geo_unk.replace(b"\r\n", b"\n")).hexdigest(),
    }

    # 4. forecast_porto_alegre
    url_fc_poa = forecast_url(lat_poa, lon_poa)
    resp_fc_poa = client.get(url_fc_poa)
    content_fc_poa = resp_fc_poa.content
    (out_dir / "forecast_porto_alegre.json").write_bytes(content_fc_poa)
    files_meta["forecast_porto_alegre"] = {
        "url": url_fc_poa,
        "status_code": resp_fc_poa.status_code,
        "content_type": resp_fc_poa.headers.get("content-type"),
        "bytes": len(content_fc_poa),
        "sha256": hashlib.sha256(content_fc_poa.replace(b"\r\n", b"\n")).hexdigest(),
    }

    # 5. forecast_invalid
    url_fc_inv = (
        "https://api.open-meteo.com/v1/forecast?latitude=999&longitude=0"
        "&daily=temperature_2m_max&timezone=auto&forecast_days=3"
    )
    resp_fc_inv = client.get(url_fc_inv)
    content_fc_inv = resp_fc_inv.content
    (out_dir / "forecast_invalid.json").write_bytes(content_fc_inv)
    files_meta["forecast_invalid"] = {
        "url": url_fc_inv,
        "status_code": resp_fc_inv.status_code,
        "content_type": resp_fc_inv.headers.get("content-type"),
        "bytes": len(content_fc_inv),
        "sha256": hashlib.sha256(content_fc_inv.replace(b"\r\n", b"\n")).hexdigest(),
    }

    # 6. ptax_moedas
    url_ptax_moedas = OLINDA + "Moedas?$format=json"
    resp_ptax_moedas = client.get(url_ptax_moedas)
    content_ptax_moedas = resp_ptax_moedas.content
    (out_dir / "ptax_moedas.json").write_bytes(content_ptax_moedas)
    files_meta["ptax_moedas"] = {
        "url": url_ptax_moedas,
        "status_code": resp_ptax_moedas.status_code,
        "content_type": resp_ptax_moedas.headers.get("content-type"),
        "bytes": len(content_ptax_moedas),
        "sha256": hashlib.sha256(content_ptax_moedas.replace(b"\r\n", b"\n")).hexdigest(),
    }

    # 7. ptax_eur_20261106
    url_ptax_eur = ptax_period_url("EUR", "11-06-2026", "11-06-2026")
    resp_ptax_eur = client.get(url_ptax_eur)
    content_ptax_eur = resp_ptax_eur.content
    (out_dir / "ptax_eur_20261106.json").write_bytes(content_ptax_eur)
    files_meta["ptax_eur_20261106"] = {
        "url": url_ptax_eur,
        "status_code": resp_ptax_eur.status_code,
        "content_type": resp_ptax_eur.headers.get("content-type"),
        "bytes": len(content_ptax_eur),
        "sha256": hashlib.sha256(content_ptax_eur.replace(b"\r\n", b"\n")).hexdigest(),
    }

    # 8. ptax_usd_20261106
    url_ptax_usd = ptax_period_url("USD", "11-06-2026", "11-06-2026")
    resp_ptax_usd = client.get(url_ptax_usd)
    content_ptax_usd = resp_ptax_usd.content
    (out_dir / "ptax_usd_20261106.json").write_bytes(content_ptax_usd)
    files_meta["ptax_usd_20261106"] = {
        "url": url_ptax_usd,
        "status_code": resp_ptax_usd.status_code,
        "content_type": resp_ptax_usd.headers.get("content-type"),
        "bytes": len(content_ptax_usd),
        "sha256": hashlib.sha256(content_ptax_usd.replace(b"\r\n", b"\n")).hexdigest(),
    }

    # 9. ptax_jpy_20261106
    url_ptax_jpy = ptax_period_url("JPY", "11-06-2026", "11-06-2026")
    resp_ptax_jpy = client.get(url_ptax_jpy)
    content_ptax_jpy = resp_ptax_jpy.content
    (out_dir / "ptax_jpy_20261106.json").write_bytes(content_ptax_jpy)
    files_meta["ptax_jpy_20261106"] = {
        "url": url_ptax_jpy,
        "status_code": resp_ptax_jpy.status_code,
        "content_type": resp_ptax_jpy.headers.get("content-type"),
        "bytes": len(content_ptax_jpy),
        "sha256": hashlib.sha256(content_ptax_jpy.replace(b"\r\n", b"\n")).hexdigest(),
    }

    # 10. ptax_eur_20261107
    url_ptax_sat = ptax_period_url("EUR", "11-07-2026", "11-07-2026")
    resp_ptax_sat = client.get(url_ptax_sat)
    content_ptax_sat = resp_ptax_sat.content
    (out_dir / "ptax_eur_20261107.json").write_bytes(content_ptax_sat)
    files_meta["ptax_eur_20261107"] = {
        "url": url_ptax_sat,
        "status_code": resp_ptax_sat.status_code,
        "content_type": resp_ptax_sat.headers.get("content-type"),
        "bytes": len(content_ptax_sat),
        "sha256": hashlib.sha256(content_ptax_sat.replace(b"\r\n", b"\n")).hexdigest(),
    }

    # 11. ptax_eur_20261030_20261109
    url_ptax_per = ptax_period_url("EUR", "10-30-2026", "11-09-2026")
    resp_ptax_per = client.get(url_ptax_per)
    content_ptax_per = resp_ptax_per.content
    (out_dir / "ptax_eur_20261030_20261109.json").write_bytes(content_ptax_per)
    files_meta["ptax_eur_20261030_20261109"] = {
        "url": url_ptax_per,
        "status_code": resp_ptax_per.status_code,
        "content_type": resp_ptax_per.headers.get("content-type"),
        "bytes": len(content_ptax_per),
        "sha256": hashlib.sha256(content_ptax_per.replace(b"\r\n", b"\n")).hexdigest(),
    }

    # 12. ptax_xyz_20261106
    url_ptax_xyz = ptax_period_url("XYZ", "11-06-2026", "11-06-2026")
    resp_ptax_xyz = client.get(url_ptax_xyz)
    content_ptax_xyz = resp_ptax_xyz.content
    (out_dir / "ptax_xyz_20261106.json").write_bytes(content_ptax_xyz)
    files_meta["ptax_xyz_20261106"] = {
        "url": url_ptax_xyz,
        "status_code": resp_ptax_xyz.status_code,
        "content_type": resp_ptax_xyz.headers.get("content-type"),
        "bytes": len(content_ptax_xyz),
        "sha256": hashlib.sha256(content_ptax_xyz.replace(b"\r\n", b"\n")).hexdigest(),
    }

    manifest = {
        "captured_at": datetime.now(UTC).isoformat(),
        "user_agent": USER_AGENT,
        "files": files_meta,
    }

    manifest_json = json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True)
    (out_dir / "manifest.json").write_text(manifest_json, encoding="utf-8")
    return manifest


def main() -> int:
    """CLI entry point for capturing public API data."""
    try:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        with httpx.Client(
            timeout=30.0,
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
        ) as client:
            manifest = capture(client, OUT_DIR)

        for name, meta in manifest["files"].items():
            print(f"{name} {meta['status_code']} {meta['bytes']}")
        return 0
    except httpx.HTTPError as exc:
        print(type(exc).__name__, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
