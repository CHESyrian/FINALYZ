"""
Excel statement parser using openpyxl.

Reads the first sheet, detects the header row, and returns
raw headers + data rows for the mapping UI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO
from typing import Any

from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet


@dataclass
class ParsedExcel:
    """Result of parsing an uploaded Excel file."""

    headers: list[str]                          # detected column headers
    rows: list[list[Any]]                       # data rows (values only)
    sheet_name: str
    header_row_index: int                       # 1-based row number of headers
    preview_rows: list[dict[str, Any]] = field(default_factory=list)  # for UI


def _cell_value(cell) -> Any:
    val = cell.value
    if val is None:
        return None
    if isinstance(val, str):
        return val.strip()
    return val


def _is_header_like(row_values: list[Any]) -> bool:
    """Heuristic: a header row has mostly non-empty strings."""
    non_empty = [v for v in row_values if v is not None and str(v).strip()]
    if len(non_empty) < 2:
        return False
    string_count = sum(1 for v in non_empty if isinstance(v, str) and not _looks_numeric(v))
    return string_count >= max(2, len(non_empty) * 0.5)


def _looks_numeric(value: str) -> bool:
    try:
        float(value.replace(",", "").replace("%", "").strip())
        return True
    except (ValueError, AttributeError):
        return False


def _detect_header_row(ws: Worksheet, max_scan: int = 20) -> int:
    """
    Scan the first rows and return the 1-based index of the best header row.
    Falls back to row 1.
    """
    best_row = 1
    best_score = -1

    for row_idx, row in enumerate(ws.iter_rows(min_row=1, max_row=max_scan), start=1):
        values = [_cell_value(c) for c in row]
        if not any(v is not None for v in values):
            continue
        if _is_header_like(values):
            score = sum(1 for v in values if v is not None and isinstance(v, str))
            if score > best_score:
                best_score = score
                best_row = row_idx

    return best_row


def parse_excel(file_bytes: bytes, sheet_index: int = 0) -> ParsedExcel:
    """
    Parse an uploaded .xlsx file.

    Parameters
    ----------
    file_bytes : bytes
        Raw content of the uploaded file.
    sheet_index : int
        Which sheet to use (0 = first).

    Returns
    -------
    ParsedExcel
    """
    wb = load_workbook(filename=BytesIO(file_bytes), data_only=True, read_only=True)
    try:
        if sheet_index >= len(wb.sheetnames):
            sheet_index = 0
        ws = wb[wb.sheetnames[sheet_index]]
        sheet_name = ws.title

        header_row_idx = _detect_header_row(ws)

        # Read header
        header_cells = list(ws.iter_rows(min_row=header_row_idx, max_row=header_row_idx))[0]
        raw_headers = [_cell_value(c) for c in header_cells]

        # Clean headers: use column letter for empty ones
        headers: list[str] = []
        for i, h in enumerate(raw_headers):
            if h is None or str(h).strip() == "":
                headers.append(f"Column_{i + 1}")
            else:
                headers.append(str(h).strip())

        # Trim trailing empty headers
        while headers and headers[-1].startswith("Column_"):
            # only trim if the whole column is empty in data too – keep simple for now
            break

        # Read data rows (up to 500 for safety)
        rows: list[list[Any]] = []
        for row in ws.iter_rows(min_row=header_row_idx + 1, max_row=header_row_idx + 500):
            values = [_cell_value(c) for c in row[: len(headers)]]
            # Skip completely empty rows
            if not any(v is not None for v in values):
                continue
            # Pad / trim to header length
            values = (values + [None] * len(headers))[: len(headers)]
            rows.append(values)

        # Build preview (first 5 rows as dicts)
        preview: list[dict[str, Any]] = []
        for row in rows[:5]:
            preview.append({headers[i]: row[i] for i in range(len(headers))})

        return ParsedExcel(
            headers=headers,
            rows=rows,
            sheet_name=sheet_name,
            header_row_index=header_row_idx,
            preview_rows=preview,
        )
    finally:
        wb.close()
