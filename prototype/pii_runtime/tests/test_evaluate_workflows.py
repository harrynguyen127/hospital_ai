"""Rules-only and fault-injection metrics remain distinct and reproducible."""

import unittest

from pii_runtime.evaluation.evaluate_workflows import evaluate_workflows
from pii_runtime.evaluation.workflow_scenarios import ScenarioType


class WorkflowEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.report = evaluate_workflows()
        self.fixtures = {item["scenario_type"]: item for item in self.report["scenario_reports"]}

    def test_reporting_is_separate_for_both_workflows(self):
        self.assertEqual(self.report["fixtures"], 2)
        doctor = self.fixtures[ScenarioType.DOCTOR_PATIENT_CONVERSATION.value]
        nurse = self.fixtures[ScenarioType.NURSE_CHART_READBACK.value]
        self.assertEqual(doctor["fault_injection"]["state"], "not_applicable")
        self.assertEqual(nurse["fault_injection"]["state"], "applied")
        self.assertEqual(doctor["rules_only"]["review_required"], True)
        self.assertEqual(nurse["rules_only"]["review_required"], True)
        self.assertEqual(doctor["rules_only"]["failed"], False)
        self.assertEqual(nurse["rules_only"]["failed"], False)

    def test_doctor_metrics_include_supported_and_all_required_denominators(self):
        doctor = self.fixtures[ScenarioType.DOCTOR_PATIENT_CONVERSATION.value]["rules_only"]
        self.assertEqual(doctor["entity_detection_exact"]["true_positives"], 4)
        self.assertEqual(doctor["entity_detection_exact"]["predictions"], 4)
        self.assertEqual(doctor["entity_detection_exact"]["ground_truth"], 5)
        self.assertEqual(doctor["full_identifier_redaction"]["supported_category"]["fully_redacted"], 4)
        self.assertEqual(doctor["full_identifier_redaction"]["supported_category"]["required"], 4)
        self.assertEqual(doctor["full_identifier_redaction"]["all_required"]["fully_redacted"], 4)
        self.assertEqual(doctor["full_identifier_redaction"]["all_required"]["required"], 5)
        self.assertEqual(doctor["known_unsupported_identifiers"]["count"], 1)
        self.assertEqual(doctor["clinical_overredacted_characters"], 0)
        self.assertEqual(doctor["clinical_protected_characters"], 152)

    def test_nurse_rules_only_and_partial_probe_metrics_are_separate(self):
        nurse = self.fixtures[ScenarioType.NURSE_CHART_READBACK.value]
        rules = nurse["rules_only"]
        injected = nurse["fault_injection"]["metrics"]

        self.assertEqual(rules["entity_detection_exact"]["true_positives"], 5)
        self.assertEqual(rules["entity_detection_exact"]["predictions"], 5)
        self.assertEqual(rules["entity_detection_exact"]["ground_truth"], 6)
        self.assertEqual(rules["entity_detection_exact"]["precision"], 1.0)
        self.assertAlmostEqual(rules["entity_detection_exact"]["recall"], 5 / 6)
        self.assertEqual(rules["partial_identifier_leakage"]["count"], 0)

        self.assertEqual(injected["entity_detection_exact"]["true_positives"], 5)
        self.assertEqual(injected["entity_detection_exact"]["predictions"], 6)
        self.assertEqual(injected["entity_detection_exact"]["ground_truth"], 6)
        self.assertAlmostEqual(injected["entity_detection_exact"]["precision"], 5 / 6)
        self.assertAlmostEqual(injected["entity_detection_exact"]["recall"], 5 / 6)
        self.assertEqual(injected["entity_detection_exact"]["non_exact_prediction_spans"], [
            {"entity_type": "HEALTH_INSURANCE_ID", "start": 178, "end": 181},
        ])
        self.assertEqual(injected["partial_identifier_leakage"]["count"], 1)
        self.assertEqual(injected["full_identifier_redaction"]["supported_category"]["fully_redacted"], 5)
        self.assertEqual(injected["full_identifier_redaction"]["all_required"]["fully_redacted"], 5)
        self.assertEqual(injected["full_identifier_redaction"]["all_required"]["required"], 6)
        self.assertEqual(injected["known_unsupported_identifiers"]["count"], 1)
        self.assertEqual(injected["clinical_overredacted_characters"], 0)
        self.assertEqual(injected["clinical_protected_characters"], 1519)
        self.assertTrue(injected["possible_residual_pii"])
        self.assertFalse(injected["external_egress_authorized"])

    def test_group_summary_separates_rules_and_fault_injection(self):
        nurse = self.report["scenario_groups"][ScenarioType.NURSE_CHART_READBACK.value]
        self.assertEqual(nurse["rules_only"]["entity_detection_exact"]["precision"], 1.0)
        self.assertAlmostEqual(
            nurse["fault_injection"]["metrics"]["entity_detection_exact"]["precision"], 5 / 6,
        )
        self.assertEqual(nurse["rules_only"]["full_identifier_redaction"]["all_required"]["required"], 6)

    def test_unsupported_cases_are_reported_but_not_successes(self):
        for scenario in self.fixtures.values():
            for mode in (scenario["rules_only"], scenario["fault_injection"]["metrics"]):
                if mode is None:
                    continue
                unsupported = mode["known_unsupported_identifiers"]
                self.assertEqual(unsupported["count"], 1)
                self.assertFalse(unsupported["counted_as_sanitized_success"])

    def test_evaluation_is_deterministic_and_disclaims_statistical_representativeness(self):
        self.assertEqual(self.report, evaluate_workflows())
        self.assertTrue(any("not statistically representative" in item
                            for item in self.report["limitations"]))


if __name__ == "__main__":
    unittest.main()
