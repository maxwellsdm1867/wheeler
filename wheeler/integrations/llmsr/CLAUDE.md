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
wheeler llmsr scaffold-spec --data D [--recipe R]  -> a filled spec + its command
wheeler llmsr init   --spec S --data D... --metric M [--group-by COL]
                     [--seed-from NAME] [--score-on NAMES] [--loader K]
                     [--optimizer K] [--use-spec-evaluate]
                     [--islands N] [--reset-every N] [--reset-period S]
                     [--cluster-tolerance F]                         -> run dir
wheeler llmsr prompt --run R      -> the next prompt (from the vendored buffer),
                                     plus samples_per_prompt (upstream's 4)
   ... the ACT generates that many candidate bodies from that ONE prompt ...
wheeler llmsr submit --run R --body-file B --island-id I --version-generated V
   ... once per body, same I and V, sequentially: one writer only ...
wheeler llmsr best   --run R [--select fit|ood|parsimony]  -> best.json
wheeler integrate ingest discover best.json ...            -> the graph
```

Plus one verb outside that loop: `transfer --run R --data HELD_OUT.csv` refits the
discovered FORM on data the search never saw and writes `transfer.json`. It reads
the run and writes nothing back into it (see the holdout invariant below). Its
result reaches the graph through its own marshal-out and its own act:

```
wheeler llmsr transfer --run R --data HELD_OUT.csv [--group-by COL]  -> transfer.json
wheeler integrate ingest transfer transfer.json ...                  -> the graph
```

Plus four listings, all computed at call time so they are truthful about open
registries: `metrics`, `loaders`, `optimizers`, `recipes`, and `specs` for what
ships.

State persists by replaying `submissions.jsonl` through the vendored
`register_program` on every call. No pickles, no daemon, no resident process.

## Modules

- `cli.py` -- the `llmsr_app` Typer sub-app: `init`, `prompt`, `submit`, `best`,
  plus `status` (a safe mid-run ping) and `metrics` (the truthful list of what
  is registered right now, computed at call time). The CLI NEVER calls a model:
  generation happens in the act. `_metric_for` is the one place a metric name is
  resolved, and it imports the scientist's metric modules first.
- `runs.py` -- on-disk run state under `.wheeler/llmsr/runs/<run_id>`, plus
  `scored_metric` / `scored_metric_report`, the one place the question "what
  quantity are this run's own numbers in" is answered (see the spec-door
  invariant below):
  `meta.json` (what the run is bound to), `submissions.jsonl` (append-only, every
  candidate in order), `heartbeat.json` (written AFTER a fit: what the search has
  achieved), `progress.json` (written DURING a fit: where that fit has got to).
  The two status files are deliberately separate, because only the second can
  answer "is it wedged?" for a submit that refits forty groups in silence.
- `data.py` -- reads a run's training tables in the shape its metric declares,
  and NAMES them. The tabular convention is upstream's (last column is the
  target). What varies is whether a column NAMES THE GROUP each row belongs to
  (excluded from the inputs, read as text so a label like `c01` is not NaN) and
  whether the target is one value per row (`regression`) or a padded column of
  recorded event times. It also owns the dataset vocabulary: `parse_datasets`
  (`--data path` or `--data NAME=path`), the `--seed-from` / `--score-on` role
  split, `key_scheme` / `score_key` (how a unit is named in the score vector),
  and `load_units`, which composes with the loader registry rather than around
  it.
- `metrics.py` -- the metric registry. `mse` and `nmse` ship built in; a
  scientist registers their own from `$WHEELER_LLMSR_METRICS` or
  `.wheeler/llmsr/metrics.py` WITHOUT editing the installed package. A metric
  declares its `data_shape` (the fit path dispatches on it) and may declare hard
  `Constraint`s, which reject a candidate whatever it scored.
- `fit.py` -- the DEFAULT fit/score seam: exec the program, read the `equation`
  callable, fit its free constants by minimizing `metric.loss`, report
  `metric.report`. Runs in a forked, timeout-bounded child (the body is
  model-generated code). **This is the substitution that is not upstream's**: see
  the invariant below. `_run_sandboxed` is that child, and it is the ONE sandbox
  both scoring doors share.
- `spec_eval.py` -- the OTHER door: call the spec's own `@evaluate.run`, which is
  what upstream does. Selected per run by `--use-spec-evaluate`, never sniffed.
  Called once per (dataset, group) unit inside `fit._run_sandboxed`, and
  normalized into the same `FitResult` so nothing downstream can tell which door
  produced it except by reading `optimizer.scored_by`.
- `selection.py` -- picking the winner and reporting how it generalizes.
  `fit` (lowest training error), `ood` (best extrapolation), `parsimony`
  (simplest form among those that fit comparably, Occam). Also `_split_metrics`
  (train / test_id / test_ood scoring, WHEELER'S addition, see below),
  `_source_theta` (which source constants may legitimately be applied to which
  group) and `_runnable_program`, which dispatches to one of four footers by the
  shape of the answer: `_no_constants_footer` (a bare-float spec-evaluate winner,
  nothing to run), `_multidata_footer` (keys spanning files), `_grouped_footer`
  (one file, several groups) and the flat one.
- `transfer.py` -- the on-demand generalization test behind `wheeler llmsr
  transfer`. Same two quantities as `_split_metrics`, against any file rather
  than the sibling splits, written to `transfer.json`. It carries the source
  run's `scored_metric` block (from `runs.scored_metric_report`, present only on
  the spec door) so the ingest can say whose machinery produced its numbers.
- `transfer_ingest.py` -- the marshal-out ingest for `transfer.json`
  (`parse_transfer` + `ingest_transfer`), the answer to "does the FORM
  generalize" landing in the graph. Same layer as `discover.py` (config +
  `asta/_marshal.py`, `execute_tool` lazy and function-local) and it imports
  discover's REGIME / CLAIM / MEASURED_BY vocabulary and `_finding_id` rather
  than restating them. Deliberately NOT inside `transfer.py`: that module
  imports the scoring machinery (`fit`, `runs`, `selection`) and says in its own
  header that it duplicates the regime literals because it is not the graph
  writer. Writes TWO Findings per transfer, never one (see the invariant below).
- `recipes.py` -- the worked `evaluate` recipes and the scaffolder behind
  `wheeler llmsr scaffold-spec`. A recipe is a spec TEMPLATE under
  `wheeler/_data/llmsr/recipes/<key>.txt` plus the flag combination it pairs with
  (`Recipe.cli`, the ONE source the cookbook quotes, the scaffolder prints and
  the test runs). Also the registry of bundled specs and their synthetic demo
  tables. The registry here is deliberately CLOSED, unlike metrics / loaders /
  optimizers: extending a recipe means editing the spec it just wrote.
- `discover.py` -- the marshal-out ingest (`parse_discover` + `ingest_discover`).
  Reads `best.json`, writes the graph via `execute_tool` (lazy, function-local;
  one of the two graph writers here, the other being `transfer_ingest.py`),
  reusing `asta/_marshal.py`'s shared helpers. It
  owns the REGIME / CLAIM / MEASURED_BY vocabulary every number in the graph is
  labelled with (`transfer.py`, `transfer_ingest.py` and
  `cli.py::_dataset_report` read it from here),
  the per-unit constant table, and the input Datasets.
- `vendor/` -- six modules adapted from upstream (`buffer.py`,
  `code_manipulation.py`, `config.py`, `evaluator.py`, `evaluator_accelerate.py`,
  `profile.py`) plus both licences and `NOTICE.md`. **Do not fork this code.**
  Only `NOTICE.md` (prose) is edited here.

## Invariants

- **The scoring seam is a SUBSTITUTION BY DEFAULT and a CHOICE by flag, and the
  attribution must say so.** A spec declares an `@evaluate.run` that fits the
  candidate's constants and returns its score, and upstream's loop calls it. The
  default driver does not: it parses the name into `meta["function_to_run"]` and
  never calls it, scoring every candidate through `fit.py` + `metrics.py`
  instead. That is what makes the metric pluggable, the constants recoverable for
  `best.json`, and per-group refitting possible, so it stays the default. A run
  created with `--use-spec-evaluate` takes the other door (`spec_eval.py`) and
  the spec's own `evaluate` scores every candidate, owning the loss, the
  optimizer, and whatever it imports. The search algorithm, the island model, and
  the program-manipulation logic ARE upstream's, unaltered. Any wording that
  claims "the scoring is theirs, untouched" is still false, and any wording that
  claims the substitution is unconditional is now false too: both are corrected
  in `vendor/NOTICE.md` and the root `README.md`.
- **The scoring door is chosen by FLAG, never by sniffing, and is fixed at
  `init`.** Nothing inspects the body of `evaluate` to guess whether it looks
  stock. Detection would silently change how a run is scored when somebody edited
  a comment inside it, and a scoring change nobody asked for is the exact failure
  this engine exists to remove. The choice is recorded in `meta.json`
  (`use_spec_evaluate`) and read back for every later verb, for the same reason
  the key scheme is: two candidates scored through different doors are not
  comparable, and the buffer would never say so. A run dir written before the
  door existed answers False, which is the substitution Wheeler has always done.
- **Through the spec door, the call is PER UNIT and the keys are still the
  run's.** `evaluate` is called once per (dataset, group) pair with that pair's
  rows, not once per candidate: calling it once would throw away the per-unit
  refit that the whole per-group protocol exists for. Data arrives in UPSTREAM'S
  shape (`data['inputs']`, `data['outputs']`) so an upstream spec runs unmodified,
  plus `data['groups']` when the run declares `--group-by`. Score keys come from
  `data.score_key` and never from the spec: a returned `per_group` may name only
  the unit the call covered, and naming anything else is a loud error, because a
  candidate that invented its own keys would silently break the vendored buffer's
  signature clustering. The return contract is additive over upstream's: a bare
  `int`/`float` is exactly upstream's (`isinstance(results, (int, float))` in
  `vendor/evaluator.py`) and is the maximize-me score, while a dict
  `{"score", "params", "per_group"}` also carries the constants upstream discards
  (every upstream spec computes `optimized_params = result.x` and throws it away).
  Anything else is an INVALID candidate with a truthful error, never a fabricated
  score. Both doors normalize into the same `FitResult`, so `submit`, `best`,
  `transfer`, selection and `discover.py` are unchanged downstream.
- **Through the spec door the run's numbers are NOT the declared metric, and are
  never named as if they were.** The spec owns its loss and never reports what it
  computed, and NOTHING checks that it equals `--metric`: every bundled recipe and
  every upstream spec minimizes mean squared error whatever the run declared. So
  a run has a SCORED metric distinct from its DECLARED one (`runs.scored_metric`:
  `spec:<function_to_run>` on that door, the declared key on the default door),
  and every number carries the name of what produced it.
  - `best.json` gains a `scored_metric` block (name / declared / measured_by /
    note), present exactly when the two differ, so a default-door run is the file
    it always was. `metrics` and `metrics_refit` stay in the DECLARED metric on
    both doors, because `fit.py` computed them.
  - the emitted `.py`'s `METRIC` is built from the SCORED name, with
    `declared_metric` beside it and a comment, in all four footers.
  - `status` gains `best_value_metric`; `best` and `init` echo `value_metric` /
    `seed_value_metric`. Only when the names differ.
  - the marshal-out reads the block off the artifact (`discover._scored_metric`,
    never reconstructed) and labels the derived train Finding with it. That path
    is every grouped and every multi-dataset run, which is exactly the shape the
    per-group protocol exists for.
  This invariant previously said the opposite for half the seam: that a mean
  derived from the spec's own per-unit vector is "the run's own objective and is
  labelled `spec-evaluate` with no caveat". True of the QUANTITY, false of its
  NAME, and that is how a stock recipe's MSE reached `best.json`, the emitted
  `.py`, `status` and the graph labelled `nmse`, 19x away from the real one.
- **What the spec door does NOT reach.** Held-out split scoring (`_split_metrics`,
  `transfer.py`) still runs through `fit.py`, under the run's DECLARED metric, so
  under `--use-spec-evaluate` those numbers are a second opinion computed by
  different machinery than the search used, not the run's own objective measured
  again. `best.json` says which door scored the run in `optimizer.scored_by`, and
  the marshal-out reads it: every Finding carries `custom_measured_by`
  (`wheeler-fit` or `spec-evaluate`) and `custom_measurement_note`. BOTH sides of
  the seam get a note (`_RunContext.note_for`), because neither is the plain
  thing: `_SECOND_OPINION_NOTE` for a number the fit seam measured in a run the
  spec scored, `_SPEC_OBJECTIVE_NOTE` for a number the spec produced. A
  default-door run has one piece of machinery and still gets no note at all.
  Where the spec returned no constants at all (upstream's bare float),
  `selection._no_constants_footer` writes the score and refuses to emit a runner,
  because there is genuinely nothing to run.
  **`transfer` is on the same side of that seam and now says so.** It refits
  through `fit.py` under the DECLARED metric whatever scored the search, so on a
  spec-door run BOTH of its numbers are a second opinion. `transfer.json`
  therefore carries the same `scored_metric` block `best.json` does (from
  `runs.scored_metric_report`, present exactly when the two names differ, absent
  on a default-door run so that file is what it always was), and
  `transfer_ingest.py` reads it: both Findings get `custom_measured_by=wheeler-fit`
  plus `_SECOND_OPINION_NOTE`, and `custom_source_scored_metric` names what the
  SEARCH was scored on so nobody compares a transfer number against a `best.json`
  headline that is a different quantity. The block is never reconstructed here,
  for the same reason `discover._scored_metric` reads it off the artifact: only
  the RUN knows how it was scored.
- **Which constant SHAPE a run has is a property of its UNITS, not of its
  constants.** `discover._is_multi` / `_is_grouped` ask `value_per_key` /
  `value_per_group` as well as the constant tables, because upstream's bare-float
  return hands back no constants at all. Reading the shape off the constants
  alone filed every grouped or multi-dataset bare-float run under the FLAT arm:
  a three-cell discovery landed as `custom_params "[]"` with no `group_by`, no
  `n_groups` and no per-group values, presented as one pooled fit. A run that
  genuinely has no constants records that (`custom_no_constants` +
  `custom_no_constants_reason`), because "none were returned" and "they are
  missing from the graph" look identical to a reader and are not the same fact.
  `selection._no_constants_footer` already handled this case at length; the graph
  writer now does too.
- **Held-out ID/OOD scoring is WHEELER'S, not the paper's protocol.** The LLM-SR
  datasets ship `<problem>/{train,test_id,test_ood}.csv`, but upstream's own
  `main.py` loads only `train.csv` and nothing in its pipeline opens the test
  splits. Wheeler scores the siblings when they exist, both by applying the
  train-fitted constants and by refitting them. Do not re-describe this as
  upstream's protocol.
- **One FORM, one theta per group.** A run may declare `--group-by COL`, and then
  every group refits its OWN constants under the SAME form. This is not a
  convenience: symbolic regression is looking for the FORM, and a single pooled
  fit charges the form for variation that belongs to the PARAMETERS, rejecting a
  correct law. The per-group score VECTOR is the primary object and is what
  reaches the vendored buffer (`_reduce_score` ranks islands, `_get_signature`
  clusters forms by their per-group profile). An ungrouped run is the one-group
  case and is bit-for-bit unchanged. See `docs/llmsr-objective-formulation.md`.
- **A run may bind SEVERAL datasets, and the unit of fitting is the (dataset,
  group) pair.** `--data` is repeatable and nameable (`--data B=cellB.csv`).
  `--seed-from` says which table shapes the prompt (where the FORM comes from);
  `--score-on` says which tables enter the objective (what it is judged on).
  Keeping the two roles apart is the point: a form extracted from one cell and
  then REFITTED on cells it never saw is a test of the FORM, not of one lucky
  parameterization, and that is fair precisely because the same law is assumed
  across cells and only the constants differ. This is upstream's shape restored,
  not an invention: `vendor/evaluator.py` loops `self._inputs` and builds
  `scores_per_test` per named input; Wheeler had collapsed it to one hardcoded
  key.
- **The score-key SCHEME is fixed at `init` and recorded in `meta.json`.** Two
  candidates in one run must present the vendored buffer with identical keys, so
  the scheme is decided once (`data.key_scheme`) and read back off the run
  forever after, never re-derived from a later command line. `scheme=group`
  means the key is the bare group label (`data` ungrouped, `c01` grouped) and is
  used for exactly one shape: a single scored dataset carrying the default name,
  which is precisely the run an older Wheeler could have created. `scheme=dataset`
  means the key names the dataset (`A`) and the group too (`A:c01`). **An unnamed
  single `--data` is byte-for-byte what it was**, and this is not politeness:
  `buffer._get_signature` clusters candidates on the sorted score signature and
  `_reduce_score` means over the keys in insertion order, so a changed key SET
  would silently invalidate the buffer state of every run already on disk without
  raising anything. `tests/integrations/llmsr/parity_singledata.py` is the gate,
  comparing a whole `init` -> `prompt` -> `submit` -> `best` walk against a golden
  captured from the pre-change code. Regenerate it per its docstring; never
  delete it. (`meta.json` may GAIN keys, since the scheme has to be recorded
  there; `submissions.jsonl` and `best.json` may not change at all.)
- **`best.json` labels every dataset by REGIME.** A multi-dataset run carries a
  `datasets` block whose entries are `scored` (the search refitted constants on
  it and ranked candidates by the result) or `held_out` (it did neither), reusing
  `discover.py`'s vocabulary rather than a parallel one. A split that scores the
  search is NOT a holdout: 40 rounds scored on B means the search optimized
  against B. A dataset that only ever seeded the prompt is held out by that rule
  and says so in `regime_reason`, carrying `seed: true`, because the generator
  did see it even though the search never scored it. Held-out entries carry no
  value: computing one means refitting the winner on data the run never touched,
  which is a separate act with its own provenance (`wheeler llmsr transfer`), not
  a footnote on this one. The block is ABSENT on a single-default-dataset run, so
  existing readers see the file they always saw.
- **A multi-file run gets a runner that ADDRESSES its units, or none at all.**
  The other two footers address ONE file: the flat one applies a single parameter
  vector to `data_path`, the grouped one filters that file's rows by a group
  column. Neither can address a run whose score keys span several tables. The
  flat branch would write `FITTED_PARAMS = []` and raise; the grouped branch
  would match keys like `A:c01` against one file's cell labels and report zero
  rows for EVERY group without failing. The second is why this matters: a silent
  wrong answer is worse than no answer, and it is exactly what the per-group
  protocol exists to prevent. So `_runnable_program` takes `dataset_report` and
  emits `_multidata_footer`: `SCORED_DATASETS`, `HELD_OUT_DATASETS`, `GROUP_BY`,
  `FITTED_PARAMS_PER_KEY` (keys are `dataset` or `dataset:group`), `METRIC`, and
  a `__main__` that loops the scored FILES and the groups within them, applying
  each unit's own constants to that unit's own rows (the row filter mirrors
  `_grouped_footer`, which mirrors `data.py::_load_xy`). It refuses in exactly
  the two cases where the file and the key set have come apart: a unit in the
  data with no constants (never fitted with a neighbour's theta) and a key no row
  matched. Both are printed, named, and exit non-zero. HELD-OUT datasets are
  listed and deliberately not run: the search fitted no constants on them, so
  refitting the form there is `wheeler llmsr transfer`, a separate act with its
  own provenance. The branch is checked only when `cli.py` passes a report, so a
  single-table run (ungrouped or grouped) reaches the footer it always reached,
  byte for byte. `tests/integrations/llmsr/test_runnable_program.py::TestFourShapesRun`
  EXECUTES all four shapes and checks the printed numbers against the file.
- **A multi-unit run's answer is the TABLE, everywhere.** `params` is EMPTY by
  construction whenever there is more than one fittable unit, whether that is
  several groups in one table or several datasets or both, so anything that reads
  it alone records nothing. `best.json` carries `params_per_group` /
  `value_per_group` (grouped) and `datasets.entries[*].params_per_key` (multi
  dataset); the written `.py` emits `FITTED_PARAMS_PER_GROUP` or
  `FITTED_PARAMS_PER_KEY` plus a `__main__` that applies each unit's own
  constants to that unit's own rows; the Script node carries exactly ONE of the
  three shapes, never two (`custom_params_per_key` + `custom_keys` +
  `custom_n_keys` + `custom_datasets_scored` / `custom_datasets_held_out` for a
  multi-dataset run, `custom_params_per_group` + `custom_group_by` +
  `custom_n_groups` + `custom_groups` for a grouped single table, `custom_params`
  only for a genuine one-unit run). Writing two of them would put the same
  numbers in the graph twice under names that invite a reader to compare them.
  The scalar is the mean over UNITS, which is what `fit.py` aggregates to
  (`sum(per_group_value) / len(per_group_value)`), derived over the SCORED
  entries only and stamped `custom_value_is_unit_mean` (or
  `custom_value_is_group_mean` one level down). The artifact is advertised as
  durable and re-runnable, so it must actually run: `tests/integrations/llmsr/`
  EXECUTES all four shapes rather than inspecting their text.
- **A run's input tables land as Dataset nodes on the USED side.** A
  multi-dataset run fitted constants on several tables, and each is an input the
  run genuinely read, so `discover._record_datasets` registers every DECLARED
  entry via `ensure_artifact` (deduped on path, so a Dataset the act already
  passed in `--used` is the same node) and links `Execution -[USED]-> Dataset`
  through `link_once`. They are inputs, so they are never in `produced_ids` and
  never `WAS_GENERATED_BY` the run, on the same rule that keeps reference-entity
  Papers off that edge. Held-out and seed-only tables land too, each carrying
  `custom_regime` / `custom_regime_reason` / `custom_seeded_the_prompt`: which
  tables a form was NOT fitted on is the more interesting half of the question,
  and only the run knows. A table whose file has moved is counted and skipped,
  never fatal. The block is absent on a single-default-dataset run, so that run
  lands exactly the nodes it always did.
- **Every metric Finding is labelled by REGIME, by CLAIM, and by what MEASURED
  it.** `custom_regime` is `scored` (the search optimized against this data),
  `held_out` (it did not), `held_out_form` (it did not, but the constants were
  REFITTED on the split being reported, so the number is held out for the FORM
  only) or `unknown` (the artifact does not record enough to tell), with
  `custom_regime_reason` spelling out why. Two things count as optimizing against
  data: FITTING the constants (train) and CHOOSING THE WINNER (`--select ood`
  ranks candidates by their `test_ood` error, so under that mode the OOD split is
  a selection set). `custom_claim` is `constants` or `form`, matching
  `transfer.py`, and it is part of the Finding id so the two numbers on one split
  are two nodes and never collide (`constants` is the historic default, so ids
  minted before the refit numbers were ingested still resolve). This is a
  scientific guardrail, not bookkeeping: forty rounds scored on a dataset makes
  that number a training number however good it looks, and the graph must never
  present it as a generalization claim. Where the regime cannot be determined,
  say `unknown` rather than picking the flattering answer.
- **"Does it generalize" is TWO questions, and they travel separately.** Applying
  the winner's constants unchanged to new data asks whether the CONSTANTS
  transfer. Refitting them from scratch under the same form asks whether the FORM
  transfers, which is the question symbolic regression is actually asking: a law
  that governs a new cell with different constants is the SAME law. `best.json`
  carries them in two dicts, `metrics` (fixed theta, the historic keys, unchanged
  number for number on an ungrouped run) and `metrics_refit`, and `transfer.json`
  carries them as two blocks each stamped with its `claim` (`constants` or
  `form`). Neither is ever derived from the other and neither stands in for the
  other. The refit's regime is its OWN label, `held_out_form`, not `held_out`
  with a longer reason, because a refit fitted its constants on the split it
  reports: `discover._refit_regime` and `transfer._refit_regime` apply the same
  rule with the same wording, and `test_transfer.py` asserts the two modules'
  vocabularies are equal. This is why the refit numbers never rode into `metrics`
  under a suffix: `_split_key` would have mislabelled them, and the regime
  labeller would have called them clean held-out numbers.
  **They travel separately all the way into the graph.** `transfer_ingest.py`
  writes TWO Findings per transfer and they must never collapse into one: the
  refit one carries `custom_claim=form` and regime `held_out_form`, the
  fixed-theta one `custom_claim=constants` and regime `held_out` proper. The ids
  differ by construction (`discover._finding_id` keys on the CLAIM), and the
  split token names the TRANSFER (`transfer:<digest>`) rather than one of the
  run's sibling splits, so neither can collide with the other nor with a Finding
  from the discovery run it came from. Both numbers and the labelled
  `refit_over_fixed` ratio ride on BOTH nodes, because a reader who lands on one
  Finding and sees a single number takes it for the answer to both questions,
  which is the failure this verb exists to prevent. A WITHHELD fixed-theta number
  still gets its Finding, carrying the `error` and `source_per_group` that say
  which group had no legitimate source vector: leaving it out would make an
  unanswerable question look like one nobody asked. No verdict is written
  anywhere, by the module or by the act: whether the two numbers are close enough
  is the scientist's call, exactly as `transfer._comparison` already declines to
  rank them.
- **A fixed-theta number is reported only where a source vector BELONGS.**
  `selection._source_theta` allows exactly two cases: the source fitted this same
  group (use its own constants) or the source has a single constant vector (what
  an ungrouped run's constants are). A grouped source with no vector for this
  group reports nothing, and `_strict_mean` then withholds the aggregate rather
  than averaging the groups that happened to work. Substituting another group's
  theta would answer a different question dressed as this one. This policy is
  what the old "held-out scoring is skipped for a grouped run" deferral was
  waiting on, and `_split_metrics` no longer returns `{}` for a grouped run.
- **`--select ood` ranks on FIXED THETA, under the run's own metric.** Fixed theta
  by design and not by omission: refitting on the OOD split before ranking would
  reward flexibility, which is precisely what OOD selection exists to punish (a
  nine-term polynomial refitted on the extrapolation region fits it; the signal
  is that its TRAIN-fitted constants diverge there). The metric is the run's,
  always: it used to be hardcoded to NMSE for any regression run, which ranked a
  run whose declared objective was a registered custom metric on a quantity it
  never chose. Ranking goes through `metric.score_from_value`, so a metric
  declaring `lower_is_better=False` is not ranked backwards. `best.json` names
  the ranked quantity in `selection.ranked_on`.
- **`--select parsimony`'s comparability band is a factor on the MAGNITUDE of the
  best pseudo-error, computed DIRECTION-FREE.** The band admits candidates within
  `_PARSIMONY_TOL` of the best and then picks the shortest, so if the band is
  wrong Occam does not weaken, it INVERTS. `selection._comparability_threshold`
  takes `best_err = -score`, which is minimize-me whichever direction the metric
  declares, and branches on the SIGN of that number rather than on
  `lower_is_better`: a lower-is-better metric whose value can go negative (a
  log-likelihood-shaped loss) inverts identically, and nothing in its declaration
  warns you. A nonnegative error keeps the historic `best_err * _PARSIMONY_TOL`
  bit for bit, so an MSE / NMSE run's threshold does not move. Measured on the
  defect: an R2 metric (`lower_is_better=False`) with R2 0.99 at complexity 1
  against 0.995 at complexity 4 gave `best_err = -0.994999999999999` and a
  threshold of -0.994999999998999, which admitted 1 of 2 candidates and the
  admitted one was the COMPLEX form, so `--select parsimony` silently returned the
  fit-ranked answer.
  The floor is the other half, and it changes what the OLD behaviour actually was:
  `max(widened, best_err + 1e-12)` is an ABSOLUTE epsilon, so at large magnitudes
  it cannot move at all (`-1e6 + 1e-12 == -1e6` in float64, while `1.0 + 1e-12`
  does move). The band then excluded even the best candidate and the `or valid`
  fallback at `selection.py:626` admitted EVERYTHING. So parsimony worked by
  accident at large magnitudes and failed at small ones, which is why no existing
  test caught it. Post-fix the widening always moves for a nonzero best, and a
  best of exactly 0.0 still degrades parsimony to fit by design: with a
  zero-magnitude reference there is no "comparably well" to compute.
- **A grouped run's scalar is a MEAN, and travels labelled as one.** A grouped
  run reports no `train` entry in `metrics`: its train answer is the per-group
  value TABLE (`value_per_group`), and the ingest derives the mean over it, which
  is exactly what `fit.py` aggregates to, and stamps
  `custom_value_is_group_mean`. Writing a pooled `<metric>_train` beside it would
  put an unlabelled duplicate where the labelled one is. Held-out splits DO
  appear for a grouped run, per group, both ways.
- **A holdout that fed back into the search would stop being a holdout.**
  `transfer` reads `submissions.jsonl` and never appends to it, and never
  registers into the experience buffer. It writes `transfer.json`, refreshes
  S0b's `progress.json` while the refit runs, and refreshes `heartbeat.json`
  once at the end (only so `status` does not report a phantom `fitting` forever
  after: `_phase` reads an un-overtaken progress ping as a fit in flight). It
  never writes `best.json`.
- **One Execution per RUN, with a truthful status.** Service tag
  `llmsr:discover`, `session_id` = the run id, so a re-ingest reuses it. The
  external-call failsafe applies unchanged: a non-`completed` `best.json`, or a
  completed one with no parseable equation, records a FAILED Execution plus the
  raw artifact and fabricates no Script or Finding. Provenance is two-sided off
  that one Execution (`output -[WAS_GENERATED_BY]-> Execution -[USED]-> input`).
  Idempotent throughout: Execution on `(service, session_id)`, Script and Dataset
  on path via `ensure_artifact`, Finding on a deterministic id (which now
  includes the SPLIT and the CLAIM, with `train` and `constants` as the historic
  defaults so existing ids still resolve), every edge through `link_once`.
- **One Execution per TRANSFER, keyed on WHAT it measured.** Service tag
  `llmsr:transfer`, and the `session_id` is `<run id>:<table stem>:<digest>`
  where the digest hashes the run, the recorded `data_path` and the candidate's
  `sample_order`. The run id ALONE would not do: one discovery can be transferred
  onto many tables and each is a separate measurement, so keying on the run would
  make the second transfer silently overwrite the first's numbers under its
  Finding ids, which is worse than a duplicate because it reads as an update. The
  recorded path is used EXACTLY as the artifact wrote it and is never re-resolved
  at ingest, else the same file would key differently from two directories. A
  different service tag from `llmsr:discover` means a transfer can never collide
  with its own discovery's Execution. The external-call failsafe applies
  unchanged: a non-`completed` `transfer.json` records a FAILED Execution plus
  the raw artifact and fabricates NO Finding, even though a failed transfer's
  fixed-theta side often carries real per-group numbers. Promoting those would
  answer the CONSTANTS question while silently dropping the FORM one the transfer
  was actually run for.
- **A transfer USED three things, and the Script edge is the one that matters.**
  `Execution -[USED]->` the table the form was transferred ONTO (carrying the
  regime the RUN assigned it), the source run's own training table (whose fitted
  constants the fixed-theta number applies, labelled `scored`), and the SOURCE
  RUN'S DISCOVERED SCRIPT at `.wheeler/llmsr/discoveries/<run_id>.py`. The third
  is what makes the chain from a transfer number back to the discovery that
  produced the form a real edge rather than a shared `custom_run_id`, and it
  resolves to the same node `discover.py` registered because `ensure_artifact`
  dedupes on path. It exists only once the DISCOVERY has been ingested, so a
  transfer ingested first is an ordinary order of operations: the edge is counted
  and logged, never fatal, and the act tells the scientist to ingest the
  discovery first. All three are INPUTS, so none is ever in `produced_ids` and
  none is `WAS_GENERATED_BY` the transfer, on the same rule that keeps
  reference-entity Papers off that edge.
- **The parser never raises.** A shape-drifted or partial `best.json` or
  `transfer.json` counts and skips; ingest is never aborted by a missing piece.
  A regime label neither module recognizes reports `unknown` with the reason
  rather than being coerced into the flattering answer, and a refit block
  labelled plain `held_out` is REPAIRED through `discover._refit_regime` on the
  way in (a no-op on anything `transfer.py` wrote, since it applies the same
  rule before writing).
- **Sequential writes only.** Never `asyncio.gather`: Neo4j forbids concurrent
  queries in one session.
- **A recipe is EXECUTED, never merely described.** Every entry in `recipes.py`
  points at a real template that `tests/integrations/llmsr/test_recipes.py` fills
  against a synthetic table and runs through the CLI, under the flag combination
  the recipe itself declares. Three recipes (`pooled`, `refit_per_group`,
  `transfer`) are flag combinations on the DEFAULT door, where the spec's
  `evaluate` is never called, so each is ALSO run once with
  `--use-spec-evaluate`: otherwise the text of three shipped files would never
  execute. `torch_adam` skips here (torch is absent) and `numpy_adam` carries the
  same claim in pure numpy, with a 400-step-versus-1-step comparison proving the
  loop ran rather than the return value being faked. Do not add a recipe without
  its file and its row in that walk, and do not let `torch_adam` become the only
  cover for the door's width. `docs/llmsr-spec-cookbook.md` quotes
  `Recipe.answers` / `assumes` / `costs` verbatim and a test pins the quotation,
  because a document that shows a different flag combination from the one the
  test runs is worse than no document.
- **The column names a scaffolded spec binds cannot shadow the recipe.** Every
  recipe binds locals (`y`, `pred`, `result`) partway through `evaluate`, and a
  CSV column with one of those names would be unpacked first and then overwritten,
  so the call to `equation` would pass the target where an input belongs and the
  fit would be scored against the wrong array WITHOUT raising. So the reserved set
  is read off the template itself (`recipes._bound_names` fills it with stand-ins,
  parses it, and collects every assignment, loop target, function name, argument
  and import) rather than hand-kept. A hand-kept list falls behind the first
  recipe that gains a local; this cannot.
- **`wheeler/_data/llmsr/` is authored, not mirrored.** `installer.sync_data()`
  mirrors `.claude/commands/wh/` and `.claude/agents/` into `_data/`; the llmsr
  tree has no upstream copy and is edited in place. It ships because hatchling
  includes every file inside a listed package, which is why no package-data glob
  exists for it, and `test_bundled.py` pins the one thing that could silently
  break it: the tree staying under `wheeler/`.
- **The demo tables are SYNTHETIC and every surface says so.** They are generated
  by `_data/llmsr/data/make_demo_data.py` from laws written in that file, not
  taken from the LLM-SR paper, whose datasets are not vendored here. The generator
  uses no RNG (an additive recurrence for the sample positions, an integer LCG for
  the noise) so the tables regenerate reproducibly, and the test reruns it and
  compares. Never describe them as the paper's data, and never drop the
  `synthetic_demo_data` flag from the `specs` listing.
- **Every open registry is SELECTABLE at `init`, not merely registerable.** A
  registry a scientist can add to but cannot choose from does not exist, however
  green its own tests are. `--metric`, `--loader` and `--optimizer` each bind
  their choice onto `meta.json` at `init`, each validated THERE (`_metric_for`,
  `_loader_for`, `_optimizer_for`) so an unresolvable name fails one command
  rather than invalidating every candidate in the search. The loader is the
  sharpest case: it decides which units exist, and per-group validity is strict,
  so a run that silently fell back to `csv` would hand the fit the very cells the
  scientist meant to exclude and reject a correct law.
  `tests/integrations/llmsr/test_cli_surface.py` is the gate: it asserts the flag
  exists on the built command, drives a userland registration of each kind
  THROUGH `init`, and proves the excluded cell really was excluded. A
  library-level test of `loaders.load_groups` cannot see any of that, which is
  why the loader registry shipped unreachable with 0 failing tests.
- **A knob the CLI has and the ACT does not is unreachable, on exactly the rule
  above.** The act is the only path a scientist actually takes: nothing Python
  reads `.claude/commands/wh/llmsr-discover.md`, so no library test can notice
  that a flag never reached it. Measured before this gate existed, `grep -c` over
  the act for `--islands`, `--reset-every`, `--cluster-tolerance` and
  `samples_per_prompt` returned 0 in both command trees and in `docs/`, and a run
  created by following the act's own assembled command wrote `islands: null`,
  `reset_every: null` and `cluster_tolerance: null`: 10 islands, a four-hour
  clock that fires 0 resets on a one-hour run, raw scores, and one body per
  prompt where upstream draws four.
  `tests/integrations/llmsr/test_act_surface.py` is that gate. It reads the flag
  names OFF the built `init` command rather than restating them, so a knob added
  to the CLI and not to the act fails; it requires both command trees to carry
  them; it requires `--cluster-tolerance` to be labelled a DEVIATION wherever it
  is offered (see the invariant below); and it requires the generation loop to
  carry the batch rule (`samples_per_prompt` bodies from ONE prompt, submitted on
  the same island and version). The service contract's ports are held to the same
  rule, since `/wh:service` interviews from them.
- **`--cluster-tolerance` is a DEVIATION from the published method and every
  surface that offers it says so.** Upstream clusters on the raw continuous score
  (`vendor/buffer.py::_get_signature` returns a tuple of floats over `s = -MSE`)
  and nothing there rounds or bins. Wheeler quantizes that signature only when
  asked, so the default is raw and reproduces the paper. It is offered because
  with continuous scores every candidate gets a unique signature, every cluster
  holds one program, and the within-cluster preference for the SHORTER program,
  upstream's only parsimony pressure, never acts: true of the paper's runs too,
  and free there (about 1,000 singleton clusters per island still let the
  score-weighted softmax select) where it costs a 30-candidate run everything.
  Do not describe quantizing as reproducing upstream, in the act, the docs, the
  contract prompt, or a report to the scientist. Same rule as the held-out
  ID/OOD invariant above.
  **And do not describe it as WORKING, either: measured, it does not currently
  change cluster formation.** `_quantize_scores` takes its bucket reference from
  the dict being quantized (`reference = max(finite)`), so the candidate's own
  largest-magnitude unit comes back exactly: a single-key signature (the
  ungrouped single-table shape, which is the commonest run) is the identity at
  every tolerance, and a multi-key one collapses its other units onto that exact
  per-candidate number and stays unique. Two real 25-program runs at 1.8, 3.2 and
  10.0 gave cluster counts identical to raw: 26 clusters / 1 holding more than one
  program ungrouped, 25 / 2 grouped. The per-candidate reference exists to remove
  a singularity at |v| = 1 and removed the collisions with it, so the per-run
  figures in `_quantize_scores`'s own docstring no longer describe its behaviour.
  A real fix needs a reference spanning the RUN, not the candidate; until then the
  act offers the flag as a deviation that does not restore the parsimony pressure.
- **`samples_per_prompt` is reported, not enforced, so the ACT owns it.** The CLI
  never calls a model, so `prompt` can only hand back upstream's
  `Config.samples_per_prompt` (4, and the paper's Appendix B b=4) and say what it
  means: four INDEPENDENT completions of ONE prompt, submitted with the same
  `--island-id` and `--version-generated` so they land on one island at one
  version and the buffer can compare them. `submit` already accepts repeated
  calls carrying the same pair; nothing else was needed on the CLI side. What was
  needed, and was missing, is the act telling the generator to produce that many
  bodies per prompt: one body per prompt is a quarter of the paper's exploration
  per context. Submits stay SEQUENTIAL because `submissions.jsonl` records exceed
  the atomic-append size, so only generation may be concurrent.
- **Every emitted `METRIC` label is checked against the same run's `best.json`.**
  Same file, `assert_metric_label_is_earned`, across all four footer shapes: the
  name must be the run's scored metric, and wherever `best.json` records a number
  under that same name, the .py's number must BE it. The .py is the durable half
  of a discovery, so a wrong label there outlives the run dir, the terminal and
  the conversation.
- **`llmsr-transfer` is a SECOND contract, not a flag on the first.** A
  generalization test is its own run with its own inputs, its own truthful
  status and its own answer, so it gets its own contract, its own act
  (`/wh:llmsr-transfer`), its own service tag and its own Execution. Its
  `dataset` port is SINGLE-valued, unlike `llmsr-discover`'s: `transfer --data`
  takes one table, and a `multi` port would interview for a call the verb
  cannot make. It declares no `options_from` because nothing on it is backed by
  an open registry: the metric, loader and optimizer are the SOURCE RUN'S and
  are read off its `meta.json`, since a transfer fitted differently from the
  search that produced the form is not comparable with it.
- **Every port reads its registry, and the dataset port takes SEVERAL.** The
  `llmsr-discover` contract in `services.default.yaml` points `metric`, `recipe`,
  `loader` and `optimizer` at their registries through `options_from`, so a
  scientist's own metric or loader is offerable by the interview instead of being
  invisible behind a hardcoded list. Resolution is lazy and falls back to the
  static `options` on any failure, because an EMPTY choice port would make every
  answer invalid. Two details that are choices, not accidents: the optimizer port
  asks `optimizers:choices` and not `available()`, because `auto` is the default
  and must therefore be a legal explicit answer while not being a concrete
  registered optimizer; and `available()` imports the userland sources itself
  (S7), so a caller that has not run `load_user_metrics()` still sees a
  registered metric.
- **The dataset port is `multi`, and a single-valued port refuses a list.**
  `--data` is repeatable and the unit of fitting is a (dataset, group) pair, so a
  contract declaring one `dataset` could not interview for the run this engine is
  built around. `invocation.InputPort` therefore carries `multi`, and the
  `datasets` / `score_on` ports set it, with `seed_from` and `score_on` carrying
  `from: datasets` so the interview knows their legal answers come from what was
  just named. The other half is load-bearing: a list handed to a single-valued
  port is reported INVALID rather than truncated, because quietly keeping one of
  several answers is exactly how a multi-input run ends up answering a smaller
  question than the scientist asked. An empty list is not an answer either.

## Conventions

- `from __future__ import annotations`; `logging.getLogger(__name__)`; async only
  where graph I/O happens (`discover.py`, `transfer_ingest.py`).
- `execute_tool` is imported lazily, function-local, in `discover.py` and
  `transfer_ingest.py` only. Same rule as the Asta adapters and
  `validation/ledger.py`. Those two are the only graph writers here, and
  `transfer_ingest.py` imports its labelling vocabulary and its Finding-id
  scheme FROM `discover.py` rather than restating them: two modules writing
  metric Findings under two spellings of "held out" is exactly what the labels
  exist to prevent.
- Add no LLM-provider SDK, and never an API key path. Generation is the act's job.
- Never use em dashes. Use colons, commas, periods, parentheses.
- Tests live in `tests/integrations/llmsr/`, whose `conftest.py` gives every test
  a scratch cwd and restores the process-wide metric registry. Do not hand-copy
  it into a new test file: it is autouse for the whole directory.
- Two parity gates run inside the suite and must stay green: `parity_bfgs.py`
  (the optimizer registry moved no bit where BFGS moved) and
  `parity_singledata.py` (the dataset seam moved no bit for an unnamed single
  `--data`). Both compare against a golden captured from an earlier commit. If a
  legitimate change alters the numbers, REGENERATE the golden per the script's
  docstring and say so loudly; do not delete the gate.
- `test_multidata.py` exports the reusable multi-dataset surface: `walk_case`
  (one `init` -> `submit` -> `best` walk returning everything it wrote),
  `scored_keys` / `scored_datasets`, and `SCORE_ON_MATRIX` (the four `--score-on`
  shapes as a plain parametrize table). Import them rather than restating them.
