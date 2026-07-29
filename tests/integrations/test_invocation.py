"""Tests for the service-invocation intake (the interview schema + validator).

The interview lives in an act (a prompt), so the reliable guarantee that it asks
for the RIGHT information lives here, in tested Python: the schema each service
declares, and the validator that decides what is still missing / invalid. The
'fake user' e2e scripts a simulated scientist through the interview loop and
asserts the right questions get asked and the right request gets assembled.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from wheeler.integrations.invocation import (
    input_ports,
    validate_request,
)
from wheeler.integrations.registry import catalog_services


def _contract(service_id: str):
    return next(c for c in catalog_services() if c.id == service_id)


# ---------------------------------------------------------------------------
# 1. Schema contract: each service declares the right inputs ("right information")
# ---------------------------------------------------------------------------


class TestSchema:
    def test_llmsr_declares_the_right_inputs(self):
        ports = {p.name: p for p in input_ports(_contract("llmsr-discover"))}
        # A dataset is required, it is a Dataset graph node, and the port takes
        # SEVERAL. `wheeler llmsr init --data` is repeatable and the unit of
        # fitting is a (dataset, group) pair, so a single-valued port could not
        # interview for the run the engine is built around.
        assert ports["datasets"].required is True
        assert ports["datasets"].kind == "node"
        assert ports["datasets"].node_type == "Dataset"
        assert ports["datasets"].multi is True
        # the metric must be asked (never silently defaulted) and offers at least
        # the built-ins. A SUPERSET check, not equality: the port reads the metric
        # registry at call time, which is open (see TestOptionsFrom), so a
        # scientist's registered metric legitimately widens this list.
        assert ports["metric"].required is True
        assert ports["metric"].kind == "choice"
        assert {"mse", "nmse"} <= set(ports["metric"].options)
        # selection strategy is offered with parsimony as the default
        assert ports["select"].kind == "choice"
        assert set(ports["select"].options) == {"parsimony", "ood", "fit"}
        assert ports["select"].default == "parsimony"
        # the linking question is optional
        assert ports["question"].required is False

    def test_llmsr_can_be_interviewed_for_the_two_dataset_ROLES(self):
        """Which table shapes the prompt and which tables are scored.

        Keeping them apart is the point of the multi-dataset run: a form
        extracted from one cell and refitted on cells it never saw is a test of
        the FORM. A contract that only asked "which dataset" made that run
        unreachable through the interview.
        """
        ports = {p.name: p for p in input_ports(_contract("llmsr-discover"))}
        assert ports["seed_from"].from_ == "datasets"
        assert ports["score_on"].from_ == "datasets"
        assert ports["score_on"].multi is True
        # both optional: the defaults (first table seeds, every table scores) are
        # the single-dataset behaviour
        assert ports["seed_from"].required is False
        assert ports["score_on"].required is False
        # and the per-group protocol is offerable
        assert ports["group_by"].kind == "text"
        assert ports["group_by"].required is False

    def test_llmsr_offers_every_open_registry_it_has(self):
        """Metric, recipe, loader and optimizer are all extensible at runtime."""
        ports = {p.name: p for p in input_ports(_contract("llmsr-discover"))}
        assert {"pooled", "refit_per_group"} <= set(ports["recipe"].options)
        assert "csv" in ports["loader"].options
        # `auto` is the default and must therefore be a legal explicit answer,
        # which is why the port asks `choices` and not `available`.
        assert "auto" in ports["optimizer"].options
        assert ports["optimizer"].default == "auto"

    def test_asta_services_require_a_query(self):
        for sid in ("paper-finder", "theorizer", "semantic-scholar", "scholar-qa"):
            ports = {p.name: p for p in input_ports(_contract(sid))}
            assert ports["query"].required is True
            assert ports["query"].kind == "text"

    def test_service_without_inputs_is_always_ready(self):
        # graph-status declares no inputs: nothing to ask, request is valid as-is
        contract = _contract("graph-status")
        assert input_ports(contract) == []
        assert validate_request(contract, {}).ok is True


# ---------------------------------------------------------------------------
# 1b. options_from: a choice port whose legal answers are OPEN
# ---------------------------------------------------------------------------


def _fake_options() -> list[str]:
    return ["alpha", "beta", "gamma"]


def _raising_options() -> list[str]:
    raise RuntimeError("the scientist's registry blew up")


def _empty_options() -> list:
    return []


def _wrong_shape_options() -> str:
    return "not a list"


class TestOptionsFrom:
    """A port whose legal answers come from a plug-in registry must offer what is
    actually registered, and must DEGRADE to the frozen list rather than to an
    empty one: an empty choice port makes every possible answer invalid."""

    _HERE = "tests.integrations.test_invocation"

    def _contract(self, **port):
        base = {
            "name": "metric",
            "kind": "choice",
            "options": ["mse", "nmse"],
            "required": True,
        }
        base.update(port)
        return SimpleNamespace(id="fake", act="/wh:fake", inputs=[base])

    def _options(self, **port) -> set[str]:
        return set(input_ports(self._contract(**port))[0].options)

    def test_resolved_options_replace_the_static_list(self):
        assert self._options(options_from=f"{self._HERE}:_fake_options") == {
            "alpha", "beta", "gamma",
        }

    def test_the_spec_stays_on_the_port(self):
        spec = f"{self._HERE}:_fake_options"
        assert input_ports(self._contract(options_from=spec))[0].options_from == spec

    def test_no_options_from_leaves_the_static_list_untouched(self):
        assert self._options() == {"mse", "nmse"}

    @pytest.mark.parametrize(
        "spec",
        [
            "wheeler.integrations.no_such_module:available",  # unimportable
            "tests.integrations.test_invocation:no_such_callable",  # missing attr
            "tests.integrations.test_invocation:_raising_options",  # raises
            "tests.integrations.test_invocation:_empty_options",  # empty answer
            "tests.integrations.test_invocation:_wrong_shape_options",  # not a list
            "not-a-spec",  # malformed
            "",  # blank
        ],
    )
    def test_every_failure_falls_back_to_the_static_options(self, spec):
        assert self._options(options_from=spec) == {"mse", "nmse"}

    def test_a_dynamically_offered_value_validates(self):
        # the point of the wiring: an answer the YAML never listed is accepted
        contract = self._contract(options_from=f"{self._HERE}:_fake_options")
        assert validate_request(contract, {"metric": "beta"}).ok is True
        assert validate_request(contract, {"metric": "mse"}).ok is False

    def test_llmsr_metric_port_is_wired_to_the_metric_registry(self):
        ports = {p.name: p for p in input_ports(_contract("llmsr-discover"))}
        assert (
            ports["metric"].options_from
            == "wheeler.integrations.llmsr.metrics:available"
        )


# ---------------------------------------------------------------------------
# 2. Validator: it correctly identifies missing / invalid inputs
# ---------------------------------------------------------------------------


class TestValidator:
    def test_empty_flags_the_required_questions(self):
        contract = _contract("llmsr-discover")
        r = validate_request(contract, {})
        assert r.ok is False
        assert set(r.missing) == {"datasets", "metric"}  # exactly the must-asks

    def test_bad_choice_value_is_rejected(self):
        contract = _contract("llmsr-discover")
        r = validate_request(contract, {"datasets": ["D-x"], "metric": "banana"})
        assert r.ok is False
        assert ("metric", "banana") in r.invalid

    def test_complete_request_is_assembled_with_defaults(self):
        contract = _contract("llmsr-discover")
        r = validate_request(
            contract, {"datasets": ["D-abc12345"], "metric": "nmse"}
        )
        assert r.ok is True
        assert r.assembled["service"] == "llmsr-discover"
        assert r.assembled["act"] == "/wh:llmsr-discover"
        assert r.assembled["inputs"]["datasets"] == ["D-abc12345"]
        assert r.assembled["inputs"]["metric"] == "nmse"
        # the optional select port fell back to its default (shown to the user)
        assert r.assembled["inputs"]["select"] == "parsimony"
        # the optional question port was not answered, so it is absent
        assert "question" not in r.assembled["inputs"]

    def test_required_input_is_never_silently_defaulted(self):
        contract = _contract("llmsr-discover")
        # metric has a default (nmse) but is required: with no answer it is MISSING,
        # not quietly filled in.
        r = validate_request(contract, {"datasets": ["D-x"]})
        assert r.ok is False
        assert "metric" in r.missing
        assert "metric" not in r.assembled["inputs"]


class TestMultiValuedPorts:
    """A port that takes SEVERAL, and one that must not be handed several.

    Both halves matter. Without the first, a tool whose CLI is repeatable can
    only ever be interviewed for one input. Without the second, a list handed to
    a single-valued port would be passed through and the adapter would take one
    of them, so the run would silently answer a smaller question than the
    scientist asked.
    """

    def test_a_multi_port_accepts_several_values(self):
        contract = _contract("llmsr-discover")
        r = validate_request(contract, {
            "datasets": ["D-a", "D-b", "D-c"],
            "metric": "mse",
            "score_on": ["D-b", "D-c"],
        })
        assert r.ok is True
        assert r.assembled["inputs"]["datasets"] == ["D-a", "D-b", "D-c"]
        assert r.assembled["inputs"]["score_on"] == ["D-b", "D-c"]

    def test_a_multi_port_still_accepts_one(self):
        contract = _contract("llmsr-discover")
        assert validate_request(
            contract, {"datasets": "D-a", "metric": "mse"}
        ).ok is True

    def test_an_empty_list_is_not_an_answer(self):
        contract = _contract("llmsr-discover")
        r = validate_request(contract, {"datasets": [], "metric": "mse"})
        assert r.ok is False
        assert "datasets" in r.missing

    def test_a_single_valued_port_refuses_a_list_rather_than_truncating(self):
        contract = _contract("llmsr-discover")
        r = validate_request(contract, {
            "datasets": ["D-a"], "metric": "mse", "seed_from": ["D-a", "D-b"],
        })
        assert r.ok is False
        assert ("seed_from", ["D-a", "D-b"]) in r.invalid

    def test_every_element_of_a_multi_choice_is_checked(self):
        contract = SimpleNamespace(id="fake", act="/wh:fake", inputs=[{
            "name": "flavour", "kind": "choice", "multi": True,
            "options": ["a", "b"], "required": True,
        }])
        r = validate_request(contract, {"flavour": ["a", "zzz"]})
        assert r.ok is False
        assert ("flavour", "zzz") in r.invalid


# ---------------------------------------------------------------------------
# 3. Fake-user e2e: script a simulated scientist through the interview loop
# ---------------------------------------------------------------------------


def _run_interview(contract, fake_answers, max_rounds=10):
    """Simulate the act's interview: repeatedly ask for the next missing/invalid
    input, a fake user answers from `fake_answers`, until the request validates.
    Returns (questions_asked, final ValidationResult)."""
    provided: dict = {}
    asked: list[str] = []
    for _ in range(max_rounds):
        result = validate_request(contract, provided)
        if result.ok:
            return asked, result
        nxt = result.missing[0] if result.missing else result.invalid[0][0]
        asked.append(nxt)
        provided[nxt] = fake_answers.get(nxt)
    return asked, validate_request(contract, provided)


class TestFakeUserInterview:
    def test_interview_asks_the_right_questions_and_assembles_the_request(self):
        contract = _contract("llmsr-discover")
        # what a scientist would answer
        fake_answers = {"datasets": ["D-deadbeef"], "metric": "mse"}
        asked, result = _run_interview(contract, fake_answers)

        # the interview ASKED for the dataset and the metric (the required inputs)
        assert "datasets" in asked
        assert "metric" in asked
        # it converged to a valid, correctly-filled request
        assert result.ok is True
        assert result.assembled["inputs"]["datasets"] == ["D-deadbeef"]
        assert result.assembled["inputs"]["metric"] == "mse"  # fake user's choice, not the default
        assert result.assembled["inputs"]["select"] == "parsimony"  # default for the optional port

    def test_interview_recovers_from_a_bad_answer(self):
        contract = _contract("llmsr-discover")
        # the fake user first gives a bad metric, then the correct one on retry
        provided = {"datasets": ["D-1"], "metric": "banana"}
        r1 = validate_request(contract, provided)
        assert not r1.ok and ("metric", "banana") in r1.invalid
        provided["metric"] = "nmse"  # fake user corrects it
        r2 = validate_request(contract, provided)
        assert r2.ok is True
        assert r2.assembled["inputs"]["metric"] == "nmse"

    def test_asta_interview_asks_for_the_query(self):
        contract = _contract("paper-finder")
        asked, result = _run_interview(contract, {"query": "damped oscillators"})
        assert "query" in asked
        assert result.ok is True
        assert result.assembled["inputs"]["query"] == "damped oscillators"
