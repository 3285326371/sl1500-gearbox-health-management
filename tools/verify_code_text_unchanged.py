from pathlib import Path

from docx import Document


CURRENT = Path(r"D:\迅雷下载\毕业设计正文模板_检测报告\毕业设计正文模板.docx")
BACKUP = Path(r"D:\迅雷下载\毕业设计正文模板_检测报告\毕业设计正文模板_仅代码格式修改前备份_20260601_172505.docx")


def all_text(path: Path):
    return [p.text for p in Document(path).paragraphs]


cur = all_text(CURRENT)
old = all_text(BACKUP)
diffs = []
for i, (a, b) in enumerate(zip(cur, old)):
    if a != b:
        diffs.append((i, b, a))
if len(cur) != len(old):
    diffs.append(("paragraph_count", str(len(old)), str(len(cur))))

print("text_diffs", len(diffs))
for item in diffs[:20]:
    print(item)
