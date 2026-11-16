# TEAM ACTION PLAN

| | |
|---|---|
| **Dự án** | Trợ lý AI nhắc việc theo quy định và nhập liệu bằng giọng nói |
| **Đơn vị** | Trung tâm Tiêu hóa – Gan mật – Tiết niệu |
| **Giai đoạn** | 10/11 – 19/11/2026 (hết tuần 3, trước đánh giá giữa kỳ 20/11) |
| **Mục tiêu** | Đạt đủ 6 tiêu chí vòng 1 để vào vòng 2 |
| **Cập nhật** | 12/11/2026 – Đợt 2–3 thay bằng *Kế hoạch chốt* (mục 2) |

---

## 1. Phân công

| Nhánh | Thành viên | Phạm vi |
|---|---|---|
| **Nhắc nhở điền form** | Nguyễn Anh Tuấn (trưởng nhóm), Trịnh Xuân Huy | Policy engine, nhắc việc theo quy định, cảnh báo đến hạn/quá hạn/thiếu trường |
| **Voice input to form** | Bùi Đức Thành, Mai Tiến Huy | Detect form dynamic + form registry, xử lý giọng nói, điền nháp |

> **Phần dùng chung:** form registry (schema trường) và rule store (bảng luật có version). Tuấn duyệt schema chung; nhắc việc dùng để kiểm tra thiếu trường, voice dùng làm khung trích xuất.

---

## 2. Kế hoạch theo đợt

### Đợt 1 (10–12/11): Nền móng và số đo

| Việc | Phụ trách | Đầu ra |
|---|---|---|
| Schema chung cho 2–3 phiếu (sinh tồn, chăm sóc, nguy cơ ngã, đánh giá ban đầu) | Tuấn chủ trì, cả team | JSON schema từng phiếu |
| Xin văn bản quy định từ QLCL, bóc thành bảng luật (hạn, trường bắt buộc, lịch sau mổ, lịch đánh giá đau) | Tuấn, Huy Trịnh | Bảng luật |
| Chọn STT tiếng Việt, thử phân biệt người nói, chốt kiến trúc local/cloud | Thành, Mai Huy | Kết quả thử + phương án kiến trúc có lý do |
| Đo hiện trạng: thời gian điền, số thao tác/click, tỷ lệ phiếu trễ hoặc thiếu, giờ ghi hồi cứu | Cả team, chia theo nhánh | Bảng số đo baseline |

📌 **Thứ 6, 13/11 (VinUni):** mang kế hoạch chốt này xin mentor góp ý, đặc biệt B4 (local/hybrid/cloud, bảo mật) và B5 (một hay nhiều model).

### Đợt 2–3 (12–19/11): KẾ HOẠCH CHỐT

*Thay thế phần Đợt 2–3 cũ. Phân công nhánh giữ nguyên.*

Team làm song song **2 sản phẩm**:

| Sản phẩm | Mục đích | Nguyên tắc |
|---|---|---|
| **A. Prototype** | Cho người dùng thật thấy và thử được | Làm gì cũng được, miễn bề ngoài giống hướng mình định làm. Dùng provider bên ngoài (cloud API). Không tối ưu, không lo hạ tầng |
| **B. Tài liệu kỹ thuật** | Chứng minh hướng đi có cơ sở, trả lời câu hỏi của hội đồng | Cấu trúc chuẩn. Mô tả kiến trúc đích (local/hybrid, bảo mật), so sánh model, hướng research |

> Prototype không cần chạy local. Tài liệu mới là nơi trả lời "chạy thật thì làm thế nào".

---

#### A. PROTOTYPE

**A1. Bốn module**

| Module | Làm gì | Yêu cầu bắt buộc |
|---|---|---|
| **1. Detect form** | Nhận diện form đang mở trên màn hình mock EMR và các trường của nó | **Dynamic:** không hardcode danh sách form. Gặp form mới thì nhận diện và đưa vào danh mục form |
| **2. Policy** | Đọc văn bản quy định, bóc thành luật (phiếu nào, ai làm, hạn bao lâu, trường bắt buộc) | **Dynamic:** đọc quy định từ file. Có quy định mới/sửa đổi thì nạp vào là luật cập nhật, không sửa code |
| **3. Nhắc việc** | Tính danh sách việc cần làm cho từng người, từng bệnh nhân; cảnh báo đến hạn, quá hạn, thiếu trường | Danh sách việc **tự tính lại** khi policy đổi hoặc khi có dữ liệu nhập mới |
| **4. Voice** | Nghe hội thoại → lọc thông tin cá nhân/ngoài lề → trích xuất → điền nháp vào form đang mở → người dùng xác nhận | Chỉ điền nháp. Chỉ dùng kịch bản đóng vai, dữ liệu giả |

**A2. Yêu cầu "dynamic" – kịch bản demo bắt buộc**

1. Hôm nay quy định yêu cầu bác sĩ làm **13 form** → màn nhắc việc hiện 13 việc.
2. Nạp một văn bản quy định mới (thêm 2 phiếu, hoặc đổi hạn từ 24h thành trong ngày).
3. Không sửa code, không khởi động lại → màn nhắc việc hiện **15 việc**, hạn được tính lại.
4. Hệ thống ghi lại phiên bản quy định nào đang áp dụng, từ ngày nào.

Tương tự cho detect form: mở một form chưa từng thấy → hệ thống nhận diện trường, ghép với luật trong policy.

**A3. Cấu trúc dùng chung (cả 4 module cắm vào)**

```
[Văn bản quy định] → Policy engine → Bảng luật (JSON, có version)
                                          ↓
[Màn hình EMR mock] → Form detection → Danh mục form + schema trường
                                          ↓
                         Reminder engine (luật × form × dữ liệu bệnh nhân)
                                          ↓
                         Giao diện nhắc việc (theo tài khoản bác sĩ / điều dưỡng)

[Âm thanh] → STT → Lọc PII → LLM trích xuất theo schema form đang mở → Điền nháp → Xác nhận
```

- **Form registry** và **rule store** là 2 nguồn dữ liệu trung tâm, mọi module đọc từ đây.
- Schema form dùng chung cho cả nhắc việc (kiểm tra thiếu trường) và voice (khung trích xuất).

**A4. Định nghĩa "xong" cho prototype (trước 17/11)**

- [ ] Chạy được kịch bản 13 → 15 form ở A2
- [ ] Nhận diện được ít nhất 3–4 phiếu chính (sinh tồn, chăm sóc, nguy cơ ngã, đánh giá ban đầu / phiếu điều trị)
- [ ] Nhắc việc hiện đúng theo vai trò (bác sĩ: bệnh án vào/ra viện; điều dưỡng: sinh tồn, chăm sóc, ngã, đau)
- [ ] Voice chạy end-to-end với kịch bản đóng vai, có bước xác nhận
- [ ] Phương án dự phòng voice: đến 16/11 chưa ổn thì demo bằng bản thu sẵn + điền nháp

---

#### B. TÀI LIỆU KỸ THUẬT

**B1. Mục lục chuẩn**

1. **Tóm tắt** (1 trang: bài toán, giải pháp, kết quả, đề xuất)
2. **Bối cảnh và nhu cầu** – minh chứng: khảo sát điều dưỡng 09/11, phỏng vấn bác sĩ, số đo baseline 10/11
3. **Yêu cầu**
   - Chức năng: 4 module
   - Phi chức năng: dynamic theo quy định, độ trễ, độ chính xác, bảo mật, không thêm app mới, tích hợp không cần sửa EMR
4. **Kiến trúc tổng thể** – sơ đồ thành phần, luồng dữ liệu, 2 chế độ (tích hợp qua cổng / chạy độc lập tự nhận diện form)
5. **Thiết kế từng module** – input/output, cách xử lý dynamic, cách cập nhật policy, version luật
6. **So sánh và lựa chọn model** (B2)
7. **Tối ưu hóa** (B3)
8. **Phương án triển khai: local / hybrid / cloud và bảo mật** (B4)
9. **Một model hay nhiều model** (B5)
10. **Đánh giá** – chỉ số, cách đo, kết quả thử nghiệm người dùng
11. **Rủi ro, an toàn người bệnh, pháp lý**
12. **Chi phí – lợi ích, lộ trình**
13. **Hướng research tiếp theo** (B6)
14. Phụ lục: schema form, bảng luật mẫu, kịch bản thử

**B2. So sánh model**

Làm **theo từng tác vụ**, không so sánh chung chung. Mỗi tác vụ một bảng:

| Tác vụ | Nhóm ứng viên cần so sánh |
|---|---|
| STT tiếng Việt + phân biệt người nói | Model mở chạy local (họ Whisper, các bản fine-tune tiếng Việt) vs API cloud trong và ngoài nước |
| Nhận diện form trên màn hình | OCR + luật vs model thị giác (vision-language) local vs cloud |
| Bóc quy định thành luật | LLM lớn cloud vs LLM mở cỡ nhỏ/vừa chạy local |
| Trích xuất hội thoại → trường form | Như trên, thêm tiêu chí ra đúng JSON schema |

Tiêu chí cố định cho mọi bảng: độ chính xác tiếng Việt (có số đo), độ trễ, chi phí/lượt hoặc phần cứng cần, chạy local được không, giấy phép, dữ liệu có bị giữ lại không.

> Phiên bản model thay đổi nhanh: chốt danh sách ứng viên mới nhất tại thời điểm viết, ghi rõ ngày kiểm tra. Số liệu nào tự đo thì ghi rõ bộ test.

**B3. Tối ưu hóa**

- Lượng tử hóa (quantization) để chạy local trên máy hiện có
- Ép đầu ra theo JSON schema (structured output / constrained decoding) để giảm lỗi định dạng
- Policy: dùng truy xuất văn bản (RAG) + bóc luật một lần, lưu cache; không fine-tune theo từng lần đổi quy định
- Cache kết quả nhận diện form (form đã biết thì không gọi model lại)
- Model nhỏ làm việc đơn giản (phân loại, định tuyến), model lớn chỉ gọi khi cần
- Đo trước/sau từng tối ưu: độ trễ, chi phí, độ chính xác

**B4. Local / hybrid / cloud và bảo mật**

**So sánh 3 phương án:** local hoàn toàn, hybrid, cloud hoàn toàn – theo bảo mật, chi phí, phần cứng, độ trễ, độ chính xác, vận hành.

**Luồng hybrid đề xuất cần mô tả rõ:**

1. **Tại máy local:** STT, phát hiện và lọc PII (tên, số điện thoại, địa chỉ, mã bệnh nhân, CCCD…), thay bằng mã giả; bảng ánh xạ mã giả chỉ lưu local.
2. **Phân loại dữ liệu:** loại nào được phép lên cloud, loại nào không bao giờ rời máy.
3. **Lên cloud:** chỉ dữ liệu đã ẩn danh, cho tác vụ nặng (trích xuất phức tạp, bóc quy định).
4. **Trả về local:** ghép lại thông tin thật từ bảng ánh xạ, điền nháp.

**Bảo mật cloud:** mã hóa khi truyền và khi lưu, thỏa thuận không lưu/không dùng dữ liệu để huấn luyện, vùng lưu trữ dữ liệu, phân quyền và nhật ký truy cập, đánh giá theo quy định bảo vệ dữ liệu cá nhân hiện hành của Việt Nam (dữ liệu sức khỏe là dữ liệu nhạy cảm – cần kiểm tra văn bản đang có hiệu lực).

**B5. Một model hay nhiều model**

Trình bày cả hai, có bảng so sánh và thử nghiệm nhỏ nếu kịp:

| Tiêu chí | 1 model đa năng | Tách model riêng |
|---|---|---|
| Đơn giản vận hành | Cao | Thấp hơn, cần điều phối |
| Chất lượng từng tác vụ | Có thể kém ở tác vụ chuyên biệt | Tối ưu từng tác vụ |
| Chạy local | Cần model lớn, máy mạnh | Nhiều model nhỏ, dễ chạy hơn |
| Thay thế, nâng cấp | Đổi là ảnh hưởng tất cả | Đổi từng phần |
| Chi phí | Gọi model lớn cho cả việc đơn giản | Việc đơn giản dùng model rẻ |

Gợi ý hướng phân tích: âm thanh (STT) và hình ảnh (nhận diện form) khác dạng dữ liệu nên thường tách riêng; phần hiểu văn bản (bóc quy định, trích xuất, suy luận nhắc việc) có thể dùng chung một LLM. Kết luận cuối dựa trên số đo của team.

**B6. Hướng research**

- Độ chính xác STT với giọng vùng miền, nhiễu buồng bệnh, thuật ngữ y khoa
- Lọc PII tiếng Việt trong hội thoại y khoa
- Nhận diện form trên ứng dụng desktop không có API (cho OH sau này)
- Quản lý version quy định và xung đột giữa các văn bản
- Liên kết phiếu (sinh tồn bất thường → phiếu chăm sóc) theo góp ý QLCL
- Biểu đồ chỉ số cho bác sĩ nội khoa (nhu cầu đã ghi nhận 10/11)

---

#### C. PHÂN CÔNG VÀ MỐC (12–19/11)

| Việc | Phụ trách | Hạn |
|---|---|---|
| Policy engine + nhắc việc + kịch bản 13 → 15 form | Tuấn, Huy Trịnh | 16/11 |
| Detect form dynamic + form registry | Thành, Mai Huy (Tuấn duyệt schema chung) | 15/11 |
| Voice end-to-end | Thành, Mai Huy | 16/11 |
| Tài liệu: mục 5 nhánh mình + B2 tác vụ của mình | Mỗi nhánh | 18/11 |
| Tài liệu: B4, B5 | Thành, Mai Huy viết; cả team review | 18/11 |
| Tài liệu: mục 1–4, 10–13, ghép bản cuối | Tuấn | 19/11 |
| Thử với 3–5 điều dưỡng/bác sĩ, xin xác nhận + endorse | Cả team, Tuấn đầu mối | 17–19/11 |

---

## 3. Đối chiếu tiêu chí vòng 1

| # | Tiêu chí | Hoạt động đáp ứng |
|---|---|---|
| 1 | Nhu cầu được xác thực | Khảo sát điều dưỡng 09/11, phỏng vấn bác sĩ 02/11, số đo baseline; tài liệu mục 2 |
| 2 | Xác nhận của trưởng khoa / điều dưỡng trưởng | Thử người dùng + xin xác nhận 17–19/11 |
| 3 | An toàn người bệnh, đạo đức | Tài liệu mục 11; voice chỉ điền nháp, chỉ dùng kịch bản đóng vai |
| 4 | Luồng dữ liệu rõ ràng, dữ liệu ẩn danh | Tài liệu mục 4 và B4 (luồng hybrid, lọc PII), mock data |
| 5 | Demo prototype được endorse | Prototype A (kịch bản 13 → 15 form, voice) + thử người dùng |
| 6 | Hồ sơ đầy đủ, đúng hạn | Tài liệu kỹ thuật B, ghép bản cuối 19/11 |

---

## 4. Rủi ro và phương án dự phòng

| Rủi ro | Phương án |
|---|---|
| **Voice trễ tiến độ** | Nếu đến 16/11 pipeline chưa chạy đủ luồng, demo bằng bản thu sẵn + điền nháp để vẫn kịp xác thực người dùng. |
| **Thử nghiệm trên người** | Không thu âm bệnh nhân thật. Chỉ dùng kịch bản đóng vai với dữ liệu giả. |
| **Không có quyền truy cập EMR** | Mọi tích hợp mô phỏng bằng mock data. |
| **Tự động điền** | QLCL không muốn tự điền toàn bộ. Voice chỉ điền nháp, người dùng xác nhận trước khi lưu. Cần hỏi QLCL sớm. |
| **Prototype dùng cloud API** | Chỉ dùng dữ liệu giả; kiến trúc local/hybrid được mô tả trong tài liệu (B4), không phải trong prototype. |

---

## 5. Câu hỏi cần làm rõ

- [ ] **IT viện:** đọc/ghi EMR qua API, database hay chỉ màn hình?
- [ ] **QLCL:** văn bản quy định chính thức về thời hạn và trường bắt buộc của từng phiếu.
- [ ] **QLCL:** voice điền nháp + người dùng xác nhận có được chấp nhận không?
- [ ] **Mentor (13/11):** góp ý B4 (local/hybrid/cloud, bảo mật) và B5 (một hay nhiều model).
