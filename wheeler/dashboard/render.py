"""Pure, deterministic, stdlib-only renderer for the research dashboard.

``render(data) -> (html, missing)`` turns a plain data dict (see
``gather.py`` for how it is assembled from the graph) into one self-contained
HTML string. It imports nothing internal, so it is trivially unit-testable
offline with a hand-built dict (mirrors ``tests/test_render_brief.py``).

Determinism: no ``datetime.now()`` and no unsorted-set/dict iteration. The
timestamp is an input field (``data["generated"]``); list order is preserved as
given by ``gather`` (so pinned hero figures keep their pin order). The same dict
renders identical bytes every time.

Safety: every text field is HTML-escaped via ``esc``/``linkify_nodes``. Figures
are embedded as ``data:`` URIs (raster/SVG) or sandboxed ``<iframe srcdoc>``
(interactive HTML); SVG is never inlined, so it cannot execute script in the
page. Per-image and whole-document byte ceilings guard against blow-up.
"""
from __future__ import annotations

import base64
import html
import json
import mimetypes
import re
from datetime import datetime
from pathlib import Path
from string import Template

from wheeler.dashboard.template import DASHBOARD_TEMPLATE

SCHEMA_VERSION = 1
RASTER_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
INTERACTIVE_EXTS = {".html", ".htm"}
MAX_FIG_BYTES = 8 * 1024 * 1024
MAX_TOTAL_BYTES = 80 * 1024 * 1024
ALT_DESC_CHARS = 120
NODE_ID_RE = re.compile(r"\[([A-Z]{1,2}-[0-9a-fA-F]{4,})\]")

_COUNT_ORDER = [("Finding", "findings"), ("OpenQuestion", "questions"), ("Plan", "plans")]


# --------------------------------------------------------------------------- text


def esc(value) -> str:
    return html.escape("" if value is None else str(value))


def node_badge(node_id: str) -> str:
    nid = str(node_id)
    prefix = nid.split("-", 1)[0][:1].upper() if "-" in nid else ""
    cls = f"node-id t-{prefix}" if prefix else "node-id"
    return f'<span class="{cls}">{esc(nid)}</span>'


def linkify_nodes(text: str) -> str:
    """Escape text, then wrap [NODE_ID] tokens in styled badges."""
    out, last = [], 0
    s = "" if text is None else str(text)
    for m in NODE_ID_RE.finditer(s):
        out.append(esc(s[last:m.start()]))
        out.append(node_badge(m.group(1)))
        last = m.end()
    out.append(esc(s[last:]))
    return "".join(out)


def pill(label: str, kind: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(kind).lower()).strip("-")
    return f'<span class="pill pill-{slug}">{esc(label)}</span>'


def fmt_date(iso: object) -> str:
    try:
        return datetime.fromisoformat(str(iso).replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return str(iso or "")


def fmt_conf(conf) -> str:
    try:
        c = float(conf)
    except (ValueError, TypeError):
        return ""
    if c <= 0:
        return ""
    return f"conf {c:.2f}"


def alt_text(f: dict) -> str:
    """Deterministic non-empty, non-huge alt text: title, else short description, else id."""
    title = (f.get("title") or "").strip()
    if title:
        return title
    desc = (f.get("description") or "").strip()
    if desc:
        return desc[:ALT_DESC_CHARS]
    return f"Figure {f.get('id', '')}".strip()


# --------------------------------------------------------------------------- figures


def resolve(path: str, root: Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else (root / p)


def embed_figure(path: str, root: Path, alt: str, title: str, budget: dict, missing: list) -> str:
    """Return an HTML fragment embedding one figure. Appends to ``missing`` when
    the file is absent or unembeddable. ``budget`` is ``{"used": int}`` tracked
    across the whole document."""
    if not path:
        missing.append(path or "(no path)")
        return '<div class="fig-placeholder">No figure path.</div>'
    fp = resolve(path, root)
    if not fp.exists():
        missing.append(path)
        return f'<div class="fig-placeholder">Figure file not found:<br><code>{esc(path)}</code></div>'

    ext = fp.suffix.lower()
    try:
        size = fp.stat().st_size
    except OSError:
        size = 0
    if size > MAX_FIG_BYTES or budget["used"] + size > MAX_TOTAL_BYTES:
        missing.append(path)
        return (
            f'<div class="fig-placeholder">Figure too large to embed '
            f'({size // 1024} KB):<br><code>{esc(fp.name)}</code></div>'
        )

    if ext in INTERACTIVE_EXTS:
        content = fp.read_text(encoding="utf-8", errors="replace")
        budget["used"] += len(content.encode("utf-8"))
        srcdoc = content.replace("&", "&amp;").replace('"', "&quot;")
        return (
            f'<iframe sandbox="allow-scripts" loading="lazy" '
            f'title="{esc(title or alt)}" srcdoc="{srcdoc}"></iframe>'
        )

    if ext in RASTER_EXTS or ext == ".svg":
        mime = "image/svg+xml" if ext == ".svg" else (mimetypes.guess_type(fp.name)[0] or "image/png")
        data = fp.read_bytes()
        budget["used"] += len(data)
        b64 = base64.b64encode(data).decode("ascii")
        return f'<img src="data:{mime};base64,{b64}" alt="{esc(alt)}">'

    missing.append(path)
    return f'<div class="fig-placeholder">Unsupported figure type:<br><code>{esc(fp.name)}</code></div>'


# --------------------------------------------------------------------------- cards


def render_question_card(q: dict) -> str:
    prio = q.get("priority")
    prio_pill = pill(f"P{prio}", "prio") if prio is not None else ""
    return (
        '<div class="card">'
        f'<div class="card-head">{node_badge(q.get("id", "?"))}{prio_pill}</div>'
        f'<p class="desc">{linkify_nodes(q.get("question", ""))}</p>'
        "</div>"
    )


def render_plan_card(p: dict) -> str:
    status = p.get("status", "")
    status_pill = pill(status, status) if status else ""
    updated = fmt_date(p.get("updated"))
    path = esc(p.get("path", ""))
    meta = " &middot; ".join(x for x in [f"updated {esc(updated)}" if updated else "", path] if x)
    return (
        '<div class="card">'
        f'<div class="card-head">{node_badge(p.get("id", "?"))}'
        f'<span class="card-title">{esc(p.get("title", "Untitled plan"))}</span>{status_pill}</div>'
        f'<div class="meta">{meta}</div>'
        "</div>"
    )


def render_result_card(f: dict) -> str:
    conf = fmt_conf(f.get("confidence"))
    conf_pill = pill(conf, "conf") if conf else ""
    stale = '<span class="flag-stale">stale</span>' if f.get("stale") else ""
    title = f.get("title") or "Finding"
    desc = str(f.get("description") or "")
    short = desc if len(desc) <= 200 else desc[:200] + "..."
    more = (
        f'<details><summary>More</summary><p class="desc">{linkify_nodes(desc)}</p></details>'
        if len(desc) > 200 else ""
    )
    return (
        '<div class="card">'
        f'<div class="card-head">{node_badge(f.get("id", "?"))}'
        f'<span class="card-title">{esc(title)}</span>{conf_pill}{stale}</div>'
        f'<p class="desc">{linkify_nodes(short)}</p>{more}'
        "</div>"
    )


def render_figure_card(f: dict, root: Path, budget: dict, missing: list, *, hero: bool = False) -> str:
    fid = f.get("id", "")
    title = f.get("title") or "Figure"
    alt = alt_text(f)
    media = embed_figure(f.get("path", ""), root, alt, title, budget, missing)
    conf = fmt_conf(f.get("confidence"))
    conf_pill = pill(conf, "conf") if conf else ""
    desc = str(f.get("description") or "")
    legend = f'<p class="fig-legend">{linkify_nodes(desc)}</p>' if desc else ""
    note = esc(f.get("note") or "")
    cls = "card fig-card hero-card" if hero else "card fig-card"
    return (
        f'<div class="{cls}">'
        f'<div class="card-head">{node_badge(fid)}'
        f'<span class="card-title">{esc(title)}</span>{conf_pill}</div>'
        f'<div class="fig-media" data-figid="{esc(fid)}" data-title="{esc(title)}">{media}</div>'
        f"{legend}"
        '<div class="note-wrap">'
        f'<label for="note-{esc(fid)}">Note</label>'
        f'<textarea id="note-{esc(fid)}" class="note" data-figid="{esc(fid)}" '
        f'placeholder="Add a note...">{note}</textarea>'
        '<div class="note-row">'
        f'<button type="button" class="toolbtn note-copy" data-figid="{esc(fid)}">Copy</button>'
        '<span class="note-hint">saved in this browser; '
        "use <code>wheeler dashboard note</code> to make it durable</span></div>"
        "</div>"
        "</div>"
    )


# --------------------------------------------------------------------------- assembly


def _zone(cards: list[str], empty: str) -> str:
    return "".join(cards) if cards else f'<p class="empty">{empty}</p>'


def render(data: dict) -> tuple[str, list[str]]:
    """Render the dashboard. Returns ``(html, missing_figure_paths)``."""
    meta = data.get("meta") or {}
    root = Path(meta.get("project_root") or ".").resolve()
    missing: list[str] = []
    budget = {"used": 0}

    project = data.get("project") or ""
    project_label = f" &middot; project: {esc(project)}" if project else ""
    gen = fmt_date(data.get("generated"))
    when = esc(gen) if gen else "unknown time"
    gen_line = f"Snapshot of the knowledge graph &middot; generated {when}"

    counts = data.get("counts") or {}
    count_chips = "".join(
        f'<span class="count"><b>{esc(counts.get(key, 0))}</b> {esc(label)}</span>'
        for key, label in _COUNT_ORDER
    )

    questions = data.get("questions") or []
    plans = data.get("plans") or []
    results = data.get("results") or []
    figures = data.get("figures") or []
    hero = data.get("hero") or []

    hero_cards = [render_figure_card(f, root, budget, missing, hero=True) for f in hero]
    hero_html = (
        '<section class="hero" aria-labelledby="z-hero">'
        f'<h2 class="zone-h" id="z-hero">Main Figures <span class="badge-count">{len(hero)}</span></h2>'
        f'<div class="hero-grid">{"".join(hero_cards)}</div></section>'
        if hero else ""
    )

    questions_html = _zone(
        [render_question_card(q) for q in questions], "No open questions recorded yet."
    )
    plans_html = _zone(
        [render_plan_card(p) for p in plans], "No open plans (approved or in-progress)."
    )
    results_html = _zone(
        [render_result_card(f) for f in results], "No findings recorded yet."
    )
    figures_html = _zone(
        [render_figure_card(f, root, budget, missing) for f in figures], "No result figures yet."
    )

    footer = (
        "Wheeler research dashboard: a read-only snapshot generated from the "
        "knowledge graph. Regenerate with <code>wheeler dashboard</code> "
        "(use Refresh to reload this file after regenerating). "
        'Badges: <span class="node-id t-Q">Q-</span> question, '
        '<span class="node-id t-P">PL-</span> plan, '
        '<span class="node-id t-F">F-</span> finding. '
        'Notes edited here are local to this browser unless saved with '
        "<code>wheeler dashboard note</code>."
    )

    out = Template(DASHBOARD_TEMPLATE).safe_substitute(
        TITLE=esc(data.get("title") or "Wheeler Research Dashboard"),
        GENERATED_LINE=gen_line,
        PROJECT=project_label,
        PROJECT_JSON=json.dumps(project),
        COUNTS_STRIP=count_chips,
        HERO_HTML=hero_html,
        QUESTIONS_HTML=questions_html,
        PLANS_HTML=plans_html,
        RESULTS_HTML=results_html,
        FIGURES_HTML=figures_html,
        Q_COUNT=str(len(questions)),
        PL_COUNT=str(len(plans)),
        R_COUNT=str(len(results)),
        F_COUNT=str(len(figures)),
        FOOTER=footer,
    )
    return out, missing
