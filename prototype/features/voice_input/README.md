# Tính năng 2 – Nhận diện giọng nói 100% Local (VAD + PhoWhisper-small) → điền form tại máy

**Làm gì:** nhận file âm thanh (lọc khoảng lặng qua **VAD** rồi chuyển thành văn bản 100% local qua `vinai/PhoWhisper-small` tại `stt.py`) hoặc transcript → che PII tại máy (`prepare_payload`) → lọc câu ngoài lề → trích xuất hoàn toàn tại máy (`extract`) → **điền nháp**. Chỉ lưu khi người dùng xác nhận.
**Chế độ chạy:** **100% Local (offline tại máy)** — không gọi Cloud STT, không gọi Cloud LLM. Slot `voice.send` trong `external_api.py` giữ ở trạng thái tắt mặc định (`send_disabled`) theo hợp đồng `contracts/CONTRACTS.md`.
**Phụ thuộc:** không phụ thuộc tính năng khác. Bộ lọc PII được truyền vào (`mask_fn`), không import `pii_filter`.

## Kịch bản giao diện

Tab **Giọng nói** có nút **🎤 Ghi âm từ micro (thật)** và 10 buổi mẫu tương ứng với 10 phiếu EMR. Với ô danh sách, bộ trích xuất chỉ nhận một lựa chọn có sẵn trên phiếu. Dữ liệu hội thoại, vai người nói và mô tả nằm trong `../../web/voice-samples.js`; hướng dẫn thử và kết quả mong đợi ở [README prototype](../../README.md#thử-kịch-bản-giọng-nói).

Mỗi câu được xử lý qua `/api/voice` (hoặc `/api/voice/audio` khi ghi âm thật) trước khi hiển thị transcript đã che. Người dùng có thể dừng để xử lý phần đã nghe hoặc hủy. Giá trị từ câu đọc lại thay thế giá trị cũ của cùng ô. Hết buổi chỉ tổng hợp vào nháp và hiển thị kết quả để kiểm tra; không tự gọi API lưu bản ghi. Buổi đang chạy bị vô hiệu khi đổi bệnh nhân, phiếu hoặc tài khoản.

## Chạy test độc lập

```bash
python features/voice_input/test_voice.py
```

## Dùng VAD + PhoWhisper Local cho file âm thanh

Mặc định `stt.transcribe(audio_path)` kiểm tra tiếng nói qua `stt.has_speech(audio_path)` (VAD Gate), sau đó chạy `vinai/PhoWhisper-small` (hoặc `PHOWHISPER_MODEL` trong `.env`) hoàn toàn tại máy qua `transformers`/`torch` (đọc WAV trực tiếp bằng `wave` + `numpy`, không cần cài `ffmpeg`, cache model trong RAM):

```python
from features.voice_input import voice
res = voice.process("", form, mask_fn=my_mask, audio_path="buoi_kham.wav")
```

Bộ trích xuất local hỗ trợ đủ 10 phiếu EMR, form mới phát sinh động, chuyển số bằng chữ tiếng Việt (như đầu ra PhoWhisper), và khớp mờ các lỗi STT lệch âm/lệch dấu.

## Bật lại Cloud API (khi cần dùng sau này)

Toàn bộ code gọi API ngoài **không bị xóa** mà đang được comment gọn với nhãn `[TẠM TẮT - CHƯA SỬ DỤNG]` tại:
- `stt.py`: `blaze_stt()` và nhánh `BLAZE_API_KEY` trong `transcribe()` / `transcribe_with_info()`.
- `external_api.py`: `llm_sender()` (hàm `sanitize_extracted()` vẫn giữ nguyên).
- `voice.py`: nhánh Hybrid gọi `external_api.send_filtered(payload)` trong `process()`.
- `server.py` và `.env`: tự động nối `voice.send` và các biến `VOICE_API_*`, `BLAZE_*`.
- `verify_hybrid.py` và `test_voice.py`: kịch bản chứng minh và unit test tương ứng.

