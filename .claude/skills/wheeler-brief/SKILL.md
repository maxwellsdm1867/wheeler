---
name: wheeler-brief
description: >-
  Render a self-contained, scientist-friendly HTML research brief (a "game plan" decision
  aid) for a Wheeler investigation plan or execution. It leads with the question and
  sub-questions, then figure mockups (wireframe or synthetic-data PNG) showing what will
  be plotted and how competing hypotheses would differ, then the execution steps, a
  pipeline flow chart, and data sources; at execute time it pairs each mockup with the
  real result figure and tucks data tables into dropdowns. ALWAYS reach for this skill,
  and do not hand-write the HTML yourself, whenever the user wants to SEE, VISUALIZE, or
  SHARE a Wheeler plan or its results as a page: triggers include "visualize the plan",
  "show/make the brief", "research brief", "render the execution dashboard", "game plan
  view", "show mockups vs results", "what will the figure look like", "draw the figure
  under each hypothesis", "re-render that plan/brief", or any request to view a specific
  plan (for example a PL-xxxx id) or its figures as an HTML page. Even a short request
  like "show me the brief for PL-99d25314" should fire it. Also invoked automatically by
  /wh:plan after a plan is approved and by /wh:execute after the completion summary.
  While composing the brief you also help plan mode by drawing the question, rationale,
  decisions, and figure intent out of the scientist. Do NOT trigger for one-off plotting
  of a data file, graph lookups (use wh:ask), adding data (wh:add), drafting prose
  (wh:write), or cosmetic edits to a single existing figure.
allowed-tools:
  - Read
  - Write
  - Glob
  - Grep
  - Bash
---

# Wheeler research brief

Turn a Wheeler plan (and later its execution) into one self-contained HTML page a
scientist can read top to bottom: the question, a bulleted game plan, and figure
mockups that pre-register what will be plotted. The HTML embeds everything (figures as
base64 or inline SVG), so it opens offline from any location.

## The brief is a thinking aid, not a report (read this first)

The whole point is to sharpen thinking and decision-making at a glance. If it turns into
a wall of text, the scientist will not read it, and it has failed. Be ruthless about
what goes on the visible page:

- The visible page holds only what drives a decision: the question, the open or settled
  decisions, the figures (and how each hypothesis would look different in them), the
  next steps, the success criteria. Everything is scannable in well under a minute.
- Captions are one line. Decision text and its resolution are short phrases, not
  paragraphs. Step titles are a handful of words. Success criteria are terse.
- Detail, nuance, and full rationale go in the collapsed Background section or stay in
  the plan markdown, not on the visible page. When in doubt, cut it from the brief; the
  plan file is the system of record, the brief is the lens.
- Prefer fewer, load-bearing items: the 3 to 5 steps that matter, not all 9 sub-tasks;
  the 2 to 3 real decisions, not every minor choice. A brief that lists everything
  helps no one decide anything.

You do two jobs at once:

1. **Elicit** the high-level content the brief needs, if the plan does not already
   contain it. This is where you genuinely help planning: a scientist often has the
   question and the analysis steps but has not said out loud what the key figure will
   look like or which decision is the load-bearing one. Drawing that out is the point.
2. **Render** the brief deterministically from a spec JSON via the bundled script.

## How it works

You compose a spec JSON; `scripts/render_brief.py` turns it into HTML. You never write
HTML by hand. The full spec contract is in `references/spec-schema.md` (read it before
composing). Figure styling guidance is in `references/figure-style-guide.md` and
`references/mockup-svg-guide.md` (read whichever applies to the figures you are
drawing).

## Step 1: Resolve the target plan

`$ARGUMENTS` may be a plan file path, an `investigation` slug, or a `PL-xxxx`. If empty,
use the plan from the current conversation, else read `.plans/STATE.md` for the active
plan. Read the plan markdown. If `.plans/<name>-SUMMARY.md` or `<name>-VERIFICATION.md`
exist, read them too.

Detect mode: **execution** if a SUMMARY exists or the plan status is `completed` or
`in-progress`; otherwise **plan**.

## Step 2: Elicit what the brief needs (the part that helps planning)

The brief has a fixed shape; walk the plan against it and fill gaps by asking the
scientist short, specific questions. Do not pad: ask only for what is genuinely missing,
and prefer one sharp question over a checklist. Compress hard as you go (see "The brief
is a thinking aid" above): the goal is the least text that still lets the scientist
decide. The fields:

- **Question** (one sentence) and **sub-questions** (2 to 4). Pull the headline from
  `## Objective`; if it is a paragraph, offer a one-sentence distillation and let the
  scientist correct it. Then decompose it into the few specific things the investigation
  will actually answer (these often map to `[Q-xxxx]` OpenQuestions or the if/then
  branches in the plan). The brief opens with the question and sub-questions and then
  goes straight to the figures, so this pairing must be crisp: it is the frame the
  scientist reads before anything else.
- **Rationale** and **scientific reasoning**. From `## Rationale` and
  `## Scientific reasoning`. These go in a collapsed Background section, so they can be
  longer; do not over-trim them.
- **Decisions to make**. The judgment calls: `checkpoint_if` conditions, scientist /
  pair assigned tasks, and any contract gate. If the plan implies a decision but never
  names it (for example a method choice with a real alternative), surface it and ask the
  scientist to confirm the call. These render as the decisions callout above the steps.
- **Execution steps**. Compress the task list into one bullet per step (title, assignee,
  inline checkpoint). Order by wave then number; the brief shows them as a simple
  numbered list, not the wave machinery.
- **Figures** (the heart). For each figure the investigation will produce, you need:
  what it plots, the predicted trend, and, when it decides between hypotheses, which
  hypotheses and how each would look. If the plan only says "produce a figure", ask:
  what is the one figure that answers the question, what are its panels, and what would
  each competing hypothesis look like in it? This question alone often sharpens the
  whole plan. Then draw the mockup (see Step 3).
- **Data sources** and **relations**. The `[NODE_ID]` citations in `## Current State`
  plus frontmatter `graph_nodes`. Look each up via the `show_node` MCP tool if available
  in this context; otherwise read `knowledge/<ID>.json` directly (fields: `id`, `type`,
  `title`, `path`, `status`). For relations, use `synthesis/<ID>.md` relationship lists
  or `search_context`; keep to 10 to 20 load-bearing edges, not a graph dump.
- **Success criteria**. From `## Success Criteria`, status `PENDING` at plan time.

## Step 3: Draw the figure mockups

Pick per figure (see `references/figure-style-guide.md`):

- **Quick sketch**: hand-draw an inline SVG into `mockup_svg` (rules in
  `references/mockup-svg-guide.md`). Good for simple single-panel figures.
- **Rich PNG**: for the primary, multi-panel figure that carries the argument, write a
  small matplotlib script with synthetic data to
  `.plans/brief/assets/<investigation>/make_mockups.py`, run it to produce a PNG, and
  set `mockup_image` to that path. Use the three-beat layout (what the read-out is, the
  test, the power floor) and add a `panels` entry per panel so the explanation cards
  render in a row directly under the figure, aligned to the panels.

Always make the competing hypotheses visually distinct and mirror them in the figure's
`hypotheses` field so the brief shows a matching legend.

## Step 4: Write the spec and render

Write the spec to `.plans/brief/<investigation>.json`. At execute time, first read any
existing spec from that path and treat `mockup_svg`, `mockup_image`, `expected_trend`,
`question`, and `rationale` as immutable pre-registration content: only fill in
`image_path`, `figure_node`, and `status` per figure, update `success_criteria` from
VERIFICATION, set `meta.export_dir`, and append to `meta.history`. The whole value of a
pre-registration is lost if you rewrite the prediction after seeing the result, so never
do it.

Then render and open:

```bash
python3 .claude/skills/wheeler-brief/scripts/render_brief.py .plans/brief/<investigation>.json
open .plans/brief/<investigation>.html
```

The script prints the absolute HTML path. Exit code 2 means some figure files were
missing (it still renders, with placeholder cards); report those gaps to the scientist.
Print the path so the scientist can reopen it.

## Rules

- Never modify the plan markdown and never write graph nodes; this skill only reads and
  renders.
- Mockups are pre-registration sketches with synthetic data, never results. Label them
  as such (the brief shows a banner automatically).
- At execute time, do not rewrite the pre-registered question, rationale, or mockups.
- No em dashes in any text you compose. Keep captions to one to four sentences.
