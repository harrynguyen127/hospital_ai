"""Role-aware, text-only clinical transcript fixture behavior."""

import unittest

from features.pii_filter.engine import process_text
from features.pii_filter.schema import AssessmentStatus, EntityType, ReasonCode, SubjectRole
from pii_runtime.evaluation.dataset import ClinicalCategory
from pii_runtime.evaluation.workflow_scenarios import (
    ScenarioType, SpeakerRole, get_workflow_fixtures, materialize,
)


class WorkflowScenarioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixtures = tuple(materialize(item) for item in get_workflow_fixtures())

    def by_type(self, kind):
        return next(item for item in self.fixtures if item.fixture.scenario_type is kind)

    def test_role_metadata_is_separate_from_subject_annotations_and_missing_stays_unknown(self):
        conversation = self.by_type(ScenarioType.DOCTOR_PATIENT_CONVERSATION)
        self.assertIs(conversation.fixture.turns[0].speaker_role, SpeakerRole.DOCTOR)
        self.assertIsNone(conversation.fixture.turns[6].speaker_role)
        relative = next(item for item in conversation.entities if item.subject_role is SubjectRole.RELATIVE)
        self.assertEqual(conversation.source.text[relative.span.start:relative.span.end], "Lê Thị Mai")
        unknown_phone = next(item for item in conversation.entities if item.entity_type is EntityType.PHONE)
        self.assertIs(unknown_phone.subject_role, SubjectRole.UNKNOWN)
        self.assertEqual(conversation.source.text[unknown_phone.span.start:unknown_phone.span.end], "0912345678")
        result = process_text(conversation.source)
        self.assertTrue(any(
            finding.entity_type is EntityType.PHONE and finding.span == unknown_phone.span
            for report in result.detector_reports for finding in report.findings
        ))

    def test_original_offsets_address_spans_in_the_complete_multiturn_transcript(self):
        for fixture in self.fixtures:
            with self.subTest(scenario=fixture.fixture.scenario_id):
                for entity in fixture.entities:
                    value = fixture.source.text[entity.span.start:entity.span.end]
                    self.assertTrue(value)
                for clinical in fixture.clinical:
                    value = fixture.source.text[clinical.span.start:clinical.span.end]
                    self.assertTrue(value)
        conversation = self.by_type(ScenarioType.DOCTOR_PATIENT_CONVERSATION)
        names = [item for item in conversation.entities if item.entity_type is EntityType.PERSON]
        self.assertEqual([conversation.source.text[item.span.start:item.span.end] for item in names],
                         ["Nguyễn Văn An", "Lê Thị Mai", "Nguyễn Văn An"])

    def test_doctor_patient_conversation_redacts_supported_identifiers_and_flags_spoken_dob(self):
        fixture = self.by_type(ScenarioType.DOCTOR_PATIENT_CONVERSATION)
        result = process_text(fixture.source)
        self.assertIs(result.assessment.status, AssessmentStatus.REVIEW_REQUIRED)
        self.assertIn(ReasonCode.POSSIBLE_RESIDUAL_PII, result.assessment.reason_codes)
        self.assertFalse(result.external_egress_authorized)
        self.assertEqual(result.output_text.count("[PII]"), 4)
        for protected in (
                "Amoxicillin 500 mg", "Không dị ứng thuốc", "đau bụng ba ngày",
                "không phải ba tuần", "có tiền sử đái tháo đường", "mạch 92, sửa lại 90"):
            self.assertIn(protected, result.output_text)
        self.assertIn("mười hai tháng ba năm một nghìn chín trăm chín mươi", result.output_text)

    def test_nurse_readback_keeps_spo2_medication_and_clinical_values_next_to_ids(self):
        fixture = self.by_type(ScenarioType.NURSE_CHART_READBACK)
        result = process_text(fixture.source)
        self.assertIs(result.assessment.status, AssessmentStatus.REVIEW_REQUIRED)
        self.assertFalse(result.external_egress_authorized)
        self.assertIn("[PII] SpO2 98%", result.output_text)
        self.assertIn("[PII] mạch 92 lần/phút", result.output_text)
        self.assertIn("[PII] mạch 92 lần/phút; mã lượt khám [PII]", result.output_text)
        self.assertIn("thuốc của bệnh nhân [PII] Metformin 500 mg", result.output_text)
        self.assertIn("HIV dương tính", result.output_text)

    def test_hiv_positive_is_annotated_as_diagnosis_or_lab_result(self):
        fixture = self.by_type(ScenarioType.NURSE_CHART_READBACK)
        finding = next(item for item in fixture.clinical
                       if fixture.source.text[item.span.start:item.span.end].endswith("HIV dương tính"))
        self.assertIs(finding.category, ClinicalCategory.DIAGNOSIS_OR_LAB_RESULT)

    def test_nurse_fixture_marks_unsupported_insurance_and_partial_probe(self):
        fixture = self.by_type(ScenarioType.NURSE_CHART_READBACK)
        self.assertEqual(len(fixture.unsupported_cases), 1)
        span, reason = fixture.unsupported_cases[0]
        self.assertEqual(fixture.source.text[span.start:span.end], "ABC123456789")
        self.assertIn("No BHYT", reason)
        self.assertEqual(len(fixture.partial_predictions), 1)
        partial_span, kind = fixture.partial_predictions[0]
        self.assertEqual(fixture.source.text[partial_span.start:partial_span.end], "ABC")
        self.assertIs(kind, EntityType.HEALTH_INSURANCE_ID)


if __name__ == "__main__":
    unittest.main()
