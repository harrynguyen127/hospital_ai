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

The official PII engine is **NOT IMPLEMENTED**. PII-01 adds only:

- `schema.py`: versioned taxonomy, immutable contracts, original Unicode
  code-point span validation, detector coverage/provenance and status contracts.
- `test_schema.py`: contract and untrusted detector-output validation tests.
- Separate standard-library evaluation tools in `prototype/pii_runtime/evaluation/`
  for synthetic ground truth, exposed development generation and split checks.

No new detector, inference runtime, renderer, pseudonymization or gateway is
provided. No model has been selected, and no contract authorizes external use.
See the [architecture](../../../docs/TEXT_PII_ARCHITECTURE.md),
[evaluation protocol and test commands](../../../docs/TEXT_PII_EVALUATION.md),
and [workstream status](../../../docs/PII_STATUS.md).
