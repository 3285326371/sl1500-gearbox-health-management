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


def set_run_font(run, name="Consolas", size=8.5):
    run.font.name = name
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)
    run.font.size = Pt(size)


def set_paragraph_code_format(paragraph):
    fmt = paragraph.paragraph_format
    fmt.left_indent = Cm(1.05)
    fmt.first_line_indent = Pt(0)
    fmt.right_indent = Cm(0)
    fmt.space_before = Pt(0)
    fmt.space_after = Pt(0)
    fmt.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    fmt.line_spacing = Pt(11.5)
    paragraph.alignment = 0
    for run in paragraph.runs:
        set_run_font(run)

    p_pr = paragraph._p.get_or_add_pPr()
    # Avoid Word splitting long tokens in odd places when possible.
    if p_pr.find(qn("w:suppressLineNumbers")) is None:
        p_pr.append(OxmlElement("w:suppressLineNumbers"))


def simplify_edge_symbols(line: str) -> str:
    text = line.expandtabs(4).rstrip()
    # Remove optional semicolons and trailing commas where the code is shown as a
    # thesis excerpt rather than a runnable source file.
    if text.strip() in {"}", "};", "});", ");", "},", "]," , "]};"}:
        return ""
    replacements = {
        "    });": "",
        "    })": "",
        "    }": "",
        "        })": "",
        "        },": "",
        "        };": "",
    }
    stripped = text.strip()
    if stripped in replacements:
        return replacements[stripped]

    # Avoid lonely punctuation at the visual line end for object/list excerpt lines.
    if text.endswith(","):
        text = text[:-1]
    if text.endswith(";"):
        text = text[:-1]
    return text


def is_probably_code(text: str) -> bool:
    s = text.strip()
    if not s:
        return False
    if s.startswith(STOP_PREFIXES):
        return False
    code_marks = [
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
    ]
    return any(s.startswith(mark) for mark in code_marks) or any(ch in s for ch in "{}();=<>[]")


def clear_paragraph(paragraph):
    for child in list(paragraph._p):
        paragraph._p.remove(child)


def main():
    backup = DOCX.with_name(
        DOCX.stem + "_代码格式修改前备份_" + datetime.now().strftime("%Y%m%d_%H%M%S") + DOCX.suffix
    )
    shutil.copy2(DOCX, backup)

    doc = Document(DOCX)
    code_count = 0
    edited_lines = 0
    in_code = False

    for i, paragraph in enumerate(doc.paragraphs):
        text = paragraph.text
        stripped = text.strip()

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

            new_text = simplify_edge_symbols(text)
            if new_text == "":
                clear_paragraph(paragraph)
                edited_lines += 1
                continue
            if new_text != text.rstrip():
                paragraph.text = new_text
                edited_lines += 1
            set_paragraph_code_format(paragraph)
            code_count += 1

    doc.save(DOCX)
    print("backup", backup)
    print("code_lines_formatted", code_count)
    print("code_lines_simplified", edited_lines)


if __name__ == "__main__":
    main()
