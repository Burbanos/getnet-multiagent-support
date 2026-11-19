"""Offline tests for the --omit-name option in human-import."""
from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from pathlib import Path

from src.eval.annotator import import_annotator_xlsx

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


def _build_xlsx(path: Path, *, authorized: str, annotator_name: str = "Fulano Teste") -> None:
    sample = json.loads(Path("reports/human_validation/sample.json").read_text(encoding="utf-8"))
    hids = [it["hid"] for it in sample["items"]]

    resp_rows: list[list[object]] = [["id", "rota", "deveria_abster", "aceitavel", "absteve", "fundamentacao", "comentario"]]
    for hid in hids:
        resp_rows.append([hid, "conhecimento", "N", "S", "N", 5, ""])
    decl_vals: list[object] = [
        annotator_name,
        "Tecnologia da Informação",
        "2026-11-20 10:00",
        "2026-11-20 11:00",
        "2026-11-20 12:00",
        2.0,
        "S",
        "S",
        "S",
        authorized,
        "",
    ]
    decl_rows = [["Campo", "Resposta"]] + [[lbl, val] for lbl, val in zip(DECL_LABELS, decl_vals)]
    sheets = {"Respostas": resp_rows, "Declaração": decl_rows}

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


def test_human_import_omit_name_withholds_authorized_name_via_cli(tmp_path: Path) -> None:
    xlsx = tmp_path / "authorized.xlsx"
    _build_xlsx(xlsx, authorized="S", annotator_name="Anotador Privado")
    out_omit = tmp_path / "out_omit"

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.eval",
            "human-import",
            "--xlsx",
            str(xlsx),
            "--out-dir",
            str(out_omit),
            "--omit-name",
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert proc.returncode == 0, proc.stderr

    decl = json.loads((out_omit / "declaration.json").read_text(encoding="utf-8"))
    assert decl["name"] is None
    assert decl["name_withheld_by_author"] is True
    assert decl["name_authorized"] == "S"

    combined = "".join(p.read_text(encoding="utf-8") for p in out_omit.iterdir() if p.is_file())
    assert "Anotador Privado" not in combined


def test_human_import_without_omit_name_keeps_authorized_name_and_records_false(tmp_path: Path) -> None:
    xlsx_yes = tmp_path / "auth_yes.xlsx"
    xlsx_no = tmp_path / "auth_no.xlsx"
    _build_xlsx(xlsx_yes, authorized="S", annotator_name="Anotador Visível")
    _build_xlsx(xlsx_no, authorized="N", annotator_name="Anotador Oculto")

    out_yes = tmp_path / "out_yes"
    out_no = tmp_path / "out_no"
    import_annotator_xlsx(xlsx_yes, out_yes)
    import_annotator_xlsx(xlsx_no, out_no)

    decl_yes = json.loads((out_yes / "declaration.json").read_text(encoding="utf-8"))
    assert decl_yes["name"] == "Anotador Visível"
    assert decl_yes["name_withheld_by_author"] is False
    assert decl_yes["name_authorized"] == "S"

    decl_no = json.loads((out_no / "declaration.json").read_text(encoding="utf-8"))
    assert decl_no["name"] is None
    assert decl_no["name_withheld_by_author"] is False
    assert decl_no["name_authorized"] == "N"
