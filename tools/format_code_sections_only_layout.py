from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil

from docx import Document
from docx.enum.text import WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt


DOCX = Path(r"D:\迅雷下载\毕业设计正文模板_检测报告\毕业设计正文模板.docx")


STOP_PREFIXES = (
    "代码清单",
    "图",
    "表",
    "第",
    "系统",
    "随后",
    "健康",
    "风机",
    "故障",
    "智能",
    "当用户",
    "参数",
)


def set_run_font(run, name="Consolas", size=8):
    run.font.name = name
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)
    run.font.size = Pt(size)


def set_paragraph_code_format(paragraph):
    fmt = paragraph.paragraph_format
    fmt.left_indent = Cm(0.72)
    fmt.first_line_indent = Pt(0)
    fmt.right_indent = Cm(0)
    fmt.space_before = Pt(0)
    fmt.space_after = Pt(0)
    fmt.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    fmt.line_spacing = Pt(10.5)
    paragraph.alignment = 0
    for run in paragraph.runs:
        set_run_font(run)

    p_pr = paragraph._p.get_or_add_pPr()
    if p_pr.find(qn("w:suppressLineNumbers")) is None:
        p_pr.append(OxmlElement("w:suppressLineNumbers"))


def is_probably_code(text: str) -> bool:
    s = text.strip()
    if not s:
        return False
    if s.startswith(STOP_PREFIXES):
        return False
    code_starts = (
        "def ",
        "async ",
        "const ",
        "let ",
        "return ",
        "if ",
        "for ",
        "await ",
        "document.",
        "@",
        "db.",
        "localStorage.",
        "render",
        "headers:",
        "body:",
        "method:",
        "username:",
        "password:",
        "question:",
        "current_status:",
        "deep_thinking:",
        "answer_mode:",
        "sources:",
        "confidence:",
        "riskLevel:",
        "engine:",
        "delta(",
        "done(",
        "streamedAnswer",
        "});",
        "});",
        "}",
        "});",
        "]);",
        ")",
    )
    return s.startswith(code_starts) or any(ch in s for ch in "{}();=<>[]")


def main():
    backup = DOCX.with_name(
        DOCX.stem + "_仅代码格式修改前备份_" + datetime.now().strftime("%Y%m%d_%H%M%S") + DOCX.suffix
    )
    shutil.copy2(DOCX, backup)

    doc = Document(DOCX)
    in_code = False
    formatted = 0

    for paragraph in doc.paragraphs:
        stripped = paragraph.text.strip()
        if stripped == "核心代码如下：":
            in_code = True
            continue
        if in_code:
            if not stripped:
                in_code = False
                continue
            if stripped.startswith("代码清单") or (
                not is_probably_code(stripped) and len(stripped) > 28
            ):
                in_code = False
                continue
            set_paragraph_code_format(paragraph)
            formatted += 1

    doc.save(DOCX)
    print("backup", backup)
    print("formatted_code_lines", formatted)


if __name__ == "__main__":
    main()
