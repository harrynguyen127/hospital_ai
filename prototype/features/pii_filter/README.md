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
