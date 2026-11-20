"""Generate a small, exposed development corpus; never a blind evaluation.

Run from prototype: python3.12 -B -m pii_runtime.evaluation.generate_synthetic
    --seed 17 --output /outside/repository/development.jsonl
"""

import argparse
from pathlib import Path
import random
import unicodedata

from features.pii_filter.schema import EntityType, Identifiability, PolicyAction, SourceSpan, SubjectRole, TextInput
from pii_runtime.evaluation.dataset import (
    ClinicalAnnotation, ClinicalCategory, DatasetRecord, DatasetSplit,
    EntityAnnotation, PolicyAnnotation, ReviewAnnotation, ReviewReason,
    validate_dataset, write_dataset,
)


GENERATOR_VERSION = "synthetic-development/1.0"
SCENARIO_VERSION = "1.0"


def generate_development(seed: int = 17) -> tuple[DatasetRecord, ...]:
    """Build annotations while composing text, without ambiguous string search.

    Values are fictional fixture inventions. Phone/ID syntax is not a claim that
    a number is reserved or unassigned. Do not contact any generated identifier.
    """
    if type(seed) is not int or not 0 <= seed < 2**64:
        raise ValueError("seed must be an unsigned 64-bit integer, excluding booleans")
    rng = random.Random(seed)
    name = rng.choice(("Nguyễn Mẫu An", "Trần Thử Bình", "Lê Giả Minh"))
    phone = "090" + "".join(str(rng.randrange(10)) for _ in range(7))
    patient_id = f"SYN-BN-{rng.randrange(10000, 99999)}"
    insurance = f"SYN-BHYT-DN-{rng.randrange(1000000000000, 9999999999999)}"
    records = []

    def build(family: str, segments: tuple) -> None:
        pieces = []
        entities, policies, clinical, reviews = [], [], [], []
        cursor = 0
        for segment in segments:
            if type(segment) is str:
                pieces.append(segment)
                cursor += len(segment)
                continue
            kind, value, *attributes = segment
            span = SourceSpan(start=cursor, end=cursor + len(value))
            pieces.append(value)
            cursor += len(value)
            if kind == "entity":
                entity_type, role, identifiability, action = attributes
                entities.append(EntityAnnotation(span=span, entity_type=entity_type, subject_role=role, identifiability=identifiability))
                policies.append(PolicyAnnotation(span=span, action=action))
                if action is PolicyAction.REVIEW or identifiability is Identifiability.AMBIGUOUS:
                    reason = ReviewReason.INDIRECT_IDENTIFICATION if identifiability is Identifiability.INDIRECT else ReviewReason.AMBIGUOUS_IDENTITY
                    reviews.append(ReviewAnnotation(span=span, reason=reason))
            elif kind == "clinical":
                category, role = attributes
                clinical.append(ClinicalAnnotation(span=span, category=category, subject_role=role, assertion_id=f"assertion-{len(clinical) + 1}"))
            else:
                raise ValueError("unknown generator segment")
        identifier = f"dev-{seed}-{family}"
        records.append(DatasetRecord(
            record_id=identifier,
            source=TextInput(text="".join(pieces), source_id=identifier, source_revision="1"),
            split=DatasetSplit.DEVELOPMENT, scenario_family=family,
            scenario_version=SCENARIO_VERSION, generator_version=GENERATOR_VERSION,
            seed=seed, entities=tuple(entities), policies=tuple(policies),
            clinical=tuple(clinical), reviews=tuple(reviews),
        ))

    def entity(value, kind, role=SubjectRole.PATIENT, identifiability=Identifiability.DIRECT, action=PolicyAction.REDACT):
        return ("entity", value, kind, role, identifiability, action)

    def fact(value, category, role=SubjectRole.PATIENT):
        return ("clinical", value, category, role)

    build("named-patient", ("Bệnh nhân ", entity(name, EntityType.PERSON), ", ", fact("đau bụng 3 ngày", ClinicalCategory.SYMPTOM), "."))
    build("phone-contact", ("Số liên hệ: ", entity(phone, EntityType.PHONE), "."))
    build("patient-reference", ("Mã bệnh nhân ", entity(patient_id, EntityType.PATIENT_ID), "; cần đối chiếu phiếu."))
    build("insurance-reference", ("Mã bảo hiểm thử nghiệm: ", entity(insurance, EntityType.HEALTH_INSURANCE_ID), "."))
    build("birth-date", ("Ngày sinh ", entity("12/03/1990", EntityType.DATE_OF_BIRTH), "."))
    build("residential-address", ("Địa chỉ giả lập: ", entity("42 đường Mẫu, phường Thử Nghiệm", EntityType.ADDRESS), "."))
    build("multiple-identifiers", (entity(name, EntityType.PERSON), ", SĐT ", entity(phone, EntityType.PHONE), ", mã ", entity(patient_id, EntityType.PATIENT_ID), "."))
    build("repeated-contact", ("Gọi ", entity(phone, EntityType.PHONE), "; xác nhận lại ", entity(phone, EntityType.PHONE), "."))
    build("nfd-name", ("Tên viết theo NFD: ", entity(unicodedata.normalize("NFD", name), EntityType.PERSON), "."))
    build("asr-style", ("ờ bệnh nhân ", entity(name.lower(), EntityType.PERSON), " à à ", fact("không đau ngực", ClinicalCategory.NEGATION), "."))
    build("spoken-phone", ("số điện thoại là ", entity("không chín không một hai ba bốn năm sáu bảy", EntityType.PHONE), "."))
    build("medication-dose", (fact("Amoxicillin", ClinicalCategory.MEDICATION), " ", fact("500 mg", ClinicalCategory.DOSAGE), ", ", fact("ngày 3 lần", ClinicalCategory.TEMPORAL), "."))
    build("vital-signs", (fact("Mạch 92 lần/phút", ClinicalCategory.VITAL_SIGN), "; ", fact("huyết áp 120/80 mmHg", ClinicalCategory.VITAL_SIGN), "."))
    build("negative-allergy", (fact("Không dị ứng thuốc", ClinicalCategory.NEGATION), "."))
    build("relative-history", (fact("Mẹ bệnh nhân có tiền sử đái tháo đường", ClinicalCategory.FAMILY_HISTORY, SubjectRole.RELATIVE), "."))
    build("named-relative", ("Mẹ bệnh nhân là ", entity("Trần Giả Mai", EntityType.PERSON, SubjectRole.RELATIVE), ", ", fact("có tiền sử đái tháo đường", ClinicalCategory.FAMILY_HISTORY, SubjectRole.RELATIVE), "."))
    build("clinician-attribution", ("Bác sĩ ", entity("Lê Mẫu Khoa", EntityType.PERSON, SubjectRole.CLINICIAN), " nói: ", fact("không dị ứng thuốc", ClinicalCategory.NEGATION), "."))
    build("contextual-date-organization", ("Tái khám tại ", entity("Bệnh viện Mô Phỏng", EntityType.ORGANIZATION, SubjectRole.OTHER, Identifiability.CONTEXTUAL, PolicyAction.PRESERVE), " vào ", entity("18/11/2026", EntityType.DATE, identifiability=Identifiability.CONTEXTUAL, action=PolicyAction.PRESERVE), "."))
    build("ambiguous-name", ("Nhắc đến ", entity("An", EntityType.PERSON, SubjectRole.UNKNOWN, Identifiability.AMBIGUOUS, PolicyAction.REVIEW), ", chưa rõ người nào."))
    build("indirect-context", ("Bệnh nhân là ", entity("người duy nhất làm nghề sửa đồng hồ trong xóm Mô Phỏng", EntityType.RARE_CONTEXT, identifiability=Identifiability.INDIRECT, action=PolicyAction.REVIEW), "."))
    result = tuple(records)
    validate_dataset(result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate 20 exposed synthetic development records outside Git.")
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        records = generate_development(args.seed)
        write_dataset(args.output, records)
    except (TypeError, ValueError, OSError) as error:
        parser.exit(2, f"Generation failed: {error}\n")
    print(f"Wrote {len(records)} exposed development records; no blind evaluation was created.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
