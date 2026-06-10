# wheeler-brief spec schema (v1)

The spec is the contract between Claude (who composes it) and `scripts/render_brief.py`
(which renders it deterministically). One spec file per investigation, at
`.plans/brief/<investigation>.json`. The renderer is mode-agnostic: it renders whatever
the spec says. All semantics (what counts as a figure, which nodes matter) are decided
by Claude at spec-composition time.

## Top-level fields

| Field | Type | Notes |
|---|---|---|
| `spec_version` | int | Must be `1`. The renderer exits 1 on any other value. |
| `mode` | str | `"plan"` (pre-registration brief) or `"execution"` (results brief). |
| `investigation` | str | Kebab-case slug. Also the output filename stem. |
| `plan_path` | str | Relative path to the plan markdown. |
| `plan_node` | str or null | `PL-xxxx` once registered. |
| `plan_status` | str | `draft`, `approved`, `in-progress`, `completed`. |
| `generated` | str | ISO 8601 timestamp of this spec write. |
| `question` | str | The single headline research question, from `## Objective`. |
| `sub_questions` | list | Optional decomposition shown right under the question. |
| `rationale` | object | See below. |
| `data_sources` | list | See below. |
| `relations` | list | Node-to-node edges among cited nodes. See below. |
| `game_plan` | object | Decisions + step flow. See below. |
| `success_criteria` | list | See below. |
| `figures` | list | The centerpiece. See below. |
| `meta` | object | See below. |

## `sub_questions` (optional)

The headline `question` decomposed into the few specific things the investigation will
actually answer. Shown as a short list directly under the question, before the figures,
so the scientist reads "here is the big question, here is how it breaks down" first.
Each item is a plain string or `{text, node}` where `node` cites a `[Q-xxxx]`
OpenQuestion. Keep to 2 to 4; this is decomposition, not a task list.

```json
"sub_questions": [
  { "text": "Does within-type break match cross-type at matched kernel distance?", "node": null },
  { "text": "Is the foreign-kernel cost type-blind after the margin is retuned?", "node": "Q-d7ad3eb7" }
]
```

## `rationale`

```json
{
  "summary": "Paragraphs from ## Rationale. Blank-line separated.",
  "scientific_reasoning": "Condensed foundation / why this method / alternatives rejected / assumptions, or null."
}
```

## `data_sources[]`

One entry per upstream node the plan rests on: every `[NODE_ID]` cited in
`## Current State` plus the frontmatter `graph_nodes` list. Look up title/type via
`show_node` when available, else read `knowledge/<ID>.json` directly.

```json
{
  "id": "D-0008d164",
  "type": "Dataset",
  "title": "Retinal ganglion spike trains, 2026-03 recordings",
  "path": "data/rgc_spikes_2026-03.mat",
  "status": "active",
  "role": "upstream"
}
```

`role` is one of `upstream` (input evidence), `method` (papers/scripts the approach
follows), `context` (background). The renderer groups by role. Data sources render in
their own section directly after the figures and pipeline.

Optional `flow_ref` on a data source is the `id` of the `flow` stage where that input
enters the pipeline; the renderer shows an "enters pipeline" link that jumps to and
highlights that stage. Example: `"flow_ref": "roster"`.

## `relations[]`

Edges among nodes that appear anywhere in the spec (data sources, plan node, figure
nodes). Gives the scientist the citation and relation structure at a glance. Use
Wheeler/PROV vocabulary: `USED`, `WAS_GENERATED_BY`, `WAS_DERIVED_FROM`, `SUPPORTS`,
`CONTRADICTS`, `CITES`, `APPEARS_IN`, `RELEVANT_TO`, `AROSE_FROM`, `DEPENDS_ON`.

```json
{ "source": "X-3df4f281", "rel": "USED", "target": "D-0008d164", "note": "plan registration execution" }
```

Sources of truth: `search_context` expansion at plan time, or the relationship lists in
`synthesis/<ID>.md`. Keep to edges that help reading the brief (10 to 20 max); this is
not a graph dump.

## `game_plan`

The easy-to-read step flow. `decisions` surfaces every point where the scientist must
choose or judge (checkpoint_if conditions, scientist-assigned tasks, contract gates).
`tasks` mirrors the plan's task list in compressed form, grouped by wave.

```json
{
  "decisions": [
    { "text": "If adaptation index varies more than 2x across cells, split analysis by cell type", "task": 3, "resolution": null }
  ],
  "tasks": [
    {
      "n": 1,
      "title": "Extract ISI distributions per cell",
      "wave": 1,
      "assignee": "wheeler",
      "type": "code",
      "depends_on": [],
      "checkpoint": null,
      "status": "pending"
    },
    {
      "n": 3,
      "title": "Judge whether cell-type split is warranted",
      "wave": 2,
      "assignee": "scientist",
      "type": "interpretation",
      "depends_on": [1, 2],
      "checkpoint": "adaptation index spread exceeds 2x",
      "status": "pending"
    }
  ]
}
```

`assignee`: `wheeler`, `scientist`, or `pair`. `status`: `pending`, `done`, `skipped`
(scientist/pair tasks not run by execute), `flagged` (checkpoint hit). `resolution` on a
decision is filled at execute time when the decision got made; otherwise null.

## `flow` (optional)

A left-to-right pipeline of boxes with arrows, shown directly after the figures, so the
scientist sees how inputs become the figure. Each stage may carry an `id` that a data
source links to (see `flow_ref` below). May be a single object or a list of them.

```json
"flow": {
  "title": "Swap-and-refit pipeline",
  "stages": [
    { "id": "roster", "label": "12-cell roster", "sub": "kernel, margin, baseline, class, ON/OFF" },
    { "label": "132 ordered pairs", "sub": "tagged by 3-tier ladder" },
    { "label": "predict_swap_refit_theta0", "sub": "refit theta0 on target holdout" },
    { "id": "metrics", "label": "vp_own / vp_raw / vp_refit", "sub": "+ kernel distances" }
  ]
}
```

Keep stage labels short (a few words) and `sub` to a phrase. The Pipeline section is
omitted entirely when `flow` is absent.

## `success_criteria[]`

```json
{ "text": "Adaptation index correlates with stimulus contrast (r > 0.5)", "status": "PENDING", "evidence": null }
```

`status`: `PENDING` (plan mode), `MET`, `PARTIAL`, `UNMET` (from VERIFICATION at execute
time). `evidence` is a node ID like `F-xxxx` or null.

## `figures[]`

One entry per expected or produced figure. At plan time every figure has a `mockup_svg`
and `image_path: null`. At execute time `image_path` points at the real file and
`status` updates. Mockups are immutable once written: execute-time edits fill fields in,
they never rewrite `mockup_svg`, `expected_trend`, `title`, or `caption`.

```json
{
  "id": "fig_A",
  "title": "Adaptation index vs stimulus contrast",
  "caption": "Each point is one cell; expected positive trend if criterion 1 holds.",
  "expected_trend": "Monotonic increase, saturating above 0.6 contrast.",
  "hypotheses": [
    { "node": "H-12ab34cd", "label": "H1 adaptive coding", "prediction": "saturating rise with contrast" },
    { "node": null, "label": "H0 null", "prediction": "flat line, no contrast dependence" }
  ],
  "mockup_svg": "<svg viewBox=\"0 0 480 320\" ...>...</svg>",
  "image_path": null,
  "figure_node": null,
  "status": "planned"
}
```

`hypotheses` is optional and is the discriminating-test view: when a figure is the one
that separates competing hypotheses, list each hypothesis with its predicted signature
in this figure, and draw one trend per hypothesis in the mockup (different dash
patterns, each labeled with the hypothesis name in text). The renderer shows the list
as a legend under the figure with `[H-xxxx]` badges when `node` is set. A figure that
tests nothing contested can omit the field entirely.

`panels` (optional) is a list of `{title, text}` explanation cards for a multi-panel
figure. They render in a row directly below the image, one column per panel, so each
card sits under the panel it explains:

```json
"panels": [
  { "title": "1. What the residual is", "text": "Break rises ~5x on swap; refit removes ~99%; the sliver left is the residual." },
  { "title": "2. The test", "text": "Residual vs kernel distance, within (blue) vs across (orange). Same curve supports [H-xxxx]." },
  { "title": "3. Power floor", "text": "Per-cell CI against the minimum detectable effect; a null reads as 'no effect larger than the band'." }
]
```

Order the panels to match the figure's panels left to right. `text` may cite `[NODE_ID]`.

`mockup_svg` is a hand-drawn inline SVG wireframe. As an alternative, set
`mockup_image` to a path to a rendered PNG mockup (matplotlib with synthetic data, the
richer style: see `figure-style-guide.md`). If both are set, the PNG wins. Use
`mockup_image` for the primary multi-panel figure, `mockup_svg` for quick sketches.

`status` values and what the renderer does with them:

| status | meaning | card rendering |
|---|---|---|
| `planned` | mockup only (plan mode) | full-width mockup, MOCKUP ribbon |
| `produced` | mockup + actual | side-by-side pair, overlay toggle |
| `missing` | expected but no file produced | mockup with NOT PRODUCED ribbon |
| `unplanned` | actual figure with no mockup | actual only, NOT PRE-REGISTERED ribbon |

`image_path` is relative to `meta.project_root` (absolute also accepted). Supported:
png, jpg, jpeg, gif (base64-embedded), svg (inlined), pdf (link card, not embedded).

## `meta`

```json
{
  "project_root": "/Users/maxwellsdm/Documents/GitHub/wheeler",
  "export_dir": null,
  "summary_path": null,
  "history": [
    { "mode": "plan", "generated": "2026-06-10T18:00:00Z" }
  ]
}
```

`export_dir`: set at execute time (`analysis_exports/<slug>_<date>`); when set and the
directory exists, the renderer copies the finished HTML into it. `history` is
append-only; the brief footer renders it as "pre-registered <date>, results <date>".

## Renderer exit codes

| code | meaning |
|---|---|
| 0 | rendered cleanly |
| 1 | spec invalid (unknown spec_version, unparseable JSON, missing required field); nothing written |
| 2 | rendered, but some `image_path` files were missing or unembeddable; placeholder cards substituted, gaps listed on stderr |

## Complete worked example

```json
{
  "spec_version": 1,
  "mode": "plan",
  "investigation": "adaptation-contrast",
  "plan_path": ".plans/adaptation-contrast.md",
  "plan_node": "PL-1a2b3c4d",
  "plan_status": "approved",
  "generated": "2026-06-10T18:00:00Z",
  "question": "Does the spike-frequency adaptation index of retinal ganglion cells increase with stimulus contrast?",
  "rationale": {
    "summary": "Adaptation strength is hypothesized to track stimulus statistics. Contrast is the cleanest axis we can vary with the 2026-03 recordings already in hand.\n\nIf the effect is absent at this scale it is unlikely to matter for the encoding model, which lets us prune that term.",
    "scientific_reasoning": "Foundation: adaptation index defined as 1 - (late rate / early rate) over a 2 s step. Why this method: rate-based index is robust to spike sorting jitter, unlike ISI-mixture fits. Alternatives rejected: GLM adaptation kernels need more data per cell than we have. Assumptions: stationarity within trials; failure mode detected by drift check in task 2."
  },
  "data_sources": [
    { "id": "D-0008d164", "type": "Dataset", "title": "RGC spike trains, 2026-03 recordings", "path": "data/rgc_spikes_2026-03.mat", "status": "active", "role": "upstream" },
    { "id": "P-77ab12cd", "type": "Paper", "title": "Fairhall et al. 2001, Efficiency and ambiguity in an adaptive neural code", "path": null, "status": "active", "role": "method" }
  ],
  "relations": [
    { "source": "X-9f8e7d6c", "rel": "USED", "target": "D-0008d164", "note": "plan registration" },
    { "source": "PL-1a2b3c4d", "rel": "WAS_GENERATED_BY", "target": "X-9f8e7d6c", "note": null },
    { "source": "PL-1a2b3c4d", "rel": "CITES", "target": "P-77ab12cd", "note": "method source" }
  ],
  "game_plan": {
    "decisions": [
      { "text": "If adaptation index spread exceeds 2x across cells, split the analysis by cell type before testing the contrast trend", "task": 3, "resolution": null }
    ],
    "tasks": [
      { "n": 1, "title": "Extract adaptation index per cell per contrast", "wave": 1, "assignee": "wheeler", "type": "code", "depends_on": [], "checkpoint": null, "status": "pending" },
      { "n": 2, "title": "Stationarity drift check within trials", "wave": 1, "assignee": "wheeler", "type": "data_wrangling", "depends_on": [], "checkpoint": null, "status": "pending" },
      { "n": 3, "title": "Judge whether cell-type split is warranted", "wave": 2, "assignee": "scientist", "type": "interpretation", "depends_on": [1, 2], "checkpoint": "adaptation index spread exceeds 2x", "status": "pending" },
      { "n": 4, "title": "Fit contrast trend, produce fig_A and fig_B", "wave": 3, "assignee": "wheeler", "type": "code", "depends_on": [3], "checkpoint": null, "status": "pending" }
    ]
  },
  "success_criteria": [
    { "text": "Adaptation index correlates with contrast (r > 0.5) in pooled data", "status": "PENDING", "evidence": null },
    { "text": "Effect survives per-cell-type split or split shown unnecessary", "status": "PENDING", "evidence": null }
  ],
  "figures": [
    {
      "id": "fig_A",
      "title": "Adaptation index vs stimulus contrast",
      "caption": "Each point is one cell at one contrast; line is the pooled fit.",
      "expected_trend": "Monotonic increase, saturating above 0.6 contrast.",
      "mockup_svg": "<svg viewBox=\"0 0 480 320\" xmlns=\"http://www.w3.org/2000/svg\" role=\"img\" aria-label=\"Mockup: adaptation index vs contrast\"><text x=\"240\" y=\"22\" text-anchor=\"middle\" font-size=\"15\" fill=\"currentColor\">Adaptation index vs contrast (mockup)</text><line x1=\"60\" y1=\"270\" x2=\"440\" y2=\"270\" stroke=\"currentColor\" stroke-width=\"1.5\"/><line x1=\"60\" y1=\"270\" x2=\"60\" y2=\"40\" stroke=\"currentColor\" stroke-width=\"1.5\"/><text x=\"250\" y=\"300\" text-anchor=\"middle\" font-size=\"13\" fill=\"currentColor\">stimulus contrast</text><text x=\"24\" y=\"160\" font-size=\"13\" fill=\"currentColor\" transform=\"rotate(-90 24 160)\" text-anchor=\"middle\">adaptation index</text><path d=\"M 70 250 C 180 230, 260 120, 430 80\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-dasharray=\"7 5\"/><circle cx=\"110\" cy=\"244\" r=\"4\" fill=\"currentColor\" opacity=\"0.45\"/><circle cx=\"190\" cy=\"210\" r=\"4\" fill=\"currentColor\" opacity=\"0.45\"/><circle cx=\"270\" cy=\"150\" r=\"4\" fill=\"currentColor\" opacity=\"0.45\"/><circle cx=\"350\" cy=\"105\" r=\"4\" fill=\"currentColor\" opacity=\"0.45\"/><text x=\"430\" y=\"60\" text-anchor=\"end\" font-size=\"12\" fill=\"currentColor\" opacity=\"0.7\">expected: saturating rise</text></svg>",
      "image_path": null,
      "figure_node": null,
      "status": "planned"
    },
    {
      "id": "fig_B",
      "title": "Per-cell-type adaptation index distributions",
      "caption": "Violin or box per cell type; only produced if the task 3 decision triggers a split.",
      "expected_trend": "ON cells higher than OFF cells if the split is real.",
      "mockup_svg": "<svg viewBox=\"0 0 480 320\" xmlns=\"http://www.w3.org/2000/svg\" role=\"img\" aria-label=\"Mockup: per-type distributions\"><text x=\"240\" y=\"22\" text-anchor=\"middle\" font-size=\"15\" fill=\"currentColor\">Per-type adaptation index (mockup)</text><line x1=\"60\" y1=\"270\" x2=\"440\" y2=\"270\" stroke=\"currentColor\" stroke-width=\"1.5\"/><line x1=\"60\" y1=\"270\" x2=\"60\" y2=\"40\" stroke=\"currentColor\" stroke-width=\"1.5\"/><text x=\"250\" y=\"300\" text-anchor=\"middle\" font-size=\"13\" fill=\"currentColor\">cell type</text><text x=\"24\" y=\"160\" font-size=\"13\" fill=\"currentColor\" transform=\"rotate(-90 24 160)\" text-anchor=\"middle\">adaptation index</text><rect x=\"130\" y=\"110\" width=\"60\" height=\"120\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-dasharray=\"6 4\"/><line x1=\"130\" y1=\"170\" x2=\"190\" y2=\"170\" stroke=\"currentColor\" stroke-width=\"2\"/><rect x=\"290\" y=\"150\" width=\"60\" height=\"100\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-dasharray=\"6 4\"/><line x1=\"290\" y1=\"200\" x2=\"350\" y2=\"200\" stroke=\"currentColor\" stroke-width=\"2\"/><text x=\"160\" y=\"288\" text-anchor=\"middle\" font-size=\"12\" fill=\"currentColor\">ON</text><text x=\"320\" y=\"288\" text-anchor=\"middle\" font-size=\"12\" fill=\"currentColor\">OFF</text></svg>",
      "image_path": null,
      "figure_node": null,
      "status": "planned"
    }
  ],
  "meta": {
    "project_root": "/Users/maxwellsdm/Documents/GitHub/wheeler",
    "export_dir": null,
    "summary_path": null,
    "history": [
      { "mode": "plan", "generated": "2026-06-10T18:00:00Z" }
    ]
  }
}
```
