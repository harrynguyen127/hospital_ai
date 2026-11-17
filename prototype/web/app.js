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
  $("back").onclick = () => { S.pt = null; S.detail = null; refreshAll(); };
  document.querySelectorAll(".tab[data-f]").forEach((b) => (b.onclick = () => { S.form = b.dataset.f; S.draft = {}; S.ai = {}; renderPatient(); renderPanel(); }));
  const save = $("save");
  if (save) save.onclick = saveRecord;
  const vo = $("voice-open");
  if (vo) vo.onclick = () => { S.view = "v"; setOpen(true); };
}

function formBlock(f) {
  const req = new Set(f.required);
  const inputs = f.fields.map((x) => {
    const isReq = req.has(x.field_id) || x.required;
    const v = S.draft[x.field_id] ?? "";
    const cls = [S.ai[x.field_id] ? "ai" : "", isReq && !String(v).trim() ? "reqmiss" : ""].join(" ");
    const type = x.ui === "number" ? "number" : x.ui === "datetime" ? "datetime-local" : "text";
    return `<div class="f ${cls}"><label for="f-${esc(x.field_id)}">${esc(x.label)}${isReq ? '<span class="req" aria-label="bắt buộc">*</span>' : ""}</label>
      <input id="f-${esc(x.field_id)}" name="${esc(x.field_id)}" type="${type}" value="${esc(v)}" ${x.ui === "number" ? 'step="any"' : ""}>
      ${S.ai[x.field_id] ? "<small>Trợ lý điền từ giọng nói (nháp, chưa lưu)</small>" : ""}</div>`;
  }).join("");
  const empty = f.required.filter((k) => !String(S.draft[k] ?? "").trim());
  const rules = f.rules.map((r) => `<div class="rulebox"><span><b>${esc(r.clause)}</b> · ${esc(r.schedule)}</span><span class="src">“${esc(r.evidence)}”</span></div>`).join("");
  const tasks = f.tasks.map((t) => {
    const u = urg(t.due, t.status);
    return `<div class="item"><span class="nm"><span>${esc(t.note || t.kind)}${t.missing_fields.length ? " · thiếu " + esc(t.missing_fields.join(", ")) : ""}</span><span class="why">${esc(t.role === "bac_si" ? "Bác sĩ" : "Điều dưỡng")}</span></span><span class="pill ${u.c}">${u.t}</span></div>`;
  }).join("");
  const hist = f.records.slice(0, 5).map((r) => `<tr><td class="mono">${fmtT(r.at)}</td>${f.fields.slice(0, 3).map((x) => `<td>${esc(r.values[x.field_id] ?? "—")}</td>`).join("")}</tr>`).join("");
  return `<div class="form">
    <div class="form-h"><h2>${esc(f.title)}</h2>${VOICE[f.form_id] ? `<button class="btn ghost sm" id="voice-open" type="button">Nhập bằng giọng nói</button>` : ""}</div>
    ${rules}${tasks ? `<div class="sec-h">Việc đang chờ</div>${tasks}` : '<p class="note">Không có việc đang chờ cho phiếu này.</p>'}
    <div class="ba"><fieldset><legend>Nội dung phiếu</legend><div class="fields">${inputs}</div></fieldset></div>
    <div class="savebar">${empty.length ? `<div class="reqwarn">Còn trống ${empty.length} trường bắt buộc: ${esc(empty.map((k) => (f.fields.find((x) => x.field_id === k) || {}).label || k).join(", "))}. Vẫn lưu được, nhắc việc sẽ tiếp tục.</div>` : '<div class="reqok">Đã đủ trường bắt buộc.</div>'}
      <button class="btn" id="save" type="button">Lưu bản ghi</button></div>
    ${hist ? `<div class="hist"><div class="sec-h">Các lần lưu gần nhất</div><div class="tablebox"><table><thead><tr><th>Giờ</th>${f.fields.slice(0, 3).map((x) => `<th>${esc(x.label)}</th>`).join("")}</tr></thead><tbody>${hist}</tbody></table></div></div>` : ""}
  </div>`;
}

async function saveRecord() {
  const f = S.detail.forms.find((x) => x.form_id === S.form);
  const values = {};
  f.fields.forEach((x) => {
    const el = document.querySelector(`[name="${x.field_id}"]`);
    if (!el || el.value === "") return;
    values[x.field_id] = el.type === "number" ? Number(el.value) : el.value;
  });
  try {
    const src = Object.keys(S.ai).length ? "voice" : "emr";
    const r = await api("/api/records", { patient_id: S.pt, form_id: S.form, values, user: S.user, source: src });
    const miss = r.record.missing_required;
    toast(miss.length ? `Đã lưu, còn thiếu: ${miss.join(", ")}` : "Đã lưu bản ghi đầy đủ.");
    S.draft = {}; S.ai = {};
    await refreshAll();
  } catch (e) { toast("Lỗi: " + e.message); }
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
      ${ts.map((t) => { const u = urg(t.due, t.status); return `<button type="button" class="item" data-p="${esc(pid)}" data-f="${esc(t.form_id)}"><span class="nm"><span>${esc(t.form_title)}</span><span class="why">${esc(t.clause)}${t.note ? " · " + esc(t.note) : ""}${t.missing_fields.length ? " · thiếu " + esc(t.missing_fields.join(", ")) : ""}</span></span><span class="pill ${u.c}">${u.t}</span></button>`; }).join("")}</div>`).join("") : '<div class="empty-state">Không còn việc nào cho tài khoản này.</div>'}`;
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
  if (p) {
    const d = await api("/api/patient?id=" + encodeURIComponent(p.patient_id));
    const ts = d.forms.flatMap((f) => f.tasks.map((t) => ({ ...t, form_title: f.title, form_id: f.form_id })));
    html = ts.length
      ? `<div class="ans-lead"><b class="mono">${esc(p.patient_id)}</b> còn ${ts.length} việc:</div>` + ts.slice(0, 6).map((t) => `<button type="button" class="item" data-p="${esc(p.patient_id)}" data-f="${esc(t.form_id)}"><span>${esc(t.form_title)}${t.missing_fields.length ? " · thiếu " + esc(t.missing_fields.join(", ")) : ""}</span><span class="pill ${urg(t.due, t.status).c}">${urg(t.due, t.status).t}</span></button>`).join("") + `<div class="src">Nguồn: trạng thái hồ sơ và bộ luật ${esc(d.ruleset_version)}</div>`
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
  $("chips").innerHTML = CHIPS.map((c) => `<button type="button">${esc(c)}</button>`).join("");
  $("chips").querySelectorAll("button").forEach((x) => (x.onclick = () => ask(x.textContent)));
  b.querySelectorAll(".item").forEach((x) => (x.onclick = () => openPatient(x.dataset.p, x.dataset.f)));
  b.scrollTop = b.scrollHeight;
}

// ===== Giọng nói: kịch bản mẫu, đi qua trích xuất đã che định danh =====
const VOICE = {
  phieu_sinh_ton_nguoi_lon: [
    "Anh Nguyễn Văn An, số điện thoại 0912345678, hôm nay trời đẹp quá.",
    "Mạch 88, nhịp thở 20, huyết áp 120 trên 80, nhiệt độ 37 phẩy 2, SpO2 98.",
    "Huyết áp 118 trên 76, mạch 90.",
  ],
  phieu_danh_gia_ban_dau: [
    "Bệnh nhân dị ứng penicillin, nổi mẩn.",
    "Đang dùng paracetamol khi sốt.",
    "Người liên hệ là Lê Thị K, số 0987654321.",
  ],
};

function renderVoice() {
  const b = $("pbody"), v = S.voice, script = VOICE[S.form];
  if (!S.pt) { b.innerHTML = '<div class="vx"><div class="none">Mở một bệnh nhân và một phiếu để nhập bằng giọng nói.</div></div>'; return; }
  if (v.st === "idle") {
    b.innerHTML = `<div class="vx">${script
      ? `<div class="target">Sẽ điền vào <b class="mono">${esc(S.pt)}</b> · <b>${esc((S.detail.forms.find((f) => f.form_id === S.form) || {}).title)}</b></div>
         <button type="button" class="bigbtn" id="vstart">Bắt đầu nghe (kịch bản mẫu)</button>
         <p class="hint">Bản mẫu không dùng micro thật: phát một buổi mẫu, lời nói được che định danh tại máy trước khi trích xuất. Kết quả chỉ là nháp, cần bấm lưu.</p>`
      : '<div class="none">Phiếu này chưa có kịch bản mẫu để thử.</div>'}</div>`;
    const s = $("vstart");
    if (s) s.onclick = () => voiceRun(script);
  } else if (v.st === "listening") {
    b.innerHTML = `<div class="vx"><div class="live"><i class="dot-rec"></i> Đang nghe</div><div class="lines">${v.segs.map((x) => `<div class="ln"><span class="who">Người nói</span><span class="tx">${esc(x)}</span></div>`).join("")}</div></div>`;
  } else if (v.st === "processing") {
    b.innerHTML = `<div class="vx"><ul class="steps">${v.steps.map((s) => `<li class="${s.s}"><span class="st">${s.s === "done" ? "✓" : ""}</span><span>${esc(s.t)}</span></li>`).join("")}</ul></div>`;
  } else {
    b.innerHTML = `<div class="vx"><div class="pills"><span class="pill aip">${v.filled} ô điền nháp</span><span class="pill late">${v.redacted} chỗ đã che định danh</span></div>
      <div class="lines">${v.lines.map((l) => `<div class="ln ${l.out ? "pii" : ""}"><span class="who">Người nói</span><span class="tx">${l.out ? '<span class="drop">Câu ngoài lề, đã bỏ</span>' : esc(l.masked)}</span></div>`).join("")}</div>
      <p class="hint">Các ô điền nháp đã hiện màu tím trên phiếu. Kiểm tra, sửa nếu cần, rồi bấm Lưu bản ghi.</p>
      <button type="button" class="btn ghost" id="vreset">Ghi buổi mới</button></div>`;
    $("vreset").onclick = () => { S.voice = { st: "idle", segs: [] }; S.ai = {}; S.draft = {}; renderPatient(); renderPanel(); };
  }
}

async function voiceRun(script) {
  S.voice = { st: "listening", segs: [] };
  renderPanel();
  for (const line of script) {
    await sleep(500);
    S.voice.segs.push(line);
    renderPanel();
  }
  await sleep(300);
  S.voice.st = "processing";
  S.voice.steps = [{ t: "Che định danh tại máy", s: "run" }, { t: "Trích xuất theo ô của phiếu", s: "wait" }, { t: "Điền nháp", s: "wait" }];
  renderPanel();
  const lines = [], draft = {}, ai = {};
  let redacted = 0;
  for (const text of S.voice.segs) {
    const r = await api("/api/voice", { text, form_id: S.form });
    redacted += r.pii_masked;
    lines.push({ masked: r.masked, out: r.out_of_scope });
    Object.assign(draft, r.extracted);
  }
  Object.keys(draft).forEach((k) => { ai[k] = true; });
  S.draft = { ...draft };
  S.ai = ai;
  S.voice = { st: "review", segs: [], lines, redacted, filled: Object.keys(draft).length };
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
  const base = [{ label: "Mạch", ui: "number", required: true }, { label: "Nhịp thở", ui: "number", required: true }, { label: "Huyết áp", ui: "text" }, { label: "Nhiệt độ", ui: "number" }, { label: "SpO2", ui: "number" }];
  const title = kind === "new" ? "Sàng lọc dinh dưỡng" : "Bảng theo dõi dấu hiệu sinh tồn cho người lớn";
  const fields = kind === "near" ? [...base, { label: "Ghi chú", ui: "text" }]
    : kind === "new" ? [{ label: "Cân nặng (kg)", ui: "number", required: true }, { label: "Ăn kém gần đây", ui: "checkbox" }, { label: "Sụt cân không chủ ý", ui: "select", options: ["Có", "Không"] }]
    : base;
  try {
    const r = await api("/api/detect", { method: "dom", title, fields });
    $("dout").innerHTML = `<div>${esc(r.title)} → <code>${esc(r.form_id)}</code> (v${r.version})</div><div>Cách khớp: <span class="pill later">${esc(r.match)}</span> · ${esc(r.action)}</div>`;
    await refreshAll();
  } catch (e) { $("dout").innerHTML = `<span class="late">${esc(e.message)}</span>`; }
}

// ===== Tải lại toàn bộ dữ liệu =====
async function refreshAll() {
  const st = await api("/api/state");
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
  $("acct").onchange = (e) => { S.user = e.target.value; S.rules = null; refreshAll(); toast("Đã đăng nhập: " + me().label); };
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
