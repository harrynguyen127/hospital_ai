# Tính năng 2 – Nhận diện giọng nói → điền form

**Làm gì:** nhận transcript (prototype: gõ/phát sẵn, chưa có STT thật) → che PII → lọc câu ngoài lề → trích xuất vào ô của form → **nháp**. Chỉ lưu khi người dùng xác nhận.
**Gửi API ngoài:** chỉ sau khi đã lọc PII, qua slot `voice.send`. Mặc định là tắt (không gọi mạng).
**Phụ thuộc:** không có tính năng khác. Bộ lọc PII được truyền vào (`mask_fn`), không import `pii_filter`.

## Chạy test độc lập

```bash
python features/voice_input/test_voice.py
```

## Nối bản thật

- **STT / trích xuất:** thay phần thân của `voice.py` (giữ hàm `process(text, form, mask_fn)`).
- **API ngoài:** viết `sender(payload) -> dict` và thêm trong `services/engine.py`:

```python
registry.connect("voice.send", my_sender)
```

`my_sender` chỉ nhận payload đã có `pii_filtered: True`. Đừng gửi transcript gốc.
