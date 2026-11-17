# Prototype – Nhắc việc theo quy định + nhập liệu bằng giọng nói

Bản prototype dựng theo `../docs/DETECT_FORM_POLICY_ENGINE.md`, `../docs/TEAM_ACTION_PLAN.md` và `../docs/TEAM_VISION.md`.
Chỉ dùng **dữ liệu giả** (mock EMR, bệnh nhân BN-01…BN-06, văn bản quy định mẫu).

## Chạy

```bash
cd prototype
python server.py          # http://127.0.0.1:8765
```

Không cần cài thư viện ngoài (chỉ Python 3.10+). Chạy test kịch bản:

```bash
python tests/test_scenario.py          # kịch bản đầy đủ qua lõi
python tests/test_isolation.py         # không phụ thuộc chéo giữa tính năng
python features/pii_filter/test_pii.py # từng tính năng, chạy độc lập
python features/voice_input/test_voice.py
python features/detect_form/test_detect_form.py
python features/policy_rules/test_policy.py
```

Tính năng nối bản thật thế nào: xem [contracts/CONTRACTS.md](contracts/CONTRACTS.md). Khi chưa nối, server dùng bản mặc định và in trạng thái khi khởi động.

## Kịch bản demo bắt buộc (A2 trong TEAM_ACTION_PLAN)

1. Tab **Nhắc việc**, người dùng `bs_a` (bác sĩ): bộ luật **v1** → **13 việc**.
2. Tab **Quy định**: chọn mẫu *QĐ chăm sóc – v2*, bấm **Phân tích** để xem diff và chạy thử tác động (13 → 15), rồi **Nạp & tự động áp dụng**.
3. Không sửa code, không khởi động lại → tab **Nhắc việc** hiện **15 việc**, hạn tính lại; header ghi "Bộ luật đang áp dụng: v2, hiệu lực từ …".
4. Nút **Hoàn tác về phiên bản trước** đưa về v1 (13 việc).

## Các module

| Module | File | Ghi chú |
|---|---|---|
| 1. Detect form | `features/detect_form/form_detection.py`, `web/app.js` (`scanDom`) | Đọc DOM (nhãn, kiểu, bắt buộc) → fingerprint (exact) → Jaccard ≥ 0,8 (gần giống, tự tăng phiên bản) → form mới: schema nháp từ nhãn (stub, **chưa gọi VLM**) → kiểm tra tự động → áp dụng hoặc lưu nháp. Có hoàn tác phiên bản form. |
| 2. Policy | `features/policy_rules/policy.py`, `data/regulations/` | Cắt theo khoản `x.y` → bóc luật bằng **mẫu câu (regex)**, thay cho LLM có structured output → kiểm tra 6 lớp → diff → chạy thử tác động → phát hành `vN` bất biến → hoàn tác. Khoản mơ hồ (“khoảng”, “hoặc”, “tối đa”) → `needs_clarification`, không áp dụng. |
| 3. Nhắc việc | `services/reminder.py` | 7 kiểu lịch (`once_within`, `once_after`, `recurring`, `sequence`, `daily_before`, `min_per_period`, `on_event`). Tất định, không gọi LLM. Đọc bộ luật đang hiệu lực. |
| 4. Voice | `features/voice_input/voice.py`, `features/voice_input/external_api.py` (gửi API ngoài chỉ sau lọc PII, đang tắt), lọc PII ở `features/pii_filter/pii.py`; tab **Voice** | Transcript gõ/phát sẵn (**không có STT thật**). Che SĐT/CCCD/tên → lọc câu ngoài lề → trích xuất vào trường form → **nháp**; chỉ lưu khi bấm xác nhận. |

Bộ luật lưu trong `.runtime/state.json` (tự tạo khi chạy, đã gitignore). Nút **Đặt lại demo** xóa state và nạp lại seed.

## Những gì prototype **chưa** làm (có chủ đích)

- Chưa có extension trình duyệt thật; quét DOM được làm từ trang mock.
- Chưa có tầng 2 (OmniParser/OCR ảnh màn hình) và tầng 3 (VLM): form mới dùng schema stub.
- Chưa gọi cloud LLM để bóc luật; bộ phân tích là regex trên mẫu câu. Văn bản thật cần LLM + cache.
- STT/diarization chưa có; voice chạy trên transcript.
- Chưa có màn hình admin đầy đủ; có nhật ký và hoàn tác ở tab Nhật ký / Quy định / form.
- Không có xác thực, không phải cấu hình production.

## Cấu trúc

```
prototype/
├── server.py                 # HTTP server (stdlib), API + phục vụ web/
├── contracts/                # registry + CONTRACTS.md (hợp đồng slot)
├── shared/                   # tiện ích thuần: chuẩn hóa tiếng Việt, fingerprint
├── services/                 # lõi: store, reminder, engine (điểm nối tích hợp)
├── features/                 # mỗi tính năng một folder, có README riêng
│   ├── pii_filter/           # lọc PII (SĐT, CCCD, tên)
│   ├── voice_input/          # giọng nói -> form; external_api.py gửi API ngoài SAU lọc PII (đang tắt)
│   ├── detect_form/          # detect form (DOM -> fingerprint -> Jaccard -> form mới)
│   └── policy_rules/         # policy (văn bản quy định -> rule, phiên bản vN)
├── data/
│   ├── form_registry/forms.json        # registry form (seed)
│   ├── patients_mock/patients.json     # bệnh nhân + sự kiện + bản ghi (giả)
│   └── regulations/qd_chamsoc_v1.txt, qd_chamsoc_v2.txt
├── web/                      # index.html, app.js, style.css
└── tests/test_scenario.py    # 10 test: kịch bản 13→15, hoàn tác, detect, voice, PII, cổng API ngoài, record
```
