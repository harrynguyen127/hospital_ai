"""Test độc lập của tính năng detect form (hàm thuần, không cần store).

Chạy:  python features/detect_form/test_detect_form.py
"""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from features.detect_form import form_detection  # noqa: E402
from shared.common import fingerprint  # noqa: E402

EMR_SINH_TON = {
    "title": "Bảng theo dõi dấu hiệu sinh tồn cho người lớn",
    "fields": [
        {"label": "Mạch", "ui": "number", "required": True},
        {"label": "Nhịp thở", "ui": "number", "required": True},
        {"label": "Huyết áp", "ui": "text"},
        {"label": "Nhiệt độ", "ui": "number"},
        {"label": "SpO2", "ui": "number"},
    ],
}


def seed_forms():
    """Registry mẫu lấy trực tiếp từ data/, không qua store."""
    raw = json.loads((ROOT / "data" / "form_registry" / "forms.json").read_text(encoding="utf-8"))
    return {fid: {"form_id": fid, **f, "status": "active", "version": 1,
                  "fingerprint": fingerprint(f["title"], f["fields"]), "history": []}
            for fid, f in raw.items()}


class DetectFormTests(unittest.TestCase):
    def test_exact_match_changes_nothing(self):
        out = form_detection.detect(seed_forms(), EMR_SINH_TON)
        self.assertEqual(out["result"]["match"], "exact")
        self.assertEqual(out["result"]["form_id"], "phieu_sinh_ton_nguoi_lon")
        self.assertEqual(out["changes"], {})
        self.assertEqual(out["events"], [])

    def test_near_match_adds_field_and_returns_new_forms(self):
        variant = {**EMR_SINH_TON, "fields": EMR_SINH_TON["fields"] + [{"label": "Ghi chú", "ui": "text"}]}
        out = form_detection.detect(seed_forms(), variant)
        self.assertTrue(out["result"]["match"].startswith("gần giống"))
        self.assertEqual(out["result"]["version"], 2)
        self.assertEqual(out["changes"]["forms"]["phieu_sinh_ton_nguoi_lon"]["version"], 2)
        self.assertEqual(out["events"][0][0], "form.version")

    def test_input_forms_are_never_mutated(self):
        forms = seed_forms()
        before = copy.deepcopy(forms)
        variant = {**EMR_SINH_TON, "fields": EMR_SINH_TON["fields"] + [{"label": "Ghi chú", "ui": "text"}]}
        form_detection.detect(forms, variant)
        self.assertEqual(forms, before)

    def test_unknown_form_is_created_as_active(self):
        new_form = {"title": "Sàng lọc dinh dưỡng", "fields": [
            {"label": "Cân nặng (kg)", "ui": "number", "required": True},
            {"label": "Ăn kém gần đây", "ui": "checkbox"},
        ]}
        out = form_detection.detect(seed_forms(), new_form)
        self.assertEqual(out["result"]["match"], "mới")
        self.assertEqual(out["result"]["form_id"], "phieu_sang_loc_dinh_duong")
        self.assertIn("phieu_sang_loc_dinh_duong", out["changes"]["forms"])
        self.assertEqual(out["events"][0][0], "form.new")

    def test_rollback_restores_previous_version(self):
        variant = {**EMR_SINH_TON, "fields": EMR_SINH_TON["fields"] + [{"label": "Ghi chú", "ui": "text"}]}
        upgraded = form_detection.detect(seed_forms(), variant)["changes"]["forms"]
        back = form_detection.rollback_form(upgraded, "phieu_sinh_ton_nguoi_lon")
        self.assertTrue(back["result"]["ok"])
        self.assertEqual(back["changes"]["forms"]["phieu_sinh_ton_nguoi_lon"]["version"], 1)

    def test_rollback_without_history_changes_nothing(self):
        out = form_detection.rollback_form(seed_forms(), "phieu_sinh_ton_nguoi_lon")
        self.assertFalse(out["result"]["ok"])
        self.assertEqual(out["changes"], {})


if __name__ == "__main__":
    unittest.main(verbosity=2)
