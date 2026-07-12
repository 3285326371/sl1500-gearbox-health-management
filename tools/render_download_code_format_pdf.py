from pathlib import Path

import fitz


ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "docs" / "download_docx_code_format_qa" / "毕业设计正文模板_代码格式检查.pdf"
OUT = ROOT / "docs" / "download_docx_code_format_qa" / "png"
OUT.mkdir(parents=True, exist_ok=True)

doc = fitz.open(PDF)
for i, page in enumerate(doc, start=1):
    pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
    pix.save(OUT / f"page-{i:02d}.png")
    text = page.get_text("text")
    if "代码清单" in text or "核心代码如下" in text:
        print("code_page", i)
print("pages", len(doc), OUT)
