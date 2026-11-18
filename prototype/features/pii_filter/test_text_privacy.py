"""Synthetic, text-only privacy preflight tests."""

import unittest

from features.pii_filter.text_privacy import (
    PiiFinding,
    detect_rules,
    process_text,
    redact,
)


class TextPrivacyTests(unittest.TestCase):
    def test_phone_and_cccd(self):
        result = process_text("SĐT 0912345678; CCCD 012345678901.")
        self.assertEqual(result.masked_text, "SĐT [PHONE]; CCCD [CCCD].")
        self.assertEqual(len(result.findings), 2)
        self.assertFalse(result.external_egress_authorized)

    def test_name_addressed_by_title(self):
        result = process_text("Bệnh nhân Nguyễn Văn An đau bụng.")
        self.assertIn("[PERSON]", result.masked_text)
        self.assertIn("đau bụng.", result.masked_text)

    def test_preserve_clinical_facts(self):
        source = "Không dị ứng thuốc, mạch 92 lần/phút, huyết áp 120/80 mmHg."
        result = process_text(source)
        self.assertEqual(result.masked_text, source)
        self.assertEqual(result.status, "review_required")

    def test_patient_id_and_birth_date_context(self):
        result = process_text("Mã bệnh nhân BN-12345, ngày sinh 12/03/1990.")
        self.assertIn("[PATIENT_ID]", result.masked_text)
        self.assertIn("[DATE_OF_BIRTH]", result.masked_text)

    def test_non_identifying_dates_not_masked(self):
        source = "Đánh giá đau ngày 18/11/2026, mạch 92."
        self.assertEqual(process_text(source).masked_text, source)

    def test_no_external_egress_even_with_ner(self):
        def ner(text):
            pos = text.index("Chợ Rẫy")
            return [PiiFinding(pos, pos + len("Chợ Rẫy"), "ORGANIZATION", "ner")]

        result = process_text("Tại Bệnh viện Chợ Rẫy.", ner)
        self.assertIn("[PII]", result.masked_text)
        self.assertEqual(result.detector_status, "rules_and_ner")
        self.assertFalse(result.external_egress_authorized)

    def test_overlapping_spans_cannot_leak_suffix(self):
        text = "Nguyễn Văn An"
        masked, merged = redact(
            text,
            (
                PiiFinding(0, 6, "PERSON", "rules"),
                PiiFinding(3, len(text), "PERSON", "ner"),
            ),
        )
        self.assertEqual(masked, "[PERSON]")
        self.assertEqual(len(merged), 1)

    def test_detector_error_fails_to_review(self):
        def broken(_):
            raise RuntimeError("simulated failure")

        result = process_text("Gọi 0912345678", broken)
        self.assertEqual(result.detector_status, "ner_failed")
        self.assertIn("NER_DETECTOR_FAILED", result.reason_codes)
        self.assertIn("[PHONE]", result.masked_text)
        self.assertFalse(result.external_egress_authorized)

    def test_invalid_detector_span_rejected(self):
        result = process_text("Mạch 92", lambda _: [PiiFinding(0, 100, "PERSON", "ner")])
        self.assertEqual(result.detector_status, "ner_invalid_spans")
        self.assertEqual(result.masked_text, "Mạch 92")
        self.assertFalse(result.external_egress_authorized)

    def test_repeated_identifiers(self):
        text = "0912345678 và 0912345678"
        result = process_text(text)
        self.assertEqual(result.masked_text, "[PHONE] và [PHONE]")
        self.assertEqual(len(result.findings), 2)

    def test_empty_string_and_validation(self):
        self.assertEqual(process_text("").masked_text, "")
        with self.assertRaises(TypeError):
            detect_rules(None)

    def test_no_ner_claim_in_rules_only(self):
        result = process_text("Không đau ngực.")
        self.assertEqual(result.detector_status, "rules_only")
        self.assertIn("UNVERIFIED_PRIVACY_COVERAGE", result.reason_codes)


if __name__ == "__main__":
    unittest.main()
