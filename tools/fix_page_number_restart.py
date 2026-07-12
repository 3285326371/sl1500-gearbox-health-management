from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn


DOCX = (
    Path.home()
    / "Desktop"
    / "\u6bd5\u4e1a\u8bbe\u8ba1\u6b63\u6587\u6a21\u677f_\u68c0\u6d4b\u62a5\u544a"
    / "\u6bd5\u4e1a\u8bbe\u8ba1\u6b63\u6587\u6a21\u677f.docx"
)


def set_page_number_start(section, start: int):
    sect_pr = section._sectPr
    pg_num_type = sect_pr.find(qn("w:pgNumType"))
    if pg_num_type is None:
        pg_num_type = OxmlElement("w:pgNumType")
        # Keep pgNumType before sectPr children that Word usually expects near
        # the end; appending is accepted by Word and preserves other settings.
        sect_pr.append(pg_num_type)
    pg_num_type.set(qn("w:start"), str(start))
    pg_num_type.set(qn("w:fmt"), "decimal")


def main():
    backup = DOCX.with_name(
        f"{DOCX.stem}_页码起始值修改前备份_{datetime.now():%Y%m%d_%H%M%S}{DOCX.suffix}"
    )
    shutil.copy2(DOCX, backup)
    doc = Document(DOCX)

    if len(doc.sections) >= 1:
        # Cover page has no displayed footer, so start from 0; the declaration
        # page then displays 1.
        set_page_number_start(doc.sections[0], 0)
    if len(doc.sections) >= 2:
        # Body page numbers should match the static catalog: Chapter 1 starts at 1.
        set_page_number_start(doc.sections[1], 1)

    doc.save(DOCX)
    print(f"saved={DOCX}")
    print(f"backup={backup}")


if __name__ == "__main__":
    main()
