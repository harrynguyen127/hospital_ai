"""Module 4 – Voice input to form (bản prototype, không có STT thật).

Văn bản đầu vào là transcript (gõ hoặc phát từ kịch bản đóng vai). Pipeline:
che PII (SĐT, CCCD, tên) -> lọc câu ngoài lề -> trích xuất theo các trường của form đang mở.
Kết quả chỉ là NHÁP; lưu chỉ xảy ra khi người dùng xác nhận (API /api/records).
"""
import re

from .common import norm

OUT_OF_SCOPE = ("trời đẹp", "thời tiết", "cuối tuần", "ăn trưa", "bóng đá", "phim")
PII = [
    (re.compile(r"\b0\d{9,10}\b"), "[SĐT]"),
    (re.compile(r"\b\d{12}\b"), "[CCCD]"),
    # Từ chỉ danh xưng + cụm tên viết hoa -> chỉ thay phần tên
    (re.compile(r"(tên là|liên hệ là|Anh|Chị|Ông|Bà|anh|chị|ông|bà|bệnh nhân)\s+((?:[A-ZÀ-Ỵ][\wÀ-ỹ]*\s?){1,4})"), None),
]
SYNONYMS = {
    "thuốc đang dùng": ["đang dùng"],
    "người liên hệ": ["người nhà", "liên hệ"],
    "nhiệt độ": ["sốt"],
}


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


def _speech(text):
    t = norm(text)
    return re.sub(r"(\d+)\s*phẩy\s*(\d+)", r"\1.\2", t)


def extract(text, fields):
    t = _speech(text)
    out = {}
    for f in fields:
        label = norm(f["label"])
        if label == "huyết áp":
            m = re.search(r"(\d{2,3})\s*(?:trên|/)\s*(\d{2,3})", t)
            if m:
                out[f["field_id"]] = f"{m.group(1)}/{m.group(2)}"
            continue
        for kw in [label] + SYNONYMS.get(label, []):
            km = re.search(re.escape(kw), t)
            if not km:
                continue
            rest = t[km.end():]
            if f["ui"] == "number":
                m = re.match(r"[^\d]{0,12}(\d+(?:\.\d+)?)", rest)
                if m:
                    v = m.group(1)
                    out[f["field_id"]] = float(v) if "." in v else int(v)
                    break
            elif f["ui"] == "text":
                m = re.match(r"\s*(?:là|:)?\s*([^.;,]+)", rest)
                if m and m.group(1).strip():
                    out[f["field_id"]] = m.group(1).strip()[:120]
                    break
    return out


def process(text, form):
    masked, pii = mask(text)
    low = norm(text)
    if any(k in low for k in OUT_OF_SCOPE):
        return {"masked": masked, "pii_masked": pii, "out_of_scope": True, "extracted": {}}
    # Chỉ trích xuất từ bản đã che định danh, không dùng văn bản gốc
    return {"masked": masked, "pii_masked": pii, "out_of_scope": False,
            "extracted": extract(masked, form["fields"])}
