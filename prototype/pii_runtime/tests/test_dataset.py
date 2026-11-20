"""Synthetic schema, reproducibility, custody, and cross-split leakage tests."""

from contextlib import redirect_stderr, redirect_stdout
from dataclasses import FrozenInstanceError, replace
from itertools import permutations
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unicodedata
import unittest

PROTOTYPE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROTOTYPE))

from features.pii_filter.schema import EntityType, Identifiability, PolicyAction, SourceSpan, SubjectRole, TextInput
from pii_runtime.evaluation.dataset import (
    ClinicalAnnotation, ClinicalCategory, DATASET_VERSION, PREVIOUS_DATASET_VERSION,
    DatasetRecord, DatasetSplit, EntityAnnotation,
    Exposure, PolicyAnnotation, ReviewAnnotation, ReviewReason, read_dataset,
    record_from_dict, record_to_dict, validate_dataset, write_dataset,
)
from pii_runtime.evaluation.generate_synthetic import GENERATOR_VERSION, generate_development, main


class DatasetTests(unittest.TestCase):
    def setUp(self):
        self.records = generate_development(17)

    def minimal(self, **overrides):
        values = dict(record_id="record-1", source=TextInput(text="Synthetic example.", source_id="source-1", source_revision="1"),
                      split=DatasetSplit.DEVELOPMENT, scenario_family="family-1", scenario_version="1",
                      generator_version="1", seed=1, entities=(), policies=(), clinical=(), reviews=())
        return DatasetRecord(**(values | overrides))

    def other(self, record, **overrides):
        return replace(record, **({"record_id": "record-2", "source": replace(record.source, source_id="source-2"),
                                  "scenario_family": "family-2"} | overrides))

    def policy_record(self, policies, *, reviews=(), clinical=(), ambiguous=False):
        source = TextInput(text="Nguyễn Mẫu An", source_id="policy-source", source_revision="1")
        entities = tuple(
            EntityAnnotation(
                span=policy.span, entity_type=EntityType.PERSON,
                subject_role=SubjectRole.PATIENT,
                identifiability=Identifiability.AMBIGUOUS if ambiguous else Identifiability.DIRECT,
            )
            for policy in policies
        )
        return self.minimal(source=source, entities=entities, policies=policies,
                            reviews=reviews, clinical=clinical)

    def audit_leakage_records(self):
        prefix = "patient reports routine follow up and takes medicine after food "
        left = self.minimal(source=TextInput(
            text=prefix + "pain fever cough dyspnea", source_id="source-1", source_revision="1",
        ))
        right = self.other(left, split=DatasetSplit.TRAIN, source=TextInput(
            text=prefix + "cough fever dyspnea pain", source_id="source-2", source_revision="1",
        ))
        return left, right

    def test_generator_is_small_and_development_only(self):
        self.assertEqual(len(self.records), 20)
        self.assertEqual({item.split for item in self.records}, {DatasetSplit.DEVELOPMENT})
        self.assertEqual({item.exposure for item in self.records}, {Exposure.EXPOSED})
        self.assertTrue(all(item.custody_reference is None for item in self.records))
        self.assertEqual({item.generator_version for item in self.records}, {GENERATOR_VERSION})

    def test_same_seed_reproduces_all_text_offsets_and_annotations(self):
        self.assertEqual(self.records, generate_development(17))
        self.assertEqual([record_to_dict(item) for item in self.records], [record_to_dict(item) for item in generate_development(17)])

    def test_different_seed_changes_generated_identifiers(self):
        other = generate_development(18)
        self.assertNotEqual(self.records[1].source.text, other[1].source.text)
        self.assertEqual([item.scenario_family for item in self.records], [item.scenario_family for item in other])

    def test_generator_does_not_change_global_random_state(self):
        import random

        before = random.getstate()
        generate_development(918)
        self.assertEqual(before, random.getstate())

    def test_generator_rejects_invalid_seeds(self):
        for seed in (True, False, -1, 2**64, "17", 1.0):
            with self.subTest(seed_type=type(seed).__name__), self.assertRaises(ValueError):
                generate_development(seed)

    def test_development_coverage_contains_required_entity_categories(self):
        categories = {item.entity_type for record in self.records for item in record.entities}
        self.assertTrue({EntityType.PERSON, EntityType.PHONE, EntityType.PATIENT_ID,
                         EntityType.HEALTH_INSURANCE_ID, EntityType.DATE_OF_BIRTH,
                         EntityType.ADDRESS, EntityType.RARE_CONTEXT}.issubset(categories))

    def test_clinical_examples_include_negative_and_attribution_cases(self):
        categories = {item.category for record in self.records for item in record.clinical}
        self.assertTrue({ClinicalCategory.MEDICATION, ClinicalCategory.DOSAGE,
                         ClinicalCategory.VITAL_SIGN, ClinicalCategory.NEGATION,
                         ClinicalCategory.FAMILY_HISTORY}.issubset(categories))
        roles = {item.subject_role for record in self.records for item in record.entities}
        self.assertTrue({SubjectRole.PATIENT, SubjectRole.CLINICIAN, SubjectRole.RELATIVE}.issubset(roles))
        self.assertTrue(any(not record.entities and record.clinical for record in self.records))

    def test_diagnosis_or_lab_result_category_is_versioned_and_prior_records_remain_readable(self):
        old_record = replace(self.records[0], dataset_version=PREVIOUS_DATASET_VERSION)
        self.assertEqual(record_from_dict(record_to_dict(old_record)), old_record)

        text = "HIV dương tính"
        source = TextInput(text=text, source_id="clinical-finding", source_revision="1")
        annotation = ClinicalAnnotation(
            span=SourceSpan(start=0, end=len(text)),
            category=ClinicalCategory.DIAGNOSIS_OR_LAB_RESULT,
            subject_role=SubjectRole.PATIENT,
            assertion_id="clinical-finding-1",
        )
        with self.assertRaises(ValueError):
            self.minimal(record_id="diagnosis-record", source=source,
                         scenario_family="diagnosis-family", clinical=(annotation,),
                         dataset_version=PREVIOUS_DATASET_VERSION)
        current = self.minimal(record_id="diagnosis-record", source=source,
                               scenario_family="diagnosis-family", clinical=(annotation,),
                               dataset_version=DATASET_VERSION)
        self.assertEqual(record_from_dict(record_to_dict(current)), current)

    def test_all_annotations_have_valid_original_source_bounds(self):
        for record in self.records:
            for item in record.entities + record.policies + record.clinical + record.reviews:
                item.span.validate_for(record.source)
                self.assertTrue(record.source.text[item.span.start:item.span.end])

    def test_nfd_offsets_and_content_survive_json_round_trip(self):
        record = next(item for item in self.records if item.scenario_family == "nfd-name")
        self.assertNotEqual(record.source.text, unicodedata.normalize("NFC", record.source.text))
        restored = record_from_dict(json.loads(json.dumps(record_to_dict(record))))
        self.assertEqual(record, restored)
        self.assertEqual(record.entities[0].span, restored.entities[0].span)

    def test_spoken_phone_is_one_original_text_annotation(self):
        record = next(item for item in self.records if item.scenario_family == "spoken-phone")
        span = record.entities[0].span
        self.assertEqual(record.source.text[span.start:span.end], "không chín không một hai ba bốn năm sáu bảy")

    def test_repeated_identifiers_have_separate_offsets(self):
        record = next(item for item in self.records if item.scenario_family == "repeated-contact")
        left, right = (item.span for item in record.entities)
        self.assertLess(left.end, right.start)
        self.assertEqual(record.source.text[left.start:left.end], record.source.text[right.start:right.end])

    def test_dates_and_organizations_can_have_preserve_policy(self):
        record = next(item for item in self.records if item.scenario_family == "contextual-date-organization")
        self.assertEqual({item.entity_type for item in record.entities}, {EntityType.DATE, EntityType.ORGANIZATION})
        self.assertTrue(all(item.action is PolicyAction.PRESERVE for item in record.policies))

    def test_ambiguity_and_indirect_identification_have_review_annotations(self):
        records = [item for item in self.records if item.review_required]
        self.assertEqual(len(records), 2)
        self.assertEqual({review.reason for item in records for review in item.reviews},
                         {ReviewReason.AMBIGUOUS_IDENTITY, ReviewReason.INDIRECT_IDENTIFICATION})

    def test_annotations_and_records_are_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            self.records[0].entities[0].entity_type = EntityType.PHONE
        with self.assertRaises(FrozenInstanceError):
            self.records[0].split = DatasetSplit.TRAIN
        with self.assertRaises(TypeError):
            replace(self.records[0], entities=list(self.records[0].entities))

    def test_dataset_rejects_invalid_versions_seeds_and_provenance(self):
        for change in ({"dataset_version": "2"}, {"seed": True}, {"provenance": "real_patient"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                replace(self.records[0], **change)

    def test_annotation_offsets_exclude_booleans(self):
        data = record_to_dict(self.records[0])
        data["entities"][0]["span"]["start"] = True
        with self.assertRaises(ValueError):
            record_from_dict(data)

    def test_out_of_bounds_ground_truth_is_rejected(self):
        record = self.records[0]
        annotation = replace(record.entities[0], span=SourceSpan(start=0, end=len(record.source.text) + 1))
        with self.assertRaises(ValueError):
            replace(record, entities=(annotation,))

    def test_ground_truth_requires_separate_policy_for_each_entity_span(self):
        with self.assertRaises(ValueError):
            replace(self.records[0], policies=())
        with self.assertRaises(ValueError):
            replace(self.records[0], policies=self.records[0].policies * 2)

    def test_ambiguous_annotations_cannot_silently_lose_review(self):
        record = next(item for item in self.records if item.scenario_family == "ambiguous-name")
        with self.assertRaises(ValueError):
            replace(record, reviews=())

    def test_gold_redaction_cannot_overlap_protected_clinical_text(self):
        record = self.records[0]
        protected = ClinicalAnnotation(span=record.entities[0].span, category=ClinicalCategory.MEDICATION,
                                       subject_role=SubjectRole.PATIENT, assertion_id="assertion-protected")
        with self.assertRaises(ValueError):
            replace(record, clinical=(protected,))

    def test_overlapping_recognition_spans_are_representable(self):
        source = TextInput(text="Nguyễn Mẫu An", source_id="overlap", source_revision="1")
        spans = (SourceSpan(start=0, end=6), SourceSpan(start=0, end=len(source.text)))
        entities = tuple(EntityAnnotation(span=span, entity_type=EntityType.PERSON,
                                         subject_role=SubjectRole.PATIENT, identifiability=Identifiability.DIRECT) for span in spans)
        record = self.minimal(source=source, entities=entities,
                              policies=tuple(PolicyAnnotation(span=span, action=PolicyAction.REDACT) for span in spans))
        validate_dataset((record,))

    def test_audit_overlapping_redact_preserve_gold_is_rejected_in_both_orders(self):
        policies = (
            PolicyAnnotation(span=SourceSpan(start=0, end=13), action=PolicyAction.REDACT),
            PolicyAnnotation(span=SourceSpan(start=0, end=6), action=PolicyAction.PRESERVE),
        )
        for ordered in permutations(policies):
            with self.subTest(policies=ordered), self.assertRaises(ValueError):
                self.policy_record(ordered)

    def test_compatible_overlapping_gold_is_allowed_for_each_action(self):
        full = SourceSpan(start=0, end=13)
        prefix = SourceSpan(start=0, end=6)
        for action in PolicyAction:
            reviews = (ReviewAnnotation(span=full, reason=ReviewReason.AMBIGUOUS_IDENTITY),) if action is PolicyAction.REVIEW else ()
            policies = tuple(PolicyAnnotation(span=span, action=action) for span in (full, prefix))
            for ordered in permutations(policies):
                with self.subTest(action=action, policies=ordered):
                    record = self.policy_record(ordered, reviews=reviews)
                    validate_dataset((record,))
                    self.assertEqual(record.review_required, action is PolicyAction.REVIEW)

    def test_distinct_overlapping_actions_have_no_implicit_precedence(self):
        full = SourceSpan(start=0, end=13)
        prefix = SourceSpan(start=0, end=6)
        reviews = (ReviewAnnotation(span=full, reason=ReviewReason.AMBIGUOUS_IDENTITY),)
        for left_action in PolicyAction:
            for right_action in PolicyAction:
                if left_action is right_action:
                    continue
                policies = (
                    PolicyAnnotation(span=full, action=left_action),
                    PolicyAnnotation(span=prefix, action=right_action),
                )
                for ordered in permutations(policies):
                    with self.subTest(left=left_action, right=right_action, policies=ordered):
                        with self.assertRaises(ValueError):
                            self.policy_record(ordered, reviews=reviews)

    def test_duplicate_compatible_policies_remain_invalid_not_silently_deduplicated(self):
        full = SourceSpan(start=0, end=13)
        for action in PolicyAction:
            reviews = (ReviewAnnotation(span=full, reason=ReviewReason.AMBIGUOUS_IDENTITY),) if action is PolicyAction.REVIEW else ()
            policy = PolicyAnnotation(span=full, action=action)
            record = self.policy_record((policy,), reviews=reviews)
            with self.subTest(action=action), self.assertRaises(ValueError):
                replace(record, policies=(policy, policy))

    def test_review_annotation_does_not_resolve_conflicting_final_gold(self):
        full = SourceSpan(start=0, end=13)
        prefix = SourceSpan(start=0, end=6)
        reviews = (ReviewAnnotation(span=full, reason=ReviewReason.AMBIGUOUS_IDENTITY),)
        policies = (
            PolicyAnnotation(span=full, action=PolicyAction.REDACT),
            PolicyAnnotation(span=prefix, action=PolicyAction.PRESERVE),
        )
        for ordered in permutations(policies):
            with self.subTest(policies=ordered), self.assertRaises(ValueError):
                self.policy_record(ordered, reviews=reviews)

    def test_ambiguous_overlapping_gold_requires_explicit_review(self):
        full = SourceSpan(start=0, end=13)
        policies = tuple(
            PolicyAnnotation(span=span, action=PolicyAction.REVIEW)
            for span in (full, SourceSpan(start=0, end=6))
        )
        for ordered in permutations(policies):
            with self.subTest(policies=ordered):
                with self.assertRaises(ValueError):
                    self.policy_record(ordered, ambiguous=True)
                record = self.policy_record(
                    ordered, ambiguous=True,
                    reviews=(ReviewAnnotation(span=full, reason=ReviewReason.AMBIGUOUS_IDENTITY),),
                )
                validate_dataset((record,))
                self.assertTrue(record.review_required)

    def test_protected_clinical_spans_allow_preserve_and_review_gold(self):
        full = SourceSpan(start=0, end=13)
        prefix = SourceSpan(start=0, end=6)
        clinical = (ClinicalAnnotation(
            span=prefix, category=ClinicalCategory.SUBJECT_ATTRIBUTION,
            subject_role=SubjectRole.PATIENT, assertion_id="subject-1",
        ),)
        for action in (PolicyAction.PRESERVE, PolicyAction.REVIEW):
            reviews = (ReviewAnnotation(span=full, reason=ReviewReason.AMBIGUOUS_IDENTITY),) if action is PolicyAction.REVIEW else ()
            policies = tuple(PolicyAnnotation(span=span, action=action) for span in (full, prefix))
            for ordered in permutations(policies):
                with self.subTest(action=action, policies=ordered):
                    validate_dataset((self.policy_record(ordered, clinical=clinical, reviews=reviews),))

    def test_review_does_not_allow_redaction_of_protected_clinical_spans(self):
        full = SourceSpan(start=0, end=13)
        clinical = (ClinicalAnnotation(
            span=SourceSpan(start=0, end=6), category=ClinicalCategory.SUBJECT_ATTRIBUTION,
            subject_role=SubjectRole.PATIENT, assertion_id="subject-1",
        ),)
        reviews = (ReviewAnnotation(span=full, reason=ReviewReason.AMBIGUOUS_IDENTITY),)
        for action in (PolicyAction.REDACT, PolicyAction.PSEUDONYMIZE):
            with self.subTest(action=action), self.assertRaises(ValueError):
                self.policy_record((PolicyAnnotation(span=full, action=action),),
                                   clinical=clinical, reviews=reviews)

    def test_touching_policy_spans_can_have_different_actions(self):
        policies = (
            PolicyAnnotation(span=SourceSpan(start=0, end=6), action=PolicyAction.PRESERVE),
            PolicyAnnotation(span=SourceSpan(start=6, end=13), action=PolicyAction.REDACT),
        )
        for ordered in permutations(policies):
            validate_dataset((self.policy_record(ordered),))

    def test_policy_validation_is_invariant_under_annotation_permutations(self):
        spans = (SourceSpan(start=0, end=13), SourceSpan(start=0, end=6), SourceSpan(start=7, end=10))
        compatible = tuple(PolicyAnnotation(span=span, action=PolicyAction.REDACT) for span in spans)
        for policies in permutations(compatible):
            record = self.policy_record(policies)
            validate_dataset((replace(record, entities=tuple(reversed(record.entities))),))
        conflicting = (compatible[0], replace(compatible[1], action=PolicyAction.PRESERVE), compatible[2])
        for policies in permutations(conflicting):
            with self.subTest(policies=policies), self.assertRaises(ValueError):
                self.policy_record(policies)

    def test_json_dictionary_round_trip(self):
        for record in self.records:
            self.assertEqual(record_from_dict(record_to_dict(record)), record)

    def test_json_boundary_rejects_unknown_labels_and_extra_fields(self):
        for modify in (lambda data: data.update(raw_patient_name="secret"),
                       lambda data: data["entities"][0].update(entity_type="NEW_LABEL"),
                       lambda data: data["source"].update(offset_unit="utf16"),
                       lambda data: data["source"].update(source_revision=True)):
            data = record_to_dict(self.records[0])
            modify(data)
            with self.assertRaises(ValueError) as caught:
                record_from_dict(data)
            self.assertEqual(str(caught.exception), "invalid dataset record")

    def test_json_boundary_rejects_malformed_nested_types(self):
        for key, value in (("source", None), ("entities", {}), ("seed", 1.5), ("clinical", [None])):
            data = record_to_dict(self.records[0])
            data[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                record_from_dict(data)

    def test_no_self_declared_blind_evaluation_from_exposed_data(self):
        with self.assertRaises(ValueError):
            replace(self.records[0], split=DatasetSplit.EVALUATION)
        with self.assertRaises(ValueError):
            replace(self.records[0], split=DatasetSplit.EVALUATION, exposure=Exposure.INDEPENDENT_CUSTODY)
        with self.assertRaises(ValueError):
            replace(self.records[0], custody_reference="custody-1")

    def test_custody_reference_is_required_but_not_verified_by_schema(self):
        record = self.minimal(split=DatasetSplit.EVALUATION, exposure=Exposure.INDEPENDENT_CUSTODY,
                              custody_reference="external-procedure-1")
        self.assertEqual(record.custody_reference, "external-procedure-1")

    def test_empty_dataset_is_not_valid_evaluation_evidence(self):
        with self.assertRaises(ValueError):
            validate_dataset(())

    def test_duplicate_record_and_source_identities_are_rejected(self):
        record = self.minimal()
        for other in (self.other(record, record_id=record.record_id), self.other(record, source=record.source)):
            with self.assertRaises(ValueError):
                validate_dataset((record, other))

    def test_family_cannot_cross_splits_even_with_new_versions_and_text(self):
        record = self.minimal()
        other = self.other(record, scenario_family=record.scenario_family, scenario_version="2", split=DatasetSplit.TRAIN,
                           source=TextInput(text="Completely different scenario.", source_id="source-2", source_revision="2"))
        with self.assertRaisesRegex(ValueError, "scenario family"):
            validate_dataset((record, other))

    def test_same_split_may_contain_scenario_variants(self):
        record = self.minimal()
        validate_dataset((record, self.other(record, scenario_family=record.scenario_family)))

    def test_exact_cross_split_duplicates_are_rejected(self):
        record = self.minimal()
        with self.assertRaisesRegex(ValueError, "near-duplicate"):
            validate_dataset((record, self.other(record, split=DatasetSplit.REGRESSION)))

    def test_unicode_and_case_variants_do_not_evade_leakage_check(self):
        record = self.minimal(source=TextInput(text="NGUYỄN MẪU AN.", source_id="source-1", source_revision="1"))
        source = TextInput(text=unicodedata.normalize("NFD", record.source.text.lower()), source_id="source-2", source_revision="1")
        with self.assertRaises(ValueError):
            validate_dataset((record, self.other(record, source=source, split=DatasetSplit.TRAIN)))

    def test_changed_identifiers_do_not_hide_near_duplicate_templates(self):
        left = self.records[0]
        right = generate_development(18)[0]
        right = replace(right, split=DatasetSplit.TRAIN, scenario_family="renamed-template")
        with self.assertRaisesRegex(ValueError, "near-duplicate"):
            validate_dataset((left, right))

    def test_minor_word_changes_do_not_hide_near_duplicates(self):
        left = self.minimal(source=TextInput(text="The synthetic patient reports no pain after medication today.", source_id="source-1", source_revision="1"))
        source = replace(left.source, source_id="source-2", text="The synthetic patient reports no pain after medication yesterday.")
        with self.assertRaises(ValueError):
            validate_dataset((left, self.other(left, source=source, split=DatasetSplit.TRAIN)))

    def test_unrelated_split_records_are_allowed(self):
        left = self.minimal()
        right = self.other(left, split=DatasetSplit.REGRESSION,
                           source=TextInput(text="Không dị ứng thuốc; huyết áp 120/80 mmHg.", source_id="source-2", source_revision="1"))
        validate_dataset((left, right))

    def test_audit_cross_split_near_duplicates_are_rejected_in_both_orders(self):
        for ordered in permutations(self.audit_leakage_records()):
            with self.subTest(order=tuple(item.record_id for item in ordered)):
                with self.assertRaisesRegex(ValueError, "near-duplicate"):
                    validate_dataset(ordered)

    def test_leakage_rejection_is_invariant_under_all_three_record_permutations(self):
        left, right = self.audit_leakage_records()
        independent = self.minimal(
            record_id="record-3", scenario_family="family-3", split=DatasetSplit.REGRESSION,
            source=TextInput(text="Independent vaccination consent was documented separately.",
                             source_id="source-3", source_revision="1"),
        )
        for ordered in permutations((left, right, independent)):
            with self.subTest(order=tuple(item.record_id for item in ordered)):
                with self.assertRaisesRegex(ValueError, "near-duplicate"):
                    validate_dataset(ordered)

    def test_same_split_audit_near_duplicates_remain_permitted_in_both_orders(self):
        left, right = self.audit_leakage_records()
        right = replace(right, split=left.split)
        for ordered in permutations((left, right)):
            validate_dataset(ordered)

    def test_nfc_nfd_cross_split_duplicates_are_rejected_in_both_orders(self):
        left = self.minimal(source=TextInput(
            text="Bệnh nhân Nguyễn Mẫu An.", source_id="source-1", source_revision="1",
        ))
        right = self.other(left, split=DatasetSplit.TRAIN, source=TextInput(
            text=unicodedata.normalize("NFD", left.source.text), source_id="source-2", source_revision="1",
        ))
        for ordered in permutations((left, right)):
            with self.assertRaisesRegex(ValueError, "near-duplicate"):
                validate_dataset(ordered)

    def test_independent_split_acceptance_is_invariant_under_all_permutations(self):
        left = self.minimal()
        right = self.other(left, split=DatasetSplit.TRAIN, source=TextInput(
            text="Không dị ứng thuốc; huyết áp 120/80 mmHg.", source_id="source-2", source_revision="1",
        ))
        third = self.minimal(
            record_id="record-3", scenario_family="family-3", split=DatasetSplit.REGRESSION,
            source=TextInput(text="Independent vaccination consent was documented separately.",
                             source_id="source-3", source_revision="1"),
        )
        for ordered in permutations((left, right, third)):
            validate_dataset(ordered)

    def test_family_isolation_rejection_is_invariant_under_record_order(self):
        left, right = self.audit_leakage_records()
        right = replace(right, scenario_family=left.scenario_family)
        for ordered in permutations((left, right)):
            with self.assertRaisesRegex(ValueError, "scenario family"):
                validate_dataset(ordered)

    def test_changed_identity_templates_are_rejected_in_both_record_orders(self):
        left = self.records[0]
        right = replace(generate_development(18)[0], split=DatasetSplit.TRAIN, scenario_family="separate-author-family")
        for ordered in permutations((left, right)):
            with self.assertRaisesRegex(ValueError, "near-duplicate"):
                validate_dataset(ordered)

    def test_similarity_threshold_is_validated(self):
        for threshold in (True, 0, 1.1, float("nan"), "0.8"):
            with self.subTest(threshold_type=type(threshold).__name__), self.assertRaises(ValueError):
                validate_dataset(self.records, similarity_threshold=threshold)

    def test_external_jsonl_round_trip_and_byte_reproducibility(self):
        with tempfile.TemporaryDirectory() as folder:
            first, second = Path(folder) / "first.jsonl", Path(folder) / "second.jsonl"
            write_dataset(first, self.records)
            write_dataset(second, generate_development(17))
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(read_dataset(first), self.records)
            self.assertLess(first.stat().st_size, 100_000)

    def test_writer_refuses_repository_paths_and_overwrite(self):
        with self.assertRaises(ValueError):
            write_dataset(PROTOTYPE / "must-not-exist.jsonl", self.records)
        self.assertFalse((PROTOTYPE / "must-not-exist.jsonl").exists())
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "data.jsonl"
            write_dataset(path, self.records)
            before = path.read_bytes()
            with self.assertRaises(FileExistsError):
                write_dataset(path, self.records)
            self.assertEqual(path.read_bytes(), before)

    def test_invalid_data_is_rejected_before_creating_output(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "data.jsonl"
            with self.assertRaises(ValueError):
                write_dataset(path, (self.records[0], self.records[0]))
            self.assertFalse(path.exists())

    def test_json_reader_rejects_bad_json_duplicate_keys_and_nan(self):
        for payload in ('not-json\n', '{"seed": 1, "seed": 2}\n', '{"seed": NaN}\n', '\n'):
            with self.subTest(payload_kind=payload[:10]), tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / "invalid.jsonl"
                path.write_text(payload, encoding="utf-8")
                with self.assertRaises(ValueError):
                    read_dataset(path)

    def test_reader_checks_split_integrity_after_parsing(self):
        left = self.minimal()
        right = self.other(left, split=DatasetSplit.TRAIN)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "leak.jsonl"
            path.write_text("\n".join(json.dumps(record_to_dict(item)) for item in (left, right)), encoding="utf-8")
            with self.assertRaises(ValueError):
                read_dataset(path)

    def test_cli_writes_only_exposed_development_data(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "cli.jsonl"
            completed = subprocess.run([sys.executable, "-B", "-m", "pii_runtime.evaluation.generate_synthetic",
                                        "--seed", "17", "--output", str(path)], cwd=PROTOTYPE,
                                       capture_output=True, text=True, timeout=15, check=False)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("no blind evaluation", completed.stdout)
            self.assertEqual(read_dataset(path), self.records)

    def test_cli_refuses_invalid_seed(self):
        with tempfile.TemporaryDirectory() as folder, redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
            path = Path(folder) / "invalid.jsonl"
            with self.assertRaises(SystemExit) as caught:
                main(["--seed", "-1", "--output", str(path)])
            self.assertEqual(caught.exception.code, 2)
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
