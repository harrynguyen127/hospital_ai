# Text PII Architecture: PII-01 Foundation and PII-02 Local Engine

## Status and ownership

**PII-01 complete; PII-02 rules-only local engine implemented for review. Not production-qualified.**

The [team regex prototype](../prototype/features/pii_filter/pii.py) and its
`pii.mask(text) -> (str, int)` registry contract remain unchanged. They are not
the official engine. No model has been selected. Earlier PhoBERT, OpenMed,
ASR, and privacy-pipeline experiments are research only.

PII ownership starts at trusted text input. Audio, ASR, microphone integration,
form detection, policy processing, shared backend logic, and external API
execution remain outside this feature. No teammate-owned module is changed.

## Implemented artifacts

- [schema.py](../prototype/features/pii_filter/schema.py): immutable contracts,
  versioned enums, source-span checks, and detector boundary validation.
- [dataset.py](../prototype/pii_runtime/evaluation/dataset.py): independent gold
  annotations, strict JSONL validation, and split-leakage checks.
- [generate_synthetic.py](../prototype/pii_runtime/evaluation/generate_synthetic.py):
  a deterministic, exposed, 20-record development corpus generated on demand.
- Contract and evaluation-data tests; no model dependencies or artifacts.
- PII-02 `normalization.py`, `rules.py`, `aggregation.py`, `deidentification.py`,
  `risk.py` and `engine.py` under the pure feature, with component/failure tests.
- [evaluate_rules.py](../prototype/pii_runtime/evaluation/evaluate_rules.py):
  reproducible exposed-development comparison against the unchanged prototype.
- [workflow_scenarios.py](../prototype/pii_runtime/evaluation/workflow_scenarios.py)
  and [evaluate_workflows.py](../prototype/pii_runtime/evaluation/evaluate_workflows.py):
  exposed role-aware synthetic dialogue/readback fixtures and separate scenario metrics.

The optional `pii_runtime` namespace currently contains evaluation tools only.
It does not provide inference. Namespace packages follow the existing repository
layout; empty package initializers and placeholder modules are unnecessary.

## Versions and taxonomy

`SCHEMA_VERSION = text-pii/1.0`; `TAXONOMY_VERSION = vi-clinical-pii/1.0`.
`DATASET_VERSION = vi-clinical-pii-dataset/1.1` is versioned independently;
existing 1.0 records remain readable, while the new clinical-result category
requires 1.1.
Unknown versions and unknown enum values are rejected, not coerced.

| Entity type | Typical identifying context; not an automatic masking rule |
| --- | --- |
| PERSON | Patient, clinician, relative, or another person's name |
| PHONE | Personal or contextually identifying contact number |
| EMAIL | Identifying mailbox |
| NATIONAL_ID | CCCD, CMND, or other national identity reference |
| PASSPORT | Passport reference |
| HEALTH_INSURANCE_ID | Insurance identifier, including Vietnamese BHYT |
| PATIENT_ID | Patient record identifier |
| ENCOUNTER_ID | Visit or encounter reference |
| DATE_OF_BIRTH | Explicit birth date |
| ADDRESS | Residential or other identifying address |
| GEO_COORDINATE | Identifying precise location |
| ACCOUNT_ID | Identifying account reference |
| FINANCIAL_ID | Financial identity or account reference |
| CONTACT_URL | URL identifying a person or account |
| ORGANIZATION | Context-dependent organization affiliation |
| DATE | Context-dependent calendar date |
| TIME | Context-dependent time |
| AGE | Context-dependent age or age band |
| OCCUPATION | Potential indirect identifier |
| RARE_CONTEXT | A rare combination of descriptive facts |
| UNKNOWN_IDENTIFIER | Suspected identifier requiring classification or review |

`SubjectRole` separates patient, clinician, relative, other, and unknown.
`Identifiability` separates direct, contextual, indirect, and ambiguous.
`PolicyAction` separates preserve, redact, pseudonymize, and review.

Entity findings have no default policy action. A date is not automatically a
birth date, an organization is not a person, and clinical measurements have no
blanket redaction rule. The classification tables describe requirements, not
implemented detection or contextual reasoning.

## Contract behavior

All seven public dataclasses are frozen, keyword-only, and slot-based. Nested
collections must be tuples with explicitly typed items. There are no arbitrary
diagnostic dictionaries or free-text failure messages in the contracts.

| Contract | Invariants |
| --- | --- |
| TextInput | Original string, opaque source ID/revision, supported versions and offset unit |
| SourceSpan | Strict integer offsets excluding bool; nonempty `[start, end)` |
| EntityFinding | Source-bound span, explicit type/role/identifiability and detector provenance |
| DetectorReport | Source binding, detector/model revision, declared entity support, processed ranges, findings, status/reasons |
| ReplacementDecision | Source-bound span and explicit policy action/version; an annotation only |
| PrivacyAssessment | Source binding, versioned profile, required detectors, status/reasons and outbound restriction |
| PrivacyResult | Versioned source-bound envelope, validated reports/decisions/assessment; never egress authorization |

Source-bound contracts receive `source=TextInput(...)` during construction.
They validate against that source and retain its ID/revision, not its raw text.
The `InitVar` source is not a stored dataclass field. `TextInput.text` and
`PrivacyResult.output_text` are excluded from normal representations, but this
is not a logging sanitizer: serializers can still expose their contents.

`output_text` is optional envelope data supplied by a caller. It is not
generated or semantically verified by PII-01. `ReplacementDecision` neither
renders a replacement nor creates an alias. Constructors do not perform an
assessment, detect PII, or certify that provided text has been de-identified.

Opaque technical IDs must match the bounded ASCII identifier format enforced
by the schema. Callers must never put patient values in those identifiers.
Closed `ReasonCode` enums prevent copying raw exceptions into diagnostics.
Format checks cannot prove that an opaque-looking identifier contains no PII.

## Original source and Unicode offsets

Offsets count Unicode code points in the original Python string, start-inclusive
and end-exclusive. They are not UTF-8 bytes, UTF-16 code units, grapheme indexes,
word indexes, or tokenizer positions. NFD strings are not normalized on input.
Source bounds are checked when findings, decisions, reports, and gold records
are bound to `TextInput`. An empty input has no nonempty span and may have an
empty complete coverage report.

The upstream trusted caller must issue a new revision whenever text changes and
must never reuse a source ID/revision for different content. Revision binding
is not cryptographic authentication. PII-01 does not maintain an identity store
or verify the truth of caller-provided patient/session context.

PII-02 implements canonical NFC/NFD views. Source segments group starters with
following combining marks and retain cross-starter canonical compositions
(including Hangul). Each analysis code point maps to its whole original segment.
Construction verifies both whole-string normalization and the complete mapping;
the rules boundary revalidates supplied views. No substring search or approximate
alignment recovers offsets. Bounds/revision/content mismatch fails explicitly.

Redaction boundaries expand to whole normalization segments, preventing residual
combining marks. This is not a full Unicode extended-grapheme/ZWJ segmenter.
Whitespace, punctuation, corrections and clinical values outside replacement
spans remain exactly as supplied. Word segmentation/tokenizer alignment remains
unimplemented. Spoken phone recognition only maps explicit digit-word spans;
it does not rewrite source numbers.

## Untrusted detector-output boundary

`validate_detector_report(source, report)` is the explicit Python callback
boundary. A dictionary, list, duck-typed object, or malformed nested contract
is rejected. Validation occurs before a consumer may use any finding.

- Source ID/revision must match, without rebinding stale findings.
- Versions, enum types, immutable collections, provenance, and bounds are checked.
- Supported entity categories are explicit and unique; each finding belongs to
  that declared support and uses the report's detector ID/version.
- Coverage is ordered and nonoverlapping; adjacent ranges are permitted.
- Findings must lie within the union of processed ranges.
- A complete report covers the entire source and carries no failure/review code.
- Partial, failed, or unavailable reports require reason codes.
- An unavailable report cannot claim findings or processed ranges.

Processed-range coverage does not mean entity recall or privacy safety.
Declared category support is also a capability claim to be benchmarked.
The function raises sanitized `TypeError` or `ValueError`; no invalid finding is
silently dropped. The PII-02 orchestrator catches boundary failures, emits failed
reports/results, and prohibits outbound use. This in-process validator does not defend against arbitrary code
execution by a malicious Python plugin.

## Assessment and gateway boundary

Assessment statuses are complete, partial, review_required, and failed.
Non-complete assessments require reasons and prohibit outbound use. Complete
means a declared assessment profile completed, never a guarantee of anonymity.
Complete results require their declared detector reports to be present and
complete, and cannot contain unresolved review decisions.

`UNRESOLVED_RISK_REASONS` explicitly classifies detector unavailable/failed,
incomplete coverage, invalid detector output/offset mapping, unknown label,
ambiguous entity, unresolved conflict, possible residual PII, indirect
identification risk, clinical review required, and context mismatch as unresolved
evidence. The same classification applies to assessment and decision reasons.
`UNQUALIFIED_PROFILE` records a qualification limitation and is not an execution
failure. No decision action implicitly resolves an unresolved reason.
PII-02 adds RESOURCE_LIMIT and UNSUPPORTED_CATEGORIES to the closed reason enum
and unresolved set without changing the seven PII-01 dataclass shapes, taxonomy,
registry or legacy behavior. Existing contract tests remain intact.

| Decision evidence | Assessment status | Outbound restriction |
| --- | --- | --- |
| Non-REVIEW action; no unresolved reasons | COMPLETE if required execution evidence is complete | PROHIBITED by default, or GATEWAY_REVIEW_REQUIRED |
| REVIEW action or any unresolved decision reason | PARTIAL, REVIEW_REQUIRED, or FAILED, with assessment reasons | PROHIBITED only |
| Any action with a non-complete assessment | PARTIAL, REVIEW_REQUIRED, or FAILED, with assessment reasons | PROHIBITED only |

A COMPLETE result with a PRESERVE decision carrying UNRESOLVED_CONFLICT is
rejected, even when its detector completed. Complete execution with
UNQUALIFIED_PROFILE can still request gateway review. These consistency checks
do not make COMPLETE mean privacy-safe, assess residual risk automatically, or
verify a caller-provided output text.

The outbound restriction defaults to prohibited. The only other value is
gateway_review_required, permitted only for a complete assessment. Neither is
ALLOW. `PrivacyResult.external_egress_authorized` is always false, excluded from
constructor arguments, and frozen. No contract grants outbound permission.

A future trusted backend must independently verify provenance, tenant/patient/
session context, purpose, source revision, payload binding, expiry, destination,
risk status, and organizational authorization. The existing prototype
`pii_filtered` flag is not sufficient authorization. No gateway or sender is
introduced here, and shared registry contracts are unchanged.

## Threat controls and deferred work

| Threat | PII-01 control | Still required later |
| --- | --- | --- |
| Invalid/partial source spans | Bounds, strict types, revision binding | Offset maps and redaction coverage |
| Unsupported label/provenance | Closed taxonomy and declared category checks | Verified model label mapping |
| Silent model failure/truncation | Explicit status, reasons and coverage contracts | Runtime enforcement and failure orchestration |
| Clinical over-redaction | Separate protected clinical ground truth | Detection policy, renderer and clinical review |
| Misleading confidence | No privacy probability field | Calibration research if justified |
| Cross-patient/retry confusion | Source identity/revision contract | Trusted context and request lifecycle |
| Log leakage | No raw-value diagnostic fields; sanitized validation errors | Safe logging in future runtime/backend |
| Prompt injection | No model, tool execution, or transcript interpretation | Keep future transcript content untrusted |
| Dataset leakage | Family and near-duplicate split checks | Independent custody and adjudication |
| Unauthorized egress | No authorization path | Trusted gateway and organizational approval |

Pseudonymization requirements remain proposed: CSPRNG aliases with at least
128 bits of entropy, stability only within a logical request, fresh independent
scopes, trusted context binding, short retention, expiry and retry checks, and
local-only mappings. No alias manager, vault, persistence or cryptographic token
generation is implemented.

## Compatibility and next phase

The legacy file, tests, placeholders, count behavior, registry slot, and README
compatibility instructions are preserved. The foundation registers no new slot
and does not replace the prototype's behavior.

PII-02 is implemented behind its own `process_text(TextInput, *, extra_detectors=(),
limits=EngineLimits()) -> PrivacyResult` API. It is not connected to the registry.
NER adapters, model selection, pseudonymization and gateway remain later phases.
See the [evaluation protocol](TEXT_PII_EVALUATION.md) for measured development
results and all limits on their interpretation.

## PII-02 actual supported rules

| Category | Implemented formats and constraints |
| --- | --- |
| PHONE | Vietnamese-style 10-digit mobile shapes starting 03/05/07/08/09; 11-digit 02 landline shapes; corresponding +84 shapes; single spaces/dots/hyphens between digits; bounded boundaries |
| PHONE, spoken | Exactly ten individual Vietnamese digit words after a phone cue; mobile shape validation; no general spoken-number grammar |
| NATIONAL_ID | Explicit CCCD/CMND/citizen-ID cues plus 9 or 12 digits, optionally separated; shape only, no authenticity/checksum/legal-status validation |
| EMAIL | Practical local-part/ASCII-domain pattern; not complete RFC or international mailbox coverage |
| PATIENT_ID | Explicit patient-ID label plus an ASCII alphanumeric/hyphen/underscore token containing a digit, at most 40 characters |
| ENCOUNTER_ID | Explicit visit/encounter label plus the same bounded token grammar |
| DATE_OF_BIRTH | Explicit birth-date cue plus numeric day/month/year and calendar validation |
| PERSON | Explicit patient/clinician/relative/title cue, a limited surname vocabulary, and bounded Vietnamese name tokens; clinical abbreviations, alphanumeric vital-sign forms, and dose/unit structure terminate a name before adjacent clinical content |

Lowercase contextual names or uncertain boundaries may produce AMBIGUOUS
findings with a REVIEW decision, not confident redactions. `Bệnh nhân là` and
unaccented equivalents are supported linking forms. `Mã bệnh nhân` is treated
as an identifier cue rather than a person-name cue. Name boundaries use
alphanumeric clinical-token recognition, medication dose/unit structure, a
limited clinical-abbreviation set, name-shape constraints and punctuation. An
unfamiliar adjacent capitalized token that cannot be segmented reliably remains
visible in a review span. Names without reliable cues, rare surnames, unusual
punctuation and unsupported formats may still be missed or misclassified.
There is no address/BHYT/passport recognizer or hospital-specific format knowledge.
Supported category declarations do not assert full recall for those categories.

### Workflow scenario fixtures

The evaluation layer has separate exposed synthetic fixtures for
`DOCTOR_PATIENT_CONVERSATION` and `NURSE_CHART_READBACK`; they exercise the same
text-only engine. `speaker_role` is sidecar fixture metadata and may be `None`.
Ground-truth `subject_role` independently describes whose identity an entity
represents. Neither field is inferred or required by `TextInput`, and unknown
speaker metadata never disables text detection. The fixtures retain offsets in
the complete original transcript, label spoken DOB and BHYT formats as known
unsupported cases, and preserve protected medication, dose, vital, negation,
temporal, family-history and attribution spans. A test-only partial detector in
the nurse scenario deliberately replaces only an identifier prefix to verify
that the residual assessor reports the visible suffix. These exposed fixtures
are not blind evidence, model evaluation, or clinical qualification.

## Aggregation, policy and rendering

All report types, revisions, categories, provenance and coverage are checked before
sorting/deduplication. Counts are bounded before deduplication. Exact duplicate
findings collapse only within the derived groups; original reports remain in
the result. Distinct detector evidence is preserved. Overlaps expand to canonical
source-segment boundaries and form connected union groups; touching spans stay
separate. Type or known-subject-role conflicts remain UNRESOLVED_CONFLICT.

The versioned policy `text-pii-redaction/1.0` redacts direct identifier groups.
Ambiguous or context-dependent groups require review and remain visible locally.
A group of conflicting direct identifier types may be conservatively redacted,
but its conflict reason still requires review. Dates/organizations are never
automatically treated as PERSON. PSEUDONYMIZE is rejected, not implemented as an alias.

The renderer validates every decision before output, rejects mixed-action
overlaps, merges same-action overlaps, and performs a single pass over the
original source. It uses a constant `[PII]`, not patient-derived identifiers.

## Risk, failures and resource limits

Profile `vi-text-rules-review/2.1` inspects detector status, processed ranges,
declared category coverage, group conflicts and review decisions. It also scans
the local output with the same rules and selected unsupported-identifier cues.
This residual scan is correlated with first-pass detection and cannot establish
anonymity or indirect re-identification safety. A cue followed by `[PII]` is
still flagged when alphanumeric content remains anywhere in the cue's remaining
value; the marker alone does not establish complete identifier removal.

The default profile always includes UNQUALIFIED_PROFILE, and includes
UNSUPPORTED_CATEGORIES when the union of declared support omits taxonomy types.
Successful rules-only requests are REVIEW_REQUIRED; valid incomplete detector
reports produce PARTIAL. Processing failures produce FAILED with output_text=None,
never raw-text fallback or a misleading sanitized-success payload. Failure
handling does not repeat the failing normalization/rendering stage. All results
are outbound PROHIBITED with external_egress_authorized=False.

Default limits are 32,000 original code points, 512 total raw findings, and four
extra detectors. Configurable hard ceilings are 200,000, 4,096 and eight,
respectively. Oversized inputs are rejected before normalization; finding limits
apply to both individual/combined reports before deduplication.

`DetectorSpec` is a trusted synchronous callback/test seam, not a model adapter.
Exceptions, invalid types/labels/offsets, stale revisions, declaration mismatches
and missing coverage have explicit failure/partial outcomes. Callback count is
bounded, but arbitrary callback CPU time/allocations cannot be preempted in this
pure in-process API. Hard timeouts and process isolation are future runtime work.
The default path loads no callbacks/models, calls no network, and keeps no state.
