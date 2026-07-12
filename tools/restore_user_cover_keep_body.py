from pathlib import Path

import win32com.client


TARGET = Path(r"C:\Users\隐涅\Desktop\毕业设计正文模板_检测报告\毕业设计正文模板.docx")
SOURCE = Path(r"C:\Users\隐涅\Desktop\毕业设计正文模板_检测报告\毕业设计正文模板_表格不跨页修改前备份_20260529_223928.docx")


def find_start(doc, text: str):
    rng = doc.Content
    find = rng.Find
    find.ClearFormatting()
    find.Text = text
    find.Forward = True
    find.Wrap = 0
    if not find.Execute():
        raise RuntimeError(f"Cannot find marker: {text}")
    return rng.Start


word = win32com.client.DispatchEx("Word.Application")
word.Visible = False
word.DisplayAlerts = 0
src = None
dst = None
try:
    src = word.Documents.Open(str(SOURCE))
    dst = word.Documents.Open(str(TARGET))
    src_marker = find_start(src, "毕业设计原创性声明")
    dst_marker = find_start(dst, "毕业设计原创性声明")
    dst.Range(dst.Content.Start, dst_marker).FormattedText = src.Range(src.Content.Start, src_marker).FormattedText
    dst.Save()
finally:
    for doc in (src, dst):
        if doc is not None:
            try:
                doc.Close(False)
            except Exception:
                pass
    try:
        word.Quit()
    except Exception:
        pass

print("restored user cover; body preserved")
