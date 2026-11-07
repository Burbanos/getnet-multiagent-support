"""Aggregate metric calculation over evaluated cases."""
import math
from typing import Any

from src.eval.checks import CHECKS, evaluate_case


def rate(vals: list[Any]) -> float | None:
    """Calculate true-rate among non-None values, returning None if empty."""
    non_null = [v for v in vals if v is not None]
    if not non_null:
        return None
    return sum(1 for v in non_null if v) / len(non_null)


def pct(xs: list[float | int], p: float) -> float | int | None:
    """Nearest-rank percentile: sort and select index ceil(p * n) - 1."""
    if not xs:
        return None
    s = sorted(xs)
    return s[max(0, math.ceil(p * len(s)) - 1)]


def aggregate(
    cases: list[dict[str, Any]], results: list[dict[str, Any]]
) -> dict[str, Any]:
    """
    Aggregate evaluation results into summary metrics, per-slice metrics, and per-case records.
    Cases without a corresponding result are ignored.
    """
    by_id = {r["id"]: r for r in results}
    rows = []
    for c in cases:
        r = by_id.get(c["id"])
        if r is None:
            continue
        ev = evaluate_case(c, r)
        rows.append((c, r, ev))

    ok = [(c, r, ev) for c, r, ev in rows if r.get("status") == "ok"]

    m: dict[str, Any] = {
        name.replace("_ok", "") + "_rate": rate([ev["checks"][name] for _, _, ev in ok])
        for name in CHECKS
    }
    m["pass_rate"] = rate([ev["passed"] for _, _, ev in ok])

    exp = [
        (c["expect"]["escalate"], r["turns"][-1].get("ticket_id") is not None)
        for c, r, _ in ok
        if c["expect"]["escalate"] is not None
    ]
    tp = sum(1 for a, b in exp if a and b)
    pred = sum(1 for _, b in exp if b)
    pos = sum(1 for a, _ in exp if a)
    m["escalation_precision"] = tp / pred if pred else None
    m["escalation_recall"] = tp / pos if pos else None

    lat = [sum(t.get("latency_ms", 0.0) for t in r.get("turns", [])) for _, r, _ in ok]
    m["latency_ms_p50"] = pct(lat, 0.5)
    m["latency_ms_p95"] = pct(lat, 0.95)

    tok = [
        sum((t.get("tokens") or {}).get("total_tokens", 0) for t in r.get("turns", []))
        for _, r, _ in ok
        if any(t.get("tokens") for t in r.get("turns", []))
    ]
    m["tokens_total"] = sum(tok) if tok else None
    m["tokens_mean_per_case"] = (sum(tok) / len(tok)) if tok else None
    m["estimated_cost_usd"] = None

    groups: dict[str, dict[str, Any]] = {}
    for key in ("category", "lang"):
        g: dict[str, list[bool]] = {}
        for c, _, ev in ok:
            g.setdefault(c[key], []).append(ev["passed"])
        groups[key] = {k: {"n": len(v), "pass_rate": rate(v)} for k, v in sorted(g.items())}

    off = [ev["passed"] for c, _, ev in ok if c.get("official")]

    per_case = [
        {
            "id": c["id"],
            "category": c["category"],
            "lang": c["lang"],
            "official": c["official"],
            "status": r.get("status"),
            "checks": ev["checks"],
            "passed": ev["passed"],
        }
        for c, r, ev in rows
    ]

    return {
        "n_cases": len(cases),
        "n_evaluated": len(ok),
        "n_errors": sum(1 for _, r, _ in rows if r.get("status") != "ok"),
        "error_ids": sorted(r["id"] for _, r, _ in rows if r.get("status") != "ok"),
        "metrics": m,
        "by_category": groups["category"],
        "by_lang": groups["lang"],
        "official": {"n": len(off), "pass_rate": rate(off)},
        "per_case": per_case,
        "cost_note": "Token pricing arrives in Phase 7; cost calculation is not active yet.",
    }
