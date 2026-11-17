# Trợ lý AI nhắc việc theo quy định và nhập liệu bằng giọng nói

Điều dưỡng và bác sĩ không còn phải tự nhớ phiếu nào đến hạn, và không phải ghi giấy rồi nhập lại. **Quyết định cuối cùng luôn thuộc về người dùng.**

Team: Nguyễn Anh Tuấn (trưởng nhóm), Bùi Đức Thành, Mai Tiến Huy, Trịnh Xuân Huy.

---

## Đọc theo thứ tự nào

| Bước | File | Đọc để biết |
|---|---|---|
| 1 | [docs/TEAM_VISION.md](docs/TEAM_VISION.md) | Vì sao làm, cho ai, thành công là gì |
| 2 | [docs/EVIDENCE_NHAC_VIEC_VOICE.md](docs/EVIDENCE_NHAC_VIEC_VOICE.md) | Bằng chứng từ khảo sát, quan sát, đo thời gian tại khoa |
| 3 | [docs/TEAM_ACTION_PLAN.md](docs/TEAM_ACTION_PLAN.md) | Ai làm gì, theo đợt nào, hạn khi nào, đang rủi ro gì |
| 4 | [docs/DETECT_FORM_POLICY_ENGINE.md](docs/DETECT_FORM_POLICY_ENGINE.md) | Thiết kế kỹ thuật chi tiết: detect form, policy engine, rule DSL |
| 5 | [prototype/README.md](prototype/README.md) | Cách chạy prototype và kịch bản demo |

Nếu chỉ có 10 phút: đọc `TEAM_VISION.md` mục 1–3, rồi chạy prototype.

---

## Cấu trúc thư mục

```
HospitalAI/
├── README.md                  # file này: hướng dẫn chung
├── docs/                      # tài liệu: tầm nhìn, bằng chứng, kế hoạch, thiết kế
│   ├── TEAM_VISION.md
│   ├── EVIDENCE_NHAC_VIEC_VOICE.md
│   ├── TEAM_ACTION_PLAN.md
│   └── DETECT_FORM_POLICY_ENGINE.md
└── prototype/                 # mã nguồn prototype (Python thuần, không cần cài thư viện)
    ├── README.md              # cách chạy và kịch bản demo
    ├── server.py              # HTTP server + API
    ├── contracts/             # registry + CONTRACTS.md (hợp đồng giữa tính năng và lõi)
    ├── shared/                # tiện ích thuần dùng chung (chuẩn hóa, fingerprint)
    ├── services/              # lõi: store, reminder, engine (điểm nối tích hợp duy nhất)
    ├── features/              # mỗi tính năng một folder: code, README, test riêng
    │   ├── pii_filter/        # lọc PII
    │   ├── voice_input/       # giọng nói -> form; external_api.py gửi API ngoài sau lọc PII
    │   ├── detect_form/       # detect form
    │   └── policy_rules/      # policy: văn bản quy định -> rule
    ├── data/                  # dữ liệu giả: form registry, bệnh nhân, quy định mẫu
    ├── web/                   # giao diện (HTML/JS/CSS)
    └── tests/                 # test kịch bản
```

Quy ước đặt file:
- **Tài liệu** (`.md` mô tả ý tưởng, kế hoạch, thiết kế) để trong `docs/`.
- **Mã nguồn** để trong `prototype/`. Mỗi tính năng có một folder trong `features/`, kèm README ngắn.
- **Lõi dùng chung** (lưu trữ, tiện ích, nhắc việc) để trong `prototype/services/`.

---

## Chạy prototype

```bash
cd prototype
python server.py          # http://127.0.0.1:8765
python tests/test_scenario.py
```

Chỉ dùng dữ liệu giả. Không đưa dữ liệu bệnh nhân thật vào repo.

---

## Chia việc cho 4 người

Mỗi tính năng là một folder độc lập: code, README, test riêng. Chạy được và test được mà không cần tính năng khác. Khi tích hợp, chỉ nối vào `prototype/services/engine.py` theo [contracts/CONTRACTS.md](prototype/contracts/CONTRACTS.md). Nếu chưa nối, hệ thống dùng bản mặc định của prototype.

| Folder | Nội dung | Phân công (đề xuất, team chốt) |
|---|---|---|
| `features/pii_filter/` | Lọc PII (slot `pii.mask`) | Trịnh Xuân Huy |
| `features/voice_input/` | Giọng nói → form, gửi API ngoài sau lọc PII (slot `voice.send`) | Mai Tiến Huy |
| `features/detect_form/` | Detect form (slot `form.detect`) | Bùi Đức Thành |
| `features/policy_rules/` | Policy → rule (slot `policy.ingest`) | Nguyễn Anh Tuấn |

Lõi `services/` (store, nhắc việc, engine) do cả team dùng chung. Thay đổi lõi cần báo nhóm.

Chạy test từng tính năng (không cần tính năng khác):

```bash
cd prototype
python features/pii_filter/test_pii.py
python features/voice_input/test_voice.py
python features/detect_form/test_detect_form.py
python features/policy_rules/test_policy.py
python tests/test_isolation.py     # kiểm tra không phụ thuộc chéo
python tests/test_scenario.py      # kịch bản đầy đủ qua lõi
```

## Quy ước khi làm việc

- Tài liệu viết bằng tiếng Việt. Tên file giữ nguyên dạng hiện tại (chữ hoa, gạch dưới).
- Khi đổi thiết kế, cập nhật `docs/DETECT_FORM_POLICY_ENGINE.md` và README của folder liên quan trong cùng một thay đổi.
- Không commit thông tin định danh, khóa API hay dữ liệu bệnh nhân thật.
- Trạng thái công việc theo đợt xem ở `docs/TEAM_ACTION_PLAN.md`, không ghi lại ở nơi khác.
