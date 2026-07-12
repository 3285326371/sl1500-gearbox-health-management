from __future__ import annotations

import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET


DOCX = Path.home() / "Desktop" / "\u6bd5\u4e1a\u8bbe\u8ba1\u6b63\u6587\u6a21\u677f.docx"

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "v": "urn:schemas-microsoft-com:vml",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
}
for prefix, uri in NS.items():
    ET.register_namespace(prefix, uri)


def text_of(el: ET.Element) -> str:
    return "".join(t.text or "" for t in el.findall(".//w:t", NS))


def remove_children(parent: ET.Element | None, tag: str) -> None:
    if parent is None:
        return
    for child in list(parent):
        if child.tag == tag:
            parent.remove(child)


def main() -> None:
    backup = DOCX.with_name(f"{DOCX.stem}_参考文献底色清理前备份_{datetime.now():%Y%m%d_%H%M%S}{DOCX.suffix}")
    shutil.copy2(DOCX, backup)

    with zipfile.ZipFile(DOCX, "r") as zin:
        files = {name: zin.read(name) for name in zin.namelist()}

    doc_name = "word/document.xml"
    root = ET.fromstring(files[doc_name])
    body = root.find("w:body", NS)
    if body is None:
        raise RuntimeError("No document body")

    children = list(body)
    in_refs = False
    cleared = 0
    for el in children:
        txt = text_of(el).strip()
        if txt == "参考文献":
            in_refs = True
        if in_refs:
            ppr = el.find("w:pPr", NS)
            if ppr is not None:
                remove_children(ppr, f"{{{NS['w']}}}shd")
                remove_children(ppr, f"{{{NS['w']}}}highlight")
                cleared += 1
            for rpr in el.findall(".//w:rPr", NS):
                remove_children(rpr, f"{{{NS['w']}}}shd")
                remove_children(rpr, f"{{{NS['w']}}}highlight")
                remove_children(rpr, f"{{{NS['w']}}}color")
                cleared += 1
        if in_refs and txt == "致谢":
            break

    # Remove document-level page background if present.
    for bg in root.findall("w:background", NS):
        root.remove(bg)
        cleared += 1

    files[doc_name] = ET.tostring(root, encoding="utf-8", xml_declaration=True)

    with zipfile.ZipFile(DOCX, "w", zipfile.ZIP_DEFLATED) as zout:
        for name, data in files.items():
            zout.writestr(name, data)

    print(f"saved={DOCX}")
    print(f"backup={backup}")
    print(f"cleared={cleared}")


if __name__ == "__main__":
    main()
