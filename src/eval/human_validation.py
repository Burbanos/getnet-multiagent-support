"""Human validation sampling, blind form generation, CSV answer parsing, and agreement reporting."""
from __future__ import annotations

import copy
import csv
import hashlib
import json
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.eval.cases import cases_sha256, load_cases
from src.eval.checks import evaluate_case
from src.eval.judge import build_judge_input, load_judgments, should_judge
from src.eval.runner import load_results

SEED = "getnet-human-validation-2026-11-12"
SOURCE_RUN = "v2-1"
SAMPLE_SIZE = 30
CASES_FILE = "data/eval/cases_v2.jsonl"
SAMPLE_DIR = "reports/human_validation"
ROUTES = ("conhecimento", "conta", "ambos", "humano", "nenhum")
FIELDS = ("id", "rota", "deveria_abster", "aceitavel", "absteve", "fundamentacao")
WILSON_Z = 1.959964

FORM_INSTRUCTIONS = """# Validação humana dos rótulos e do juiz

Amostra de 30 casos da execução `v2-1` do conjunto v2, sorteada antes de qualquer resposta (semente fixa em `sample.json`). Os ids `h01` a `h30` não revelam o caso nem a categoria.

Até terminar, não abra `reports/human_validation/sample.json`, `data/eval/cases_v2.jsonl`, `reports/eval_runs/v2-1.jsonl` nem `reports/eval_runs/v2-1.judge.jsonl`: eles têm o mapa dos ids, os rótulos e as notas do juiz.

Copie `answers_template.csv` para `answers.csv` na mesma pasta e preencha com um editor de texto: uma linha por caso, separador `;`, valores sem acento.

## Como preencher

Parte 1 (só as mensagens do lojista). Preencha `rota` de todos os casos antes de abrir a Parte 2:

- `rota`: quem deveria tratar a última mensagem: `conhecimento` (produtos, taxas, prazos e regras da Getnet, clima, câmbio, notícias), `conta` (dados da conta do próprio lojista: vendas, depósitos, transações recusadas, maquininha), `ambos`, `humano` (o lojista pede um atendente ou faz uma reclamação formal) ou `nenhum` (cumprimento ou assunto fora do suporte, que o assistente trata sem consultar nada).

Parte 2 (resposta final e evidências que o assistente tinha, as mesmas que o juiz recebeu):

- `deveria_abster` (`S` ou `N`): `S` se, com as evidências mostradas, o certo era dizer que a informação não está disponível ou recusar o assunto; `N` se as evidências permitiam responder.
- `aceitavel` (`S` ou `N`): `S` se você enviaria essa resposta a um lojista sem correção (fatos certos, responde ao que foi pedido, no idioma da pergunta).
- `absteve` (`S` ou `N`): `S` se a resposta não dá uma resposta substantiva e só diz que não encontrou, que não pode ajudar ou que encaminha a um atendente; `N` se dá uma resposta substantiva, mesmo errada.
- `fundamentacao` (1 a 5, a escala do juiz): 5 = toda afirmação factual está nas evidências ou decorre delas, ou a resposta não faz afirmação factual; 4 = apoiada, com redação além das evidências que não muda nenhum fato; 3 = quase tudo apoiado, mas ao menos um detalhe não está nas evidências; 2 = uma afirmação importante não está nas evidências; 1 = a afirmação principal contradiz as evidências ou é inventada. Conhecimento geral que não é sobre a Getnet, seus produtos ou a conta do lojista não precisa de evidência; valores de clima e câmbio precisam.
"""


def file_sha256(path: str | Path) -> str:
    """Compute SHA-256 hex digest of file bytes with CRLF normalized to LF."""
    raw = Path(path).read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(raw).hexdigest()


def hash_key(*parts: str) -> str:
    """Compute deterministic SHA-256 sort key prefixed with the fixed seed."""
    return hashlib.sha256(":".join((SEED, *parts)).encode("utf-8")).hexdigest()


def eligible_ids(
    cases: list[dict[str, Any]],
    results: dict[str, dict[str, Any]],
    judgments: dict[str, dict[str, Any]],
) -> list[str]:
    """Return eligible case IDs in dataset order."""
    out: list[str] = []
    for case in cases:
        cid = case["id"]
        res = results.get(cid)
        jd = judgments.get(cid)
        if res is not None and should_judge(case, res) and jd is not None and jd.get("status") == "ok":
            out.append(cid)
    return out


def allocate(counts: dict[str, int], size: int) -> dict[str, int]:
    """Allocate sample size across categories using largest remainder and alphabetical tie-breaking."""
    n = sum(counts.values())
    if n == 0:
        return {cat: 0 for cat in sorted(counts)}

    base = {cat: size * count // n for cat, count in counts.items()}
    rem = {cat: size * count - base[cat] * n for cat, count in counts.items()}
    remaining = size - sum(base.values())
    for cat in sorted(counts, key=lambda c: (-rem[c], c))[:remaining]:
        base[cat] += 1
    return {cat: base[cat] for cat in sorted(counts)}


def select_sample(
    cases: list[dict[str, Any]],
    results: dict[str, dict[str, Any]],
    judgments: dict[str, dict[str, Any]],
    size: int = SAMPLE_SIZE,
) -> list[dict[str, str]]:
    """Select a stratified deterministic sample and assign blinded IDs h01..hNN."""
    elig = eligible_ids(cases, results, judgments)
    cases_by_id = {c["id"]: c for c in cases}

    by_cat: dict[str, list[str]] = {}
    for cid in elig:
        cat = cases_by_id[cid]["category"]
        by_cat.setdefault(cat, []).append(cid)

    counts = {cat: len(cids) for cat, cids in by_cat.items()}
    alloc = allocate(counts, size)

    picked: list[str] = []
    for cat in sorted(by_cat):
        cids_sorted = sorted(by_cat[cat], key=lambda c: hash_key("pick", c))
        picked.extend(cids_sorted[: alloc[cat]])

    ordered = sorted(picked, key=lambda c: hash_key("order", c))
    return [{"hid": f"h{i:02d}", "case_id": cid} for i, cid in enumerate(ordered, 1)]


def label_route(case: dict[str, Any]) -> str | None:
    """Map expected case routing to Portuguese validation route category."""
    expect = case["expect"]
    if expect.get("escalate") is True:
        return "humano"
    agents = expect.get("agents")
    if agents is None:
        return None
    agent_set = set(agents)
    mapping = {
        frozenset(): "nenhum",
        frozenset({"KnowledgeAgent"}): "conhecimento",
        frozenset({"SupportAgent"}): "conta",
        frozenset({"KnowledgeAgent", "SupportAgent"}): "ambos",
    }
    return mapping.get(frozenset(agent_set))


def judge_acceptable(judgment: dict[str, Any]) -> bool:
    """Return True if judge ratings meet the acceptability threshold (>= 4 on both scales)."""
    return bool(judgment["grounded"] >= 4 and judgment["answers_question"] >= 4)


def _quote_turn(text: str) -> str:
    return "\n".join(">" if not line else f"> {line}" for line in text.split("\n"))


def _omit_session_id(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: ("omitido" if k == "session_id" else _omit_session_id(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_omit_session_id(item) for item in obj]
    return copy.deepcopy(obj)


def render_form(
    items: list[dict[str, str]],
    cases_by_id: dict[str, dict[str, Any]],
    results: dict[str, dict[str, Any]],
) -> str:
    """Render the two-part blind Markdown validation form matching the judge's evidence."""
    lines: list[str] = [FORM_INSTRUCTIONS.rstrip("\n"), ""]

    lines.append("## Parte 1: mensagens do lojista")
    lines.append("")
    for item in items:
        hid = item["hid"]
        case = cases_by_id[item["case_id"]]
        lines.append(f"### {hid}")
        lines.append("")
        for idx, turn_text in enumerate(case["turns"], 1):
            lines.append(f"Mensagem {idx} do lojista:")
            lines.append("")
            lines.append(_quote_turn(turn_text))
            lines.append("")

    lines.append("## Parte 2: respostas e evidências")
    lines.append("")
    for item in items:
        hid = item["hid"]
        case = cases_by_id[item["case_id"]]
        result = results[item["case_id"]]
        payload = json.loads(build_judge_input(case, result))

        lines.append(f"### {hid}")
        lines.append("")
        for idx, turn_text in enumerate(case["turns"], 1):
            lines.append(f"Mensagem {idx} do lojista:")
            lines.append("")
            lines.append(_quote_turn(turn_text))
            lines.append("")

        lines.append("Resposta final do assistente:")
        lines.append("")
        lines.append("````text")
        lines.append(str(payload.get("final_response") or ""))
        lines.append("````")
        lines.append("")

        passages = payload.get("passages") or []
        if not passages:
            lines.append("Evidências: nenhuma.")
            lines.append("")
        else:
            for idx, passage in enumerate(passages, 1):
                url = passage.get("url") or "sem URL"
                lines.append(f"Evidência {idx}: {url}")
                lines.append("")
                lines.append("````text")
                lines.append(str(passage.get("text") or ""))
                lines.append("````")
                lines.append("")

        tool_outputs = payload.get("tool_outputs") or []
        if not tool_outputs:
            lines.append("Saídas dos agentes e ferramentas: nenhuma.")
            lines.append("")
        else:
            sanitized = _omit_session_id(tool_outputs)
            lines.append("Saídas dos agentes e ferramentas:")
            lines.append("")
            lines.append("````json")
            lines.append(json.dumps(sanitized, ensure_ascii=False, indent=2))
            lines.append("````")
            lines.append("")

    return "\n".join(lines).rstrip("\n") + "\n"


def write_sample(
    out_dir: str | Path = SAMPLE_DIR,
    cases_path: str | Path = CASES_FILE,
    run_id: str = SOURCE_RUN,
    runs_dir: str | Path = "reports/eval_runs",
) -> dict[str, Any]:
    """Generate and persist sample.json, form.md, and answers_template.csv without overwriting."""
    out_path = Path(out_dir)
    sample_path = out_path / "sample.json"
    if sample_path.exists():
        raise FileExistsError(f"Sample file already exists: {sample_path}")

    cases_p = Path(cases_path)
    runs_p = Path(runs_dir)
    results_path = runs_p / f"{run_id}.jsonl"
    judgments_path = runs_p / f"{run_id}.judge.jsonl"

    cases = load_cases(cases_p)
    cases_by_id = {c["id"]: c for c in cases}
    results = load_results(results_path)
    judgments = load_judgments(judgments_path)

    elig = eligible_ids(cases, results, judgments)
    counts: dict[str, int] = {}
    for cid in elig:
        cat = cases_by_id[cid]["category"]
        counts[cat] = counts.get(cat, 0) + 1

    allocation = allocate(counts, SAMPLE_SIZE)
    items = select_sample(cases, results, judgments, size=SAMPLE_SIZE)

    sample_obj: dict[str, Any] = {
        "seed": SEED,
        "source_run": run_id,
        "cases_file": cases_p.as_posix(),
        "cases_sha256": cases_sha256(cases),
        "records_sha256": file_sha256(results_path),
        "judgments_sha256": file_sha256(judgments_path),
        "size": SAMPLE_SIZE,
        "eligible": len(elig),
        "allocation": allocation,
        "items": items,
    }

    form_text = render_form(items, cases_by_id, results)
    template_lines = [";".join(FIELDS)] + [f"{it['hid']};;;;;" for it in items]
    template_text = "\n".join(template_lines) + "\n"

    out_path.mkdir(parents=True, exist_ok=True)
    sample_path.write_text(json.dumps(sample_obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    (out_path / "form.md").write_text(form_text, encoding="utf-8", newline="\n")
    (out_path / "answers_template.csv").write_text(template_text, encoding="utf-8", newline="\n")

    return sample_obj


def _parse_bool_sn(val: str, line_no: int, hid: str, col_name: str) -> bool:
    low = val.lower()
    if low == "s":
        return True
    if low == "n":
        return False
    raise ValueError(f"Line {line_no} ({hid}): invalid {col_name} '{val}', expected S or N")


def parse_answers(path: str | Path, hids: list[str]) -> dict[str, dict[str, Any]]:
    """Parse and validate human answers from CSV (supports UTF-8-SIG and cp1252, ';' or ',')."""
    raw_bytes = Path(path).read_bytes()
    try:
        text = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw_bytes.decode("cp1252")

    lines = [ln for ln in text.replace("\r\n", "\n").replace("\r", "\n").splitlines() if ln.strip()]
    if not lines:
        raise ValueError("Line 1: answers CSV is empty")

    delimiter = ";" if ";" in lines[0] else ","
    reader = csv.reader(lines, delimiter=delimiter)

    header_row = next(reader)
    normalized_header = tuple(col.strip().lower() for col in header_row)
    if len(normalized_header) != len(FIELDS) or normalized_header != FIELDS:
        raise ValueError(f"Line 1: invalid header {header_row}, expected {list(FIELDS)}")

    expected_hids = set(hids)
    parsed: dict[str, dict[str, Any]] = {}

    for line_no, row in enumerate(reader, start=2):
        if len(row) != len(FIELDS):
            raise ValueError(f"Line {line_no}: expected {len(FIELDS)} columns, got {len(row)}")

        cells = [c.strip() for c in row]
        hid = cells[0]
        if not hid:
            raise ValueError(f"Line {line_no}: empty id")
        if hid not in expected_hids:
            raise ValueError(f"Line {line_no}: unknown id '{hid}'")
        if hid in parsed:
            raise ValueError(f"Line {line_no}: duplicate id '{hid}'")

        rota = cells[1].lower()
        if rota not in ROUTES:
            raise ValueError(f"Line {line_no} ({hid}): invalid rota '{cells[1]}', expected one of {ROUTES}")

        deveria_abster = _parse_bool_sn(cells[2], line_no, hid, "deveria_abster")
        aceitavel = _parse_bool_sn(cells[3], line_no, hid, "aceitavel")
        absteve = _parse_bool_sn(cells[4], line_no, hid, "absteve")

        fund_raw = cells[5]
        if fund_raw not in ("1", "2", "3", "4", "5"):
            raise ValueError(f"Line {line_no} ({hid}): invalid fundamentacao '{fund_raw}', expected integer 1..5")

        parsed[hid] = {
            "rota": rota,
            "deveria_abster": deveria_abster,
            "aceitavel": aceitavel,
            "absteve": absteve,
            "fundamentacao": int(fund_raw),
        }

    missing = [h for h in hids if h not in parsed]
    if missing:
        raise ValueError(f"Missing answers for ids: {missing}")

    return {h: parsed[h] for h in hids}


def _wilson_ci(agree: int, n: int) -> tuple[float | None, float | None]:
    if n == 0:
        return None, None
    p = agree / n
    z2 = WILSON_Z * WILSON_Z
    denom = 1.0 + z2 / n
    center = (p + z2 / (2.0 * n)) / denom
    half = WILSON_Z * math.sqrt(p * (1.0 - p) / n + z2 / (4.0 * n * n)) / denom
    return center - half, center + half


def _compare_pair_list(pairs: list[tuple[str, str, Any, Any]]) -> dict[str, Any]:
    used = [(hid, cid, hum, oth) for hid, cid, hum, oth in pairs if oth is not None]
    n = len(used)
    agree = sum(1 for _, _, hum, oth in used if hum == oth)
    rate = agree / n if n else None
    w_low, w_high = _wilson_ci(agree, n)

    kappa: float | None = None
    if n:
        po = agree / n
        cats = {hum for _, _, hum, _ in used} | {oth for _, _, _, oth in used}
        pe = math.fsum(
            (sum(1 for _, _, hum, _ in used if hum == c) / n)
            * (sum(1 for _, _, _, oth in used if oth == c) / n)
            for c in cats
        )
        kappa = None if pe == 1 else (po - pe) / (1.0 - pe)

    disagreements = [
        {"hid": hid, "case_id": cid, "human": hum, "other": oth}
        for hid, cid, hum, oth in used
        if hum != oth
    ]
    return {
        "n": n,
        "agree": agree,
        "rate": rate,
        "wilson_low": w_low,
        "wilson_high": w_high,
        "kappa": kappa,
        "disagreements": disagreements,
    }


def agreement(
    sample: dict[str, Any],
    answers: dict[str, dict[str, Any]],
    cases_by_id: dict[str, dict[str, Any]],
    results: dict[str, dict[str, Any]],
    judgments: dict[str, dict[str, Any]],
    sample_sha256: str,
    answers_sha256: str,
) -> dict[str, Any]:
    """Compute human agreement metrics, Wilson 95% intervals, Cohen's kappa, and disagreements."""
    if cases_sha256(list(cases_by_id.values())) != sample["cases_sha256"]:
        raise ValueError("cases changed since the sample")

    items = sample["items"]
    comp_rows: dict[str, list[tuple[str, str, Any, Any]]] = {
        "route_vs_label": [],
        "abstain_vs_label": [],
        "acceptable_vs_checks": [],
        "acceptable_vs_judge": [],
        "abstained_vs_judge": [],
    }
    g_pairs: list[dict[str, Any]] = []
    passed_checks = 0

    for item in items:
        hid = item["hid"]
        cid = item["case_id"]
        case = cases_by_id[cid]
        res = results[cid]
        jd = judgments[cid]
        ans = answers[hid]

        checks_ok = bool(evaluate_case(case, res)["passed"])
        if checks_ok:
            passed_checks += 1

        comp_rows["route_vs_label"].append((hid, cid, ans["rota"], label_route(case)))
        comp_rows["abstain_vs_label"].append((hid, cid, ans["deveria_abster"], case["expect"].get("abstain")))
        comp_rows["acceptable_vs_checks"].append((hid, cid, ans["aceitavel"], checks_ok))
        comp_rows["acceptable_vs_judge"].append((hid, cid, ans["aceitavel"], judge_acceptable(jd)))
        comp_rows["abstained_vs_judge"].append((hid, cid, ans["absteve"], bool(jd["abstained"])))

        g_pairs.append({
            "hid": hid,
            "case_id": cid,
            "human": ans["fundamentacao"],
            "judge": jd["grounded"],
        })

    n_items = len(items)
    exact = sum(1 for p in g_pairs if p["human"] == p["judge"])
    within_one = sum(1 for p in g_pairs if abs(p["human"] - p["judge"]) <= 1)

    grounded_vs_judge = {
        "n": n_items,
        "exact": exact,
        "exact_rate": exact / n_items if n_items else 0.0,
        "within_one": within_one,
        "within_one_rate": within_one / n_items if n_items else 0.0,
        "human_mean": math.fsum(p["human"] for p in g_pairs) / n_items if n_items else 0.0,
        "judge_mean": math.fsum(p["judge"] for p in g_pairs) / n_items if n_items else 0.0,
        "human_lower": sum(1 for p in g_pairs if p["human"] < p["judge"]),
        "human_higher": sum(1 for p in g_pairs if p["human"] > p["judge"]),
        "pairs": g_pairs,
    }

    return {
        "source_run": sample["source_run"],
        "seed": sample["seed"],
        "sample_sha256": sample_sha256,
        "answers_sha256": answers_sha256,
        "n_items": n_items,
        "comparisons": {key: _compare_pair_list(rows) for key, rows in comp_rows.items()},
        "grounded_vs_judge": grounded_vs_judge,
        "pass_rate_checks": passed_checks / n_items if n_items else 0.0,
        "acceptable_rate_human": (
            sum(1 for it in items if answers[it["hid"]]["aceitavel"]) / n_items if n_items else 0.0
        ),
    }


def _fmt_pct(val: float | None) -> str:
    return "n/a" if val is None else f"{val * 100:.1f}%"


def _fmt_num(val: float | None, nd: int = 3) -> str:
    return "n/a" if val is None else f"{val:.{nd}f}"


def render_agreement_md(report: dict[str, Any]) -> str:
    """Render human validation agreement report as Markdown."""
    lines: list[str] = [
        f"# Human Validation Agreement ({report['source_run']})",
        "",
        f"- **Source run:** `{report['source_run']}`",
        f"- **Sample items:** {report['n_items']}",
        f"- **Seed:** `{report['seed']}`",
        f"- **Pass rate (deterministic checks):** {_fmt_pct(report['pass_rate_checks'])}",
        f"- **Acceptable rate (human):** {_fmt_pct(report['acceptable_rate_human'])}",
        "",
        "## Comparisons",
        "",
        "| Comparison | Agree/n | Rate | Wilson 95% CI | Kappa |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ]

    for key, comp in report["comparisons"].items():
        agree_str = f"{comp['agree']}/{comp['n']}"
        rate_str = _fmt_pct(comp["rate"])
        if comp["wilson_low"] is not None and comp["wilson_high"] is not None:
            ci_str = f"[{_fmt_pct(comp['wilson_low'])}, {_fmt_pct(comp['wilson_high'])}]"
        else:
            ci_str = "n/a"
        kappa_str = _fmt_num(comp["kappa"])
        lines.append(f"| `{key}` | {agree_str} | {rate_str} | {ci_str} | {kappa_str} |")

    g = report["grounded_vs_judge"]
    lines.extend([
        "",
        "## Groundedness Rating (Human vs Judge)",
        "",
        "| Metric | Value |",
        "| :--- | :--- |",
        f"| n | {g['n']} |",
        f"| Exact match | {g['exact']}/{g['n']} ({_fmt_pct(g['exact_rate'])}) |",
        f"| Within 1 point | {g['within_one']}/{g['n']} ({_fmt_pct(g['within_one_rate'])}) |",
        f"| Human mean | {_fmt_num(g['human_mean'])} |",
        f"| Judge mean | {_fmt_num(g['judge_mean'])} |",
        f"| Human lower than judge | {g['human_lower']} |",
        f"| Human higher than judge | {g['human_higher']} |",
        "",
        "## Disagreements",
        "",
    ])

    any_disagree = False
    for key, comp in report["comparisons"].items():
        dis = comp["disagreements"]
        if dis:
            any_disagree = True
            lines.append(f"### `{key}` ({len(dis)})")
            lines.append("")
            for d in dis:
                lines.append(f"- `{d['hid']}` (`{d['case_id']}`): human=`{d['human']}` vs other=`{d['other']}`")
            lines.append("")
    if not any_disagree:
        lines.append("None.")
        lines.append("")

    return "\n".join(lines).rstrip("\n") + "\n"


def write_agreement_report(
    report: dict[str, Any],
    out_json: str | Path,
    out_md: str | Path,
) -> dict[str, Any]:
    """Persist agreement report JSON (with UTC generated_at) and Markdown."""
    out_obj = dict(report)
    out_obj["generated_at"] = datetime.now(UTC).isoformat()

    json_p = Path(out_json)
    md_p = Path(out_md)
    json_p.parent.mkdir(parents=True, exist_ok=True)
    md_p.parent.mkdir(parents=True, exist_ok=True)

    json_p.write_text(json.dumps(out_obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    md_p.write_text(render_agreement_md(out_obj), encoding="utf-8", newline="\n")

    return out_obj
