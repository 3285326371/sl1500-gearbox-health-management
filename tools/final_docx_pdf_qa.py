from pathlib import Path
import zipfile

import fitz
from docx import Document


ROOT = Path(__file__).resolve().parents[1]
DOCX = Path(r"C:\Users\隐涅\Desktop\毕业设计正文模板_检测报告\毕业设计正文模板.docx")
PDF = ROOT / "docs" / "qa_detection_report" / "final_cover_ai_toc_checked.pdf"
PNG = ROOT / "docs" / "qa_detection_report" / "png_final_cover_ai_toc_checked"


def compact(text: str) -> str:
    return "".join((text or "").split())


PNG.mkdir(parents=True, exist_ok=True)
pdf = fitz.open(PDF)
for i, page in enumerate(pdf):
    pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
    pix.save(PNG / f"page-{i + 1:02d}.png")

print("pdf_pages", len(pdf))
for i, page in enumerate(pdf, start=1):
    text = page.get_text("text")
    c = compact(text)
    hits = []
    for needle in ["第1章绪论", "智能运维诊断助手", "代码清单5.6", "图5.9", "参考文献", "致谢"]:
        if needle in c:
            hits.append(needle)
    if hits:
        print("page", i, ",".join(hits))

doc = Document(DOCX)
for i, para in enumerate(doc.paragraphs):
    t = para.text.strip()
    if any(k in t for k in ["智能运维诊断助手", "代码清单5.6", "图5.9", "毕业设计原创性声明"]):
        print("para", i, para.style.name, t[:100])

with zipfile.ZipFile(DOCX) as zf:
    names = set(zf.namelist())
    xml = zf.read("word/document.xml").decode("utf-8")
    print("comments.xml", "word/comments.xml" in names)
    print("commentRangeStart", "w:commentRangeStart" in xml)
    print("commentReference", "w:commentReference" in xml)

print("png_dir", PNG)
