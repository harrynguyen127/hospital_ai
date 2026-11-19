"""Original-offset invariants, including canonical reordering and combining marks."""

from dataclasses import FrozenInstanceError, replace
import unicodedata
import unittest

from features.pii_filter.normalization import AnalysisView, build_view
from features.pii_filter.schema import SourceSpan, TextInput


class NormalizationTests(unittest.TestCase):
    def source(self, text):
        return TextInput(text=text, source_id="unicode-source", source_revision="1")

    def test_nfc_and_nfd_views_preserve_the_source(self):
        original = "🙂 " + unicodedata.normalize("NFD", "Nguyễn Văn An") + ", mạch 92."
        source = self.source(original)
        for form in ("NFC", "NFD"):
            view = build_view(source, form)
            self.assertEqual(view.text, unicodedata.normalize(form, original))
            self.assertEqual(source.text, original)
            self.assertEqual(view.source_span(2, len(view.text) - len(unicodedata.normalize(form, ", mạch 92."))),
                             SourceSpan(start=2, end=len(original) - len(", mạch 92.")))

    def test_repeated_names_map_to_their_own_occurrences(self):
        name = unicodedata.normalize("NFD", "Nguyễn")
        view = build_view(self.source(name + "; " + name))
        self.assertEqual(view.source_span(8, 14), SourceSpan(start=len(name) + 2, end=2 * len(name) + 2))

    def test_mark_reordering_has_verified_cluster_coverage(self):
        source = self.source("a\u0315\u0300")
        view = build_view(source)
        self.assertEqual(view.text, "à\u0315")
        self.assertEqual(view.source_span(0, 1), SourceSpan(start=0, end=3))
        self.assertEqual(view.source_span(1, 2), SourceSpan(start=0, end=3))

    def test_leading_marks_are_not_lost(self):
        source = self.source("\u0315\u0300a")
        view = build_view(source)
        self.assertEqual(view.source_span(0, 2), SourceSpan(start=0, end=2))
        self.assertEqual(view.text, unicodedata.normalize("NFC", source.text))

    def test_hangul_composition_across_starters_is_mapped(self):
        view = build_view(self.source("\u1100\u1161\u11a8"))
        self.assertEqual(view.text, "각")
        self.assertEqual(view.source_span(0, 1), SourceSpan(start=0, end=3))

    def test_partial_combining_span_expands_to_whole_cluster(self):
        view = build_view(self.source("a\u0301b"))
        self.assertEqual(view.expand_span(SourceSpan(start=1, end=2)), SourceSpan(start=0, end=2))

    def test_invalid_maps_are_rejected_instead_of_searched(self):
        source = self.source("a\u0301")
        with self.assertRaises(ValueError):
            AnalysisView(source=source, text="á", offsets=(SourceSpan(start=0, end=1),))
        with self.assertRaises(ValueError):
            AnalysisView(source=source, text="a", offsets=(SourceSpan(start=0, end=2),))

    def test_offsets_reject_bool_and_out_of_bounds(self):
        view = build_view(self.source("An"))
        for start, end in ((True, 2), (0, False), (0, 3), (-1, 1), (1, 1)):
            with self.subTest(start=start, end=end), self.assertRaises((TypeError, ValueError)):
                view.source_span(start, end)

    def test_source_binding_includes_content_and_revision(self):
        source = self.source("An")
        view = build_view(source)
        for other in (replace(source, source_revision="2"), replace(source, text="Bo")):
            with self.assertRaises(ValueError):
                view.validate_source(other)

    def test_empty_view_and_immutability(self):
        view = build_view(self.source(""))
        self.assertEqual((view.text, view.offsets, view.boundaries), ("", (), (0,)))
        with self.assertRaises(ValueError):
            view.source_span(0, 1)
        with self.assertRaises(FrozenInstanceError):
            view.text = "other"

    def test_compatibility_normalization_is_not_silently_enabled(self):
        for form in ("NFKC", "NFKD", None):
            with self.assertRaises(ValueError):
                build_view(self.source("１２３"), form)

    def test_large_mark_cluster_and_unexpected_unicode(self):
        for text in ("a" + "\u0301" * 2048, "🩺\u200d⚕️\u200b; An\r\n"):
            view = build_view(self.source(text))
            self.assertEqual(view.text, unicodedata.normalize("NFC", text))
            self.assertEqual(view.source_span(0, len(view.text)), SourceSpan(start=0, end=len(text)))
