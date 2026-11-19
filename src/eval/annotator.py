"""Standard-library importer for blinded annotator .xlsx workbooks and inter-rater agreement."""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import math
import posixpath
import re
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.eval.human_validation import (
    FIELDS,
    ROUTES,
    SAMPLE_DIR,
    _compare_pair_list,
    _fmt_num,
    _fmt_pct,
    file_sha256,
    parse_answers,
)

RESPONSE_HEADERS = ("id", "rota", "deveria_abster", "aceitavel", "absteve", "fundamentacao", "comentario")

DECLARATION_FIELDS: tuple[tuple[str, str], ...] = (
    ("name", "Nome"),
    ("occupation", "Ocupação / área"),
    ("part1_start", "Data e hora de início da Parte 1"),
    ("part1_end", "Data e hora de término da Parte 1"),
    ("part2_end", "Data e hora de término da Parte 2"),
    ("hours", "Tempo total aproximado (horas)"),
    (
        "no_access",
        "Não tive acesso ao repositório do projeto, aos rótulos, às notas do juiz nem às respostas do autor (S/N)",
    ),
    ("no_discussion", "Não conversei sobre os casos com o autor ou outra pessoa antes de entregar (S/N)"),
    ("route_before_part2", "Preenchi a coluna rota dos 30 casos antes de abrir a Parte 2 (S/N)"),
    ("name_authorized", "Autorizo citar meu nome no relatório (S/N)"),
    ("questions", "Dúvidas sobre as instruções que perguntei ao autor (texto)"),
)

SN_DECL_KEYS = frozenset({"no_access", "no_discussion", "route_before_part2", "name_authorized"})
_CELL_REF_RE = re.compile(r"^([A-Za-z]+)")
_EXCEL_BUILTIN_DATE_FMTS = frozenset(range(14, 23)) | frozenset({45, 46, 47})


class AnnotatorImportError(ValueError):
    """Raised when an annotator spreadsheet fails validation, carrying all collected errors."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("\n".join(errors))


@dataclass(slots=True)
class _ParsedWorkbook:
    sheets: dict[str, list[list[str]]]


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _col_index(cell_ref: str) -> int:
    match = _CELL_REF_RE.match(cell_ref.strip())
    if not match:
        return -1
    idx = 0
    for ch in match.group(1).upper():
        idx = idx * 26 + (ord(ch) - ord("A") + 1)
    return idx - 1


def _extract_rich_text(elem: ET.Element | None) -> str:
    if elem is None:
        return ""
    parts: list[str] = []

    def _walk(node: ET.Element) -> None:
        name = _local_name(node.tag)
        if name == "rPh":
            return
        if name == "t":
            parts.append(node.text or "")
            return
        for child in node:
            _walk(child)

    _walk(elem)
    return "".join(parts)


def _normalize_target(target: str) -> str:
    clean = target.lstrip("/")
    if not clean.startswith("xl/"):
        clean = posixpath.normpath(posixpath.join("xl", clean))
    else:
        clean = posixpath.normpath(clean)
    return clean


def _looks_like_date_format(fmt_code: str) -> bool:
    stripped = re.sub(r'"[^"]*"|\[[^\]]*\]|\\.', "", fmt_code).lower()
    return any(tok in stripped for tok in ("yy", "dd", "hh", "mm"))


def _read_date_style_indices(zf: zipfile.ZipFile) -> set[int]:
    if "xl/styles.xml" not in zf.namelist():
        return set()
    root = ET.fromstring(zf.read("xl/styles.xml"))
    custom_date_fmts: set[int] = set()
    for elem in root.iter():
        if _local_name(elem.tag) == "numFmt":
            try:
                num_id = int(elem.attrib.get("numFmtId", ""))
            except ValueError:
                continue
            if _looks_like_date_format(elem.attrib.get("formatCode", "")):
                custom_date_fmts.add(num_id)

    date_xfs: set[int] = set()
    for child in root:
        if _local_name(child.tag) == "cellXfs":
            for idx, xf in enumerate(c for c in child if _local_name(c.tag) == "xf"):
                try:
                    num_id = int(xf.attrib.get("numFmtId", ""))
                except ValueError:
                    continue
                if num_id in _EXCEL_BUILTIN_DATE_FMTS or num_id in custom_date_fmts:
                    date_xfs.add(idx)
    return date_xfs


def _format_excel_serial_date(raw_val: str) -> str | None:
    try:
        serial = float(raw_val)
    except ValueError:
        return None
    if not math.isfinite(serial) or serial < 1:
        return None
    epoch = dt.datetime(1899, 12, 30)
    rendered = epoch + dt.timedelta(days=serial)
    if rendered.hour == 0 and rendered.minute == 0 and rendered.second == 0:
        return rendered.strftime("%Y-%m-%d")
    return rendered.strftime("%Y-%m-%d %H:%M")


def _read_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []
    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    return [_extract_rich_text(child) for child in root if _local_name(child.tag) == "si"]


def _read_sheet_rows(
    xml_bytes: bytes,
    shared_strings: list[str],
    date_style_indices: set[int],
) -> list[list[str]]:
    root = ET.fromstring(xml_bytes)
    sheet_data = next((child for child in root if _local_name(child.tag) == "sheetData"), None)
    if sheet_data is None:
        return []

    parsed_rows: dict[int, list[str]] = {}
    next_row_num = 1
    max_row_num = 0

    for row_el in sheet_data:
        if _local_name(row_el.tag) != "row":
            continue
        r_attr = row_el.attrib.get("r")
        if r_attr and r_attr.isdigit():
            row_num = int(r_attr)
        else:
            row_num = next_row_num
        next_row_num = row_num + 1
        max_row_num = max(max_row_num, row_num)

        row_cells: dict[int, str] = {}
        next_col = 0
        for cell_el in row_el:
            if _local_name(cell_el.tag) != "c":
                continue
            ref = cell_el.attrib.get("r", "")
            col_idx = _col_index(ref) if ref else -1
            if col_idx < 0:
                col_idx = next_col
            next_col = col_idx + 1

            ctype = cell_el.attrib.get("t", "")
            v_el = next((c for c in cell_el if _local_name(c.tag) == "v"), None)
            is_el = next((c for c in cell_el if _local_name(c.tag) == "is"), None)
            v_text = (v_el.text or "") if v_el is not None else ""

            val = ""
            if ctype == "s":
                if v_text.strip().isdigit():
                    idx = int(v_text.strip())
                    if 0 <= idx < len(shared_strings):
                        val = shared_strings[idx]
            elif ctype == "inlineStr":
                val = _extract_rich_text(is_el)
            elif ctype in ("str", "e"):
                val = v_text
            elif ctype == "b":
                val = "TRUE" if v_text.strip() == "1" else "FALSE"
            else:
                val = v_text
                style_raw = cell_el.attrib.get("s", "")
                if val and style_raw.isdigit() and int(style_raw) in date_style_indices:
                    formatted = _format_excel_serial_date(val)
                    if formatted is not None:
                        val = formatted

            row_cells[col_idx] = val

        if row_cells:
            width = max(row_cells) + 1
            parsed_rows[row_num] = [row_cells.get(i, "") for i in range(width)]
        else:
            parsed_rows[row_num] = []

    return [parsed_rows.get(r, []) for r in range(1, max_row_num + 1)]


def read_xlsx_sheets(xlsx_path: str | Path) -> _ParsedWorkbook:
    """Read all worksheets by sheet name from an .xlsx archive using Python's standard library."""
    p = Path(xlsx_path)
    if not p.exists():
        raise FileNotFoundError(f"Workbook not found: {p}")

    with zipfile.ZipFile(p, "r") as zf:
        names = set(zf.namelist())
        if "xl/workbook.xml" not in names or "xl/_rels/workbook.xml.rels" not in names:
            raise ValueError("Invalid .xlsx workbook: missing xl/workbook.xml or relationships.")

        rels_root = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        rel_targets: dict[str, str] = {}
        for rel in rels_root:
            if _local_name(rel.tag) != "Relationship":
                continue
            rid = rel.attrib.get("Id")
            target = rel.attrib.get("Target")
            if rid and target:
                rel_targets[rid] = _normalize_target(target)

        wb_root = ET.fromstring(zf.read("xl/workbook.xml"))
        sheets_el = next((c for c in wb_root if _local_name(c.tag) == "sheets"), None)
        if sheets_el is None:
            raise ValueError("Invalid .xlsx workbook: missing <sheets> element.")

        shared_strings = _read_shared_strings(zf)
        date_styles = _read_date_style_indices(zf)
        sheets: dict[str, list[list[str]]] = {}

        for sheet_el in sheets_el:
            if _local_name(sheet_el.tag) != "sheet":
                continue
            sheet_name = sheet_el.attrib.get("name", "").strip()
            rid = next(
                (v for k, v in sheet_el.attrib.items() if k == "r:id" or k.endswith("}id")),
                "",
            )
            target_path = rel_targets.get(rid, "")
            if not sheet_name or target_path not in names:
                continue
            sheets[sheet_name] = _read_sheet_rows(zf.read(target_path), shared_strings, date_styles)

    return _ParsedWorkbook(sheets=sheets)


def _cell(row: list[str], idx: int) -> str:
    return row[idx].strip() if idx < len(row) else ""


def _parse_grade(raw: str) -> int | None:
    text = raw.strip()
    if not text:
        return None
    if text in ("1", "2", "3", "4", "5"):
        return int(text)
    try:
        num = float(text)
    except ValueError:
        return None
    if not math.isfinite(num) or not num.is_integer():
        return None
    iv = int(num)
    return iv if 1 <= iv <= 5 else None


def _parse_sn(raw: str) -> str | None:
    up = raw.strip().upper()
    return up if up in ("S", "N") else None


def _validate_responses_sheet(
    rows: list[list[str]],
    sample_hids: list[str],
    errors: list[str],
) -> dict[str, dict[str, Any]]:
    if not rows:
        errors.append("Respostas [cabeçalho]: aba vazia.")
        return {}

    header = tuple(_cell(rows[0], i).lower() for i in range(len(RESPONSE_HEADERS)))
    if header != RESPONSE_HEADERS:
        errors.append(
            f"Respostas [cabeçalho]: esperado {list(RESPONSE_HEADERS)}, encontrado {rows[0][:len(RESPONSE_HEADERS)]}."
        )
        return {}

    expected_set = set(sample_hids)
    parsed: dict[str, dict[str, Any]] = {}

    for row in rows[1:]:
        hid = _cell(row, 0)
        if hid not in expected_set:
            continue
        if hid in parsed:
            errors.append(f"{hid} [id]: caso duplicado na aba Respostas.")
            continue

        rota_raw = _cell(row, 1)
        rota = rota_raw.lower()
        if rota not in ROUTES:
            errors.append(f"{hid} [rota]: valor inválido {rota_raw!r}; esperado um de {list(ROUTES)}.")

        dev_raw = _cell(row, 2)
        deveria_abster = _parse_sn(dev_raw)
        if deveria_abster is None:
            errors.append(f"{hid} [deveria_abster]: valor inválido {dev_raw!r}; esperado S ou N.")

        aceit_raw = _cell(row, 3)
        aceitavel = _parse_sn(aceit_raw)
        if aceitavel is None:
            errors.append(f"{hid} [aceitavel]: valor inválido {aceit_raw!r}; esperado S ou N.")

        abst_raw = _cell(row, 4)
        absteve = _parse_sn(abst_raw)
        if absteve is None:
            errors.append(f"{hid} [absteve]: valor inválido {abst_raw!r}; esperado S ou N.")

        fund_raw = _cell(row, 5)
        fundamentacao = _parse_grade(fund_raw)
        if fundamentacao is None:
            errors.append(f"{hid} [fundamentacao]: valor inválido {fund_raw!r}; esperado inteiro 1..5.")

        parsed[hid] = {
            "rota": rota,
            "deveria_abster": deveria_abster or "",
            "aceitavel": aceitavel or "",
            "absteve": absteve or "",
            "fundamentacao": fundamentacao,
            "comentario": _cell(row, 6),
        }

    for hid in sample_hids:
        if hid not in parsed:
            errors.append(f"{hid} [id]: caso ausente na aba Respostas.")

    return parsed


def _validate_declaration_sheet(
    rows: list[list[str]],
    errors: list[str],
) -> dict[str, Any]:
    if not rows:
        errors.append("Declaração [cabeçalho]: aba vazia.")
        return {}

    first_cols = tuple(_cell(rows[0], i).lower() for i in range(2))
    if first_cols != ("campo", "resposta"):
        errors.append(
            f"Declaração [cabeçalho]: esperado ['Campo', 'Resposta'], encontrado {rows[0][:2]}."
        )

    by_label: dict[str, str] = {}
    for row in rows[1:]:
        label = _cell(row, 0)
        if label:
            by_label[label] = _cell(row, 1)

    raw_values: dict[str, str] = {}
    for key, label in DECLARATION_FIELDS:
        if label not in by_label:
            errors.append(f"Declaração [{key}]: rótulo ausente ({label!r}).")
            raw_values[key] = ""
        else:
            raw_values[key] = by_label[label]

    out: dict[str, Any] = {}
    decl_label_by_key = dict(DECLARATION_FIELDS)
    sn_parsed: dict[str, str | None] = {}
    for key in SN_DECL_KEYS:
        val = _parse_sn(raw_values.get(key, ""))
        if decl_label_by_key[key] in by_label and val is None:
            errors.append(f"Declaração [{key}]: valor inválido {raw_values.get(key, '')!r}; esperado S ou N.")
        sn_parsed[key] = val

    name_auth = sn_parsed.get("name_authorized")
    raw_name = raw_values.get("name", "")
    if name_auth == "S" and not raw_name:
        errors.append("Declaração [name]: campo Nome é obrigatório quando a citação foi autorizada.")

    for key in ("occupation", "part1_start", "part1_end", "part2_end"):
        label = dict(DECLARATION_FIELDS)[key]
        if label in by_label and not raw_values.get(key, ""):
            errors.append(f"Declaração [{key}]: campo obrigatório vazio ({label!r}).")

    hours_label = dict(DECLARATION_FIELDS)["hours"]
    hours_val: float | None = None
    if hours_label in by_label:
        hours_raw = raw_values.get("hours", "").replace(",", ".")
        try:
            parsed_h = float(hours_raw)
        except ValueError:
            parsed_h = -1.0
        if not math.isfinite(parsed_h) or parsed_h <= 0:
            errors.append(f"Declaração [hours]: valor inválido {raw_values.get('hours', '')!r}; esperado número > 0.")
        else:
            hours_val = parsed_h

    if name_auth == "S":
        out["name"] = raw_name
    else:
        out["name"] = None
    out["occupation"] = raw_values.get("occupation", "")
    out["part1_start"] = raw_values.get("part1_start", "")
    out["part1_end"] = raw_values.get("part1_end", "")
    out["part2_end"] = raw_values.get("part2_end", "")
    out["hours"] = hours_val
    out["no_access"] = sn_parsed.get("no_access")
    out["no_discussion"] = sn_parsed.get("no_discussion")
    out["route_before_part2"] = sn_parsed.get("route_before_part2")
    out["name_authorized"] = name_auth
    questions_raw = raw_values.get("questions", "")
    out["questions"] = questions_raw if questions_raw else None
    return out


def import_annotator_xlsx(
    xlsx_path: str | Path,
    out_dir: str | Path,
    sample_dir: str | Path = SAMPLE_DIR,
    omit_name: bool = False,
) -> dict[str, Any]:
    """Validate and convert an external annotator .xlsx into answers.csv, comments.csv and declaration.json."""
    sample_path = Path(sample_dir) / "sample.json"
    if not sample_path.exists():
        raise FileNotFoundError(f"Sample file not found at {sample_path}")
    sample = json.loads(sample_path.read_text(encoding="utf-8"))
    sample_hids = [it["hid"] for it in sample["items"]]

    xlsx_p = Path(xlsx_path)
    workbook = read_xlsx_sheets(xlsx_p)
    errors: list[str] = []

    responses_by_hid: dict[str, dict[str, Any]] = {}
    if "Respostas" not in workbook.sheets:
        errors.append("Respostas: aba 'Respostas' não encontrada na planilha.")
    else:
        responses_by_hid = _validate_responses_sheet(workbook.sheets["Respostas"], sample_hids, errors)

    declaration: dict[str, Any] = {}
    if "Declaração" not in workbook.sheets:
        errors.append("Declaração: aba 'Declaração' não encontrada na planilha.")
    else:
        declaration = _validate_declaration_sheet(workbook.sheets["Declaração"], errors)

    if errors:
        raise AnnotatorImportError(errors)

    if omit_name:
        declaration["name"] = None
    declaration["name_withheld_by_author"] = bool(omit_name)

    xlsx_sha = hashlib.sha256(xlsx_p.read_bytes()).hexdigest()
    declaration["xlsx_sha256"] = xlsx_sha
    declaration["imported_at"] = datetime.now(UTC).isoformat()

    out_p = Path(out_dir)
    out_p.mkdir(parents=True, exist_ok=True)

    answers_path = out_p / "answers.csv"
    with answers_path.open("w", encoding="utf-8", newline="\n") as fh:
        writer = csv.writer(fh, delimiter=";", lineterminator="\n")
        writer.writerow(list(FIELDS))
        for hid in sample_hids:
            row = responses_by_hid[hid]
            writer.writerow([
                hid,
                row["rota"],
                row["deveria_abster"],
                row["aceitavel"],
                row["absteve"],
                str(row["fundamentacao"]),
            ])

    comments_path = out_p / "comments.csv"
    comments_count = 0
    with comments_path.open("w", encoding="utf-8", newline="\n") as fh:
        writer = csv.writer(fh, delimiter=";", lineterminator="\n")
        writer.writerow(["id", "comentario"])
        for hid in sample_hids:
            comment = responses_by_hid[hid]["comentario"]
            if comment:
                writer.writerow([hid, comment])
                comments_count += 1

    declaration_path = out_p / "declaration.json"
    declaration_path.write_text(
        json.dumps(declaration, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    return {
        "n_items": len(sample_hids),
        "comments_count": comments_count,
        "xlsx_sha256": xlsx_sha,
        "out_dir": str(out_p),
    }


def _categorical_rater_metrics(
    items: list[dict[str, str]],
    ans_a: dict[str, dict[str, Any]],
    ans_b: dict[str, dict[str, Any]],
    field: str,
) -> dict[str, Any]:
    pairs = [(it["hid"], it["case_id"], ans_a[it["hid"]][field], ans_b[it["hid"]][field]) for it in items]
    comp = _compare_pair_list(pairs)
    comp["disagreements"] = [
        {"hid": d["hid"], "case_id": d["case_id"], "a": d["human"], "b": d["other"]}
        for d in comp["disagreements"]
    ]
    return comp


def _groundedness_rater_metrics(
    items: list[dict[str, str]],
    ans_a: dict[str, dict[str, Any]],
    ans_b: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    n = len(items)
    pairs = [
        (it["hid"], it["case_id"], int(ans_a[it["hid"]]["fundamentacao"]), int(ans_b[it["hid"]]["fundamentacao"]))
        for it in items
    ]
    exact = sum(1 for _, _, va, vb in pairs if va == vb)
    within_one = sum(1 for _, _, va, vb in pairs if abs(va - vb) <= 1)
    a_mean = math.fsum(va for _, _, va, _ in pairs) / n if n else 0.0
    b_mean = math.fsum(vb for _, _, _, vb in pairs) / n if n else 0.0
    disagreements = [
        {"hid": hid, "case_id": cid, "a": va, "b": vb}
        for hid, cid, va, vb in pairs
        if va != vb
    ]
    return {
        "n": n,
        "exact": exact,
        "exact_rate": exact / n if n else 0.0,
        "within_one": within_one,
        "within_one_rate": within_one / n if n else 0.0,
        "a_mean": a_mean,
        "b_mean": b_mean,
        "a_lower": sum(1 for _, _, va, vb in pairs if va < vb),
        "a_higher": sum(1 for _, _, va, vb in pairs if va > vb),
        "disagreements": disagreements,
    }


def _render_raters_md(report: dict[str, Any]) -> str:
    a_name = report["a"]
    b_name = report["b"]
    fields = report["fields"]
    lines: list[str] = [
        f"# Concordância entre avaliadores ({a_name} × {b_name})",
        "",
        f"- **Itens na amostra:** {report['n_items']}",
        f"- **Avaliador A:** `{a_name}` (`{report['a_sha256'][:12]}`)",
        f"- **Avaliador B:** `{b_name}` (`{report['b_sha256'][:12]}`)",
        "",
        "## Campos categóricos",
        "",
        "| Campo | Concordância | Taxa | IC Wilson 95% | Kappa de Cohen |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ]

    cat_fields = ("rota", "deveria_abster", "aceitavel", "absteve")
    for field in cat_fields:
        m = fields[field]
        ci = (
            f"[{_fmt_pct(m['wilson_low'])}, {_fmt_pct(m['wilson_high'])}]"
            if m["wilson_low"] is not None and m["wilson_high"] is not None
            else "n/a"
        )
        lines.append(f"| `{field}` | {m['agree']}/{m['n']} | {_fmt_pct(m['rate'])} | {ci} | {_fmt_num(m['kappa'])} |")

    g = fields["fundamentacao"]
    lines.extend([
        "",
        "## Nota de fundamentação (`fundamentacao`)",
        "",
        "| Métrica | Valor |",
        "| :--- | :--- |",
        f"| n | {g['n']} |",
        f"| Acordo exato | {g['exact']}/{g['n']} ({_fmt_pct(g['exact_rate'])}) |",
        f"| Diferença ≤ 1 ponto | {g['within_one']}/{g['n']} ({_fmt_pct(g['within_one_rate'])}) |",
        f"| Média ({a_name}) | {_fmt_num(g['a_mean'])} |",
        f"| Média ({b_name}) | {_fmt_num(g['b_mean'])} |",
        f"| {a_name} < {b_name} | {g['a_lower']} |",
        f"| {a_name} > {b_name} | {g['a_higher']} |",
        "",
        "## Divergências",
        "",
    ])

    any_dis = False
    for field in (*cat_fields, "fundamentacao"):
        dis = fields[field]["disagreements"]
        if dis:
            any_dis = True
            lines.append(f"### `{field}` ({len(dis)})")
            lines.append("")
            for d in dis:
                lines.append(f"- `{d['hid']}` (`{d['case_id']}`): {a_name}=`{d['a']}` vs {b_name}=`{d['b']}`")
            lines.append("")
    if not any_dis:
        lines.append("Nenhuma divergência.")
        lines.append("")

    return "\n".join(lines).rstrip("\n") + "\n"


def compare_raters(
    a_path: str | Path,
    b_path: str | Path,
    a_name: str,
    b_name: str,
    out_dir: str | Path,
    sample_dir: str | Path = SAMPLE_DIR,
) -> dict[str, Any]:
    """Compare two annotator answer CSVs on the same sample and write raters.json and raters.md."""
    sample_path = Path(sample_dir) / "sample.json"
    if not sample_path.exists():
        raise FileNotFoundError(f"Sample file not found at {sample_path}")
    sample = json.loads(sample_path.read_text(encoding="utf-8"))
    items = list(sample["items"])
    hids = [it["hid"] for it in items]

    a_p, b_p = Path(a_path), Path(b_path)
    if not a_p.exists():
        raise FileNotFoundError(f"Answers file not found: {a_p}")
    if not b_p.exists():
        raise FileNotFoundError(f"Answers file not found: {b_p}")

    ans_a = parse_answers(a_p, hids)
    ans_b = parse_answers(b_p, hids)

    fields: dict[str, Any] = {
        field: _categorical_rater_metrics(items, ans_a, ans_b, field)
        for field in ("rota", "deveria_abster", "aceitavel", "absteve")
    }
    fields["fundamentacao"] = _groundedness_rater_metrics(items, ans_a, ans_b)

    report = {
        "a": a_name,
        "b": b_name,
        "a_sha256": file_sha256(a_p),
        "b_sha256": file_sha256(b_p),
        "sample_sha256": file_sha256(sample_path),
        "n_items": len(items),
        "fields": fields,
        "generated_at": datetime.now(UTC).isoformat(),
    }

    out_p = Path(out_dir)
    out_p.mkdir(parents=True, exist_ok=True)
    (out_p / "raters.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (out_p / "raters.md").write_text(_render_raters_md(report), encoding="utf-8", newline="\n")
    return report
