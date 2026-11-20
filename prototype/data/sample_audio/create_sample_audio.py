"""Tạo các file âm thanh mẫu chuẩn WAV (16-bit PCM, 16000Hz mono) để test VAD và STT.

Chạy: python prototype/data/sample_audio/create_sample_audio.py
"""
import math
import os
import random
import struct
import wave
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent


def make_wav(filename, samples, sample_rate=16000):
    filepath = OUT_DIR / filename
    with wave.open(str(filepath), "wb") as wf:
        wf.setnchannels(1)      # Mono
        wf.setsampwidth(2)      # 16-bit
        wf.setframerate(sample_rate)
        raw_data = struct.pack(f"<{len(samples)}h", *samples)
        wf.writeframes(raw_data)
    print(f"[+] Đã tạo file: {filepath.name} ({len(samples)/sample_rate:.1f}s)")


def main():
    sample_rate = 16000
    duration_sec = 3
    num_samples = sample_rate * duration_sec

    # 1. File im lặng 100% (RMS = 0) -> Dùng để test VAD chặn tuyệt đối lỗi ảo giác (Hallucination)
    silence = [0] * num_samples
    make_wav("sample_im_lang_3s.wav", silence, sample_rate)

    # 2. File chỉ có tiếng ồn nền buồng bệnh nhỏ (RMS ~ 50 < ngưỡng 300) -> Test VAD lọc nhiễu
    random.seed(42)
    noise = [random.randint(-50, 50) for _ in range(num_samples)]
    make_wav("sample_nhieu_nen_3s.wav", noise, sample_rate)

    # 3. File có xung âm thanh mô phỏng tiếng nói (RMS ~ 4000 > ngưỡng 300) -> Test VAD phát hiện tiếng nói
    speech_sim = []
    for i in range(num_samples):
        # Tạo chuỗi sóng âm mô phỏng tần số giọng nói người (150Hz - 300Hz)
        t = i / sample_rate
        val = int(3500 * math.sin(2 * math.pi * 200 * t) + 1500 * math.sin(2 * math.pi * 400 * t))
        speech_sim.append(max(-32768, min(32767, val)))
    make_wav("sample_tin_hieu_am_thanh_3s.wav", speech_sim, sample_rate)

    # 4. File đang nói thì dừng lâu (2s nói + 4s dừng/im lặng + 2s nói tiếp) -> Test VAD tách phân đoạn (segmentation)
    p1 = [int(3500 * math.sin(2 * math.pi * 200 * (i / sample_rate))) for i in range(sample_rate * 2)]
    p2 = [random.randint(-15, 15) for _ in range(sample_rate * 4)]  # 4s khoảng lặng
    p3 = [int(3500 * math.sin(2 * math.pi * 250 * (i / sample_rate))) for i in range(sample_rate * 2)]
    long_pause_samples = p1 + p2 + p3
    make_wav("sample_noi_va_dung_lau_8s.wav", long_pause_samples, sample_rate)

    print("\n[OK] Đã tạo xong các file âm thanh kỹ thuật mẫu!")


if __name__ == "__main__":
    main()
