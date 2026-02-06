from __future__ import annotations

import argparse
import hashlib
import logging
import re
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import yaml

from .diff_notes import diff_note_lists, split_note_bullets
from .diff_specs import extract_spec_sections
from .diff_tables import diff_tables, table_signature
from .export_excel import write_workbook
from .identify import guess_discipline
from .ingest import ingest_set, list_pdfs
from .match import match_pages
from .models import ChangeRow, Config, DocSet, MatchResult

LOGGER = logging.getLogger(__name__)


def load_config(path: str) -> Config:
    with open(path, "r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def short_hash(*parts: str) -> str:
    digest = hashlib.sha1()
    for part in parts:
        digest.update(part.encode("utf-8", errors="ignore"))
        digest.update(b"\0")
    return digest.hexdigest()[:10]


def apply_flags(config: Config, text: str) -> List[str]:
    text_lower = text.lower()
    hits: List[str] = []
    for group, terms in (config.get("flags") or {}).items():
        if any(term.lower() in text_lower for term in terms):
            hits.append(group)
    return hits


def compute_impact(change_type: str, flags: List[str], before: str, after: str, table_delta: bool = False) -> Tuple[int, str]:
    score = 0
    rationale: List[str] = []
    if change_type in {"Added", "Removed"}:
        score += 20
        rationale.append("sheet/spec presence changed")
    if table_delta:
        score += 20
        rationale.append("schedule row delta")
    if flags:
        score += 15
        rationale.append(f"flags: {', '.join(flags)}")
    if re.search(r"\b(contractor shall|provide|include|by others)\b", after, re.IGNORECASE):
        score += 10
        rationale.append("responsibility language changed")
    return min(score, 100), "; ".join(rationale)


def parse_sets(args: argparse.Namespace) -> Dict[str, str]:
    sets: Dict[str, str] = {}
    if args.set:
        for item in args.set:
            name, path = item.split("=", 1)
            sets[name.strip().upper()] = path.strip()
    else:
        if args.gmp:
            sets["GMP"] = args.gmp
        if args.bid:
            sets["BID"] = args.bid
        if args.addenda:
            sets["ADDENDA"] = args.addenda
        if not sets and Path("input").exists():
            for name in ["GMP", "BID", "ADDENDA"]:
                p = Path("input") / name
                if p.exists():
                    sets[name] = str(p)
    return sets


def inventory_changes(set_from: DocSet, set_to: DocSet) -> List[ChangeRow]:
    from_ids = {p.sheet_id for p in set_from.pages if p.sheet_id}
    to_ids = {p.sheet_id for p in set_to.pages if p.sheet_id}
    rows: List[ChangeRow] = []
    for sid in sorted(to_ids - from_ids):
        rows.append(ChangeRow(short_hash(set_from.name, set_to.name, sid, "Added"), set_from.name, set_to.name, guess_discipline(sid), "Drawing", sid, "Added", f"Sheet appears in {set_to.name}: {sid}", "", "", "High", "", 25, "new sheet"))
    for sid in sorted(from_ids - to_ids):
        rows.append(ChangeRow(short_hash(set_from.name, set_to.name, sid, "Removed"), set_from.name, set_to.name, guess_discipline(sid), "Drawing", sid, "Removed", f"Sheet missing from {set_to.name}: {sid}", "", "", "High", "", 20, "sheet removed"))
    return rows


def compare_sets(config: Config, set_from: DocSet, set_to: DocSet, matches: List[MatchResult]) -> List[ChangeRow]:
    rows: List[ChangeRow] = []
    spec_patterns = config.get("spec_section_patterns") or []
    max_snippet = int(((config.get("diff") or {}).get("max_snippet_chars", 700))

)
    for match in matches:
        if not match.to_page:
            continue
        source = match.from_page
        target = match.to_page
        reference = source.sheet_id or f"{Path(source.pdf_path).name}:p{source.page_num+1}"

        source_notes = split_note_bullets(source.text)
        target_notes = split_note_bullets(target.text)
        added_notes, removed_notes = diff_note_lists(source_notes, target_notes)
        if added_notes:
            after = "\n".join(added_notes)[:max_snippet]
            flags = apply_flags(config, after)
            impact, rationale = compute_impact("Added", flags, "", after)
            rows.append(ChangeRow(short_hash(set_from.name, set_to.name, reference, "notes_added", after), set_from.name, set_to.name, source.discipline, "Drawing", reference, "Added", f"Added note items on {reference}: {len(added_notes)}", "", after, match.confidence, ";".join(flags), impact, rationale))
        if removed_notes:
            before = "\n".join(removed_notes)[:max_snippet]
            impact, rationale = compute_impact("Removed", [], before, "")
            rows.append(ChangeRow(short_hash(set_from.name, set_to.name, reference, "notes_removed", before), set_from.name, set_to.name, source.discipline, "Drawing", reference, "Removed", f"Removed note items on {reference}: {len(removed_notes)}", before, "", match.confidence, "", impact, rationale))

        add_rows, rem_rows = diff_tables(source.tables, target.tables)
        if add_rows or rem_rows:
            before = "\n".join(table_signature(source.tables[0])[:30])[:max_snippet] if source.tables else ""
            after = "\n".join(table_signature(target.tables[0])[:30])[:max_snippet] if target.tables else ""
            flags = apply_flags(config, before + "\n" + after)
            impact, rationale = compute_impact("Modified", flags, before, after, table_delta=True)
            rows.append(ChangeRow(short_hash(set_from.name, set_to.name, reference, "tables", str(add_rows), str(rem_rows)), set_from.name, set_to.name, source.discipline, "Drawing", reference, "Modified", f"Table delta on {reference}: +{add_rows} / -{rem_rows}", before, after, match.confidence, ";".join(flags), impact, rationale))

        if re.search(r"\bSECTION\b", source.text + target.text, flags=re.IGNORECASE):
            src_secs = extract_spec_sections(source.text, spec_patterns)
            dst_secs = extract_spec_sections(target.text, spec_patterns)
            for sec in sorted(set(dst_secs) - set(src_secs)):
                after = dst_secs[sec][:max_snippet]
                flags = apply_flags(config, after)
                impact, rationale = compute_impact("Added", flags, "", after)
                rows.append(ChangeRow(short_hash(set_from.name, set_to.name, sec, "spec_add"), set_from.name, set_to.name, "Specifications", "Spec", sec, "Added", f"Spec section added: {sec}", "", after, "High", ";".join(flags), impact, rationale))

    dedupe: Dict[str, ChangeRow] = {row.change_id: row for row in rows}
    return list(dedupe.values())


def run(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Construction PDF set differ")
    parser.add_argument("--set", action="append", help="Set input as NAME=PATH; can repeat")
    parser.add_argument("--gmp", help="Legacy: GMP folder")
    parser.add_argument("--bid", help="Legacy: BID folder")
    parser.add_argument("--addenda", help="Legacy: ADDENDA folder")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--out", required=True)
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(list(argv) if argv else None)

    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO), format="%(levelname)s %(name)s: %(message)s")
    config = load_config(args.config)
    sets = parse_sets(args)

    if "GMP" not in sets or "BID" not in sets:
        raise SystemExit("GMP and BID sets are required")

    gmp = ingest_set(config, "GMP", sets["GMP"])
    bid = ingest_set(config, "BID", sets["BID"])

    weight_cfg = (config.get("matching") or {}).get("weights") or {}
    matches = match_pages(gmp, bid, weight_cfg)
    changes = compare_sets(config, gmp, bid, matches)
    inventory = inventory_changes(gmp, bid)

    if "ADDENDA" in sets and list_pdfs(sets["ADDENDA"]):
        addenda = ingest_set(config, "ADDENDA", sets["ADDENDA"])
        add_matches = match_pages(gmp, addenda, weight_cfg)
        changes.extend(compare_sets(config, gmp, addenda, add_matches))
        matches.extend(add_matches)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    write_workbook(args.out, changes, inventory, matches)
    LOGGER.info("Wrote %s (changes=%d)", args.out, len(changes))
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
