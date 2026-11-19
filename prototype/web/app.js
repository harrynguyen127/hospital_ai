// Giao diện theo artifact "Trợ lý Hồ sơ EMR". Dữ liệu lấy từ API của server.py (giả lập).
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const norm = (s) => String(s).toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/đ/g, "d");

// Mở trực tiếp file (file://) thì không có server: dùng API giả lập trong trình duyệt (mock-api.js).
// Nếu gọi server thất bại vì không kết nối được, cũng chuyển sang giả lập cho cả phiên.
let USE_MOCK = location.protocol === "file:";
async function api(path, body) {
  if (!USE_MOCK) {
    const opt = body === undefined ? {} : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
    let r = null;
    try { r = await fetch(path, opt); }
    catch (e) { USE_MOCK = true; }
    if (r) {
      const d = await r.json();
      if (!r.ok) throw new Error(d.error || r.statusText);
      return d;
    }
  }
  return window.MockServer.call(path, body);
}

// Giờ đọc trực tiếp từ chuỗi ISO (+07:00), không phụ thuộc múi giờ của máy
const wall = (iso) => ({ day: iso.slice(0, 10), date: iso.slice(8, 10) + "/" + iso.slice(5, 7), time: iso.slice(11, 16) });
const fmtT = (iso) => (iso ? wall(iso).date + " " + wall(iso).time : "—");
const ms = (iso) => Date.parse(iso);
const sleep = (t) => new Promise((r) => setTimeout(r, t));

const S = { clock: null, users: [], patients: [], user: null, pt: null, detail: null, form: null,
  view: "r", open: innerWidth > 600, rscope: "pt", tasks: [], draft: {}, ai: {}, voice: { st: "idle", segs: [] }, rules: null, chat: [] };

const me = () => S.users.find((u) => u.id === S.user) || {};
const RN = { bac_si: "Bác sĩ", dieu_duong: "Điều dưỡng" };

// Thời hạn và trạng thái hiển thị
function urg(due, status) {
  if (!due) return { c: "soon", t: "Đang chờ" };
  const d = ms(due) - ms(S.clock), a = Math.abs(d) / 6e4, h = Math.floor(a / 60), m = Math.round(a % 60);
  const len = (h ? h + " giờ " : "") + (m ? m + " phút" : "");
  if (status === "quá hạn" || d < 0) return { c: "late", t: "Quá hạn " + (len || "0 phút") };
  if (wall(due).day === wall(S.clock).day) return { c: "soon", t: "Còn " + len };
  return { c: "later", t: "Hạn " + fmtT(due) };
}

// ===== Khung trên, đồng hồ, tài khoản =====
function renderTop() {
  $("clock").textContent = fmtT(S.clock);
  $("acct").innerHTML = S.users.map((u) => `<option value="${esc(u.id)}" ${u.id === S.user ? "selected" : ""}>${esc(u.label)}</option>`).join("");
}
async function setClock(minutes) {
  await api("/api/clock", { minutes });
  await refreshAll();
  toast(`Giờ mô phỏng: ${fmtT(S.clock)}`);
}

// ===== Danh sách bệnh nhân =====
function renderList() {
  $("emr").innerHTML = `<div class="crumb"><h1>Bệnh nhân nội trú</h1></div>
    <div class="tablebox"><table><thead><tr><th>Mã BN</th><th>Giường</th><th>Bác sĩ điều trị</th><th>Điều dưỡng phụ trách</th><th>Việc chờ</th></tr></thead><tbody>
    ${S.patients.map((p) => `<tr data-pid="${esc(p.patient_id)}" tabindex="0"><td class="mono">${esc(p.patient_id)}</td><td class="mono">${esc(p.bed)}</td><td>${esc(p.doctor)}</td><td>${esc(p.nurse)}</td>
      <td>${p.open ? `<span class="pill ${p.overdue ? "late" : "soon"}">${p.open} việc${p.overdue ? `, ${p.overdue} quá hạn` : ""}</span>` : '<span class="pill okp">Không có</span>'}</td></tr>`).join("")}
    </tbody></table></div>
    <p class="note">Bấm một bệnh nhân để mở hồ sơ. Đổi tài khoản ở góc trên để xem nhắc việc của bác sĩ hoặc điều dưỡng. Dùng +15 phút, +1 giờ để xem nhắc việc chạy theo thời gian.</p>`;
  document.querySelectorAll("tr[data-pid]").forEach((tr) => {
    tr.onclick = () => openPatient(tr.dataset.pid);
    tr.onkeydown = (e) => { if (e.key === "Enter") openPatient(tr.dataset.pid); };
  });
}

// ===== Hồ sơ bệnh nhân: tab theo phiếu =====
async function openPatient(pid, formId) {
  resetVoice();
  S.pt = pid;
  S.detail = await api("/api/patient?id=" + encodeURIComponent(pid));
  if (formId) S.form = formId;
  else if (!S.detail.forms.some((f) => f.form_id === S.form)) S.form = S.detail.forms[0] ? S.detail.forms[0].form_id : null;
  S.draft = {}; S.ai = {};
  renderPatient();
  renderPanel();
  if (innerWidth <= 600 && formId) setOpen(false);
}

function renderPatient() {
  const d = S.detail, p = d.patient;
  const admit = (p.events || []).find((e) => e.event === "admission");
  const f = d.forms.find((x) => x.form_id === S.form) || d.forms[0];
  if (f) S.form = f.form_id;
  const dueSet = new Set(d.forms.filter((x) => x.tasks.length).map((x) => x.form_id));
  $("emr").innerHTML = `<div class="crumb"><button class="link" id="back" type="button">Danh sách</button><h1>${esc(p.patient_id)}</h1></div>
    <div class="chart-h"><span><b>${esc(p.name)}</b></span><span>Giường <span class="mono">${esc(p.bed)}</span></span><span>${esc(p.doctor)} · ${esc(p.nurse)}</span>
      ${admit ? `<span>Vào viện <span class="mono">${fmtT(admit.at)}</span></span>` : ""}<span class="muted">Bộ luật ${esc(d.ruleset_version || "—")}</span></div>
    <div><div class="tabs">${d.forms.map((x) => `<button type="button" class="tab ${x.form_id === S.form ? "on" : ""}" data-f="${esc(x.form_id)}">${dueSet.has(x.form_id) ? '<i class="dot" aria-label="Có việc chờ"></i>' : ""}${esc(x.title)}</button>`).join("") || '<span class="tab">Không có phiếu nào</span>'}</div>
    ${f ? formBlock(f) : ""}</div>`;
  $("back").onclick = () => { resetVoice(); S.pt = null; S.detail = null; refreshAll(); };
  document.querySelectorAll(".tab[data-f]").forEach((b) => (b.onclick = () => { resetVoice(); S.form = b.dataset.f; S.draft = {}; S.ai = {}; renderPatient(); renderPanel(); }));
  document.querySelectorAll(".fields [name]").forEach((el) => (el.oninput = () => {
    S.draft[el.name] = el.type === "number" && el.value !== "" ? Number(el.value) : el.value;
    const wrapper = el.closest(".f");
    if (S.ai[el.name]) {
      delete S.ai[el.name];
      wrapper.classList.remove("ai");
      wrapper.querySelector("small")?.remove();
    }
    wrapper.classList.toggle("reqmiss", el.getAttribute("aria-required") === "true" && !el.value.trim());
    $("completeness").innerHTML = completeness(f);
    if (S.view === "v" && S.voice.st === "review") renderVoice();
  }));
  const fill = $("fill-sample");
  if (fill) fill.onclick = () => {
    let added = 0;
    for (const field of f.fields) {
      if (String(S.draft[field.field_id] ?? "").trim()) continue;
      const value = field.ui === "datetime" ? S.clock.slice(0, 16) : field.example;
      if (value === undefined) continue;
      S.draft[field.field_id] = value;
      added++;
    }
    renderPatient();
    renderPanel();
    toast(added ? `Đã điền thử ${added} ô trống. Bản nháp đang chờ kiểm tra.` : "Các ô có dữ liệu mẫu đã được điền.");
  };
  const save = $("save");
  if (save) save.onclick = saveRecord;
  const vo = $("voice-open");
  if (vo) vo.onclick = () => { S.view = "v"; setOpen(true); };
}

function completeness(form) {
  const empty = form.fields.filter((x) => (x.required || form.required.includes(x.field_id)) && !String(S.draft[x.field_id] ?? "").trim());
  return empty.length ? `<div class="reqwarn">Còn trống ${empty.length} trường bắt buộc: ${esc(empty.map((x) => x.label).join(", "))}. Vẫn lưu được, nhắc việc sẽ tiếp tục.</div>` : '<div class="reqok">Đã đủ trường bắt buộc.</div>';
}

function fieldControl(x, required) {
  const id = esc(x.field_id), value = S.draft[x.field_id] ?? "";
  const attrs = `id="f-${id}" name="${id}" aria-required="${required}"`;
  const cls = [S.ai[x.field_id] ? "ai" : "", required && !String(value).trim() ? "reqmiss" : ""].join(" ");
  const hint = x.example === undefined ? "" : `placeholder="Ví dụ: ${esc(x.example)}"`;
  let control;
  if (x.ui === "select") {
    control = `<select ${attrs}><option value="">Chọn…</option>${x.options.map((v) => `<option${v === value ? " selected" : ""}>${esc(v)}</option>`).join("")}</select>`;
  } else if (x.ui === "textarea") {
    control = `<textarea ${attrs} rows="2" ${hint}>${esc(value)}</textarea>`;
  } else {
    const type = x.ui === "datetime" ? "datetime-local" : x.ui === "number" ? "number" : "text";
    const limits = ["min", "max"].filter((key) => x[key] !== undefined).map((key) => `${key}="${esc(x[key])}"`).join(" ");
    control = `<input ${attrs} type="${type}" value="${esc(value)}" ${hint} ${type === "number" ? 'step="any"' : ""} ${limits}>`;
  }
  const measure = [x.min !== undefined && x.max !== undefined ? `${x.min}–${x.max}` : "", x.unit].filter(Boolean).join(" ");
  return `<div class="f ${cls}"><label for="f-${id}">${esc(x.label)}${measure ? ` (${esc(measure)})` : ""}${required ? '<span class="req" aria-hidden="true">*</span>' : ""}</label>${control}
    ${S.ai[x.field_id] ? "<small>Nháp từ giọng nói</small>" : ""}</div>`;
}

function formBlock(f) {
  const groups = new Map();
  for (const field of f.fields) {
    const group = field.group || "Nội dung phiếu";
    if (!groups.has(group)) groups.set(group, []);
    groups.get(group).push(fieldControl(field, !!field.required || f.required.includes(field.field_id)));
  }
  const inputs = [...groups].map(([group, fields]) => `<fieldset><legend>${esc(group)}</legend><div class="fields">${fields.join("")}</div></fieldset>`).join("");
  const rules = f.rules.map((r) => `<div class="rulebox"><span><b>${esc(r.clause)}</b> · ${esc(r.schedule)}</span><span class="src">“${esc(r.evidence)}”</span></div>`).join("");
  const tasks = f.tasks.map((t) => {
    const u = urg(t.due, t.status);
    return `<div class="item"><span class="nm"><span>${esc(t.note || t.kind)}${t.missing_fields.length ? " · thiếu " + esc((t.missing_labels || t.missing_fields).join(", ")) : ""}</span><span class="why">${esc(t.role === "bac_si" ? "Bác sĩ" : "Điều dưỡng")}</span></span><span class="pill ${u.c}">${u.t}</span></div>`;
  }).join("");
  const hist = f.records.slice(0, 5).map((r) => `<details class="record"><summary><b class="mono">${fmtT(r.at)}</b> · ${esc(r.record_id)} · ${esc(S.users.find((u) => u.id === r.user)?.label || r.user || "Tài khoản mô phỏng")}</summary><dl>
    ${f.fields.filter((x) => r.values[x.field_id] !== undefined).map((x) => `<div><dt>${esc(x.label)}</dt><dd>${esc(r.values[x.field_id])} ${esc(x.unit || "")}</dd></div>`).join("") || "<div>Chưa nhập nội dung.</div>"}</dl></details>`).join("");
  return `<div class="form">
    <div class="form-h"><h2>${esc(f.title)}</h2>${VOICE[f.form_id] ? `<button class="btn ghost sm" id="voice-open" type="button">Nhập bằng giọng nói</button>` : ""}</div>
    ${rules}${tasks ? `<div class="sec-h">Việc đang chờ</div>${tasks}` : '<p class="note">Không có việc đang chờ cho phiếu này.</p>'}
    <div class="form-h"><b>Nội dung phiếu <span class="muted">· ${f.fields.length} trường</span></b><button class="btn ghost sm" id="fill-sample" type="button">Điền mẫu vào ô trống</button></div>
    <div class="ba">${inputs}</div>
    ${hist ? `<div class="hist"><div class="sec-h">Các lần lưu gần nhất</div>${hist}</div>` : ""}
    <div class="savebar"><div id="completeness" aria-live="polite">${completeness(f)}</div>
      <button class="btn" id="save" type="button">Lưu bản ghi</button></div>
  </div>`;
}

async function saveRecord() {
  const f = S.detail.forms.find((x) => x.form_id === S.form);
  const values = {};
  for (const el of document.querySelectorAll(".fields [name]")) {
    if (!el.reportValidity()) return;
    if (el.value.trim()) values[el.name] = el.type === "number" ? Number(el.value) : el.value.trim();
  }
  $("save").disabled = true;
  try {
    const src = Object.keys(S.ai).length ? "voice" : "emr";
    const r = await api("/api/records", { patient_id: S.pt, form_id: S.form, values, user: S.user, source: src });
    const miss = r.record.missing_required;
    toast(miss.length ? `Đã lưu, còn thiếu: ${miss.map((id) => f.fields.find((x) => x.field_id === id)?.label || id).join(", ")}` : "Đã lưu bản ghi đầy đủ.");
    resetVoice(); S.draft = {}; S.ai = {};
    await refreshAll();
  } catch (e) { toast("Lỗi: " + e.message); }
  finally { if ($("save")) $("save").disabled = false; }
}

// ===== Trợ lý nổi: nhắc việc =====
function renderBubble() {
  const n = S.tasks.length, late = S.tasks.filter((t) => t.status === "quá hạn");
  $("count").textContent = n;
  $("bubble").classList.toggle("rec", S.voice.st === "listening");
  $("blabel").innerHTML = S.voice.st === "listening" ? '<i class="dot-rec"></i> Đang nghe' : "Trợ lý";
  $("nudge").hidden = S.open || !late.length || S.voice.st !== "idle";
  if (late.length) $("nudge").innerHTML = `<span class="pill late">Quá hạn</span><br><b>${esc(late[0].patient_id)}</b> · ${esc(late[0].form_title)}`;
}

function renderPanel() {
  renderBubble();
  $("panel").hidden = !S.open;
  $("tabR").classList.toggle("on", S.view === "r");
  $("tabQ").classList.toggle("on", S.view === "q");
  $("tabV").classList.toggle("on", S.view === "v");
  $("askwrap").hidden = S.view !== "q";
  const c = $("ctx");
  c.hidden = !S.pt;
  if (S.pt) {
    const k = S.tasks.filter((t) => t.patient_id === S.pt).length;
    c.innerHTML = `<span>Đang mở <b class="mono">${esc(S.pt)}</b></span><span>${k ? `Còn ${k} việc` : "Không còn việc"}</span>`;
  }
  ({ r: renderReminders, q: renderChat, v: renderVoice })[S.view]();
}

function renderReminders() {
  const b = $("pbody");
  const scoped = S.pt && S.rscope === "pt";
  const list = scoped ? S.tasks.filter((t) => t.patient_id === S.pt) : S.tasks;
  const bar = S.pt ? `<div class="rtabs"><button type="button" data-s="pt" class="${scoped ? "on" : ""}">${esc(S.pt)} <span>${S.tasks.filter((t) => t.patient_id === S.pt).length}</span></button><button type="button" data-s="all" class="${scoped ? "" : "on"}">Tất cả bệnh nhân <span>${S.tasks.length}</span></button></div>` : "";
  const byPt = {};
  list.forEach((t) => { (byPt[t.patient_id] = byPt[t.patient_id] || []).push(t); });
  const late = list.filter((t) => t.status === "quá hạn").length;
  b.innerHTML = bar + `<div class="rolebar">Việc của <b>${esc(RN[me().role] || "")}</b> · ${esc(me().label || "")}</div>
    <div class="summary"><span class="pill late">${late} quá hạn</span><span class="pill soon">${list.length - late} còn lại</span></div>
    ${Object.keys(byPt).length ? Object.entries(byPt).map(([pid, ts]) => `<div class="pt"><div class="pt-h"><b class="mono">${esc(pid)}</b><span class="dx">${esc(ts[0].patient)}</span></div>
      ${ts.map((t) => { const u = urg(t.due, t.status); return `<button type="button" class="item" data-p="${esc(pid)}" data-f="${esc(t.form_id)}"><span class="nm"><span>${esc(t.form_title)}</span><span class="why">${esc(t.clause)}${t.note ? " · " + esc(t.note) : ""}${t.missing_fields.length ? " · thiếu " + esc((t.missing_labels || t.missing_fields).join(", ")) : ""}</span></span><span class="pill ${u.c}">${u.t}</span></button>`; }).join("")}</div>`).join("") : '<div class="empty-state">Không còn việc nào cho tài khoản này.</div>'}`;
  b.querySelectorAll("[data-s]").forEach((x) => (x.onclick = () => { S.rscope = x.dataset.s; renderPanel(); }));
  b.querySelectorAll(".item").forEach((x) => (x.onclick = () => openPatient(x.dataset.p, x.dataset.f)));
}

// ===== Hỏi đáp: tra việc, hồ sơ và bộ luật đang áp dụng =====
const CHIPS = ["BN-02 còn thiếu gì?", "Tôi cần làm gì hôm nay?", "Đánh giá đau khi nào?", "Quy định về sinh tồn sau mổ?"];
const STOP = new Set("la gi cua co cho va khi nao bao nhieu the nao thi can phai duoc khong toi em anh chi bac si quy dinh nhung hay o trong ve voi nhu mot cac can hom nay".split(" "));
const toks = (s) => norm(s).split(/[^a-z0-9]+/).filter((t) => t.length > 2 && !STOP.has(t));

async function ask(q) {
  q = q.trim();
  if (!q) return;
  S.chat.push({ me: q });
  S.view = "q";
  const n = norm(q);
  const p = S.patients.find((x) => n.includes(x.patient_id.toLowerCase()));
  let html;
  const current = S.detail?.forms.find((f) => f.form_id === S.form);
  if (S.pt && current && !p && n.includes("phieu dang mo")) {
    const record = current.records[0];
    const draft = n.includes("nhap");
    const values = draft ? S.draft : record?.values || {};
    const entries = current.fields.filter((field) => String(values[field.field_id] ?? "").trim());
    const rows = entries.map((field) => `<div><b>${esc(field.label)}</b> · ${esc(values[field.field_id])} ${esc(field.unit || "")}</div>`).join("");
    const source = draft ? "Bản nháp đang nhập" : record ? "Bản ghi " + record.record_id + " · " + fmtT(record.at) : "Chưa có bản ghi";
    html = `<b>${esc(S.pt)} · ${esc(current.title)}</b><div class="src">${esc(source)}</div>${rows || "Chưa có nội dung."}`;
  } else if (p) {
    const d = await api("/api/patient?id=" + encodeURIComponent(p.patient_id));
    const ts = d.forms.flatMap((f) => f.tasks.map((t) => ({ ...t, form_title: f.title, form_id: f.form_id })));
    html = ts.length
      ? `<div class="ans-lead"><b class="mono">${esc(p.patient_id)}</b> còn ${ts.length} việc:</div>` + ts.slice(0, 6).map((t) => `<button type="button" class="item" data-p="${esc(p.patient_id)}" data-f="${esc(t.form_id)}"><span>${esc(t.form_title)}${t.missing_fields.length ? " · thiếu " + esc((t.missing_labels || t.missing_fields).join(", ")) : ""}</span><span class="pill ${urg(t.due, t.status).c}">${urg(t.due, t.status).t}</span></button>`).join("") + `<div class="src">Nguồn: trạng thái hồ sơ và bộ luật ${esc(d.ruleset_version)}</div>`
      : `<div class="ans-lead"><b class="mono">${esc(p.patient_id)}</b> không còn việc nào.</div>`;
  } else if (/viec|lam gi|nhac|hom nay/.test(n)) {
    html = S.tasks.length
      ? `<div class="ans-lead">${S.tasks.length} việc của ${esc(me().label)}:</div>` + S.tasks.slice(0, 6).map((t) => `<button type="button" class="item" data-p="${esc(t.patient_id)}" data-f="${esc(t.form_id)}"><span>${esc(t.patient_id)} · ${esc(t.form_title)}</span><span class="pill ${urg(t.due, t.status).c}">${urg(t.due, t.status).t}</span></button>`).join("")
      : '<div class="ans-lead">Không có việc nào cho tài khoản này.</div>';
  } else {
    S.rules = S.rules || (await api("/api/rules")).rules;
    const qt = toks(q);
    const hits = S.rules.map((r) => ({ r, s: toks(r.evidence + " " + r.form_title).filter((t) => qt.includes(t)).length }))
      .filter((x) => x.s >= 2).sort((a, b) => b.s - a.s).slice(0, 2).map((x) => x.r);
    html = hits.length
      ? `<div class="ans-lead">Theo bộ luật đang áp dụng:</div>` + hits.map((r) => `<div class="quote"><div>${esc(r.evidence)}</div><div class="src">${esc(r.clause)} · ${esc(r.form_title)}</div></div>`).join("")
      : `<div class="none">Không tìm thấy nội dung này trong bộ luật đang áp dụng, nên trợ lý không trả lời để tránh suy đoán.</div>`;
  }
  S.chat.push({ html });
  renderPanel();
}
function renderChat() {
  const b = $("pbody");
  b.innerHTML = S.chat.length
    ? `<div class="chat">${S.chat.map((m) => (m.me ? `<div class="msg me">${esc(m.me)}</div>` : `<div class="msg ai">${m.html}</div>`)).join("")}</div>`
    : `<div class="chat-empty"><b>Hỏi bằng lời thường, như hỏi đồng nghiệp.</b><span>Trợ lý đọc trạng thái hồ sơ và tra bộ luật đang áp dụng, rồi trả lời kèm nguồn.</span></div>`;
  const chips = S.pt ? ["Xem bản nháp phiếu đang mở", "Xem lần lưu cuối của phiếu đang mở", ...CHIPS] : CHIPS;
  $("chips").innerHTML = chips.map((c) => `<button type="button">${esc(c)}</button>`).join("");
  $("chips").querySelectorAll("button").forEach((x) => (x.onclick = () => ask(x.textContent)));
  b.querySelectorAll(".item").forEach((x) => (x.onclick = () => openPatient(x.dataset.p, x.dataset.f)));
  b.scrollTop = b.scrollHeight;
}

// ===== Giọng nói: kịch bản mẫu, đi qua trích xuất đã che định danh =====
const VOICE = window.VOICE_SAMPLES;

function resetVoice() { S.voice = { st: "idle", segs: [] }; }

function voiceShortcuts() {
  return `<div class="voice-samples"><div class="sec-h">Chọn buổi mẫu</div>${Object.entries(VOICE).filter(([id]) => !S.detail || S.detail.forms.some((f) => f.form_id === id)).map(([id, sample]) =>
    `<button type="button" class="item" data-voice-form="${esc(id)}"><span class="nm"><b>${esc(sample.title)}</b><span class="why">${esc(sample.description)}</span></span><span class="mono">${sample.segments.length} câu</span></button>`).join("")}</div>`;
}

function bindVoiceShortcuts() {
  $("pbody").querySelectorAll("[data-voice-form]").forEach((el) => (el.onclick = async () => {
    const pid = S.pt || S.patients[0]?.patient_id;
    if (!pid) return;
    try {
      const detail = S.detail || await api("/api/patient?id=" + encodeURIComponent(pid));
      if (!detail.forms.some((f) => f.form_id === el.dataset.voiceForm)) {
        toast("Bộ quy định hiện tại chưa mở phiếu này.");
        return;
      }
      S.view = "v";
      await openPatient(pid, el.dataset.voiceForm);
      setOpen(true);
    } catch (e) { toast("Không mở được buổi mẫu: " + e.message); }
  }));
}

function voiceLines(lines) {
  return `<div class="lines">${lines.map((l) => `<div class="ln ${l.out ? "pii" : ""}"><span class="who">${esc(l.who)}</span><span class="tx">${l.out ? '<span class="drop">Câu ngoài lề, đã bỏ</span>' : esc(l.masked)}${l.pii ? ' <span class="tag pii">Đã che định danh</span>' : ""}</span></div>`).join("")}</div>`;
}

// ===== Thử micro thật: ghi âm -> WAV 16kHz -> /api/voice/audio, hiển thị từng bước để quan sát =====
const MIC = { stream: null, ctx: null, node: null, chunks: [], t0: 0, timer: null };
// STT_NAME: tạm tắt Cloud STT Blaze.vn, chỉ chạy local PhoWhisper
const STT_NAME = {
  // blaze: "Blaze.vn Cloud STT",
  phowhisper: "PhoWhisper-small (local)",
  none: "— (VAD chặn, không gọi STT)",
};

async function micStart() {
  if (USE_MOCK) { toast("Thử micro cần chạy qua server (python server.py), không dùng file://"); return; }
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) { toast("Trình duyệt không hỗ trợ micro (cần http://127.0.0.1)"); return; }
  try {
    MIC.stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true } });
  } catch (e) { toast("Không mở được micro: " + e.message); return; }
  MIC.ctx = new (window.AudioContext || window.webkitAudioContext)();
  const src = MIC.ctx.createMediaStreamSource(MIC.stream);
  MIC.node = MIC.ctx.createScriptProcessor(4096, 1, 1);
  MIC.chunks = [];
  MIC.node.onaudioprocess = (e) => {
    const d = new Float32Array(e.inputBuffer.getChannelData(0));
    MIC.chunks.push(d);
    let s = 0; for (let i = 0; i < d.length; i++) s += d[i] * d[i];
    const lv = $("miclvl");
    if (lv) lv.style.width = Math.min(100, Math.sqrt(s / d.length) * 400) + "%";
  };
  src.connect(MIC.node); MIC.node.connect(MIC.ctx.destination);
  MIC.t0 = Date.now();
  S.voice = { st: "mic_rec", segs: [] };
  renderPanel();
  MIC.timer = setInterval(() => {
    const secs = (Date.now() - MIC.t0) / 1000;
    const t = $("mictime");
    if (t) t.textContent = secs.toFixed(1) + " / 60 giây";
    if (secs >= 60) micStop();
  }, 200);
}

function encodeWav16k(chunks, srcRate) {
  let len = 0; chunks.forEach((c) => (len += c.length));
  const all = new Float32Array(len); let o = 0; chunks.forEach((c) => { all.set(c, o); o += c.length; });
  const ratio = srcRate / 16000, n = Math.floor(all.length / ratio);
  const pcm = new Int16Array(n);
  for (let i = 0; i < n; i++) {
    const x = i * ratio, i0 = Math.floor(x), i1 = Math.min(i0 + 1, all.length - 1), f = x - i0;
    const v = Math.max(-1, Math.min(1, all[i0] * (1 - f) + all[i1] * f));
    pcm[i] = v < 0 ? v * 0x8000 : v * 0x7fff;
  }
  const buf = new ArrayBuffer(44 + pcm.length * 2), dv = new DataView(buf);
  const w = (p, s) => { for (let i = 0; i < s.length; i++) dv.setUint8(p + i, s.charCodeAt(i)); };
  w(0, "RIFF"); dv.setUint32(4, 36 + pcm.length * 2, true); w(8, "WAVEfmt "); dv.setUint32(16, 16, true);
  dv.setUint16(20, 1, true); dv.setUint16(22, 1, true); dv.setUint32(24, 16000, true); dv.setUint32(28, 32000, true);
  dv.setUint16(32, 2, true); dv.setUint16(34, 16, true); w(36, "data"); dv.setUint32(40, pcm.length * 2, true);
  new Int16Array(buf, 44).set(pcm);
  return new Uint8Array(buf);
}
function toB64(bytes) { let s = ""; for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000)); return btoa(s); }

async function micStop() {
  clearInterval(MIC.timer);
  const rate = MIC.ctx.sampleRate, secs = (Date.now() - MIC.t0) / 1000;
  MIC.node.disconnect(); MIC.stream.getTracks().forEach((t) => t.stop()); MIC.ctx.close();
  S.voice = { st: "mic_proc", segs: [] };
  renderPanel();
  try {
    const wav = encodeWav16k(MIC.chunks, rate);
    const r = await api("/api/voice/audio", { form_id: S.form, audio_b64: toB64(wav) });
    S.voice = { st: "mic_res", r, secs, segs: [] };
    if (r.extracted && Object.keys(r.extracted).length) {
      S.draft = { ...S.draft, ...r.extracted };
      Object.keys(r.extracted).forEach((k) => { S.ai[k] = true; });
      renderPatient();
    }
  } catch (e) { S.voice = { st: "mic_res", r: { error: e.message }, secs, segs: [] }; }
  renderPanel();
}

function micResultHtml(v) {
  const r = v.r || {};
  if (r.error) return `<div class="vx"><div class="none">Lỗi: ${esc(r.error)}</div><button type="button" class="btn ghost" id="vreset">Thử lại</button></div>`;
  const ok = (b) => `<span class="pill ${b ? "okp" : "late"}">${b ? "✓" : "✗"}</span>`;
  const segs = (r.segments || []).map((s) => s[0] + "–" + s[1] + "s").join(", ") || "không có";
  const fields = (S.detail.forms.find((f) => f.form_id === S.form) || { fields: [] }).fields || [];
  const label = (id) => (fields.find((f) => f.field_id === id) || {}).label || id;
  const ex = Object.entries(r.extracted || {});
  return `<div class="vx"><ul class="steps">
    <li class="done"><span class="st">1</span><span><b>Ghi âm</b>: ${v.secs.toFixed(1)} giây</span></li>
    <li class="done"><span class="st">2</span><span><b>VAD</b> ${ok(r.has_speech)} đoạn có tiếng nói: ${esc(segs)}</span></li>
    <li class="${r.stt_backend && r.stt_backend !== "none" && !(r.stt_error && !r.transcript_len) ? "done" : "err"}"><span class="st">3</span><span><b>STT</b>: ${esc(r.stt_error && !r.transcript_len ? "THẤT BẠI" : (STT_NAME[r.stt_backend] || r.stt_backend))}${r.stt_error ? `<br><span class="muted small">${esc(r.stt_error)}</span>` : ""}</span></li>
    <li class="done"><span class="st">4</span><span><b>Che PII</b>: ${r.pii_masked ?? 0} chỗ<br><span class="small">${r.masked ? esc(r.masked) : '<span class="muted">(chưa có văn bản)</span>'}</span></span></li>
    <li class="done"><span class="st">5</span><span><b>Trích xuất</b>: ${r.source === "local" ? "Local tại máy (100% offline)" : "—"}${r.out_of_scope ? "<br><span class=\"muted small\">Câu ngoài lề, đã bỏ</span>" : ""}</span></li>
  </ul>
  <div class="sec-h">Điền nháp (${ex.length} ô)</div>
  ${ex.length ? `<div class="lines">${ex.map(([k, val]) => `<div class="ln"><span class="who">${esc(label(k))}</span><span class="tx mono">${esc(val)}</span></div>`).join("")}</div>` : '<div class="none">Không trích xuất được ô nào. Hãy đọc rõ tên chỉ số kèm số, ví dụ "mạch 88, huyết áp 120 trên 80".</div>'}
  <button type="button" class="btn ghost" id="vreset">Ghi lại</button></div>`;
  // [TẠM TẮT - HYBRID] Dòng bước 5 cũ khi dùng Cloud LLM:
  // `<li class="done"><span class="st">5</span><span><b>Trích xuất</b>: ${r.source === "api" ? "Cloud LLM (voice.send)" : r.source === "local" ? "Local fallback" : "—"} · slot voice.send: ${esc(r.send_mode || "?")}</span></li>`
}

function renderVoice() {
  const b = $("pbody"), v = S.voice, sample = VOICE[S.form];
  if (!S.pt) {
    b.innerHTML = `<div class="vx"><div class="none">Mở một bệnh nhân và một phiếu để nhập bằng giọng nói. Chọn buổi mẫu bên dưới để mở hồ sơ đầu tiên.</div>${voiceShortcuts()}</div>`;
    bindVoiceShortcuts(); return;
  }
  if (v.st === "mic_rec") {
    b.innerHTML = `<div class="vx"><div class="live"><i class="dot-rec"></i> Đang ghi âm từ micro <span class="mono" id="mictime">0.0 / 60 giây</span></div>
      <div style="height:10px;background:var(--surface-2);border:1px solid var(--line);border-radius:5px;overflow:hidden"><div id="miclvl" style="height:100%;width:0;background:var(--ok)"></div></div>
      <p class="hint">Thanh xanh nhảy khi micro nghe được tiếng. Hỗ trợ ghi tối đa 60 giây (tự chia đoạn ≤ 28s cho PhoWhisper local).</p>
      <button type="button" class="bigbtn" id="micstop">Dừng và xử lý</button></div>`;
    $("micstop").onclick = micStop;
    return;
  }
  if (v.st === "mic_proc") { b.innerHTML = '<div class="vx"><div class="live">Đang xử lý: VAD → STT → che PII → trích xuất…</div></div>'; return; }
  if (v.st === "mic_res") { b.innerHTML = micResultHtml(v); $("vreset").onclick = () => { resetVoice(); renderPanel(); }; return; }
  if (v.st === "idle") {
    b.innerHTML = `<div class="vx"><div class="target">Sẽ điền vào <b class="mono">${esc(S.pt)}</b> · <b>${esc((S.detail.forms.find((f) => f.form_id === S.form) || {}).title)}</b></div>
      <button type="button" class="bigbtn" id="micstart">🎤 Ghi âm từ micro (thật)</button>
      ${sample
        ? `<p class="note">${esc(sample.description)} (${sample.segments.length} câu)</p>
           <button type="button" class="btn ghost" id="vstart">Bắt đầu nghe (kịch bản mẫu)</button>
           <p class="hint">Micro thật: âm thanh qua VAD → STT → che PII → trích xuất. Hoặc chạy kịch bản mẫu đóng vai. Kết quả chỉ là nháp, cần kiểm tra và bấm lưu.</p>
           <ol class="voice-guide"><li>Phát hội thoại theo từng người nói.</li><li>Che tên, số điện thoại và số giấy tờ; bỏ câu ngoài lề.</li><li>Trích xuất theo các ô của phiếu đang mở.</li><li>Kiểm tra, sửa và lưu bản ghi.</li></ol>`
        : '<div class="none">Phiếu này chưa có kịch bản mẫu để thử.</div>'}${voiceShortcuts()}</div>`;
    $("micstart").onclick = micStart;
    const s = $("vstart");
    if (s) s.onclick = () => voiceRun(sample);
    bindVoiceShortcuts();
  } else if (v.st === "listening") {
    b.innerHTML = `<div class="vx"><div class="live" role="status"><i class="dot-rec"></i> Đang nghe · ${v.segs.length}/${v.total} câu</div>
      ${v.segs.length ? voiceLines(v.segs) : '<p class="hint">Đang chờ người nói…</p>'}
      <button type="button" class="bigbtn stop" id="vstop" ${v.segs.length ? "" : "disabled"}>Dừng và xử lý</button>
      <button type="button" class="btn ghost" id="vcancel">Hủy, không xử lý</button></div>`;
    $("vstop").onclick = () => voiceProcess(v);
    $("vcancel").onclick = () => { resetVoice(); renderPanel(); };
  } else if (v.st === "processing") {
    b.innerHTML = `<div class="vx"><ul class="steps" aria-label="Tiến trình xử lý">${v.steps.map((s) => `<li class="${s.s}"><span class="st">${s.s === "done" ? "✓" : ""}</span><span>${esc(s.t)}</span></li>`).join("")}</ul>
      <button type="button" class="btn ghost" id="vcancel">Hủy, không xử lý</button></div>`;
    $("vcancel").onclick = () => { resetVoice(); renderPanel(); };
  } else if (v.st === "error") {
    b.innerHTML = `<div class="vx"><div class="none" role="alert">${esc(v.error)}</div><button type="button" class="btn ghost" id="vreset">Thử lại buổi mẫu</button></div>`;
    $("vreset").onclick = () => { resetVoice(); renderPanel(); };
  } else {
    const form = S.detail.forms.find((f) => f.form_id === S.form);
    const required = form.fields.filter((f) => f.required || form.required.includes(f.field_id));
    const missing = required.filter((f) => !String(S.draft[f.field_id] ?? "").trim());
    b.innerHTML = `<div class="vx"><div class="pills"><span class="pill aip">${v.filled} ô điền nháp</span><span class="pill late">${v.redacted} chỗ đã che định danh</span></div>
      <div class="hint">${v.lines.filter((l) => l.out).length} câu ngoài lề đã bỏ · Câu đọc lại cập nhật giá trị trước đó.</div>
      ${voiceLines(v.lines)}
      <div class="voice-result"><div class="sec-h">Kết quả trích xuất · chưa lưu</div>${Object.entries(v.draft).map(([key, value]) => `<div><span>${esc(form.fields.find((f) => f.field_id === key)?.label || key)}</span><b>${esc(value)}</b></div>`).join("") || '<p class="hint">Chưa nghe được giá trị phù hợp với ô nào.</p>'}</div>
      ${missing.length ? `<div class="reqwarn">Cần bổ sung: ${esc(missing.map((f) => f.label).join(", "))}.</div>` : '<div class="reqok">Đã đủ trường bắt buộc.</div>'}
      <p class="hint">Ô màu tím chứa giá trị từ hội thoại. Kiểm tra và sửa trên phiếu rồi bấm Lưu bản ghi.</p>
      <button type="button" class="btn ghost" id="vreset">Ghi buổi mới</button></div>`;
    $("vreset").onclick = () => { resetVoice(); renderPanel(); };
  }
}

async function voiceRun(sample) {
  const v = { st: "listening", segs: [], total: sample.segments.length, patient: S.pt, form: S.form };
  S.voice = v;
  renderPanel();
  try {
    for (const segment of sample.segments) {
      await sleep(900);
      if (S.voice !== v || v.st !== "listening") return;
      const r = await api("/api/voice", { text: segment.text, form_id: v.form });
      if (S.voice !== v || v.st !== "listening") return;
      v.segs.push({ who: segment.who, masked: r.masked, out: r.out_of_scope, pii: r.pii_masked, extracted: r.extracted });
      renderPanel();
    }
    await sleep(600);
    if (S.voice === v && v.st === "listening") await voiceProcess(v);
  } catch (e) {
    if (S.voice !== v || v.st !== "listening") return;
    v.st = "error"; v.error = "Không xử lý được hội thoại: " + e.message;
    renderPanel();
  }
}

async function voiceProcess(v) {
  if (S.voice !== v || v.st !== "listening") return;
  v.st = "processing";
  v.steps = [{ t: "Đã che định danh trước khi trích xuất", s: "done" }, { t: "Tổng hợp theo ô của phiếu, bỏ câu ngoài lề", s: "run" }, { t: "Điền nháp để người dùng kiểm tra", s: "wait" }];
  renderPanel();
  await sleep(450);
  if (S.voice !== v) return;
  const draft = {};
  v.segs.filter((l) => !l.out).forEach((l) => Object.assign(draft, l.extracted));
  v.steps[1].s = "done"; v.steps[2].s = "run";
  renderPanel();
  await sleep(450);
  if (S.voice !== v || S.pt !== v.patient || S.form !== v.form) return;
  S.draft = { ...S.draft, ...draft };
  Object.keys(draft).forEach((k) => { S.ai[k] = true; });
  S.voice = { st: "review", segs: [], lines: v.segs, draft, redacted: v.segs.reduce((n, l) => n + l.pii, 0), filled: Object.keys(draft).length };
  renderPatient();
  renderPanel();
}

// ===== Quản trị quy định (ngoài giao diện EMR, dành cho QLCL và kỹ thuật) =====
let ADMIN_TAB = "policy";
async function renderAdmin() {
  const body = $("adminbody");
  document.querySelectorAll("#admin [data-a]").forEach((b) => b.classList.toggle("on", b.dataset.a === ADMIN_TAB));
  if (ADMIN_TAB === "policy") {
    const rs = await api("/api/rulesets");
    const samples = (await api("/api/samples")).samples;
    window.SAMPLES = samples;
    body.innerHTML = `<p class="note">Luật qua kiểm tra được tự động áp dụng thành phiên bản bất biến, có thể hoàn tác.</p>
      <table><thead><tr><th>Phiên bản</th><th>Trạng thái</th><th>Hiệu lực từ</th><th>Số luật</th></tr></thead><tbody>
      ${rs.rulesets.slice().reverse().map((v) => `<tr><td><b>${esc(v.version)}</b></td><td class="${v.status === "active" ? "okp" : "muted"}">${esc(v.status)}</td><td>${esc(v.effective_from)}</td><td>${v.applied}</td></tr>`).join("")}</tbody></table>
      <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:8px"><select id="sample">${samples.map((s, i) => `<option value="${i}">${esc(s.label)}</option>`).join("")}</select>
        <button type="button" id="ana">Phân tích (chưa áp dụng)</button><button type="button" class="btn" id="pub">Nạp & tự động áp dụng</button><button type="button" id="rb">Hoàn tác phiên bản trước</button></div>
      <textarea id="ptext" rows="10" style="width:100%;font-family:var(--mono);font-size:12.5px">${esc(samples[0].text)}</textarea>
      <div id="pout" class="small"></div>`;
    $("sample").onchange = (e) => { $("ptext").value = samples[e.target.value].text; };
    $("ana").onclick = () => runIngest(true);
    $("pub").onclick = () => runIngest(false);
    $("rb").onclick = async () => {
      try { const r = await api("/api/policy/rollback", {}); toast("Đã hoàn tác, bộ luật hiện tại: " + r.active); }
      catch (e) { toast(e.message); }
      await refreshAll(); renderAdmin();
    };
  } else if (ADMIN_TAB === "detect") {
    body.innerHTML = `<p class="note">Thử nhận diện form từ màn hình: khớp chính xác, gần giống (tự tăng phiên bản) hoặc form mới (tự áp dụng nếu qua kiểm tra).</p>
      <div style="display:flex;gap:8px;flex-wrap:wrap"><button type="button" class="btn sm" data-d="exact">Màn hình đã biết</button><button type="button" class="btn sm" data-d="near">Bản EMR có thêm 1 trường</button><button type="button" class="btn sm" data-d="new">Màn hình chưa từng thấy</button></div><div id="dout" class="small"></div>`;
    body.querySelectorAll("[data-d]").forEach((b) => (b.onclick = () => runDetect(b.dataset.d)));
  } else {
    const a = await api("/api/audit");
    body.innerHTML = `<div class="log">${a.audit.map((x) => `<div><span class="muted small">${fmtT(x.at)}</span> <span class="pill later">${esc(x.kind)}</span> ${esc(x.detail)}</div>`).join("") || "Chưa có thay đổi."}</div>`;
  }
}
async function runIngest(dry) {
  try {
    const sample = (window.SAMPLES || [])[$("sample").value] || {};
    const res = await api("/api/policy/ingest", { doc_id: "QD-CHAMSOC-2026", doc_version: (sample.name || "").includes("v2") ? "v2" : "v1", text: $("ptext").value, effective_from: S.clock.slice(0, 10), dry_run: dry });
    const d = res.diff;
    $("pout").innerHTML = `<div>Tóm tắt: ${Object.entries(res.summary).map(([k, v]) => `${esc(k)} ${v}`).join(" · ")}</div>
      ${d.added.map((x) => `<div class="diff-add">+ ${esc(x.clause)}: ${esc(x.evidence)}</div>`).join("")}
      ${d.changed.map((x) => `<div class="diff-chg">~ ${esc(x.clause)} (${esc(x.changed_fields.join(", "))})</div>`).join("")}
      <div class="sec-h" style="margin-top:8px">Chạy thử tác động (số việc trước → sau)</div>
      ${Object.entries(res.impact).map(([u, v]) => `<div>${esc(u)}: ${v.before} → <b>${v.after}</b></div>`).join("")}
      <div class="muted">${dry ? "Chưa áp dụng." : "Đã áp dụng " + esc(res.published_version) + "."}</div>`;
    if (!dry) { toast("Đã áp dụng " + res.published_version); await refreshAll(); renderAdmin(); }
  } catch (e) { $("pout").innerHTML = `<span class="late">${esc(e.message)}</span>`; }
}
async function runDetect(kind) {
  try {
    const { forms } = await api("/api/forms");
    const known = forms.find((f) => f.form_id === "phieu_sinh_ton_nguoi_lon");
    const title = kind === "new" ? "Sàng lọc dinh dưỡng" : known.title;
    const fields = kind === "new" ? [
      { label: "Cân nặng (kg)", ui: "number", required: true },
      { label: "Ăn kém gần đây", ui: "checkbox" },
      { label: "Sụt cân không chủ ý", ui: "select", options: ["Có", "Không"] },
    ] : [...known.fields];
    if (kind === "near" && !fields.some((f) => f.label === "Ghi chú")) fields.push({ label: "Ghi chú", ui: "text" });
    const r = await api("/api/detect", { method: "dom", title, fields });
    $("dout").innerHTML = `<div>${esc(r.title)} → <code>${esc(r.form_id)}</code> (v${r.version})</div><div>Cách khớp: <span class="pill later">${esc(r.match)}</span> · ${esc(r.action)}</div>`;
    await refreshAll();
  } catch (e) { $("dout").innerHTML = `<span class="late">${esc(e.message)}</span>`; }
}

// ===== Tải lại toàn bộ dữ liệu =====
async function refreshAll() {
  const st = await api("/api/state");
  S.rules = null;
  S.clock = st.clock;
  S.patients = (await api("/api/patients")).patients;
  S.tasks = (await api("/api/tasks?user=" + encodeURIComponent(S.user))).tasks;
  renderTop();
  if (S.pt) {
    try { S.detail = await api("/api/patient?id=" + encodeURIComponent(S.pt)); renderPatient(); }
    catch (e) { S.pt = null; renderList(); }
  } else renderList();
  renderPanel();
}

function setOpen(v) { S.open = v; renderPanel(); }
function toast(t) {
  const e = $("toast");
  e.textContent = t;
  e.hidden = false;
  clearTimeout(toast.t);
  toast.t = setTimeout(() => (e.hidden = true), 3500);
}

// ===== Khởi tạo =====
async function init() {
  S.users = (await api("/api/users")).users;
  S.user = S.users[0].id;
  if (USE_MOCK) {
    const b = document.querySelector(".proto");
    if (b) b.textContent = "Bản mẫu thử nghiệm đang chạy giả lập trong trình duyệt (không cần server). Bệnh nhân, dữ liệu và văn bản quy định đều là dữ liệu giả. Trạng thái chỉ lưu trong trang này, tải lại sẽ về dữ liệu mặc định.";
  }
  $("acct").onchange = (e) => { resetVoice(); S.user = e.target.value; S.rules = null; refreshAll(); toast("Đã đăng nhập: " + me().label); };
  $("t15").onclick = () => setClock(15);
  $("t60").onclick = () => setClock(60);
  $("flowbtn").onclick = () => { $("flow").hidden = false; $("flowclose").focus(); };
  $("flowclose").onclick = () => ($("flow").hidden = true);
  $("flow").onclick = (e) => { if (e.target === $("flow")) $("flow").hidden = true; };
  $("adminbtn").onclick = () => { $("admin").hidden = false; renderAdmin(); };
  $("adminclose").onclick = () => ($("admin").hidden = true);
  $("admin").onclick = (e) => { if (e.target === $("admin")) $("admin").hidden = true; };
  document.querySelectorAll("#admin [data-a]").forEach((b) => (b.onclick = () => { ADMIN_TAB = b.dataset.a; renderAdmin(); }));
  $("bubble").onclick = () => setOpen(!S.open);
  $("close").onclick = () => setOpen(false);
  $("tabR").onclick = () => { S.view = "r"; renderPanel(); };
  $("tabQ").onclick = () => { S.view = "q"; renderPanel(); };
  $("tabV").onclick = () => { S.view = "v"; renderPanel(); };
  $("askform").onsubmit = (e) => { e.preventDefault(); const q = $("askinput").value; $("askinput").value = ""; ask(q); };
  $("nudge").onclick = () => { S.view = "r"; setOpen(true); };
  await refreshAll();
}

init().catch((e) => { document.body.insertAdjacentHTML("afterbegin", `<p class="late">Lỗi khởi tạo: ${esc(e.message)}</p>`); });
