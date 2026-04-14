"""Field-level validation and normalization for mutation tool arguments.

Each mutation tool has a set of required fields, optional typed fields,
and status enums. ``validate_and_normalize`` checks all of them in one
pass and returns structured errors the LLM can act on.

This is a leaf module: stdlib + pathlib only, no internal imports.
"""

from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# Required fields per tool (error if missing or empty string)
# ---------------------------------------------------------------------------

_REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "add_finding": ("description", "confidence"),
    "add_hypothesis": ("statement",),
    "add_question": ("question",),
    "add_dataset": ("path", "type", "description"),
    "add_paper": ("title",),
    "add_document": ("title", "path"),
    "add_note": ("content",),
    "add_script": ("path", "language"),
    "add_execution": ("kind", "description"),
}

# ---------------------------------------------------------------------------
# Status enums per tool
# ---------------------------------------------------------------------------

_STATUS_ENUMS: dict[str, tuple[str, ...]] = {
    "add_hypothesis": ("open", "supported", "rejected"),
    "add_document": ("draft", "revision", "final"),
    "add_execution": ("completed", "failed", "running"),
}

# ---------------------------------------------------------------------------
# Fields managed by _complete_provenance (skip validation)
# ---------------------------------------------------------------------------

_PROVENANCE_FIELDS = frozenset({
    "execution_kind", "used_entities", "execution_description",
    "agent_id", "session_id", "started_at", "ended_at",
})

# ---------------------------------------------------------------------------
# Per-field validators
# ---------------------------------------------------------------------------


def _check_confidence(value: object) -> tuple[object, str | None, str | None]:
    """Validate confidence is a float in [0.0, 1.0]. Coerces strings."""
    try:
        fval = float(value)
    except (ValueError, TypeError):
        return value, f"must be a number, got {type(value).__name__}", None
    if not (0.0 <= fval <= 1.0):
        return fval, "must be 0.0-1.0", None
    return fval, None, None


def _check_priority(value: object) -> tuple[object, str | None, str | None]:
    """Validate priority is an int in [1, 10]. Coerces strings/floats."""
    try:
        ival = int(value)
    except (ValueError, TypeError):
        return value, f"must be an integer, got {type(value).__name__}", None
    if not (1 <= ival <= 10):
        return ival, "must be 1-10", None
    return ival, None, None


def _check_tier(value: object) -> tuple[object, str | None, str | None]:
    """Validate tier is 'generated' or 'reference'. Normalizes case."""
    normalized = str(value).strip().lower()
    if normalized not in ("generated", "reference"):
        return value, f"must be 'generated' or 'reference', got '{value}'", None
    return normalized, None, None


def _check_year(value: object) -> tuple[object, str | None, str | None]:
    """Validate year is an int. Warns if 0 (unknown)."""
    try:
        ival = int(value)
    except (ValueError, TypeError):
        return value, f"must be an integer, got {type(value).__name__}", None
    warn = "year is 0 (unknown)" if ival == 0 else None
    return ival, None, warn


# Tools where path must point to an existing file (the artifact is the input).
# For other tools (add_finding, add_document), path may reference a file
# that will be created later, so missing path is only a warning.
_PATH_MUST_EXIST: frozenset[str] = frozenset({"add_dataset", "add_script"})


def _check_path(
    value: object, *, must_exist: bool = False,
) -> tuple[object, str | None, str | None]:
    """Normalize path to absolute. Error or warn if file does not exist."""
    s = str(value)
    if not s:
        return s, None, None
    resolved = Path(s).resolve()
    resolved_str = str(resolved)
    if not resolved.exists():
        msg = f"does not exist on disk: {resolved_str}"
        if must_exist:
            return resolved_str, msg, None
        return resolved_str, None, msg
    return resolved_str, None, None


def _check_status(
    value: object, tool_name: str,
) -> tuple[object, str | None, str | None]:
    """Validate status against tool-specific enum."""
    allowed = _STATUS_ENUMS.get(tool_name)
    if allowed is None:
        return value, None, None
    s = str(value)
    if s not in allowed:
        return value, f"must be one of {allowed}, got '{s}'", None
    return s, None, None


# ---------------------------------------------------------------------------
# Dispatch table: field name -> checker function
# ---------------------------------------------------------------------------

_FIELD_CHECKERS: dict[str, object] = {
    "confidence": _check_confidence,
    "priority": _check_priority,
    "tier": _check_tier,
    "year": _check_year,
    # path is handled separately (tool-aware: error vs warning)
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def validate_and_normalize(
    tool_name: str,
    args: dict,
) -> tuple[dict[str, dict], dict[str, str]]:
    """Validate and normalize mutation tool arguments in-place.

    Args:
        tool_name: The mutation tool name (e.g., "add_finding").
        args: The arguments dict. Modified in-place for normalization.

    Returns:
        ``(errors, warnings)`` where:

        - errors: ``{field: {"value": original, "error": message}}``
        - warnings: ``{field: message}``

    Only runs for tools listed in ``_REQUIRED_FIELDS``.
    Returns ``({}, {})`` for unknown or excluded tools (e.g. add_ledger).
    Collects ALL errors before returning (no short-circuit).
    """
    required = _REQUIRED_FIELDS.get(tool_name)
    if required is None:
        return {}, {}

    errors: dict[str, dict] = {}
    warnings: dict[str, str] = {}

    # 1. Check required fields are present and non-empty
    for field in required:
        val = args.get(field)
        # confidence=0.0 and priority=1 are valid, so only reject
        # missing keys and empty/whitespace strings.
        if val is None:
            errors[field] = {"value": None, "error": "required field is missing"}
        elif isinstance(val, str) and not val.strip():
            errors[field] = {"value": val, "error": "required, must be non-empty"}

    # 2. Run typed field validators (only when the field is present)
    for field, checker in _FIELD_CHECKERS.items():
        if field not in args:
            continue
        # Skip fields already flagged as missing/empty
        if field in errors:
            continue
        # Skip provenance fields
        if field in _PROVENANCE_FIELDS:
            continue

        original = args[field]
        normalized, error, warn = checker(original)

        if error:
            errors[field] = {"value": original, "error": error}
        else:
            # Write normalized value back in-place
            args[field] = normalized
        if warn:
            warnings[field] = warn

    # 3. Check path (tool-aware: dataset/script error, others warn)
    if "path" in args and "path" not in errors:
        original = args["path"]
        must_exist = tool_name in _PATH_MUST_EXIST
        normalized, error, warn = _check_path(original, must_exist=must_exist)
        if error:
            errors["path"] = {"value": original, "error": error}
        else:
            args["path"] = normalized
        if warn:
            warnings["path"] = warn

    # 4. Check status enum (tool-specific)
    if "status" in args and "status" not in errors:
        original = args["status"]
        normalized, error, warn = _check_status(original, tool_name)
        if error:
            errors["status"] = {"value": original, "error": error}

    return errors, warnings
