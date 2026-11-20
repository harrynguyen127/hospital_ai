"""Recognizer boundaries and clinical negative examples, using synthetic text."""

import unicodedata
import unittest

from features.pii_filter.normalization import ResourceLimitError, build_view
from features.pii_filter.rules import detect_rules
from features.pii_filter.schema import EntityType, Identifiability, SubjectRole, TextInput


class RulesTests(unittest.TestCase):
    def detect(self, text, **kwargs):
        source = TextInput(text=text, source_id="rules-source", source_revision="1")
        return source, detect_rules(source, **kwargs)

    def test_vietnamese_mobile_and_landline_shapes(self):
        for value in ("0912345678", "03 1234 5678", "+84 912 345 678", "02412345678", "+84 2412345678"):
            with self.subTest(value=value):
                source, report = self.detect("Gọi " + value + ".")
                self.assertEqual(len(report.findings), 1)
                finding = report.findings[0]
                self.assertEqual(finding.entity_type, EntityType.PHONE)
                self.assertEqual(source.text[finding.span.start:finding.span.end], value)

    def test_phone_does_not_match_embedded_or_overlong_numbers(self):
        for text in ("x0912345678z", "091234567890", "0912 345 678 9", "+840912345678"):
            with self.subTest(text=text):
                self.assertFalse(self.detect(text)[1].findings)

    def test_measurement_units_are_negative_phone_context(self):
        self.assertFalse(self.detect("Kết quả xét nghiệm 0912345678 mg.")[1].findings)
        self.assertEqual(self.detect("SĐT: 0912345678 mg.")[1].findings[0].entity_type, EntityType.PHONE)

    def test_contextual_national_ids_cover_nine_and_twelve_digits(self):
        for text, value in (("CCCD: 012345678901", "012345678901"),
                            ("CMND 123456789", "123456789"),
                            ("Căn cước công dân 0123 4567 8901", "0123 4567 8901")):
            source, report = self.detect(text)
            finding = next(item for item in report.findings if item.entity_type is EntityType.NATIONAL_ID)
            self.assertEqual(source.text[finding.span.start:finding.span.end], value)

    def test_unlabelled_numbers_are_not_assumed_national_ids(self):
        self.assertFalse(self.detect("123456789012")[1].findings)

    def test_email_has_complete_source_boundary(self):
        source, report = self.detect("Email: mau.an+test@example.invalid.")
        finding = report.findings[0]
        self.assertEqual(source.text[finding.span.start:finding.span.end], "mau.an+test@example.invalid")
        self.assertFalse(self.detect("a@example.invalid.123")[1].findings)

    def test_contextual_patient_and_encounter_references(self):
        for text, kind, value in (("Mã bệnh nhân SYN-BN-123.", EntityType.PATIENT_ID, "SYN-BN-123"),
                                  ("patient id: 123", EntityType.PATIENT_ID, "123"),
                                  ("Mã lượt khám VK_456", EntityType.ENCOUNTER_ID, "VK_456"),
                                  ("visit id: V-789", EntityType.ENCOUNTER_ID, "V-789")):
            source, report = self.detect(text)
            self.assertEqual(len(report.findings), 1)
            finding = report.findings[0]
            self.assertIs(finding.entity_type, kind)
            self.assertEqual(source.text[finding.span.start:finding.span.end], value)

    def test_reference_rules_do_not_guess_hospital_formats_or_partial_values(self):
        for text in ("BN-123", "Mã bệnh nhân đau", "Mã bệnh nhân 120/80", "Mã bệnh nhân BN.123"):
            self.assertFalse(any(item.entity_type is EntityType.PATIENT_ID for item in self.detect(text)[1].findings))
        self.assertFalse(self.detect("BHYT SYN-BHYT-123456789")[1].findings)

    def test_dob_requires_cue_and_calendar_validity(self):
        source, report = self.detect("Ngày sinh: 29/02/2000; tái khám 18/11/2026.")
        self.assertEqual(len(report.findings), 1)
        self.assertEqual(source.text[report.findings[0].span.start:report.findings[0].span.end], "29/02/2000")
        self.assertFalse(self.detect("Ngày sinh 31/02/2000")[1].findings)
        self.assertFalse(self.detect("Đánh giá ngày 18/11/2026")[1].findings)

    def test_names_with_and_without_diacritics_and_no_space_after_colon(self):
        for name in ("Nguyễn Văn An", "Nguyen Van An", "Đặng Văn An"):
            source, report = self.detect("Bệnh nhân:" + name + ", đau bụng.")
            self.assertEqual(len(report.findings), 1)
            self.assertEqual(source.text[report.findings[0].span.start:report.findings[0].span.end], name)
            self.assertIs(report.findings[0].identifiability, Identifiability.DIRECT)

    def test_patient_linking_word_variants_are_bounded_to_the_name(self):
        cases = (
            ("Bệnh nhân là Nguyễn Văn An, đau bụng.", "Nguyễn Văn An"),
            ("Bệnh nhân, là Nguyễn Văn An; không đau.", "Nguyễn Văn An"),
            ("Bệnh nhân là: Nguyễn Văn An.", "Nguyễn Văn An"),
            ("benh nhan la Nguyen Van An, dau bung.", "Nguyen Van An"),
        )
        for text, expected in cases:
            with self.subTest(text=text):
                source, report = self.detect(text)
                people = tuple(item for item in report.findings if item.entity_type is EntityType.PERSON)
                self.assertEqual(len(people), 1)
                self.assertEqual(source.text[people[0].span.start:people[0].span.end], expected)

    def test_clinical_abbreviations_and_dose_patterns_bound_names_without_stopword_only_logic(self):
        cases = (
            ("Bệnh nhân Nguyễn Văn An SpO2 98%", "Nguyễn Văn An", "SpO2 98%"),
            ("Bệnh nhân Nguyễn Văn An GCS 15", "Nguyễn Văn An", "GCS 15"),
            ("Bệnh nhân Nguyễn Văn An BMI 25", "Nguyễn Văn An", "BMI 25"),
            ("Bệnh nhân Nguyễn Văn An HbA1c 6.2", "Nguyễn Văn An", "HbA1c 6.2"),
            ("Bệnh nhân Nguyễn Văn An Metformin 500 mg", "Nguyễn Văn An", "Metformin 500 mg"),
            ("Bệnh nhân Nguyễn Văn An Cefalexin 250 mg", "Nguyễn Văn An", "Cefalexin 250 mg"),
            ("Bệnh nhân Nguyễn Văn An HIV dương tính", "Nguyễn Văn An", "HIV dương tính"),
            ("Bệnh nhân Nguyễn Văn An COPD ổn định", "Nguyễn Văn An", "COPD ổn định"),
        )
        for text, expected_name, clinical in cases:
            with self.subTest(text=text):
                source, report = self.detect(text)
                people = tuple(item for item in report.findings if item.entity_type is EntityType.PERSON)
                self.assertEqual(len(people), 1)
                self.assertEqual(source.text[people[0].span.start:people[0].span.end], expected_name)
                self.assertIn(clinical, source.text[people[0].span.end:])

    def test_four_component_names_are_supported_when_a_punctuation_boundary_is_clear(self):
        text = "Bệnh nhân Nguyễn Văn Minh Tấn, đau bụng."
        source, report = self.detect(text)
        person = next(item for item in report.findings if item.entity_type is EntityType.PERSON)
        self.assertEqual(source.text[person.span.start:person.span.end], "Nguyễn Văn Minh Tấn")
        self.assertIs(person.identifiability, Identifiability.DIRECT)

    def test_unfamiliar_fused_boundary_requires_review_instead_of_guessing(self):
        source, report = self.detect("Bệnh nhân Nguyễn Văn An CardioFlag")
        person = next(item for item in report.findings if item.entity_type is EntityType.PERSON)
        self.assertEqual(source.text[person.span.start:person.span.end], "Nguyễn Văn An CardioFlag")
        self.assertIs(person.identifiability, Identifiability.AMBIGUOUS)

    def test_patient_identifier_field_is_not_duplicated_as_a_person(self):
        source, report = self.detect("Mã bệnh nhân SYN-BN-123.")
        self.assertEqual(len(report.findings), 1)
        self.assertIs(report.findings[0].entity_type, EntityType.PATIENT_ID)

    def test_name_subject_roles_are_explicit(self):
        for cue, role in (("Bệnh nhân", SubjectRole.PATIENT), ("Bác sĩ", SubjectRole.CLINICIAN),
                          ("Mẹ bệnh nhân là", SubjectRole.RELATIVE)):
            finding = self.detect(cue + " Nguyễn Văn An, không đau.")[1].findings[0]
            self.assertIs(finding.subject_role, role)

    def test_lowercase_contextual_name_uses_cue_and_name_shape_without_case_assumptions(self):
        source, report = self.detect("bệnh nhân nguyen van an, đau bụng.")
        finding = next(item for item in report.findings if item.entity_type is EntityType.PERSON)
        self.assertEqual(source.text[finding.span.start:finding.span.end], "nguyen van an")
        self.assertIs(finding.identifiability, Identifiability.DIRECT)

    def test_clinical_homographs_are_complete_name_tokens_across_subject_roles(self):
        cases = (
            ("Bệnh nhân Nguyễn Văn Đăng, mạch 92.", "Nguyễn Văn Đăng", SubjectRole.PATIENT),
            ("Bệnh nhân Lê Thị Tiên, không đau.", "Lê Thị Tiên", SubjectRole.PATIENT),
            ("Bác sĩ Nguyễn Văn Đăng, ghi nhận ổn định.", "Nguyễn Văn Đăng", SubjectRole.CLINICIAN),
            ("Bác sĩ Lê Thị Tiên, ghi nhận ổn định.", "Lê Thị Tiên", SubjectRole.CLINICIAN),
            ("Mẹ bệnh nhân là Phạm Văn Đăng, tiền sử ổn.", "Phạm Văn Đăng", SubjectRole.RELATIVE),
            ("Cha bệnh nhân là Trần Thị Tiên, tiền sử ổn.", "Trần Thị Tiên", SubjectRole.RELATIVE),
            ("bac si nguyen van dang, ghi nhan on dinh.", "nguyen van dang", SubjectRole.CLINICIAN),
            ("me benh nhan la pham van tien, tien su on.", "pham van tien", SubjectRole.RELATIVE),
            ("cha benh nhan la tran thi dang, tien su on.", "tran thi dang", SubjectRole.RELATIVE),
        )
        for text, expected, role in cases:
            with self.subTest(text=text):
                source, report = self.detect(text)
                finding = next(item for item in report.findings if item.entity_type is EntityType.PERSON)
                self.assertEqual(source.text[finding.span.start:finding.span.end], expected)
                self.assertIs(finding.subject_role, role)
                self.assertIs(finding.identifiability, Identifiability.DIRECT)

    def test_two_three_and_four_token_names_include_homographic_name_tokens(self):
        cases = (
            ("Bệnh nhân Nguyễn Đăng.", "Nguyễn Đăng"),
            ("Bệnh nhân Nguyễn Văn Đăng.", "Nguyễn Văn Đăng"),
            ("Bệnh nhân Nguyễn Văn Đăng Minh.", "Nguyễn Văn Đăng Minh"),
            ("Bệnh nhân Lê Tiên.", "Lê Tiên"),
            ("Bệnh nhân Lê Thị Tiên.", "Lê Thị Tiên"),
            ("Bệnh nhân Lê Thị Tiên Anh.", "Lê Thị Tiên Anh"),
        )
        for text, expected in cases:
            with self.subTest(text=text):
                source, report = self.detect(text)
                finding = next(item for item in report.findings if item.entity_type is EntityType.PERSON)
                self.assertEqual(source.text[finding.span.start:finding.span.end], expected)
                self.assertIs(finding.identifiability, Identifiability.DIRECT)

    def test_lowercase_unaccented_asr_names_and_nfd_offsets_are_supported(self):
        cases = (
            ("benh nhan nguyen van dang, mach 92.", "nguyen van dang"),
            ("benh nhan le thi tien, khong dau.", "le thi tien"),
            ("Bệnh nhân Nguyễn văn An, đau bụng.", "Nguyễn văn An"),
            ("Bệnh nhân NGUYỄN VĂN đăng, mạch 92.", "NGUYỄN VĂN đăng"),
        )
        for text, expected in cases:
            with self.subTest(text=text):
                source, report = self.detect(text)
                finding = next(item for item in report.findings if item.entity_type is EntityType.PERSON)
                self.assertEqual(source.text[finding.span.start:finding.span.end], expected)
                self.assertIs(finding.identifiability, Identifiability.DIRECT)

        name = unicodedata.normalize("NFD", "Lê Thị Tiên")
        text = "Bệnh nhân " + name + ", không đau."
        source, report = self.detect(text)
        finding = next(item for item in report.findings if item.entity_type is EntityType.PERSON)
        self.assertEqual(source.text[finding.span.start:finding.span.end], name)

    def test_ordinary_dang_and_tien_clinical_phrases_do_not_become_name_tokens(self):
        cases = (
            ("Bệnh nhân Nguyễn Văn đang dùng Metformin 500 mg.", "đang dùng Metformin 500 mg."),
            ("Bệnh nhân Nguyễn Văn tiền sử tăng huyết áp.", "tiền sử tăng huyết áp."),
            ("Bệnh nhân đang dùng thuốc.", "đang dùng thuốc."),
            ("Bệnh nhân có tiền sử đái tháo đường.", "có tiền sử đái tháo đường."),
        )
        for text, clinical in cases:
            with self.subTest(text=text):
                source, report = self.detect(text)
                people = tuple(item for item in report.findings if item.entity_type is EntityType.PERSON)
                self.assertTrue(all(
                    "đang" not in source.text[item.span.start:item.span.end].casefold()
                    and "tiền" not in source.text[item.span.start:item.span.end].casefold()
                    for item in people
                ))
                self.assertIn(clinical, source.text)

    def test_nfd_name_and_repeated_identifiers_use_original_offsets(self):
        name = unicodedata.normalize("NFD", "Nguyễn Văn An")
        source, report = self.detect("Bệnh nhân " + name + "; SĐT 0912345678 và 0912345678.")
        self.assertEqual(len(report.findings), 3)
        first = report.findings[0]
        self.assertEqual(source.text[first.span.start:first.span.end], name)
        self.assertNotEqual(report.findings[1].span, report.findings[2].span)

    def test_spoken_phone_only_supports_explicit_digit_sequence(self):
        value = "không chín không một hai ba bốn năm sáu bảy"
        source, report = self.detect("Số điện thoại là " + value + ".")
        self.assertEqual(len(report.findings), 1)
        self.assertEqual(source.text[report.findings[0].span.start:report.findings[0].span.end], value)
        self.assertFalse(self.detect("Mạch chín mươi hai")[1].findings)
        self.assertFalse(self.detect("Số điện thoại là " + value + " tám.")[1].findings)

    def test_clinical_negatives_and_limits(self):
        text = "Mạch 92 lần/phút; huyết áp 120/80 mmHg; Không dị ứng thuốc; Amoxicillin 500 mg; Đau bụng 3 ngày; Mẹ bệnh nhân có tiền sử đái tháo đường."
        self.assertFalse(self.detect(text)[1].findings)
        with self.assertRaises(ResourceLimitError):
            self.detect("0912345678; 0912345678", max_findings=1)
        with self.assertRaises(ValueError):
            self.detect("", max_findings=True)

    def test_medication_after_a_name_is_not_consumed_as_another_name_token(self):
        source, report = self.detect("Bệnh nhân Nguyễn Văn An Amoxicillin 500 mg.")
        finding = report.findings[0]
        self.assertEqual(source.text[finding.span.start:finding.span.end], "Nguyễn Văn An")

    def test_injected_analysis_view_is_revalidated_at_rule_boundary(self):
        source = TextInput(text="Bệnh nhân Nguyễn Văn An.", source_id="mapping-test", source_revision="1")
        view = build_view(source)
        object.__setattr__(view, "offsets", tuple(reversed(view.offsets)))
        with self.assertRaises(ValueError):
            detect_rules(source, view=view)
