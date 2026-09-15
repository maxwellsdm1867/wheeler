#!/usr/bin/env python
"""Aggregate every ``runs/*/results.json`` into ``REPORT.md``.

    .venv/bin/python evals/batch_registration/report.py [--runs DIR] [--out FILE]

Stdlib only. A run whose results.json is missing or unreadable is listed in a
"skipped" note rather than aborting the report.
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent

RUN_COLUMNS = [
    ("run", "run"),
    ("strategy", "s"),
    ("model", "model"),
    ("turns", "turns"),
    ("input_tokens", "input"),
    ("cache_read", "cache read"),
    ("cache_create", "cache create"),
    ("output_tokens", "output"),
    ("cost_usd", "cost $"),
    ("wall_clock_s", "wall s"),
    ("nodes", "nodes"),
    ("edges", "edges"),
    ("edge_recall", "edge recall"),
    ("edge_precision", "edge prec"),
    ("mutation_calls", "mutation calls"),
    ("status", "status"),
]

MEAN_COLUMNS = [
    ("strategy", "s"),
    ("model", "model"),
    ("n", "runs"),
    ("turns", "turns"),
    ("input_tokens", "input"),
    ("cache_read", "cache read"),
    ("cache_create", "cache create"),
    ("output_tokens", "output"),
    ("cost_usd", "cost $"),
    ("wall_clock_s", "wall s"),
    ("nodes", "nodes"),
    ("edges", "edges"),
    ("edge_recall", "edge recall"),
    ("edge_precision", "edge prec"),
    ("mutation_calls", "mutation calls"),
]


def _get(d: dict, *path, default=None):
    cur = d
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def flatten(results: dict) -> dict:
    score = results.get("score") or {}
    # The final "result" line's usage block is the authoritative total for the
    # session (the per-message stream events carry partial output counts). Fall
    # back to the per-message sum only when a run has no result line.
    tokens = _get(results, "result", "usage") or results.get("tokens") or {}
    cost = _get(results, "result", "total_cost_usd")
    status = "ok"
    if results.get("timed_out"):
        status = "timeout"
    elif results.get("returncode") not in (0, None):
        status = f"rc={results.get('returncode')}"
    elif "error" in score:
        status = "unscored"
    elif _get(results, "result", "is_error"):
        status = "claude_error"
    return {
        "run": Path(results.get("run_dir", "?")).name,
        "strategy": results.get("strategy"),
        "model": results.get("model") or "-",
        "turns": results.get("turns", 0),
        "input_tokens": tokens.get("input_tokens", 0),
        "cache_read": tokens.get("cache_read_input_tokens", 0),
        "cache_create": tokens.get("cache_creation_input_tokens", 0),
        "output_tokens": tokens.get("output_tokens", 0),
        "cost_usd": round(cost, 3) if isinstance(cost, (int, float)) else 0.0,
        "wall_clock_s": results.get("wall_clock_s", 0.0),
        "nodes": f"{score.get('nodes_matched', 0)}/{score.get('nodes_expected', '?')}",
        "nodes_matched": score.get("nodes_matched", 0),
        "edges": f"{score.get('edges_matched', 0)}/{score.get('edges_expected', '?')}",
        "edges_matched": score.get("edges_matched", 0),
        "edge_recall": score.get("edge_recall", 0.0),
        "edge_precision": score.get("edge_precision", 0.0),
        "mutation_calls": results.get("mutation_calls", 0),
        "status": status,
        "subagent_usage_visible": results.get("subagent_usage_visible"),
        "done_line": results.get("done_line"),
    }


def _fmt(value) -> str:
    if isinstance(value, float):
        return f"{value:.3f}" if 0 < abs(value) <= 1 else f"{value:.1f}"
    return str(value)


def _table(columns: list[tuple[str, str]], rows: list[dict]) -> list[str]:
    head = "| " + " | ".join(h for _, h in columns) + " |"
    sep = "|" + "|".join("---" for _ in columns) + "|"
    body = ["| " + " | ".join(_fmt(r.get(k, "")) for k, _ in columns) + " |" for r in rows]
    return [head, sep, *body]


def per_strategy_means(rows: list[dict]) -> list[dict]:
    out = []
    keys = sorted({(r["strategy"], r["model"]) for r in rows}, key=lambda x: (x[0] is None, x[0], x[1]))
    for s, model in keys:
        group = [r for r in rows if r["strategy"] == s and r["model"] == model]
        mean_row: dict = {"strategy": s, "model": model, "n": len(group)}
        for key in ("turns", "input_tokens", "cache_read", "cache_create", "output_tokens",
                    "cost_usd", "wall_clock_s", "edge_recall", "edge_precision", "mutation_calls"):
            vals = [float(r[key]) for r in group if isinstance(r.get(key), (int, float))]
            digits = 3 if key in ("edge_recall", "edge_precision", "cost_usd") else 1
            mean_row[key] = round(statistics.fmean(vals), digits) if vals else 0.0
        nm = statistics.fmean(r["nodes_matched"] for r in group)
        em = statistics.fmean(r["edges_matched"] for r in group)
        expected_n = group[0]["nodes"].split("/")[-1]
        expected_e = group[0]["edges"].split("/")[-1]
        mean_row["nodes"] = f"{nm:.1f}/{expected_n}"
        mean_row["edges"] = f"{em:.1f}/{expected_e}"
        out.append(mean_row)
    return out


def build_report(runs_dir: Path, recommendation: str = "") -> str:
    rows: list[dict] = []
    skipped: list[str] = []
    for path in sorted(runs_dir.glob("*/results.json")):
        try:
            rows.append(flatten(json.loads(path.read_text())))
        except Exception as exc:  # a broken run must not hide the others
            skipped.append(f"{path.parent.name}: {type(exc).__name__}: {exc}")
    for d in sorted(runs_dir.glob("*/")):
        if d.is_dir() and not (d / "results.json").exists():
            skipped.append(f"{d.name}: no results.json (run still in progress or crashed before scoring)")

    lines = [
        "# Batch registration experiment (issue #117)",
        "",
        f"Runs aggregated from `{runs_dir.relative_to(HERE) if runs_dir.is_relative_to(HERE) else runs_dir}`: "
        f"{len(rows)} run(s).",
        "",
        "## Per run",
        "",
        *_table(RUN_COLUMNS, rows),
        "",
        "## Per strategy (means)",
        "",
        *(_table(MEAN_COLUMNS, per_strategy_means(rows)) if rows else ["(no runs yet)"]),
        "",
        "## How to read this",
        "",
        "Strategy 0 is the oracle: `register_batch` called directly from the gold manifest with no "
        "model, so its tokens and turns are zero by construction and its recall proves the scorer. "
        "Strategies 1 to 6 are the model-driven methods described in `prompts/`. `turns` counts "
        "distinct assistant messages in the transcript. `input`, `cache read`, `cache create`, "
        "`output` and `cost $` come from the final `result` line's usage block, the session total "
        "(per-message stream events carry partial output counts and are kept in results.json only "
        "as a cross-check). `input` is the uncached share; the context the model read over the whole "
        "run is input + cache read + cache create, and because every turn re-reads the whole "
        "context, `cache read` scales with turns times context size. "
        "`wall s` is the harness-measured wall clock of the `claude` subprocess, including MCP "
        "server startup. `nodes` and `edges` are matched-against-gold over expected (30 nodes, 43 "
        "edges); `edge recall` is matched over expected and `edge prec` is matched over every edge "
        "the run created among tagged nodes, so duplicated or invented edges lower precision without "
        "touching recall. `mutation calls` counts calls to `wheeler_mutations` tools plus each "
        "non-dry-run CLI `integrate register` call. For strategy 5 the parent transcript may not "
        "carry the subagent's usage; check `subagent_usage_visible` in that run's results.json "
        "before comparing its token columns with the others.",
        "",
    ]
    subagent_rows = [r for r in rows if r["strategy"] == 5]
    if subagent_rows:
        lines += [
            "Strategy 5 subagent usage visible in the parent stream: "
            + ", ".join(f"{r['run']}={r['subagent_usage_visible']}" for r in subagent_rows),
            "",
        ]
    if skipped:
        lines += ["## Skipped", "", *[f"- {s}" for s in skipped], ""]
    lines += ["## Recommendation", "", recommendation or "_To be filled in by the human after reading the tables._", ""]
    return "\n".join(lines)


def _existing_recommendation(path: Path) -> str:
    """Text a human already wrote under '## Recommendation', kept across re-renders."""
    if not path.exists():
        return ""
    text = path.read_text()
    marker = "## Recommendation"
    if marker not in text:
        return ""
    return text.split(marker, 1)[1].strip()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runs", type=Path, default=HERE / "runs")
    ap.add_argument("--out", type=Path, default=HERE / "REPORT.md")
    ns = ap.parse_args()
    text = build_report(ns.runs, recommendation=_existing_recommendation(ns.out))
    ns.out.write_text(text)
    print(f"wrote {ns.out}")
    print(text)


if __name__ == "__main__":
    main()
