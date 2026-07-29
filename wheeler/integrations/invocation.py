"""Service invocation intake: give meaning to a ServiceContract's `inputs` schema.

The registry treats `inputs` opaquely (a list of dicts). This module interprets
them so the router / plan acts can (1) INTERVIEW the scientist for the right
inputs, (2) VALIDATE the answers, and (3) ASSEMBLE the request to SHOW before
dispatch. Keeping that "what to ask / is it valid / what gets sent" logic here,
not in the act prose, is what makes the interview behavior TESTABLE: a fake user
can be scripted through ``validate_request`` deterministically.

Input port schema (per dict in a contract's ``inputs``):
  name         the input's name (becomes a request key)
  kind         node | choice | text
  required     bool; a required port must be answered before dispatch
  multi        bool; the port takes a LIST. A single-valued port handed a list of
               several is INVALID rather than silently taking one of them, which
               is the failure this field exists to remove: a service whose tool
               accepts several inputs but whose contract declared one could not be
               interviewed for the others, and nothing said so
  prompt       the question the interview asks
  node_type    (kind=node) the graph label to offer, e.g. Dataset / Question
  source       (kind=node) the graph query that lists the options
  options      (kind=choice) the allowed values
  options_from (kind=choice) "<dotted.module:callable>" asked for the allowed
               values at read time, so a port whose legal answers are OPEN (a
               plug-in registry the scientist extends) offers what is actually
               registered rather than a list frozen into the YAML. Falls back to
               the static ``options`` on any failure, so a broken or missing
               resolver degrades to today's behavior instead of emptying the port
  default      (kind=choice/text) value used when an OPTIONAL port is unanswered
  from         (kind=text) the name of an EARLIER port whose answers this one
               chooses among (``score_on`` picks from the datasets just named).
               Carried for the interview to render; not validated here, because
               the legal set is whatever the scientist answered a moment ago and
               is not knowable from the manifest

Note the layering: this module stays generic. WHICH callable a port asks is the
service's own business and lives in its registry entry, never here.
"""

from __future__ import annotations

import importlib
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
    options: tuple[str, ...] = ()  # kind=choice (resolved: see options_from)
    default: Any = None
    # kind=choice: "<dotted.module:callable>" consulted for `options` at read
    # time. Kept on the port (not consumed) so the interview can say where the
    # list came from, and so a test can assert the wiring without importing the
    # target.
    options_from: str = ""
    # The port takes a LIST of values rather than one. Declared per port because
    # it is a property of the TOOL: `wheeler llmsr init --data` is repeatable and
    # scoring one form against several tables is the point of the run, so a
    # contract that offered one dataset made the interview unable to ask for what
    # the tool can do.
    multi: bool = False
    # kind=text: the earlier port whose answers this one chooses among.
    from_: str = ""


def _resolve_options(spec: str) -> tuple[str, ...]:
    """Ask ``"<dotted.module:callable>"`` for a port's allowed values.

    Returns ``()`` on ANY failure (malformed spec, unimportable module, missing
    attribute, the call raising, a non-list or empty answer), which the caller
    reads as "use the static options". Degrading to the frozen list is always
    safe; emptying a choice port would make every answer invalid.

    Resolution happens here, at read time, rather than at import: the callable
    reports what is registered in the CALLING process, and this module must not
    drag a service's dependencies into every import of the registry.
    """
    module_path, sep, attr = str(spec or "").partition(":")
    if not sep or not module_path.strip() or not attr.strip():
        logger.warning(
            "options_from %r is not '<dotted.module:callable>'; using static options",
            spec,
        )
        return ()
    try:
        module = importlib.import_module(module_path.strip())
        values = getattr(module, attr.strip())()
    except Exception:
        logger.warning(
            "options_from %r did not resolve; using static options", spec, exc_info=True
        )
        return ()
    if not isinstance(values, (list, tuple)) or not values:
        logger.warning(
            "options_from %r returned %r, not a non-empty list; using static options",
            spec,
            values,
        )
        return ()
    return tuple(str(v) for v in values)


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
        options_from = str(raw.get("options_from", "")).strip()
        if options_from:
            # `or options`: a resolver that fails falls back to the static list.
            options = _resolve_options(options_from) or options
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
                options_from=options_from,
                multi=bool(raw.get("multi", False)),
                from_=str(raw.get("from", "")),
            )
        )
    return ports


def _has_value(provided: dict, name: str) -> bool:
    """Whether a port has an answer. An EMPTY list is not one.

    Checked explicitly because a multi port answered ``[]`` would otherwise pass
    ``not in (None, "")`` and count as answered, so a required port with no
    selections would dispatch instead of being asked again.
    """
    if name not in provided:
        return False
    value = provided[name]
    if value is None or value == "":
        return False
    if isinstance(value, (list, tuple)) and not value:
        return False
    return True


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

    ``ok`` iff no required port is missing and no value is illegal.
    Optional ports fall back to their ``default``; required ports are never
    silently defaulted (a required port with no value is reported ``missing``).

    Two things count as illegal. A ``choice`` value outside the port's options,
    which is the historic rule and is now applied to EVERY element of a multi
    port. And a list handed to a single-valued port, which is reported rather
    than truncated: quietly keeping one of several answers is precisely how a
    multi-input tool ends up running against one input while the scientist
    believes otherwise.
    """
    ports = input_ports(contract)
    missing: list[str] = []
    invalid: list[tuple[str, Any]] = []
    inputs: dict[str, Any] = {}
    for p in ports:
        if _has_value(provided, p.name):
            val = provided[p.name]
            values = list(val) if isinstance(val, (list, tuple)) else [val]
            if not p.multi and len(values) > 1:
                invalid.append((p.name, val))
            elif p.kind == "choice" and p.options:
                invalid.extend(
                    (p.name, v) for v in values if v not in p.options
                )
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
