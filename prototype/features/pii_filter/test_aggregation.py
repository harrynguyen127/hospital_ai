"""Evidence preservation and Unicode-expanded conflict groups."""

from dataclasses import replace
from itertools import permutations
import unittest

from features.pii_filter.aggregation import EntityGroup, aggregate
from features.pii_filter.normalization import ResourceLimitError, build_view
from features.pii_filter.schema import (
    DetectorReport, DetectorStatus, EntityFinding, EntityType, Identifiability,
    ReasonCode, SourceSpan, SubjectRole, TextInput,
)


def make_report(source, spans, *, detector="test", kinds=None, roles=None):
    findings = tuple(EntityFinding(
        source=source, span=span, entity_type=kinds[index] if kinds else EntityType.PERSON,
        subject_role=roles[index] if roles else SubjectRole.PATIENT,
        identifiability=Identifiability.DIRECT, detector_id=detector, detector_version="1",
    ) for index, span in enumerate(spans))
    return DetectorReport(
        source=source, detector_id=detector, detector_version="1", status=DetectorStatus.COMPLETE,
        supported_entities=tuple(sorted({item.entity_type for item in findings}, key=lambda item: item.value)) or (EntityType.PERSON,),
        findings=findings, coverage=(SourceSpan(start=0, end=len(source.text)),) if source.text else (),
    )


class AggregationTests(unittest.TestCase):
    def setUp(self):
        self.source = TextInput(text="Nguyễn Văn An", source_id="group-source", source_revision="1")

    def test_duplicate_findings_do_not_destroy_raw_report_evidence(self):
        report = make_report(self.source, (SourceSpan(start=0, end=6),))
        report = replace(report, source=self.source, findings=report.findings * 2)
        groups = aggregate(self.source, (report,))
        self.assertEqual(len(groups[0].evidence), 1)
        self.assertEqual(len(report.findings), 2)

    def test_identical_spans_from_two_detectors_keep_both_provenances(self):
        spans = (SourceSpan(start=0, end=6),)
        reports = tuple(make_report(self.source, spans, detector=name) for name in ("a", "b"))
        group = aggregate(self.source, reports)[0]
        self.assertEqual({item.detector_id for item in group.evidence}, {"a", "b"})

    def test_overlapping_suffix_is_fully_covered(self):
        report = make_report(self.source, (SourceSpan(start=0, end=6), SourceSpan(start=3, end=len(self.source.text))))
        group = aggregate(self.source, (report,))[0]
        self.assertEqual(group.span, SourceSpan(start=0, end=len(self.source.text)))
        self.assertEqual(len(group.evidence), 2)

    def test_type_and_role_conflicts_remain_visible(self):
        span = SourceSpan(start=0, end=6)
        for kinds, roles in (((EntityType.PERSON, EntityType.PATIENT_ID), None),
                             (None, (SubjectRole.PATIENT, SubjectRole.RELATIVE))):
            report = make_report(self.source, (span, span), kinds=kinds, roles=roles)
            self.assertIn(ReasonCode.UNRESOLVED_CONFLICT, aggregate(self.source, (report,))[0].reason_codes)

    def test_report_order_does_not_change_groups(self):
        reports = (make_report(self.source, (SourceSpan(start=0, end=6),), detector="b"),
                   make_report(self.source, (SourceSpan(start=3, end=10),), detector="a"))
        expected = aggregate(self.source, reports)
        for ordered in permutations(reports):
            self.assertEqual(aggregate(self.source, ordered), expected)

    def test_touching_spans_do_not_merge(self):
        report = make_report(self.source, (SourceSpan(start=0, end=6), SourceSpan(start=6, end=10)))
        self.assertEqual(len(aggregate(self.source, (report,))), 2)

    def test_expansion_can_merge_spans_inside_one_combining_cluster(self):
        source = replace(self.source, text="a\u0301b")
        report = make_report(source, (SourceSpan(start=0, end=1), SourceSpan(start=1, end=2)))
        groups = aggregate(source, (report,))
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].span, SourceSpan(start=0, end=2))

    def test_invalid_objects_are_rejected_before_sorting(self):
        for reports in ((None,), [], ({},)):
            with self.assertRaises(TypeError):
                aggregate(self.source, reports)

    def test_forged_offsets_and_revision_mismatch_are_rejected(self):
        report = make_report(self.source, (SourceSpan(start=0, end=6),))
        object.__setattr__(report.findings[0].span, "end", 100)
        with self.assertRaises(ValueError):
            aggregate(self.source, (report,))
        other = replace(self.source, source_revision="2")
        with self.assertRaises(ValueError):
            aggregate(self.source, (make_report(other, (SourceSpan(start=0, end=6),)),))

    def test_budget_counts_duplicates_before_deduplication(self):
        report = make_report(self.source, (SourceSpan(start=0, end=6),))
        report = replace(report, source=self.source, findings=report.findings * 2)
        with self.assertRaises(ResourceLimitError):
            aggregate(self.source, (report,), max_findings=1)

    def test_manually_forged_group_must_match_connected_evidence(self):
        report = make_report(self.source, (SourceSpan(start=0, end=6),))
        group = EntityGroup(span=SourceSpan(start=0, end=10), evidence=report.findings)
        with self.assertRaises(ValueError):
            group.validate_for(self.source, build_view(self.source))
