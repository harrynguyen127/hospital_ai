# Vietnamese Text PII Evaluation Protocol

## Implemented foundation and limits

PII-01 implements gold-data contracts, JSONL validation, leakage heuristics and
a small deterministic development generator. PII-02 adds a deterministic exposed
development comparison for the new rules-only engine and team regex prototype.
Model inference, independent clinical qualification and production authorization
are not implemented. No NLP model has been selected or benchmarked.

Historical model experiments, repository tests, model-card examples, and phrases
already discussed with developers are exposed evidence. They must not be
relabelled as independently blind evaluation data.

## Dataset schema and provenance

The [dataset module](../prototype/pii_runtime/evaluation/dataset.py) is independent
of detector predictions and `EntityFinding`. It reuses only primitive contracts
and shared taxonomy definitions from the pure feature.

Each immutable `DatasetRecord` records:

- Dataset/schema/taxonomy versions and original text ID/revision/offset unit.
- Record ID, split, stable scenario family, scenario version, generator version
  and unsigned 64-bit random seed.
- `project_synthetic` provenance, exposure status and optional custody reference.
- Recognition entities with exact spans, type, subject role and identifiability.
- A separate policy annotation for every unique recognized span.
- Protected clinical spans with category, subject role and assertion ID.
- Review spans and structured reasons for ambiguous or indirect identification.

The validator rejects unsupported versions, unknown labels, wrong types,
boolean offsets, out-of-bounds spans, duplicate annotations, missing/conflicting
policy annotations and redaction gold that overlaps protected clinical text.
Overlapping recognition annotations remain representable. Ambiguous recognition
and review policy require review annotations. `review_required` is derived from
those review annotations, not detector confidence.

Overlapping recognition spans are allowed, but overlapping gold policies must
have the same action. PRESERVE/REDACT, PRESERVE/PSEUDONYMIZE, REDACT/PSEUDONYMIZE,
and REVIEW/final-action overlaps are rejected in either annotation order. There
is no implicit action precedence or adjudication contract. A review annotation
does not resolve contradictory gold: authors must resolve the actual policies
before validation. Overlapping REVIEW policies remain valid with explicit review
annotations. Identical duplicate policies remain invalid (one policy per unique
entity span); they are not silently deduplicated. Touching half-open spans do not
overlap. Clinical preservation restrictions still apply independently.

The initial source is synthetic only. Generated phone-like strings might
coincidentally resemble assigned numbers; they are fictional fixtures and must
never be contacted. Insurance/patient references use explicit synthetic markers;
they test annotation/contract behavior, not production identifier-format recall.
Future format-realistic and public datasets require a documented provenance,
license and institutional-use review. Do not add real patient or hospital data.

## Development generation and storage

From `prototype/`, with Python 3.12 and no third-party dependencies:

```bash
python3.12 -B -m pii_runtime.evaluation.generate_synthetic \
  --seed 17 --output /tmp/hospital-ai-pii-development.jsonl
```

The output parent must already exist. The configurable output must resolve
outside the repository; an existing file is not overwritten. The generator
creates exactly 20 exposed development records, not training, regression or
evaluation splits. No generated corpus is checked into Git. Test fixtures are
source-code examples and are exposed too.

Scenario families cover names, phone, patient ID, insurance ID, DOB, address,
multiple and repeated identifiers, NFC/NFD distinctions, informal transcript
style, spoken digits, medication/dose, vital signs, negation, family history,
clinician/relative names, contextual dates/organizations, ambiguity and indirect
context. This is a contract exercise, not coverage of the entire taxonomy.

The same generator version, Python environment and seed reproduce text, offsets,
annotations and deterministic JSONL bytes. The generator uses an isolated
`random.Random`, not global state or cryptographic randomness. Scenario changes
require a version update. Python Unicode behavior/version belongs in a future
benchmark manifest. Public seed and code mean this corpus cannot be blind.

Programmatic APIs:

- `generate_development(seed)` returns an immutable tuple without writing files.
- `validate_dataset(records)` validates records and split integrity.
- `record_to_dict` / `record_from_dict` provide the strict JSON object boundary.
- `write_dataset` validates before creating an external JSONL file.
- `read_dataset` rejects malformed JSON, duplicate JSON keys, nonstandard numeric
  constants, unsupported fields/labels and split leakage.

Write failures can leave a partial file; read validation must succeed before
use. The initial tools are for small local corpora, not a hostile upload service
or a streaming large-dataset platform.

## Split independence and custody

| Split | Intended use | Access |
| --- | --- | --- |
| train | Optional future supervised training | Developer-visible |
| development | Rules, thresholds, debugging and error analysis | Exposed |
| regression | Independently authored failures and compatibility checks | Exposed after adoption |
| evaluation | Frozen one-time comparison of preregistered configurations | Independent custody |

Regression cases should be authored separately from training/development
templates. Once inspected, they remain useful regression tests but are not
blind evidence. Changing seeds does not create an independent split.

The validator requires unique record/source IDs and prohibits a scenario family
from crossing splits, even across seeds or scenario versions. It checks
cross-split normalized text and entity-erased template skeletons using token
sequence similarity (default threshold 0.85). NFC/case normalization, numeric
token canonicalization and gold-entity erasure help catch changed-value leakage.
Similarity uses the maximum of forward and reverse SequenceMatcher ratios so
pairwise acceptance/rejection is symmetric and invariant under record ordering.
Same-split variants are allowed. Near-duplicate checks are pairwise and suitable
for the initial small corpus. They cannot detect every semantic paraphrase.

Do not rename a family merely to evade the check or tune the similarity
threshold after viewing evaluation results. Human semantic review remains
required for split independence.

An evaluation record requires `independent_custody` plus a technical reference
to an external custody procedure. This is only a necessary schema condition:
the validator cannot verify that the procedure happened. An arbitrary reference
is not proof of independence. No independently held evaluation set is created
by this task, and the generator cannot create one.

Before locked evaluation, an independent custodian must:

1. Author/adjudicate new scenario families and maintain restricted access.
2. Check provenance, near duplicates and semantic leakage against exposed data.
3. Freeze record IDs, content hashes, annotation/policy versions and split quotas.
4. Record authorized access and preregister models, revisions, preprocessing,
   thresholds, metrics, matching and comparison rules.
5. Execute evaluation without allowing iterative tuning on its failures.
6. Retire the holdout for confirmation claims after it is opened for debugging.

Separate confirmation data is needed for strong final claims after selection,
unless the analysis explicitly accounts for selection and multiple comparisons.

## Future detection and privacy metrics

Use one-to-one prediction/gold matching so duplicate predictions cannot count
as multiple true positives. Report micro, macro and per-category metrics.

- Precision = TP / (TP + FP); recall = TP / (TP + FN).
- F1 = 2PR / (P + R). Undefined denominators must be shown as N/A with counts,
  not silently interpreted as perfect performance.
- Exact-span typed match requires identical source revision, `[start, end)` and
  entity type. Subject-role accuracy/confusion is reported separately.
- Overlap typed match requires positive character intersection and equal type.
  Use a preregistered maximum-cardinality bipartite match with deterministic
  tie-breaking; report overlap quality separately from exact scores.
- Full-identifier redaction coverage requires every gold character in a
  redact/pseudonymize span to be covered by the union of actual replacement
  source spans. A partial name or leaked suffix is a failure even if overlap
  detection scores count a match. Also report category FN and partial-leak rates.
- Report document-level incidence of at least one residual direct identifier.
- Keep recognition truth and policy truth separate. A correctly recognized but
  preserved organization is not automatically a redaction failure.
- Unsupported categories remain visible in the full-system denominator.

Report raw counts and confusion by category, identifier format, source style,
Unicode representation, length/window boundary and subject role. Report review
and failure rates on all eligible inputs, not only successful requests.

## Clinical preservation

Protected clinical characters are the union of gold clinical spans. Define
clinical over-redaction as protected source characters replaced divided by all
protected characters. Track affected assertions/documents separately so a small
character percentage cannot hide a dangerous negation or dose change.

Literal preservation requires unchanged source slices outside replacements.
Structured assertion checks cover medication, dose/unit, vital signs, symptom,
negation scope, temporal relations, corrections, family history and attribution.
The initial annotation categories/spans are a foundation for that work, not a
complete semantic assertion extractor.

Automated string/structure checks are not proof of clinical semantic correctness.
Use independent clinical review and adjudication of high-risk failures. Without
that review, semantic qualification remains unverified.

## Runtime methodology

Use the same data, taxonomy and masking policy for rules, each eligible NER,
and rules-plus-NER configurations. Preserve model-required preprocessing while
including its cost. Do not benchmark an untrained classification head as NER.

Start with CPU FP32, one model/worker, batch size 1 on Mac M1/8 GB. Record Python,
OS, dependency/model/tokenizer/segmenter revisions, input sizes, seeds, thread
settings and dtype. Keep environments, weights, caches and reports outside Git.

Measure normalization/segmentation, inference and total request latency;
cold load and warm p50/p95; peak process-tree RSS, memory pressure and MPS memory
where measurable; timeout/OOM/failure counts. MPS is a separate measured profile
after CPU correctness, with synchronization for timing and explicit fallbacks.
No performance or compatibility is claimed until measured.

## Confidence intervals and sample-size requirements

For high-recall claims with few failures, preregister one-sided exact binomial
confidence bounds rather than a normal approximation. With zero misses in `n`
independent opportunities, the one-sided 95% lower bound is `L = 0.05 ** (1/n)`.

| Target lower recall bound | Minimum n with zero misses |
| --- | ---: |
| 98% | 149 |
| 99% | 299 |
| 99.5% | 598 |
| 99.9% | 2,995 |

These are mathematical sample-size requirements, not observed performance or
a power analysis. With misses, calculate the exact bound again. For simultaneous
claims adjust multiplicity: six categories with Bonferroni family-wise 95%
confidence need 477 independent zero-miss opportunities per category for a
99% lower bound. Predefine categories and do not pool rare weak groups away.

Entities sharing a transcript/template are correlated, not independent trials.
Use independently sampled scenarios for binomial claims or preregister
cluster-aware estimates/intervals and a justified sampling design. Bootstrap
documents/scenario clusters for paired comparisons; do not bootstrap individual
correlated entities as if independent. Insufficient sample size means
insufficient evidence, not a pass. Synthetic bounds describe only the tested
synthetic distribution, not all clinical transcripts.

Statistical reference: [NIST confidence intervals for proportions](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm).

## Research selection versus production qualification

Maintain a research leaderboard separately from privacy qualification. Gate
license/provenance, trained-head validity, original-source mapping and coverage
before execution. Model-card scores and parameter counts do not select a winner.

Candidate future gates from the approved plan, to freeze before evaluation:

- High-risk category recall point estimate >=99% and one-sided 95% lower bound
  >=98%, with adequate independent samples for each declared category.
- Exact-span precision >=95%, separate full-identifier coverage reporting and
  no partial direct-ID leaks in the critical regression challenge.
- Protected-character over-redaction <=0.5%, with no adjudicated critical change
  to medication/dose, negation or subject meaning in the critical challenge.
- All tested invalid-output, missing-coverage and context-mismatch faults remain
  fail-closed for outbound use; no silent detector downgrade.
- CPU/MPS resource budgets preregistered before comparison; no lowering privacy
  gates to meet latency. Initial UX/memory proposals need workflow confirmation.

No threshold is a guarantee. A research winner still needs domain validation,
clinical review, security review, trustworthy backend provenance/context checks,
purpose/destination policy and organizational authorization. If none qualifies,
report no winner and limitations. PII-01 itself qualifies no engine or model.

## Verification commands

Run from `prototype/` using Python 3.12:

```bash
python3.12 -B -m unittest discover -s features/pii_filter -p 'test_schema.py' -v
python3.12 -B -m unittest discover -s pii_runtime/tests -p 'test_dataset.py' -v
python3.12 -B -m unittest discover -s features/pii_filter -p 'test_pii.py' -v
python3.12 -B -m unittest discover -s features/voice_input -p 'test*.py' -v
python3.12 -B -m unittest discover -s features/detect_form -p 'test*.py' -v
python3.12 -B -m unittest discover -s features/policy_rules -p 'test*.py' -v
python3.12 -B -m unittest discover -s tests -p 'test*.py' -v
```

Generation reproducibility, split-integrity, external JSONL round-trip and CLI
integration checks are included in the dataset tests. Test outputs use external
temporary directories and are removed afterward. Use explicit discovery roots:
the repository uses namespace-style directories rather than package initializers.

## PII-02 measured exposed-development comparison

Executed with Python 3.12, generator version `synthetic-development/1.0`, seed 17,
and the same 20 records for both systems. Reproduce from `prototype/`:

```bash
python3.12 -B -m pii_runtime.evaluation.evaluate_rules --seed 17
```

The command emits aggregate JSON to stdout and creates no dataset/report files.
The legacy tuple API has no native source findings: the evaluator replays its
exact substitutions with character-origin tracking, types spans by the original
placeholder rule, and asserts output/count equality to unchanged `pii.mask`.
There is no approximate diff alignment. Legacy exact-span metrics therefore
refer to substitution spans, including any accidentally replaced whitespace or
clinical words. They are not an independent NER evaluation. Full required-span
coverage is the common output-oriented measure. Duplicate predictions use
one-to-one matching; overlap uses maximum-cardinality matching. F1 is
`2*TP/(predicted+gold)`; unavailable denominators are N/A.

Percentages below are measured values on this exposed corpus only:

| Category | Gold | New exact P / R / F1 (%) | Legacy substitution P / R / F1 (%) | Overlap TP new / legacy | Required full coverage new vs legacy |
| --- | ---: | --- | --- | --- | --- |
| ADDRESS | 1 | N/A / 0.00 / 0.00 | N/A / 0.00 / 0.00 | 0 / 0 | 0/1 vs 0/1 |
| DATE | 1 | N/A / 0.00 / 0.00 | N/A / 0.00 / 0.00 | 0 / 0 | N/A: preserve/review policy |
| DATE_OF_BIRTH | 1 | 100.00 / 100.00 / 100.00 | N/A / 0.00 / 0.00 | 1 / 0 | 1/1 vs 0/1 |
| HEALTH_INSURANCE_ID | 1 | N/A / 0.00 / 0.00 | N/A / 0.00 / 0.00 | 0 / 0 | 0/1 vs 0/1 |
| ORGANIZATION | 1 | N/A / 0.00 / 0.00 | N/A / 0.00 / 0.00 | 0 / 0 | N/A: preserve/review policy |
| PATIENT_ID | 2 | 100.00 / 50.00 / 66.67 | N/A / 0.00 / 0.00 | 1 / 0 | 1/2 vs 0/2 |
| PERSON | 7 | 100.00 / 57.14 / 72.73 | 33.33 / 14.29 / 20.00 | 4 / 1 | 4/6 vs 1/6 |
| PHONE | 5 | 100.00 / 100.00 / 100.00 | 100.00 / 80.00 / 88.89 | 5 / 4 | 5/5 vs 4/5 |
| RARE_CONTEXT | 1 | N/A / 0.00 / 0.00 | N/A / 0.00 / 0.00 | 0 / 0 | N/A: preserve/review policy |

New engine full required-identifier coverage: **11/16**; legacy: **5/16**.
All 20 new results are REVIEW_REQUIRED, zero requests FAILED. Both systems were
compared over 191 protected clinical code points: new engine replaced **0/191**,
legacy **4/191** (2.09%). These are character-level observations, not proof of
clinical semantic correctness or negation-scope safety.

The new rules-only supported-category redaction coverage on these records is
**11/14** (PERSON, PHONE, PATIENT_ID and DATE_OF_BIRTH required redactions); the
all-required denominator is **16**, including unsupported BHYT and address.
The legacy trace supports only PHONE, NATIONAL_ID and PERSON here, with **5/11**
redactions among identifiers in those categories, versus **5/16** overall.
Coverage counts are output-span based and do not imply privacy qualification.

Key misses include names without supported cues, the technical NFD-name fixture
without an ordinary name cue, the ambiguous uncued given name, BHYT and addresses.
Lowercase ASR-style names are now redacted when an explicit cue, supported
Vietnamese surname structure and a resolvable boundary agree; unresolved
homographs remain review cases. A bare patient-ID mention without an explicit
label is missed. NATIONAL_ID, ENCOUNTER_ID and EMAIL have unit tests but no positive
examples in this 20-record corpus; no development recall claim is made for them.
Fourteen taxonomy categories have no built-in recognizer. Review-policy and
preserve-policy entities still count in recognition metrics, but are excluded
from the required-redaction denominator. There is no winner/qualification claim.

## Role-aware transcript scenario evaluation

Two additional small fixtures live in
`prototype/pii_runtime/evaluation/workflow_scenarios.py` and are evaluated
separately with:

```bash
python3.12 -B -m pii_runtime.evaluation.evaluate_workflows
```

`DOCTOR_PATIENT_CONVERSATION` contains a doctor asking for identity, patient
self-introduction and repeated reference, spoken DOB words, family-member
identification, hesitation, medication/dose, negation, symptom duration,
correction, and a phone value under an unknown speaker. Its expected local state
is REVIEW_REQUIRED. The unknown speaker's metadata is `None`; speaker role and
entity subject role are separate fields, and neither is passed to `TextInput`.

`NURSE_CHART_READBACK` contains adjacent name, SpO2, patient/encounter IDs, a
patient name before a medication/dose, unsupported BHYT, numeric DOB, diagnosis,
vital values, and a long protected note. A test-only detector replaces only the
`ABC` prefix of the synthetic BHYT value to ensure the remaining digits count as
partial-identifier leakage and trigger residual-risk review. This injection is
failure-test evidence, not a claimed BHYT recognizer. Its expected local state
is also REVIEW_REQUIRED.

Current deterministic output on the exposed fixtures keeps rules-only results
separate from the test-only partial-span fault injection:

| Scenario / run | Exact detection TP / predictions / gold | Precision / recall | Supported redaction | All-required redaction | Clinical over-redaction | Partial identifier leakage | Unsupported | Review / failure |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DOCTOR_PATIENT_CONVERSATION / rules-only | 4 / 4 / 5 | 100% / 80% | 4/4 (100%) | 4/5 (80%) | 0/152 | 0 | 1 spoken DOB | 1/1; 0/1 |
| NURSE_CHART_READBACK / rules-only | 5 / 5 / 6 | 100% / 83.33% | 5/5 (100%) | 5/6 (83.33%) | 0/1,519 | 0 | 1 BHYT format | 1/1; 0/1 |
| NURSE_CHART_READBACK / injected prefix | 5 / 6 / 6 | 83.33% / 83.33% | 5/5 (100%) | 5/6 (83.33%) | 0/1,519 | 1 BHYT suffix | 1 BHYT format | 1/1; 0/1 |

The injected run deliberately adds only the `ABC` prefix span for the synthetic
BHYT value. Exact-span matching correctly counts that prefix as an FP and leaves
the full unsupported gold entity as an FN. It is a fault-injection result, not
the standalone rules-only precision. The unsupported identifier remains
unredacted by the rules-only engine and is never counted as sanitized. All runs
report residual risk, require local review, and prohibit outbound use.

The evaluator emits prediction span coordinates, supported-category and
all-required coverage, known unsupported identifiers, clinical over-redaction,
residual leakage, review and failure states separately for each run. Exact
detection is typed, one-to-one matching. There is one project-authored synthetic
fixture per workflow; these exposed fixtures are not statistically
representative, independently blinded, real-clinical performance, or engine
qualification.

PII-02 verification after the targeted boundary/residual fixes and workflow
fixtures: **159** feature tests and **80** runtime/evaluation tests pass. The
prototype regression suites also pass: voice **8**, form detection **6**, policy
**6**, and isolation/scenario **13**. Total: **272 tests**, including the 146
pre-existing tests, with zero failures/errors/skips.

```bash
python3.12 -B -m unittest discover -s features/pii_filter -p 'test*.py' -v
python3.12 -B -m unittest discover -s pii_runtime/tests -p 'test*.py' -v
python3.12 -B -m unittest discover -s features/voice_input -p 'test*.py' -v
python3.12 -B -m unittest discover -s features/detect_form -p 'test*.py' -v
python3.12 -B -m unittest discover -s features/policy_rules -p 'test*.py' -v
python3.12 -B -m unittest discover -s tests -p 'test*.py' -v
python3.12 -B -m pii_runtime.evaluation.evaluate_workflows
```

The last command reports the two workflow scenarios independently; it does not
modify or replace the original 20-record development benchmark above.
