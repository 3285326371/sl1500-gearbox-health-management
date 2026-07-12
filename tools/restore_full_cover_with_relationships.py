from __future__ import annotations

import copy
import re
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET


DESKTOP = Path.home() / "Desktop"
TARGET = next(DESKTOP.glob("*正文模板.docx"))
SOURCE = DESKTOP / "毕业设计正文模板_扩展40页前备份_20260524_200412.docx"

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}
for k, v in NS.items():
    if k != "rel":
        ET.register_namespace(k, v)


def text_of(el):
    return "".join(t.text or "" for t in el.findall(".//w:t", NS))


def find_decl_idx(children):
    for i, child in enumerate(children):
        if "毕业设计原创性声明" in text_of(child):
            return i
    raise RuntimeError("Cannot locate declaration paragraph")


def read_xml(zf, name):
    return ET.fromstring(zf.read(name))


def rels_by_id(root):
    return {rel.get("Id"): rel for rel in root.findall("rel:Relationship", NS)}


def next_rid(existing):
    nums = []
    for rid in existing:
        m = re.match(r"rId(\d+)$", rid or "")
        if m:
            nums.append(int(m.group(1)))
    n = max(nums or [0]) + 1
    while f"rId{n}" in existing:
        n += 1
    return f"rId{n}"


def collect_rids(elements):
    rids = set()
    rel_attrs = {
        f"{{{NS['r']}}}id",
        f"{{{NS['r']}}}embed",
        f"{{{NS['r']}}}link",
    }
    for el in elements:
        for node in el.iter():
            for attr, value in node.attrib.items():
                if attr in rel_attrs:
                    rids.add(value)
    return rids


def remap_rids(elements, mapping):
    rel_attrs = {
        f"{{{NS['r']}}}id",
        f"{{{NS['r']}}}embed",
        f"{{{NS['r']}}}link",
    }
    for el in elements:
        for node in el.iter():
            for attr, value in list(node.attrib.items()):
                if attr in rel_attrs and value in mapping:
                    node.set(attr, mapping[value])


def ext_from_target(target):
    return Path(target).suffix or ".bin"


def main():
    backup = TARGET.with_name(f"{TARGET.stem}_恢复完整封面前备份_{datetime.now():%Y%m%d_%H%M%S}{TARGET.suffix}")
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
    src_children = list(src_body)
    tgt_children = list(tgt_body)
    src_cut = find_decl_idx(src_children)
    tgt_cut = find_decl_idx(tgt_children)
    cover_children = [copy.deepcopy(el) for el in src_children[:src_cut]]

    src_rel_map = rels_by_id(src_rels)
    tgt_rel_map = rels_by_id(tgt_rels)
    existing_ids = set(tgt_rel_map)
    rid_mapping = {}

    for old_rid in sorted(collect_rids(cover_children)):
        src_rel = src_rel_map.get(old_rid)
        if src_rel is None:
            continue
        new_rid = next_rid(existing_ids)
        existing_ids.add(new_rid)
        rid_mapping[old_rid] = new_rid

        rel_type = src_rel.get("Type")
        target = src_rel.get("Target")
        target_mode = src_rel.get("TargetMode")
        new_rel = ET.Element("Relationship")
        new_rel.set("Id", new_rid)
        new_rel.set("Type", rel_type)
        if target and target.startswith("media/"):
            src_part = "word/" + target
            ext = ext_from_target(target)
            new_target = f"media/cover_{old_rid}{ext}"
            tgt_files["word/" + new_target] = src_files[src_part]
            new_rel.set("Target", new_target)
        else:
            new_rel.set("Target", target or "")
        if target_mode:
            new_rel.set("TargetMode", target_mode)
        tgt_rels.append(new_rel)

    remap_rids(cover_children, rid_mapping)

    for child in tgt_children[:tgt_cut]:
        tgt_body.remove(child)
    for i, child in enumerate(cover_children):
        tgt_body.insert(i, child)

    tgt_files["word/document.xml"] = ET.tostring(tgt_doc, encoding="utf-8", xml_declaration=True)
    tgt_files["word/_rels/document.xml.rels"] = ET.tostring(tgt_rels, encoding="utf-8", xml_declaration=True)

    with zipfile.ZipFile(TARGET, "w", zipfile.ZIP_DEFLATED) as out_zip:
        for name, data in tgt_files.items():
            out_zip.writestr(name, data)

    print(f"saved={TARGET}")
    print(f"backup={backup}")
    print(f"source={SOURCE}")


if __name__ == "__main__":
    main()
