# PII Workstream Status

**NOT IMPLEMENTED — ARCHITECTURE AND RESEARCH PHASE**

Official PII implementation has not started. Implementation will begin only after a separately approved architecture plan.

The existing [regex prototype](../prototype/features/pii_filter/pii.py) and [compatibility tests](../prototype/features/pii_filter/test_pii.py) are a team-provided compatibility baseline, not an official or production PII implementation. The [feature README](../prototype/features/pii_filter/README.md) is restored unchanged from origin/main and describes that prototype baseline.

Previous PhoBERT, OpenMed, ASR, and privacy pipeline work was experimental research only. PhoBERT has not been selected as the official PII model.

The following capabilities are not implemented as part of the official PII workstream:

- Production PII detection
- PhoBERT inference
- OpenMed inference
- Hybrid NER
- Pseudonymization
- Privacy Gateway
- Residual risk assessment
- Clinical PII benchmark qualification

Experimental text privacy implementation and tests have been removed. No previous Windows benchmark runtime is restored.
