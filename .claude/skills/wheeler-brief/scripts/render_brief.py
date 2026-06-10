#!/usr/bin/env python3
"""Render a Wheeler research-brief spec JSON into one self-contained HTML file.

Deterministic and stdlib-only. Claude composes the spec (including hand-drawn mockup
SVGs); this script only turns that spec into HTML from assets/template.html.

Usage:
    render_brief.py SPEC_JSON [-o OUT_HTML]

Exit codes:
    0  rendered cleanly
    1  spec invalid (bad JSON, unknown spec_version, missing required field); nothing written
    2  rendered, but some figure image files were missing or unembeddable (placeholders used)

See ../references/spec-schema.md for the full schema.
"""
from __future__ import annotations

import argparse
import base64
import html
import json
import mimetypes
import re
import sys
from datetime import datetime
from pathlib import Path
from string import Template

SUPPORTED_VERSION = 1
RASTER_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
WARN_BYTES = 25 * 1024 * 1024
NODE_ID_RE = re.compile(r"\[([A-Z]{1,2}-[0-9a-fA-F]{4,})\]")
TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "assets" / "template.html"


class SpecError(Exception):
    """Raised for unrecoverable spec problems (exit 1)."""


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
    for m in NODE_ID_RE.finditer(text):
        out.append(esc(text[last:m.start()]))
        out.append(node_badge(m.group(1)))
        last = m.end()
    out.append(esc(text[last:]))
    return "".join(out)


def paragraphs(text) -> str:
    if not text:
        return ""
    blocks = [b.strip() for b in str(text).split("\n\n") if b.strip()]
    return "".join(f"<p>{linkify_nodes(b)}</p>" for b in blocks)


def pill(label: str, kind: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(kind).lower()).strip("-")
    return f'<span class="pill pill-{slug}">{esc(label)}</span>'


# --------------------------------------------------------------------------- svg / img


def safe_svg(svg: str) -> str | None:
    s = (svg or "").strip()
    if not s.startswith("<svg") or "<script" in s.lower():
        return None
    return s


def resolve(path: str, root: Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else (root / p)


def embed_image(image_path: str, root: Path, alt: str) -> tuple[str, bool]:
    """Return (html, ok). ok=False means the file was missing/unembeddable."""
    fp = resolve(image_path, root)
    if not fp.exists():
        return (
            f'<div class="fig-placeholder">Figure file not found:'
            f'<br><code>{esc(image_path)}</code></div>',
            False,
        )
    ext = fp.suffix.lower()
    if ext == ".svg":
        text = fp.read_text(encoding="utf-8", errors="replace")
        if "<script" not in text.lower():
            return (re.sub(r"^<\?xml[^>]*\?>\s*", "", text.strip()), True)
        # fall through to data-uri for script-bearing svg
    if ext == ".pdf":
        return (
            f'<div class="fig-placeholder">PDF figure (not embedded):'
            f'<br><a href="file://{esc(str(fp))}">{esc(fp.name)}</a></div>',
            True,
        )
    if ext in RASTER_EXTS or ext == ".svg":
        mime = mimetypes.guess_type(fp.name)[0] or "application/octet-stream"
        b64 = base64.b64encode(fp.read_bytes()).decode("ascii")
        return (f'<img src="data:{mime};base64,{b64}" alt="{esc(alt)}">', True)
    return (
        f'<div class="fig-placeholder">Unsupported figure type:'
        f'<br><code>{esc(fp.name)}</code></div>',
        False,
    )


# --------------------------------------------------------------------------- sections


def render_rationale(rationale: dict) -> tuple[str, str]:
    summary = paragraphs((rationale or {}).get("summary")) or "<p>No rationale recorded.</p>"
    sci = (rationale or {}).get("scientific_reasoning")
    if sci:
        sci_html = (
            '<details class="card"><summary>Scientific reasoning</summary>'
            f"{paragraphs(sci)}</details>"
        )
    else:
        sci_html = ""
    return summary, sci_html


def render_game_plan(gp: dict) -> str:
    """A simple, scannable bulleted execution plan.

    Leads with the steps as plain bullets (this is what the scientist reads first),
    each tagged with who runs it and any decision checkpoint inline. A short
    'decisions to make' callout sits above only when the plan has real judgment
    points, so the page does not bury the question and figures under task machinery.
    """
    gp = gp or {}
    parts: list[str] = []

    decisions = gp.get("decisions") or []
    if decisions:
        items = []
        for d in decisions:
            res = d.get("resolution")
            tail = (
                f' <span class="decision-resolution">&rarr; {linkify_nodes(str(res))}</span>'
                if res else ' <span class="pill pill-pending">to decide</span>'
            )
            items.append(f"<li>{linkify_nodes(str(d.get('text', '')))}{tail}</li>")
        parts.append(
            '<div class="decisions"><h3>Decisions to make</h3><ul>'
            + "".join(items) + "</ul></div>"
        )

    tasks = gp.get("tasks") or []
    if not tasks:
        if not decisions:
            return '<p class="fig-caption">No execution steps recorded in this plan yet.</p>'
        return "".join(parts)

    items = []
    for t in sorted(tasks, key=lambda x: (int(x.get("wave", 1)), x.get("n", 0))):
        items.append(render_step(t))
    parts.append(f'<ol class="step-list">{"".join(items)}</ol>')
    return "".join(parts)


def render_step(t: dict) -> str:
    """One execution step as a bullet: title, who runs it, inline checkpoint."""
    assignee = str(t.get("assignee", "wheeler")).lower()
    status = str(t.get("status", "pending")).lower()
    title = esc(t.get("title", "untitled step"))
    checkpoint = t.get("checkpoint")
    cp_html = (
        f'<span class="step-checkpoint">&#9873; decide if {esc(checkpoint)}</span>'
        if checkpoint else ""
    )
    done_cls = " step-done" if status == "done" else ""
    status_mark = ""
    if status == "done":
        status_mark = '<span class="step-mark">&#10003;</span>'
    elif status == "flagged":
        status_mark = '<span class="step-mark step-mark-flag">&#9873;</span>'
    elif status == "skipped":
        status_mark = '<span class="step-mark step-mark-skip">&ndash;</span>'
    return (
        f'<li class="step{done_cls}">{status_mark}'
        f'<span class="step-title">{title}</span> '
        f'<span class="assignee assignee-{esc(assignee)}">{esc(assignee)}</span>'
        f"{cp_html}</li>"
    )


def render_sub_questions(subqs: list) -> str:
    """Sub-questions under the headline question: the decomposition the scientist will
    actually chase. Each may cite a [Q-xxxx] OpenQuestion node."""
    if not subqs:
        return ""
    items = []
    for sq in subqs:
        if isinstance(sq, dict):
            badge = node_badge(sq["node"]) + " " if sq.get("node") else ""
            text = linkify_nodes(str(sq.get("text", "")))
        else:
            badge, text = "", linkify_nodes(str(sq))
        items.append(f"<li>{badge}{text}</li>")
    return f'<ul class="subq-list">{"".join(items)}</ul>'


def render_flow(flow) -> str:
    """A left-to-right pipeline of boxes with arrows. Each stage gets an id anchor so a
    data source can link to where it enters the pipeline. `flow` may be a single
    {title?, stages:[...]} object or a list of them."""
    if not flow:
        return ""
    flows = flow if isinstance(flow, list) else [flow]
    blocks = []
    for fl in flows:
        stages = (fl or {}).get("stages") or []
        if not stages:
            continue
        boxes = []
        for st in stages:
            sid = st.get("id")
            anchor = f' id="flow-{esc(sid)}"' if sid else ""
            sub = f'<small>{esc(st["sub"])}</small>' if st.get("sub") else ""
            boxes.append(
                f'<div class="flow-box"{anchor}>'
                f'<span class="flow-box-label">{esc(st.get("label", ""))}</span>{sub}</div>'
            )
        inner = '<span class="flow-arrow">&rarr;</span>'.join(boxes)
        title = f'<div class="flow-title">{esc(fl["title"])}</div>' if fl.get("title") else ""
        blocks.append(f'{title}<div class="flow">{inner}</div>')
    return "".join(blocks)


def render_data_sources(sources: list) -> str:
    if not sources:
        return '<p class="fig-caption">No upstream nodes cited in the plan yet.</p>'
    groups = {"upstream": [], "method": [], "context": [], "other": []}
    for s in sources:
        groups.get(str(s.get("role", "other")), groups["other"]).append(s)
    labels = {"upstream": "Input evidence", "method": "Methods and references",
              "context": "Background", "other": "Other"}
    out = []
    for role in ("upstream", "method", "context", "other"):
        rows = groups[role]
        if not rows:
            continue
        out.append(f'<div class="ds-group-label">{labels[role]}</div><div class="ds-list">')
        for s in rows:
            path = (
                f'<span class="ds-path">{esc(s["path"])}</span>'
                if s.get("path") else ""
            )
            status = pill(s.get("status", "active"), s.get("status", "active")) if s.get("status") else ""
            flow_link = (
                f'<a class="ds-flowlink" href="#flow-{esc(s["flow_ref"])}">enters pipeline &darr;</a>'
                if s.get("flow_ref") else ""
            )
            out.append(
                '<div class="ds-row">'
                f'{node_badge(s.get("id", "?"))}'
                f'<span class="ds-title">{esc(s.get("title", "untitled"))}</span>'
                f'<span class="ds-type">{esc(s.get("type", ""))}</span>'
                f'{path}{status}{flow_link}</div>'
            )
        out.append("</div>")
    return "".join(out)


def render_tables(tables: list) -> str:
    """Result/data tables, each as a collapsible dropdown so a report stays scannable.
    A table is {title, columns:[...], rows:[[...]], note?} or {title, html}."""
    if not tables:
        return ""
    blocks = []
    for t in tables:
        title = esc(t.get("title", "Table"))
        if t.get("html"):
            inner = t["html"]  # trusted caller-built table fragment
        else:
            cols = t.get("columns") or []
            head = "".join(f"<th>{esc(c)}</th>" for c in cols)
            body = []
            for row in (t.get("rows") or []):
                cells = "".join(f"<td>{linkify_nodes(str(c))}</td>" for c in row)
                body.append(f"<tr>{cells}</tr>")
            inner = (
                f'<table class="data-table"><thead><tr>{head}</tr></thead>'
                f'<tbody>{"".join(body)}</tbody></table>'
            )
        note = f'<p class="table-note">{linkify_nodes(str(t["note"]))}</p>' if t.get("note") else ""
        blocks.append(
            f'<details class="table-drop"><summary>{title}</summary>{inner}{note}</details>'
        )
    return "".join(blocks)


def render_relations(relations: list) -> str:
    if not relations:
        return '<p class="fig-caption">No node relations recorded.</p>'
    rows = []
    for r in relations:
        note = f'<span class="rel-note">{esc(r["note"])}</span>' if r.get("note") else ""
        rows.append(
            '<div class="rel-row">'
            f'{node_badge(r.get("source", "?"))}'
            f'<span class="rel-arrow">&mdash; {esc(r.get("rel", "REL"))} &rarr;</span>'
            f'{node_badge(r.get("target", "?"))}{note}</div>'
        )
    return f'<div class="rel-list">{"".join(rows)}</div>'


def render_hypotheses(hyps: list) -> str:
    if not hyps:
        return ""
    rows = []
    for h in hyps:
        badge = node_badge(h["node"]) if h.get("node") else ""
        rows.append(
            '<div class="hyp-row">'
            f'{badge}<span class="hyp-name">{esc(h.get("label", "hypothesis"))}</span>'
            f'<span class="hyp-pred">predicts: {esc(h.get("prediction", ""))}</span></div>'
        )
    return (
        '<div class="hyp-legend"><div class="hyp-legend-label">'
        "How hypotheses differ here</div>" + "".join(rows) + "</div>"
    )


def render_figures(figures: list, root: Path, missing: list) -> str:
    if not figures:
        return '<p class="fig-caption">No figures pre-registered for this investigation.</p>'
    cards = []
    for i, f in enumerate(figures, start=1):
        cards.append(render_figure_card(f, root, missing, i))
    return "".join(cards)


def render_figure_card(f: dict, root: Path, missing: list, fignum: int) -> str:
    status = str(f.get("status", "planned")).lower()
    title = esc(f.get("title", "Untitled figure"))
    caption = esc(f.get("caption", ""))
    expected = f.get("expected_trend")
    alt = f.get("caption") or f.get("title") or "figure"

    mockup_well = ""
    if f.get("mockup_image"):
        img_html, ok = embed_image(f["mockup_image"], root, f"Mockup: {f.get('title', '')}")
        if not ok:
            missing.append(f["mockup_image"])
        mockup_well = (
            f'<div class="fig-well mockup-img-well">'
            f'<div class="well-label">Mockup (synthetic data, pre-registered)</div>{img_html}</div>'
        )
    else:
        mockup = safe_svg(f.get("mockup_svg") or "")
        mockup_well = (
            f'<div class="fig-well mockup-well" role="img" aria-label="Mockup: {esc(title)}">'
            f'<div class="well-label">Mockup (pre-registered sketch)</div>{mockup}</div>'
            if mockup else ""
        )

    actual_well = ""
    if f.get("image_path"):
        img_html, ok = embed_image(f["image_path"], root, alt)
        if not ok:
            missing.append(f["image_path"])
        actual_well = (
            f'<div class="fig-well"><div class="well-label">Actual result</div>{img_html}</div>'
        )

    ribbon, body_cls, toggle = "", "fig-body", ""
    if status == "produced" and mockup_well and actual_well:
        body_cls = "fig-body paired"
        body = mockup_well + actual_well
        toggle = '<button type="button" class="overlay-toggle">Overlay mockup on result</button>'
    elif status == "unplanned":
        ribbon = '<span class="ribbon ribbon-unplanned">NOT PRE-REGISTERED</span>'
        body = actual_well or mockup_well
    elif status == "missing":
        ribbon = '<span class="ribbon ribbon-missing">NOT PRODUCED</span>'
        body = mockup_well
    else:  # planned, or produced lacking one side
        ribbon = '<span class="ribbon ribbon-mockup">MOCKUP / PRE-REGISTERED</span>'
        body = mockup_well + actual_well

    expected_html = (
        f'<p class="fig-expected"><strong>Expected:</strong> {esc(expected)}</p>'
        if expected else ""
    )
    # The legend is a referenceable line: "Figure N. <caption>" so the scientist can
    # point an AI at "Figure 2" unambiguously.
    legend = (
        f'<p class="fig-legend"><strong>Figure {fignum}.</strong> {caption}</p>'
        if caption else f'<p class="fig-legend"><strong>Figure {fignum}.</strong></p>'
    )
    fig_id = f'fig-{fignum}'
    return (
        f'<div class="fig-card" id="{fig_id}">'
        f'<div class="fig-head"><span class="fig-letter">Figure {fignum}</span>'
        f'<h3>{title}</h3>{ribbon}{pill(status, status)}</div>'
        f'<div class="{body_cls}">{body}</div>'
        f'{toggle}'
        f'{render_panels(f.get("panels"))}'
        f'{legend}{expected_html}'
        f'{render_hypotheses(f.get("hypotheses"))}'
        "</div>"
    )


def render_panels(panels: list) -> str:
    """Per-panel explanation cards, laid out directly below the figure with one column
    per panel so each card sits under the panel it explains. A multi-panel figure whose
    explanations drift into a mismatched grid is hard to read; keeping the column count
    equal to the panel count preserves the panel-to-text mapping."""
    if not panels:
        return ""
    n = len(panels)
    cards = []
    for p in panels:
        title = (
            f'<strong>{esc(p["title"])}.</strong> ' if p.get("title") else ""
        )
        cards.append(f'<div class="panel-card">{title}{linkify_nodes(str(p.get("text", "")))}</div>')
    return f'<div class="fig-panels" style="--panel-cols: {n}">{"".join(cards)}</div>'


def render_criteria(criteria: list) -> str:
    if not criteria:
        return '<p class="fig-caption">No success criteria recorded.</p>'
    rows = []
    for c in criteria:
        st = str(c.get("status", "PENDING"))
        ev = (
            f' {node_badge(c["evidence"])}' if c.get("evidence") else ""
        )
        rows.append(
            '<div class="crit-row">'
            f'{pill(st, st)}'
            f'<span class="crit-text">{linkify_nodes(str(c.get("text", "")))}{ev}</span></div>'
        )
    return "".join(rows)


# --------------------------------------------------------------------------- assembly


def fmt_date(iso: str) -> str:
    try:
        return datetime.fromisoformat(str(iso).replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return str(iso)


def render(spec: dict) -> tuple[str, list]:
    version = spec.get("spec_version")
    if version != SUPPORTED_VERSION:
        raise SpecError(f"unsupported spec_version {version!r}; this renderer handles {SUPPORTED_VERSION}")
    for field in ("mode", "investigation", "question", "figures"):
        if field not in spec:
            raise SpecError(f"missing required field: {field!r}")

    meta = spec.get("meta") or {}
    root = Path(meta.get("project_root") or ".").resolve()
    mode = spec.get("mode")
    missing: list = []

    rationale_html, sci_html = render_rationale(spec.get("rationale") or {})
    plan_node = spec.get("plan_node")
    plan_badge = node_badge(plan_node) if plan_node else ""
    status_pill = pill(spec.get("plan_status", "draft"), spec.get("plan_status", "draft"))
    banner = "Execution results" if mode == "execution" else "Pre-registration brief"

    history = meta.get("history") or []
    hist_parts = [f"{h.get('mode')} {fmt_date(h.get('generated'))}" for h in history]
    hist_line = " &middot; ".join(hist_parts) if hist_parts else ""
    gen_line = f"Generated {fmt_date(spec.get('generated'))}"
    if hist_line:
        gen_line += f" &middot; history: {hist_line}"

    figures = spec.get("figures") or []
    has_mockup = any(f.get("mockup_svg") or f.get("mockup_image") for f in figures)
    if has_mockup:
        fig_banner = (
            '<div class="fig-banner">All mockups below use synthetic data and show the '
            "agreed plot layout and predicted shape. They are not results.</div>"
        )
    else:
        fig_banner = ""

    flow_html = render_flow(spec.get("flow"))
    flow_section = (
        '<section aria-labelledby="sec-flow"><h2 id="sec-flow">Pipeline</h2>'
        f"{flow_html}</section>" if flow_html else ""
    )

    # Data sources and result tables. In an execution report these can be bulky, so the
    # whole block collapses behind a dropdown (the example the scientist liked tucks its
    # full data table inside a <details>). In a plan brief the sources stay inline.
    sources_html = render_data_sources(spec.get("data_sources") or [])
    tables_html = render_tables(spec.get("tables") or [])
    if mode == "execution":
        data_inner = (
            '<details class="data-drop"><summary>Show data sources and tables</summary>'
            f"{sources_html}{tables_html}</details>"
        )
    else:
        data_inner = sources_html + tables_html
    data_section = (
        '<section aria-labelledby="sec-sources"><h2 id="sec-sources">Data sources</h2>'
        f"{data_inner}</section>"
    )

    footer = (
        f"Wheeler research brief for <code>{esc(spec.get('plan_path', ''))}</code>. "
        "Figure mockups are pre-registration sketches, not data."
    )

    template = Template(TEMPLATE_PATH.read_text(encoding="utf-8"))
    out = template.safe_substitute(
        TITLE=esc(spec.get("investigation")),
        MODE_BANNER=esc(banner),
        PLAN_NODE_BADGE=plan_badge,
        STATUS_PILL=status_pill,
        GENERATED_LINE=gen_line,
        QUESTION_HTML=linkify_nodes(str(spec.get("question", ""))),
        SUBQUESTIONS_HTML=render_sub_questions(spec.get("sub_questions")),
        RATIONALE_HTML=rationale_html,
        SCIREASON_HTML=sci_html,
        GAMEPLAN_HTML=render_game_plan(spec.get("game_plan") or {}),
        RELATIONS_HTML=render_relations(spec.get("relations") or []),
        FIGURE_BANNER=fig_banner,
        FIGURES_HTML=render_figures(figures, root, missing),
        FLOW_SECTION=flow_section,
        DATA_SECTION=data_section,
        CRITERIA_HTML=render_criteria(spec.get("success_criteria") or []),
        FOOTER_HTML=footer,
    )
    return out, missing


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Render a Wheeler research-brief spec to HTML.")
    ap.add_argument("spec", help="path to the spec JSON")
    ap.add_argument("-o", "--out", help="output HTML path (default: spec path with .html)")
    args = ap.parse_args(argv)

    spec_path = Path(args.spec)
    try:
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"error: spec not found: {spec_path}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"error: spec is not valid JSON: {e}", file=sys.stderr)
        return 1

    try:
        html_out, missing = render(spec)
    except SpecError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    out_path = Path(args.out) if args.out else spec_path.with_suffix(".html")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html_out, encoding="utf-8")

    size = len(html_out.encode("utf-8"))
    if size > WARN_BYTES:
        print(f"warning: output is {size / 1_048_576:.1f} MB (many large figures embedded)",
              file=sys.stderr)

    # copy into the export dir at execution time so the archive is self-contained
    export_dir = (spec.get("meta") or {}).get("export_dir")
    if export_dir:
        edir = Path(export_dir)
        if not edir.is_absolute():
            edir = Path((spec.get("meta") or {}).get("project_root") or ".") / edir
        if edir.exists() and edir.is_dir():
            (edir / out_path.name).write_text(html_out, encoding="utf-8")

    print(str(out_path.resolve()))
    if missing:
        print("missing figure files:", file=sys.stderr)
        for m in missing:
            print(f"  - {m}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
