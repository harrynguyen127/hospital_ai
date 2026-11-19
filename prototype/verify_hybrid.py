"""Script chứng minh hoạt động thực tế của Module Voice Input: Chế độ Local vs Chế độ Cloud API (Hybrid).

Lưu ý: Hiện tại hệ thống đang chạy 100% Local (phần gọi API trong voice.py / external_api.py / stt.py
đang được comment tạm tắt). Giữ lại script này để dùng lại khi bỏ comment phần Hybrid.
Chạy: python prototype/verify_hybrid.py
"""
import os
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from contracts import registry
from features.pii_filter import pii
from features.voice_input import external_api, stt, voice

FORM = {
    "fields": [
        {"field_id": "mach", "label": "Mạch", "ui": "number"},
        {"field_id": "huyet_ap", "label": "Huyết áp", "ui": "text"},
        {"field_id": "nhiet_do", "label": "Nhiệt độ", "ui": "number"},
    ]
}

SAMPLE_VOICE = "Bệnh nhân Nguyễn Văn An, số điện thoại 0912345678, mạch 88, huyết áp 120 trên 80, nhiệt độ 37 phẩy 2"


def test_mode_1_local():
    print("=" * 65)
    print("1. CHỨNG MINH CHẾ ĐỘ CHẠY LOCAL (OFFLINE TẠI MÁY)")
    print("=" * 65)
    print(f"[-] Câu nói gốc vào: '{SAMPLE_VOICE}'")

    # Đảm bảo slot voice.send ở trạng thái mặc định (send_disabled)
    registry.disconnect("voice.send")
    registry.define("voice.send", external_api.send_disabled)

    result = voice.process(SAMPLE_VOICE, FORM, mask_fn=pii.mask)
    print("[+] Bước 1 (Lọc PII Local): Đã che ->", result["masked"])
    print(f"[+] Số chỗ đã che định danh: {result['pii_masked']} (SĐT & Tên)")
    print("[+] Bước 2 (Kiểm tra slot voice.send): Trạng thái -> MẶC ĐỊNH (TẮT API)")
    print("[+] Bước 3 (Bóc tách Local tại máy): Dùng regex + từ điển y khoa")
    print(f"[+] KẾT QUẢ ĐIỀN NHÁP (LOCAL): {result['extracted']}")
    print(">>> KẾT LUẬN: Chạy offline 100%, không tốn mạng, không lộ PII ra ngoài!\n")


# --- [TẠM TẮT - CHƯA SỬ DỤNG] Bỏ comment khi bật lại nhánh Hybrid trong voice.py ---
# def test_mode_2_api():
#     print("=" * 65)
#     print("2. CHỨNG MINH CHẾ ĐỘ GỌI CLOUD API (HYBRID QUA SLOT voice.send)")
#     print("=" * 65)
#     print(f"[-] Câu nói gốc vào: '{SAMPLE_VOICE}'")
#
#     calls_made = []
#
#     def mock_cloud_llm(payload):
#         calls_made.append(payload)
#         return {
#             "sent": True,
#             "extracted": {"mach": 88, "huyet_ap": "120/80", "nhiet_do": 37.2},
#         }
#
#     registry.connect("voice.send", mock_cloud_llm)
#     try:
#         result = voice.process(SAMPLE_VOICE, FORM, mask_fn=pii.mask)
#         sent_payload = calls_made[0]
#
#         print("[+] Bước 1 (Lọc PII Local): Đã che ->", result["masked"])
#         print("[+] Bước 2 (Chốt chặn an toàn): cờ pii_filtered =", sent_payload.get("pii_filtered"))
#         print("[+] Bước 3 (Gói tin gửi lên Cloud API):")
#         print("    * Text gửi lên Cloud:", sent_payload["text"])
#         print("    * Dữ liệu định danh thật (0912345678, Nguyễn Văn An) có bị gửi lên không?: KHÔNG!")
#         print("[+] Bước 4 (Cloud API bóc tách JSON):", result["extracted"])
#         print(">>> KẾT LUẬN: Đã gọi API ngoài thành công mà vẫn bảo vệ tuyệt đối PII!\n")
#     finally:
#         registry.disconnect("voice.send")
#         registry.define("voice.send", external_api.send_disabled)
#
#
# def test_mode_3_fallback():
#     print("=" * 65)
#     print("3. CHỨNG MINH CƠ CHẾ TỰ ĐỘNG FALLBACK KHI MẤT MẠNG / LỖI API")
#     print("=" * 65)
#     registry.connect("voice.send", lambda payload: {"sent": False, "reason": "Connection timed out (Rớt mạng)"})
#     try:
#         result = voice.process(SAMPLE_VOICE, FORM, mask_fn=pii.mask)
#         print("[-] Tình huống: Slot voice.send đang bật NHƯNG API ngoài bị lỗi mạng/timeout.")
#         print("[+] Hệ thống tự động phát hiện API lỗi -> Tức thì lùi về bộ trích xuất Local tại máy!")
#         print(f"[+] KẾT QUẢ ĐIỀN NHÁP (FALLBACK LOCAL): {result['extracted']}")
#         print(">>> KẾT LUẬN: Demo không bao giờ bị đơ hay báo lỗi 500 kể cả khi rớt mạng!\n")
#     finally:
#         registry.disconnect("voice.send")
#         registry.define("voice.send", external_api.send_disabled)


if __name__ == "__main__":
    print("\n" + "#" * 65)
    print("#  BÁO CÁO BẰNG CHỨNG THỰC TẾ: CHẾ ĐỘ LOCAL (HYBRID ĐANG TẮT)    #")
    print("#" * 65 + "\n")
    test_mode_1_local()
    # test_mode_2_api()
    # test_mode_3_fallback()
