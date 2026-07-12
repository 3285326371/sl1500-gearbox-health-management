from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def set_cell_border(cell, top=None, bottom=None, left=None, right=None):
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_borders = tc_pr.first_child_found_in("w:tcBorders")
    if tc_borders is None:
        tc_borders = OxmlElement("w:tcBorders")
        tc_pr.append(tc_borders)
    values = {"top": top, "bottom": bottom, "left": left, "right": right}
    for edge, spec in values.items():
        tag = "w:" + edge
        element = tc_borders.find(qn(tag))
        if element is None:
            element = OxmlElement(tag)
            tc_borders.append(element)
        if spec is None:
            spec = {"val": "nil"}
        for key, value in spec.items():
            element.set(qn("w:" + key), str(value))


def remove_shading(cell):
    tc_pr = cell._tc.get_or_add_tcPr()
    for shd in list(tc_pr.findall(qn("w:shd"))):
        tc_pr.remove(shd)


def apply_three_line(table):
    thick = {"val": "single", "sz": "12", "color": "000000"}
    thin = {"val": "single", "sz": "6", "color": "000000"}
    nil = {"val": "nil"}
    rows = list(table.rows)
    if not rows:
        return
    last = len(rows) - 1
    for r_idx, row in enumerate(rows):
        for cell in row.cells:
            remove_shading(cell)
            set_cell_border(cell, top=nil, bottom=nil, left=nil, right=nil)
            if r_idx == 0:
                set_cell_border(cell, top=thick, bottom=thin, left=nil, right=nil)
            elif r_idx == last:
                set_cell_border(cell, top=nil, bottom=thick, left=nil, right=nil)


def main():
    candidates = [
        p for p in DOCS.glob("*毕业论文*.docx")
        if not p.name.startswith("~$") and "三线表" not in p.stem
    ]
    source = max(candidates, key=lambda p: p.stat().st_mtime)
    out = source.with_name(source.stem + "_三线表.docx")
    doc = Document(source)
    for table in doc.tables:
        apply_three_line(table)
    doc.save(out)
    print(out)


if __name__ == "__main__":
    main()
