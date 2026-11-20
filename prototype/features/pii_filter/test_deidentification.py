"""Explicit policies and literal preservation; no claim of clinical semantics."""

from dataclasses import replace
from itertools import permutations
import unicodedata
import unittest

from features.pii_filter.aggregation import aggregate
from features.pii_filter.deidentification import POLICY_VERSION, plan_redactions, render
from features.pii_filter.schema import (
    EntityType, Identifiability, PolicyAction, ReasonCode, ReplacementDecision,
    SourceSpan, TextInput,
)
from features.pii_filter.test_aggregation import make_report


class DeidentificationTests(unittest.TestCase):
    def setUp(self):
        self.source = TextInput(text="Nguyễn Văn An; Không dị ứng thuốc, mạch 92.", source_id="render-source", source_revision="1")
        self.span = SourceSpan(start=0, end=len("Nguyễn Văn An"))

    def decision(self, span=None, action=PolicyAction.REDACT, **overrides):
        values = dict(source=self.source, span=span or self.span, action=action, policy_version=POLICY_VERSION)
        return ReplacementDecision(**(values | overrides))

    def test_single_pass_preserves_every_character_outside_replacement(self):
        self.assertEqual(render(self.source, (self.decision(),)), "[PII]" + self.source.text[self.span.end:])

    def test_nfd_name_is_replaced_without_residual_marks(self):
        text = unicodedata.normalize("NFD", "Nguyễn Văn An")
        source = replace(self.source, text=text + "; mạch 92.")
        report = make_report(source, (SourceSpan(start=0, end=len(text)),))
        self.assertEqual(render(source, plan_redactions(source, aggregate(source, (report,)))), "[PII]; mạch 92.")

    def test_compatible_overlaps_merge_without_leaking_suffix(self):
        decisions = (self.decision(SourceSpan(start=0, end=6)), self.decision(SourceSpan(start=3, end=self.span.end)))
        for ordered in permutations(decisions):
            self.assertEqual(render(self.source, ordered), "[PII]" + self.source.text[self.span.end:])

    def test_contradictory_overlaps_fail_in_both_orders(self):
        decisions = (self.decision(), self.decision(SourceSpan(start=0, end=6), PolicyAction.PRESERVE))
        for ordered in permutations(decisions):
            with self.assertRaises(ValueError):
                render(self.source, ordered)

    def test_pseudonymization_and_unknown_policy_are_not_implemented(self):
        with self.assertRaises(ValueError):
            render(self.source, (self.decision(action=PolicyAction.PSEUDONYMIZE),))
        with self.assertRaises(ValueError):
            render(self.source, (self.decision(policy_version="unknown"),))

    def test_contextual_categories_require_review_instead_of_blanket_masking(self):
        for kind in (EntityType.DATE, EntityType.ORGANIZATION, EntityType.AGE):
            report = make_report(self.source, (self.span,), kinds=(kind,))
            decisions = plan_redactions(self.source, aggregate(self.source, (report,)))
            self.assertIs(decisions[0].action, PolicyAction.REVIEW)
            self.assertEqual(render(self.source, decisions), self.source.text)

    def test_ambiguous_name_is_preserved_only_as_a_review_draft(self):
        report = make_report(self.source, (self.span,))
        finding = replace(report.findings[0], source=self.source, identifiability=Identifiability.AMBIGUOUS)
        report = replace(report, source=self.source, findings=(finding,))
        decisions = plan_redactions(self.source, aggregate(self.source, (report,)))
        self.assertIs(decisions[0].action, PolicyAction.REVIEW)
        self.assertIn(ReasonCode.AMBIGUOUS_ENTITY, decisions[0].reason_codes)
        self.assertEqual(render(self.source, decisions), self.source.text)

    def test_direct_type_conflict_can_be_redacted_but_evidence_is_not_resolved(self):
        report = make_report(self.source, (self.span, self.span), kinds=(EntityType.PERSON, EntityType.PATIENT_ID))
        decisions = plan_redactions(self.source, aggregate(self.source, (report,)))
        self.assertIs(decisions[0].action, PolicyAction.REDACT)
        self.assertIn(ReasonCode.UNRESOLVED_CONFLICT, decisions[0].reason_codes)
        self.assertEqual(len(report.findings), 2)

    def test_manual_partial_cluster_span_cannot_be_rendered(self):
        source = replace(self.source, text="a\u0301b")
        decision = self.decision(source=source, span=SourceSpan(start=0, end=1))
        with self.assertRaises(ValueError):
            render(source, (decision,))

    def test_forged_offsets_and_stale_source_are_rejected(self):
        decision = self.decision()
        with self.assertRaises(ValueError):
            render(replace(self.source, source_revision="2"), (decision,))
        object.__setattr__(decision.span, "end", 1000)
        with self.assertRaises(ValueError):
            render(self.source, (decision,))

    def test_empty_plan_does_not_normalize_or_rewrite_original_text(self):
        source = replace(self.source, text="  A\u0301\t\r\n🙂  ")
        self.assertEqual(render(source, ()), source.text)
