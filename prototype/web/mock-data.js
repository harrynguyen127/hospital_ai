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
     "field_id": "mach",
     "label": "Mạch",
     "type": "number",
     "ui": "number",
     "required": true,
     "data_level": 2
    },
    {
     "field_id": "nhip_tho",
     "label": "Nhịp thở",
     "type": "number",
     "ui": "number",
     "required": true,
     "data_level": 2
    },
    {
     "field_id": "huyet_ap",
     "label": "Huyết áp",
     "type": "string",
     "ui": "text",
     "required": false,
     "data_level": 2
    },
    {
     "field_id": "nhiet_do",
     "label": "Nhiệt độ",
     "type": "number",
     "ui": "number",
     "required": false,
     "data_level": 2
    },
    {
     "field_id": "spo2",
     "label": "SpO2",
     "type": "number",
     "ui": "number",
     "required": false,
     "data_level": 2
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
     "field_id": "thuc_hien",
     "label": "Nội dung chăm sóc",
     "type": "string",
     "ui": "text",
     "required": true,
     "data_level": 2
    },
    {
     "field_id": "nguoi_thuc_hien",
     "label": "Người thực hiện",
     "type": "string",
     "ui": "text",
     "required": true,
     "data_level": 2
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
     "field_id": "diem_nga",
     "label": "Điểm nguy cơ ngã",
     "type": "number",
     "ui": "number",
     "required": true,
     "data_level": 2
    },
    {
     "field_id": "ket_qua",
     "label": "Kết quả",
     "type": "string",
     "ui": "text",
     "required": true,
     "data_level": 2
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
     "field_id": "diem_dau",
     "label": "Điểm đau",
     "type": "number",
     "ui": "number",
     "required": true,
     "data_level": 2
    },
    {
     "field_id": "thoi_diem_danh_gia",
     "label": "Thời điểm đánh giá",
     "type": "datetime",
     "ui": "datetime",
     "required": true,
     "data_level": 2
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
     "field_id": "di_ung",
     "label": "Dị ứng",
     "type": "string",
     "ui": "text",
     "required": true,
     "data_level": 2
    },
    {
     "field_id": "thuoc_dang_dung",
     "label": "Thuốc đang dùng",
     "type": "string",
     "ui": "text",
     "required": false,
     "data_level": 2
    },
    {
     "field_id": "nguoi_lien_he",
     "label": "Người liên hệ",
     "type": "string",
     "ui": "text",
     "required": true,
     "data_level": 2
    },
    {
     "field_id": "tien_su",
     "label": "Tiền sử",
     "type": "string",
     "ui": "text",
     "required": false,
     "data_level": 2
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
     "field_id": "ly_do_vao_vien",
     "label": "Lý do vào viện",
     "type": "string",
     "ui": "text",
     "required": true,
     "data_level": 2
    },
    {
     "field_id": "chan_doan",
     "label": "Chẩn đoán",
     "type": "string",
     "ui": "text",
     "required": true,
     "data_level": 2
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
     "field_id": "chan_doan_ra_vien",
     "label": "Chẩn đoán ra viện",
     "type": "string",
     "ui": "text",
     "required": true,
     "data_level": 2
    },
    {
     "field_id": "huong_dieu_tri",
     "label": "Hướng điều trị",
     "type": "string",
     "ui": "text",
     "required": true,
     "data_level": 2
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
     "field_id": "dau_hieu",
     "label": "Dấu hiệu theo dõi",
     "type": "string",
     "ui": "text",
     "required": true,
     "data_level": 2
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
     "field_id": "noi_dung",
     "label": "Nội dung giáo dục",
     "type": "string",
     "ui": "text",
     "required": true,
     "data_level": 2
    },
    {
     "field_id": "nguoi_nhan",
     "label": "Người nhận giáo dục",
     "type": "string",
     "ui": "text",
     "required": true,
     "data_level": 2
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
     "field_id": "diem_braden",
     "label": "Điểm Braden",
     "type": "number",
     "ui": "number",
     "required": true,
     "data_level": 2
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
    "di_ung": "Penicillin"
   },
   "user": "dd_b",
   "source": "emr",
   "missing_required": [
    "nguoi_lien_he"
   ]
  }
 ],
 "regulations": {
  "qd_chamsoc_v1.txt": "QUYẾT ĐỊNH NỘI BỘ – QUY ĐỊNH CHĂM SÓC (DỮ LIỆU GIẢ, PROTOTYPE)\nMã văn bản: QD-CHAMSOC-2026 · Phiên bản: v1 · Hiệu lực từ: 10/11/2026\n\nĐiều 1. Bệnh án\n1.1 Bác sĩ phải lập phiếu bệnh án vào viện trong vòng 24 giờ kể từ khi bệnh nhân vào viện. Trường bắt buộc: lý do vào viện, chẩn đoán.\n1.2 Bác sĩ phải lập phiếu tóm tắt ra viện trong ngày khi bệnh nhân ra viện. Trường bắt buộc: chẩn đoán ra viện, hướng điều trị.\n\nĐiều 2. Theo dõi sau mổ\n2.1 Bác sĩ phải lập phiếu theo dõi sau mổ theo lịch: 1, 1, 2, 2, 2, 4, 4, 4, 4 giờ, tính từ lúc kết thúc phẫu thuật. Trường bắt buộc: dấu hiệu theo dõi.\n\nĐiều 3. Điều dưỡng\n3.1 Điều dưỡng phải lập phiếu sinh tồn mỗi 4 giờ một lần, tính từ lần nhập gần nhất. Trường bắt buộc: mạch, nhịp thở.\n3.2 Điều dưỡng phải lập phiếu chăm sóc tối thiểu 4 lần mỗi ngày. Trường bắt buộc: nội dung chăm sóc, người thực hiện.\n3.3 Điều dưỡng phải đánh giá nguy cơ ngã trước 12:00 mỗi ngày. Trường bắt buộc: điểm nguy cơ ngã, kết quả.\n3.4 Điều dưỡng phải lập phiếu đánh giá ban đầu trong vòng 24 giờ kể từ khi bệnh nhân vào viện. Trường bắt buộc: dị ứng, người liên hệ.\n\nĐiều 4. Đánh giá đau\n4.1 Điều dưỡng phải lập phiếu đánh giá đau sau 30 phút khi dùng thuốc tiêm, truyền giảm đau. Trường bắt buộc: điểm đau, thời điểm đánh giá.\n",
  "qd_chamsoc_v2.txt": "QUYẾT ĐỊNH NỘI BỘ – QUY ĐỊNH CHĂM SÓC (DỮ LIỆU GIẢ, PROTOTYPE)\nMã văn bản: QD-CHAMSOC-2026 · Phiên bản: v2 · Hiệu lực từ: 16/11/2026\n\nĐiều 1. Bệnh án\n1.1 Bác sĩ phải lập phiếu bệnh án vào viện trong ngày kể từ khi bệnh nhân vào viện. Trường bắt buộc: lý do vào viện, chẩn đoán.\n1.2 Bác sĩ phải lập phiếu tóm tắt ra viện trong ngày khi bệnh nhân ra viện. Trường bắt buộc: chẩn đoán ra viện, hướng điều trị.\n1.3 Bác sĩ phải lập phiếu giáo dục sức khỏe khi bệnh nhân ra viện. Trường bắt buộc: nội dung giáo dục, người nhận giáo dục.\n\nĐiều 2. Theo dõi sau mổ\n2.1 Bác sĩ phải lập phiếu theo dõi sau mổ theo lịch: 1, 1, 2, 2, 2, 4, 4, 4, 4 giờ, tính từ lúc kết thúc phẫu thuật. Trường bắt buộc: dấu hiệu theo dõi.\n2.2 Bác sĩ phải lập phiếu theo dõi sau mổ khoảng 6 giờ một lần trong ngày thứ hai. Trường bắt buộc: dấu hiệu theo dõi.\n\nĐiều 3. Điều dưỡng\n3.1 Điều dưỡng phải lập phiếu sinh tồn mỗi 4 giờ một lần, tính từ lần nhập gần nhất. Trường bắt buộc: mạch, nhịp thở.\n3.2 Điều dưỡng phải lập phiếu chăm sóc tối thiểu 4 lần mỗi ngày. Trường bắt buộc: nội dung chăm sóc, người thực hiện.\n3.3 Điều dưỡng phải đánh giá nguy cơ ngã trước 12:00 mỗi ngày. Trường bắt buộc: điểm nguy cơ ngã, kết quả.\n3.4 Điều dưỡng phải lập phiếu đánh giá ban đầu trong vòng 24 giờ kể từ khi bệnh nhân vào viện. Trường bắt buộc: dị ứng, người liên hệ.\n\nĐiều 4. Đánh giá đau\n4.1 Điều dưỡng phải lập phiếu đánh giá đau sau 30 phút khi dùng thuốc tiêm, truyền giảm đau. Trường bắt buộc: điểm đau, thời điểm đánh giá.\n\nĐiều 5. Đánh giá loét\n5.1 Điều dưỡng phải lập phiếu đánh giá loét tối thiểu 1 lần mỗi ngày. Trường bắt buộc: điểm Braden.\n"
 }
};
