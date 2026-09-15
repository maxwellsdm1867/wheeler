#!/usr/bin/env python
"""Aggregate every ``runs/*/results.json`` into ``REPORT.md``.

    .venv/bin/python evals/close_cost/report.py [--runs DIR] [--out FILE]

Stdlib only. A run whose results.json is missing or unreadable is listed under
"Skipped" rather than aborting the report. Anything a human wrote under
``## Recommendation`` survives a re-render.
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent

RUN_COLUMNS = [
    ("run", "run"),
    ("arm", "arm"),
    ("context", "ctx"),
    ("context_target_tokens", "ctx target"),
    ("context_achieved_tokens", "ctx achieved"),
    ("turns", "turns"),
    ("parent_turns", "parent turns"),
    ("subagent_turns", "sub turns"),
    ("input_tokens", "input"),
    ("cache_read", "cache read"),
    ("cache_create", "cache create"),
    ("output_tokens", "output"),
    ("context_total", "context total"),
    ("cost_usd", "cost $"),
    ("wall_clock_s", "wall s"),
    ("tool_calls_total", "tool calls"),
    ("sweep_tool_calls", "sweep calls"),
    ("subagent_used", "subagent"),
    ("subagent_usage_visible", "sub usage visible"),
    ("window_recall", "win recall"),
    ("window_precision", "win prec"),
    ("orphan_recall", "orph recall"),
    ("orphan_precision", "orph prec"),
    ("inventory_exact", "inv exact"),
    ("all_exact", "all exact"),
    ("status", "status"),
]

MEAN_COLUMNS = [
    ("arm", "arm"),
    ("context", "ctx"),
    ("n", "runs"),
    ("context_achieved_tokens", "ctx achieved"),
    ("turns", "turns"),
    ("input_tokens", "input"),
    ("cache_read", "cache read"),
    ("cache_create", "cache create"),
    ("output_tokens", "output"),
    ("context_total", "context total"),
    ("cost_usd", "cost $"),
    ("wall_clock_s", "wall s"),
    ("sweep_tool_calls", "sweep calls"),
    ("window_recall", "win recall"),
    ("orphan_recall", "orph recall"),
    ("all_exact_rate", "all exact rate"),
]

MEAN_KEYS = [
    "context_achieved_tokens", "turns", "input_tokens", "cache_read", "cache_create",
    "output_tokens", "context_total", "cost_usd", "wall_clock_s", "sweep_tool_calls",
    "window_recall", "window_precision", "orphan_recall", "orphan_precision",
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
    totals = results.get("totals") or {}
    status = "ok"
    if results.get("timed_out"):
        status = "timeout"
    elif results.get("returncode") not in (0, None):
        status = f"rc={results.get('returncode')}"
    elif not score.get("ok"):
        status = "no digest"
    elif _get(results, "result", "is_error"):
        status = "claude_error"
    if results.get("context_target_missed"):
        status += " CTX-MISSED"
    if results.get("agent_calls") and not results.get("subagent_usage_visible"):
        status += " SUB-UNCOUNTED"
    return {
        "run": Path(results.get("run_dir", "?")).name,
        "arm": results.get("arm"),
        "context": results.get("context"),
        "context_target_tokens": results.get("context_target_tokens", 0),
        "context_achieved_tokens": results.get("context_achieved_tokens", 0),
        "context_target_missed": bool(results.get("context_target_missed")),
        "turns": results.get("turns", 0),
        "parent_turns": results.get("parent_turns", 0),
        "subagent_turns": results.get("subagent_turns", 0),
        "input_tokens": totals.get("input", 0),
        "cache_read": totals.get("cache_read", 0),
        "cache_create": totals.get("cache_creation", 0),
        "output_tokens": totals.get("output", 0),
        "context_total": totals.get("context_total", 0),
        "token_source": totals.get("source", "?"),
        "cost_usd": round(totals.get("cost_usd", 0.0), 4),
        "wall_clock_s": results.get("wall_clock_s", 0.0),
        "tool_calls_total": sum((results.get("tool_calls") or {}).values()),
        "sweep_tool_calls": results.get("sweep_tool_calls", 0),
        "parent_sweep_tool_calls": results.get("parent_sweep_tool_calls", 0),
        "subagent_used": bool(results.get("agent_calls")),
        "subagent_usage_visible": bool(results.get("subagent_usage_visible")),
        "parent_context_peak": results.get("parent_context_peak_tokens", 0),
        "subagent_context_peak": results.get("subagent_context_peak_tokens", 0),
        "consistency_graph_only": results.get("consistency_graph_only"),
        "consistency_result_chars": results.get("consistency_result_chars"),
        "window_recall": _get(score, "window", "recall", default=0.0),
        "window_precision": _get(score, "window", "precision", default=0.0),
        "orphan_recall": _get(score, "orphan", "recall", default=0.0),
        "orphan_precision": _get(score, "orphan", "precision", default=0.0),
        "inventory_exact": bool(_get(score, "inventory", "exact", default=False)),
        "stale_exact": bool(_get(score, "stale", "exact", default=False)),
        "citations_exact": bool(_get(score, "citations", "exact", default=False)),
        "malformed_exact": bool(_get(score, "malformed_closes", "exact", default=False)),
        "all_exact": bool(score.get("all_exact")),
        "status": status,
    }


def _fmt(value) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return f"{value:.3f}" if 0 < abs(value) <= 1 else f"{value:.1f}"
    if value is None:
        return "-"
    return str(value)


def _table(columns: list[tuple[str, str]], rows: list[dict]) -> list[str]:
    head = "| " + " | ".join(h for _, h in columns) + " |"
    sep = "|" + "|".join("---" for _ in columns) + "|"
    body = ["| " + " | ".join(_fmt(r.get(k, "")) for k, _ in columns) + " |" for r in rows]
    return [head, sep, *body]


def cell_means(rows: list[dict]) -> list[dict]:
    out = []
    keys = sorted({(r["arm"], r["context"]) for r in rows},
                  key=lambda x: (str(x[1]), str(x[0])))
    for arm, ctx in keys:
        group = [r for r in rows if r["arm"] == arm and r["context"] == ctx]
        mean_row: dict = {"arm": arm, "context": ctx, "n": len(group)}
        for key in MEAN_KEYS:
            vals = [float(r[key]) for r in group if isinstance(r.get(key), (int, float))]
            digits = 3 if key.endswith(("recall", "precision")) or key == "cost_usd" else 1
            mean_row[key] = round(statistics.fmean(vals), digits) if vals else 0.0
        mean_row["all_exact_rate"] = round(
            statistics.fmean(1.0 if r["all_exact"] else 0.0 for r in group), 3
        )
        out.append(mean_row)
    return out


def payoff_section(means: list[dict]) -> list[str]:
    lines = [
        "## Does the split pay off?",
        "",
        "`context total` is input + cache read + cache creation over the whole "
        "session, taken from the final `result` line's `modelUsage`, which "
        "includes the subagent. `ratio` is split over inline: below 1.0 means "
        "the split read less. Correctness sits in the same table on purpose: a "
        "cheaper arm that gets the sweep wrong is not cheaper.",
        "",
    ]
    contexts = sorted({m["context"] for m in means})
    rows = []
    for ctx in contexts:
        inline = next((m for m in means if m["context"] == ctx and m["arm"] == "inline"), None)
        split = next((m for m in means if m["context"] == ctx and m["arm"] == "split"), None)
        if not (inline and split):
            lines.append(f"- `{ctx}`: only one arm has runs, no comparison yet.")
            continue
        for label, key, digits in [
            ("context total (tokens)", "context_total", 1),
            ("cost (USD)", "cost_usd", 4),
            ("output tokens", "output_tokens", 1),
            ("wall clock (s)", "wall_clock_s", 1),
        ]:
            a, b = inline[key], split[key]
            rows.append({
                "context": ctx,
                "metric": label,
                "inline": round(a, digits),
                "split": round(b, digits),
                "delta": round(b - a, digits),
                "ratio": round(b / a, 3) if a else "-",
            })
        rows.append({
            "context": ctx,
            "metric": "all-gold-exact rate",
            "inline": inline["all_exact_rate"],
            "split": split["all_exact_rate"],
            "delta": round(split["all_exact_rate"] - inline["all_exact_rate"], 3),
            "ratio": "-",
        })
    if rows:
        lines += _table(
            [("context", "ctx"), ("metric", "metric"), ("inline", "inline"),
             ("split", "split"), ("delta", "split - inline"), ("ratio", "split / inline")],
            rows,
        )
        lines.append("")
    return lines


def build_report(runs_dir: Path, recommendation: str = "") -> str:
    rows: list[dict] = []
    skipped: list[str] = []
    for path in sorted(runs_dir.glob("*/results.json")):
        if path.parent.name.endswith("checkgold"):
            continue
        try:
            rows.append(flatten(json.loads(path.read_text())))
        except Exception as exc:  # a broken run must not hide the others
            skipped.append(f"{path.parent.name}: {type(exc).__name__}: {exc}")
    for d in sorted(runs_dir.glob("*/")) if runs_dir.exists() else []:
        if d.is_dir() and not (d / "results.json").exists() and not d.name.endswith("checkgold"):
            skipped.append(f"{d.name}: no results.json (run crashed before scoring)")

    means = cell_means(rows) if rows else []
    lines = [
        "# /wh:close mechanical sweep: inline or one subagent?",
        "",
        f"Runs aggregated from `{runs_dir if not runs_dir.is_relative_to(HERE) else runs_dir.relative_to(HERE)}`: "
        f"{len(rows)} run(s).",
        "",
        "## What is measured",
        "",
        "Only the MECHANICAL half of a close: the phases that need a timestamp "
        "and the graph, not the conversation. Those are 1.1 (window boundary "
        "plus the malformed-close check), 1.2 (recent entities), 1.3 (orphans), "
        "1.6 (`detect_stale`), 2.1 (per-type inventory), 2.4 "
        "(`validate_citations`) and 2.6 (`graph_consistency_check`).",
        "",
        "The judgment phases (1.3b conversation sweep, 1.3c graph-state updates, "
        "orphan grouping in 1.4, and the synthesis narrative in 2.2) need the "
        "scientist and stay in the main session in BOTH arms, so they cancel out "
        "and are deliberately excluded. Nothing here says what a whole close "
        "costs; it says what the delegable part of one costs.",
        "",
        "## Per run",
        "",
        *(_table(RUN_COLUMNS, rows) if rows else ["(no runs yet)"]),
        "",
        "## Per cell (means by arm and context)",
        "",
        *(_table(MEAN_COLUMNS, means) if means else ["(no runs yet)"]),
        "",
        *payoff_section(means),
        "## How to read this",
        "",
        "`ctx target` is the estimated token size of the filler the model was "
        "told to read first; `ctx achieved` is the largest per-turn context "
        "(input + cache read + cache creation) seen on a PARENT assistant turn, "
        "which is what the main session actually carried. A run whose achieved "
        "context fell below 70 percent of target is flagged `CTX-MISSED` in the "
        "status column and must not be compared with the others.",
        "",
        "`input`, `cache read`, `cache create`, `output` and `cost $` come from "
        "the final `result` line's `modelUsage`, NOT from its `usage` block. "
        "Once an Agent call has run, `usage` carries only the parent's last "
        "exchange and undercounts the session by orders of magnitude; "
        "`modelUsage` and `total_cost_usd` are session totals that include the "
        "subagent. A run where an Agent call happened but no subagent assistant "
        "line reached the parent stream is flagged `SUB-UNCOUNTED`: its total is "
        "not trustworthy and must not be reported as a win.",
        "",
        "`win recall` / `orph recall` are matched-over-expected against the gold "
        "id sets, `prec` is matched over what the run returned, so an invented "
        "id lowers precision without touching recall. `all exact` is true only "
        "when every gold field matches: window set, orphan set, inventory "
        "counts, stale script, malformed-close count, citation totals, the "
        "`$since` instant and `consistency_ok`.",
        "",
        "Two fixture facts that inflate both arms equally and are worth "
        "subtracting mentally from the absolute numbers:",
        "",
        "- `graph_consistency_check` runs an UNSCOPED `MATCH (n) RETURN n.id` "
        "over the whole database. This database is shared and holds about 4100 "
        "nodes from other work, so step 7's `graph_only` list comes back with "
        "roughly 4100 ids in it. On a single-project database that list would "
        "be empty. Each run records `consistency_graph_only` and "
        "`consistency_result_chars` in its `results.json`.",
        "- `consistency_ok` is therefore defined on the layers this project owns "
        "(`json_only`, `synthesis_missing`, `synthesis_orphaned` all empty) and "
        "ignores `graph_only`.",
        "",
    ]
    if rows:
        lines += [
            "Subagent usage visible in the parent stream: "
            + ", ".join(f"{r['run']}={_fmt(r['subagent_usage_visible'])}"
                        for r in rows if r["subagent_used"])
            + (" (no run made an Agent call)" if not any(r["subagent_used"] for r in rows) else ""),
            "",
            "Token source per run: "
            + ", ".join(f"{r['run']}={r['token_source']}" for r in rows),
            "",
        ]
    if skipped:
        lines += ["## Skipped", "", *[f"- {s}" for s in skipped], ""]
    lines += [
        "## Recommendation",
        "",
        recommendation or "_To be filled in by the human after reading the tables._",
        "",
    ]
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
