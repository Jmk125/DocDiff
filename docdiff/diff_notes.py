from __future__ import annotations

import re
from typing import List, Tuple


def split_note_bullets(text: str, min_len: int = 12) -> List[str]:
    bullets: List[str] = []
    for line in [ln.strip() for ln in text.splitlines() if ln.strip()]:
        if len(line) < min_len:
            continue
        if re.match(r"^(\(?\d{1,3}\)?[.)]|[A-Z][.)]|[-•])\s+", line):
            bullets.append(line)
        elif re.match(r"^(KEYNOTE|GENERAL NOTES|NOTE)\b", line, flags=re.IGNORECASE):
            bullets.append(line)
    deduped: List[str] = []
    seen = set()
    for bullet in bullets:
        key = re.sub(r"\s+", " ", bullet).lower()
        if key not in seen:
            seen.add(key)
            deduped.append(bullet)
    return deduped


def diff_note_lists(before: List[str], after: List[str]) -> Tuple[List[str], List[str]]:
    bset = {item.strip() for item in before if item.strip()}
    aset = {item.strip() for item in after if item.strip()}
    return sorted(aset - bset), sorted(bset - aset)
