"""Aggregate metric calculation over evaluated cases and judge assessments."""
import math
from typing import Any

from src.core.pricing import cost_usd
from src.eval.checks import CHECKS, evaluate_case

COST_NOTE = (
    "Estimated answer cost from src/core/pricing.py (paid tier, Standard); null when no turn has tokens or any "
    "turn with tokens has no price. Excludes judge calls and query embeddings."
)


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


def _mean(xs: list[int | float]) -> float | None:
    """Calculate arithmetic mean, returning None if empty."""
    return (sum(xs) / len(xs)) if xs else None


def aggregate(
    cases: list[dict[str, Any]],
    results: list[dict[str, Any]],
    judgments: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Aggregate evaluation results and optional judge assessments into summary metrics.
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
    priced: list[float | None] = []
    for _, r, _ in ok:
        for t in r.get("turns", []):
            tk = t.get("tokens")
            if not tk:
                continue
            priced.append(
                cost_usd(t.get("llm_model"), tk.get("input_tokens"), tk.get("output_tokens"))
            )

    m["estimated_cost_usd"] = (
        round(math.fsum(c for c in priced if c is not None), 6)
        if priced and all(c is not None for c in priced)
        else None
    )

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

    answer_models = sorted(
        {t["llm_model"] for _, r, _ in ok for t in r.get("turns", []) if t.get("llm_model")}
    )

    judge_section: dict[str, Any] | None = None
    if judgments is not None:
        by_r = {r["id"]: r for r in results}
        by_j = {j["id"]: j for j in judgments}
        j_rows = [
            (c, by_r[c["id"]], by_j.get(c["id"]))
            for c in cases
            if c["id"] in by_r and by_r[c["id"]].get("status") == "ok"
        ]
        judged = [(c, r, j) for c, r, j in j_rows if j and j.get("status") == "ok"]
        n_err = sum(1 for _, _, j in j_rows if j and j.get("status") != "ok")

        ab = [
            (c["expect"]["abstain"], j["abstained"])
            for c, _, j in judged
            if c["expect"]["abstain"] is not None
        ]
        tp_ab = sum(1 for e, p in ab if e and p)
        pred_ab = sum(1 for _, p in ab if p)
        pos_ab = sum(1 for e, _ in ab if e)

        dis: list[str] = []
        for c, r, j in judged:
            ev = evaluate_case(c, r)
            f = ev["checks"]["facts_ok"]
            if (f is True and j["grounded"] <= 2) or (
                f is False and j["grounded"] >= 4 and j["answers_question"] >= 4
            ):
                dis.append(c["id"])

        judge_section = {
            "n_judged": len(judged),
            "n_judge_errors": n_err,
            "grounded_mean": _mean([j["grounded"] for _, _, j in judged]),
            "answers_mean": _mean([j["answers_question"] for _, _, j in judged]),
            "abstention_precision": tp_ab / pred_ab if pred_ab else None,
            "abstention_recall": tp_ab / pos_ab if pos_ab else None,
            "abstention_errors": sorted(
                c["id"]
                for c, _, j in judged
                if c["expect"]["abstain"] is not None and j["abstained"] != c["expect"]["abstain"]
            ),
            "disagreements": sorted(dis),
            "judge_models": sorted(
                {j.get("judge_model") for _, _, j in judged if j.get("judge_model")}
            ),
        }

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
        "answer_models": answer_models,
        "judge": judge_section,
        "cost_note": COST_NOTE,
    }
