#!/usr/bin/env python
"""Build the deterministic fixture for the /wh:close mechanical-sweep experiment.

Writes, under ``fixture/``:

  files/            the scratch project skeleton copied into every run
                    (scripts, data, docs, .plans, plus the draft template)
  graph.json        every node, artifact and edge to seed, by symbolic key,
                    with timestamps expressed as HOURS BEFORE the run's start
                    (absolute instants are resolved by run.py at seed time, so
                    this file stays byte-identical across regenerations)
  gold.json         what each measured phase of the sweep must return, by
                    symbolic key; run.py resolves the keys to real node ids
                    after seeding
  context/          synthetic prior-session filler, split into files of a known
                    estimated token size, for the ``small`` and ``large`` arms
  context/manifest.json   per-file and per-target token estimates

Regenerating is idempotent and byte-for-byte reproducible::

    PYTHONPATH=$PWD .venv/bin/python evals/close_cost/make_fixture.py
"""

from __future__ import annotations

import argparse
import json
import random
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "fixture"
FILES = FIXTURE / "files"
CONTEXT = FIXTURE / "context"

SEED = 20260915

# Hours before the run's start instant.
SINCE_HOURS_AGO = 48.0        # the boundary close Execution's started_at
BEFORE_HOURS_AGO = 120.0      # nodes that must fall OUTSIDE the window
MALFORMED_HOURS_AGO = 200.0   # the close with no started_at at all

# Context targets, in estimated tokens of filler the model must read.
CONTEXT_TARGETS = {"small": 30_000, "large": 400_000}
CONTEXT_FILES = {"small": 2, "large": 20}

# A citation that resolves to nothing. Shaped like a real id so the extractor
# picks it up, and long enough that it cannot collide with a generated one.
FAKE_CITATION = "F-deadbeef"


# ---------------------------------------------------------------------------
# Project skeleton
# ---------------------------------------------------------------------------

SCRIPTS: dict[str, str] = {
    "scripts/load_epochs.py": '''"""Load one cell's epochs from the raw export."""

import csv
from pathlib import Path

RAW = Path("data/epochs_cell01.csv")


def load(path: Path = RAW) -> list[dict]:
    with path.open() as fh:
        return [dict(row) for row in csv.DictReader(fh)]


if __name__ == "__main__":
    rows = load()
    print(f"loaded {len(rows)} epochs")
''',
    "scripts/fit_kernel.py": '''"""Fit the one-lag history kernel per cell."""

import csv
from pathlib import Path

OUT = Path("data/kernel_params.csv")


def fit(rows: list[dict]) -> dict:
    n = max(len(rows), 1)
    mean = sum(float(r["count"]) for r in rows) / n
    return {"mean_count": mean, "n": n}


def write(params: dict, path: Path = OUT) -> None:
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=sorted(params))
        w.writeheader()
        w.writerow(params)
''',
    "scripts/bootstrap.py": '''"""Bootstrap confidence intervals for the kernel coefficient."""

import random

N_RESAMPLES = 2000


def resample(values: list[float], rng: random.Random) -> list[float]:
    return [rng.choice(values) for _ in values]


def ci(values: list[float], seed: int = 0) -> tuple[float, float]:
    rng = random.Random(seed)
    means = []
    for _ in range(N_RESAMPLES):
        draw = resample(values, rng)
        means.append(sum(draw) / len(draw))
    means.sort()
    lo = means[int(0.025 * len(means))]
    hi = means[int(0.975 * len(means))]
    return lo, hi
''',
    "scripts/make_figs.py": '''"""Render the figure set for the kernel analysis."""

from pathlib import Path

FIGDIR = Path("figures")


def ensure_figdir() -> Path:
    FIGDIR.mkdir(exist_ok=True)
    return FIGDIR


def figure_names() -> list[str]:
    return ["fig01_counts.png", "fig02_kernel.png", "fig03_ci.png"]
''',
}

DATASETS: dict[str, str] = {
    "data/epochs_cell01.csv": (
        "epoch,count,duration_s,holding_mv\n"
        + "".join(
            f"{i},{(i * 7) % 23},{0.5 + (i % 5) * 0.1:.1f},-60\n" for i in range(1, 41)
        )
    ),
    "data/kernel_params.csv": (
        "cell,coefficient,stderr,n_epochs\n"
        + "".join(
            f"cell{i:02d},{0.10 + i * 0.013:.3f},{0.02 + i * 0.001:.3f},{40 + i}\n"
            for i in range(1, 13)
        )
    ),
    "data/bootstrap_ci.csv": (
        "cell,lo,hi,width\n"
        + "".join(
            f"cell{i:02d},{0.05 + i * 0.01:.3f},{0.18 + i * 0.011:.3f},"
            f"{0.13 + i * 0.001:.3f}\n"
            for i in range(1, 13)
        )
    ),
    "data/legacy_raw.csv": (
        "epoch,raw_pa\n" + "".join(f"{i},{(i * 13) % 97}\n" for i in range(1, 25))
    ),
}

METHODS_MD = """# Methods

Recordings were made in whole-cell voltage clamp at a holding potential of
-60 mV. Epochs were segmented by the stimulus marker channel and counted with
`scripts/load_epochs.py`.

The one-lag history kernel is fit per cell by least squares on the epoch count
series. Confidence intervals come from a 2000-resample bootstrap over epochs,
stratified by cell. No pooling across cells is performed at the fit stage: the
coefficient is estimated per cell and only summarized afterwards.

Figures are rendered by `scripts/make_figs.py` into `figures/`.
"""

PLAN_KERNEL_MD = """---
title: Fit the one-lag history kernel per cell
status: in-progress
---

# Fit the one-lag history kernel per cell

## Question
Does the one-lag history coefficient vary systematically across cells, or is
the apparent spread consistent with estimation noise?

## Steps
1. Load epochs per cell.
2. Fit the coefficient per cell.
3. Bootstrap a CI per cell.
4. Compare the between-cell spread with the within-cell CI width.
"""

PLAN_BOOTSTRAP_MD = """---
title: Bootstrap the kernel coefficient CIs
status: draft
---

# Bootstrap the kernel coefficient CIs

## Question
How wide is the per-cell confidence interval on the history coefficient at
2000 resamples, and does widening the resample count change the answer?

## Steps
1. Resample epochs within cell.
2. Recompute the coefficient on each resample.
3. Take the 2.5 and 97.5 percentiles.
"""

# Rendered at seed time with real node ids substituted for {CITE1}, {CITE2},
# {CITE3}. {FAKE} is a citation that resolves to nothing.
DRAFT_TEMPLATE = """---
title: Draft session notes
section: draft
---

# Draft session notes

The per-cell coefficient spread is larger than the within-cell interval width
[{CITE1}], and the effect survives dropping the two shortest recordings
[{CITE2}]. A separate pass suggested the spread tracks recording duration
[{CITE3}], which has not been wired to an execution yet.

An earlier pass reported the opposite sign [{FAKE}]; that record no longer
exists and the claim should not be carried forward.
"""


def write_project_files() -> None:
    if FILES.exists():
        shutil.rmtree(FILES)
    for rel, body in {**SCRIPTS, **DATASETS}.items():
        path = FILES / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body)
    (FILES / "docs").mkdir(parents=True, exist_ok=True)
    (FILES / "docs" / "METHODS.md").write_text(METHODS_MD)
    (FILES / "docs" / "DRAFT-SESSION.md.template").write_text(DRAFT_TEMPLATE)
    (FILES / ".plans").mkdir(parents=True, exist_ok=True)
    (FILES / ".plans" / "PLAN-kernel.md").write_text(PLAN_KERNEL_MD)
    (FILES / ".plans" / "PLAN-bootstrap.md").write_text(PLAN_BOOTSTRAP_MD)


# ---------------------------------------------------------------------------
# Graph manifest
# ---------------------------------------------------------------------------

FINDING_TEXT = [
    "Per-cell history coefficients span 0.11 to 0.26, wider than any single cell's bootstrap interval.",
    "Dropping the two shortest recordings leaves the spread unchanged at 0.12 to 0.25.",
    "Bootstrap CI width is flat in resample count above 1000 resamples.",
    "Coefficient estimates are insensitive to the epoch segmentation threshold between 0.4 and 0.7.",
    "Holding potential does not predict the coefficient across the twelve cells.",
    "Epoch count per cell ranges from 41 to 52 and does not correlate with the coefficient.",
    "Two cells show a bimodal resample distribution; both are the shortest recordings.",
    "Pooling across cells before fitting shrinks the estimate by 38 percent, an artifact of unequal epoch counts.",
    "The residual autocorrelation at lag 2 is indistinguishable from zero in every cell.",
    "Refitting on the second half of each recording reproduces the per-cell ordering.",
    "The coefficient's standard error scales as the inverse square root of epoch count, as expected.",
    "Recording duration and coefficient are correlated at r = 0.31, which is not significant at n = 12.",
]

QUESTION_TEXT = [
    "Is the between-cell coefficient spread biological, or driven by unequal epoch counts?",
    "Does the history kernel need a second lag term for the two bimodal cells?",
    "Should the bootstrap resample epochs or whole trials?",
    "What is the minimum epoch count for a usable per-cell fit?",
]

HYPOTHESIS_TEXT = [
    "The history coefficient is cell-specific and stable within a recording.",
    "The bimodal resample distribution reflects a second, slower adaptation process.",
    "Unequal epoch counts alone explain the apparent between-cell spread.",
]

NOTE_TEXT = [
    "Decided to fit per cell and summarize afterwards rather than pooling, because pooling shrinks the estimate by an amount that depends on epoch count.",
    "Parked the second-lag model until the two short recordings are re-segmented; fitting it now would confound model choice with data quality.",
    "The bootstrap seed is fixed at 0 in scripts/bootstrap.py so the CIs are reproducible run to run.",
]

OLD_FINDING_TEXT = [
    "An earlier segmentation threshold of 0.3 admitted stimulus artifacts into the epoch count.",
    "The first export was missing the holding potential column, which has since been added.",
]


def build_graph() -> dict:
    """Every node, artifact and edge, keyed symbolically. Timestamps are offsets."""
    nodes: list[dict] = []
    artifacts: list[dict] = []

    def node(key: str, ntype: str, hours_ago: float, **fields) -> None:
        nodes.append({"key": key, "type": ntype, "hours_ago": hours_ago, "fields": fields})

    def artifact(key: str, path: str, hours_ago: float, **fields) -> None:
        artifacts.append({"key": key, "path": path, "hours_ago": hours_ago, "fields": fields})

    # --- Close Executions: the window boundary and one malformed record ------
    node(
        "XCLOSE_BOUNDARY", "execution", SINCE_HOURS_AGO,
        kind="close",
        description="Session synthesis: previous close, valid boundary",
    )
    node(
        "XCLOSE_BAD", "execution", MALFORMED_HOURS_AGO,
        kind="close",
        description="Session synthesis: close with no started_at",
    )

    # --- Work Executions inside the window -----------------------------------
    for i, (key, hours, kind, desc) in enumerate([
        ("X1", 36.0, "script", "Ran load_epochs and the first per-cell fit"),
        ("X2", 24.0, "script", "Bootstrap pass over the twelve cells"),
        ("X3", 6.0, "discuss", "Reviewed the spread against the CI widths"),
    ]):
        node(key, "execution", hours, kind=kind, description=desc)
        del i

    # --- In-window entities ---------------------------------------------------
    for i, text in enumerate(FINDING_TEXT, start=1):
        node(
            f"F{i:02d}", "finding", 40.0 - i * 1.5,
            description=text,
            confidence=round(0.55 + 0.03 * (i % 8), 2),
        )
    for i, text in enumerate(QUESTION_TEXT, start=1):
        node(f"Q{i}", "question", 30.0 - i * 2.0, question=text, priority=9 - i)
    for i, text in enumerate(HYPOTHESIS_TEXT, start=1):
        node(f"H{i}", "hypothesis", 28.0 - i * 2.0, statement=text, status="open")
    for i, text in enumerate(NOTE_TEXT, start=1):
        node(f"N{i}", "note", 20.0 - i * 2.0, content=text, context="kernel fit")

    artifact("S1", "scripts/load_epochs.py", 39.0, artifact_type="script", language="python",
             description="Load one cell's epochs from the raw export")
    artifact("S2", "scripts/fit_kernel.py", 33.0, artifact_type="script", language="python",
             description="Fit the one-lag history kernel per cell")
    artifact("S3", "scripts/bootstrap.py", 22.0, artifact_type="script", language="python",
             description="Bootstrap confidence intervals for the kernel coefficient")
    artifact("S4", "scripts/make_figs.py", 9.0, artifact_type="script", language="python",
             description="Render the figure set for the kernel analysis")

    artifact("D1", "data/epochs_cell01.csv", 38.0, artifact_type="dataset", type="raw",
             description="Segmented epochs for cell 01")
    artifact("D2", "data/kernel_params.csv", 32.0, artifact_type="dataset", type="derived",
             description="Per-cell history coefficient and stderr")
    artifact("D3", "data/bootstrap_ci.csv", 21.0, artifact_type="dataset", type="derived",
             description="Per-cell bootstrap confidence intervals")

    artifact("W1", "docs/METHODS.md", 26.0, artifact_type="document",
             title="Methods: epoch segmentation and kernel fit", section="methods", status="draft")

    artifact("PL1", ".plans/PLAN-kernel.md", 35.0, artifact_type="plan",
             title="Fit the one-lag history kernel per cell", status="in-progress")
    artifact("PL2", ".plans/PLAN-bootstrap.md", 12.0, artifact_type="plan",
             title="Bootstrap the kernel coefficient CIs", status="draft")

    # --- Entities BEFORE the window: must never appear in 1.2, 1.3 or 2.1 -----
    for i, text in enumerate(OLD_FINDING_TEXT, start=1):
        node(f"OLD_F{i}", "finding", BEFORE_HOURS_AGO + i, description=text, confidence=0.5)
    node("OLD_H1", "hypothesis", BEFORE_HOURS_AGO + 3,
         statement="The segmentation threshold sets the apparent epoch count.", status="rejected")
    node("OLD_N1", "note", BEFORE_HOURS_AGO + 4,
         content="Re-exported the raw file with the holding potential column included.",
         context="data export")
    artifact("OLD_D1", "data/legacy_raw.csv", BEFORE_HOURS_AGO + 5,
             artifact_type="dataset", type="raw", description="First raw export, superseded")

    # --- Provenance: WAS_GENERATED_BY for roughly half the in-window entities -
    generated: dict[str, list[str]] = {
        "X1": ["F01", "F02", "F03", "D1", "S1"],
        "X2": ["F04", "F05", "F06", "H1", "W1"],
        "X3": ["F07", "F08", "Q1", "N1", "PL1", "D2", "S2"],
    }
    edges: list[list[str]] = []
    for exec_key, produced in generated.items():
        for key in produced:
            edges.append([key, "WAS_GENERATED_BY", exec_key])

    # USED edges and a few semantic edges: realistic noise that changes no gold
    # set, since 1.2 and 1.3 only care about WAS_GENERATED_BY.
    edges += [
        ["X1", "USED", "OLD_D1"],
        ["X2", "USED", "D1"],
        ["X2", "USED", "S2"],
        ["X3", "USED", "D3"],
        ["X3", "USED", "OLD_F1"],
        ["F01", "SUPPORTS", "H1"],
        ["F08", "CONTRADICTS", "H3"],
        ["F02", "RELEVANT_TO", "Q1"],
        ["F09", "RELEVANT_TO", "Q2"],
        ["S3", "DEPENDS_ON", "D1"],
    ]

    draft = {
        "key": "W2",
        "template": "docs/DRAFT-SESSION.md.template",
        "out": "docs/DRAFT-SESSION.md",
        "hours_ago": 3.0,
        "cites": ["F01", "F02", "F09"],
        "fake": FAKE_CITATION,
        "fields": {
            "artifact_type": "document",
            "title": "Draft session notes",
            "section": "draft",
            "status": "draft",
        },
    }

    return {
        "seed": SEED,
        "since_hours_ago": SINCE_HOURS_AGO,
        "malformed_close_key": "XCLOSE_BAD",
        "boundary_close_key": "XCLOSE_BOUNDARY",
        "stale": {"key": "S3", "path": "scripts/bootstrap.py",
                  "append": "\n# touched after registration, so detect_stale reports it\n"},
        "nodes": nodes,
        "artifacts": artifacts,
        "edges": edges,
        "draft": draft,
    }


def build_gold(graph: dict) -> dict:
    """What each measured phase must return, by symbolic key."""
    in_window_entities = (
        [f"F{i:02d}" for i in range(1, 13)]
        + [f"Q{i}" for i in range(1, 5)]
        + [f"H{i}" for i in range(1, 4)]
        + [f"N{i}" for i in range(1, 4)]
        + [f"S{i}" for i in range(1, 5)]
        + [f"D{i}" for i in range(1, 4)]
        + ["W1", "W2", "PL1", "PL2"]
    )
    has_provenance = {
        e[0] for e in graph["edges"] if e[1] == "WAS_GENERATED_BY"
    }
    orphans = [k for k in in_window_entities if k not in has_provenance]
    return {
        # Phase 1.1
        "since_key": graph["boundary_close_key"],
        "malformed_closes": 1,
        # Phase 1.2: every non-Execution, non-Paper node stamped at or after
        # $since. The five OLD_* nodes are deliberately outside it.
        "window_ids": sorted(in_window_entities),
        # Phase 1.3: the subset of those with no WAS_GENERATED_BY edge.
        "orphan_ids": sorted(orphans),
        # Phase 2.1: row counts of the act's six per-type queries, run verbatim
        # (scoped to the project tag). Execution is 4, not 3: the boundary close
        # itself satisfies started_at >= $since.
        "inventory": {
            "Finding": 12,
            "Hypothesis": 3,
            "OpenQuestion": 4,
            "Plan": 2,
            "Execution": 4,
            "Document": 2,
        },
        # Phase 1.6
        "stale": [graph["stale"]["key"]],
        # Phase 2.4: three real ids (two with provenance, one orphan Finding)
        # plus one that resolves to nothing.
        "citations": {"total": 4, "valid": 2},
        # Phase 2.6: true when the layers this project owns agree. graph_only is
        # excluded on purpose: check_consistency reads the whole database, which
        # is shared, so graph_only counts every other project's node.
        "consistency_ok": True,
    }


# ---------------------------------------------------------------------------
# Context filler
# ---------------------------------------------------------------------------

CELLS = [f"cell{i:02d}" for i in range(1, 25)]
STEPS = [
    "segmenting epochs", "fitting the one-lag kernel", "bootstrapping the CI",
    "checking residual autocorrelation", "re-exporting the raw traces",
    "comparing per-cell orderings", "auditing the holding potential column",
    "re-running with a tighter segmentation threshold",
]
OBSERVATIONS = [
    "the estimate moved less than one standard error",
    "the ordering of cells was preserved",
    "two cells fell out of the usable range",
    "the residual at lag 2 stayed indistinguishable from zero",
    "the CI narrowed by roughly a tenth",
    "the coefficient tracked epoch count more closely than duration",
    "nothing in the figure changed at print size",
    "the pooled estimate shrank, as it always does with unequal counts",
]
ASIDES = [
    "Worth noting for the writeup, though not a result on its own.",
    "Parking this until the re-segmentation lands.",
    "This is the part that will need a real statistical argument.",
    "Noted and moved on; it does not change the decision.",
    "Flagging it so it does not get rediscovered next week.",
]


def _paragraph(rng: random.Random) -> str:
    sentences = []
    for _ in range(rng.randint(3, 6)):
        cell = rng.choice(CELLS)
        step = rng.choice(STEPS)
        obs = rng.choice(OBSERVATIONS)
        sentences.append(
            f"While {step} for {cell}, {obs} (coefficient "
            f"{rng.uniform(0.08, 0.31):.3f}, stderr {rng.uniform(0.01, 0.05):.3f}, "
            f"n = {rng.randint(38, 58)})."
        )
    if rng.random() < 0.4:
        sentences.append(rng.choice(ASIDES))
    return " ".join(sentences)


def _tool_block(rng: random.Random) -> str:
    head = "cell      coef    stderr   lo      hi      n_epochs  resamples"
    rows = []
    for _ in range(rng.randint(6, 14)):
        cell = rng.choice(CELLS)
        coef = rng.uniform(0.08, 0.31)
        se = rng.uniform(0.01, 0.05)
        rows.append(
            f"{cell:<9} {coef:.3f}  {se:.3f}   {coef - 1.96 * se:.3f}  "
            f"{coef + 1.96 * se:.3f}  {rng.randint(38, 58):<9} {rng.choice([500, 1000, 2000, 4000])}"
        )
    return "```\n" + head + "\n" + "\n".join(rows) + "\n```"


def _code_block(rng: random.Random) -> str:
    return (
        "```python\n"
        f"coefs = fit_per_cell(rows, threshold={rng.uniform(0.3, 0.8):.2f})\n"
        f"lo, hi = ci(coefs, seed={rng.randint(0, 99)})\n"
        f"print(f\"{{len(coefs)}} cells, width {{hi - lo:.4f}}\")\n"
        "```"
    )


def _section(rng: random.Random, index: int) -> str:
    parts = [f"### Step {index}: {rng.choice(STEPS)}", ""]
    for _ in range(rng.randint(2, 4)):
        roll = rng.random()
        if roll < 0.62:
            parts.append(_paragraph(rng))
        elif roll < 0.86:
            parts.append(_tool_block(rng))
        else:
            parts.append(_code_block(rng))
        parts.append("")
    return "\n".join(parts)


def build_context_file(rng: random.Random, target_tokens: int, title: str) -> tuple[str, int]:
    from wheeler.knowledge.versions import estimate_tokens

    parts = [f"# {title}", "",
             "Transcript of an earlier working session on the history-kernel analysis.",
             ""]
    text = "\n".join(parts)
    tokens = estimate_tokens(text)
    index = 1
    while tokens < target_tokens:
        block = _section(rng, index)
        parts.append(block)
        text = "\n".join(parts)
        tokens = estimate_tokens(text)
        index += 1
    return text + "\n", tokens


def write_context() -> dict:
    from wheeler.knowledge.versions import estimate_tokens

    if CONTEXT.exists():
        shutil.rmtree(CONTEXT)
    manifest: dict = {"targets": {}}
    for name, total_target in CONTEXT_TARGETS.items():
        n_files = CONTEXT_FILES[name]
        per_file = total_target // n_files
        out_dir = CONTEXT / name
        out_dir.mkdir(parents=True, exist_ok=True)
        rng = random.Random(SEED + sum(ord(c) for c in name))
        files = []
        total = 0
        for k in range(1, n_files + 1):
            title = f"Prior session {k} of {n_files}"
            body, _ = build_context_file(rng, per_file, title)
            rel = f"{name}/session_{k:02d}.md"
            (CONTEXT / rel).write_text(body)
            tokens = estimate_tokens(body)
            total += tokens
            files.append({
                "path": rel, "estimated_tokens": tokens,
                "bytes": len(body.encode()), "lines": body.count("\n") + 1,
            })
        manifest["targets"][name] = {
            "target_tokens": total_target,
            "estimated_tokens": total,
            "n_files": n_files,
            "files": files,
        }
    (CONTEXT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


# ---------------------------------------------------------------------------


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=FIXTURE)
    ns = ap.parse_args()
    if ns.out != FIXTURE:  # pragma: no cover - escape hatch for a side-by-side diff
        globals()["FIXTURE"] = ns.out

    FIXTURE.mkdir(parents=True, exist_ok=True)
    write_project_files()
    graph = build_graph()
    gold = build_gold(graph)
    (FIXTURE / "graph.json").write_text(json.dumps(graph, indent=2, sort_keys=False) + "\n")
    (FIXTURE / "gold.json").write_text(json.dumps(gold, indent=2, sort_keys=False) + "\n")
    manifest = write_context()

    n_nodes = len(graph["nodes"]) + len(graph["artifacts"]) + 1  # +1 for the draft
    print(f"wrote {FIXTURE}")
    print(f"  files/      {sum(1 for _ in FILES.rglob('*') if _.is_file())} project files")
    print(f"  graph.json  {n_nodes} nodes/artifacts, {len(graph['edges'])} edges")
    print(f"  gold.json   window={len(gold['window_ids'])} orphans={len(gold['orphan_ids'])} "
          f"inventory={gold['inventory']} stale={gold['stale']} "
          f"malformed={gold['malformed_closes']} citations={gold['citations']}")
    for name, info in manifest["targets"].items():
        print(f"  context/{name:<6} {info['n_files']} files, "
              f"{info['estimated_tokens']} estimated tokens (target {info['target_tokens']})")


if __name__ == "__main__":
    main()
