"""Tính năng 2 – Nhập liệu bằng giọng nói (bản prototype, không có STT thật).

Văn bản đầu vào là transcript (gõ hoặc phát từ kịch bản đóng vai). Pipeline:
che PII (features/pii_filter) -> lọc câu ngoài lề -> trích xuất theo các trường của form đang mở.
Kết quả chỉ là NHÁP; lưu chỉ xảy ra khi người dùng xác nhận (API /api/records).
Gửi bản đã lọc ra API ngoài: xem external_api.py (chưa bật trong prototype).
"""
import re

from shared.common import norm

OUT_OF_SCOPE = ("trời đẹp", "thời tiết", "cuối tuần", "ăn trưa", "bóng đá", "phim")
SYNONYMS = {
    "thuốc đang dùng": ["đang dùng"],
    "người liên hệ": ["người nhà", "liên hệ"],
    "nhiệt độ": ["sốt"],
}


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
            elif f["ui"] in ("text", "textarea", "select"):
                m = re.match(r"\s*(?:là|:)?\s*([^.;,]+)", rest)
                if m and m.group(1).strip():
                    value = m.group(1).strip()[:120]
                    if f["ui"] == "select":
                        value = next((opt for opt in f["options"] if norm(opt) == value), None)
                        if value is None:
                            continue
                    out[f["field_id"]] = value
                    break
    return out


def process(text, form, mask_fn=None):
    """Hàm THUẦN. mask_fn: hàm che PII (slot "pii.mask"), bắt buộc; không có thì từ chối, không đoán."""
    if mask_fn is None:
        raise RuntimeError("chưa có bộ lọc PII: truyền mask_fn (slot pii.mask)")
    masked, pii = mask_fn(text)
    low = norm(text)
    if any(k in low for k in OUT_OF_SCOPE):
        return {"masked": masked, "pii_masked": pii, "out_of_scope": True, "extracted": {}}
    # Chỉ trích xuất từ bản đã che định danh, không dùng văn bản gốc
    return {"masked": masked, "pii_masked": pii, "out_of_scope": False,
            "extracted": extract(masked, form["fields"])}
