"""Contract invariants and malicious/malformed detector boundary tests."""

from dataclasses import FrozenInstanceError, fields, replace
from itertools import permutations
from pathlib import Path
import sys
import unicodedata
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from features.pii_filter.schema import (
    SCHEMA_VERSION, TAXONOMY_VERSION, AssessmentStatus, DetectorReport,
    DetectorStatus, EntityFinding, EntityType, Identifiability, OffsetUnit,
    OutboundRestriction, PolicyAction, PrivacyAssessment, PrivacyResult,
    ReasonCode, ReplacementDecision, SourceSpan, SubjectRole, TextInput,
    validate_detector_report,
)


class SchemaTests(unittest.TestCase):
    def setUp(self):
        self.source = TextInput(text="An nói không đau.", source_id="source-1", source_revision="rev-1")

    def finding(self, **overrides):
        values = dict(source=self.source, span=SourceSpan(start=0, end=2), entity_type=EntityType.PERSON,
                      subject_role=SubjectRole.PATIENT, identifiability=Identifiability.DIRECT,
                      detector_id="fake", detector_version="1")
        return EntityFinding(**(values | overrides))

    def report(self, **overrides):
        values = dict(source=self.source, detector_id="fake", detector_version="1",
                      status=DetectorStatus.COMPLETE, supported_entities=(EntityType.PERSON,), findings=(self.finding(),),
                      coverage=(SourceSpan(start=0, end=len(self.source.text)),))
        return DetectorReport(**(values | overrides))

    def assessment(self, **overrides):
        values = dict(source=self.source, status=AssessmentStatus.REVIEW_REQUIRED,
                      profile_id="research", profile_version="1", required_detectors=("fake",),
                      reason_codes=(ReasonCode.UNQUALIFIED_PROFILE,))
        return PrivacyAssessment(**(values | overrides))

    def decision(self, **overrides):
        values = dict(source=self.source, span=SourceSpan(start=0, end=2), action=PolicyAction.REDACT, policy_version="1")
        return ReplacementDecision(**(values | overrides))

    def result(self, **overrides):
        values = dict(source=self.source, detector_reports=(self.report(),), decisions=(self.decision(),),
                      assessment=self.assessment(), policy_version="1")
        return PrivacyResult(**(values | overrides))

    def test_taxonomy_is_versioned_and_exact(self):
        expected = {"PERSON", "PHONE", "EMAIL", "NATIONAL_ID", "PASSPORT", "HEALTH_INSURANCE_ID",
                    "PATIENT_ID", "ENCOUNTER_ID", "DATE_OF_BIRTH", "ADDRESS", "GEO_COORDINATE",
                    "ACCOUNT_ID", "FINANCIAL_ID", "CONTACT_URL", "ORGANIZATION", "DATE", "TIME",
                    "AGE", "OCCUPATION", "RARE_CONTEXT", "UNKNOWN_IDENTIFIER"}
        self.assertEqual({item.value for item in EntityType}, expected)
        self.assertEqual(self.source.taxonomy_version, TAXONOMY_VERSION)
        self.assertEqual(self.source.schema_version, SCHEMA_VERSION)

    def test_contracts_are_frozen_and_nested_collections_are_tuples(self):
        objects = (self.source, SourceSpan(start=0, end=2), self.finding(), self.report(),
                   self.decision(), self.assessment(), self.result())
        for item in objects:
            with self.subTest(contract=type(item).__name__):
                with self.assertRaises(FrozenInstanceError):
                    setattr(item, fields(item)[0].name, None)
        with self.assertRaises(TypeError):
            self.report(findings=[self.finding()])

    def test_text_input_rejects_non_text(self):
        for text in (None, b"An", 12, True):
            with self.subTest(value_type=type(text).__name__), self.assertRaises(TypeError):
                TextInput(text=text, source_id="source-1", source_revision="1")

    def test_input_requires_technical_identity_and_revision(self):
        for key in ("source_id", "source_revision"):
            for value in ("", "raw clinical phrase", None, True):
                with self.subTest(key=key, value_type=type(value).__name__), self.assertRaises(ValueError):
                    replace(self.source, **{key: value})

    def test_unknown_versions_and_offset_units_are_rejected(self):
        for key, value in (("schema_version", "2"), ("taxonomy_version", "2"), ("offset_unit", "utf16")):
            with self.subTest(key=key), self.assertRaises((ValueError, TypeError)):
                replace(self.source, **{key: value})

    def test_span_rejects_boolean_float_and_string_offsets(self):
        for key in ("start", "end"):
            for value in (True, False, 1.0, "1", None):
                with self.subTest(key=key, value_type=type(value).__name__), self.assertRaises(TypeError):
                    SourceSpan(**({"start": 0, "end": 2} | {key: value}))

    def test_span_rejects_empty_negative_and_reversed_ranges(self):
        for start, end in ((-1, 2), (0, 0), (3, 2)):
            with self.subTest(start=start, end=end), self.assertRaises(ValueError):
                SourceSpan(start=start, end=end)

    def test_bounds_are_checked_against_original_text(self):
        with self.assertRaises(ValueError):
            self.finding(span=SourceSpan(start=0, end=100))
        with self.assertRaises(TypeError):
            self.finding(span={"start": 0, "end": 2})

    def test_nfd_offsets_are_not_silently_normalized(self):
        text = "🙂 " + unicodedata.normalize("NFD", "Nguyễn")
        source = TextInput(text=text, source_id="unicode", source_revision="1")
        span = SourceSpan(start=2, end=len(text))
        span.validate_for(source)
        self.assertEqual(source.text[span.start:span.end], unicodedata.normalize("NFD", "Nguyễn"))
        self.assertGreater(span.end, len(unicodedata.normalize("NFC", text)))
        self.assertEqual(source.offset_unit, OffsetUnit.UNICODE_CODE_POINT)

    def test_finding_requires_explicit_enums(self):
        for key, value in (("entity_type", "PERSON"), ("subject_role", "patient"), ("identifiability", "direct")):
            with self.subTest(key=key), self.assertRaises(TypeError):
                self.finding(**{key: value})

    def test_finding_cannot_cross_source_or_revision(self):
        for change in ({"source_id": "source-2"}, {"source_revision": "rev-2"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.report(findings=(self.finding(source=replace(self.source, **change)),))

    def test_finding_provenance_must_match_report(self):
        for change in ({"detector_id": "different"}, {"detector_version": "2"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.report(findings=(self.finding(**change),))

    def test_declared_entity_coverage_is_explicit_and_enforced(self):
        for supported in ((), (EntityType.PHONE,), (EntityType.PERSON, EntityType.PERSON)):
            with self.subTest(supported=supported), self.assertRaises(ValueError):
                self.report(supported_entities=supported)
        with self.assertRaises(TypeError):
            self.report(supported_entities=("PERSON",))

    def test_complete_report_requires_full_coverage(self):
        for coverage in ((), (SourceSpan(start=0, end=2),)):
            with self.subTest(coverage=coverage), self.assertRaises(ValueError):
                self.report(coverage=coverage)

    def test_coverage_rejects_overlap_disorder_and_out_of_bounds(self):
        invalid = ((SourceSpan(start=0, end=5), SourceSpan(start=4, end=len(self.source.text))),
                   (SourceSpan(start=3, end=5), SourceSpan(start=0, end=2)),
                   (SourceSpan(start=0, end=100),))
        for coverage in invalid:
            with self.subTest(coverage=coverage), self.assertRaises(ValueError):
                self.report(coverage=coverage)

    def test_adjacent_coverage_is_allowed(self):
        report = self.report(coverage=(SourceSpan(start=0, end=1), SourceSpan(start=1, end=len(self.source.text))))
        self.assertIs(validate_detector_report(self.source, report), report)

    def test_findings_cannot_occupy_unprocessed_gaps(self):
        with self.assertRaises(ValueError):
            self.report(status=DetectorStatus.PARTIAL, coverage=(SourceSpan(start=3, end=5),),
                        reason_codes=(ReasonCode.INCOMPLETE_COVERAGE,))

    def test_partial_failed_and_unavailable_require_reasons(self):
        for status in (DetectorStatus.PARTIAL, DetectorStatus.FAILED, DetectorStatus.UNAVAILABLE):
            with self.subTest(status=status), self.assertRaises(ValueError):
                self.report(status=status, findings=(), coverage=())

    def test_unavailable_detector_cannot_claim_coverage(self):
        with self.assertRaises(ValueError):
            self.report(status=DetectorStatus.UNAVAILABLE, reason_codes=(ReasonCode.DETECTOR_UNAVAILABLE,))
        report = self.report(status=DetectorStatus.UNAVAILABLE, findings=(), coverage=(),
                             reason_codes=(ReasonCode.DETECTOR_UNAVAILABLE,))
        self.assertEqual(report.findings, ())

    def test_partial_report_can_preserve_valid_partial_findings(self):
        report = self.report(status=DetectorStatus.PARTIAL, coverage=(SourceSpan(start=0, end=2),),
                             reason_codes=(ReasonCode.INCOMPLETE_COVERAGE,))
        self.assertEqual(len(report.findings), 1)

    def test_complete_report_rejects_failure_codes(self):
        with self.assertRaises(ValueError):
            self.report(reason_codes=(ReasonCode.DETECTOR_FAILED,))

    def test_empty_source_has_empty_complete_coverage(self):
        empty = replace(self.source, text="")
        self.report(source=empty, findings=(), coverage=())
        with self.assertRaises(ValueError):
            self.report(source=empty, findings=(), coverage=(SourceSpan(start=0, end=1),))

    def test_untrusted_boundary_rejects_duck_types_and_collections(self):
        for value in (None, {}, [], object(), (self.finding(),)):
            with self.subTest(value_type=type(value).__name__), self.assertRaises(TypeError):
                validate_detector_report(self.source, value)

    def test_untrusted_boundary_revalidates_nested_fields(self):
        report = self.report()
        object.__setattr__(report.findings[0].span, "start", True)
        with self.assertRaises(TypeError):
            validate_detector_report(self.source, report)

    def test_untrusted_boundary_checks_revision_without_rebinding(self):
        report = self.report()
        with self.assertRaises(ValueError):
            validate_detector_report(replace(self.source, source_revision="2"), report)
        self.assertEqual(report.source_revision, "rev-1")

    def test_raw_diagnostic_fields_are_not_accepted(self):
        with self.assertRaises(TypeError):
            self.finding(raw_value="An")
        with self.assertRaises(TypeError):
            self.report(reason_codes=("raw text",))
        with self.assertRaises(ValueError) as caught:
            self.finding(detector_id="raw clinical phrase")
        self.assertNotIn("raw clinical phrase", str(caught.exception))
        self.assertNotIn(self.source.text, repr(self.source))
        self.assertNotIn(self.source.text, repr(self.result(output_text=self.source.text)))

    def test_metadata_rejects_mutable_or_duplicate_reason_codes(self):
        with self.assertRaises(TypeError):
            self.assessment(reason_codes=[ReasonCode.UNQUALIFIED_PROFILE])
        with self.assertRaises(ValueError):
            self.assessment(reason_codes=(ReasonCode.UNQUALIFIED_PROFILE,) * 2)

    def test_dates_and_organizations_do_not_have_automatic_policy_actions(self):
        for kind in (EntityType.DATE, EntityType.ORGANIZATION, EntityType.AGE):
            finding = self.finding(entity_type=kind, identifiability=Identifiability.CONTEXTUAL)
            self.assertFalse(hasattr(finding, "action"))
        self.assertEqual(self.decision(action=PolicyAction.PRESERVE).action, PolicyAction.PRESERVE)

    def test_review_decision_requires_a_reason(self):
        with self.assertRaises(ValueError):
            self.decision(action=PolicyAction.REVIEW)
        self.decision(action=PolicyAction.REVIEW, reason_codes=(ReasonCode.AMBIGUOUS_ENTITY,))

    def test_policy_action_requires_enum_not_string(self):
        with self.assertRaises(TypeError):
            self.decision(action="redact")

    def test_uncertain_assessments_prohibit_outbound_use(self):
        for status in (AssessmentStatus.PARTIAL, AssessmentStatus.REVIEW_REQUIRED, AssessmentStatus.FAILED):
            with self.subTest(status=status):
                self.assertEqual(self.assessment(status=status).outbound_restriction, OutboundRestriction.PROHIBITED)
                with self.assertRaises(ValueError):
                    self.assessment(status=status, outbound_restriction=OutboundRestriction.GATEWAY_REVIEW_REQUIRED)

    def test_uncertain_assessment_requires_reasons(self):
        with self.assertRaises(ValueError):
            self.assessment(reason_codes=())

    def test_complete_assessment_requires_explicit_profile(self):
        with self.assertRaises(ValueError):
            self.assessment(status=AssessmentStatus.COMPLETE, required_detectors=())
        with self.assertRaises(ValueError):
            self.assessment(required_detectors=("fake", "fake"))

    def test_complete_assessment_cannot_hide_unresolved_risk(self):
        with self.assertRaises(ValueError):
            self.assessment(status=AssessmentStatus.COMPLETE, reason_codes=(ReasonCode.AMBIGUOUS_ENTITY,))

    def test_result_rejects_source_and_policy_mismatch(self):
        with self.assertRaises(ValueError):
            self.result(source=replace(self.source, source_revision="2"))
        with self.assertRaises(ValueError):
            self.result(decisions=(self.decision(policy_version="2"),))

    def test_result_rejects_missing_required_detector_for_complete_assessment(self):
        with self.assertRaises(ValueError):
            self.result(detector_reports=(), assessment=self.assessment(status=AssessmentStatus.COMPLETE))

    def test_complete_result_cannot_hide_failed_report(self):
        failed = self.report(status=DetectorStatus.FAILED, findings=(), coverage=(), reason_codes=(ReasonCode.DETECTOR_FAILED,))
        with self.assertRaises(ValueError):
            self.result(detector_reports=(failed,), assessment=self.assessment(status=AssessmentStatus.COMPLETE))

    def test_complete_result_cannot_hide_review_decisions(self):
        review = self.decision(action=PolicyAction.REVIEW, reason_codes=(ReasonCode.AMBIGUOUS_ENTITY,))
        with self.assertRaises(ValueError):
            self.result(decisions=(review,), assessment=self.assessment(status=AssessmentStatus.COMPLETE))

    def test_audit_complete_result_rejects_unresolved_preserve_reason(self):
        source = replace(self.source, text="Nguyễn Mẫu An")
        span = SourceSpan(start=0, end=len(source.text))
        finding = self.finding(source=source, span=span)
        report = self.report(source=source, findings=(finding,), coverage=(span,))
        decision = self.decision(
            source=source, span=span, action=PolicyAction.PRESERVE,
            reason_codes=(ReasonCode.UNRESOLVED_CONFLICT,),
        )
        assessment = self.assessment(
            source=source, status=AssessmentStatus.COMPLETE, reason_codes=(),
            outbound_restriction=OutboundRestriction.GATEWAY_REVIEW_REQUIRED,
        )
        with self.assertRaises(ValueError):
            self.result(source=source, detector_reports=(report,),
                        decisions=(decision,), assessment=assessment)

    def test_complete_result_rejects_each_unresolved_decision_reason(self):
        for reason in ReasonCode:
            if reason is ReasonCode.UNQUALIFIED_PROFILE:
                continue
            for action in PolicyAction:
                for restriction in OutboundRestriction:
                    with self.subTest(reason=reason, action=action, restriction=restriction):
                        decision = self.decision(action=action, reason_codes=(reason,))
                        assessment = self.assessment(
                            status=AssessmentStatus.COMPLETE, reason_codes=(),
                            outbound_restriction=restriction,
                        )
                        with self.assertRaises(ValueError):
                            self.result(decisions=(decision,), assessment=assessment)

    def test_unresolved_decisions_allow_noncomplete_prohibited_results(self):
        for status in (AssessmentStatus.PARTIAL, AssessmentStatus.REVIEW_REQUIRED, AssessmentStatus.FAILED):
            for action in PolicyAction:
                with self.subTest(status=status, action=action):
                    assessment = self.assessment(
                        status=status, reason_codes=(ReasonCode.UNRESOLVED_CONFLICT,),
                    )
                    decision = self.decision(
                        action=action, reason_codes=(ReasonCode.UNRESOLVED_CONFLICT,),
                    )
                    result = self.result(decisions=(decision,), assessment=assessment)
                    self.assertIs(result.detector_reports[0].status, DetectorStatus.COMPLETE)
                    self.assertIs(result.assessment.outbound_restriction, OutboundRestriction.PROHIBITED)
                    self.assertFalse(result.external_egress_authorized)
                    with self.assertRaises(ValueError):
                        self.assessment(status=status, outbound_restriction=OutboundRestriction.GATEWAY_REVIEW_REQUIRED)

    def test_complete_execution_can_retain_qualification_limit_and_gateway_review(self):
        for action in (PolicyAction.PRESERVE, PolicyAction.REDACT, PolicyAction.PSEUDONYMIZE):
            with self.subTest(action=action):
                result = self.result(
                    decisions=(self.decision(action=action, reason_codes=(ReasonCode.UNQUALIFIED_PROFILE,)),),
                    assessment=self.assessment(
                        status=AssessmentStatus.COMPLETE,
                        outbound_restriction=OutboundRestriction.GATEWAY_REVIEW_REQUIRED,
                    ),
                )
                self.assertIs(result.assessment.status, AssessmentStatus.COMPLETE)
                self.assertIn(ReasonCode.UNQUALIFIED_PROFILE, result.assessment.reason_codes)
                self.assertIs(result.assessment.outbound_restriction, OutboundRestriction.GATEWAY_REVIEW_REQUIRED)
                self.assertFalse(result.external_egress_authorized)

    def test_complete_execution_with_no_reasons_still_defaults_to_prohibited(self):
        result = self.result(assessment=self.assessment(status=AssessmentStatus.COMPLETE, reason_codes=()))
        self.assertIs(result.assessment.outbound_restriction, OutboundRestriction.PROHIBITED)
        self.assertFalse(result.external_egress_authorized)

    def test_decision_order_cannot_hide_unresolved_evidence(self):
        resolved = self.decision(span=SourceSpan(start=3, end=6))
        unresolved = self.decision(reason_codes=(ReasonCode.UNRESOLVED_CONFLICT,))
        for decisions in permutations((resolved, unresolved)):
            with self.subTest(decisions=decisions), self.assertRaises(ValueError):
                self.result(decisions=decisions, assessment=self.assessment(status=AssessmentStatus.COMPLETE))

    def test_result_rejects_duplicate_detectors_and_mutable_decisions(self):
        with self.assertRaises(ValueError):
            self.result(detector_reports=(self.report(), self.report()))
        with self.assertRaises(TypeError):
            self.result(decisions=[])

    def test_egress_cannot_be_authorized_by_any_result_status(self):
        for status in AssessmentStatus:
            result = self.result(assessment=self.assessment(status=status))
            self.assertIs(result.external_egress_authorized, False)
        with self.assertRaises(TypeError):
            self.result(external_egress_authorized=True)
        with self.assertRaises(FrozenInstanceError):
            self.result().external_egress_authorized = True

    def test_even_gateway_review_is_not_authorization(self):
        result = self.result(assessment=self.assessment(status=AssessmentStatus.COMPLETE,
                             outbound_restriction=OutboundRestriction.GATEWAY_REVIEW_REQUIRED))
        self.assertFalse(result.external_egress_authorized)

    def test_result_is_not_a_renderer_or_source_text_container(self):
        result = self.result()
        self.assertIsNone(result.output_text)
        self.assertNotIn("source", {item.name for item in fields(result)})
        self.assertNotIn("raw_value", {item.name for item in fields(self.finding())})


if __name__ == "__main__":
    unittest.main()
