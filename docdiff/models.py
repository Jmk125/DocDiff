from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PageExtract:
    pdf_path: str
    page_num: int
    text: str
    sheet_id: Optional[str]
    sheet_title_hint: Optional[str]
    discipline: str
    tables: List[List[List[str]]]
    title_block_text: str = ""
    fingerprint: int = 0


@dataclass
class DocSet:
    name: str
    root: str
    pages: List[PageExtract] = field(default_factory=list)


@dataclass
class MatchResult:
    from_page: PageExtract
    to_page: Optional[PageExtract]
    score: float
    confidence: str
    reasons: List[str]


@dataclass
class ChangeRow:
    change_id: str
    set_from: str
    set_to: str
    discipline: str
    doc_type: str
    reference: str
    change_type: str
    change_summary: str
    before_snippet: str
    after_snippet: str
    confidence: str
    auto_flags: str
    impact_score: int
    impact_rationale: str


Config = Dict[str, Any]
