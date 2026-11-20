"""Verified Unicode analysis views; the original text is never rewritten."""

from bisect import bisect_left, bisect_right
from dataclasses import dataclass, field
import unicodedata

from features.pii_filter.schema import SourceSpan, TextInput, require_tuple


class ResourceLimitError(ValueError):
    """A declared local processing budget was exceeded."""


def _mapped(text: str, form: str) -> tuple[str, tuple[SourceSpan, ...], tuple[int, ...]]:
    pieces, offsets, boundaries = [], [], [0]
    start = 0

    def flush(end: int) -> None:
        normalized = unicodedata.normalize(form, text[start:end])
        pieces.append(normalized)
        offsets.extend([SourceSpan(start=start, end=end)] * len(normalized))
        boundaries.append(end)

    for index in range(1, len(text)):
        if unicodedata.category(text[index]).startswith("M"):
            continue
        # Hangul and any other canonical composition across starter boundaries
        # must stay in the same segment. This is exact normalization, not search.
        left = unicodedata.normalize("NFC", text[start:index])
        right = unicodedata.normalize("NFC", text[index])
        if unicodedata.normalize("NFC", left + right) != left + right:
            continue
        flush(index)
        start = index
    if text:
        flush(len(text))
    result = "".join(pieces)
    if result != unicodedata.normalize(form, text):
        raise ValueError("normalization cannot be mapped exactly")
    return result, tuple(offsets), tuple(boundaries)


@dataclass(frozen=True, slots=True, kw_only=True)
class AnalysisView:
    source: TextInput = field(repr=False)
    text: str = field(repr=False)
    offsets: tuple[SourceSpan, ...]
    form: str = "NFC"
    boundaries: tuple[int, ...] = field(init=False)

    def __post_init__(self) -> None:
        if type(self.source) is not TextInput:
            raise TypeError("analysis requires a TextInput")
        self.source.__post_init__()
        if type(self.form) is not str or self.form not in ("NFC", "NFD"):
            raise ValueError("only canonical NFC and NFD views are supported")
        if type(self.text) is not str:
            raise TypeError("analysis text must be a string")
        require_tuple(self.offsets, SourceSpan)
        expected, mapping, boundaries = _mapped(self.source.text, self.form)
        for span in self.offsets:
            span.validate_for(self.source)
        if self.text != expected or self.offsets != mapping:
            raise ValueError("invalid original-source normalization mapping")
        object.__setattr__(self, "boundaries", boundaries)

    def validate_source(self, source: TextInput) -> None:
        if type(source) is not TextInput or source != self.source:
            raise ValueError("analysis source identity, revision, or content mismatch")

    def source_span(self, start: int, end: int) -> SourceSpan:
        span = SourceSpan(start=start, end=end)
        if span.end > len(self.text):
            raise ValueError("analysis span is out of bounds")
        return SourceSpan(start=self.offsets[start].start, end=self.offsets[end - 1].end)

    def expand_span(self, span: SourceSpan) -> SourceSpan:
        if type(span) is not SourceSpan:
            raise TypeError("a SourceSpan is required")
        span.validate_for(self.source)
        return SourceSpan(
            start=self.boundaries[bisect_right(self.boundaries, span.start) - 1],
            end=self.boundaries[bisect_left(self.boundaries, span.end)],
        )


def build_view(source: TextInput, form: str = "NFC") -> AnalysisView:
    if type(source) is not TextInput:
        raise TypeError("analysis requires a TextInput")
    source.__post_init__()
    if type(form) is not str or form not in ("NFC", "NFD"):
        raise ValueError("only canonical NFC and NFD views are supported")
    text, offsets, _ = _mapped(source.text, form)
    return AnalysisView(source=source, text=text, offsets=offsets, form=form)
