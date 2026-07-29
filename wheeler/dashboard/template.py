"""The self-contained HTML/CSS/JS shell for the research dashboard.

A single ``string.Template`` with ``$SLOTS`` that ``render.py`` fills. Kept as a
module-string constant (not a data file) so it ships with the package with zero
packaging surface and ``render.py`` stays import-only and stdlib-only.

No ``$`` appears in the CSS or JS below (only in the template slots), so
``string.Template`` substitution is unambiguous. The JS avoids template literals
for the same reason.
"""
from __future__ import annotations

DASHBOARD_TEMPLATE = """<!DOCTYPE html>
<html lang="en" data-theme="auto">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>$TITLE</title>
<style>
:root {
  --bg: #f6f7f9; --panel: #ffffff; --ink: #1c2330; --muted: #5b6472;
  --line: #d8dde5; --accent: #2f6df0; --accent-ink: #ffffff;
  --pill-bg: #eef1f6; --shadow: 0 1px 3px rgba(20,30,50,.10);
  --q: #7c4dff; --pl: #0a8f6b; --f: #d9730d; --warn: #b25000; --stale: #b00020;
}
html[data-theme="dark"] {
  --bg: #11151c; --panel: #1a212c; --ink: #e7ecf3; --muted: #9aa6b6;
  --line: #2a3340; --accent: #5b8cff; --accent-ink: #0b0e13;
  --pill-bg: #232c39; --shadow: 0 1px 3px rgba(0,0,0,.45);
  --q: #b39dff; --pl: #4fd2a8; --f: #f6a96b; --warn: #ffb86b; --stale: #ff6b81;
}
/* auto: follow the OS preference when no explicit choice is made */
@media (prefers-color-scheme: dark) {
  html[data-theme="auto"] {
    --bg: #11151c; --panel: #1a212c; --ink: #e7ecf3; --muted: #9aa6b6;
    --line: #2a3340; --accent: #5b8cff; --accent-ink: #0b0e13;
    --pill-bg: #232c39; --shadow: 0 1px 3px rgba(0,0,0,.45);
    --q: #b39dff; --pl: #4fd2a8; --f: #f6a96b; --warn: #ffb86b; --stale: #ff6b81;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--bg); color: var(--ink);
  font: 15px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}
a { color: var(--accent); }
.wrap { max-width: 1280px; margin: 0 auto; padding: 18px; }
header.top {
  display: flex; align-items: center; gap: 14px; flex-wrap: wrap;
  padding-bottom: 12px; border-bottom: 1px solid var(--line); margin-bottom: 16px;
}
header.top h1 { font-size: 20px; margin: 0; }
.gen { color: var(--muted); font-size: 13px; }
.counts { display: flex; gap: 8px; flex-wrap: wrap; }
.count { background: var(--pill-bg); border-radius: 999px; padding: 3px 11px; font-size: 13px; }
.count b { color: var(--ink); }
.spacer { flex: 1 1 auto; }
.toolbtn {
  background: var(--panel); color: var(--ink); border: 1px solid var(--line);
  border-radius: 8px; padding: 6px 12px; font-size: 13px; cursor: pointer;
}
.toolbtn:hover { border-color: var(--accent); }
.toolbtn:focus-visible, a:focus-visible, summary:focus-visible, textarea:focus-visible {
  outline: 3px solid var(--accent); outline-offset: 2px;
}
#filter {
  background: var(--panel); color: var(--ink); border: 1px solid var(--line);
  border-radius: 8px; padding: 6px 12px; font-size: 13px; min-width: 200px;
}
/* hero */
section.hero { margin-bottom: 16px; }
.hero-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 14px; }
.zone-h { display: flex; align-items: baseline; gap: 8px; margin: 0 0 10px; font-size: 16px; }
.zone-h .badge-count { color: var(--muted); font-size: 13px; font-weight: 400; }
/* four corners */
.zones { display: grid; grid-template-columns: 1fr 1fr; grid-template-rows: auto auto; gap: 16px; }
@media (max-width: 900px) { .zones { grid-template-columns: 1fr; } }
section.zone {
  background: var(--panel); border: 1px solid var(--line); border-radius: 12px;
  box-shadow: var(--shadow); padding: 14px; min-height: 120px;
}
.card {
  border: 1px solid var(--line); border-radius: 10px; padding: 10px 12px;
  margin-bottom: 10px; background: var(--bg);
}
.card:last-child { margin-bottom: 0; }
.card-head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.card-title { font-weight: 600; }
.empty { color: var(--muted); font-style: italic; }
/* clickable cards -> detail drawer */
.card-open { cursor: pointer; transition: border-color .12s, box-shadow .12s; }
.card-open:hover { border-color: var(--accent); box-shadow: var(--shadow); }
.open-hint { margin-left: auto; color: var(--muted); font-size: 12px; opacity: 0; transition: opacity .15s; }
.card-open:hover .open-hint { opacity: .85; }
/* badges + pills */
.node-id {
  font: 600 12px/1 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  padding: 2px 6px; border-radius: 5px; background: var(--pill-bg); color: var(--ink);
  border: 1px solid var(--line);
}
.node-id.t-Q { color: var(--q); border-color: var(--q); }
.node-id.t-P { color: var(--pl); border-color: var(--pl); }
.node-id.t-F { color: var(--f); border-color: var(--f); }
.node-id[data-nodeid] { cursor: pointer; }
.node-id[data-nodeid]:hover { filter: brightness(1.12); }
#toast {
  position: fixed; bottom: 22px; left: 50%; transform: translateX(-50%);
  background: var(--ink); color: var(--bg); padding: 8px 14px; border-radius: 8px;
  font-size: 13px; opacity: 0; pointer-events: none; transition: opacity .18s; z-index: 80;
}
#toast.show { opacity: 1; }
.nodemenu {
  position: absolute; display: none; background: var(--panel); border: 1px solid var(--line);
  border-radius: 8px; box-shadow: var(--shadow); z-index: 90; min-width: 170px; padding: 4px;
}
.nodemenu.open { display: block; }
.nodemenu button {
  display: block; width: 100%; text-align: left; background: none; border: 0; color: var(--ink);
  padding: 7px 10px; border-radius: 6px; cursor: pointer; font: inherit; font-size: 13px;
}
.nodemenu button:hover { background: var(--pill-bg); }
.pill { font-size: 12px; padding: 2px 9px; border-radius: 999px; background: var(--pill-bg); }
.pill-in-progress { background: #fde9d0; color: #8a4b00; }
.pill-approved { background: #d6f0e4; color: #0a6b4f; }
.pill-prio { background: var(--q); color: #fff; }
.flag-stale { color: var(--stale); font-size: 12px; font-weight: 600; }
.meta { color: var(--muted); font-size: 12px; }
details > summary { cursor: pointer; color: var(--accent); font-size: 13px; margin-top: 6px; }
details[open] > summary { margin-bottom: 6px; }
.desc { margin: 6px 0 0; }
/* figures */
.fig-card { display: flex; flex-direction: column; }
.fig-media { position: relative; background: var(--bg); border-radius: 8px; overflow: hidden; text-align: center; }
.fig-media img { max-width: 100%; height: auto; display: block; margin: 0 auto; cursor: zoom-in; }
.fig-media iframe { width: 100%; height: 360px; border: 0; background: #fff; }
.hero .fig-media iframe { height: 460px; }
.fig-placeholder { padding: 20px; color: var(--muted); font-size: 13px; }
.fig-legend { font-size: 13px; margin: 8px 0 4px; }
.note-wrap { margin-top: 8px; }
.note-wrap label { font-size: 12px; color: var(--muted); display: block; margin-bottom: 3px; }
.note {
  width: 100%; min-height: 44px; resize: vertical; border: 1px solid var(--line);
  border-radius: 8px; padding: 7px 9px; font: inherit; font-size: 13px;
  background: var(--panel); color: var(--ink);
}
.note-row { display: flex; align-items: center; gap: 8px; margin-top: 4px; }
.note-hint { font-size: 11px; color: var(--muted); }
.durable-note {
  margin: 6px 0; padding: 7px 9px; border-left: 3px solid var(--pl);
  background: var(--pill-bg); border-radius: 0 8px 8px 0; font-size: 13px;
}
/* detail drawer */
.drawer-back {
  display: none; position: fixed; inset: 0; background: rgba(8,12,20,.45); z-index: 70;
}
.drawer-back.open { display: block; }
.drawer {
  position: fixed; top: 0; right: 0; height: 100%; width: 460px; max-width: 92vw;
  background: var(--panel); border-left: 1px solid var(--line); box-shadow: -4px 0 24px rgba(0,0,0,.22);
  z-index: 71; transform: translateX(100%); transition: transform .2s ease; overflow-y: auto;
  display: flex; flex-direction: column;
}
.drawer.open { transform: translateX(0); }
@media (prefers-reduced-motion: reduce) { .drawer { transition: none; } }
.drawer-head {
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap; padding: 14px 16px;
  border-bottom: 1px solid var(--line); position: sticky; top: 0; background: var(--panel);
}
.drawer-head .kind { color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .04em; }
.drawer-body { padding: 14px 16px; }
.drawer h3 { margin: 0 0 4px; font-size: 17px; }
.dr-section-h { font-size: 12px; text-transform: uppercase; letter-spacing: .04em; color: var(--muted); margin: 16px 0 6px; }
.dr-content { white-space: pre-wrap; word-wrap: break-word; }
.dr-fields { width: 100%; border-collapse: collapse; font-size: 13px; }
.dr-fields td { padding: 4px 6px; border-bottom: 1px solid var(--line); vertical-align: top; }
.dr-fields td.k { color: var(--muted); width: 38%; }
.dr-fields td.v { word-break: break-word; }
.dr-rels { list-style: none; margin: 0; padding: 0; }
.dr-rel {
  display: flex; align-items: center; gap: 8px; padding: 7px 8px; border: 1px solid var(--line);
  border-radius: 8px; margin-bottom: 6px; background: var(--bg);
}
.dr-rel .rel-type { font-size: 11px; color: var(--muted); font-family: ui-monospace, Menlo, monospace; }
.dr-rel .rel-arrow { color: var(--accent); font-weight: 700; }
.dr-rel .rel-title { flex: 1 1 auto; font-size: 13px; color: var(--ink); }
.dr-rel.hop { cursor: pointer; }
.dr-rel.hop:hover { border-color: var(--accent); }
.dr-empty { color: var(--muted); font-style: italic; font-size: 13px; }
.drawer-close {
  background: none; border: 0; color: var(--muted); font-size: 22px; line-height: 1;
  cursor: pointer; padding: 2px 6px; margin-left: auto;
}
.drawer-close:hover { color: var(--ink); }
/* lightbox */
.lightbox {
  display: none; position: fixed; inset: 0; background: rgba(8,12,20,.86);
  z-index: 50; align-items: center; justify-content: center; padding: 24px;
}
.lightbox.open { display: flex; }
.lightbox img { max-width: 96vw; max-height: 92vh; border-radius: 8px; }
/* canvas */
.canvas-overlay {
  display: none; position: fixed; inset: 0; background: var(--bg); z-index: 60; flex-direction: column;
}
.canvas-overlay.open { display: flex; }
.canvas-bar {
  display: flex; align-items: center; gap: 8px; padding: 10px 14px;
  border-bottom: 1px solid var(--line); background: var(--panel);
}
.canvas-bar .title { font-weight: 600; }
.canvas-viewport { flex: 1 1 auto; overflow: hidden; position: relative; cursor: grab; }
.canvas-viewport.panning { cursor: grabbing; }
.canvas-surface { position: absolute; top: 0; left: 0; transform-origin: 0 0; }
.canvas-tile {
  position: absolute; width: 460px; background: var(--panel); border: 1px solid var(--line);
  border-radius: 10px; box-shadow: var(--shadow); padding: 10px;
}
@media (prefers-reduced-motion: reduce) {
  .canvas-surface, .fig-media img { transition: none !important; }
}
footer { margin-top: 22px; padding-top: 12px; border-top: 1px solid var(--line); color: var(--muted); font-size: 12px; }
.legend { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 6px; }
</style>
</head>
<body>
<div class="wrap">
<header class="top">
  <h1>$TITLE</h1>
  <span class="gen">$GENERATED_LINE$PROJECT</span>
  <span class="spacer"></span>
  <div class="counts">$COUNTS_STRIP</div>
  <input id="filter" type="search" placeholder="Filter cards..." aria-label="Filter cards by text">
  <button class="toolbtn" id="refresh" type="button"
    title="Reload to re-query the knowledge graph for the latest data">Refresh</button>
  <button class="toolbtn" id="canvas-open" type="button">Open canvas</button>
  <button class="toolbtn" id="theme-toggle" type="button" aria-label="Cycle light, dark, or auto theme">Theme</button>
</header>

$HERO_HTML

<div class="zones">
  <section class="zone" aria-labelledby="z-questions">
    <h2 class="zone-h" id="z-questions">Open Questions <span class="badge-count">$Q_COUNT</span></h2>
    $QUESTIONS_HTML
  </section>
  <section class="zone" aria-labelledby="z-plans">
    <h2 class="zone-h" id="z-plans">Open Plans <span class="badge-count">$PL_COUNT</span></h2>
    $PLANS_HTML
  </section>
  <section class="zone" aria-labelledby="z-results">
    <h2 class="zone-h" id="z-results">Major Results <span class="badge-count">$R_COUNT</span></h2>
    $RESULTS_HTML
  </section>
  <section class="zone" aria-labelledby="z-figures">
    <h2 class="zone-h" id="z-figures">Figures <span class="badge-count">$F_COUNT</span></h2>
    $FIGURES_HTML
  </section>
</div>

<footer>$FOOTER</footer>
</div>

<div class="lightbox" id="lightbox" role="dialog" aria-modal="true" aria-label="Figure zoom">
  <img id="lightbox-img" src="" alt="">
</div>

<script type="application/json" id="wh-details">$DETAILS_JSON</script>
<div class="drawer-back" id="drawer-back"></div>
<aside class="drawer" id="drawer" role="dialog" aria-modal="true" aria-labelledby="drawer-title" aria-hidden="true">
  <div class="drawer-head">
    <span class="kind" id="drawer-kind"></span>
    <span id="drawer-badge"></span>
    <button class="drawer-close" id="drawer-close" type="button" aria-label="Close details">&times;</button>
  </div>
  <div class="drawer-body" id="drawer-body"></div>
</aside>

<div id="toast" role="status" aria-live="polite"></div>

<div class="nodemenu" id="nodemenu" role="menu" aria-label="Node actions">
  <button type="button" data-copy="ref" role="menuitem">Copy reference [id]</button>
  <button type="button" data-copy="id" role="menuitem">Copy node id</button>
</div>

<div class="canvas-overlay" id="canvas" role="dialog" aria-modal="true" aria-label="Figure canvas">
  <div class="canvas-bar">
    <span class="title">Figure canvas</span>
    <button class="toolbtn" type="button" data-canvas="zoomout" aria-label="Zoom out">-</button>
    <button class="toolbtn" type="button" data-canvas="zoomin" aria-label="Zoom in">+</button>
    <button class="toolbtn" type="button" data-canvas="reset">Fit</button>
    <span class="spacer"></span>
    <span class="note-hint">drag to pan, wheel to zoom, arrows to pan, Esc to close</span>
    <button class="toolbtn" type="button" data-canvas="close">Close</button>
  </div>
  <div class="canvas-viewport" id="canvas-viewport" tabindex="0">
    <div class="canvas-surface" id="canvas-surface"></div>
  </div>
</div>

<script>
(function () {
  "use strict";
  var PROJECT = $PROJECT_JSON;
  var noteKey = function (id) { return "wh-note:" + PROJECT + ":" + id; };

  // --- clipboard + toast ---
  function copyText(t) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(t);
    } else {
      var ta = document.createElement("textarea");
      ta.value = t; ta.style.position = "fixed"; ta.style.opacity = "0";
      document.body.appendChild(ta); ta.select();
      try { document.execCommand("copy"); } catch (e) {}
      document.body.removeChild(ta);
    }
  }
  var toastEl = document.getElementById("toast");
  function toast(msg) {
    toastEl.textContent = msg; toastEl.classList.add("show");
    clearTimeout(toastEl._t);
    toastEl._t = setTimeout(function () { toastEl.classList.remove("show"); }, 1400);
  }

  // --- copyable node badges: click/Enter copies [ID]; right-click for options ---
  function badgeOf(t) { return t && t.closest ? t.closest(".node-id[data-nodeid]") : null; }
  document.addEventListener("click", function (ev) {
    var b = badgeOf(ev.target);
    if (!b) return;
    var id = b.getAttribute("data-nodeid");
    copyText("[" + id + "]"); toast("Copied [" + id + "]");
  });
  document.addEventListener("keydown", function (ev) {
    if (ev.key !== "Enter" && ev.key !== " ") return;
    var b = ev.target;
    if (!b.classList || !b.classList.contains("node-id") || !b.getAttribute("data-nodeid")) return;
    ev.preventDefault();
    var id = b.getAttribute("data-nodeid");
    copyText("[" + id + "]"); toast("Copied [" + id + "]");
  });
  var nodemenu = document.getElementById("nodemenu");
  var menuId = null;
  document.addEventListener("contextmenu", function (ev) {
    var b = badgeOf(ev.target);
    if (!b) return;
    ev.preventDefault();
    menuId = b.getAttribute("data-nodeid");
    nodemenu.style.left = ev.pageX + "px";
    nodemenu.style.top = ev.pageY + "px";
    nodemenu.classList.add("open");
  });
  nodemenu.addEventListener("click", function (ev) {
    var act = ev.target.getAttribute && ev.target.getAttribute("data-copy");
    if (!act || !menuId) return;
    var val = act === "ref" ? "[" + menuId + "]" : menuId;
    copyText(val); toast("Copied " + val);
    nodemenu.classList.remove("open");
  });
  document.addEventListener("click", function () { nodemenu.classList.remove("open"); });

  // --- theme: light / dark / auto (auto follows the OS via CSS media query) ---
  var THEME_KEY = "wh-dash-theme";
  var THEMES = ["light", "dark", "auto"];
  // --- refresh: reload the file from disk (re-run `wheeler dashboard` for fresh graph data) ---
  var rb = document.getElementById("refresh");
  if (rb) rb.addEventListener("click", function () { location.reload(); });

  var tt = document.getElementById("theme-toggle");
  function setTheme(t) {
    document.documentElement.setAttribute("data-theme", t);
    if (tt) tt.textContent = "Theme: " + t;
    try { localStorage.setItem(THEME_KEY, t); } catch (e) {}
  }
  var saved = "auto";
  try { saved = localStorage.getItem(THEME_KEY) || "auto"; } catch (e) {}
  if (THEMES.indexOf(saved) === -1) saved = "auto";
  setTheme(saved);
  if (tt) tt.addEventListener("click", function () {
    var cur = document.documentElement.getAttribute("data-theme");
    var next = THEMES[(THEMES.indexOf(cur) + 1) % THEMES.length];
    setTheme(next);
  });

  // --- notes: seed from localStorage, autosave, sync instances sharing a figid ---
  function allNotes(id) {
    return Array.prototype.slice.call(document.querySelectorAll('textarea.note[data-figid="' + id + '"]'));
  }
  Array.prototype.forEach.call(document.querySelectorAll("textarea.note"), function (ta) {
    var id = ta.getAttribute("data-figid");
    try {
      var v = localStorage.getItem(noteKey(id));
      // Only seed from local storage when the server-rendered durable note is
      // empty, so a durable note (set via `wheeler dashboard note`) is never
      // clobbered by a stale or empty browser-local value.
      if (v && !ta.value) ta.value = v;
    } catch (e) {}
  });
  document.addEventListener("input", function (ev) {
    var ta = ev.target;
    if (!ta.classList || !ta.classList.contains("note")) return;
    var id = ta.getAttribute("data-figid");
    try { localStorage.setItem(noteKey(id), ta.value); } catch (e) {}
    allNotes(id).forEach(function (other) { if (other !== ta) other.value = ta.value; });
  });
  document.addEventListener("click", function (ev) {
    var b = ev.target;
    if (!b.classList || !b.classList.contains("note-copy")) return;
    var id = b.getAttribute("data-figid");
    var ta = document.querySelector('textarea.note[data-figid="' + id + '"]');
    if (ta && navigator.clipboard) navigator.clipboard.writeText(ta.value);
  });

  // --- filter ---
  var fi = document.getElementById("filter");
  if (fi) fi.addEventListener("input", function () {
    var q = fi.value.trim().toLowerCase();
    Array.prototype.forEach.call(document.querySelectorAll(".card"), function (c) {
      c.style.display = (!q || c.textContent.toLowerCase().indexOf(q) !== -1) ? "" : "none";
    });
  });

  // --- lightbox ---
  var lb = document.getElementById("lightbox"), lbi = document.getElementById("lightbox-img");
  var lbTrigger = null;
  function openLB(src, alt) {
    lbi.src = src; lbi.alt = alt || ""; lb.classList.add("open"); lb.focus();
  }
  function closeLB() {
    lb.classList.remove("open"); lbi.src = "";
    if (lbTrigger) { lbTrigger.focus(); lbTrigger = null; }
  }
  document.addEventListener("click", function (ev) {
    var img = ev.target;
    if (img.tagName === "IMG" && img.closest && img.closest(".fig-media") && !img.closest(".canvas-tile")) {
      lbTrigger = img; openLB(img.src, img.alt);
    } else if (ev.target === lb || ev.target === lbi) { closeLB(); }
  });

  // --- canvas ---
  var canvas = document.getElementById("canvas");
  var surface = document.getElementById("canvas-surface");
  var viewport = document.getElementById("canvas-viewport");
  var view = { x: 40, y: 40, s: 1 };
  var canvasTrigger = null, built = false;
  function applyView() {
    surface.style.transform = "translate(" + view.x + "px," + view.y + "px) scale(" + view.s + ")";
  }
  function buildCanvas() {
    if (built) return;
    var cards = document.querySelectorAll(".fig-card");
    var col = 0, row = 0, perRow = 3;
    Array.prototype.forEach.call(cards, function (card, i) {
      var tile = document.createElement("div");
      tile.className = "canvas-tile";
      tile.style.left = (col * 500) + "px";
      tile.style.top = (row * 540) + "px";
      tile.innerHTML = card.innerHTML;
      // Strip duplicate ids/for-refs the clone introduces, and avoid embedding
      // interactive iframes twice (double payload + re-running their scripts):
      // replace cloned iframes with a lightweight placeholder.
      Array.prototype.forEach.call(tile.querySelectorAll("[id]"), function (e) { e.removeAttribute("id"); });
      Array.prototype.forEach.call(tile.querySelectorAll("label[for]"), function (e) { e.removeAttribute("for"); });
      Array.prototype.forEach.call(tile.querySelectorAll("iframe"), function (fr) {
        var ph = document.createElement("div");
        ph.className = "fig-placeholder";
        ph.textContent = "Interactive figure (open from the main view)";
        fr.parentNode.replaceChild(ph, fr);
      });
      surface.appendChild(tile);
      col++; if (col >= perRow) { col = 0; row++; }
    });
    built = true;
  }
  function openCanvas() {
    buildCanvas(); canvas.classList.add("open"); view = { x: 40, y: 40, s: 1 }; applyView();
    viewport.focus();
  }
  function closeCanvas() {
    canvas.classList.remove("open");
    if (canvasTrigger) { canvasTrigger.focus(); canvasTrigger = null; }
  }
  var co = document.getElementById("canvas-open");
  if (co) co.addEventListener("click", function () { canvasTrigger = co; openCanvas(); });
  canvas.addEventListener("click", function (ev) {
    var act = ev.target.getAttribute && ev.target.getAttribute("data-canvas");
    if (act === "close") closeCanvas();
    else if (act === "zoomin") { view.s = Math.min(4, view.s * 1.2); applyView(); }
    else if (act === "zoomout") { view.s = Math.max(0.2, view.s / 1.2); applyView(); }
    else if (act === "reset") { view = { x: 40, y: 40, s: 1 }; applyView(); }
  });
  viewport.addEventListener("wheel", function (ev) {
    if (!canvas.classList.contains("open")) return;
    ev.preventDefault();
    var f = ev.deltaY < 0 ? 1.1 : 1 / 1.1;
    view.s = Math.max(0.2, Math.min(4, view.s * f)); applyView();
  }, { passive: false });
  var drag = null;
  viewport.addEventListener("mousedown", function (ev) {
    if (ev.target.closest && ev.target.closest("textarea, button, a")) return;
    drag = { x: ev.clientX, y: ev.clientY, ox: view.x, oy: view.y };
    viewport.classList.add("panning");
  });
  window.addEventListener("mousemove", function (ev) {
    if (!drag) return;
    view.x = drag.ox + (ev.clientX - drag.x); view.y = drag.oy + (ev.clientY - drag.y); applyView();
  });
  window.addEventListener("mouseup", function () { drag = null; viewport.classList.remove("panning"); });
  viewport.addEventListener("keydown", function (ev) {
    var step = 60;
    if (ev.key === "ArrowLeft") { view.x += step; applyView(); }
    else if (ev.key === "ArrowRight") { view.x -= step; applyView(); }
    else if (ev.key === "ArrowUp") { view.y += step; applyView(); }
    else if (ev.key === "ArrowDown") { view.y -= step; applyView(); }
    else if (ev.key === "+" || ev.key === "=") { view.s = Math.min(4, view.s * 1.2); applyView(); }
    else if (ev.key === "-") { view.s = Math.max(0.2, view.s / 1.2); applyView(); }
  });

  // --- detail drawer: click any card to open full content + metadata + links ---
  var details = {};
  try {
    var dEl = document.getElementById("wh-details");
    if (dEl) details = JSON.parse(dEl.textContent || "{}");
  } catch (e) { details = {}; }

  var drawer = document.getElementById("drawer");
  var drawerBack = document.getElementById("drawer-back");
  var drawerBody = document.getElementById("drawer-body");
  var drawerKind = document.getElementById("drawer-kind");
  var drawerBadgeBox = document.getElementById("drawer-badge");
  var drawerTrigger = null;

  function prefixOf(id) { return id.indexOf("-") >= 0 ? id.charAt(0).toUpperCase() : ""; }
  function makeBadge(id) {
    var s = document.createElement("span");
    var p = prefixOf(id);
    s.className = "node-id" + (p ? " t-" + p : "");
    s.setAttribute("data-nodeid", id);
    s.setAttribute("role", "button");
    s.setAttribute("tabindex", "0");
    s.setAttribute("title", "Click to copy [" + id + "]");
    s.textContent = id;
    return s;
  }
  function idLabel(id) {  // non-copyable colored id, for relationship rows
    var s = document.createElement("span");
    var p = prefixOf(id);
    s.className = "node-id" + (p ? " t-" + p : "");
    s.textContent = id;
    return s;
  }

  function renderDrawer(id) {
    var d = details[id];
    if (!d) return false;
    drawerKind.textContent = d.kind || "";
    drawerBadgeBox.innerHTML = "";
    drawerBadgeBox.appendChild(makeBadge(id));
    drawerBody.innerHTML = "";

    var h = document.createElement("h3");
    h.textContent = d.title || id;
    drawerBody.appendChild(h);

    if (d.content) {
      var cb = document.createElement("div"); cb.className = "dr-content"; cb.textContent = d.content;
      drawerBody.appendChild(cb);
    }
    if (d.note) {
      var nh = document.createElement("div"); nh.className = "dr-section-h"; nh.textContent = "Note";
      drawerBody.appendChild(nh);
      var nb = document.createElement("div"); nb.className = "durable-note";
      if (d.note_id) { nb.appendChild(idLabel(d.note_id)); nb.appendChild(document.createTextNode(" ")); }
      nb.appendChild(document.createTextNode(d.note));
      drawerBody.appendChild(nb);
    }
    var fields = d.fields || [];
    if (fields.length) {
      var fh = document.createElement("div"); fh.className = "dr-section-h"; fh.textContent = "Metadata";
      drawerBody.appendChild(fh);
      var tbl = document.createElement("table"); tbl.className = "dr-fields";
      fields.forEach(function (kv) {
        var tr = document.createElement("tr");
        var tdk = document.createElement("td"); tdk.className = "k"; tdk.textContent = kv[0];
        var tdv = document.createElement("td"); tdv.className = "v"; tdv.textContent = kv[1];
        tr.appendChild(tdk); tr.appendChild(tdv); tbl.appendChild(tr);
      });
      drawerBody.appendChild(tbl);
    }
    var rh = document.createElement("div"); rh.className = "dr-section-h"; rh.textContent = "Linked nodes";
    drawerBody.appendChild(rh);
    var rels = d.rels || [];
    if (!rels.length) {
      var empty = document.createElement("div"); empty.className = "dr-empty";
      empty.textContent = "No linked nodes."; drawerBody.appendChild(empty);
    } else {
      var ul = document.createElement("ul"); ul.className = "dr-rels";
      rels.forEach(function (r) {
        var li = document.createElement("li");
        var hoppable = !!details[r.id];
        li.className = "dr-rel" + (hoppable ? " hop" : "");
        if (hoppable) li.setAttribute("data-go", r.id);
        li.title = hoppable ? "Open this node" : "Not in the current view";
        var rt = document.createElement("span"); rt.className = "rel-type"; rt.textContent = r.rel || "";
        var ar = document.createElement("span"); ar.className = "rel-arrow";
        ar.textContent = r.dir === "out" ? "\\u2192" : "\\u2190";
        var title = document.createElement("span"); title.className = "rel-title";
        title.textContent = r.title || (r.label ? "(" + r.label + ")" : "");
        li.appendChild(rt); li.appendChild(ar); li.appendChild(title); li.appendChild(idLabel(r.id));
        ul.appendChild(li);
      });
      drawerBody.appendChild(ul);
    }
    return true;
  }

  function openDrawer(id, trigger) {
    if (!renderDrawer(id)) return;
    if (trigger) drawerTrigger = trigger;
    drawerBack.classList.add("open");
    drawer.classList.add("open");
    drawer.setAttribute("aria-hidden", "false");
    drawerBody.scrollTop = 0;
    var cl = document.getElementById("drawer-close");
    if (cl) cl.focus();
  }
  function closeDrawer() {
    drawer.classList.remove("open");
    drawerBack.classList.remove("open");
    drawer.setAttribute("aria-hidden", "true");
    if (drawerTrigger) { try { drawerTrigger.focus(); } catch (e) {} drawerTrigger = null; }
  }

  // Open the drawer on a card click, but never steal clicks meant for a badge
  // (copy), the figure image (lightbox), or the note controls.
  document.addEventListener("click", function (ev) {
    var t = ev.target;
    if (t.closest && t.closest(".drawer")) return;
    if (t.closest && t.closest(".node-id[data-nodeid]")) return;     // badge copy
    if (t.tagName === "IMG" && t.closest && t.closest(".fig-media")) return;  // lightbox
    if (t.closest && t.closest("textarea, button, a, summary, label, .note-wrap")) return;
    var card = t.closest && t.closest(".card-open");
    if (!card) return;
    var id = card.getAttribute("data-nodeid");
    if (id && details[id]) openDrawer(id, card);
  });
  drawerBody.addEventListener("click", function (ev) {
    var row = ev.target.closest && ev.target.closest(".dr-rel.hop");
    if (!row) return;
    var go = row.getAttribute("data-go");
    if (go && details[go]) openDrawer(go, drawerTrigger);
  });
  var dc = document.getElementById("drawer-close");
  if (dc) dc.addEventListener("click", closeDrawer);
  drawerBack.addEventListener("click", closeDrawer);

  // --- global escape ---
  document.addEventListener("keydown", function (ev) {
    if (ev.key !== "Escape") return;
    if (nodemenu.classList.contains("open")) nodemenu.classList.remove("open");
    else if (drawer.classList.contains("open")) closeDrawer();
    else if (canvas.classList.contains("open")) closeCanvas();
    else if (lb.classList.contains("open")) closeLB();
  });
})();
</script>
</body>
</html>
"""
