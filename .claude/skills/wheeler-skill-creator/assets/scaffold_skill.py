"""Stdlib-only SCAFFOLDER for a Wheeler-aware Claude Code skill.

Writes the two files a skill needs (``SKILL.md`` and ``evals/evals.json``) from a
contract given on the command line. It bakes in the parts that are mechanical and
easy to get subtly wrong: the description shape that actually triggers, the
correct split-server tool ids for the chosen read recipe, the read-only hard rule
or the write confirmation step, the score thresholds, and a starter eval set with
negative cases.

It leaves exactly one thing for the human, marked ``TODO``: the domain specifics
(the generalization clause, the query paraphrases, the worked examples). Those
depend on the science, which the scaffolder cannot know.

Run::

    python scaffold_skill.py --name wheeler-figure-trace \\
      --purpose "Trace a figure back to the script and data that produced it" \\
      --trigger "what made this figure" --trigger "regenerate this plot" \\
      --anti-trigger "renaming or moving an artifact file" \\
      --anti-trigger "cosmetic edits (colors, labels, fonts)" \\
      --recipe search-context --mode read --dry-run

Then read the emitted files, fill every TODO, and run ``audit_skill.py``.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

# Read recipes. Each maps to the tools it needs and the fast-path body.
RECIPES = {
    "search-context": {
        "tools": ["mcp__wheeler_core__search_context", "mcp__wheeler_core__show_node"],
        "call": 'mcp__wheeler_core__search_context(query="<paraphrase>", limit=5, hops=2)',
        "why": (
            "`search_context` walks 2 hops along the provenance edges (`USED`, "
            "`WAS_GENERATED_BY`, `WAS_DERIVED_FROM`), so one call returns the seed "
            "node plus the producing script plus the source data. That is almost "
            "always the whole context needed."
        ),
    },
    "search-findings": {
        "tools": ["mcp__wheeler_core__search_findings", "mcp__wheeler_core__show_node"],
        "call": 'mcp__wheeler_core__search_findings(query="<paraphrase>", limit=5)',
        "why": (
            "`search_findings` matches on meaning without expanding the provenance "
            "chain. Use it when the statement is the answer and the chain is not. If "
            "you find yourself asking what produced the finding, the recipe should "
            "have been `search_context`."
        ),
    },
    "typed-query": {
        "tools": ["mcp__wheeler_query__query_TYPE", "mcp__wheeler_core__search_context"],
        "call": "mcp__wheeler_query__query_TYPE(keyword=\"<filter>\", limit=20)",
        "why": (
            "The node type is known and the task needs an ENUMERATION, not a "
            "ranking. Semantic search over a known type silently drops the tail; a "
            "typed listing does not."
        ),
    },
    "direct-id": {
        "tools": ["mcp__wheeler_core__show_node", "mcp__wheeler_core__run_cypher"],
        "call": 'mcp__wheeler_core__show_node(node_id="<F-xxxxxxxx>")',
        "why": (
            "The user named the node. Searching for something you can already "
            "address wastes a call and can rank a different node first."
        ),
    },
    "orientation": {
        "tools": [
            "mcp__wheeler_core__graph_context",
            "mcp__wheeler_core__graph_status",
            "mcp__wheeler_core__graph_gaps",
        ],
        "call": 'mcp__wheeler_core__graph_context(topic="")',
        "why": (
            "`graph_context` reports recent activity, which is the right read for "
            "orientation and the wrong read for locating one artifact."
        ),
    },
}

BASE_TOOLS = ["Read", "Grep", "Glob"]

QUERY_TYPES = (
    "findings hypotheses open_questions datasets papers documents plans notes "
    "executions analyses review_queue"
).split()

PLUGIN_PREFIX = "mcp__plugin_wh_wheeler"


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (value or "").strip().lower()).strip("-")


def plugin_twin(tool: str) -> str:
    return tool.replace("mcp__wheeler", PLUGIN_PREFIX, 1)


def build_description(args) -> str:
    """The five-part shape that actually triggers.

    ACTION, QUOTED PHRASES, GENERALIZATION, GATE, ANTI-TRIGGERS. A description
    that describes the skill instead of describing when to use it never fires.
    """
    purpose = args.purpose.rstrip(".")
    phrases = ", ".join(f'"{t}"' for t in args.trigger)
    # Comma-joined with no trailing "and": the sentence continues past this
    # clause with two more "for ..." items, so an Oxford "and" reads as a stop.
    anti = args.anti_trigger or ["TODO: the adjacent request this must ignore"]
    anti_clause = ", ".join(anti)
    return (
        f"{purpose}. "
        f"Use whenever the user asks {phrases}, or otherwise "
        f"TODO: state the general case these phrasings are examples of. "
        f"Use even when the user does not say the word \"Wheeler\": "
        f"TODO: one clause on why the graph beats the obvious alternative here. "
        f"Only applies in Wheeler-managed projects (a `.wheeler/` directory exists "
        f"or CLAUDE.md identifies it as such). "
        f"Skip for {anti_clause}, for generic coding repos, and while a `/wh:*` "
        f"slash command is already driving the turn."
    )


def build_tools(args) -> list[str]:
    recipe = RECIPES[args.recipe]
    tools = list(recipe["tools"])
    if args.recipe == "typed-query":
        tools = [t.replace("query_TYPE", f"query_{args.query_type}") for t in tools]
    for extra in args.extra_tool:
        if extra not in tools:
            tools.append(extra)
    if args.mode == "write":
        for w in args.write_tool or []:
            t = w if w.startswith("mcp__") else f"mcp__wheeler_mutations__{w}"
            if t not in tools:
                tools.append(t)
    ordered = tools + [t for t in BASE_TOOLS if t not in tools]
    if args.plugin_spellings:
        wheeler = [t for t in ordered if t.startswith("mcp__wheeler")]
        ordered = ordered + [plugin_twin(t) for t in wheeler]
    return ordered


def build_skill_md(args) -> str:
    recipe = RECIPES[args.recipe]
    call = recipe["call"]
    if args.recipe == "typed-query":
        call = call.replace("query_TYPE", f"query_{args.query_type}")
    tools = build_tools(args)
    tool_block = "\n".join(f"  - {t}" for t in tools)
    title = args.name.replace("-", " ").title()

    cypher_note = (
        "\n\n`run_cypher` is read-only by tool design (it rejects CREATE and "
        "DELETE), which is why it can sit on a read-only allowlist."
        if any("run_cypher" in t for t in tools)
        else ""
    )

    if args.mode == "read":
        mode_section = """## Read-only, hard rule

This skill **never writes to the graph.** The frontmatter `allowed-tools`
whitelists reads only. Every mutating Wheeler tool (`add_*`, `update_node`,
`delete_node`, `link_nodes`, `unlink_nodes`, `set_tier`, `ensure_artifact`,
`execute_merge`, `index_node`, `init_schema`) is deliberately excluded.

If you notice a missing edge, a stale node, or an unindexed artifact while
reading, **do not fix it from inside this skill.** Say so in one line, point the
scientist at `/wh:add`, `/wh:note`, or `/wh:close`, and carry on with the task
they actually asked for.""" + cypher_note
    else:
        mode_section = """## Writes need confirmation

This skill can write, so it carries the obligations a read-only skill does not.

- **Every graph write goes through a `mcp__wheeler_mutations__*` tool.** Those
  route through `execute_tool()`, which is what fires the triple-write (Neo4j
  node, `knowledge/{id}.json`, `synthesis/{id}.md`) plus the embedding, the write
  receipt, and the trace id.
- **Never write `knowledge/*.json` or `synthesis/*.md` with `Write` or `Edit`.**
  That leaves a file with no graph node and no receipt, which shows up later as
  drift in `graph_consistency_check`. Reading those files is fine, and is often
  where the full content you need lives.
- **Confirm before every mutation.** State what you are about to write, in the
  scientist's terms, and wait. This skill fires on phrasing rather than on a
  typed command, so its mandate is weaker than an act's, not stronger.
- **Prefer routing to an act.** If the write is a recognized Wheeler operation,
  point at `/wh:note`, `/wh:add`, or `/wh:close` instead of reimplementing it.
  The acts carry the citation rules and the session bookkeeping."""

    return f"""---
name: {args.name}
description: {build_description(args)}
allowed-tools:
{tool_block}
---

# {title}

## Why this exists

TODO: two or three sentences. What does the graph already know that makes this
skill worth firing? Name the concrete thing the model would otherwise get wrong
(grep a stale filename, read the wrong `.mat`, re-derive a number that a Finding
already records). Be specific to this skill's job, not to Wheeler in general.

{mode_section}

## When NOT to use

The trigger is "{args.purpose.rstrip('.')}". Skip the graph call when the
operation is mechanical and the read would only add latency:

{chr(10).join(f"- **{a[0].upper() + a[1:]}**." for a in (args.anti_trigger or ["TODO: fill from the anti-triggers"]))}
- **Brand-new work** where nothing could be in the graph yet.
- **An active `/wh:*` flow.** If the scientist invoked a Wheeler slash command
  this turn, defer to it: the act owns the graph interaction.

## The fast path

This is a context-gathering step, not an investigation. The default is one call:

```
{call}
```

{recipe["why"]}

Follow-up file reads, greps, and edits are expected after the graph call. "One
graph call" means one graph call, not one tool call. Add a second graph call only
for a weak-match retry, a second anchor in a comparison, or a direct-id lookup
after a search located the id. Past that you are investigating, which belongs to
`/wh:ask` or `/wh:discuss`.

## Interpreting the result

Scores come from RRF fusion over four channels, any of which can be unavailable,
so they skew low. Absolute value matters more than spread.

| Top score | Meaning | Action |
|---|---|---|
| `> 0.3` | Solid hit | Use it. Report the seed and proceed. |
| `0.1 to 0.3` | Plausible but weak | Retry once with a different paraphrase. If it stays in band, use the best result and say so: "weak match (0.18), verify this is the right artifact". |
| `< 0.1` | Miss | One line to the scientist, then fall back to grep or glob. |

**Surface the miss in one line.** A silent fallback is the dangerous case: when
the graph is authoritative but the query was bad, a near-miss grep result gets
reported with full confidence and the scientist has no signal that the lookup
failed.

**Ids that look like Wheeler nodes but are not.** Wheeler ids are
`<letter>-<8 hex>`, and scientific domains use identifiers in the same shape (a
cell id, a recording id). An empty neighborhood from a direct-id lookup does not
prove the node is absent. Fall back to `search_context` before saying it is not
in the graph.

**Field names.** The primary key is `id`, not `node_id`. Content lives in `text`
on a Finding (older nodes use `description`, so coalesce both), `statement` on a
Hypothesis, `path` on a Script or Dataset, `title` on a Document, Paper, or
OpenQuestion, `command` on an Execution.

## Reporting back

Give the scientist enough to sanity-check that you are looking at the right
thing, then get on with the task. Three to six lines:

```
Found in Wheeler:
- TODO: the seed node, id and one-line content
- TODO: the producing artifact, id and path
- TODO: the source data
```

Do not dump every related node, hypothesis, and cross-reference. Report the
minimum context needed to do the task correctly, then do it.

## Strict rules

- **{"Read-only" if args.mode == "read" else "Confirm every write"}.** Enforced by `allowed-tools`.
- **One graph call by default.** See the fast path for the three exceptions.
- **Do not re-verify the project type.** The description already gates on
  Wheeler-managed projects. Inside the skill, skip the `.wheeler/` check.
- **Never block on the graph.** If the MCP server is down, the breaker is open,
  or the query errors, say so in one line and continue with filesystem tools.
- **Never do the scientist's thinking.** Sharpen the question, flag sparse areas,
  ask rather than pad a thin answer.
- **No em dashes.** Use commas, colons, periods, parentheses.

## What good looks like

TODO: two or three worked examples, each showing the user's actual words, the
exact call made, what came back, and how it was reported. Include one MISS
example where the graph returns nothing and the skill falls back cleanly, and one
NEGATIVE example where the skill correctly does not fire. Worked examples do more
for reliability than another paragraph of rules.
"""


def build_evals(args) -> list[dict]:
    rows = [{"query": t, "should_trigger": True} for t in args.trigger]
    rows += [{"query": a, "should_trigger": False} for a in (args.anti_trigger or [])]
    rows.append(
        {
            "query": "TODO: a near-miss that uses this skill's vocabulary but wants "
            "something else. This is the case that catches over-firing.",
            "should_trigger": False,
        }
    )
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--name", required=True, help="skill directory name, kebab-case")
    ap.add_argument("--purpose", required=True, help="one line: what it does and when")
    ap.add_argument(
        "--trigger",
        action="append",
        default=[],
        required=True,
        help="a phrasing that SHOULD fire it, in the scientist's words (repeatable)",
    )
    ap.add_argument(
        "--anti-trigger",
        action="append",
        default=[],
        help="a near-miss that should NOT fire it (repeatable, strongly recommended)",
    )
    ap.add_argument("--recipe", choices=sorted(RECIPES), default="search-context")
    ap.add_argument("--query-type", choices=QUERY_TYPES, help="for --recipe typed-query")
    ap.add_argument("--mode", choices=("read", "write"), default="read")
    ap.add_argument(
        "--write-tool",
        action="append",
        default=[],
        help="mutation tool for --mode write (bare name or full id, repeatable)",
    )
    ap.add_argument("--extra-tool", action="append", default=[], help="any other grant")
    ap.add_argument(
        "--plugin-spellings",
        action="store_true",
        help="also emit the mcp__plugin_wh_* twin of every Wheeler grant",
    )
    ap.add_argument("--dest", default=".claude/skills", help="parent directory")
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    args.name = slug(args.name)
    if not args.name:
        ap.error("--name did not slugify to anything")
    if args.recipe == "typed-query" and not args.query_type:
        ap.error("--recipe typed-query requires --query-type")
    if args.mode == "write" and not args.write_tool:
        ap.error("--mode write requires at least one --write-tool")
    if not args.anti_trigger:
        print("NOTE: no --anti-trigger given. Over-firing is the more common failure;")
        print("      the emitted description and evals carry TODOs for it.\n")

    root = Path(args.dest).expanduser().resolve() / args.name
    files = {
        root / "SKILL.md": build_skill_md(args),
        root / "evals" / "evals.json": json.dumps(build_evals(args), indent=2) + "\n",
    }

    for path, content in files.items():
        rel = path
        if path.exists() and not args.overwrite:
            print(f"skipped  {rel}  (exists; pass --overwrite)")
            continue
        if args.dry_run:
            print(f"would write  {rel}  ({len(content)} bytes)")
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(f"wrote    {rel}")

    if not args.dry_run:
        print(f"\nNext: fill every TODO in {root / 'SKILL.md'}, then run")
        print(
            "  python "
            + str(Path(__file__).with_name("audit_skill.py"))
            + f" --skill {root}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
