"""Independent PII-02 API; no registry integration, persistence, network, or ML."""

from collections.abc import Callable
from dataclasses import dataclass, field

from features.pii_filter.aggregation import aggregate
from features.pii_filter.deidentification import POLICY_VERSION, plan_redactions, render
from features.pii_filter.normalization import ResourceLimitError, build_view
from features.pii_filter.risk import PROFILE_ID, PROFILE_VERSION, assess
from features.pii_filter.rules import DETECTOR_ID, DETECTOR_VERSION, SUPPORTED_ENTITIES, detect_rules
from features.pii_filter.schema import (
    AssessmentStatus, DetectorReport, DetectorStatus, EntityFinding, EntityType,
    PrivacyAssessment, PrivacyResult,
    ReasonCode, TextInput, require_identifier, require_tuple, validate_detector_report,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class EngineLimits:
    max_characters: int = 32_000
    max_findings: int = 512
    max_extra_detectors: int = 4

    def __post_init__(self) -> None:
        for value, maximum, minimum in ((self.max_characters, 200_000, 1),
                                        (self.max_findings, 4096, 1),
                                        (self.max_extra_detectors, 8, 0)):
            if type(value) is not int or not minimum <= value <= maximum:
                raise ValueError("invalid engine resource budget")


@dataclass(frozen=True, slots=True, kw_only=True)
class DetectorSpec:
    """Metadata for a trusted synchronous test/future detector callback.

    Callbacks must return promptly. In-process code cannot enforce hard timeouts
    or prevent allocations performed inside a callback; isolation is future work.
    """

    detector_id: str
    detector_version: str
    supported_entities: tuple[EntityType, ...]
    detect: Callable[[TextInput], DetectorReport] = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        require_identifier(self.detector_id)
        require_identifier(self.detector_version)
        require_tuple(self.supported_entities, EntityType)
        if not self.supported_entities or len(set(self.supported_entities)) != len(self.supported_entities):
            raise ValueError("detector spec requires unique declared categories")
        if not callable(self.detect):
            raise TypeError("detector spec requires a callable")


def process_text(source: TextInput, *, extra_detectors: tuple[DetectorSpec, ...] = (),
                 limits: EngineLimits = EngineLimits()) -> PrivacyResult:
    """Return a local review draft or a failed result with output_text=None.

    Invalid request contracts raise sanitized errors. Valid requests experiencing
    processing failures return structured FAILED results, never raw-text fallback.
    """
    if type(source) is not TextInput:
        raise TypeError("process_text requires a TextInput")
    source.__post_init__()
    if type(limits) is not EngineLimits:
        raise TypeError("an EngineLimits is required")
    limits.__post_init__()
    reports = []

    def failed(*reasons):
        # Do not rerun the stage that just failed (especially normalization).
        codes = {ReasonCode.UNQUALIFIED_PROFILE, ReasonCode.UNSUPPORTED_CATEGORIES, *reasons}
        codes.update(code for report in reports for code in report.reason_codes)
        assessment = PrivacyAssessment(
            source=source, status=AssessmentStatus.FAILED, profile_id=PROFILE_ID,
            profile_version=PROFILE_VERSION,
            required_detectors=tuple(sorted({DETECTOR_ID, *(item.detector_id for item in reports)})),
            reason_codes=tuple(sorted(codes, key=lambda item: item.value)),
        )
        return PrivacyResult(source=source, detector_reports=tuple(reports), decisions=(),
                             assessment=assessment, policy_version=POLICY_VERSION)

    if len(source.text) > limits.max_characters:
        # Avoid normalization/allocation on a rejected input.
        return failed(ReasonCode.RESOURCE_LIMIT)
    try:
        require_tuple(extra_detectors, DetectorSpec)
        if len(extra_detectors) > limits.max_extra_detectors:
            raise ResourceLimitError("detector budget exceeded")
        identities = {DETECTOR_ID}
        for spec in extra_detectors:
            spec.__post_init__()
            if spec.detector_id in identities:
                raise ValueError("duplicate detector identity")
            identities.add(spec.detector_id)
    except ResourceLimitError:
        return failed(ReasonCode.RESOURCE_LIMIT)
    except Exception:
        return failed(ReasonCode.INVALID_DETECTOR_OUTPUT)
    try:
        view = build_view(source)
    except Exception:
        return failed(ReasonCode.INVALID_OFFSET_MAPPING)
    try:
        rules_report = detect_rules(source, view=view, max_findings=limits.max_findings)
        validate_detector_report(source, rules_report)
        if (rules_report.detector_id, rules_report.detector_version) != (DETECTOR_ID, DETECTOR_VERSION):
            raise ValueError("rules detector provenance mismatch")
        reports.append(rules_report)
    except ResourceLimitError:
        return failed(ReasonCode.RESOURCE_LIMIT)
    except Exception:
        return failed(ReasonCode.DETECTOR_FAILED)
    for spec in extra_detectors:
        reasons = ()
        try:
            report = spec.detect(source)
        except ResourceLimitError:
            reasons = (ReasonCode.RESOURCE_LIMIT,)
        except Exception:
            reasons = (ReasonCode.DETECTOR_FAILED,)
        else:
            try:
                if type(report) is not DetectorReport:
                    raise TypeError("invalid detector report")
                require_tuple(report.findings, EntityFinding)
                if len(report.findings) + sum(len(item.findings) for item in reports) > limits.max_findings:
                    raise ResourceLimitError("total finding budget exceeded")
                validate_detector_report(source, report)
                if (report.detector_id, report.detector_version, set(report.supported_entities)) != (
                        spec.detector_id, spec.detector_version, set(spec.supported_entities)):
                    raise ValueError("detector declaration mismatch")
            except ResourceLimitError:
                reasons = (ReasonCode.RESOURCE_LIMIT,)
            except Exception:
                reasons = (ReasonCode.INVALID_DETECTOR_OUTPUT,)
                if type(report) is DetectorReport and type(getattr(report, "findings", None)) is tuple:
                    if any(type(getattr(item, "entity_type", None)) is not EntityType for item in report.findings):
                        reasons += (ReasonCode.UNKNOWN_LABEL,)
                if type(report) is DetectorReport and (
                        getattr(report, "source_id", None), getattr(report, "source_revision", None)) != (
                            source.source_id, source.source_revision):
                    reasons += (ReasonCode.CONTEXT_MISMATCH,)
        if reasons:
            reports.append(DetectorReport(
                source=source, detector_id=spec.detector_id, detector_version=spec.detector_version,
                status=DetectorStatus.FAILED, supported_entities=spec.supported_entities,
                findings=(), coverage=(), reason_codes=reasons,
            ))
        else:
            reports.append(report)
    if any(report.status is DetectorStatus.FAILED for report in reports):
        return failed(ReasonCode.DETECTOR_FAILED)
    try:
        groups = aggregate(source, tuple(reports), max_findings=limits.max_findings)
        decisions = plan_redactions(source, groups)
        output = render(source, decisions)
        assessment = assess(source, tuple(reports), groups, decisions, output, max_findings=limits.max_findings)
        return PrivacyResult(source=source, detector_reports=tuple(reports), decisions=decisions,
                             assessment=assessment, policy_version=POLICY_VERSION, output_text=output)
    except ResourceLimitError:
        return failed(ReasonCode.RESOURCE_LIMIT)
    except Exception:
        return failed(ReasonCode.INVALID_DETECTOR_OUTPUT)
