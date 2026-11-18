"""Account tier and date of each real-model run, as declared by the author in reports/run_context.json."""
from __future__ import annotations

import datetime as dt
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_RUN_CONTEXT_PATH = Path("reports/run_context.json")
TIER_LABELS = {"free": "nível gratuito", "paid_tier_1": "Tier 1 (pago)"}
CONTEXT_NOTE = "Tier da conta declarado pelo autor em `reports/run_context.json`; modelos lidos dos registros das execuções."


def load_run_context(path: Path | str = DEFAULT_RUN_CONTEXT_PATH) -> dict[str, dict[str, Any]]:
    """Return {run_id: {"date", "tier"}} from the declaration file ({} if it does not exist)."""
    p = Path(path)
    if not p.exists():
        return {}
    doc = json.loads(p.read_text(encoding="utf-8"))
    runs = doc.get("runs")
    if not isinstance(runs, dict):
        raise TypeError("run context: 'runs' must be an object")
    for rid, ctx in runs.items():
        if not isinstance(ctx, dict) or set(ctx) != {"date", "tier"} or ctx["tier"] not in TIER_LABELS:
            raise ValueError(f"run context: invalid entry for {rid!r}")
    return runs


def tier_label(ctx: dict[str, Any] | None) -> str:
    """Portuguese label of the declared tier, or "não informado"."""
    return TIER_LABELS.get((ctx or {}).get("tier"), "não informado")


def update_run_context(
    run_ids: list[str],
    tier: str,
    date_str: str | None = None,
    path: Path | str = DEFAULT_RUN_CONTEXT_PATH,
) -> dict[str, dict[str, Any]]:
    """Append {date, tier} for new run IDs without altering existing entries or metadata keys."""
    if tier not in TIER_LABELS:
        raise ValueError(f"Invalid tier {tier!r}; expected one of {list(TIER_LABELS)}")

    cleaned_ids: list[str] = []
    seen_new: set[str] = set()
    for raw in run_ids:
        rid = raw.strip()
        if not rid:
            continue
        if rid in seen_new:
            raise ValueError(f"Duplicate run id in argument: {rid!r}")
        seen_new.add(rid)
        cleaned_ids.append(rid)
    if not cleaned_ids:
        raise ValueError("At least one run id must be provided.")

    if date_str is None:
        resolved_date = datetime.now(UTC).strftime("%Y-%m-%d")
    else:
        resolved_date = date_str.strip()
        if len(resolved_date) != 10:
            raise ValueError(f"Invalid date {date_str!r}; expected YYYY-MM-DD.")
        dt.date.fromisoformat(resolved_date)

    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Run context file not found: {p}")

    doc = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(doc, dict) or not isinstance(doc.get("runs"), dict):
        raise TypeError("run context: 'runs' must be an object")

    runs: dict[str, dict[str, Any]] = doc["runs"]
    existing_dups = [rid for rid in cleaned_ids if rid in runs]
    if existing_dups:
        raise ValueError(f"Run id(s) already declared: {', '.join(existing_dups)}")

    for rid in cleaned_ids:
        runs[rid] = {"date": resolved_date, "tier": tier}

    for rid, ctx in runs.items():
        if not isinstance(ctx, dict) or set(ctx) != {"date", "tier"} or ctx["tier"] not in TIER_LABELS:
            raise ValueError(f"run context: invalid entry for {rid!r}")

    p.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return load_run_context(p)
