"""Small, exposed synthetic transcript fixtures for two workflow scenarios.

Role metadata is sidecar evaluation data. It is never added to TextInput or
passed into the text engine, and a missing speaker role remains ``None``.
"""

from dataclasses import dataclass
from enum import StrEnum

from features.pii_filter.schema import (
    AssessmentStatus, EntityType, Identifiability, PolicyAction, SourceSpan,
    SubjectRole, TextInput, require_enum, require_identifier, require_tuple,
)
from pii_runtime.evaluation.dataset import (
    ClinicalAnnotation, ClinicalCategory, EntityAnnotation, PolicyAnnotation,
)


class ScenarioType(StrEnum):
    DOCTOR_PATIENT_CONVERSATION = "DOCTOR_PATIENT_CONVERSATION"
    NURSE_CHART_READBACK = "NURSE_CHART_READBACK"


class SpeakerRole(StrEnum):
    DOCTOR = "doctor"
    NURSE = "nurse"
    PATIENT = "patient"
    OTHER = "other"


@dataclass(frozen=True, slots=True, kw_only=True)
class TranscriptSegment:
    text: str
    entity_type: EntityType | None = None
    subject_role: SubjectRole = SubjectRole.UNKNOWN
    identifiability: Identifiability = Identifiability.DIRECT
    action: PolicyAction | None = None
    supported_case: bool = True
    unsupported_reason: str | None = None
    partial_prediction_chars: int | None = None
    clinical_category: ClinicalCategory | None = None
    clinical_subject_role: SubjectRole = SubjectRole.PATIENT

    def __post_init__(self) -> None:
        if type(self.text) is not str or not self.text:
            raise ValueError("scenario segments must contain text")
        if type(self.supported_case) is not bool:
            raise TypeError("supported_case must be an explicit boolean")
        if self.action is not None:
            require_enum(self.action, PolicyAction)
        if self.entity_type is not None:
            require_enum(self.entity_type, EntityType)
            require_enum(self.subject_role, SubjectRole)
            require_enum(self.identifiability, Identifiability)
            if self.action is not PolicyAction.REDACT or self.clinical_category is not None:
                raise ValueError("PII fixture segments require one redaction policy")
            if self.unsupported_reason is not None and not self.unsupported_reason.strip():
                raise ValueError("unsupported cases require an explanatory reason")
            if not self.supported_case and self.unsupported_reason is None:
                raise ValueError("unsupported ground truth requires an explanatory reason")
            if self.partial_prediction_chars is not None:
                if (type(self.partial_prediction_chars) is not int
                        or not 0 < self.partial_prediction_chars < len(self.text)):
                    raise ValueError("partial detector span must be a strict prefix")
        elif self.action is not None or self.unsupported_reason is not None or self.partial_prediction_chars is not None:
            raise ValueError("PII-only fixture metadata requires an entity segment")
        if self.clinical_category is not None:
            require_enum(self.clinical_category, ClinicalCategory)
            require_enum(self.clinical_subject_role, SubjectRole)
            if self.entity_type is not None:
                raise ValueError("a segment cannot be both PII and protected clinical ground truth")


@dataclass(frozen=True, slots=True, kw_only=True)
class TranscriptTurn:
    speaker_role: SpeakerRole | None
    segments: tuple[TranscriptSegment, ...]

    def __post_init__(self) -> None:
        if self.speaker_role is not None:
            require_enum(self.speaker_role, SpeakerRole)
        require_tuple(self.segments, TranscriptSegment)
        if not self.segments:
            raise ValueError("transcript turns cannot be empty")


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkflowFixture:
    scenario_id: str
    scenario_type: ScenarioType
    turns: tuple[TranscriptTurn, ...]
    expected_assessment_status: AssessmentStatus

    def __post_init__(self) -> None:
        require_identifier(self.scenario_id)
        require_enum(self.scenario_type, ScenarioType)
        require_tuple(self.turns, TranscriptTurn)
        require_enum(self.expected_assessment_status, AssessmentStatus)
        if not self.turns:
            raise ValueError("scenario fixtures require at least one turn")


@dataclass(frozen=True, slots=True, kw_only=True)
class MaterializedFixture:
    fixture: WorkflowFixture
    source: TextInput
    entities: tuple[EntityAnnotation, ...]
    policies: tuple[PolicyAnnotation, ...]
    clinical: tuple[ClinicalAnnotation, ...]
    unsupported_cases: tuple[tuple[SourceSpan, str], ...]
    partial_predictions: tuple[tuple[SourceSpan, EntityType], ...]


def materialize(fixture: WorkflowFixture) -> MaterializedFixture:
    """Build the exact transcript and source-grounded spans from text segments."""
    fixture.__post_init__()
    chunks: list[str] = []
    entities: list[EntityAnnotation] = []
    policies: list[PolicyAnnotation] = []
    clinical: list[ClinicalAnnotation] = []
    unsupported: list[tuple[SourceSpan, str]] = []
    partial_predictions: list[tuple[SourceSpan, EntityType]] = []
    offset = 0
    clinical_index = 0
    for turn_index, turn in enumerate(fixture.turns):
        if turn_index:
            chunks.append("\n")
            offset += 1
        for segment in turn.segments:
            start, end = offset, offset + len(segment.text)
            chunks.append(segment.text)
            offset = end
            if segment.entity_type is not None:
                span = SourceSpan(start=start, end=end)
                entities.append(EntityAnnotation(
                    span=span, entity_type=segment.entity_type,
                    subject_role=segment.subject_role,
                    identifiability=segment.identifiability,
                ))
                policies.append(PolicyAnnotation(span=span, action=segment.action))
                if segment.unsupported_reason is not None:
                    unsupported.append((span, segment.unsupported_reason))
                if segment.partial_prediction_chars is not None:
                    partial_predictions.append((
                        SourceSpan(start=start, end=start + segment.partial_prediction_chars),
                        segment.entity_type,
                    ))
            if segment.clinical_category is not None:
                clinical_index += 1
                clinical.append(ClinicalAnnotation(
                    span=SourceSpan(start=start, end=end),
                    category=segment.clinical_category,
                    subject_role=segment.clinical_subject_role,
                    assertion_id=f"{fixture.scenario_id}-clinical-{clinical_index}",
                ))
    source = TextInput(
        text="".join(chunks), source_id=f"workflow-{fixture.scenario_id}", source_revision="1",
    )
    for annotation in (*entities, *policies, *clinical):
        annotation.span.validate_for(source)
    return MaterializedFixture(
        fixture=fixture, source=source, entities=tuple(entities), policies=tuple(policies),
        clinical=tuple(clinical), unsupported_cases=tuple(unsupported),
        partial_predictions=tuple(partial_predictions),
    )


def _segment(text: str, *, entity_type: EntityType | None = None,
             subject_role: SubjectRole = SubjectRole.UNKNOWN,
             clinical: ClinicalCategory | None = None,
             clinical_subject: SubjectRole = SubjectRole.PATIENT,
             supported: bool = True, unsupported_reason: str | None = None,
             partial_prediction_chars: int | None = None) -> TranscriptSegment:
    return TranscriptSegment(
        text=text, entity_type=entity_type, subject_role=subject_role,
        identifiability=Identifiability.DIRECT, action=PolicyAction.REDACT if entity_type else None,
        supported_case=supported, unsupported_reason=unsupported_reason,
        partial_prediction_chars=partial_prediction_chars, clinical_category=clinical,
        clinical_subject_role=clinical_subject,
    )


def get_workflow_fixtures() -> tuple[WorkflowFixture, ...]:
    """Return compact deterministic fixtures containing only invented data."""
    review = AssessmentStatus.REVIEW_REQUIRED
    doctor_patient = WorkflowFixture(
        scenario_id="doctor-patient-01",
        scenario_type=ScenarioType.DOCTOR_PATIENT_CONVERSATION,
        expected_assessment_status=review,
        turns=(
            TranscriptTurn(speaker_role=SpeakerRole.DOCTOR, segments=(
                _segment("Bác sĩ: Anh vui lòng cho biết họ tên?"),
            )),
            TranscriptTurn(speaker_role=SpeakerRole.PATIENT, segments=(
                _segment("Bệnh nhân: Tôi tên là "),
                _segment("Nguyễn Văn An", entity_type=EntityType.PERSON, subject_role=SubjectRole.PATIENT),
                _segment("."),
            )),
            TranscriptTurn(speaker_role=SpeakerRole.DOCTOR, segments=(
                _segment("Bác sĩ: Anh sinh ngày nào?"),
            )),
            TranscriptTurn(speaker_role=SpeakerRole.PATIENT, segments=(
                _segment("Bệnh nhân: Ngày sinh của tôi là "),
                _segment("mười hai tháng ba năm một nghìn chín trăm chín mươi",
                         entity_type=EntityType.DATE_OF_BIRTH, subject_role=SubjectRole.PATIENT,
                         supported=False,
                         unsupported_reason="Spoken date-of-birth words are not detected by the current rules profile."),
                _segment("."),
            )),
            TranscriptTurn(speaker_role=SpeakerRole.PATIENT, segments=(
                _segment("Bệnh nhân: À... tôi đang dùng "),
                _segment("Amoxicillin 500 mg", clinical=ClinicalCategory.MEDICATION),
                _segment(". Không dị ứng thuốc", clinical=ClinicalCategory.NEGATION),
                _segment("; đau bụng", clinical=ClinicalCategory.SYMPTOM),
                _segment(" ba ngày", clinical=ClinicalCategory.TEMPORAL),
                _segment(", sửa lại: không phải ba tuần", clinical=ClinicalCategory.NEGATION),
                _segment("."),
            )),
            TranscriptTurn(speaker_role=SpeakerRole.PATIENT, segments=(
                _segment("Bệnh nhân: Mẹ bệnh nhân là "),
                _segment("Lê Thị Mai", entity_type=EntityType.PERSON, subject_role=SubjectRole.RELATIVE),
                _segment(", có tiền sử đái tháo đường",
                         clinical=ClinicalCategory.FAMILY_HISTORY,
                         clinical_subject=SubjectRole.RELATIVE),
                _segment("."),
            )),
            TranscriptTurn(speaker_role=None, segments=(
                _segment("Người nói không rõ: SĐT "),
                _segment("0912345678", entity_type=EntityType.PHONE, subject_role=SubjectRole.UNKNOWN),
            )),
            TranscriptTurn(speaker_role=SpeakerRole.PATIENT, segments=(
                _segment("Bệnh nhân: "),
                _segment("Nguyễn Văn An", entity_type=EntityType.PERSON, subject_role=SubjectRole.PATIENT),
                _segment(" xác nhận thông tin; mạch 92, sửa lại 90",
                         clinical=ClinicalCategory.VITAL_SIGN),
                _segment("."),
            )),
        ),
    )

    nurse_readback = WorkflowFixture(
        scenario_id="nurse-readback-01",
        scenario_type=ScenarioType.NURSE_CHART_READBACK,
        expected_assessment_status=review,
        turns=(
            TranscriptTurn(speaker_role=SpeakerRole.NURSE, segments=(
                _segment("Điều dưỡng đọc lại: Họ tên: "),
                _segment("Trần Giả Minh", entity_type=EntityType.PERSON, subject_role=SubjectRole.PATIENT),
                _segment(" SpO2 98%", clinical=ClinicalCategory.VITAL_SIGN),
                _segment("; mã bệnh nhân "),
                _segment("SYN-BN-042", entity_type=EntityType.PATIENT_ID,
                         subject_role=SubjectRole.PATIENT),
                _segment(" mạch 92 lần/phút", clinical=ClinicalCategory.VITAL_SIGN),
                _segment("; mã lượt khám "),
                _segment("VK-2026-042", entity_type=EntityType.ENCOUNTER_ID,
                         subject_role=SubjectRole.PATIENT),
                _segment("; thuốc của bệnh nhân "),
                _segment("Nguyễn Văn An", entity_type=EntityType.PERSON,
                         subject_role=SubjectRole.PATIENT),
                _segment(" Metformin 500 mg", clinical=ClinicalCategory.MEDICATION),
                _segment("; BHYT: "),
                _segment("ABC123456789", entity_type=EntityType.HEALTH_INSURANCE_ID,
                         subject_role=SubjectRole.PATIENT, supported=False,
                         unsupported_reason="No BHYT identifier format is implemented or claimed.",
                         partial_prediction_chars=3),
                _segment("; ngày sinh: "),
                _segment("12/03/1990", entity_type=EntityType.DATE_OF_BIRTH,
                         subject_role=SubjectRole.PATIENT),
                _segment("; HIV dương tính", clinical=ClinicalCategory.DIAGNOSIS_OR_LAB_RESULT),
                _segment("; không dị ứng thuốc", clinical=ClinicalCategory.NEGATION),
                _segment(". Ghi chú: "),
                _segment("theo dõi ổn định; " * 80, clinical=ClinicalCategory.SUBJECT_ATTRIBUTION),
            )),
        ),
    )
    return doctor_patient, nurse_readback
