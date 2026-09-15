#!/usr/bin/env python
"""Aggregate every ``runs/*/t*-r*/results.json`` into ``REPORT.md``.

    .venv/bin/python evals/disclosure/report.py [--runs DIR] [--out FILE]

Stdlib only. A run whose results.json is missing or unreadable is listed in a
"skipped" note rather than aborting the report. Text a human wrote under
``## Recommendation`` is preserved across re-renders.
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent

LEVEL_ORDER = {"full": 0, "trimmed": 1, "pointer": 2}

RUN_COLUMNS = [
    ("level", "level"),
    ("task", "task"),
    ("kind", "kind"),
    ("body", "body?"),
    ("repeat", "r"),
    ("verdict", "verdict"),
    ("score", "score"),
    ("turns", "turns"),
    ("context", "context"),
    ("output_tokens", "output"),
    ("cost_usd", "cost $"),
    ("wall_clock_s", "wall s"),
    ("show_node", "show_node"),
    ("hop_calls", "hop"),
    ("cypher_calls", "cypher"),
    ("status", "status"),
]

MEAN_COLUMNS = [
    ("level", "level"),
    ("model", "model"),
    ("n", "runs"),
    ("accuracy", "accuracy"),
    ("score", "mean score"),
    ("turns", "turns"),
    ("context", "context"),
    ("output_tokens", "output"),
    ("cost_usd", "cost $"),
    ("wall_clock_s", "wall s"),
    ("show_node", "show_node"),
    ("hop_calls", "hop"),
    ("cypher_calls", "cypher"),
    ("body_accuracy", "acc: needs body"),
    ("body_score", "score: needs body"),
    ("rest_accuracy", "acc: rest"),
    ("rest_score", "score: rest"),
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
    # The final "result" line's usage block is the authoritative session total
    # (per-message stream events carry partial output counts). Fall back to the
    # per-message sum only when a run has no result line.
    tokens = _get(results, "result", "usage") or results.get("tokens") or {}
    cost = _get(results, "result", "total_cost_usd")
    status = "ok"
    if results.get("timed_out"):
        status = "timeout"
    elif results.get("returncode") not in (0, None):
        status = f"rc={results.get('returncode')}"
    elif _get(results, "result", "is_error"):
        status = "claude_error"
    elif results.get("answer_line") is None:
        status = "no_answer"
    sn = results.get("show_node") or {}
    flags = []
    if sn.get("with_neighbors"):
        flags.append("n")
    if sn.get("with_fields"):
        flags.append("f")
    if sn.get("with_node_ids"):
        flags.append("m")
    context = (
        int(tokens.get("input_tokens", 0))
        + int(tokens.get("cache_read_input_tokens", 0))
        + int(tokens.get("cache_creation_input_tokens", 0))
    )
    return {
        "level": results.get("level", "?"),
        "model": results.get("model") or "-",
        "task": results.get("task"),
        "kind": results.get("kind", "?"),
        "body": "yes" if results.get("may_need_body") else "no",
        "may_need_body": bool(results.get("may_need_body")),
        "repeat": results.get("repeat_index", 1),
        "verdict": score.get("verdict", "unscored"),
        "score": float(score.get("score", 0.0)),
        "correct": 1.0 if score.get("verdict") == "correct" else 0.0,
        "turns": results.get("turns", 0),
        "context": context,
        "output_tokens": int(tokens.get("output_tokens", 0)),
        "cost_usd": round(cost, 3) if isinstance(cost, (int, float)) else 0.0,
        "wall_clock_s": results.get("wall_clock_s", 0.0),
        "show_node": f"{sn.get('calls', 0)}" + (f" [{''.join(flags)}]" if flags else ""),
        "show_node_calls": sn.get("calls", 0),
        "hop_calls": results.get("hop_calls", 0),
        "cypher_calls": results.get("cypher_calls", 0),
        "status": status,
        "answer_line": results.get("answer_line"),
        "run": Path(results.get("out_dir", "?")).name,
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


def _mean(vals: list[float], digits: int = 1) -> float:
    return round(statistics.fmean(vals), digits) if vals else 0.0


def per_level_means(rows: list[dict]) -> list[dict]:
    out = []
    keys = sorted({(r["level"], r["model"]) for r in rows}, key=lambda x: (LEVEL_ORDER.get(x[0], 9), x[1]))
    for level, model in keys:
        group = [r for r in rows if r["level"] == level and r["model"] == model]
        body = [r for r in group if r["may_need_body"]]
        rest = [r for r in group if not r["may_need_body"]]
        out.append({
            "level": level,
            "model": model,
            "n": len(group),
            "accuracy": _mean([r["correct"] for r in group], 3),
            "score": _mean([r["score"] for r in group], 3),
            "turns": _mean([r["turns"] for r in group]),
            "context": _mean([r["context"] for r in group]),
            "output_tokens": _mean([r["output_tokens"] for r in group]),
            "cost_usd": _mean([r["cost_usd"] for r in group], 3),
            "wall_clock_s": _mean([r["wall_clock_s"] for r in group]),
            "show_node": _mean([r["show_node_calls"] for r in group]),
            "hop_calls": _mean([r["hop_calls"] for r in group]),
            "cypher_calls": _mean([r["cypher_calls"] for r in group]),
            "body_accuracy": _mean([r["correct"] for r in body], 3) if body else "-",
            "body_score": _mean([r["score"] for r in body], 3) if body else "-",
            "rest_accuracy": _mean([r["correct"] for r in rest], 3) if rest else "-",
            "rest_score": _mean([r["score"] for r in rest], 3) if rest else "-",
        })
    return out


def per_task_by_level(rows: list[dict]) -> list[str]:
    """One row per task, one column per level: verdict and mean context."""
    levels = sorted({r["level"] for r in rows}, key=lambda x: LEVEL_ORDER.get(x, 9))
    tasks = sorted({r["task"] for r in rows}, key=lambda t: (t is None, t))
    head = "| task | kind | body? | " + " | ".join(f"{lv} (score / turns / context)" for lv in levels) + " |"
    sep = "|" + "|".join("---" for _ in range(3 + len(levels))) + "|"
    lines = [head, sep]
    for t in tasks:
        trs = [r for r in rows if r["task"] == t]
        kind = trs[0]["kind"]
        body = trs[0]["body"]
        cells = []
        for lv in levels:
            g = [r for r in trs if r["level"] == lv]
            if not g:
                cells.append("-")
                continue
            cells.append(f"{_mean([r['score'] for r in g], 2)} / {_mean([r['turns'] for r in g])} / {int(_mean([r['context'] for r in g], 0))}")
        lines.append(f"| {t} | {kind} | {body} | " + " | ".join(cells) + " |")
    return lines


def build_report(runs_dir: Path, recommendation: str = "") -> str:
    rows: list[dict] = []
    skipped: list[str] = []
    for path in sorted(runs_dir.glob("*/t*-r*/results.json")):
        try:
            rows.append(flatten(json.loads(path.read_text())))
        except Exception as exc:  # a broken run must not hide the others
            skipped.append(f"{path.parent.parent.name}/{path.parent.name}: {type(exc).__name__}: {exc}")
    for d in sorted(runs_dir.glob("*/t*-r*/")):
        if d.is_dir() and not (d / "results.json").exists():
            skipped.append(f"{d.parent.name}/{d.name}: no results.json (in progress or crashed before scoring)")
    rows.sort(key=lambda r: (LEVEL_ORDER.get(r["level"], 9), r["task"] or 0, r["repeat"]))

    rel = runs_dir.relative_to(HERE) if runs_dir.is_relative_to(HERE) else runs_dir
    lines = [
        "# Progressive disclosure experiment",
        "",
        "How much of a node should a listing return by default? Three levels of `WHEELER_DISCLOSURE` "
        "(`full`, `trimmed`, `pointer`) over ten read-only research tasks on one seeded graph.",
        "",
        f"Runs aggregated from `{rel}`: {len(rows)} task run(s).",
        "",
        "## Per level (means)",
        "",
        *(_table(MEAN_COLUMNS, per_level_means(rows)) if rows else ["(no runs yet)"]),
        "",
        "## Per task, across levels",
        "",
        *(per_task_by_level(rows) if rows else ["(no runs yet)"]),
        "",
        "## Per run",
        "",
        *_table(RUN_COLUMNS, rows),
        "",
        "## How to read this",
        "",
        "`level` is the value of `WHEELER_DISCLOSURE` the MCP servers were started with; the model "
        "was never told which. `body?` is the task's `may_need_body` flag set by design in "
        "`fixture/tasks.json`: tasks 5 and 6 can only be answered from a finding's full text, the "
        "rest from ids, edges and metadata. The key split is `acc: needs body` against `acc: rest`: "
        "if a pointer default costs accuracy it shows up in the first column, and if the model "
        "simply reads the node when it needs to, it shows up as extra `show_node` calls instead. "
        "`verdict` is correct (score 1), partial (0 < score < 1) or wrong (0); `score` is exact "
        "match on ids, Jaccard for sets, prefix match for ordered chains, per-field for objects "
        "(task 4 weights chain 0.7 and scripts 0.3; task 9 weights count 0.5 and top-3 prefix 0.5). "
        "`turns` counts distinct assistant messages. `context` is the context the model read over "
        "the run: input + cache read + cache create from the final `result` line's usage block (the "
        "session total), so it scales with turns times the size of what the tools returned, which "
        "is exactly what the disclosure level changes. `output` and `cost $` come from the same "
        "block. `wall s` is the `claude` subprocess wall clock including MCP server startup. "
        "`show_node` is the number of show_node calls with flags [n] neighbors=true, [f] fields=, "
        "[m] node_ids= used at least once; `hop` counts the one-hop expanders (show_node with "
        "neighbors=true, search_context); `cypher` counts run_cypher calls. `status` `no_answer` "
        "means the transcript had no parseable `ANSWER <json>` line.",
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
    body = text.split(marker, 1)[1].strip()
    if body.startswith("_To be filled in by the human"):
        return ""
    return body


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
