"""Local assessment statuses, residual indicators, and coverage limitations."""

from dataclasses import replace
import unittest

from features.pii_filter.aggregation import aggregate
from features.pii_filter.deidentification import plan_redactions, render
from features.pii_filter.risk import assess
from features.pii_filter.rules import detect_rules
from features.pii_filter.schema import (
    AssessmentStatus, DetectorStatus, EntityType, OutboundRestriction, ReasonCode,
    SourceSpan, TextInput,
)
from features.pii_filter.test_aggregation import make_report


class RiskTests(unittest.TestCase):
    def setUp(self):
        self.source = TextInput(text="Không đau ngực.", source_id="risk-source", source_revision="1")
        self.rules = detect_rules(self.source)

    def test_rules_only_never_claim_comprehensive_assurance(self):
        assessment = assess(self.source, (self.rules,), (), (), self.source.text)
        self.assertIs(assessment.status, AssessmentStatus.REVIEW_REQUIRED)
        self.assertIn(ReasonCode.UNQUALIFIED_PROFILE, assessment.reason_codes)
        self.assertIn(ReasonCode.UNSUPPORTED_CATEGORIES, assessment.reason_codes)
        self.assertIs(assessment.outbound_restriction, OutboundRestriction.PROHIBITED)

    def test_unavailable_detector_makes_assessment_partial(self):
        unavailable = replace(make_report(self.source, (), detector="optional"), source=self.source,
                              status=DetectorStatus.UNAVAILABLE, coverage=(),
                              reason_codes=(ReasonCode.DETECTOR_UNAVAILABLE,))
        assessment = assess(self.source, (self.rules, unavailable), (), (), self.source.text)
        self.assertIs(assessment.status, AssessmentStatus.PARTIAL)
        self.assertIn(ReasonCode.DETECTOR_UNAVAILABLE, assessment.reason_codes)

    def test_spatially_partial_report_cannot_become_complete(self):
        partial = replace(make_report(self.source, (), detector="optional"), source=self.source,
                          status=DetectorStatus.PARTIAL, coverage=(SourceSpan(start=0, end=2),),
                          reason_codes=(ReasonCode.INCOMPLETE_COVERAGE,))
        assessment = assess(self.source, (self.rules, partial), (), (), self.source.text)
        self.assertIs(assessment.status, AssessmentStatus.PARTIAL)

    def test_failed_or_missing_required_detector_cannot_succeed(self):
        failed = replace(self.rules, source=self.source, status=DetectorStatus.FAILED,
                         coverage=(), reason_codes=(ReasonCode.DETECTOR_FAILED,))
        self.assertIs(assess(self.source, (failed,), (), (), None).status, AssessmentStatus.FAILED)
        self.assertIs(assess(self.source, (), (), (), self.source.text).status, AssessmentStatus.FAILED)

    def test_declared_full_taxonomy_does_not_remove_qualification_limit(self):
        extra = replace(make_report(self.source, (), detector="all-labels"), source=self.source,
                        supported_entities=tuple(EntityType))
        assessment = assess(self.source, (self.rules, extra), (), (), self.source.text)
        self.assertNotIn(ReasonCode.UNSUPPORTED_CATEGORIES, assessment.reason_codes)
        self.assertIn(ReasonCode.UNQUALIFIED_PROFILE, assessment.reason_codes)
        self.assertIs(assessment.status, AssessmentStatus.REVIEW_REQUIRED)

    def test_residual_phone_is_reported_even_if_original_report_was_complete(self):
        assessment = assess(self.source, (self.rules,), (), (), "Gọi 0912345678.")
        self.assertIn(ReasonCode.POSSIBLE_RESIDUAL_PII, assessment.reason_codes)

    def test_unsupported_or_invalid_identifier_cues_require_review(self):
        for text in ("BHYT SYN-BHYT-123", "Địa chỉ: đường Mô Phỏng", "Ngày sinh 31/02/2000"):
            with self.subTest(text=text):
                assessment = assess(self.source, (self.rules,), (), (), text)
                self.assertIn(ReasonCode.POSSIBLE_RESIDUAL_PII, assessment.reason_codes)

    def test_complete_placeholder_stops_at_the_next_explicit_field_delimiter(self):
        assessment = assess(self.source, (self.rules,), (), (), "BHYT: [PII]; mạch 92 lần/phút")
        self.assertNotIn(ReasonCode.POSSIBLE_RESIDUAL_PII, assessment.reason_codes)

    def test_successful_redaction_does_not_erase_entity_conflicts(self):
        span = SourceSpan(start=0, end=5)
        extra = make_report(self.source, (span, span), kinds=(EntityType.PERSON, EntityType.PATIENT_ID))
        reports = (self.rules, extra)
        groups = aggregate(self.source, reports)
        decisions = plan_redactions(self.source, groups)
        assessment = assess(self.source, reports, groups, decisions, render(self.source, decisions))
        self.assertIn(ReasonCode.UNRESOLVED_CONFLICT, assessment.reason_codes)
        self.assertIs(assessment.status, AssessmentStatus.REVIEW_REQUIRED)

    def test_explicit_processing_failure_is_failed_not_a_review_success(self):
        assessment = assess(self.source, (self.rules,), (), (), None,
                            failure_reasons=(ReasonCode.RESOURCE_LIMIT,))
        self.assertIs(assessment.status, AssessmentStatus.FAILED)
        self.assertIn(ReasonCode.RESOURCE_LIMIT, assessment.reason_codes)
