// Hội thoại hoàn toàn giả, dùng chung cho chế độ mở file và chạy server.
// Không gán sẵn kết quả: từng câu vẫn đi qua /api/voice để che PII và trích xuất.
window.VOICE_SAMPLES = {
  benh_an_vao_vien: {
    title: "Bệnh án vào viện",
    description: "Bác sĩ hỏi bệnh, ghi lý do vào viện và chẩn đoán; bỏ câu ngoài lề.",
    segments: [
      { who: "Bác sĩ", text: "Chị mô tả tình trạng hiện tại giúp tôi nhé." },
      { who: "Bệnh nhân", text: "Em tên là Nguyễn Thị Mai, số điện thoại 0912345678." },
      { who: "Bệnh nhân", text: "Lý do vào viện là đau bụng vùng hạ sườn phải đã ba ngày." },
      { who: "Người nhà", text: "Cuối tuần nhà em định đi xem phim." },
      { who: "Bác sĩ", text: "Chẩn đoán là đau bụng hạ sườn phải đang theo dõi nguyên nhân." },
    ],
  },
  phieu_danh_gia_ban_dau: {
    title: "Đánh giá ban đầu",
    description: "Điều dưỡng ghi dị ứng, thuốc và tiền sử; che tên và số người liên hệ.",
    segments: [
      { who: "Điều dưỡng", text: "Chị cho biết tình trạng sức khỏe trước đây nhé." },
      { who: "Bệnh nhân", text: "Dị ứng penicillin gây nổi mẩn." },
      { who: "Bệnh nhân", text: "Đang dùng amlodipin 5 mg mỗi sáng." },
      { who: "Người nhà", text: "Hôm nay trời đẹp quá." },
      { who: "Bệnh nhân", text: "Tiền sử tăng huyết áp năm năm và đã mổ ruột thừa." },
      { who: "Bệnh nhân", text: "Người liên hệ là Lê Văn Nam, số điện thoại 0987654321." },
    ],
  },
  phieu_sinh_ton_nguoi_lon: {
    title: "Dấu hiệu sinh tồn",
    description: "Đọc năm chỉ số, sau đó sửa mạch và huyết áp bằng câu đọc lại.",
    segments: [
      { who: "Điều dưỡng", text: "Anh Nguyễn Văn An, số điện thoại 0912345678." },
      { who: "Người nhà", text: "Mọi người ăn trưa chưa?" },
      { who: "Điều dưỡng", text: "Mạch 88, nhịp thở 20, huyết áp 120 trên 80." },
      { who: "Điều dưỡng", text: "Nhiệt độ 37 phẩy 2, SpO2 98." },
      { who: "Điều dưỡng", text: "Tôi đọc lại: huyết áp 118 trên 76, mạch 90." },
    ],
  },
};
