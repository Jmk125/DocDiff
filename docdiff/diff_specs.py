from __future__ import annotations

import re
from typing import Dict, Iterable


def extract_spec_sections(text: str, patterns: Iterable[str]) -> Dict[str, str]:
    starts = []
    for pat in patterns:
        for m in re.finditer(pat, text, flags=re.IGNORECASE):
            sec = m.group(1) if m.lastindex else m.group(0)
            starts.append((m.start(), re.sub(r"\s+", " ", sec.strip())))
    if not starts:
        return {"UNKNOWN": text.strip()}
    starts.sort(key=lambda pair: pair[0])
    out: Dict[str, str] = {}
    for idx, (start, sec) in enumerate(starts):
        end = starts[idx + 1][0] if idx + 1 < len(starts) else len(text)
        chunk = text[start:end].strip()
        if sec not in out or len(chunk) > len(out[sec]):
            out[sec] = chunk
    return out
