"""Tính năng 2 – Nhập liệu bằng giọng nói 100% Local (VAD + PhoWhisper-small STT + Trích xuất tại máy).

Pipeline (hoàn toàn offline tại máy, không gọi API ngoài):
1. Nếu có audio_path (và chưa có text): gọi stt.transcribe(audio_path) (VAD + PhoWhisper-small local) để lấy transcript.
2. Che PII tại máy qua external_api.prepare_payload(text, mask_fn) -> pii_filtered=True.
3. Lọc câu ngoài lề (OUT_OF_SCOPE).
4. Trích xuất tại máy bằng hàm extract(masked, fields) hỗ trợ đủ 10 phiếu EMR và form mới phát sinh động.
Kết quả chỉ là NHÁP; lưu chỉ xảy ra khi người dùng xác nhận (API /api/records).
"""
import difflib
import re
import unicodedata

from features.voice_input import external_api, stt
from shared.common import norm

OUT_OF_SCOPE = ("trời đẹp", "thời tiết", "cuối tuần", "ăn trưa", "bóng đá", "phim")
# SYNONYMS chỉ giữ các từ đồng nghĩa khác từ trong y khoa; lỗi STT lệch âm/dấu được xử lý tự động bằng _find_kw_end().
SYNONYMS = {
    "tên bệnh nhân": ["họ tên bệnh nhân", "bệnh nhân tên là", "bệnh nhân là", "tên người bệnh"],
    "mạch": ["nhịp tim", "mách", "mạnh"],
    "nhịp thở": ["tần số thở", "nhìn thời", "nhịp thờ"],
    "huyết áp": ["ha"],
    "nhiệt độ": ["thân nhiệt", "sốt"],
    "spo2": ["oxy máu", "bão hòa oxy"],
    "nội dung chăm sóc": ["chăm sóc", "thực hiện chăm sóc"],
    "người thực hiện": ["điều dưỡng thực hiện", "người làm"],
    "điểm nguy cơ ngã": ["điểm ngã", "nguy cơ ngã"],
    "kết quả": ["kết quả đánh giá", "kết luận"],
    "điểm đau": ["mức độ đau", "thang điểm đau"],
    "thời điểm đánh giá": ["thời gian đánh giá", "lúc đánh giá", "thời điểm"],
    "dị ứng": ["tiền sử dị ứng", "bệnh nhân dị ứng"],
    "thuốc đang dùng": ["đang dùng", "thuốc hiện tại"],
    "người liên hệ": ["người nhà", "liên hệ"],
    "tiền sử": ["tiền sử bệnh", "bệnh nền"],
    "lý do vào viện": ["vào viện vì", "lý do nhập viện", "lý do", "lý do vào", "lý do khám"],
    "chẩn đoán": ["chẩn đoán vào viện", "chẩn đoán sơ bộ", "chẩn đoán là", "chẩn đoán xác định"],
    "chẩn đoán ra viện": ["chẩn đoán khi ra viện"],
    "hướng điều trị": ["kế hoạch điều trị", "điều trị tiếp"],
    "dấu hiệu theo dõi": ["theo dõi sau mổ", "dấu hiệu"],
    "nội dung giáo dục": ["tư vấn giáo dục", "hướng dẫn bệnh nhân", "nội dung tư vấn"],
    "người nhận giáo dục": ["người nhận", "người nghe tư vấn"],
    "điểm braden": ["braden", "điểm loét"],
    "nguồn cung cấp bệnh sử": ["cung cấp bệnh sử", "cung cấp bệnh", "nguồn cung cấp", "người cung cấp", "nguồn bệnh sử"],
    "nguồn tiếp nhận": ["tiếp nhận", "muốn tiếp nhận", "muồn tiếp nhận", "nơi tiếp nhận", "đơn vị tiếp nhận"],
    "khám bụng": ["kháng bụng", "khám vùng bụng"],
    "khám ban đầu": ["khám tiếp nhận", "khám tổng quát", "khám lúc vào"],
}

_UNITS = {"không": 0, "một": 1, "mốt": 1, "hai": 2, "ba": 3, "bốn": 4, "tư": 4, "năm": 5, "lăm": 5,
          "sáu": 6, "bảy": 7, "bẩy": 7, "tám": 8, "chín": 9}
_NUMWORDS = set(_UNITS) | {"mười", "mươi", "trăm", "linh", "lẻ"}


def _parse_group(w, i):
    """Một số theo văn nói tiếng Việt (vd 'một trăm hai mươi', 'hai mươi', 'tám'). Trả (giá trị, vị trí kế)."""
    n = len(w)
    val = 0
    if i + 1 < n and w[i] in _UNITS and w[i + 1] == "trăm":
        val, i = _UNITS[w[i]] * 100, i + 2
        if i + 1 < n and w[i] in ("linh", "lẻ") and w[i + 1] in _UNITS:
            return val + _UNITS[w[i + 1]], i + 2
    if i < n and w[i] == "mười":
        val, i = val + 10, i + 1
        if i < n and w[i] in _UNITS and w[i] != "không":
            val, i = val + _UNITS[w[i]], i + 1
        return val, i
    if i + 1 < n and w[i] in _UNITS and w[i + 1] == "mươi":
        val, i = val + _UNITS[w[i]] * 10, i + 2
        if i < n and w[i] in _UNITS and w[i] != "không":
            val, i = val + _UNITS[w[i]], i + 1
        return val, i
    if i < n and w[i] in _UNITS:
        return val + _UNITS[w[i]], i + 1
    return val, i + 1


def _words_to_digits(t):
    """STT tiếng Việt thường trả số bằng chữ ('tám tám', 'hai mươi'): đổi sang chữ số.

    Các nhóm số đứng liền nhau được ghép chữ số: 'một hai mươi' -> 120, 'tám tám' -> 88, 'ba bảy' -> 37.
    Từ 'không' đứng một mình giữ nguyên (vì là từ phủ định thông dụng).
    """
    toks = re.findall(r"\w+|\W+", t)
    out, i = [], 0
    while i < len(toks):
        if toks[i] not in _NUMWORDS:
            out.append(toks[i])
            i += 1
            continue
        run, j = [], i
        while j < len(toks):
            if toks[j] in _NUMWORDS:
                run.append(toks[j])
                j += 1
            elif toks[j].isspace() and j + 1 < len(toks) and toks[j + 1] in _NUMWORDS:
                j += 1
            else:
                break
        if run == ["không"]:
            out.append("không")
        else:
            k, digits = 0, ""
            while k < len(run):
                v, k = _parse_group(run, k)
                digits += str(v)
            out.append(digits)
        i = j
    return "".join(out)


def _speech(text):
    t = _words_to_digits(norm(text))
    return re.sub(r"(\d+)\s*phẩy\s*(\d+)", r"\1.\2", t)


def _keywords_for(label):
    base = re.sub(r"\s*\([^)]*\)", "", label).strip()
    kws = [label]
    if base and base != label:
        kws.append(base)
    for k in list(kws):
        for syn in SYNONYMS.get(k, []):
            if syn not in kws:
                kws.append(syn)
    return kws


def _strip_accents(s):
    s = unicodedata.normalize("NFD", (s or "").replace("đ", "d").replace("Đ", "D"))
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()


def _find_kw_span(text, kw, allow_fuzzy=True, blocked_spans=()):
    """Tìm khoảng (start, end) của từ khóa `kw` trong `text`: ưu tiên khớp chính xác không bị lồng trong nhãn dài hơn, sau đó khớp mờ."""
    for km in re.finditer(r"\b" + re.escape(kw) + r"\b", text):
        s, e = km.start(), km.end()
        if not any(bs <= s and e <= be and (be - bs) > (e - s) for bs, be in blocked_spans):
            return s, e
    if not allow_fuzzy:
        return None

    kw_words = re.findall(r"[a-z0-9]+", _strip_accents(kw))
    if not kw_words:
        return None
    tokens = [(_strip_accents(m.group(0)), m.start(), m.end()) for m in re.finditer(r"\w+", text)]
    k = len(kw_words)
    if len(tokens) < k:
        return None

    kw_joined = " ".join(kw_words)
    best_score, best_span = 0.0, None
    for i in range(len(tokens) - k + 1):
        s_tok, e_tok = tokens[i][1], tokens[i + k - 1][2]
        if any(bs <= s_tok and e_tok <= be for bs, be in blocked_spans):
            continue
        win = [tokens[i + j][0] for j in range(k)]
        if not win[0] or win[0][0] != kw_words[0][0]:
            continue
        if k == 1:
            if len(kw_words[0]) < 4:
                continue
            score = 1.0 if win[0] == kw_words[0] else difflib.SequenceMatcher(None, win[0], kw_words[0]).ratio()
            threshold = 0.80
        else:
            if any((len(tw) <= 2 and w != tw) or difflib.SequenceMatcher(None, w, tw).ratio() < 0.70 for w, tw in zip(win, kw_words)):
                continue
            score = difflib.SequenceMatcher(None, " ".join(win), kw_joined).ratio()
            threshold = 0.84
        if score >= threshold and score > best_score:
            best_score, best_span = score, (s_tok, e_tok)
    return best_span


def _find_kw_end(text, kw, allow_fuzzy=True):
    span = _find_kw_span(text, kw, allow_fuzzy=allow_fuzzy)
    return span[1] if span else None


def extract(text, fields):
    t_raw = re.sub(r"(\d+)\s*phẩy\s*(\d+)", r"\1.\2", norm(text))
    t_num = _speech(text)
    out = {}

    # 1. Tập hợp các từ khóa ứng viên, sắp xếp từ dài đến ngắn để nhãn dài được ưu tiên trước
    #    (ví dụ: "nguồn cung cấp bệnh sử" dài hơn sẽ chiếm chỗ trước, tránh "bệnh sử" nhận nhầm)
    candidates = []
    for f in fields:
        label = norm(f["label"])
        ui = f.get("ui", "text")
        for kw in _keywords_for(label):
            candidates.append((kw, f["field_id"], ui))
    candidates.sort(key=lambda c: len(c[0]), reverse=True)

    raw_spans = []
    occupied = []
    for kw, fid, ui in candidates:
        if any(f == fid for _, _, f in raw_spans):
            continue
        for km in re.finditer(r"\b" + re.escape(kw) + r"\b", t_raw):
            s, e = km.start(), km.end()
            if not any(bs <= s and e <= be for bs, be in occupied):
                raw_spans.append((s, e, fid))
                occupied.append((s, e))
                break
        if not any(f == fid for _, _, f in raw_spans) and (ui in ("select", "checkbox") or len(kw) >= 4 or len(kw.split()) >= 2):
            span = _find_kw_span(t_raw, kw, allow_fuzzy=True, blocked_spans=occupied)
            if span:
                raw_spans.append((span[0], span[1], fid))
                occupied.append(span)

    raw_spans.sort(key=lambda x: x[0])

    # 2. Bóc tách từng trường theo biên xác định bởi mốc từ khóa kế tiếp (next_bound)
    for f in fields:
        label = norm(f["label"])
        fid = f["field_id"]
        ui = f.get("ui", "text")

        if label == "huyết áp":
            m = re.search(r"(\d{2,3})\s*(?:trên|/)\s*(\d{2,3})", t_num)
            if m:
                out[fid] = f"{m.group(1)}/{m.group(2)}"
            continue

        f_span = next(((s, e) for s, e, other in raw_spans if other == fid), None)
        if not f_span:
            continue

        other_spans = [s for s, e, other in raw_spans if other != fid and s >= f_span[1]]
        next_bound = min(other_spans, default=len(t_raw))
        rest = t_raw[f_span[1]:next_bound]

        if ui == "number":
            rest_num = _speech(rest)
            m = re.match(r"[^\d]{0,12}(\d+(?:\.\d+)?)", rest_num)
            if m:
                v = m.group(1)
                out[fid] = float(v) if "." in v else int(v)
        elif ui == "datetime":
            rest_num = _speech(rest)
            dt_m = re.search(r"(\d{4}-\d{2}-\d{2})[t\s]+(\d{1,2})(?::|\s*giờ\s*|\s+)(\d{2})", rest_num)
            if dt_m:
                out[fid] = f"{dt_m.group(1)}T{int(dt_m.group(2)):02d}:{int(dt_m.group(3)):02d}"
            else:
                hm_m = re.search(r"(\d{1,2})\s*(?:giờ|h|:)\s*(\d{2})?", rest_num)
                if hm_m:
                    hh = int(hm_m.group(1))
                    mm = int(hm_m.group(2) or 0)
                    out[fid] = f"{hh:02d}:{mm:02d}"
        elif ui == "checkbox":
            cb_m = re.match(r"\s*(?:là|:)?\s*(có|không|đúng|sai|true|false)\b", rest)
            if cb_m:
                out[fid] = cb_m.group(1) in ("có", "đúng", "true")
        elif ui in ("text", "textarea", "select"):
            m = re.match(r"\s*(?:là|:)?\s*([^.;,]+)", rest)
            val = m.group(1).strip() if (m and m.group(1).strip()) else re.sub(r"^\s*(?:là|:)\s*", "", rest).strip()
            val = re.sub(r"^[\s.:;,-]+", "", val).strip()
            if val:
                val = val[:120]
                if fid in ("ten_benh_nhan", "nguoi_lien_he"):
                    low_val = val.lower()
                    if "[tên]" in low_val:
                        val = "[TÊN]"
                    elif "[pii]" in low_val:
                        val = "[PII]"
                    else:
                        val = re.split(
                            r"\s+\b(?:mạch|mách|mạnh|nhịp|nhìn|huyết|nhiệt|spo2|số\s+điện|cccd|tư\s+thế|trạng\s+thái)\b",
                            val, maxsplit=1
                        )[0].strip()
                        val = " ".join(val.split()[:4])
                for tag in ("[tên]", "[sđt]", "[cccd]", "[pii]"):
                    if tag in val:
                        val = val.replace(tag, tag.upper())
                if not val:
                    continue
                if ui == "select":
                    options = f.get("options") or []
                    matched = next((opt for opt in options if norm(opt) == norm(val)), None)
                    if matched is None:
                        for opt in options:
                            if re.search(r"\b" + re.escape(norm(opt)) + r"\b", norm(rest)):
                                matched = opt
                                break
                    if matched is None:
                        continue
                    val = matched
                out[fid] = val

    return out


def process(text, form, mask_fn=None, audio_path=None, stt_fn=None):
    """Hàm THUẦN. mask_fn: hàm che PII (slot "pii.mask"), bắt buộc; không có thì từ chối, không đoán."""
    if mask_fn is None:
        raise RuntimeError("chưa có bộ lọc PII: truyền mask_fn (slot pii.mask)")
    if audio_path and not (text and str(text).strip()):
        runner = stt_fn or stt.transcribe
        text = runner(audio_path)

    fields = form.get("fields", [])
    payload = external_api.prepare_payload(text, mask_fn, fields=fields)
    masked = payload["text"]
    pii = payload["pii_masked"]

    low = norm(text)
    if any(k in low for k in OUT_OF_SCOPE):
        return {"masked": masked, "pii_masked": pii, "out_of_scope": True, "extracted": {}, "source": "local"}

    # --- [TẠM TẮT - CHƯA SỬ DỤNG] Bước 3 (Hybrid): Gửi văn bản ĐÃ LỌC PII qua slot voice.send ---
    # api_res = external_api.send_filtered(payload)
    # if isinstance(api_res, dict) and api_res.get("sent") and isinstance(api_res.get("extracted"), dict):
    #     cleaned = external_api.sanitize_extracted(api_res["extracted"], fields)
    #     if cleaned:
    #         return {"masked": masked, "pii_masked": pii, "out_of_scope": False, "extracted": cleaned,
    #                 "source": "api"}

    # Trích xuất 100% Local từ bản đã che định danh (không gửi dữ liệu ra ngoài)
    return {"masked": masked, "pii_masked": pii, "out_of_scope": False,
            "extracted": extract(masked, fields), "source": "local"}
