"""Offline unit tests for standard-library .xlsx annotator import."""
from __future__ import annotations

import csv
import io
import json
import zipfile
from pathlib import Path

import pytest

from src.eval.annotator import AnnotatorImportError, import_annotator_xlsx
from src.eval.human_validation import parse_answers

DECL_LABELS = [
    "Nome",
    "Ocupação / área",
    "Data e hora de início da Parte 1",
    "Data e hora de término da Parte 1",
    "Data e hora de término da Parte 2",
    "Tempo total aproximado (horas)",
    "Não tive acesso ao repositório do projeto, aos rótulos, às notas do juiz nem às respostas do autor (S/N)",
    "Não conversei sobre os casos com o autor ou outra pessoa antes de entregar (S/N)",
    "Preenchi a coluna rota dos 30 casos antes de abrir a Parte 2 (S/N)",
    "Autorizo citar meu nome no relatório (S/N)",
    "Dúvidas sobre as instruções que perguntei ao autor (texto)",
]


def _col_letter(i: int) -> str:
    s = ""
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def _esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _write_xlsx(path: Path, sheets: dict[str, list[list[object]]], *, inline: bool = False) -> None:
    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    rns = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    shared: list[str] = []

    def sst(text: str) -> int:
        if text not in shared:
            shared.append(text)
        return shared.index(text)

    sheet_xml: list[str] = []
    for rows in sheets.values():
        out_rows: list[str] = []
        for ri, row in enumerate(rows, start=1):
            cells: list[str] = []
            for ci, val in enumerate(row, start=1):
                if val is None or val == "":
                    continue
                ref = f"{_col_letter(ci)}{ri}"
                if isinstance(val, (int, float)) and not isinstance(val, bool):
                    cells.append(f'<c r="{ref}"><v>{val}</v></c>')
                elif inline:
                    cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{_esc(str(val))}</t></is></c>')
                else:
                    cells.append(f'<c r="{ref}" t="s"><v>{sst(str(val))}</v></c>')
            out_rows.append(f'<row r="{ri}">{"".join(cells)}</row>')
        sheet_xml.append(
            f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<worksheet xmlns="{ns}"><sheetData>{"".join(out_rows)}</sheetData></worksheet>'
        )

    names = list(sheets)
    wb = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="{ns}" xmlns:r="{rns}"><sheets>'
        + "".join(f'<sheet name="{_esc(n)}" sheetId="{i}" r:id="rId{i}"/>' for i, n in enumerate(names, start=1))
        + "</sheets></workbook>"
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        + "".join(
            f'<Relationship Id="rId{i}" Type="{rns}/worksheet" Target="worksheets/sheet{i}.xml"/>'
            for i in range(1, len(names) + 1)
        )
        + f'<Relationship Id="rId{len(names) + 1}" Type="{rns}/sharedStrings" Target="sharedStrings.xml"/>'
        + "</Relationships>"
    )
    sst_xml = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<sst xmlns="{ns}" count="{len(shared)}" uniqueCount="{len(shared)}">'
        + "".join(f"<si><t>{_esc(s)}</t></si>" for s in shared)
        + "</sst>"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("xl/workbook.xml", wb)
        zf.writestr("xl/_rels/workbook.xml.rels", rels)
        zf.writestr("xl/sharedStrings.xml", sst_xml)
        for i, x in enumerate(sheet_xml, start=1):
            zf.writestr(f"xl/worksheets/sheet{i}.xml", x)


def _sample_hids() -> list[str]:
    sample = json.loads(Path("reports/human_validation/sample.json").read_text(encoding="utf-8"))
    return [it["hid"] for it in sample["items"]]


def _base_sheets(*, name_auth: str = "N", grade_override: object = 5) -> dict[str, list[list[object]]]:
    hids = _sample_hids()
    rows: list[list[object]] = [["id", "rota", "deveria_abster", "aceitavel", "absteve", "fundamentacao", "comentario"]]
    for idx, hid in enumerate(hids):
        grade: object = grade_override if idx == 0 else (4.0 if idx == 1 else 5)
        comment = "Primeira observação; inclui ponto e vírgula" if idx == 2 else ""
        rows.append([hid, "CONHECIMENTO" if idx == 0 else "conta", "s", "S", "N", grade, comment])
    rows.append([])
    rows.append(["Instrução final: ignore esta linha."])
    decl_vals: list[object] = [
        "Maria Teste",
        "Engenheira de dados",
        "2026-11-20 09:00",
        "2026-11-20 10:15",
        "2026-11-20 12:30",
        3.5,
        "S",
        "S",
        "S",
        name_auth,
        "",
    ]
    decl = [["Campo", "Resposta"]] + [[lbl, val] for lbl, val in zip(DECL_LABELS, decl_vals)]
    return {"Respostas": rows, "Declaração": decl}


def test_import_shared_inline_and_numeric_cells(tmp_path: Path) -> None:
    xlsx_shared = tmp_path / "shared.xlsx"
    xlsx_inline = tmp_path / "inline.xlsx"
    _write_xlsx(xlsx_shared, _base_sheets(grade_override=5), inline=False)
    _write_xlsx(xlsx_inline, _base_sheets(grade_override=5.0), inline=True)

    out_s = tmp_path / "out_s"
    out_i = tmp_path / "out_i"
    import_annotator_xlsx(xlsx_shared, out_s)
    import_annotator_xlsx(xlsx_inline, out_i)

    ans_s = (out_s / "answers.csv").read_text(encoding="utf-8")
    ans_i = (out_i / "answers.csv").read_text(encoding="utf-8")
    assert ans_s == ans_i
    assert "\r\n" not in ans_s
    assert ans_s.splitlines()[0] == "id;rota;deveria_abster;aceitavel;absteve;fundamentacao"
    parsed = parse_answers(out_s / "answers.csv", _sample_hids())
    assert len(parsed) == 30
    assert parsed["h01"]["rota"] == "conhecimento"
    assert parsed["h02"]["fundamentacao"] == 4


def test_import_preserves_comments_with_semicolon(tmp_path: Path) -> None:
    xlsx = tmp_path / "comments.xlsx"
    _write_xlsx(xlsx, _base_sheets())
    out = tmp_path / "out"
    import_annotator_xlsx(xlsx, out)

    rows = list(csv.reader(io.StringIO((out / "comments.csv").read_text(encoding="utf-8")), delimiter=";"))
    assert rows == [
        ["id", "comentario"],
        ["h03", "Primeira observação; inclui ponto e vírgula"],
    ]


def test_import_omits_or_includes_name_based_on_authorization(tmp_path: Path) -> None:
    xlsx_no = tmp_path / "no_auth.xlsx"
    xlsx_yes = tmp_path / "yes_auth.xlsx"
    _write_xlsx(xlsx_no, _base_sheets(name_auth="N"))
    _write_xlsx(xlsx_yes, _base_sheets(name_auth="S"))

    out_no = tmp_path / "out_no"
    out_yes = tmp_path / "out_yes"
    import_annotator_xlsx(xlsx_no, out_no)
    import_annotator_xlsx(xlsx_yes, out_yes)

    all_no_text = "".join(p.read_text(encoding="utf-8") for p in out_no.iterdir())
    assert "Maria Teste" not in all_no_text
    decl_no = json.loads((out_no / "declaration.json").read_text(encoding="utf-8"))
    decl_yes = json.loads((out_yes / "declaration.json").read_text(encoding="utf-8"))
    assert decl_no["name"] is None
    assert decl_no["questions"] is None
    assert decl_yes["name"] == "Maria Teste"


def test_import_validation_error_lists_all_problems_and_writes_nothing(tmp_path: Path) -> None:
    sheets = _base_sheets()
    # Break h07 (invalid grade) and h12 (invalid route) and drop a declaration field
    sheets["Respostas"][7][5] = 3.5
    sheets["Respostas"][12][1] = "desconhecido"
    sheets["Declaração"].pop()

    xlsx = tmp_path / "bad.xlsx"
    _write_xlsx(xlsx, sheets)
    out = tmp_path / "out_bad"

    with pytest.raises(AnnotatorImportError) as exc_info:
        import_annotator_xlsx(xlsx, out)

    msg = str(exc_info.value)
    assert "h07" in msg and "fundamentacao" in msg
    assert "h12" in msg and "rota" in msg
    assert "Declaração" in msg and "questions" in msg
    assert not out.exists()


def test_import_rejects_wrong_response_header(tmp_path: Path) -> None:
    sheets = _base_sheets()
    sheets["Respostas"][0] = ["id", "rota_errada", "deveria_abster", "aceitavel", "absteve", "fundamentacao", "comentario"]
    xlsx = tmp_path / "bad_header.xlsx"
    _write_xlsx(xlsx, sheets)
    out = tmp_path / "out_hdr"

    with pytest.raises(AnnotatorImportError, match="cabeçalho"):
        import_annotator_xlsx(xlsx, out)
    assert not out.exists()


def test_import_ignores_non_sample_ids_and_extra_rows(tmp_path: Path) -> None:
    sheets = _base_sheets()
    sheets["Respostas"].insert(5, ["h99", "invalido", "X", "Y", "Z", 99, "ignorar"])
    xlsx = tmp_path / "extra_ids.xlsx"
    _write_xlsx(xlsx, sheets)
    out = tmp_path / "out_extra"

    res = import_annotator_xlsx(xlsx, out)
    assert res["n_items"] == 30
    parsed = parse_answers(out / "answers.csv", _sample_hids())
    assert "h99" not in parsed and len(parsed) == 30
