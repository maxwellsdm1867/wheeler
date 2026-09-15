"""Render the summary figures for the lag-1 history analysis.

Every figure is written to ``figures/figNN_<slug>.png``. The slug is the
figure's title so the file name, the graph node and the on-figure title
match.
"""

FIGURES = [
    "fig01_lag1_counts_hist",
    "fig02_event_raster_cell01",
    "fig03_history_kernel",
    "fig04_fit_residuals",
    "fig05_bootstrap_ci",
    "fig06_fano_factor",
    "fig07_count_autocorr",
    "fig08_rate_vs_coef",
    "fig09_per_cell_params",
    "fig10_summary_grid",
]


def render_all(out_dir, params, counts, ci):
    """Render every figure in FIGURES into out_dir (plotting backend elided)."""
    paths = []
    for slug in FIGURES:
        path = f"{out_dir}/{slug}.png"
        paths.append(path)
    return paths


if __name__ == "__main__":
    print("\n".join(render_all("figures", None, None, None)))
