"""Test độc lập của tính năng lọc PII. Chạy:  python features/pii_filter/test_pii.py"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from features.pii_filter.pii import mask  # noqa: E402


class PiiFilterTests(unittest.TestCase):
    def test_phone_is_masked(self):
        text, n = mask("Gọi lại số 0000000000 nhé")
        self.assertEqual(text, "Gọi lại số [SĐT] nhé")
        self.assertEqual(n, 1)

    def test_cccd_is_masked(self):
        text, n = mask("CCCD 000000000000 của bệnh nhân")
        self.assertIn("[CCCD]", text)
        self.assertNotIn("000000000000", text)
        self.assertEqual(n, 1)

    def test_name_after_title_is_masked_lower_and_capitalized(self):
        for src in ("anh Mẫu A đau bụng", "Bệnh nhân Mẫu A đau bụng"):
            text, _ = mask(src)
            self.assertNotIn("Mẫu A", text, src)
            self.assertIn("[TÊN]", text, src)

    def test_ten_benh_nhan_la_masks_once_without_masking_la(self):
        text, n = mask("Tên bệnh nhân là Nguyễn Văn An, số điện thoại 0912345678.")
        self.assertEqual(text, "Tên bệnh nhân là [TÊN], số điện thoại [SĐT].")
        self.assertEqual(n, 2)

    def test_text_without_pii_is_unchanged(self):
        text, n = mask("Mạch 88, nhịp thở 20")
        self.assertEqual(text, "Mạch 88, nhịp thở 20")
        self.assertEqual(n, 0)

    def test_empty_input(self):
        self.assertEqual(mask(""), ("", 0))


if __name__ == "__main__":
    unittest.main(verbosity=2)
