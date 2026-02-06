from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Iterable, List

import fitz
import pdfplumber

from .identify import guess_discipline, identify_sheet, normalize_whitespace
from .models import Config, DocSet, PageExtract

LOGGER = logging.getLogger(__name__)


def list_pdfs(folder: str) -> List[str]:
    root = Path(folder)
    if not root.exists():
        return []
    return sorted(str(p) for p in root.rglob("*.pdf"))


def _clip_to_rect(page: fitz.Page, region: Dict[str, float]) -> str:
    rect = page.rect
    clip = fitz.Rect(
        rect.x0 + rect.width * region["x0"],
        rect.y0 + rect.height * region["y0"],
        rect.x0 + rect.width * region["x1"],
        rect.y0 + rect.height * region["y1"],
    )
    return page.get_text("text", clip=clip) or ""


def extract_title_block_text(page: fitz.Page, config: Config) -> str:
    regions = (config.get("title_block") or {}).get(
        "regions",
        [
            {"name": "bottom_right", "x0": 0.65, "y0": 0.78, "x1": 1.0, "y1": 1.0},
            {"name": "bottom_center", "x0": 0.3, "y0": 0.78, "x1": 0.75, "y1": 1.0},
        ],
    )
    snippets: List[str] = []
    for region in regions:
        try:
            snippets.append(_clip_to_rect(page, region))
        except Exception as exc:  # pragma: no cover - defensive
            LOGGER.debug("clip region failed: %s", exc)
    return normalize_whitespace("\n".join(snippets))


def extract_tables(pdf_path: str, page_num: int) -> List[List[List[str]]]:
    tables: List[List[List[str]]] = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            page = pdf.pages[page_num]
            for table in page.extract_tables() or []:
                cleaned = [[(cell or "").strip() for cell in row or []] for row in table]
                if len(cleaned) >= 2:
                    tables.append(cleaned)
    except Exception as exc:  # pragma: no cover - non-deterministic from PDFs
        LOGGER.warning("table extraction failed for %s p%s: %s", pdf_path, page_num + 1, exc)
    return tables


def extract_pdf_pages(config: Config, pdf_path: str) -> List[PageExtract]:
    patterns: Iterable[str] = config.get("sheet_id_patterns") or []
    pages: List[PageExtract] = []
    with fitz.open(pdf_path) as doc:
        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            text = normalize_whitespace(page.get_text("text") or "")
            title_block_text = extract_title_block_text(page, config)
            sheet_id, title = identify_sheet(text, title_block_text, patterns)
            pages.append(
                PageExtract(
                    pdf_path=pdf_path,
                    page_num=page_num,
                    text=text,
                    sheet_id=sheet_id,
                    sheet_title_hint=title,
                    discipline=guess_discipline(sheet_id),
                    tables=extract_tables(pdf_path, page_num),
                    title_block_text=title_block_text,
                )
            )
    return pages


def ingest_set(config: Config, name: str, path: str) -> DocSet:
    pages: List[PageExtract] = []
    for pdf_path in list_pdfs(path):
        pages.extend(extract_pdf_pages(config, pdf_path))
    LOGGER.info("Ingested %s: %d pages", name, len(pages))
    return DocSet(name=name, root=path, pages=pages)
