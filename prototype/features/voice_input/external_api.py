"""Tính năng 2 (phần gửi API ngoài) – CHỈ NHẬN văn bản ĐÃ LỌC PII.

Hiện tại hệ thống đang chạy 100% Local: phần gọi Cloud LLM API (`llm_sender`) tạm comment
để chưa sử dụng, slot "voice.send" luôn ở mặc định `send_disabled`.
prepare_payload(raw, mask_fn, fields=None) và send_filtered(payload) vẫn giữ nguyên theo hợp đồng.
"""
# import json
# import os
# import urllib.error
# import urllib.request

from contracts import registry

# DEFAULT_API_URL = "https://api.openai.com/v1/chat/completions"
# DEFAULT_MODEL = "gpt-4o-mini"


def prepare_payload(raw_transcript, mask_fn, fields=None):
    """Lọc PII trước; trả về payload có cờ pii_filtered=True để send_filtered kiểm tra."""
    masked, count = mask_fn(raw_transcript)
    payload = {"text": masked, "pii_filtered": True, "pii_masked": count}
    if fields is not None:
        payload["fields"] = fields
    return payload


def sanitize_extracted(raw_dict, fields):
    """Chỉ giữ field_id có trong schema của form và ép kiểu an toàn."""
    if not isinstance(raw_dict, dict) or not fields:
        return {}
    by_id = {f["field_id"]: f for f in fields if "field_id" in f}
    out = {}
    for fid, val in raw_dict.items():
        if fid not in by_id or val in (None, ""):
            continue
        ui = by_id[fid].get("ui", "text")
        if ui == "number":
            try:
                num = float(str(val).replace(",", "."))
                out[fid] = int(num) if num.is_integer() else num
            except (ValueError, TypeError):
                continue
        elif ui == "checkbox":
            if isinstance(val, bool):
                out[fid] = val
            elif str(val).strip().lower() in ("true", "1", "có", "co", "yes"):
                out[fid] = True
            elif str(val).strip().lower() in ("false", "0", "không", "khong", "no"):
                out[fid] = False
        else:
            out[fid] = str(val).strip()[:120]
    return out


def send_disabled(payload):
    return {"sent": False, "reason": "prototype: API ngoài chưa được bật"}


# --- [TẠM TẮT - CHƯA SỬ DỤNG] Cloud LLM API sender (bỏ comment để bật lại Hybrid) ---
# def llm_sender(payload):
#     """Sender gọi LLM qua HTTP chuẩn (urllib.request) khi có VOICE_API_KEY.
#
#     Nếu thiếu VOICE_API_KEY hoặc lỗi mạng/timeout, trả về sent=False để voice.py tự fallback về local.
#     """
#     if not isinstance(payload, dict) or payload.get("pii_filtered") is not True:
#         raise ValueError("Từ chối gửi: nội dung chưa được lọc PII")
#     api_key = os.environ.get("VOICE_API_KEY", "").strip()
#     if not api_key:
#         return {"sent": False, "reason": "chưa cấu hình VOICE_API_KEY"}
#
#     fields = payload.get("fields") or []
#     schema_desc = [
#         {"field_id": f.get("field_id"), "label": f.get("label"), "ui": f.get("ui", "text"),
#          **({"options": f["options"]} if f.get("options") else {})}
#         for f in fields
#     ]
#     prompt = (
#         "Trích xuất thông tin y khoa từ câu nói đã ẩn danh vào đúng JSON object {field_id: value} "
#         "theo danh sách trường sau. Chỉ trả về JSON object, không giải thích.\n"
#         f"Trường của form: {json.dumps(schema_desc, ensure_ascii=False)}\n"
#         f"Câu nói: {payload.get('text', '')}"
#     )
#     api_url = os.environ.get("VOICE_API_URL", DEFAULT_API_URL).strip()
#     model = os.environ.get("VOICE_MODEL", DEFAULT_MODEL).strip()
#     timeout = float(os.environ.get("VOICE_TIMEOUT", "3.0"))
#
#     req_body = json.dumps({
#         "model": model,
#         "messages": [
#             {"role": "system", "content": "Bạn là trợ lý trích xuất dữ liệu bệnh án chính xác theo JSON."},
#             {"role": "user", "content": prompt},
#         ],
#         "temperature": 0,
#         "response_format": {"type": "json_object"},
#     }, ensure_ascii=False).encode("utf-8")
#
#     req = urllib.request.Request(
#         api_url,
#         data=req_body,
#         headers={
#             "Content-Type": "application/json; charset=utf-8",
#             "Authorization": f"Bearer {api_key}",
#         },
#         method="POST",
#     )
#     try:
#         with urllib.request.urlopen(req, timeout=timeout) as resp:
#             data = json.loads(resp.read().decode("utf-8"))
#         content = data["choices"][0]["message"]["content"]
#         parsed = json.loads(content)
#         return {"sent": True, "extracted": sanitize_extracted(parsed, fields)}
#     except (urllib.error.URLError, TimeoutError, KeyError, ValueError, TypeError) as exc:
#         return {"sent": False, "reason": f"lỗi gọi API: {exc}"}


def send_filtered(payload):
    if not isinstance(payload, dict) or payload.get("pii_filtered") is not True:
        raise ValueError("Từ chối gửi: nội dung chưa được lọc PII")
    return registry.get("voice.send")(payload)


# Bản mặc định của tính năng: tự đăng ký để lõi dùng được khi chưa nối bản thật
registry.define("voice.send", send_disabled)
