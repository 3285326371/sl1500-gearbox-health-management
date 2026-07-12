from pathlib import Path
from zipfile import ZipFile


DOCX = Path(r"D:\迅雷下载\毕业设计正文模板_检测报告\毕业设计正文模板.docx")

with ZipFile(DOCX) as z:
    settings = z.read("word/settings.xml").decode("utf-8", errors="ignore")
    document = z.read("word/document.xml").decode("utf-8", errors="ignore")
    print("trackRevisions", "w:trackRevisions" in settings)
    print("ins", "<w:ins" in document)
    print("del", "<w:del" in document)
    print("rPrChange", "<w:rPrChange" in document)
    print("pPrChange", "<w:pPrChange" in document)
