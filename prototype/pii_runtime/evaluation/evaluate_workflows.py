"""Deterministic rules-only and fault-injection evaluation on synthetic transcripts."""

import argparse
from collections import Counter
import json

from features.pii_filter.engine import DetectorSpec, process_text
from features.pii_filter.schema import (
    DetectorReport, DetectorStatus, EntityFinding, EntityType, Identifiability,
    PolicyAction, SourceSpan, SubjectRole,
)
from pii_runtime.evaluation.workflow_scenarios import (
    MaterializedFixture, ScenarioType, get_workflow_fixtures, materialize,
)


def _exact_counts(predicted: tuple[EntityFinding, ...], gold: tuple) -> int:
    """Count typed exact matches one-to-one, so duplicate predictions cannot inflate TP."""
    predicted_counts = Counter((item.span, item.entity_type) for item in predicted)
    gold_counts = Counter((item.span, item.entity_type) for item in gold)
    return sum((predicted_counts & gold_counts).values())


def _partial_detector(fixture: MaterializedFixture) -> tuple[DetectorSpec, ...]:
    """Build an explicit test-only prefix detector for configured failure fixtures."""
    if not fixture.partial_predictions:
        return ()
    categories = tuple(sorted({kind for _, kind in fixture.partial_predictions}, key=lambda item: item.value))

    def detect(source):
        findings = tuple(EntityFinding(
            source=source, span=span, entity_type=kind, subject_role=SubjectRole.UNKNOWN,
            identifiability=Identifiability.DIRECT,
            detector_id="scenario-partial-prefix", detector_version="1",
        ) for span, kind in fixture.partial_predictions)
        coverage = (SourceSpan(start=0, end=len(source.text)),) if source.text else ()
        return DetectorReport(
            source=source, detector_id="scenario-partial-prefix", detector_version="1",
            status=DetectorStatus.COMPLETE, supported_entities=categories,
            findings=findings, coverage=coverage,
        )

    return (DetectorSpec(
        detector_id="scenario-partial-prefix", detector_version="1",
        supported_entities=categories, detect=detect,
    ),)


def _measure_run(fixture: MaterializedFixture, result) -> dict:
    if result.external_egress_authorized:
        raise ValueError("PII engine unexpectedly authorized outbound use")
    if result.assessment.status is not fixture.fixture.expected_assessment_status:
        raise ValueError("scenario assessment differs from its explicit expected state")

    predictions = tuple(item for report in result.detector_reports for item in report.findings)
    true_positives = _exact_counts(predictions, fixture.entities)
    redacted_indices = {
        index for decision in result.decisions if decision.action is PolicyAction.REDACT
        for index in range(decision.span.start, decision.span.end)
    }
    policy_by_span = {policy.span: policy.action for policy in fixture.policies}
    unsupported = {span: reason for span, reason in fixture.unsupported_cases}
    required = tuple(
        item for item in fixture.entities
        if policy_by_span[item.span] in (PolicyAction.REDACT, PolicyAction.PSEUDONYMIZE)
    )
    supported_required = tuple(item for item in required if item.span not in unsupported)

    def fully_redacted(annotation) -> bool:
        return all(index in redacted_indices
                   for index in range(annotation.span.start, annotation.span.end))

    full_supported = sum(fully_redacted(item) for item in supported_required)
    full_all_required = sum(fully_redacted(item) for item in required)
    partial_leaks = []
    for item in required:
        redacted_count = sum(index in redacted_indices
                             for index in range(item.span.start, item.span.end))
        span_length = item.span.end - item.span.start
        if 0 < redacted_count < span_length:
            partial_leaks.append({
                "entity_type": item.entity_type.value,
                "start": item.span.start,
                "end": item.span.end,
                "redacted_characters": redacted_count,
                "total_characters": span_length,
                "unsupported": item.span in unsupported,
            })

    clinical_indices = {
        index for annotation in fixture.clinical
        for index in range(annotation.span.start, annotation.span.end)
    }
    prediction_keys = {(item.span, item.entity_type) for item in fixture.entities}
    non_exact_predictions = [
        {"entity_type": item.entity_type.value, "start": item.span.start, "end": item.span.end}
        for item in predictions if (item.span, item.entity_type) not in prediction_keys
    ]
    unsupported_types = [
        next(item.entity_type.value for item in required if item.span == span)
        for span in unsupported
    ]
    reasons = {item.value for item in result.assessment.reason_codes}
    return {
        "entity_detection_exact": {
            "true_positives": true_positives,
            "predictions": len(predictions),
            "ground_truth": len(fixture.entities),
            "false_positive_count": len(predictions) - true_positives,
            "false_negative_count": len(fixture.entities) - true_positives,
            "precision": true_positives / len(predictions) if predictions else None,
            "recall": true_positives / len(fixture.entities) if fixture.entities else None,
            "prediction_spans": [
                {"entity_type": item.entity_type.value, "start": item.span.start, "end": item.span.end}
                for item in predictions
            ],
            "non_exact_prediction_spans": non_exact_predictions,
        },
        "full_identifier_redaction": {
            "supported_category": {
                "required": len(supported_required),
                "fully_redacted": full_supported,
                "coverage": full_supported / len(supported_required) if supported_required else None,
            },
            "all_required": {
                "required": len(required),
                "fully_redacted": full_all_required,
                "coverage": full_all_required / len(required) if required else None,
            },
        },
        "known_unsupported_identifiers": {
            "count": len(unsupported),
            "entity_types": unsupported_types,
            "counted_as_sanitized_success": False,
        },
        "clinical_protected_characters": len(clinical_indices),
        "clinical_overredacted_characters": len(clinical_indices & redacted_indices),
        "partial_identifier_leakage": {
            "count": len(partial_leaks),
            "spans": partial_leaks,
        },
        "possible_residual_pii": "possible_residual_pii" in reasons,
        "assessment_status": result.assessment.status.value,
        "review_required": result.assessment.status.value == "review_required",
        "failed": result.assessment.status.value == "failed",
        "outbound_restriction": result.assessment.outbound_restriction.value,
        "external_egress_authorized": result.external_egress_authorized,
    }


def _aggregate_metrics(reports: list[dict]) -> dict:
    predicted = sum(item["entity_detection_exact"]["predictions"] for item in reports)
    gold = sum(item["entity_detection_exact"]["ground_truth"] for item in reports)
    true_positives = sum(item["entity_detection_exact"]["true_positives"] for item in reports)
    supported_required = sum(
        item["full_identifier_redaction"]["supported_category"]["required"] for item in reports
    )
    full_supported = sum(
        item["full_identifier_redaction"]["supported_category"]["fully_redacted"] for item in reports
    )
    all_required = sum(item["full_identifier_redaction"]["all_required"]["required"] for item in reports)
    full_all_required = sum(
        item["full_identifier_redaction"]["all_required"]["fully_redacted"] for item in reports
    )
    clinical = sum(item["clinical_protected_characters"] for item in reports)
    overredacted = sum(item["clinical_overredacted_characters"] for item in reports)
    fixtures = len(reports)
    return {
        "fixtures": fixtures,
        "entity_detection_exact": {
            "true_positives": true_positives,
            "predictions": predicted,
            "ground_truth": gold,
            "false_positive_count": predicted - true_positives,
            "false_negative_count": gold - true_positives,
            "precision": true_positives / predicted if predicted else None,
            "recall": true_positives / gold if gold else None,
        },
        "full_identifier_redaction": {
            "supported_category": {
                "required": supported_required,
                "fully_redacted": full_supported,
                "coverage": full_supported / supported_required if supported_required else None,
            },
            "all_required": {
                "required": all_required,
                "fully_redacted": full_all_required,
                "coverage": full_all_required / all_required if all_required else None,
            },
        },
        "known_unsupported_identifiers": sum(item["known_unsupported_identifiers"]["count"] for item in reports),
        "clinical_protected_characters": clinical,
        "clinical_overredacted_characters": overredacted,
        "partial_identifier_leakage": sum(item["partial_identifier_leakage"]["count"] for item in reports),
        "possible_residual_pii_cases": sum(item["possible_residual_pii"] for item in reports),
        "review_required_cases": sum(item["review_required"] for item in reports),
        "review_required_rate": sum(item["review_required"] for item in reports) / fixtures if fixtures else None,
        "failed_cases": sum(item["failed"] for item in reports),
        "failure_rate": sum(item["failed"] for item in reports) / fixtures if fixtures else None,
        "outbound_authorized_cases": sum(item["external_egress_authorized"] for item in reports),
    }


def evaluate_workflows() -> dict:
    fixtures = tuple(materialize(item) for item in get_workflow_fixtures())
    scenario_reports = []
    for fixture in fixtures:
        rules_result = process_text(fixture.source)
        rules_metrics = _measure_run(fixture, rules_result)
        fault_specs = _partial_detector(fixture)
        if fault_specs:
            fault_metrics = _measure_run(
                fixture, process_text(fixture.source, extra_detectors=fault_specs),
            )
            fault_report = {
                "state": "applied",
                "detector_id": fault_specs[0].detector_id,
                "metrics": fault_metrics,
            }
        else:
            fault_report = {"state": "not_applicable", "metrics": None}
        scenario_reports.append({
            "scenario_id": fixture.fixture.scenario_id,
            "scenario_type": fixture.fixture.scenario_type.value,
            "source_characters": len(fixture.source.text),
            "speaker_roles": [turn.speaker_role.value if turn.speaker_role is not None else None
                              for turn in fixture.fixture.turns],
            "subject_roles": sorted({item.subject_role.value for item in fixture.entities}),
            "expected_assessment_status": fixture.fixture.expected_assessment_status.value,
            "rules_only": rules_metrics,
            "fault_injection": fault_report,
        })

    groups = {kind.value: [] for kind in ScenarioType}
    for report in scenario_reports:
        groups[report["scenario_type"]].append(report)
    scenario_groups = {}
    for name, reports in groups.items():
        rules_metrics = [item["rules_only"] for item in reports]
        injected_metrics = [item["fault_injection"]["metrics"] for item in reports
                            if item["fault_injection"]["metrics"] is not None]
        scenario_groups[name] = {
            "rules_only": _aggregate_metrics(rules_metrics),
            "fault_injection": {
                "state": "applied" if injected_metrics else "not_applicable",
                "metrics": _aggregate_metrics(injected_metrics) if injected_metrics else None,
            },
        }

    return {
        "dataset": "exposed-synthetic-workflow",
        "custody": "project-authored synthetic; not independently blinded",
        "fixtures": len(scenario_reports),
        "scenario_reports": scenario_reports,
        "scenario_groups": scenario_groups,
        "limitations": [
            "One synthetic fixture per workflow is not statistically representative and does not estimate real clinical performance.",
            "Missing speaker metadata remains unknown and is not provided to the text engine.",
            "Fault-injection metrics are separate from standalone rules-only metrics.",
            "Unsupported identifiers are visible in the all-required denominator and never count as sanitized successes.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate exposed synthetic transcript scenarios.")
    parser.parse_args()
    print(json.dumps(evaluate_workflows(), ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
