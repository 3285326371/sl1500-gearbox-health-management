from pathlib import Path

import win32com.client


DOCX = Path(r"D:\迅雷下载\毕业设计正文模板_检测报告\毕业设计正文模板.docx")
PDF = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "download_docx_code_format_qa"
    / "毕业设计正文模板_代码格式检查.pdf"
)
PDF.parent.mkdir(parents=True, exist_ok=True)

word = win32com.client.DispatchEx("Word.Application")
word.Visible = False
word.DisplayAlerts = 0
doc = None
try:
    doc = word.Documents.Open(str(DOCX))
    doc.Save()
    doc.ExportAsFixedFormat(str(PDF), 17)
finally:
    if doc is not None:
        try:
            doc.Close(False)
        except Exception:
            pass
    try:
        word.Quit()
    except Exception:
        pass

print(PDF)
