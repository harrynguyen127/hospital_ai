"""Tính năng 1 – Lọc PII (che thông tin định danh).

Che SĐT, CCCD và tên người sau các danh xưng. Đây là bước BẮT BUỘC trước mọi lời gọi ra API ngoài
(xem features/voice_input/external_api.py). Chỉ dùng regex, tất định, không gọi mạng.
"""
import re

from contracts import registry

PII = [
    (re.compile(r"\b0\d{9,10}\b"), "[SĐT]"),
    (re.compile(r"\b\d{12}\b"), "[CCCD]"),
    # Từ chỉ danh xưng + cụm tên viết hoa -> chỉ thay phần tên
    (re.compile(r"(tên là|liên hệ là|Anh|Chị|Ông|Bà|anh|chị|ông|bà|bệnh nhân|Bệnh nhân)\s+((?:[A-ZÀ-Ỵ][\wÀ-ỹ]*\s?){1,4})"), None),
]


def mask(text):
    """Trả về (văn bản đã che, số chỗ đã che)."""
    count = 0
    for pat, rep in PII:
        if rep is None:
            def _name(m):
                nonlocal count
                count += 1
                return m.group(0).replace(m.group(2), "[TÊN]")
            text = pat.sub(_name, text)
        else:
            text, k = pat.subn(rep, text)
            count += k
    return text, count


# Bản mặc định của tính năng: tự đăng ký để lõi dùng được khi chưa nối bản thật
registry.define("pii.mask", mask)
