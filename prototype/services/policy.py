"""Module 2 – Policy engine.

Văn bản quy định -> cắt theo khoản (x.y) -> bóc luật (ở prototype: bộ phân tích theo mẫu câu,
thay cho LLM có structured output) -> kiểm tra 6 lớp (code thường) -> so khác biệt, chạy thử
tác động -> tự động phát hành phiên bản bất biến (có hoàn tác).

Luật không qua kiểm tra không được áp dụng: `rejected` (lỗi) và `needs_clarification` (mơ hồ / cờ).
"""
import copy
import difflib
import json
import re
from datetime import timedelta

from . import reminder, store
from .common import norm, parse_duration

ROLE_PHRASES = {"bác sĩ": "bac_si", "điều dưỡng": "dieu_duong"}
ROLES = {"bac_si", "dieu_duong"}
SCHEDULE_TYPES = {"once_within", "once_after", "recurring", "sequence", "daily_before", "min_per_period", "on_event"}
EVENT_CATALOG = {"admission", "discharge", "surgery_end", "medication_given"}
AMBIGUOUS = re.compile(r"khoảng|hoặc|tối đa", re.IGNORECASE)
HEAD_STOP = re.compile(
    r"\s(?=trong vòng|trong ngày|sau \d+ phút|mỗi \d+ giờ|theo lịch|trước \d|tối thiểu|khi bệnh nhân|khoảng)"
)
CLAUSE_RE = re.compile(r"^(\d+\.\d+)\s+(.+)$")
WATCH_FIELDS = ("form_id", "role", "trigger", "schedule", "required_fields")

# Mẫu câu -> (type, tham số, sự kiện kích hoạt, điều kiện 'where')
SCHEDULE_PATTERNS = [
    (r"trong vòng (\d+) giờ kể từ khi bệnh nhân vào viện",
     lambda m: ("once_within", {"within": f"PT{m[1]}H"}, "admission", None)),
    (r"trong ngày kể từ khi bệnh nhân vào viện",
     lambda m: ("once_within", {"within": "end_of_day"}, "admission", None)),
    (r"trong ngày khi bệnh nhân ra viện",
     lambda m: ("once_within", {"within": "end_of_day"}, "discharge", None)),
    (r"sau (\d+) phút khi dùng thuốc tiêm, truyền giảm đau",
     lambda m: ("once_after", {"offset": f"PT{m[1]}M"}, "medication_given",
                {"route": ["tiem", "truyen"], "purpose": "giam_dau"})),
    (r"mỗi (\d+) giờ một lần, tính từ lần nhập gần nhất",
     lambda m: ("recurring", {"every": f"PT{m[1]}H", "anchor": "last_entry"}, "admission", None)),
    (r"theo lịch: ([\d, ]+) giờ, tính từ lúc kết thúc phẫu thuật",
     lambda m: ("sequence", {"intervals": [int(x) for x in re.findall(r"\d+", m[1])], "unit": "hour",
                             "anchor": "surgery_end"}, "surgery_end", None)),
    (r"trước (\d{2}:\d{2}) mỗi ngày",
     lambda m: ("daily_before", {"time": m[1]}, "admission", None)),
    (r"tối thiểu (\d+) lần mỗi ngày",
     lambda m: ("min_per_period", {"count": int(m[1]), "period": "P1D"}, "admission", None)),
    (r"khi bệnh nhân ra viện",
     lambda m: ("on_event", {"events": ["discharge"]}, "discharge", None)),
]


def split_clauses(text):
    out = []
    for raw in text.splitlines():
        m = CLAUSE_RE.match(raw.strip())
        if m:
            out.append((m.group(1), m.group(2)))
    return out


def build_rule(doc_id, doc_version, effective_from, clause_id, body, forms):
    main, _, req_part = body.partition("Trường bắt buộc:")
    sentence = main.strip()
    roles = [r for p, r in ROLE_PHRASES.items() if p in norm(sentence)]
    head_m = HEAD_STOP.search(sentence)
    head = norm(sentence[:head_m.start()] if head_m else sentence)

    form_id, best = None, 0
    for fid, f in forms.items():
        for alias in f.get("aliases", []):
            a = norm(alias)
            if a and a in head and len(a) > best:
                form_id, best = fid, len(a)

    stype, params, event, where = None, {}, None, None
    for pattern, build in SCHEDULE_PATTERNS:
        m = re.search(pattern, sentence, re.IGNORECASE)
        if m:
            stype, params, event, where = build(m)
            break

    pre_flags = []
    if stype is None and AMBIGUOUS.search(sentence):
        pre_flags.append("diễn đạt mơ hồ (khoảng/hoặc/tối đa): cần làm rõ, không đoán lịch")

    req_labels = [x.strip() for x in req_part.strip().rstrip(".").split(",") if x.strip()]
    lookup = {norm(f["label"]): f["field_id"] for f in forms[form_id]["fields"]} if form_id else {}
    required = [lookup.get(norm(x), x) for x in req_labels]

    trigger = None
    if event:
        trigger = {"event": event}
        if where:
            trigger["where"] = where
    rule = {
        "rule_id": f"{doc_id}:{clause_id}",
        "source": {"doc_id": doc_id, "doc_version": doc_version, "clause": f"Điều {clause_id}", "evidence": sentence},
        "form_id": form_id,
        "role": roles,
        "trigger": trigger,
        "condition": None,
        "schedule": {"type": stype, **params} if stype else None,
        "required_fields": required,
        "priority": "normal",
        "effective_from": effective_from,
        "effective_to": None,
        "supersedes": [],
        "status": "active",
    }
    return rule, body, pre_flags


def _check(rule, clause_body, pre_flags, forms):
    """Kiểm tra lớp 1–5 cho một luật. Trả về (lỗi, cờ)."""
    errors, flags = [], list(pre_flags)
    sched = rule.get("schedule")
    ev = rule["source"]["evidence"]

    # Lớp 1 – đúng khuôn
    need = ["rule_id", "source", "form_id", "role", "trigger", "schedule", "required_fields", "effective_from", "status"]
    if pre_flags:
        need = [k for k in need if k not in ("schedule", "trigger")]
    missing = [k for k in need if rule.get(k) in (None, "", [])]
    if missing:
        errors.append(f"L1: thiếu khóa {', '.join(missing)}")
    if sched is not None and sched.get("type") not in SCHEDULE_TYPES:
        errors.append("L1: schedule.type không hợp lệ")
    if rule.get("role") and not set(rule["role"]) <= ROLES:
        errors.append("L1: role không hợp lệ")

    # Lớp 2 – tham chiếu có thật
    form = forms.get(rule.get("form_id") or "")
    if rule.get("form_id") and (not form or form.get("status") != "active"):
        errors.append("L2: form_id không có trong registry hoặc không active")
    elif form:
        ids = {f["field_id"] for f in form["fields"]}
        bad = [x for x in rule.get("required_fields", []) if x not in ids]
        if bad:
            errors.append(f"L2: trường bắt buộc không có trong form: {', '.join(bad)}")
    if rule.get("trigger") and rule["trigger"].get("event") not in EVENT_CATALOG:
        errors.append("L2: trigger.event ngoài danh mục sự kiện")

    # Lớp 3 – câu trích nguyên văn (chuẩn hóa rồi so khớp với đúng khoản)
    a, b = norm(ev), norm(clause_body)
    if a:
        match = difflib.SequenceMatcher(None, a, b, autojunk=False).find_longest_match(0, len(a), 0, len(b))
        ratio = match.size / len(a)
        if ratio < 0.95:
            errors.append(f"L3: trích dẫn không nằm trong khoản ({ratio:.0%} khớp)")
        elif ratio < 1.0:
            flags.append(f"L3: trích dẫn gần đúng ({ratio:.0%}), cần xem lại")

    # Lớp 4 – con số trong luật phải có trong trích dẫn
    if sched:
        nums = []
        for k in ("within", "offset", "every", "time"):
            if isinstance(sched.get(k), str):
                nums += re.findall(r"\d+", sched[k])
        nums += [str(x) for x in sched.get("intervals", [])]
        if "count" in sched:
            nums.append(str(sched["count"]))
        ev_nums = set(re.findall(r"\d+", ev))
        bad_nums = [n for n in nums if n not in ev_nums]
        if bad_nums:
            errors.append(f"L4: số {', '.join(bad_nums)} không có trong trích dẫn")

        # Lớp 5 – hợp lý
        for k in ("within", "offset", "every"):
            v = sched.get(k)
            if isinstance(v, str) and v != "end_of_day":
                d = parse_duration(v)
                if d is None:
                    errors.append(f"L5: thời lượng không hợp lệ: {v}")
                elif not (timedelta(minutes=5) <= d <= timedelta(days=30)):
                    errors.append(f"L5: thời lượng ngoài khoảng 5 phút – 30 ngày: {v}")
        if sched.get("type") == "sequence" and (not sched.get("intervals") or min(sched["intervals"]) <= 0):
            errors.append("L5: chuỗi lịch rỗng hoặc có giá trị <= 0")
        if sched.get("type") == "min_per_period" and sched.get("count", 0) <= 0:
            errors.append("L5: số lần tối thiểu phải > 0")
    if rule.get("effective_to") and rule["effective_to"] < rule["effective_from"]:
        errors.append("L5: effective_from > effective_to")
    return errors, flags


def _key(r):
    if not r.get("form_id") or not r.get("trigger"):
        return None
    return (r["form_id"], tuple(sorted(r.get("role") or [])), r["trigger"]["event"])


def _sig(r):
    return json.dumps(r.get("schedule"), sort_keys=True, ensure_ascii=False)


def _resolve_within_doc(rules):
    """Lớp 6 (trong cùng văn bản): trùng thì gộp; xung đột lịch thì cần làm rõ."""
    groups = {}
    for r in rules:
        k = _key(r)
        if r["status"] == "active" and k:
            groups.setdefault(k, []).append(r)
    for items in groups.values():
        if len(items) < 2:
            continue
        if len({_sig(i) for i in items}) == 1:
            keep = items[0]
            for dup in items[1:]:
                dup["status"] = "merged"
                dup["validation"]["flags"].append(f"L6: trùng với {keep['rule_id']}, đã gộp")
        else:
            for it in items:
                it["status"] = "needs_clarification"
                it["validation"]["flags"].append("L6: xung đột lịch với luật cùng form/vai trò/sự kiện")


def _resolve_cross_doc(new_rules, other):
    """Lớp 6 (với bộ luật đang áp dụng từ văn bản khác): luật mới thay thế luật cũ cùng khóa."""
    for o in other:
        k = _key(o)
        for r in new_rules:
            if r["status"] == "active" and k and _key(r) == k:
                if _sig(r) == _sig(o):
                    o["status"] = "merged"
                else:
                    o["status"] = "superseded"
                    r["supersedes"].append(o["rule_id"])


def _diff(old, new):
    om = {r["rule_id"]: r for r in old}
    nm = {r["rule_id"]: r for r in new}
    added = [{"rule_id": k, "clause": n["source"]["clause"], "evidence": n["source"]["evidence"]}
             for k, n in nm.items() if k not in om]
    removed = [{"rule_id": k, "clause": o["source"]["clause"], "evidence": o["source"]["evidence"]}
               for k, o in om.items() if k not in nm]
    changed = []
    for k, n in nm.items():
        if k not in om:
            continue
        o = om[k]
        fields = [f for f in WATCH_FIELDS if o.get(f) != n.get(f)]
        if fields or o["source"]["evidence"] != n["source"]["evidence"]:
            changed.append({"rule_id": k, "clause": n["source"]["clause"], "evidence": n["source"]["evidence"],
                            "before": o.get("schedule"), "after": n.get("schedule"), "changed_fields": fields})
    return {"added": added, "changed": changed, "removed": removed}


def _impact(st, old, new):
    now = store.now(st)
    users = sorted({p.get("doctor") for p in st["patients"] if p.get("doctor")} |
                   {p.get("nurse") for p in st["patients"] if p.get("nurse")})
    return {u: {"before": len(reminder.compute_tasks(st, u, old, now)),
                "after": len(reminder.compute_tasks(st, u, new, now))} for u in users}


def _applied(st):
    v = reminder.active_ruleset(st)
    return v["rules"] if v else []


def ingest(st, doc_id, doc_version, text, effective_from, dry_run=False):
    clauses = split_clauses(text)
    if not clauses:
        return {"ok": False, "error": "Không tìm thấy khoản nào. Mỗi khoản cần dạng '1.1 Nội dung...'."}
    forms = st["forms"]
    checked = []
    for cid, body in clauses:
        rule, clause_body, pre_flags = build_rule(doc_id, doc_version, effective_from, cid, body, forms)
        errors, flags = _check(rule, clause_body, pre_flags, forms)
        rule["validation"] = {"errors": errors, "flags": flags}
        rule["status"] = "rejected" if errors else ("needs_clarification" if flags else "active")
        checked.append(rule)
    _resolve_within_doc(checked)

    current = copy.deepcopy(_applied(st))
    other = [r for r in current if r["source"]["doc_id"] != doc_id]
    _resolve_cross_doc(checked, other)
    if not any(r["status"] == "active" for r in checked):
        return {"ok": False, "error": "Không có khoản nào của văn bản này qua kiểm tra.", "checked": checked}
    applied = [r for r in checked if r["status"] == "active"] + [r for r in other if r["status"] == "active"]

    diff = _diff(current, applied)
    impact = _impact(st, current, applied)
    summary = {s: sum(1 for r in checked if r["status"] == s)
               for s in ("active", "needs_clarification", "rejected", "merged")}
    result = {
        "ok": True, "dry_run": dry_run, "doc_id": doc_id, "doc_version": doc_version,
        "effective_from": effective_from, "summary": summary, "checked": checked,
        "diff": diff, "impact": impact, "applied_count": len(applied),
    }
    if dry_run:
        return result

    version = f"v{len(st['rulesets']) + 1}"
    for v in st["rulesets"]:
        if v["status"] == "active":
            v["status"] = "superseded"
    st["rulesets"].append({
        "version": version, "status": "active", "effective_from": effective_from,
        "published_at": st["clock"], "source": {"doc_id": doc_id, "doc_version": doc_version},
        "rules": applied, "checked": checked, "summary": summary, "diff": diff, "impact": impact,
    })
    st["docs"][f"{doc_id}@{doc_version}"] = {"uploaded_at": st["clock"], "text": text}
    store.audit(st, "policy.publish",
                f"{version} từ {doc_id} {doc_version}: +{len(diff['added'])} ~{len(diff['changed'])} "
                f"-{len(diff['removed'])}; áp dụng {len(applied)} luật, cần làm rõ {summary['needs_clarification']}, "
                f"từ chối {summary['rejected']}")
    result["published_version"] = version
    return result


def rollback(st):
    idx = next((i for i, v in enumerate(st["rulesets"]) if v["status"] == "active"), None)
    if idx is None or idx == 0:
        return {"ok": False, "error": "Không có phiên bản trước để hoàn tác."}
    cur, prev = st["rulesets"][idx], st["rulesets"][idx - 1]
    cur["status"] = "rolled_back"
    prev["status"] = "active"
    store.audit(st, "policy.rollback", f"hoàn tác {cur['version']} về {prev['version']}")
    return {"ok": True, "active": prev["version"]}
