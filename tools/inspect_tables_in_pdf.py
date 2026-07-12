from pathlib import Path

import fitz


ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "docs" / "qa_detection_report" / "final_cover_ai_toc_checked.pdf"

doc = fitz.open(PDF)
for i, page in enumerate(doc, start=1):
    text = page.get_text("text")
    lines = [line.strip() for line in text.splitlines() if line.strip().startswith("表")]
    if lines:
        print("page", i)
        for line in lines:
            print(" ", line[:100])
