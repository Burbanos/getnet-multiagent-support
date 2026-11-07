"""Evaluation report generator producing JSON and Markdown summaries."""
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.eval.cases import cases_sha256
from src.eval.metrics import aggregate


def _fmt_pct(val: float | None) -> str:
    return f"{val * 100:.2f}%" if val is not None else "-"


def _fmt_ms(val: float | None) -> str:
    return f"{val:.1f} ms" if val is not None else "-"


def _fmt_val(val: Any) -> str:
    return str(val) if val is not None else "-"


def write_report(
    cases: list[dict[str, Any]],
    results: list[dict[str, Any]],
    out_json: str | Path,
    out_md: str | Path,
    run_id: str = "eval",
) -> dict[str, Any]:
    """
    Compute aggregate metrics and write out evaluation report in both JSON and Markdown formats.
    Returns the report data dictionary.
    """
    agg = aggregate(cases, results)
    sha = cases_sha256(cases)
    generated_at = datetime.now(UTC).isoformat()

    report_data: dict[str, Any] = {
        "run_id": run_id,
        "generated_at": generated_at,
        "cases_sha256": sha,
        **agg,
    }

    # 1. Write JSON report
    json_path = Path(out_json)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(report_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 2. Build Markdown report
    m = agg["metrics"]
    cost_note = agg.get("cost_note", "")
    lines: list[str] = [
        f"# Relatório de Avaliação: {run_id}",
        "",
        f"- **Gerado em**: `{generated_at}`",
        f"- **Cases SHA256**: `{sha}`",
        f"- **Total de Casos**: {agg['n_cases']}",
        f"- **Avaliados com Sucesso**: {agg['n_evaluated']}",
        f"- **Erros de Execução**: {agg['n_errors']}",
        "",
        "## Métricas Determinísticas Principais",
        "",
        "| Métrica | Valor |",
        "| :--- | :--- |",
        f"| `pass_rate` | {_fmt_pct(m.get('pass_rate'))} |",
        f"| `routing_rate` | {_fmt_pct(m.get('routing_rate'))} |",
        f"| `tools_rate` | {_fmt_pct(m.get('tools_rate'))} |",
        f"| `escalation_rate` | {_fmt_pct(m.get('escalation_rate'))} |",
        f"| `priority_rate` | {_fmt_pct(m.get('priority_rate'))} |",
        f"| `blocked_rate` | {_fmt_pct(m.get('blocked_rate'))} |",
        f"| `sources_rate` | {_fmt_pct(m.get('sources_rate'))} |",
        f"| `facts_rate` | {_fmt_pct(m.get('facts_rate'))} |",
        f"| `facts_none_rate` | {_fmt_pct(m.get('facts_none_rate'))} |",
        f"| `language_rate` | {_fmt_pct(m.get('language_rate'))} |",
        f"| `escalation_precision` | {_fmt_pct(m.get('escalation_precision'))} |",
        f"| `escalation_recall` | {_fmt_pct(m.get('escalation_recall'))} |",
        f"| `latency_ms_p50` | {_fmt_ms(m.get('latency_ms_p50'))} |",
        f"| `latency_ms_p95` | {_fmt_ms(m.get('latency_ms_p95'))} |",
        f"| `tokens_total` | {_fmt_val(m.get('tokens_total'))} |",
        f"| `tokens_mean_per_case` | {_fmt_val(m.get('tokens_mean_per_case'))} |",
        f"| `estimated_cost_usd` | {_fmt_val(m.get('estimated_cost_usd'))} |",
        "",
        f"> *Nota de Custo*: {cost_note}",
        "",
        "## Performance por Categoria",
        "",
        "| Categoria | Casos (n) | Pass Rate |",
        "| :--- | :--- | :--- |",
    ]

    for cat, data in agg.get("by_category", {}).items():
        lines.append(f"| `{cat}` | {data['n']} | {_fmt_pct(data['pass_rate'])} |")

    lines.extend([
        "",
        "## Performance por Idioma",
        "",
        "| Idioma | Casos (n) | Pass Rate |",
        "| :--- | :--- | :--- |",
    ])
    for lang, data in agg.get("by_lang", {}).items():
        lines.append(f"| `{lang}` | {data['n']} | {_fmt_pct(data['pass_rate'])} |")

    lines.extend([
        "",
        "## Cenários Oficiais (10 Casos de Referência)",
        "",
        f"- **Casos Avaliados**: {agg['official']['n']}",
        f"- **Pass Rate**: {_fmt_pct(agg['official']['pass_rate'])}",
        "",
        "## Casos Reprovados",
        "",
    ])

    failed_cases = [c for c in agg.get("per_case", []) if not c.get("passed")]
    if not failed_cases:
        lines.append("Nenhum caso reprovado nesta execução.")
    else:
        lines.append("| ID | Categoria | Idioma | Status | Checagens Reprovadas |")
        lines.append("| :--- | :--- | :--- | :--- | :--- |")
        for fc in failed_cases:
            checks = fc.get("checks") or {}
            failing_checks = [k for k, v in checks.items() if v is False]
            chk_str = ", ".join(failing_checks) if failing_checks else (
                f"status={fc.get('status')}" if fc.get("status") != "ok" else "none"
            )
            lines.append(
                f"| `{fc['id']}` | `{fc['category']}` | `{fc['lang']}` | `{fc['status']}` | `{chk_str}` |"
            )

    lines.append("")
    md_content = "\n".join(lines)
    md_path = Path(out_md)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(md_content, encoding="utf-8")

    return report_data
