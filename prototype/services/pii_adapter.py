"""Integration adapter connecting the PII-02 rules-based text privacy engine to slot `pii.mask`.

- Leaves `features/pii_filter/pii.py` and all PII-01/PII-02 modules untouched so the
  PII evaluation baseline (`pii_runtime/tests/test_evaluate_rules.py`) remains intact.
- Runs `features.pii_filter.engine.process_text` as the primary detector/assessor,
  preserves fail-closed behavior (`external_egress_authorized` is always False in PII-02),
  maps entity types to readable prototype placeholders (`[TÊN]`, `[SĐT]`, `[CCCD]`, `[PII]`),
  trims ambiguous lowercase ASR PERSON spans before EMR field keywords, and applies a
  clinical-safe legacy compatibility fallback for mock names/phones (e.g. `Anh Mẫu A`, `0000000000`).
"""
import re
import unicodedata

from features.pii_filter.engine import process_text
from features.pii_filter.schema import (
    AssessmentStatus,
    EntityType,
    PolicyAction,
    TextInput,
)

PII_ENGINE_ID = "pii-02-rules-review"

_PLACEHOLDER_BY_TYPE = {
    EntityType.PERSON: "[TÊN]",
    EntityType.PHONE: "[SĐT]",
    EntityType.NATIONAL_ID: "[CCCD]",
}

# Multi-word EMR/clinical phrases that signal the end of a lowercase ASR person name
# without blocking valid Vietnamese surnames/given names (e.g., Lý, Phương, Bảo, Nhân).
_EMR_STOP_PHRASES = (
    "số điện thoại", "điện thoại", "số cccd", "số cmnd", "căn cước",
    "bảo hiểm", "ca trực", "lý do", "phương pháp", "khả năng",
    "thời điểm", "thời gian", "thời tiết", "thời lượng", "vị trí",
    "tính chất", "tình trạng", "tư thế", "trạng thái", "hoàn cảnh",
    "hướng dẫn", "hướng điều", "hướng lan", "hình thức", "biện pháp",
    "môi trường", "kiểm tra", "dấu hiệu", "buồn nôn", "vấn đề",
    "bệnh nhân", "bệnh sử", "người bệnh", "người nhà", "người liên hệ",
    "người thực hiện", "người nhận", "người mô tả", "người cung cấp",
    "người chăm sóc", "chỉ số", "ăn uống", "cuối tuần", "hôm nay",
)

# Single-word clinical/field/function tokens (exact lowercase NFC) safe to stop on.
_SINGLE_STOP_WORDS = frozenset({
    "là", "của", "mạch", "mách", "mạnh", "nhịp", "nhìn", "huyết", "nhiệt",
    "spo2", "hba1c", "gcs", "bmi", "ecg", "eeg", "mri", "ct",
    "cccd", "cmnd", "bhyt", "sđt", "sdt", "số", "đau", "sốt", "thuốc",
    "khám", "kháng", "buồn", "đang", "không", "hôm", "trời", "ăn", "uống",
    "điểm", "tiền", "bệnh", "triệu", "chẩn", "vận", "hỗ", "nguồn", "cách",
    "biện", "môi", "kiểm", "dấu", "đáp", "mức", "dụng", "cung", "tiếp",
    "kết", "dị", "nội", "đường", "vùng", "trạng", "bàn", "ghi", "thực",
    "đánh", "theo", "giáo", "nhận", "than", "mục", "vệ", "đại", "tiểu",
    "giấc", "dáng", "chuyển", "chóng", "thị", "yếu", "lo", "ưu", "kế",
    "quá", "thủ", "diễn", "đối", "giấy", "nơi", "lời", "xác", "phẫu",
    "đơn", "tỉnh", "hô", "dẫn", "nhu", "hiểu", "địa", "phản", "độ", "xoay",
})

# Clinical tokens that legacy capitalized-name compatibility MUST NEVER mask.
_LEGACY_PROTECTED_FIRST = frozenset({
    "spo2", "hba1c", "gcs", "bmi", "ecg", "eeg", "mri", "ct",
    "hiv", "hbv", "hcv", "copd", "aids", "ckd", "cad", "tb", "dm",
    "đau", "sốt", "mạch", "huyết", "nhiệt", "nhịp", "không", "có",
    "thuốc", "tiền", "triệu", "bụng", "thở", "tỉnh", "viêm", "suy",
    "tăng", "giảm", "chẩn", "khám", "điểm", "cần", "đã", "đang",
})

_LEGACY_PHONE = re.compile(r"\b0\d{9,10}\b")
_LEGACY_CCCD = re.compile(r"\b\d{12}\b")
_LEGACY_CAP_NAME = re.compile(
    r"(?<!\w)((?i:tên bệnh nhân là|tên bệnh nhân|bệnh nhân tên là|bệnh nhân là|"
    r"tên là|người liên hệ là|liên hệ là|anh|chị|ông|bà|bệnh nhân))\s+"
    r"((?:[A-ZÀ-Ỵ][\wÀ-ỹ]*\s?){1,4})"
)


def _nfc_lower(value: str) -> str:
    return unicodedata.normalize("NFC", value).lower()


def _trim_ambiguous_person_span(text: str, start: int, end: int) -> int | None:
    """Return trimmed end offset for a PII-02 REVIEW PERSON span, or None if not a name."""
    segment = text[start:end]
    tokens = list(re.finditer(r"[^\W\d_]+", segment))
    if not tokens:
        return None
    kept = []
    for idx, tok in enumerate(tokens):
        if len(kept) >= 4:
            break
        word = _nfc_lower(tok.group(0))
        if word in _SINGLE_STOP_WORDS:
            break
        # Check multi-word stop phrases starting at this token
        tail_words = " ".join(_nfc_lower(t.group(0)) for t in tokens[idx : idx + 3])
        if any(
            tail_words == phrase or tail_words.startswith(phrase + " ")
            for phrase in _EMR_STOP_PHRASES
        ):
            break
        kept.append(tok)
    if not kept:
        return None
    return start + kept[-1].end()


def _placeholder_for_types(entity_types: set[EntityType]) -> str:
    if len(entity_types) == 1:
        return _PLACEHOLDER_BY_TYPE.get(next(iter(entity_types)), "[PII]")
    return "[PII]"


def _legacy_fallback_segment(segment: str) -> tuple[str, int]:
    """Mask mock/legacy identifiers missed by PII-02 without touching clinical tokens."""
    count = 0

    def _sub_name(match: re.Match) -> str:
        nonlocal count
        target = match.group(2).strip()
        if not target:
            return match.group(0)
        first_word = _nfc_lower(target.split()[0])
        if first_word in _LEGACY_PROTECTED_FIRST:
            return match.group(0)
        # Never corrupt an already-inserted placeholder
        if target.startswith("["):
            return match.group(0)
        count += 1
        rel_start = match.start(2) - match.start(0)
        rel_end = rel_start + len(target)
        raw = match.group(0)
        return raw[:rel_start] + "[TÊN]" + raw[rel_end:]

    segment, k = _LEGACY_PHONE.subn("[SĐT]", segment)
    count += k
    segment, k = _LEGACY_CCCD.subn("[CCCD]", segment)
    count += k
    segment = _LEGACY_CAP_NAME.sub(_sub_name, segment)
    return segment, count


def mask_with_assessment(text: str) -> dict:
    """Run PII-02 local engine and return masked text, count, and fail-closed assessment metadata."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    source = TextInput(text=text, source_id="voice-local", source_revision="1")
    result = process_text(source)
    if result.assessment.status is AssessmentStatus.FAILED:
        reasons = ", ".join(r.value for r in result.assessment.reason_codes)
        raise RuntimeError(f"PII-02 engine failed (fail-closed): {reasons}")

    findings = [
        finding
        for report in result.detector_reports
        for finding in report.findings
    ]

    # Collect prioritized non-overlapping replacements from PII-02 decisions.
    # REDACT spans take precedence over trimmed REVIEW spans.
    candidates = []
    review_decisions = 0
    for decision in result.decisions:
        overlapping = [
            f for f in findings
            if f.span.start < decision.span.end and f.span.end > decision.span.start
        ]
        etypes = {f.entity_type for f in overlapping}
        placeholder = _placeholder_for_types(etypes)
        if decision.action is PolicyAction.REDACT:
            candidates.append((0, decision.span.start, decision.span.end, placeholder))
        elif decision.action is PolicyAction.REVIEW:
            review_decisions += 1
            if EntityType.PERSON in etypes:
                trimmed_end = _trim_ambiguous_person_span(text, decision.span.start, decision.span.end)
                if trimmed_end is not None and trimmed_end > decision.span.start:
                    candidates.append((1, decision.span.start, trimmed_end, "[TÊN]"))

    # Select non-overlapping spans (priority 0 = REDACT first, then REVIEW)
    selected = []
    for prio, start, end, placeholder in sorted(candidates, key=lambda x: (x[0], x[1], -(x[2] - x[1]))):
        if any(not (end <= s or start >= e) for s, e, _ in selected):
            continue
        selected.append((start, end, placeholder))
    selected.sort(key=lambda x: x[0])

    # Render text, running clinical-safe legacy compatibility ONLY on unmasked gaps
    chunks = []
    cursor = 0
    total_masked = 0
    for start, end, placeholder in selected:
        if start > cursor:
            gap, gap_count = _legacy_fallback_segment(text[cursor:start])
            chunks.append(gap)
            total_masked += gap_count
        chunks.append(placeholder)
        total_masked += 1
        cursor = end
    if cursor < len(text):
        tail, tail_count = _legacy_fallback_segment(text[cursor:])
        chunks.append(tail)
        total_masked += tail_count

    return {
        "text": "".join(chunks),
        "pii_masked": total_masked,
        "pii_engine": PII_ENGINE_ID,
        "pii_status": result.assessment.status.value,
        "pii_reasons": [r.value for r in result.assessment.reason_codes],
        "external_egress_authorized": result.external_egress_authorized,
        "review_decisions": review_decisions,
    }


def mask(text: str) -> tuple[str, int]:
    """Contract-compatible slot `pii.mask(text) -> (str, int)` backed by PII-02."""
    out = mask_with_assessment(text)
    return out["text"], out["pii_masked"]
