# Text PII Preflight

## Scope

This feature accepts **text** (for example, a transcript produced by a teammate's trusted local speech-to-text service) and returns candidate personal information findings plus a redacted local text draft.

**Audio capture, ASR, PhoWhisper, audio redaction, and Cloud STT are outside this module's ownership.** No model files, datasets, or virtual environments are stored in this repository.

The new text preflight is experimental. It **does not certify de-identification, anonymization, or approval to transmit clinical data externally**. Detecting and masking some identifiers does not guarantee that all protected health information has been removed.

## Architecture

```text
Trusted source: transcript string
    |
    v
Text PII rules (standard library, local)
    |
    +-- Optional injected NER detector
    |       (future PhoBERT/OpenMed benchmark adapter)
    v
Source-offset findings -> overlap merging -> local redaction
    |
    v
TextPrivacyResult
    - masked_text
    - findings (offsets, types, sources)
    - status = review_required
    - detector_status, reason_codes
    - external_egress_authorized = False
```

## Files

| File | Purpose |
| --- | --- |
| `pii.py` | Existing registry-based `pii.mask(text) -> (str, int)` compatibility implementation |
| `text_privacy.py` | New pure text-only detection, optional detector injection, span aggregation and redaction |
| `test_pii.py` | Legacy contract tests |
| `test_text_privacy.py` | New synthetic privacy, failure and clinical preservation tests |

The pure feature has **no third-party dependencies and no network requests**. Future inference models should be loaded by a separate runtime adapter and passed as a detector callback. Do not import PyTorch or Transformers directly into the pure feature.

## API

Run from the repository's `prototype/` directory:

```python
from features.pii_filter.text_privacy import PiiFinding, process_text

result = process_text("Bệnh nhân Nguyễn Văn An, mạch 92 lần/phút.")
print(result.masked_text)
print(result.detector_status)
print(result.external_egress_authorized)  # Always False
```

Optional injected detector contract:

```python
from features.pii_filter.text_privacy import PiiFinding, process_text

def example_detector(text: str):
    # Replace with a verified local NER adapter in the trusted runtime.
    return [PiiFinding(0, 2, "PERSON", "example")]

result = process_text("An", ner_detector=example_detector)
```

All detector offsets must refer to the **original Python string**, not subword-token or word-segmented offsets. Invalid spans or detector failures result in a review-required result and do not enable network egress.

Overlapping spans are merged conservatively. Masking policies and semantic preservation need clinical review before integration.

## Setup on another computer

```bash
git clone --branch feat/pii-text-privacy --single-branch https://github.com/harrynguyen127/hospital_ai.git
cd hospital_ai/prototype
python3.12 -B -m unittest discover -s features/pii_filter -p 'test*.py' -v
python3.12 -B -m unittest discover -s tests -p 'test*.py' -v
```

This text-only foundation needs Python 3.11+ and the standard library. It does not need a GPU or a model download. A future benchmark-specific runtime can maintain its own environment and cache outside the Git repository.

For a Windows example, substitute `python` for `python3` where necessary. The previous Windows benchmark environment (`D:\hospital_ai_data`) is not part of the repository and is **not required** for these tests.

## Status and limitations

**Implemented:**
- Basic deterministic recognizers for email, phone, CCCD, contextual patient ID, contextual date of birth, and some titled person names
- Local span merging and redaction
- Optional NER callback with failure handling
- Structured result containing detector provenance and explicit non-authorization
- Synthetic tests and existing registry compatibility (legacy slot unchanged)

**Not implemented or not validated:**
- Production-grade Vietnamese clinical PII recall or safety thresholds
- Native PhoBERT or OpenMed inference in this new text-only branch
- Comprehensive names, addresses, hospital context, and mixed spoken numerals
- Clinical semantic preservation by clinician review
- Speaker/subject attribution or reliable pseudonymization
- Audio redaction, local ASR, Cloud STT, or an external privacy gateway
- Permission to transmit real patient data

Previous Windows research results for PhoWhisper/OpenMed are historical experiments only and were **not** migrated as runnable model code into this clean text-only branch. Do not treat those benchmarks as validation of the current implementation.

## Integration boundary

`pii.mask(text) -> (str, int)` remains registered for prototype compatibility. The new `process_text` path is independent and should only be integrated after the team approves a versioned text privacy contract, NER adapter behavior, and appropriate clinical/security review. The existing `voice.send` path is not changed by this work.

Always keep raw transcripts and detected identifiers inside an approved trusted environment. **Never use `status`, `masked_text`, or an arbitrary `pii_filtered` flag as proof of safe external egress.**

## Next steps

1. Define and freeze PII entity taxonomy and independent evaluation dataset.
2. Benchmark local PhoBERT/OpenMed inference adapters on validated Vietnamese clinical text.
3. Improve rules and clinical preservation against development data.
4. Have clinical and privacy reviewers validate false negatives and residual identification risks.
5. Agree on an explicit, separately authorized external-evaluation boundary if needed.
