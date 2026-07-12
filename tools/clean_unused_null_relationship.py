from __future__ import annotations

import shutil
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


TARGET = Path.home() / "Desktop" / "\u6bd5\u4e1a\u8bbe\u8ba1\u6b63\u6587\u6a21\u677f.docx"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
ET.register_namespace("", REL_NS)


def main() -> None:
    backup = TARGET.with_name(f"{TARGET.stem}_清理空关系前备份{TARGET.suffix}")
    shutil.copy2(TARGET, backup)

    with zipfile.ZipFile(TARGET, "r") as zin:
        files = {name: zin.read(name) for name in zin.namelist()}

    rel_name = "word/_rels/document.xml.rels"
    root = ET.fromstring(files[rel_name])
    removed = 0
    for rel in list(root):
        target = rel.get("Target", "")
        if target in {"../NULL", "NULL"}:
            root.remove(rel)
            removed += 1
    files[rel_name] = ET.tostring(root, encoding="utf-8", xml_declaration=True)

    with zipfile.ZipFile(TARGET, "w", zipfile.ZIP_DEFLATED) as zout:
        for name, data in files.items():
            zout.writestr(name, data)

    print(f"removed={removed}")
    print(f"backup={backup}")


if __name__ == "__main__":
    main()
