from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Iterable, List

from openai import OpenAI

from .models import ChangeRow, MatchResult

LOGGER = logging.getLogger(__name__)


@dataclass
class AiConfig:
    model: str
    max_items: int
    max_chars: int


def _short_hash(*parts: str) -> str:
    import hashlib

    digest = hashlib.sha1()
    for part in parts:
        digest.update(part.encode("utf-8", errors="ignore"))
        digest.update(b"\0")
    return digest.hexdigest()[:10]


def _prompt_for_change(before: str, after: str) -> str:
    return (
        "You are a construction estimator assistant. Compare the BEFORE and AFTER text and "
        "return a JSON array called findings. Each finding should have: "
        "summary (string), rationale (string), significance_1to5 (int 1-5). "
        "If no meaningful changes, return an empty array. "
        "Respond ONLY with JSON.\n\n"
        f"BEFORE:\n{before}\n\nAFTER:\n{after}\n"
    )


def ai_scan_matches(
    client: OpenAI,
    matches: Iterable[MatchResult],
    ai_config: AiConfig,
) -> List[ChangeRow]:
    results: List[ChangeRow] = []
    reviewed = 0

    for match in matches:
        if not match.to_page:
            continue
        if reviewed >= ai_config.max_items:
            break

        before = (match.from_page.text or "")[: ai_config.max_chars]
        after = (match.to_page.text or "")[: ai_config.max_chars]
        reference = match.from_page.sheet_id or f"p{match.from_page.page_num+1}"

        prompt = _prompt_for_change(before, after)
        try:
            response = client.chat.completions.create(
                model=ai_config.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            content = response.choices[0].message.content or "{}"
            data = json.loads(content)
            findings = data.get("findings", []) if isinstance(data, dict) else data
        except Exception as exc:  # pragma: no cover - network/LLM
            LOGGER.warning("AI scan failed for %s: %s", reference, exc)
            findings = []

        for idx, finding in enumerate(findings or []):
            summary = str(finding.get("summary", "")).strip()
            rationale = str(finding.get("rationale", "")).strip()
            score = finding.get("significance_1to5", "")
            change_id = _short_hash(reference, summary, rationale, str(idx))
            results.append(
                ChangeRow(
                    change_id=change_id,
                    set_from="AI",
                    set_to="AI",
                    discipline=match.from_page.discipline,
                    doc_type="AI",
                    reference=reference,
                    change_type="AI_Finding",
                    change_summary=summary or "AI detected potential scope change.",
                    before_snippet=before[:700],
                    after_snippet=after[:700],
                    confidence="AI",
                    auto_flags="",
                    impact_score=int(score) if isinstance(score, int) else 0,
                    impact_rationale=rationale or "AI review",
                )
            )

        reviewed += 1

    return results
