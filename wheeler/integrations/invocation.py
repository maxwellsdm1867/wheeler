"""Service invocation intake: give meaning to a ServiceContract's `inputs` schema.

The registry treats `inputs` opaquely (a list of dicts). This module interprets
them so the router / plan acts can (1) INTERVIEW the scientist for the right
inputs, (2) VALIDATE the answers, and (3) ASSEMBLE the request to SHOW before
dispatch. Keeping that "what to ask / is it valid / what gets sent" logic here,
not in the act prose, is what makes the interview behavior TESTABLE: a fake user
can be scripted through ``validate_request`` deterministically.

Input port schema (per dict in a contract's ``inputs``):
  name      the input's name (becomes a request key)
  kind      node | choice | text
  required  bool; a required port must be answered before dispatch
  prompt    the question the interview asks
  node_type (kind=node) the graph label to offer, e.g. Dataset / Question
  source    (kind=node) the graph query that lists the options
  options   (kind=choice) the allowed values
  default   (kind=choice/text) value used when an OPTIONAL port is unanswered
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from typing import Any

logger = logging.getLogger(__name__)

_VALID_KINDS = ("node", "choice", "text")


@dataclass(frozen=True)
class InputPort:
    name: str
    kind: str  # node | choice | text
    required: bool = False
    prompt: str = ""
    node_type: str = ""  # kind=node: the graph label (Dataset, Question, ...)
    source: str = ""  # kind=node: the graph query that offers options
    options: tuple[str, ...] = ()  # kind=choice
    default: Any = None


@dataclass
class ValidationResult:
    ok: bool
    missing: list[str]  # required ports with no value (the questions to ask)
    invalid: list[tuple[str, Any]]  # (name, bad_value) for choice violations
    assembled: dict[str, Any]  # {service, act, inputs} to show + dispatch


def input_ports(contract: Any) -> list[InputPort]:
    """Parse a contract's raw ``inputs`` into typed ports. Defensive: a malformed
    port is skipped (logged), never raises."""
    ports: list[InputPort] = []
    raw_inputs = getattr(contract, "inputs", None) or []
    for raw in raw_inputs:
        if not isinstance(raw, dict):
            continue
        name = str(raw.get("name", "")).strip()
        if not name:
            continue
        kind = str(raw.get("kind", "text")).strip().lower()
        if kind not in _VALID_KINDS:
            kind = "text"
        opts = raw.get("options")
        options = tuple(str(o) for o in opts) if isinstance(opts, list) else ()
        ports.append(
            InputPort(
                name=name,
                kind=kind,
                required=bool(raw.get("required", False)),
                prompt=str(raw.get("prompt", "")),
                node_type=str(raw.get("node_type", "")),
                source=str(raw.get("source", "")),
                options=options,
                default=raw.get("default"),
            )
        )
    return ports


def _has_value(provided: dict, name: str) -> bool:
    return name in provided and provided[name] not in (None, "")


def missing_inputs(contract: Any, provided: dict) -> list[str]:
    """Required ports the scientist has not answered yet: the next questions the
    interview must ask before it may dispatch."""
    return [
        p.name
        for p in input_ports(contract)
        if p.required and not _has_value(provided, p.name)
    ]


def validate_request(contract: Any, provided: dict) -> ValidationResult:
    """Check ``provided`` against the schema and assemble the request.

    ``ok`` iff no required port is missing and no choice value is illegal.
    Optional ports fall back to their ``default``; required ports are never
    silently defaulted (a required port with no value is reported ``missing``).
    """
    ports = input_ports(contract)
    missing: list[str] = []
    invalid: list[tuple[str, Any]] = []
    inputs: dict[str, Any] = {}
    for p in ports:
        if _has_value(provided, p.name):
            val = provided[p.name]
            if p.kind == "choice" and p.options and val not in p.options:
                invalid.append((p.name, val))
            inputs[p.name] = val
        elif p.required:
            missing.append(p.name)
        elif p.default is not None:
            inputs[p.name] = p.default
    return ValidationResult(
        ok=(not missing and not invalid),
        missing=missing,
        invalid=invalid,
        assembled={
            "service": getattr(contract, "id", ""),
            "act": getattr(contract, "act", ""),
            "inputs": inputs,
        },
    )


# --- convenience wrappers for the acts (called via a python -c one-liner) ---


def _find(config: Any, service_id: str) -> Any | None:
    from wheeler.integrations.registry import available_services

    sid = (service_id or "").strip().lower()
    for c in available_services(config):
        if c.id == sid:
            return c
    return None


def describe_inputs(service_id: str, config: Any = None) -> list[dict]:
    """The interview schema for an available service, as plain dicts (the act
    renders these as AskUserQuestion prompts). Empty if the service is unknown or
    unavailable."""
    from wheeler.config import load_config

    contract = _find(config or load_config(), service_id)
    if contract is None:
        return []
    return [asdict(p) for p in input_ports(contract)]


def check_request(service_id: str, provided: dict, config: Any = None) -> dict:
    """Validate a provided input set for an available service. Returns a JSON-able
    dict {ok, missing, invalid, assembled} the act uses to decide what to ask and
    what to show before dispatch."""
    from wheeler.config import load_config

    contract = _find(config or load_config(), service_id)
    if contract is None:
        return {"ok": False, "missing": [], "invalid": [],
                "assembled": {}, "error": f"unknown or unavailable service {service_id!r}"}
    result = validate_request(contract, provided)
    return {
        "ok": result.ok,
        "missing": result.missing,
        "invalid": result.invalid,
        "assembled": result.assembled,
    }
