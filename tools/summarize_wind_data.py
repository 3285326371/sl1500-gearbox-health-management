from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

import xlrd


def turbine_id(name: str) -> str:
    match = re.search(r"#(\d+)", name)
    return f"WTG-{int(match.group(1)):03d}" if match else name


def to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def to_dt(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y-%m-%d %H:%M:%S.%f"):
            try:
                return datetime.strptime(value.strip(), fmt)
            except ValueError:
                pass
    return None


def read_sheet(path: Path):
    book = xlrd.open_workbook(str(path), on_demand=True)
    sheet = book.sheet_by_index(0)
    headers = [str(sheet.cell_value(0, c)).strip().replace("\r\n", "") for c in range(sheet.ncols)]
    return book, sheet, headers


def summarize_realtime(path: Path):
    book, sheet, headers = read_sheet(path)
    indexes = {name: idx for idx, name in enumerate(headers)}
    numeric_names = ["发电机转速", "有功功率", "叶片1角度", "叶片2角度", "叶片3角度", "齿轮箱油温", "齿轮箱加热", "机舱位置"]
    sums = {name: 0.0 for name in numeric_names if name in indexes}
    counts = {name: 0 for name in numeric_names if name in indexes}
    mins = {}
    maxs = {}
    first_time = None
    last_time = None
    sample_last = {}

    for r in range(1, sheet.nrows):
        raw_time = sheet.cell_value(r, indexes.get("日期", 1))
        dt = to_dt(raw_time)
        if dt:
            first_time = dt if first_time is None or dt < first_time else first_time
            last_time = dt if last_time is None or dt > last_time else last_time
        for name, c in indexes.items():
            if name in sums:
                value = to_float(sheet.cell_value(r, c))
                if value is None:
                    continue
                sums[name] += value
                counts[name] += 1
                mins[name] = value if name not in mins else min(mins[name], value)
                maxs[name] = value if name not in maxs else max(maxs[name], value)

    if sheet.nrows > 1:
        last_row = sheet.nrows - 1
        sample_last = {
            headers[c]: sheet.cell_value(last_row, c)
            for c in range(min(sheet.ncols, 9))
        }

    book.release_resources()
    return {
        "turbine": turbine_id(path.name),
        "file": path.name,
        "rows": sheet.nrows - 1,
        "columns": headers,
        "start": first_time.strftime("%Y-%m-%d %H:%M:%S") if first_time else "",
        "end": last_time.strftime("%Y-%m-%d %H:%M:%S") if last_time else "",
        "avg": {name: round(sums[name] / counts[name], 3) for name in sums if counts[name]},
        "min": {name: round(mins[name], 3) for name in mins},
        "max": {name: round(maxs[name], 3) for name in maxs},
        "last": sample_last,
    }


def summarize_fault_stats(path: Path):
    book, sheet, headers = read_sheet(path)
    total = 0
    days = 0
    max_day = {"date": "", "count": 0}
    for r in range(1, sheet.nrows):
        count = to_float(sheet.cell_value(r, 2)) or 0
        total += int(count)
        days += 1
        if count > max_day["count"]:
            max_day = {"date": str(sheet.cell_value(r, 1)), "count": int(count)}
    book.release_resources()
    return {
        "turbine": turbine_id(path.name),
        "file": path.name,
        "days": days,
        "fault_count": total,
        "peak_day": max_day,
    }


def summarize_fault_info(path: Path):
    book, sheet, headers = read_sheet(path)
    code_counter = Counter()
    first_time = None
    last_time = None
    for r in range(1, sheet.nrows):
        dt = to_dt(sheet.cell_value(r, 2))
        if dt:
            first_time = dt if first_time is None or dt < first_time else first_time
            last_time = dt if last_time is None or dt > last_time else last_time
        for c in range(4, min(sheet.ncols, 17)):
            value = str(sheet.cell_value(r, c)).strip()
            if value and value not in {"0", "0.0"}:
                code_counter[value] += 1
    book.release_resources()
    return {
        "turbine": turbine_id(path.name),
        "file": path.name,
        "records": sheet.nrows - 1,
        "start": first_time.strftime("%Y-%m-%d %H:%M:%S") if first_time else "",
        "end": last_time.strftime("%Y-%m-%d %H:%M:%S") if last_time else "",
        "top_codes": code_counter.most_common(8),
    }


def main():
    cwd = Path.cwd()
    data_dir = next(p for p in cwd.iterdir() if p.is_dir() and p.name == "\u98ce\u673a\u6570\u636e")
    report = {
        "data_dir": str(data_dir),
        "free_report": None,
        "realtime": [],
        "fault_stats": [],
        "fault_info": [],
    }

    free_files = sorted(data_dir.glob("*.xls"), key=lambda p: p.name)
    if free_files:
        book, sheet, headers = read_sheet(free_files[0])
        report["free_report"] = {
            "file": free_files[0].name,
            "rows": sheet.nrows - 1,
            "columns": headers,
            "sample": [
                [sheet.cell_value(r, c) for c in range(sheet.ncols)]
                for r in range(1, min(sheet.nrows, 6))
            ],
            "records": [
                [sheet.cell_value(r, c) for c in range(sheet.ncols)]
                for r in range(1, sheet.nrows)
            ],
        }
        book.release_resources()

    for path in sorted((data_dir / "\u98ce\u673a\u5b9e\u65f6\u6570\u636e").glob("*.xls"), key=lambda p: p.name):
        report["realtime"].append(summarize_realtime(path))
    for path in sorted((data_dir / "\u6545\u969c\u7edf\u8ba1").glob("*.xls"), key=lambda p: p.name):
        report["fault_stats"].append(summarize_fault_stats(path))
    for path in sorted((data_dir / "\u6545\u969c\u4fe1\u606f\u7edf\u8ba1").glob("*.xls"), key=lambda p: p.name):
        report["fault_info"].append(summarize_fault_info(path))

    out = data_dir / "wind_data_summary.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2)[:12000])
    print(f"\nSUMMARY_FILE={out}")


if __name__ == "__main__":
    main()
