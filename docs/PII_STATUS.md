# PII Workstream Status

**PII-01 COMPLETE AND COMMITTED — PII-02 COMPLETED AND PUSHED (RULES-ONLY REVIEW MVP)**

The approved Architecture Plan V2 is in phased implementation. PII-01 contracts, taxonomy, and evaluation-data foundations are complete. PII-02 adds an independent deterministic local engine. PII-03 research and architecture planning is committed and pushed; PII-03 implementation has not started.

PII-02 commit: `cb2d7156e4a3fd1df63ae6dd16f826a72cca8777`.

PII-03 research-plan commit: `9ad7ab6536fe02b521da6dde529d2f387d52e66c`.

Production privacy qualification has not been achieved. External transcript egress is prohibited.

The existing [regex prototype](../prototype/features/pii_filter/pii.py) and [compatibility tests](../prototype/features/pii_filter/test_pii.py) remain unchanged team-provided compatibility code, not an official or production PII implementation. The [feature README](../prototype/features/pii_filter/README.md) retains the legacy compatibility instructions and separately documents the new foundation.

Completed PII-01 work:

- Versioned taxonomy and immutable typed contracts with original-source span validation.
- Detector provenance/category/range coverage and fail-closed status contracts.
- Synthetic gold-data schema, validator, deterministic development generator, and split-leakage checks.
- Foundation tests and English [architecture](TEXT_PII_ARCHITECTURE.md) and [evaluation methodology](TEXT_PII_EVALUATION.md) documentation.

PII-02 work implemented for review:

- Verified NFC/NFD analysis views mapping to original Unicode code-point spans.
- Limited contextual rules for phone, email, national ID, patient/encounter ID, explicit DOB and person names, including bounded Vietnamese name/clinical homograph handling and GCS/BMI/SpO2/HbA1c boundaries.
- Clinical gold taxonomy distinguishes diagnosis/lab-result spans; dataset v1.1 adds the category and keeps v1.0 records readable.
- Evidence-preserving aggregation, versioned redaction decisions and original-source rendering.
- Conservative local residual-risk assessment, explicit resource/failure handling and an independent API.
- Conservative person boundaries for alphanumeric vital tokens, medication dose/unit patterns, and known clinical abbreviations; unfamiliar adjacent terms remain explicit review cases.
- Placeholder suffix checking that flags residual alphanumeric identifier content instead of treating `[PII]` alone as complete redaction evidence.
- Exposed sidecar fixtures for doctor–patient conversations and nurse chart readbacks; unknown speaker metadata remains unknown and does not gate detection.
- 272 passing tests across PII feature/runtime and prototype regression suites, including the 146 pre-existing tests; zero failures/errors/skips.
- Deterministic comparison on the same 20 exposed synthetic development records: required-identifier full coverage 11/16 new versus 5/16 legacy; protected clinical characters replaced 0/191 new versus 4/191 legacy. The increase from 10/16 is the newly handled lowercase ASR-style patient name.
- Separate rules-only workflow results: doctor–patient exact detection 4/4 predictions and 4/5 gold, supported redaction 4/4 and all-required redaction 4/5; nurse readback 5/5 rules-only predictions and 5/6 gold, supported redaction 5/5 and all-required redaction 5/6. Clinical over-redaction is 0/152 and 0/1,519 respectively. The nurse prefix detector is a separate fault-injection result (5/6 exact precision/recall) and reports one partial BHYT leak; it is not included in rules-only precision. Both workflows require review and prohibit outbound use.

All 20 development engine results require review. This small exposed corpus is not a blind evaluation or production qualification. Local drafts can contain residual PII. The engine never authorizes external transmission.

Previous ASR and privacy-pipeline work was experimental research only. No model has been selected for the official PII workstream.

The following capabilities are not implemented as part of the official PII workstream:

- Production PII detection
- OpenMed inference
- Hybrid NER
- Pseudonymization
- Privacy Gateway
- Comprehensive residual/re-identification risk assessment
- Clinical PII benchmark qualification

Experimental text privacy implementation and tests have been removed. No previous Windows benchmark runtime is restored.

PII-02 is completed and pushed as a rules-only review MVP; it is not production-qualified. PII-03 remains research-only, with implementation not started. PII-04 through PII-06 have not started. No new registry integration or teammate-owned code changes are included.
