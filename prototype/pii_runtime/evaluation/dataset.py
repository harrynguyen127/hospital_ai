"""Independent synthetic ground-truth schema and small-dataset integrity tools.

Recognition annotations are not detector predictions. Policy and clinical
annotations are separate. Similarity checks are leakage heuristics, not proof
that an evaluation has independent custody or represents clinical practice.
"""

from dataclasses import asdict, dataclass, fields
from difflib import SequenceMatcher
from enum import StrEnum
import json
from pathlib import Path
import re
import unicodedata

from features.pii_filter.schema import (
    EntityType, Identifiability, OffsetUnit, PolicyAction, SourceSpan, SubjectRole, TextInput,
    require_enum, require_identifier, require_tuple,
)


DATASET_VERSION = "vi-clinical-pii-dataset/1.0"


class DatasetSplit(StrEnum):
    TRAIN = "train"
    DEVELOPMENT = "development"
    REGRESSION = "regression"
    EVALUATION = "evaluation"


class Exposure(StrEnum):
    EXPOSED = "exposed"
    INDEPENDENT_CUSTODY = "independent_custody"


class ClinicalCategory(StrEnum):
    MEDICATION = "medication"
    DOSAGE = "dosage"
    VITAL_SIGN = "vital_sign"
    NEGATION = "negation"
    SYMPTOM = "symptom"
    TEMPORAL = "temporal"
    FAMILY_HISTORY = "family_history"
    SUBJECT_ATTRIBUTION = "subject_attribution"


class ReviewReason(StrEnum):
    AMBIGUOUS_IDENTITY = "ambiguous_identity"
    INDIRECT_IDENTIFICATION = "indirect_identification"
    INCOMPLETE_CONTEXT = "incomplete_context"


@dataclass(frozen=True, slots=True, kw_only=True)
class EntityAnnotation:
    span: SourceSpan
    entity_type: EntityType
    subject_role: SubjectRole
    identifiability: Identifiability

    def __post_init__(self) -> None:
        if type(self.span) is not SourceSpan:
            raise TypeError("annotation requires a SourceSpan")
        require_enum(self.entity_type, EntityType)
        require_enum(self.subject_role, SubjectRole)
        require_enum(self.identifiability, Identifiability)


@dataclass(frozen=True, slots=True, kw_only=True)
class PolicyAnnotation:
    span: SourceSpan
    action: PolicyAction

    def __post_init__(self) -> None:
        if type(self.span) is not SourceSpan:
            raise TypeError("policy annotation requires a SourceSpan")
        require_enum(self.action, PolicyAction)


@dataclass(frozen=True, slots=True, kw_only=True)
class ClinicalAnnotation:
    span: SourceSpan
    category: ClinicalCategory
    subject_role: SubjectRole
    assertion_id: str

    def __post_init__(self) -> None:
        if type(self.span) is not SourceSpan:
            raise TypeError("clinical annotation requires a SourceSpan")
        require_enum(self.category, ClinicalCategory)
        require_enum(self.subject_role, SubjectRole)
        require_identifier(self.assertion_id)


@dataclass(frozen=True, slots=True, kw_only=True)
class ReviewAnnotation:
    span: SourceSpan
    reason: ReviewReason

    def __post_init__(self) -> None:
        if type(self.span) is not SourceSpan:
            raise TypeError("review annotation requires a SourceSpan")
        require_enum(self.reason, ReviewReason)


def _overlaps(left: SourceSpan, right: SourceSpan) -> bool:
    return left.start < right.end and right.start < left.end


@dataclass(frozen=True, slots=True, kw_only=True)
class DatasetRecord:
    record_id: str
    source: TextInput
    split: DatasetSplit
    scenario_family: str
    scenario_version: str
    generator_version: str
    seed: int
    entities: tuple[EntityAnnotation, ...]
    policies: tuple[PolicyAnnotation, ...]
    clinical: tuple[ClinicalAnnotation, ...]
    reviews: tuple[ReviewAnnotation, ...]
    exposure: Exposure = Exposure.EXPOSED
    custody_reference: str | None = None
    provenance: str = "project_synthetic"
    dataset_version: str = DATASET_VERSION

    @property
    def review_required(self) -> bool:
        return bool(self.reviews)

    def __post_init__(self) -> None:
        for identifier in (self.record_id, self.scenario_family, self.scenario_version, self.generator_version):
            require_identifier(identifier)
        if type(self.source) is not TextInput:
            raise TypeError("dataset source must be a TextInput")
        self.source.__post_init__()
        if type(self.seed) is not int or not 0 <= self.seed < 2**64:
            raise ValueError("seed must be an unsigned 64-bit integer, excluding booleans")
        if self.dataset_version != DATASET_VERSION or self.provenance != "project_synthetic":
            raise ValueError("unsupported dataset version or provenance")
        require_enum(self.split, DatasetSplit)
        require_enum(self.exposure, Exposure)
        if self.custody_reference is not None:
            require_identifier(self.custody_reference)
        if self.exposure is Exposure.INDEPENDENT_CUSTODY:
            if self.custody_reference is None:
                raise ValueError("independent custody requires an external procedure reference")
        elif self.custody_reference is not None:
            raise ValueError("exposed data cannot claim independent custody")
        if self.split is DatasetSplit.EVALUATION and self.exposure is not Exposure.INDEPENDENT_CUSTODY:
            raise ValueError("evaluation requires independent custody; a label alone is insufficient")
        for annotations, kind in (
            (self.entities, EntityAnnotation), (self.policies, PolicyAnnotation),
            (self.clinical, ClinicalAnnotation), (self.reviews, ReviewAnnotation),
        ):
            require_tuple(annotations, kind)
            for annotation in annotations:
                annotation.__post_init__()
                annotation.span.validate_for(self.source)
            if len(set(annotations)) != len(annotations):
                raise ValueError("duplicate ground-truth annotations")
        entity_spans = {annotation.span for annotation in self.entities}
        policy_spans = [annotation.span for annotation in self.policies]
        if set(policy_spans) != entity_spans or len(set(policy_spans)) != len(policy_spans):
            raise ValueError("each entity span requires exactly one separate policy annotation")
        # No precedence or adjudication contract exists in PII-01. Overlapping
        # gold policies must agree on the action, including REVIEW vs final gold.
        for index, policy in enumerate(self.policies):
            for other in self.policies[index + 1:]:
                if _overlaps(policy.span, other.span) and policy.action is not other.action:
                    raise ValueError("overlapping gold policies require the same action")
        for annotation in self.entities:
            if annotation.identifiability is Identifiability.AMBIGUOUS:
                if not any(_overlaps(annotation.span, item.span) for item in self.reviews):
                    raise ValueError("ambiguous recognition requires review annotation")
        for policy in self.policies:
            if policy.action is PolicyAction.REVIEW:
                if not any(_overlaps(policy.span, item.span) for item in self.reviews):
                    raise ValueError("review policy requires a review annotation")
            if policy.action in (PolicyAction.REDACT, PolicyAction.PSEUDONYMIZE):
                if any(_overlaps(policy.span, item.span) for item in self.clinical):
                    raise ValueError("redaction ground truth conflicts with protected clinical content")


def record_to_dict(record: DatasetRecord) -> dict:
    if type(record) is not DatasetRecord:
        raise TypeError("a DatasetRecord is required")
    record.__post_init__()
    def json_value(value):
        if isinstance(value, StrEnum):
            return value.value
        if type(value) is dict:
            return {key: json_value(item) for key, item in value.items()}
        if type(value) in (tuple, list):
            return [json_value(item) for item in value]
        return value

    return json_value(asdict(record))


def _object(value: object, keys: set[str]) -> dict:
    if type(value) is not dict or set(value) != keys:
        raise ValueError("invalid dataset object fields")
    return value


def _span_from_dict(value: object) -> SourceSpan:
    return SourceSpan(**_object(value, {"start", "end"}))


def record_from_dict(value: object) -> DatasetRecord:
    """Strict JSON boundary: reject extra fields, unknown labels and coercions."""
    try:
        data = dict(_object(value, {item.name for item in fields(DatasetRecord)}))
        source = dict(_object(data["source"], {item.name for item in fields(TextInput)}))
        source["offset_unit"] = OffsetUnit(source["offset_unit"])
        data["source"] = TextInput(**source)
        data["split"] = DatasetSplit(data["split"])
        data["exposure"] = Exposure(data["exposure"])
        definitions = (
            ("entities", EntityAnnotation, {"entity_type": EntityType, "subject_role": SubjectRole, "identifiability": Identifiability}),
            ("policies", PolicyAnnotation, {"action": PolicyAction}),
            ("clinical", ClinicalAnnotation, {"category": ClinicalCategory, "subject_role": SubjectRole}),
            ("reviews", ReviewAnnotation, {"reason": ReviewReason}),
        )
        for name, kind, enums in definitions:
            if type(data[name]) is not list:
                raise ValueError("JSON annotations must be arrays")
            annotations = []
            for raw in data[name]:
                annotation = dict(_object(raw, {item.name for item in fields(kind)}))
                annotation["span"] = _span_from_dict(annotation["span"])
                for key, enum in enums.items():
                    annotation[key] = enum(annotation[key])
                annotations.append(kind(**annotation))
            data[name] = tuple(annotations)
        return DatasetRecord(**data)
    except (TypeError, ValueError, KeyError):
        raise ValueError("invalid dataset record") from None


def _tokens(text: str) -> tuple[str, ...]:
    normalized = unicodedata.normalize("NFC", text).casefold()
    return tuple("NUMBER" if word.isdecimal() else word for word in re.findall(r"\w+", normalized))


def _skeleton(record: DatasetRecord) -> tuple[str, ...]:
    """Erase annotated identities to detect templates with different values."""
    pieces = []
    cursor = 0
    for span in sorted({item.span for item in record.entities}, key=lambda item: (item.start, -item.end)):
        if span.end <= cursor:
            continue
        if span.start >= cursor:
            pieces.extend((record.source.text[cursor:span.start], " IDENTIFIER "))
        cursor = span.end
    pieces.append(record.source.text[cursor:])
    return _tokens("".join(pieces))


def _similar(left: tuple[str, ...], right: tuple[str, ...], threshold: float) -> bool:
    forward = SequenceMatcher(None, left, right, autojunk=False).ratio()
    reverse = SequenceMatcher(None, right, left, autojunk=False).ratio()
    return max(forward, reverse) >= threshold


def validate_dataset(records: tuple[DatasetRecord, ...], *, similarity_threshold: float = 0.85) -> None:
    """Check records, family independence, and cross-split near duplicates.

    Pairwise comparison is intentional for the initial small corpus. Family IDs
    must stay stable across versions and seeds. This cannot detect every semantic
    paraphrase and does not verify the external custody procedure.
    """
    require_tuple(records, DatasetRecord)
    if not records:
        raise ValueError("dataset must contain at least one record")
    if type(similarity_threshold) not in (int, float) or not 0 < similarity_threshold <= 1:
        raise ValueError("similarity threshold must be in (0, 1]")
    record_ids = set()
    source_ids = set()
    family_splits = {}
    for record in records:
        record.__post_init__()
        if record.record_id in record_ids or record.source.source_id in source_ids:
            raise ValueError("duplicate record or source identity")
        record_ids.add(record.record_id)
        source_ids.add(record.source.source_id)
        previous = family_splits.setdefault(record.scenario_family, record.split)
        if previous is not record.split:
            raise ValueError("scenario family crosses dataset splits")
    comparisons = [(_tokens(record.source.text), _skeleton(record)) for record in records]
    for index, left in enumerate(records):
        for other_index in range(index + 1, len(records)):
            right = records[other_index]
            if left.split is right.split:
                continue
            if any(_similar(a, b, similarity_threshold) for a, b in zip(comparisons[index], comparisons[other_index])):
                raise ValueError("cross-split duplicate or near-duplicate content")


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object field")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError("nonstandard JSON numeric constant")


def read_dataset(path: str | Path) -> tuple[DatasetRecord, ...]:
    records = []
    with Path(path).open(encoding="utf-8") as stream:
        for line in stream:
            try:
                data = json.loads(line, object_pairs_hook=_unique_object, parse_constant=_reject_constant)
            except (ValueError, TypeError):
                raise ValueError("invalid dataset JSON line") from None
            records.append(record_from_dict(data))
    result = tuple(records)
    validate_dataset(result)
    return result


def write_dataset(path: str | Path, records: tuple[DatasetRecord, ...]) -> None:
    """Write validated JSONL outside the repository; never overwrite a file."""
    validate_dataset(records)
    destination = Path(path).expanduser().resolve()
    repository = Path(__file__).resolve().parents[3]
    if destination.is_relative_to(repository):
        raise ValueError("generated datasets must remain outside the repository")
    payload = "".join(json.dumps(record_to_dict(record), ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n" for record in records)
    with destination.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(payload)
