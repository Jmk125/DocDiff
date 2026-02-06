from __future__ import annotations

import logging
import re
from typing import Iterable, List, Optional, Tuple

LOGGER = logging.getLogger(__name__)


def normalize_whitespace(text: str) -> str:
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_sheet_id(sheet_id: str) -> str:
    candidate = re.sub(r"\s+", "", sheet_id).upper()
    candidate = candidate.replace("_", "-")
    m = re.match(r"^([A-Z]{1,4})-?(\d[\dA-Z.]*)$", candidate)
    if not m:
        return candidate
    return f"{m.group(1)}-{m.group(2)}"


def score_sheet_candidate(candidate: str) -> float:
    c = normalize_sheet_id(candidate)
    score = 0.0
    if re.match(r"^[A-Z]{1,4}-\d", c):
        score += 10
    else:
        score -= 5
    if "-" in c:
        score += 3
    if re.search(r"\b(NOTE|PROJECT|SHEET)\b", c):
        score -= 4
    if re.search(r"\.\d+", c):
        score += 1
    score += min(len(c), 12) * 0.1
    return score


def find_sheet_candidates(text: str, patterns: Iterable[str]) -> List[str]:
    found: List[str] = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            found.append(match.group(0))
    return found


def choose_best_sheet_id(candidates: List[str]) -> Optional[str]:
    if not candidates:
        return None
    best = sorted(candidates, key=score_sheet_candidate, reverse=True)[0]
    return normalize_sheet_id(best)


def extract_title_hint(text: str, sheet_id: Optional[str]) -> Optional[str]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return None
    search_id = sheet_id.replace("-", "") if sheet_id else None
    if search_id:
        for i, line in enumerate(lines[:80]):
            if search_id in re.sub(r"\W+", "", line.upper()):
                for idx in range(i + 1, min(i + 5, len(lines))):
                    candidate = lines[idx]
                    if 6 <= len(candidate) <= 100 and not candidate.isdigit():
                        return candidate[:100]
    for line in lines[:40]:
        if 8 <= len(line) <= 100 and not re.search(r"\b(date|issued|revision|scale)\b", line, re.IGNORECASE):
            return line[:100]
    return None


def guess_discipline(sheet_id: Optional[str]) -> str:
    if not sheet_id:
        return "Unknown"
    prefix = sheet_id.split("-")[0].upper()
    mapping = {
        "A": "Architectural",
        "S": "Structural",
        "M": "Mechanical",
        "ME": "Mechanical",
        "P": "Plumbing",
        "PL": "Plumbing",
        "E": "Electrical",
        "EL": "Electrical",
        "FP": "Fire Protection",
        "FA": "Fire Alarm",
        "C": "Civil",
        "L": "Landscape",
    }
    for key, value in mapping.items():
        if prefix.startswith(key):
            return value
    return "Unknown"


def identify_sheet(text: str, title_block_text: str, patterns: Iterable[str]) -> Tuple[Optional[str], Optional[str]]:
    candidates = find_sheet_candidates(title_block_text, patterns)
    if not candidates:
        candidates = find_sheet_candidates(text[:6000], patterns)
    sheet_id = choose_best_sheet_id(candidates)
    title_hint = extract_title_hint(title_block_text or text, sheet_id)
    LOGGER.debug("Identify sheet: %s (%d candidates)", sheet_id, len(candidates))
    return sheet_id, title_hint
