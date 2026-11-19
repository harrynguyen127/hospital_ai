"""Tính năng 1 – Lọc PII (che thông tin định danh).

Che SĐT, CCCD và tên người sau các danh xưng. Đây là bước BẮT BUỘC trước mọi lời gọi ra API ngoài
(xem features/voice_input/external_api.py). Chỉ dùng regex, tất định, không gọi mạng.
"""
import re

from contracts import registry

_STOP_WORDS = (
    r"là|của|mạch|mách|mạnh|nhịp|nhìn|huyết|nhiệt|spo2|số|điện|cccd|bảo|hiểm|"
    r"hôm|trời|thời|cuối|ăn|đang|tư\s+thế|trạng\s+thái|điểm|vị\s+trí|triệu\s+chứng|"
    r"ca|lý|dị|thuốc|tiền|chẩn|phương|khả|hình|cách|nguồn|nội|người|đáp|mức|dụng|"
    r"biện|môi|hướng|thời|vị|tính|hoàn|yếu|hỗ|vận|tiếp|kết|dấu|tình|buồn|khám|vấn|kiểm"
)

PII = [
    (re.compile(r"\b0\d{9,10}\b"), "[SĐT]"),
    (re.compile(r"\b\d{12}\b"), "[CCCD]"),
    # Từ chỉ danh xưng + cụm tên viết hoa -> chỉ thay phần tên
    (re.compile(
        r"((?i:tên bệnh nhân là|tên bệnh nhân|bệnh nhân tên là|bệnh nhân là|tên là|người liên hệ là|liên hệ là|"
        r"anh|chị|ông|bà|bệnh nhân))\s+"
        r"((?:[A-ZÀ-Ỵ][\wÀ-ỹ]*\s?){1,4})"
    ), None),
    # Hỗ trợ thêm đầu ra STT viết thường sau "tên bệnh nhân (là) / người liên hệ (là)" (dừng trước từ khóa chỉ số y khoa và tên trường)
    (re.compile(
        r"((?i:\b(?:tên\s+bệnh\s+nhân(?:\s+là)?|bệnh\s+nhân\s+tên(?:\s+là)?|tên\s+là|người\s+liên\s+hệ(?:\s+là)?|liên\s+hệ(?:\s+là)?)))\s+"
        r"((?:(?!(?:" + _STOP_WORDS + r")\b)[a-zà-ỹA-ZÀ-Ỵ]+\s*){1,4})"
    ), None),
]


def mask(text):
    """Trả về (văn bản đã che, số chỗ đã che)."""
    count = 0
    for pat, rep in PII:
        if rep is None:
            def _name(m):
                nonlocal count
                target = m.group(2).strip()
                if not target:
                    return m.group(0)
                count += 1
                return m.group(0).replace(target, "[TÊN]", 1)
            text = pat.sub(_name, text)
        else:
            text, k = pat.subn(rep, text)
            count += k
    return text, count


# Bản mặc định của tính năng: tự đăng ký để lõi dùng được khi chưa nối bản thật
registry.define("pii.mask", mask)
