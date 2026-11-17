"""Nhắc việc (reminder engine) – tất định, không gọi LLM.

Áp 7 kiểu lịch (schedule) lên bệnh nhân × sự kiện × bản ghi đã nhập để ra danh sách việc
còn mở, theo vai trò của người dùng. Luôn đọc bộ luật đang hiệu lực.
"""
from datetime import datetime, timedelta, time as dtime

from . import store
from shared.common import parse_duration


def active_ruleset(st):
    return next((v for v in st["rulesets"] if v["status"] == "active"), None)


def user_patients(st, user):
    out = []
    for p in st["patients"]:
        if p.get("doctor") == user:
            out.append((p, "bac_si"))
        if p.get("nurse") == user:
            out.append((p, "dieu_duong"))
    return out


def missing_fields(values, required):
    vals = values or {}
    out = []
    for f in required:
        v = vals.get(f)
        if v is None or (isinstance(v, str) and not v.strip()):
            out.append(f)
    return out


def _parse(s):
    return datetime.fromisoformat(s)


def _where_ok(ev, where):
    for k, v in (where or {}).items():
        val = ev.get(k)
        ok = (val in v) if isinstance(v, list) else (val == v)
        if not ok:
            return False
    return True


def _events(patient, rule):
    t = rule["trigger"]
    evs = [e for e in patient.get("events", []) if e["event"] == t["event"] and _where_ok(e, t.get("where"))]
    return sorted(evs, key=lambda e: _parse(e["at"]))


def _hhmm(s):
    h, m = map(int, s.split(":"))
    return dtime(h, m)


def _rule_tasks(st, p, rule, now):
    s = rule["schedule"]
    kind = s["type"]
    fid = rule["form_id"]
    req = rule.get("required_fields", [])
    title = st["forms"].get(fid, {}).get("title", fid)
    recs = [r for r in st["records"] if r["patient_id"] == p["patient_id"] and r["form_id"] == fid]
    out = []

    def since(t):
        return [r for r in recs if _parse(r["at"]) >= t]

    def complete(r):
        return not missing_fields(r["values"], req)

    def latest(rs):
        return max(rs, key=lambda r: _parse(r["at"])) if rs else None

    def add(key, status, due, missing, note=""):
        out.append({
            "task_id": f"{rule['rule_id']}|{p['patient_id']}|{key}",
            "patient_id": p["patient_id"], "patient": p.get("name", p["patient_id"]), "bed": p.get("bed"),
            "rule_id": rule["rule_id"], "clause": rule["source"]["clause"], "form_id": fid, "form_title": title,
            "kind": kind, "status": status, "due": due.isoformat() if due else None,
            "missing_fields": missing, "note": note,
        })

    evs = _events(p, rule)
    if kind in ("once_within", "once_after"):
        for ev in evs:
            start = _parse(ev["at"])
            if kind == "once_after":
                due = start + parse_duration(s["offset"])
            elif s["within"] == "end_of_day":
                due = datetime.combine(start.date(), dtime(23, 59), tzinfo=start.tzinfo)
            else:
                due = start + parse_duration(s["within"])
            after = since(start)
            if any(complete(r) for r in after):
                continue
            last = latest(after)
            add(ev["at"], "quá hạn" if now > due else "đang chờ", due,
                missing_fields(last["values"], req) if last else list(req))
    elif kind == "on_event":
        for ev in evs:
            start = _parse(ev["at"])
            after = since(start)
            if any(complete(r) for r in after):
                continue
            last = latest(after)
            add(ev["at"], "đang chờ", None, missing_fields(last["values"], req) if last else list(req), "theo sự kiện")
    elif kind == "recurring":
        if evs:
            start = _parse(evs[-1]["at"])
            after = since(start)
            base = _parse(latest(after)["at"]) if after else start
            due = base + parse_duration(s["every"])
            add("stream", "quá hạn" if now > due else "đang chờ", due, [], f"lặp mỗi {s['every']}")
    elif kind == "sequence":
        if evs:
            start = _parse(evs[-1]["at"])
            done = sum(1 for r in since(start) if complete(r))
            ints = s["intervals"]
            if done < len(ints):
                due = start + timedelta(hours=sum(ints[:done + 1]))
                add(f"step{done + 1}", "quá hạn" if now > due else "đang chờ", due, [],
                    f"lần {done + 1}/{len(ints)}")
    elif kind == "daily_before":
        if evs:
            limit = datetime.combine(now.date(), _hhmm(s["time"]), tzinfo=now.tzinfo)
            today = [r for r in recs if _parse(r["at"]).date() == now.date()]
            if not any(complete(r) for r in today):
                last = latest(today)
                add(now.date().isoformat(), "quá hạn" if now > limit else "đang chờ", limit,
                    missing_fields(last["values"], req) if last else list(req), f"trước {s['time']}")
    elif kind == "min_per_period":
        if evs:
            n = s["count"]
            done = [r for r in recs if _parse(r["at"]).date() == now.date() and complete(r)]
            if len(done) < n:
                due = datetime.combine(now.date(), dtime(23, 59), tzinfo=now.tzinfo)
                add(now.date().isoformat(), "đang chờ", due, [], f"{len(done)}/{n} lần hôm nay")
    return out


def compute_tasks(st, user, rules, now):
    tasks = []
    for p, role in user_patients(st, user):
        for rule in rules:
            if role in rule.get("role", []):
                tasks.extend(_rule_tasks(st, p, rule, now))
    return tasks


def patient_tasks(st, p, rules, now):
    """Việc còn mở của một bệnh nhân, theo cả bác sĩ và điều dưỡng phụ trách."""
    roles = {"bac_si": bool(p.get("doctor")), "dieu_duong": bool(p.get("nurse"))}
    out = []
    for rule in rules:
        role = next((r for r in rule.get("role", []) if roles.get(r)), None)
        if role:
            for t in _rule_tasks(st, p, rule, now):
                t["role"] = role
                out.append(t)
    return out


def summary(st, user):
    v = active_ruleset(st)
    now = store.now(st)
    tasks = compute_tasks(st, user, v["rules"] if v else [], now)
    tasks.sort(key=lambda t: (t["due"] or "9999", t["patient_id"]))
    return {
        "user": user,
        "ruleset_version": v["version"] if v else None,
        "effective_from": v["effective_from"] if v else None,
        "count": len(tasks),
        "overdue": sum(1 for t in tasks if t["status"] == "quá hạn"),
        "tasks": tasks,
    }
