"""Evaluation harness and report generation for the guardrail pattern matching layer."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.agents.guardrails import GuardrailAgent

VALID_LABELS = {"block", "allow"}
VALID_KINDS = {"prompt_injection", "prompt_leak", "attack_request", "legit"}
VALID_SOURCES = {"audit_probe", "safety_case", "paraphrase", "near_miss"}
VALID_SPLITS = {"dev", "holdout"}
VALID_LANGS = {"pt", "en"}
CASE_KEYS = {"id", "lang", "label", "kind", "source", "split", "text"}
DEFAULT_SET_PATH = Path("data/eval/guardrail_labeled.jsonl")


def load_guardrail_set(path: Path | str = DEFAULT_SET_PATH) -> list[dict[str, Any]]:
    """Load and validate the pre-registered guardrail evaluation dataset."""
    p = Path(path)
    if not p.exists():
        raise ValueError(f"Guardrail set file not found: {p}")

    cases: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for lineno, raw_line in enumerate(p.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue

        try:
            record = json.loads(line)
        except Exception as exc:
            raise ValueError(f"Line {lineno}: invalid JSON - {exc}") from exc

        if not isinstance(record, dict) or set(record.keys()) != CASE_KEYS:
            raise ValueError(f"Line {lineno}: keys do not match CASE_KEYS exactly: {sorted(record.keys()) if isinstance(record, dict) else type(record)}")

        if record["lang"] not in VALID_LANGS:
            raise ValueError(f"Line {lineno}: invalid lang '{record['lang']}'")
        if record["label"] not in VALID_LABELS:
            raise ValueError(f"Line {lineno}: invalid label '{record['label']}'")
        if record["kind"] not in VALID_KINDS:
            raise ValueError(f"Line {lineno}: invalid kind '{record['kind']}'")
        if record["source"] not in VALID_SOURCES:
            raise ValueError(f"Line {lineno}: invalid source '{record['source']}'")
        if record["split"] not in VALID_SPLITS:
            raise ValueError(f"Line {lineno}: invalid split '{record['split']}'")

        cid = record["id"]
        if cid in seen_ids:
            raise ValueError(f"Line {lineno}: duplicate case id '{cid}'")
        seen_ids.add(cid)

        text = record["text"]
        if not text or not text.strip():
            raise ValueError(f"Line {lineno}: text is empty or whitespace only")

        if (record["label"] == "allow") != (record["kind"] == "legit"):
            raise ValueError(f"Line {lineno}: inconsistent label and kind (label='{record['label']}', kind='{record['kind']}')")

        cases.append(record)

    return cases


def guardrail_set_sha256(cases: list[dict[str, Any]]) -> str:
    """Compute deterministic SHA-256 hex digest for a list of guardrail cases."""
    canonical = "\n".join(json.dumps(c, ensure_ascii=False, sort_keys=True) for c in cases)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def rates(cases: list[dict[str, Any]], blocked: dict[str, bool]) -> dict[str, Any]:
    """Compute block rate, false positive rate, missed cases and false positives."""
    blk = [c for c in cases if c["label"] == "block"]
    alw = [c for c in cases if c["label"] == "allow"]
    bb = [c["id"] for c in blk if blocked.get(c["id"], False)]
    ba = [c["id"] for c in alw if blocked.get(c["id"], False)]

    return {
        "n_block": len(blk),
        "n_allow": len(alw),
        "blocked_block": len(bb),
        "blocked_allow": len(ba),
        "block_rate": round(len(bb) / len(blk), 4) if blk else None,
        "false_positive_rate": round(len(ba) / len(alw), 4) if alw else None,
        "missed": sorted(c["id"] for c in blk if not blocked.get(c["id"], False)),
        "false_positives": sorted(ba),
    }


def layer_metrics(cases: list[dict[str, Any]], blocked: dict[str, bool]) -> dict[str, Any]:
    """Compute rates across all cases, by split and counts by kind."""
    kinds = sorted({c["kind"] for c in cases})
    return {
        "all": rates(cases, blocked),
        "by_split": {
            s: rates([c for c in cases if c["split"] == s], blocked)
            for s in ("dev", "holdout")
        },
        "by_kind": {
            k: {
                "n": sum(1 for c in cases if c["kind"] == k),
                "blocked": sum(1 for c in cases if c["kind"] == k and blocked.get(c["id"], False)),
            }
            for k in kinds
        },
    }


def pattern_results(cases: list[dict[str, Any]], agent: GuardrailAgent | None = None) -> dict[str, str | None]:
    """Evaluate pattern matching for each case in the dataset."""
    ag = agent if agent is not None else GuardrailAgent()
    return {c["id"]: ag.match_patterns(c["text"]) for c in cases}


def _fmt_ids(ids: list[str]) -> str:
    return ", ".join(ids) if ids else "nenhum"


def write_pattern_report(
    cases: list[dict[str, Any]],
    out_json: Path | str,
    out_md: Path | str,
    set_path: Path | str = DEFAULT_SET_PATH,
) -> dict[str, Any]:
    """Generate and write JSON and Markdown reports for the guardrail pattern layer."""
    results = pattern_results(cases)
    blocked = {cid: res is not None for cid, res in results.items()}
    norm_set_path = Path(set_path).as_posix()
    set_sha = guardrail_set_sha256(cases)
    now_iso = datetime.now(UTC).isoformat()
    metrics = layer_metrics(cases, blocked)

    case_items = [
        {
            "id": c["id"],
            "label": c["label"],
            "kind": c["kind"],
            "split": c["split"],
            "blocked": blocked.get(c["id"], False),
            "category": results.get(c["id"]),
        }
        for c in cases
    ]

    report_data = {
        "set_path": norm_set_path,
        "set_sha256": set_sha,
        "n_cases": len(cases),
        "layer": "patterns",
        "generated_at": now_iso,
        "metrics": metrics,
        "cases": case_items,
    }

    p_json = Path(out_json)
    p_json.parent.mkdir(parents=True, exist_ok=True)
    p_json.write_text(json.dumps(report_data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _row(name: str, r: dict[str, Any]) -> str:
        b_rate = f"{r['block_rate']:.2f}" if r["block_rate"] is not None else "N/A"
        fp_rate = f"{r['false_positive_rate']:.2f}" if r["false_positive_rate"] is not None else "N/A"
        return f"| {name} | {r['blocked_block']}/{r['n_block']} ({b_rate}) | {r['blocked_allow']}/{r['n_allow']} ({fp_rate}) |"

    m = metrics
    md_lines = [
        "# Guardrail: camada de padrões",
        "",
        f"Conjunto: `{norm_set_path}` (sha256 `{set_sha}`), {len(cases)} mensagens. Gerado em {now_iso}.",
        "",
        "| Recorte | Injeções e ataques bloqueados | Legítimas bloqueadas (falsos positivos) |",
        "|---|---|---|",
        _row("todos", m["all"]),
        _row("dev", m["by_split"]["dev"]),
        _row("holdout", m["by_split"]["holdout"]),
        "",
        f"Não bloqueadas pelos padrões: {_fmt_ids(m['all']['missed'])}",
        f"Falsos positivos: {_fmt_ids(m['all']['false_positives'])}",
    ]
    p_md = Path(out_md)
    p_md.parent.mkdir(parents=True, exist_ok=True)
    p_md.write_text("\n".join(md_lines), encoding="utf-8")

    return report_data
