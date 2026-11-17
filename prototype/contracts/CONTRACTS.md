# Hợp đồng giữa tính năng và lõi

Mỗi tính năng là một **hàm thuần** và có bản mặc định (code prototype). Lõi (`services/engine.py`) gọi qua **registry**, nên bản thật thay được bản mặc định mà không sửa tính năng khác.

## Quy tắc

1. **Độc lập:** tính năng chỉ import thư viện chuẩn, `contracts/`, `shared/` và chính folder của mình. Không import tính năng khác, không import `services/`. Được kiểm tự động bởi `tests/test_isolation.py`.
2. **Hàm thuần:** không đọc hay ghi state. Nhận dữ liệu qua tham số, trả về `{"result", "changes", "events"}`:
   - `result`: dữ liệu trả cho API (`ok`, `error`, …).
   - `changes`: `{khóa_state: giá_trị_mới}`. Lõi thay từng khóa trong state. Rỗng nghĩa là không đổi gì.
   - `events`: danh sách `(loại, nội dung)`. Lõi ghi vào nhật ký.
3. **Tự đăng ký mặc định:** cuối file tính năng có `registry.define(slot, hàm_mặc_định)`.
4. **Nối bản thật:** thêm `registry.connect(slot, impl)` vào mục CONNECTIONS trong `services/engine.py`. Không có dòng nào thì dùng mặc định.
5. **Giữ nguyên chữ ký:** bản thật phải nhận và trả đúng dạng của slot. Thêm tham số thì phải có giá trị mặc định.

Trạng thái các điểm nối khi chạy server: in ra lúc khởi động (`nối` hoặc `mặc định`).

## Các slot

| Slot | Chữ ký | Đầu vào | Đầu ra | Mặc định (file) |
|---|---|---|---|---|
| `pii.mask` | `mask(text) -> (str, int)` | văn bản thô | văn bản đã che, số chỗ che | `features/pii_filter/pii.py` |
| `voice.send` | `send(payload) -> dict` | `{"text", "pii_filtered": True, "pii_masked"}` | `{"sent": bool, "reason"?}` | `features/voice_input/external_api.py` (`send_disabled`) |
| `form.detect` | `detect(forms, payload) -> out` | `forms`: registry; `payload`: `{"title", "fields": [{label, ui, required?, options?}]}` | `out` | `features/detect_form/form_detection.py` |
| `form.rollback` | `rollback_form(forms, form_id) -> out` | registry, id form | `out` | `features/detect_form/form_detection.py` |
| `policy.ingest` | `ingest(text, doc_id, doc_version, effective_from, rulesets, forms, docs, clock, dry_run, impact_fn) -> out` | văn bản quy định + state cần đọc | `out` | `features/policy_rules/policy.py` |
| `policy.rollback` | `rollback(rulesets) -> out` | danh sách phiên bản luật | `out` | `features/policy_rules/policy.py` |

Ghi chú:
- `impact_fn(rules_cu, rules_moi) -> dict` do lõi cung cấp. Nó tính số việc nhắc theo người dùng (phụ thuộc `services/reminder`). Tính năng không tự tính.
- `voice.process(text, form, mask_fn)` không phải slot: lõi gọi và truyền `mask_fn` lấy từ slot `pii.mask`. Không truyền thì hàm từ chối chạy.
- `prepare_payload(raw, mask_fn)` và `send_filtered(payload)` trong `external_api.py`: payload gửi ra ngoài phải có `pii_filtered: True`, nếu không thì bị từ chối.

## Chẩn đoán

```bash
cd prototype
python -c "from services import engine; from contracts import registry; print(registry.status())"
```
