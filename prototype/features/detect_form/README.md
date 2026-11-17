# Tính năng 3 – Detect form

**Làm gì:** đọc nhãn, kiểu, bắt buộc của form trên màn hình → so khớp với registry: trùng chính xác (fingerprint), gần giống (Jaccard ≥ 0,8, tự tăng phiên bản), hoặc form mới (schema nháp, kiểm tra tự động, áp dụng hoặc lưu nháp). Có hoàn tác phiên bản.
**Slot:** `form.detect`, `form.rollback`.
**Mặc định:** `form_detection.py`. Hàm thuần, không đụng state.
**Phụ thuộc:** `shared/common.py` (chuẩn hóa, fingerprint). Không phụ thuộc tính năng khác.

## Chạy test độc lập

```bash
python features/detect_form/test_detect_form.py
```

## Nối bản thật

Thay tầng nhận diện (tầng 2 OCR/OmniParser, tầng 3 VLM sinh schema). Giữ đúng chữ ký `detect(forms, payload)` và trả `changes["forms"]` khi có thay đổi. Nối bằng:

```python
registry.connect("form.detect", my_detect)
```

Hiện form mới đang dùng schema stub từ nhãn (chưa gọi VLM).
