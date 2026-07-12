from pathlib import Path

from docx import Document


DOCX = max(Path("docs").glob("*开题文献版.docx"), key=lambda p: p.stat().st_mtime)

TOC_LINES = [
    "摘要\tI",
    "ABSTRACT\tII",
    "第1章 绪论\t1",
    "1.1 研究背景与意义\t1",
    "1.2 国内外研究现状\t1",
    "1.3 本文研究内容\t2",
    "1.4 技术路线\t2",
    "第2章 系统需求分析\t3",
    "2.1 业务需求分析\t3",
    "2.2 功能需求分析\t3",
    "2.3 非功能需求分析\t4",
    "2.4 数据需求分析\t4",
    "第3章 相关技术与理论基础\t5",
    "3.1 齿轮箱典型故障机理\t5",
    "3.2 多源状态监测技术\t5",
    "3.3 振动特征提取方法\t5",
    "3.4 风险评分与健康评估方法\t5",
    "3.5 Web系统开发技术\t6",
    "第4章 系统总体设计\t7",
    "4.1 系统架构设计\t7",
    "4.2 数据库设计\t7",
    "4.3 后端接口设计\t7",
    "4.4 诊断流程设计\t8",
    "4.5 前端页面设计\t8",
    "第5章 系统详细实现\t9",
    "5.1 数据采集与融合模块实现\t9",
    "5.2 故障诊断算法模块实现\t9",
    "5.3 风场总览与单机详情实现\t9",
    "5.4 故障代码库与数据管理实现\t10",
    "5.5 AI运维问答模块实现\t10",
    "5.6 健康报告与工单闭环实现\t10",
    "第6章 系统测试与结果分析\t11",
    "6.1 测试环境\t11",
    "6.2 功能测试\t11",
    "6.3 诊断场景测试分析\t11",
    "6.4 结果评价\t12",
    "第7章 总结与展望\t13",
    "参考文献\t14",
    "致谢\t15",
    "附录A 系统主要接口\t16",
]


def main() -> None:
    doc = Document(DOCX)
    paragraphs = doc.paragraphs
    start = next(i for i, p in enumerate(paragraphs) if p.text.strip() == "目  录") + 1
    end = next(i for i in range(start, len(paragraphs)) if paragraphs[i].text.strip() == "第1章 绪论")

    for offset, line in enumerate(TOC_LINES):
        paragraphs[start + offset].text = line

    for i in range(start + len(TOC_LINES), end):
        paragraphs[i].text = ""

    doc.save(DOCX)
    print(DOCX)


if __name__ == "__main__":
    main()
