#!/usr/bin/env python
"""Generate the synthetic ``vmn_lag1_history_counts`` analysis export.

Deterministic (seeded): running it twice yields byte-identical files, so the
fixture can be regenerated at will and the gold file stays in step with the
files on disk. Stdlib only.

Output tree (``fixture/`` next to this script unless ``--out`` is given)::

    scripts/    5 Python scripts
    data/       5 CSV outputs
    figures/    10 small valid PNGs
    docs/       3 markdown documents
    BRIEF.md.template   narrative the model reads ({QUESTION_ID}, {DATASET_ID})
    gold.json           ground truth for the scorer (never copied into a run)
"""

from __future__ import annotations

import argparse
import json
import random
import struct
import zlib
from pathlib import Path

PROJECT_NAME = "vmn_lag1_history_counts"
RUN_DATE = "2026-09-12"
SEED = 20260912

EXECUTION = {
    "kind": "script_run",
    "description": (
        "vmn_lag1_history_counts: fit a lag-1 spike-count history model to "
        "12 ON-parasol cells, bootstrap the population coefficient, and "
        "render the summary figures (2026-09-12)."
    ),
}

# ---------------------------------------------------------------------------
# Scripts
# ---------------------------------------------------------------------------

SCRIPTS: dict[str, tuple[str, str, str]] = {
    # relative path: (title, one-line description, body)
    "scripts/load_epochs.py": (
        "load_epochs",
        "Load the raw epoch table and bin spikes into 20 ms count vectors per cell.",
        '''"""Load raw epochs and bin spikes into fixed-width count vectors.

Reads ``data/raw_epochs_cell01.csv`` style tables (one row per spike) and
returns a dict of cell id -> list of per-bin spike counts.
"""

import csv
from collections import defaultdict

BIN_MS = 20.0


def load_counts(path, bin_ms=BIN_MS):
    """Return {cell_id: [count per bin]} for one raw epoch file."""
    spikes = defaultdict(list)
    with open(path) as f:
        for row in csv.DictReader(f):
            spikes[row["cell_id"]].append(float(row["spike_time_ms"]))
    counts = {}
    for cell, times in spikes.items():
        n_bins = int(max(times) // bin_ms) + 1
        vec = [0] * n_bins
        for t in times:
            vec[int(t // bin_ms)] += 1
        counts[cell] = vec
    return counts


if __name__ == "__main__":
    import sys

    c = load_counts(sys.argv[1])
    print({k: len(v) for k, v in c.items()})
''',
    ),
    "scripts/fit_lag1_history.py": (
        "fit_lag1_history",
        "Fit the lag-1 count history model (Poisson GLM with one history term) per cell.",
        '''"""Fit a lag-1 spike-count history model per cell.

Model: log E[n_t] = b0 + b1 * n_{t-1}. Fit by Newton steps on the Poisson
log-likelihood. Writes ``data/history_fit_params.csv``.
"""

import csv
import math


def fit_lag1(counts, n_iter=25):
    """Return (b0, b1, loglik) for one count vector."""
    x = counts[:-1]
    y = counts[1:]
    b0, b1 = math.log(max(sum(y) / len(y), 1e-3)), 0.0
    for _ in range(n_iter):
        mu = [math.exp(b0 + b1 * xi) for xi in x]
        g0 = sum(yi - mi for yi, mi in zip(y, mu))
        g1 = sum((yi - mi) * xi for yi, mi, xi in zip(y, mu, x))
        h00 = sum(mu)
        h01 = sum(mi * xi for mi, xi in zip(mu, x))
        h11 = sum(mi * xi * xi for mi, xi in zip(mu, x))
        det = h00 * h11 - h01 * h01
        if det <= 0:
            break
        b0 += (h11 * g0 - h01 * g1) / det
        b1 += (-h01 * g0 + h00 * g1) / det
    mu = [math.exp(b0 + b1 * xi) for xi in x]
    ll = sum(yi * math.log(mi) - mi for yi, mi in zip(y, mu))
    return b0, b1, ll


def write_params(rows, path):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["cell_id", "b0", "b1", "loglik"])
        w.writerows(rows)
''',
    ),
    "scripts/count_events.py": (
        "count_events",
        "Count spike events per cell and compute the Fano factor of the 20 ms counts.",
        '''"""Count events and compute the Fano factor per cell.

Writes ``data/lag1_counts_by_cell.csv`` (n_events, mean, var, fano) and the
per-cell event times for cell 01 (``data/event_times_cell01.csv``).
"""

import csv
import statistics


def fano(counts):
    m = statistics.fmean(counts)
    v = statistics.pvariance(counts)
    return v / m if m > 0 else float("nan")


def summarize(counts_by_cell):
    rows = []
    for cell, vec in sorted(counts_by_cell.items()):
        rows.append([cell, sum(vec), statistics.fmean(vec), statistics.pvariance(vec), fano(vec)])
    return rows


def write_summary(rows, path):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["cell_id", "n_events", "mean_count", "var_count", "fano"])
        w.writerows(rows)
''',
    ),
    "scripts/bootstrap_ci.py": (
        "bootstrap_ci",
        "Bootstrap 95% confidence intervals for the population lag-1 coefficient.",
        '''"""Bootstrap 95% CI for the population-mean lag-1 coefficient.

Resamples cells with replacement (2000 draws, seed 7) and writes
``data/bootstrap_ci.csv``.
"""

import csv
import random
import statistics

N_BOOT = 2000


def bootstrap_mean(values, n_boot=N_BOOT, seed=7):
    rng = random.Random(seed)
    means = []
    for _ in range(n_boot):
        draw = [rng.choice(values) for _ in values]
        means.append(statistics.fmean(draw))
    means.sort()
    lo = means[int(0.025 * n_boot)]
    hi = means[int(0.975 * n_boot)]
    return statistics.fmean(values), lo, hi


def write_ci(rows, path):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["quantity", "estimate", "ci_lo", "ci_hi", "n_boot"])
        w.writerows(rows)
''',
    ),
    "scripts/make_figures.py": (
        "make_figures",
        "Render the ten summary figures from the fitted parameters and count tables.",
        '''"""Render the summary figures for the lag-1 history analysis.

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
    print("\\n".join(render_all("figures", None, None, None)))
''',
    ),
}

# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

DATA_TITLES: dict[str, tuple[str, str]] = {
    "data/lag1_counts_by_cell.csv": (
        "lag1_counts_by_cell",
        "Per-cell event count, mean, variance and Fano factor of the 20 ms counts.",
    ),
    "data/history_fit_params.csv": (
        "history_fit_params",
        "Fitted lag-1 history model parameters (b0, b1, log-likelihood) per cell.",
    ),
    "data/bootstrap_ci.csv": (
        "bootstrap_ci",
        "Bootstrap 95% confidence intervals for the population-level quantities.",
    ),
    "data/event_times_cell01.csv": (
        "event_times_cell01",
        "Spike event times (ms) for cell 01, one row per event, first 10 events.",
    ),
    "data/summary_table.csv": (
        "summary_table",
        "One-row-per-cell summary joining fit parameters with count statistics.",
    ),
}

# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------

FIGURES: dict[str, tuple[str, str]] = {
    "figures/fig01_lag1_counts_hist.png": (
        "fig01_lag1_counts_hist",
        "Histogram of the fitted lag-1 coefficient b1 across the 12 cells.",
    ),
    "figures/fig02_event_raster_cell01.png": (
        "fig02_event_raster_cell01",
        "Spike raster for cell 01 across all epochs, 20 ms bins overlaid.",
    ),
    "figures/fig03_history_kernel.png": (
        "fig03_history_kernel",
        "Estimated count history kernel as a function of lag, population average.",
    ),
    "figures/fig04_fit_residuals.png": (
        "fig04_fit_residuals",
        "Pearson residuals of the lag-1 model versus fitted mean, all cells pooled.",
    ),
    "figures/fig05_bootstrap_ci.png": (
        "fig05_bootstrap_ci",
        "Bootstrap distribution of the population-mean b1 with the 95% interval marked.",
    ),
    "figures/fig06_fano_factor.png": (
        "fig06_fano_factor",
        "Fano factor of 20 ms counts per cell against the Poisson reference line.",
    ),
    "figures/fig07_count_autocorr.png": (
        "fig07_count_autocorr",
        "Autocorrelation of binned counts out to lag 10, per cell and averaged.",
    ),
    "figures/fig08_rate_vs_coef.png": (
        "fig08_rate_vs_coef",
        "Scatter of baseline firing rate against the fitted b1 with a linear trend.",
    ),
    "figures/fig09_per_cell_params.png": (
        "fig09_per_cell_params",
        "Dot plot of b0 and b1 with per-cell standard errors.",
    ),
    "figures/fig10_summary_grid.png": (
        "fig10_summary_grid",
        "Summary grid: held-out log-likelihood gain per cell for the lag-1 model.",
    ),
}

# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

DOCS: dict[str, tuple[str, str, str]] = {
    "docs/METHODS.md": (
        "METHODS",
        "Methods: recording, binning, the lag-1 Poisson GLM and the bootstrap.",
        f"""# Methods: {PROJECT_NAME}

Date: {RUN_DATE}

## Recordings

Twelve ON-parasol retinal ganglion cells recorded in loose-patch under a
full-field white-noise stimulus (8 ms frames, 50% contrast). Each cell
contributed between 40 and 60 epochs of 4 s.

## Binning

Spikes were binned at 20 ms (`scripts/load_epochs.py`). Counts from all epochs
of a cell were concatenated for fitting.

## Model

The lag-1 count history model is a Poisson GLM with a single history term,

    log E[n_t] = b0 + b1 * n_(t-1),

fit by Newton steps on the Poisson log-likelihood
(`scripts/fit_lag1_history.py`). Held-out log-likelihood used a 5-fold split
over epochs.

## Bootstrap

The population coefficient was bootstrapped by resampling cells with
replacement, 2000 draws (`scripts/bootstrap_ci.py`).
""",
    ),
    "docs/RESULTS.md": (
        "RESULTS",
        "Results narrative referencing the ten figures and the five data tables.",
        f"""# Results: {PROJECT_NAME}

Date: {RUN_DATE}

The fitted lag-1 coefficient is negative for most cells (fig01) and the
population mean is reliably below zero (fig05). The count history kernel
returns to baseline within a few bins (fig03). Counts are over-dispersed
relative to Poisson (fig06), and cells with higher baseline rates show less
suppression (fig08). Adding the lag-1 term improves held-out log-likelihood in
every cell (fig10).

Tables: `data/history_fit_params.csv`, `data/lag1_counts_by_cell.csv`,
`data/bootstrap_ci.csv`, `data/summary_table.csv`.
""",
    ),
    "docs/NOTES.md": (
        "NOTES",
        "Working notes and caveats from the analysis session.",
        f"""# Notes: {PROJECT_NAME}

- {RUN_DATE}: cell 07 has a short recording (40 epochs); its standard errors are
  the widest in fig09.
- The Newton fit occasionally overshoots on cells with very low rates; capped
  at 25 iterations, converged everywhere.
- Consider a lag-2 term next; the autocorrelation (fig07) hints at residual
  structure at lag 2 for three cells.
""",
    ),
}

# ---------------------------------------------------------------------------
# Findings: the six claims, each pinned to one figure
# ---------------------------------------------------------------------------

FINDINGS: list[dict] = [
    {
        "key": "negative in 9 of 12 cells",
        "text": "The fitted lag-1 history coefficient b1 is negative in 9 of 12 cells (median b1 = -0.14).",
        "confidence": 0.8,
        "figure": "figures/fig01_lag1_counts_hist.png",
    },
    {
        "key": "decays within 150 ms",
        "text": "The population-average count history kernel decays within 150 ms, so a single lag captures most of the history dependence at 20 ms binning.",
        "confidence": 0.7,
        "figure": "figures/fig03_history_kernel.png",
    },
    {
        "key": "excludes zero for the population mean",
        "text": "The bootstrap 95% confidence interval excludes zero for the population mean b1 (mean -0.12, CI [-0.19, -0.05], 2000 draws).",
        "confidence": 0.85,
        "figure": "figures/fig05_bootstrap_ci.png",
    },
    {
        "key": "exceeds Poisson expectation by 1.6x",
        "text": "Spike-count variance exceeds Poisson expectation by 1.6x on average (Fano factor 1.6, range 1.2 to 2.1).",
        "confidence": 0.75,
        "figure": "figures/fig06_fano_factor.png",
    },
    {
        "key": "weaker lag-1 suppression",
        "text": "Cells with higher baseline firing rate show weaker lag-1 suppression (Spearman rho = 0.58 between rate and b1).",
        "confidence": 0.6,
        "figure": "figures/fig08_rate_vs_coef.png",
    },
    {
        "key": "improves held-out log-likelihood",
        "text": "The model with a lag-1 term improves held-out log-likelihood over the rate-only model in all 12 cells (median gain 0.031 bits per bin).",
        "confidence": 0.65,
        "figure": "figures/fig10_summary_grid.png",
    },
]


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------


def _png(width: int, height: int, pixel) -> bytes:
    """Encode an RGB PNG with stdlib only. ``pixel(x, y) -> (r, g, b)``."""

    def chunk(tag: bytes, payload: bytes) -> bytes:
        return (
            struct.pack(">I", len(payload))
            + tag
            + payload
            + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)
        )

    raw = bytearray()
    for y in range(height):
        raw.append(0)  # filter type: none
        for x in range(width):
            raw.extend(pixel(x, y))
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + chunk(b"IEND", b"")
    )


def _write(path: Path, content: str | bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content)


def _csv_rows(rng: random.Random, rel: str) -> str:
    cells = [f"cell{i:02d}" for i in range(1, 13)]
    if rel == "data/lag1_counts_by_cell.csv":
        lines = ["cell_id,n_events,mean_count,var_count,fano"]
        for c in cells[:10]:
            m = rng.uniform(0.4, 1.6)
            f = rng.uniform(1.2, 2.1)
            lines.append(f"{c},{int(m * 2400)},{m:.3f},{m * f:.3f},{f:.2f}")
    elif rel == "data/history_fit_params.csv":
        lines = ["cell_id,b0,b1,loglik"]
        for c in cells[:10]:
            lines.append(
                f"{c},{rng.uniform(-0.8, 0.5):.4f},{rng.uniform(-0.35, 0.08):.4f},"
                f"{rng.uniform(-3200, -1800):.1f}"
            )
    elif rel == "data/bootstrap_ci.csv":
        lines = ["quantity,estimate,ci_lo,ci_hi,n_boot"]
        quantities = [
            "mean_b1", "median_b1", "mean_b0", "mean_fano", "median_fano",
            "mean_rate_hz", "kernel_tau_ms", "frac_negative_b1", "mean_ll_gain",
            "median_ll_gain",
        ]
        for q in quantities:
            est = rng.uniform(-0.5, 2.0)
            w = rng.uniform(0.02, 0.4)
            lines.append(f"{q},{est:.4f},{est - w:.4f},{est + w:.4f},2000")
    elif rel == "data/event_times_cell01.csv":
        lines = ["event_index,epoch,spike_time_ms"]
        t = 0.0
        for i in range(10):
            t += rng.expovariate(1 / 35.0)
            lines.append(f"{i},1,{t:.2f}")
    elif rel == "data/summary_table.csv":
        lines = ["cell_id,rate_hz,b1,fano,ll_gain_bits"]
        for c in cells[:10]:
            lines.append(
                f"{c},{rng.uniform(8, 40):.2f},{rng.uniform(-0.35, 0.08):.4f},"
                f"{rng.uniform(1.2, 2.1):.2f},{rng.uniform(0.01, 0.06):.4f}"
            )
    else:  # pragma: no cover - every data file is enumerated above
        raise KeyError(rel)
    return "\n".join(lines) + "\n"


def _brief_template() -> str:
    lines = [
        f"# BRIEF: {PROJECT_NAME}",
        "",
        f"Run date: {RUN_DATE}",
        "",
        "## What was run",
        "",
        "One execution of kind `script_run`:",
        "",
        f"> {EXECUTION['description']}",
        "",
        "The run consumed two nodes that already exist in the Wheeler graph:",
        "",
        "- the open question `{QUESTION_ID}` (does spike-count history at lag 1 shape ON-parasol counts?)",
        "- the raw dataset `{DATASET_ID}` (`data/raw_epochs_cell01.csv`, the raw epoch table)",
        "",
        "The execution USED both of them.",
        "",
        "## Files produced by the run",
        "",
        "Every file below WAS_GENERATED_BY the execution. Paths are relative to this project directory.",
        "",
        "### Scripts",
        "",
    ]
    for rel, (title, desc, _body) in SCRIPTS.items():
        lines.append(f"- `{rel}` (title: `{title}`): {desc}")
    lines += ["", "### Data tables", ""]
    for rel, (title, desc) in DATA_TITLES.items():
        lines.append(f"- `{rel}` (title: `{title}`): {desc}")
    lines += ["", "### Figures", ""]
    for rel, (title, desc) in FIGURES.items():
        lines.append(f"- `{rel}` (title: `{title}`): {desc}")
    lines += ["", "### Documents", ""]
    for rel, (title, desc, _body) in DOCS.items():
        lines.append(f"- `{rel}` (title: `{title}`): {desc}")
    lines += [
        "",
        "## Findings",
        "",
        "Six findings came out of the run. Record each one VERBATIM as its own Finding "
        "node with the stated confidence. Each finding WAS_GENERATED_BY the execution, "
        "APPEARS_IN exactly the one figure named, and is RELEVANT_TO the open question "
        "`{QUESTION_ID}`.",
        "",
    ]
    for i, f in enumerate(FINDINGS, 1):
        lines.append(f"{i}. \"{f['text']}\"")
        lines.append(f"   confidence: {f['confidence']}; appears in `{f['figure']}`")
        lines.append("")
    lines += [
        "## Provenance summary",
        "",
        "- 1 Execution node (kind `script_run`)",
        f"- {len(SCRIPTS) + len(DATA_TITLES) + len(FIGURES) + len(DOCS)} file artifacts "
        f"({len(SCRIPTS)} scripts, {len(DATA_TITLES)} data tables, {len(FIGURES)} figures, "
        f"{len(DOCS)} documents), each WAS_GENERATED_BY the execution",
        f"- {len(FINDINGS)} Finding nodes, each WAS_GENERATED_BY the execution, APPEARS_IN "
        "one figure, RELEVANT_TO `{QUESTION_ID}`",
        "- the execution USED `{DATASET_ID}` and USED `{QUESTION_ID}`",
        "",
    ]
    return "\n".join(lines)


def _gold() -> dict:
    artifacts: dict[str, dict] = {}
    for rel, (title, desc, _body) in SCRIPTS.items():
        artifacts[rel] = {"label": "Script", "title": title, "description": desc}
    for rel, (title, desc) in DATA_TITLES.items():
        artifacts[rel] = {"label": "Dataset", "title": title, "description": desc}
    for rel, (title, desc) in FIGURES.items():
        artifacts[rel] = {
            "label": "Finding",
            "artifact_type": "figure",
            "title": title,
            "description": desc,
        }
    for rel, (title, desc, _body) in DOCS.items():
        artifacts[rel] = {"label": "Document", "title": title, "description": desc}

    findings = {f["key"]: dict(f) for f in FINDINGS}

    edges: list[list[str]] = []
    for rel in artifacts:
        edges.append([rel, "WAS_GENERATED_BY", "exec"])
    for f in FINDINGS:
        edges.append([f"finding:{f['key']}", "WAS_GENERATED_BY", "exec"])
    for f in FINDINGS:
        edges.append([f"finding:{f['key']}", "APPEARS_IN", f["figure"]])
    for f in FINDINGS:
        edges.append([f"finding:{f['key']}", "RELEVANT_TO", "QUESTION_ID"])
    edges.append(["exec", "USED", "DATASET_ID"])
    edges.append(["exec", "USED", "QUESTION_ID"])

    return {
        "project": PROJECT_NAME,
        "date": RUN_DATE,
        "seed_question": (
            "Does spike-count history at lag 1 shape ON-parasol spike counts "
            "under white-noise stimulation?"
        ),
        "seed_dataset": {
            "path": "data/raw_epochs_cell01.csv",
            "type": "csv",
            "description": "Raw epoch table for cell 01: one row per spike (epoch, spike_time_ms).",
        },
        "nodes": {
            "execution": EXECUTION,
            "artifacts": artifacts,
            "findings": findings,
        },
        "edges": edges,
        "counts": {
            "artifacts": len(artifacts),
            "findings": len(findings),
            "edges": len(edges),
        },
    }


def build(out: Path) -> dict:
    rng = random.Random(SEED)
    for rel, (_title, _desc, body) in SCRIPTS.items():
        _write(out / rel, body)
    for rel in DATA_TITLES:
        _write(out / rel, _csv_rows(rng, rel))
    for i, rel in enumerate(FIGURES):
        # Distinct gradient per figure so the files differ (and so do hashes).
        shift = i * 23

        def pixel(x: int, y: int, shift: int = shift) -> tuple[int, int, int]:
            return ((x * 16 + shift) % 256, (y * 16 + shift) % 256, (x * y + shift) % 256)

        _write(out / rel, _png(16, 16, pixel))
    for rel, (_title, _desc, body) in DOCS.items():
        _write(out / rel, body)
    _write(out / "BRIEF.md.template", _brief_template())
    gold = _gold()
    _write(out / "gold.json", json.dumps(gold, indent=2) + "\n")
    return gold


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parent / "fixture",
        help="output directory (default: fixture/ next to this script)",
    )
    ns = ap.parse_args()
    gold = build(ns.out)
    c = gold["counts"]
    print(
        f"fixture written to {ns.out}: {c['artifacts']} artifacts, "
        f"{c['findings']} findings, {c['edges']} gold edges"
    )


if __name__ == "__main__":
    main()
