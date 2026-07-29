# integrations/llmsr/ -- LLM-SR equation discovery (a plug-in, not a Wheeler method)

This subtree drives **LLM-SR** (Shojaee et al., ICLR 2025, building on
DeepMind's FunSearch) from Claude Code and lands the result in the knowledge
graph with provenance. The method is upstream's; read
`vendor/NOTICE.md` before touching anything here, and cite their papers, not
Wheeler, if you publish.

It is shaped like every other Wheeler integration (act shapes the request, tool
runs, one deterministic marshal-out writes the graph), with one difference that
explains most of the code: **there is no external service to call.** Wheeler
runs on a Max subscription with no API key, so upstream's sampler and its
orchestration loop cannot be used as shipped. Instead the evolutionary loop is
INVERTED into four CLI verbs, and Claude Code steps it:

```
wheeler llmsr init   --spec S --data D --metric M [--group-by COL]  -> run dir
wheeler llmsr prompt --run R      -> the next prompt (from the vendored buffer)
   ... the ACT generates a candidate body with a sub-agent (no API key) ...
wheeler llmsr submit --run R --body-file B --island-id I --version-generated V
wheeler llmsr best   --run R [--select fit|ood|parsimony]  -> best.json
wheeler integrate ingest llmsr-discover best.json ...      -> the graph
```

State persists by replaying `submissions.jsonl` through the vendored
`register_program` on every call. No pickles, no daemon, no resident process.

## Modules

- `cli.py` -- the `llmsr_app` Typer sub-app: `init`, `prompt`, `submit`, `best`,
  plus `status` (a safe mid-run ping) and `metrics` (the truthful list of what
  is registered right now, computed at call time). The CLI NEVER calls a model:
  generation happens in the act. `_metric_for` is the one place a metric name is
  resolved, and it imports the scientist's metric modules first.
- `runs.py` -- on-disk run state under `.wheeler/llmsr/runs/<run_id>`:
  `meta.json` (what the run is bound to), `submissions.jsonl` (append-only, every
  candidate in order), `heartbeat.json` (written AFTER a fit: what the search has
  achieved), `progress.json` (written DURING a fit: where that fit has got to).
  The two status files are deliberately separate, because only the second can
  answer "is it wedged?" for a submit that refits forty groups in silence.
- `data.py` -- reads the training table in the shape its metric declares. The
  tabular convention is upstream's (last column is the target). What varies is
  whether a column NAMES THE GROUP each row belongs to (excluded from the inputs,
  read as text so a label like `c01` is not NaN) and whether the target is one
  value per row (`regression`) or a padded column of recorded event times.
- `metrics.py` -- the metric registry. `mse` and `nmse` ship built in; a
  scientist registers their own from `$WHEELER_LLMSR_METRICS` or
  `.wheeler/llmsr/metrics.py` WITHOUT editing the installed package. A metric
  declares its `data_shape` (the fit path dispatches on it) and may declare hard
  `Constraint`s, which reject a candidate whatever it scored.
- `fit.py` -- the fit/score seam: exec the program, read the `equation`
  callable, fit its free constants by minimizing `metric.loss`, report
  `metric.report`. Runs in a forked, timeout-bounded child (the body is
  model-generated code). **This is the substitution that is not upstream's**: see
  the invariant below.
- `selection.py` -- picking the winner and reporting how it generalizes.
  `fit` (lowest training error), `ood` (best extrapolation), `parsimony`
  (simplest form among those that fit comparably, Occam). Also `_split_metrics`
  (train / test_id / test_ood scoring, WHEELER'S addition, see below) and
  `_runnable_program` (the footer that turns the winner into a `.py` that
  reproduces the answer).
- `discover.py` -- the marshal-out ingest (`parse_discover` + `ingest_discover`).
  Reads `best.json`, writes the graph via `execute_tool` (lazy, function-local,
  the only graph writer here), reusing `asta/_marshal.py`'s shared helpers.
- `vendor/` -- six modules adapted from upstream (`buffer.py`,
  `code_manipulation.py`, `config.py`, `evaluator.py`, `evaluator_accelerate.py`,
  `profile.py`) plus both licences and `NOTICE.md`. **Do not fork this code.**
  Only `NOTICE.md` (prose) is edited here.

## Invariants

- **The scoring seam is a SUBSTITUTION, and the attribution must say so.** A spec
  declares an `@evaluate.run` that fits the candidate's constants and returns its
  score, and upstream's loop calls it. The driver does not: it parses the name
  into `meta["function_to_run"]` and never calls it, scoring every candidate
  through `fit.py` + `metrics.py` instead. That is what makes the metric
  pluggable, the constants recoverable for `best.json`, and per-group refitting
  possible. The search algorithm, the island model, and the program-manipulation
  logic ARE upstream's, unaltered. Any wording that claims "the scoring is
  theirs, untouched" is false: it is corrected in `vendor/NOTICE.md` and the root
  `README.md`. PLANNED (issue #107, slice S4): make the spec's `@evaluate.run`
  selectable, so the substitution becomes a choice rather than an imposition.
- **Held-out ID/OOD scoring is WHEELER'S, not the paper's protocol.** The LLM-SR
  datasets ship `<problem>/{train,test_id,test_ood}.csv`, but upstream's own
  `main.py` loads only `train.csv` and nothing in its pipeline opens the test
  splits. Wheeler applies the train-fitted constants to the siblings when they
  exist. Do not re-describe this as upstream's protocol.
- **One FORM, one theta per group.** A run may declare `--group-by COL`, and then
  every group refits its OWN constants under the SAME form. This is not a
  convenience: symbolic regression is looking for the FORM, and a single pooled
  fit charges the form for variation that belongs to the PARAMETERS, rejecting a
  correct law. The per-group score VECTOR is the primary object and is what
  reaches the vendored buffer (`_reduce_score` ranks islands, `_get_signature`
  clusters forms by their per-group profile). An ungrouped run is the one-group
  case and is bit-for-bit unchanged. See `docs/llmsr-objective-formulation.md`.
- **A grouped run's answer is the TABLE, everywhere.** `params` is EMPTY by
  construction whenever there is more than one group, so anything that reads it
  alone records nothing. `best.json` carries `params_per_group` /
  `value_per_group`; the written `.py` emits `FITTED_PARAMS_PER_GROUP` plus a
  `__main__` that filters rows by group and applies that group's own constants
  (mirroring `data.py::_load_xy`, group column excluded from the inputs, labels
  read as text); the Script node carries `custom_params_per_group`,
  `custom_group_by`, `custom_n_groups`, and `custom_groups`. The artifact is
  advertised as durable and re-runnable, so its grouped form must actually run:
  `tests/integrations/llmsr/` EXECUTES it rather than inspecting its text.
- **Every metric Finding is labelled by REGIME.** `custom_regime` is `scored`
  (the search optimized against this data), `held_out` (it did not), or `unknown`
  (the artifact does not record enough to tell), with `custom_regime_reason`
  spelling out why. Two things count as optimizing against data: FITTING the
  constants (train) and CHOOSING THE WINNER (`--select ood` ranks candidates by
  their `test_ood` error, so under that mode the OOD split is a selection set).
  This is a scientific guardrail, not bookkeeping: forty rounds scored on a
  dataset makes that number a training number however good it looks, and the
  graph must never present it as a generalization claim. Where the regime cannot
  be determined, say `unknown` rather than picking the flattering answer.
- **A grouped run's scalar is a MEAN, and travels labelled as one.** A grouped
  run reports no scalar in `metrics` (held-out scoring is skipped for it, since
  applying one group's constants to a held-out file needs a policy for absent
  groups, deferred with the rest of the Objective work). The ingest derives the
  mean over `value_per_group`, which is exactly what `fit.py` aggregates to, and
  stamps `custom_value_is_group_mean`.
- **One Execution per RUN, with a truthful status.** Service tag
  `llmsr:discover`, `session_id` = the run id, so a re-ingest reuses it. The
  external-call failsafe applies unchanged: a non-`completed` `best.json`, or a
  completed one with no parseable equation, records a FAILED Execution plus the
  raw artifact and fabricates no Script or Finding. Provenance is two-sided off
  that one Execution (`output -[WAS_GENERATED_BY]-> Execution -[USED]-> input`).
  Idempotent throughout: Execution on `(service, session_id)`, Script on file
  hash via `ensure_artifact`, Finding on a deterministic id (which now includes
  the SPLIT, with `train` as the historic default so existing ids still resolve),
  every edge through `link_once`.
- **The parser never raises.** A shape-drifted or partial `best.json` counts and
  skips; ingest is never aborted by a missing piece.
- **Sequential writes only.** Never `asyncio.gather`: Neo4j forbids concurrent
  queries in one session.
- **The metric port reads the registry.** The `llmsr-discover` contract in
  `services.default.yaml` points its `metric` port at
  `wheeler.integrations.llmsr.metrics:available` via `options_from`, so a
  registered metric is offerable by the interview instead of being invisible
  behind a hardcoded `[nmse, mse]`. Resolution is lazy and falls back to the
  static list on any failure. CAVEAT: `available()` reports what is registered in
  the CALLING process and does not itself import the userland sources, so a
  caller that has not run `load_user_metrics()` still sees only the built-ins.
  Making `available()` load first is the natural follow-up (issue #107).

## Conventions

- `from __future__ import annotations`; `logging.getLogger(__name__)`; async only
  where graph I/O happens (`discover.py`).
- `execute_tool` is imported lazily, function-local, in `discover.py` only. Same
  rule as the Asta adapters and `validation/ledger.py`.
- Add no LLM-provider SDK, and never an API key path. Generation is the act's job.
- Never use em dashes. Use colons, commas, periods, parentheses.
- Tests live in `tests/integrations/llmsr/`, whose `conftest.py` gives every test
  a scratch cwd and restores the process-wide metric registry. Do not hand-copy
  it into a new test file: it is autouse for the whole directory.
