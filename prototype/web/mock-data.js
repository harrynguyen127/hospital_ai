// Dữ liệu giả lập, sao chép từ data/ của bản Python (server.py đọc cùng nguồn này).
window.PROTO_SEED = {
  "forms": {
    "phieu_sinh_ton_nguoi_lon": {
      "title": "Bảng theo dõi dấu hiệu sinh tồn cho người lớn",
      "aliases": [
        "phiếu sinh tồn",
        "sinh tồn",
        "DHST"
      ],
      "fields": [
        {
          "field_id": "ten_benh_nhan",
          "label": "Tên bệnh nhân",
          "type": "string",
          "ui": "text",
          "required": false,
          "data_level": 1,
          "group": "Điều kiện đo",
          "example": "[TÊN]"
        },
        {
          "field_id": "thoi_diem_do",
          "label": "Thời điểm đo",
          "type": "datetime",
          "ui": "datetime",
          "required": false,
          "data_level": 2,
          "group": "Điều kiện đo"
        },
        {
          "field_id": "tu_the_do",
          "label": "Tư thế đo",
          "type": "enum",
          "ui": "select",
          "required": false,
          "data_level": 2,
          "group": "Điều kiện đo",
          "options": [
            "Nằm",
            "Ngồi",
            "Đứng"
          ],
          "example": "Nằm"
        },
        {
          "field_id": "ly_do_do",
          "label": "Lý do đo",
          "type": "enum",
          "ui": "select",
          "required": false,
          "data_level": 2,
          "group": "Điều kiện đo",
          "options": [
            "Định kỳ",
            "Sau vận động",
            "Theo dõi lại"
          ],
          "example": "Định kỳ"
        },
        {
          "field_id": "trang_thai_do",
          "label": "Trạng thái lúc đo",
          "type": "enum",
          "ui": "select",
          "required": false,
          "data_level": 2,
          "group": "Điều kiện đo",
          "options": [
            "Đang nghỉ",
            "Vừa đi lại",
            "Đang ngủ"
          ],
          "example": "Đang nghỉ"
        },
        {
          "field_id": "vi_tri_do_ha",
          "label": "Vị trí đo huyết áp",
          "type": "enum",
          "ui": "select",
          "required": false,
          "data_level": 2,
          "group": "Điều kiện đo",
          "options": [
            "Cánh tay trái",
            "Cánh tay phải"
          ],
          "example": "Cánh tay trái"
        },
        {
          "field_id": "phuong_phap_nhiet",
          "label": "Vị trí đo nhiệt độ",
          "type": "enum",
          "ui": "select",
          "required": false,
          "data_level": 2,
          "group": "Điều kiện đo",
          "options": [
            "Nách",
            "Tai",
            "Miệng"
          ],
          "example": "Nách"
        },
        {
          "field_id": "mach",
          "label": "Mạch",
          "type": "number",
          "ui": "number",
          "required": true,
          "data_level": 2,
          "group": "Chỉ số tại giường",
          "unit": "lần/phút",
          "example": 88
        },
        {
          "field_id": "nhip_tho",
          "label": "Nhịp thở",
          "type": "number",
          "ui": "number",
          "required": true,
          "data_level": 2,
          "group": "Chỉ số tại giường",
          "unit": "lần/phút",
          "example": 20
        },
        {
          "field_id": "huyet_ap",
          "label": "Huyết áp",
          "type": "string",
          "ui": "text",
          "required": false,
          "data_level": 2,
          "group": "Chỉ số tại giường",
          "unit": "mmHg",
          "example": "118/76"
        },
        {
          "field_id": "nhiet_do",
          "label": "Nhiệt độ",
          "type": "number",
          "ui": "number",
          "required": false,
          "data_level": 2,
          "group": "Chỉ số tại giường",
          "unit": "°C",
          "example": 37.2
        },
        {
          "field_id": "spo2",
          "label": "SpO2",
          "type": "number",
          "ui": "number",
          "required": false,
          "data_level": 2,
          "group": "Chỉ số tại giường",
          "unit": "%",
          "example": 98,
          "min": 0,
          "max": 100
        },
        {
          "field_id": "nhip_mach",
          "label": "Nhịp mạch khi bắt",
          "type": "enum",
          "ui": "select",
          "required": false,
          "data_level": 2,
          "group": "Quan sát tại giường",
          "options": [
            "Đều",
            "Không đều",
            "Khó bắt"
          ],
          "example": "Đều"
        },
        {
          "field_id": "kieu_tho",
          "label": "Kiểu thở quan sát được",
          "type": "enum",
          "ui": "select",
          "required": false,
          "data_level": 2,
          "group": "Quan sát tại giường",
          "options": [
            "Đều",
            "Nông",
            "Có gắng sức"
          ],
          "example": "Đều"
        },
        {
          "field_id": "ho_tro_oxy",
          "label": "Hỗ trợ hô hấp lúc đo",
          "type": "enum",
          "ui": "select",
          "required": false,
          "data_level": 2,
          "group": "Quan sát tại giường",
          "options": [
            "Khí phòng",
            "Gọng mũi",
            "Mặt nạ"
          ],
          "example": "Khí phòng"
        },
        {
          "field_id": "trang_thai_tiep_xuc",
          "label": "Tiếp xúc khi đo",
          "type": "enum",
          "ui": "select",
          "required": false,
          "data_level": 2,
          "group": "Quan sát tại giường",
          "options": [
            "Tỉnh, trả lời rõ",
            "Buồn ngủ",
            "Khó đánh thức"
          ],
          "example": "Tỉnh, trả lời rõ"
        },
        {
          "field_id": "trieu_chung",
          "label": "Triệu chứng người bệnh mô tả",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Quan sát tại giường",
          "example": "Hơi mệt sau khi đi lại, đã ngồi nghỉ trước khi đo."
        },
        {
          "field_id": "so_voi_truoc",
          "label": "So với lần đo trước",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Đối chiếu và bàn giao",
          "example": "Mạch lần này ghi nhận khi người bệnh đang nghỉ tại giường."
        },
        {
          "field_id": "xu_tri_sau_do",
          "label": "Việc đã thực hiện sau đo",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Đối chiếu và bàn giao",
          "example": "Đã ghi kết quả và đối chiếu với bảng theo dõi của ca trước."
        },
        {
          "field_id": "ban_giao_do",
          "label": "Điểm cần bàn giao",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Đối chiếu và bàn giao",
          "example": "Ghi rõ tư thế ở lần đo tiếp theo để tiện đối chiếu."
        }
      ]
    },
    "phieu_cham_soc": {
      "title": "Phiếu chăm sóc điều dưỡng",
      "aliases": [
        "phiếu chăm sóc",
        "chăm sóc"
      ],
      "fields": [
        {
          "field_id": "ten_benh_nhan",
          "label": "Tên bệnh nhân",
          "type": "string",
          "ui": "text",
          "required": false,
          "data_level": 1,
          "group": "Nhận định đầu ca",
          "example": "[TÊN]"
        },
        {
          "field_id": "gio_nhan_dinh",
          "label": "Thời điểm nhận định",
          "type": "datetime",
          "ui": "datetime",
          "required": false,
          "data_level": 2,
          "group": "Nhận định đầu ca"
        },
        {
          "field_id": "than_phien",
          "label": "Than phiền đầu ca",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Nhận định đầu ca",
          "example": "Người bệnh thấy mệt khi tự ngồi dậy."
        },
        {
          "field_id": "muc_doc_lap",
          "label": "Mức hỗ trợ sinh hoạt",
          "type": "enum",
          "ui": "select",
          "required": false,
          "data_level": 2,
          "group": "Nhận định đầu ca",
          "options": [
            "Hỗ trợ một phần",
            "Độc lập",
            "Hỗ trợ hoàn toàn"
          ],
          "example": "Hỗ trợ một phần"
        },
        {
          "field_id": "van_de_chinh",
          "label": "Vấn đề chăm sóc trong ca",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Nhận định đầu ca",
          "example": "Cần trợ giúp khi di chuyển và vệ sinh tại giường."
        },
        {
          "field_id": "muc_tieu_ca",
          "label": "Mục tiêu trong ca",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Nhận định đầu ca",
          "example": "Người bệnh có thể tham gia vệ sinh cá nhân với trợ giúp."
        },
        {
          "field_id": "thuc_hien",
          "label": "Nội dung chăm sóc",
          "type": "string",
          "ui": "textarea",
          "required": true,
          "data_level": 2,
          "group": "Chăm sóc trong ca",
          "example": "Hỗ trợ vệ sinh cá nhân tại giường."
        },
        {
          "field_id": "nguoi_thuc_hien",
          "label": "Người thực hiện",
          "type": "string",
          "ui": "text",
          "required": true,
          "data_level": 2,
          "group": "Chăm sóc trong ca",
          "example": "ĐD-MẪU-B"
        },
        {
          "field_id": "ca_truc",
          "label": "Ca trực",
          "type": "enum",
          "ui": "select",
          "required": false,
          "data_level": 2,
          "group": "Chăm sóc trong ca",
          "options": [
            "Ca sáng",
            "Ca chiều",
            "Ca đêm"
          ],
          "example": "Ca sáng"
        },
        {
          "field_id": "dinh_duong",
          "label": "Ăn uống thực tế",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Chăm sóc trong ca",
          "example": "Ăn được khoảng nửa suất mẫu, tự uống nước."
        },
        {
          "field_id": "dai_tieu_tien",
          "label": "Theo dõi bài tiết",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Chăm sóc trong ca",
          "example": "Tự đi tiểu với người hỗ trợ lúc ra khỏi giường."
        },
        {
          "field_id": "van_dong_trong_ca",
          "label": "Vận động trong ca",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Chăm sóc trong ca",
          "example": "Đã ngồi ở mép giường có trợ giúp."
        },
        {
          "field_id": "cham_soc_da",
          "label": "Vệ sinh và chăm sóc da",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Chăm sóc trong ca",
          "example": "Đã thay áo và kiểm tra vùng da tiếp xúc với băng dính."
        },
        {
          "field_id": "duong_truyen",
          "label": "Tình trạng đường truyền",
          "type": "enum",
          "ui": "select",
          "required": false,
          "data_level": 2,
          "group": "Chăm sóc trong ca",
          "options": [
            "Không có đường truyền",
            "Đang theo dõi tại chỗ",
            "Đã tháo"
          ],
          "example": "Không có đường truyền"
        },
        {
          "field_id": "dap_ung",
          "label": "Đáp ứng sau chăm sóc",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Sau chăm sóc",
          "example": "Người bệnh mẫu cho biết đã dễ chịu hơn."
        },
        {
          "field_id": "ban_giao",
          "label": "Nội dung bàn giao",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Sau chăm sóc",
          "example": "Ghi lại mức độ tự vận động ở ca kế tiếp."
        },
        {
          "field_id": "muc_dat",
          "label": "Mức đạt mục tiêu",
          "type": "enum",
          "ui": "select",
          "required": false,
          "data_level": 2,
          "group": "Sau chăm sóc",
          "options": [
            "Đạt một phần",
            "Đã đạt",
            "Chưa đạt"
          ],
          "example": "Đạt một phần"
        },
        {
          "field_id": "viec_con_lai",
          "label": "Việc còn lại cuối ca",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Sau chăm sóc",
          "example": "Cần hỗ trợ thêm trong lần đi lại tiếp theo."
        },
        {
          "field_id": "nguoi_nhan_ca",
          "label": "Mã người nhận bàn giao",
          "type": "string",
          "ui": "text",
          "required": false,
          "data_level": 2,
          "group": "Sau chăm sóc",
          "example": "ĐD-MẪU-C"
        }
      ]
    },
    "phieu_nguy_co_nga": {
      "title": "Đánh giá nguy cơ ngã",
      "aliases": [
        "nguy cơ ngã",
        "phiếu ngã",
        "đánh giá ngã"
      ],
      "fields": [
        {
          "field_id": "ten_benh_nhan",
          "label": "Tên bệnh nhân",
          "type": "string",
          "ui": "text",
          "required": false,
          "data_level": 1,
          "group": "Bối cảnh đánh giá",
          "example": "[TÊN]"
        },
        {
          "field_id": "luc_danh_gia",
          "label": "Thời điểm ghi nhận",
          "type": "datetime",
          "ui": "datetime",
          "required": false,
          "data_level": 2,
          "group": "Bối cảnh đánh giá"
        },
        {
          "field_id": "ly_do_danh_gia",
          "label": "Lý do đánh giá",
          "type": "enum",
          "ui": "select",
          "required": false,
          "data_level": 2,
          "group": "Bối cảnh đánh giá",
          "options": [
            "Đầu ca",
            "Lúc nhập viện",
            "Sau thay đổi vận động"
          ],
          "example": "Đầu ca"
        },
        {
          "field_id": "nguon_khai",
          "label": "Nguồn thông tin về lần ngã",
          "type": "enum",
          "ui": "select",
          "required": false,
          "data_level": 2,
          "group": "Bối cảnh đánh giá",
          "options": [
            "Người bệnh",
            "Người chăm sóc",
            "Hồ sơ trong khoa"
          ],
          "example": "Người bệnh"
        },
        {
          "field_id": "tien_su_nga",
          "label": "Tiền sử ngã theo lời kể",
          "type": "enum",
          "ui": "select",
          "required": false,
          "data_level": 2,
          "group": "Yếu tố quan sát",
          "options": [
            "Chưa ghi nhận",
            "Có lần ngã",
            "Chưa rõ"
          ],
          "example": "Chưa ghi nhận"
        },
        {
          "field_id": "dung_cu_di",
          "label": "Dụng cụ trợ giúp đi lại",
          "type": "enum",
          "ui": "select",
          "required": false,
          "data_level": 2,
          "group": "Yếu tố quan sát",
          "options": [
            "Khung tập đi",
            "Gậy",
            "Xe lăn",
            "Không sử dụng"
          ],
          "example": "Khung tập đi"
        },
        {
          "field_id": "dang_di",
          "label": "Dáng đi quan sát được",
          "type": "enum",
          "ui": "select",
          "required": false,
          "data_level": 2,
          "group": "Yếu tố quan sát",
          "options": [
            "Bước ngắn, cần vịn",
            "Vững",
            "Chưa quan sát"
          ],
          "example": "Bước ngắn, cần vịn"
        },
        {
          "field_id": "chuyen_tu_the",
          "label": "Khả năng chuyển tư thế",
          "type": "enum",
          "ui": "select",
          "required": false,
          "data_level": 2,
          "group": "Yếu tố quan sát",
          "options": [
            "Cần người dìu",
            "Tự thực hiện",
            "Chưa đánh giá"
          ],
          "example": "Cần người dìu"
        },
        {
          "field_id": "chong_mat",
          "label": "Triệu chứng khi đứng lên",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Yếu tố quan sát",
          "example": "Cho biết hơi choáng khi đứng dậy lần đầu."
        },
        {
          "field_id": "thi_luc",
          "label": "Khả năng nhìn đường đi",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Yếu tố quan sát",
          "example": "Nhìn rõ lối đi khi đeo kính mẫu."
        },
        {
          "field_id": "diem_nga",
          "label": "Điểm nguy cơ ngã",
          "type": "number",
          "ui": "number",
          "required": true,
          "data_level": 2,
          "group": "Đánh giá tại giường",
          "unit": "điểm",
          "example": 25
        },
        {
          "field_id": "ket_qua",
          "label": "Kết quả",
          "type": "string",
          "ui": "text",
          "required": true,
          "data_level": 2,
          "group": "Đánh giá tại giường",
          "example": "Cần hỗ trợ khi di chuyển."
        },
        {
          "field_id": "di_chuyen",
          "label": "Khả năng di chuyển",
          "type": "enum",
          "ui": "select",
          "required": false,
          "data_level": 2,
          "group": "Đánh giá tại giường",
          "options": [
            "Có người hỗ trợ",
            "Tự đi lại",
            "Tại giường"
          ],
          "example": "Có người hỗ trợ"
        },
        {
          "field_id": "yeu_to",
          "label": "Yếu tố ghi nhận",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Chăm sóc trong ca",
          "example": "Còn loạng choạng khi đứng dậy."
        },
        {
          "field_id": "bien_phap",
          "label": "Biện pháp đã thực hiện",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Chăm sóc trong ca",
          "example": "Đã đặt chuông gọi trong tầm tay."
        },
        {
          "field_id": "moi_truong",
          "label": "Môi trường quanh giường",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Chăm sóc trong ca",
          "example": "Lối đi thông thoáng, dép và kính trong tầm với."
        },
        {
          "field_id": "huong_dan",
          "label": "Hướng dẫn người bệnh và người chăm sóc",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Chăm sóc trong ca",
          "example": "Đã thực hành gọi người hỗ trợ trước khi rời giường."
        },
        {
          "field_id": "kiem_tra_lai",
          "label": "Kiểm tra sau sắp xếp",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Chăm sóc trong ca",
          "example": "Người bệnh với được chuông gọi từ tư thế nằm."
        },
        {
          "field_id": "ban_giao_nga",
          "label": "Nội dung bàn giao nguy cơ ngã",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Chăm sóc trong ca",
          "example": "Cần người đi cùng trong lần vào nhà vệ sinh tiếp theo."
        }
      ]
    },
    "phieu_danh_gia_dau": {
      "title": "Đánh giá đau",
      "aliases": [
        "đánh giá đau",
        "phiếu đau"
      ],
      "fields": [
        {
          "field_id": "ten_benh_nhan",
          "label": "Tên bệnh nhân",
          "type": "string",
          "ui": "text",
          "required": false,
          "data_level": 1,
          "group": "Đánh giá đau",
          "example": "[TÊN]"
        },
        {
          "field_id": "diem_dau",
          "label": "Điểm đau",
          "type": "number",
          "ui": "number",
          "required": true,
          "data_level": 2,
          "group": "Đánh giá đau",
          "unit": "điểm",
          "example": 4,
          "min": 0,
          "max": 10
        },
        {
          "field_id": "thoi_diem_danh_gia",
          "label": "Thời điểm đánh giá",
          "type": "datetime",
          "ui": "datetime",
          "required": true,
          "data_level": 2,
          "group": "Đánh giá đau"
        },
        {
          "field_id": "vi_tri_dau",
          "label": "Vị trí đau",
          "type": "string",
          "ui": "text",
          "required": false,
          "data_level": 2,
          "group": "Đánh giá đau",
          "example": "Vùng quanh vết mổ"
        },
        {
          "field_id": "tinh_chat_dau",
          "label": "Tính chất đau",
          "type": "enum",
          "ui": "select",
          "required": false,
          "data_level": 2,
          "group": "Đánh giá đau",
          "options": [
            "Âm ỉ",
            "Đau nhói",
            "Từng cơn"
          ],
          "example": "Âm ỉ"
        },
        {
          "field_id": "nguon_danh_gia",
          "label": "Người mô tả cơn đau",
          "type": "enum",
          "ui": "select",
          "required": false,
          "data_level": 2,
          "group": "Đánh giá đau",
          "options": [
            "Người bệnh",
            "Người chăm sóc"
          ],
          "example": "Người bệnh"
        },
        {
          "field_id": "thang_diem",
          "label": "Thang dùng để ghi điểm",
          "type": "string",
          "ui": "text",
          "required": false,
          "data_level": 2,
          "group": "Đánh giá đau",
          "example": "Thang số 0–10"
        },
        {
          "field_id": "dac_diem_khoi_phat",
          "label": "Khởi phát cơn đau",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Đánh giá đau",
          "example": "Xuất hiện từ khi đổi tư thế sáng nay."
        },
        {
          "field_id": "thoi_luong",
          "label": "Thời lượng mỗi cơn",
          "type": "string",
          "ui": "text",
          "required": false,
          "data_level": 2,
          "group": "Đánh giá đau",
          "example": "Vài phút theo lời kể"
        },
        {
          "field_id": "huong_lan",
          "label": "Hướng lan của đau",
          "type": "enum",
          "ui": "select",
          "required": false,
          "data_level": 2,
          "group": "Đánh giá đau",
          "options": [
            "Khu trú tại chỗ",
            "Lan sang vùng lân cận",
            "Chưa rõ"
          ],
          "example": "Khu trú tại chỗ"
        },
        {
          "field_id": "yeu_to_tang",
          "label": "Yếu tố làm đau tăng",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Ảnh hưởng đến sinh hoạt",
          "example": "Đau tăng lúc ngồi dậy."
        },
        {
          "field_id": "yeu_to_giam",
          "label": "Yếu tố làm đau giảm",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Ảnh hưởng đến sinh hoạt",
          "example": "Dễ chịu hơn khi có gối đỡ."
        },
        {
          "field_id": "anh_huong_van_dong",
          "label": "Ảnh hưởng đến vận động",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Ảnh hưởng đến sinh hoạt",
          "example": "Người bệnh ngại xoay trở trên giường."
        },
        {
          "field_id": "anh_huong_ngu",
          "label": "Ảnh hưởng đến giấc ngủ",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Ảnh hưởng đến sinh hoạt",
          "example": "Đã thức giấc một lần vì đau."
        },
        {
          "field_id": "hoan_canh",
          "label": "Hoàn cảnh đánh giá",
          "type": "enum",
          "ui": "select",
          "required": false,
          "data_level": 2,
          "group": "Theo dõi",
          "options": [
            "Khi nghỉ",
            "Khi vận động",
            "Sau can thiệp"
          ],
          "example": "Khi nghỉ"
        },
        {
          "field_id": "dien_bien",
          "label": "Diễn biến người bệnh mô tả",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Theo dõi",
          "example": "Cảm giác đau tăng khi thay đổi tư thế."
        },
        {
          "field_id": "ho_tro_da_lam",
          "label": "Hỗ trợ đã thực hiện",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Theo dõi",
          "example": "Đã giúp người bệnh tìm tư thế nghỉ dễ chịu."
        },
        {
          "field_id": "dap_ung_sau_ho_tro",
          "label": "Phản hồi sau hỗ trợ",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Theo dõi",
          "example": "Người bệnh cho biết nằm nghỉ thoải mái hơn."
        },
        {
          "field_id": "ban_giao_dau",
          "label": "Điểm cần đánh giá lại",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Theo dõi",
          "example": "Ghi nhận cảm giác đau khi người bệnh vận động lần tới."
        }
      ]
    },
    "phieu_danh_gia_ban_dau": {
      "title": "Đánh giá ban đầu",
      "aliases": [
        "đánh giá ban đầu",
        "đánh giá khi nhập viện"
      ],
      "fields": [
        {
          "field_id": "ten_benh_nhan",
          "label": "Tên bệnh nhân",
          "type": "string",
          "ui": "text",
          "required": false,
          "data_level": 1,
          "group": "Thông tin khi tiếp nhận",
          "example": "[TÊN]"
        },
        {
          "field_id": "di_ung",
          "label": "Dị ứng",
          "type": "string",
          "ui": "text",
          "required": true,
          "data_level": 2,
          "group": "Thông tin khi tiếp nhận",
          "example": "Có nổi mẩn với thuốc mẫu A."
        },
        {
          "field_id": "thuoc_dang_dung",
          "label": "Thuốc đang dùng",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Thông tin khi tiếp nhận",
          "example": "Thuốc mẫu B theo hồ sơ mô phỏng."
        },
        {
          "field_id": "tien_su",
          "label": "Tiền sử",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Thông tin khi tiếp nhận",
          "example": "Đã từng phẫu thuật bụng."
        },
        {
          "field_id": "tu_cham_soc",
          "label": "Khả năng tự chăm sóc",
          "type": "enum",
          "ui": "select",
          "required": false,
          "data_level": 2,
          "group": "Thông tin khi tiếp nhận",
          "options": [
            "Cần hỗ trợ một phần",
            "Độc lập",
            "Cần hỗ trợ hoàn toàn"
          ],
          "example": "Cần hỗ trợ một phần"
        },
        {
          "field_id": "gio_tiep_nhan",
          "label": "Thời điểm điều dưỡng tiếp nhận",
          "type": "datetime",
          "ui": "datetime",
          "required": false,
          "data_level": 2,
          "group": "Thông tin khi tiếp nhận"
        },
        {
          "field_id": "nguon_thong_tin",
          "label": "Người cung cấp thông tin",
          "type": "enum",
          "ui": "select",
          "required": false,
          "data_level": 2,
          "group": "Thông tin khi tiếp nhận",
          "options": [
            "Người bệnh",
            "Người chăm sóc",
            "Điều dưỡng bàn giao"
          ],
          "example": "Người bệnh"
        },
        {
          "field_id": "giao_tiep",
          "label": "Khả năng giao tiếp",
          "type": "enum",
          "ui": "select",
          "required": false,
          "data_level": 2,
          "group": "Nhu cầu sinh hoạt",
          "options": [
            "Trả lời rõ",
            "Cần nhắc lại câu hỏi",
            "Cần người hỗ trợ"
          ],
          "example": "Trả lời rõ"
        },
        {
          "field_id": "an_uong",
          "label": "Ăn uống trong ngày",
          "type": "enum",
          "ui": "select",
          "required": false,
          "data_level": 2,
          "group": "Nhu cầu sinh hoạt",
          "options": [
            "Ăn ít hơn thường lệ",
            "Ăn như thường lệ",
            "Chưa ăn"
          ],
          "example": "Ăn ít hơn thường lệ"
        },
        {
          "field_id": "nuot",
          "label": "Khả năng nuốt theo lời kể",
          "type": "enum",
          "ui": "select",
          "required": false,
          "data_level": 2,
          "group": "Nhu cầu sinh hoạt",
          "options": [
            "Nuốt được",
            "Khó nuốt",
            "Chưa đánh giá"
          ],
          "example": "Nuốt được"
        },
        {
          "field_id": "giac_ngu",
          "label": "Giấc ngủ gần đây",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Nhu cầu sinh hoạt",
          "example": "Thức giấc vài lần do khó chịu."
        },
        {
          "field_id": "tieu_tien",
          "label": "Tiểu tiện",
          "type": "enum",
          "ui": "select",
          "required": false,
          "data_level": 2,
          "group": "Nhu cầu sinh hoạt",
          "options": [
            "Tự đi tiểu",
            "Cần trợ giúp",
            "Qua dụng cụ"
          ],
          "example": "Tự đi tiểu"
        },
        {
          "field_id": "dai_tien",
          "label": "Đại tiện",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Nhu cầu sinh hoạt",
          "example": "Người bệnh cho biết đã đại tiện hôm trước."
        },
        {
          "field_id": "van_dong",
          "label": "Vận động khi vào khoa",
          "type": "enum",
          "ui": "select",
          "required": false,
          "data_level": 2,
          "group": "Nhu cầu sinh hoạt",
          "options": [
            "Đi có người dìu",
            "Đi độc lập",
            "Nằm tại giường"
          ],
          "example": "Đi có người dìu"
        },
        {
          "field_id": "da_niem",
          "label": "Tình trạng da lúc tiếp nhận",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "An toàn và nhu cầu hỗ trợ",
          "example": "Da vùng tì đè quan sát được còn nguyên vẹn."
        },
        {
          "field_id": "dung_cu",
          "label": "Dụng cụ mang theo",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "An toàn và nhu cầu hỗ trợ",
          "example": "Có kính đọc sách trong túi đồ cá nhân."
        },
        {
          "field_id": "lo_lang",
          "label": "Điều người bệnh lo lắng",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "An toàn và nhu cầu hỗ trợ",
          "example": "Muốn biết khi nào người nhà có thể vào thăm."
        },
        {
          "field_id": "uu_tien",
          "label": "Nhu cầu chăm sóc ưu tiên",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "An toàn và nhu cầu hỗ trợ",
          "example": "Cần hướng dẫn đường đi và hỗ trợ lần đầu ra khỏi giường."
        },
        {
          "field_id": "huong_dan_khoa",
          "label": "Nội dung đã hướng dẫn khi vào khoa",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "An toàn và nhu cầu hỗ trợ",
          "example": "Đã hướng dẫn sử dụng chuông gọi và vị trí nhà vệ sinh."
        },
        {
          "field_id": "nguoi_lien_he",
          "label": "Người liên hệ",
          "type": "string",
          "ui": "text",
          "required": true,
          "data_level": 2,
          "group": "Liên hệ trong hồ sơ mẫu",
          "example": "LH-MẪU-A"
        },
        {
          "field_id": "quan_he",
          "label": "Quan hệ với người bệnh",
          "type": "enum",
          "ui": "select",
          "required": false,
          "data_level": 2,
          "group": "Liên hệ trong hồ sơ mẫu",
          "options": [
            "Người thân",
            "Người chăm sóc",
            "Chưa ghi nhận"
          ],
          "example": "Người thân"
        }
      ]
    },
    "benh_an_vao_vien": {
      "title": "Bệnh án vào viện",
      "aliases": [
        "bệnh án vào viện",
        "bệnh án nhập viện"
      ],
      "fields": [
        {
          "field_id": "ten_benh_nhan",
          "label": "Tên bệnh nhân",
          "type": "string",
          "ui": "text",
          "required": false,
          "data_level": 1,
          "group": "Tiếp nhận tại khoa",
          "example": "[TÊN]"
        },
        {
          "field_id": "gio_kham",
          "label": "Thời điểm khám tiếp nhận",
          "type": "datetime",
          "ui": "datetime",
          "required": false,
          "data_level": 2,
          "group": "Tiếp nhận tại khoa"
        },
        {
          "field_id": "nguoi_cung_cap",
          "label": "Nguồn cung cấp bệnh sử",
          "type": "enum",
          "ui": "select",
          "required": false,
          "data_level": 2,
          "group": "Tiếp nhận tại khoa",
          "options": [
            "Người bệnh",
            "Người chăm sóc",
            "Hồ sơ chuyển khoa"
          ],
          "example": "Người bệnh"
        },
        {
          "field_id": "cach_vao_khoa",
          "label": "Cách vào khoa",
          "type": "enum",
          "ui": "select",
          "required": false,
          "data_level": 2,
          "group": "Tiếp nhận tại khoa",
          "options": [
            "Tự đi",
            "Xe lăn",
            "Cáng"
          ],
          "example": "Tự đi"
        },
        {
          "field_id": "khoa_gui",
          "label": "Đơn vị chuyển đến",
          "type": "string",
          "ui": "text",
          "required": false,
          "data_level": 2,
          "group": "Tiếp nhận tại khoa",
          "example": "Khoa khám bệnh mô phỏng"
        },
        {
          "field_id": "ly_do_vao_vien",
          "label": "Lý do vào viện",
          "type": "string",
          "ui": "textarea",
          "required": true,
          "data_level": 2,
          "group": "Hỏi bệnh",
          "example": "Đau bụng vùng thượng vị."
        },
        {
          "field_id": "benh_su",
          "label": "Bệnh sử",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Hỏi bệnh",
          "example": "Đau âm ỉ từ tối hôm trước, tăng sau ăn."
        },
        {
          "field_id": "nguon_tiep_nhan",
          "label": "Nguồn tiếp nhận",
          "type": "enum",
          "ui": "select",
          "required": false,
          "data_level": 2,
          "group": "Hỏi bệnh",
          "options": [
            "Khoa khám bệnh",
            "Khoa cấp cứu",
            "Chuyển khoa"
          ],
          "example": "Khoa khám bệnh"
        },
        {
          "field_id": "khoi_phat",
          "label": "Thời điểm khởi phát",
          "type": "string",
          "ui": "text",
          "required": false,
          "data_level": 2,
          "group": "Hỏi bệnh",
          "example": "Tối trước ngày nhập viện"
        },
        {
          "field_id": "dien_tien",
          "label": "Diễn tiến trước nhập viện",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Hỏi bệnh",
          "example": "Đau từng đợt và ăn ít hơn so với thường ngày."
        },
        {
          "field_id": "xu_tri_truoc_vien",
          "label": "Xử trí trước khi đến viện",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Hỏi bệnh",
          "example": "Đã nghỉ tại nhà và đến khám khi còn khó chịu."
        },
        {
          "field_id": "trieu_chung_kem",
          "label": "Triệu chứng đi kèm",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Hỏi bệnh",
          "example": "Buồn nôn thoáng qua sau ăn."
        },
        {
          "field_id": "tien_su_ban_than",
          "label": "Tiền sử bản thân",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Tiền sử và dị ứng",
          "example": "Từng phẫu thuật bụng theo lời kể của người bệnh mẫu."
        },
        {
          "field_id": "tien_su_gia_dinh",
          "label": "Tiền sử gia đình",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Tiền sử và dị ứng",
          "example": "Chưa ghi nhận bệnh tương tự trong gia đình."
        },
        {
          "field_id": "tien_su_di_ung",
          "label": "Tiền sử dị ứng",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Tiền sử và dị ứng",
          "example": "Người bệnh chưa nhớ rõ tên tác nhân."
        },
        {
          "field_id": "thuoc_truoc_vien",
          "label": "Thuốc dùng trước nhập viện",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Tiền sử và dị ứng",
          "example": "Chưa mang theo danh sách thuốc khi vào khoa."
        },
        {
          "field_id": "chan_doan",
          "label": "Chẩn đoán",
          "type": "string",
          "ui": "textarea",
          "required": true,
          "data_level": 2,
          "group": "Khám và nhận định",
          "example": "Đau bụng đang theo dõi nguyên nhân."
        },
        {
          "field_id": "kham_ban_dau",
          "label": "Khám ban đầu",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Khám và nhận định",
          "example": "Người bệnh tỉnh, trả lời được câu hỏi."
        },
        {
          "field_id": "kham_tuan_hoan",
          "label": "Khám tuần hoàn",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Khám và nhận định",
          "example": "Chi ấm, mạch ngoại vi bắt được."
        },
        {
          "field_id": "kham_ho_hap",
          "label": "Khám hô hấp",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Khám và nhận định",
          "example": "Lồng ngực di động đều khi quan sát."
        },
        {
          "field_id": "kham_bung",
          "label": "Khám bụng",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Khám và nhận định",
          "example": "Bụng mềm, người bệnh chỉ vị trí khó chịu vùng thượng vị."
        },
        {
          "field_id": "ket_qua_mang_theo",
          "label": "Kết quả cận lâm sàng mang theo",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Khám và nhận định",
          "example": "Chưa có kết quả kèm giấy tiếp nhận mẫu."
        },
        {
          "field_id": "van_de_theo_doi",
          "label": "Vấn đề cần theo dõi",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Kế hoạch tại khoa",
          "example": "Diễn biến đau bụng và khả năng ăn uống."
        },
        {
          "field_id": "ke_hoach_ban_dau",
          "label": "Kế hoạch ghi trong hồ sơ",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Kế hoạch tại khoa",
          "example": "Đã mở bảng theo dõi và bàn giao cho ca tiếp nhận."
        },
        {
          "field_id": "trao_doi_vao_khoa",
          "label": "Nội dung đã trao đổi",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Kế hoạch tại khoa",
          "example": "Người bệnh đã được giới thiệu khu vực buồng bệnh và cách gọi hỗ trợ."
        }
      ]
    },
    "benh_an_ra_vien": {
      "title": "Tóm tắt bệnh án ra viện",
      "aliases": [
        "tóm tắt ra viện",
        "bệnh án ra viện",
        "ra viện"
      ],
      "fields": [
        {
          "field_id": "ten_benh_nhan",
          "label": "Tên bệnh nhân",
          "type": "string",
          "ui": "text",
          "required": false,
          "data_level": 1,
          "group": "Tổng kết đợt điều trị",
          "example": "[TÊN]"
        },
        {
          "field_id": "chan_doan_ra_vien",
          "label": "Chẩn đoán ra viện",
          "type": "string",
          "ui": "textarea",
          "required": true,
          "data_level": 2,
          "group": "Tổng kết đợt điều trị",
          "example": "Đau bụng đã cải thiện."
        },
        {
          "field_id": "qua_trinh",
          "label": "Quá trình điều trị",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Tổng kết đợt điều trị",
          "example": "Đã theo dõi diễn biến và ghi nhận đáp ứng trong hồ sơ mẫu."
        },
        {
          "field_id": "tinh_trang_ra_vien",
          "label": "Tình trạng lúc ra viện",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Tổng kết đợt điều trị",
          "example": "Tỉnh, tự đi lại trong phòng."
        },
        {
          "field_id": "ly_do_nhap",
          "label": "Lý do vào điều trị",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Tổng kết đợt điều trị",
          "example": "Đau bụng và ăn uống kém trước khi nhập khoa."
        },
        {
          "field_id": "chan_doan_vao",
          "label": "Chẩn đoán lúc vào khoa",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Tổng kết đợt điều trị",
          "example": "Đau bụng đang theo dõi nguyên nhân."
        },
        {
          "field_id": "ket_qua_kham",
          "label": "Dấu hiệu nổi bật trong đợt điều trị",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Tổng kết đợt điều trị",
          "example": "Người bệnh khó chịu vùng thượng vị, tăng sau ăn."
        },
        {
          "field_id": "can_lam_sang",
          "label": "Tóm tắt kết quả cận lâm sàng",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Tổng kết đợt điều trị",
          "example": "Đã đối chiếu phiếu kết quả mô phỏng trong bệnh án."
        },
        {
          "field_id": "thu_thuat",
          "label": "Thủ thuật trong đợt điều trị",
          "type": "string",
          "ui": "text",
          "required": false,
          "data_level": 2,
          "group": "Tổng kết đợt điều trị",
          "example": "Chưa ghi nhận thủ thuật trong hồ sơ mẫu."
        },
        {
          "field_id": "dien_bien_chinh",
          "label": "Diễn biến qua các ngày",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Tổng kết đợt điều trị",
          "example": "Ăn uống và đi lại cải thiện dần trong những ngày cuối."
        },
        {
          "field_id": "an_uong_ra_vien",
          "label": "Khả năng ăn uống lúc ra viện",
          "type": "enum",
          "ui": "select",
          "required": false,
          "data_level": 2,
          "group": "Đánh giá khi ra viện",
          "options": [
            "Tự ăn",
            "Cần hỗ trợ",
            "Chưa đánh giá"
          ],
          "example": "Tự ăn"
        },
        {
          "field_id": "van_dong_ra_vien",
          "label": "Khả năng đi lại lúc ra viện",
          "type": "enum",
          "ui": "select",
          "required": false,
          "data_level": 2,
          "group": "Đánh giá khi ra viện",
          "options": [
            "Tự đi lại",
            "Có người dìu",
            "Dùng xe lăn"
          ],
          "example": "Tự đi lại"
        },
        {
          "field_id": "van_de_con_lai",
          "label": "Vấn đề còn theo dõi",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Đánh giá khi ra viện",
          "example": "Còn mệt nhẹ khi đi bộ lâu."
        },
        {
          "field_id": "huong_dieu_tri",
          "label": "Hướng điều trị",
          "type": "string",
          "ui": "textarea",
          "required": true,
          "data_level": 2,
          "group": "Bàn giao sau ra viện",
          "example": "Đã bàn giao kế hoạch theo dõi trong hồ sơ mẫu."
        },
        {
          "field_id": "hinh_thuc",
          "label": "Hình thức ra viện",
          "type": "enum",
          "ui": "select",
          "required": false,
          "data_level": 2,
          "group": "Bàn giao sau ra viện",
          "options": [
            "Về nhà",
            "Chuyển viện"
          ],
          "example": "Về nhà"
        },
        {
          "field_id": "doi_chieu_thuoc",
          "label": "Đối chiếu danh sách thuốc",
          "type": "enum",
          "ui": "select",
          "required": false,
          "data_level": 2,
          "group": "Bàn giao sau ra viện",
          "options": [
            "Đã đối chiếu với phiếu mẫu",
            "Đang bổ sung",
            "Chưa ghi nhận"
          ],
          "example": "Đã đối chiếu với phiếu mẫu"
        },
        {
          "field_id": "giay_to",
          "label": "Giấy tờ đã bàn giao",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Bàn giao sau ra viện",
          "example": "Bản tóm tắt đợt điều trị và phiếu hẹn mô phỏng."
        },
        {
          "field_id": "nguoi_nhan_hoso",
          "label": "Người nhận hồ sơ",
          "type": "enum",
          "ui": "select",
          "required": false,
          "data_level": 2,
          "group": "Bàn giao sau ra viện",
          "options": [
            "Người bệnh",
            "Người chăm sóc",
            "Đơn vị tiếp nhận"
          ],
          "example": "Người bệnh"
        },
        {
          "field_id": "noi_tai_kham",
          "label": "Nơi hẹn tái khám",
          "type": "string",
          "ui": "text",
          "required": false,
          "data_level": 2,
          "group": "Bàn giao sau ra viện",
          "example": "Phòng khám MẪU-A"
        },
        {
          "field_id": "loi_dan",
          "label": "Nội dung đã dặn khi ra viện",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Bàn giao sau ra viện",
          "example": "Đã chỉ vị trí thông tin hẹn và kênh liên hệ trên phiếu mẫu."
        },
        {
          "field_id": "xac_nhan_hieu",
          "label": "Xác nhận của người nhận",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Bàn giao sau ra viện",
          "example": "Người nhận nhắc lại được nơi tái khám."
        }
      ]
    },
    "phieu_theo_doi_sau_mo": {
      "title": "Theo dõi sau mổ",
      "aliases": [
        "theo dõi sau mổ",
        "sau mổ"
      ],
      "fields": [
        {
          "field_id": "ten_benh_nhan",
          "label": "Tên bệnh nhân",
          "type": "string",
          "ui": "text",
          "required": false,
          "data_level": 1,
          "group": "Bàn giao từ phòng mổ",
          "example": "[TÊN]"
        },
        {
          "field_id": "ten_phau_thuat",
          "label": "Phẫu thuật theo phiếu bàn giao",
          "type": "string",
          "ui": "text",
          "required": false,
          "data_level": 2,
          "group": "Bàn giao từ phòng mổ",
          "example": "Phẫu thuật bụng mô phỏng"
        },
        {
          "field_id": "vo_cam",
          "label": "Phương pháp vô cảm đã ghi",
          "type": "enum",
          "ui": "select",
          "required": false,
          "data_level": 2,
          "group": "Bàn giao từ phòng mổ",
          "options": [
            "Gây mê",
            "Gây tê vùng",
            "Gây tê tại chỗ"
          ],
          "example": "Gây mê"
        },
        {
          "field_id": "don_vi_gui",
          "label": "Đơn vị bàn giao",
          "type": "string",
          "ui": "text",
          "required": false,
          "data_level": 2,
          "group": "Bàn giao từ phòng mổ",
          "example": "Buồng hồi tỉnh MẪU-A"
        },
        {
          "field_id": "duong_truyen_nhan",
          "label": "Đường truyền khi tiếp nhận",
          "type": "enum",
          "ui": "select",
          "required": false,
          "data_level": 2,
          "group": "Bàn giao từ phòng mổ",
          "options": [
            "Ngoại vi",
            "Trung tâm",
            "Chưa ghi nhận"
          ],
          "example": "Ngoại vi"
        },
        {
          "field_id": "dau_hieu",
          "label": "Dấu hiệu theo dõi",
          "type": "string",
          "ui": "textarea",
          "required": true,
          "data_level": 2,
          "group": "Đánh giá sau mổ",
          "example": "Tỉnh, tiếp xúc được khi gọi hỏi."
        },
        {
          "field_id": "thoi_diem_theo_doi",
          "label": "Thời điểm theo dõi",
          "type": "datetime",
          "ui": "datetime",
          "required": false,
          "data_level": 2,
          "group": "Đánh giá sau mổ"
        },
        {
          "field_id": "vet_mo",
          "label": "Tình trạng băng vết mổ",
          "type": "enum",
          "ui": "select",
          "required": false,
          "data_level": 2,
          "group": "Đánh giá sau mổ",
          "options": [
            "Khô",
            "Thấm dịch",
            "Đã thay băng"
          ],
          "example": "Khô"
        },
        {
          "field_id": "tinh_tao",
          "label": "Mức tỉnh khi gọi hỏi",
          "type": "enum",
          "ui": "select",
          "required": false,
          "data_level": 2,
          "group": "Đánh giá sau mổ",
          "options": [
            "Tỉnh, tiếp xúc được",
            "Buồn ngủ, gọi đáp ứng",
            "Chưa đánh giá"
          ],
          "example": "Tỉnh, tiếp xúc được"
        },
        {
          "field_id": "ho_hap_sau_mo",
          "label": "Hô hấp lúc theo dõi",
          "type": "enum",
          "ui": "select",
          "required": false,
          "data_level": 2,
          "group": "Đánh giá sau mổ",
          "options": [
            "Tự thở khí phòng",
            "Đang hỗ trợ oxy",
            "Theo hồ sơ bàn giao"
          ],
          "example": "Tự thở khí phòng"
        },
        {
          "field_id": "mach_sau_mo",
          "label": "Mạch khi theo dõi",
          "type": "number",
          "ui": "number",
          "required": false,
          "data_level": 2,
          "group": "Đánh giá sau mổ",
          "example": 84,
          "unit": "lần/phút",
          "min": 0
        },
        {
          "field_id": "huyet_ap_sau_mo",
          "label": "Huyết áp khi theo dõi",
          "type": "string",
          "ui": "text",
          "required": false,
          "data_level": 2,
          "group": "Đánh giá sau mổ",
          "example": "116/74 mmHg"
        },
        {
          "field_id": "diem_dau_sau_mo",
          "label": "Điểm đau khi nghỉ",
          "type": "number",
          "ui": "number",
          "required": false,
          "data_level": 2,
          "group": "Đánh giá sau mổ",
          "example": 3,
          "unit": "điểm",
          "min": 0,
          "max": 10
        },
        {
          "field_id": "buon_non",
          "label": "Buồn nôn sau mổ",
          "type": "enum",
          "ui": "select",
          "required": false,
          "data_level": 2,
          "group": "Đánh giá sau mổ",
          "options": [
            "Chưa ghi nhận",
            "Có cảm giác buồn nôn",
            "Đã nôn"
          ],
          "example": "Chưa ghi nhận"
        },
        {
          "field_id": "bai_tiet",
          "label": "Theo dõi bài tiết sau mổ",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Chăm sóc sau mổ",
          "example": "Đã ghi nhận lần tiểu đầu sau khi về khoa."
        },
        {
          "field_id": "tu_the",
          "label": "Tư thế hiện tại",
          "type": "enum",
          "ui": "select",
          "required": false,
          "data_level": 2,
          "group": "Chăm sóc sau mổ",
          "options": [
            "Nằm ngửa",
            "Nằm nghiêng",
            "Ngồi có hỗ trợ"
          ],
          "example": "Nằm ngửa"
        },
        {
          "field_id": "van_dong_sau_mo",
          "label": "Mức vận động đã thực hiện",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Chăm sóc sau mổ",
          "example": "Đã ngồi dậy có người đỡ."
        },
        {
          "field_id": "dan_luu",
          "label": "Ghi nhận dẫn lưu",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Bàn giao",
          "example": "Chưa ghi nhận dẫn lưu trong ca mẫu."
        },
        {
          "field_id": "dien_bien",
          "label": "Diễn biến trong ca",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Bàn giao",
          "example": "Người bệnh đã ngồi dậy có hỗ trợ."
        },
        {
          "field_id": "noi_dung_theo_doi",
          "label": "Điểm cần tiếp tục theo dõi",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Bàn giao",
          "example": "Đối chiếu tình trạng băng vết mổ ở lần theo dõi sau."
        }
      ]
    },
    "phieu_giao_duc_suc_khoe": {
      "title": "Giáo dục sức khỏe",
      "aliases": [
        "giáo dục sức khỏe"
      ],
      "fields": [
        {
          "field_id": "ten_benh_nhan",
          "label": "Tên bệnh nhân",
          "type": "string",
          "ui": "text",
          "required": false,
          "data_level": 1,
          "group": "Chuẩn bị buổi hướng dẫn",
          "example": "[TÊN]"
        },
        {
          "field_id": "thoi_diem_huong_dan",
          "label": "Thời điểm hướng dẫn",
          "type": "datetime",
          "ui": "datetime",
          "required": false,
          "data_level": 2,
          "group": "Chuẩn bị buổi hướng dẫn"
        },
        {
          "field_id": "nhu_cau_hoc",
          "label": "Nhu cầu người nhận nêu ra",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Chuẩn bị buổi hướng dẫn",
          "example": "Muốn biết cách gọi hỗ trợ khi cần rời giường."
        },
        {
          "field_id": "kien_thuc_ban_dau",
          "label": "Hiểu biết trước buổi hướng dẫn",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Chuẩn bị buổi hướng dẫn",
          "example": "Biết vị trí chuông nhưng chưa từng dùng."
        },
        {
          "field_id": "kha_nang_tiep_nhan",
          "label": "Khả năng tiếp nhận",
          "type": "enum",
          "ui": "select",
          "required": false,
          "data_level": 2,
          "group": "Chuẩn bị buổi hướng dẫn",
          "options": [
            "Tự trao đổi",
            "Cần người hỗ trợ",
            "Cần nhắc lại nhiều lần"
          ],
          "example": "Tự trao đổi"
        },
        {
          "field_id": "muc_tieu",
          "label": "Mục tiêu buổi hướng dẫn",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Chuẩn bị buổi hướng dẫn",
          "example": "Người nhận tự thao tác được chuông gọi tại giường."
        },
        {
          "field_id": "noi_dung",
          "label": "Nội dung giáo dục",
          "type": "string",
          "ui": "textarea",
          "required": true,
          "data_level": 2,
          "group": "Buổi hướng dẫn",
          "example": "Cách sử dụng chuông gọi tại giường."
        },
        {
          "field_id": "nguoi_nhan",
          "label": "Người nhận giáo dục",
          "type": "string",
          "ui": "text",
          "required": true,
          "data_level": 2,
          "group": "Buổi hướng dẫn",
          "example": "Người bệnh"
        },
        {
          "field_id": "hinh_thuc",
          "label": "Hình thức hướng dẫn",
          "type": "enum",
          "ui": "select",
          "required": false,
          "data_level": 2,
          "group": "Buổi hướng dẫn",
          "options": [
            "Trực tiếp tại giường",
            "Qua tài liệu mẫu"
          ],
          "example": "Trực tiếp tại giường"
        },
        {
          "field_id": "dia_diem",
          "label": "Địa điểm thực hiện",
          "type": "string",
          "ui": "text",
          "required": false,
          "data_level": 2,
          "group": "Buổi hướng dẫn",
          "example": "Buồng bệnh MẪU-A"
        },
        {
          "field_id": "nguoi_day",
          "label": "Mã người hướng dẫn",
          "type": "string",
          "ui": "text",
          "required": false,
          "data_level": 2,
          "group": "Buổi hướng dẫn",
          "example": "ĐD-MẪU-B"
        },
        {
          "field_id": "hoc_lieu",
          "label": "Tài liệu hoặc dụng cụ minh họa",
          "type": "string",
          "ui": "text",
          "required": false,
          "data_level": 2,
          "group": "Buổi hướng dẫn",
          "example": "Chuông gọi tại giường mẫu"
        },
        {
          "field_id": "thoi_luong",
          "label": "Thời lượng buổi hướng dẫn",
          "type": "number",
          "ui": "number",
          "required": false,
          "data_level": 2,
          "group": "Buổi hướng dẫn",
          "example": 10,
          "unit": "phút",
          "min": 0
        },
        {
          "field_id": "phan_hoi",
          "label": "Phản hồi của người nhận",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Đánh giá tiếp nhận",
          "example": "Đã thực hành lại thao tác gọi hỗ trợ."
        },
        {
          "field_id": "kiem_tra_hieu",
          "label": "Cách kiểm tra mức độ hiểu",
          "type": "enum",
          "ui": "select",
          "required": false,
          "data_level": 2,
          "group": "Đánh giá tiếp nhận",
          "options": [
            "Thực hành lại",
            "Nhắc lại bằng lời",
            "Đặt câu hỏi"
          ],
          "example": "Thực hành lại"
        },
        {
          "field_id": "ket_qua_hoc",
          "label": "Kết quả sau hướng dẫn",
          "type": "enum",
          "ui": "select",
          "required": false,
          "data_level": 2,
          "group": "Đánh giá tiếp nhận",
          "options": [
            "Đã tự thực hiện",
            "Cần hỗ trợ",
            "Cần hướng dẫn lại"
          ],
          "example": "Đã tự thực hiện"
        },
        {
          "field_id": "cau_hoi",
          "label": "Câu hỏi còn lại",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Đánh giá tiếp nhận",
          "example": "Người nhận hỏi cách nhận biết tín hiệu đã gửi."
        },
        {
          "field_id": "noi_dung_nhac",
          "label": "Nội dung cần củng cố",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Đánh giá tiếp nhận",
          "example": "Nhắc lại vị trí đặt chuông sau khi di chuyển giường."
        }
      ]
    },
    "phieu_danh_gia_loet": {
      "title": "Đánh giá nguy cơ loét tì đè",
      "aliases": [
        "đánh giá loét",
        "nguy cơ loét",
        "loét"
      ],
      "fields": [
        {
          "field_id": "ten_benh_nhan",
          "label": "Tên bệnh nhân",
          "type": "string",
          "ui": "text",
          "required": false,
          "data_level": 1,
          "group": "Bối cảnh đánh giá",
          "example": "[TÊN]"
        },
        {
          "field_id": "gio_danh_gia_da",
          "label": "Thời điểm kiểm tra da",
          "type": "datetime",
          "ui": "datetime",
          "required": false,
          "data_level": 2,
          "group": "Bối cảnh đánh giá"
        },
        {
          "field_id": "ly_do_kiem_tra",
          "label": "Lý do kiểm tra",
          "type": "enum",
          "ui": "select",
          "required": false,
          "data_level": 2,
          "group": "Bối cảnh đánh giá",
          "options": [
            "Đầu ca",
            "Tiếp nhận vào khoa",
            "Khi thay đổi vận động"
          ],
          "example": "Đầu ca"
        },
        {
          "field_id": "tu_the_quan_sat",
          "label": "Tư thế lúc quan sát",
          "type": "enum",
          "ui": "select",
          "required": false,
          "data_level": 2,
          "group": "Bối cảnh đánh giá",
          "options": [
            "Nằm nghiêng có hỗ trợ",
            "Nằm ngửa",
            "Ngồi"
          ],
          "example": "Nằm nghiêng có hỗ trợ"
        },
        {
          "field_id": "diem_braden",
          "label": "Điểm Braden",
          "type": "number",
          "ui": "number",
          "required": true,
          "data_level": 2,
          "group": "Đánh giá da",
          "unit": "điểm",
          "example": 18,
          "min": 6,
          "max": 23
        },
        {
          "field_id": "vi_tri",
          "label": "Vị trí quan sát",
          "type": "string",
          "ui": "text",
          "required": false,
          "data_level": 2,
          "group": "Đánh giá da",
          "example": "Vùng gót chân"
        },
        {
          "field_id": "tinh_trang_da",
          "label": "Tình trạng da",
          "type": "enum",
          "ui": "select",
          "required": false,
          "data_level": 2,
          "group": "Đánh giá da",
          "options": [
            "Nguyên vẹn",
            "Đỏ da",
            "Có tổn thương"
          ],
          "example": "Nguyên vẹn"
        },
        {
          "field_id": "mau_sac_da",
          "label": "Màu da ở vùng quan sát",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Đánh giá da",
          "example": "Chưa ghi nhận thay đổi màu ở hai gót."
        },
        {
          "field_id": "do_am_da",
          "label": "Độ ẩm tại vùng quan sát",
          "type": "enum",
          "ui": "select",
          "required": false,
          "data_level": 2,
          "group": "Đánh giá da",
          "options": [
            "Khô",
            "Hơi ẩm",
            "Ẩm nhiều"
          ],
          "example": "Khô"
        },
        {
          "field_id": "da_dung_cu",
          "label": "Da tại vị trí tiếp xúc dụng cụ",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Đánh giá da",
          "example": "Da vùng tiếp xúc với dây cố định còn nguyên vẹn."
        },
        {
          "field_id": "cam_nhan",
          "label": "Khả năng báo khó chịu",
          "type": "enum",
          "ui": "select",
          "required": false,
          "data_level": 2,
          "group": "Yếu tố tì đè",
          "options": [
            "Báo được bằng lời",
            "Cần gợi hỏi",
            "Chưa đánh giá"
          ],
          "example": "Báo được bằng lời"
        },
        {
          "field_id": "hoat_dong",
          "label": "Mức hoạt động trong ca",
          "type": "enum",
          "ui": "select",
          "required": false,
          "data_level": 2,
          "group": "Yếu tố tì đè",
          "options": [
            "Chủ yếu tại giường",
            "Có đi lại",
            "Ngồi ghế"
          ],
          "example": "Chủ yếu tại giường"
        },
        {
          "field_id": "xoay_tro",
          "label": "Khả năng tự xoay trở",
          "type": "enum",
          "ui": "select",
          "required": false,
          "data_level": 2,
          "group": "Yếu tố tì đè",
          "options": [
            "Cần trợ giúp",
            "Tự xoay trở",
            "Phụ thuộc hoàn toàn"
          ],
          "example": "Cần trợ giúp"
        },
        {
          "field_id": "an_trong_ca",
          "label": "Khẩu phần đã ăn trong ca",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Yếu tố tì đè",
          "example": "Đã ăn khoảng nửa suất mô phỏng."
        },
        {
          "field_id": "ma_sat",
          "label": "Ma sát khi di chuyển",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Yếu tố tì đè",
          "example": "Cần trợ giúp khi dịch chuyển trên giường."
        },
        {
          "field_id": "ghi_nhan",
          "label": "Ghi nhận trong ca",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Theo dõi",
          "example": "Đã ghi tình trạng da khi bàn giao ca."
        },
        {
          "field_id": "ho_tro_giam_ty",
          "label": "Biện pháp giảm tì đã thực hiện",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Theo dõi",
          "example": "Đã kê đỡ vùng gót và ghi nhận tư thế sau chăm sóc."
        },
        {
          "field_id": "phan_hoi_da",
          "label": "Phản hồi của người bệnh",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Theo dõi",
          "example": "Người bệnh cho biết vùng gót dễ chịu hơn."
        },
        {
          "field_id": "ban_giao_da",
          "label": "Vùng cần kiểm tra ở ca sau",
          "type": "string",
          "ui": "textarea",
          "required": false,
          "data_level": 2,
          "group": "Theo dõi",
          "example": "Đối chiếu lại da hai gót và vị trí dây cố định."
        }
      ]
    }
  },
  "users": [
    {
      "id": "bs_a",
      "label": "Bác sĩ A (dữ liệu giả)",
      "role": "bac_si"
    },
    {
      "id": "dd_b",
      "label": "Điều dưỡng B (dữ liệu giả)",
      "role": "dieu_duong"
    }
  ],
  "patients": [
    {
      "patient_id": "BN-01",
      "name": "BN-01 (giả)",
      "bed": "G1-01",
      "doctor": "bs_a",
      "nurse": "dd_b",
      "events": [
        {
          "event": "admission",
          "at": "2026-11-15T08:00:00+07:00"
        },
        {
          "event": "surgery_end",
          "at": "2026-11-15T13:30:00+07:00"
        },
        {
          "event": "medication_given",
          "at": "2026-11-16T09:00:00+07:00",
          "route": "tiem",
          "purpose": "giam_dau"
        }
      ]
    },
    {
      "patient_id": "BN-02",
      "name": "BN-02 (giả)",
      "bed": "G1-02",
      "doctor": "bs_a",
      "nurse": "dd_b",
      "events": [
        {
          "event": "admission",
          "at": "2026-11-14T09:00:00+07:00"
        },
        {
          "event": "surgery_end",
          "at": "2026-11-14T15:00:00+07:00"
        }
      ]
    },
    {
      "patient_id": "BN-03",
      "name": "BN-03 (giả)",
      "bed": "G1-03",
      "doctor": "bs_a",
      "nurse": "dd_b",
      "events": [
        {
          "event": "admission",
          "at": "2026-11-13T10:00:00+07:00"
        },
        {
          "event": "surgery_end",
          "at": "2026-11-13T14:00:00+07:00"
        }
      ]
    },
    {
      "patient_id": "BN-04",
      "name": "BN-04 (giả)",
      "bed": "G2-01",
      "doctor": "bs_a",
      "nurse": "dd_b",
      "events": [
        {
          "event": "admission",
          "at": "2026-11-12T08:30:00+07:00"
        },
        {
          "event": "surgery_end",
          "at": "2026-11-12T11:00:00+07:00"
        }
      ]
    },
    {
      "patient_id": "BN-05",
      "name": "BN-05 (giả)",
      "bed": "G2-02",
      "doctor": "bs_a",
      "nurse": "dd_b",
      "events": [
        {
          "event": "admission",
          "at": "2026-11-10T09:00:00+07:00"
        },
        {
          "event": "surgery_end",
          "at": "2026-11-10T12:00:00+07:00"
        },
        {
          "event": "discharge",
          "at": "2026-11-15T15:00:00+07:00"
        }
      ]
    },
    {
      "patient_id": "BN-06",
      "name": "BN-06 (giả)",
      "bed": "G2-03",
      "doctor": "bs_a",
      "nurse": "dd_b",
      "events": [
        {
          "event": "admission",
          "at": "2026-11-11T10:00:00+07:00"
        },
        {
          "event": "surgery_end",
          "at": "2026-11-11T13:00:00+07:00"
        },
        {
          "event": "discharge",
          "at": "2026-11-16T08:00:00+07:00"
        }
      ]
    }
  ],
  "records": [
    {
      "record_id": "REC-0001",
      "patient_id": "BN-01",
      "form_id": "benh_an_vao_vien",
      "at": "2026-11-15T09:00:00+07:00",
      "values": {
        "ly_do_vao_vien": "Đau bụng vùng thượng vị",
        "benh_su": "Đau từ tối hôm trước, tăng sau ăn.",
        "nguon_tiep_nhan": "Khoa cấp cứu",
        "kham_ban_dau": "Tỉnh, trả lời được câu hỏi.",
        "chan_doan": "Viêm tụy cấp (giả)"
      },
      "user": "bs_a",
      "source": "emr",
      "missing_required": []
    },
    {
      "record_id": "REC-0002",
      "patient_id": "BN-02",
      "form_id": "phieu_danh_gia_ban_dau",
      "at": "2026-11-14T10:00:00+07:00",
      "values": {
        "di_ung": "Penicillin",
        "tu_cham_soc": "Cần hỗ trợ một phần"
      },
      "user": "dd_b",
      "source": "emr",
      "missing_required": [
        "nguoi_lien_he"
      ]
    },
    {
      "record_id": "REC-0003",
      "patient_id": "BN-01",
      "form_id": "phieu_sinh_ton_nguoi_lon",
      "at": "2026-11-16T06:15:00+07:00",
      "values": {
        "mach": 84,
        "nhip_tho": 19,
        "huyet_ap": "116/74",
        "nhiet_do": 37.1,
        "spo2": 98,
        "thoi_diem_do": "2026-11-16T06:10",
        "tu_the_do": "Nằm"
      },
      "user": "dd_b",
      "source": "emr",
      "missing_required": []
    }
  ],
  "regulations": {
    "qd_chamsoc_v1.txt": "QUYẾT ĐỊNH NỘI BỘ – QUY ĐỊNH CHĂM SÓC (DỮ LIỆU GIẢ, PROTOTYPE)\nMã văn bản: QD-CHAMSOC-2026 · Phiên bản: v1 · Hiệu lực từ: 10/11/2026\n\nĐiều 1. Bệnh án\n1.1 Bác sĩ phải lập phiếu bệnh án vào viện trong vòng 24 giờ kể từ khi bệnh nhân vào viện. Trường bắt buộc: lý do vào viện, chẩn đoán.\n1.2 Bác sĩ phải lập phiếu tóm tắt ra viện trong ngày khi bệnh nhân ra viện. Trường bắt buộc: chẩn đoán ra viện, hướng điều trị.\n\nĐiều 2. Theo dõi sau mổ\n2.1 Bác sĩ phải lập phiếu theo dõi sau mổ theo lịch: 1, 1, 2, 2, 2, 4, 4, 4, 4 giờ, tính từ lúc kết thúc phẫu thuật. Trường bắt buộc: dấu hiệu theo dõi.\n\nĐiều 3. Điều dưỡng\n3.1 Điều dưỡng phải lập phiếu sinh tồn mỗi 4 giờ một lần, tính từ lần nhập gần nhất. Trường bắt buộc: mạch, nhịp thở.\n3.2 Điều dưỡng phải lập phiếu chăm sóc tối thiểu 4 lần mỗi ngày. Trường bắt buộc: nội dung chăm sóc, người thực hiện.\n3.3 Điều dưỡng phải đánh giá nguy cơ ngã trước 12:00 mỗi ngày. Trường bắt buộc: điểm nguy cơ ngã, kết quả.\n3.4 Điều dưỡng phải lập phiếu đánh giá ban đầu trong vòng 24 giờ kể từ khi bệnh nhân vào viện. Trường bắt buộc: dị ứng, người liên hệ.\n\nĐiều 4. Đánh giá đau\n4.1 Điều dưỡng phải lập phiếu đánh giá đau sau 30 phút khi dùng thuốc tiêm, truyền giảm đau. Trường bắt buộc: điểm đau, thời điểm đánh giá.\n",
    "qd_chamsoc_v2.txt": "QUYẾT ĐỊNH NỘI BỘ – QUY ĐỊNH CHĂM SÓC (DỮ LIỆU GIẢ, PROTOTYPE)\nMã văn bản: QD-CHAMSOC-2026 · Phiên bản: v2 · Hiệu lực từ: 16/11/2026\n\nĐiều 1. Bệnh án\n1.1 Bác sĩ phải lập phiếu bệnh án vào viện trong ngày kể từ khi bệnh nhân vào viện. Trường bắt buộc: lý do vào viện, chẩn đoán.\n1.2 Bác sĩ phải lập phiếu tóm tắt ra viện trong ngày khi bệnh nhân ra viện. Trường bắt buộc: chẩn đoán ra viện, hướng điều trị.\n1.3 Bác sĩ phải lập phiếu giáo dục sức khỏe khi bệnh nhân ra viện. Trường bắt buộc: nội dung giáo dục, người nhận giáo dục.\n\nĐiều 2. Theo dõi sau mổ\n2.1 Bác sĩ phải lập phiếu theo dõi sau mổ theo lịch: 1, 1, 2, 2, 2, 4, 4, 4, 4 giờ, tính từ lúc kết thúc phẫu thuật. Trường bắt buộc: dấu hiệu theo dõi.\n2.2 Bác sĩ phải lập phiếu theo dõi sau mổ khoảng 6 giờ một lần trong ngày thứ hai. Trường bắt buộc: dấu hiệu theo dõi.\n\nĐiều 3. Điều dưỡng\n3.1 Điều dưỡng phải lập phiếu sinh tồn mỗi 4 giờ một lần, tính từ lần nhập gần nhất. Trường bắt buộc: mạch, nhịp thở.\n3.2 Điều dưỡng phải lập phiếu chăm sóc tối thiểu 4 lần mỗi ngày. Trường bắt buộc: nội dung chăm sóc, người thực hiện.\n3.3 Điều dưỡng phải đánh giá nguy cơ ngã trước 12:00 mỗi ngày. Trường bắt buộc: điểm nguy cơ ngã, kết quả.\n3.4 Điều dưỡng phải lập phiếu đánh giá ban đầu trong vòng 24 giờ kể từ khi bệnh nhân vào viện. Trường bắt buộc: dị ứng, người liên hệ.\n\nĐiều 4. Đánh giá đau\n4.1 Điều dưỡng phải lập phiếu đánh giá đau sau 30 phút khi dùng thuốc tiêm, truyền giảm đau. Trường bắt buộc: điểm đau, thời điểm đánh giá.\n\nĐiều 5. Đánh giá loét\n5.1 Điều dưỡng phải lập phiếu đánh giá loét tối thiểu 1 lần mỗi ngày. Trường bắt buộc: điểm Braden.\n"
  }
};
