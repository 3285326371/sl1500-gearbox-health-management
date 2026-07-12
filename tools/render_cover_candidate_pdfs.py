from pathlib import Path

import fitz


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "cover_candidates"

for pdf in OUT.glob("*.pdf"):
    png = OUT / f"{pdf.stem}_page01.png"
    doc = fitz.open(pdf)
    pix = doc[0].get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
    pix.save(png)
    print(png)
