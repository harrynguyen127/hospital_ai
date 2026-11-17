"""Lõi nối: áp kết quả thuần của các tính năng vào state, và là ĐIỂM NỐI TÍCH HỢP DUY NHẤT.

- Tính năng là hàm thuần (xem contracts/CONTRACTS.md). Lõi lấy hàm qua registry.get(slot),
  gọi, rồi áp `changes` vào state và ghi `events` vào nhật ký.
- Tích hợp bản thật: thêm registry.connect(slot, impl) vào mục CONNECTIONS bên dưới.
  Không có dòng nào thì hệ thống dùng bản mặc định (hardcode prototype).
"""
from contracts import registry
from features.detect_form import form_detection  # noqa: F401  (đăng ký mặc định)
from features.pii_filter import pii  # noqa: F401
from features.policy_rules import policy  # noqa: F401
from features.voice_input import external_api, voice  # noqa: F401
from services import reminder, store

# ---------------- CONNECTIONS: nối bản thật của từng tính năng tại đây ----------------
# Ví dụ (khi có bản thật):
#   from features.pii_filter.ner_pii import mask as ner_mask
#   registry.connect("pii.mask", ner_mask)
# -------------------------------------------------------------------------------------


def _impact(st, old, new):
    """Tác động theo người dùng: số việc trước/sau khi đổi bộ luật. Phụ thuộc reminder nên nằm ở lõi."""
    now = store.now(st)
    users = sorted({p.get("doctor") for p in st["patients"] if p.get("doctor")} |
                   {p.get("nurse") for p in st["patients"] if p.get("nurse")})
    return {u: {"before": len(reminder.compute_tasks(st, u, old, now)),
                "after": len(reminder.compute_tasks(st, u, new, now))} for u in users}


def _apply(st, out):
    for key, value in out["changes"].items():
        st[key] = value
    for kind, detail in out["events"]:
        store.audit(st, kind, detail)
    return out["result"]


def detect(st, payload):
    return _apply(st, registry.get("form.detect")(st["forms"], payload))


def rollback_form(st, form_id):
    return _apply(st, registry.get("form.rollback")(st["forms"], form_id))


def ingest(st, doc_id, doc_version, text, effective_from, dry_run=False):
    return _apply(st, registry.get("policy.ingest")(
        text, doc_id, doc_version, effective_from,
        rulesets=st["rulesets"], forms=st["forms"], docs=st["docs"], clock=st["clock"],
        dry_run=dry_run, impact_fn=lambda old, new: _impact(st, old, new)))


def rollback_policy(st):
    return _apply(st, registry.get("policy.rollback")(st["rulesets"]))


def voice_process(text, form):
    return voice.process(text, form, mask_fn=registry.get("pii.mask"))
