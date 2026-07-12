from pathlib import Path

import win32com.client


DOCX = Path(r"C:\Users\隐涅\Desktop\毕业设计正文模板_检测报告\毕业设计正文模板.docx")
PDF = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "qa_detection_report"
    / "final_cover_ai_toc_checked.pdf"
)
PDF.parent.mkdir(parents=True, exist_ok=True)

word = win32com.client.DispatchEx("Word.Application")
word.Visible = False
word.DisplayAlerts = 0
doc = None
try:
    doc = word.Documents.Open(str(DOCX))
    doc.Save()
    doc.ExportAsFixedFormat(
        OutputFileName=str(PDF),
        ExportFormat=17,
        OpenAfterExport=False,
        OptimizeFor=0,
        Range=0,
        Item=0,
        IncludeDocProps=True,
        KeepIRM=True,
        CreateBookmarks=1,
        DocStructureTags=True,
        BitmapMissingFonts=True,
        UseISO19005_1=False,
    )
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
