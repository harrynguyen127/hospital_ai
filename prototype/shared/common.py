"""Tiện ích dùng chung: chuẩn hóa tiếng Việt, thời lượng ISO 8601, fingerprint form.

Được gọi bởi: store.py (fingerprint seed), form_detection.py, policy.py, reminder.py.
"""
import datetime as dt
import hashlib
import re
import unicodedata

DUR_RE = re.compile(r"^P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?)?$")


def norm(s):
    """NFC, chữ thường, gộp khoảng trắng; giữ nguyên dấu tiếng Việt."""
    s = unicodedata.normalize("NFC", s or "")
    return re.sub(r"\s+", " ", s).strip().lower()


def slugify(s):
    """Bỏ dấu, đổi sang snake_case ASCII (dùng cho field_id / form_id)."""
    s = unicodedata.normalize("NFD", (s or "").replace("đ", "d").replace("Đ", "D"))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def parse_duration(s):
    """'PT24H' -> timedelta(hours=24). Trả None nếu không hợp lệ."""
    m = DUR_RE.match(s or "")
    if not m or not any(m.groups()):
        return None
    d, h, mi = (int(x) if x else 0 for x in m.groups())
    return dt.timedelta(days=d, hours=h, minutes=mi)


def fingerprint(title, fields):
    """sha256(tiêu đề + nhãn đã sắp xếp + kiểu giao diện)."""
    labels = sorted(f"{norm(f['label'])}:{f['ui']}" for f in fields)
    raw = norm(title) + "|" + "|".join(labels)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def label_keys(fields):
    return {f"{norm(f['label'])}:{f['ui']}" for f in fields}


def jaccard(a, b):
    return len(a & b) / len(a | b) if (a | b) else 0.0
