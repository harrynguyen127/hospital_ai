# PII-03 Research and Architecture Plan

**Status: RESEARCH ONLY — DRAFT FOR ARCHITECTURE APPROVAL**

This document proposes the next research phase for context-aware Vietnamese
clinical transcript PII detection. It does not authorize implementation, model
selection, model downloads, inference, real-patient-data use, production
qualification, or external transmission. PII-01 and PII-02 remain the existing
published baseline; this plan adds no implementation.

## 1. Verified repository baseline

- Repository: `hospital_ai`
- Branch: `feat/pii-text-privacy`
- Baseline HEAD: `cb2d7156e4a3fd1df63ae6dd16f826a72cca8777`
- Before creating this plan, the worktree was clean and the branch matched its upstream.
- The current [PII-02 engine](../prototype/features/pii_filter/engine.py) is a
  separate text-only API. The original `pii.mask(text) -> (str, int)` slot and
  team compatibility prototype remain unchanged.
- `docs/PII_STATUS.md` contains a stale sentence at its end saying PII-02 is
  uncommitted. The branch history confirms the opposite. Refresh that status
  statement as a separate documentation correction before future implementation.

The current architecture and evaluation details are in
[TEXT_PII_ARCHITECTURE.md](TEXT_PII_ARCHITECTURE.md) and
[TEXT_PII_EVALUATION.md](TEXT_PII_EVALUATION.md). PII-02 does not choose a
model, authorize outbound traffic, or qualify clinical privacy performance.

## 2. Measured baseline and limitations

The deterministic rules evaluation on the 20-record exposed synthetic
development set (seed 17) reports 11/16 full redactions for all required
identifiers; the unchanged team regex baseline reports 5/16. On 191 protected
clinical characters, rules changed 0 and the legacy baseline changed 4. The
rules engine marks all 20 records for review. This is a small, exposed synthetic
corpus, not a blind test or a production estimate.

Category counts are descriptive only: the development set contains seven PERSON
annotations, of which four were detected exactly; two PATIENT_ID annotations,
of which one was detected; and one each for ADDRESS and HEALTH_INSURANCE_ID,
neither detected. Five PHONE annotations were detected, and the single explicit
DATE_OF_BIRTH example was detected. These small denominators do not support
category-level recall claims.

The exposed doctor–patient fixture has 4/5 exact detections and 4/5 all-required
redactions; all four supported required identifiers were redacted. The missed
case is a spoken-form DOB. Its protected clinical text has 0/152 characters
over-redacted. The exposed nurse-readback fixture has 5/6 exact detections and
5/6 all-required redactions; all five supported required identifiers were
redacted. The unsupported BHYT identifier remains in the denominator. Clinical
over-redaction is 0/1,519 characters. There is one synthetic fixture per
workflow, so neither result is statistically representative.

A separate injected partial-prefix detector on the nurse fixture produces a
deliberate partial identifier leak. The engine retains review status, flags
possible residual PII, and prohibits egress. Do not combine this fault-injection
result with rules-only precision or recall.

Current PII-02 gaps that should shape PII-03 research include contextual PERSON
misses, unsupported BHYT/address formats, spoken dates of birth, and the
distinction between speaker and identity subject. PII-02 has not evaluated
model-specific long-context windowing; future token classifiers need explicit
seam tests. Residual scanning is correlated with first-pass detection and cannot
prove anonymity. Current reports are review drafts, not sanitized payloads.

## 3. Scope, ownership, and trust boundaries

PII ownership begins with trusted **text** supplied by the upstream transcript
provider. Audio, ASR, microphone handling, form detection, policy processing,
shared backend code, and outbound API execution are outside PII-03.

Keep these fields separate:

- `scenario_type`: conversation or chart-readback workflow.
- `speaker_role`: who is speaking on a turn, possibly unknown.
- `subject_role`: whose identity a mention refers to, possibly unknown.

The scenario values are `DOCTOR_PATIENT_CONVERSATION` and
`NURSE_CHART_READBACK`; they share one text engine.

Never infer that the speaker is the person named. Unknown speaker metadata must
not suppress text detection. Runtime metadata, if needed, belongs in an optional
sidecar context and must not change the stable `TextInput` API.

The trust path remains local: the engine receives the original text and
source/revision binding; optional detectors return evidence; aggregation and
policy create a local review draft. No PII-03 result authorizes transmission.
Diagnostics, model outputs, benchmark logs, caches, and crash reports must not
contain raw transcript text or raw identifier values.

## 4. Candidate approaches — research only

No candidate is selected. All upstream descriptions and performance numbers
below are claims from the linked source, not results reproduced on this project.

| Candidate | Potential value | Limitations and provenance gates |
| --- | --- | --- |
| Deterministic rules and contextual validators | Retain PII-02 as the zero-dependency, reproducible control for structured phone, email, national-ID, patient/encounter-ID, explicit-DOB patterns, and context-cued names. Clear provenance and span behavior. | Current misses show that rules do not cover all name forms or unsupported categories. Expanding a list alone can create clinical false positives. Keep as a baseline and a possible hybrid component, not a completeness claim. |
| VnCoreNLP NER | Vietnamese word segmentation and general NER can provide a comparison for person/location/organization boundaries. Its NER has historical VLSP 2016 provenance. | General news-style NER, not a PII detector or clinical transcript model. The repository's program license is GPLv3; inspect model/data rights separately before any use. Java/runtime footprint and licensing make it a comparison candidate only. [Repository](https://github.com/vncorenlp/VnCoreNLP), [license](https://raw.githubusercontent.com/vncorenlp/VnCoreNLP/master/LICENSE.md), [releases](https://github.com/vncorenlp/VnCoreNLP/releases). |
| PhoBERT token classification | A Vietnamese-specific encoder is a candidate for a locally fine-tuned PII head after an approved PII training corpus exists. | `vinai/phobert-base` is listed as MIT, 135M parameters, with a 256-token limit and a word-segmented input requirement; `base-v2` is listed as AGPLv3. The pretrained base is not a trained PII detector. Tokenization/segmentation must preserve exact original-source offsets. [VinAI repository](https://github.com/VinAIResearch/PhoBERT). |
| XLM-R token classification | Multilingual baseline worth comparing for code-switching and ASR-style transcripts. A Vietnamese medical spoken-NER paper reports XLM-R performing well on its medical NER task and ASR output. | That is not PII evidence. The base model is MIT-licensed but has no project-specific PII head. [Model card](https://huggingface.co/FacebookAI/xlm-roberta-base), [spoken medical-NER paper](https://arxiv.org/abs/2406.13337). |
| OpenMed Vietnamese PII model | A PII-specific candidate whose card claims 54 entity types and reports self-evaluated results on an AI4Privacy-plus-synthetic test split. The card labels a SuperClinical Small model as 44M and Apache-2.0. | The card reports micro-F1 0.7305 and recall 0.7466, and explicitly warns about false negatives and human review. Those results are not independent and are not on these workflows. Its card says AI4Privacy 200K spans eight languages, while the current AI4Privacy card lists English, French, German, and Italian and no dataset license in the card. OpenMed also lists NVIDIA Nemotron-PII and about 25K Vietnamese synthetic samples. Resolve the data-version, license, base-weight, and training-provenance discrepancy before considering use. Nemotron-PII is described by NVIDIA as synthetic and CC BY 4.0; that does not settle rights for every training source. [OpenMed model card](https://huggingface.co/OpenMed/OpenMed-PII-Vietnamese-SuperClinical-Small-44M-v1), [AI4Privacy dataset card](https://huggingface.co/datasets/ai4privacy/pii-masking-200k), [Nemotron-PII dataset card](https://huggingface.co/datasets/nvidia/Nemotron-PII). |
| Rules plus contextual PII NER | A benchmark candidate: rules cover precise structured forms while NER proposes context-dependent mentions; aggregation retains evidence and sends unresolved cases to review. | Must be tested as an ablation against each component. Do not let clinical NER veto a possible identifier. Do not use a single global threshold or count an ambiguous unredacted span as safe. |

Vietnamese clinical NER resources are useful for terminology and hard-negative
design, not as PII qualification. ViMedNER describes more than 8,000 annotated
medical samples across five clinical entity types from Vietnamese health
websites; it is not a transcript PII corpus. The publication pages show
inconsistent license metadata, and the dataset's own reuse terms need separate
confirmation. VietMed-NER describes 18 medical entity types and ASR-like issues
such as missing punctuation and disfluencies, but is based on real-world medical
transcripts and does not provide the PII labels required here. En-ViMedNER is a
new biomedical abstract corpus built through translation and label projection;
it is described as silver-standard with a 450-sentence human-audited subset. None
of these resources is a substitute for this project's workflow-specific PII
evaluation. Do not ingest real transcripts under this plan. [ViMedNER paper](https://publications.eai.eu/index.php/inis/article/download/5221/3275), [ViMedNER publication record](https://eudl.eu/doi/10.4108/eetinis.v11i3.5221), [VietMed-NER paper](https://arxiv.org/abs/2406.13337), [En-ViMedNER project](https://vinuni-medical-mt.github.io/EnViMedNER/).

## 5. Proposed transcript benchmark

Build separate, synthetic evaluation groups. Report each workflow independently;
do not let a large readback group hide conversation-specific failures.

### Doctor–patient conversation

Include multi-turn questions/answers, patient self-identification, requests for
identification, DOB and contact details spoken as words or digits, repeated
mentions, pronouns, family members, clinician names, hesitations, corrections,
negation, medication discussion, and turns with unknown speaker metadata.
Annotate the identity subject separately from the speaker and retain a global
offset space across the entire transcript.

### Nurse chart readback

Include semi-structured consecutive fields for synthetic name, patient ID,
encounter ID, DOB, phone/national ID/insurance ID formats, vitals, diagnoses,
medications and doses. Emphasize adjacent fields, long uninterrupted utterances,
alphanumeric clinical terms, missing punctuation, ASR substitutions, and values
immediately following an identifier. Include explicit partial-prefix and
partial-suffix failure cases.

### Shared challenge design

- Positive PII: PERSON for patient, clinician, relative, and unknown subject;
  PHONE, EMAIL, NATIONAL_ID, PATIENT_ID, ENCOUNTER_ID, DATE_OF_BIRTH, and any
  category only after its format and policy are specified. Unsupported categories
  remain explicit review cases, not successful redactions.
- Hard negatives: medication names/doses, vital values/units, clinical
  abbreviations, dates of treatment, ages, symptoms, family history, negation,
  temporal phrases, corrections, and hospital/organization references that are
  clinically meaningful.
- Robustness: lowercase and unaccented ASR-like text, NFC/NFD, spacing and
  punctuation variation, number words, code-switching, multi-token names,
  repeated identifiers, Unicode combining marks, and tokenization/window seams.
- All examples and identity/contact values must be synthetic. Use a validated
  non-routable contact test namespace. Do not use live contact values or
  real-patient examples.
- Annotate original Python-string Unicode code-point `[start, end)` offsets on
  the complete source. Keep recognition, subject role, identifiability, masking
  action, ambiguity/review need, and protected clinical spans as distinct labels.
  For protected clinical events, annotate value/unit, negation, temporality,
  subject attribution, medication/dose, and correction state.
- Use two independent annotators and adjudication. Pilot the guideline before
  creating the locked set. Split by scenario family, transcript template,
  synthetic identity/identifier families, and base text before producing any
  ASR-style variants. Keep frozen evaluation custody independent of model and
  threshold tuning; hash and lock it before candidate evaluation.

The first pilot should validate the annotation rubric and coverage quotas, not
claim model quality. Scale the frozen set by the statistical requirements below.
Do not reuse the exposed PII-02 examples as an independently blind evaluation.

## 6. Metrics and statistical requirements

Report per workflow, entity category, subject role, supported/unsupported
status, and detector profile:

1. **Span/entity detection:** exact typed span precision, recall, and F1 with
   one-to-one matching; secondary overlap/IoU scores; duplicate predictions;
   boundary error and false negatives by category.
2. **Redaction:** complete identifier coverage at original-source offsets;
   supported-category and all-required denominators; partial-leak counts and
   residual characters. Unsupported required identifiers stay in all-required
   denominators and never count as sanitized successes.
3. **Transcript:** percentage with any remaining required PII; all-required
   redaction rate; review, partial, failed, and unsupported-case rates; complete
   source/window coverage; no silent truncation.
4. **Role/context:** subject-role accuracy separately from speaker-role metadata;
   mention-link accuracy for repeated references; results with role metadata
   absent versus present.
5. **Clinical preservation:** protected-span over-redaction, clinical assertion
   preservation and severity review. Measure preservation of subject,
   negation, temporality, medication/dose, values/units, corrections, and family
   attribution. Literal unchanged text alone is not a semantic-safety claim.
6. **Confidence/operations:** calibration by class/workflow, Brier or ECE,
   selective-risk/coverage curves, latency p50/p95, peak memory, cold start,
   maximum input length, and window-boundary errors.

For zero false negatives in `n` independent positive cases, the exact one-sided
95% lower bound on recall is `0.05 ** (1/n)`: at least 299 independent positives
per critical category and workflow are needed to support a 99% lower bound;
598 for 99.5%; 2,995 for 99.9%. Repeated mentions from the same transcript,
template, identity, or generated family are clustered, not independent. Use
cluster-aware confidence intervals and report the effective sampling unit.
If sample size is insufficient, report the estimate and interval without a
high-recall qualification.

## 7. Clinical-preservation and review semantics

- Never redact clinical measurements or medication doses solely because they
  contain digits. Protect their value, unit, negation, time context, correction,
  and subject attribution through overlapping PII/clinical boundaries.
- If an entity boundary conflicts with a medication, diagnosis, measurement, or
  another identifier, preserve both pieces of detector evidence. If the
  boundary cannot be resolved safely, mark the case ambiguous and require local
  review; do not label a partial name or identifier as fully removed.
- High detector execution completeness does not imply privacy safety. Keep the
  existing distinction among `COMPLETE`, `PARTIAL`, `REVIEW_REQUIRED`, and
  `FAILED`. Low or uncalibrated confidence and unsupported categories cannot
  become permission to transmit.
- A full-span direct identifier may be proposed for `[PII]` replacement only
  after a versioned policy decision. Any partial span, residual suffix, overlap
  conflict, or unresolved likely PII requires review and remains outbound
  prohibited.
- Do not introduce pseudonymization or identity mapping in PII-03. Do not
  interpret a residual-risk scan as proof of anonymity; it is correlated with
  first-pass detection.

The current immutable `EntityFinding` does not store model confidence. Keep
calibration artifacts in the optional research/runtime layer and bind their
revision to detector provenance. If later evidence shows confidence must be
persisted in public results, propose a separately versioned, backward-compatible
contract change rather than silently repurposing an existing field.

## 8. API and runtime integration proposal

Keep the existing `process_text` API unchanged:

```python
process_text(source: TextInput, *, extra_detectors=..., limits=...) -> PrivacyResult
```

Each optional adapter should implement the existing `DetectorSpec` callback
contract and return a validated `DetectorReport`:

- Bind findings to the exact `source_id` and `source_revision`.
- Convert every token/segment offset to the original source's Unicode
  code-point offsets using a verified mapping. Never recover offsets with
  approximate substring search.
- Report detector ID/version, model/tokenizer/calibration revision, declared
  supported categories, and processed coverage. No silent category omission or
  truncation.
- Preserve model/rule disagreements as separate evidence for aggregation.
- Map unresolved or low-confidence candidates to explicit ambiguity/review
  evidence; only a calibrated, supported, source-grounded finding may become a
  redaction proposal.
- Keep weights, caches, and benchmark artifacts outside Git. Pin hashes and
  licenses. Disable network and telemetry in all transcript-processing tests.
- The current callback is synchronous and cannot preempt arbitrary callback
  work. A future local runtime supervisor must enforce process-level deadlines,
  memory/resource limits, and failure semantics around the unchanged API.

Long transcripts exceed common encoder context windows. Evaluate deterministic
overlapping windows, maintain global offsets, merge evidence without dropping
entities at seams, and fail closed if any source region was not processed.

## 9. Hardware feasibility — estimate, not measurement

The primary development host is MacBook Air M1 with 8 GB unified memory;
Python 3.12 is available. Start with CPU inference and record cold-start,
throughput, p50/p95 latency, peak RSS, and thermal behavior. Approximate FP32
weight storage from parameter count alone is 4 bytes per parameter (e.g.
44M ≈176 MB, 135M ≈540 MB); this excludes framework, tokenizer, activations,
windows, and the operating system and is not a measured footprint. Verify model
parameter counts and actual memory before drawing feasibility conclusions.

MPS is optional only after CPU correctness is established. Apple Silicon uses
shared unified memory for CPU/GPU, and MPS operator/build support varies; compare
outputs with CPU and measure fallback, peak memory, and long-run stability.
[PyTorch MPS documentation](https://docs.pytorch.org/docs/main/notes/mps.html),
[Hugging Face Apple Silicon guide](https://huggingface.co/docs/transformers/main/apple_silicon).
Large-scale training can be evaluated later on a separate approved workstation.

## 10. Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Synthetic templates overstate recall | Use many unrelated scenario families, hard negatives, adversarial variants, independent locked custody, and report synthetic limitations. |
| License or training-data rights are unclear | Maintain separate manifests for code, weights, tokenizer, every dataset, and derived model; block candidate use until rights/provenance are reviewed. |
| Model finds clinical terms as PII or misses names/IDs | Per-category and workflow evaluation, clinical protected spans, conservative conflict-to-review behavior, and clinician adjudication. |
| ASR spelling/offset drift | Text-only corruption suite with exact transformation maps, original-offset tests, and window-seam challenges. Do not add ASR processing. |
| Speaker/subject confusion | Separate role annotations; unknown stays unknown; never equate speaker with subject. |
| Calibration drift or uncalibrated score | Calibrate by category/workflow on development data; freeze thresholds before locked test; low-confidence candidate PII goes to review. |
| Long callback stalls or memory exhaustion | Process-level timeout and memory supervision outside the pure API; hard input/finding/window budgets; failure returns no sanitized-success payload. |
| Logs or artifacts re-expose transcript data | Synthetic-only research, local-only execution, no raw text in logs, weights/cache/data outside Git, and verify no network access at runtime. |

## 11. Proposed milestones

1. **PII-03A — architecture and requirements approval.** Confirm taxonomy,
   workflow metadata, role semantics, clinical-preservation rubric, confidence
   policy, and license/governance checklist. Exit: owners approve the research
   scope; no model is selected.
2. **PII-03B — benchmark/annotation pilot.** Define versioned synthetic
   transcript schema and annotation handbook in the evaluation layer; create
   workflow-separated families, negatives, variants, and source-offset checks.
   Exit: inter-annotator agreement and adjudication meet the approved rubric.
3. **PII-03C — provenance and candidate audit.** Audit model cards, licenses,
   tokenizer/base weights, dataset snapshots, training sources, and acquisition
   hashes. Exit: only approved candidates may enter an offline experiment.
4. **PII-03D — reproducible local bake-off.** Compare PII-02 rules, eligible
   general Vietnamese NER, eligible PII-specific checkpoints, and hybrid
   ablations on CPU. No real transcript content or network inference. Exit:
   full metrics, resource results, failures, calibration, and provenance
   reviewed; model choice remains open if evidence is inconclusive.
5. **PII-03E — independent locked evaluation.** Freeze code, thresholds, and
   dataset hashes before independent custodian evaluation; publish confidence
   intervals and clinical review. Exit: independent report accepted for
   architecture review only.
6. **PII-03F — handoff gate.** Present evidence, risks, and open decisions for
   human approval. Any gateway or external-transmission design is a separate
   later phase and requires separate approval.

## 12. GO / NO-GO criteria and open decisions

**GO now:** architecture and benchmark design may be reviewed by the team.

**NO-GO now:** model selection, weights download, model inference, real-patient
training/evaluation data, production claims, gateway implementation, or external
transmission. Current evidence is an exposed 20-record baseline plus one
synthetic fixture per workflow; it does not qualify privacy safety.

Before considering any future external-transmission integration, require at
minimum: independent locked evaluation; lower 95% confidence bound of at least
99% recall per critical identifier category and workflow; a separately approved
transcript-level all-required threshold; no high-severity clinical assertion
loss; clinical over-redaction below a threshold approved by clinical/privacy
owners; complete source coverage; documented false-negative and residual-risk
handling; and zero egress for every `PARTIAL`, `REVIEW_REQUIRED`, `FAILED`,
unsupported, ambiguous, or unresolved-conflict result. These gates only permit
consideration of a separate gateway architecture; they do not themselves
authorize transmission.

Open decisions for architecture approval:

- Which PII categories are critical in each workflow, and which are
  unsupported/review-only?
- What clinical-over-redaction severity rubric and acceptable upper confidence
  bound will clinical/privacy owners approve?
- Which synthetic test-value namespace is guaranteed non-routable and safe?
- Who independently owns the frozen benchmark, adjudication, and unlock process?
- What license and provenance requirements are mandatory for weights, base
  models, tokenizers, and training data?
- How will the project represent calibrated confidence without breaking the
  public schema, if such persistence proves necessary?
- What deployment latency and memory budgets must the M1 and future runtime
  satisfy?
- What independent approvals and controls would be required before a separate
  trusted gateway phase is even proposed?

**Final status: PII-03 remains research-only and unapproved for implementation.
No model has been selected.**
