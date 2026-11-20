"""Test độc lập của tính năng voice input 100% Local (không cần lõi, store hay tính năng khác).

Chạy:  python features/voice_input/test_voice.py
Bộ lọc PII được TIÊM vào (fake), nên test không phụ thuộc features/pii_filter.
"""
import struct
import sys
import tempfile
import unittest
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from contracts import registry  # noqa: E402
from features.voice_input import external_api, stt, voice  # noqa: E402

FORM = {"fields": [
    {"field_id": "mach", "label": "Mạch", "ui": "number"},
    {"field_id": "huyet_ap", "label": "Huyết áp", "ui": "text"},
    {"field_id": "nhiet_do", "label": "Nhiệt độ", "ui": "number"},
]}


def fake_mask(text):
    """Bộ lọc giả: chỉ che chuỗi SĐT mẫu, để kiểm tra voice dùng đúng bản đã che."""
    count = text.count("0912345678") + text.count("0000000000")
    return text.replace("0912345678", "[SĐT]").replace("0000000000", "[SĐT]"), count


class VoiceProcessTests(unittest.TestCase):
    def test_extracts_fields_from_speech(self):
        out = voice.process("Mạch 88, huyết áp 120 trên 80, nhiệt độ 37 phẩy 2", FORM, mask_fn=fake_mask)
        self.assertEqual(out["extracted"], {"mach": 88, "huyet_ap": "120/80", "nhiet_do": 37.2})
        self.assertFalse(out["out_of_scope"])
        self.assertEqual(out["source"], "local")

    def test_uses_injected_mask_and_extracts_from_masked_text(self):
        out = voice.process("Số 0912345678, mạch 90", FORM, mask_fn=fake_mask)
        self.assertIn("[SĐT]", out["masked"])
        self.assertNotIn("0912345678", out["masked"])
        self.assertEqual(out["pii_masked"], 1)
        self.assertEqual(out["extracted"], {"mach": 90})
        self.assertEqual(out["source"], "local")

    def test_out_of_scope_sentence_extracts_nothing(self):
        out = voice.process("Hôm nay trời đẹp quá, mạch 80", FORM, mask_fn=fake_mask)
        self.assertTrue(out["out_of_scope"])
        self.assertEqual(out["extracted"], {})
        self.assertEqual(out["source"], "local")

    def test_refuses_to_run_without_a_mask(self):
        # Không có bộ lọc thì không xử lý, để tránh đưa văn bản chưa che vào pipeline
        with self.assertRaises(RuntimeError):
            voice.process("mạch 80", FORM)

    def test_process_transcribes_audio_via_phowhisper_before_masking_and_extracting(self):
        fake_stt = lambda path: "Số 0912345678, mạch 92, huyết áp 120 trên 80"
        out = voice.process("", FORM, mask_fn=fake_mask, audio_path="recording.wav", stt_fn=fake_stt)
        self.assertIn("[SĐT]", out["masked"])
        self.assertEqual(out["pii_masked"], 1)
        self.assertEqual(out["extracted"], {"mach": 92, "huyet_ap": "120/80"})
        self.assertEqual(out["source"], "local")

    def test_process_always_runs_local_without_calling_external_api(self):
        called = []
        registry.connect("voice.send", lambda p: called.append(p) or {"sent": True, "extracted": {"mach": 999}})
        try:
            out = voice.process("Mạch 84, nhiệt độ 36 phẩy 8", FORM, mask_fn=fake_mask)
            self.assertEqual(called, [])
            self.assertEqual(out["source"], "local")
            self.assertEqual(out["extracted"], {"mach": 84, "nhiet_do": 36.8})
        finally:
            registry.disconnect("voice.send")

    def test_extracts_datetime_checkbox_select_and_parenthetical_labels(self):
        dynamic_form = {"fields": [
            {"field_id": "diem_dau", "label": "Điểm đau", "ui": "number"},
            {"field_id": "thoi_diem_danh_gia", "label": "Thời điểm đánh giá", "ui": "datetime"},
            {"field_id": "can_nang", "label": "Cân nặng (kg)", "ui": "number"},
            {"field_id": "an_kem", "label": "Ăn kém gần đây", "ui": "checkbox"},
            {"field_id": "sut_can", "label": "Sụt cân không chủ ý", "ui": "select", "options": ["Có", "Không"]},
        ]}
        text = (
            "Điểm đau 4, thời điểm đánh giá 2026-11-16 09:30, "
            "cân nặng 54 phẩy 5, ăn kém gần đây có, sụt cân không chủ ý không"
        )
        out = voice.process(text, dynamic_form, mask_fn=fake_mask)
        self.assertEqual(out["extracted"], {
            "diem_dau": 4,
            "thoi_diem_danh_gia": "2026-11-16T09:30",
            "can_nang": 54.5,
            "an_kem": True,
            "sut_can": "Không",
        })


class ExternalApiContractTests(unittest.TestCase):
    def test_prepare_payload_masks_before_sending(self):
        payload = external_api.prepare_payload("Số 0912345678", fake_mask)
        self.assertEqual(payload, {"text": "Số [SĐT]", "pii_filtered": True, "pii_masked": 1})

    def test_send_refuses_unfiltered_content(self):
        with self.assertRaises(ValueError):
            external_api.send_filtered("Số 0912345678")
        with self.assertRaises(ValueError):
            external_api.send_filtered({"text": "Số 0912345678", "pii_filtered": False})

    def test_default_sender_is_disabled(self):
        payload = external_api.prepare_payload("mạch 80", fake_mask)
        self.assertFalse(external_api.send_filtered(payload)["sent"])

    def test_connected_sender_receives_only_filtered_payload(self):
        received = []
        registry.connect("voice.send", lambda p: received.append(p) or {"sent": True})
        try:
            payload = external_api.prepare_payload("Số 0912345678", fake_mask)
            self.assertEqual(external_api.send_filtered(payload), {"sent": True})
            self.assertEqual(received, [payload])
        finally:
            registry.disconnect("voice.send")
        self.assertFalse(external_api.send_filtered(external_api.prepare_payload("x", fake_mask))["sent"])

    def test_prepare_payload_includes_fields_when_provided(self):
        payload = external_api.prepare_payload("mạch 80", fake_mask, fields=FORM["fields"])
        self.assertTrue(payload["pii_filtered"])
        self.assertEqual(payload["fields"], FORM["fields"])

    def test_sanitize_extracted_filters_unknown_fields_and_coerces_types(self):
        fields = FORM["fields"] + [{"field_id": "an_kem", "label": "Ăn kém", "ui": "checkbox"}]
        raw_extracted = {
            "mach": "88",
            "nhiet_do": "37.5",
            "huyet_ap": "120/80",
            "an_kem": "có",
            "truong_la": "abc",
        }
        cleaned = external_api.sanitize_extracted(raw_extracted, fields)
        self.assertEqual(cleaned, {"mach": 88, "nhiet_do": 37.5, "huyet_ap": "120/80", "an_kem": True})

    # --- [TẠM TẮT - CHƯA SỬ DỤNG] Unit tests cho Cloud LLM API (llm_sender) ---
    # def test_llm_sender_without_api_key_returns_not_sent(self):
    #     import os
    #     old = os.environ.pop("VOICE_API_KEY", None)
    #     try:
    #         payload = external_api.prepare_payload("mạch 80", fake_mask, fields=FORM["fields"])
    #         res = external_api.llm_sender(payload)
    #         self.assertFalse(res["sent"])
    #         self.assertIn("VOICE_API_KEY", res["reason"])
    #     finally:
    #         if old is not None:
    #             os.environ["VOICE_API_KEY"] = old
    #
    # def test_llm_sender_parses_response_and_handles_network_errors(self):
    #     import io, json, os, urllib.error
    #     from unittest.mock import patch
    #     os.environ["VOICE_API_KEY"] = "test-key"
    #     try:
    #         payload = external_api.prepare_payload("mạch 88", fake_mask, fields=FORM["fields"])
    #         fake_resp = io.BytesIO(json.dumps({
    #             "choices": [{"message": {"content": '{"mach": "88", "huyet_ap": "120/80"}'}}]
    #         }).encode("utf-8"))
    #         fake_resp.__enter__ = lambda s: s
    #         fake_resp.__exit__ = lambda *a: False
    #         with patch("urllib.request.urlopen", return_value=fake_resp):
    #             res = external_api.llm_sender(payload)
    #             self.assertEqual(res, {"sent": True, "extracted": {"mach": 88, "huyet_ap": "120/80"}})
    #         with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("timeout")):
    #             err_res = external_api.llm_sender(payload)
    #             self.assertFalse(err_res["sent"])
    #             self.assertIn("lỗi gọi API", err_res["reason"])
    #     finally:
    #         os.environ.pop("VOICE_API_KEY", None)


class PhoWhisperSttTests(unittest.TestCase):
    def setUp(self):
        stt.clear_cache()

    def test_transcribe_uses_injected_backend_and_strips_text(self):
        calls = []

        def fake_backend(path, model_name):
            calls.append((str(path), model_name))
            return "  Mạch 88, huyết áp 120 trên 80  "

        text = stt.transcribe("sample.wav", backend_fn=fake_backend, vad_fn=lambda p: True)
        self.assertEqual(text, "Mạch 88, huyết áp 120 trên 80")
        self.assertEqual(calls, [("sample.wav", "vinai/PhoWhisper-small")])

    def test_transcribe_skips_phowhisper_when_vad_detects_silence(self):
        called = []

        def fake_backend(path, model_name):
            called.append(path)
            return "Ảo giác khi im lặng"

        text = stt.transcribe("silent.wav", backend_fn=fake_backend, vad_fn=lambda p: False)
        self.assertEqual(text, "")
        self.assertEqual(called, [])

    def test_vad_detects_silence_and_speech_on_wav_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            silent_wav = Path(tmp) / "silent.wav"
            with wave.open(str(silent_wav), "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(b"\x00\x00" * 8000)
            self.assertFalse(stt.has_speech(silent_wav))
            self.assertEqual(stt.detect_voice_segments(silent_wav), [])

            speech_wav = Path(tmp) / "speech.wav"
            with wave.open(str(speech_wav), "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                tone = struct.pack("<h", 4000) * 8000
                wf.writeframes(tone)
            self.assertTrue(stt.has_speech(speech_wav))
            self.assertTrue(len(stt.detect_voice_segments(speech_wav)) >= 1)

    def test_transcribe_with_info_always_uses_local_phowhisper_backend(self):
        with tempfile.TemporaryDirectory() as tmp:
            speech_wav = Path(tmp) / "speech.wav"
            with wave.open(str(speech_wav), "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(struct.pack("<h", 4000) * 8000)

            info = stt.transcribe_with_info(speech_wav, backend_fn=lambda p, m: "Mạch 88")
            self.assertEqual(info["backend"], "phowhisper")
            self.assertEqual(info["text"], "Mạch 88")
            self.assertIsNone(info["error"])
            self.assertTrue(len(info["segments"]) >= 1)

    def test_transcribe_rejects_empty_audio_path(self):
        with self.assertRaises(ValueError):
            stt.transcribe("")

    def test_split_audio_chunks_splits_60s_audio_under_28s_at_quiet_pauses(self):
        import importlib
        try:
            np = importlib.import_module("numpy")
        except ModuleNotFoundError:
            self.skipTest("numpy chưa cài")
        rate = 16000
        # Tạo âm thanh 60 giây có tiếng nói liên tục, nhưng có khoảng im lặng 0.5s ở giây 24 và giây 48
        arr = np.full(60 * rate, 0.2, dtype="float32")
        arr[24 * rate : int(24.5 * rate)] = 0.0
        arr[48 * rate : int(48.5 * rate)] = 0.0
        chunks = stt._split_audio_chunks(arr, rate)
        self.assertEqual(len(chunks), 3)
        self.assertEqual(sum(len(c) for c in chunks), len(arr))
        for c in chunks:
            self.assertLessEqual(len(c) / rate, stt.MAX_CHUNK_SECONDS)
        # Điểm cắt đầu tiên phải rơi đúng khoảng im lặng 24.0..24.5s
        self.assertAlmostEqual(len(chunks[0]) / rate, 24.25, delta=0.3)

    # --- [TẠM TẮT - CHƯA SỬ DỤNG] Unit tests cho Cloud STT Blaze.vn ---
    # def test_blaze_stt_without_key_returns_none(self):
    #     import os
    #     old = os.environ.pop("BLAZE_API_KEY", None)
    #     try:
    #         self.assertIsNone(stt.blaze_stt("sample.wav"))
    #     finally:
    #         if old is not None:
    #             os.environ["BLAZE_API_KEY"] = old
    #
    # def test_blaze_stt_transcribes_via_mocked_urlopen(self):
    #     import io, json, os
    #     from unittest.mock import patch
    #     with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
    #         tmp.write(b"RIFFdummyWAVEfmt ")
    #         tmp_path = tmp.name
    #     try:
    #         fake_resp = io.BytesIO(json.dumps({"text": "Bệnh nhân mạch 80, huyết áp 120/80"}).encode("utf-8"))
    #         fake_resp.__enter__ = lambda s: s
    #         fake_resp.__exit__ = lambda *a: False
    #         with patch("urllib.request.urlopen", return_value=fake_resp):
    #             text = stt.blaze_stt(tmp_path, api_key="blaze-test-key")
    #             self.assertEqual(text, "Bệnh nhân mạch 80, huyết áp 120/80")
    #     finally:
    #         try:
    #             os.unlink(tmp_path)
    #         except OSError:
    #             pass

    def test_vad_segments_long_pause_audio(self):
        wav_path = Path(__file__).resolve().parents[2] / "data" / "sample_audio" / "sample_noi_va_dung_lau_8s.wav"
        if not wav_path.is_file():
            self.skipTest("sample_noi_va_dung_lau_8s.wav chưa được tạo")
        segs = stt.detect_voice_segments(wav_path)
        self.assertEqual(len(segs), 2)
        self.assertAlmostEqual(segs[0][0], 0.0, delta=0.1)
        self.assertAlmostEqual(segs[0][1], 2.0, delta=0.2)
        self.assertAlmostEqual(segs[1][0], 6.0, delta=0.2)
        self.assertAlmostEqual(segs[1][1], 8.0, delta=0.2)

    def test_multi_speaker_and_pause_dialogue_extraction(self):
        """Kiểm thử hội thoại đa vai (ĐD, BN) kèm ngắt quãng dừng lâu và cập nhật chỉ số."""
        turns = [
            ("Điều dưỡng", "Chào bác An, số điện thoại 0912345678, hôm nay trời đẹp quá."),
            ("Bệnh nhân", "Chào cô, tôi thấy đỡ sốt rồi."),
            ("Điều dưỡng", "Mạch 88, nhịp thở 20, SpO2 98, nhiệt độ 37 phẩy 2."),
            # Mô phỏng tạm dừng 4 giây quấn băng đo huyết áp và đo lại mạch
            ("Điều dưỡng", "Huyết áp 118 trên 76, mạch 90."),
        ]
        form = {
            "fields": [
                {"field_id": "mach", "label": "Mạch", "ui": "number"},
                {"field_id": "nhip_tho", "label": "Nhịp thở", "ui": "number"},
                {"field_id": "huyet_ap", "label": "Huyết áp", "ui": "text"},
                {"field_id": "nhiet_do", "label": "Nhiệt độ", "ui": "number"},
                {"field_id": "spo2", "label": "SpO2", "ui": "number"},
            ]
        }
        draft = {}
        total_pii = 0
        for who, text in turns:
            res = voice.process(text, form, mask_fn=fake_mask)
            total_pii += res["pii_masked"]
            if not res["out_of_scope"]:
                draft.update(res["extracted"])

        self.assertEqual(total_pii, 1)  # Đã che SĐT
        # Giá trị mạch ban đầu 88 đã được cập nhật thành 90 sau khi đo lại
        self.assertEqual(draft, {
            "mach": 90,
            "nhip_tho": 20,
            "spo2": 98,
            "nhiet_do": 37.2,
            "huyet_ap": "118/76",
        })

    def test_extracts_from_spoken_number_words_like_phowhisper_output(self):
        """Đúng câu PhoWhisper trả về khi thử micro thật: số bằng chữ + nghe nhầm 'mạch', 'nhịp thở'."""
        form = {"fields": [
            {"field_id": "mach", "label": "Mạch", "ui": "number"},
            {"field_id": "nhip_tho", "label": "Nhịp thở", "ui": "number"},
            {"field_id": "huyet_ap", "label": "Huyết áp", "ui": "text"},
            {"field_id": "nhiet_do", "label": "Nhiệt độ", "ui": "number"},
        ]}
        text = "mách tám tám nhìn thời hai mươi huyết áp một hai mươi trên tám mươi nhiệt độ ba bảy phẩy hai."
        res = voice.process(text, form, mask_fn=fake_mask)
        self.assertEqual(res["extracted"], {"mach": 88, "nhip_tho": 20, "huyet_ap": "120/80", "nhiet_do": 37.2})

    def test_words_to_digits_keeps_plain_khong(self):
        self.assertEqual(voice._words_to_digits("bệnh nhân không đau"), "bệnh nhân không đau")
        self.assertEqual(voice._words_to_digits("một trăm hai mươi lăm"), "125")
        self.assertEqual(voice._words_to_digits("chín mươi"), "90")

    def test_fuzzy_matching_handles_unlisted_stt_mishearings_without_false_positives(self):
        """Khớp mờ tự bắt các lỗi STT lệch dấu/lệch âm không cần khai báo trong SYNONYMS, và không khớp nhầm."""
        form = {"fields": [
            {"field_id": "mach", "label": "Mạch", "ui": "number"},
            {"field_id": "nhip_tho", "label": "Nhịp thở", "ui": "number"},
            {"field_id": "nhiet_do", "label": "Nhiệt độ", "ui": "number"},
            {"field_id": "diem_dau", "label": "Điểm đau", "ui": "number"},
        ]}
        # "mạnh", "nhịp thờ", "nhiệt đố" không hề nằm trong SYNONYMS
        res = voice.process("mạnh 85, nhịp thờ 19, nhiệt đố 37 phẩy 5", form, mask_fn=fake_mask)
        self.assertEqual(res["extracted"], {"mach": 85, "nhip_tho": 19, "nhiet_do": 37.5})
        # Câu không liên quan không được khớp nhầm
        res2 = voice.process("bệnh nhân nằm nghỉ tại giường số 12", form, mask_fn=fake_mask)
        self.assertEqual(res2["extracted"], {})

    def test_longer_field_label_prevents_shorter_synonym_collision(self):
        """Nhãn dài ('đáp ứng sau chăm sóc', 'nguồn cung cấp bệnh sử') không bị từ khóa ngắn ('chăm sóc', 'bệnh sử') khớp đè."""
        care_form = {"fields": [
            {"field_id": "thuc_hien", "label": "Nội dung chăm sóc", "ui": "textarea"},
            {"field_id": "dap_ung", "label": "Đáp ứng sau chăm sóc", "ui": "textarea"},
        ]}
        res = voice.process(
            "Nội dung chăm sóc là thay ga giường. Đáp ứng sau chăm sóc là người bệnh dễ chịu.",
            care_form, mask_fn=fake_mask,
        )
        self.assertEqual(res["extracted"], {
            "thuc_hien": "thay ga giường",
            "dap_ung": "người bệnh dễ chịu",
        })

        admit_form = {"fields": [
            {"field_id": "nguoi_cung_cap", "label": "Nguồn cung cấp bệnh sử", "ui": "select", "options": ["Người bệnh", "Người chăm sóc"]},
            {"field_id": "benh_su", "label": "Bệnh sử", "ui": "textarea"},
        ]}
        res2 = voice.process(
            "Nguồn cung cấp bệnh sử là người bệnh. Bệnh sử là đau âm ỉ tăng sau ăn.",
            admit_form, mask_fn=fake_mask,
        )
        self.assertEqual(res2["extracted"], {
            "nguoi_cung_cap": "Người bệnh",
            "benh_su": "đau âm ỉ tăng sau ăn",
        })

    def test_continuous_speech_without_punctuation_does_not_overflow_fields(self):
        """Giọng nói liên tục không có dấu câu ngăn trường trước nuốt nội dung trường kế tiếp."""
        admit_form = {"fields": [
            {"field_id": "ten_benh_nhan", "label": "Tên bệnh nhân", "ui": "text"},
            {"field_id": "nguoi_cung_cap", "label": "Nguồn cung cấp bệnh sử", "ui": "select", "options": ["Người bệnh", "Người chăm sóc"]},
            {"field_id": "cach_vao_khoa", "label": "Cách vào khoa", "ui": "select", "options": ["Tự đi", "Xe lăn", "Cáng"]},
            {"field_id": "ly_do_vao_vien", "label": "Lý do vào viện", "ui": "textarea"},
            {"field_id": "benh_su", "label": "Bệnh sử", "ui": "textarea"},
            {"field_id": "trieu_chung_kem", "label": "Triệu chứng đi kèm", "ui": "textarea"},
            {"field_id": "kham_ban_dau", "label": "Khám ban đầu", "ui": "textarea"},
            {"field_id": "kham_bung", "label": "Khám bụng", "ui": "textarea"},
            {"field_id": "chan_doan", "label": "Chẩn đoán", "ui": "textarea"},
        ]}
        speech = (
            "tên bệnh nhân là [TÊN] cung cấp bệnh là người bệnh cách vào khoa tự đi "
            "lý do đau bụng vùng thượng vị hai ngày bệnh sử đau âm ỉ tăng sau ăn "
            "triệu chứng đi kèm buồn nôn nhẹ khám ban đầu người bệnh tỉnh tiếp xúc tốt "
            "kháng bụng mềm ấn tức nhẹ chẩn đoán là theo dõi viêm dạ dày cấp"
        )
        res = voice.process(speech, admit_form, mask_fn=fake_mask)
        ext = res["extracted"]
        self.assertEqual(ext["ten_benh_nhan"], "[TÊN]")
        self.assertEqual(ext["nguoi_cung_cap"], "Người bệnh")
        self.assertEqual(ext["cach_vao_khoa"], "Tự đi")
        self.assertEqual(ext["ly_do_vao_vien"], "đau bụng vùng thượng vị hai ngày")
        self.assertEqual(ext["benh_su"], "đau âm ỉ tăng sau ăn")
        self.assertEqual(ext["trieu_chung_kem"], "buồn nôn nhẹ")
        self.assertEqual(ext["kham_ban_dau"], "người bệnh tỉnh tiếp xúc tốt")
        self.assertEqual(ext["kham_bung"], "mềm ấn tức nhẹ")
        self.assertEqual(ext["chan_doan"], "theo dõi viêm dạ dày cấp")

    def test_extracts_pii02_placeholder_uppercase(self):
        """Hỗ trợ placeholder chuẩn [PII] của PII-02 bên cạnh [TÊN]/[SĐT]/[CCCD]."""
        form = {"fields": [
            {"field_id": "ten_benh_nhan", "label": "Tên bệnh nhân", "ui": "text"},
            {"field_id": "nguoi_lien_he", "label": "Người liên hệ", "ui": "text"},
            {"field_id": "mach", "label": "Mạch", "ui": "number"},
        ]}
        pii02_fake = lambda s: (
            s.replace("Nguyễn Văn An", "[PII]").replace("Trần Thị Bình", "[PII]"),
            2,
        )
        res = voice.process(
            "Tên bệnh nhân là Nguyễn Văn An, người liên hệ là Trần Thị Bình, mạch 86.",
            form,
            mask_fn=pii02_fake,
        )
        self.assertEqual(res["extracted"]["ten_benh_nhan"], "[PII]")
        self.assertEqual(res["extracted"]["nguoi_lien_he"], "[PII]")
        self.assertEqual(res["extracted"]["mach"], 86)


if __name__ == "__main__":
    unittest.main(verbosity=2)
