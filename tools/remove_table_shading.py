from pathlib import Path

from docx import Document
from docx.oxml.ns import qn


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def remove_shading(doc):
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                tc_pr = cell._tc.get_or_add_tcPr()
                for shd in list(tc_pr.findall(qn("w:shd"))):
                    tc_pr.remove(shd)


def main():
    candidates = [
        p for p in DOCS.glob("*毕业论文*.docx")
        if not p.name.startswith("~$") and "无底纹" not in p.stem
    ]
    source = max(candidates, key=lambda p: p.stat().st_mtime)
    out = source.with_name(source.stem + "_无底纹.docx")
    doc = Document(source)
    remove_shading(doc)
    doc.save(out)
    print(out)


if __name__ == "__main__":
    main()
