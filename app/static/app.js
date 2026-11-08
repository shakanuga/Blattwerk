/* Blattwerk – Frontend (ohne Build-Schritt, ohne Abhängigkeiten) */
"use strict";

const $app = document.getElementById("app");
const state = { config: null, plants: [], filter: "alle", q: "", draft: null };

// ------------------------------------------------------------------ Ornamente
const LEAF = "M0,0 C6,-9 19,-9 26,0 C19,9 6,9 0,0Z";
function leaf(x, y, rot, s = 1, cls = "lf") {
  return `<path class="${cls}" d="${LEAF}" transform="translate(${x} ${y}) rotate(${rot}) scale(${s})"/>`;
}
function vine(pos = "tl") {
  return `<svg class="vine ${pos}" viewBox="0 0 240 150" aria-hidden="true">
    <path class="stem" d="M-4,14 C40,4 58,44 98,34 S158,2 196,26 S232,78 222,146"/>
    <path class="tendril" d="M98,34 c6,10 18,12 20,4 c2,-6 -6,-8 -8,-3"/>
    <path class="tendril" d="M210,60 c10,-2 14,8 8,12 c-4,3 -8,-1 -5,-4"/>
    ${leaf(18, 9, -35, 1.0)}${leaf(30, 12, 40, .85, "lf2")}
    ${leaf(62, 30, -60, .9, "lf2")}${leaf(78, 36, 30, 1.05)}
    ${leaf(128, 20, -40, .95)}${leaf(140, 14, 35, .8, "lf2")}
    ${leaf(176, 16, -20, 1.05, "lf2")}${leaf(198, 30, 70, .9)}
    ${leaf(222, 72, 120, .95, "lf2")}${leaf(224, 96, 50, .85)}${leaf(222, 122, 130, .9, "lf2")}
  </svg>`;
}
function cornerVine() {
  return `<svg class="corner" viewBox="0 0 80 80" aria-hidden="true">
    <path d="M2,6 C20,2 30,16 44,12 S60,4 72,10" fill="none" stroke="#a7c995" stroke-width="1.6" stroke-linecap="round"/>
    <path d="M6,2 C4,20 16,30 12,46 S4,62 8,74" fill="none" stroke="#a7c995" stroke-width="1.6" stroke-linecap="round"/>
    ${leaf(22, 8, -30, .55)}${leaf(46, 11, 25, .5, "lf2")}${leaf(64, 7, -20, .45)}
    ${leaf(9, 26, 70, .55, "lf2")}${leaf(12, 50, 110, .5)}
  </svg>`.replace(/class="lf"/g, 'fill="#8fbf6f"').replace(/class="lf2"/g, 'fill="#6d9a55"');
}
const LEAFMARK = `<svg class="leafmark" viewBox="0 0 24 24"><path d="M4 20 C4 9 11 4 21 3 C20 13 15 20 4 20Z" fill="#79a65e"/><path d="M4 20 C9 15 13 11 17 7" stroke="#2c5139" stroke-width="1.4" fill="none" stroke-linecap="round"/></svg>`;
const DIVIDER = `<div class="divider"><svg viewBox="0 0 180 24"><path d="M2,12 H70 M110,12 H178" stroke="#9fbf8c" stroke-width="1.2"/>${leaf(72, 12, -25, .7)}${leaf(108, 12, 205, .7, "lf2")}<circle cx="90" cy="12" r="3" fill="#79a65e"/></svg></div>`.replace(/class="lf"/g, 'fill="#79a65e"').replace(/class="lf2"/g, 'fill="#5e8d4c"');
const GROWING = `<svg viewBox="0 0 60 70"><path d="M10 66 H50" stroke="#6b5338" stroke-width="3" stroke-linecap="round"/><g class="sprout"><path d="M30 66 V30" stroke="#4f7a4a" stroke-width="3" stroke-linecap="round"/><path d="M30 42 C18 42 12 32 12 24 C22 24 30 30 30 42Z" fill="#79a65e"/><path d="M30 34 C42 34 48 24 48 16 C38 16 30 22 30 34Z" fill="#5e8d4c"/></g></svg>`;

// ------------------------------------------------------------------ Helfer
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const LOC = { drinnen: "🏠 Drinnen", balkon: "🪴 Balkon", draussen: "🌳 Draußen" };
const HARDY = {
  ja: { t: "Winterhart", cls: "ok", i: "❄️" },
  bedingt: { t: "Bedingt winterhart", cls: "mid", i: "🧣" },
  nein: { t: "Nicht winterhart", cls: "bad", i: "🥶" },
  unbekannt: { t: "Winterhärte unbekannt", cls: "", i: "❔" },
};

async function api(path, opts = {}) {
  const o = { headers: {}, ...opts };
  if (o.body && typeof o.body !== "string") {
    o.body = JSON.stringify(o.body);
    o.headers["Content-Type"] = "application/json";
  }
  const r = await fetch("/api/" + path, o);
  if (r.status === 401) {
    location.href = "/auth/pocketid?next=" + encodeURIComponent(location.pathname + location.search + location.hash);
    throw new Error("Bitte anmelden");
  }
  let data = null;
  try { data = await r.json(); } catch { /* leer */ }
  if (!r.ok) throw new Error((data && data.error) || `Fehler ${r.status}`);
  return data;
}

let toastT;
function toast(msg, err = false) {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.className = "toast show" + (err ? " err" : "");
  clearTimeout(toastT);
  toastT = setTimeout(() => (t.className = "toast"), err ? 4200 : 2400);
}

function fmtDate(iso, withTime = false) {
  if (!iso) return "";
  const d = new Date(iso);
  if (isNaN(d)) return iso;
  const o = { day: "2-digit", month: "2-digit", year: "numeric" };
  if (withTime) Object.assign(o, { hour: "2-digit", minute: "2-digit" });
  return d.toLocaleString("de-DE", o);
}
function relDays(iso) {
  if (!iso) return "";
  const d = Math.round((new Date().setHours(0, 0, 0, 0) - new Date(iso).setHours(0, 0, 0, 0)) / 864e5);
  if (d <= 0) return "heute";
  if (d === 1) return "gestern";
  return `vor ${d} Tagen`;
}
function needsFrostCare(p) {
  return p.location !== "drinnen" && (p.hardy === "nein" || p.hardy === "bedingt");
}
function isWinterish() {
  const m = new Date().getMonth() + 1;
  return m >= 10 || m <= 4;
}

/** Bild verkleinern + Vorschaubild erzeugen (spart Speicher & lädt schnell). */
function loadImage(file) {
  return new Promise((res, rej) => {
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => { URL.revokeObjectURL(url); res(img); };
    img.onerror = () => { URL.revokeObjectURL(url); rej(new Error("Bild konnte nicht gelesen werden")); };
    img.src = url;
  });
}
function scaleTo(img, max, q = 0.85) {
  const s = Math.min(1, max / Math.max(img.naturalWidth, img.naturalHeight));
  const c = document.createElement("canvas");
  c.width = Math.round(img.naturalWidth * s);
  c.height = Math.round(img.naturalHeight * s);
  c.getContext("2d").drawImage(img, 0, 0, c.width, c.height);
  return c.toDataURL("image/jpeg", q);
}
async function processPhoto(file) {
  const img = await loadImage(file);
  return { full: scaleTo(img, 1800, 0.86), thumb: scaleTo(img, 520, 0.8), taken_at: new Date(file.lastModified || Date.now()).toISOString().slice(0, 19) };
}

function winterText(p) {
  const info = p.info || {};
  if (info.winter) return info.winter;
  const t = p.min_temp !== null && p.min_temp !== undefined ? String(p.min_temp).replace(".", ",") : null;
  switch (p.hardy) {
    case "ja":
      return p.location === "drinnen" ? "Winterhart – könnte auch draußen stehen." : "Winterhart, kann draußen bleiben." + (p.location === "balkon" ? " Kübel vor Durchfrieren schützen (Jute, Styroporplatte)." : "");
    case "bedingt":
      return `Verträgt leichten Frost${t ? " bis etwa " + t + " °C" : ""}. Bei strengem Frost mit Vlies schützen oder geschützt an die Hauswand stellen.`;
    case "nein":
      if (p.location === "drinnen") return `Nicht frosthart – ganzjährig drinnen halten${info.tropical ? ", nicht unter 15 °C" : ""}.`;
      return info.tropical
        ? "Nicht frosthart. Ab etwa 10 °C nachts reinholen und warm (über 15 °C) und hell überwintern."
        : "Nicht frosthart. Vor dem ersten Frost reinholen, hell und kühl (ca. 5–12 °C) überwintern, wenig gießen, nicht düngen.";
    default:
      return null;
  }
}

function careRows(p) {
  const info = p.info || {};
  const rows = [];
  const add = (label, val) => { if (val) rows.push(`<div class="tagrow"><b>${label}:</b> ${esc(val)}</div>`); };
  add("Herkunft", info.origin);
  add("Standort", [info.light, info.indoor_ok ? "auch als Zimmerpflanze" : null].filter(Boolean).join(", "));
  add("Gießen", info.water_text || (p.water_interval ? `Etwa alle ${p.water_interval} Tage gießen.` : info.water ? `Wasserbedarf ${info.water}.` : null));
  add("Düngen", info.fertilize);
  add("Blüte", info.flowering);
  add("Überwintern", winterText(p));
  add("Erde", info.soil);
  add("Rückschnitt", info.pruning);
  add("Vermehrung", info.propagation);
  add("Wuchshöhe", info.height);
  add("Lockt an", info.attracts);
  add("Essbar", info.edible || (info.toxic_humans ? "nein (giftig)" : null));
  add("Topf", info.pot_size);
  return rows.join("");
}

function setTab(name) {
  document.querySelectorAll("#tabbar a").forEach((a) => a.classList.toggle("on", a.dataset.tab === name));
}

// ------------------------------------------------------------------ Router
async function router() {
  const h = location.hash.replace(/^#/, "") || "/";
  window.scrollTo(0, 0);
  try {
    if (!state.config) state.config = await api("config");
    let m;
    if (h === "/" || h === "") { setTab("home"); return await viewList(); }
    if (h === "/neu") { setTab("new"); return viewNew(); }
    if (h === "/neu/details") { setTab("new"); return viewForm(); }
    if (h === "/einstellungen") { setTab("settings"); return viewSettings(); }
    if ((m = h.match(/^\/pflanze\/(\d+)$/))) { setTab(""); return await viewDetail(+m[1]); }
    if ((m = h.match(/^\/pflanze\/(\d+)\/bearbeiten$/))) { setTab(""); return await viewEdit(+m[1]); }
    location.hash = "#/";
  } catch (e) {
    $app.innerHTML = `<header class="hero slim">${vine("tl")}<h1>Hoppla</h1><p class="sub">${esc(e.message)}</p></header>`;
  }
}
window.addEventListener("hashchange", router);

// ------------------------------------------------------------------ Übersicht
async function viewList() {
  $app.innerHTML = `<header class="hero">${vine("tl")}${vine("tr")}<h1>Blatt<em>werk</em></h1><p class="sub">Dein Pflanzen-Tagebuch</p></header><div class="growing">${GROWING}</div>`;
  const { plants } = await api("plants");
  state.plants = plants;
  const thirsty = plants.filter((p) => p.next_water_in !== null && p.next_water_in <= 0);
  const frost = plants.filter(needsFrostCare);

  let notices = "";
  if (frost.length && isWinterish()) {
    notices += `<div class="notice"><span class="ni">❄️</span><div><b>Frostschutz prüfen</b>${frost.map((p) => `<a href="#/pflanze/${p.id}">${esc(p.name)}</a>`).join(", ")} ${frost.length === 1 ? "steht" : "stehen"} draußen und ${frost.length === 1 ? "ist" : "sind"} nicht (voll) winterhart.</div></div>`;
  }
  if (thirsty.length) {
    notices += `<div class="notice warn"><span class="ni">💧</span><div><b>Durstig</b>${thirsty.map((p) => `<a href="#/pflanze/${p.id}">${esc(p.name)}</a>`).join(", ")}</div></div>`;
  }

  $app.innerHTML = `
    <header class="hero">${vine("tl")}${vine("tr")}
      <h1>Blatt<em>werk</em></h1>
      <p class="sub">Dein Pflanzen-Tagebuch</p>
    </header>
    <main class="wrap">
      <div class="stats">
        <div class="stat"><b>${plants.length}</b><span>Pflanzen</span></div>
        <div class="stat"><b>${thirsty.length}</b><span>durstig</span></div>
        <div class="stat"><b>${plants.filter((p) => p.hardy === "ja").length}</b><span>winterhart</span></div>
      </div>
      ${notices}
      ${plants.length ? `
      <div class="toolbar">
        <label class="searchbox">🔎<input id="q" type="search" placeholder="Pflanzen durchsuchen…" value="${esc(state.q)}"></label>
        <div class="chips" id="chips">
          ${[["alle", "Alle"], ["drinnen", "🏠 Drinnen"], ["balkon", "🪴 Balkon"], ["draussen", "🌳 Draußen"], ["durstig", "💧 Durstig"], ["frost", "🥶 Nicht winterhart"], ["giftig", "⚠️ Giftig für Tiere"]]
            .map(([k, t]) => `<button class="chip ${state.filter === k ? "on" : ""}" data-f="${k}">${t}</button>`).join("")}
        </div>
      </div>
      <div class="grid" id="grid"></div>` : `
      <div class="empty">
        <div class="big">🌱</div>
        <h2>Noch keine Pflanzen</h2>
        <p>Mach ein Foto von deiner ersten Pflanze – Blattwerk sucht die passenden Infos dazu.</p>
        <a class="btn" href="#/neu">＋ Erste Pflanze anlegen</a>
      </div>`}
      ${DIVIDER}
      <div class="footer">Blattwerk ${esc(state.config.version)}</div>
    </main>`;

  if (!plants.length) return;
  const renderGrid = () => {
    const q = state.q.toLowerCase();
    const list = plants.filter((p) => {
      if (q && ![p.name, p.species_common, p.species_sci, p.spot].some((v) => (v || "").toLowerCase().includes(q))) return false;
      switch (state.filter) {
        case "drinnen": case "balkon": case "draussen": return p.location === state.filter;
        case "durstig": return p.next_water_in !== null && p.next_water_in <= 0;
        case "frost": return p.hardy === "nein" || p.hardy === "bedingt";
        case "giftig": return p.info && p.info.toxic_pets === true;
        default: return true;
      }
    });
    document.getElementById("grid").innerHTML = list.length ? list.map(card).join("") : `<div class="empty" style="grid-column:1/-1"><p>Keine Treffer.</p></div>`;
  };
  renderGrid();
  document.getElementById("q").addEventListener("input", (e) => { state.q = e.target.value; renderGrid(); });
  document.getElementById("chips").addEventListener("click", (e) => {
    const b = e.target.closest(".chip");
    if (!b) return;
    state.filter = b.dataset.f;
    document.querySelectorAll(".chip").forEach((c) => c.classList.toggle("on", c === b));
    renderGrid();
  });
}

function waterPill(p) {
  if (p.next_water_in === null) return "";
  if (p.next_water_in <= 0) return `<span class="pill thirsty">💧 gießen!</span>`;
  return `<span class="pill water">💧 in ${p.next_water_in} T</span>`;
}
function hardyPill(p) {
  const h = HARDY[p.hardy] || HARDY.unbekannt;
  if (p.hardy === "unbekannt" || !p.hardy) return "";
  if (needsFrostCare(p)) return `<span class="pill frost">${h.i} Frost!</span>`;
  return `<span class="pill ${h.cls}">${h.i}</span>`;
}
function card(p) {
  const img = p.cover || p.ref_image;
  return `<a class="card" href="#/pflanze/${p.id}">
    <div class="ph">${img ? `<img loading="lazy" src="${esc(img)}" alt="">` : `<div class="noimg">🪴</div>`}
      ${cornerVine()}
      <div class="badges">${waterPill(p)}${hardyPill(p)}</div>
      <div class="where">${LOC[p.location] || ""}${p.spot ? " · " + esc(p.spot) : ""}</div>
    </div>
    <div class="meta"><h3>${esc(p.name)}</h3><div class="sp">${esc(p.species_sci || p.species_common || "Art unbekannt")}</div></div>
  </a>`;
}

// ------------------------------------------------------------------ Neue Pflanze
function viewNew() {
  const cfg = state.config;
  state.draft = state.draft || { photo: null };
  $app.innerHTML = `
    <header class="hero slim">${vine("tl")}${vine("tr")}
      <a class="back" href="#/">← Zurück</a>
      <h1>Neue Pflanze</h1>
      <p class="sub">Foto machen, Art finden, fertig.</p>
    </header>
    <main class="wrap">
      <section class="panel lift">
        <h2>${LEAFMARK}1. Foto</h2>
        <label class="photo-drop" id="drop">
          <input type="file" accept="image/*" capture="environment" id="file">
          <div class="cam">📷</div>
          <b>Foto aufnehmen</b>
          <small>oder aus der Galerie wählen</small>
        </label>
        ${cfg.plantnet ? `
          <div class="seg" id="organ" style="margin-top:12px">
            ${[["auto", "Automatisch"], ["leaf", "Blatt"], ["flower", "Blüte"], ["fruit", "Frucht"], ["bark", "Rinde"]].map(([k, t], i) => `<button type="button" data-o="${k}" class="${i ? "" : "on"}">${t}</button>`).join("")}
          </div>
          <button class="btn block" id="identify" style="margin-top:12px" disabled>🔍 Pflanze erkennen</button>
          <div id="idres" class="results"></div>` : `
          <p class="sources">Tipp: Mit einem kostenlosen Pl@ntNet-Key erkennt Blattwerk die Art direkt am Foto (siehe Einstellungen).</p>`}
      </section>
      <section class="panel">
        <h2>${LEAFMARK}2. ${cfg.plantnet ? "Oder " : ""}nach Namen suchen</h2>
        <label class="searchbox">🔎<input id="sq" type="search" placeholder="z. B. Monstera, Lavendel, Olivenbaum" autocomplete="off"></label>
        <div id="sres" class="results"></div>
        <div class="or">oder</div>
        <button class="btn ghost block" id="manual">Ohne Suche selbst eintragen</button>
      </section>
    </main>`;

  const fileIn = document.getElementById("file");
  const drop = document.getElementById("drop");
  const showPreview = () => {
    if (!state.draft.photo) return;
    drop.innerHTML = `<input type="file" accept="image/*" capture="environment" id="file"><img class="preview" src="${state.draft.photo.thumb}"><span class="change">Anderes Foto</span>`;
    document.getElementById("file").addEventListener("change", onFile);
    const idb = document.getElementById("identify");
    if (idb) idb.disabled = false;
  };
  async function onFile(e) {
    const f = e.target.files[0];
    if (!f) return;
    try {
      state.draft.photo = await processPhoto(f);
      showPreview();
      if (cfg.plantnet) identify();
    } catch (err) { toast(err.message, true); }
  }
  fileIn.addEventListener("change", onFile);
  showPreview();

  let organ = "auto";
  const organEl = document.getElementById("organ");
  if (organEl) organEl.addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (!b) return;
    organ = b.dataset.o;
    organEl.querySelectorAll("button").forEach((x) => x.classList.toggle("on", x === b));
  });

  async function identify() {
    const out = document.getElementById("idres");
    out.innerHTML = `<div class="loading"><span class="spinner"></span>Pl@ntNet schaut sich das Foto an…</div>`;
    try {
      const r = await api("identify", { method: "POST", body: { image: state.draft.photo.full, organ } });
      if (!r.results.length) { out.innerHTML = `<p class="sources">Keine sichere Erkennung. Probier ein Foto, auf dem ein Blatt oder die Blüte groß zu sehen ist – oder such unten nach dem Namen.</p>`; return; }
      out.innerHTML = r.results.map((x, i) => `
        <button class="result" data-sci="${esc(x.sci)}" data-i="${i}">
          ${x.thumb ? `<img src="${esc(x.thumb)}" alt="">` : `<span class="ri">🌿</span>`}
          <span class="rt"><b>${esc(x.common[0] || x.sci)}</b><i>${esc(x.sci)}${x.family ? " · " + esc(x.family) : ""}</i>
          <div class="score"><span style="width:${Math.max(3, x.score)}%"></span></div><small>${x.score} % Übereinstimmung</small></span>
        </button>`).join("") + (r.remaining != null ? `<p class="sources">Noch ${r.remaining} Erkennungen heute frei.</p>` : "");
      out.querySelectorAll(".result").forEach((b) => b.addEventListener("click", () => pick({ sci: b.dataset.sci, common: r.results[+b.dataset.i].common[0] })));
    } catch (err) { out.innerHTML = `<p class="sources">⚠️ ${esc(err.message)}</p>`; }
  }
  const idb = document.getElementById("identify");
  if (idb) idb.addEventListener("click", identify);

  let t;
  document.getElementById("sq").addEventListener("input", (e) => {
    clearTimeout(t);
    const q = e.target.value.trim();
    const out = document.getElementById("sres");
    if (q.length < 2) { out.innerHTML = ""; return; }
    out.innerHTML = `<div class="loading"><span class="spinner"></span>Suche…</div>`;
    t = setTimeout(async () => {
      try {
        const { results } = await api("search?q=" + encodeURIComponent(q));
        if (e.target.value.trim() !== q) return;
        out.innerHTML = results.length ? results.map((x) => `
          <button class="result" data-title="${esc(x.title)}">
            ${x.thumb ? `<img src="${esc(x.thumb)}" alt="" loading="lazy">` : `<span class="ri">🌿</span>`}
            <span class="rt"><b>${esc(x.title)}</b><small>${esc(x.extract)}</small></span>
          </button>`).join("") : `<p class="sources">Nichts gefunden. Versuch's mit dem botanischen Namen.</p>`;
        out.querySelectorAll(".result").forEach((b) => b.addEventListener("click", () => pick({ title: b.dataset.title })));
      } catch (err) { out.innerHTML = `<p class="sources">⚠️ ${esc(err.message)}</p>`; }
    }, 380);
  });

  document.getElementById("manual").addEventListener("click", () => {
    state.draft.profile = { info: {}, hardy: "unbekannt", location: "drinnen" };
    state.draft.keep = true;
    location.hash = "#/neu/details";
  });
}

async function pick({ title, sci, common }) {
  $app.innerHTML = `<header class="hero slim">${vine("tl")}${vine("tr")}<h1>Einen Moment…</h1><p class="sub">Blattwerk sammelt alles über ${esc(title || common || sci)}</p></header>
    <div class="growing">${GROWING}<span>Wikipedia, Pflege- und Winterhärtedaten werden geladen…</span></div>`;
  try {
    const params = new URLSearchParams();
    if (title) params.set("title", title);
    if (sci) params.set("sci", sci);
    const prof = await api("lookup?" + params);
    if (!prof.species_common && common) prof.species_common = common;
    state.draft.profile = prof;
    state.draft.keep = true;
    (prof.warnings || []).forEach((w) => toast(w, true));
    location.hash = "#/neu/details";
  } catch (e) {
    toast(e.message, true);
    state.draft.keep = true;
    viewNew();
  }
}

// ------------------------------------------------------------------ Formular
function viewForm(existing) {
  const isEdit = !!existing;
  if (!isEdit && !(state.draft && state.draft.profile)) { location.hash = "#/neu"; return; }
  const p = isEdit ? existing : { location: "drinnen", ...state.draft.profile, name: state.draft.profile.name || state.draft.profile.species_common || "" };
  const info = p.info || {};
  const ref = isEdit ? (p.ref_image_url !== undefined ? p.ref_image_url : p.ref_image) : p.ref_image_url;
  const triSel = (name, v) => `<select class="inp" name="${name}">
      <option value="" ${v === undefined || v === null || v === "" ? "selected" : ""}>unbekannt</option>
      <option value="true" ${v === true ? "selected" : ""}>ja, giftig</option>
      <option value="false" ${v === false ? "selected" : ""}>nein</option></select>`;

  $app.innerHTML = `
    <header class="hero slim">${vine("tl")}${vine("tr")}
      <a class="back" href="${isEdit ? `#/pflanze/${p.id}` : "#/neu"}">← Zurück</a>
      <h1>${isEdit ? "Bearbeiten" : "Fast fertig"}</h1>
      <p class="sub">${isEdit ? esc(p.name) : "Prüf die Daten und gib deiner Pflanze einen Namen."}</p>
    </header>
    <main class="wrap">
      <form id="pf" class="panel lift" autocomplete="off">
        ${ref ? `<figure class="ref" style="float:none;width:auto;margin:0 0 14px"><span class="tag">Musterbild</span><img src="${esc(ref)}" alt=""><figcaption><span>${esc(info.ref_credit || "")}</span></figcaption></figure>` : ""}
        ${!isEdit && state.draft.photo ? `<p class="sources">📷 Dein Foto wird als erstes Bild gespeichert.</p>` : ""}
        <label class="f"><span>Name / Spitzname</span><input class="inp" name="name" required value="${esc(p.name)}" placeholder="z. B. Monsti"></label>
        <div class="row2">
          <label class="f"><span>Art (deutsch)</span><input class="inp" name="species_common" value="${esc(p.species_common)}"></label>
          <label class="f"><span>Botanischer Name</span><input class="inp" name="species_sci" value="${esc(p.species_sci)}" style="font-style:italic"></label>
        </div>
        <label class="f"><span>Standort</span>
          <div class="seg" id="loc">${Object.entries(LOC).map(([k, t]) => `<button type="button" data-v="${k}" class="${p.location === k ? "on" : ""}">${t}</button>`).join("")}</div>
        </label>
        <div class="row2">
          <label class="f"><span>Platz</span><input class="inp" name="spot" value="${esc(p.spot)}" placeholder="z. B. Wohnzimmer, Südfenster"></label>
          <label class="f"><span>Bei mir seit</span><input class="inp" type="date" name="acquired" value="${esc(p.acquired || (isEdit ? "" : new Date().toISOString().slice(0, 10)))}"></label>
        </div>
        <div class="row2">
          <label class="f"><span>Gießen alle … Tage</span><input class="inp" type="number" min="1" max="120" name="water_interval" value="${esc(p.water_interval ?? "")}"></label>
          <label class="f"><span>Wasserbedarf</span><input class="inp" name="i_water" value="${esc(info.water)}" placeholder="wenig / mittel / viel"></label>
        </div>
        <label class="f"><span>Gieß-Hinweis</span><input class="inp" name="i_water_text" value="${esc(info.water_text)}" placeholder="z. B. Gut feucht halten"></label>
        <label class="f"><span>Licht / Standort</span><input class="inp" name="i_light" value="${esc(info.light)}" placeholder="Sonne, Halbschatten…"></label>
        <div class="row2">
          <label class="f"><span>Düngen</span><input class="inp" name="i_fertilize" value="${esc(info.fertilize)}" placeholder="z. B. wöchentlich"></label>
          <label class="f"><span>Herkunft</span><input class="inp" name="i_origin" value="${esc(info.origin)}"></label>
        </div>
        <div class="row2">
          <label class="f"><span>Winterhart?</span><select class="inp" name="hardy">
            ${Object.entries(HARDY).map(([k, h]) => `<option value="${k}" ${p.hardy === k ? "selected" : ""}>${h.t}</option>`).join("")}
          </select></label>
          <label class="f"><span>Verträgt bis (°C)</span><input class="inp" type="number" step="0.5" name="min_temp" value="${esc(p.min_temp ?? "")}"></label>
        </div>
        <div class="row2">
          <label class="f"><span>Giftig für Menschen</span>${triSel("i_toxic_humans", info.toxic_humans)}</label>
          <label class="f"><span>Giftig für Haustiere</span>${triSel("i_toxic_pets", info.toxic_pets)}</label>
        </div>
        <label class="f"><span>Eigene Notizen</span><textarea class="inp" name="notes" placeholder="Umgetopft, gedüngt, Ableger…">${esc(p.notes)}</textarea></label>
        <details class="more">
          <summary>Weitere Steckbrief-Daten</summary>
          <div class="row2">
            <label class="f"><span>Wuchsform</span><input class="inp" name="i_plant_type" value="${esc(info.plant_type)}"></label>
            <label class="f"><span>Lebensdauer</span><input class="inp" name="i_cycle" value="${esc(info.cycle)}"></label>
          </div>
          <div class="row2">
            <label class="f"><span>Blütezeit</span><input class="inp" name="i_flowering" value="${esc(info.flowering)}"></label>
            <label class="f"><span>Pflegeaufwand</span><input class="inp" name="i_care_level" value="${esc(info.care_level)}"></label>
          </div>
          <div class="row2">
            <label class="f"><span>Familie</span><input class="inp" name="i_family" value="${esc(info.family)}"></label>
            <label class="f"><span>Winterhärtezone (USDA)</span><input class="inp" name="i_hardiness_zone" value="${esc(info.hardiness_zone)}"></label>
          </div>
          <label class="f"><span>Überwintern (leer = automatisch)</span><input class="inp" name="i_winter" value="${esc(info.winter)}" placeholder="${esc(winterText({ ...p, info: { ...info, winter: null } }) || "")}"></label>
          <div class="row2">
            <label class="f"><span>Essbar</span><input class="inp" name="i_edible" value="${esc(info.edible)}" placeholder="ja / nein"></label>
            <label class="f"><span>Topfgröße</span><input class="inp" name="i_pot_size" value="${esc(info.pot_size)}" placeholder="z. B. 3 l"></label>
          </div>
          <div class="row2">
            <label class="f"><span>Erde</span><input class="inp" name="i_soil" value="${esc(info.soil)}"></label>
            <label class="f"><span>Rückschnitt</span><input class="inp" name="i_pruning" value="${esc(info.pruning)}"></label>
          </div>
          <div class="row2">
            <label class="f"><span>Wuchshöhe</span><input class="inp" name="i_height" value="${esc(info.height)}"></label>
            <label class="f"><span>Vermehrung</span><input class="inp" name="i_propagation" value="${esc(info.propagation)}"></label>
          </div>
          <label class="f"><span>Musterbild (URL)</span><input class="inp" name="ref_image_url" value="${esc(ref || "")}"></label>
          <label class="f"><span>Beschreibung</span><textarea class="inp" name="i_description" style="min-height:160px">${esc(info.description)}</textarea></label>
        </details>
        <button class="btn block" type="submit" style="margin-top:10px">${isEdit ? "💾 Speichern" : "🌱 Pflanze speichern"}</button>
      </form>
    </main>`;

  let loc = p.location || "drinnen";
  document.getElementById("loc").addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (!b) return;
    loc = b.dataset.v;
    document.querySelectorAll("#loc button").forEach((x) => x.classList.toggle("on", x === b));
  });
  // Winterhärte automatisch aus Temperatur vorschlagen
  const minIn = document.querySelector("[name=min_temp]");
  minIn.addEventListener("change", () => {
    const v = parseFloat(minIn.value);
    if (isNaN(v)) return;
    const local = parseFloat(state.config.settings.local_min_temp);
    document.querySelector("[name=hardy]").value = v <= local ? "ja" : v <= local + 6 ? "bedingt" : "nein";
  });

  document.getElementById("pf").addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const newInfo = { ...info };
    for (const [k, v] of fd.entries()) {
      if (!k.startsWith("i_")) continue;
      const key = k.slice(2);
      if (key.startsWith("toxic_")) newInfo[key] = v === "" ? null : v === "true";
      else newInfo[key] = v.trim() || null;
    }
    const body = {
      name: fd.get("name").trim(),
      species_common: fd.get("species_common").trim() || null,
      species_sci: fd.get("species_sci").trim() || null,
      location: loc,
      spot: fd.get("spot").trim() || null,
      acquired: fd.get("acquired") || null,
      water_interval: fd.get("water_interval"),
      hardy: fd.get("hardy"),
      min_temp: fd.get("min_temp"),
      notes: fd.get("notes").trim() || null,
      info: newInfo,
    };
    const refNew = fd.get("ref_image_url").trim();
    if (!isEdit || refNew !== (p.ref_image || "")) body.ref_image_url = refNew || null;
    if (!isEdit && state.draft.photo) body.photo = state.draft.photo;
    const btn = e.target.querySelector("button[type=submit]");
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner"></span> Speichere…`;
    try {
      const saved = isEdit ? await api("plants/" + p.id, { method: "PUT", body }) : await api("plants", { method: "POST", body });
      state.draft = null;
      toast(isEdit ? "Gespeichert" : "🌱 Willkommen, " + saved.name + "!");
      location.hash = "#/pflanze/" + saved.id;
    } catch (err) {
      toast(err.message, true);
      btn.disabled = false;
      btn.textContent = "Nochmal versuchen";
    }
  });
}

async function viewEdit(id, refreshed) {
  const p = await api("plants/" + id);
  if (refreshed) {
    // Neu abgerufene Daten über bestehende legen, eigene Angaben bleiben
    p.info = { ...p.info, ...Object.fromEntries(Object.entries(refreshed.info || {}).filter(([, v]) => v !== null && v !== undefined && v !== "")) };
    for (const k of ["species_common", "species_sci", "min_temp", "water_interval", "hardy"]) if (refreshed[k] !== undefined && refreshed[k] !== null) p[k] = refreshed[k];
    if (refreshed.ref_image_url) p.ref_image_url = refreshed.ref_image_url;
  }
  viewForm(p);
}

// ------------------------------------------------------------------ Detail
async function viewDetail(id) {
  $app.innerHTML = `<div class="growing" style="padding-top:120px">${GROWING}</div>`;
  const p = await api("plants/" + id);
  const info = p.info || {};
  const heroImg = p.cover || p.ref_image;
  const h = HARDY[p.hardy] || HARDY.unbekannt;

  const facts = [];
  const add = (i, label, val, cls = "") => { if (val !== undefined && val !== null && val !== "") facts.push(`<div class="fact ${cls}"><div class="fi">${i}</div><small>${label}</small><b>${esc(val)}</b></div>`); };
  add(h.i, "Winterhärte", h.t + (p.min_temp !== null && p.min_temp !== undefined ? ` (bis ${String(p.min_temp).replace(".", ",")} °C)` : ""), needsFrostCare(p) ? "frost" : h.cls);
  add("☀️", "Licht", info.light);
  add("💧", "Wasserbedarf", info.water);
  add("🗓️", "Gießen", p.water_interval ? `alle ${p.water_interval} Tage` : null);
  add("🌡️", "Temperatur", info.temp_range);
  add("💨", "Luftfeuchte", info.humidity);
  add("🪨", "Bodenfeuchte", info.soil_moisture);
  add("🔆", "Licht (Lux)", info.light_lux);
  if (info.toxic_humans !== undefined && info.toxic_humans !== null) add(info.toxic_humans ? "⚠️" : "✅", "Für Menschen", info.toxic_humans ? "giftig" : "ungiftig", info.toxic_humans ? "bad" : "ok");
  if (info.toxic_pets !== undefined && info.toxic_pets !== null) add(info.toxic_pets ? "🐾" : "🐶", "Für Haustiere", info.toxic_pets ? "giftig" : "ungiftig", info.toxic_pets ? "bad" : "ok");
  add("🌸", "Blütezeit", info.flowering);
  add("🌿", "Wuchsform", info.plant_type);
  add("♻️", "Lebensdauer", info.cycle);
  add("🧤", "Pflegeaufwand", info.care_level);
  add("🧬", "Familie", info.family);
  add("🗺️", "USDA-Zone", info.hardiness_zone);
  if (info.indoor_ok) add("🏠", "Zimmerpflanze", "geeignet");
  if (info.drought_tolerant) add("🏜️", "Trockenheit", "verträgt sie gut");
  add("📅", "Bei dir seit", p.acquired ? fmtDate(p.acquired) : null);

  const desc = (info.description || "").split(/\n+/).filter(Boolean).map((x) => `<p>${esc(x)}</p>`).join("");
  const frostNote = needsFrostCare(p)
    ? `<div class="notice"><span class="ni">❄️</span><div><b>${p.hardy === "nein" ? "Vor dem ersten Frost reinholen" : "Im Winter schützen"}</b>${esc(winterText(p) || "")}</div></div>`
    : "";

  $app.innerHTML = `
    <main class="wrap">
      <div class="dhero">
        <div class="img">${heroImg ? `<img src="${esc(heroImg)}" alt="" id="heroimg">` : ""}</div>
        ${vine("tl")}
        <div class="top"><a class="round" href="#/">←</a><a class="round" href="#/pflanze/${p.id}/bearbeiten" title="Bearbeiten">✏️</a></div>
        <div class="title">
          <h1>${esc(p.name)}</h1>
          <div class="sci">${esc([p.species_common !== p.name ? p.species_common : null, p.species_sci].filter(Boolean).join(" · "))}</div>
          <div class="pills"><span class="pill">${LOC[p.location] || ""}${p.spot ? " · " + esc(p.spot) : ""}</span>${waterPill(p)}</div>
        </div>
      </div>

      <div class="actions">
        <button class="btn water" id="water">💧 Gegossen</button>
        <label class="btn light" style="cursor:pointer">📷 Foto<input type="file" accept="image/*" capture="environment" id="addphoto" hidden></label>
      </div>
      ${p.last_watered ? `<p class="sources" style="text-align:center">Zuletzt gegossen ${relDays(p.last_watered)}${p.next_water_in !== null ? (p.next_water_in > 0 ? ` · nächstes Mal in ${p.next_water_in} Tagen` : " · ist wieder dran") : ""}</p>` : ""}
      ${frostNote}

      ${careRows(p) ? `<section class="panel care"><h2>${LEAFMARK}Pflege</h2><div class="tagcard"><div class="tagname">${esc(p.species_common || p.name)}</div>${careRows(p)}${p.species_sci ? `<div class="tagsci">${esc(p.species_sci)}</div>` : ""}</div>
        ${info.care_guide ? `<details class="more"><summary>Ausführliche Pflegeanleitung (englisch, Perenual)</summary>${Object.entries(info.care_guide).map(([k, v]) => `<p class="desc"><b>${esc({ watering: "Gießen", sunlight: "Licht", pruning: "Rückschnitt" }[k] || k)}:</b> ${esc(v)}</p>`).join("")}</details>` : ""}
      </section>` : ""}
      <section class="panel"><h2>${LEAFMARK}Steckbrief</h2>
        ${facts.length ? `<div class="facts">${facts.join("")}</div>` : `<p class="sources">Noch keine Daten. Über „Daten neu abrufen“ oder „Bearbeiten“ ergänzen.</p>`}
        ${info.sources && info.sources.length ? `<p class="sources">Quellen: ${esc(info.sources.join(", "))}</p>` : ""}
        ${!(info.sources || []).some((x) => x === "Perenual" || x === "Open Plantbook")
          ? `<div class="notice warn"><span class="ni">🔑</span><div><b>Keine Pflegedaten abgerufen</b>${state.config.perenual || state.config.openplantbook
              ? "Für diese Art hatte die Pflege-Datenbank nichts. Du kannst die Werte über ✏️ selbst eintragen."
              : `Winterhärte, Wasser, Licht und Giftigkeit kommen von Perenual. Dafür fehlt noch der kostenlose API-Key – siehe <a href="#/einstellungen">Einstellungen</a>. Danach unten auf „Daten neu abrufen“.`}</div></div>`
          : ""}
      </section>

      ${desc || p.ref_image ? `<section class="panel"><h2>${LEAFMARK}Beschreibung</h2>
        <div class="desc">
          ${p.ref_image ? `<figure class="ref"><span class="tag">Musterbild</span><img src="${esc(p.ref_image)}" alt="Musterbild ${esc(p.species_common || "")}" id="refimg"><figcaption><span>${esc(info.ref_credit || "")}</span>${info.wiki_url ? `<a href="${esc(info.wiki_url)}" target="_blank" rel="noopener">Wikipedia ↗</a>` : ""}</figcaption></figure>` : ""}
          ${desc}
          ${!p.ref_image && info.wiki_url ? `<p><a href="${esc(info.wiki_url)}" target="_blank" rel="noopener">Weiterlesen auf Wikipedia ↗</a></p>` : ""}
          <div class="clear"></div>
        </div>
        ${info.description_en && !desc ? `<details class="more"><summary>Englische Beschreibung (Perenual)</summary><p class="desc">${esc(info.description_en)}</p></details>` : ""}
      </section>` : ""}

      ${p.notes ? `<section class="panel"><h2>${LEAFMARK}Notizen</h2><div class="desc">${p.notes.split(/\n+/).map((x) => `<p>${esc(x)}</p>`).join("")}</div></section>` : ""}

      <section class="panel"><h2>${LEAFMARK}Fotos <small style="font-family:var(--sans);font-size:.8rem;color:var(--muted);font-weight:400">${p.photos.length}</small></h2>
        <div class="gallery">
          <label class="add"><input type="file" accept="image/*" id="addphoto2" multiple>＋<br>Foto</label>
          ${p.photos.map((ph, i) => `<div class="g ${p.cover_photo_id === ph.id ? "cover" : ""}" data-i="${i}"><img loading="lazy" src="${esc(ph.thumb_url)}" alt=""><span>${fmtDate(ph.taken_at)}</span></div>`).join("")}
        </div>
      </section>

      <section class="panel"><h2>${LEAFMARK}Gieß-Protokoll</h2>
        ${p.waterings.length ? `<ul class="log">${p.waterings.map((w) => `<li><span>💧 ${fmtDate(w.at, true)} <small style="color:var(--muted)">(${relDays(w.at)})</small></span><button data-w="${w.id}" title="Eintrag löschen">✕</button></li>`).join("")}</ul>` : `<p class="sources">Noch nicht gegossen – tipp oben auf „Gegossen“.</p>`}
      </section>

      <div class="btns" style="justify-content:center;margin:20px 0">
        <button class="btn ghost" id="refresh">🔄 Daten neu abrufen</button>
        <button class="btn danger" id="del">🗑 Löschen</button>
      </div>
      ${DIVIDER}
    </main>`;

  document.getElementById("water").addEventListener("click", async () => {
    await api(`plants/${p.id}/water`, { method: "POST", body: {} });
    toast("💧 Danke fürs Gießen!");
    viewDetail(id);
  });
  const uploadFiles = async (files) => {
    if (!files.length) return;
    toast("Foto wird hochgeladen…");
    try {
      for (const f of files) await api(`plants/${p.id}/photos`, { method: "POST", body: { ...(await processPhoto(f)), set_cover: true } });
      toast("📷 Foto gespeichert");
      viewDetail(id);
    } catch (err) { toast(err.message, true); }
  };
  document.getElementById("addphoto").addEventListener("change", (e) => uploadFiles([...e.target.files]));
  document.getElementById("addphoto2").addEventListener("change", (e) => uploadFiles([...e.target.files]));
  document.querySelectorAll(".gallery .g").forEach((g) => g.addEventListener("click", () => lightbox(p, +g.dataset.i)));
  const ri = document.getElementById("refimg");
  if (ri) ri.addEventListener("click", () => showLB(`<img src="${esc(p.ref_image)}"><div class="cap">${esc(info.ref_credit || "Musterbild")}</div>`));
  document.querySelectorAll(".log button").forEach((b) => b.addEventListener("click", async () => {
    await api("waterings/" + b.dataset.w, { method: "DELETE" });
    viewDetail(id);
  }));
  document.getElementById("del").addEventListener("click", async () => {
    if (!confirm(`„${p.name}“ mit allen Fotos löschen?`)) return;
    await api("plants/" + p.id, { method: "DELETE" });
    toast("Gelöscht");
    location.hash = "#/";
  });
  document.getElementById("refresh").addEventListener("click", async (e) => {
    if (!p.species_sci && !p.species_common) { toast("Erst Art oder botanischen Namen eintragen", true); return; }
    e.target.disabled = true;
    e.target.innerHTML = `<span class="spinner"></span> Lade…`;
    try {
      const params = new URLSearchParams();
      if (p.species_common) params.set("title", p.species_common);
      if (p.species_sci) params.set("sci", p.species_sci);
      params.set("refresh", "1");
      const prof = await api("lookup?" + params);
      (prof.warnings || []).forEach((w) => toast(w, true));
      toast("Neue Daten geladen – bitte prüfen & speichern");
      await viewEdit(p.id, prof);
    } catch (err) { toast(err.message, true); e.target.disabled = false; e.target.textContent = "🔄 Daten neu abrufen"; }
  });
}

function showLB(html) {
  const lb = document.getElementById("lightbox");
  lb.innerHTML = `<button class="round x" id="lbx">✕</button>${html}`;
  lb.hidden = false;
  const close = () => { lb.hidden = true; lb.innerHTML = ""; };
  document.getElementById("lbx").onclick = close;
  lb.onclick = (e) => { if (e.target === lb) close(); };
}
function lightbox(p, i) {
  const ph = p.photos[i];
  showLB(`<img src="${esc(ph.url)}"><div class="cap">${fmtDate(ph.taken_at, true)}</div>
    <div class="lbbar">
      ${i > 0 ? `<button class="btn light" id="lbp">←</button>` : ""}
      <button class="btn light" id="lbc">★ Titelbild</button>
      <button class="btn danger" id="lbd">🗑 Löschen</button>
      ${i < p.photos.length - 1 ? `<button class="btn light" id="lbn">→</button>` : ""}
    </div>`);
  const on = (id, fn) => { const el = document.getElementById(id); if (el) el.onclick = fn; };
  on("lbp", () => lightbox(p, i - 1));
  on("lbn", () => lightbox(p, i + 1));
  on("lbc", async () => { await api("photos/" + ph.id, { method: "PUT", body: { cover: true } }); document.getElementById("lightbox").hidden = true; toast("Titelbild gesetzt"); viewDetail(p.id); });
  on("lbd", async () => { if (!confirm("Foto löschen?")) return; await api("photos/" + ph.id, { method: "DELETE" }); document.getElementById("lightbox").hidden = true; viewDetail(p.id); });
}

// ------------------------------------------------------------------ Einstellungen
function viewSettings() {
  const c = state.config;
  const s = c.settings;
  const apis = [
    ["Wikipedia & Wikidata", true, "Beschreibung, Musterbild, botanischer Name. Kein Key nötig.", null, []],
    ["Pl@ntNet", c.plantnet, "Erkennt die Art direkt am Foto (500 Erkennungen/Tag gratis).", "https://my.plantnet.org/", [["PLANTNET_API_KEY", "API-Key"]]],
    ["Perenual", c.perenual, "Licht, Wasser, Gießintervall, Winterhärtezone, Giftigkeit (100 Abfragen/Tag gratis; Antworten werden lokal gespeichert, jede Art kostet nur einmal).", "https://perenual.com/docs/api", [["PERENUAL_API_KEY", "API-Key"]]],
    ["Open Plantbook", c.openplantbook, "Temperatur-, Licht-, Luft- und Bodenfeuchte-Bereiche.", "https://open.plantbook.io/", [["OPENPLANTBOOK_CLIENT_ID", "Client-ID"], ["OPENPLANTBOOK_CLIENT_SECRET", "Client-Secret"]]],
  ];
  $app.innerHTML = `
    <header class="hero slim">${vine("tl")}${vine("tr")}
      <a class="back" href="#/">← Zurück</a>
      <h1>Einstellungen</h1>
      <p class="sub">Winterhärte & Datenquellen</p>
    </header>
    <main class="wrap">
      <section class="panel lift"><h2>${LEAFMARK}Dein Winter</h2>
        <p class="sources" style="margin-top:0">Ob eine Pflanze „winterhart“ ist, hängt davon ab, wie kalt es bei dir wird. In weiten Teilen Deutschlands sind es meist −10 bis −20 °C (Zone 6b–8a). Wer sicher gehen will, rechnet lieber ein paar Grad kälter.</p>
        <label class="f"><span>Tiefste Wintertemperatur bei dir (°C)</span><input class="inp" type="number" step="0.5" id="lmt" value="${esc(s.local_min_temp)}"></label>
        <button class="btn" id="saveS">Speichern & alle Pflanzen neu bewerten</button>
      </section>
      <section class="panel"><h2>${LEAFMARK}Datenquellen</h2>
        ${apis.map(([n, on, d, url, fields]) => `<div class="api"><span class="dot ${on ? "on" : ""}"></span><div style="flex:1;min-width:0"><b>${n}</b> ${on ? "– aktiv" : "– nicht eingerichtet"}<p>${d}</p>
          ${url && !on ? `<p>Kostenlosen Key holen bei <a href="${url}" target="_blank" rel="noopener">${url.replace(/^https:\/\//, "").replace(/\/$/, "")}</a></p>` : ""}
          ${fields.map(([envName, label]) => {
            const src = (c.keys || {})[envName];
            return src === "env"
              ? `<p>✓ ${label} kommt aus dem Container (<code>${envName}</code>)</p>`
              : `<label class="f" style="margin:8px 0 0"><span>${label}</span><input class="inp keyin" type="password" autocomplete="off" data-k="${envName}" placeholder="${src ? "•••••• gespeichert – zum Ändern neu eingeben" : "einfügen…"}"></label>`;
          }).join("")}</div></div>`).join("")}
        ${apis.some((a) => a[4].some(([k]) => (c.keys || {})[k] !== "env")) ? `<button class="btn" id="saveK" style="margin-top:14px">🔑 Keys speichern</button>` : ""}
        <p class="sources">Die Keys werden nur auf deinem Server gespeichert (in <code>/data</code>) und nie an den Browser zurückgeschickt. Ein Key im Container hat Vorrang.</p>
      </section>
      <section class="panel"><h2>${LEAFMARK}Aufs Handy</h2>
        <p class="desc" style="margin:0">Öffne Blattwerk im Handy-Browser und wähle „Zum Home-Bildschirm“. Dann startet es wie eine App, und „Foto“ öffnet direkt die Kamera.</p>
      </section>
      ${DIVIDER}<div class="footer">Blattwerk ${esc(c.version)}</div>
    </main>`;
  document.getElementById("saveK")?.addEventListener("click", async () => {
    const keys = {};
    document.querySelectorAll(".keyin").forEach((i) => { if (i.value.trim()) keys[i.dataset.k] = i.value.trim(); });
    if (!Object.keys(keys).length) { toast("Kein neuer Key eingetragen", true); return; }
    try {
      await api("settings", { method: "PUT", body: { keys } });
      state.config = await api("config");
      toast("🔑 Keys gespeichert");
      viewSettings();
    } catch (err) { toast(err.message, true); }
  });
  document.getElementById("saveS").addEventListener("click", async () => {
    const v = parseFloat(document.getElementById("lmt").value);
    if (isNaN(v)) { toast("Bitte eine Zahl eingeben", true); return; }
    c.settings = await api("settings", { method: "PUT", body: { local_min_temp: v } });
    const r = await api("rehardy", { method: "POST" });
    toast(`Gespeichert · ${r.updated} Pflanzen neu bewertet`);
  });
}

router();
