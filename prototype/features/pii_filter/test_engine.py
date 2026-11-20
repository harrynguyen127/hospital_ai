"""End-to-end review drafts and fail-closed fault injection, without models."""

from dataclasses import replace
import unittest
from unittest.mock import Mock, patch

from features.pii_filter.deidentification import POLICY_VERSION
from features.pii_filter.engine import DetectorSpec, EngineLimits, process_text
from features.pii_filter.rules import DETECTOR_ID
from features.pii_filter.schema import (
    AssessmentStatus, DetectorStatus, EntityType, OutboundRestriction, PolicyAction,
    ReasonCode, ReplacementDecision, SourceSpan, TextInput,
)
from features.pii_filter.test_aggregation import make_report


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.source = TextInput(text="Không đau ngực.", source_id="engine-source", source_revision="1")

    def spec(self, callback, **overrides):
        return DetectorSpec(**(dict(detector_id="extra", detector_version="1",
                                    supported_entities=(EntityType.PERSON,), detect=callback) | overrides))

    def assert_failed(self, result, reason):
        self.assertIs(result.assessment.status, AssessmentStatus.FAILED)
        self.assertIsNone(result.output_text)
        self.assertIn(reason, result.assessment.reason_codes)
        self.assertIs(result.assessment.outbound_restriction, OutboundRestriction.PROHIBITED)
        self.assertFalse(result.external_egress_authorized)

    def test_required_clinical_phrases_are_literally_preserved(self):
        phrases = ("Mạch 92 lần/phút", "Huyết áp 120/80 mmHg", "Không dị ứng thuốc",
                   "Amoxicillin 500 mg", "Đau bụng 3 ngày",
                   "Mẹ bệnh nhân có tiền sử đái tháo đường", "mạch 92, sửa lại 90")
        for phrase in phrases:
            with self.subTest(phrase=phrase):
                source = replace(self.source, text=phrase)
                result = process_text(source)
                self.assertEqual(result.output_text, phrase)
                self.assertEqual(result.decisions, ())
                self.assertIs(result.assessment.status, AssessmentStatus.REVIEW_REQUIRED)

    def test_mixed_identifiers_are_redacted_but_clinical_suffix_is_preserved(self):
        source = replace(self.source, text="Bệnh nhân Nguyễn Văn An; SĐT 0912345678; mạch 92, sửa lại 90.")
        result = process_text(source)
        self.assertEqual(result.output_text, "Bệnh nhân [PII]; SĐT [PII]; mạch 92, sửa lại 90.")
        self.assertFalse(result.external_egress_authorized)

    def test_p1_a_name_before_spo2_preserves_the_alphanumeric_clinical_token(self):
        source = replace(self.source, text="Bệnh nhân Nguyễn Văn An SpO2 98%")
        result = process_text(source)
        self.assertEqual(result.output_text, "Bệnh nhân [PII] SpO2 98%")

    def test_p1_b_patient_linking_word_allows_self_identification(self):
        source = replace(self.source, text="Bệnh nhân là Nguyễn Văn An, đau bụng.")
        result = process_text(source)
        self.assertEqual(result.output_text, "Bệnh nhân là [PII], đau bụng.")

    def test_p1_c_person_boundary_preserves_medication_and_diagnosis(self):
        cases = (
            ("Bệnh nhân Nguyễn Văn An Metformin 500 mg", "Bệnh nhân [PII] Metformin 500 mg"),
            ("Bệnh nhân Nguyễn Văn An HIV dương tính", "Bệnh nhân [PII] HIV dương tính"),
        )
        for text, expected in cases:
            with self.subTest(text=text):
                result = process_text(replace(self.source, text=text))
                self.assertEqual(result.output_text, expected)

    def test_p1_name_dang_homograph_is_not_partially_redacted(self):
        text = "Bệnh nhân Nguyễn Văn Đăng, mạch 92."
        result = process_text(replace(self.source, text=text))
        self.assertEqual(result.output_text, "Bệnh nhân [PII], mạch 92.")

    def test_p1_name_tien_homograph_is_not_partially_redacted(self):
        text = "Bệnh nhân Lê Thị Tiên, không đau."
        result = process_text(replace(self.source, text=text))
        self.assertEqual(result.output_text, "Bệnh nhân [PII], không đau.")

    def test_unreliable_name_clinical_boundary_stays_visible_and_requires_review(self):
        source = replace(self.source, text="Bệnh nhân Nguyễn Văn An CardioFlag")
        result = process_text(source)
        self.assertEqual(result.output_text, source.text)
        self.assertTrue(any(item.action is PolicyAction.REVIEW for item in result.decisions))
        self.assertIn(ReasonCode.AMBIGUOUS_ENTITY, result.assessment.reason_codes)
        self.assertIn(ReasonCode.POSSIBLE_RESIDUAL_PII, result.assessment.reason_codes)
        self.assertFalse(result.external_egress_authorized)

    def test_unaccented_name_versus_ongoing_verb_is_explicitly_ambiguous(self):
        source = replace(self.source, text="benh nhan nguyen van dang dung metformin 500 mg.")
        result = process_text(source)
        self.assertEqual(result.output_text, source.text)
        self.assertTrue(any(item.action is PolicyAction.REVIEW for item in result.decisions))
        self.assertIn(ReasonCode.AMBIGUOUS_ENTITY, result.assessment.reason_codes)
        self.assertIn(ReasonCode.POSSIBLE_RESIDUAL_PII, result.assessment.reason_codes)
        self.assertFalse(result.external_egress_authorized)

    def test_name_homograph_before_administrative_verb_requires_review(self):
        source = replace(self.source, text="Bệnh nhân Nguyễn Văn Đăng ký khám.")
        result = process_text(source)
        self.assertEqual(result.output_text, source.text)
        self.assertTrue(any(item.action is PolicyAction.REVIEW for item in result.decisions))
        self.assertIn(ReasonCode.AMBIGUOUS_ENTITY, result.assessment.reason_codes)
        self.assertFalse(result.external_egress_authorized)

    def test_lowercase_unknown_post_name_token_is_reviewed_not_swallowed(self):
        source = replace(self.source, text="Bệnh nhân Nguyễn Văn An clinicalterm")
        result = process_text(source)
        self.assertEqual(result.output_text, source.text)
        self.assertTrue(any(item.action is PolicyAction.REVIEW for item in result.decisions))
        self.assertIn(ReasonCode.AMBIGUOUS_ENTITY, result.assessment.reason_codes)
        self.assertFalse(result.external_egress_authorized)

    def test_p1_d_partial_identifier_suffix_after_placeholder_is_residual_risk(self):
        source = replace(self.source, text="BHYT: ABC123456789")
        span = SourceSpan(start=6, end=9)
        report = make_report(source, (span,), detector="extra",
                             kinds=(EntityType.HEALTH_INSURANCE_ID,))
        detector = self.spec(
            lambda current: report,
            supported_entities=(EntityType.HEALTH_INSURANCE_ID,),
        )

        result = process_text(source, extra_detectors=(detector,))

        self.assertEqual(result.output_text, "BHYT: [PII]123456789")
        self.assertIn(ReasonCode.POSSIBLE_RESIDUAL_PII, result.assessment.reason_codes)
        self.assertFalse(result.external_egress_authorized)

    def test_empty_input_is_an_explicit_review_result(self):
        result = process_text(replace(self.source, text=""))
        self.assertEqual(result.output_text, "")
        self.assertEqual(result.detector_reports[0].coverage, ())
        self.assertIs(result.assessment.status, AssessmentStatus.REVIEW_REQUIRED)

    def test_repeated_calls_are_deterministic(self):
        self.assertEqual(process_text(self.source), process_text(self.source))

    def test_very_long_input_is_rejected_before_normalization(self):
        with patch("features.pii_filter.engine.build_view") as normalization:
            result = process_text(replace(self.source, text="a" * 32_001))
        normalization.assert_not_called()
        self.assert_failed(result, ReasonCode.RESOURCE_LIMIT)

    def test_repeated_identifiers_exceeding_budget_do_not_return_a_partial_mask(self):
        result = process_text(replace(self.source, text="0912345678; " * 5), limits=EngineLimits(max_findings=4))
        self.assert_failed(result, ReasonCode.RESOURCE_LIMIT)

    def test_excessive_detectors_fail_before_invocation(self):
        callback = Mock()
        specs = tuple(self.spec(callback, detector_id=f"extra-{index}") for index in range(5))
        self.assert_failed(process_text(self.source, extra_detectors=specs), ReasonCode.RESOURCE_LIMIT)
        callback.assert_not_called()

    def test_invalid_requests_and_boolean_limits_raise_sanitized_errors(self):
        with self.assertRaises(TypeError):
            process_text(self.source.text)
        for change in ({"max_findings": True}, {"max_characters": 0}, {"max_extra_detectors": 9}):
            with self.assertRaises(ValueError):
                EngineLimits(**change)

    def test_detector_exception_has_no_raw_exception_text_or_fallback_output(self):
        callback = Mock(side_effect=RuntimeError(self.source.text))
        result = process_text(self.source, extra_detectors=(self.spec(callback),))
        self.assert_failed(result, ReasonCode.DETECTOR_FAILED)
        self.assertNotIn(self.source.text, repr(result))

    def test_invalid_detector_output_types_are_explicit_failures(self):
        for value in (None, {}, [], "raw text", True):
            with self.subTest(value_type=type(value).__name__):
                result = process_text(self.source, extra_detectors=(self.spec(lambda source: value),))
                self.assert_failed(result, ReasonCode.INVALID_DETECTOR_OUTPUT)

    def test_unknown_entity_label_is_not_coerced_or_dropped(self):
        report = make_report(self.source, (SourceSpan(start=0, end=5),), detector="extra")
        object.__setattr__(report.findings[0], "entity_type", "UNKNOWN-LABEL")
        result = process_text(self.source, extra_detectors=(self.spec(lambda source: report),))
        self.assert_failed(result, ReasonCode.UNKNOWN_LABEL)

    def test_invalid_source_offsets_are_explicit_failures(self):
        report = make_report(self.source, (SourceSpan(start=0, end=5),), detector="extra")
        object.__setattr__(report.findings[0].span, "end", 100)
        result = process_text(self.source, extra_detectors=(self.spec(lambda source: report),))
        self.assert_failed(result, ReasonCode.INVALID_DETECTOR_OUTPUT)

    def test_stale_source_revision_does_not_rebind_report(self):
        other = replace(self.source, source_revision="2")
        report = make_report(other, (), detector="extra")
        result = process_text(self.source, extra_detectors=(self.spec(lambda source: report),))
        self.assert_failed(result, ReasonCode.CONTEXT_MISMATCH)
        self.assertEqual(report.source_revision, "2")

    def test_missing_coverage_is_partial_not_full_assessment(self):
        report = replace(make_report(self.source, (), detector="extra"), source=self.source,
                         status=DetectorStatus.PARTIAL, coverage=(), reason_codes=(ReasonCode.INCOMPLETE_COVERAGE,))
        result = process_text(self.source, extra_detectors=(self.spec(lambda source: report),))
        self.assertIs(result.assessment.status, AssessmentStatus.PARTIAL)
        self.assertEqual(result.output_text, self.source.text)
        self.assertIn(ReasonCode.INCOMPLETE_COVERAGE, result.assessment.reason_codes)

    def test_falsely_complete_coverage_is_rejected(self):
        report = make_report(self.source, (), detector="extra")
        object.__setattr__(report, "coverage", ())
        result = process_text(self.source, extra_detectors=(self.spec(lambda source: report),))
        self.assert_failed(result, ReasonCode.INVALID_DETECTOR_OUTPUT)

    def test_contradictory_policy_plan_never_returns_a_sanitized_success(self):
        span = SourceSpan(start=0, end=5)
        decisions = tuple(ReplacementDecision(source=self.source, span=span, action=action, policy_version=POLICY_VERSION)
                          for action in (PolicyAction.PRESERVE, PolicyAction.REDACT))
        with patch("features.pii_filter.engine.plan_redactions", return_value=decisions):
            result = process_text(self.source)
        self.assert_failed(result, ReasonCode.INVALID_DETECTOR_OUTPUT)

    def test_mapping_failure_is_not_retried_by_the_failure_path(self):
        with patch("features.pii_filter.engine.build_view", side_effect=ValueError("bad mapping")) as normalization:
            result = process_text(self.source)
        self.assertEqual(normalization.call_count, 1)
        self.assert_failed(result, ReasonCode.INVALID_OFFSET_MAPPING)

    def test_render_and_aggregation_failures_have_no_output(self):
        for target in ("render", "aggregate"):
            with self.subTest(target=target), patch("features.pii_filter.engine." + target, side_effect=MemoryError()):
                result = process_text(self.source)
                self.assert_failed(result, ReasonCode.INVALID_DETECTOR_OUTPUT)

    def test_excessive_callback_findings_count_before_deduplication(self):
        report = make_report(self.source, (SourceSpan(start=0, end=5),), detector="extra")
        report = replace(report, source=self.source, findings=report.findings * 3)
        result = process_text(self.source, extra_detectors=(self.spec(lambda source: report),), limits=EngineLimits(max_findings=2))
        self.assert_failed(result, ReasonCode.RESOURCE_LIMIT)

    def test_duplicate_detector_identity_is_rejected_before_invocation(self):
        callback = Mock()
        for specs in ((self.spec(callback), self.spec(callback)), (self.spec(callback, detector_id=DETECTOR_ID),)):
            self.assert_failed(process_text(self.source, extra_detectors=specs), ReasonCode.INVALID_DETECTOR_OUTPUT)
        callback.assert_not_called()

    def test_detector_declaration_must_match_report(self):
        report = make_report(self.source, (), detector="wrong-id")
        result = process_text(self.source, extra_detectors=(self.spec(lambda source: report),))
        self.assert_failed(result, ReasonCode.INVALID_DETECTOR_OUTPUT)

    def test_invalid_extra_detector_container_is_a_failed_result(self):
        for specs in ([], (None,), (lambda source: None,)):
            self.assert_failed(process_text(self.source, extra_detectors=specs), ReasonCode.INVALID_DETECTOR_OUTPUT)

    def test_incomplete_detector_spec_is_not_a_crashing_failure_path(self):
        spec = object.__new__(DetectorSpec)
        self.assert_failed(process_text(self.source, extra_detectors=(spec,)), ReasonCode.INVALID_DETECTOR_OUTPUT)

    def test_long_input_within_budget_preserves_all_clinical_characters(self):
        text = "Mạch 92 lần/phút. " * 500
        result = process_text(replace(self.source, text=text))
        self.assertEqual(result.output_text, text)
        self.assertIs(result.assessment.status, AssessmentStatus.REVIEW_REQUIRED)

    def test_unavailable_detector_is_explicitly_partial(self):
        report = replace(make_report(self.source, (), detector="extra"), source=self.source,
                         status=DetectorStatus.UNAVAILABLE, coverage=(), reason_codes=(ReasonCode.DETECTOR_UNAVAILABLE,))
        result = process_text(self.source, extra_detectors=(self.spec(lambda source: report),))
        self.assertIs(result.assessment.status, AssessmentStatus.PARTIAL)
        self.assertIn(ReasonCode.DETECTOR_UNAVAILABLE, result.assessment.reason_codes)

    def test_unexpected_unicode_does_not_change_unmasked_content(self):
        source = replace(self.source, text="🙂\u200b Không dị ứng thuốc\r\nSĐT: 0912345678.")
        result = process_text(source)
        self.assertEqual(result.output_text, "🙂\u200b Không dị ứng thuốc\r\nSĐT: [PII].")
