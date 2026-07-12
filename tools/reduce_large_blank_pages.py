from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from docx import Document


DOCX = Path.home() / "Desktop" / "\u6bd5\u4e1a\u8bbe\u8ba1\u6b63\u6587\u6a21\u677f.docx"


def main():
    backup = DOCX.with_name(
        f"{DOCX.stem}_减少页面留白前备份_{datetime.now():%Y%m%d_%H%M%S}{DOCX.suffix}"
    )
    shutil.copy2(DOCX, backup)
    doc = Document(DOCX)

    # Keep the first body chapter after the catalog as a clean start, but allow
    # later chapters and back matter to follow the previous page when space permits.
    keep_new_page = {"第1章 绪论"}
    changed = []
    for p in doc.paragraphs:
        text = p.text.strip()
        if p.style.name == "Heading 1" and (
            text.startswith("第") or text in {"参考文献", "致谢"}
        ):
            if text not in keep_new_page:
                p.paragraph_format.page_break_before = False
                changed.append(text)

    doc.save(DOCX)
    print(f"saved={DOCX}")
    print(f"backup={backup}")
    print("changed=" + ",".join(changed))


if __name__ == "__main__":
    main()
