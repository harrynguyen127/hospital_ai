# CẨM NANG TRÌNH BÀY CHI TIẾT: MODULE VOICE INPUT (100% LOCAL)

Tài liệu hỗ trợ trình bày kiến trúc **100% Local (Offline tại máy)** của module `features/voice_input/`.

---

## 1. Tổng quan kiến trúc 100% Local

1. **VAD + PhoWhisper-small Local (`stt.py`):**
   - Lọc khoảng lặng/nhiễu nền theo khung 30ms bằng RMS (`detect_voice_segments`, `has_speech`) để chống ảo giác Whisper.
   - Chạy `vinai/PhoWhisper-small` trực tiếp tại máy, nạp động qua `importlib` (pass `test_isolation.py`), đọc WAV trực tiếp bằng `wave` + `numpy` (không cần `ffmpeg`), cache model trong RAM (`_MODEL_CACHE`).
2. **Bảo mật tuyệt đối – Zero Cloud Leakage (`external_api.py` + `pii.mask`):**
   - Không gửi bất kỳ dữ liệu âm thanh hay văn bản nào ra Cloud STT hay Cloud LLM.
   - Mọi văn bản đều bắt buộc đi qua `mask_fn` (`pii.mask`) để che SĐT (`[SĐT]`), CCCD (`[CCCD]`), Tên (`[TÊN]`) ngay tại máy.
   - Slot `voice.send` giữ mặc định `send_disabled` theo hợp đồng `contracts/CONTRACTS.md`.
3. **Bộ trích xuất hoàn toàn Local (`voice.py`):**
   - Hỗ trợ đầy đủ **10 phiếu EMR trong `forms.json`** và các form mới phát sinh động.
   - Hỗ trợ **5 kiểu trường UI**: `number`, `text`/`textarea`, `datetime`, `checkbox`, `select`.
   - Tự động chuyển số bằng chữ tiếng Việt (*"tám tám"* → `88`, *"37 phẩy 2"* → `37.2`, *"một hai mươi trên tám mươi"* → `"120/80"`).
   - Khớp mờ tự động xử lý lỗi STT lệch âm/dấu (*"mách"*, *"nhìn thời"*, *"nhiệt đố"*) mà không cần khai báo thủ công từng lỗi.

---

## 2. Q&A nhanh

- **Không dùng Cloud API thì có chạy được khi mất mạng không?**
  Có. Toàn bộ pipeline chạy offline 100% tại máy, không phụ thuộc Internet hay API key.
- **Có bị vi phạm `test_isolation.py` khi dùng PhoWhisper không?**
  Không. `stt.py` dùng `importlib.import_module("transformers")` và `importlib.import_module("numpy")` trong hàm thay vì top-level import.
- **Kịch bản kiểm thử đầy đủ nằm ở đâu?**
  Xem 10 kịch bản Happy Case (tương ứng đủ 10 phiếu EMR) kèm Synthetic Output đã kiểm chứng thực tế tại [VOICE_LOCAL_TEST_SCENARIOS.md](file:///d:/hospital_ai/docs/VOICE_LOCAL_TEST_SCENARIOS.md).
