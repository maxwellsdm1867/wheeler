"""Render a harvested Asta mission as one self-contained HTML page.

The Research Assistant is the long-horizon, goal-driven adapter: unlike the
one-shot Asta tools it runs autonomously for hours and a single harvest lands a
whole BATCH of nodes at once (the mission Document, one work-log Document per
completed unit of work, and every computed artifact under ``work/<slug>/data/``).
Nobody can rule on a dozen outcomes from a terminal summary they have not read,
so every harvest writes this page: the scientist SEES what came back (verdicts,
summaries, the figures the assistant actually produced) before deciding anything.

Why this is a renderer in the package and not the ``wheeler-brief`` skill:

  - It must be there BY DEFAULT, on every harvest, including headless runs. The
    skill is optional in shipped installs, so a brief that depended on it would
    silently not exist for most users.
  - It is deterministic and unit-testable: no model composes a spec.
  - Different job. ``wheeler-brief`` pre-registers a plan ("what will the figure
    look like under each hypothesis"). This answers "what came back, and which of
    it still needs a human".

Leaf module by design: stdlib only, no graph import, no config. It takes the
already-parsed record plus the ingest's curation candidates and returns a
string, so it is testable without Neo4j and cannot break the harvest.

Everything is inlined (CSS, images as data URIs) so the page opens offline from
anywhere, and it renders in light or dark to match the reader's system.
"""

from __future__ import annotations

import base64
import html
import logging
import mimetypes
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

BRIEF_FILENAME = "harvest.html"

# Image artifacts are embedded as data URIs so the page stays self-contained.
# Caps keep it openable: a mission that wrote 200 frames must not produce a
# 400 MB page. Anything past the cap is still LISTED, never silently dropped.
_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}
_MAX_IMAGE_BYTES = 1_500_000
_MAX_EMBEDDED_IMAGES = 12

_VERDICT_KINDS = {
    "accomplished": "ok",
    "partial": "warn",
    "not accomplished": "bad",
}


def _esc(value: Any) -> str:
    """HTML-escape any value. Never raises."""
    return html.escape(str(value if value is not None else ""), quote=True)


def _paragraphs(text: str) -> str:
    """Blank-line separated text into <p> blocks, escaped."""
    if not text or not text.strip():
        return ""
    blocks = [b.strip() for b in text.replace("\r\n", "\n").split("\n\n") if b.strip()]
    return "".join(f"<p>{_esc(b)}</p>" for b in blocks)


def _human_size(num_bytes: int) -> str:
    """Compact byte size for an artifact listing."""
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def _embed_image(path: Path) -> str | None:
    """Return a data URI for an image file, or None if it cannot be embedded."""
    try:
        if not path.is_file():
            return None
        size = path.stat().st_size
        if size == 0 or size > _MAX_IMAGE_BYTES:
            return None
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if not mime.startswith("image/"):
            return None
        payload = base64.b64encode(path.read_bytes()).decode("ascii")
    except (OSError, ValueError):
        logger.debug("harvest_brief: could not embed %s", path, exc_info=True)
        return None
    return f"data:{mime};base64,{payload}"


def _pill(text: str, kind: str) -> str:
    return f'<span class="pill pill-{_esc(kind)}">{_esc(text)}</span>'


def _verdict_pill(verdict: str) -> str:
    if not verdict:
        return _pill("no verdict", "muted")
    return _pill(verdict, _VERDICT_KINDS.get(verdict.lower(), "muted"))


def _review_pill(state: str) -> str:
    if state == "discussed":
        return _pill("discussed", "ok")
    return _pill("not discussed", "todo")


def _node_badge(node_id: str) -> str:
    if not node_id:
        return ""
    return f'<code class="node">{_esc(node_id)}</code>'


def _render_artifacts(item: dict, embedded: list[int]) -> str:
    """Figures inline, everything else as a compact file listing."""
    files = [Path(p) for p in item.get("data_files") or []]
    if not files:
        return ""
    figures: list[str] = []
    rows: list[str] = []
    node_ids = list(item.get("data_ids") or [])
    for i, path in enumerate(files):
        node_id = node_ids[i] if i < len(node_ids) else ""
        uri = None
        if path.suffix.lower() in _IMAGE_EXTS and embedded[0] < _MAX_EMBEDDED_IMAGES:
            uri = _embed_image(path)
            if uri:
                embedded[0] += 1
        if uri:
            figures.append(
                '<figure class="fig">'
                f'<img src="{uri}" alt="{_esc(path.name)}" loading="lazy">'
                f"<figcaption>{_esc(path.name)} {_node_badge(node_id)}</figcaption>"
                "</figure>"
            )
            continue
        try:
            size = _human_size(path.stat().st_size) if path.is_file() else "missing"
        except OSError:
            size = "unreadable"
        rows.append(
            f"<li>{_esc(path.name)} <span class='dim'>{_esc(size)}</span> "
            f"{_node_badge(node_id)}</li>"
        )

    out = ""
    if figures:
        out += f'<div class="figs">{"".join(figures)}</div>'
    if rows:
        out += (
            f'<details class="files"><summary>{len(rows)} more artifact'
            f'{"s" if len(rows) != 1 else ""}</summary><ul>{"".join(rows)}</ul></details>'
        )
    return out


def _render_item(item: dict, embedded: list[int]) -> str:
    title = item.get("title") or item.get("slug") or "work item"
    summary = item.get("summary") or ""
    root_cause = item.get("root_cause") or ""
    state = item.get("review_state") or "undiscussed"
    classes = "card" + (" card-todo" if state != "discussed" else "")
    head = (
        f'<div class="card-head"><h3>{_esc(title)}</h3>'
        f'<div class="pills">{_verdict_pill(item.get("verdict", ""))}'
        f'{_review_pill(state)}</div></div>'
    )
    meta = (
        f'<div class="meta">{_node_badge(item.get("document_id", ""))}'
        f'<span class="dim">{_esc(item.get("slug", ""))}</span></div>'
    )
    body = _paragraphs(summary) or '<p class="dim">No result summary recorded.</p>'
    if root_cause:
        body += (
            '<details class="why"><summary>Root cause</summary>'
            f"{_paragraphs(root_cause)}</details>"
        )
    return (
        f'<section class="{classes}">{head}{meta}{body}'
        f"{_render_artifacts(item, embedded)}</section>"
    )


_STYLE = """
:root{color-scheme:light dark;--bg:#fbfbfa;--fg:#1c1c1a;--dim:#6b6b66;
--line:#e2e2dd;--card:#fff;--accent:#2f5f8f;--todo:#a8620a;--todo-bg:#fdf3e6;
--ok:#2c6e49;--ok-bg:#e9f3ec;--warn:#8a6d1f;--warn-bg:#faf3df;--bad:#9b3232;
--bad-bg:#f8eaea;--code:#f2f2ef}
@media (prefers-color-scheme:dark){:root{--bg:#16161a;--fg:#e8e8e4;--dim:#9a9a94;
--line:#2c2c31;--card:#1d1d22;--accent:#8ab4de;--todo:#e0a35c;--todo-bg:#2e2417;
--ok:#7fc09a;--ok-bg:#182a20;--warn:#d6bd76;--warn-bg:#2a2618;--bad:#e08f8f;
--bad-bg:#2c1b1b;--code:#26262b}}
*{box-sizing:border-box}
body{margin:0;padding:2rem 1.25rem 4rem;background:var(--bg);color:var(--fg);
font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}
.wrap{max-width:52rem;margin:0 auto}
h1{font-size:1.5rem;margin:0 0 .35rem;line-height:1.3}
h2{font-size:1.05rem;margin:2.25rem 0 .75rem;text-transform:uppercase;
letter-spacing:.06em;color:var(--dim)}
h3{font-size:1.05rem;margin:0;line-height:1.35}
p{margin:.55rem 0}
.sub{color:var(--dim);font-size:.9rem;margin:0 0 1.25rem}
.bar{display:flex;flex-wrap:wrap;gap:.4rem 1.25rem;padding:.75rem 0;
border-top:1px solid var(--line);border-bottom:1px solid var(--line);
font-size:.88rem;color:var(--dim)}
.bar b{color:var(--fg);font-weight:600}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;
padding:1rem 1.1rem;margin:.85rem 0}
.card-todo{border-left:3px solid var(--todo)}
.card-head{display:flex;flex-wrap:wrap;gap:.5rem;align-items:baseline;
justify-content:space-between}
.pills{display:flex;gap:.35rem;flex-wrap:wrap}
.pill{font-size:.72rem;font-weight:600;padding:.15rem .5rem;border-radius:999px;
text-transform:uppercase;letter-spacing:.04em;white-space:nowrap}
.pill-ok{background:var(--ok-bg);color:var(--ok)}
.pill-warn{background:var(--warn-bg);color:var(--warn)}
.pill-bad{background:var(--bad-bg);color:var(--bad)}
.pill-todo{background:var(--todo-bg);color:var(--todo)}
.pill-muted{background:var(--code);color:var(--dim)}
.meta{display:flex;gap:.5rem;align-items:center;margin:.4rem 0 .2rem;font-size:.85rem}
.node{background:var(--code);color:var(--accent);border-radius:4px;
padding:.1rem .35rem;font-size:.8rem;font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
.dim{color:var(--dim);font-size:.85rem}
.figs{display:flex;flex-wrap:wrap;gap:.75rem;margin:.85rem 0 .25rem}
.fig{margin:0;flex:1 1 15rem;min-width:0}
.fig img{max-width:100%;height:auto;border:1px solid var(--line);border-radius:6px;
background:#fff;display:block}
figcaption{color:var(--dim);font-size:.78rem;margin-top:.3rem;
display:flex;gap:.35rem;align-items:center;flex-wrap:wrap}
details{margin:.6rem 0}
summary{cursor:pointer;color:var(--accent);font-size:.88rem}
details ul{margin:.5rem 0 0;padding-left:1.15rem}
details li{margin:.2rem 0;font-size:.9rem}
.next{border:1px dashed var(--line);border-radius:10px;padding:.9rem 1.1rem;
margin-top:1.5rem;font-size:.92rem}
.next code{background:var(--code);padding:.12rem .4rem;border-radius:4px;
font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.85rem}
.empty{color:var(--dim);font-style:italic}
.overflow{overflow-x:auto}
"""


def render_harvest_brief(
    *,
    title: str,
    slug: str,
    goal: str,
    background: str,
    items: list[dict],
    execution_id: str = "",
    mission_document: str = "",
    link_to: str = "",
    generated: str = "",
) -> str:
    """Render the harvest page. Pure function over already-parsed values.

    Args:
        title: The mission title (its Goal's first line).
        slug: The mission slug, which is also the batch key stamped on every
            node the harvest produced.
        goal / background: The project.md sections.
        items: One dict per harvested work-log, as written to ``.harvest.json``
            (slug, title, verdict, status, summary, root_cause, document_id,
            data_ids, data_files, review_state).
        execution_id / mission_document / link_to: The run's anchor nodes.
        generated: ISO timestamp for the page footer.

    Returns:
        A complete HTML document as a string. Never raises on odd input: a
        missing field renders as empty, not as a traceback.
    """
    items = list(items or [])
    pending = [i for i in items if (i.get("review_state") or "undiscussed") != "discussed"]
    embedded = [0]  # boxed counter shared across cards, capping total embeds

    cards = "".join(_render_item(i, embedded) for i in items)
    if not cards:
        cards = (
            '<p class="empty">No completed work items yet. The mission has run but '
            "nothing has a filled Results section, so there is nothing to review.</p>"
        )

    anchors = []
    if execution_id:
        anchors.append(f"Run {_node_badge(execution_id)}")
    if mission_document:
        anchors.append(f"Mission {_node_badge(mission_document)}")
    if link_to:
        anchors.append(f"Seeded from {_node_badge(link_to)}")

    bar = (
        f'<div class="bar"><span><b>{len(items)}</b> work item'
        f'{"s" if len(items) != 1 else ""}</span>'
        f'<span><b>{len(pending)}</b> not discussed</span>'
        f'<span>batch <b>{_esc(slug)}</b></span>'
        + "".join(f"<span>{a}</span>" for a in anchors)
        + "</div>"
    )

    background_html = ""
    if background.strip():
        background_html = (
            "<details><summary>Mission background</summary>"
            f"{_paragraphs(background)}</details>"
        )

    if pending:
        next_step = (
            f"<b>{len(pending)}</b> item{'s' if len(pending) != 1 else ''} "
            "still need a human read. Nothing here is a Finding yet: a work-log is "
            "a saved narrative, not an endorsed result. When you have time, run "
            f"<code>/wh:discuss {_esc(slug)}</code> to go through them together and "
            "decide which become Findings."
        )
    else:
        next_step = (
            "Every item in this batch has been discussed. Run "
            f"<code>/wh:discuss {_esc(slug)}</code> again to revisit, or "
            "<code>/wh:close</code> to wrap the session."
        )

    footer = f'<p class="dim">Harvested {_esc(generated)}.</p>' if generated else ""

    return (
        "<!doctype html>\n"
        '<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>Asta mission harvest: {_esc(title)}</title>"
        f"<style>{_STYLE}</style></head><body><div class=\"wrap\">"
        f"<h1>{_esc(title)}</h1>"
        f'<p class="sub">Asta Research Assistant mission harvest</p>'
        f"{bar}"
        f"{_paragraphs(goal) if goal.strip() else ''}"
        f"{background_html}"
        f"<h2>What came back</h2>"
        f"{cards}"
        f'<div class="next">{next_step}</div>'
        f"{footer}"
        "</div></body></html>"
    )


def write_harvest_brief(mission_dir: Path | str, html_text: str) -> str | None:
    """Write the brief to ``<mission>/harvest.html``. Best-effort, never raises.

    Returns the written path, or None when it could not be written (a read-only
    mission directory must not fail a harvest that already wrote the graph).
    """
    try:
        out = Path(mission_dir) / BRIEF_FILENAME
        out.write_text(html_text, encoding="utf-8")
        return str(out)
    except OSError:
        logger.warning(
            "harvest_brief: could not write the brief (best-effort)", exc_info=True
        )
        return None
