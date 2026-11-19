"""Validated, deterministic overlap groups retaining original detector evidence."""

from dataclasses import dataclass

from features.pii_filter.normalization import AnalysisView, ResourceLimitError, build_view
from features.pii_filter.schema import (
    DetectorReport, EntityFinding, Identifiability, ReasonCode, SourceSpan,
    SubjectRole, TextInput, require_tuple, validate_detector_report,
)


def finding_key(finding: EntityFinding) -> tuple:
    return (finding.span.start, finding.span.end, finding.entity_type.value,
            finding.subject_role.value, finding.identifiability.value,
            finding.detector_id, finding.detector_version)


@dataclass(frozen=True, slots=True, kw_only=True)
class EntityGroup:
    span: SourceSpan
    evidence: tuple[EntityFinding, ...]

    @property
    def entity_types(self) -> tuple:
        return tuple(sorted({item.entity_type for item in self.evidence}, key=lambda item: item.value))

    @property
    def reason_codes(self) -> tuple[ReasonCode, ...]:
        reasons = []
        roles = {item.subject_role for item in self.evidence} - {SubjectRole.UNKNOWN}
        if len(self.entity_types) > 1 or len(roles) > 1:
            reasons.append(ReasonCode.UNRESOLVED_CONFLICT)
        if any(item.identifiability is Identifiability.AMBIGUOUS for item in self.evidence):
            reasons.append(ReasonCode.AMBIGUOUS_ENTITY)
        return tuple(reasons)

    def validate_for(self, source: TextInput, view: AnalysisView) -> None:
        view.validate_source(source)
        if type(self.span) is not SourceSpan:
            raise TypeError("group requires a SourceSpan")
        self.span.validate_for(source)
        require_tuple(self.evidence, EntityFinding)
        if not self.evidence:
            raise ValueError("group requires detector evidence")
        for finding in self.evidence:
            finding.validate_for(source)
        ordered = tuple(sorted(set(self.evidence), key=finding_key))
        if ordered != self.evidence:
            raise ValueError("group evidence must be unique and canonically ordered")
        intervals = sorted((view.expand_span(item.span) for item in ordered), key=lambda item: (item.start, item.end))
        start, end = intervals[0].start, intervals[0].end
        for interval in intervals[1:]:
            if interval.start >= end:
                raise ValueError("group evidence is not connected by overlap")
            end = max(end, interval.end)
        if self.span != SourceSpan(start=start, end=end):
            raise ValueError("group span differs from its expanded source evidence")


def aggregate(source: TextInput, reports: tuple[DetectorReport, ...], *, max_findings: int = 512) -> tuple[EntityGroup, ...]:
    require_tuple(reports, DetectorReport)
    if type(max_findings) is not int or not 0 < max_findings <= 4096:
        raise ValueError("invalid aggregation budget")
    total = 0
    for report in reports:
        require_tuple(report.findings, EntityFinding)
        total += len(report.findings)
        if total > max_findings:
            raise ResourceLimitError("aggregate finding budget exceeded")
        validate_detector_report(source, report)
    if len({report.detector_id for report in reports}) != len(reports):
        raise ValueError("duplicate detector reports")
    view = build_view(source)
    evidence = sorted({item for report in reports for item in report.findings}, key=finding_key)
    expanded = sorted(((view.expand_span(item.span), item) for item in evidence),
                      key=lambda pair: (pair[0].start, pair[0].end, finding_key(pair[1])))
    groups = []
    active = []
    start = end = 0
    for interval, finding in expanded:
        if active and interval.start >= end:
            groups.append(EntityGroup(span=SourceSpan(start=start, end=end), evidence=tuple(sorted(active, key=finding_key))))
            active = []
        if not active:
            start = interval.start
        end = max(end if active else interval.end, interval.end)
        active.append(finding)
    if active:
        groups.append(EntityGroup(span=SourceSpan(start=start, end=end), evidence=tuple(sorted(active, key=finding_key))))
    return tuple(groups)
