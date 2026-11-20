"""Layer ablation analysis and Markdown/JSON report generation for Phase 15."""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from src.config import settings
from src.core.pricing import cost_usd
from src.eval.cases import cases_sha256, load_cases
from src.eval.checks import evaluate_case
from src.eval.compare import COMPARE_METRICS, format_cell
from src.eval.judge import load_judgments
from src.eval.metrics import aggregate
from src.eval.runner import load_results

LAYER_KEYS = ("planner", "verifier", "language", "plan_coverage")
GATE_KEYS = ("unrequested_tickets", "wrong_language", "out_of_scope_tools")

ABLATION_RULE_TEXT = (
    "Regra da seção 3.4 do `docs/SPEC.md` (declarada antes da rodada): "
    "para o verificador, seja ΔQ = média de casos aprovados por execução em `full` menos em `no_verifier` (78 casos), "
    "e G = soma dos contadores dos três portões (`unrequested_tickets` + `wrong_language` + `out_of_scope_tools`) nas três execuções. "
    "O verificador permanece ligado por padrão se e somente se ΔQ ≥ 1,0 ou G(`no_verifier`) > G(`full`); caso contrário, "
    "`VERIFIER_ENABLED` passa a `false` por padrão na 15C (código, testes e flag permanecem no repositório). "
    "A checagem de idioma permanece ligada se e somente se os registros da configuração de referência mostrarem pelo menos 1 turno reescrito "
    "ou se a participação dela no custo total médio for inferior a 1%. "
    "O planner permanece sempre ligado por dependência funcional (portão de escalonamento e confirmação de ação de escrita); "
    "sua execução sem planner é reportada para medição de custo, latência e qualidade."
)


def _normalize_layers(raw: Any, context: str) -> dict[str, bool]:
    if raw is None or not isinstance(raw, dict):
        raise ValueError(f"Missing 'layers' mapping in {context}")
    missing = [k for k in LAYER_KEYS if k not in raw or not isinstance(raw[k], bool)]
    if missing:
        raise ValueError(f"Invalid or missing layer booleans {missing} in {context}")
    return {k: bool(raw[k]) for k in LAYER_KEYS}


def _extract_config_layers(label: str, run_ids: list[str], runs_dir: Path) -> tuple[dict[str, bool], list[tuple[str, list[dict[str, Any]], list[dict[str, Any]] | None]]]:
    loaded_runs: list[tuple[str, list[dict[str, Any]], list[dict[str, Any]] | None]] = []
    common_layers: dict[str, bool] | None = None

    for rid in run_ids:
        res_file = runs_dir / f"{rid}.jsonl"
        if not res_file.exists():
            raise ValueError(f"Results file not found for ablation run '{rid}': {res_file}")
        results = list(load_results(res_file).values())
        judge_file = runs_dir / f"{rid}.judge.jsonl"
        judgments = list(load_judgments(judge_file).values()) if judge_file.exists() else None
        loaded_runs.append((rid, results, judgments))

        for rec in results:
            for t_idx, turn in enumerate(rec.get("turns") or []):
                if not isinstance(turn, dict):
                    continue
                t_layers = _normalize_layers(turn.get("layers"), f"config '{label}' run '{rid}' case '{rec.get('id')}' turn {t_idx}")
                if common_layers is None:
                    common_layers = t_layers
                elif t_layers != common_layers:
                    raise ValueError(
                        f"Mixed layers inside config '{label}': run '{rid}' has {t_layers}, expected {common_layers}"
                    )

    if common_layers is None:
        raise ValueError(f"Config '{label}' has no turn records with layers")
    return common_layers, loaded_runs


def _compute_metrics_summary(
    cases: list[dict[str, Any]],
    runs_data: list[tuple[str, list[dict[str, Any]], list[dict[str, Any]] | None]],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    aggs = [aggregate(cases, res, jud) for _, res, jud in runs_data]
    mets: dict[str, dict[str, Any]] = {}
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
    return mets, aggs


def _compute_run_cost_by_agent(
    cases: list[dict[str, Any]],
    results: list[dict[str, Any]],
) -> dict[str, float]:
    by_id = {r["id"]: r for r in results}
    agent_costs: dict[str, list[float]] = {}
    for c in cases:
        r = by_id.get(c["id"])
        if not r or r.get("status") != "ok":
            continue
        for turn in r.get("turns") or []:
            tba = turn.get("tokens_by_agent")
            if not isinstance(tba, dict):
                continue
            model = turn.get("llm_model") or settings.LLM_MODEL
            for agent_name, tok in tba.items():
                if not isinstance(tok, dict):
                    continue
                usd = cost_usd(model, tok.get("input_tokens"), tok.get("output_tokens"))
                if usd is not None:
                    agent_costs.setdefault(agent_name, []).append(usd)
    return {agent: math.fsum(vals) for agent, vals in agent_costs.items()}


def _compute_run_gates(
    cases: list[dict[str, Any]],
    results: list[dict[str, Any]],
) -> dict[str, int]:
    by_id = {r["id"]: r for r in results}
    counts = {k: 0 for k in GATE_KEYS}
    for c in cases:
        r = by_id.get(c["id"])
        if not r or r.get("status") != "ok":
            continue
        turns = r.get("turns") or []
        if not turns:
            continue
        last_turn = turns[-1]
        if c.get("expect", {}).get("escalate") is False and last_turn.get("ticket_id") is not None:
            counts["unrequested_tickets"] += 1
        ev = evaluate_case(c, r)
        if ev["checks"].get("language_ok") is False:
            counts["wrong_language"] += 1
        if c.get("category") == "off_topic" and bool(last_turn.get("tools_used")):
            counts["out_of_scope_tools"] += 1
    return counts


def _case_pass_counts(cases: list[dict[str, Any]], aggs: list[dict[str, Any]]) -> dict[str, tuple[int, int]]:
    pass_counts: dict[str, int] = {c["id"]: 0 for c in cases}
    fail_counts: dict[str, int] = {c["id"]: 0 for c in cases}
    for a in aggs:
        per = {pc["id"]: pc["passed"] for pc in a.get("per_case", [])}
        for cid, passed in per.items():
            if passed:
                pass_counts[cid] = pass_counts.get(cid, 0) + 1
            else:
                fail_counts[cid] = fail_counts.get(cid, 0) + 1
    return {cid: (pass_counts.get(cid, 0), fail_counts.get(cid, 0)) for cid in pass_counts}


def build_ablation(
    cases_path: str | Path,
    configs: dict[str, list[str]],
    baseline: str,
    runs_dir: str | Path = Path("reports/eval_runs"),
    *,
    name: str = "",
) -> dict[str, Any]:
    """Compute ablation comparison, paired win/loss deltas, costs, gates, and §3.4 decisions."""
    if not configs:
        raise ValueError("At least one configuration is required")
    if baseline not in configs:
        raise ValueError(f"Baseline configuration '{baseline}' is missing from configs")

    c_path = Path(cases_path)
    cases = load_cases(c_path)
    r_dir = Path(runs_dir)

    raw_cfg_layers: dict[str, dict[str, bool]] = {}
    loaded_by_cfg: dict[str, list[tuple[str, list[dict[str, Any]], list[dict[str, Any]] | None]]] = {}

    for label, run_ids in configs.items():
        if not run_ids:
            raise ValueError(f"Configuration '{label}' has no run IDs")
        layers, loaded = _extract_config_layers(label, list(run_ids), r_dir)
        raw_cfg_layers[label] = layers
        loaded_by_cfg[label] = loaded

    base_layers = raw_cfg_layers[baseline]
    single_diffs: dict[str, str] = {}
    for label, layers in raw_cfg_layers.items():
        if label == baseline:
            continue
        diffs = [k for k in LAYER_KEYS if base_layers.get(k) != layers.get(k)]
        if len(diffs) > 1:
            raise ValueError(
                f"Config '{label}' differs from baseline '{baseline}' in more than one layer: {diffs}"
            )
        if len(diffs) == 1:
            single_diffs[label] = diffs[0]

    cfg_entries: dict[str, dict[str, Any]] = {}
    aggs_by_cfg: dict[str, list[dict[str, Any]]] = {}

    for label, loaded in loaded_by_cfg.items():
        mets, aggs = _compute_metrics_summary(cases, loaded)
        aggs_by_cfg[label] = aggs
        passed_per_run = [sum(1 for pc in a["per_case"] if pc["passed"]) for a in aggs]

        per_run_costs = [_compute_run_cost_by_agent(cases, res) for _, res, _ in loaded]
        all_agents = sorted({ag for rc in per_run_costs for ag in rc})
        n_runs = len(loaded)
        cost_by_agent = {
            agent: round(math.fsum(rc.get(agent, 0.0) for rc in per_run_costs) / n_runs, 8)
            for agent in all_agents
        }

        per_run_gates = [_compute_run_gates(cases, res) for _, res, _ in loaded]
        gates_sum = {k: sum(g[k] for g in per_run_gates) for k in GATE_KEYS}

        cfg_entries[label] = {
            "runs": [rid for rid, _, _ in loaded],
            "layers": raw_cfg_layers[label],
            "metrics": mets,
            "passed_per_run": passed_per_run,
            "cost_by_agent": cost_by_agent,
            "gates": gates_sum,
        }

    base_counts = _case_pass_counts(cases, aggs_by_cfg[baseline])
    n_base = len(aggs_by_cfg[baseline])
    paired: dict[str, dict[str, list[str]]] = {}
    for label in configs:
        if label == baseline:
            continue
        cfg_counts = _case_pass_counts(cases, aggs_by_cfg[label])
        n_cfg = len(aggs_by_cfg[label])
        lost: list[str] = []
        gained: list[str] = []
        for c in cases:
            cid = c["id"]
            bp, bf = base_counts[cid]
            cp, cf = cfg_counts[cid]
            if (2 * bp > n_base) and (2 * cf > n_cfg):
                lost.append(cid)
            elif (2 * bf > n_base) and (2 * cp > n_cfg):
                gained.append(cid)
        paired[label] = {"lost": sorted(lost), "gained": sorted(gained)}

    # Language estimate from baseline records
    rewritten_turns = 0
    for _, res, _ in loaded_by_cfg[baseline]:
        by_id = {r["id"]: r for r in res}
        for c in cases:
            r = by_id.get(c["id"])
            if not r or r.get("status") != "ok":
                continue
            for turn in r.get("turns") or []:
                if (turn.get("language") or {}).get("status") == "rewritten":
                    rewritten_turns += 1

    lang_cost_usd_per_run = cfg_entries[baseline]["cost_by_agent"].get("LanguageRewriter", 0.0)
    total_cost_mean = cfg_entries[baseline]["metrics"]["estimated_cost_usd"]["mean"]
    cost_share = (lang_cost_usd_per_run / total_cost_mean) if (total_cost_mean and total_cost_mean > 0) else 0.0
    language_estimate = {
        "rewritten_turns": rewritten_turns,
        "cost_usd_per_run": lang_cost_usd_per_run,
        "cost_share": cost_share,
    }

    # Decisions (§3.4)
    verifier_cfg = next(
        (lbl for lbl, layer in single_diffs.items() if layer == "verifier" and raw_cfg_layers[lbl].get("verifier") is False),
        None,
    )
    verifier_decision: dict[str, Any] | None = None
    if verifier_cfg is not None:
        base_ppr = cfg_entries[baseline]["passed_per_run"]
        abl_ppr = cfg_entries[verifier_cfg]["passed_per_run"]
        delta_q = (math.fsum(base_ppr) / len(base_ppr)) - (math.fsum(abl_ppr) / len(abl_ppr))
        gates_base = sum(cfg_entries[baseline]["gates"].values())
        gates_abl = sum(cfg_entries[verifier_cfg]["gates"].values())
        verifier_decision = {
            "config": verifier_cfg,
            "delta_q": delta_q,
            "gates_baseline": gates_base,
            "gates_ablated": gates_abl,
            "keep": bool(delta_q >= 1.0 or gates_abl > gates_base),
        }

    planner_cfg = next(
        (lbl for lbl, layer in single_diffs.items() if layer == "planner" and raw_cfg_layers[lbl].get("planner") is False),
        None,
    )
    decisions = {
        "verifier": verifier_decision,
        "language": {
            "rewritten_turns": rewritten_turns,
            "cost_share": cost_share,
            "keep": bool(rewritten_turns >= 1 or cost_share < 0.01),
        },
        "planner": {
            "config": planner_cfg,
            "keep": True,
            "reason": "feature_dependency",
        },
    }

    return {
        "name": name,
        "cases_sha256": cases_sha256(cases),
        "baseline": baseline,
        "configs": cfg_entries,
        "paired": paired,
        "language_estimate": language_estimate,
        "decisions": decisions,
    }


def _fmt_usd(val: float | None) -> str:
    if val is None:
        return "n/d"
    return f"US$ {val:.4f}".replace(".", ",")


def _render_ablation_md(report: dict[str, Any]) -> str:
    configs = report["configs"]
    labels = list(configs.keys())
    lines: list[str] = [
        f"# Relatório de Ablação: {report['name']}",
        "",
        f"- **Baseline:** `{report['baseline']}`",
        f"- **SHA-256 do conjunto:** `{report['cases_sha256']}`",
        "",
        "## Métricas por configuração",
        "",
        "| Métrica | " + " | ".join(labels) + " |",
        "| :--- |" + " :--- |" * len(labels),
        "| Execuções | " + " | ".join(", ".join(configs[lbl]["runs"]) for lbl in labels) + " |",
        "| Aprovados por execução | " + " | ".join(", ".join(str(x) for x in configs[lbl]["passed_per_run"]) for lbl in labels) + " |",
    ]
    for name, _, _, title, kind in COMPARE_METRICS:
        lines.append(f"| {title} | " + " | ".join(format_cell(kind, configs[lbl]["metrics"][name]) for lbl in labels) + " |")

    all_agents = sorted({ag for lbl in labels for ag in configs[lbl]["cost_by_agent"]})
    lines.extend(["", "## Custo médio por agente (US$ / execução)", ""])
    if all_agents:
        lines.append("| Agente | " + " | ".join(labels) + " |")
        lines.append("| :--- |" + " :--- |" * len(labels))
        for ag in all_agents:
            lines.append("| `" + ag + "` | " + " | ".join(_fmt_usd(configs[lbl]["cost_by_agent"].get(ag, 0.0)) for lbl in labels) + " |")
    else:
        lines.append("Sem dados de tokens por agente.")

    lines.extend([
        "",
        "## Portões de segurança e escopo (soma nas execuções)",
        "",
        "| Portão | " + " | ".join(labels) + " |",
        "| :--- |" + " :--- |" * len(labels),
    ])
    for gkey, gtitle in (
        ("unrequested_tickets", "Chamados sem pedido (`escalate: false`)"),
        ("wrong_language", "Idioma incorreto (`language_ok == false`)"),
        ("out_of_scope_tools", "Ferramentas fora de escopo (`off_topic`)"),
    ):
        lines.append(f"| {gtitle} | " + " | ".join(str(configs[lbl]["gates"][gkey]) for lbl in labels) + " |")

    lines.extend(["", f"## Comparação pareada contra `{report['baseline']}`", ""])
    if report["paired"]:
        lines.append("| Configuração | Perdidos (`lost`) | Ganhos (`gained`) |")
        lines.append("| :--- | :--- | :--- |")
        for lbl, delta in report["paired"].items():
            lost_str = ", ".join(f"`{x}`" for x in delta["lost"]) or "nenhum"
            gained_str = ", ".join(f"`{x}`" for x in delta["gained"]) or "nenhum"
            lines.append(f"| `{lbl}` | {lost_str} | {gained_str} |")
    else:
        lines.append("Nenhuma configuração alternativa comparada.")

    le = report["language_estimate"]
    dec = report["decisions"]
    lines.extend([
        "",
        "## Estimativa da camada de idioma",
        "",
        f"- Turnos reescritos no baseline: **{le['rewritten_turns']}**",
        f"- Custo médio do `LanguageRewriter` por execução: **{_fmt_usd(le['cost_usd_per_run'])}**",
        f"- Participação no custo total médio: **{le['cost_share'] * 100:.2f}%**".replace(".", ","),
        "",
        "## Decisões pela regra de ablação",
        "",
        ABLATION_RULE_TEXT,
        "",
        "| Camada | Configuração comparada | Entradas | Manter padrão? |",
        "| :--- | :--- | :--- | :--- |",
    ])
    dv = dec.get("verifier")
    if dv is not None:
        dv_inputs = f"ΔQ={dv['delta_q']:.3f}, G_base={dv['gates_baseline']}, G_abl={dv['gates_ablated']}"
        lines.append(f"| Verificador | `{dv['config']}` | {dv_inputs} | {'sim' if dv['keep'] else 'não'} |")
    else:
        lines.append("| Verificador | n/d | sem configuração `no_verifier` | n/d |")
    dl = dec["language"]
    dl_inputs = f"rewritten_turns={dl['rewritten_turns']}, cost_share={dl['cost_share'] * 100:.2f}%"
    lines.append(f"| Checagem de idioma | `{report['baseline']}` | {dl_inputs} | {'sim' if dl['keep'] else 'não'} |")
    dp = dec["planner"]
    dp_cfg = f"`{dp['config']}`" if dp["config"] else "n/d"
    lines.append(f"| Planner | {dp_cfg} | reason={dp['reason']} | {'sim' if dp['keep'] else 'não'} |")
    lines.append("")
    return "\n".join(lines)


def write_ablation(
    name: str,
    cases_path: str | Path,
    configs: dict[str, list[str]],
    baseline: str,
    runs_dir: str | Path = Path("reports/eval_runs"),
    out_dir: str | Path = Path("reports"),
) -> dict[str, Any]:
    """Build ablation analysis and write `<out_dir>/<name>.json` and `<out_dir>/<name>.md`."""
    report = build_ablation(cases_path, configs, baseline, runs_dir=runs_dir, name=name)
    out_base = Path(out_dir)
    out_base.mkdir(parents=True, exist_ok=True)
    json_path = out_base / f"{name}.json"
    md_path = out_base / f"{name}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    md_path.write_text(_render_ablation_md(report), encoding="utf-8", newline="\n")
    return report
