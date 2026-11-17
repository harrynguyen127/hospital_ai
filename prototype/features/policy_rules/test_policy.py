"""Test độc lập của tính năng policy → rule (hàm thuần, không cần store hay reminder).

Chạy:  python features/policy_rules/test_policy.py
Tác động (impact) được TIÊM vào bằng hàm giả, nên không cần lõi nhắc việc.
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from features.policy_rules import policy  # noqa: E402
from shared.common import fingerprint  # noqa: E402

CLOCK = "2026-11-10T10:00:00+07:00"
REG = ROOT / "data" / "regulations"


def seed_forms():
    raw = json.loads((ROOT / "data" / "form_registry" / "forms.json").read_text(encoding="utf-8"))
    return {fid: {"form_id": fid, **f, "status": "active", "version": 1,
                  "fingerprint": fingerprint(f["title"], f["fields"]), "history": []}
            for fid, f in raw.items()}


def ingest(text, doc_version, rulesets, dry_run=False, impact_fn=None):
    return policy.ingest(text, "QD-CHAMSOC-2026", doc_version, "2026-11-10", rulesets=rulesets,
                         forms=seed_forms(), docs={}, clock=CLOCK, dry_run=dry_run, impact_fn=impact_fn)


class PolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v1 = (REG / "qd_chamsoc_v1.txt").read_text(encoding="utf-8")
        cls.v2 = (REG / "qd_chamsoc_v2.txt").read_text(encoding="utf-8")

    def test_publish_v1_returns_new_ruleset_without_touching_input(self):
        rulesets = []
        out = ingest(self.v1, "v1", rulesets)
        self.assertTrue(out["result"]["ok"])
        self.assertEqual(out["result"]["published_version"], "v1")
        self.assertEqual(out["changes"]["rulesets"][-1]["status"], "active")
        self.assertEqual(out["events"][0][0], "policy.publish")
        self.assertEqual(rulesets, [])  # đầu vào không bị đổi

    def test_dry_run_changes_nothing(self):
        out = ingest(self.v1, "v1", [], dry_run=True)
        self.assertTrue(out["result"]["dry_run"])
        self.assertEqual(out["changes"], {})
        self.assertEqual(out["events"], [])

    def test_impact_comes_from_injected_function(self):
        calls = []

        def fake_impact(old, new):
            calls.append((len(old), len(new)))
            return {"bs_a": {"before": 0, "after": len(new)}}

        out = ingest(self.v1, "v1", [], impact_fn=fake_impact)
        self.assertEqual(calls, [(0, out["result"]["applied_count"])])
        self.assertEqual(out["result"]["impact"], {"bs_a": {"before": 0, "after": out["result"]["applied_count"]}})

    def test_v2_supersedes_v1_and_rollback_restores_it(self):
        rulesets = ingest(self.v1, "v1", [])["changes"]["rulesets"]
        v2 = ingest(self.v2, "v2", rulesets)
        self.assertEqual(v2["result"]["published_version"], "v2")
        self.assertEqual(v2["result"]["summary"]["needs_clarification"], 1)
        new_rulesets = v2["changes"]["rulesets"]
        self.assertEqual([r["status"] for r in new_rulesets], ["superseded", "active"])

        back = policy.rollback(new_rulesets)
        self.assertEqual(back["result"]["active"], "v1")
        self.assertEqual(back["changes"]["rulesets"][0]["status"], "active")
        self.assertEqual(back["changes"]["rulesets"][1]["status"], "rolled_back")

    def test_rollback_without_previous_version_changes_nothing(self):
        out = policy.rollback(ingest(self.v1, "v1", [])["changes"]["rulesets"])
        self.assertFalse(out["result"]["ok"])
        self.assertEqual(out["changes"], {})

    def test_text_without_clauses_is_rejected(self):
        out = ingest("Văn bản không có khoản nào", "v1", [])
        self.assertFalse(out["result"]["ok"])
        self.assertEqual(out["changes"], {})


if __name__ == "__main__":
    unittest.main(verbosity=2)
