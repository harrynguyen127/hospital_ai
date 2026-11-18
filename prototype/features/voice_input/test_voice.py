"""Test độc lập của tính năng voice input (không cần lõi, store hay tính năng khác).

Chạy:  python features/voice_input/test_voice.py
Bộ lọc PII được TIÊM vào (fake), nên test không phụ thuộc features/pii_filter.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from contracts import registry  # noqa: E402
from features.voice_input import external_api, voice  # noqa: E402

FORM = {"fields": [
    {"field_id": "mach", "label": "Mạch", "ui": "number"},
    {"field_id": "huyet_ap", "label": "Huyết áp", "ui": "text"},
    {"field_id": "nhiet_do", "label": "Nhiệt độ", "ui": "number"},
]}


def fake_mask(text):
    """Bộ lọc giả: chỉ che đúng một chuỗi, để kiểm tra voice dùng đúng bản đã che."""
    return text.replace("0000000000", "[SĐT]"), text.count("0000000000")


class VoiceProcessTests(unittest.TestCase):
    def test_extracts_fields_from_speech(self):
        out = voice.process("Mạch 88, huyết áp 120 trên 80, nhiệt độ 37 phẩy 2", FORM, mask_fn=fake_mask)
        self.assertEqual(out["extracted"], {"mach": 88, "huyet_ap": "120/80", "nhiet_do": 37.2})
        self.assertFalse(out["out_of_scope"])

    def test_uses_injected_mask_and_extracts_from_masked_text(self):
        out = voice.process("Số 0000000000, mạch 90", FORM, mask_fn=fake_mask)
        self.assertIn("[SĐT]", out["masked"])
        self.assertNotIn("0000000000", out["masked"])
        self.assertEqual(out["pii_masked"], 1)
        self.assertEqual(out["extracted"], {"mach": 90})

    def test_out_of_scope_sentence_extracts_nothing(self):
        out = voice.process("Hôm nay trời đẹp quá, mạch 80", FORM, mask_fn=fake_mask)
        self.assertTrue(out["out_of_scope"])
        self.assertEqual(out["extracted"], {})

    def test_refuses_to_run_without_a_mask(self):
        # Không có bộ lọc thì không xử lý, để tránh đưa văn bản chưa che ra ngoài
        with self.assertRaises(RuntimeError):
            voice.process("mạch 80", FORM)


class ExternalApiTests(unittest.TestCase):
    def test_prepare_payload_masks_before_sending(self):
        payload = external_api.prepare_payload("Số 0000000000", fake_mask)
        self.assertEqual(payload, {"text": "Số [SĐT]", "pii_filtered": True, "pii_masked": 1})

    def test_send_refuses_unfiltered_content(self):
        with self.assertRaises(ValueError):
            external_api.send_filtered("Số 0000000000")
        with self.assertRaises(ValueError):
            external_api.send_filtered({"text": "Số 0000000000", "pii_filtered": False})

    def test_default_sender_is_disabled(self):
        payload = external_api.prepare_payload("mạch 80", fake_mask)
        self.assertFalse(external_api.send_filtered(payload)["sent"])

    def test_connected_sender_receives_only_filtered_payload(self):
        received = []
        registry.connect("voice.send", lambda p: received.append(p) or {"sent": True})
        try:
            payload = external_api.prepare_payload("Số 0000000000", fake_mask)
            self.assertEqual(external_api.send_filtered(payload), {"sent": True})
            self.assertEqual(received, [payload])
        finally:
            registry.disconnect("voice.send")
        self.assertFalse(external_api.send_filtered(external_api.prepare_payload("x", fake_mask))["sent"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
