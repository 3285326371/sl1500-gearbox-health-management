from pathlib import Path
import win32com.client


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "cover_candidates"
OUT.mkdir(parents=True, exist_ok=True)

CANDIDATES = {
    "current": Path(r"C:\Users\隐涅\Desktop\毕业设计正文模板_检测报告\毕业设计正文模板.docx"),
    "desktop_0526": Path(r"C:\Users\隐涅\Desktop\毕业设计正文模板.docx"),
    "backup_0520": Path(r"C:\Users\隐涅\Desktop\毕业设计正文模板_修改前备份_20260520_180331.docx"),
    "case_0524": Path(r"C:\Users\隐涅\Desktop\侯有朔毕业设计修改10.docx"),
}


def export_pdf(docx: Path, pdf: Path):
    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    doc = None
    try:
        doc = word.Documents.Open(str(docx))
        doc.ExportAsFixedFormat(str(pdf), 17)
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


for name, docx in CANDIDATES.items():
    if not docx.exists():
        print("missing", name, docx)
        continue
    pdf = OUT / f"{name}.pdf"
    png = OUT / f"{name}_page01.png"
    export_pdf(docx, pdf)
    print(name, png)
