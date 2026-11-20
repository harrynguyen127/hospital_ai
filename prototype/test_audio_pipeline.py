"""Script kiểm thử toàn bộ pipeline 100% Local với FILE ÂM THANH THỰC TẾ (.wav).

Pipeline:
[File .wav] -> VAD (Lọc khoảng lặng) -> STT Local (vinai/PhoWhisper-small) -> Lọc PII Local -> Điền form Local

Chạy:
  python prototype/test_audio_pipeline.py
  python prototype/test_audio_pipeline.py prototype/data/sample_audio/file_cua_ban.wav
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from features.voice_input import stt
from services import engine

FORM = {
    "form_id": "phieu_sinh_ton_nguoi_lon",
    "fields": [
        {"field_id": "ten_benh_nhan", "label": "Tên bệnh nhân", "ui": "text"},
        {"field_id": "mach", "label": "Mạch", "ui": "number"},
        {"field_id": "nhip_tho", "label": "Nhịp thở", "ui": "number"},
        {"field_id": "huyet_ap", "label": "Huyết áp", "ui": "text"},
        {"field_id": "nhiet_do", "label": "Nhiệt độ", "ui": "number"},
        {"field_id": "spo2", "label": "SpO2", "ui": "number"},
    ],
}


def run_pipeline_on_file(audio_path, mock_stt_text=None):
    path = Path(audio_path)
    print("=" * 70)
    print(f"[*] KIỂM THỬ FILE ÂM THANH: {path.name}")
    print("=" * 70)

    # 1. Kiểm tra VAD
    segments = stt.detect_voice_segments(path)
    has_voice = stt.has_speech(path)
    print(f"[1] VAD Check:")
    print(f"    - Có tiếng người nói không?: {'CÓ' if has_voice else 'KHÔNG (Im lặng/Nhiễu)'}")
    print(f"    - Các khoảng phát hiện tiếng nói (giây): {segments}")

    if not has_voice:
        print("[!] VAD chặn xử lý vì file không chứa tiếng người nói (Chống ảo giác Whisper)!")
        print(">>> Kết quả: Dừng sớm, không tiêu tốn tài nguyên gọi STT / LLM.\n")
        return

    # 2. Chạy STT Local (phần Cloud STT Blaze.vn đang được comment tạm tắt)
    print(f"\n[2] Tầng STT (Speech-to-Text 100% Local):")
    # if os.environ.get("BLAZE_API_KEY"):
    #     print("    - Đang dùng: Blaze.vn Cloud STT API (BLAZE_API_KEY đã được cấu hình)")
    # else:
    model_name = os.environ.get("PHOWHISPER_MODEL") or stt.DEFAULT_STT_MODEL
    print(f"    - Đang dùng: {model_name} (Local tại máy, 100% offline)")

    fake_runner = (lambda p, m: mock_stt_text) if mock_stt_text else None
    transcript = stt.transcribe(path, backend_fn=fake_runner)
    print(f"    - Văn bản bóc từ âm thanh: \"{transcript}\"")

    if not transcript:
        print("[!] Không nhận diện được chữ nào từ file âm thanh.")
        return

    # 3. Đưa qua pipeline Voice (qua lõi engine nối PII-02 + kiểm tra ngưỡng policy)
    print(f"\n[3] Tầng Voice Pipeline (Lọc PII-02 Local + Điền Form + Kiểm tra ngưỡng):")
    res = engine.voice_process(transcript, FORM)
    print(f"    - Văn bản sau lọc PII: \"{res['masked']}\"")
    print(f"    - Số thông tin PII đã che: {res['pii_masked']}")
    if res.get("pii_assessment"):
        pa = res["pii_assessment"]
        print(f"    - Đánh giá PII-02: engine={pa['engine']} | status={pa['status']} | egress={pa['external_egress_authorized']}")
    print(f"    - Câu ngoài lề: {res['out_of_scope']}")
    if res.get("validation_warnings"):
        print(f"    - Cảnh báo ngưỡng (Policy): {res['validation_warnings']}")
    if res.get("policy_alerts"):
        print(f"    - Cảnh báo cấp cứu (Policy): {res['policy_alerts']}")
    print(f"\n[4] KẾT QUẢ ĐIỀN NHÁP VÀO PHIẾU:")
    print(f"    {res['extracted']}")
    print("=" * 70 + "\n")


def main():
    audio_dir = ROOT / "data" / "sample_audio"

    if len(sys.argv) > 1:
        target = Path(sys.argv[1])
        if not target.is_file():
            print(f"Lỗi: Không tìm thấy file {target}")
            sys.exit(1)
        run_pipeline_on_file(target)
        return

    # Test file 1: Im lặng
    run_pipeline_on_file(audio_dir / "sample_im_lang_3s.wav")

    # Test file 2: Nhiễu nền buồng bệnh
    run_pipeline_on_file(audio_dir / "sample_nhieu_nen_3s.wav")

    # Test file 3: File có tiếng nói (Mô phỏng bác sĩ đọc chỉ số)
    sample_text = (
        "Bệnh nhân Nguyễn Văn An, số điện thoại 0912345678. "
        "Mạch 88, nhịp thở 20, huyết áp 120 trên 80, nhiệt độ 37 phẩy 2, SpO2 98."
    )
    run_pipeline_on_file(audio_dir / "sample_tin_hieu_am_thanh_3s.wav", mock_stt_text=sample_text)

    # Test file 4: File đang nói thì dừng lâu 4 giây (VAD phát hiện 2 phân đoạn riêng biệt)
    pause_text = (
        "Mạch 88, nhịp thở 20. Huyết áp 118 trên 76, SpO2 98."
    )
    run_pipeline_on_file(audio_dir / "sample_noi_va_dung_lau_8s.wav", mock_stt_text=pause_text)


if __name__ == "__main__":
    main()
