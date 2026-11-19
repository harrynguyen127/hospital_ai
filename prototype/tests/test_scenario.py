"""Kiểm thử kịch bản demo bắt buộc (TEAM_ACTION_PLAN A2) + các nhánh chính.

Module được kiểm: features/policy_rules, reminder (services), features/detect_form, features/voice_input
(gồm external_api), features/pii_filter. Repo chưa có test nào
khác. Chạy:  python tests/test_scenario.py   (từ thư mục prototype/)
Dùng thư mục runtime tạm, không đụng tới .runtime/ của bản chạy thật.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ["PROTO_RUNTIME_DIR"] = tempfile.mkdtemp(prefix="proto_test_")
sys.path.insert(0, str(ROOT))

from features.pii_filter import pii  # noqa: E402
from features.voice_input.external_api import prepare_payload, send_filtered  # noqa: E402
from services import engine, reminder, store  # noqa: E402
import server  # noqa: E402


def _v2_text():
    return (ROOT / "data" / "regulations" / "qd_chamsoc_v2.txt").read_text(encoding="utf-8")


EMR_SINH_TON = {
    "title": "Bảng theo dõi dấu hiệu sinh tồn cho người lớn",
    "fields": [
        {"label": "Tên bệnh nhân", "ui": "text"},
        {"label": "Thời điểm đo", "ui": "datetime"},
        {"label": "Tư thế đo", "ui": "select"},
        {"label": "Lý do đo", "ui": "select"},
        {"label": "Trạng thái lúc đo", "ui": "select"},
        {"label": "Vị trí đo huyết áp", "ui": "select"},
        {"label": "Vị trí đo nhiệt độ", "ui": "select"},
        {"label": "Mạch", "ui": "number", "required": True},
        {"label": "Nhịp thở", "ui": "number", "required": True},
        {"label": "Huyết áp", "ui": "text"},
        {"label": "Nhiệt độ", "ui": "number"},
        {"label": "SpO2", "ui": "number"},
        {"label": "Nhịp mạch khi bắt", "ui": "select"},
        {"label": "Kiểu thở quan sát được", "ui": "select"},
        {"label": "Hỗ trợ hô hấp lúc đo", "ui": "select"},
        {"label": "Tiếp xúc khi đo", "ui": "select"},
        {"label": "Triệu chứng người bệnh mô tả", "ui": "textarea"},
        {"label": "So với lần đo trước", "ui": "textarea"},
        {"label": "Việc đã thực hiện sau đo", "ui": "textarea"},
        {"label": "Điểm cần bàn giao", "ui": "textarea"},
    ],
}


class ScenarioTests(unittest.TestCase):
    def setUp(self):
        store.reset()
        server.ensure_seeded()

    def count(self, user="bs_a"):
        return reminder.summary(store.read(), user)["count"]

    # --- Kịch bản 13 -> 15 ---
    def test_v1_gives_13_tasks_for_doctor(self):
        self.assertEqual(self.count("bs_a"), 13)
        self.assertEqual(reminder.active_ruleset(store.read())["version"], "v1")

    def test_publish_v2_gives_15_then_rollback_to_13(self):
        with store.transaction() as st:
            res = engine.ingest(st, "QD-CHAMSOC-2026", "v2", _v2_text(), "2026-11-16")
        self.assertTrue(res["ok"])
        self.assertEqual(res["published_version"], "v2")
        self.assertEqual(res["summary"]["needs_clarification"], 1)  # khoản 2.2 (mơ hồ) không được áp dụng
        self.assertEqual(len(res["diff"]["added"]), 2)
        self.assertEqual(len(res["diff"]["changed"]), 1)
        self.assertEqual(self.count("bs_a"), 15)

        with store.transaction() as st:
            engine.rollback_policy(st)
        self.assertEqual(reminder.active_ruleset(store.read())["version"], "v1")
        self.assertEqual(self.count("bs_a"), 13)

    def test_dry_run_does_not_publish(self):
        with store.transaction() as st:
            res = engine.ingest(st, "QD-CHAMSOC-2026", "v2", _v2_text(), "2026-11-16", dry_run=True)
        self.assertTrue(res["dry_run"])
        self.assertEqual(res["impact"]["bs_a"], {"before": 13, "after": 15})
        self.assertEqual(len(store.read()["rulesets"]), 1)

    def test_unknown_form_is_rejected_not_applied(self):
        text = ("1.1 Bác sĩ phải lập phiếu không tồn tại trong vòng 24 giờ kể từ khi "
                "bệnh nhân vào viện. Trường bắt buộc: a.")
        with store.transaction() as st:
            res = engine.ingest(st, "QD-TEST", "v1", text, "2026-11-16", dry_run=True)
        self.assertEqual(res["checked"][0]["status"], "rejected")
        self.assertFalse(res["ok"])  # không có luật nào được áp dụng

    def test_saving_required_record_closes_task(self):
        res = server.p_records({"patient_id": "BN-02", "form_id": "benh_an_vao_vien",
                                "values": {"ly_do_vao_vien": "Đau bụng", "chan_doan": "Sỏi mật"},
                                "user": "bs_a"})
        self.assertEqual(res["record"]["missing_required"], [])
        self.assertEqual(self.count("bs_a"), 12)

    def test_incomplete_record_keeps_task_and_lists_missing_field(self):
        tasks = reminder.summary(store.read(), "dd_b")["tasks"]
        t = next(t for t in tasks if t["patient_id"] == "BN-02" and t["form_id"] == "phieu_danh_gia_ban_dau")
        self.assertEqual(t["missing_fields"], ["nguoi_lien_he"])

    def test_partial_vitals_do_not_postpone_deadline(self):
        def task():
            return next(t for t in reminder.summary(store.read(), "dd_b")["tasks"]
                        if t["patient_id"] == "BN-01" and t["form_id"] == "phieu_sinh_ton_nguoi_lon")

        due = task()["due"]
        record = {"patient_id": "BN-01", "form_id": "phieu_sinh_ton_nguoi_lon", "user": "dd_b"}
        server.p_records({**record, "values": {"mach": 88}})
        self.assertEqual(task()["missing_labels"], ["Nhịp thở"])
        self.assertEqual(task()["due"], due)
        server.p_records({**record, "values": {"mach": 88, "nhip_tho": 20}})
        self.assertEqual(task()["missing_fields"], [])
        self.assertEqual(task()["due"], "2026-11-16T14:00:00+07:00")

    # --- Detect form ---
    def test_detect_exact_near_and_new(self):
        with store.transaction() as st:
            exact = engine.detect(st,{"method": "dom", **EMR_SINH_TON})
        self.assertEqual(exact["match"], "exact")
        self.assertEqual(exact["form_id"], "phieu_sinh_ton_nguoi_lon")

        variant = {**EMR_SINH_TON, "fields": EMR_SINH_TON["fields"] + [{"label": "Ghi chú", "ui": "text"}]}
        with store.transaction() as st:
            near = engine.detect(st,{"method": "dom", **variant})
        self.assertTrue(near["match"].startswith("gần giống"))
        self.assertEqual(near["version"], 2)
        self.assertEqual(near["field_map"][-1]["field_id"], "ghi_chu")
        # Lần thứ hai: nhãn đã có trong registry, không tạo thêm phiên bản
        with store.transaction() as st:
            again = engine.detect(st,{"method": "dom", **variant})
        self.assertEqual(again["version"], 2)

        new_form = {"title": "Sàng lọc dinh dưỡng", "fields": [
            {"label": "Cân nặng (kg)", "ui": "number", "required": True},
            {"label": "Ăn kém gần đây", "ui": "checkbox"},
            {"label": "Sụt cân không chủ ý", "ui": "select", "options": ["Có", "Không"]},
        ]}
        with store.transaction() as st:
            new = engine.detect(st,{"method": "dom", **new_form})
        self.assertEqual(new["match"], "mới")
        self.assertEqual(new["status"], "active")
        self.assertEqual(new["form_id"], "phieu_sang_loc_dinh_duong")

    # --- Voice ---
    def test_voice_masks_pii_and_extracts_fields(self):
        form = store.read()["forms"]["phieu_sinh_ton_nguoi_lon"]
        res = engine.voice_process("Anh Mẫu A, số điện thoại 0000000000, hôm nay trời đẹp quá.", form)
        self.assertNotIn("0000000000", res["masked"])
        self.assertIn("[SĐT]", res["masked"])
        self.assertNotIn("Mẫu A", res["masked"])
        self.assertTrue(res["out_of_scope"])

        res = engine.voice_process("Mạch 88, nhịp thở 20, huyết áp 120 trên 80, nhiệt độ 37 phẩy 2, SpO2 98.", form)
        self.assertEqual(res["extracted"], {"mach": 88, "nhip_tho": 20, "huyet_ap": "120/80",
                                            "nhiet_do": 37.2, "spo2": 98})

    def test_all_10_forms_local_test_scenarios_pass_continuously_and_segmented(self):
        """Toàn bộ 10 kịch bản test trên 10 form trích xuất đúng 100% ở cả 2 chế độ (nói liên tục & kịch bản mẫu)."""
        import json, re
        forms = store.read()["forms"]
        scenarios_file = ROOT.parent / "docs" / "VOICE_LOCAL_TEST_SCENARIOS.md"
        doc = scenarios_file.read_text(encoding="utf-8")
        scenarios = re.findall(
            r"## Kịch bản (\d+):[^(]+\((`[^`]+`)\).*?### Kịch bản thoại đầu vào \(Input\)(.*?)### Synthetic Output(.*?)```json\s*(.*?)\s*```",
            doc,
            re.DOTALL,
        )
        self.assertEqual(len(scenarios), 10)

        for num, fid_code, input_block, _, synth_json in scenarios:
            fid = fid_code.strip("`")
            form = forms[fid]
            expected = json.loads(synth_json)["extracted"]

            lines = [m.group(1) for m in re.finditer(r'> \d+\.\s*"([^"]+)"', input_block)]
            full_text = " ".join(lines)
            raw_cont = re.sub(r"[,.:;!?]+", " ", full_text).lower()
            raw_cont = re.sub(r"\s+", " ", raw_cont).strip()

            # Chế độ nói liên tục không dấu câu (PhoWhisper thực tế)
            res_cont = engine.voice_process(raw_cont, form)
            ext_cont = res_cont["extracted"]

            # Chế độ từng câu (Kịch bản mẫu trên Web)
            ext_seg = {}
            for line in lines:
                r = engine.voice_process(line, form)
                ext_seg.update(r["extracted"])

            for k, exp_val in expected.items():
                self.assertIn(k, ext_cont, f"Kịch bản {num} ({fid}) thiếu trường {k} ở chế độ nói liên tục")
                self.assertIn(k, ext_seg, f"Kịch bản {num} ({fid}) thiếu trường {k} ở chế độ kịch bản mẫu")
                self.assertEqual(
                    str(ext_cont[k]).strip().lower(),
                    str(exp_val).strip().lower(),
                    f"Kịch bản {num} ({fid}) sai giá trị trường {k} ở chế độ nói liên tục: expected='{exp_val}' got='{ext_cont[k]}'"
                )
                self.assertEqual(
                    str(ext_seg[k]).strip().lower(),
                    str(exp_val).strip().lower(),
                    f"Kịch bản {num} ({fid}) sai giá trị trường {k} ở chế độ kịch bản mẫu: expected='{exp_val}' got='{ext_seg[k]}'"
                )

    # --- Gửi API ngoài: chỉ nhận bản đã lọc PII ---
    def test_external_api_refuses_unfiltered_text(self):
        with self.assertRaises(ValueError):
            send_filtered({"text": "SĐT 0000000000", "pii_filtered": False})
        with self.assertRaises(ValueError):
            send_filtered("SĐT 0000000000")

    def test_external_api_payload_is_masked_and_disabled_by_default(self):
        payload = prepare_payload("Bệnh nhân Mẫu A, SĐT 0000000000, mạch 88.", pii.mask)
        self.assertNotIn("0000000000", payload["text"])
        self.assertNotIn("Mẫu A", payload["text"])
        self.assertEqual(payload["pii_masked"], 2)
        self.assertEqual(send_filtered(payload), {"sent": False, "reason": "prototype: API ngoài chưa được bật"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
