"""Marshal-out (deterministic): ingest an Asta Theorizer artifact.

A marshal-out module, mirroring ``ingest.py`` and ``artifacts.py``: it imports
``execute_tool`` lazily (function-local), so every graph write routes through
the triple-write + write-receipt + trace-id + embedding wiring. Reads (paper
dedupe by corpus_id, edge existence for ``link_once``) reuse the same cached
backend the dispatch path uses, and reuse the shared helpers in ``_marshal.py``
(``_link_once`` / ``_edge_exists`` / ``_find_paper_by_corpus_id`` and the
persisted corpus_id index) plus ``register_output_artifact`` in ``artifacts.py``.

REAL Theorizer output shape (confirmed against a live ``generate-theories``
literature-theory-generation run, /tmp/theorizer_out2.json). The output is an
A2A Task::

    {
      "id": str, "kind": "task", "contextId": str,
      "metadata": {"run_id", "workflow_id", "cost", "time"},
      "status": {"state": "completed", "message": {"parts": [{"text"}]}},
      "artifacts": [...32...], "history": [...]
    }

Each artifact is ``{artifactId, name, description, metadata:{type}, parts:[...]}``
with ``metadata.type`` in {extraction-schema, theory_store, extraction, theory,
novelty}. We dispatch on that type:

  - ``theory`` (artifactId ``theory-N``): ``parts[0].data`` carries
    ``{id, name, description, subtype, entities, annotations, content}``.
    ``entities`` maps ``paper-<hash>`` -> ``{type:"PAPER", displayLabel,
    s2Metadata}`` (s2Metadata.corpusId is the corpus id; s2Metadata may be a
    stringified dict). ``annotations`` maps ``ann_id`` -> ``{entityId, type, text}``.
    ``content`` is a flat list of tree nodes ``{id, type, title, text, childIds,
    annotationIds}`` with type in {SECTIONS, SECTION, MARKDOWN}. The tree:
      * a top SECTIONS titled "Theory Statements" whose child SECTION nodes are
        the LAWS (the SECTION title is the law statement); each law SECTION has
        MARKDOWN children (the law body, a "Supporting evidence:" header, then
        bullet MARKDOWN nodes whose annotationIds point to annotations pointing
        to a PAPER entity = the supporting papers for that law).
      * a top SECTIONS titled "Predictions" (its text -> custom_predictions on
        the parent Finding).
      * a top SECTIONS titled "Conflicting & Unaccounted Evidence" (the PAPER
        entities annotated under it = the theory-level contradicting papers).
  - ``novelty`` (artifactId ``novelty-theory-N-M``): the novelty verdict for
    theory N, law index M. The verdict is the leading phrase of ``data.description``
    ("Explicit Established" -> established, "Derivable Unstated" -> derivable,
    "Genuinely New" -> new). Joined back to the right law Hypothesis by N and M.
  - ``extraction`` / ``extraction-schema`` / ``theory_store``: NOT mapped to
    nodes in v1 (reachable via the saved raw output).

Bucketing (each theory becomes a small provenance subgraph):
  - One Execution per RUN (kind ``theory-generation``, service ``asta:theorizer``),
    stamped with benchmark fields (run_id, cost, time) from Task.metadata.
  - The raw service output is saved durably (see artifacts.py) and registered as
    a Document (``W-``) node: Theorizer output is synthesized WRITING, not data.
    The raw node points at the saved path and carries benchmark metadata.
  - Per theory: a PARENT Finding (``artifact_type="theory"``, low confidence,
    title=name, description=description). Predictions text -> custom_predictions.
  - Per law SECTION: a Hypothesis (statement=law SECTION title); parent
    -[CONTAINS]-> Hypothesis. The law body markdown becomes custom_rationale.
    The novelty verdict is parked in custom_novelty via a follow-up update_node,
    NEVER in Hypothesis.status (acts rely on its open/supported/rejected enum).
  - supporting papers (PAPER entities referenced by a law's supporting-evidence
    annotations) -> add_paper (dedupe by corpus_id), Paper -[SUPPORTS]-> the law
    Hypothesis. contradicting papers (PAPER entities annotated under Conflicting
    and Unaccounted Evidence) -> Paper -[CONTRADICTS]-> the parent theory Finding
    (theory level, DECISION 1 default).
  - Provenance: the run Execution is WAS_GENERATED_BY the Wheeler-PRODUCED nodes
    only: the parent theory Findings, the law Hypotheses, and the raw Document
    node. Papers are REFERENCE ENTITIES, not produced by Wheeler, so they carry
    NO WAS_GENERATED_BY (per /wh:close and /wh:graph-link: "Papers are never
    orphans. They are reference entities, not produced by Wheeler"). Because the
    theories were DERIVED from the evidence, the run Execution -[USED]-> each
    supporting/contradicting evidence paper (the paper is a genuine input). If
    ``link_to`` is given, parent -[AROSE_FROM]-> link_to. If ``artifact_path`` is
    given, the raw output registers as a Document and each generated node (incl.
    papers) links WAS_DERIVED_FROM it (best-effort).

Invariants:
  - Defensive: every step tolerates missing pieces, counts and skips, never
    raises. A partial or shape-drifted artifact never aborts ingest.
  - Sequential writes only. Never ``asyncio.gather``: ``execute_tool`` reuses
    one cached backend singleton and Neo4j forbids concurrent queries.
  - link_once. Every edge is guarded by an existence check because the
    backend's ``create_relationship`` is a bare CREATE that would duplicate on
    re-run. Theories dedupe on a content hash, hypotheses on a content hash,
    papers on corpus_id, so re-ingest is a no-op.
  - One Execution per RUN, tagged service ``asta:theorizer``.
"""

from __future__ import annotations

import ast
import hashlib
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from wheeler.config import WheelerConfig
from wheeler.integrations.asta._marshal import (
    ImportReport,
    _find_execution,
    _find_paper_by_corpus_id,
    _link_once,
    _load_index,
    _paper_exists,
    _record_used,
    _save_index,
)
from wheeler.integrations.asta.schemas import _normalize_corpus_id

logger = logging.getLogger(__name__)

_SERVICE_TAG = "asta:theorizer"

# The raw Theorizer output is synthesized WRITING (theory prose), so its raw
# node is a Document (W-), NOT a Dataset. Reserve Dataset for genuine data.
_RAW_NODE_TYPE = "document"

# Persisted (content-hash -> Wheeler H-id) map so re-ingest of the same theory
# law reuses the existing Hypothesis instead of creating a duplicate. Kept
# separate from the shared corpus_id paper index (paper_finder_index.json),
# which we reuse for cross-tool paper dedupe.
_HYP_INDEX_REL_PATH = ".wheeler/integrations/theorizer_hyp_index.json"

# Persisted (content-hash -> Wheeler F-id) map for the per-theory parent
# Finding. A theory has no external id, so it dedupes on a content hash of its
# identity (name + description), mirroring the Hypothesis dedupe. Re-ingest of
# the same artifact reuses the existing parent Finding instead of duplicating.
_THEORY_INDEX_REL_PATH = ".wheeler/integrations/theorizer_theory_index.json"

# Valid novelty verdicts. Anything else is normalized to "" (unknown) and not
# written, so the custom bag only ever holds a known verdict.
_NOVELTY_VERDICTS = {"established", "derivable", "new"}

# Title substrings that identify the three top-level SECTIONS in a theory's
# content tree. Matched case-insensitively on a substring so prefixes/suffixes
# ("3 Theory Statements", "Conflicting & Unaccounted Evidence") still match.
_THEORY_STATEMENTS_MARKER = "theory statement"
_PREDICTIONS_MARKER = "prediction"
_CONFLICTING_MARKER = "conflicting"

# Substring that marks the "Supporting evidence:" header MARKDOWN inside a law
# SECTION. The law body is the MARKDOWN child(ren) that precede it.
_SUPPORTING_EVIDENCE_MARKER = "supporting evidence"


# ---------------------------------------------------------------------------
# Parse records (intermediate, shape-drift tolerant, never raises)
# ---------------------------------------------------------------------------


@dataclass
class PaperRef:
    """A supporting or contradicting paper reference inside a theory."""

    corpus_id: str
    title: str
    custom: dict[str, Any] = field(default_factory=dict)


@dataclass
class LawRecord:
    """One law/statement inside a theory (becomes a Hypothesis)."""

    text: str
    rationale: str = ""
    novelty: str = ""
    supporting: list[PaperRef] = field(default_factory=list)


@dataclass
class TheoryRecord:
    """One theory (becomes a parent Finding with artifact_type=theory)."""

    name: str
    summary: str
    laws: list[LawRecord] = field(default_factory=list)
    contradicting: list[PaperRef] = field(default_factory=list)
    predictions: str = ""
    custom: dict[str, Any] = field(default_factory=dict)


@dataclass
class RunMeta:
    """Benchmark fields lifted from the A2A Task.metadata block."""

    run_id: str = ""
    cost: float | None = None
    time: float | None = None
    model: str = ""

    def custom_bag(self) -> dict[str, Any]:
        """Benchmark scalars to stamp into a node's custom bag (queryable)."""
        bag: dict[str, Any] = {"service": _SERVICE_TAG}
        if self.run_id:
            bag["run_id"] = self.run_id
        if self.cost is not None:
            bag["cost"] = self.cost
        if self.time is not None:
            bag["time"] = self.time
        if self.model:
            bag["model"] = self.model
        return bag


# ---------------------------------------------------------------------------
# Small coercion helpers (defensive)
# ---------------------------------------------------------------------------


def _first(d: dict[str, Any], *keys: str, default: Any = None) -> Any:
    """Return the first present, non-None value among ``keys`` in ``d``."""
    for key in keys:
        if key in d and d[key] is not None:
            return d[key]
    return default


def _as_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value)


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def _normalize_novelty(value: Any) -> str:
    """Coerce a novelty verdict to a known token, or "" if unrecognized."""
    s = _as_str(value).lower()
    return s if s in _NOVELTY_VERDICTS else ""


def _verdict_from_description(text: Any) -> str:
    """Map a novelty artifact's leading description phrase to a known verdict.

    The real shape leads the description with a two-word verdict tag:
      "Explicit Established." -> established
      "Derivable Unstated."   -> derivable
      "Genuinely New."        -> new
    Matched case-insensitively on the presence of the canonical token anywhere
    in the leading clause, so minor wording drift ("Established", "Derivable",
    "New") still resolves. Returns "" when no token is recognized.
    """
    s = _as_str(text).lower()
    head = s[:80]  # only the leading clause carries the verdict
    if "established" in head:
        return "established"
    if "derivable" in head:
        return "derivable"
    if "new" in head:
        return "new"
    return ""


def _coerce_dict(value: Any) -> dict[str, Any]:
    """Return ``value`` as a dict, parsing a stringified dict if needed.

    s2Metadata may arrive as a real dict OR as a stringified Python/JSON dict.
    Try JSON first, then ``ast.literal_eval`` (handles single-quoted Python
    repr). Returns ``{}`` on anything unparseable.
    """
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        for parser in (json.loads, ast.literal_eval):
            try:
                parsed = parser(value)
            except (ValueError, SyntaxError, TypeError):
                continue
            if isinstance(parsed, dict):
                return parsed
    return {}


def _scalar_or_none(value: Any) -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, (str, int, float)):
        return value
    return None


# ---------------------------------------------------------------------------
# Entity / annotation -> PaperRef
# ---------------------------------------------------------------------------


def _paper_ref_from_entity(entity: Any) -> PaperRef | None:
    """Build a PaperRef from a theory ``entities`` PAPER entry, or None.

    Reads corpus_id from ``s2Metadata.corpusId`` (s2Metadata may be a
    stringified dict). Title falls back from s2Metadata.title to displayLabel.
    Long-tail scalars (year, venue, journal) are parked in the custom bag.
    """
    if not isinstance(entity, dict):
        return None
    if _as_str(entity.get("type")).upper() not in ("", "PAPER"):
        return None
    s2 = _coerce_dict(entity.get("s2Metadata"))
    corpus_id = _normalize_corpus_id(
        _first(s2, "corpusId", "corpus_id", "corpusid")
    )
    title = _as_str(
        _first(s2, "title", default="")
        or entity.get("displayLabel")
        or ""
    )
    if not corpus_id and not title:
        return None
    custom: dict[str, Any] = {}
    for src_key, dst_key in (
        ("year", "year"),
        ("venue", "venue"),
        ("journal", "journal"),
    ):
        val = _scalar_or_none(s2.get(src_key))
        if val is not None and val != "":
            custom[dst_key] = val
    return PaperRef(corpus_id=corpus_id, title=title, custom=custom)


def _entity_id_to_paper_ref(
    entity_id: str,
    entities: dict[str, Any],
    cache: dict[str, PaperRef | None],
) -> PaperRef | None:
    """Resolve an entity id to a PaperRef, memoized within one theory."""
    if entity_id in cache:
        return cache[entity_id]
    ref = _paper_ref_from_entity(entities.get(entity_id))
    cache[entity_id] = ref
    return ref


# ---------------------------------------------------------------------------
# Content-tree walking
# ---------------------------------------------------------------------------


def _index_content(content: Any) -> dict[str, dict[str, Any]]:
    """Index a content list into an id -> node map (defensive)."""
    nodes: dict[str, dict[str, Any]] = {}
    if not isinstance(content, list):
        return nodes
    for node in content:
        if isinstance(node, dict):
            nid = _as_str(node.get("id"))
            if nid:
                nodes[nid] = node
    return nodes


def _find_top_sections(
    content: Any, nodes: dict[str, dict[str, Any]], marker: str
) -> dict[str, Any] | None:
    """Find the top-level SECTIONS node whose title contains ``marker``."""
    if not isinstance(content, list):
        return None
    for node in content:
        if not isinstance(node, dict):
            continue
        if _as_str(node.get("type")).upper() != "SECTIONS":
            continue
        if marker in _as_str(node.get("title")).lower():
            return node
    return None


def _collect_annotation_ids(
    node_id: str, nodes: dict[str, dict[str, Any]], acc: list[str], seen: set[str]
) -> None:
    """Recursively collect every annotationId under ``node_id`` (cycle-safe)."""
    if node_id in seen:
        return
    seen.add(node_id)
    node = nodes.get(node_id)
    if not node:
        return
    ann_ids = node.get("annotationIds")
    if isinstance(ann_ids, list):
        acc.extend(_as_str(a) for a in ann_ids if a)
    child_ids = node.get("childIds")
    if isinstance(child_ids, list):
        for child in child_ids:
            _collect_annotation_ids(_as_str(child), nodes, acc, seen)


def _papers_from_annotations(
    ann_ids: list[str],
    annotations: dict[str, Any],
    entities: dict[str, Any],
    cache: dict[str, PaperRef | None],
) -> list[PaperRef]:
    """Resolve annotation ids -> entityId -> PaperRef, deduped by corpus_id.

    A paper cited by several bullets resolves once; corpus-id-less refs dedupe
    on title so a malformed entity is not double counted.
    """
    refs: list[PaperRef] = []
    seen_keys: set[str] = set()
    for ann_id in ann_ids:
        ann = annotations.get(ann_id)
        if not isinstance(ann, dict):
            continue
        entity_id = _as_str(ann.get("entityId"))
        if not entity_id:
            continue
        ref = _entity_id_to_paper_ref(entity_id, entities, cache)
        if ref is None:
            continue
        key = ref.corpus_id or f"title:{ref.title}"
        if key in seen_keys:
            continue
        seen_keys.add(key)
        refs.append(ref)
    return refs


def _parse_law_section(
    law_node: dict[str, Any],
    nodes: dict[str, dict[str, Any]],
    annotations: dict[str, Any],
    entities: dict[str, Any],
    cache: dict[str, PaperRef | None],
) -> LawRecord | None:
    """Parse one law SECTION into a LawRecord, or None if it has no statement.

    The SECTION title is the law statement. Its MARKDOWN children are, in order:
    the law body (one or more MARKDOWN nodes preceding the "Supporting evidence:"
    header), the header itself, then bullet MARKDOWN nodes carrying annotationIds
    that point to the supporting papers. Supporting papers are gathered from the
    annotationIds on every descendant of the law SECTION, so the body order does
    not matter for the edges.
    """
    statement = _as_str(law_node.get("title"))
    if not statement:
        return None

    body_parts: list[str] = []
    hit_supporting = False
    child_ids = law_node.get("childIds")
    if isinstance(child_ids, list):
        for child_id in child_ids:
            child = nodes.get(_as_str(child_id))
            if not child:
                continue
            text = _as_str(child.get("text"))
            if _SUPPORTING_EVIDENCE_MARKER in text.lower():
                hit_supporting = True
                continue
            # Body = the MARKDOWN text that precedes the supporting-evidence
            # header (typically a single node). Two guards keep evidence bullets
            # out of the rationale: stop once the header is seen, and skip any
            # node carrying annotationIds (those are evidence bullets, which
            # reference a PAPER entity; the law body carries no annotations).
            if hit_supporting or not text:
                continue
            if child.get("annotationIds"):
                hit_supporting = True
                continue
            body_parts.append(text)

    # Supporting papers: every annotation under this law SECTION resolves to a
    # PAPER entity. (The body / header nodes carry no annotationIds, so this is
    # exactly the supporting-evidence bullets.)
    ann_ids: list[str] = []
    _collect_annotation_ids(_as_str(law_node.get("id")), nodes, ann_ids, set())
    supporting = _papers_from_annotations(ann_ids, annotations, entities, cache)

    rationale = "\n\n".join(p for p in body_parts if p).strip()
    return LawRecord(
        text=statement,
        rationale=rationale,
        supporting=supporting,
    )


def _collect_section_text(
    section_node: dict[str, Any], nodes: dict[str, dict[str, Any]]
) -> str:
    """Flatten the MARKDOWN text under a top SECTIONS node (e.g. Predictions)."""
    parts: list[str] = []
    seen: set[str] = set()

    def _walk(nid: str) -> None:
        if nid in seen:
            return
        seen.add(nid)
        node = nodes.get(nid)
        if not node:
            return
        title = _as_str(node.get("title"))
        if title and _as_str(node.get("type")).upper() == "SECTION":
            parts.append(f"**{title}**")
        text = _as_str(node.get("text"))
        if text:
            parts.append(text)
        child_ids = node.get("childIds")
        if isinstance(child_ids, list):
            for child in child_ids:
                _walk(_as_str(child))

    child_ids = section_node.get("childIds")
    if isinstance(child_ids, list):
        for child in child_ids:
            _walk(_as_str(child))
    return "\n\n".join(p for p in parts if p).strip()


def _parse_theory_artifact(
    artifact: dict[str, Any],
) -> TheoryRecord | None:
    """Parse one ``theory`` artifact's ``parts[0].data`` into a TheoryRecord."""
    data = _artifact_data(artifact)
    if not isinstance(data, dict):
        return None

    name = _as_str(_first(data, "name", "id", default="")) or _as_str(
        artifact.get("name")
    )
    summary = _as_str(_first(data, "description", default="")) or _as_str(
        artifact.get("description")
    )
    raw_entities = data.get("entities")
    entities: dict[str, Any] = raw_entities if isinstance(raw_entities, dict) else {}
    raw_annotations = data.get("annotations")
    annotations: dict[str, Any] = (
        raw_annotations if isinstance(raw_annotations, dict) else {}
    )
    content = data.get("content")
    nodes = _index_content(content)
    cache: dict[str, PaperRef | None] = {}

    # --- Laws (Theory Statements SECTIONS -> SECTION children) ---
    laws: list[LawRecord] = []
    statements = _find_top_sections(content, nodes, _THEORY_STATEMENTS_MARKER)
    if statements:
        child_ids = statements.get("childIds")
        if isinstance(child_ids, list):
            for law_id in child_ids:
                law_node = nodes.get(_as_str(law_id))
                if not law_node:
                    continue
                law = _parse_law_section(
                    law_node, nodes, annotations, entities, cache
                )
                if law is not None:
                    laws.append(law)

    # --- Conflicting / Unaccounted evidence (theory-level contradicting) ---
    contradicting: list[PaperRef] = []
    conflicting = _find_top_sections(content, nodes, _CONFLICTING_MARKER)
    if conflicting:
        ann_ids: list[str] = []
        _collect_annotation_ids(
            _as_str(conflicting.get("id")), nodes, ann_ids, set()
        )
        contradicting = _papers_from_annotations(
            ann_ids, annotations, entities, cache
        )

    # --- Predictions text -> parent Finding custom ---
    predictions = ""
    pred_section = _find_top_sections(content, nodes, _PREDICTIONS_MARKER)
    if pred_section:
        predictions = _collect_section_text(pred_section, nodes)

    if not name and not laws:
        logger.warning(
            "parse_theorizer: theory artifact %r has no name and no laws, skipping",
            _as_str(artifact.get("artifactId")),
        )
        return None
    if not name:
        name = summary[:60] or "Untitled theory"

    custom: dict[str, Any] = {}
    if laws:
        custom["law_count"] = len(laws)
    if contradicting:
        custom["contradicting_count"] = len(contradicting)

    return TheoryRecord(
        name=name,
        summary=summary,
        laws=laws,
        contradicting=contradicting,
        predictions=predictions,
        custom=custom,
    )


# ---------------------------------------------------------------------------
# A2A Task parsing (top level)
# ---------------------------------------------------------------------------


def _artifact_data(artifact: dict[str, Any]) -> Any:
    """Return ``parts[0].data`` from an artifact, or None (defensive)."""
    parts = artifact.get("parts")
    if not isinstance(parts, list) or not parts:
        return None
    part0 = parts[0]
    if not isinstance(part0, dict):
        return None
    return part0.get("data")


def _artifact_type(artifact: dict[str, Any]) -> str:
    """Return the artifact's ``metadata.type`` token (lower-cased)."""
    meta = artifact.get("metadata")
    if isinstance(meta, dict):
        return _as_str(meta.get("type")).lower()
    return ""


def _parse_run_meta(doc: dict[str, Any]) -> RunMeta:
    """Lift benchmark fields from the A2A Task.metadata block (defensive)."""
    meta = doc.get("metadata") if isinstance(doc, dict) else None
    if not isinstance(meta, dict):
        return RunMeta()
    return RunMeta(
        run_id=_as_str(_first(meta, "run_id", "workflow_id", default="")),
        cost=_as_float(meta.get("cost")),
        time=_as_float(meta.get("time")),
        model=_as_str(meta.get("model")),
    )


@dataclass
class _NoveltyEntry:
    """A novelty verdict plus the law statement the verdict's data names.

    ``name`` (stripped of the ``Novelty:`` prefix) carries the EXACT law
    statement, so the positional (theory_N, law_M) join can be cross-checked
    against the law title to surface any future M/position drift instead of
    silently misattributing a verdict.
    """

    verdict: str
    name: str = ""


_NOVELTY_NAME_PREFIX = "novelty:"


def _novelty_name(value: Any) -> str:
    """Return the novelty data.name with a leading 'Novelty:' prefix stripped."""
    s = _as_str(value)
    if s.lower().startswith(_NOVELTY_NAME_PREFIX):
        return s[len(_NOVELTY_NAME_PREFIX) :].strip()
    return s


def _novelty_index(
    artifacts: list[Any],
) -> dict[tuple[int, int], _NoveltyEntry]:
    """Map (theory_N, law_M) -> _NoveltyEntry from every ``novelty`` artifact.

    The artifactId is ``novelty-theory-N-M``; N keys the theory (theory-N) and
    M is the 0-based law index within that theory. The verdict is read from the
    leading phrase of the novelty data's description; the data ``name`` (minus
    its ``Novelty:`` prefix) is the law statement, kept for a join cross-check.
    Unparseable ids/verdicts are skipped.
    """
    index: dict[tuple[int, int], _NoveltyEntry] = {}
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            continue
        if _artifact_type(artifact) != "novelty":
            continue
        aid = _as_str(artifact.get("artifactId"))
        if not aid.startswith("novelty-theory-"):
            continue
        rest = aid[len("novelty-theory-") :]
        try:
            n_str, m_str = rest.rsplit("-", 1)
            theory_n = int(n_str)
            law_m = int(m_str)
        except (ValueError, AttributeError):
            continue
        data = _artifact_data(artifact)
        desc = data.get("description") if isinstance(data, dict) else None
        name = _novelty_name(data.get("name") if isinstance(data, dict) else None)
        verdict = _verdict_from_description(desc)
        if not verdict:
            # Fall back to the artifact-level description / name.
            verdict = _verdict_from_description(
                artifact.get("description")
            ) or _normalize_novelty(artifact.get("name"))
        if verdict:
            index[(theory_n, law_m)] = _NoveltyEntry(verdict=verdict, name=name)
    return index


def parse_theorizer(doc: Any) -> tuple[list[TheoryRecord], RunMeta]:
    """Parse an Asta Theorizer A2A Task into TheoryRecords + run metadata.

    Returns ``(theories, run_meta)``. Defensive throughout: a doc that is not an
    A2A Task, or has no parseable theory artifacts, yields ``([], RunMeta())`` so
    a partial artifact never aborts ingest. Novelty verdicts are joined onto each
    theory's laws by (theory index, law index) derived from the artifactIds.
    """
    if not isinstance(doc, dict):
        logger.warning(
            "parse_theorizer: doc is not an A2A Task dict, got %s",
            type(doc).__name__,
        )
        return [], RunMeta()

    artifacts = doc.get("artifacts")
    if not isinstance(artifacts, list):
        logger.warning("parse_theorizer: no 'artifacts' list in Task")
        return [], _parse_run_meta(doc)

    run_meta = _parse_run_meta(doc)
    novelty = _novelty_index(artifacts)

    records: list[TheoryRecord] = []
    skipped = 0
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            skipped += 1
            continue
        atype = _artifact_type(artifact)
        if atype != "theory":
            # extraction / extraction-schema / theory_store / novelty: not mapped
            # to nodes in v1 (reachable via the saved raw output).
            continue
        record = _parse_theory_artifact(artifact)
        if record is None:
            skipped += 1
            continue
        # Join novelty verdicts by the artifact's theory index (theory-N). The
        # M index is the 0-based law SECTION position; cross-check the novelty
        # data.name (the law statement) against the joined law title so any
        # future M/position drift logs a warning instead of silently
        # misattributing a verdict.
        theory_n = _theory_number(artifact)
        if theory_n is not None:
            for law_idx, law in enumerate(record.laws):
                entry = novelty.get((theory_n, law_idx))
                if entry is None or not entry.verdict:
                    continue
                if entry.name and not _names_align(entry.name, law.text):
                    logger.warning(
                        "parse_theorizer: novelty name/law mismatch at "
                        "theory-%d law %d (novelty names %r, law is %r); "
                        "applying positional verdict anyway",
                        theory_n,
                        law_idx,
                        entry.name[:60],
                        law.text[:60],
                    )
                law.novelty = entry.verdict
            # Roll novelty counts into the theory custom bag for queryability.
            counts: dict[str, int] = {}
            for law in record.laws:
                if law.novelty:
                    counts[law.novelty] = counts.get(law.novelty, 0) + 1
            for verdict, count in counts.items():
                record.custom[f"novelty_{verdict}_count"] = count
        records.append(record)

    if skipped:
        logger.info(
            "parse_theorizer: skipped %d unparseable artifact(s)", skipped
        )
    return records, run_meta


def _names_align(novelty_name: str, law_text: str) -> bool:
    """Return True if a novelty data.name matches the joined law statement.

    The novelty name and the law SECTION title both carry the law statement, so
    a positional join is correct when one substring-contains the other (after a
    lowercase strip). The novelty name may be a truncated prefix of the law (or
    vice versa), so a directional substring test in either direction passes. An
    empty name is treated as aligned (nothing to cross-check against).
    """
    a = novelty_name.strip().lower()
    b = law_text.strip().lower()
    if not a or not b:
        return True
    return a in b or b in a


def _theory_number(artifact: dict[str, Any]) -> int | None:
    """Extract N from a ``theory-N`` artifactId, or None."""
    aid = _as_str(artifact.get("artifactId"))
    if not aid.startswith("theory-"):
        return None
    try:
        return int(aid[len("theory-") :])
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Content-hash dedupe indices (no external id, so key on content)
# ---------------------------------------------------------------------------


def _hyp_index_path() -> Path:
    return Path(_HYP_INDEX_REL_PATH)


def _load_hyp_index() -> dict[str, str]:
    path = _hyp_index_path()
    try:
        if path.exists():
            data = json.loads(path.read_text())
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items()}
    except (OSError, json.JSONDecodeError):
        logger.warning("theorizer: could not read hyp index %s, starting fresh", path)
    return {}


def _save_hyp_index(index: dict[str, str]) -> None:
    path = _hyp_index_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(index, indent=2, sort_keys=True))
        tmp.replace(path)
    except OSError:
        logger.error(
            "theorizer: could not persist hyp index %s (best-effort)",
            path,
            exc_info=True,
        )


def _hyp_key(theory_name: str, law_text: str) -> str:
    """Stable content hash for a (theory, law) pair (the Hypothesis dedupe key)."""
    digest = hashlib.sha256(f"{theory_name}\x00{law_text}".encode()).hexdigest()
    return digest[:16]


def _theory_index_path() -> Path:
    return Path(_THEORY_INDEX_REL_PATH)


def _load_theory_index() -> dict[str, str]:
    path = _theory_index_path()
    try:
        if path.exists():
            data = json.loads(path.read_text())
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items()}
    except (OSError, json.JSONDecodeError):
        logger.warning(
            "theorizer: could not read theory index %s, starting fresh", path
        )
    return {}


def _save_theory_index(index: dict[str, str]) -> None:
    path = _theory_index_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(index, indent=2, sort_keys=True))
        tmp.replace(path)
    except OSError:
        logger.error(
            "theorizer: could not persist theory index %s (best-effort)",
            path,
            exc_info=True,
        )


def _theory_key(theory_name: str, summary: str) -> str:
    """Stable content hash for a theory (the parent Finding dedupe key)."""
    digest = hashlib.sha256(f"{theory_name}\x00{summary}".encode()).hexdigest()
    return digest[:16]


async def _finding_exists(backend, config: WheelerConfig, finding_id: str) -> bool:
    """Return True if a Finding with this id still lives in the graph.

    Guards the persisted theory index against staleness (a deleted node would
    otherwise leave a dangling id that re-ingest would link to). Project-aware,
    mirroring the read scoping in the query handlers.
    """
    ptag = getattr(config.neo4j, "project_tag", "") or ""
    if ptag:
        query = (
            "MATCH (f:Finding {id: $id}) "
            "WHERE f._wheeler_project = $ptag RETURN f.id AS id LIMIT 1"
        )
        params = {"id": finding_id, "ptag": ptag}
    else:
        query = "MATCH (f:Finding {id: $id}) RETURN f.id AS id LIMIT 1"
        params = {"id": finding_id}
    rows = await backend.run_cypher(query, params)
    return bool(rows)


async def _hypothesis_exists(backend, config: WheelerConfig, hyp_id: str) -> bool:
    """Return True if a Hypothesis with this id still lives in the graph.

    Guards the persisted hyp index against staleness (a deleted node would
    otherwise leave a dangling id that re-ingest would link to). Project-aware,
    mirroring the read scoping in the query handlers.
    """
    ptag = getattr(config.neo4j, "project_tag", "") or ""
    if ptag:
        query = (
            "MATCH (h:Hypothesis {id: $id}) "
            "WHERE h._wheeler_project = $ptag RETURN h.id AS id LIMIT 1"
        )
        params = {"id": hyp_id, "ptag": ptag}
    else:
        query = "MATCH (h:Hypothesis {id: $id}) RETURN h.id AS id LIMIT 1"
        params = {"id": hyp_id}
    rows = await backend.run_cypher(query, params)
    return bool(rows)


# ---------------------------------------------------------------------------
# Ingest
# ---------------------------------------------------------------------------


async def ingest_theorizer(
    doc: dict[str, Any],
    *,
    link_to: str | None = None,
    config: WheelerConfig,
    artifact_path: str | None = None,
    used_inputs: list[str] | None = None,
) -> ImportReport:
    """Ingest a parsed Asta Theorizer A2A Task into the knowledge graph.

    Args:
        doc: The Theorizer A2A Task dict, from transport.run_asta.
        link_to: Optional node id (Question/Plan) every theory parent is linked
            to via AROSE_FROM.
        config: Active Wheeler config.
        artifact_path: Optional path to the raw service output file. When given,
            it is copied into the durable raw store and registered as a Document
            node (Theorizer output is synthesized writing, not data), linked
            WAS_GENERATED_BY the run Execution, and every generated node is
            linked WAS_DERIVED_FROM it. Best-effort: an artifact failure never
            breaks theory ingest.
        used_inputs: Optional graph node ids the marshal-in consumed to build
            the request: the link target (the Question/Plan that motivated the
            run) plus the Finding ids seeded into the Theorizer extraction
            payload. The run Execution -[USED]-> each one that exists in the
            graph (existence-guarded, link_once): input-side provenance, on top
            of the per-evidence-paper USED edges. A missing id is skipped and
            logged, never fabricated.

    Returns:
        An ImportReport with created / deduped / linked / skipped / used counts.
        ``paper_ids`` collects every Paper touched (created or deduped).
    """
    from wheeler.tools.graph_tools import _get_backend, execute_tool

    report = ImportReport()
    theories, run_meta = parse_theorizer(doc)
    if not theories:
        logger.warning("ingest_theorizer: no parseable theories in artifact")
        return report

    backend = await _get_backend(config)
    paper_index = _load_index()
    hyp_index = _load_hyp_index()
    theory_index = _load_theory_index()

    # One Execution per RUN, tagged with the service. session_id correlates
    # every node written this turn (validate_contract audits on session_id).
    # Prefer the run_id from Task.metadata so the session is the real run.
    status = doc.get("status") if isinstance(doc, dict) else {}
    state_msg = ""
    if isinstance(status, dict):
        msg = status.get("message")
        if isinstance(msg, dict):
            parts = msg.get("parts")
            if isinstance(parts, list) and parts and isinstance(parts[0], dict):
                state_msg = _as_str(parts[0].get("text"))[:80]
    session_id = run_meta.run_id or (
        f"asta-th-{abs(hash(state_msg)) & 0xffffffff:08x}"
    )
    # The Execution is itself idempotent: re-ingesting the same artifact reuses
    # the existing Execution (keyed on service + session_id, the stable run id)
    # instead of creating a duplicate node and stale WAS_GENERATED_BY edges.
    exec_id = await _find_execution(
        backend, config, service=_SERVICE_TAG, session_id=session_id
    )
    if not exec_id:
        exec_result = json.loads(
            await execute_tool(
                "add_execution",
                {
                    "kind": "theory-generation",
                    "description": f"Asta Theorizer: {state_msg or run_meta.run_id}",
                    "agent_id": "asta",
                    "status": "completed",
                    "session_id": session_id,
                    "service": _SERVICE_TAG,
                },
                config,
            )
        )
        exec_id = exec_result.get("node_id", "")
        # Stamp benchmark fields (run_id, cost, time, model) onto the Execution
        # so runs are benchmarkable later (custom_run_id/custom_cost/custom_time).
        if exec_id:
            await _stamp_custom(execute_tool, config, exec_id, run_meta.custom_bag())
    report.execution_id = exec_id

    # Input-side provenance: the marshal-in built this request FROM graph nodes
    # (the link target that motivated the run plus the Finding ids seeded into
    # the extraction payload), so the run USED them. This is on TOP of the
    # per-evidence-paper USED edges added in _ingest_paper_edge; link_once
    # collapses any overlap. Existence-guarded, so a missing id is skipped, never
    # fabricated; re-ingest dedupes.
    if exec_id and used_inputs:
        report.used += await _record_used(backend, config, exec_id, used_inputs)

    # The raw service output is synthesized WRITING, so it registers as a
    # Document (W-) node (not a Dataset). register_output_artifact copies the
    # ephemeral file into the durable raw store, registers the right node type,
    # stamps benchmark fields, and links it WAS_GENERATED_BY the Execution.
    # Best-effort: returns None on any failure and never raises.
    artifact_id: str | None = None
    try:
        from wheeler.integrations.asta.artifacts import register_output_artifact

        artifact_id = await register_output_artifact(
            artifact_path,
            execution_id=exec_id,
            service=_SERVICE_TAG,
            config=config,
            node_type=_RAW_NODE_TYPE,
            run_id=run_meta.run_id,
            benchmark=run_meta.custom_bag(),
            description=f"{_SERVICE_TAG} raw output",
        )
    except Exception:
        logger.warning(
            "ingest_theorizer: artifact registration raised (best-effort)",
            exc_info=True,
        )
    if artifact_id:
        report.artifact = artifact_id

    # corpus_id -> P-id for papers touched this run, so a paper cited by two
    # laws is created once and reused across both.
    seen_papers: dict[str, str] = {}

    for theory in theories:
        await _ingest_one_theory(
            backend=backend,
            execute_tool=execute_tool,
            config=config,
            theory=theory,
            link_to=link_to,
            session_id=session_id,
            exec_id=exec_id,
            artifact_id=artifact_id,
            paper_index=paper_index,
            hyp_index=hyp_index,
            theory_index=theory_index,
            seen_papers=seen_papers,
            report=report,
        )

    _save_index(paper_index)
    _save_hyp_index(hyp_index)
    _save_theory_index(theory_index)
    logger.info(
        "ingest_theorizer: created=%d deduped=%d linked=%d skipped=%d "
        "used=%d (exec=%s)",
        report.created,
        report.deduped,
        report.linked,
        report.skipped,
        report.used,
        exec_id,
    )
    return report


async def _ingest_one_theory(
    *,
    backend,
    execute_tool,
    config: WheelerConfig,
    theory: TheoryRecord,
    link_to: str | None,
    session_id: str,
    exec_id: str,
    artifact_id: str | None,
    paper_index: dict[str, str],
    hyp_index: dict[str, str],
    theory_index: dict[str, str],
    seen_papers: dict[str, str],
    report: ImportReport,
) -> None:
    """Bucket one theory into a parent Finding + law Hypotheses + paper edges."""
    # PARENT = a Finding with artifact_type="theory", low confidence (generated,
    # not yet evidence-grounded). A theory has no external id, so it dedupes on a
    # content hash of (name, summary): re-ingest of the same artifact reuses the
    # existing parent instead of creating a duplicate.
    theory_key = _theory_key(theory.name, theory.summary)
    parent_id = theory_index.get(theory_key)
    if parent_id and not await _finding_exists(backend, config, parent_id):
        # Stale index entry (the node was deleted); drop it and recreate.
        parent_id = None

    if parent_id:
        report.deduped += 1
    else:
        parent_args: dict[str, Any] = {
            "description": theory.summary or theory.name,
            "title": theory.name[:100],
            "confidence": 0.3,
            "artifact_type": "theory",
            "session_id": session_id,
            "service": _SERVICE_TAG,
        }
        parent_result = json.loads(
            await execute_tool("add_finding", parent_args, config)
        )
        parent_id = parent_result.get("node_id")
        if not parent_id or "error" in parent_result:
            logger.warning(
                "ingest_theorizer: add_finding failed for theory %r", theory.name
            )
            report.skipped += 1
            return
        report.created += 1
        theory_index[theory_key] = parent_id

        # Park the theory-level custom scalars (law_count, novelty_*_count,
        # contradicting_count) plus the predictions text so they are queryable.
        # add_finding does not forward custom into create_node, so stamp it via
        # update_node (custom is a first-class NodeBase field, so the update
        # allow-list accepts it; the backend flattens it to custom_<key>).
        parent_custom: dict[str, Any] = dict(theory.custom)
        if theory.predictions:
            parent_custom["predictions"] = theory.predictions
        if parent_custom:
            await _stamp_custom(execute_tool, config, parent_id, parent_custom)

    # Provenance: parent WAS_GENERATED_BY the run Execution.
    if exec_id and await _link_once(
        backend, config, parent_id, "WAS_GENERATED_BY", exec_id
    ):
        report.linked += 1
    # parent WAS_DERIVED_FROM the raw output artifact.
    if artifact_id and await _link_once(
        backend, config, parent_id, "WAS_DERIVED_FROM", artifact_id
    ):
        report.linked += 1
    # parent AROSE_FROM the link target (the Question/Plan that prompted it).
    if link_to and await _link_once(backend, config, parent_id, "AROSE_FROM", link_to):
        report.linked += 1

    for law in theory.laws:
        await _ingest_one_law(
            backend=backend,
            execute_tool=execute_tool,
            config=config,
            theory_name=theory.name,
            law=law,
            parent_id=parent_id,
            session_id=session_id,
            exec_id=exec_id,
            artifact_id=artifact_id,
            paper_index=paper_index,
            hyp_index=hyp_index,
            seen_papers=seen_papers,
            report=report,
        )

    # Theory-level contradicting papers -[CONTRADICTS]-> the parent Finding
    # (DECISION 1: contradicting evidence is keyed at theory level, not per law).
    for ref in theory.contradicting:
        await _ingest_paper_edge(
            backend=backend,
            execute_tool=execute_tool,
            config=config,
            ref=ref,
            target_id=parent_id,
            rel="CONTRADICTS",
            session_id=session_id,
            exec_id=exec_id,
            artifact_id=artifact_id,
            paper_index=paper_index,
            seen_papers=seen_papers,
            report=report,
        )


async def _ingest_one_law(
    *,
    backend,
    execute_tool,
    config: WheelerConfig,
    theory_name: str,
    law: LawRecord,
    parent_id: str,
    session_id: str,
    exec_id: str,
    artifact_id: str | None,
    paper_index: dict[str, str],
    hyp_index: dict[str, str],
    seen_papers: dict[str, str],
    report: ImportReport,
) -> None:
    """Bucket one law into a Hypothesis with supporting papers."""
    key = _hyp_key(theory_name, law.text)
    hyp_id = hyp_index.get(key)
    if hyp_id and not await _hypothesis_exists(backend, config, hyp_id):
        # Stale index entry (the node was deleted); drop it and recreate.
        hyp_id = None

    if hyp_id:
        report.deduped += 1
    else:
        hyp_result = json.loads(
            await execute_tool(
                "add_hypothesis",
                {
                    "statement": law.text,
                    "session_id": session_id,
                    "service": _SERVICE_TAG,
                },
                config,
            )
        )
        hyp_id = hyp_result.get("node_id")
        if not hyp_id or "error" in hyp_result:
            logger.warning(
                "ingest_theorizer: add_hypothesis failed for law %r", law.text[:60]
            )
            report.skipped += 1
            return
        report.created += 1
        hyp_index[key] = hyp_id

        # Novelty verdict + rationale go in the custom bag, NEVER in
        # Hypothesis.status (acts rely on open/supported/rejected). add_hypothesis
        # does not forward custom into create_node, so stamp it via update_node.
        law_custom: dict[str, Any] = {}
        if law.novelty:
            law_custom["novelty"] = law.novelty
        if law.rationale:
            law_custom["rationale"] = law.rationale
        if law_custom:
            await _stamp_custom(execute_tool, config, hyp_id, law_custom)

        # Provenance for the freshly created Hypothesis.
        if exec_id and await _link_once(
            backend, config, hyp_id, "WAS_GENERATED_BY", exec_id
        ):
            report.linked += 1
        if artifact_id and await _link_once(
            backend, config, hyp_id, "WAS_DERIVED_FROM", artifact_id
        ):
            report.linked += 1

    # parent -[CONTAINS]-> Hypothesis (link_once-guarded on every run).
    if await _link_once(backend, config, parent_id, "CONTAINS", hyp_id):
        report.linked += 1

    # supporting papers -[SUPPORTS]-> Hypothesis.
    for ref in law.supporting:
        await _ingest_paper_edge(
            backend=backend,
            execute_tool=execute_tool,
            config=config,
            ref=ref,
            target_id=hyp_id,
            rel="SUPPORTS",
            session_id=session_id,
            exec_id=exec_id,
            artifact_id=artifact_id,
            paper_index=paper_index,
            seen_papers=seen_papers,
            report=report,
        )


async def _ingest_paper_edge(
    *,
    backend,
    execute_tool,
    config: WheelerConfig,
    ref: PaperRef,
    target_id: str,
    rel: str,
    session_id: str,
    exec_id: str,
    artifact_id: str | None,
    paper_index: dict[str, str],
    seen_papers: dict[str, str],
    report: ImportReport,
) -> None:
    """Dedupe-or-create one evidence paper, then wire its edges.

    The paper -[rel]-> target_id is the semantic edge (SUPPORTS the law
    Hypothesis, or CONTRADICTS the parent theory Finding). Additionally, the run
    Execution -[USED]-> the paper: the theories were DERIVED from this evidence,
    so the paper is a genuine INPUT to the produced knowledge. (Papers are
    reference entities that carry no WAS_GENERATED_BY of their own; the USED edge
    is the run-side record that the Execution consumed them. See /wh:close and
    /wh:graph-link.) Both edges are link_once-guarded.
    """
    paper_id = await _resolve_paper(
        backend=backend,
        execute_tool=execute_tool,
        config=config,
        ref=ref,
        session_id=session_id,
        artifact_id=artifact_id,
        paper_index=paper_index,
        seen_papers=seen_papers,
        report=report,
    )
    if paper_id is None:
        return
    if await _link_once(backend, config, paper_id, rel, target_id):
        report.linked += 1
    # Execution -[USED]-> the evidence paper: the theories were derived from it,
    # so it is an input the run consumed (Paper Finder / Sem Scholar runs do NOT
    # USE their result-set papers; only Theorizer's evidence is a genuine input).
    if exec_id and await _link_once(backend, config, exec_id, "USED", paper_id):
        report.linked += 1


async def _resolve_paper(
    *,
    backend,
    execute_tool,
    config: WheelerConfig,
    ref: PaperRef,
    session_id: str,
    artifact_id: str | None,
    paper_index: dict[str, str],
    seen_papers: dict[str, str],
    report: ImportReport,
) -> str | None:
    """Return a Paper node id for ``ref``, deduping by corpus_id where possible."""
    cid = ref.corpus_id
    # 1. Already created this run.
    if cid and cid in seen_papers:
        return seen_papers[cid]
    # 2. Persisted cross-tool corpus_id index. Only trust the hit if the node
    # still lives in the graph: a stale id (deleted/pruned node) would make
    # link_once target a missing node and silently drop the SUPPORTS/CONTRADICTS
    # edge. Drop the dead entry and fall through to a fresh corpus_id read.
    existing = paper_index.get(cid) if cid else None
    if existing and not await _paper_exists(backend, config, existing):
        existing = None
        if cid:
            paper_index.pop(cid, None)
    # 3. Project-aware graph read.
    if not existing and cid:
        existing = await _find_paper_by_corpus_id(backend, config, cid)
    if existing:
        report.deduped += 1
        if existing not in report.paper_ids:
            report.paper_ids.append(existing)
        if cid:
            paper_index[cid] = existing
            seen_papers[cid] = existing
        return existing

    # 4. Create. A ref with no corpus_id and no title was dropped at parse time,
    # so title is guaranteed here when corpus_id is absent.
    add_args: dict[str, Any] = {
        "title": ref.title or f"Paper {cid}",
        "corpus_id": cid,
        "custom": ref.custom,
        "session_id": session_id,
        "service": _SERVICE_TAG,
    }
    result = json.loads(await execute_tool("add_paper", add_args, config))
    paper_id = result.get("node_id")
    if not paper_id or "error" in result:
        logger.warning("ingest_theorizer: add_paper failed for corpus_id=%s", cid)
        return None
    report.created += 1
    report.paper_ids.append(paper_id)
    if cid:
        paper_index[cid] = paper_id
        seen_papers[cid] = paper_id

    # Papers are REFERENCE ENTITIES, not produced by Wheeler (per /wh:close and
    # /wh:graph-link: "Papers are never orphans. They are reference entities,
    # not produced by Wheeler"). A Theorizer evidence paper is an INPUT the
    # theories were derived from, not a node the run produced, so it carries NO
    # WAS_GENERATED_BY. Its lineage is WAS_DERIVED_FROM the raw output artifact;
    # the Execution -[USED]-> edge (added by _ingest_paper_edge) records that the
    # run consumed it; its semantic edges (SUPPORTS/CONTRADICTS) are added by the
    # caller.
    if artifact_id and await _link_once(
        backend, config, paper_id, "WAS_DERIVED_FROM", artifact_id
    ):
        report.linked += 1
    return paper_id


async def _stamp_custom(
    execute_tool, config: WheelerConfig, node_id: str, custom: dict[str, Any]
) -> None:
    """Stamp custom-bag scalars onto an existing node via update_node.

    add_finding / add_hypothesis / add_execution do not forward ``custom`` into
    create_node, so the bag must be applied with a follow-up update_node.
    ``custom`` is a first-class NodeBase field (update_node's model-derived
    allow-list accepts it) and the backend flattens it to discrete
    ``custom_<key>`` props on write, so ``custom_novelty`` / ``custom_run_id`` /
    ``custom_cost`` are queryable. A ``service`` key in the bag is lifted to the
    first-class field. Best-effort: a failure here never breaks ingest.
    """
    if not custom:
        return
    bag = dict(custom)
    service = bag.pop("service", None)
    update_args: dict[str, Any] = {"node_id": node_id}
    if bag:
        update_args["custom"] = bag
    if service:
        update_args["service"] = service
    if len(update_args) == 1:  # only node_id, nothing to do
        return
    try:
        result = json.loads(
            await execute_tool("update_node", update_args, config)
        )
        if "error" in result:
            logger.warning(
                "ingest_theorizer: custom-bag update failed for %s: %s",
                node_id,
                result,
            )
    except Exception:
        logger.warning(
            "ingest_theorizer: custom-bag update raised for %s (best-effort)",
            node_id,
            exc_info=True,
        )
