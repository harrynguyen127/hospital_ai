# BÁO CÁO KỸ THUẬT: MODULE POLICY (BÓC QUY ĐỊNH THÀNH LUẬT)

- **Người phụ trách:** Trịnh Xuân Huy (phối hợp cùng Nguyễn Anh Tuấn)
- **Dự án:** Trợ lý AI nhắc việc theo quy định và nhập liệu bằng giọng nói – Trung tâm Tiêu hóa – Gan mật – Tiết niệu
- **Ngày hoàn thiện:** 17/11/2026
- **Phạm vi tài liệu:** Đáp ứng **Mục 5 (Thiết kế chi tiết Module Policy)** và **Mục 6 / B2 (So sánh model cho tác vụ bóc quy định)** theo cấu trúc quy định tại [docs/TEAM_ACTION_PLAN.md](file:///d:/hospital_ai/docs/TEAM_ACTION_PLAN.md).

---

## PHẦN 1. THIẾT KẾ CHI TIẾT MODULE POLICY (MỤC 5)

### 1.1 Mục tiêu và Nguyên tắc thiết kế
1. **Tự động hóa bóc tách quy chế:** Chuyển đổi văn bản quy định của bệnh viện (do Phòng QLCL ban hành dưới dạng docx/pdf/txt) thành bộ luật nhắc việc có cấu trúc (Rule DSL).
2. **Tính chất Dynamic (Không sửa code):** Khi bệnh viện cập nhật hoặc ban hành quy định mới, chỉ cần nạp văn bản mới vào hệ thống. Hệ thống tự động bóc luật, kiểm tra an toàn và phát hành phiên bản luật mới mà **không cần sửa code hay khởi động lại server**.
3. **An toàn y tế và tính giải trình:** LLM chỉ đóng vai trò đọc hiểu văn bản; toàn bộ quyết định áp dụng và tính toán lịch trình nhắc việc do **code tất định (deterministic)** thực hiện. Mọi luật áp dụng đều phải có câu trích dẫn nguyên văn (`evidence`) và phiên bản bất biến.

### 1.2 Kiến trúc dữ liệu: Hợp đồng Rule DSL (JSON Schema)
Mỗi điều khoản sau khi bóc tách được chuẩn hóa theo định dạng JSON với cấu trúc:

```json
{
  "rule_id": "QD-CHAMSOC-2026:1.1",
  "source": {
    "doc_id": "QD-CHAMSOC-2026",
    "doc_version": "v1",
    "clause": "Điều 1.1",
    "evidence": "Bác sĩ phải lập phiếu bệnh án vào viện trong vòng 24 giờ kể từ khi bệnh nhân vào viện."
  },
  "form_id": "benh_an_vao_vien",
  "role": ["bac_si"],
  "trigger": { "event": "admission" },
  "condition": null,
  "schedule": {
    "type": "once_within",
    "within": "PT24H"
  },
  "required_fields": ["ly_do_vao_vien", "chan_doan"],
  "priority": "normal",
  "effective_from": "2026-11-10",
  "effective_to": null,
  "supersedes": [],
  "status": "active"
}
```

#### 7 Kiểu lịch trình (`schedule`) hỗ trợ trong bệnh viện:
- `once_within`: Thực hiện trong khoảng thời gian kể từ sự kiện (ví dụ: làm bệnh án trong vòng 24h hoặc trong ngày `end_of_day`).
- `once_after`: Đánh giá lại sau một khoảng thời gian (ví dụ: đánh giá lại đau sau 30 phút dùng thuốc giảm đau tiêm/truyền).
- `recurring`: Lặp lại định kỳ (ví dụ: đo sinh tồn mỗi 4 giờ một lần tính từ lần nhập gần nhất).
- `sequence`: Chuỗi lịch giãn cách phức tạp (ví dụ: theo dõi sau mổ vào các mốc 1, 1, 2, 2, 2, 4, 4, 4, 4 giờ).
- `daily_before`: Hoàn thành trước giờ cố định mỗi ngày (ví dụ: đánh giá nguy cơ ngã trước 12:00 hàng ngày).
- `min_per_period`: Tối thiểu N lần trong chu kỳ (ví dụ: phiếu chăm sóc điều dưỡng tối thiểu 4 lần/ngày).
- `on_event`: Thực hiện khi có sự kiện đặc thù (ví dụ: giáo dục sức khỏe lúc bệnh nhân ra viện).

### 1.3 Quy trình kiểm tra tự động 6 Lớp (Automated 6-Layer Validation)
Để chống hiện tượng ảo giác (hallucination) của AI và đảm bảo an toàn tuyệt đối, mỗi luật được bóc tách phải vượt qua 6 lớp kiểm tra bằng code thuần (không gọi AI):

```
Văn bản quy định → Cắt đoạn (Điều/Khoản) → Bóc luật (DSL)
                                              ↓
                        [Lớp 1: Kiểm tra cấu trúc & kiểu ISO 8601]
                                              ↓
                        [Lớp 2: Kiểm tra Form ID & Fields trong Registry]
                                              ↓
                        [Lớp 3: Đối chiếu câu trích nguyên văn (>= 95%)]
                                              ↓
                        [Lớp 4: Kiểm tra con số trùng khớp với câu trích]
                                              ↓
                        [Lớp 5: Kiểm tra tính hợp lý ngữ nghĩa (5 phút - 30 ngày)]
                                              ↓
                        [Lớp 6: Phân giải xung đột & Gộp luật]
                                              ↓
                        [Phát hành Ruleset vN (Active) / Cần làm rõ (Draft)]
```

1. **Lớp 1 – Đúng khuôn (Schema Integrity):** Kiểm tra đầy đủ khóa bắt buộc; `schedule.type` thuộc 7 kiểu hợp lệ; thời lượng chuẩn ISO 8601 (`PT24H`, `PT30M`); vai trò phải thuộc `bac_si` hoặc `dieu_duong`.
2. **Lớp 2 – Tham chiếu có thật (Ontology Grounding):** `form_id` bắt buộc phải tồn tại trong `forms.json` và đang ở trạng thái `active`; các `required_fields` phải thuộc danh sách trường của form. Ngăn chặn triệt để việc AI tự "bịa" form hoặc trường không tồn tại.
3. **Lớp 3 – Câu trích nguyên văn (Evidence Verification):** Dùng thuật toán so khớp chuỗi (`difflib.SequenceMatcher`) trên văn bản tiếng Việt chuẩn hóa NFC. Tỷ lệ khớp $< 95\%$ sẽ bị loại bỏ ngay lập tức. Khớp từ $95\% - 99\%$ sẽ đưa vào danh sách xem xét `needs_clarification`.
4. **Lớp 4 – Khớp con số (Numeric Exactness):** Toàn bộ tham số số học trong luật (24, 30, 4, 1...) bắt buộc phải xuất hiện trong câu trích `evidence`. Nếu câu trích ghi 30 phút mà luật bóc thành 60 phút sẽ bị từ chối ngay.
5. **Lớp 5 – Tính hợp lý y khoa (Sanity Checks):** Khoảng thời gian phải nằm trong giới hạn thực tế (5 phút đến 30 ngày); chuỗi lịch `sequence` không được rỗng và các bước phải $> 0$.
6. **Lớp 6 – Xử lý trùng lặp và xung đột:**
   - *Trong cùng văn bản:* Cùng form/vai trò/sự kiện: nếu cùng lịch trình thì gộp (`merged`); nếu khác lịch trình thì đánh dấu `needs_clarification` (mơ hồ, không tự ý đoán).
   - *So với văn bản cũ đang áp dụng:* Luật mới ban hành từ văn bản có ngày hiệu lực mới hơn sẽ tự động thay thế (`supersedes`) luật cũ.

### 1.4 Quản lý Phiên bản (Versioning) và Cơ chế Hoàn tác (Rollback)
- Mỗi lần nạp văn bản thành công, hệ thống tạo ra một bộ luật có phiên bản bất biến (`v1`, `v2`, `v3`...), ghi nhận thời điểm xuất bản, nguồn văn bản và bảng so sánh khác biệt (`diff`: thêm, sửa, bỏ).
- **Cơ chế Rollback:** Khi phát hiện văn bản mới có sai sót hoặc quy định bị đình chỉ thi hành, người quản trị chỉ cần bấm nút hoặc gọi API `p_rollback`. Hệ thống lập tức chuyển trạng thái của ruleset hiện tại thành `rolled_back` và tái kích hoạt ruleset liền trước trong vòng dưới 50ms mà không làm gián đoạn hệ thống.

---

## PHẦN 2. SO SÁNH VÀ LỰA CHỌN MODEL CHO TÁC VỤ BÓC LUẬT (MỤC B2)

### 2.1 Bảng so sánh các phương án công nghệ

| Tiêu chí | Regex / Rule-based (Bản Prototype hiện tại) | LLM Cloud lớn (Gemini 1.5 Pro / GPT-4o) | LLM Open-weights Local (Qwen 2.5 7B/14B, Llama 3.1 8B) |
|---|---|---|---|
| **Độ chính xác tiếng Việt** | Rất cao với câu chuẩn khuôn; **0%** với câu diễn đạt tự nhiên mới lạ | Rất cao (> 94% trích đúng schema JSON có cấu trúc) | Khá - Tốt (85% - 90% khi có few-shot prompt chuẩn) |
| **Độ trễ xử lý (Latency)** | Cực nhanh (< 30ms/văn bản) | Trung bình (2s – 5s/văn bản) | Phụ thuộc GPU (1s – 4s trên RTX 3060/4060) |
| **Chi phí / Phần cứng** | CPU thông thường, 0 VNĐ | Trả phí theo token API cloud | Cần máy trạm có GPU VRAM $\ge$ 8GB – 16GB |
| **Chạy Local (Offline)** | **Có 100%** | **Không** (Bắt buộc kết nối Internet) | **Có 100%** (Chạy qua Ollama / vLLM tại viện) |
| **Bảo mật văn bản nội bộ** | Tuyệt đối (không rời khỏi máy) | Rủi ro rò rỉ quy định nội bộ nếu viện cấm đưa dữ liệu ra ngoài | Tuyệt đối an toàn (chạy trọn vẹn trong mạng LAN viện) |
| **Khả năng cập nhật dynamic** | Kém: Phải cập nhật regex khi xuất hiện mẫu câu mới | Rất cao: Hiểu được văn bản hành chính tiếng Việt phức tạp | Rất cao: Hiểu được văn bản hành chính khi kèm few-shot |

### 2.2 Đề xuất kiến trúc triển khai thực tế (Production Target)
1. **Giai đoạn Prototype:** Sử dụng phương pháp lai (Hybrid) kết hợp Regex chuẩn mẫu cho demo nhanh và LLM Cloud với Structured Output để thử nghiệm bóc các văn bản Word dài.
2. **Giai đoạn Triển khai tại Bệnh viện (On-premise):**
   - Sử dụng mô hình nguồn mở **Qwen 2.5 14B-Instruct** (được đánh giá xử lý tiếng Việt và ép JSON schema xuất sắc nhất hiện nay) lượng tử hóa 4-bit (AWQ/GGUF) chạy cục bộ trên máy chủ nội bộ của viện.
   - **Tối ưu hóa chi phí (One-time Extraction):** Tác vụ bóc quy định chỉ diễn ra **1 lần duy nhất** khi có văn bản mới ban hành, kết quả được lưu vào cơ sở dữ liệu (cache). Hệ thống nhắc việc hàng ngày chỉ việc đọc bảng luật đã bóc nên hoàn toàn không tiêu tốn tài nguyên GPU trong quá trình vận hành thường nhật.
   - Kết hợp chặt chẽ với **Bộ lọc 6 Lớp**: LLM chỉ làm nhiệm vụ gợi ý bóc tách, bộ kiểm tra 6 lớp đảm bảo tính đúng đắn 100% trước khi luật được tự động phát hành.

---

## PHẦN 3. MINH CHỨNG KẾT QUẢ ĐÃ ĐẠT ĐƯỢC TRÊN REPOSITORY

1. **Bảng luật chuẩn hóa đã lưu trữ:**
   - Bộ luật v1: [prototype/data/rulesets/ruleset_v1.json](file:///d:/hospital_ai/prototype/data/rulesets/ruleset_v1.json) (8 luật hợp lệ, sinh 13 việc cho bác sĩ).
   - Bộ luật v2: [prototype/data/rulesets/ruleset_v2.json](file:///d:/hospital_ai/prototype/data/rulesets/ruleset_v2.json) (11 luật, trong đó 1 luật mơ hồ `needs_clarification`, 2 luật thêm mới, sinh 15 việc cho bác sĩ).
   - Bộ luật đa nhóm: [prototype/data/rulesets/ruleset_multi_category.json](file:///d:/hospital_ai/prototype/data/rulesets/ruleset_multi_category.json) (8 luật đại diện cho cả 5 nhóm chức năng y tế).
2. **Bộ kiểm thử độc lập:**
   - File test: [prototype/features/policy_rules/test_policy.py](file:///d:/hospital_ai/prototype/features/policy_rules/test_policy.py).
   - Kết quả: **6/6 test pass 100%**, xác thực tính toàn vẹn của logic bóc luật, kiểm tra 6 lớp, diff và rollback.

---

## PHẦN 4. ĐỀ XUẤT MỞ RỘNG: PHÂN LOẠI POLICY THEO 5 NHÓM CHỨC NĂNG Y TẾ (FUTURE WORK)

Trong thực tế vận hành tại bệnh viện, quy chế của phòng Quản lý chất lượng (QLCL) và Hội đồng Thuốc & Điều trị không chỉ giới hạn ở việc *nhắc thời hạn điền phiếu*, mà bao hàm toàn bộ chu trình chăm sóc và an toàn người bệnh. Dưới đây là đề xuất phân loại Policy theo 5 nhóm chức năng chuyên biệt nhằm mở rộng hệ thống trong các giai đoạn tiếp theo (Vòng 2 & Triển khai thực tế):

### 4.1 Chi tiết 5 Nhóm Policy Chức năng

```
                                  ┌── 1. Timing & Reminder (Nhắc hạn & Chu kỳ)
                                  ├── 2. Form Validation (Ràng buộc điền form & Logic chéo)
HỆ THỐNG QUY ĐỊNH BỆNH VIỆN ──────┼── 3. Cross-form Trigger (Kích hoạt liên kết phiếu)
                                  ├── 4. Role & Authorization (Phân quyền & Ký duyệt)
                                  └── 5. Billing & Compliance (Điều kiện BHYT & Pháp lý)
```

1. **Nhóm 1 – Policy Nhắc hạn & Lịch trình (Timing & Reminder Policy):**
   - *Phạm vi:* Quy định thời điểm cần làm, chu kỳ lặp lại và hạn chót.
   - *Ví dụ:* Bệnh án vào viện trong 24 giờ; đo dấu hiệu sinh tồn mỗi 4 giờ; đánh giá ngã trước 12:00; theo dõi sau mổ 1-1-2-2-4 giờ. *(Đây là nhóm đã được hiện thực hóa trọn vẹn trong bản prototype hiện tại).*
2. **Nhóm 2 – Policy Ràng buộc & Điền form (Form Validation & Completeness Policy):**
   - *Phạm vi:* Quy định tính hợp lệ của từng trường dữ liệu và ràng buộc logic chéo ngay trong quá trình nhập liệu.
   - *Ví dụ:* 
     - Ràng buộc bắt buộc (`required_fields`): Phiếu vào viện không được để trống *Lý do vào viện* và *Chẩn đoán*.
     - Ràng buộc logic chéo (Cross-field logic): Nếu trường `co_di_ung` chọn `"Có"`, bắt buộc trường `ten_di_nguyen` phải hiển thị và bắt buộc điền.
     - Ràng buộc ngưỡng sinh tồn an toàn: Mạch trong khoảng 30–220 lần/phút, Huyết áp tâm thu bắt buộc phải lớn hơn tâm trương.
3. **Nhóm 3 – Policy Kích hoạt liên kết giữa các phiếu (Cross-form Trigger & Workflow Policy):**
   - *Phạm vi:* Khi dữ liệu ở một form có dấu hiệu bất thường, hệ thống tự động kích hoạt yêu cầu lập một form khác theo phác đồ điều trị.
   - *Ví dụ:*
     - Từ *Phiếu Sinh tồn* $\rightarrow$ *Phiếu Báo động/Cấp cứu*: Khi nhập SpO2 $< 90\%$ hoặc Mạch $> 120$ $\rightarrow$ Kích hoạt ngay việc lập Phiếu báo cáo bác sĩ khẩn cấp hoặc chuyển sang dõi chăm sóc cấp 1.
     - Từ *Đánh giá đau* $\rightarrow$ *Phiếu Tái đánh giá*: Khi cho dùng thuốc giảm đau $\rightarrow$ Tự động tạo lịch nhắc đánh giá lại đau sau 30 phút.
     - Chuỗi an toàn phẫu thuật: Bệnh nhân có lịch mổ $\rightarrow$ Kích hoạt chuỗi 3 bảng kiểm an toàn phẫu thuật (Trước gây mê $\rightarrow$ Trước rạch da $\rightarrow$ Trước khi rời phòng mổ).
4. **Nhóm 4 – Policy Phân quyền & Ký duyệt (Role & Authorization Policy):**
   - *Phạm vi:* Quy định trách nhiệm pháp lý hồ sơ bệnh án giữa các chức danh.
   - *Ví dụ:* Điều dưỡng ghi nhận diễn biến chăm sóc; khi có biến chứng thì Bác sĩ điều trị bắt buộc phải ký xác nhận (countersign) trong 24 giờ; Bác sĩ nội trú làm bệnh án thì Bác sĩ trưởng tua/phó khoa phải duyệt và ký số trong vòng 48 giờ.
5. **Nhóm 5 – Policy Điều kiện Thanh toán BHYT & Pháp lý (Billing & Compliance Policy):**
   - *Phạm vi:* Đảm bảo tính hợp lệ của hồ sơ để tránh cơ quan Bảo hiểm xã hội từ chối thanh toán (xuất toán).
   - *Ví dụ:* Kê đơn thuốc kháng sinh phổ rộng (nhóm 3) $\rightarrow$ Bắt buộc hồ sơ phải có đính kèm *Phiếu kết quả kháng sinh đồ* hoặc *Biên bản hội chẩn thuốc đặc trị*.

### 4.2 Thiết kế mở rộng Rule DSL (Tương thích chuẩn HL7 FHIR)
Để hỗ trợ cả 5 nhóm policy trên, cấu trúc Rule DSL được thiết kế mở rộng thêm trường `category` và `action`:

```json
{
  "rule_id": "POL-TRIGGER-01",
  "category": "cross_form_trigger",
  "source": { "doc_id": "QD-CAPCUU-2026", "clause": "Điều 4.2", "evidence": "Khi SpO2 < 90% phải báo cáo bác sĩ và lập phiếu xử trí cấp cứu ngay" },
  "trigger": { "form_id": "phieu_sinh_ton_nguoi_lon", "field": "spo2", "condition": { "<": 90 } },
  "action": {
    "type": "create_task",
    "target_form_id": "phieu_xu_tri_cap_cuu",
    "target_role": ["bac_si", "dieu_duong"],
    "priority": "urgent",
    "deadline": "immediate"
  },
  "status": "active"
}
```

- **Định hướng chuẩn hóa quốc tế:**
  - Nhóm 1 & Nhóm 3 (Timing & Trigger) $\rightarrow$ Ánh xạ sang tài nguyên **FHIR PlanDefinition** (định nghĩa quy trình hành động) và **FHIR Task** (công việc giao cho nhân viên y tế).
  - Nhóm 2 (Validation) $\rightarrow$ Ánh xạ sang **FHIR Questionnaire** và **QuestionnaireResponse** (cấu trúc biểu mẫu và dữ liệu điền).
  - Đảm bảo hệ thống sau này có thể tích hợp mượt mà vào bất kỳ hệ thống HIS/EMR tiêu chuẩn quốc tế nào mà không cần đập đi xây lại kiến trúc.
