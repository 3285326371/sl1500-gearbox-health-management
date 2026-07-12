from pathlib import Path

import win32com.client


DOCX = Path(r"C:\Users\隐涅\Desktop\毕业设计正文模板_检测报告\毕业设计正文模板.docx")
TARGETS = [
    "华锐 SL1500 型双馈式风机齿轮箱",
    "智能健康管理体系",
]


word = win32com.client.DispatchEx("Word.Application")
word.Visible = False
word.DisplayAlerts = 0
doc = None
try:
    doc = word.Documents.Open(str(DOCX))
    for text in TARGETS:
        rng = doc.Range(0, min(doc.Content.End, 5000))
        f = rng.Find
        f.ClearFormatting()
        f.Text = text
        f.Forward = True
        f.Wrap = 0
        while f.Execute():
            rng.Font.Underline = 0
            rng.Font.Bold = False
            rng.Font.NameFarEast = "黑体"
            rng.Font.Name = "Arial"
            rng.Font.Size = 20
            break
    doc.Save()
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

print("cover underline removed")
