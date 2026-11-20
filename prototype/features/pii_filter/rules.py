"""Bounded Vietnamese identifier rules; pattern plausibility is not identity validation."""

from datetime import date
import re
import unicodedata

from features.pii_filter.normalization import AnalysisView, ResourceLimitError, build_view
from features.pii_filter.schema import (
    DetectorReport, DetectorStatus, EntityFinding, EntityType, Identifiability,
    SourceSpan, SubjectRole, TextInput,
)


DETECTOR_ID = "vi-text-rules"
DETECTOR_VERSION = "2.1"
SUPPORTED_ENTITIES = (
    EntityType.PERSON, EntityType.PHONE, EntityType.EMAIL, EntityType.NATIONAL_ID,
    EntityType.PATIENT_ID, EntityType.ENCOUNTER_ID, EntityType.DATE_OF_BIRTH,
)
_PHONE = re.compile(
    r"(?<![\w+])(?:0[ .-]?(?:[35789](?:[ .-]?[0-9]){8}|2(?:[ .-]?[0-9]){9})"
    r"|\+84[ .-]?(?:[35789](?:[ .-]?[0-9]){8}|2(?:[ .-]?[0-9]){9}))(?![\w]|[ .-]*[0-9])"
)
_EMAIL = re.compile(r"(?<![\w@.+-])[\w.+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}(?![\w@-]|\.[A-Za-z0-9])")
_ID = re.compile(
    r"(?i)\b(?:CCCD|CMND|căn[ \t]+cước(?:[ \t]+công[ \t]+dân)?|chứng[ \t]+minh[ \t]+nhân[ \t]+dân)"
    r"[ \t]*[:#=-]?[ \t]*(?P<value>[0-9](?:[ .-]?[0-9]){8}(?:(?:[ .-]?[0-9]){3})?)(?![\w]|[ .-]?[0-9])"
)
_REFERENCES = (
    (EntityType.PATIENT_ID, re.compile(
        r"(?i)\b(?:mã[ \t]+(?:bệnh[ \t]+nhân|BN)|ma[ \t]+benh[ \t]+nhan|patient[ \t]+id)"
        r"[ \t]*[:#=]?[ \t]*(?P<value>[A-Za-z0-9][A-Za-z0-9_-]{0,39})(?![\w/-]|\.[A-Za-z0-9])")),
    (EntityType.ENCOUNTER_ID, re.compile(
        r"(?i)\b(?:mã[ \t]+(?:(?:lượt|lần|đợt)[ \t]+khám|khám)|encounter[ \t]+id|visit[ \t]+id)"
        r"[ \t]*[:#=]?[ \t]*(?P<value>[A-Za-z0-9][A-Za-z0-9_-]{0,39})(?![\w/-]|\.[A-Za-z0-9])")),
)
_DOB = re.compile(
    r"(?i)\b(?:ngày[ \t]+sinh|sinh[ \t]+ngày|ngay[ \t]+sinh|DOB|date[ \t]+of[ \t]+birth)"
    r"[ \t]*[:=]?[ \t]*(?P<value>[0-9]{1,2}[/\-][0-9]{1,2}[/\-][0-9]{4})(?![\w/\-])"
)
_NAME_CUE = re.compile(
    r"(?i)\b(?:mẹ[ \t]+bệnh[ \t]+nhân[ \t]+là|cha[ \t]+bệnh[ \t]+nhân[ \t]+là|"
    r"me[ \t]+benh[ \t]+nhan[ \t]+la|cha[ \t]+benh[ \t]+nhan[ \t]+la|"
    r"người[ \t]+liên[ \t]+hệ[ \t]+là|nguoi[ \t]+lien[ \t]+he[ \t]+la|"
    r"họ[ \t]+tên|ho[ \t]+ten|tên[ \t]+là|ten[ \t]+la|"
    r"bệnh[ \t]+nhân(?:[ \t]*[,，]?[ \t]+(?:là|la|tên[ \t]+là|ten[ \t]+la))?|"
    r"benh[ \t]+nhan(?:[ \t]*[,，]?[ \t]+(?:la|ten[ \t]+la))?|"
    r"bác[ \t]+sĩ|bac[ \t]+si|BS\.?|ông|bà|anh|chị)"
    r"(?:[ \t]*[:=][ \t]*|[ \t]+)"
)
_WORDS = re.compile(r"[^\W\d_]+(?:[ \t]+[^\W\d_]+){0,5}")
_SURNAMES = frozenset("nguyen tran le pham hoang huynh phan vu vo dang bui do ho ngo duong ly trinh luong".split())
_CLINICAL_STOPS = frozenset("dau mach huyet khong co thuoc sot sua ngay dang duoc noi a tien trieu amoxicillin".split())
_CLINICAL_ABBREVIATIONS = frozenset(
    "hiv hbv hcv copd aids ckd cad tb dm hba1c ecg eeg mri ct bmi".split()
)
_COMMON_NAME_CONTINUATIONS = frozenset(
    "thi van minh ngoc quoc hoang huy thanh thien tuan anh khanh duc gia bao phuong kim"
    " trung huu nhat my thuy linh viet xuan nhan tam phuc trong huu tan son tien tu an dang".split()
)
_NAME_CLINICAL_HOMOGRAPHS = frozenset({"dang", "tien", "co"})
_HOMOGRAPH_NAME_FORMS = {"dang": "đăng", "tien": "tiên", "co": "cô"}
_HOMOGRAPH_CLINICAL_FORMS = {"dang": "đang", "tien": "tiền", "co": "có"}
_ONGOING_VERBS = frozenset("dung uong dieu tri su dung theo doi ky".split())
_PREDICATE_WORDS = frozenset("dau the sot met kho tho".split())
_POST_NAME_PHRASE = re.compile(
    r"(?i)(?:xác[ \t]+nhận|xac[ \t]+nhan|ghi[ \t]+nhận|ghi[ \t]+nhan|tái[ \t]+khám|tai[ \t]+kham)\b"
)
_CLINICAL_COMPOUND = re.compile(
    r"(?i)(?:SpO2|HbA1c|GCS|BMI|ECG|EEG|MRI|CT)(?=\s*(?:\d|[%.,;:]|$))"
)
_DOSE_AFTER_TERM = re.compile(
    r"(?i)^[ \t]+\d+(?:[.,]\d+)?[ \t]*(?:mg|mcg|μg|µg|g|ml|iu|units?)\b"
)
_SPOKEN_CUE = re.compile(r"(?i)\b(?:số[ \t]+điện[ \t]+thoại|sđt|phone)[ \t]*(?:là[ \t]+|:[ \t]*)?")
_DIGITS = {word: str(index) for index, word in enumerate("khong mot hai ba bon nam sau bay tam chin".split())}
_PHONE_CUE = re.compile(r"(?i)(?:điện[ \t]+thoại|sđt|phone)[ \t:=-]*$")
_MEASUREMENT = re.compile(r"(?i)^[ \t]*(?:mg|ml|mmHg|mmol/l|lần/phút|bpm)\b")


def _fold(value: str) -> str:
    return "".join(char for char in unicodedata.normalize("NFD", value.casefold().replace("đ", "d"))
                   if not unicodedata.category(char).startswith("M"))


def _homograph_boundary(surface: str, following: str, *, has_name_prefix: bool) -> str:
    """Resolve common Vietnamese name/clinical homographs conservatively.

    Exact Vietnamese tone distinguishes forms such as Đăng/đang and
    Tiên/tiền without relying on case. Unaccented ASR text is resolved only
    when punctuation, a known name continuation, or a clear clinical phrase
    supplies a boundary; otherwise callers must request review.
    """
    folded = _fold(surface)
    if folded not in _NAME_CLINICAL_HOMOGRAPHS:
        return "ambiguous"
    normalized = unicodedata.normalize("NFC", surface).casefold()
    tail = following.lstrip(" \t")
    next_word = re.match(r"[^\W\d_]+", tail)
    next_folded = _fold(next_word.group()) if next_word is not None else None
    if folded == "dang" and next_folded == "ky":
        return "ambiguous" if has_name_prefix else "clinical"
    if normalized == _HOMOGRAPH_NAME_FORMS[folded]:
        return "name"
    if normalized == _HOMOGRAPH_CLINICAL_FORMS[folded]:
        return "clinical"

    if not tail or tail[0] in ",;.!?:)]}\r\n":
        return "name"
    if next_word is None:
        return "ambiguous"
    assert next_folded is not None
    if folded == "tien" and next_folded == "su":
        return "clinical"
    if folded == "dang" and next_folded in _ONGOING_VERBS:
        return "ambiguous" if has_name_prefix else "clinical"
    if folded == "co" and next_folded in _PREDICATE_WORDS:
        return "ambiguous" if has_name_prefix else "clinical"
    if next_folded in _COMMON_NAME_CONTINUATIONS:
        return "name"
    if (next_folded in _CLINICAL_STOPS or next_folded in _CLINICAL_ABBREVIATIONS
            or _CLINICAL_COMPOUND.match(tail) is not None):
        return "name" if has_name_prefix else "ambiguous"
    next_end = len(following) - len(tail) + next_word.end()
    if _DOSE_AFTER_TERM.match(following[next_end:]) is not None:
        return "name" if has_name_prefix else "ambiguous"
    return "ambiguous"


def detect_rules(source: TextInput, *, view: AnalysisView | None = None, max_findings: int = 512) -> DetectorReport:
    if type(max_findings) is not int or not 0 < max_findings <= 4096:
        raise ValueError("invalid finding budget")
    view = build_view(source) if view is None else view
    if type(view) is not AnalysisView or view.form != "NFC":
        raise ValueError("rules require a verified NFC view")
    view.validate_source(source)
    view.__post_init__()
    text = view.text
    findings = []

    def add(start, end, kind, role=SubjectRole.UNKNOWN, identifiability=Identifiability.DIRECT):
        if len(findings) >= max_findings:
            raise ResourceLimitError("finding budget exceeded")
        findings.append(EntityFinding(
            source=source, span=view.source_span(start, end), entity_type=kind,
            subject_role=role, identifiability=identifiability,
            detector_id=DETECTOR_ID, detector_version=DETECTOR_VERSION,
        ))

    for match in _EMAIL.finditer(text):
        add(*match.span(), EntityType.EMAIL)
    for match in _PHONE.finditer(text):
        if _MEASUREMENT.match(text[match.end():]) and not _PHONE_CUE.search(text[max(0, match.start() - 32):match.start()]):
            continue
        add(*match.span(), EntityType.PHONE)
    for match in _ID.finditer(text):
        add(*match.span("value"), EntityType.NATIONAL_ID)
    for kind, pattern in _REFERENCES:
        for match in pattern.finditer(text):
            if any(char.isdecimal() for char in match.group("value")):
                add(*match.span("value"), kind, SubjectRole.PATIENT)
    for match in _DOB.finditer(text):
        day, month, year = (int(part) for part in re.split(r"[/\-]", match.group("value")))
        try:
            date(year, month, day)
        except ValueError:
            continue
        add(*match.span("value"), EntityType.DATE_OF_BIRTH)
    for cue in _NAME_CUE.finditer(text):
        cue_prefix = text[max(0, cue.start() - 8):cue.start()]
        if re.search(r"(?i)\b(?:mã|ma)[ \t]+$", cue_prefix):
            # The phrase "mã bệnh nhân" introduces an identifier field, not
            # a person's name; leave its value to the contextual ID detector.
            continue
        candidate = _WORDS.match(text, cue.end())
        if candidate is None:
            continue
        tokens = list(re.finditer(r"[^\W\d_]+", candidate.group()))
        if not tokens:
            continue
        boundary_ambiguous = False
        if candidate.end() < len(text) and (text[candidate.end()].isalnum() or text[candidate.end()] in "-_@"):
            last_start = candidate.start() + tokens[-1].start()
            compound = _CLINICAL_COMPOUND.match(text, last_start)
            if compound is not None and compound.end() >= candidate.end():
                # The word lexer stops before a compound's digit (SpO2, for
                # example); discard that clinical token, retaining the name.
                tokens.pop()
            else:
                boundary_ambiguous = True
        selected = []
        for token in tokens:
            absolute_start = candidate.start() + token.start()
            absolute_end = candidate.start() + token.end()
            folded = _fold(token.group())
            compound = _CLINICAL_COMPOUND.match(text, absolute_start)
            if folded in _NAME_CLINICAL_HOMOGRAPHS:
                decision = _homograph_boundary(
                    token.group(), text[absolute_end:],
                    has_name_prefix=bool(selected) and _fold(selected[0].group()) in _SURNAMES,
                )
                if decision == "clinical":
                    break
                if decision == "ambiguous":
                    if selected:
                        boundary_ambiguous = True
                        break
                    continue
                selected.append(token)
                continue
            if selected and (
                    folded in _CLINICAL_STOPS
                    or folded in _CLINICAL_ABBREVIATIONS
                    or (compound is not None and compound.end() >= absolute_end)
                    or _POST_NAME_PHRASE.match(text, absolute_start) is not None
                    or _DOSE_AFTER_TERM.match(text[absolute_end:]) is not None):
                break
            # After a three-token Vietnamese name, an unfamiliar adjacent
            # token is ambiguous regardless of casing. ASR commonly erases
            # capitalization, so case cannot be used as a clinical boundary.
            if (len(selected) >= 3 and _fold(selected[0].group()) in _SURNAMES
                    and folded not in _COMMON_NAME_CONTINUATIONS):
                boundary_ambiguous = True
                break
            selected.append(token)
        if not selected:
            continue
        surname = _fold(selected[0].group()) in _SURNAMES
        cue_text = _fold(cue.group())
        explicit_name_cue = any(token in cue_text for token in ("ho ten", "ten la", "lien he la"))
        if not surname and not explicit_name_cue:
            continue
        reliable = not boundary_ambiguous and surname and 2 <= len(selected) <= 5
        role = SubjectRole.CLINICIAN if any(word in cue_text for word in ("bac si", "bs")) else (
            SubjectRole.RELATIVE if any(word in cue_text for word in ("me benh", "cha benh", "lien he")) else (
                SubjectRole.PATIENT if "benh nhan" in cue_text else SubjectRole.UNKNOWN))
        finding_end = candidate.end() if boundary_ambiguous else candidate.start() + selected[-1].end()
        add(candidate.start(), finding_end, EntityType.PERSON, role,
            Identifiability.DIRECT if reliable else Identifiability.AMBIGUOUS)
    for cue in _SPOKEN_CUE.finditer(text):
        # Spoken digit strings need ten tokens; the name-oriented word bound is
        # deliberately not reused here. Only literal digit words are supported.
        words = re.match(r"[^\W\d_]+(?:[ \t]+[^\W\d_]+){0,11}", text[cue.end():])
        if words is None:
            continue
        tokens = tuple(re.finditer(r"[^\W\d_]+", words.group()))
        selected = []
        for token in tokens:
            if _fold(token.group()) not in _DIGITS:
                break
            selected.append(token)
        digits = "".join(_DIGITS[_fold(token.group())] for token in selected)
        if re.fullmatch(r"0[35789][0-9]{8}", digits):
            add(cue.end(), cue.end() + selected[-1].end(), EntityType.PHONE)
    ordered = tuple(sorted(findings, key=lambda item: (item.span.start, item.span.end, item.entity_type.value)))
    return DetectorReport(
        source=source, detector_id=DETECTOR_ID, detector_version=DETECTOR_VERSION,
        status=DetectorStatus.COMPLETE, supported_entities=SUPPORTED_ENTITIES,
        findings=ordered, coverage=(SourceSpan(start=0, end=len(source.text)),) if source.text else (),
    )
