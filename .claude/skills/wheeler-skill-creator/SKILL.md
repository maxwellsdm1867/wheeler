---
name: wheeler-skill-creator
description: >-
  Design and scaffold a NEW Wheeler-aware Claude Code skill by working out with
  the scientist what it does and where the knowledge graph enters it. Use
  whenever the user says "make a wheeler skill", "create a skill for this",
  "I want a skill that pulls in graph context", "turn this workflow into a
  skill", "add a skill that reads the graph", or otherwise wants a repeatable
  research behaviour packaged as a skill that reads or writes the Wheeler
  knowledge graph. Use even when the user does not say the word "skill": "make
  this automatic", "do this every time I ask about X", and "you should always
  check the graph before Y" are all requests for a skill. Only applies in
  Wheeler-managed projects (a `.wheeler/` directory exists or CLAUDE.md
  identifies it as such). Skip for authoring a `/wh:*` act or slash command
  (edit `.claude/commands/wh/` and run `sync_data` instead), for wiring an
  external tool into the graph (that is `wheeler-service-creator`), for running
  or debugging a skill that already exists, and for generic coding.
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
  - AskUserQuestion
  - mcp__wheeler_core__list_acts
  - mcp__wheeler_core__get_act
  - mcp__wheeler_core__graph_status
  - mcp__wheeler_core__graph_context
---

# Wheeler skill creator

You design a new Wheeler-aware skill **with** the scientist, then emit it. The
design conversation is the work. The files are a transcript of a decision the two
of you already made.

Two things have to come out of that conversation, and neither can be guessed:

1. **Their actual workflow.** Not the one-line request: the real sequence of
   steps they walk through, and the artifact it produces at the end.
2. **Where the graph enters that workflow, and in which direction.** Which steps
   can read context that already exists, which steps should put something back
   about the artifact they just produced, and which steps the graph has nothing
   to say about.

Get those wrong and the scaffolding is worthless: a skill that never fires, or
one that fires constantly and dumps forty nodes into context, or one that writes
where it should have asked.

## The one idea

Every Wheeler skill is an answer to a single question: **where does the graph
enter this task, and in which direction.**

That is not a stylistic claim. It is what Wheeler's own corpus does. Across the
39 shipped acts:

| | count |
|---|---|
| Acts that touch the graph | 33 of 39 |
| Of those, acts that write | 25 |
| Of those 25, acts that **read before they write** | **25** |
| Acts that write without any read | **0** |

Read grants outnumber write grants in nearly every act (`add` is 3 reads to 12
writes and is the most write-heavy in the corpus; `discuss` is 14 to 9, `chat` is
7 to 3, the Asta adapters are 4 to 9 reads against a single `link_nodes`).

So the corpus gives you a default and a rule:

- **Reading is the default.** A skill that only reads is safe, cheap, and
  composes with everything else.
- **A write is earned by a read.** You cannot know what a new node duplicates,
  contradicts, or belongs next to without looking first. There is no exception to
  this in 25 acts, and you should not invent the first one.

And a third thing worth saying out loud: **6 of 39 acts touch the graph not at
all** (`backup`, `bump`, `dev-feedback`, `restore`, `triage`, `update`). If the
answer to "where does the graph enter" is "nowhere", that is a legitimate answer.
Say so and build a plain skill.

## What you produce

```
.claude/skills/<name>/
  SKILL.md            the skill: frontmatter description (the trigger) + body
  evals/evals.json    trigger cases, positive and negative
  references/*.md     optional, for material too long for the body
```

No `sync_data`, no `build_plugin`, no `_data` mirror. Those belong to acts, and a
skill is not an act. If what the scientist wants is a typed `/wh:` command,
**stop and say so**: that is a file in `.claude/commands/wh/` plus a `sync_data`
run, and this skill is the wrong tool.

Repo skills are gitignored by default. If the new skill should be versioned, add
a negation to `.gitignore` next to the existing ones.

## Step 1: get clear on their workflow

**Do not scaffold from a one-line request.** "A skill that pulls in graph
context" is not a contract, it is a wish. Three things to settle, in this order.
Use `AskUserQuestion` where the fork is genuine, and prose where you just need
them to talk.

### A. The workflow

**Ask about the work, not about the skill.** Opening with "what should the skill
do" gets you their guess at an implementation. Opening with "walk me through how
you actually do this" gets you the thing you can design against.

So: ask them to walk you through **one real instance**, start to finish, in their
own words. Not the abstraction, the actual last time they did it. Get it to the
granularity of steps ("I open the figure, I go find which script made it, I check
what data it loaded, I rerun it with the new parameter, I write down what
changed"). Note what **artifact** the workflow produces at the end, because that
is what the graph will be asked to remember.

Listen for the step where they got something wrong or slow. That step is usually
the skill. If they cannot produce a real instance, the skill is speculative, and
the honest move is to say so and stop. A skill built for an imagined workflow
fires on nothing.

### B. The trigger

Two questions, and the second is the one that matters:

1. What do you type when you want this?
2. **What do you type that is nearby but must NOT set this off?**

Push for three or four of each, in their words, including the sloppy phrasings.
The negatives are harder to produce and worth more: over-firing is the more
common failure, and a skill that fires on adjacent requests gets disabled by the
user within a week.

Look at whether an existing act or skill already covers it. `list_acts` gives you
the 39 act names and `get_act` gives you a body. If `/wh:ask` already does this,
say so rather than building a second thing that competes with it for the same
phrasing.

### C. The graph contract

This is the co-design, and it is the part the scientist cannot skip. Take the
workflow from A and walk it **step by step**. At each step, ask two questions:

> **Read:** does the graph already know something that would make this step
> faster or less wrong? (What produced this artifact, what the last run
> concluded, whether this question is already open, whether this finding is a
> duplicate.)
>
> **Write back:** did this step produce or change something the graph should
> remember about the artifact? (A result worth recording, a link from the new
> output to the question it answers, a hash that just changed.)

Do not ask this as one abstract question at the end. Ask it per step. The answers
differ per step, and that per-step resolution IS the contract. "Somewhere in here
we should use the graph" is not a design.

Most workflows come out lopsided, and that is correct: several read points near
the start (locating the artifact and its provenance), zero or one write point at
the end (recording what the run produced and wiring it to what it bears on). A
workflow that reads at every step is usually one that should read once and pass
the result along. A workflow that wants to write at every step is usually an act,
not a skill.

Bring the decision aids to the conversation rather than expecting the scientist
to hold them:

- `references/graph-context-recipes.md` has the read recipes (which of the 53
  tools answers which kind of question), the score thresholds, the field names,
  and the traps.
- The five shapes below are what the existing acts actually do. Naming the shape
  usually settles the contract in one exchange.

### The five shapes

| Shape | What it does | Acts that do it |
|---|---|---|
| **Read-only lookup** | Reads to answer a question. Never writes. | `ask`, `report`, `status`, `resume`, `graph-review` |
| **Context-first, then work outside the graph** | One read to locate the artifact and its provenance, then filesystem or analysis work. The graph is an index, not a destination. | `wheeler-context-first` |
| **Read to sharpen, write on approval** | Reads for duplicates and context, proposes, writes only what the scientist approves. | `chat`, `note`, `plan`, `discuss` |
| **Read to shape a request, write the result back** | Reads inputs, calls something external, ingests with provenance on both sides, then wires semantics. Narrow write surface. | `asta-*`, `llmsr-*` |
| **Sweep and consolidate** | Broad read, many writes, end of session. | `close`, `dream`, `compile` |

If the scientist's job does not fit a shape, that is informative: either the job
is two skills, or it is an act.

## Step 2: write the contract back and confirm it

Before you write a file, put the contract in front of them as a table. One row
per step of the job. This is the artifact of Step 1 and the thing they approve.

```
Skill: wheeler-<name>
Fires on: "<phrase>", "<phrase>", "<phrase>"
Never on: "<phrase>", "<phrase>"
Shape:   read to sharpen, write on approval

  step                         direction   tool                        why
  1 locate the artifact        READ        core.search_context         2-hop PROV gives script + data in one call
  2 read the producing script  none        Read                        graph has the path, not the content
  3 record what changed        WRITE       mutations.add_finding       after explicit approval
  4 link it to the question    WRITE       mutations.link_nodes        RELEVANT_TO the open question
```

Then ask the two questions that catch the real mistakes:

- **Is any WRITE row unearned?** Is there a READ above it that tells us what this
  duplicates or contradicts? If not, either add the read or drop the write.
- **Is any READ row unused?** If nothing downstream consumes it, delete it. An
  unused read is pure context cost, and it is the reason skills get a reputation
  for bloat.

Confirm the table before generating. A wrong contract means a wrong skill, and
the scientist reads a four-row table far more carefully than a finished
`SKILL.md`.

## Step 3: the description is the intent surface

The `description` field is the **only** text the model sees when deciding whether
to fire. The body is not consulted. So the description is not documentation, it
is a classifier, and it must carry five parts:

1. **Action.** What it does, in one clause, in the scientist's terms.
2. **Quoted phrases.** Three or four real phrasings from Step 1B, in quotes.
3. **Generalization.** The general case those are examples of, plus the clause
   that catches the implicit ask: "Use even when the user does not say the word
   Wheeler: <why the graph beats the obvious alternative here>."
4. **Gate.** "Only applies in Wheeler-managed projects (a `.wheeler/` directory
   exists or CLAUDE.md identifies it as such)."
5. **Anti-triggers.** "Skip for X, Y, and Z." From Step 1B's negatives, plus the
   standing one: while a `/wh:*` command is already driving the turn.

The failure to watch for: a description that describes **what the skill is**
instead of **when to use it**. "A skill for working with Wheeler graph context"
matches everything and nothing. Concrete phrasings are what the match keys on.

## Step 4: mode and allowed-tools

`allowed-tools` is an allowlist matched on the **full** tool id, so a name that is
wrong in any segment denies the tool silently. The skill still loads, still
fires, and then cannot read the graph. Get the ids from the surface, never from
memory:

```bash
./.venv/bin/python .claude/skills/wheeler-skill-creator/assets/audit_skill.py --list-tools
```

Three things that are easy to get wrong:

- **`mcp__wheeler__<tool>` is dead.** That was the monolith, deleted in v0.14.0.
  There are four servers now and the server is part of the id.
- **The right tool under the wrong server is still denied.**
  `mcp__wheeler_core__query_findings` does not exist: `query_findings` is on
  `wheeler_query`.
- **Server wildcards work** (`mcp__wheeler_query__*`) and are fine for read
  servers. `mcp__wheeler_mutations__*` grants all 18 writes at once, which
  defeats the whole point of a mode, so list the specific mutations instead
  unless the skill is deliberately full-access.

Default to read-only. If the skill writes, it needs a confirmation step in the
body and it needs the reads that earn the write (Step 2). And it must never write
`knowledge/*.json` or `synthesis/*.md` with `Write` or `Edit`: those are two of
the three triple-write layers, and writing them directly leaves a file with no
graph node and no receipt. Reading them is fine and is often where the content
you want lives.

## Step 5: scaffold

The scaffolder emits `SKILL.md` and `evals/evals.json` from the contract, with
the description shape, the correct tool ids for the chosen recipe, the mode
section, and the score thresholds already in place. It is stdlib-only and will
not overwrite without `--overwrite`. Preview with `--dry-run` first.

```bash
./.venv/bin/python .claude/skills/wheeler-skill-creator/assets/scaffold_skill.py \
  --name wheeler-<slug> \
  --purpose "<one line: what it does and when>" \
  --trigger "<phrasing that should fire it>" --trigger "<another>" \
  --anti-trigger "<near-miss that must not fire it>" \
  --recipe search-context \
  --mode read \
  --dry-run
```

Flags worth knowing: `--recipe` is one of `search-context` (the default and
right answer most of the time), `search-findings`, `typed-query` (needs
`--query-type`), `direct-id`, `orientation`. `--mode write` requires at least one
`--write-tool` and emits the confirmation section instead of the read-only rule.
`--plugin-spellings` also emits the `mcp__plugin_wh_*` twin of every Wheeler
grant, which is needed only if the skill must work for someone running the `wh`
plugin rather than direct MCP servers.

Then **fill every TODO**. The scaffolder marks exactly what it cannot know: the
generalization clause, the "why this exists" paragraph, the query paraphrases,
and the worked examples. Do not leave a TODO in a landed skill.

## Step 6: the worked examples matter more than the rules

The single highest-leverage part of the body is the "What good looks like"
section. Write two or three examples, each showing the scientist's actual words,
the exact call made, what came back, and how it was reported. Include:

- one **miss**, where the graph returns nothing and the skill says so in one line
  and falls back cleanly, and
- one **negative**, where the skill correctly does not fire.

Those two do more for reliability than another paragraph of rules, because they
show the model the shape of restraint rather than asserting it.

## Step 7: audit

```bash
./.venv/bin/python .claude/skills/wheeler-skill-creator/assets/audit_skill.py \
  --skill .claude/skills/<name> --verbose
```

It parses the live servers for the real tool surface, then checks the frontmatter
position (a leading comment makes the whole block invisible), every tool id
against that surface, read-only claims against the actual grants, writes against
the presence of reads and a confirmation step, direct writes to the triple-write
layers, the description shape, and the evals for negative cases. It exits
non-zero if a BLOCKER fired.

A PASS is necessary, not sufficient. It cannot tell you the skill fires on the
right things: only the evals and real use do that.

## Step 8: hand off

Report the files you wrote, the confirmed contract table, and the audit result.
Then tell the scientist the two things only they can do:

1. **Use it on a real task** and watch whether it fires. Trigger tuning is
   empirical. If it misfires, the fix is almost always in the description's
   quoted phrases or its anti-triggers, not in the body.
2. **Add the `.gitignore` negation** if it should be versioned with the repo.

Never use em dashes. Never do the scientist's thinking: if the graph contract has
a genuinely open question, ask it rather than picking for them and writing it
down as though it were settled.
