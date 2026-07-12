from __future__ import annotations

import copy
import re
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET


DESKTOP = Path.home() / "Desktop"
TARGET = DESKTOP / "\u6bd5\u4e1a\u8bbe\u8ba1\u6b63\u6587\u6a21\u677f.docx"
SOURCE = DESKTOP / "\u6bd5\u4e1a\u8bbe\u8ba1\u6b63\u6587\u6a21\u677f_\u6269\u5c5540\u9875\u524d\u5907\u4efd_20260524_200412.docx"

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}
for prefix, uri in NS.items():
    if prefix != "rel":
        ET.register_namespace(prefix, uri)


def text_of(el: ET.Element) -> str:
    return "".join(t.text or "" for t in el.findall(".//w:t", NS))


def read_xml(zf: zipfile.ZipFile, name: str) -> ET.Element:
    return ET.fromstring(zf.read(name))


def find_declaration_index(children: list[ET.Element]) -> int:
    for idx, child in enumerate(children):
        if "\u6bd5\u4e1a\u8bbe\u8ba1\u539f\u521b\u6027\u58f0\u660e" in text_of(child):
            return idx
    raise RuntimeError("Cannot locate declaration paragraph")


def relationship_map(root: ET.Element) -> dict[str, ET.Element]:
    return {rel.get("Id", ""): rel for rel in root.findall("rel:Relationship", NS)}


def next_rid(existing: set[str]) -> str:
    numbers = []
    for rid in existing:
        match = re.fullmatch(r"rId(\d+)", rid or "")
        if match:
            numbers.append(int(match.group(1)))
    candidate = max(numbers or [0]) + 1
    while f"rId{candidate}" in existing:
        candidate += 1
    return f"rId{candidate}"


def collect_relationship_ids(elements: list[ET.Element]) -> set[str]:
    rel_attrs = {
        f"{{{NS['r']}}}id",
        f"{{{NS['r']}}}embed",
        f"{{{NS['r']}}}link",
    }
    ids: set[str] = set()
    for element in elements:
        for node in element.iter():
            for attr, value in node.attrib.items():
                if attr in rel_attrs:
                    ids.add(value)
    return ids


def remap_relationship_ids(elements: list[ET.Element], mapping: dict[str, str]) -> None:
    rel_attrs = {
        f"{{{NS['r']}}}id",
        f"{{{NS['r']}}}embed",
        f"{{{NS['r']}}}link",
    }
    for element in elements:
        for node in element.iter():
            for attr, value in list(node.attrib.items()):
                if attr in rel_attrs and value in mapping:
                    node.set(attr, mapping[value])


def copy_cover() -> None:
    if not TARGET.exists():
        raise FileNotFoundError(TARGET)
    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)

    backup = TARGET.with_name(f"{TARGET.stem}_\u6062\u590d\u5b8c\u6574\u5c01\u9762\u524d\u5907\u4efd_{datetime.now():%Y%m%d_%H%M%S}{TARGET.suffix}")
    shutil.copy2(TARGET, backup)

    with zipfile.ZipFile(SOURCE, "r") as src_zip:
        src_doc = read_xml(src_zip, "word/document.xml")
        src_rels = read_xml(src_zip, "word/_rels/document.xml.rels")
        src_files = {name: src_zip.read(name) for name in src_zip.namelist()}

    with zipfile.ZipFile(TARGET, "r") as tgt_zip:
        tgt_doc = read_xml(tgt_zip, "word/document.xml")
        tgt_rels = read_xml(tgt_zip, "word/_rels/document.xml.rels")
        tgt_files = {name: tgt_zip.read(name) for name in tgt_zip.namelist()}

    src_body = src_doc.find("w:body", NS)
    tgt_body = tgt_doc.find("w:body", NS)
    if src_body is None or tgt_body is None:
        raise RuntimeError("Invalid document body")

    src_children = list(src_body)
    tgt_children = list(tgt_body)
    src_cut = find_declaration_index(src_children)
    tgt_cut = find_declaration_index(tgt_children)
    cover_children = [copy.deepcopy(child) for child in src_children[:src_cut]]

    src_rel_map = relationship_map(src_rels)
    tgt_rel_map = relationship_map(tgt_rels)
    existing_ids = set(tgt_rel_map)
    rid_mapping: dict[str, str] = {}

    for old_rid in sorted(collect_relationship_ids(cover_children)):
        src_rel = src_rel_map.get(old_rid)
        if src_rel is None:
            continue
        new_rid = next_rid(existing_ids)
        existing_ids.add(new_rid)
        rid_mapping[old_rid] = new_rid

        new_rel = ET.Element(f"{{{NS['rel']}}}Relationship")
        new_rel.set("Id", new_rid)
        new_rel.set("Type", src_rel.get("Type", ""))
        target = src_rel.get("Target", "")
        target_mode = src_rel.get("TargetMode")
        if target.startswith("media/"):
            ext = Path(target).suffix or ".bin"
            new_target = f"media/restored_cover_{old_rid}{ext}"
            tgt_files["word/" + new_target] = src_files["word/" + target]
            new_rel.set("Target", new_target)
        else:
            new_rel.set("Target", target)
        if target_mode:
            new_rel.set("TargetMode", target_mode)
        tgt_rels.append(new_rel)

    remap_relationship_ids(cover_children, rid_mapping)

    for child in tgt_children[:tgt_cut]:
        tgt_body.remove(child)
    for idx, child in enumerate(cover_children):
        tgt_body.insert(idx, child)

    tgt_files["word/document.xml"] = ET.tostring(tgt_doc, encoding="utf-8", xml_declaration=True)
    tgt_files["word/_rels/document.xml.rels"] = ET.tostring(tgt_rels, encoding="utf-8", xml_declaration=True)

    with zipfile.ZipFile(TARGET, "w", zipfile.ZIP_DEFLATED) as out_zip:
        for name, data in tgt_files.items():
            out_zip.writestr(name, data)

    print(f"saved={TARGET}")
    print(f"backup={backup}")


if __name__ == "__main__":
    copy_cover()
