"use strict";
const $ = s => document.querySelector(s);
function el(t, a, ...k) {
  const e = document.createElement(t);
  for (const [x, v] of Object.entries(a || {})) {
    if (x === "class") e.className = v;
    else if (x.startsWith("on")) e.addEventListener(x.slice(2), v);
    else if (v !== false && v != null) e.setAttribute(x, v === true ? "" : v);
  }
  e.append(...k.flat().filter(c => c != null && c !== false));
  return e;
}
async function api(p, o) {
  let r;
  try {
    r = await fetch(p, o ? { method: o.method, headers: { "Content-Type": "application/json" }, body: o.body ? JSON.stringify(o.body) : undefined } : undefined);
  } catch { throw new Error("Couldn't reach Laz Helper. Check your connection and try again."); }
  let d = null;
  try { d = await r.json(); } catch {}
  if (!r.ok) throw new Error(d && typeof d.detail === "string" ? d.detail : "Something went wrong. Try again.");
  return d;
}
let tt;
function toast(m) { const t = $("#toast"); t.textContent = m; t.classList.add("on"); clearTimeout(tt); tt = setTimeout(() => t.classList.remove("on"), 4500); }

const S = { files: [], plan: [], sel: new Set(), dups: null, queue: [], journal: null, ins: null, prefs: null, rules: {}, sloth: null, tab: "moves", scanned: false, view: "home", busy: false };
const TYPES = { ".pdf": "PDF", ".docx": "Word document", ".txt": "Text", ".md": "Text", ".rtf": "Text", ".csv": "Spreadsheet", ".xls": "Spreadsheet", ".xlsx": "Spreadsheet", ".pptx": "Presentation", ".png": "Image", ".jpg": "Image", ".jpeg": "Image", ".webp": "Image", ".zip": "Archive", ".json": "Data file" };
const kind = e => TYPES[e] || (e && e !== "[no extension]" ? e.slice(1).toUpperCase() + " file" : "No extension");
const size = b => b < 1024 ? b + " B" : b < 1048576 ? Math.round(b / 1024) + " KB" : b < 1073741824 ? (b / 1048576).toFixed(1) + " MB" : (b / 1073741824).toFixed(1) + " GB";
const when = i => { try { return new Date(i).toLocaleString([], { dateStyle: "medium", timeStyle: "short" }); } catch { return ""; } };
const hidden = p => p.split("/").some(s => s.startsWith("."));
const base = p => p.split("/").pop();
const dir = p => p.includes("/") ? p.replace(/\/[^/]*$/, "") : "";
const vis = () => S.files.filter(f => !hidden(f.relative_path));
const sw = (on, fn, label) => el("button", { class: "sw" + (on ? " on" : ""), role: "switch", "aria-checked": String(!!on), "aria-label": label, onclick: fn });
const stat = (l, v) => el("div", { class: "stat" }, el("span", {}, l), el("b", {}, v));
const INTERVALS = [[15, "Every 15 minutes"], [30, "Every 30 minutes"], [60, "Every hour"], [180, "Every 3 hours"], [360, "Every 6 hours"], [720, "Every 12 hours"], [1440, "Once a day"]];

function steps() {
  const n = S.scanned ? 2 : 0;
  return el("ol", { class: "steps" }, ["Scan", "Understand", "Review", "Organise"].map((t, i) => el("li", { class: i < n ? "done" : i === n ? "now" : "" }, el("b", {}, String(i + 1)), t)));
}
function insCard() {
  const i = S.ins;
  if (i === false) return null;
  if (!i) return el("section", { class: "card" }, el("p", { class: "mute" }, "Loading your workspace summary…"));
  const g = {};
  for (const [e, c] of Object.entries(i.extension_counts)) g[kind(e)] = (g[kind(e)] || 0) + c;
  const top = Object.entries(g).sort((a, b) => b[1] - a[1]).slice(0, 5), max = top[0] ? top[0][1] : 1;
  const big = i.largest_files.filter(f => !hidden(f.path)).slice(0, 3);
  return el("section", { class: "card" }, el("h2", {}, "What's inside"),
    el("div", { class: "stats" }, stat("Files", i.files_count.toLocaleString()), stat("Total size", size(i.total_bytes))),
    top.length ? top.map(([n, c]) => el("div", { class: "bar" }, el("span", {}, n), el("div", { class: "trk" }, el("i", { style: "width:" + Math.max(6, c / max * 100) + "%" })), el("em", {}, String(c)))) : el("p", { class: "mute" }, "No files yet. Add some to your workspace and scan again."),
    big.length ? el("div", {}, el("h3", {}, "Largest files"), big.map(f => el("div", { class: "li" }, el("span", { class: "nm" }, base(f.path)), el("span", { class: "mute" }, size(f.size_bytes))))) : null);
}
function slothResult(s) {
  if (!s) return null;
  if (s.error) return el("p", { class: "note warn" }, "The last check couldn't finish. No files were changed.");
  return el("div", { class: "note" }, el("b", {}, "Checked “" + s.inbox + "” · " + when(s.ran_at)),
    el("div", { class: "kv" }, el("span", {}, "Files seen"), el("span", {}, String(s.files_seen)), el("span", {}, "Ready to move"), el("span", {}, String(s.ready_for_review)), el("span", {}, "Need your decision"), el("span", {}, String(s.needs_review)), el("span", {}, "Name clashes"), el("span", {}, String(s.conflicts))),
    el("span", { class: "small mute" }, "No files were moved or deleted."));
}
function slothCard() {
  const s = S.sloth;
  if (!s) return null;
  const inbox = el("input", { type: "text", id: "slInbox", value: s.inbox, "aria-label": "Inbox folder" });
  const every = el("select", { id: "slEvery", "aria-label": "How often" }, INTERVALS.map(([m, l]) => el("option", { value: m, selected: m === s.interval_minutes }, l)));
  return el("section", { class: "card" },
    el("div", { class: "between" }, el("div", {}, el("h2", { style: "margin:0" }, "Sloth Mode"), el("p", { class: "mute small" }, "Checks one folder on a schedule and gives you a summary. It never moves files.")),
      sw(s.enabled, async () => { try { S.sloth = await api("/api/sloth-mode", { method: "PUT", body: { enabled: !s.enabled } }); toast(S.sloth.enabled ? "Sloth Mode is on." : "Sloth Mode is off."); home(); } catch (e) { toast(e.message); } }, "Sloth Mode")),
    el("details", { class: "opt" }, el("summary", {}, "Choose folder and schedule"),
      el("div", { class: "field" }, el("label", {}, "Folder to watch"), inbox), el("div", { class: "field" }, el("label", {}, "How often"), every),
      el("button", { onclick: async () => { try { S.sloth = await api("/api/sloth-mode", { method: "PUT", body: { inbox: inbox.value, interval_minutes: Number(every.value) } }); toast("Sloth Mode settings saved."); home(); } catch (e) { toast(e.message); } } }, "Save")),
    el("div", { style: "margin-top:12px" }, el("button", { class: "big", id: "slRun", onclick: async ev => { const b = ev.currentTarget; b.disabled = true; b.textContent = "Checking…"; try { const r = await api("/api/sloth-mode/run", { method: "POST" }); S.sloth.last_summary = r; S.sloth.last_run = r.ran_at; home(); } catch (e) { toast(e.message); b.disabled = false; b.textContent = "Check now"; } } }, "Check now")),
    s.last_summary ? el("div", { style: "margin-top:12px" }, slothResult(s.last_summary)) : null,
    el("p", { class: "mute small", style: "margin-top:10px" }, "Scheduled checks run while Laz Helper is open on your computer."));
}
function home() {
  $("#v-home").replaceChildren(
    el("section", { class: "card hero" }, el("h1", {}, "Your files. ", el("span", {}, "Less fuss.")),
      el("p", {}, S.scanned ? "Last scan found " + vis().length + " files. Nothing was changed." : "Scan your workspace to see what's inside and get tidy-up suggestions. Nothing moves until you approve it."),
      el("button", { class: "pri big", id: "scanBtn", onclick: scan }, "Scan workspace"), el("p", { class: "mute small", id: "prog", role: "status", style: "margin:10px 0 0" })),
    steps(), insCard(), slothCard());
}
async function scan() {
  if (S.busy) return;
  S.busy = true;
  const b = $("#scanBtn"), p = $("#prog");
  b.disabled = true; b.textContent = "Scanning…";
  try {
    p.textContent = "Looking through your folders…";
    const r = await api("/api/scan", { method: "POST", body: { relative_path: "." } });
    S.files = r.files;
    const paths = vis().map(f => f.relative_path).slice(0, 500);
    p.textContent = "Working out where files belong…";
    S.plan = paths.length ? (await api("/api/organize/plan", { method: "POST", body: { relative_paths: paths } })).plan : [];
    S.sel = new Set(S.plan.filter(x => x.status === "ready").map(x => x.source));
    S.scanned = true; S.dups = null;
    await Promise.all([loadIns(), loadQueue()]);
    toast(r.truncated ? "Scan finished. A very large workspace was only partly checked." : "Scan finished. Nothing was changed.");
    go("review");
  } catch (e) { toast(e.message); }
  finally { S.busy = false; const b2 = $("#scanBtn"); if (b2) { b2.disabled = false; b2.textContent = "Scan workspace"; } const p2 = $("#prog"); if (p2) p2.textContent = ""; }
}
async function loadIns() { try { S.ins = await api("/api/insights"); } catch { S.ins = false; } }
async function loadQueue() { try { S.queue = (await api("/api/review-queue")).items.filter(i => !hidden(i.path)); } catch { S.queue = []; } }

function emptyReview() {
  return el("section", { class: "card empty" }, el("h2", {}, "Nothing to review yet"), el("p", { class: "mute" }, "Scan your workspace and your suggestions will appear here."), el("button", { class: "pri", onclick: () => { go("home"); scan(); } }, "Scan workspace"));
}
function moveCard(x) {
  const ready = x.status === "ready";
  return el("div", { class: "card mv" + (ready ? "" : " dim") },
    ready ? el("input", { type: "checkbox", checked: S.sel.has(x.source), "aria-label": "Include " + base(x.source), onchange: e => { e.target.checked ? S.sel.add(x.source) : S.sel.delete(x.source); updBar(); } }) : null,
    el("button", { class: "mvb", onclick: () => details(x) }, el("b", {}, base(x.source)),
      el("span", { class: "mute small" }, ready ? "Move to " + dir(x.destination) : "A file with this name is already in that folder. Nothing will be overwritten.")));
}
function updBar() {
  const b = $("#applyBtn");
  if (!b) return;
  const n = S.sel.size;
  b.disabled = n === 0;
  b.textContent = n ? "Approve " + n + (n === 1 ? " move" : " moves") : "Choose files to move";
}
async function applyMoves() {
  const items = S.plan.filter(x => x.status === "ready" && S.sel.has(x.source)).map(x => ({ source: x.source, destination: x.destination, approved: true }));
  if (!items.length) return;
  const b = $("#applyBtn"); b.disabled = true; b.textContent = "Moving…";
  try {
    const r = await api("/api/organize/apply", { method: "POST", body: { items } });
    const done = new Set(r.completed.map(c => c.source));
    S.plan = S.plan.filter(x => !done.has(x.source));
    done.forEach(d => S.sel.delete(d));
    S.journal = null;
    toast(r.completed.length + (r.completed.length === 1 ? " file moved. " : " files moved. ") + "Nothing was deleted." + (r.failed.length ? " " + r.failed.length + " couldn't be moved: " + r.failed[0].reason : ""));
  } catch (e) { toast(e.message); }
  review();
}
function review() {
  const v = $("#v-review");
  if (!S.scanned) return v.replaceChildren(emptyReview());
  const moves = S.plan.filter(x => x.status === "ready" || x.status === "conflict");
  const tabs = [["moves", "Moves " + moves.length], ["dups", "Copies" + (S.dups ? " " + S.dups.length : "")], ["unsure", "Not sure " + S.queue.length]];
  const seg = el("div", { class: "seg", role: "tablist" }, tabs.map(([k, l]) => el("button", { role: "tab", class: S.tab === k ? "on" : "", "aria-selected": String(S.tab === k), onclick: () => { S.tab = k; review(); } }, l)));
  const out = [el("h1", { style: "font-size:28px" }, "Review"), seg];
  if (S.tab === "moves") {
    if (!moves.length) out.push(el("section", { class: "card empty" }, el("h2", {}, "Your workspace is tidy"), el("p", { class: "mute" }, "No moves to suggest right now.")));
    else {
      out.push(el("p", { class: "mute small", style: "margin-bottom:10px" }, "Tap a file to see what it is. Tick the ones you want to move."), moves.map(moveCard),
        el("div", { class: "apply" }, el("button", { class: "pri big", id: "applyBtn", onclick: applyMoves }, "Approve"), el("p", {}, "Files are moved, never deleted. You can undo from History.")));
    }
  } else if (S.tab === "dups") {
    if (!S.dups) out.push(el("section", { class: "card empty" }, el("h2", {}, "Find exact copies"), el("p", { class: "mute" }, "Laz Helper looks for files that are identical. It never deletes anything."), el("button", { class: "pri", onclick: findDups }, "Look for copies")));
    else if (!S.dups.length) out.push(el("section", { class: "card empty" }, el("h2", {}, "No copies found"), el("p", { class: "mute" }, "Every file here is unique.")));
    else out.push(el("p", { class: "mute small", style: "margin-bottom:10px" }, "These files are exact copies. Laz Helper never deletes files, so open your folder to remove the ones you don't need."),
      S.dups.map(g => el("section", { class: "card" }, el("b", {}, g.count + " identical copies"), el("p", { class: "mute small" }, size(g.files[0].size_bytes) + " each"), g.files.map(f => el("div", { class: "li" }, el("span", { class: "nm" }, f.path))))));
  } else {
    if (!S.queue.length) out.push(el("section", { class: "card empty" }, el("h2", {}, "Nothing needs your decision"), el("p", { class: "mute" }, "Files Laz Helper isn't sure about will show up here.")));
    else out.push(el("p", { class: "mute small", style: "margin-bottom:10px" }, "No folder rule fits these files. Move them yourself, then mark them done."),
      S.queue.map(q => el("section", { class: "card" }, el("b", { class: "nm", style: "display:block" }, base(q.path)), el("p", { class: "mute small", style: "margin-bottom:10px" }, "No folder rule fits this file type."),
        el("div", { class: "row" }, el("button", { onclick: () => decide(q, "reviewed") }, "Mark done"), el("button", { onclick: () => decide(q, "dismissed") }, "Dismiss")))));
  }
  v.replaceChildren(...out);
  updBar();
}
async function findDups(ev) {
  const b = ev.currentTarget; b.disabled = true; b.textContent = "Looking…";
  try { S.dups = (await api("/api/duplicates", { method: "POST", body: { relative_path: "." } })).groups.filter(g => !g.files.every(f => hidden(f.path))); } catch (e) { toast(e.message); }
  review();
}
async function decide(q, d) {
  try { await api("/api/review-queue/decision", { method: "POST", body: { path: q.path, decision: d } }); S.queue = S.queue.filter(x => x.path !== q.path); toast(d === "reviewed" ? "Marked as done." : "Dismissed."); } catch (e) { toast(e.message); }
  review();
}

function openSheet(...k) { $("#panel").replaceChildren(...k); $("#sheet").classList.add("on"); const x = $("#panel .x"); if (x) x.focus(); }
function closeSheet() { $("#sheet").classList.remove("on"); }
async function details(item) {
  const name = base(item.source);
  const head = el("div", { class: "sh-h" }, el("div", {}, el("h2", {}, name), el("p", { class: "mute small" }, item.destination ? "Suggested folder: " + dir(item.destination) : "")), el("button", { class: "x", "aria-label": "Close", onclick: closeSheet }, "×"));
  const body = el("div", {}, el("p", { class: "mute" }, "Reading this file…"));
  const ready = item.status === "ready";
  const foot = ready ? el("div", { class: "row", style: "margin-top:14px" }, el("button", { class: "pri", onclick: () => { S.sel.add(item.source); closeSheet(); review(); } }, "Include this move"), el("button", { onclick: () => { S.sel.delete(item.source); closeSheet(); review(); } }, "Skip it")) : null;
  openSheet(head, body, foot);
  try {
    const r = await api("/api/analyze", { method: "POST", body: { relative_path: item.source } });
    const rec = r.recommendation, out = [];
    if (rec) {
      out.push(el("p", {}, rec.summary), el("div", { class: "kv" }, el("span", {}, "Looks like"), el("span", {}, rec.document_type), el("span", {}, "Suggested name"), el("span", {}, rec.suggested_filename), el("span", {}, "Suggested folder"), el("span", {}, rec.suggested_category)));
      if (rec.evidence.length) out.push(el("h3", {}, "Why"), el("ul", {}, rec.evidence.map(e => el("li", {}, e))));
      if (rec.limitations.length) out.push(el("h3", {}, "Good to know"), el("ul", {}, rec.limitations.map(e => el("li", {}, e))));
    } else out.push(el("p", { class: "note warn" }, r.message));
    if (r.extracted_text) out.push(el("details", {}, el("summary", {}, "Preview of the text"), el("pre", {}, r.extracted_text.slice(0, 800))));
    body.replaceChildren(...out);
  } catch (e) { body.replaceChildren(el("p", { class: "note warn" }, e.message)); }
}

async function history() {
  const v = $("#v-history");
  if (!S.journal) { v.replaceChildren(el("h1", { style: "font-size:28px" }, "History"), el("p", { class: "mute" }, "Loading…")); try { S.journal = (await api("/api/journal")).operations; } catch (e) { toast(e.message); S.journal = []; } }
  const out = [el("h1", { style: "font-size:28px;margin-bottom:6px" }, "History"), el("p", { class: "mute small", style: "margin-bottom:12px" }, "Every move you approved. Undo works while the original folder is still there.")];
  if (!S.journal.length) out.push(el("section", { class: "card empty" }, el("h2", {}, "No moves yet"), el("p", { class: "mute" }, "Approved moves will appear here so you can undo them.")));
  S.journal.forEach(o => out.push(el("section", { class: "card" }, el("div", { class: "between" },
    el("div", { style: "min-width:0" }, el("b", { class: "nm", style: "display:block" }, base(o.source_path)), el("p", { class: "mute small" }, (o.status === "undone" ? "Restored" : "Moved") + " · " + dir(o.destination_path || "") + " · " + when(o.undone_at || o.created_at))),
    o.status === "applied" ? el("button", { style: "flex:none", onclick: async () => { try { await api("/api/journal/" + o.id + "/undo", { method: "POST" }); toast("Put back where it was."); S.journal = null; S.scanned = false; history(); } catch (e) { toast(e.message); } } }, "Undo") : el("span", { class: "badge" }, "Restored")))));
  v.replaceChildren(...out);
}

async function settings() {
  const v = $("#v-settings");
  if (!S.prefs) { try { S.prefs = await api("/api/preferences"); S.rules = JSON.parse(JSON.stringify(S.prefs.category_rules)); } catch (e) { toast(e.message); return; } }
  const date = el("button", { class: "sw" + (S.prefs.include_date_in_plan ? " on" : ""), role: "switch", "aria-checked": String(S.prefs.include_date_in_plan), "aria-label": "Put files in month folders", onclick: e => { const on = !e.currentTarget.classList.contains("on"); e.currentTarget.classList.toggle("on", on); e.currentTarget.setAttribute("aria-checked", String(on)); } });
  const rows = el("div", {});
  const addRow = (n, exts, fresh) => rows.append(el("div", { class: "cat" }, el("input", { type: "text", class: "cn", value: n, placeholder: "Folder name", "aria-label": "Folder name", readonly: !fresh }), el("input", { type: "text", class: "ce", value: exts.join(", "), placeholder: ".pdf, .docx", "aria-label": "File types for " + (n || "new folder") })));
  Object.entries(S.rules).forEach(([n, e]) => addRow(n, e, false));
  v.replaceChildren(el("h1", { style: "font-size:28px;margin-bottom:12px" }, "Settings"),
    el("section", { class: "card" }, el("div", { class: "between" }, el("div", {}, el("b", {}, "Month folders"), el("p", { class: "mute small" }, "Sort files into folders like Documents / 2026-03.")), date)),
    el("section", { class: "card" }, el("h2", {}, "Where files go"), el("p", { class: "mute small" }, "Each folder takes the file types you list. Separate types with commas."), rows,
      el("button", { style: "margin-top:12px", onclick: () => addRow("", [], true) }, "Add a folder")),
    el("button", { class: "pri big", onclick: async () => {
      const rules = {};
      rows.querySelectorAll(".cat").forEach(r => { const n = r.querySelector(".cn").value.trim(), e = r.querySelector(".ce").value.split(/[,\s]+/).filter(Boolean); if (n) rules[n] = e; });
      try { S.prefs = await api("/api/preferences", { method: "PUT", body: { category_rules: rules, include_date_in_plan: date.classList.contains("on") } }); S.rules = JSON.parse(JSON.stringify(S.prefs.category_rules)); S.scanned = false; toast("Settings saved. Scan again to see new suggestions."); settings(); } catch (e) { toast(e.message); }
    } }, "Save settings"));
}

function go(v) {
  S.view = v;
  document.querySelectorAll(".view").forEach(s => s.classList.toggle("on", s.id === "v-" + v));
  document.querySelectorAll("#nav button").forEach(b => { const on = b.dataset.v === v; b.classList.toggle("on", on); on ? b.setAttribute("aria-current", "page") : b.removeAttribute("aria-current"); });
  window.scrollTo(0, 0);
  ({ home, review, history, settings })[v]();
}
document.querySelectorAll("#nav button").forEach(b => b.addEventListener("click", () => go(b.dataset.v)));
$("#sheet").addEventListener("click", e => { if (e.target.id === "sheet") closeSheet(); });
document.addEventListener("keydown", e => { if (e.key === "Escape") closeSheet(); });

(async function init() {
  home();
  await Promise.all([loadIns(), api("/api/sloth-mode").then(s => { S.sloth = s; }).catch(() => {})]);
  if (S.view === "home") home();
})();
