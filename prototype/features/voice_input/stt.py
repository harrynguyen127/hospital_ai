"""Tầng VAD (Voice Activity Detection) + STT (Speech-to-Text) chạy 100% Local với vinai/PhoWhisper-small.

- Bước 1 (VAD): Phát hiện khoảng có tiếng người nói (detect_voice_segments / has_speech) bằng
  phân tích năng lượng RMS theo frame 30ms trên file WAV (stdlib: wave, struct, math).
  Chặn các đoạn ghi âm chỉ có im lặng/nhiễu nền để chống lỗi ảo giác (hallucination)
  của họ mô hình Whisper và tiết kiệm thời gian xử lý.
- Bước 2 (STT Local): Dùng importlib (thuộc stdlib) để nạp động transformers cho
  vinai/PhoWhisper-small chạy hoàn toàn tại máy, đảm bảo vượt qua 100% tests/test_isolation.py.
- Phần gọi Cloud STT Blaze.vn được giữ lại ở dạng comment bên dưới để bật lại khi cần.
- Lưu cache model trong RAM (_MODEL_CACHE) để chỉ nạp 1 lần duy nhất khi chạy local.
"""
import importlib
# import json
import math
import os
import struct
# import urllib.error
# import urllib.request
import wave
from pathlib import Path

DEFAULT_STT_MODEL = "vinai/PhoWhisper-small"
DEFAULT_RMS_THRESHOLD = 300.0
MAX_CHUNK_SECONDS = 28.0  # Whisper/PhoWhisper giới hạn 30s (3000 mel frames)/lần suy luận
MIN_CHUNK_SECONDS = 18.0  # Tìm điểm im lặng trong khoảng [18s..28s] để không cắt ngang giữa từ
# DEFAULT_BLAZE_API_URL = "https://api.blaze.vn/v1/stt/execute"
# DEFAULT_BLAZE_MODEL = "stt-async-1.5"
_MODEL_CACHE = {}
# LAST_BLAZE_ERROR = {"msg": ""}


def clear_cache():
    """Xóa cache model trong RAM (dùng khi test hoặc đổi cấu hình)."""
    _MODEL_CACHE.clear()


def _frame_rms_16bit(raw_bytes):
    count = len(raw_bytes) // 2
    if count == 0:
        return 0.0
    samples = struct.unpack(f"<{count}h", raw_bytes[: count * 2])
    mean_sq = sum(s * s for s in samples) / count
    return math.sqrt(mean_sq)


def _merge_close(segments, gap):
    """Gộp các đoạn cách nhau < gap giây (nhịp ngắt giữa các âm tiết không phải là dừng thật)."""
    merged = []
    for s, e in segments:
        if merged and s - merged[-1][1] < gap:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))
    return merged


def detect_voice_segments(audio_path, rms_threshold=DEFAULT_RMS_THRESHOLD, frame_ms=30, merge_gap=0.6):
    """Phát hiện các đoạn [start_sec, end_sec] có tiếng nói trong file .wav (16-bit PCM).

    Nếu file không phải định dạng .wav chuẩn (ví dụ .mp3), trả về [(0.0, -1.0)] để nhường cho
    tầng giải mã âm thanh của PhoWhisper xử lý.
    """
    path = Path(audio_path)
    if not path.is_file():
        raise FileNotFoundError(f"Không tìm thấy file âm thanh: {audio_path}")
    try:
        with wave.open(str(path), "rb") as wf:
            rate = wf.getframerate()
            sampwidth = wf.getsampwidth()
            if sampwidth != 2 or rate <= 0:
                return [(0.0, -1.0)]
            frames_per_chunk = max(1, int(rate * frame_ms / 1000))
            segments = []
            in_speech = False
            start_sec = 0.0
            idx = 0
            while True:
                raw = wf.readframes(frames_per_chunk)
                if not raw:
                    break
                cur_sec = (idx * frames_per_chunk) / rate
                rms = _frame_rms_16bit(raw)
                if rms >= rms_threshold and not in_speech:
                    in_speech = True
                    start_sec = cur_sec
                elif rms < rms_threshold and in_speech:
                    in_speech = False
                    segments.append((round(start_sec, 3), round(cur_sec, 3)))
                idx += 1
            if in_speech:
                end_sec = (idx * frames_per_chunk) / rate
                segments.append((round(start_sec, 3), round(end_sec, 3)))
            return _merge_close(segments, merge_gap)
    except wave.Error:
        return [(0.0, -1.0)]


def has_speech(audio_path, rms_threshold=DEFAULT_RMS_THRESHOLD, vad_fn=None):
    """Kiểm tra file âm thanh có chứa tiếng nói hay không (VAD gate)."""
    if vad_fn is not None:
        return bool(vad_fn(audio_path))
    return len(detect_voice_segments(audio_path, rms_threshold=rms_threshold)) > 0


# --- [TẠM TẮT - CHƯA SỬ DỤNG] Cloud STT Blaze.vn (bỏ comment để dùng lại) ---
# def blaze_stt(audio_path, api_key=None, api_url=None, model=None, timeout=20.0):
#     """Gọi STT API của Blaze.vn qua HTTP POST multipart/form-data (chỉ dùng stdlib urllib)."""
#     key = (api_key or os.environ.get("BLAZE_API_KEY", "")).strip()
#     if not key:
#         return None
#     path = Path(audio_path)
#     if not path.is_file():
#         return None
#
#     url = (api_url or os.environ.get("BLAZE_API_URL") or DEFAULT_BLAZE_API_URL).strip()
#     stt_model = (model or os.environ.get("BLAZE_STT_MODEL") or DEFAULT_BLAZE_MODEL).strip()
#     full_url = f"{url}?language=vi&model={stt_model}"
#
#     boundary = "----WebKitFormBoundary" + os.urandom(8).hex()
#     audio_bytes = path.read_bytes()
#     filename = path.name
#
#     body = bytearray()
#     body.extend(f"--{boundary}\r\n".encode("utf-8"))
#     body.extend(f'Content-Disposition: form-data; name="audio_file"; filename="{filename}"\r\n'.encode("utf-8"))
#     body.extend(b"Content-Type: audio/wav\r\n\r\n")
#     body.extend(audio_bytes)
#     body.extend(b"\r\n")
#     body.extend(f"--{boundary}--\r\n".encode("utf-8"))
#
#     req = urllib.request.Request(
#         full_url,
#         data=bytes(body),
#         headers={
#             "Content-Type": f"multipart/form-data; boundary={boundary}",
#             "Authorization": f"Bearer {key}",
#         },
#         method="POST",
#     )
#     try:
#         with urllib.request.urlopen(req, timeout=timeout) as resp:
#             data = json.loads(resp.read().decode("utf-8"))
#         if isinstance(data, dict):
#             if "text" in data:
#                 return str(data["text"]).strip()
#             if "data" in data and isinstance(data["data"], dict) and "text" in data["data"]:
#                 return str(data["data"]["text"]).strip()
#             if "transcript" in data:
#                 return str(data["transcript"]).strip()
#         return str(data).strip()
#     except (urllib.error.URLError, TimeoutError, KeyError, ValueError, TypeError, OSError) as exc:
#         detail = ""
#         if isinstance(exc, urllib.error.HTTPError):
#             try:
#                 detail = " | " + exc.read().decode("utf-8", "replace")[:200]
#             except Exception:  # noqa: BLE001
#                 pass
#         LAST_BLAZE_ERROR["msg"] = f"{type(exc).__name__}: {exc}{detail}"
#         return None


def _load_pipeline(model_name):
    if model_name in _MODEL_CACHE:
        return _MODEL_CACHE[model_name]
    try:
        transformers = importlib.import_module("transformers")
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Chưa cài thư viện 'transformers' và 'torch' để chạy PhoWhisper local. "
            "Cài đặt: pip install transformers torch"
        ) from exc
    pipe = transformers.pipeline(
        "automatic-speech-recognition",
        model=model_name,
        generate_kwargs={"language": "vi", "task": "transcribe"},
    )
    _MODEL_CACHE[model_name] = pipe
    return pipe


def _read_wav_float(path):
    """Đọc WAV 16-bit thành (mảng float32 mono, sample_rate) để KHÔNG cần ffmpeg. None nếu không phải WAV."""
    try:
        np = importlib.import_module("numpy")
        with wave.open(str(path), "rb") as wf:
            if wf.getsampwidth() != 2:
                return None
            rate, ch, raw = wf.getframerate(), wf.getnchannels(), wf.readframes(wf.getnframes())
        arr = np.frombuffer(raw, dtype="<i2").astype("float32") / 32768.0
        if ch > 1:
            arr = arr[: len(arr) // ch * ch].reshape(-1, ch).mean(axis=1)
        return arr, rate
    except (wave.Error, ModuleNotFoundError):
        return None


def _split_audio_chunks(arr, rate, max_chunk_sec=MAX_CHUNK_SECONDS, min_chunk_sec=MIN_CHUNK_SECONDS):
    """Chia mảng âm thanh dài (> 28s, vd 60s+) thành các đoạn <= 28s để không vượt giới hạn 3000 mel frames của Whisper.

    Ưu tiên cắt tại khung 50ms yên tĩnh nhất trong cửa sổ [min_chunk_sec..max_chunk_sec] để tránh cắt ngang từ.
    """
    total = len(arr)
    max_samples = max(1, int(rate * max_chunk_sec))
    if total <= max_samples:
        return [arr]

    min_samples = max(1, min(max_samples - 1, int(rate * min_chunk_sec)))
    win = max(1, int(rate * 0.05))  # khung 50ms
    chunks = []
    start = 0
    while start < total:
        end = start + max_samples
        if end >= total:
            chunks.append(arr[start:total])
            break
        search_from = start + min_samples
        best_cut = end
        best_energy = float("inf")
        pos = search_from
        while pos + win <= end:
            seg = arr[pos : pos + win]
            energy = float((seg * seg).mean())
            if energy < best_energy:
                best_energy = energy
                best_cut = pos + win // 2
            pos += win
        chunks.append(arr[start:best_cut])
        start = best_cut
    return chunks


def _default_backend(audio_path, model_name):
    path = Path(audio_path)
    if not path.is_file():
        raise FileNotFoundError(f"Không tìm thấy file âm thanh: {audio_path}")
    pipe = _load_pipeline(model_name)
    wav = _read_wav_float(path)
    if wav:
        arr, rate = wav
        chunks = _split_audio_chunks(arr, rate)
        if len(chunks) > 1:
            dur = len(arr) / max(1, rate)
            print(f"[STT] Âm thanh dài {dur:.1f}s -> tự động chia {len(chunks)} đoạn (<= {int(MAX_CHUNK_SECONDS)}s/đoạn)", flush=True)
        parts = []
        for i, chunk in enumerate(chunks, 1):
            if len(chunks) > 1:
                print(f"[STT] Đang nhận diện đoạn {i}/{len(chunks)} ({len(chunk)/rate:.1f}s)...", flush=True)
            res = pipe({"raw": chunk, "sampling_rate": rate})
            txt = (res.get("text", "") if isinstance(res, dict) else str(res)).strip()
            if txt:
                parts.append(txt)
        return " ".join(parts)
    res = pipe(str(path), return_timestamps=True)
    if isinstance(res, dict):
        return res.get("text", "")
    return str(res)


def transcribe_with_info(audio_path, model_name=None, backend_fn=None):
    """Như transcribe() nhưng trả thêm thông tin để quan sát/gỡ lỗi (dùng cho thử micro).

    Trả về dict: {segments, backend, text, error}. Không ném lỗi: lỗi STT nằm trong `error`.
    backend: "none" (VAD chặn) | "phowhisper".
    """
    info = {"segments": [], "backend": "none", "text": "", "error": None}
    info["segments"] = [list(s) for s in detect_voice_segments(audio_path)]
    if not info["segments"]:
        return info
    errors = []
    # --- [TẠM TẮT - CHƯA SỬ DỤNG] Gọi Cloud STT Blaze.vn nếu có BLAZE_API_KEY ---
    # if os.environ.get("BLAZE_API_KEY", "").strip():
    #     text = blaze_stt(audio_path)
    #     if text:
    #         info.update(backend="blaze", text=text)
    #         return info
    #     errors.append("Blaze STT lỗi: " + (LAST_BLAZE_ERROR["msg"] or "không trả kết quả"))
    chosen = (model_name or os.environ.get("PHOWHISPER_MODEL") or DEFAULT_STT_MODEL).strip()
    runner = backend_fn or _default_backend
    try:
        info.update(backend="phowhisper", text=str(runner(audio_path, chosen)).strip())
    except Exception as exc:  # noqa: BLE001 - trả lỗi để hiển thị, không làm sập server
        errors.append(f"PhoWhisper local lỗi: {exc}")
    info["error"] = "; ".join(errors) or None
    return info


def transcribe(audio_path, model_name=None, backend_fn=None, vad_fn=None):
    """Lọc khoảng lặng qua VAD rồi chuyển file âm thanh thành văn bản 100% Local (PhoWhisper)."""
    if not audio_path or not str(audio_path).strip():
        raise ValueError("Đường dẫn file âm thanh không được để trống")
    if not has_speech(audio_path, vad_fn=vad_fn):
        return ""

    if backend_fn is not None:
        chosen_model = (model_name or os.environ.get("PHOWHISPER_MODEL") or DEFAULT_STT_MODEL).strip()
        return str(backend_fn(audio_path, chosen_model)).strip()

    # --- [TẠM TẮT - CHƯA SỬ DỤNG] Thử gọi Blaze API nếu có biến môi trường BLAZE_API_KEY ---
    # if os.environ.get("BLAZE_API_KEY"):
    #     blaze_res = blaze_stt(audio_path)
    #     if blaze_res:
    #         return blaze_res

    chosen_model = (model_name or os.environ.get("PHOWHISPER_MODEL") or DEFAULT_STT_MODEL).strip()
    return str(_default_backend(audio_path, chosen_model)).strip()
