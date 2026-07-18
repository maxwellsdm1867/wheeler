"""Tests for the service-invocation intake (the interview schema + validator).

The interview lives in an act (a prompt), so the reliable guarantee that it asks
for the RIGHT information lives here, in tested Python: the schema each service
declares, and the validator that decides what is still missing / invalid. The
'fake user' e2e scripts a simulated scientist through the interview loop and
asserts the right questions get asked and the right request gets assembled.
"""

from __future__ import annotations

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
        # a dataset is required, and it is a Dataset graph node
        assert ports["dataset"].required is True
        assert ports["dataset"].kind == "node"
        assert ports["dataset"].node_type == "Dataset"
        # the metric must be asked (never silently defaulted) and offers mse/nmse
        assert ports["metric"].required is True
        assert ports["metric"].kind == "choice"
        assert set(ports["metric"].options) == {"mse", "nmse"}
        # selection strategy is offered with parsimony as the default
        assert ports["select"].kind == "choice"
        assert set(ports["select"].options) == {"parsimony", "ood", "fit"}
        assert ports["select"].default == "parsimony"
        # the linking question is optional
        assert ports["question"].required is False

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
# 2. Validator: it correctly identifies missing / invalid inputs
# ---------------------------------------------------------------------------


class TestValidator:
    def test_empty_flags_the_required_questions(self):
        contract = _contract("llmsr-discover")
        r = validate_request(contract, {})
        assert r.ok is False
        assert set(r.missing) == {"dataset", "metric"}  # exactly the must-asks

    def test_bad_choice_value_is_rejected(self):
        contract = _contract("llmsr-discover")
        r = validate_request(contract, {"dataset": "D-x", "metric": "banana"})
        assert r.ok is False
        assert ("metric", "banana") in r.invalid

    def test_complete_request_is_assembled_with_defaults(self):
        contract = _contract("llmsr-discover")
        r = validate_request(contract, {"dataset": "D-abc12345", "metric": "nmse"})
        assert r.ok is True
        assert r.assembled["service"] == "llmsr-discover"
        assert r.assembled["act"] == "/wh:llmsr-discover"
        assert r.assembled["inputs"]["dataset"] == "D-abc12345"
        assert r.assembled["inputs"]["metric"] == "nmse"
        # the optional select port fell back to its default (shown to the user)
        assert r.assembled["inputs"]["select"] == "parsimony"
        # the optional question port was not answered, so it is absent
        assert "question" not in r.assembled["inputs"]

    def test_required_input_is_never_silently_defaulted(self):
        contract = _contract("llmsr-discover")
        # metric has a default (nmse) but is required: with no answer it is MISSING,
        # not quietly filled in.
        r = validate_request(contract, {"dataset": "D-x"})
        assert r.ok is False
        assert "metric" in r.missing
        assert "metric" not in r.assembled["inputs"]


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
        fake_answers = {"dataset": "D-deadbeef", "metric": "mse"}
        asked, result = _run_interview(contract, fake_answers)

        # the interview ASKED for the dataset and the metric (the required inputs)
        assert "dataset" in asked
        assert "metric" in asked
        # it converged to a valid, correctly-filled request
        assert result.ok is True
        assert result.assembled["inputs"]["dataset"] == "D-deadbeef"
        assert result.assembled["inputs"]["metric"] == "mse"  # fake user's choice, not the default
        assert result.assembled["inputs"]["select"] == "parsimony"  # default for the optional port

    def test_interview_recovers_from_a_bad_answer(self):
        contract = _contract("llmsr-discover")
        # the fake user first gives a bad metric, then the correct one on retry
        provided = {"dataset": "D-1", "metric": "banana"}
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
