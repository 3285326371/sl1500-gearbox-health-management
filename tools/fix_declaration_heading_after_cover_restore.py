from pathlib import Path

from docx import Document


DOCX = Path(r"C:\Users\隐涅\Desktop\毕业设计正文模板_检测报告\毕业设计正文模板.docx")

doc = Document(DOCX)
changed = False
for paragraph in doc.paragraphs:
    if "毕业设毕业设计原创性声明" in paragraph.text:
        for run in paragraph.runs:
            if "毕业设毕业设计原创性声明" in run.text:
                run.text = run.text.replace("毕业设毕业设计原创性声明", "毕业设计原创性声明")
                changed = True
        if not changed:
            paragraph.text = paragraph.text.replace("毕业设毕业设计原创性声明", "毕业设计原创性声明")
            changed = True

if changed:
    doc.save(DOCX)
print("changed", changed)
