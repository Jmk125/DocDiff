import unittest

from docdiff.match import match_pages
from docdiff.models import DocSet, PageExtract


class MatchTests(unittest.TestCase):
    def _page(self, sheet_id, title, text, discipline="Architectural"):
        return PageExtract(
            pdf_path="a.pdf",
            page_num=0,
            text=text,
            sheet_id=sheet_id,
            sheet_title_hint=title,
            discipline=discipline,
            tables=[],
        )

    def test_exact_sheet_id_has_high_score(self):
        src = self._page("A-101", "Floor Plan", "level 1 rooms")
        dst = self._page("A-101", "Floor Plan - Revised", "level 1 rooms updated")
        out = match_pages(DocSet("GMP", ".", [src]), DocSet("BID", ".", [dst]))
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].to_page.sheet_id, "A-101")
        self.assertGreaterEqual(out[0].score, 80)

    def test_fallback_uses_title_and_content(self):
        src = self._page(None, "Roof Plan", "roof drain overflow")
        dst = self._page(None, "ROOF PLAN", "roof drain overflow revised")
        other = self._page(None, "Site Plan", "parking striping")
        out = match_pages(DocSet("GMP", ".", [src]), DocSet("BID", ".", [dst, other]))
        self.assertEqual(out[0].to_page.sheet_title_hint, "ROOF PLAN")


if __name__ == "__main__":
    unittest.main()
