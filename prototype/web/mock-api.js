// Giả lập API của server.py ngay trong trình duyệt.
// Dùng khi mở web/index.html trực tiếp (file://) hoặc khi không có server. Logic bám sát bản Python:
//   shared/common.py, services/reminder.py, services/engine.py, features/*.
// Trạng thái chỉ nằm trong bộ nhớ của trang: tải lại là về dữ liệu mặc định.
(function () {
  "use strict";

  const SEED = window.PROTO_SEED;
  const DOC_ID = "QD-CHAMSOC-2026";
  const DEFAULT_NOW = "2026-11-16T10:00:00+07:00";
  const REG_LABELS = {
    "qd_chamsoc_v1.txt": "QĐ chăm sóc – v1",
    "qd_chamsoc_v2.txt": "QĐ chăm sóc – v2 (có thay đổi)",
  };

  // ---------- tiện ích (shared/common.py) ----------
  const clone = (x) => JSON.parse(JSON.stringify(x));
  const norm = (s) => String(s ?? "").normalize("NFC").replace(/\s+/g, " ").trim().toLowerCase();
  const slugify = (s) =>
    String(s ?? "").replace(/đ/g, "d").replace(/Đ/g, "D").normalize("NFD")
      .replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
  const DUR_RE = /^P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?)?$/;
  function parseDur(s) {
    const m = DUR_RE.exec(s || "");
    if (!m || !m.slice(1).some((x) => x !== undefined)) return null;
    const [d, h, mi] = m.slice(1).map((x) => (x ? Number(x) : 0));
    return d * 864e5 + h * 36e5 + mi * 6e4;
  }
  // Băm nhanh, tất định (thay sha256 của Python). Chỉ dùng để so khớp nội bộ trong trang này.
  function hash(str) {
    let h1 = 0xdeadbeef, h2 = 0x41c6ce57;
    for (let i = 0; i < str.length; i++) {
      const ch = str.charCodeAt(i);
      h1 = Math.imul(h1 ^ ch, 2654435761);
      h2 = Math.imul(h2 ^ ch, 1597334677);
    }
    h1 = Math.imul(h1 ^ (h1 >>> 16), 2246822507) ^ Math.imul(h2 ^ (h2 >>> 13), 3266489909);
    h2 = Math.imul(h2 ^ (h2 >>> 16), 2246822507) ^ Math.imul(h1 ^ (h1 >>> 13), 3266489909);
    return (4294967296 * (2097151 & h2) + (h1 >>> 0)).toString(16).padStart(14, "0");
  }
  const fingerprint = (title, fields) => {
    const labels = fields.map((f) => `${norm(f.label)}:${f.ui}`).sort();
    return "hash:" + hash(norm(title) + "|" + labels.join("|"));
  };
  const labelKeys = (fields) => new Set(fields.map((f) => `${norm(f.label)}:${f.ui}`));
  function jaccard(a, b) {
    let inter = 0;
    for (const x of a) if (b.has(x)) inter++;
    const union = a.size + b.size - inter;
    return union ? inter / union : 0;
  }

  // ---------- thời gian: giữ nguyên múi giờ của chuỗi ISO, như bản Python ----------
  const msOf = (iso) => Date.parse(iso);
  const offOf = (iso) => iso.slice(-6);
  const dayOf = (iso) => iso.slice(0, 10);
  function isoAt(ms, off) {
    const sgn = off[0] === "-" ? -1 : 1;
    const mins = Number(off.slice(1, 3)) * 60 + Number(off.slice(4, 6));
    return new Date(ms + sgn * mins * 6e4).toISOString().slice(0, 19) + off;
  }

  // ---------- trạng thái ----------
  let STATE = null;

  function seedState() {
    const forms = {};
    for (const [fid, f] of Object.entries(SEED.forms)) {
      forms[fid] = { form_id: fid, ...clone(f), status: "active", version: 1,
        fingerprint: fingerprint(f.title, f.fields), history: [] };
    }
    return { clock: DEFAULT_NOW, forms, users: clone(SEED.users), patients: clone(SEED.patients),
      records: clone(SEED.records), rulesets: [], docs: {}, audit: [] };
  }

  function audit(st, kind, detail) {
    st.audit.push({ id: st.audit.length + 1, at: st.clock, kind, detail });
  }
  // Giao dịch: làm việc trên bản sao, chỉ commit khi không có lỗi (như store.transaction)
  function tx(fn) {
    const work = clone(STATE);
    const res = fn(work);
    STATE = work;
    return res;
  }
  function apply(st, res) {
    Object.assign(st, res.changes);
    for (const [kind, detail] of res.events) audit(st, kind, detail);
    return res.result;
  }
  const out = (result, changes = {}, events = []) => ({ result, changes, events });
  function fail(msg) {
    throw new Error("Dữ liệu không hợp lệ: " + msg);
  }

  // ---------- nhắc việc (services/reminder.py) ----------
  const activeRuleset = (st) => st.rulesets.find((v) => v.status === "active") || null;
  const activeRules = (st) => (activeRuleset(st) ? activeRuleset(st).rules : []);

  function userPatients(st, user) {
    const res = [];
    for (const p of st.patients) {
      if (p.doctor === user) res.push([p, "bac_si"]);
      if (p.nurse === user) res.push([p, "dieu_duong"]);
    }
    return res;
  }

  function missingFields(values, required) {
    const vals = values || {};
    return required.filter((f) => {
      const v = vals[f];
      return v === undefined || v === null || (typeof v === "string" && !v.trim());
    });
  }

  function whereOk(ev, where) {
    for (const [k, v] of Object.entries(where || {})) {
      const val = ev[k];
      const ok = Array.isArray(v) ? v.includes(val) : val === v;
      if (!ok) return false;
    }
    return true;
  }

  function eventsOf(patient, rule) {
    const t = rule.trigger;
    if (!t) return [];
    return (patient.events || [])
      .filter((e) => e.event === t.event && whereOk(e, t.where))
      .sort((a, b) => msOf(a.at) - msOf(b.at));
  }

  function ruleTasks(st, p, rule, now) {
    const nowMs = msOf(now);
    const s = rule.schedule;
    const kind = s.type;
    const fid = rule.form_id;
    const req = rule.required_fields || [];
    const title = (st.forms[fid] || {}).title || fid;
    const recs = st.records.filter((r) => r.patient_id === p.patient_id && r.form_id === fid);
    const result = [];

    const since = (t) => recs.filter((r) => msOf(r.at) >= t);
    const complete = (r) => missingFields(r.values, req).length === 0;
    const latest = (rs) => rs.reduce((best, r) => (!best || msOf(r.at) >= msOf(best.at) ? r : best), null);
    const add = (key, status, dueIso, missing, note = "") => {
      result.push({
        task_id: `${rule.rule_id}|${p.patient_id}|${key}`,
        patient_id: p.patient_id, patient: p.name || p.patient_id, bed: p.bed,
        rule_id: rule.rule_id, clause: rule.source.clause, form_id: fid, form_title: title,
        kind, status, due: dueIso ?? null, missing_fields: missing, note,
        missing_labels: missing.map((id) => st.forms[fid].fields.find((f) => f.field_id === id)?.label || id),
      });
    };
    const late = (dueIso) => (nowMs > msOf(dueIso) ? "quá hạn" : "đang chờ");
    const missOf = (last) => (last ? missingFields(last.values, req) : [...req]);

    const evs = eventsOf(p, rule);
    if (kind === "once_within" || kind === "once_after") {
      for (const ev of evs) {
        const startMs = msOf(ev.at);
        const off = offOf(ev.at);
        let dueIso;
        if (kind === "once_after") dueIso = isoAt(startMs + parseDur(s.offset), off);
        else if (s.within === "end_of_day") dueIso = `${dayOf(ev.at)}T23:59:00${off}`;
        else dueIso = isoAt(startMs + parseDur(s.within), off);
        const after = since(startMs);
        if (after.some(complete)) continue;
        add(ev.at, late(dueIso), dueIso, missOf(latest(after)));
      }
    } else if (kind === "on_event") {
      for (const ev of evs) {
        const after = since(msOf(ev.at));
        if (after.some(complete)) continue;
        add(ev.at, "đang chờ", null, missOf(latest(after)), "theo sự kiện");
      }
    } else if (kind === "recurring") {
      if (evs.length) {
        const last = evs[evs.length - 1];
        const start = msOf(last.at);
        const after = since(start);
        const baseRec = latest(after.filter(complete));
        const baseMs = baseRec ? msOf(baseRec.at) : start;
        const baseOff = offOf(baseRec ? baseRec.at : last.at);
        const dueIso = isoAt(baseMs + parseDur(s.every), baseOff);
        add("stream", late(dueIso), dueIso, missOf(latest(after)), `lặp mỗi ${s.every}`);
      }
    } else if (kind === "sequence") {
      if (evs.length) {
        const last = evs[evs.length - 1];
        const start = msOf(last.at);
        const done = since(start).filter(complete).length;
        const ints = s.intervals;
        if (done < ints.length) {
          const hours = ints.slice(0, done + 1).reduce((a, b) => a + b, 0);
          const dueIso = isoAt(start + hours * 36e5, offOf(last.at));
          add(`step${done + 1}`, late(dueIso), dueIso, [], `lần ${done + 1}/${ints.length}`);
        }
      }
    } else if (kind === "daily_before") {
      if (evs.length) {
        const off = offOf(now), day = dayOf(now);
        const limitIso = `${day}T${s.time}:00${off}`;
        const today = recs.filter((r) => dayOf(r.at) === day);
        if (!today.some(complete)) {
          add(day, late(limitIso), limitIso, missOf(latest(today)), `trước ${s.time}`);
        }
      }
    } else if (kind === "min_per_period") {
      if (evs.length) {
        const day = dayOf(now);
        const n = s.count;
        const done = recs.filter((r) => dayOf(r.at) === day && complete(r));
        if (done.length < n) {
          add(day, "đang chờ", `${day}T23:59:00${offOf(now)}`, [], `${done.length}/${n} lần hôm nay`);
        }
      }
    }
    return result;
  }

  function computeTasks(st, user, rules, now) {
    const tasks = [];
    for (const [p, role] of userPatients(st, user)) {
      for (const rule of rules) {
        if ((rule.role || []).includes(role)) tasks.push(...ruleTasks(st, p, rule, now));
      }
    }
    return tasks;
  }

  function patientTasks(st, p, rules, now) {
    const roles = { bac_si: !!p.doctor, dieu_duong: !!p.nurse };
    const res = [];
    for (const rule of rules) {
      const role = (rule.role || []).find((r) => roles[r]);
      if (role) {
        for (const t of ruleTasks(st, p, rule, now)) res.push({ ...t, role });
      }
    }
    return res;
  }

  function summary(st, user) {
    const v = activeRuleset(st);
    const tasks = computeTasks(st, user, v ? v.rules : [], st.clock);
    tasks.sort((a, b) => {
      const da = a.due || "9999", db = b.due || "9999";
      if (da !== db) return da < db ? -1 : 1;
      return a.patient_id < b.patient_id ? -1 : a.patient_id > b.patient_id ? 1 : 0;
    });
    return {
      user, ruleset_version: v ? v.version : null, effective_from: v ? v.effective_from : null,
      count: tasks.length, overdue: tasks.filter((t) => t.status === "quá hạn").length, tasks,
    };
  }

  // ---------- phát hiện form (features/detect_form) ----------
  const NEAR_THRESHOLD = 0.8;
  const UI_TO_TYPE = { number: "number", text: "string", datetime: "datetime", checkbox: "boolean", select: "enum" };
  const FIELD_TYPES = new Set(Object.values(UI_TO_TYPE));

  function newField(item, used) {
    const base = slugify(item.label) || "truong";
    let fid = base, i = 2;
    while (used.has(fid)) { fid = `${base}_${i}`; i++; }
    used.add(fid);
    const ui = item.ui ?? "text";
    const field = {
      field_id: fid, label: item.label, type: UI_TO_TYPE[item.ui] ?? "string", ui,
      required: !!item.required, data_level: 2,
    };
    if (ui === "select") field.options = item.options && item.options.length ? item.options : ["Có", "Không"];
    return field;
  }

  function checkSchema(form) {
    const errs = [];
    const fields = form.fields || [];
    if (!fields.length) errs.push("form không có trường nào");
    const ids = fields.map((f) => f.field_id);
    if (new Set(ids).size !== ids.length) errs.push("field_id bị trùng");
    for (const f of fields) {
      if (!FIELD_TYPES.has(f.type)) errs.push(`kiểu không hợp lệ: ${f.type}`);
      if (![1, 2, 3].includes(f.data_level)) errs.push(`data_level không hợp lệ: ${f.field_id}`);
    }
    return errs;
  }

  function fieldMap(items, formFields) {
    const lookup = {};
    for (const f of formFields) lookup[norm(f.label)] = f.field_id;
    return items.map((x) => ({ label: x.label, field_id: lookup[norm(x.label)] ?? null }));
  }

  function detectResult(items, fp, match, action, fid, form) {
    return {
      ok: true, match, action, form_id: fid, title: form.title, version: form.version, status: form.status,
      fingerprint: fp, field_map: fieldMap(items, form.fields),
    };
  }

  function detectRun(forms, payload, events) {
    const title = (payload.title || "").trim() || "Biểu mẫu không tên";
    const items = (payload.fields || []).filter((f) => f.label);
    if (!items.length) return { ok: false, error: "Không đọc được trường nào trên màn hình." };
    const fp = fingerprint(title, items);
    const active = Object.entries(forms).filter(([, v]) => v.status === "active");

    for (const [fid, form] of active) {
      if (form.fingerprint === fp) return detectResult(items, fp, "exact", "không cần làm gì", fid, form);
    }

    const keys = labelKeys(items);
    let bestId = null, best = 0;
    for (const [fid, form] of active) {
      const score = jaccard(keys, labelKeys(form.fields));
      if (score > best) { bestId = fid; best = score; }
    }
    if (bestId && best >= NEAR_THRESHOLD) {
      const form = forms[bestId];
      const known = labelKeys(form.fields);
      const newItems = items.filter((x) => !known.has(`${norm(x.label)}:${x.ui}`));
      const match = `gần giống (${best.toFixed(2)})`;
      if (!newItems.length) return detectResult(items, fp, match, "đã có trong registry", bestId, form);
      const used = new Set(form.fields.map((f) => f.field_id));
      const added = newItems.map((x) => newField(x, used));
      const candidate = { ...form, fields: [...form.fields, ...added] };
      const errs = checkSchema(candidate);
      if (errs.length) return { ok: false, error: errs.join("; ") };
      form.history.push({ version: form.version, fields: form.fields, fingerprint: form.fingerprint });
      form.fields = candidate.fields;
      form.version += 1;
      form.fingerprint = fp;
      const labelList = "[" + added.map((x) => `'${x.label}'`).join(", ") + "]";
      events.push(["form.version", `${bestId} lên v${form.version}: thêm trường ${labelList}`]);
      return detectResult(items, fp, match, `tự áp dụng v${form.version}`, bestId, form);
    }

    const baseId = "phieu_" + slugify(title);
    let fid = baseId, i = 2;
    while (forms[fid]) { fid = `${baseId}_${i}`; i++; }
    const used = new Set();
    const schema = items.map((x) => newField(x, used));
    const form = {
      form_id: fid, title, aliases: [norm(title)], status: "active", version: 1, fields: schema,
      fingerprint: fp, history: [], detected_by: payload.method || "dom",
      generated_by: "stub-schema (tầng 3 chưa nối VLM)",
    };
    const errs = checkSchema(form);
    if (errs.length) form.status = "draft";
    forms[fid] = form;
    events.push(["form.new", `${fid} (${title}): ` + (!errs.length ? "tự áp dụng" : "lưu nháp – " + errs.join("; "))]);
    return detectResult(items, fp, "mới", !errs.length ? "tự áp dụng" : "lưu nháp", fid, form);
  }

  function detectForm(forms, payload) {
    const work = clone(forms), events = [];
    const result = detectRun(work, payload, events);
    if (result.ok && events.length) return out(result, { forms: work }, events);
    return out(result);
  }

  function rollbackForm(forms, formId) {
    const work = clone(forms);
    const form = work[formId];
    if (!form || !form.history.length) return out({ ok: false, error: "Form này không có phiên bản trước để hoàn tác." });
    const prev = form.history.pop();
    Object.assign(form, { fields: prev.fields, version: prev.version, fingerprint: prev.fingerprint });
    return out({ ok: true, form_id: formId, version: form.version }, { forms: work },
      [["form.rollback", `${formId} quay về v${form.version}`]]);
  }

  // ---------- bộ luật chính sách (features/policy_rules) ----------
  const ROLE_PHRASES = [["bác sĩ", "bac_si"], ["điều dưỡng", "dieu_duong"]];
  const SCHEDULE_TYPES = new Set(["once_within", "once_after", "recurring", "sequence", "daily_before", "min_per_period", "on_event"]);
  const EVENT_CATALOG = new Set(["admission", "discharge", "surgery_end", "medication_given"]);
  const AMBIGUOUS = /khoảng|hoặc|tối đa/i;
  const HEAD_STOP = /\s(?=trong vòng|trong ngày|sau \d+ phút|mỗi \d+ giờ|theo lịch|trước \d|tối thiểu|khi bệnh nhân|khoảng)/;
  const CLAUSE_RE = /^(\d+\.\d+)\s+(.+)$/;
  const WATCH_FIELDS = ["form_id", "role", "trigger", "schedule", "required_fields"];
  const SCHEDULE_PATTERNS = [
    [/trong vòng (\d+) giờ kể từ khi bệnh nhân vào viện/i, (m) => ["once_within", { within: `PT${m[1]}H` }, "admission", null]],
    [/trong ngày kể từ khi bệnh nhân vào viện/i, () => ["once_within", { within: "end_of_day" }, "admission", null]],
    [/trong ngày khi bệnh nhân ra viện/i, () => ["once_within", { within: "end_of_day" }, "discharge", null]],
    [/sau (\d+) phút khi dùng thuốc tiêm, truyền giảm đau/i,
      (m) => ["once_after", { offset: `PT${m[1]}M` }, "medication_given", { route: ["tiem", "truyen"], purpose: "giam_dau" }]],
    [/mỗi (\d+) giờ một lần, tính từ lần nhập gần nhất/i,
      (m) => ["recurring", { every: `PT${m[1]}H`, anchor: "last_entry" }, "admission", null]],
    [/theo lịch: ([\d, ]+) giờ, tính từ lúc kết thúc phẫu thuật/i,
      (m) => ["sequence", { intervals: (m[1].match(/\d+/g) || []).map(Number), unit: "hour", anchor: "surgery_end" }, "surgery_end", null]],
    [/trước (\d{2}:\d{2}) mỗi ngày/i, (m) => ["daily_before", { time: m[1] }, "admission", null]],
    [/tối thiểu (\d+) lần mỗi ngày/i, (m) => ["min_per_period", { count: Number(m[1]), period: "P1D" }, "admission", null]],
    [/khi bệnh nhân ra viện/i, () => ["on_event", { events: ["discharge"] }, "discharge", null]],
  ];

  function splitClauses(text) {
    const res = [];
    for (const raw of text.split(/\r?\n/)) {
      const m = CLAUSE_RE.exec(raw.trim());
      if (m) res.push([m[1], m[2]]);
    }
    return res;
  }

  function buildRule(docId, docVersion, effectiveFrom, clauseId, body, forms) {
    const cut = body.indexOf("Trường bắt buộc:");
    const main = cut >= 0 ? body.slice(0, cut) : body;
    const reqPart = cut >= 0 ? body.slice(cut + "Trường bắt buộc:".length) : "";
    const sentence = main.trim();
    const roles = ROLE_PHRASES.filter(([p]) => norm(sentence).includes(p)).map(([, r]) => r);
    const hs = sentence.search(HEAD_STOP);
    const head = norm(hs >= 0 ? sentence.slice(0, hs) : sentence);

    let formId = null, best = 0;
    for (const [fid, f] of Object.entries(forms)) {
      for (const alias of f.aliases || []) {
        const a = norm(alias);
        if (a && head.includes(a) && a.length > best) { formId = fid; best = a.length; }
      }
    }

    let stype = null, params = {}, event = null, where = null;
    for (const [pattern, build] of SCHEDULE_PATTERNS) {
      const m = pattern.exec(sentence);
      if (m) { [stype, params, event, where] = build(m); break; }
    }

    const preFlags = [];
    if (stype === null && AMBIGUOUS.test(sentence)) {
      preFlags.push("diễn đạt mơ hồ (khoảng/hoặc/tối đa): cần làm rõ, không đoán lịch");
    }

    const reqLabels = reqPart.trim().replace(/\.+$/, "").split(",").map((x) => x.trim()).filter(Boolean);
    const lookup = {};
    if (formId) for (const f of forms[formId].fields) lookup[norm(f.label)] = f.field_id;
    const required = reqLabels.map((x) => lookup[norm(x)] ?? x);

    let trigger = null;
    if (event) {
      trigger = { event };
      if (where) trigger.where = where;
    }
    const rule = {
      rule_id: `${docId}:${clauseId}`,
      source: { doc_id: docId, doc_version: docVersion, clause: `Điều ${clauseId}`, evidence: sentence },
      form_id: formId, role: roles, trigger, condition: null,
      schedule: stype ? { type: stype, ...params } : null,
      required_fields: required, priority: "normal", effective_from: effectiveFrom, effective_to: null,
      supersedes: [], status: "active",
    };
    return [rule, body, preFlags];
  }

  // Độ trùng khớp dài nhất (tương đương difflib.find_longest_match không có junk)
  function longestCommon(a, b) {
    let best = 0;
    let prev = new Array(b.length + 1).fill(0);
    for (let i = 1; i <= a.length; i++) {
      const cur = new Array(b.length + 1).fill(0);
      for (let j = 1; j <= b.length; j++) {
        if (a[i - 1] === b[j - 1]) {
          cur[j] = prev[j - 1] + 1;
          if (cur[j] > best) best = cur[j];
        }
      }
      prev = cur;
    }
    return best;
  }

  const isEmptyVal = (v) => v === undefined || v === null || v === "" || (Array.isArray(v) && v.length === 0);

  function checkRule(rule, clauseBody, preFlags, forms) {
    const errors = [], flags = [...preFlags];
    const sched = rule.schedule;
    const ev = rule.source.evidence;

    let need = ["rule_id", "source", "form_id", "role", "trigger", "schedule", "required_fields", "effective_from", "status"];
    if (preFlags.length) need = need.filter((k) => k !== "schedule" && k !== "trigger");
    const missing = need.filter((k) => isEmptyVal(rule[k]));
    if (missing.length) errors.push(`L1: thiếu khóa ${missing.join(", ")}`);
    if (sched && !SCHEDULE_TYPES.has(sched.type)) errors.push("L1: schedule.type không hợp lệ");
    if (rule.role.length && !rule.role.every((r) => r === "bac_si" || r === "dieu_duong")) errors.push("L1: role không hợp lệ");

    const form = forms[rule.form_id || ""];
    if (rule.form_id && (!form || form.status !== "active")) {
      errors.push("L2: form_id không có trong registry hoặc không active");
    } else if (form) {
      const ids = new Set(form.fields.map((f) => f.field_id));
      const bad = rule.required_fields.filter((x) => !ids.has(x));
      if (bad.length) errors.push(`L2: trường bắt buộc không có trong form: ${bad.join(", ")}`);
    }
    if (rule.trigger && !EVENT_CATALOG.has(rule.trigger.event)) errors.push("L2: trigger.event ngoài danh mục sự kiện");

    const a = norm(ev), b = norm(clauseBody);
    if (a) {
      const ratio = longestCommon(a, b) / a.length;
      if (ratio < 0.95) errors.push(`L3: trích dẫn không nằm trong khoản (${Math.round(ratio * 100)}% khớp)`);
      else if (ratio < 1) flags.push(`L3: trích dẫn gần đúng (${Math.round(ratio * 100)}%), cần xem lại`);
    }

    if (sched) {
      let nums = [];
      for (const k of ["within", "offset", "every", "time"]) {
        if (typeof sched[k] === "string") nums = nums.concat(sched[k].match(/\d+/g) || []);
      }
      nums = nums.concat((sched.intervals || []).map(String));
      if (sched.count !== undefined) nums.push(String(sched.count));
      const evNums = new Set(ev.match(/\d+/g) || []);
      const badNums = nums.filter((n) => !evNums.has(n));
      if (badNums.length) errors.push(`L4: số ${badNums.join(", ")} không có trong trích dẫn`);

      for (const k of ["within", "offset", "every"]) {
        const v = sched[k];
        if (typeof v === "string" && v !== "end_of_day") {
          const d = parseDur(v);
          if (d === null) errors.push(`L5: thời lượng không hợp lệ: ${v}`);
          else if (!(5 * 6e4 <= d && d <= 30 * 864e5)) errors.push(`L5: thời lượng ngoài khoảng 5 phút – 30 ngày: ${v}`);
        }
      }
      if (sched.type === "sequence" && (!sched.intervals || !sched.intervals.length || Math.min(...sched.intervals) <= 0)) {
        errors.push("L5: chuỗi lịch rỗng hoặc có giá trị <= 0");
      }
      if (sched.type === "min_per_period" && (sched.count ?? 0) <= 0) errors.push("L5: số lần tối thiểu phải > 0");
    }
    return [errors, flags];
  }

  const ruleKey = (r) => (!r.form_id || !r.trigger ? null : JSON.stringify([r.form_id, [...(r.role || [])].sort(), r.trigger.event]));
  const ruleSig = (r) => JSON.stringify(r.schedule);

  function resolveWithinDoc(rules) {
    const groups = new Map();
    for (const r of rules) {
      const k = ruleKey(r);
      if (r.status === "active" && k) {
        if (!groups.has(k)) groups.set(k, []);
        groups.get(k).push(r);
      }
    }
    for (const items of groups.values()) {
      if (items.length < 2) continue;
      if (new Set(items.map(ruleSig)).size === 1) {
        const keep = items[0];
        for (const dup of items.slice(1)) {
          dup.status = "merged";
          dup.validation.flags.push(`L6: trùng với ${keep.rule_id}, đã gộp`);
        }
      } else {
        for (const it of items) {
          it.status = "needs_clarification";
          it.validation.flags.push("L6: xung đột lịch với luật cùng form/vai trò/sự kiện");
        }
      }
    }
  }

  function resolveCrossDoc(newRules, other) {
    for (const o of other) {
      const k = ruleKey(o);
      for (const r of newRules) {
        if (r.status === "active" && k && ruleKey(r) === k) {
          if (ruleSig(r) === ruleSig(o)) o.status = "merged";
          else { o.status = "superseded"; r.supersedes.push(o.rule_id); }
        }
      }
    }
  }

  function diffRules(old, neu) {
    const om = new Map(old.map((r) => [r.rule_id, r]));
    const nm = new Map(neu.map((r) => [r.rule_id, r]));
    const added = [], removed = [], changed = [];
    for (const [k, n] of nm) {
      if (!om.has(k)) added.push({ rule_id: k, clause: n.source.clause, evidence: n.source.evidence });
    }
    for (const [k, o] of om) {
      if (!nm.has(k)) removed.push({ rule_id: k, clause: o.source.clause, evidence: o.source.evidence });
    }
    for (const [k, n] of nm) {
      if (!om.has(k)) continue;
      const o = om.get(k);
      const fields = WATCH_FIELDS.filter((f) => JSON.stringify(o[f]) !== JSON.stringify(n[f]));
      if (fields.length || o.source.evidence !== n.source.evidence) {
        changed.push({ rule_id: k, clause: n.source.clause, evidence: n.source.evidence,
          before: o.schedule, after: n.schedule, changed_fields: fields });
      }
    }
    return { added, changed, removed };
  }

  function policyIngest(st, text, docId, docVersion, effectiveFrom, dryRun) {
    const rulesets = st.rulesets, forms = st.forms, docs = st.docs, clock = st.clock;
    const clauses = splitClauses(text);
    if (!clauses.length) {
      return out({ ok: false, error: "Không tìm thấy khoản nào. Mỗi khoản cần dạng '1.1 Nội dung...'." });
    }
    const checked = [];
    for (const [cid, body] of clauses) {
      const [rule, clauseBody, preFlags] = buildRule(docId, docVersion, effectiveFrom, cid, body, forms);
      const [errors, flags] = checkRule(rule, clauseBody, preFlags, forms);
      rule.validation = { errors, flags };
      rule.status = errors.length ? "rejected" : flags.length ? "needs_clarification" : "active";
      checked.push(rule);
    }
    resolveWithinDoc(checked);

    const cur = clone(activeRules(st));
    const other = cur.filter((r) => r.source.doc_id !== docId);
    resolveCrossDoc(checked, other);
    if (!checked.some((r) => r.status === "active")) {
      return out({ ok: false, error: "Không có khoản nào của văn bản này qua kiểm tra.", checked });
    }
    const applied = [...checked.filter((r) => r.status === "active"), ...other.filter((r) => r.status === "active")];

    const diff = diffRules(cur, applied);
    const impact = {};
    const users = [...new Set([...st.patients.map((p) => p.doctor), ...st.patients.map((p) => p.nurse)].filter(Boolean))].sort();
    for (const u of users) {
      impact[u] = { before: computeTasks(st, u, cur, clock).length, after: computeTasks(st, u, applied, clock).length };
    }
    const summaryCount = {};
    for (const s of ["active", "needs_clarification", "rejected", "merged"]) {
      summaryCount[s] = checked.filter((r) => r.status === s).length;
    }
    const result = {
      ok: true, dry_run: dryRun, doc_id: docId, doc_version: docVersion, effective_from: effectiveFrom,
      summary: summaryCount, checked, diff, impact, applied_count: applied.length,
    };
    if (dryRun) return out(result);

    const version = `v${rulesets.length + 1}`;
    const newRulesets = clone(rulesets);
    for (const v of newRulesets) if (v.status === "active") v.status = "superseded";
    newRulesets.push({
      version, status: "active", effective_from: effectiveFrom, published_at: clock,
      source: { doc_id: docId, doc_version: docVersion }, rules: applied, checked, summary: summaryCount, diff, impact,
    });
    const newDocs = { ...docs, [`${docId}@${docVersion}`]: { uploaded_at: clock, text } };
    result.published_version = version;
    const event = ["policy.publish",
      `${version} từ ${docId} ${docVersion}: +${diff.added.length} ~${diff.changed.length} -${diff.removed.length}; ` +
      `áp dụng ${applied.length} luật, cần làm rõ ${summaryCount.needs_clarification}, từ chối ${summaryCount.rejected}`];
    return out(result, { rulesets: newRulesets, docs: newDocs }, [event]);
  }

  function policyRollback(rulesets) {
    const idx = rulesets.findIndex((v) => v.status === "active");
    if (idx < 0 || idx === 0) return out({ ok: false, error: "Không có phiên bản trước để hoàn tác." });
    const next = clone(rulesets);
    const cur = next[idx], prev = next[idx - 1];
    cur.status = "rolled_back";
    prev.status = "active";
    return out({ ok: true, active: prev.version }, { rulesets: next },
      [["policy.rollback", `hoàn tác ${cur.version} về ${prev.version}`]]);
  }

  // ---------- PII và giọng nói (đồng bộ services/pii_adapter, features/voice_input, services/policy_validation) ----------
  const PII_PHONE = /\b0\d{9,10}\b/g;
  const PII_CCCD = /\b\d{12}\b/g;
  const PII_EMAIL = /(?<![\w@.+-])[\w.+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}(?![\w@-])/g;
  const PII_NAME = /(?<![\p{L}\p{N}_])([Tt]ên bệnh nhân là|[Tt]ên bệnh nhân|[Bb]ệnh nhân tên là|[Bb]ệnh nhân là|[Tt]ên là|[Nn]gười liên hệ là|[Ll]iên hệ là|Anh|Chị|Ông|Bà|anh|chị|ông|bà|[Bb]ệnh nhân)\s+((?:[A-ZÀ-Ỵ][\p{L}\p{N}_]*\s?){1,4})/gu;
  const PII_CLINICAL_GUARD = new Set(["spo2", "hba1c", "gcs", "bmi", "đau", "sốt", "mạch", "huyết", "nhiệt", "nhịp", "không", "có"]);

  function maskPii(text) {
    let count = 0;
    text = text.replace(PII_PHONE, () => { count++; return "[SĐT]"; });
    text = text.replace(PII_CCCD, () => { count++; return "[CCCD]"; });
    text = text.replace(PII_EMAIL, () => { count++; return "[PII]"; });
    text = text.replace(PII_NAME, (m, g1, g2) => {
      const target = g2.trim();
      if (!target || target.startsWith("[") || PII_CLINICAL_GUARD.has(norm(target.split(/\s+/)[0]))) return m;
      count++;
      const idx = m.lastIndexOf(target);
      return idx >= 0 ? m.slice(0, idx) + "[TÊN]" + m.slice(idx + target.length) : m;
    });
    return [text, count];
  }

  const OUT_OF_SCOPE = ["trời đẹp", "thời tiết", "cuối tuần", "ăn trưa", "bóng đá", "phim"];
  const SYNONYMS = {
    "tên bệnh nhân": ["họ tên bệnh nhân", "bệnh nhân tên là", "bệnh nhân là", "tên người bệnh"],
    "mạch": ["nhịp tim"], "nhịp thở": ["tần số thở"], "huyết áp": ["ha"],
    "nhiệt độ": ["thân nhiệt", "sốt"], "spo2": ["oxy máu", "bão hòa oxy"],
    "nội dung chăm sóc": ["chăm sóc", "thực hiện chăm sóc"],
    "người thực hiện": ["điều dưỡng thực hiện", "người làm"],
    "điểm nguy cơ ngã": ["điểm ngã", "nguy cơ ngã"], "kết quả": ["kết quả đánh giá", "kết luận"],
    "điểm đau": ["mức độ đau", "thang điểm đau"], "thời điểm đánh giá": ["thời gian đánh giá", "lúc đánh giá", "thời điểm"],
    "dị ứng": ["tiền sử dị ứng", "bệnh nhân dị ứng"], "thuốc đang dùng": ["đang dùng", "thuốc hiện tại"],
    "người liên hệ": ["người nhà", "liên hệ"], "tiền sử": ["tiền sử bệnh", "bệnh nền"],
    "lý do vào viện": ["vào viện vì", "lý do nhập viện", "lý do"],
    "chẩn đoán": ["chẩn đoán vào viện", "chẩn đoán sơ bộ", "chẩn đoán là"],
    "chẩn đoán ra viện": ["chẩn đoán khi ra viện"], "hướng điều trị": ["kế hoạch điều trị", "điều trị tiếp"],
    "dấu hiệu theo dõi": ["theo dõi sau mổ", "dấu hiệu"],
    "nội dung giáo dục": ["tư vấn giáo dục", "hướng dẫn bệnh nhân"], "người nhận giáo dục": ["người nhận"],
    "điểm braden": ["braden", "điểm loét"], "nguồn cung cấp bệnh sử": ["cung cấp bệnh sử", "nguồn cung cấp"],
    "nguồn tiếp nhận": ["tiếp nhận", "nơi tiếp nhận"],
  };

  function speech(text) {
    return norm(text).replace(/(\d+)\s*phẩy\s*(\d+)/g, "$1.$2");
  }

  function validateDraftMock(formId, extracted) {
    const warnings = [], alerts = [];
    if (formId !== "phieu_sinh_ton_nguoi_lon" || !extracted) return { validation_warnings: warnings, policy_alerts: alerts };
    if (typeof extracted.mach === "number" && (extracted.mach < 30 || extracted.mach > 220)) {
      warnings.push({ rule_id: "POL-VALID-01", clause: "Điều 3.1.b", field: "mach", value: extracted.mach, message: "Chỉ số mạch ngoài khoảng hợp lý (30 - 220 lần/phút)" });
    }
    if (typeof extracted.spo2 === "number" && (extracted.spo2 < 50 || extracted.spo2 > 100)) {
      warnings.push({ rule_id: "POL-VALID-01", clause: "Điều 3.1.b", field: "spo2", value: extracted.spo2, message: "Chỉ số SpO2 phải từ 50% đến 100%" });
    }
    if (typeof extracted.huyet_ap === "string") {
      const m = /^\s*(\d{2,3})\s*\/\s*(\d{2,3})/.exec(extracted.huyet_ap);
      if (m && Number(m[1]) <= Number(m[2])) {
        warnings.push({ rule_id: "POL-VALID-01", clause: "Điều 3.1.b", field: "huyet_ap", value: extracted.huyet_ap, message: "Huyết áp tâm thu bắt buộc phải lớn hơn huyết áp tâm trương" });
      }
    }
    const matched = [];
    if (typeof extracted.spo2 === "number" && extracted.spo2 < 90) matched.push(`spo2=${extracted.spo2}`);
    if (typeof extracted.mach === "number" && extracted.mach > 120) matched.push(`mach=${extracted.mach}`);
    if (matched.length) {
      alerts.push({ rule_id: "POL-TRIGGER-01", clause: "Điều 4.2", alert_level: "RED", matched, message: "Khi chỉ số SpO2 dưới 90% hoặc Mạch trên 120 lần/phút, phải kích hoạt ngay phiếu xử trí cấp cứu và báo bác sĩ." });
    }
    return { validation_warnings: warnings, policy_alerts: alerts };
  }

  function extract(text, fields) {
    const t = speech(text);
    const res = {};
    const cands = [];
    for (const f of fields) {
      const label = norm(f.label);
      const base = label.replace(/\s*\([^)]*\)/g, "").trim();
      const kws = [label, ...(base && base !== label ? [base] : []), ...(SYNONYMS[label] || []), ...(SYNONYMS[base] || [])];
      for (const kw of new Set(kws)) cands.push([kw, f.field_id]);
    }
    cands.sort((a, b) => b[0].length - a[0].length);
    const spans = [], occ = [];
    for (const [kw, fid] of cands) {
      if (spans.some((x) => x[2] === fid)) continue;
      const idx = t.indexOf(kw);
      if (idx < 0) continue;
      const s = idx, e = idx + kw.length;
      if (occ.some(([bs, be]) => bs <= s && e <= be)) continue;
      spans.push([s, e, fid]); occ.push([s, e]);
    }
    spans.sort((a, b) => a[0] - b[0]);

    for (const f of fields) {
      const label = norm(f.label);
      if (label === "huyết áp") {
        const m = /(\d{2,3})\s*(?:trên|\/)\s*(\d{2,3})/.exec(t);
        if (m) res[f.field_id] = `${m[1]}/${m[2]}`;
        continue;
      }
      const sp = spans.find((x) => x[2] === f.field_id);
      if (!sp) continue;
      const nextBound = spans.filter((x) => x[2] !== f.field_id && x[0] >= sp[1]).reduce((mn, x) => Math.min(mn, x[0]), t.length);
      const rest = t.slice(sp[1], nextBound);
      if (f.ui === "number") {
        const m = /^[^\d]{0,12}(\d+(?:\.\d+)?)/.exec(rest);
        if (m) res[f.field_id] = Number(m[1]);
      } else if (f.ui === "datetime") {
        const dm = /(\d{4}-\d{2}-\d{2})[t\s]+(\d{1,2})(?::|\s*giờ\s*|\s+)(\d{2})/.exec(rest);
        if (dm) res[f.field_id] = `${dm[1]}T${String(dm[2]).padStart(2, "0")}:${dm[3]}`;
      } else if (f.ui === "checkbox") {
        const cm = /^\s*(?:là|:)?\s*(có|không|đúng|sai|true|false)\b/.exec(rest);
        if (cm) res[f.field_id] = ["có", "đúng", "true"].includes(cm[1]);
      } else if (["text", "textarea", "select"].includes(f.ui)) {
        const m = /^\s*(?:là|:)?\s*([^.;,]+)/.exec(rest);
        if (m && m[1].trim()) {
          let textValue = m[1].trim().slice(0, 120);
          for (const tag of ["[tên]", "[sđt]", "[cccd]", "[pii]"]) {
            if (textValue.includes(tag)) textValue = textValue.replaceAll(tag, tag.toUpperCase());
          }
          if ((f.field_id === "ten_benh_nhan" || f.field_id === "nguoi_lien_he") && textValue.includes("[TÊN]")) textValue = "[TÊN]";
          const value = f.ui === "select" ? (f.options || []).find((o) => norm(o) === norm(textValue)) : textValue;
          if (value !== undefined) res[f.field_id] = value;
        }
      }
    }
    return res;
  }

  function voiceProcess(text, form) {
    const [masked, pii] = maskPii(text);
    const low = norm(text);
    if (OUT_OF_SCOPE.some((k) => low.includes(k))) {
      return { masked, pii_masked: pii, out_of_scope: true, extracted: {}, validation_warnings: [], policy_alerts: [] };
    }
    const extracted = extract(masked, form.fields);
    const checks = validateDraftMock(form.form_id, extracted);
    return { masked, pii_masked: pii, out_of_scope: false, extracted, ...checks };
  }

  // ---------- endpoint GET ----------
  const rulesetList = (st) => st.rulesets.map((v) => ({
    version: v.version, status: v.status, effective_from: v.effective_from, published_at: v.published_at,
    applied: v.rules.length, summary: v.summary, source: v.source,
  }));

  const GET = {
    "/api/state": (st) => {
      const v = activeRuleset(st);
      return {
        clock: st.clock, active_ruleset: v ? v.version : null, effective_from: v ? v.effective_from : null,
        active_forms: Object.values(st.forms).filter((f) => f.status === "active").length,
        rulesets: rulesetList(st),
      };
    },
    "/api/forms": (st) => ({
      forms: Object.values(st.forms).map((f) => ({
        form_id: f.form_id, title: f.title, status: f.status, version: f.version, fields: f.fields,
        history_len: f.history.length,
      })),
    }),
    "/api/users": (st) => ({ users: st.users }),
    "/api/patients": (st) => ({
      patients: st.patients.map((p) => {
        const tasks = patientTasks(st, p, activeRules(st), st.clock);
        return {
          patient_id: p.patient_id, name: p.name, bed: p.bed, doctor: p.doctor, nurse: p.nurse,
          open: tasks.length, overdue: tasks.filter((t) => t.status === "quá hạn").length,
        };
      }),
      clock: st.clock,
    }),
    "/api/patient": (st, q) => {
      const pid = q.get("id") || "";
      const p = st.patients.find((x) => x.patient_id === pid);
      if (!p) fail("không tìm thấy bệnh nhân");
      const rules = activeRules(st);
      const tasks = patientTasks(st, p, rules, st.clock);
      const forms = new Map();
      for (const r of rules) {
        const applies = (r.role || []).some((role) => (role === "bac_si" && p.doctor) || (role === "dieu_duong" && p.nurse));
        if (!applies) continue;
        if (!forms.has(r.form_id)) {
          const sf = st.forms[r.form_id] || {};
          forms.set(r.form_id, {
            form_id: r.form_id, title: sf.title ?? r.form_id, fields: sf.fields ?? [],
            rules: [], required: [], roles: [], tasks: [], records: [],
          });
        }
        const f = forms.get(r.form_id);
        f.rules.push({ rule_id: r.rule_id, clause: r.source.clause, evidence: r.source.evidence, schedule: r.schedule.type });
        f.required = [...new Set([...f.required, ...(r.required_fields || [])])].sort();
        f.roles = [...new Set([...f.roles, ...(r.role || [])])].sort();
      }
      for (const t of tasks) if (forms.has(t.form_id)) forms.get(t.form_id).tasks.push(t);
      for (const rec of st.records) {
        if (rec.patient_id === pid && forms.has(rec.form_id)) forms.get(rec.form_id).records.push(rec);
      }
      for (const f of forms.values()) {
        f.records.reverse().sort((a, b) => (a.at < b.at ? 1 : a.at > b.at ? -1 : 0));
      }
      const v = activeRuleset(st);
      return {
        patient: { patient_id: p.patient_id, name: p.name, bed: p.bed, doctor: p.doctor, nurse: p.nurse, events: p.events },
        clock: st.clock, ruleset_version: v ? v.version : null, forms: [...forms.values()],
      };
    },
    "/api/rules": (st) => {
      const v = activeRuleset(st);
      const rows = (v ? v.rules : []).map((r) => ({
        rule_id: r.rule_id, clause: r.source.clause, evidence: r.source.evidence, form_id: r.form_id,
        form_title: (st.forms[r.form_id] || {}).title || r.form_id, role: r.role, schedule: r.schedule.type,
      }));
      return { rules: rows, version: v ? v.version : null };
    },
    "/api/tasks": (st, q) => summary(st, q.get("user") || "bs_a"),
    "/api/rulesets": (st) => ({ rulesets: rulesetList(st) }),
    "/api/samples": () => ({
      samples: Object.keys(REG_LABELS).map((name) => ({ name, label: REG_LABELS[name], text: SEED.regulations[name] })),
    }),
    "/api/audit": (st) => ({ audit: [...st.audit].reverse().slice(0, 300) }),
  };

  // ---------- endpoint POST ----------
  const POST = {
    "/api/detect": (body) => tx((st) => apply(st, detectForm(st.forms, body))),
    "/api/forms/rollback": (body) => tx((st) => apply(st, rollbackForm(st.forms, body.form_id))),
    "/api/records": (body) => tx((st) => {
      const pid = body.patient_id, fid = body.form_id;
      if (!st.patients.some((p) => p.patient_id === pid)) fail("không tìm thấy bệnh nhân");
      const form = st.forms[fid];
      if (!form) fail("không tìm thấy form");
      const fieldIds = new Set(form.fields.map((f) => f.field_id));
      const values = {};
      for (const [k, v] of Object.entries(body.values || {})) {
        if (fieldIds.has(k) && v !== null && v !== undefined && v !== "") values[k] = v;
      }
      const required = form.fields.filter((f) => f.required).map((f) => f.field_id);
      for (const rule of activeRules(st)) {
        if (rule.form_id === fid) {
          for (const id of rule.required_fields) if (!required.includes(id)) required.push(id);
        }
      }
      const missing = missingFields(values, required);
      const rec = {
        record_id: `REC-${String(st.records.length + 1).padStart(4, "0")}`, patient_id: pid, form_id: fid,
        at: st.clock, values, user: body.user ?? null, source: body.source ?? "emr", missing_required: missing,
      };
      st.records.push(rec);
      audit(st, "record.save", `${rec.record_id} ${fid} cho ${pid} (nguồn ${rec.source}); thiếu: ${missing.join(", ") || "không"}`);
      return { ok: true, record: rec };
    }),
    "/api/policy/ingest": (body) => tx((st) => apply(st, policyIngest(
      st, body.text, body.doc_id || DOC_ID, body.doc_version, body.effective_from || st.clock.slice(0, 10), !!body.dry_run))),
    "/api/policy/rollback": () => tx((st) => apply(st, policyRollback(st.rulesets))),
    "/api/voice": (body) => {
      const form = STATE.forms[body.form_id];
      if (!form) fail("không tìm thấy form");
      return { ok: true, ...voiceProcess(body.text || "", form) };
    },
    "/api/clock": (body) => tx((st) => {
      let value;
      if (body.minutes !== undefined) {
        value = isoAt(msOf(st.clock) + Number(body.minutes) * 6e4, offOf(st.clock));
      } else {
        value = body.now || "";
        if (Number.isNaN(Date.parse(value))) fail("định dạng thời gian không hợp lệ");
      }
      st.clock = value;
      audit(st, "clock", `đặt giờ hệ thống: ${value}`);
      return { ok: true, clock: value };
    }),
    "/api/reset": () => { STATE = seedState(); seedPolicy(); return { ok: true }; },
  };

  // Nạp bộ luật v1 khi khởi tạo, giống ensure_seeded() trong server.py
  function seedPolicy() {
    tx((st) => {
      if (st.rulesets.length) return;
      const res = policyIngest(st, SEED.regulations["qd_chamsoc_v1.txt"], DOC_ID, "v1", "2026-11-10", false);
      if (!res.result.ok) throw new Error("Không nạp được bộ luật v1: " + res.result.error);
      apply(st, res);
    });
  }

  // ---------- điểm vào ----------
  // Kết quả có ok === false thì ném lỗi, như server trả mã 400 cho trình duyệt.
  async function call(url, body) {
    const [path, qs] = String(url).split("?");
    const q = new URLSearchParams(qs || "");
    const handler = body === undefined ? GET[path] : POST[path];
    if (!handler) throw new Error("không có API này");
    const res = body === undefined ? handler(STATE, q) : handler(body);
    if (res && res.ok === false) throw new Error(res.error || "Lỗi không xác định");
    return clone(res);
  }

  STATE = seedState();
  seedPolicy();

  window.MockServer = { call };
})();
