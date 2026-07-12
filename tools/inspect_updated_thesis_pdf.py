from pathlib import Path

import fitz


ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "docs" / "qa_detection_report" / "cover_ai_update_pass1.pdf"


def norm(s: str) -> str:
    return "".join(s.split())


doc = fitz.open(PDF)
needles = [
    "智能运维诊断助手",
    "代码清单5.6",
    "图5.9",
    "第1章 绪论",
    "参考文献",
    "致谢",
]

for i, page in enumerate(doc, start=1):
    text = page.get_text("text")
    compact = norm(text)
    hits = [n for n in needles if norm(n) in compact]
    if hits:
        print(f"page {i}: {', '.join(hits)}")
        for line in text.splitlines():
            if any(norm(n) in norm(line) for n in hits):
                print("  ", line[:120])
