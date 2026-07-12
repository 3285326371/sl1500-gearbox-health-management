from pathlib import Path

from docx import Document


DOCX = Path(r"C:\Users\隐涅\Desktop\毕业设计正文模板_检测报告\毕业设计正文模板.docx")

doc = Document(DOCX)
for paragraph in doc.paragraphs[:40]:
    if "毕业设计原创性声明" in paragraph.text:
        paragraph.text = "毕业设计原创性声明"
        break
doc.save(DOCX)
print("fixed declaration title only")
