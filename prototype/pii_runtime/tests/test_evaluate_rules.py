"""Independent metric/trace oracles, not model performance assertions."""

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from features.pii_filter import pii
from features.pii_filter.schema import EntityType, SourceSpan
from pii_runtime.evaluation.evaluate_rules import Prediction, _overlap_count, _scores, evaluate_development, trace_legacy
from pii_runtime.evaluation.generate_synthetic import generate_development


class EvaluationTests(unittest.TestCase):
    def test_legacy_replay_matches_actual_prototype_on_all_development_records(self):
        for record in generate_development(17):
            self.assertEqual(trace_legacy(record.source.text)[0], pii.mask(record.source.text)[0])

    def test_repeated_legacy_phone_trace_has_exact_distinct_source_spans(self):
        output, predictions, removed = trace_legacy("0912345678; 0912345678")
        self.assertEqual(output, "[SĐT]; [SĐT]")
        self.assertEqual([item.span for item in predictions], [SourceSpan(start=0, end=10), SourceSpan(start=12, end=22)])
        self.assertEqual(removed, frozenset((*range(10), *range(12, 22))))

    def test_legacy_trace_handles_literal_name_replacement_including_prefix(self):
        output, _, removed = trace_legacy("Anh Anh")
        self.assertEqual(output, pii.mask("Anh Anh")[0])
        self.assertEqual(removed, frozenset((*range(3), *range(4, 7))))

    def test_overlap_matching_cannot_count_a_gold_entity_twice(self):
        prediction = Prediction(SourceSpan(start=0, end=2), EntityType.PERSON)
        self.assertEqual(_overlap_count((prediction, prediction), (prediction,)), 1)
        other = Prediction(SourceSpan(start=0, end=2), EntityType.EMAIL)
        self.assertEqual(_overlap_count((other,), (prediction,)), 0)

    def test_overlap_matching_uses_maximum_cardinality(self):
        predicted = (Prediction(SourceSpan(start=0, end=5), EntityType.PERSON),
                     Prediction(SourceSpan(start=0, end=2), EntityType.PERSON))
        gold = (Prediction(SourceSpan(start=0, end=2), EntityType.PERSON),
                Prediction(SourceSpan(start=3, end=5), EntityType.PERSON))
        self.assertEqual(_overlap_count(predicted, gold), 2)

    def test_score_denominators_and_false_negatives_are_explicit(self):
        self.assertEqual(_scores(1, 2, 4), dict(tp=1, fp=1, fn=3, precision=0.5, recall=0.25, f1=1/3))
        self.assertIsNone(_scores(0, 0, 0)["f1"])
        self.assertEqual(_scores(0, 0, 2)["recall"], 0)

    def test_evaluation_is_deterministic_and_keeps_unsupported_gold_categories(self):
        first = evaluate_development(17)
        self.assertEqual(first, evaluate_development(17))
        self.assertEqual(first["records"], 20)
        self.assertEqual(first["dataset"], "exposed-development")
        for system in first["systems"].values():
            self.assertEqual(system["categories"]["HEALTH_INSURANCE_ID"]["gold"], 1)
            self.assertEqual(system["categories"]["HEALTH_INSURANCE_ID"]["exact"]["fn"], 1)
