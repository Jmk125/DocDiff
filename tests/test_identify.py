import unittest

from docdiff.identify import normalize_sheet_id, choose_best_sheet_id


class IdentifyTests(unittest.TestCase):
    def test_normalize_sheet_id_variants(self):
        self.assertEqual(normalize_sheet_id("A101"), "A-101")
        self.assertEqual(normalize_sheet_id("A-101"), "A-101")
        self.assertEqual(normalize_sheet_id("A 101"), "A-101")

    def test_choose_best_candidate_prefers_sheet_like(self):
        candidates = ["PROJECT 101", "A101", "note 3"]
        self.assertEqual(choose_best_sheet_id(candidates), "A-101")


if __name__ == "__main__":
    unittest.main()
