"""Local rules-only assessment; residual checks are not independent certification."""

import re

from features.pii_filter.aggregation import EntityGroup
from features.pii_filter.deidentification import REPLACEMENT
from features.pii_filter.normalization import build_view
from features.pii_filter.rules import DETECTOR_ID, detect_rules
from features.pii_filter.schema import (
    AssessmentStatus, DetectorReport, DetectorStatus, EntityType, OutboundRestriction,
    PolicyAction, PrivacyAssessment, ReasonCode, ReplacementDecision, TextInput,
    require_tuple, validate_detector_report,
)


PROFILE_ID = "vi-text-rules-review"
PROFILE_VERSION = "2.1"
_UNHANDLED_CUE = re.compile(
    r"(?i)\b(?:BHYT|bảo[ \t]+hiểm(?:[ \t]+y[ \t]+tế)?|địa[ \t]+chỉ|hộ[ \t]+chiếu|passport|"
    r"CCCD|CMND|ngày[ \t]+sinh|DOB|mã[ \t]+bệnh[ \t]+nhân|mã[ \t]+lượt[ \t]+khám|"
    r"số[ \t]+điện[ \t]+thoại|sđt)[ \t]*(?:là[ \t]*)?[:#=-]?[ \t]*"
)


def assess(source: TextInput, reports: tuple[DetectorReport, ...],
           groups: tuple[EntityGroup, ...], decisions: tuple[ReplacementDecision, ...],
           output_text: str | None, *, failure_reasons: tuple[ReasonCode, ...] = (),
           max_findings: int = 512) -> PrivacyAssessment:
    require_tuple(reports, DetectorReport)
    require_tuple(groups, EntityGroup)
    require_tuple(decisions, ReplacementDecision)
    require_tuple(failure_reasons, ReasonCode)
    reasons = {ReasonCode.UNQUALIFIED_PROFILE, ReasonCode.UNSUPPORTED_CATEGORIES}
    reasons.update(failure_reasons)
    failed = bool(failure_reasons) or output_text is None
    partial = False
    supported = set()
    for report in reports:
        validate_detector_report(source, report)
        supported.update(report.supported_entities)
        reasons.update(report.reason_codes)
        if report.status is DetectorStatus.FAILED:
            failed = True
            reasons.add(ReasonCode.DETECTOR_FAILED)
        elif report.status is not DetectorStatus.COMPLETE:
            partial = True
            reasons.add(ReasonCode.INCOMPLETE_COVERAGE)
            if report.status is DetectorStatus.UNAVAILABLE:
                reasons.add(ReasonCode.DETECTOR_UNAVAILABLE)
    if supported == set(EntityType):
        reasons.discard(ReasonCode.UNSUPPORTED_CATEGORIES)
    if not reports or not any(report.detector_id == DETECTOR_ID for report in reports):
        failed = True
        reasons.add(ReasonCode.DETECTOR_UNAVAILABLE)
    view = build_view(source)
    for group in groups:
        group.validate_for(source, view)
        reasons.update(group.reason_codes)
    for decision in decisions:
        decision.validate_for(source)
        reasons.update(decision.reason_codes)
        if decision.action is PolicyAction.REVIEW:
            reasons.add(ReasonCode.POSSIBLE_RESIDUAL_PII)
    if not failed and output_text is not None:
        residual_source = TextInput(text=output_text, source_id="residual-check", source_revision=source.source_revision)
        residual = detect_rules(residual_source, max_findings=max_findings)
        if residual.findings:
            reasons.add(ReasonCode.POSSIBLE_RESIDUAL_PII)
        normalized = build_view(residual_source).text
        for cue in _UNHANDLED_CUE.finditer(normalized):
            tail = normalized[cue.end():].lstrip()
            if not tail:
                continue
            if tail.startswith(REPLACEMENT):
                # A placeholder proves only that some span was replaced. Any
                # remaining alphanumeric content may be an exposed suffix of
                # the same field value, so retain residual risk. Stop at the
                # next explicit field delimiter to avoid treating a later
                # administrative field as a suffix of this identifier.
                remainder = re.split(r"[;\r\n|]", tail[len(REPLACEMENT):], maxsplit=1)[0]
                if any(character.isalnum() for character in remainder):
                    reasons.add(ReasonCode.POSSIBLE_RESIDUAL_PII)
            else:
                reasons.add(ReasonCode.POSSIBLE_RESIDUAL_PII)
    status = AssessmentStatus.FAILED if failed else (
        AssessmentStatus.PARTIAL if partial else AssessmentStatus.REVIEW_REQUIRED)
    return PrivacyAssessment(
        source=source, status=status, profile_id=PROFILE_ID, profile_version=PROFILE_VERSION,
        required_detectors=tuple(sorted({DETECTOR_ID, *(report.detector_id for report in reports)})),
        reason_codes=tuple(sorted(reasons, key=lambda item: item.value)),
        outbound_restriction=OutboundRestriction.PROHIBITED,
    )
