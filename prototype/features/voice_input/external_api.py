"""Tính năng 2 (phần gửi API ngoài) – CHỈ NHẬN văn bản ĐÃ LỌC PII.

prepare_payload(raw, mask_fn) luôn lọc PII trước. send_filtered(payload) từ chối payload chưa lọc,
rồi gọi sender của slot "voice.send". Mặc định là send_disabled: không gọi mạng, không cần khóa API.
Khi nối API thật, người phụ trách gọi registry.connect("voice.send", sender) ở services/engine.py.
"""
from contracts import registry


def prepare_payload(raw_transcript, mask_fn):
    """Lọc PII trước; trả về payload có cờ pii_filtered=True để send_filtered kiểm tra."""
    masked, count = mask_fn(raw_transcript)
    return {"text": masked, "pii_filtered": True, "pii_masked": count}


def send_disabled(payload):
    return {"sent": False, "reason": "prototype: API ngoài chưa được bật"}


def send_filtered(payload):
    if not isinstance(payload, dict) or payload.get("pii_filtered") is not True:
        raise ValueError("Từ chối gửi: nội dung chưa được lọc PII")
    return registry.get("voice.send")(payload)


# Bản mặc định của tính năng: tự đăng ký để lõi dùng được khi chưa nối bản thật
registry.define("voice.send", send_disabled)
