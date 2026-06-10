# Mockup SVG conventions

Figure mockups are pre-registration sketches: they show what the figure will look like
and what trend is predicted, before any data is touched. They are drawn by hand as
inline SVG strings in the spec's `figures[].mockup_svg` field. The scientist reads them
in the brief, so clarity beats polish.

## Hard rules (the renderer depends on these)

- The string starts with `<svg` and contains no `<script>` tag. The renderer rejects
  anything else.
- `viewBox="0 0 480 320"`, no `width`/`height` attributes (the card scales it).
- Every stroke and fill uses `currentColor` (with `opacity` for de-emphasis). This is
  what makes the mockup legible in both light and dark themes.
- Stroke width 1.5 or greater. Thin hairlines disappear on retina displays.
- No external fonts, no `<image>` elements, no CSS classes. Inline attributes only.
- `role="img"` and an `aria-label` of the form "Mockup: <title>".

## Anatomy of a good mockup

1. Title text at the top, font-size 15, ending in "(mockup)".
2. Axis lines with axis labels in plain words and units where known
   (font-size 13). A y-axis label rotated -90 degrees is fine.
3. The expected trend drawn DASHED (`stroke-dasharray="7 5"`). Dashed means
   prediction, solid means data; never draw the predicted curve solid.
4. A few representative data marks (circles, bars, box outlines) at reduced opacity
   (0.4 to 0.5) to show the plot type, not fake data values.
5. Optional one-line annotation of the prediction near the curve, font-size 12,
   opacity 0.7 (for example "expected: saturating rise").

## Competing hypotheses in one mockup

When the figure is the discriminating test between hypotheses, draw one predicted
trend per hypothesis so the scientist sees at a glance how the outcomes differ:

- Each hypothesis gets its own dash pattern: `stroke-dasharray="7 5"` for the first,
  `"2 4"` (dotted) for the second, `"10 3 2 3"` (dash-dot) for a third.
- Label each curve in text at its end point with the hypothesis name (for example
  "H1: saturates", "H0: flat"), font-size 12. Never rely on the dash pattern alone.
- Mirror the same hypotheses in the figure entry's `hypotheses` field so the brief
  renders a matching legend with `[H-xxxx]` badges.

## What NOT to do

- Do not invent plausible-looking numbers or tick values that could be mistaken for
  results. Ticks can be unlabeled or use round placeholder values (0, 0.5, 1).
- Do not draw more than one panel per mockup. One figure entry = one panel; multi-panel
  figures get one entry per panel (fig_A, fig_B, ...).
- Do not encode meaning in color alone. The mockup is monochrome (currentColor) by
  design; use dash patterns, marker shapes, and text labels to distinguish series.
- Do not exceed roughly 25 SVG elements. If the sketch needs more, it is too detailed
  for a mockup.

## Plot-type starters

- Scatter + trend: axis lines, 4 to 6 circles opacity 0.45, dashed bezier trend.
- Distributions: dashed rect outlines (boxes) with a solid median line, category labels
  under the x axis.
- Time series: dashed wavy path, x label "time (s)".
- Heatmap: 3x3 grid of rects with opacity steps 0.15 / 0.4 / 0.7 and a small
  "low to high" text legend, never a color gradient.
