from __future__ import annotations

import json
from pathlib import Path

import xlrd


def cell_value(v):
    if isinstance(v, float) and v.is_integer():
        return int(v)
    return v


def preview_book(path: Path, max_rows: int = 5):
    book = xlrd.open_workbook(str(path), on_demand=True)
    sheets = []
    for sheet in book.sheets():
        rows = []
        limit = min(sheet.nrows, max_rows)
        for r in range(limit):
            rows.append([cell_value(sheet.cell_value(r, c)) for c in range(min(sheet.ncols, 12))])
        sheets.append(
            {
                "sheet": sheet.name,
                "rows": sheet.nrows,
                "cols": sheet.ncols,
                "preview": rows,
            }
        )
    book.release_resources()
    return sheets


def main():
    cwd = Path.cwd()
    data_dir = next(
        p for p in cwd.iterdir() if p.is_dir() and p.name == "\u98ce\u673a\u6570\u636e"
    )

    result = {
        "data_dir": str(data_dir),
        "groups": [],
    }

    for folder in [data_dir, *sorted([p for p in data_dir.iterdir() if p.is_dir()], key=lambda p: p.name)]:
        files = sorted(folder.glob("*.xls"), key=lambda p: p.name)
        group = {
            "folder": str(folder),
            "file_count": len(files),
            "total_mb": round(sum(p.stat().st_size for p in files) / 1024 / 1024, 2),
            "files": [p.name for p in files[:30]],
            "samples": [],
        }
        for path in files[:2]:
            try:
                group["samples"].append(
                    {
                        "file": path.name,
                        "size_mb": round(path.stat().st_size / 1024 / 1024, 2),
                        "sheets": preview_book(path),
                    }
                )
            except Exception as exc:
                group["samples"].append({"file": path.name, "error": str(exc)})
        result["groups"].append(group)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
