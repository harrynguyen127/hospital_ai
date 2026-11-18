"""Pure, local-only text PII preflight with injectable detector support.

This module does not authorize external transmission or claim anonymization.
It intentionally avoids ASR, audio processing, model weights, and network access.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Iterable


@dataclass(frozen=True)
class PiiFinding:
    start: int
    end: int
    entity_type: str
    source: str

    def __post_init__(self) -> None:
        if self.start < 0 or self.end <= self.start:
            raise ValueError("invalid PII span")
        if not self.entity_type or not self.source:
            raise ValueError("entity type and source are required")


@dataclass(frozen=True)
class TextPrivacyResult:
    masked_text: str
    findings: tuple[PiiFinding, ...]
    status: str
    detector_status: str
    reason_codes: tuple[str, ...]
    external_egress_authorized: bool = False


TextDetector = Callable[[str], Iterable[PiiFinding]]

_PATTERNS = (
    ("EMAIL", re.compile(r"(?<![\w@])[-\w.+]+@[-\w.]+\.[A-Za-z]{2,}(?![\w@])")),
    ("PHONE", re.compile(r"(?<!\d)0\d{9,10}(?!\d)")),
    ("CCCD", re.compile(r"(?<!\d)\d{12}(?!\d)")),
    ("PATIENT_ID", re.compile(
        r"(?i)\b(?:mã\s+(?:bệnh\s+nhân|BN)|patient\s+id)\s*[:#-]?\s*(?P<value>BN[- ]?\d{2,12})\b"
    )),
    ("DATE_OF_BIRTH", re.compile(
        r"(?i)\b(?:ngày\s+sinh|sinh\s+ngày)\s*[:]?\s*(?P<value>\d{1,2}[/-]\d{1,2}[/-]\d{4})"
    )),
)
_NAME_PATTERN = re.compile(
    r"(?i:\b(?:bệnh\s+nhân|tên\s+là|anh|chị|ông|bà))\s+"
    r"(?P<value>[^\W\d_]+(?:\s+[^\W\d_]+){1,3})"
)
_REPLACEMENTS = {
    "EMAIL": "[EMAIL]",
    "PHONE": "[PHONE]",
    "CCCD": "[CCCD]",
    "PATIENT_ID": "[PATIENT_ID]",
    "DATE_OF_BIRTH": "[DATE_OF_BIRTH]",
    "PERSON": "[PERSON]",
}


def detect_rules(text: str) -> tuple[PiiFinding, ...]:
    """Detect selected explicit identifiers; recall is intentionally incomplete."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    findings: list[PiiFinding] = []
    for kind, pattern in _PATTERNS:
        for match in pattern.finditer(text):
            start, end = match.span("value") if "value" in match.re.groupindex else match.span()
            findings.append(PiiFinding(start, end, kind, "rules"))
    for match in _NAME_PATTERN.finditer(text):
        words = list(re.finditer(r"[^\W\d_]+", match.group("value")))
        capitalized = []
        for word in words:
            if not word.group(0)[0].isupper():
                break
            capitalized.append(word)
        if len(capitalized) >= 2:
            start = match.start("value")
            end = start + capitalized[-1].end()
            findings.append(PiiFinding(start, end, "PERSON", "rules"))
    return tuple(sorted(findings, key=lambda item: (item.start, -item.end)))


def _merge_intervals(text: str, findings: Iterable[PiiFinding]) -> tuple[PiiFinding, ...]:
    ordered = sorted(findings, key=lambda item: (item.start, item.end))
    for finding in ordered:
        if not isinstance(finding, PiiFinding) or finding.end > len(text):
            raise ValueError("detector returned an invalid or out-of-bounds span")
    combined: list[PiiFinding] = []
    for finding in ordered:
        if combined and finding.start < combined[-1].end:
            previous = combined[-1]
            combined[-1] = PiiFinding(
                previous.start,
                max(previous.end, finding.end),
                previous.entity_type if previous.entity_type == finding.entity_type else "PII",
                previous.source if previous.source == finding.source else "multiple",
            )
        else:
            combined.append(finding)
    return tuple(combined)


def redact(text: str, findings: Iterable[PiiFinding]) -> tuple[str, tuple[PiiFinding, ...]]:
    """Redact source offsets in one pass without changing unrelated clinical text."""
    merged = _merge_intervals(text, findings)
    chunks: list[str] = []
    cursor = 0
    for finding in merged:
        chunks.append(text[cursor:finding.start])
        chunks.append(_REPLACEMENTS.get(finding.entity_type, "[PII]"))
        cursor = finding.end
    chunks.append(text[cursor:])
    return "".join(chunks), merged


def process_text(text: str, ner_detector: TextDetector | None = None) -> TextPrivacyResult:
    """Local text analysis only; every result requires downstream privacy review."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    findings = list(detect_rules(text))
    codes = ["UNVERIFIED_PRIVACY_COVERAGE"]
    detector_status = "rules_only"
    if ner_detector is not None:
        try:
            extra = tuple(ner_detector(text))
            findings.extend(extra)
            detector_status = "rules_and_ner"
        except Exception:
            detector_status = "ner_failed"
            codes.append("NER_DETECTOR_FAILED")
    try:
        masked, merged = redact(text, findings)
    except (TypeError, ValueError):
        masked, merged = redact(text, detect_rules(text))
        detector_status = "ner_invalid_spans"
        codes.append("NER_DETECTOR_INVALID_OUTPUT")
    return TextPrivacyResult(
        masked_text=masked,
        findings=merged,
        status="review_required",
        detector_status=detector_status,
        reason_codes=tuple(codes),
        external_egress_authorized=False,
    )
