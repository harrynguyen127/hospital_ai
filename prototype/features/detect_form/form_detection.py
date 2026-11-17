"""Module 1 – Detect form.

Tầng 1 (DOM, do web/app.js gửi lên) -> so khớp chính xác bằng fingerprint -> so khớp gần đúng
bằng Jaccard trên tập nhãn -> form mới: sinh schema nháp (stub, chưa gọi VLM) -> kiểm tra tự động
-> áp dụng ngay nếu qua kiểm tra (có nhật ký, hoàn tác được).
"""
import copy

from contracts import registry
from shared.common import fingerprint, jaccard, label_keys, norm, slugify

NEAR_THRESHOLD = 0.8
UI_TO_TYPE = {"number": "number", "text": "string", "datetime": "datetime", "checkbox": "boolean", "select": "enum"}
FIELD_TYPES = set(UI_TO_TYPE.values())


def _new_field(item, used):
    base = slugify(item["label"]) or "truong"
    fid, i = base, 2
    while fid in used:
        fid, i = f"{base}_{i}", i + 1
    used.add(fid)
    field = {
        "field_id": fid, "label": item["label"], "type": UI_TO_TYPE.get(item.get("ui"), "string"),
        "ui": item.get("ui", "text"), "required": bool(item.get("required")), "data_level": 2,
    }
    if field["ui"] == "select":
        field["options"] = item.get("options") or ["Có", "Không"]
    return field


def check_schema(form):
    """Kiểm tra tự động schema form (không gọi model)."""
    errs = []
    fields = form.get("fields") or []
    if not fields:
        errs.append("form không có trường nào")
    ids = [f["field_id"] for f in fields]
    if len(ids) != len(set(ids)):
        errs.append("field_id bị trùng")
    for f in fields:
        if f.get("type") not in FIELD_TYPES:
            errs.append(f"kiểu không hợp lệ: {f.get('type')}")
        if f.get("data_level") not in (1, 2, 3):
            errs.append(f"data_level không hợp lệ: {f.get('field_id')}")
    return errs


def _field_map(items, form_fields):
    lookup = {norm(f["label"]): f["field_id"] for f in form_fields}
    return [{"label": x["label"], "field_id": lookup.get(norm(x["label"]))} for x in items]


def _result(items, fp, match, action, fid, form):
    return {
        "ok": True, "match": match, "action": action, "form_id": fid, "title": form["title"],
        "version": form["version"], "status": form["status"], "fingerprint": fp,
        "field_map": _field_map(items, form["fields"]),
    }


def _out(result, changes=None, events=None):
    """Kết quả chuẩn: result (trả cho API), changes (khóa state cần thay), events (nhật ký)."""
    return {"result": result, "changes": changes or {}, "events": events or []}


def _run(forms, payload, events):
    """Lõi phát hiện: làm việc TRÊN `forms` (bản sao) và ghi nhật ký vào `events`."""
    title = (payload.get("title") or "").strip() or "Biểu mẫu không tên"
    items = [f for f in payload.get("fields", []) if f.get("label")]
    if not items:
        return {"ok": False, "error": "Không đọc được trường nào trên màn hình."}
    fp = fingerprint(title, items)
    active ={k: v for k, v in forms.items() if v["status"] == "active"}

    # Khớp chính xác (fingerprint)
    for fid, form in active.items():
        if form["fingerprint"] == fp:
            return _result(items, fp, "exact", "không cần làm gì", fid, form)

    # Gần giống (Jaccard trên nhãn, ngưỡng 0,8)
    keys = label_keys(items)
    best_id, best = None, 0.0
    for fid, form in active.items():
        score = jaccard(keys, label_keys(form["fields"]))
        if score > best:
            best_id, best = fid, score
    if best_id and best >= NEAR_THRESHOLD:
        form = forms[best_id]
        known = label_keys(form["fields"])
        new_items = [x for x in items if f"{norm(x['label'])}:{x['ui']}" not in known]
        if not new_items:
            return _result(items, fp, f"gần giống ({best:.2f})", "đã có trong registry", best_id, form)
        used = {f["field_id"] for f in form["fields"]}
        added = [_new_field(x, used) for x in new_items]
        candidate = {**form, "fields": form["fields"] + added}
        errs = check_schema(candidate)
        if errs:
            return {"ok": False, "error": "; ".join(errs)}
        form["history"].append({"version": form["version"], "fields": form["fields"], "fingerprint": form["fingerprint"]})
        form["fields"] = candidate["fields"]
        form["version"] += 1
        form["fingerprint"] = fp
        events.append(("form.version", f"{best_id} lên v{form['version']}: thêm trường {[x['label'] for x in added]}"))
        return _result(items, fp, f"gần giống ({best:.2f})", f"tự áp dụng v{form['version']}", best_id, form)

    # Form mới: tầng 3 (stub) sinh schema từ nhãn + kiểu, rồi kiểm tra tự động
    base_id = "phieu_" + slugify(title)
    fid, i = base_id, 2
    while fid in forms:
        fid, i = f"{base_id}_{i}", i + 1
    used, schema = set(), []
    for x in items:
        schema.append(_new_field(x, used))
    form = {
        "form_id": fid, "title": title, "aliases": [norm(title)], "status": "active", "version": 1,
        "fields": schema, "fingerprint": fp, "history": [],
        "detected_by": payload.get("method", "dom"), "generated_by": "stub-schema (tầng 3 chưa nối VLM)",
    }
    errs = check_schema(form)
    if errs:
        form["status"] = "draft"
    forms[fid] = form
    events.append(("form.new", f"{fid} ({title}): " + ("tự áp dụng" if not errs else "lưu nháp – " + "; ".join(errs))))
    return _result(items, fp, "mới", "tự áp dụng" if not errs else "lưu nháp", fid, form)


def detect(forms, payload):
    """Phát hiện form. THUẦN: không đổi `forms` đầu vào; có thay đổi thì trả changes['forms']."""
    work, events = copy.deepcopy(forms), []
    result = _run(work, payload, events)
    if result.get("ok") and events:
        return _out(result, {"forms": work}, events)
    return _out(result)


def rollback_form(forms, form_id):
    work = copy.deepcopy(forms)
    form = work.get(form_id)
    if not form or not form["history"]:
        return _out({"ok": False, "error": "Form này không có phiên bản trước để hoàn tác."})
    prev = form["history"].pop()
    form.update(fields=prev["fields"], version=prev["version"], fingerprint=prev["fingerprint"])
    return _out({"ok": True, "form_id": form_id, "version": form["version"]}, {"forms": work},
                [("form.rollback", f"{form_id} quay về v{form['version']}")])


# Bản mặc định của tính năng: tự đăng ký để lõi dùng được khi chưa nối bản thật
registry.define("form.detect", detect)
registry.define("form.rollback", rollback_form)
