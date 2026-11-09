"""Account tier and date of each real-model run, as declared by the author in reports/run_context.json."""
from __future__ import annotations

import json
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
