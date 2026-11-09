"""Evaluation run comparison for multi-run benchmarks and model comparison."""
from __future__ import annotations

import json
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.eval.cases import cases_sha256
from src.eval.metrics import aggregate
from src.eval.run_context import CONTEXT_NOTE, load_run_context, tier_label

COMPARE_METRICS = [
    ("pass_rate", "metrics", "pass_rate", "Casos aprovados (checagens determinísticas)", "pct"),
    ("official_pass_rate", "official", "pass_rate", "Cenários oficiais aprovados", "pct"),
    ("routing_rate", "metrics", "routing_rate", "Roteamento correto", "pct"),
    ("tools_rate", "metrics", "tools_rate", "Ferramentas corretas", "pct"),
    ("escalation_rate", "metrics", "escalation_rate", "Escalonamento correto", "pct"),
    ("facts_rate", "metrics", "facts_rate", "Fatos esperados presentes", "pct"),
    ("sources_rate", "metrics", "sources_rate", "Fonte oficial recuperada", "pct"),
    ("language_rate", "metrics", "language_rate", "Idioma da resposta", "pct"),
    ("judge_grounded_mean", "judge", "grounded_mean", "Juiz: fundamentação (1 a 5)", "dec2"),
    ("judge_answers_mean", "judge", "answers_mean", "Juiz: responde à pergunta (1 a 5)", "dec2"),
    ("judge_abstention_precision", "judge", "abstention_precision", "Juiz: precisão da abstenção", "pct"),
    ("judge_abstention_recall", "judge", "abstention_recall", "Juiz: cobertura da abstenção", "pct"),
    ("latency_ms_p50", "metrics", "latency_ms_p50", "Latência por caso, mediana", "sec"),
    ("latency_ms_p95", "metrics", "latency_ms_p95", "Latência por caso, p95", "sec"),
    ("tokens_total", "metrics", "tokens_total", "Tokens por execução", "int"),
    ("estimated_cost_usd", "metrics", "estimated_cost_usd", "Custo estimado por execução (USD, plano pago)", "usd"),
]


def compare_runs(
    cases: list[dict],
    groups: list[tuple[str, list[tuple[str, list, list | None]]]],
) -> dict[str, Any]:
    """Aggregate metrics across multiple runs and group them for comparison."""
    out_groups = []
    for label, runs in groups:
        aggs = [aggregate(cases, res, jud) for _, res, jud in runs]
        mets = {}
        for name, sec, key, _, _ in COMPARE_METRICS:
            vals = [(a.get(sec) or {}).get(key) for a in aggs]
            if any(v is None for v in vals):
                mets[name] = {"values": vals, "mean": None, "min": None, "max": None}
            else:
                mets[name] = {
                    "values": vals,
                    "mean": math.fsum(vals) / len(vals),
                    "min": min(vals),
                    "max": max(vals),
                }
        failed = None
        for a in aggs:
            ids = {pc["id"] for pc in a["per_case"] if pc["status"] == "ok" and not pc["passed"]}
            failed = ids if failed is None else failed & ids
        if all(a.get("judge") for a in aggs):
            ab = None
            for a in aggs:
                ids = set(a["judge"]["abstention_errors"])
                ab = ids if ab is None else ab & ids
            ab = sorted(ab)
        else:
            ab = []
        out_groups.append({
            "label": label,
            "runs": [rid for rid, _, _ in runs],
            "answer_models": sorted({m for a in aggs for m in a.get("answer_models", [])}),
            "complete": all(a["n_errors"] == 0 and a["n_evaluated"] == len(cases) for a in aggs),
            "metrics": mets,
            "failed_in_all_runs": sorted(failed or set()),
            "judge_abstention_errors_in_all_runs": ab,
        })
    return {
        "cases_sha256": cases_sha256(cases),
        "groups": out_groups,
    }


def format_metric(kind: str, v: float | None) -> str:
    """Format a metric value according to its display category."""
    if v is None:
        return "n/d"
    if kind == "pct":
        s = f"{v * 100:.1f}"
    elif kind == "dec2":
        s = f"{v:.2f}"
    elif kind == "sec":
        s = f"{v / 1000:.1f}"
    elif kind == "int":
        return f"{round(v):,}".replace(",", ".")
    else:  # usd
        s = f"{v:.3f}"
    return s.replace(".", ",")


def format_cell(kind: str, m: dict[str, Any]) -> str:
    """Format a table cell with mean, min, and max."""
    if m["mean"] is None:
        return "n/d"
    rng = f"{format_metric(kind, m['min'])}–{format_metric(kind, m['max'])}"
    if kind == "pct":
        return f"{format_metric(kind, m['mean'])}% ({rng})"
    if kind == "sec":
        return f"{format_metric(kind, m['mean'])} s ({rng})"
    if kind == "usd":
        return f"US$ {format_metric(kind, m['mean'])} ({rng})"
    return f"{format_metric(kind, m['mean'])} ({rng})"


def build_markdown_table(groups: list[dict[str, Any]]) -> list[str]:
    """Generate Markdown comparison table lines."""
    lines = [
        "| Métrica | " + " | ".join(g["label"] for g in groups) + " |",
        "| :--- |" + " :--- |" * len(groups),
        "| Execuções | " + " | ".join(", ".join(g["runs"]) for g in groups) + " |",
        "| Modelo das respostas | " + " | ".join(", ".join(g["answer_models"]) or "n/d" for g in groups) + " |",
    ]
    for name, _, _, title, kind in COMPARE_METRICS:
        lines.append(f"| {title} | " + " | ".join(format_cell(kind, g["metrics"][name]) for g in groups) + " |")
    return lines


def runs_context(
    groups: list[tuple[str, list[tuple[str, list, list | None]]]],
    context: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Date and declared tier of each run, with the answer and judge models read from its records."""
    out = []
    for label, runs in groups:
        for rid, res, jud in runs:
            ctx = context.get(rid) or {}
            out.append({
                "run_id": rid,
                "group": label,
                "date": ctx.get("date"),
                "tier": ctx.get("tier"),
                "answer_models": sorted({t["llm_model"] for r in res if r.get("status") == "ok"
                                         for t in r.get("turns", []) if t.get("llm_model")}),
                "judge_models": sorted({j["judge_model"] for j in (jud or []) if j.get("status") == "ok" and j.get("judge_model")}),
            })
    return out


def runs_context_lines(rows: list[dict[str, Any]]) -> list[str]:
    """Markdown section listing date, tier and models of each run."""
    lines = ["", "## Execuções", ""]
    for r in rows:
        ctx = {"tier": r["tier"]} if r["tier"] else None
        lines.append(
            f"- `{r['run_id']}` ({r['group']}): {r['date'] or 'data não informada'}, conta {tier_label(ctx)}; "
            f"respostas: {', '.join(r['answer_models']) or 'n/d'}; juiz: {', '.join(r['judge_models']) or 'sem juiz'}"
        )
    lines += ["", CONTEXT_NOTE]
    return lines


def write_comparison(
    cases: list[dict],
    groups: list[tuple[str, list[tuple[str, list, list | None]]]],
    out_json: str | Path,
    out_md: str | Path,
    name: str,
    context: dict[str, dict[str, Any]] | None = None,
) -> None:
    """Write comparison artifacts to JSON and Markdown."""
    comparison = compare_runs(cases, groups)
    rows = runs_context(groups, load_run_context() if context is None else context)
    doc = {
        "name": name,
        "generated_at": datetime.now(UTC).isoformat(),
        **comparison,
        "runs_context": rows,
    }
    out_json_path = Path(out_json)
    out_json_path.parent.mkdir(parents=True, exist_ok=True)
    out_json_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [f"# Comparação de execuções: {name}", ""] + build_markdown_table(comparison["groups"]) + runs_context_lines(rows)
    out_md_path = Path(out_md)
    out_md_path.parent.mkdir(parents=True, exist_ok=True)
    out_md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
