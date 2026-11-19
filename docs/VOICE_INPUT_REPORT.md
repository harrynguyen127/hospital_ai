# BÁO CÁO PHƯƠNG ÁN TRIỂN KHAI: MODULE VOICE INPUT (`features/voice_input`) – 100% LOCAL

| Thông tin | Chi tiết |
|---|---|
| **Tính năng** | Tính năng 2 – Nhập liệu bằng giọng nói (`features/voice_input/`) |
| **Phụ trách** | Mai Tiến Huy |
| **Tiền xử lý âm thanh** | **VAD (Voice Activity Detection)** – Phát hiện tiếng nói, lọc khoảng lặng & chống ảo giác |
| **Mô hình STT** | `vinai/PhoWhisper-small` (chạy 100% local tại máy, có cache RAM) |
| **Trích xuất dữ liệu** | **100% Local** tại máy (`voice.extract`: chuyển số bằng chữ + khớp mờ lỗi STT + từ điển đồng nghĩa y khoa) |
| **Định hướng chốt** | **100% Local Offline (VAD + PhoWhisper-small Local + Local PII Mask + Local Form Extraction)** |

---

## 1. Mục tiêu & Phạm vi

Hoàn thiện module `features/voice_input/` chạy **100% Local (offline tại máy, không gọi bất kỳ Cloud API nào)**:
1. **Tiền xử lý âm thanh bằng VAD (`stt.py`):** Phát hiện đoạn có tiếng nói thật (`detect_voice_segments`, `has_speech`) theo từng frame 30ms trước khi đưa vào STT, giúp chặn đứng lỗi ảo giác khi im lặng (Whisper Hallucination) và tiết kiệm tài nguyên.
2. **Nhận diện giọng nói tiếng Việt tại máy (`stt.py`):** Dùng `vinai/PhoWhisper-small` (hoặc `vinai/PhoWhisper-tiny` qua `PHOWHISPER_MODEL`) chạy hoàn toàn trên máy, đọc WAV trực tiếp bằng `wave` + `numpy` (không cần `ffmpeg`), lưu cache model trong RAM.
3. **Bảo mật tuyệt đối dữ liệu bệnh nhân (100% On-Device):** Không gửi âm thanh hay văn bản ra internet. Toàn bộ dữ liệu được che định danh (`pii.mask`) ngay tại máy trước khi trích xuất điền nháp.
4. **Trích xuất thông minh hoàn toàn Local (`voice.py`):** Hỗ trợ đầy đủ cả **10 phiếu trong `forms.json`**, form mới phát sinh động từ `detect_form`, đủ **5 kiểu trường UI** (`number`, `text`/`textarea`, `datetime`, `checkbox`, `select`), tự đổi số bằng chữ tiếng Việt và khớp mờ các lỗi STT lệch âm/lệch dấu.
5. **Tuân thủ hợp đồng (`contracts/CONTRACTS.md`):** Giữ nguyên slot `voice.send` ở trạng thái tắt mặc định (`send_disabled`) và vượt qua 100% bài kiểm tra `tests/test_isolation.py` và `tests/test_scenario.py`.

---

## 2. Luồng xử lý kỹ thuật 4 bước (100% Local)

```
[Đầu vào: audio_path (file .wav từ micro) hoặc text (transcript), form (schema các trường), mask_fn (slot pii.mask)]
       │
       ▼
Bước 1 – VAD & STT Local (stt.py):
       ├── 1a. VAD Gate (detect_voice_segments / has_speech): Phân tích RMS theo khung 30ms.
       │       Nếu chỉ có im lặng / nhiễu nền -> Dừng ngay (trả về rỗng, chống ảo giác).
       └── 1b. STT Local (vinai/PhoWhisper-small): Nạp 1 lần vào RAM (_MODEL_CACHE) -> Chuỗi `text`.
       │
       ▼
Bước 2 – Lọc PII tại máy (external_api.prepare_payload):
       ├── Bắt buộc có `mask_fn` (không có -> RuntimeError).
       └── Che SĐT (`[SĐT]`), CCCD (`[CCCD]`), Tên (`[TÊN]`) -> `masked`, `pii_masked`, `pii_filtered=True`.
       │
       ▼
Bước 3 – Lọc câu ngoài lề (OUT_OF_SCOPE):
       └── Nếu chứa từ khóa tán gẫu ngoài lề -> trả về `out_of_scope: True, extracted: {}, source: "local"`.
       │
       ▼
Bước 4 – Trích xuất hoàn toàn Local (voice.extract):
       ├── Chuyển số bằng chữ tiếng Việt ("tám tám" -> 88, "37 phẩy 2" -> 37.2)
       ├── Khớp chính xác + từ đồng nghĩa y khoa (`SYNONYMS`) + khớp mờ lỗi STT (`_find_kw_end`)
       └── Trả về bản NHÁP `{"masked", "pii_masked", "out_of_scope": False, "extracted": {...}, "source": "local"}`
           (Chỉ lưu vào hồ sơ khi người dùng xác nhận qua `/api/records`)
```
