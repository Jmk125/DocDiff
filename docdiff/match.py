from __future__ import annotations

import hashlib
import logging
import re
from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from rapidfuzz import fuzz

from .models import DocSet, MatchResult, PageExtract

LOGGER = logging.getLogger(__name__)


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]{3,}", text.lower())


def simhash64(text: str) -> int:
    vec = [0] * 64
    for tok in _tokenize(text)[:5000]:
        hv = int.from_bytes(hashlib.sha1(tok.encode("utf-8")).digest()[:8], "big")
        for i in range(64):
            vec[i] += 1 if (hv >> i) & 1 else -1
    out = 0
    for i, val in enumerate(vec):
        if val >= 0:
            out |= (1 << i)
    return out


def hamming_similarity(a: int, b: int) -> float:
    bits = 64
    diff = (a ^ b).bit_count()
    return 1 - (diff / bits)


def _composite_score(src: PageExtract, dst: PageExtract, weights: Dict[str, float]) -> Tuple[float, List[str]]:
    score = 0.0
    reasons: List[str] = []

    if src.sheet_id and dst.sheet_id and src.sheet_id == dst.sheet_id:
        score += weights.get("sheet_id_exact", 60.0)
        reasons.append("sheet_id exact")

    title_sim = 0.0
    if src.sheet_title_hint or dst.sheet_title_hint:
        src_title = (src.sheet_title_hint or "").strip().upper()
        dst_title = (dst.sheet_title_hint or "").strip().upper()
        title_sim = fuzz.WRatio(src_title, dst_title) / 100.0
        score += title_sim * weights.get("title_similarity", 20.0)
        if src_title and src_title == dst_title:
            score += 10
            reasons.append("title exact")
        reasons.append(f"title {title_sim:.2f}")

    if src.discipline != "Unknown" and src.discipline == dst.discipline:
        score += weights.get("discipline_similarity", 10.0)
        reasons.append("discipline")

    src_fp = src.fingerprint or simhash64(src.text)
    dst_fp = dst.fingerprint or simhash64(dst.text)
    fp_sim = hamming_similarity(src_fp, dst_fp)
    score += fp_sim * weights.get("fingerprint_similarity", 10.0)
    reasons.append(f"fingerprint {fp_sim:.2f}")

    return score, reasons


def _confidence(score: float) -> str:
    if score >= 80:
        return "High"
    if score >= 55:
        return "Med"
    return "Low"


def _candidate_pool(src: PageExtract, to_pages: Sequence[PageExtract], by_sheet: Dict[str, List[PageExtract]]) -> Sequence[PageExtract]:
    if src.sheet_id and src.sheet_id in by_sheet:
        return by_sheet[src.sheet_id]
    if src.discipline != "Unknown":
        subset = [p for p in to_pages if p.discipline == src.discipline]
        if subset:
            return subset
    return to_pages


def match_pages(from_set: DocSet, to_set: DocSet, weights: Optional[Dict[str, float]] = None) -> List[MatchResult]:
    weights = weights or {}
    by_sheet: Dict[str, List[PageExtract]] = defaultdict(list)
    for page in to_set.pages:
        if page.sheet_id:
            by_sheet[page.sheet_id].append(page)

    results: List[MatchResult] = []
    for src in from_set.pages:
        candidates = _candidate_pool(src, to_set.pages, by_sheet)
        best_page: Optional[PageExtract] = None
        best_score = -1.0
        best_reasons: List[str] = []
        for dst in candidates:
            score, reasons = _composite_score(src, dst, weights)
            if score > best_score:
                best_score = score
                best_page = dst
                best_reasons = reasons
        if best_page is None:
            results.append(MatchResult(src, None, 0.0, "Low", ["no candidate"]))
        else:
            results.append(MatchResult(src, best_page, best_score, _confidence(best_score), best_reasons))

    LOGGER.info("Matched %d pages from %s to %s", len(results), from_set.name, to_set.name)
    return results
