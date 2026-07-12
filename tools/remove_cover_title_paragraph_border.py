from pathlib import Path

from docx import Document
from docx.oxml.ns import qn


DOCX = Path(r"C:\Users\隐涅\Desktop\毕业设计正文模板_检测报告\毕业设计正文模板.docx")

doc = Document(DOCX)
for paragraph in doc.paragraphs[:40]:
    if "华锐 SL1500" in paragraph.text:
        p_pr = paragraph._p.get_or_add_pPr()
        for tag in ("w:pBdr", "w:ind", "w:shd"):
            for child in list(p_pr.findall(qn(tag))):
                p_pr.remove(child)
        for run in paragraph.runs:
            run.font.underline = False
        break

doc.save(DOCX)
print("removed cover title paragraph border")
