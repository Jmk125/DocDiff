from __future__ import annotations

import re
from typing import List, Tuple

KEY_HEADERS = {"mark", "tag", "id", "room", "panel", "circuit"}


def normalize_cell(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def infer_key_col(table: List[List[str]]) -> int:
    if not table:
        return 0
    headers = [normalize_cell(h).lower() for h in table[0]]
    for i, header in enumerate(headers):
        if any(key in header for key in KEY_HEADERS):
            return i
    return 0


def table_signature(table: List[List[str]]) -> List[str]:
    return [" | ".join(normalize_cell(c) for c in row if normalize_cell(c)) for row in table if row]


def diff_tables(before_tables: List[List[List[str]]], after_tables: List[List[List[str]]]) -> Tuple[int, int]:
    before_rows = set()
    after_rows = set()
    for table in before_tables:
        before_rows.update(table_signature(table))
    for table in after_tables:
        after_rows.update(table_signature(table))
    return len(after_rows - before_rows), len(before_rows - after_rows)
