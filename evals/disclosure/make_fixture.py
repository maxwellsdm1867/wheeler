#!/usr/bin/env python
"""Build the deterministic fixture for the progressive-disclosure experiment.

Writes ``fixture/``:

    graph.json      nodes (symbolic key -> add_* tool + args) and edges by key
    tasks.json      10 research-agent tasks with gold answers by symbolic key
    files/          the project tree the nodes point at: scripts, CSV datasets,
                    markdown documents and 6 stdlib-encoded PNG figures

The graph is a synthetic retinal-electrophysiology project: one open question
about contrast-dependent shortening of the spike-history kernel in primate
parasol cells, three hypotheses, 14 findings, 6 figures, 6 scripts, 5 datasets,
7 executions, 3 documents and 20 papers, wired with about 110 PROV and semantic
edges. Every byte is a function of the literals below, so re-running the script
reproduces the tree exactly (the harness checks this).

    PYTHONPATH=$PWD .venv/bin/python evals/disclosure/make_fixture.py
"""

from __future__ import annotations

import json
import math
import struct
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "fixture"
FILES = FIXTURE / "files"

SEED = 20260914

# ---------------------------------------------------------------------------
# Nodes. Each entry: key -> (tool, args). Paths are project-relative; run.py
# resolves them against the scratch project before calling execute_tool.
# ---------------------------------------------------------------------------

QUESTION = {
    "Q1": (
        "add_question",
        {
            "question": (
                "Does the spike-history kernel of primate parasol retinal ganglion "
                "cells shorten under high contrast, and is the shortening explained "
                "by adaptation of the slow afterhyperpolarization rather than by a "
                "change in spike threshold?"
            ),
            "priority": 8,
        },
    ),
}

HYPOTHESES = {
    # H1: contradicted (status rejected). H2: supported. H3: open.
    "H1": (
        "add_hypothesis",
        {
            "statement": (
                "The contrast-dependent shortening of the spike-history kernel is "
                "absent in OFF parasol cells: their slow kernel time constant is "
                "contrast-invariant between 10 percent and 50 percent contrast."
            ),
            "status": "rejected",
        },
    ),
    "H2": (
        "add_hypothesis",
        {
            "statement": (
                "ON parasol spike-history kernels shorten by more than 30 percent "
                "(slow time constant) between 10 percent and 50 percent contrast."
            ),
            "status": "supported",
        },
    ),
    "H3": (
        "add_hypothesis",
        {
            "statement": (
                "Kernel shortening is driven by a reduction of the slow "
                "afterhyperpolarization current, not by a change in spike threshold."
            ),
            "status": "open",
        },
    ),
}

# Finding texts. Lengths vary between 300 and 1,500 characters and every one
# carries numbers, the way lab findings do. F11 holds the task 5 number past
# character 240 and F10 holds the task 6 phrase past character 400; the checks
# at the bottom of this file enforce both.
FINDINGS: dict[str, dict] = {
    "F01": {
        "title": "ON parasol slow kernel time constant falls 43 percent from 10 to 50 percent contrast",
        "confidence": 0.85,
        "description": (
            "Spike-history kernel time constant of ON parasol cells falls from 38.4 ms at "
            "10 percent contrast to 21.7 ms at 50 percent contrast (n = 17 cells, 3 retinas). "
            "The fit used the two-exponential SRM kernel from fit_srm.py with 2 ms bins; the "
            "fast component (tau_1 = 4.1 +/- 0.6 ms) was contrast-independent, so the "
            "shortening is carried entirely by the slow component. Median shortening was 43 "
            "percent (IQR 35 to 51 percent), exceeding the 30 percent threshold in every retina. "
            "Bootstrap 95 percent CI on the pooled ratio of slow time constants (50 over 10 "
            "percent): 0.51 to 0.63."
        ),
    },
    "F02": {
        "title": "Slow kernel time constant follows a power law in contrast with exponent -0.36",
        "confidence": 0.78,
        "description": (
            "Kernel shortening in ON parasol cells is graded across five contrast levels (10, "
            "20, 30, 40, 50 percent) rather than stepped: slow time constant 38.4, 33.0, 28.9, "
            "24.6, 21.7 ms. A power law tau_slow = 91.2 * c^-0.36 (c in percent) fits with "
            "R^2 = 0.97 across cells, and the exponent did not differ between retinas (range "
            "-0.33 to -0.39). A saturating exponential fit worse (R^2 = 0.91) and left "
            "structured residuals at 40 and 50 percent contrast, so the graded description is "
            "preferred for the manuscript figure."
        ),
    },
    "F03": {
        "title": "Contrast dependence of the slow kernel is stable within recordings",
        "confidence": 0.70,
        "description": (
            "The contrast dependence of the slow kernel is stable across the recording: "
            "splitting each cell's epochs into first and second halves gives power-law "
            "exponents of -0.35 and -0.37 (paired difference 0.02, p = 0.61, n = 17), so the "
            "shortening is not a rundown artefact. Cells recorded for more than 40 minutes "
            "(n = 6) showed the same exponents as short recordings (-0.36 versus -0.36)."
        ),
    },
    "F04": {
        "title": "OFF parasol cells also shorten their spike-history kernel with contrast",
        "confidence": 0.80,
        "description": (
            "OFF parasol cells also shorten their spike-history kernel with contrast: slow "
            "time constant 44.9 ms at 10 percent falling to 27.2 ms at 50 percent contrast "
            "(n = 11 cells, 2 retinas), a 39 percent median reduction (IQR 31 to 46 percent). "
            "This is opposite to the prediction that OFF parasol kernels are contrast-"
            "invariant. The fast component (3.8 +/- 0.5 ms) was unchanged, matching the ON "
            "parasol pattern. Fits used the same fit_srm.py settings (2 ms bins, two-"
            "exponential kernel, 300 ms history window)."
        ),
    },
    "F05": {
        "title": "Kernel shortening survives firing-rate matching",
        "confidence": 0.74,
        "description": (
            "Kernel shortening in ON parasol cells does not depend on mean firing rate: "
            "restricting the 50 percent contrast epochs to rate-matched windows (mean rate 22 "
            "to 26 Hz, matching the 10 percent contrast rate) still gives tau_slow = 23.1 ms "
            "versus 38.4 ms at 10 percent contrast (n = 12 cells with enough rate-matched "
            "epochs). Rate matching removed 31 percent of the spikes but changed the ratio of "
            "time constants by only 0.03."
        ),
    },
    "F06": {
        "title": "OFF to ON slow time constant ratio is constant at 1.19 across contrast",
        "confidence": 0.76,
        "description": (
            "The ratio of OFF to ON parasol slow time constants is constant across contrast "
            "at 1.19 +/- 0.07 (10 percent: 1.17, 30 percent: 1.21, 50 percent: 1.25). If OFF "
            "cells lacked the shortening the ratio would rise to about 2.1 at 50 percent "
            "contrast; the observed value rules that out with a 95 percent CI of 1.05 to 1.33. "
            "The comparison uses the 2026-03 ON dataset and the 2026-04 OFF dataset, which were "
            "recorded with the same stimulus protocol and bath temperature (32 to 33 C)."
        ),
    },
    "F07": {
        "title": "A small OFF parasol subset shows less than 15 percent shortening",
        "confidence": 0.40,
        "description": (
            "A subset of 3 of 11 OFF parasol cells showed less than 15 percent shortening "
            "between 10 and 50 percent contrast (values 8, 11 and 14 percent). These cells had "
            "the lowest baseline firing rates (below 9 Hz at 10 percent contrast). This is "
            "consistent with a contrast-invariant OFF subpopulation, but the sample is too "
            "small to separate it from noise (permutation p = 0.19)."
        ),
    },
    "F08": {
        "title": "Slow AHP amplitude falls with contrast and tracks the slow kernel time constant",
        "confidence": 0.68,
        "description": (
            "Slow afterhyperpolarization amplitude, measured from the average post-spike "
            "voltage in current-clamp recordings, falls from -6.2 mV at 10 percent contrast to "
            "-3.4 mV at 50 percent contrast (n = 8 ON parasol cells). Across cells, AHP "
            "amplitude and slow kernel time constant are correlated with r = 0.81 (p = 0.002), "
            "and the per-cell change in AHP amplitude predicts the change in tau_slow with a "
            "slope of 4.6 ms per mV (95 percent CI 2.9 to 6.3). Spike threshold, estimated "
            "from the dV/dt criterion, moved by only 0.8 mV over the same contrast range."
        ),
    },
    "F09": {
        "title": "Two control ON parasol cells shortened by less than 30 percent",
        "confidence": 0.45,
        "description": (
            "Two ON parasol cells in the 2026-04 OFF-cell dataset (recorded as controls) "
            "showed kernel shortening of only 18 and 22 percent between 10 and 50 percent "
            "contrast, below the 30 percent threshold. Both had unusually high input "
            "resistance (over 180 MOhm) and may have been damaged during sealing; they are "
            "excluded from the main ON parasol sample but are reported here for completeness."
        ),
    },
    "F10": {
        "title": "Threshold dynamics do not account for the kernel shortening",
        "confidence": 0.62,
        "description": (
            "Spike threshold dynamics do not account for the kernel shortening. A dynamic-"
            "threshold SRM variant (threshold rising by theta_0 after each spike and decaying "
            "with time constant tau_theta) fitted to the same ON parasol epochs gives "
            "tau_theta = 12.3 ms at 10 percent contrast and 11.6 ms at 50 percent contrast "
            "(n = 8 cells), a change of 6 percent that is far smaller than the 43 percent "
            "shortening of the slow history kernel. Fixing the threshold parameters at their "
            "10 percent values and refitting only the kernel at 50 percent contrast recovers "
            "the full shortening (tau_slow = 22.0 ms versus 21.7 ms in the free fit). In "
            "cesium-blocked control epochs (2 mM external Cs+ to suppress the h-current, "
            "n = 5 cells), the slow kernel time constant at 10 percent contrast rose to 46.1 ms "
            "and the contrast-dependent shortening was reduced to 27 percent, which points to "
            "a hyperpolarization-activated conductance contributing to the slow kernel. "
            "Together these two controls favour a conductance-based mechanism over a "
            "threshold-based one, although the cesium sample is small."
        ),
    },
    "F11": {
        "title": "First-spike latency to a contrast step in ON parasol cells shortens with step amplitude",
        "confidence": 0.72,
        "description": (
            "First-spike latency to a contrast step in ON parasol cells shortens with step "
            "amplitude. Latency was measured from step onset to the first spike in each epoch, "
            "pooled over 15 cells, and summarised by the mode of the pooled latency histogram "
            "(1 ms bins) rather than by the mean, because the distribution has a long tail from "
            "epochs in which the cell skipped the first stimulus cycle. At 10 percent contrast "
            "the histogram peak latency is 47.3 ms; at 50 percent contrast it is 31.8 ms. The "
            "latency shift is complete within the first 200 ms of the step and does not change "
            "over the 4 s step duration."
        ),
    },
    "F12": {
        "title": "Latency shortening and kernel shortening co-vary across cells",
        "confidence": 0.60,
        "description": (
            "Latency shortening and kernel shortening co-vary across cells: the per-cell "
            "reduction in first-spike latency between 10 and 50 percent contrast correlates "
            "with the per-cell reduction in slow kernel time constant with r = 0.66 (p = 0.008, "
            "n = 15 ON parasol cells). The correlation survives partialling out the change in "
            "mean firing rate (partial r = 0.58). This is an interpretation: the two measures "
            "may share a common cause in the afterhyperpolarization rather than one driving "
            "the other."
        ),
    },
    "F13": {
        "title": "Bootstrap CI for the ON parasol slow time constant ratio is 0.52 to 0.62",
        "confidence": 0.80,
        "description": (
            "Bootstrap over cells (10,000 resamples, seed 7) gives a 95 percent CI for the "
            "pooled ON parasol slow time constant ratio (50 over 10 percent contrast) of 0.52 to "
            "0.62, consistent with the parametric interval 0.51 to 0.63 reported earlier. The "
            "bootstrap distribution is slightly right-skewed (skewness 0.31) because three "
            "cells with long baseline kernels dominate the upper tail."
        ),
    },
    "F14": {
        "title": "Bootstrap CI for the OFF parasol slow time constant ratio is 0.55 to 0.68",
        "confidence": 0.77,
        "description": (
            "Bootstrap over cells (10,000 resamples, seed 7) gives a 95 percent CI for the "
            "pooled OFF parasol slow time constant ratio (50 over 10 percent contrast) of 0.55 "
            "to 0.68 (n = 11 cells). The ON and OFF intervals overlap by 0.07, and a two-sample "
            "bootstrap of the difference in ratios gives a 95 percent CI of -0.04 to 0.13, so "
            "the two cell types shorten by statistically indistinguishable amounts."
        ),
    },
}

# Order of the title-stamping pass. ``update_node`` sets ``updated`` on every
# finding it touches, so this order defines "most recently updated". The three
# findings RELEVANT_TO the question that come last are the task 9 gold.
UPDATE_ORDER = ["F13", "F14", "F11", "F01", "F03", "F04", "F06", "F07", "F08", "F09", "F10", "F12", "F05", "F02"]

FIGURES = {
    "fig01": ("figures/fig01_kernel_tau_vs_contrast.png",
              "Slow kernel time constant versus contrast for 17 ON parasol cells with power-law fit."),
    "fig02": ("figures/fig02_on_kernels_overlay.png",
              "Overlay of ON parasol spike-history kernels at five contrast levels, population mean."),
    "fig03": ("figures/fig03_off_parasol_kernels.png",
              "OFF parasol spike-history kernels at 10 and 50 percent contrast, 11 cells."),
    "fig04": ("figures/fig04_off_vs_on_tau_ratio.png",
              "Ratio of OFF to ON slow time constants across contrast with bootstrap CI."),
    "fig05": ("figures/fig05_ahp_amplitude_vs_tau.png",
              "Slow AHP amplitude against slow kernel time constant per cell, 8 ON parasol cells."),
    "fig06": ("figures/fig06_first_spike_latency.png",
              "First-spike latency histograms at 10 and 50 percent contrast, 15 ON parasol cells."),
}

SCRIPTS = {
    "S1": "scripts/preprocess_epochs.py",
    "S2": "scripts/analyze_off_parasol.py",
    "S3": "scripts/fit_srm.py",
    "S4": "scripts/plot_on_kernels.py",
    "S5": "scripts/ahp_analysis.py",
    "S6": "scripts/latency_summary.py",
}

DATASETS = {
    "Draw1": ("data/raw/on_parasol_contrast_steps_2026-03.csv",
              "Raw spike times and stimulus contrast per epoch, 17 ON parasol cells, 3 retinas, March 2026."),
    "Draw2": ("data/raw/off_parasol_contrast_steps_2026-04.csv",
              "Raw spike times and stimulus contrast per epoch, 11 OFF parasol cells plus 2 ON controls, April 2026."),
    "Draw3": ("data/raw/on_parasol_current_clamp_2026-05.csv",
              "Current-clamp membrane voltage traces for AHP and latency analysis, 15 ON parasol cells, May 2026."),
    "Dint1": ("data/interim/on_parasol_spike_trains.csv",
              "Binned ON parasol spike trains (2 ms) with contrast labels, output of preprocess_epochs.py."),
    "Dint2": ("data/interim/srm_fits_on_parasol.csv",
              "Fitted SRM kernel parameters per cell and contrast level, output of fit_srm.py."),
}

EXECUTIONS = {
    "X1": "preprocess_epochs.py on the 2026-03 ON parasol raw epochs: 2 ms binning, artefact rejection, contrast labelling",
    "X2": "fit_srm.py on the binned ON parasol spike trains: two-exponential history kernel per cell and contrast",
    "X3": "plot_on_kernels.py on the ON parasol SRM fits: kernel overlays, tau versus contrast, power-law fit",
    "X4": "analyze_off_parasol.py on the 2026-04 OFF parasol raw epochs: preprocessing, SRM fits and OFF versus ON comparison",
    "X5": "ahp_analysis.py on the current-clamp traces and the ON parasol SRM fits: AHP amplitude, threshold dynamics, cesium controls",
    "X6": "latency_summary.py on the current-clamp traces: first-spike latency histograms and their relation to kernel shortening",
    "X7": "ahp_analysis.py --bootstrap on the ON parasol SRM fits: 10,000-resample confidence intervals for the time constant ratios",
}

DOCUMENTS = {
    "W1": ("Contrast-dependent shortening of spike-history kernels in primate parasol cells",
           "docs/manuscript_kernel_shortening.md", "draft"),
    "W2": ("Literature review: spike-history and afterhyperpolarization in retinal ganglion cells",
           "docs/review_ahp_literature.md", "revision"),
    "W3": ("Lab notebook: SRM fitting protocol and parameter conventions",
           "docs/notebook_srm_protocol.md", "final"),
}

PAPERS = [
    ("P01", "Spike-history dependence of retinal ganglion cell firing under natural contrast", "Alvarez, M., Okonkwo, T., Lindqvist, S.", 2019),
    ("P02", "A spike response model of primate parasol cells", "Bergström, L., Nakamura, K.", 2015),
    ("P03", "Afterhyperpolarization currents in mammalian retinal ganglion cells", "Chen, Y., Duarte, P., Feldman, R.", 2012),
    ("P04", "Contrast adaptation in the primate retina: cellular mechanisms", "Duarte, P., Alvarez, M.", 2017),
    ("P05", "Generalized linear models of retinal spike trains", "Eriksen, H., Fischer, G., Gupta, A.", 2008),
    ("P06", "Dynamic threshold models reproduce adaptation in ganglion cell spiking", "Fischer, G., Hoang, L.", 2020),
    ("P07", "ON and OFF parasol cells differ in intrinsic excitability", "Gupta, A., Ibarra, C.", 2016),
    ("P08", "Slow potassium currents shape the interspike interval distribution in retina", "Hoang, L., Jensen, O., Kimura, S.", 2014),
    ("P09", "The h-current in retinal ganglion cells: pharmacology and function", "Ibarra, C., Lindqvist, S.", 2011),
    ("P10", "First-spike latency coding in the retina", "Jensen, O., Moreau, D.", 2013),
    ("P11", "Firing-rate adaptation and history filters: a unifying account", "Kimura, S., Nakamura, K., Okonkwo, T.", 2021),
    ("P12", "Bootstrap methods for neural time constant estimation", "Lindqvist, S., Petrov, V.", 2018),
    ("P13", "Cesium block of Ih alters spike timing in ganglion cells", "Moreau, D., Chen, Y.", 2010),
    ("P14", "Contrast gain control at the ganglion cell spike generator", "Nakamura, K., Bergström, L.", 2022),
    ("P15", "Sodium channel inactivation and spike-history effects in the retina", "Okonkwo, T., Quiroga, F.", 2009),
    ("P16", "Rate matching as a control for adaptation studies", "Petrov, V., Eriksen, H.", 2019),
    ("P17", "Power-law dynamics of neuronal adaptation", "Quiroga, F., Rasmussen, E.", 2007),
    ("P18", "Recording stability criteria for long whole-cell retinal recordings", "Rasmussen, E., Sato, M.", 2016),
    ("P19", "Input resistance as a marker of cell health in patch recordings", "Sato, M., Thornton, W.", 2014),
    ("P20", "Kernel estimation for point-process models of spiking", "Thornton, W., Alvarez, M.", 2023),
]

# Document -> cited papers. W1 cites 10, W2 cites 12 (overlapping), W3 none.
CITES = {
    "W1": ["P01", "P02", "P03", "P04", "P05", "P06", "P07", "P11", "P12", "P14"],
    "W2": ["P03", "P05", "P06", "P08", "P09", "P10", "P11", "P13", "P15", "P16", "P17", "P20"],
}

# Which execution generated which figure and finding.
GENERATED_BY = {
    "Dint1": "X1", "Dint2": "X2",
    "fig01": "X3", "fig02": "X3", "fig03": "X4", "fig04": "X4", "fig05": "X5", "fig06": "X6",
    "F01": "X3", "F02": "X3", "F03": "X3", "F05": "X3",
    "F04": "X4", "F06": "X4", "F07": "X4", "F09": "X4",
    "F08": "X5", "F10": "X5",
    "F11": "X6", "F12": "X6",
    "F13": "X7", "F14": "X7",
}

USED = {
    "X1": ["S1", "Draw1"],
    "X2": ["S3", "Dint1"],
    "X3": ["S4", "Dint2"],
    "X4": ["S2", "Draw2"],
    "X5": ["S5", "Dint2", "Draw3"],
    "X6": ["S6", "Draw3"],
    "X7": ["S5", "Dint2"],
}

APPEARS_IN = {
    "F01": "fig01", "F02": "fig02", "F03": "fig02", "F04": "fig03", "F05": "fig01",
    "F06": "fig04", "F07": "fig04", "F08": "fig05", "F09": "fig03", "F10": "fig05",
    "F11": "fig06", "F12": "fig06", "F13": "fig05", "F14": "fig06",
}

SUPPORTS = [("F01", "H2"), ("F02", "H2"), ("F03", "H2"), ("F05", "H2"),
            ("F07", "H1"), ("F08", "H3"), ("F10", "H3")]
CONTRADICTS = [("F04", "H1"), ("F06", "H1"), ("F09", "H2")]
RELEVANT_FINDINGS = ["F01", "F02", "F03", "F04", "F05", "F06", "F07", "F08", "F09", "F10", "F12"]
RELEVANT_PAPERS = ["P01", "P02", "P04", "P06", "P14"]
DERIVED_FROM = [("F02", "F01"), ("F03", "F02"), ("F12", "F11")]
INFORMED_BY = [("X2", "X1"), ("X3", "X2"), ("X5", "X2"), ("X7", "X5")]


# ---------------------------------------------------------------------------
# Files
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
        raw.append(0)
        for x in range(width):
            raw.extend(pixel(x, y))
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + chunk(b"IEND", b"")
    )


def _figure_pixels(index: int):
    """A distinct deterministic pattern per figure: a decaying curve on a grid."""

    def pixel(x: int, y: int) -> tuple[int, int, int]:
        curve = 28 - int(20 * math.exp(-x / (6.0 + 2.5 * index)))
        if abs(y - curve) <= 0:
            return (30 + 30 * index, 60, 200 - 20 * index)
        if x % 8 == 0 or y % 8 == 0:
            return (225, 225, 225)
        return (250, 250, 250)

    return pixel


def _csv(key: str, rows: int) -> str:
    """Deterministic CSV body: values are closed-form in the row index."""
    if key.startswith("Draw"):
        header = "cell,epoch,contrast_pct,spike_time_ms\n"
        lines = [
            f"c{1 + (i % 17):02d},{i // 17},{10 * (1 + (i % 5))},{12.5 + 37.25 * (i % 23) + 0.125 * i:.3f}"
            for i in range(rows)
        ]
    elif key == "Dint1":
        header = "cell,contrast_pct,bin_ms,spike_count\n"
        lines = [f"c{1 + (i % 17):02d},{10 * (1 + (i % 5))},{2 * (i // 85)},{(i * 7) % 3}" for i in range(rows)]
    else:
        header = "cell,contrast_pct,tau_fast_ms,tau_slow_ms,a_fast,a_slow\n"
        lines = [
            f"c{1 + (i % 17):02d},{10 * (1 + (i // 17))},{4.1 + 0.01 * (i % 7):.2f},"
            f"{91.2 * (10 * (1 + (i // 17))) ** -0.36 + 0.3 * ((i * 3) % 5 - 2):.2f},"
            f"{-1.8 + 0.02 * (i % 4):.2f},{-0.9 + 0.01 * (i % 6):.2f}"
            for i in range(rows)
        ]
    return header + "\n".join(lines) + "\n"


def _script(key: str, rel: str) -> str:
    name = Path(rel).stem
    return (
        f'"""{name}: part of the synthetic parasol kernel-shortening project (fixture {key}).\n\n'
        "This file exists so the Script node has a real path and hash. It is not run.\n"
        '"""\n\n'
        "import sys\n\n\n"
        "def main(argv: list[str]) -> int:\n"
        f'    print("{name}: fixture script, nothing to do", argv)\n'
        "    return 0\n\n\n"
        'if __name__ == "__main__":\n'
        "    raise SystemExit(main(sys.argv[1:]))\n"
    )


def _document(key: str, title: str, status: str) -> str:
    cites = CITES.get(key, [])
    body = [f"# {title}", "", f"Status: {status}. Fixture document {key} for the disclosure experiment.", ""]
    if cites:
        body += ["## References", ""] + [f"- {k}: " + next(p[1] for p in PAPERS if p[0] == k) for k in cites] + [""]
    else:
        body += ["## Protocol", "", "2 ms bins, two-exponential history kernel, 300 ms window, L2 penalty 1e-3.", ""]
    return "\n".join(body)


def write_files() -> dict[str, str]:
    """Write the project files under fixture/files and return {relpath: kind}."""
    written: dict[str, str] = {}

    def put(rel: str, content: str | bytes, kind: str) -> None:
        path = FILES / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content)
        written[rel] = kind

    for i, (key, (rel, _desc)) in enumerate(sorted(FIGURES.items())):
        put(rel, _png(64, 32, _figure_pixels(i)), "figure")
    for key, rel in SCRIPTS.items():
        put(rel, _script(key, rel), "script")
    for key, (rel, _desc) in DATASETS.items():
        put(rel, _csv(key, 340 if key.startswith("Draw") else 170), "dataset")
    for key, (title, rel, status) in DOCUMENTS.items():
        put(rel, _document(key, title, status), "document")
    return written


# ---------------------------------------------------------------------------
# graph.json
# ---------------------------------------------------------------------------


def build_nodes() -> list[dict]:
    nodes: list[dict] = []
    for key, (tool, args) in QUESTION.items():
        nodes.append({"key": key, "tool": tool, "args": args})
    for key, (tool, args) in HYPOTHESES.items():
        nodes.append({"key": key, "tool": tool, "args": args})
    for key, title, authors, year in PAPERS:
        nodes.append({
            "key": key,
            "tool": "add_paper",
            "args": {"title": title, "authors": authors, "year": year,
                     "doi": f"10.99999/disclosure-fixture.{key.lower()}"},
        })
    for key, (title, rel, status) in DOCUMENTS.items():
        nodes.append({"key": key, "tool": "add_document",
                      "args": {"title": title, "path": rel, "status": status}})
    for key, (rel, desc) in DATASETS.items():
        nodes.append({"key": key, "tool": "add_dataset",
                      "args": {"path": rel, "type": "csv", "description": desc,
                               "tier": "reference" if key.startswith("Draw") else "generated"}})
    for key, rel in SCRIPTS.items():
        nodes.append({"key": key, "tool": "add_script", "args": {"path": rel, "language": "python"}})
    for key, desc in EXECUTIONS.items():
        nodes.append({"key": key, "tool": "add_execution",
                      "args": {"kind": "script_run", "description": desc, "status": "completed"}})
    for key, f in FINDINGS.items():
        # Title is deliberately NOT passed here: the title pass in run.py sets
        # it through update_node so every finding gets an ``updated`` stamp.
        nodes.append({"key": key, "tool": "add_finding",
                      "args": {"description": f["description"], "confidence": f["confidence"]},
                      "title": f["title"]})
    for key, (rel, desc) in FIGURES.items():
        nodes.append({"key": key, "tool": "ensure_artifact",
                      # No artifact_type override: a .png auto-detects to a Finding
                      # with artifact_type "figure", which is how figures are told apart.
                      "args": {"path": rel, "title": Path(rel).stem, "description": desc}})
    return nodes


def build_edges() -> list[list[str]]:
    edges: list[list[str]] = []
    for src, x in GENERATED_BY.items():
        edges.append([src, "WAS_GENERATED_BY", x])
    for x, inputs in USED.items():
        for inp in inputs:
            edges.append([x, "USED", inp])
    for f, fig in APPEARS_IN.items():
        edges.append([f, "APPEARS_IN", fig])
    for f, h in SUPPORTS:
        edges.append([f, "SUPPORTS", h])
    for f, h in CONTRADICTS:
        edges.append([f, "CONTRADICTS", h])
    for f in RELEVANT_FINDINGS:
        edges.append([f, "RELEVANT_TO", "Q1"])
    for h in HYPOTHESES:
        edges.append([h, "RELEVANT_TO", "Q1"])
    for p in RELEVANT_PAPERS:
        edges.append([p, "RELEVANT_TO", "Q1"])
    for w, papers in CITES.items():
        for p in papers:
            edges.append([w, "CITES", p])
    for a, b in DERIVED_FROM:
        edges.append([a, "WAS_DERIVED_FROM", b])
    for a, b in INFORMED_BY:
        edges.append([a, "WAS_INFORMED_BY", b])
    return edges


# ---------------------------------------------------------------------------
# tasks.json
# ---------------------------------------------------------------------------

TASK5_PHRASE = "first-spike latency to a contrast step in ON parasol cells"
TASK5_NUMBER = "47.3"
TASK6_PHRASE = "cesium-blocked control epochs"

ANSWER_LINE = "Reply with exactly one line: ANSWER <json>"


def build_tasks() -> list[dict]:
    fig02_chain = ["fig02", "X3", "Dint2", "X2", "Dint1", "X1", "Draw1"]
    return [
        {
            "id": 1, "kind": "lookup", "may_need_body": False,
            "prompt": (
                "Which script generated the figure stored at figures/fig03_off_parasol_kernels.png? "
                "Give the Script node's id."
            ),
            "shape": "a JSON string holding one Script node id, for example \"S-0123abcd\"",
            "gold": {"type": "id", "value": "S2"},
        },
        {
            "id": 2, "kind": "one-hop", "may_need_body": False,
            "prompt": (
                "List every Finding that SUPPORTS the hypothesis stating that ON parasol "
                "spike-history kernels shorten by more than 30 percent between 10 percent and "
                "50 percent contrast."
            ),
            "shape": "a sorted JSON list of Finding node ids",
            "gold": {"type": "id_set", "value": ["F01", "F02", "F03", "F05"]},
        },
        {
            "id": 3, "kind": "two-hop", "may_need_body": False,
            "prompt": (
                "Which datasets did the execution that produced "
                "figures/fig05_ahp_amplitude_vs_tau.png use?"
            ),
            "shape": "a sorted JSON list of Dataset node ids",
            "gold": {"type": "id_set", "value": ["Dint2", "Draw3"]},
        },
        {
            "id": 4, "kind": "deep-trace", "may_need_body": False,
            "prompt": (
                "Trace figures/fig02_on_kernels_overlay.png back to its raw dataset through "
                "every execution and intermediate dataset, and name the scripts those "
                "executions used."
            ),
            "shape": (
                "a JSON object {\"chain\": [...], \"scripts\": [...]} where chain is the ordered "
                "list of node ids from the figure to the raw dataset, alternating the node and "
                "the execution that generated it (figure, execution, dataset, execution, ..., "
                "raw dataset), and scripts is the sorted list of Script ids USED by those executions"
            ),
            "gold": {"type": "chain_and_set", "chain": fig02_chain, "set": ["S1", "S3", "S4"]},
        },
        {
            "id": 5, "kind": "content-read", "may_need_body": True,
            "prompt": (
                f"Find the finding about {TASK5_PHRASE}. What confidence does it carry, and what "
                "numeric histogram peak latency in milliseconds does it state at 10 percent contrast?"
            ),
            "shape": "a JSON object {\"confidence\": <number>, \"peak_latency_ms\": <number>}",
            "gold": {"type": "object", "value": {"confidence": FINDINGS["F11"]["confidence"],
                                                 "peak_latency_ms": float(TASK5_NUMBER)},
                     "finding": "F11"},
        },
        {
            "id": 6, "kind": "content-read", "may_need_body": True,
            "prompt": f"Which finding mentions {TASK6_PHRASE}? Give its node id.",
            "shape": "a JSON string holding one Finding node id",
            "gold": {"type": "id", "value": "F10"},
        },
        {
            "id": 7, "kind": "contradiction", "may_need_body": False,
            "prompt": (
                "Which findings CONTRADICT a hypothesis, and which hypothesis does each one "
                "contradict?"
            ),
            "shape": "a sorted JSON list of two-element lists [finding_id, hypothesis_id]",
            "gold": {"type": "pair_set", "value": [list(p) for p in CONTRADICTS]},
        },
        {
            "id": 8, "kind": "staleness", "may_need_body": False,
            "prompt": (
                "Which figure nodes are downstream of the script scripts/fit_srm.py, that is, "
                "would go stale if that script changed? A figure counts as downstream when a "
                "chain of WAS_GENERATED_BY and USED edges leads from the figure back to the "
                "script, through any number of executions and intermediate datasets."
            ),
            "shape": "a sorted JSON list of figure node ids",
            "gold": {"type": "id_set", "value": ["fig01", "fig02", "fig05"]},
        },
        {
            "id": 9, "kind": "counting", "may_need_body": False,
            "prompt": (
                "How many Finding nodes are RELEVANT_TO the open question about contrast-"
                "dependent shortening of the spike-history kernel, and which three of those "
                "findings were updated most recently (most recent first)?"
            ),
            "shape": "a JSON object {\"count\": <integer>, \"top3\": [id, id, id]}",
            "gold": {"type": "count_and_chain", "count": len(RELEVANT_FINDINGS),
                     "chain": [k for k in reversed(UPDATE_ORDER) if k in RELEVANT_FINDINGS][:3]},
        },
        {
            "id": 10, "kind": "literature", "may_need_body": False,
            "prompt": (
                f"Which papers are cited by the document titled \"{DOCUMENTS['W1'][0]}\"?"
            ),
            "shape": "a sorted JSON list of Paper node ids",
            "gold": {"type": "id_set", "value": list(CITES["W1"])},
        },
    ]


# ---------------------------------------------------------------------------
# Self-checks: the fixture must satisfy the contract before it is written
# ---------------------------------------------------------------------------


def check(nodes: list[dict], edges: list[list[str]], tasks: list[dict]) -> list[str]:
    problems: list[str] = []
    keys = {n["key"] for n in nodes}
    if len(keys) != len(nodes):
        problems.append("duplicate node keys")
    for src, rel, dst in edges:
        if src not in keys or dst not in keys:
            problems.append(f"edge endpoint unknown: {src} {rel} {dst}")
    seen = set()
    for e in edges:
        t = tuple(e)
        if t in seen:
            problems.append(f"duplicate edge {e}")
        seen.add(t)

    for key, f in FINDINGS.items():
        n = len(f["description"])
        if not 300 <= n <= 1500:
            problems.append(f"{key}: description is {n} chars, want 300 to 1500")
        if len(f["title"]) > 100:
            problems.append(f"{key}: title is {len(f['title'])} chars, want <= 100")

    all_text = " ".join(
        json.dumps(n["args"]) + json.dumps(n.get("title", "")) for n in nodes
    )
    f11 = FINDINGS["F11"]["description"]
    pos5 = f11.find(TASK5_NUMBER)
    if pos5 < 240:
        problems.append(f"task 5 number {TASK5_NUMBER} at char {pos5} of F11, want >= 240")
    if all_text.count(TASK5_NUMBER) != 1:
        problems.append(f"task 5 number {TASK5_NUMBER} appears {all_text.count(TASK5_NUMBER)} times in the fixture, want 1")
    if TASK5_PHRASE.lower() not in f11[:240].lower():
        problems.append("task 5 phrase must sit inside the first 240 chars of F11")
    f10 = FINDINGS["F10"]["description"]
    pos6 = f10.find(TASK6_PHRASE)
    if pos6 < 400:
        problems.append(f"task 6 phrase at char {pos6} of F10, want >= 400")
    if all_text.lower().count(TASK6_PHRASE.lower()) != 1:
        problems.append("task 6 phrase must appear exactly once in the fixture")
    if TASK6_PHRASE.lower() in FINDINGS["F10"]["title"].lower():
        problems.append("task 6 phrase must not be in the F10 title")

    # Provenance shape the tasks rely on.
    gen = {s: d for s, r, d in edges if r == "WAS_GENERATED_BY"}
    used: dict[str, set[str]] = {}
    for s, r, d in edges:
        if r == "USED":
            used.setdefault(s, set()).add(d)
    for fig in FIGURES:
        if fig not in gen:
            problems.append(f"{fig} has no WAS_GENERATED_BY")
    for f in FINDINGS:
        if f not in gen:
            problems.append(f"{f} has no WAS_GENERATED_BY")
        if f not in APPEARS_IN:
            problems.append(f"{f} has no APPEARS_IN")
    for x in EXECUTIONS:
        if not any(v.startswith("S") for v in used.get(x, ())):
            problems.append(f"{x} USED no script")
    chain = next(t for t in tasks if t["id"] == 4)["gold"]["chain"]
    for i in range(len(chain) - 1):
        a, b = chain[i], chain[i + 1]
        ok = gen.get(a) == b if i % 2 == 0 else b in used.get(a, set())
        if not ok:
            problems.append(f"task 4 chain broken between {a} and {b}")
    titles = [n["args"]["title"] for n in nodes if n["tool"] == "add_document"]
    if len(set(titles)) != len(titles):
        problems.append("document titles must be unique")
    return problems


def main() -> None:
    nodes = build_nodes()
    edges = build_edges()
    tasks = build_tasks()
    problems = check(nodes, edges, tasks)
    if problems:
        for p in problems:
            print("FIXTURE PROBLEM:", p, file=sys.stderr)
        sys.exit(1)

    FIXTURE.mkdir(parents=True, exist_ok=True)
    files = write_files()
    graph = {
        "seed": SEED,
        "description": (
            "Synthetic retinal-electrophysiology research graph for the progressive-disclosure "
            "experiment. Node paths are relative to the scratch project root; run.py copies "
            "fixture/files there and resolves them."
        ),
        "nodes": nodes,
        "edges": edges,
        "update_order": UPDATE_ORDER,
        "files": files,
        "counts": {
            "nodes": len(nodes),
            "edges": len(edges),
            "by_tool": {t: sum(1 for n in nodes if n["tool"] == t) for t in sorted({n["tool"] for n in nodes})},
            "by_rel": {r: sum(1 for e in edges if e[1] == r) for r in sorted({e[1] for e in edges})},
        },
    }
    (FIXTURE / "graph.json").write_text(json.dumps(graph, indent=2, ensure_ascii=False) + "\n")
    (FIXTURE / "tasks.json").write_text(
        json.dumps({"answer_line": ANSWER_LINE, "tasks": tasks}, indent=2, ensure_ascii=False) + "\n"
    )
    print(f"wrote {FIXTURE}: {graph['counts']['nodes']} nodes, {graph['counts']['edges']} edges, "
          f"{len(tasks)} tasks, {len(files)} files")
    print(json.dumps(graph["counts"], indent=2))


if __name__ == "__main__":
    main()
