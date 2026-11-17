"""Server prototype (thư viện chuẩn Python, không cần cài thêm).

Chạy:  python server.py            -> http://127.0.0.1:8765
Đọc:   data/ (seed), web/ (giao diện); ghi: .runtime/state.json (trạng thái demo).
"""
import datetime as dt
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))

from services import form_detection, policy, reminder, store, voice  # noqa: E402

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
REG_DIR = store.DATA_DIR / "regulations"
DOC_ID = "QD-CHAMSOC-2026"


def ensure_seeded():
    with store.transaction() as st:
        if not st["rulesets"]:
            text = (REG_DIR / "qd_chamsoc_v1.txt").read_text(encoding="utf-8")
            res = policy.ingest(st, DOC_ID, "v1", text, "2026-11-10")
            if not res.get("ok"):
                raise RuntimeError(f"Không nạp được bộ luật v1: {res.get('error')}")


# ---------- GET ----------

def _ruleset_list(st):
    return [{"version": v["version"], "status": v["status"], "effective_from": v["effective_from"],
             "published_at": v["published_at"], "applied": len(v["rules"]), "summary": v["summary"],
             "source": v["source"]} for v in st["rulesets"]]


def g_state(q):
    st = store.read()
    v = reminder.active_ruleset(st)
    return {
        "clock": st["clock"],
        "active_ruleset": v["version"] if v else None,
        "effective_from": v["effective_from"] if v else None,
        "active_forms": sum(1 for f in st["forms"].values() if f["status"] == "active"),
        "rulesets": _ruleset_list(st),
    }


def g_forms(q):
    st = store.read()
    return {"forms": [{k: f[k] for k in ("form_id", "title", "status", "version", "fields")}
                      | {"history_len": len(f["history"])} for f in st["forms"].values()]}


def g_users(q):
    return {"users": store.read()["users"]}


def _active_rules(st):
    v = reminder.active_ruleset(st)
    return v["rules"] if v else []


def g_patients(q):
    st = store.read()
    rules, now = _active_rules(st), store.now(st)
    out = []
    for p in st["patients"]:
        tasks = reminder.patient_tasks(st, p, rules, now)
        out.append({
            "patient_id": p["patient_id"], "name": p["name"], "bed": p["bed"], "doctor": p["doctor"],
            "nurse": p["nurse"], "open": len(tasks), "overdue": sum(1 for t in tasks if t["status"] == "quá hạn"),
        })
    return {"patients": out, "clock": st["clock"]}


def g_patient(q):
    pid = q.get("id", [""])[0]
    st = store.read()
    p = next((x for x in st["patients"] if x["patient_id"] == pid), None)
    if not p:
        raise ValueError("không tìm thấy bệnh nhân")
    now = store.now(st)
    rules = _active_rules(st)
    tasks = reminder.patient_tasks(st, p, rules, now)
    forms = {}
    for r in rules:
        if not any((role == "bac_si" and p.get("doctor")) or (role == "dieu_duong" and p.get("nurse"))
                   for role in r.get("role", [])):
            continue
        f = forms.setdefault(r["form_id"], {
            "form_id": r["form_id"], "title": st["forms"].get(r["form_id"], {}).get("title", r["form_id"]),
            "fields": st["forms"].get(r["form_id"], {}).get("fields", []), "rules": [], "required": [],
            "roles": [], "tasks": [], "records": [],
        })
        f["rules"].append({"rule_id": r["rule_id"], "clause": r["source"]["clause"],
                           "evidence": r["source"]["evidence"], "schedule": r["schedule"]["type"]})
        f["required"] = sorted(set(f["required"]) | set(r.get("required_fields", [])))
        f["roles"] = sorted(set(f["roles"]) | set(r.get("role", [])))
    for t in tasks:
        if t["form_id"] in forms:
            forms[t["form_id"]]["tasks"].append(t)
    for rec in st["records"]:
        if rec["patient_id"] == pid and rec["form_id"] in forms:
            forms[rec["form_id"]]["records"].append(rec)
    for f in forms.values():
        f["records"].sort(key=lambda r: r["at"], reverse=True)
    return {"patient": {k: p[k] for k in ("patient_id", "name", "bed", "doctor", "nurse", "events")},
            "clock": st["clock"], "ruleset_version": (reminder.active_ruleset(st) or {}).get("version"),
            "forms": list(forms.values())}


def g_rules(q):
    st = store.read()
    v = reminder.active_ruleset(st)
    rows = []
    for r in (v["rules"] if v else []):
        rows.append({"rule_id": r["rule_id"], "clause": r["source"]["clause"], "evidence": r["source"]["evidence"],
                     "form_id": r["form_id"], "form_title": st["forms"].get(r["form_id"], {}).get("title", r["form_id"]),
                     "role": r["role"], "schedule": r["schedule"]["type"]})
    return {"rules": rows, "version": v["version"] if v else None}


def g_tasks(q):
    return reminder.summary(store.read(), q.get("user", ["bs_a"])[0])


def g_rulesets(q):
    return {"rulesets": _ruleset_list(store.read())}


def g_samples(q):
    out = []
    for name, label in (("qd_chamsoc_v1.txt", "QĐ chăm sóc – v1"),
                        ("qd_chamsoc_v2.txt", "QĐ chăm sóc – v2 (có thay đổi)")):
        out.append({"name": name, "label": label, "text": (REG_DIR / name).read_text(encoding="utf-8")})
    return {"samples": out}


def g_audit(q):
    return {"audit": list(reversed(store.read()["audit"]))[:300]}


GET_ROUTES = {
    "/api/state": g_state, "/api/forms": g_forms, "/api/users": g_users, "/api/patients": g_patients,
    "/api/patient": g_patient, "/api/rules": g_rules,
    "/api/tasks": g_tasks, "/api/rulesets": g_rulesets, "/api/samples": g_samples, "/api/audit": g_audit,
}


# ---------- POST ----------

def p_detect(body):
    with store.transaction() as st:
        return form_detection.detect(st, body)


def p_form_rollback(body):
    with store.transaction() as st:
        return form_detection.rollback_form(st, body["form_id"])


def p_records(body):
    with store.transaction() as st:
        pid, fid = body.get("patient_id"), body.get("form_id")
        if not any(p["patient_id"] == pid for p in st["patients"]):
            raise ValueError("không tìm thấy bệnh nhân")
        form = st["forms"].get(fid)
        if not form:
            raise ValueError("không tìm thấy form")
        field_ids = {f["field_id"] for f in form["fields"]}
        values = {k: v for k, v in (body.get("values") or {}).items()
                  if k in field_ids and v not in (None, "")}
        required = [f["field_id"] for f in form["fields"] if f.get("required")]
        missing = reminder.missing_fields(values, required)
        rec = {"record_id": f"REC-{len(st['records']) + 1:04d}", "patient_id": pid, "form_id": fid,
               "at": st["clock"], "values": values, "user": body.get("user"),
               "source": body.get("source", "emr"), "missing_required": missing}
        st["records"].append(rec)
        store.audit(st, "record.save", f"{rec['record_id']} {fid} cho {pid} (nguồn {rec['source']}); "
                                       f"thiếu: {', '.join(missing) or 'không'}")
        return {"ok": True, "record": rec}


def p_ingest(body):
    with store.transaction() as st:
        effective = body.get("effective_from") or st["clock"][:10]
        return policy.ingest(st, body.get("doc_id", DOC_ID), body["doc_version"], body["text"],
                             effective, dry_run=bool(body.get("dry_run")))


def p_rollback(body):
    with store.transaction() as st:
        return policy.rollback(st)


def p_voice(body):
    st = store.read()
    form = st["forms"].get(body.get("form_id"))
    if not form:
        raise ValueError("không tìm thấy form")
    return {"ok": True, **voice.process(body.get("text", ""), form)}


def p_clock(body):
    with store.transaction() as st:
        if "minutes" in body:
            value = (store.now(st) + dt.timedelta(minutes=int(body["minutes"]))).isoformat()
        else:
            value = body.get("now", "")
            dt.datetime.fromisoformat(value)  # ném lỗi nếu sai định dạng
        st["clock"] = value
        store.audit(st, "clock", f"đặt giờ hệ thống: {value}")
        return {"ok": True, "clock": value}


def p_reset(body):
    store.reset()
    ensure_seeded()
    return {"ok": True}


POST_ROUTES = {
    "/api/detect": p_detect, "/api/forms/rollback": p_form_rollback, "/api/records": p_records,
    "/api/policy/ingest": p_ingest, "/api/policy/rollback": p_rollback, "/api/voice": p_voice,
    "/api/clock": p_clock, "/api/reset": p_reset,
}

CTYPES = {".html": "text/html; charset=utf-8", ".js": "application/javascript; charset=utf-8",
          ".css": "text/css; charset=utf-8", ".json": "application/json; charset=utf-8"}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # giữ console gọn
        pass

    def _send(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code, obj):
        self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def _run(self, fn, *args):
        try:
            res = fn(*args)
            self._json(200 if res.get("ok", True) else 400, res)
        except (ValueError, KeyError) as e:
            self._json(400, {"ok": False, "error": f"Dữ liệu không hợp lệ: {e}"})
        except Exception as e:  # prototype: trả lỗi để dễ debug
            self._json(500, {"ok": False, "error": str(e)})

    def do_GET(self):
        url = urlparse(self.path)
        if url.path.startswith("/api/"):
            fn = GET_ROUTES.get(url.path)
            if not fn:
                return self._json(404, {"ok": False, "error": "không có API này"})
            return self._run(fn, parse_qs(url.query))
        rel = "index.html" if url.path in ("", "/") else url.path.lstrip("/")
        path = (WEB / rel).resolve()
        if WEB.resolve() not in path.parents or not path.is_file():
            return self._send(404, b"not found", "text/plain; charset=utf-8")
        self._send(200, path.read_bytes(), CTYPES.get(path.suffix, "application/octet-stream"))

    def do_POST(self):
        url = urlparse(self.path)
        fn = POST_ROUTES.get(url.path)
        if not fn:
            return self._json(404, {"ok": False, "error": "không có API này"})
        length = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(length) or b"{}")  # UnicodeDecodeError cũng là ValueError
        except ValueError:
            return self._json(400, {"ok": False, "error": "JSON không hợp lệ (cần UTF-8)"})
        self._run(fn, body)


def main():
    ensure_seeded()
    port = int(os.environ.get("PORT", "8765"))
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Prototype chạy tại http://127.0.0.1:{port}  (Ctrl+C để dừng)")
    srv.serve_forever()


if __name__ == "__main__":
    main()
