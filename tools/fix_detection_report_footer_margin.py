from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from docx import Document
from docx.shared import Cm


DOCX = (
    Path.home()
    / "Desktop"
    / "\u6bd5\u4e1a\u8bbe\u8ba1\u6b63\u6587\u6a21\u677f_\u68c0\u6d4b\u62a5\u544a"
    / "\u6bd5\u4e1a\u8bbe\u8ba1\u6b63\u6587\u6a21\u677f.docx"
)


def main():
    backup = DOCX.with_name(
        f"{DOCX.stem}_页脚边距修改前备份_{datetime.now():%Y%m%d_%H%M%S}{DOCX.suffix}"
    )
    shutil.copy2(DOCX, backup)

    doc = Document(DOCX)
    for section in doc.sections:
        section.footer_distance = Cm(1.75)

    doc.save(DOCX)
    print(f"saved={DOCX}")
    print(f"backup={backup}")
    for i, section in enumerate(doc.sections, 1):
        print(i, round(section.footer_distance.cm, 2))


if __name__ == "__main__":
    main()
