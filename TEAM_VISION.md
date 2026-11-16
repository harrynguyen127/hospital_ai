# TEAM VISION

| | |
|---|---|
| **Dự án** | Trợ lý AI nhắc điền form theo quy định và nhập liệu bằng giọng nói |
| **Đơn vị** | Trung tâm Tiêu hóa – Gan mật – Tiết niệu |
| **Team** | Nguyễn Anh Tuấn (trưởng nhóm), Bùi Đức Thành, Mai Tiến Huy, Trịnh Xuân Huy |

---

## 1. Tầm nhìn

> Điều dưỡng và bác sĩ không còn phải tự nhớ phiếu nào đến hạn, trường nào còn thiếu, và không phải ghi giấy rồi nhập lại.

Một trợ lý AI chạy cạnh EMR nhắc đúng lúc theo quy định và giúp nhập liệu bằng giọng nói. **Quyết định cuối cùng luôn thuộc về người dùng.**

---

## 2. Vấn đề

| Vấn đề | Biểu hiện |
|---|---|
| **Nhiều phiếu, nhiều thời hạn** | Sinh tồn, chăm sóc, nguy cơ ngã, đánh giá đau, loét, giáo dục sức khỏe; lịch theo dõi sau mổ đan xen và lệch giờ. Hệ thống hiện không cảnh báo khi thiếu hoặc trễ. |
| **Quy định phân tán** | Rải rác qua mail, biên bản, khó tra cứu. |
| **Nhập liệu trùng lặp** | Nhập nhiều nơi, thường dồn đến cuối ngày để ghi hồi cứu. |
| **Đánh giá ban đầu ghi giấy** | Dị ứng, thuốc đang dùng, người liên hệ, tiền sử phải ghi giấy rồi nhập lại. |

---

## 3. Giải pháp

### Tính năng 1: Nhắc nhở điền form theo quy định

- Nhắc phiếu đến hạn hoặc quá hạn, tính lần tiếp theo từ dữ liệu vừa nhập.
- Cảnh báo trường bắt buộc còn thiếu trong phiếu đã làm.
- Phân quyền theo tài khoản: điều dưỡng và bác sĩ nhận nhắc việc phù hợp vai trò.
- Chỉ báo thiếu, **không tự điền**.

### Tính năng 2: Voice input to form

- Nhận diện form và các trường đang hiển thị trên màn hình EMR.
- Chuyển giọng nói thành text, phân biệt người nói khi có nhiều người.
- Lọc thông tin nhạy cảm và thông tin không liên quan.
- Trích xuất vào đúng trường, điền nháp. Người dùng xác nhận rồi mới lưu.

### Liên kết hai tính năng

```
Voice điền nháp → Người dùng xác nhận → Hệ thống nhắc phiếu còn thiếu trường nào
```

Cả hai tính năng dùng chung bộ định nghĩa form.

---

## 4. Nguyên tắc thiết kế

1. **Con người quyết định cuối cùng:** AI chỉ nhắc và điền nháp, không tự lưu.
2. **Bảo mật trước:** dữ liệu nhạy cảm xử lý local; chỉ dữ liệu đã lọc mới được đưa lên cloud khi có lý do rõ ràng.
3. **Không tạo thêm app mới:** chạy cạnh hệ thống sẵn có, thiết kế dạng microservice tích hợp qua cổng kết nối.
4. **Không thay đổi quy trình bệnh viện:** bám theo quy định hiện hành của QLCL.
5. **Nhu cầu trước giải pháp:** mọi tính năng phải có minh chứng từ quan sát, phỏng vấn, đo đạc.

---

## 5. Người dùng mục tiêu

| Vai trò | Nhu cầu chính |
|---|---|
| **Điều dưỡng** | Nhắc phiếu hằng ngày, nhập đánh giá ban đầu bằng giọng nói |
| **Bác sĩ** | Nhắc bệnh án vào viện, ra viện; nhập liệu bằng giọng nói |
| **Quản lý chất lượng** | Hồ sơ đầy đủ, đúng hạn hơn |

---

## 6. Thước đo thành công

- [ ] Giảm thời gian và số thao tác khi điền form so với baseline.
- [ ] Giảm tỷ lệ phiếu trễ hạn hoặc thiếu trường.
- [ ] Giảm việc ghi hồi cứu cuối ngày.
- [ ] Được 3–5 người dùng thật xác nhận hữu ích và điều dưỡng trưởng / trưởng khoa endorse.

---

## 7. Hướng đi tiếp

| Mốc | Nội dung |
|---|---|
| **Đến 19/11** | Prototype hai tính năng trên mock EMR, đạt đủ tiêu chí vòng 1. |
| **Tuần 4–6** *(nếu qua vòng 1)* | Làm sâu với PO và dữ liệu thực tế đã ẩn danh; tính chi phí phát triển, thời gian, mức tiết kiệm. |
| **Dài hạn** | Mở rộng sang tra cứu quy định, điều kiện bảo hiểm, và áp dụng cho các khoa, bệnh viện khác trong hệ thống. |
