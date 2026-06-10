# Figure style guide

How to design the figure mockups that are the heart of a Wheeler brief. There are two
ways to draw a mockup; pick per figure:

- **Inline SVG sketch** (`mockup_svg`): a quick wireframe, drawn by hand in the spec.
  Best for simple single-panel figures and fast plan-time briefs. See
  `mockup-svg-guide.md` for the SVG rules.
- **Rendered PNG mockup** (`mockup_image`): a real matplotlib figure drawn with
  SYNTHETIC data, saved to disk, and embedded. Best for the primary, multi-panel
  figure that carries the scientific argument. This is the richer style and the one to
  reach for when the figure is the point of the investigation.

Both embed identically in the brief. A figure entry may set `mockup_svg` OR
`mockup_image` (the path to a PNG); if both are set, the PNG wins.

## The golden rule: a mockup is a contract, not a result

A mockup exists so the scientist and Wheeler agree on WHAT WILL BE PLOTTED before any
real data is touched. It uses synthetic numbers that illustrate the plot type and the
predicted shape. It must never be mistaken for data:

- Every mockup figure carries a visible label "MOCKUP - synthetic data, not results"
  (the brief also shows a banner above the figures section).
- Synthetic points are drawn from an obvious toy model, never from the real dataset.
- File names start with `mockup_` (for example `mockup_residual_primary.png`).

## The primary figure tells a three-beat story

The single most important figure should walk the reader from "what we measure" to "the
test" to "could we even detect it". This three-panel pattern, lifted from strong real
briefs, is the default for a primary figure:

1. **What the read-out is.** Show the quantity itself and how it is constructed (for
   example a waterfall: raw effect, what a control removes, the residual that is left).
   The reader should finish this panel knowing exactly what number the test runs on.
2. **The test.** Plot the discriminating comparison: the competing hypotheses as
   different series (for example within = blue vs across = orange) against the relevant
   axis. State in the caption what each outcome means: "same curve supports [H-xxxx];
   separated curves mean the type effect is real". This is the panel that decides
   between hypotheses, so it must make the predicted signatures visually distinct.
3. **Could we even detect it (power / honest floor).** Show the minimum effect the
   sample size can resolve (a confidence interval against a detectability band). This
   keeps a null result honest: it is reported as "no effect larger than the band",
   never as positive proof. Skip only when power is genuinely not a concern.

## Showing how hypotheses differ (the discriminating panel)

When a figure separates competing hypotheses, draw one predicted series per hypothesis
and make their signatures unmistakable:

- Distinct color AND distinct marker/line style per hypothesis (never color alone).
- A short text annotation on each predicted curve naming the hypothesis and its
  signature ("H1: across sits above", "H0: one shared curve").
- Mirror them in the figure entry's `hypotheses` field so the brief renders a matching
  legend with `[H-xxxx]` badges under the figure.

The scientist should be able to glance at this panel and say "if the world is H1 it
looks like THIS, if H0 it looks like THAT".

## Consistent visual vocabulary

Keep encodings stable across every figure in a brief so the reader learns them once:

- Fix a color per condition and reuse it everywhere (for example within = blue,
  across = orange; tiers = green / orange / purple).
- Fixed glyph conventions: filled = before-correction, open = after-correction, is a
  common and readable choice. State the convention in the caption.
- Colorblind-safe families (blue / orange / purple / rose); do not rely on red-vs-green.
- Always label both axes with units. Always include a legend when there is more than
  one series. Title each panel with what it answers, not just what it shows.

## Supporting and context figures

Separate the primary figure from supporting ones. Mark context figures honestly: if a
panel is descriptive and cannot decide the question (for example a near-tautological
relationship), say so in the caption ("descriptive, not the test"). A figure that
orients the reader is valuable, but it must not masquerade as the discriminating test.

## Panel explanations go directly under their panel

When a figure has several panels, the per-panel explanation cards must sit DIRECTLY
below the figure with one column per panel, so each card lines up under the panel it
describes. A common mistake is laying three panel explanations into a two-column grid:
the third card orphans onto a second row, far from its panel, and the reader loses the
panel-to-text mapping. Use the figure entry's `panels` field (one `{title, text}` per
panel, in left-to-right order); the renderer makes the column count match the panel
count automatically. Keep each panel card to one to three sentences; the full caption
sits below the panel row for anything that spans the whole figure.

## Captions do real work, in one line

A brief caption is one line: what is plotted and what the outcome would mean, the
sharper the better. The discriminating logic ("same curve supports [H-xxxx], separated
means the type effect is real") belongs in the panel cards or the `expected_trend`, not
a long paragraph under the figure. The brief is a thinking aid, so a caption that runs
several sentences is working against it: push the nuance into the plan markdown and keep
the figure scannable.

## Producing PNG mockups (when you choose `mockup_image`)

At plan time there is no `analysis_exports/` directory yet, so write mockup PNGs and
their generating script under `.plans/brief/assets/<investigation>/`:

```
.plans/brief/assets/<investigation>/
├── make_mockups.py            # matplotlib, synthetic data only
├── mockup_residual_primary.png
└── mockup_ladder_support.png
```

Keep the generating script alongside the PNG so the real analysis can later mirror its
panel layout (the actual figure should look like the mockup, just with real data). Set
each figure entry's `mockup_image` to the PNG path. At execute time, fill `image_path`
with the real figure; the brief then shows mockup and result side by side, and the
match between them is the visual proof that the pre-registration held.

Guidance for the script: matplotlib only (no seaborn dependency required), synthetic
data from a small explicit toy model, a figure-level suptitle or text box reading
"MOCKUP - synthetic data", panel titles per the three-beat story, axis labels with
units, and a legend. Save at >=150 dpi so the embedded PNG stays crisp.
