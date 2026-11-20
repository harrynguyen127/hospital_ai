"""PII-01 contracts only: no detection, rendering, inference, or authorization.

Spans address the original Python string in Unicode code points. Constructors
validate local structure; validate_detector_report is the untrusted-output
boundary. Diagnostic fields use closed enums and opaque identifiers, not text.
"""

from dataclasses import InitVar, dataclass, field
from enum import StrEnum
import re


SCHEMA_VERSION = "text-pii/1.0"
TAXONOMY_VERSION = "vi-clinical-pii/1.0"


class EntityType(StrEnum):
    PERSON = "PERSON"
    PHONE = "PHONE"
    EMAIL = "EMAIL"
    NATIONAL_ID = "NATIONAL_ID"
    PASSPORT = "PASSPORT"
    HEALTH_INSURANCE_ID = "HEALTH_INSURANCE_ID"
    PATIENT_ID = "PATIENT_ID"
    ENCOUNTER_ID = "ENCOUNTER_ID"
    DATE_OF_BIRTH = "DATE_OF_BIRTH"
    ADDRESS = "ADDRESS"
    GEO_COORDINATE = "GEO_COORDINATE"
    ACCOUNT_ID = "ACCOUNT_ID"
    FINANCIAL_ID = "FINANCIAL_ID"
    CONTACT_URL = "CONTACT_URL"
    ORGANIZATION = "ORGANIZATION"
    DATE = "DATE"
    TIME = "TIME"
    AGE = "AGE"
    OCCUPATION = "OCCUPATION"
    RARE_CONTEXT = "RARE_CONTEXT"
    UNKNOWN_IDENTIFIER = "UNKNOWN_IDENTIFIER"


class SubjectRole(StrEnum):
    PATIENT = "patient"
    CLINICIAN = "clinician"
    RELATIVE = "relative"
    OTHER = "other"
    UNKNOWN = "unknown"


class Identifiability(StrEnum):
    DIRECT = "direct"
    CONTEXTUAL = "contextual"
    INDIRECT = "indirect"
    AMBIGUOUS = "ambiguous"


class PolicyAction(StrEnum):
    PRESERVE = "preserve"
    REDACT = "redact"
    PSEUDONYMIZE = "pseudonymize"
    REVIEW = "review"


class OffsetUnit(StrEnum):
    UNICODE_CODE_POINT = "unicode_code_point"


class DetectorStatus(StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    FAILED = "failed"
    UNAVAILABLE = "unavailable"


class AssessmentStatus(StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    REVIEW_REQUIRED = "review_required"
    FAILED = "failed"


class OutboundRestriction(StrEnum):
    PROHIBITED = "prohibited"
    GATEWAY_REVIEW_REQUIRED = "gateway_review_required"


class ReasonCode(StrEnum):
    UNQUALIFIED_PROFILE = "unqualified_profile"
    DETECTOR_UNAVAILABLE = "detector_unavailable"
    DETECTOR_FAILED = "detector_failed"
    INCOMPLETE_COVERAGE = "incomplete_coverage"
    INVALID_DETECTOR_OUTPUT = "invalid_detector_output"
    INVALID_OFFSET_MAPPING = "invalid_offset_mapping"
    UNKNOWN_LABEL = "unknown_label"
    AMBIGUOUS_ENTITY = "ambiguous_entity"
    UNRESOLVED_CONFLICT = "unresolved_conflict"
    POSSIBLE_RESIDUAL_PII = "possible_residual_pii"
    INDIRECT_IDENTIFICATION_RISK = "indirect_identification_risk"
    CLINICAL_REVIEW_REQUIRED = "clinical_review_required"
    CONTEXT_MISMATCH = "context_mismatch"
    RESOURCE_LIMIT = "resource_limit"
    UNSUPPORTED_CATEGORIES = "unsupported_categories"


# These codes indicate pending review, incomplete evidence, or failed context.
# UNQUALIFIED_PROFILE is a qualification limitation, not an execution failure;
# a complete assessment can retain it while still requiring gateway review.
UNRESOLVED_RISK_REASONS = frozenset({
    ReasonCode.DETECTOR_UNAVAILABLE,
    ReasonCode.DETECTOR_FAILED,
    ReasonCode.INCOMPLETE_COVERAGE,
    ReasonCode.INVALID_DETECTOR_OUTPUT,
    ReasonCode.INVALID_OFFSET_MAPPING,
    ReasonCode.UNKNOWN_LABEL,
    ReasonCode.AMBIGUOUS_ENTITY,
    ReasonCode.UNRESOLVED_CONFLICT,
    ReasonCode.POSSIBLE_RESIDUAL_PII,
    ReasonCode.INDIRECT_IDENTIFICATION_RISK,
    ReasonCode.CLINICAL_REVIEW_REQUIRED,
    ReasonCode.CONTEXT_MISMATCH,
    ReasonCode.RESOURCE_LIMIT,
    ReasonCode.UNSUPPORTED_CATEGORIES,
})


def require_identifier(value: object) -> None:
    """Accept an opaque technical identifier, never a free-text diagnostic."""
    if type(value) is not str or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}", value):
        raise ValueError("invalid technical identifier")


def require_enum(value: object, enum_type: type[StrEnum]) -> None:
    if type(value) is not enum_type:
        raise TypeError("an explicit enum member is required")


def require_tuple(value: object, item_type: type) -> None:
    if type(value) is not tuple or any(type(item) is not item_type for item in value):
        raise TypeError("an immutable tuple of the declared type is required")


def _versions(schema_version: str, taxonomy_version: str) -> None:
    if (type(schema_version) is not str or type(taxonomy_version) is not str
            or schema_version != SCHEMA_VERSION or taxonomy_version != TAXONOMY_VERSION):
        raise ValueError("unsupported contract version")


@dataclass(frozen=True, slots=True, kw_only=True)
class TextInput:
    text: str = field(repr=False)
    source_id: str
    source_revision: str
    schema_version: str = SCHEMA_VERSION
    taxonomy_version: str = TAXONOMY_VERSION
    offset_unit: OffsetUnit = OffsetUnit.UNICODE_CODE_POINT

    def __post_init__(self) -> None:
        if type(self.text) is not str:
            raise TypeError("source text must be a string")
        require_identifier(self.source_id)
        require_identifier(self.source_revision)
        _versions(self.schema_version, self.taxonomy_version)
        require_enum(self.offset_unit, OffsetUnit)


def _source(source: TextInput) -> None:
    if type(source) is not TextInput:
        raise TypeError("a TextInput is required")
    source.__post_init__()


@dataclass(frozen=True, slots=True, kw_only=True)
class SourceSpan:
    start: int
    end: int

    def __post_init__(self) -> None:
        if type(self.start) is not int or type(self.end) is not int:
            raise TypeError("span offsets must be integers, excluding booleans")
        if self.start < 0 or self.end <= self.start:
            raise ValueError("span must be nonempty and start-inclusive/end-exclusive")

    def validate_for(self, source: TextInput) -> None:
        _source(source)
        self.__post_init__()
        if self.end > len(source.text):
            raise ValueError("span exceeds the original source")


def _bind(instance: object, source: TextInput) -> None:
    _source(source)
    object.__setattr__(instance, "source_id", source.source_id)
    object.__setattr__(instance, "source_revision", source.source_revision)


def _same_source(instance: object, source: TextInput) -> None:
    _source(source)
    if (instance.source_id, instance.source_revision) != (source.source_id, source.source_revision):
        raise ValueError("source identity or revision mismatch")


def _span(span: SourceSpan, source: TextInput) -> None:
    if type(span) is not SourceSpan:
        raise TypeError("a SourceSpan is required")
    span.validate_for(source)


def _reasons(reasons: tuple[ReasonCode, ...]) -> None:
    require_tuple(reasons, ReasonCode)
    if len(set(reasons)) != len(reasons):
        raise ValueError("duplicate reason codes")


@dataclass(frozen=True, slots=True, kw_only=True)
class EntityFinding:
    source: InitVar[TextInput]
    span: SourceSpan
    entity_type: EntityType
    subject_role: SubjectRole
    identifiability: Identifiability
    detector_id: str
    detector_version: str
    source_id: str = field(init=False)
    source_revision: str = field(init=False)

    def __post_init__(self, source: TextInput) -> None:
        _bind(self, source)
        self.validate_for(source)

    def validate_for(self, source: TextInput) -> None:
        _same_source(self, source)
        _span(self.span, source)
        require_enum(self.entity_type, EntityType)
        require_enum(self.subject_role, SubjectRole)
        require_enum(self.identifiability, Identifiability)
        require_identifier(self.detector_id)
        require_identifier(self.detector_version)


def covers_span(coverage: tuple[SourceSpan, ...], span: SourceSpan) -> bool:
    """Check union coverage; adjacent intervals may cover one finding."""
    cursor = span.start
    for interval in coverage:
        if interval.start > cursor:
            break
        cursor = max(cursor, interval.end)
        if cursor >= span.end:
            return True
    return False


@dataclass(frozen=True, slots=True, kw_only=True)
class DetectorReport:
    source: InitVar[TextInput]
    detector_id: str
    detector_version: str
    status: DetectorStatus
    supported_entities: tuple[EntityType, ...]
    findings: tuple[EntityFinding, ...]
    coverage: tuple[SourceSpan, ...]
    reason_codes: tuple[ReasonCode, ...] = ()
    model_revision: str | None = None
    schema_version: str = SCHEMA_VERSION
    taxonomy_version: str = TAXONOMY_VERSION
    offset_unit: OffsetUnit = OffsetUnit.UNICODE_CODE_POINT
    source_id: str = field(init=False)
    source_revision: str = field(init=False)

    def __post_init__(self, source: TextInput) -> None:
        _bind(self, source)
        validate_detector_report(source, self)


def validate_detector_report(source: TextInput, report: object) -> DetectorReport:
    """Reject malformed callback output before consuming any finding.

    No duck typing, coercion, source rebinding, or silent filtering is performed.
    The caller must issue a failed assessment when this boundary raises.
    """
    if type(report) is not DetectorReport:
        raise TypeError("detector output must be a DetectorReport")
    _same_source(report, source)
    _versions(report.schema_version, report.taxonomy_version)
    require_enum(report.offset_unit, OffsetUnit)
    require_identifier(report.detector_id)
    require_identifier(report.detector_version)
    if report.model_revision is not None:
        require_identifier(report.model_revision)
    require_enum(report.status, DetectorStatus)
    require_tuple(report.supported_entities, EntityType)
    if len(set(report.supported_entities)) != len(report.supported_entities):
        raise ValueError("duplicate supported entity categories")
    if report.status is not DetectorStatus.UNAVAILABLE and not report.supported_entities:
        raise ValueError("processed report requires explicit entity-category coverage")
    require_tuple(report.findings, EntityFinding)
    require_tuple(report.coverage, SourceSpan)
    _reasons(report.reason_codes)
    previous_end = 0
    for interval in report.coverage:
        _span(interval, source)
        if interval.start < previous_end:
            raise ValueError("coverage must be ordered and nonoverlapping")
        previous_end = interval.end
    for finding in report.findings:
        finding.validate_for(source)
        if finding.entity_type not in report.supported_entities:
            raise ValueError("finding category is outside declared detector support")
        if (finding.detector_id, finding.detector_version) != (report.detector_id, report.detector_version):
            raise ValueError("finding provenance differs from its detector report")
        if not covers_span(report.coverage, finding.span):
            raise ValueError("finding lies outside detector coverage")
    if report.status is DetectorStatus.COMPLETE:
        if source.text and not covers_span(report.coverage, SourceSpan(start=0, end=len(source.text))):
            raise ValueError("complete detector report requires full source coverage")
        if report.reason_codes:
            raise ValueError("complete detector report cannot carry failure or review codes")
    elif not report.reason_codes:
        raise ValueError("incomplete detector report requires reason codes")
    if report.status is DetectorStatus.UNAVAILABLE and (report.coverage or report.findings):
        raise ValueError("unavailable detector cannot claim processed coverage")
    return report


@dataclass(frozen=True, slots=True, kw_only=True)
class ReplacementDecision:
    """A policy annotation, not an executed replacement or rendering claim."""

    source: InitVar[TextInput]
    span: SourceSpan
    action: PolicyAction
    policy_version: str
    reason_codes: tuple[ReasonCode, ...] = ()
    source_id: str = field(init=False)
    source_revision: str = field(init=False)

    def __post_init__(self, source: TextInput) -> None:
        _bind(self, source)
        self.validate_for(source)

    def validate_for(self, source: TextInput) -> None:
        _same_source(self, source)
        _span(self.span, source)
        require_enum(self.action, PolicyAction)
        require_identifier(self.policy_version)
        _reasons(self.reason_codes)
        if self.action is PolicyAction.REVIEW and not self.reason_codes:
            raise ValueError("review decision requires reason codes")


@dataclass(frozen=True, slots=True, kw_only=True)
class PrivacyAssessment:
    source: InitVar[TextInput]
    status: AssessmentStatus
    profile_id: str
    profile_version: str
    required_detectors: tuple[str, ...]
    reason_codes: tuple[ReasonCode, ...]
    outbound_restriction: OutboundRestriction = OutboundRestriction.PROHIBITED
    source_id: str = field(init=False)
    source_revision: str = field(init=False)

    def __post_init__(self, source: TextInput) -> None:
        _bind(self, source)
        self.validate_for(source)

    def validate_for(self, source: TextInput) -> None:
        _same_source(self, source)
        require_enum(self.status, AssessmentStatus)
        require_enum(self.outbound_restriction, OutboundRestriction)
        require_identifier(self.profile_id)
        require_identifier(self.profile_version)
        require_tuple(self.required_detectors, str)
        for detector in self.required_detectors:
            require_identifier(detector)
        if len(set(self.required_detectors)) != len(self.required_detectors):
            raise ValueError("duplicate required detector identifiers")
        _reasons(self.reason_codes)
        if self.status is AssessmentStatus.COMPLETE:
            if not self.required_detectors:
                raise ValueError("complete assessment requires a detector profile")
            if UNRESOLVED_RISK_REASONS.intersection(self.reason_codes):
                raise ValueError("unresolved risk requires a non-complete assessment")
        else:
            if not self.reason_codes:
                raise ValueError("uncertain or failed assessment requires reason codes")
            if self.outbound_restriction is not OutboundRestriction.PROHIBITED:
                raise ValueError("uncertain or failed assessment prohibits outbound use")


@dataclass(frozen=True, slots=True, kw_only=True)
class PrivacyResult:
    """Validated envelope only; this class performs no privacy processing."""

    source: InitVar[TextInput]
    detector_reports: tuple[DetectorReport, ...]
    decisions: tuple[ReplacementDecision, ...]
    assessment: PrivacyAssessment
    policy_version: str
    output_text: str | None = field(default=None, repr=False)
    schema_version: str = SCHEMA_VERSION
    taxonomy_version: str = TAXONOMY_VERSION
    offset_unit: OffsetUnit = OffsetUnit.UNICODE_CODE_POINT
    source_id: str = field(init=False)
    source_revision: str = field(init=False)
    external_egress_authorized: bool = field(default=False, init=False)

    def __post_init__(self, source: TextInput) -> None:
        _bind(self, source)
        _versions(self.schema_version, self.taxonomy_version)
        require_enum(self.offset_unit, OffsetUnit)
        require_identifier(self.policy_version)
        if self.output_text is not None and type(self.output_text) is not str:
            raise TypeError("output text must be a string or absent")
        require_tuple(self.detector_reports, DetectorReport)
        require_tuple(self.decisions, ReplacementDecision)
        if type(self.assessment) is not PrivacyAssessment:
            raise TypeError("a PrivacyAssessment is required")
        self.assessment.validate_for(source)
        detector_ids = []
        for report in self.detector_reports:
            validate_detector_report(source, report)
            detector_ids.append(report.detector_id)
        if len(set(detector_ids)) != len(detector_ids):
            raise ValueError("duplicate detector reports")
        for decision in self.decisions:
            decision.validate_for(source)
            if decision.policy_version != self.policy_version:
                raise ValueError("decision policy version mismatch")
        if self.assessment.status is AssessmentStatus.COMPLETE:
            if not set(self.assessment.required_detectors).issubset(detector_ids):
                raise ValueError("complete assessment is missing a required detector")
            if any(report.status is not DetectorStatus.COMPLETE for report in self.detector_reports):
                raise ValueError("complete assessment cannot contain incomplete reports")
            if any(decision.action is PolicyAction.REVIEW for decision in self.decisions):
                raise ValueError("complete assessment has unresolved review decisions")
            if any(UNRESOLVED_RISK_REASONS.intersection(decision.reason_codes) for decision in self.decisions):
                raise ValueError("complete assessment has unresolved decision evidence")
