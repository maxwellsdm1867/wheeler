"""The seam between what the CLI accepts and what the ACT actually offers.

`test_cli_surface.py` keeps one rule: a registry a scientist can add to but not
SELECT is a feature that does not exist. This file keeps the next link in the same
chain, which that rule does not cover: **a knob the CLI accepts and the ACT never
mentions is equally unreachable.** `/wh:llmsr-discover` is the only path a
scientist actually takes, and nothing in Python reads it, so no library test and
no CLI test can notice that a flag never arrived there.

That is not hypothetical. An audit added four mechanisms to the search and every
one of them stopped at the CLI. Measured before this file existed, `grep -c` over
`.claude/commands/wh/llmsr-discover.md` for `--islands`, `--reset-every`,
`--cluster-tolerance` and `samples_per_prompt` returned 0, and the same for the
shipped `wheeler/_data/` mirror and for `docs/`. A run created by following the
act's own assembled `init` command wrote `islands: null`, `reset_every: null`,
`cluster_tolerance: null`: upstream's 10 islands, a four-hour reset clock that
fires 0 resets on a one-hour run, raw scores, and one candidate body per prompt
where upstream draws four.

Three rules, and each is checked against the LIVE CLI rather than against a list
restated here, so a flag renamed in `cli.py` fails this file instead of quietly
turning an act instruction into a typo:

**1. Every search knob on `init` is offered by the act, in both command trees.**
**2. Every flag the act tells the scientist to type is one the CLI accepts.**
**3. `--cluster-tolerance` is labelled a DEVIATION from the published method
   wherever it is offered.** The paper clusters on the raw continuous score;
   quantizing it is Wheeler's accommodation for a small sample budget, off by
   default, and must never be presented as reproducing upstream. Same rule the
   held-out ID/OOD protocol is held to.

No live model and no Neo4j: the behavioural half runs against the scratch project
this directory's ``conftest.py`` gives every test.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from wheeler.integrations.llmsr.cli import llmsr_app
from wheeler.integrations.registry import load_services

runner = CliRunner()

REPO = Path(__file__).resolve().parents[3]

# The act, and the mirror `wheeler install` actually ships. `installer.sync_data`
# flattens `.claude/commands/wh/` into `_data/commands/`, so the mirror has no
# `wh/` level: hardcoding one here would make every mirror assertion skip on a
# missing file instead of failing on stale content.
ACT_TREES = (
    pytest.param(REPO / ".claude" / "commands" / "wh", id="source"),
    pytest.param(REPO / "wheeler" / "_data" / "commands", id="shipped"),
)

DISCOVER_ACT = "llmsr-discover.md"


# ------------------------------------------------------------------ CLI truth

def _init_options() -> set[str]:
    """Every long option ``wheeler llmsr init`` really accepts.

    Read off the built click command, not grepped out of ``--help``: help text is
    wrapped for a terminal, and a flag broken across two lines would make a grep
    pass for the wrong reason.
    """
    return _verb_options("init")


def _verb_options(verb: str) -> set[str]:
    from typer.main import get_command

    commands = get_command(llmsr_app).commands  # type: ignore[attr-defined]
    if verb not in commands:
        return set()
    return {opt for param in commands[verb].params for opt in param.opts}


def _act(tree: Path, name: str = DISCOVER_ACT) -> str:
    path = tree / name
    assert path.is_file(), f"{path} is missing: the command trees have drifted"
    return path.read_text()


def _fenced_blocks(text: str) -> list[str]:
    """Every fenced code block, including the ones indented inside a list item.

    The scaffold-spec command lives in an indented fence, and a left-anchored
    fence pattern silently skipped it, which is exactly the kind of gap that
    makes a surface test pass while covering less than it claims.
    """
    return re.findall(r"^[ \t]*```.*?^[ \t]*```", text, re.S | re.M)


def _init_block(text: str) -> str:
    """The assembled ``init`` command the act tells the scientist to run.

    Checked separately from the act's prose: a knob described in a paragraph and
    absent from the command block is a knob the reader is told about and then
    shown how to omit.
    """
    blocks = [b for b in _fenced_blocks(text) if "wheeler llmsr init" in b]
    assert blocks, "the act shows no assembled `wheeler llmsr init` command"
    # Line continuations joined, so a flag on a wrapped line still reads as part
    # of the one command.
    return blocks[0].replace("\\\n", " ")


# ===========================================================================
# 1. Every search knob on `init` reaches the act
# ===========================================================================

# The knobs that configure the SEARCH ITSELF rather than the objective, each with
# the default it overrides. All four were reachable from `init` and unreachable
# from the act. Adding a search knob without adding its row here is what this
# table exists to make impossible to do quietly.
SEARCH_KNOBS = (
    pytest.param("--islands", "the island count (upstream's 10)", id="islands"),
    pytest.param(
        "--reset-every",
        "the submission-count reset clock (off, and the wall clock never fires)",
        id="reset-every",
    ),
    pytest.param(
        "--cluster-tolerance",
        "score quantization so clusters form at all (off, which is the paper)",
        id="cluster-tolerance",
    ),
)


class TestEverySearchKnobReachesTheAct:
    """A knob on the CLI and not in the act is unreachable, like an unselectable
    registry. The act is the surface; the CLI is an implementation detail of it.
    """

    @pytest.mark.parametrize("flag,what", SEARCH_KNOBS)
    def test_the_knob_is_still_on_the_init_command(self, flag, what):
        """The CLI end of the chain. If this fails, the flag was renamed and every
        act instruction naming it became a typo the act cannot detect."""
        assert flag in _init_options(), f"{flag} ({what}) is gone from `init`"

    @pytest.mark.parametrize("tree", ACT_TREES)
    @pytest.mark.parametrize("flag,what", SEARCH_KNOBS)
    def test_the_act_offers_the_knob(self, tree, flag, what):
        assert flag in _act(tree), (
            f"{flag} sets {what} and `wheeler llmsr init` accepts it, but "
            f"{tree / DISCOVER_ACT} never mentions it, so no run driven by the "
            "act can ever set it"
        )

    @pytest.mark.parametrize("tree", ACT_TREES)
    @pytest.mark.parametrize("flag,what", SEARCH_KNOBS)
    def test_the_assembled_command_carries_the_knob(self, tree, flag, what):
        assert flag in _init_block(_act(tree)), (
            f"{flag} is discussed in the act but missing from the assembled "
            "`init` command block, which is the line that actually gets run"
        )

    def test_typing_them_the_act_s_way_binds_them_to_the_run(self):
        """The behavioural half: the flags the act names really do reach `meta.json`.

        Bound to the RUN and not to a later command line, because the buffer is
        replayed from `submissions.jsonl` on every verb: a setting read off a
        later invocation would silently reassign islands.
        """
        _write_spec_and_data()
        result = runner.invoke(llmsr_app, [
            "init", "--spec", "spec.txt", "--data", "train.csv", "--metric", "mse",
            "--run-id", "act-knobs",
            "--islands", "3", "--reset-every", "8", "--cluster-tolerance", "1.8",
        ])
        assert result.exit_code == 0, result.output + str(result.exception)

        meta = json.loads(
            (Path(".wheeler/llmsr/runs/act-knobs/meta.json")).read_text()
        )
        assert meta["islands"] == 3
        assert meta["reset_every"] == 8
        assert meta["cluster_tolerance"] == pytest.approx(1.8)

    def test_the_defaults_are_still_what_the_act_says_they_are(self):
        """The act tells the scientist that omitting these means upstream's
        behaviour. That claim is checked here rather than trusted: if a default
        ever moves, the act's description of it becomes false."""
        _write_spec_and_data()
        result = runner.invoke(llmsr_app, [
            "init", "--spec", "spec.txt", "--data", "train.csv", "--metric", "mse",
            "--run-id", "act-defaults",
        ])
        assert result.exit_code == 0, result.output + str(result.exception)
        meta = json.loads(
            (Path(".wheeler/llmsr/runs/act-defaults/meta.json")).read_text()
        )
        for key in ("islands", "reset_every", "cluster_tolerance"):
            assert not meta.get(key), (
                f"{key} now defaults to {meta.get(key)!r}; the act says omitting "
                "it means upstream's default"
            )


# ===========================================================================
# 2. Every flag the act types is one the CLI accepts
# ===========================================================================

class TestEveryCommandTheActShowsIsRunnable:
    """The other direction, and the one a grep for known flags cannot cover.

    An act is a system prompt, so a misspelled flag in it is not a syntax error
    anywhere: it is an instruction a model follows until the CLI rejects it
    mid-search. Every `wheeler llmsr` invocation in a fenced block is therefore
    checked verb by verb and flag by flag against the built command.
    """

    ACTS = ("llmsr-discover.md", "llmsr-transfer.md")

    @pytest.mark.parametrize("tree", ACT_TREES)
    @pytest.mark.parametrize("act_name", ACTS)
    def test_every_verb_and_flag_resolves(self, tree, act_name):
        found = 0
        for block in _fenced_blocks(_act(tree, act_name)):
            joined = block.replace("\\\n", " ")
            for match in re.finditer(
                r"wheeler llmsr ([a-z][a-z0-9-]*)([^\n]*(?:\n[ \t]+[^\n]*)*)", joined
            ):
                verb, tail = match.group(1), match.group(2)
                options = _verb_options(verb)
                assert options, (
                    f"{act_name} shows `wheeler llmsr {verb}`, which is not a verb"
                )
                unknown = set(re.findall(r"--[a-z][a-z0-9-]*", tail)) - options
                assert not unknown, (
                    f"{act_name} tells the scientist to pass {sorted(unknown)} to "
                    f"`wheeler llmsr {verb}`, which does not accept them"
                )
                found += 1
        assert found, f"{act_name} shows no `wheeler llmsr` command to check"


# ===========================================================================
# 3. The batch rule: samples_per_prompt candidates from ONE prompt
# ===========================================================================

class TestTheBatchRuleReachesTheAct:
    """`samples_per_prompt` is REPORTED, not enforced, so the act owns it.

    The CLI never calls a model, so `prompt` can only hand back upstream's value
    (4, the paper's Appendix B b=4) and say what it means. If the act does not
    tell the generator to produce that many bodies from one prompt and submit them
    on the same island and version, the run does a quarter of the paper's
    exploration per context and nothing anywhere reports that it did.
    """

    @pytest.mark.parametrize("tree", ACT_TREES)
    def test_the_act_names_it(self, tree):
        assert "samples_per_prompt" in _act(tree), (
            "`wheeler llmsr prompt` reports samples_per_prompt and the act never "
            "reads it, so the generator produces one body per prompt"
        )

    @pytest.mark.parametrize("tree", ACT_TREES)
    def test_the_act_pins_the_batch_to_one_island_and_version(self, tree):
        """Four bodies submitted under four different prompts are not a batch.

        The whole content of `samples_per_prompt` is that the completions share a
        context, and what records that on disk is the island id and the version.
        """
        text = _act(tree)
        assert "--island-id" in text and "--version-generated" in text
        assert re.search(r"same\s+`?--island-id", text) or re.search(
            r"SAME\s+`?--island-id", text
        ), (
            "the act mentions samples_per_prompt but never says the batch is "
            "submitted on the SAME --island-id and --version-generated"
        )

    def test_prompt_really_reports_it(self):
        """Ties the act's instruction to the CLI's actual output: the act says to
        read the field off `prompt`, so the field must be there to read."""
        _write_spec_and_data()
        init = runner.invoke(llmsr_app, [
            "init", "--spec", "spec.txt", "--data", "train.csv", "--metric", "mse",
            "--run-id", "act-batch",
        ])
        assert init.exit_code == 0, init.output + str(init.exception)

        got = runner.invoke(llmsr_app, ["prompt", "--run", "act-batch"])
        assert got.exit_code == 0, got.output + str(got.exception)
        payload = json.loads(got.output.strip().splitlines()[-1])
        assert payload["samples_per_prompt"] >= 1
        assert "island_id" in payload and "version_generated" in payload

    def test_a_batch_lands_on_one_island_at_one_version(self):
        """The submit side of the act's instruction, driven the way it prescribes:
        one `prompt`, several bodies, the SAME bookkeeping on every submit."""
        _write_spec_and_data()
        init = runner.invoke(llmsr_app, [
            "init", "--spec", "spec.txt", "--data", "train.csv", "--metric", "mse",
            "--run-id", "act-batch-submit", "--islands", "3",
        ])
        assert init.exit_code == 0, init.output + str(init.exception)

        got = runner.invoke(llmsr_app, ["prompt", "--run", "act-batch-submit"])
        payload = json.loads(got.output.strip().splitlines()[-1])
        batch = int(payload["samples_per_prompt"])
        assert batch > 1, "a batch of one is what this act change exists to fix"

        for i in range(batch):
            # Distinct bodies, as independent completions of one prompt would be.
            body = Path(f"body_{i}.py")
            body.write_text(f"    return params[0]*x1 + {i}.0*params[1]*x2\n")
            sub = runner.invoke(llmsr_app, [
                "submit", "--run", "act-batch-submit", "--body-file", str(body),
                "--island-id", str(payload["island_id"]),
                "--version-generated", str(payload["version_generated"]),
            ])
            assert sub.exit_code == 0, sub.output + str(sub.exception)

        log = Path(".wheeler/llmsr/runs/act-batch-submit/submissions.jsonl")
        rows = [json.loads(line) for line in log.read_text().splitlines() if line]
        batched = [r for r in rows if r.get("island_id") == payload["island_id"]]
        assert len(batched) >= batch, (
            "the batch did not all land on the prompt's island: "
            f"{len(batched)} of {batch}"
        )
        assert {r.get("version_generated") for r in batched} == {
            payload["version_generated"]
        }, "the batch spans several versions, so it was not one prompt's output"


# ===========================================================================
# 4. `--cluster-tolerance` is offered as a DEVIATION, not as fidelity
# ===========================================================================

class TestClusterToleranceIsLabelledADeviation:
    """LLM-SR clusters on the raw continuous score and nothing upstream rounds or
    bins it, so quantizing is Wheeler's, exactly as the held-out ID/OOD protocol
    is Wheeler's. Every surface that OFFERS the flag has to say so, because the
    scientist reading that surface is the one who may publish the result.
    """

    # Any of these, in the sentence that offers the flag, is an honest label.
    DEVIATION_WORDS = ("deviation", "deviates", "not the paper", "not upstream")

    @pytest.mark.parametrize("tree", ACT_TREES)
    def test_the_act_calls_it_a_deviation(self, tree):
        text = _act(tree)
        # The paragraph that introduces the flag, not the whole act: the label has
        # to sit where the offer is made.
        start = text.index("--cluster-tolerance")
        window = text[max(0, start - 200):start + 1200].lower()
        assert any(word in window for word in self.DEVIATION_WORDS), (
            "the act offers --cluster-tolerance without saying it deviates from "
            "the published method, which clusters on the raw score"
        )

    @pytest.mark.parametrize("tree", ACT_TREES)
    def test_the_act_says_the_default_is_off(self, tree):
        text = _act(tree)
        start = text.index("--cluster-tolerance")
        window = text[max(0, start - 200):start + 1200].lower()
        assert "off" in window or "absent" in window or "raw" in window, (
            "the act does not say --cluster-tolerance is off by default, so a "
            "reader cannot tell whether their run deviated"
        )

    # Phrasings that tell the reader the flag does not currently deliver the
    # clustering it aims at.
    UNFIXED_WORDS = ("does not currently", "not restore", "still absent",
                     "does not yet")

    @pytest.mark.parametrize("tree", ACT_TREES)
    def test_the_act_s_claim_matches_what_the_quantizer_actually_does(self, tree):
        """Pinned to the CODE, not to a sentence, so it cannot go stale either way.

        History, because the direction of this test has already flipped once and
        will flip again if the quantizer changes. It once took its bucket
        reference from the dict being quantized, so a candidate's own
        largest-magnitude unit came back exactly: on a single-key signature that
        made the whole function the IDENTITY at every tolerance, and cluster
        counts were identical to raw at 1.8, 3.2 and 10.0. The act was then
        required to SAY the lever did nothing, because offering a dead lever is
        worse than not offering it.

        The reference is now FIXED at 1.0, so buckets are shared across
        candidates and the lever works. Re-measured on a real 26-submission run
        with a 5-unit signature over 10 islands: raw gives 35 clusters and 0
        holding more than one program, 1.8x gives 32 and 3, 3.2x gives 30 and 4.
        Isolating the mechanism from the island split, distinct signatures over
        those 26 candidates go 26 raw, 13 at 1.8x, 10 at 3.2x. So the act must
        now NOT claim it is dead, while still naming it a deviation.

        The branch is on the code's measured behaviour rather than on which
        version is checked in, so whichever way somebody changes
        `_quantize_scores`, the surfaces are held to what it really does.
        """
        from wheeler.integrations.llmsr.cli import _quantize_scores

        single = {"data": -0.657362}
        identity = _quantize_scores(single, 10.0)["data"] == pytest.approx(
            single["data"]
        )
        surfaces = {
            str(tree / DISCOVER_ACT): _act(tree).lower(),
            "services.default.yaml:cluster_tolerance":
                _discover_port("cluster_tolerance")["prompt"].lower(),
        }
        if identity:
            for where, text in surfaces.items():
                assert any(word in text for word in self.UNFIXED_WORDS), (
                    "_quantize_scores is the identity on a single-key "
                    "signature, so --cluster-tolerance changes nothing on an "
                    f"ungrouped single-table run, and {where} offers it without "
                    "saying so"
                )
        else:
            # The quantizer works, so the surfaces must not still claim it is
            # dead. A stale caveat is its own defect: it talks a scientist out of
            # a lever that now does something.
            for where, text in surfaces.items():
                stale = [word for word in self.UNFIXED_WORDS if word in text]
                assert not stale, (
                    "_quantize_scores buckets across candidates now (measured: "
                    "raw 35 clusters / 0 holding more than one program, 1.8x "
                    f"32 / 3, 3.2x 30 / 4), but {where} still says it does not "
                    f"deliver: {stale}. Re-measure and update the claim."
                )

    def test_the_service_contract_prompt_says_it_too(self):
        """`/wh:service` interviews from the contract, not from the act, so the
        label has to be on the port as well. Two surfaces, one rule."""
        port = _discover_port("cluster_tolerance")
        prompt = port["prompt"].lower()
        assert any(word in prompt for word in self.DEVIATION_WORDS), (
            "the contract asks about cluster_tolerance without naming it a "
            "deviation, so the interview presents it as an ordinary option"
        )


# ===========================================================================
# 5. The service contract interviews for the knobs too
# ===========================================================================

def _discover_port(name: str) -> dict:
    """One input port off the shipped `llmsr-discover` contract.

    ``ServiceContract.inputs`` is deliberately opaque in the registry (raw dicts;
    the adapters interpret them), so read it as the manifest wrote it.
    """
    services = {s.id: s for s in load_services()}
    assert "llmsr-discover" in services, "the llmsr-discover contract is missing"
    ports = list(services["llmsr-discover"].inputs)
    match = [p for p in ports if p.get("name") == name]
    assert match, (
        f"the llmsr-discover contract has no {name!r} port, so `/wh:service` "
        f"never asks about it: ports are {sorted(str(p.get('name')) for p in ports)}"
    )
    return {
        "name": name,
        "prompt": str(match[0].get("prompt", "")),
        "kind": str(match[0].get("kind", "")),
    }


class TestTheContractInterviewsForTheSearchConfiguration:
    """`/wh:service` is the second way a scientist reaches this run, and it asks
    only what the contract declares. A knob absent from the ports is unreachable
    down that path however well the act covers it.
    """

    @pytest.mark.parametrize(
        "port", ["islands", "reset_every", "cluster_tolerance"]
    )
    def test_the_port_exists_and_asks_something(self, port):
        got = _discover_port(port)
        assert got["prompt"].strip(), f"the {port!r} port asks nothing"


# ===========================================================================
# Shared scratch fixtures
# ===========================================================================

def _write_spec_and_data() -> None:
    """A minimal runnable spec and a two-input table, in the scratch cwd.

    Deliberately local rather than imported from `test_cli_surface.py`: this file
    checks a different surface and must not fail because that file's private
    helpers were renamed.
    """
    Path("spec.txt").write_text(
        '"""toy: y from x1 and x2."""\n'
        "import numpy as np\n\n"
        "MAX_NPARAMS = 2\n\n\n"
        "@evaluate.run\n"
        "def evaluate(data: dict):\n"
        "    return 0.0\n\n\n"
        "@equation.evolve\n"
        "def equation(x1: np.ndarray, x2: np.ndarray, "
        "params: np.ndarray) -> np.ndarray:\n"
        "    return params[0]*x1\n"
    )
    lines = ["x1,x2,y"]
    for i in range(20):
        x1 = -3.0 + 0.3 * i
        x2 = 2.0 - 0.2 * i
        lines.append(f"{x1:.17g},{x2:.17g},{2.0 * x1 + 0.5 * x2:.17g}")
    Path("train.csv").write_text("\n".join(lines) + "\n")
