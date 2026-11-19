# 10 KỊCH BẢN TEST HAPPY CASE & SYNTHETIC OUTPUT (100% LOCAL)

Tài liệu này cung cấp **10 kịch bản Happy Case** phủ đủ **10 phiếu EMR** trong [forms.json](file:///d:/hospital_ai/prototype/data/form_registry/forms.json), chạy trên pipeline **100% Local**:

`Micro (.wav) / Transcript` → `VAD (RMS 30ms)` → `STT Local (vinai/PhoWhisper-small)` → `Che PII Local (pii.mask)` → `Trích xuất Local (voice.extract)` → `Điền nháp (ô màu tím)` → `Lưu bản ghi (/api/records)`

> **Điểm nổi bật cho đợt test:**
> - Toàn bộ **10/10 phiếu** trên hệ thống hiện đã có trường **`Tên bệnh nhân`** (`ten_benh_nhan`).
> - Mọi kịch bản đều chứa câu đọc tên bệnh nhân và/hoặc thông tin định danh (SĐT, CCCD) để bạn kiểm tra trực tiếp khả năng **che PII tự động** (`[TÊN]`, `[SĐT]`, `[CCCD]`) hiển thị trên ô nháp màu tím.
> - Kịch bản **1–8** áp dụng ngay với **Bộ luật v1** mặc định.
> - Kịch bản **9–10** áp dụng sau khi nạp **Bộ luật v2** (Quản trị quy định → chọn *QĐ chăm sóc – v2* → *Nạp & tự động áp dụng*).

---

## 3 Cách chạy test nhanh

### Cách 1: Chạy tự động bằng kịch bản mẫu trên Web (Khuyên dùng - Nhanh nhất)
1. Chạy server trong terminal: `python server.py`.
2. Mở trình duyệt `http://127.0.0.1:8765`.
3. Chọn đúng **Tài khoản** và **Bệnh nhân** theo kịch bản.
4. Nhấp vào tab phiếu cần test (ví dụ: *Phiếu chăm sóc*).
5. Mở tab **Giọng nói** bên phải → bấm **Bắt đầu nghe (kịch bản mẫu)**:
   - Hệ thống sẽ phát từng câu thoại, câu đọc tên bệnh nhân sẽ tự động gắn nhãn **Đã che định danh** và trường **Tên bệnh nhân** trên phiếu sẽ được điền nháp giá trị `[TÊN]`.
6. Bấm **Lưu bản ghi** để xác nhận lưu thành công (`missing_required: []`).

### Cách 2: Thử bằng Micro thật (Đọc trực tiếp)
1. Tại tab **Giọng nói** của phiếu đang mở, bấm **🎤 Ghi âm từ micro (thật)**.
2. Đọc to, rõ ràng đoạn thoại mẫu của kịch bản (đặc biệt là câu: *"Tên bệnh nhân là..."*).
3. Bấm **Dừng và xử lý** (hoặc đợi hết 60 giây): PhoWhisper local nhận diện âm thanh → Che PII → Trích xuất vào ô màu tím.
4. Đối chiếu với **Synthetic Output** và bấm **Lưu bản ghi**.

### Cách 3: Gửi qua API (Terminal PowerShell)
Gửi trực tiếp câu thoại vào endpoint `POST /api/voice`:
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8765/api/voice" -Method Post -ContentType "application/json" -Body '{"form_id":"phieu_cham_soc","text":"Tên bệnh nhân là Nguyễn Văn An. Ca trực là ca sáng, nội dung chăm sóc là hỗ trợ vệ sinh cá nhân. Người thực hiện là ĐD-MẪU-B."}'
```

---

## Kịch bản 1: Bảng theo dõi dấu hiệu sinh tồn cho người lớn (`phieu_sinh_ton_nguoi_lon`)

- **Bối cảnh:** Đo sinh tồn định kỳ, có che PII (Tên + SĐT) và đọc số bằng chữ tiếng Việt giống đầu ra PhoWhisper.
- **Tài khoản / Bệnh nhân:** Điều dưỡng (`dd_b`) / `BN-01` (Bộ luật `v1`)
- **Trường bắt buộc:** `mach`, `nhip_tho` (đều được điền đủ → `missing_required: []`)
- **Trường PII được che:** `ten_benh_nhan` → `[TÊN]`, số điện thoại → `[SĐT]`

### Kịch bản thoại đầu vào (Input)
> 1. "Tên bệnh nhân là Nguyễn Văn An, số điện thoại 0912345678."
> 2. "Tư thế đo là nằm, trạng thái lúc đo là đang nghỉ."
> 3. "Mạch tám tám, nhịp thở hai mươi, huyết áp một trăm hai mươi trên tám mươi."
> 4. "Nhiệt độ ba bảy phẩy hai, SpO2 98."
> 5. "Nhịp mạch khi bắt là đều, kiểu thở quan sát được là đều, hỗ trợ hô hấp lúc đo là khí phòng."
> 6. "Điểm cần bàn giao là tiếp tục theo dõi sinh tồn ca chiều."

### Synthetic Output (Pipeline Local – `POST /api/voice/audio`)
```json
{
  "ok": true,
  "mode": "local",
  "has_speech": true,
  "stt_backend": "phowhisper",
  "stt_error": null,
  "source": "local",
  "out_of_scope": false,
  "pii_masked": 2,
  "masked": "Tên bệnh nhân là [TÊN], số điện thoại [SĐT]. Tư thế đo là nằm, trạng thái lúc đo là đang nghỉ. Mạch tám tám, nhịp thở hai mươi, huyết áp một trăm hai mươi trên tám mươi. Nhiệt độ ba bảy phẩy hai, SpO2 98. Nhịp mạch khi bắt là đều, kiểu thở quan sát được là đều, hỗ trợ hô hấp lúc đo là khí phòng. Điểm cần bàn giao là tiếp tục theo dõi sinh tồn ca chiều.",
  "extracted": {
    "ten_benh_nhan": "[TÊN]",
    "tu_the_do": "Nằm",
    "trang_thai_do": "Đang nghỉ",
    "mach": 88,
    "nhip_tho": 20,
    "huyet_ap": "120/80",
    "nhiet_do": 37.2,
    "spo2": 98,
    "nhip_mach": "Đều",
    "kieu_tho": "Đều",
    "ho_tro_oxy": "Khí phòng",
    "ban_giao_do": "tiếp tục theo dõi sinh tồn ca chiều"
  },
  "save_preview": {
    "patient_id": "BN-01",
    "form_id": "phieu_sinh_ton_nguoi_lon",
    "source": "voice",
    "filled_count": 12,
    "missing_required": []
  }
}
```

---

## Kịch bản 2: Phiếu chăm sóc điều dưỡng (`phieu_cham_soc`)

- **Bối cảnh:** Ghi nhận chăm sóc điều dưỡng đầu ca sáng, đánh giá đáp ứng và bàn giao ca. Có che PII tên bệnh nhân.
- **Tài khoản / Bệnh nhân:** Điều dưỡng (`dd_b`) / `BN-01` (Bộ luật `v1`)
- **Trường bắt buộc:** `thuc_hien`, `nguoi_thuc_hien`
- **Trường PII được che:** `ten_benh_nhan` → `[TÊN]`

### Kịch bản thoại đầu vào (Input)
> 1. "Tên bệnh nhân là Nguyễn Văn An."
> 2. "Ca trực là ca sáng, mức hỗ trợ sinh hoạt là hỗ trợ một phần."
> 3. "Nội dung chăm sóc là hỗ trợ vệ sinh cá nhân và thay ga giường."
> 4. "Người thực hiện là ĐD-MẪU-B."
> 5. "Đáp ứng sau chăm sóc là người bệnh dễ chịu và nghỉ ngơi tốt."
> 6. "Mức đạt mục tiêu là đã đạt, mã người nhận bàn giao là ĐD-MẪU-C."

### Synthetic Output (Pipeline Local – `POST /api/voice/audio`)
```json
{
  "ok": true,
  "mode": "local",
  "has_speech": true,
  "stt_backend": "phowhisper",
  "stt_error": null,
  "source": "local",
  "out_of_scope": false,
  "pii_masked": 1,
  "masked": "Tên bệnh nhân là [TÊN]. Ca trực là ca sáng, mức hỗ trợ sinh hoạt là hỗ trợ một phần. Nội dung chăm sóc là hỗ trợ vệ sinh cá nhân và thay ga giường. Người thực hiện là ĐD-MẪU-B. Đáp ứng sau chăm sóc là người bệnh dễ chịu và nghỉ ngơi tốt. Mức đạt mục tiêu là đã đạt, mã người nhận bàn giao là ĐD-MẪU-C.",
  "extracted": {
    "ten_benh_nhan": "[TÊN]",
    "muc_doc_lap": "Hỗ trợ một phần",
    "thuc_hien": "hỗ trợ vệ sinh cá nhân và thay ga giường",
    "nguoi_thuc_hien": "đd-mẫu-b",
    "ca_truc": "Ca sáng",
    "dap_ung": "người bệnh dễ chịu và nghỉ ngơi tốt",
    "muc_dat": "Đã đạt",
    "nguoi_nhan_ca": "đd-mẫu-c"
  },
  "save_preview": {
    "patient_id": "BN-01",
    "form_id": "phieu_cham_soc",
    "source": "voice",
    "filled_count": 8,
    "missing_required": []
  }
}
```

---

## Kịch bản 3: Đánh giá nguy cơ ngã (`phieu_nguy_co_nga`)

- **Bối cảnh:** Đánh giá nguy cơ ngã đầu ca tại giường kèm biện pháp dự phòng an toàn. Có che PII tên bệnh nhân.
- **Tài khoản / Bệnh nhân:** Điều dưỡng (`dd_b`) / `BN-01` (Bộ luật `v1`)
- **Trường bắt buộc:** `diem_nga`, `ket_qua`
- **Trường PII được che:** `ten_benh_nhan` → `[TÊN]`

### Kịch bản thoại đầu vào (Input)
> 1. "Tên bệnh nhân là Nguyễn Văn An."
> 2. "Lý do đánh giá là đầu ca, tiền sử ngã theo lời kể là chưa ghi nhận."
> 3. "Dụng cụ trợ giúp đi lại là khung tập đi, khả năng chuyển tư thế là cần người dìu."
> 4. "Điểm nguy cơ ngã 25, kết quả là cần hỗ trợ khi di chuyển."
> 5. "Khả năng di chuyển là có người hỗ trợ."
> 6. "Biện pháp đã thực hiện là đặt chuông gọi trong tầm tay và nâng thanh chắn giường."
> 7. "Môi trường quanh giường là lối đi thông thoáng."

### Synthetic Output (Pipeline Local – `POST /api/voice/audio`)
```json
{
  "ok": true,
  "mode": "local",
  "has_speech": true,
  "stt_backend": "phowhisper",
  "stt_error": null,
  "source": "local",
  "out_of_scope": false,
  "pii_masked": 1,
  "masked": "Tên bệnh nhân là [TÊN]. Lý do đánh giá là đầu ca, tiền sử ngã theo lời kể là chưa ghi nhận. Dụng cụ trợ giúp đi lại là khung tập đi, khả năng chuyển tư thế là cần người dìu. Điểm nguy cơ ngã 25, kết quả là cần hỗ trợ khi di chuyển. Khả năng di chuyển là có người hỗ trợ. Biện pháp đã thực hiện là đặt chuông gọi trong tầm tay và nâng thanh chắn giường. Môi trường quanh giường là lối đi thông thoáng.",
  "extracted": {
    "ten_benh_nhan": "[TÊN]",
    "ly_do_danh_gia": "Đầu ca",
    "tien_su_nga": "Chưa ghi nhận",
    "dung_cu_di": "Khung tập đi",
    "chuyen_tu_the": "Cần người dìu",
    "diem_nga": 25,
    "ket_qua": "cần hỗ trợ khi di chuyển",
    "di_chuyen": "Có người hỗ trợ",
    "bien_phap": "đặt chuông gọi trong tầm tay và nâng thanh chắn giường",
    "moi_truong": "lối đi thông thoáng"
  },
  "save_preview": {
    "patient_id": "BN-01",
    "form_id": "phieu_nguy_co_nga",
    "source": "voice",
    "filled_count": 10,
    "missing_required": []
  }
}
```

---

## Kịch bản 4: Đánh giá đau (`phieu_danh_gia_dau`)

- **Bối cảnh:** Ghi nhận điểm đau sau mổ kèm thời điểm đánh giá (`datetime`), vị trí, tính chất và yếu tố tăng/giảm đau. Có che PII tên bệnh nhân.
- **Tài khoản / Bệnh nhân:** Điều dưỡng (`dd_b`) / `BN-03` (Bộ luật `v1`)
- **Trường bắt buộc:** `diem_dau`, `thoi_diem_danh_gia`
- **Trường PII được che:** `ten_benh_nhan` → `[TÊN]`

### Kịch bản thoại đầu vào (Input)
> 1. "Tên bệnh nhân là Phạm Thị Lan."
> 2. "Điểm đau 4, thời điểm đánh giá 2026-11-16 10:15."
> 3. "Vị trí đau là vùng quanh vết mổ, tính chất đau là âm ỉ."
> 4. "Người mô tả cơn đau là người bệnh, hướng lan của đau là khu trú tại chỗ."
> 5. "Hoàn cảnh đánh giá là khi nghỉ."
> 6. "Yếu tố làm đau tăng là ngồi dậy, yếu tố làm đau giảm là kê gối đỡ."
> 7. "Hỗ trợ đã thực hiện là hướng dẫn tư thế nằm giảm đau."

### Synthetic Output (Pipeline Local – `POST /api/voice/audio`)
```json
{
  "ok": true,
  "mode": "local",
  "has_speech": true,
  "stt_backend": "phowhisper",
  "stt_error": null,
  "source": "local",
  "out_of_scope": false,
  "pii_masked": 1,
  "masked": "Tên bệnh nhân là [TÊN]. Điểm đau 4, thời điểm đánh giá 2026-11-16 10:15. Vị trí đau là vùng quanh vết mổ, tính chất đau là âm ỉ. Người mô tả cơn đau là người bệnh, hướng lan của đau là khu trú tại chỗ. Hoàn cảnh đánh giá là khi nghỉ. Yếu tố làm đau tăng là ngồi dậy, yếu tố làm đau giảm là kê gối đỡ. Hỗ trợ đã thực hiện là hướng dẫn tư thế nằm giảm đau.",
  "extracted": {
    "ten_benh_nhan": "[TÊN]",
    "diem_dau": 4,
    "thoi_diem_danh_gia": "2026-11-16T10:15",
    "vi_tri_dau": "vùng quanh vết mổ",
    "tinh_chat_dau": "Âm ỉ",
    "nguon_danh_gia": "Người bệnh",
    "huong_lan": "Khu trú tại chỗ",
    "yeu_to_tang": "ngồi dậy",
    "yeu_to_giam": "kê gối đỡ",
    "hoan_canh": "Khi nghỉ",
    "ho_tro_da_lam": "hướng dẫn tư thế nằm giảm đau"
  },
  "save_preview": {
    "patient_id": "BN-03",
    "form_id": "phieu_danh_gia_dau",
    "source": "voice",
    "filled_count": 11,
    "missing_required": []
  }
}
```

---

## Kịch bản 5: Đánh giá ban đầu (`phieu_danh_gia_ban_dau`)

- **Bối cảnh:** Tiếp nhận bệnh nhân mới vào khoa, ghi dị ứng, thuốc đang dùng, nhu cầu sinh hoạt. Có che PII tên bệnh nhân + tên & SĐT người liên hệ (tổng 3 token PII).
- **Tài khoản / Bệnh nhân:** Điều dưỡng (`dd_b`) / `BN-02` (Bộ luật `v1`)
- **Trường bắt buộc:** `di_ung`, `nguoi_lien_he`
- **Trường PII được che:** `ten_benh_nhan` → `[TÊN]`, `nguoi_lien_he` → `[TÊN]`, số điện thoại → `[SĐT]`

### Kịch bản thoại đầu vào (Input)
> 1. "Tên bệnh nhân là Trần Thị Mai."
> 2. "Dị ứng là penicillin gây nổi mẩn, thuốc đang dùng là amlodipin 5 mg mỗi sáng."
> 3. "Tiền sử là tăng huyết áp 5 năm, khả năng tự chăm sóc là cần hỗ trợ một phần."
> 4. "Khả năng giao tiếp là trả lời rõ, ăn uống trong ngày là ăn như thường lệ, khả năng nuốt theo lời kể là nuốt được."
> 5. "Vận động khi vào khoa là đi có người dìu, dụng cụ mang theo là kính đọc sách."
> 6. "Người liên hệ là Trần Thị Bình, số điện thoại 0987654321, quan hệ với người bệnh là người thân."

### Synthetic Output (Pipeline Local – `POST /api/voice/audio`)
```json
{
  "ok": true,
  "mode": "local",
  "has_speech": true,
  "stt_backend": "phowhisper",
  "stt_error": null,
  "source": "local",
  "out_of_scope": false,
  "pii_masked": 3,
  "masked": "Tên bệnh nhân là [TÊN]. Dị ứng là penicillin gây nổi mẩn, thuốc đang dùng là amlodipin 5 mg mỗi sáng. Tiền sử là tăng huyết áp 5 năm, khả năng tự chăm sóc là cần hỗ trợ một phần. Khả năng giao tiếp là trả lời rõ, ăn uống trong ngày là ăn như thường lệ, khả năng nuốt theo lời kể là nuốt được. Vận động khi vào khoa là đi có người dìu, dụng cụ mang theo là kính đọc sách. Người liên hệ là [TÊN], số điện thoại [SĐT], quan hệ với người bệnh là người thân.",
  "extracted": {
    "ten_benh_nhan": "[TÊN]",
    "di_ung": "penicillin gây nổi mẩn",
    "thuoc_dang_dung": "amlodipin 5 mg mỗi sáng",
    "tien_su": "tăng huyết áp 5 năm",
    "tu_cham_soc": "Cần hỗ trợ một phần",
    "giao_tiep": "Trả lời rõ",
    "an_uong": "Ăn như thường lệ",
    "nuot": "Nuốt được",
    "van_dong": "Đi có người dìu",
    "dung_cu": "kính đọc sách",
    "nguoi_lien_he": "[TÊN]",
    "quan_he": "Người thân"
  },
  "save_preview": {
    "patient_id": "BN-02",
    "form_id": "phieu_danh_gia_ban_dau",
    "source": "voice",
    "filled_count": 12,
    "missing_required": []
  }
}
```

---

## Kịch bản 6: Bệnh án vào viện (`benh_an_vao_vien`)

- **Bối cảnh:** Bác sĩ hỏi bệnh và khám tiếp nhận, có che PII tên bệnh nhân & số CCCD 12 chữ số (tổng 2 token PII).
- **Tài khoản / Bệnh nhân:** Bác sĩ (`bs_a`) / `BN-02` (Bộ luật `v1`)
- **Trường bắt buộc:** `ly_do_vao_vien`, `chan_doan`
- **Trường PII được che:** `ten_benh_nhan` → `[TÊN]`, số CCCD → `[CCCD]`

### Kịch bản thoại đầu vào (Input)
> 1. "Tên bệnh nhân là Lê Văn Cường, số CCCD 001090123456."
> 2. "Nguồn cung cấp bệnh sử là người bệnh, cách vào khoa là tự đi, nguồn tiếp nhận là khoa khám bệnh."
> 3. "Lý do vào viện là đau bụng vùng thượng vị đã hai ngày."
> 4. "Bệnh sử là đau âm ỉ tăng sau ăn, triệu chứng đi kèm là buồn nôn nhẹ."
> 5. "Khám ban đầu là người bệnh tỉnh tiếp xúc tốt, khám bụng là bụng mềm ấn tức nhẹ thượng vị."
> 6. "Chẩn đoán là theo dõi viêm dạ dày cấp, vấn đề cần theo dõi là diễn biến đau bụng và ăn uống."

### Synthetic Output (Pipeline Local – `POST /api/voice/audio`)
```json
{
  "ok": true,
  "mode": "local",
  "has_speech": true,
  "stt_backend": "phowhisper",
  "stt_error": null,
  "source": "local",
  "out_of_scope": false,
  "pii_masked": 2,
  "masked": "Tên bệnh nhân là [TÊN], số CCCD [CCCD]. Nguồn cung cấp bệnh sử là người bệnh, cách vào khoa là tự đi, nguồn tiếp nhận là khoa khám bệnh. Lý do vào viện là đau bụng vùng thượng vị đã hai ngày. Bệnh sử là đau âm ỉ tăng sau ăn, triệu chứng đi kèm là buồn nôn nhẹ. Khám ban đầu là người bệnh tỉnh tiếp xúc tốt, khám bụng là bụng mềm ấn tức nhẹ thượng vị. Chẩn đoán là theo dõi viêm dạ dày cấp, vấn đề cần theo dõi là diễn biến đau bụng và ăn uống.",
  "extracted": {
    "ten_benh_nhan": "[TÊN]",
    "nguoi_cung_cap": "Người bệnh",
    "cach_vao_khoa": "Tự đi",
    "ly_do_vao_vien": "đau bụng vùng thượng vị đã hai ngày",
    "benh_su": "đau âm ỉ tăng sau ăn",
    "nguon_tiep_nhan": "Khoa khám bệnh",
    "trieu_chung_kem": "buồn nôn nhẹ",
    "chan_doan": "theo dõi viêm dạ dày cấp",
    "kham_ban_dau": "người bệnh tỉnh tiếp xúc tốt",
    "kham_bung": "bụng mềm ấn tức nhẹ thượng vị",
    "van_de_theo_doi": "diễn biến đau bụng và ăn uống"
  },
  "save_preview": {
    "patient_id": "BN-02",
    "form_id": "benh_an_vao_vien",
    "source": "voice",
    "filled_count": 11,
    "missing_required": []
  }
}
```

---

## Kịch bản 7: Tóm tắt bệnh án ra viện (`benh_an_ra_vien`)

- **Bối cảnh:** Bác sĩ hoàn thiện hồ sơ ra viện, hướng dẫn điều trị ngoại trú và hẹn tái khám. Có che PII tên bệnh nhân.
- **Tài khoản / Bệnh nhân:** Bác sĩ (`bs_a`) / `BN-04` (Bộ luật `v1`)
- **Trường bắt buộc:** `chan_doan_ra_vien`, `huong_dieu_tri`
- **Trường PII được che:** `ten_benh_nhan` → `[TÊN]`

### Kịch bản thoại đầu vào (Input)
> 1. "Tên bệnh nhân là Hoàng Văn Minh."
> 2. "Chẩn đoán ra viện là viêm dạ dày cấp đã ổn định."
> 3. "Tình trạng lúc ra viện là tỉnh hoàn toàn hết đau bụng."
> 4. "Khả năng ăn uống lúc ra viện là tự ăn, khả năng đi lại lúc ra viện là tự đi lại."
> 5. "Hướng điều trị là dùng thuốc theo đơn ngoại trú và tái khám sau 7 ngày."
> 6. "Giấy tờ đã bàn giao là giấy ra viện và đơn thuốc, nơi hẹn tái khám là phòng khám nội tiêu hóa."

### Synthetic Output (Pipeline Local – `POST /api/voice/audio`)
```json
{
  "ok": true,
  "mode": "local",
  "has_speech": true,
  "stt_backend": "phowhisper",
  "stt_error": null,
  "source": "local",
  "out_of_scope": false,
  "pii_masked": 1,
  "masked": "Tên bệnh nhân là [TÊN]. Chẩn đoán ra viện là viêm dạ dày cấp đã ổn định. Tình trạng lúc ra viện là tỉnh hoàn toàn hết đau bụng. Khả năng ăn uống lúc ra viện là tự ăn, khả năng đi lại lúc ra viện là tự đi lại. Hướng điều trị là dùng thuốc theo đơn ngoại trú và tái khám sau 7 ngày. Giấy tờ đã bàn giao là giấy ra viện và đơn thuốc, nơi hẹn tái khám là phòng khám nội tiêu hóa.",
  "extracted": {
    "ten_benh_nhan": "[TÊN]",
    "chan_doan_ra_vien": "viêm dạ dày cấp đã ổn định",
    "tinh_trang_ra_vien": "tỉnh hoàn toàn hết đau bụng",
    "an_uong_ra_vien": "Tự ăn",
    "van_dong_ra_vien": "Tự đi lại",
    "huong_dieu_tri": "dùng thuốc theo đơn ngoại trú và tái khám sau 7 ngày",
    "giay_to": "giấy ra viện và đơn thuốc",
    "noi_tai_kham": "phòng khám nội tiêu hóa"
  },
  "save_preview": {
    "patient_id": "BN-04",
    "form_id": "benh_an_ra_vien",
    "source": "voice",
    "filled_count": 8,
    "missing_required": []
  }
}
```

---

## Kịch bản 8: Theo dõi sau mổ (`phieu_theo_doi_sau_mo`)

- **Bối cảnh:** Điều dưỡng tiếp nhận và theo dõi bệnh nhân từ buồng hồi tỉnh về khoa. Có che PII tên bệnh nhân.
- **Tài khoản / Bệnh nhân:** Điều dưỡng (`dd_b`) / `BN-03` (Bộ luật `v1`)
- **Trường bắt buộc:** `dau_hieu`
- **Trường PII được che:** `ten_benh_nhan` → `[TÊN]`

### Kịch bản thoại đầu vào (Input)
> 1. "Tên bệnh nhân là Phạm Thị Lan."
> 2. "Phương pháp vô cảm đã ghi là gây mê, đường truyền khi tiếp nhận là ngoại vi."
> 3. "Dấu hiệu theo dõi là người bệnh tỉnh tiếp xúc tốt khi gọi hỏi."
> 4. "Tình trạng băng vết mổ là khô, hô hấp lúc theo dõi là tự thở khí phòng."
> 5. "Mạch khi theo dõi 84, huyết áp khi theo dõi là 116/74 mmHg, điểm đau khi nghỉ 3."
> 6. "Buồn nôn sau mổ là chưa ghi nhận, tư thế hiện tại là nằm ngửa."
> 7. "Điểm cần tiếp tục theo dõi là kiểm tra lại băng vết mổ sau 2 giờ."

### Synthetic Output (Pipeline Local – `POST /api/voice/audio`)
```json
{
  "ok": true,
  "mode": "local",
  "has_speech": true,
  "stt_backend": "phowhisper",
  "stt_error": null,
  "source": "local",
  "out_of_scope": false,
  "pii_masked": 1,
  "masked": "Tên bệnh nhân là [TÊN]. Phương pháp vô cảm đã ghi là gây mê, đường truyền khi tiếp nhận là ngoại vi. Dấu hiệu theo dõi là người bệnh tỉnh tiếp xúc tốt khi gọi hỏi. Tình trạng băng vết mổ là khô, hô hấp lúc theo dõi là tự thở khí phòng. Mạch khi theo dõi 84, huyết áp khi theo dõi là 116/74 mmHg, điểm đau khi nghỉ 3. Buồn nôn sau mổ là chưa ghi nhận, tư thế hiện tại là nằm ngửa. Điểm cần tiếp tục theo dõi là kiểm tra lại băng vết mổ sau 2 giờ.",
  "extracted": {
    "ten_benh_nhan": "[TÊN]",
    "vo_cam": "Gây mê",
    "duong_truyen_nhan": "Ngoại vi",
    "dau_hieu": "người bệnh tỉnh tiếp xúc tốt khi gọi hỏi",
    "vet_mo": "Khô",
    "ho_hap_sau_mo": "Tự thở khí phòng",
    "mach_sau_mo": 84,
    "huyet_ap_sau_mo": "116/74 mmhg",
    "diem_dau_sau_mo": 3,
    "buon_non": "Chưa ghi nhận",
    "tu_the": "Nằm ngửa",
    "noi_dung_theo_doi": "kiểm tra lại băng vết mổ sau 2 giờ"
  },
  "save_preview": {
    "patient_id": "BN-03",
    "form_id": "phieu_theo_doi_sau_mo",
    "source": "voice",
    "filled_count": 12,
    "missing_required": []
  }
}
```

---

## Kịch bản 9: Giáo dục sức khỏe (`phieu_giao_duc_suc_khoe`)

- **Bối cảnh:** Điều dưỡng hướng dẫn trực tiếp tại giường cách dùng chuông gọi và phòng ngừa ngã, người bệnh thực hành đạt yêu cầu. Có che PII tên bệnh nhân.
- **Tài khoản / Bệnh nhân:** Điều dưỡng (`dd_b`) / `BN-01` (**Bộ luật `v2`**)
- **Trường bắt buộc:** `noi_dung`, `nguoi_nhan`
- **Trường PII được che:** `ten_benh_nhan` → `[TÊN]`

### Kịch bản thoại đầu vào (Input)
> 1. "Tên bệnh nhân là Nguyễn Văn An."
> 2. "Khả năng tiếp nhận là tự trao đổi, hình thức hướng dẫn là trực tiếp tại giường."
> 3. "Nội dung giáo dục là hướng dẫn sử dụng chuông gọi và phòng ngừa ngã."
> 4. "Người nhận giáo dục là người bệnh, địa điểm thực hiện là buồng bệnh A102."
> 5. "Thời lượng buổi hướng dẫn 15 phút."
> 6. "Cách kiểm tra mức độ hiểu là thực hành lại, kết quả sau hướng dẫn là đã tự thực hiện."
> 7. "Phản hồi của người nhận là đã nắm rõ và bấm thử chuông thành công."

### Synthetic Output (Pipeline Local – `POST /api/voice/audio`)
```json
{
  "ok": true,
  "mode": "local",
  "has_speech": true,
  "stt_backend": "phowhisper",
  "stt_error": null,
  "source": "local",
  "out_of_scope": false,
  "pii_masked": 1,
  "masked": "Tên bệnh nhân là [TÊN]. Khả năng tiếp nhận là tự trao đổi, hình thức hướng dẫn là trực tiếp tại giường. Nội dung giáo dục là hướng dẫn sử dụng chuông gọi và phòng ngừa ngã. Người nhận giáo dục là người bệnh, địa điểm thực hiện là buồng bệnh A102. Thời lượng buổi hướng dẫn 15 phút. Cách kiểm tra mức độ hiểu là thực hành lại, kết quả sau hướng dẫn là đã tự thực hiện. Phản hồi của người nhận là đã nắm rõ và bấm thử chuông thành công.",
  "extracted": {
    "ten_benh_nhan": "[TÊN]",
    "kha_nang_tiep_nhan": "Tự trao đổi",
    "noi_dung": "hướng dẫn sử dụng chuông gọi và phòng ngừa ngã",
    "nguoi_nhan": "người bệnh",
    "hinh_thuc": "Trực tiếp tại giường",
    "dia_diem": "buồng bệnh a102",
    "thoi_luong": 15,
    "phan_hoi": "đã nắm rõ và bấm thử chuông thành công",
    "kiem_tra_hieu": "Thực hành lại",
    "ket_qua_hoc": "Đã tự thực hiện"
  },
  "save_preview": {
    "patient_id": "BN-01",
    "form_id": "phieu_giao_duc_suc_khoe",
    "source": "voice",
    "filled_count": 10,
    "missing_required": []
  }
}
```

---

## Kịch bản 10: Đánh giá nguy cơ loét tì đè (`phieu_danh_gia_loet`)

- **Bối cảnh:** Điều dưỡng kiểm tra da vùng gót chân và cùng cụt đầu ca theo thang điểm Braden, kê gối giảm tì đè và bàn giao ca sau. Có che PII tên bệnh nhân.
- **Tài khoản / Bệnh nhân:** Điều dưỡng (`dd_b`) / `BN-01` (**Bộ luật `v2`**)
- **Trường bắt buộc:** `diem_braden`
- **Trường PII được che:** `ten_benh_nhan` → `[TÊN]`

### Kịch bản thoại đầu vào (Input)
> 1. "Tên bệnh nhân là Nguyễn Văn An."
> 2. "Lý do kiểm tra là đầu ca, tư thế lúc quan sát là nằm nghiêng có hỗ trợ."
> 3. "Điểm Braden 18, vị trí quan sát là hai gót chân và vùng cùng cụt."
> 4. "Tình trạng da là nguyên vẹn, độ ẩm tại vùng quan sát là khô."
> 5. "Khả năng báo khó chịu là báo được bằng lời, mức hoạt động trong ca là chủ yếu tại giường, khả năng tự xoay trở là cần trợ giúp."
> 6. "Biện pháp giảm tì đã thực hiện là kê gối mềm dưới hai gót chân."
> 7. "Vùng cần kiểm tra ở ca sau là hai gót chân và vùng cùng cụt."

### Synthetic Output (Pipeline Local – `POST /api/voice/audio`)
```json
{
  "ok": true,
  "mode": "local",
  "has_speech": true,
  "stt_backend": "phowhisper",
  "stt_error": null,
  "source": "local",
  "out_of_scope": false,
  "pii_masked": 1,
  "masked": "Tên bệnh nhân là [TÊN]. Lý do kiểm tra là đầu ca, tư thế lúc quan sát là nằm nghiêng có hỗ trợ. Điểm Braden 18, vị trí quan sát là hai gót chân và vùng cùng cụt. Tình trạng da là nguyên vẹn, độ ẩm tại vùng quan sát là khô. Khả năng báo khó chịu là báo được bằng lời, mức hoạt động trong ca là chủ yếu tại giường, khả năng tự xoay trở là cần trợ giúp. Biện pháp giảm tì đã thực hiện là kê gối mềm dưới hai gót chân. Vùng cần kiểm tra ở ca sau là hai gót chân và vùng cùng cụt.",
  "extracted": {
    "ten_benh_nhan": "[TÊN]",
    "ly_do_kiem_tra": "Đầu ca",
    "tu_the_quan_sat": "Nằm nghiêng có hỗ trợ",
    "diem_braden": 18,
    "vi_tri": "hai gót chân và vùng cùng cụt",
    "tinh_trang_da": "Nguyên vẹn",
    "do_am_da": "Khô",
    "cam_nhan": "Báo được bằng lời",
    "hoat_dong": "Chủ yếu tại giường",
    "xoay_tro": "Cần trợ giúp",
    "ho_tro_giam_ty": "kê gối mềm dưới hai gót chân",
    "ban_giao_da": "hai gót chân và vùng cùng cụt"
  },
  "save_preview": {
    "patient_id": "BN-01",
    "form_id": "phieu_danh_gia_loet",
    "source": "voice",
    "filled_count": 12,
    "missing_required": []
  }
}
```
