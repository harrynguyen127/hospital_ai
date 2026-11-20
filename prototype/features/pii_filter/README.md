# Tính năng 1 – Lọc PII

**Làm gì:** che SĐT, CCCD và tên sau danh xưng. Đây là bước bắt buộc trước khi dữ liệu đi ra ngoài.
**Slot:** `pii.mask` (xem [contracts/CONTRACTS.md](../../contracts/CONTRACTS.md)).
**Mặc định:** `pii.py` (regex, tất định, không gọi mạng).
**Phụ thuộc:** không có (chỉ thư viện chuẩn).

## Chạy test độc lập

```bash
python features/pii_filter/test_pii.py
```

## Nối bản thật

Viết hàm `mask(text) -> (str, int)` trong file riêng (ví dụ `ner_pii.py`), rồi trong `services/engine.py` thêm:

```python
registry.connect("pii.mask", ner_mask)
```

Bản thật phải che ít nhất những gì bản mặc định che. Thêm loại PII mới thì thêm test vào `test_pii.py`.

## PII-01 foundation (separate from the team prototype)

The legacy compatibility instructions above and `pii.mask(text) -> (str, int)`
behavior are unchanged. They describe the team-provided regex prototype.

PII-01 provides the completed foundation:

- `schema.py`: versioned taxonomy, immutable contracts, original Unicode
  code-point span validation, detector coverage/provenance and status contracts.
- `test_schema.py`: contract and untrusted detector-output validation tests.
- Separate standard-library evaluation tools in `prototype/pii_runtime/evaluation/`
  for synthetic ground truth, exposed development generation and split checks.

PII-02 now adds a local rules-only engine for review. It is independent of the
legacy slot and is not production-qualified. No model has been selected.
See the [architecture](../../../docs/TEXT_PII_ARCHITECTURE.md),
[evaluation protocol and test commands](../../../docs/TEXT_PII_EVALUATION.md),
and [workstream status](../../../docs/PII_STATUS.md).

## PII-02 API

Run from `prototype/` using Python 3.12 and the standard library:

```python
from features.pii_filter.engine import process_text
from features.pii_filter.schema import TextInput

source = TextInput(
    text="Bệnh nhân Nguyễn Văn An; mạch 92 lần/phút.",
    source_id="example-1",
    source_revision="1",
)
result = process_text(source)
assert result.output_text == "Bệnh nhân [PII]; mạch 92 lần/phút."
assert result.assessment.status.value == "review_required"
assert result.external_egress_authorized is False
```

Supported categories are PERSON, PHONE, EMAIL, NATIONAL_ID, PATIENT_ID,
ENCOUNTER_ID and DATE_OF_BIRTH, within the explicit formats/cues documented in
the architecture. Coverage is incomplete even within these categories. No BHYT
or hospital-specific format is guessed. Spoken phone support is limited to ten
individual Vietnamese digit words after an explicit phone cue.

The engine uses verified NFC views with original code-point mappings, keeps raw
detector evidence in reports, expands replacement boundaries over combining
clusters, and replaces selected spans with `[PII]`. Everything outside replacement
spans is preserved literally. PERSON boundaries use clinical compounds, dose/unit
structure, limited name continuations and punctuation; unfamiliar adjacent
capitalized terms stay visible as ambiguous findings for local review. A
placeholder followed by remaining alphanumeric content is not treated as proof
that the complete identifier was removed. Do not treat a review draft as
sanitized for transmission.

The evaluation layer also contains exposed synthetic fixtures for
`DOCTOR_PATIENT_CONVERSATION` and `NURSE_CHART_READBACK`. `speaker_role` is
sidecar metadata and may be unknown; `subject_role` belongs to each annotated
identity. Neither changes the compatible `TextInput` API or creates a separate
engine. Run the scenario report with
`python3.12 -B -m pii_runtime.evaluation.evaluate_workflows` from `prototype/`.

Default budgets: 32,000 original code points, 512 raw findings and four optional
trusted synchronous callbacks. `EngineLimits` allows bounded configuration.
Callback integration is a contract/test seam, not an inference runtime; hard
callback timeouts/process isolation are not implemented.

Invalid request contracts raise sanitized errors. Processing failures return
FAILED with `output_text=None`; partial detector coverage returns PARTIAL.
Successful rules-only processing returns REVIEW_REQUIRED, never authorization.
Pseudonymization, models, cloud APIs, gateway, audio and frontend integration
remain unimplemented. Literal tests do not prove clinical semantic safety.

```bash
python3.12 -B -m unittest discover -s features/pii_filter -p 'test*.py' -v
python3.12 -B -m unittest discover -s pii_runtime/tests -p 'test*.py' -v
python3.12 -B -m unittest discover -s tests -p 'test*.py' -v
python3.12 -B -m pii_runtime.evaluation.evaluate_rules --seed 17
python3.12 -B -m pii_runtime.evaluation.evaluate_workflows
```

Verification: 272 tests passed across the PII feature/runtime and prototype
regression suites, including the 146 pre-existing tests. On the
20 exposed synthetic development records, full required-identifier coverage was
11/16 for the new engine versus 5/16 for the unchanged team prototype. All 20 new
results required review. See the evaluation document for per-category scores,
misses and trace-method limitations. The two exposed workflow fixtures are
reported with standalone rules-only metrics and a separate nurse partial-prefix
fault injection; both review states and the residual identifier leak are shown
separately. No blind or production qualification is claimed.
