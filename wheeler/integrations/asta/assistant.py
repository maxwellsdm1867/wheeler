"""Marshal-out (deterministic): harvest an Asta Research Assistant mission.

The Asta Research Assistant (upstream: the ``asta-assistant`` plugin from the
Allen Institute for AI, Ai2) is NOT a one-shot CLI like the other four Asta
adapters. It is a long-range AUTONOMOUS loop (the ``/asta-assistant:run`` skill)
that the scientist drives with Claude Code ``/loop`` + ``/goal`` inside a project
DIRECTORY. Wheeler does not run the loop; the marshal-in act SEEDS the mission
from the graph and the scientist runs it, then this module HARVESTS the resulting
project directory back into the graph with provenance.

REAL deliverable shape (a directory, not one file):

    <mission>/
      project.md                      # the mission: # Goal / # Background /
                                      #   # Completed Work / # Pending Work
      work/<slug>/README.md           # one unit of work: frontmatter status +
                                      #   # Goal / # Instructions / # Results /
                                      #   # Assessment (verdict)
      work/<slug>/data/<file>         # the computed artifacts (databases, csv,
                                      #   figures, scripts) do-work produced

Bucketing (the mission becomes a small provenance subgraph, one Execution per
MISSION so incremental re-harvests accrue under one run):
  - One Execution per MISSION, kind ``research-assistant``, service
    ``asta:assistant``, session_id = the mission slug (the project dir name), so
    re-harvesting as the mission progresses REUSES the one Execution rather than
    minting a new one each pass.
  - ``project.md`` registers as a Document (W-, synthesized writing = the mission
    statement + narrative) via ``ensure_artifact`` pointing at the LIVE file (not
    a frozen copy: the mission evolves, and the in-tree workspace persists), so
    the node's hash tracks the file across harvests. Document
    ``-[WAS_GENERATED_BY]-> Execution``.
  - Each COMPLETED work item (a ``work/<slug>/README.md`` with a non-empty
    ``# Results`` section) -> a Finding whose description is the Results summary
    and whose Assessment verdict + status + root cause are parked in the queryable
    custom bag. Deduped across harvests on a stable ``work_key`` =
    ``<mission-slug>/<work-slug>`` (a graph read on ``custom_work_key``), so a
    re-harvest updates nothing and creates nothing for an already-recorded item.
    Finding ``-[WAS_GENERATED_BY]-> Execution``, ``-[AROSE_FROM]-> the mission
    Document`` (and the seed Question/Plan when ``link_to`` is given).
  - Each ``work/<slug>/data/<file>`` -> a Dataset (data) or Script (code) node via
    ``ensure_artifact`` (deduped on path). Data node ``-[WAS_GENERATED_BY]->
    Execution``; the work Finding ``-[WAS_DERIVED_FROM]-> the data node`` (the
    result was computed from it).

Input-side provenance: the marshal-in act SEEDED the mission FROM graph nodes
(the mission Question/Plan, the seeded Findings, the Dataset paths), so the run
``Execution -[USED]-> each seed id``. The act passes them via ``--used`` and the
CLI forwards them here (existence-guarded, never fabricated).

Semantic wiring to the EXISTING graph (a harvested Finding SUPPORTS/CONTRADICTS a
prior Hypothesis, RELEVANT_TO an open Question) is JUDGMENT, so it lives in the
``/wh:asta-assistant`` act post-harvest, NOT in this parser (the three-part model,
docs/asta-engine-spec.md).

Papers: the assistant MAY use ``asta literature find`` inside a work item, but a
corpus_id is not reliably recoverable from arbitrary work output, so this adapter
does NOT extract Paper nodes (the contract's ``nodes`` list is Document / Finding
/ Dataset). A literature-heavy mission should record papers via ``/wh:asta-lit``
directly; a future enhancement can parse a work item's cited corpus ids.

Invariants:
  - Defensive: every step tolerates missing pieces, counts and skips, never
    raises. A malformed project.md or a work README with no Results never aborts
    the harvest.
  - Sequential writes only. Never ``asyncio.gather``: ``execute_tool`` reuses one
    cached backend singleton and Neo4j forbids concurrent queries.
  - link_once: every edge is existence-guarded because the backend's
    ``create_relationship`` is a bare CREATE that duplicates on re-run.
  - One Execution per MISSION, tagged service ``asta:assistant``. The
    partial-ingest failsafe marks the run failed if output bucketing raises; a
    missing / unparseable project.md fabricates nothing (returns an empty report).
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from wheeler.config import WheelerConfig
from wheeler.integrations.asta._marshal import (
    ImportReport,
    JobOutcome,
    _edge_exists,
    _find_execution,
    _link_execution_to_plan,
    _link_once,
    _node_exists,
    _record_used,
    job_outcome,
    mark_execution_completed,
    mark_execution_failed,
)

logger = logging.getLogger(__name__)

_SERVICE_TAG = "asta:assistant"
_RAW_NODE_TYPE = "document"  # project.md is synthesized WRITING (the mission)

# Persisted (work_key -> Finding id) index so re-harvest dedupes a work item even
# if the in-graph custom_work_key stamp (a separate best-effort write) failed. The
# hit is existence-guarded before reuse (a deleted node's stale id is dropped),
# mirroring the theorizer / corpus_id index pattern. Belt-and-suspenders with the
# graph read in _find_finding_by_work_key.
_WORK_INDEX_REL_PATH = ".wheeler/integrations/assistant_work_index.json"

# File extensions that classify a work data artifact. Code -> Script (S-), prose
# -> Document (W-), everything else (csv, mat, db, parquet, npy, png, ...) ->
# Dataset (D-): the user cares about "the things you compute, artifacts like
# databases", which are Datasets.
_SCRIPT_EXTS = {
    ".py", ".m", ".r", ".jl", ".sh", ".ipynb", ".js", ".ts", ".cpp", ".c",
    ".java", ".go", ".rs", ".sql",
}
_DOC_EXTS = {".md", ".txt", ".rst", ".org"}


# ---------------------------------------------------------------------------
# Parse records (intermediate, shape-drift tolerant, never raises)
# ---------------------------------------------------------------------------


@dataclass
class WorkItem:
    """One harvested unit of work (a ``work/<slug>/README.md`` with a Result)."""

    slug: str
    status: str = ""
    title: str = ""            # the one-line summary
    goal: str = ""
    result_summary: str = ""   # the # Results narrative (or its ## Summary)
    verdict: str = ""          # accomplished | partial | not accomplished
    root_cause: str = ""
    readme_path: str = ""      # abs path to work/<slug>/README.md
    data_files: list[str] = field(default_factory=list)  # abs paths


@dataclass
class ProjectRecord:
    """A parsed mission: the project.md identity + its completed work items."""

    slug: str                  # the mission slug (the project dir name)
    title: str
    goal: str = ""
    background: str = ""
    project_md_path: str = ""  # abs path to project.md
    work_items: list[WorkItem] = field(default_factory=list)


@dataclass
class RunMeta:
    """Benchmark fields for the run. run_id = the mission slug (stable key)."""

    run_id: str = ""

    def custom_bag(self) -> dict[str, Any]:
        bag: dict[str, Any] = {"service": _SERVICE_TAG}
        if self.run_id:
            bag["run_id"] = self.run_id
        return bag


def _read_text(path: Path) -> str:
    """Read a file as text, defensively. Returns "" on any error.

    ``utf-8-sig`` strips a leading BOM (which would otherwise defeat the ``^#``
    heading regex, losing the Goal and mistitling the mission); ``errors=
    "replace"`` turns a stray non-UTF-8 byte into a replacement char instead of
    raising ``UnicodeDecodeError`` (a ``ValueError``, which a bare ``except
    OSError`` would NOT catch, breaking the never-raises invariant on a
    mis-encoded README).
    """
    try:
        return path.read_text(encoding="utf-8-sig", errors="replace")
    except (OSError, ValueError):
        return ""


def _slugify(value: str) -> str:
    """Filesystem/graph-safe slug for a mission or work key. Never raises."""
    safe = re.sub(r"[^a-zA-Z0-9._-]+", "-", (value or "").strip().lower())
    return safe.strip("-._") or "mission"


def _parse_frontmatter(md: str) -> dict[str, str]:
    """Parse a leading ``---`` YAML frontmatter block into a flat str->str map.

    Only the simple ``key: value`` lines the assistant writes (slug, status) are
    needed, so this is a deliberately tiny hand-rolled parser (no PyYAML): it
    reads lines between the first two ``---`` fences. Defensive: no fence, or a
    malformed block, yields {}.
    """
    if not md.startswith("---"):
        return {}
    lines = md.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    out: dict[str, str] = {}
    closed = False
    for line in lines[1:]:
        if line.strip() == "---":
            closed = True
            break
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            if key:
                out[key] = val.strip().strip("'\"")
    # Require a closing fence: without it, an unterminated block would slurp the
    # whole document and let a body line (a prose ``Note: ...`` or a stray
    # ``status: ...``) overwrite the real frontmatter keys.
    return out if closed else {}


# Trailing ``#+`` (a closed ATX heading like ``## Results ##``) is optional and
# stripped, so a valid-CommonMark closed heading is not mistaken for a different
# title (which would silently drop the whole work item).
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)(?:\s+#+)?\s*$")


def _section(md: str, name: str, *, prefix: bool = False) -> str:
    """Return the body of the markdown section titled ``name`` (any level).

    Finds the first heading whose text equals ``name`` (case-insensitive), then
    collects lines until the next heading of the SAME OR HIGHER level (so a
    ``## Results`` body includes its ``### Summary`` subsection but stops at the
    next ``##``). With ``prefix=True`` the heading only has to START with ``name``,
    which matches the review-work skill's ``## Root cause (if not fully
    accomplished)`` heading. Defensive: a missing section yields "". Never raises.
    """
    lines = md.splitlines()
    target = name.strip().lower()
    start: int | None = None
    level = 0
    for i, line in enumerate(lines):
        m = _HEADING_RE.match(line)
        if not m:
            continue
        head = m.group(2).strip().lower()
        if head.startswith(target) if prefix else head == target:
            start = i + 1
            level = len(m.group(1))
            break
    if start is None:
        return ""
    body: list[str] = []
    for line in lines[start:]:
        m = _HEADING_RE.match(line)
        if m and len(m.group(1)) <= level:
            break
        body.append(line)
    return "\n".join(body).strip()


def _first_heading(md: str) -> str:
    """First level-1 ATX heading text (``# ...``), or ""."""
    for line in md.splitlines():
        m = _HEADING_RE.match(line)
        if m and len(m.group(1)) == 1:
            return m.group(2).strip()
    return ""


# Ordered so the most specific token wins the substring scan: "not accomplished"
# before "accomplished" (else the negation is swallowed), and "partial" before
# "accomplished" (else the reviewer's natural phrasing "partially accomplished"
# reads as a clean success and inverts the verdict).
_VERDICT_TOKENS = ("not accomplished", "partial", "accomplished")


def _verdict(assessment: str) -> str:
    """Best-effort verdict from an ``# Assessment`` body. "" when none found.

    Prefers a ``## Verdict`` subsection value; else scans the text for the
    review-work verdict tokens in specificity order (see ``_VERDICT_TOKENS``), so
    "not accomplished" and "partially accomplished" are not mis-read as the bare
    "accomplished". Never raises.
    """
    if not assessment:
        return ""
    verdict_section = _section(assessment, "Verdict")
    hay = (verdict_section or assessment).lower()
    for token in _VERDICT_TOKENS:
        if token in hay:
            return token
    return ""


def _result_summary(results: str) -> str:
    """A compact result summary: the ``## Summary`` subsection, else the head."""
    summary = _section(results, "Summary")
    text = summary or results
    return text.strip()[:1500]


def _artifact_type_for(path: Path) -> str:
    """Classify a work data file as script / document / dataset by extension."""
    ext = path.suffix.lower()
    if ext in _SCRIPT_EXTS:
        return "script"
    if ext in _DOC_EXTS:
        return "document"
    return "dataset"


def _list_data_files(work_dir: Path) -> list[str]:
    """Absolute paths of every file under ``work/<slug>/data/`` (recursive)."""
    data_dir = work_dir / "data"
    if not data_dir.is_dir():
        return []
    out: list[str] = []
    try:
        for p in sorted(data_dir.rglob("*")):
            if p.is_file():
                out.append(str(p.resolve()))
    except OSError:
        logger.warning("parse_assistant: could not list %s", data_dir, exc_info=True)
    return out


def _resolve_project_dir(project_dir: str | Path) -> Path | None:
    """Resolve the mission root from a directory OR a project.md path.

    Accepts the project directory, or a path to ``project.md`` itself (the act
    may pass either). Returns the directory that contains ``project.md``, or None
    if there is no readable ``project.md``.
    """
    p = Path(project_dir)
    if p.is_file() and p.name == "project.md":
        return p.parent
    if p.is_dir() and (p / "project.md").is_file():
        return p
    return None


def parse_assistant(project_dir: str | Path) -> tuple[ProjectRecord | None, RunMeta]:
    """Walk an Asta Research Assistant mission directory into a ProjectRecord.

    Reads ``project.md`` for the mission identity and every
    ``work/<slug>/README.md`` with a non-empty ``# Results`` section (an executed
    unit of work worth harvesting), lifting its result summary, verdict, and the
    data files under ``work/<slug>/data/``. Defensive throughout: a missing
    project.md yields ``(None, RunMeta())``; a malformed work README is skipped,
    never fatal.
    """
    root = _resolve_project_dir(project_dir)
    if root is None:
        logger.warning(
            "parse_assistant: no readable project.md under %s", project_dir
        )
        return None, RunMeta()

    project_md = root / "project.md"
    md = _read_text(project_md)
    # The mission identity (the Execution session_id AND the work_key dedupe
    # prefix) must be UNIQUE per mission, so it folds a short hash of the resolved
    # absolute path into the readable basename. Basename alone would collide when
    # two missions share a directory name (different repos, one graph) or both
    # sanitize to the "mission" fallback, which would make distinct missions reuse
    # one Execution and cross-dedupe each other's Findings (silent data loss).
    resolved = str(root.resolve())
    slug = f"{_slugify(root.resolve().name)}-{hashlib.sha256(resolved.encode()).hexdigest()[:8]}"
    goal = _section(md, "Goal")
    background = _section(md, "Background")
    # The mission title is the first non-empty line of the Goal section (the
    # project.md's first heading is the literal "Goal", not a title), falling back
    # to a top-level heading, then the mission slug.
    first_goal_line = next((ln.strip() for ln in goal.splitlines() if ln.strip()), "")
    title = (first_goal_line or _first_heading(md) or root.name)[:200]

    work_items: list[WorkItem] = []
    work_root = root / "work"
    if work_root.is_dir():
        try:
            work_dirs = sorted(work_root.iterdir())
        except OSError:  # an unreadable work/ dir must not abort the harvest
            logger.warning("parse_assistant: could not list %s", work_root, exc_info=True)
            work_dirs = []
        for work_dir in work_dirs:
            if not work_dir.is_dir():
                continue
            readme = work_dir / "README.md"
            if not readme.is_file():
                continue
            try:
                item = _parse_work_item(work_dir, readme)
            except Exception:  # never let one bad README abort the harvest
                logger.warning(
                    "parse_assistant: work item %s failed to parse (skipped)",
                    work_dir.name,
                    exc_info=True,
                )
                continue
            if item is not None:
                work_items.append(item)

    record = ProjectRecord(
        slug=slug,
        title=str(title)[:200],
        goal=goal,
        background=background,
        project_md_path=str(project_md.resolve()),
        work_items=work_items,
    )
    return record, RunMeta(run_id=slug)


def _parse_work_item(work_dir: Path, readme: Path) -> WorkItem | None:
    """Parse one ``work/<slug>/README.md``, or None if it has no Result.

    Only an EXECUTED unit of work (a non-empty ``# Results`` section) is
    harvestable: a still-pending item with an empty Results section has nothing
    to record and is skipped (returns None), so the harvest never fabricates a
    Finding for work that has not happened.
    """
    md = _read_text(readme)
    if not md.strip():
        return None
    results = _section(md, "Results")
    if not results.strip():
        return None  # not executed yet: nothing to harvest
    fm = _parse_frontmatter(md)
    slug = _slugify(fm.get("slug") or work_dir.name)
    goal = _section(md, "Goal")
    assessment = _section(md, "Assessment")
    return WorkItem(
        slug=slug,
        status=fm.get("status", ""),
        title=(goal.splitlines()[0].strip() if goal else slug)[:200],
        goal=goal,
        result_summary=_result_summary(results),
        verdict=_verdict(assessment),
        # prefix match: the review-work skill writes "## Root cause (if not fully
        # accomplished)", not a bare "## Root cause".
        root_cause=_section(assessment, "Root cause", prefix=True),
        readme_path=str(readme.resolve()),
        data_files=_list_data_files(work_dir),
    )


# ---------------------------------------------------------------------------
# Project-aware reads (dedupe a work Finding across harvests)
# ---------------------------------------------------------------------------


def _work_index_path() -> Path:
    return Path(_WORK_INDEX_REL_PATH)


def _load_work_index() -> dict[str, str]:
    path = _work_index_path()
    try:
        if path.exists():
            data = json.loads(path.read_text())
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items()}
    except (OSError, json.JSONDecodeError):
        logger.warning(
            "ingest_assistant: could not read work index %s, starting fresh", path
        )
    return {}


def _save_work_index(index: dict[str, str]) -> None:
    path = _work_index_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(index, indent=2, sort_keys=True))
        tmp.replace(path)
    except OSError:
        logger.error(
            "ingest_assistant: could not persist work index %s (best-effort)",
            path,
            exc_info=True,
        )


async def _find_finding_by_work_key(
    backend, config: WheelerConfig, work_key: str, work_index: dict[str, str]
) -> str | None:
    """Return an existing Finding id for this ``work_key``, or None.

    Makes a work item idempotent across incremental harvests via TWO signals, so a
    single failed write cannot cause a duplicate:
      1. the persisted ``work_index`` (work_key -> F-id), existence-guarded with
         ``_node_exists`` so a deleted node's stale id is dropped, not trusted;
      2. the in-graph ``custom_work_key`` = ``<mission-slug>/<work-slug>`` (a
         separate best-effort stamp), read project-aware.
    A graph hit repopulates the index. Returns None only when NEITHER signal
    finds a live Finding.
    """
    if not work_key:
        return None
    # 1. Persisted index (guarded against staleness).
    cached = work_index.get(work_key)
    if cached and await _node_exists(backend, config, cached):
        return cached
    if cached:
        work_index.pop(work_key, None)  # stale: node gone, fall through
    # 2. Project-aware graph read on the stamped key.
    ptag = getattr(config.neo4j, "project_tag", "") or ""
    if ptag:
        query = (
            "MATCH (f:Finding {custom_work_key: $key}) "
            "WHERE f._wheeler_project = $ptag RETURN f.id AS id LIMIT 1"
        )
        params = {"key": work_key, "ptag": ptag}
    else:
        query = (
            "MATCH (f:Finding {custom_work_key: $key}) RETURN f.id AS id LIMIT 1"
        )
        params = {"key": work_key}
    rows = await backend.run_cypher(query, params)
    if rows and rows[0].get("id"):
        work_index[work_key] = rows[0]["id"]
        return rows[0]["id"]
    return None


# ---------------------------------------------------------------------------
# Ingest
# ---------------------------------------------------------------------------


async def ingest_assistant(
    project_dir: str | Path,
    *,
    link_to: str | None = None,
    config: WheelerConfig,
    used_inputs: list[str] | None = None,
) -> ImportReport:
    """Harvest an Asta Research Assistant mission directory into the graph.

    Args:
        project_dir: The mission project directory (or the path to its
            ``project.md``). Must contain a readable ``project.md``; otherwise
            the harvest fabricates nothing and returns an empty report.
        link_to: Optional seed node id (Question ``Q-`` or Plan ``PL-``) the
            mission AROSE_FROM. Each harvested Finding and the mission Document
            AROSE_FROM it; when it is a Plan, the run Execution AROSE_FROM it too.
        config: Active Wheeler config.
        used_inputs: The graph node ids the mission was SEEDED from (the mission
            Question/Plan plus any seeded Finding/Dataset ids). The run Execution
            ``-[USED]->`` each one that exists (input-side provenance,
            existence-guarded, never fabricated).

    Returns:
        An ImportReport with created / deduped / linked / used counts. ``artifact``
        is the mission Document id; ``execution_id`` the one mission Execution.
    """
    from wheeler.tools.graph_tools import _get_backend, execute_tool

    report = ImportReport()
    record, run_meta = parse_assistant(project_dir)

    # Failsafe gate (honest status, no fabricated outputs). There is no A2A job
    # status here: the "artifact" is the mission directory. The truthful signal of
    # a usable run is a parseable mission (a readable project.md), which
    # parse_assistant already rejects the missing / unparseable cases of, mirroring
    # the transport's guarantee for the other adapters. Route it through the same
    # job_outcome primitive: a None record is state "missing" (not ok) and
    # fabricates nothing; a parsed mission is ok. The visible-failed-Execution for
    # a job that produced no directory at all is the act's record-failure step.
    outcome = job_outcome(
        {"mission": record.slug} if record is not None else None
    )
    if not outcome.ok or record is None:
        logger.warning(
            "ingest_assistant: no usable mission (%s: %s)",
            outcome.state,
            outcome.detail or "no project.md",
        )
        return report

    backend = await _get_backend(config)
    work_index = _load_work_index()

    # One Execution per MISSION, keyed on the mission slug so incremental
    # re-harvests REUSE it (session_id stable across passes). Falls back to a
    # content hash only if the slug is somehow empty.
    session_id = run_meta.run_id or (
        "assistant-" + hashlib.sha256(str(project_dir).encode()).hexdigest()[:16]
    )
    exec_id = await _find_execution(
        backend, config, service=_SERVICE_TAG, session_id=session_id
    )
    reused = bool(exec_id)
    if not exec_id:
        exec_result = json.loads(
            await execute_tool(
                "add_execution",
                {
                    "kind": "research-assistant",
                    "description": f"Asta Research Assistant mission: {record.title}"[
                        :200
                    ],
                    "agent_id": "asta",
                    "status": "completed",
                    "session_id": session_id,
                    "service": _SERVICE_TAG,
                },
                config,
            )
        )
        exec_id = exec_result.get("node_id", "")
    report.execution_id = exec_id

    # Plan lifecycle: anchor the run Execution to its Plan (Execution -[AROSE_FROM]
    # -> Plan) when link_to is a PL- id. No-op otherwise; link_once.
    if exec_id and await _link_execution_to_plan(backend, config, exec_id, link_to):
        report.plan_linked += 1

    # Input-side provenance: the mission was SEEDED from these graph nodes, so the
    # run USED them. Existence-guarded, never fabricated, re-harvest dedupes.
    if exec_id and used_inputs:
        report.used += await _record_used(backend, config, exec_id, used_inputs)

    # A reused Execution from a prior failed attempt: a now-successful harvest must
    # not inherit the stale "failed" status. Reset before any output is written.
    if reused:
        await mark_execution_completed(config, exec_id)

    # project.md registers as the mission Document (W-), pointing at the LIVE file
    # so its hash tracks the evolving mission across harvests.
    doc_id = await _register_artifact(
        execute_tool,
        backend,
        config,
        path=record.project_md_path,
        artifact_type="document",
        description=f"Asta Research Assistant mission: {record.title}"[:200],
        exec_id=exec_id,
        report=report,
    )
    if doc_id:
        report.artifact = doc_id
        if link_to and await _link_once(backend, config, doc_id, "AROSE_FROM", link_to):
            report.linked += 1

    # Output bucketing: each completed work item -> a Finding + its data artifacts.
    # Wrapped so a partial-ingest exception marks the run failed (no clean masquerade).
    try:
        for item in record.work_items:
            await _ingest_work_item(
                backend=backend,
                execute_tool=execute_tool,
                config=config,
                item=item,
                mission_slug=record.slug,
                exec_id=exec_id,
                doc_id=doc_id,
                link_to=link_to,
                session_id=session_id,
                work_index=work_index,
                report=report,
            )
    except Exception:
        logger.error(
            "ingest_assistant: output bucketing raised partway; marking run failed",
            exc_info=True,
        )
        await mark_execution_failed(
            config,
            exec_id,
            JobOutcome(ok=False, state="ingest-error", detail="output bucketing raised"),
        )
        report.failed = True
        report.job_state = "ingest-error"
        # Persist whatever the index learned before the failure, so the work items
        # already recorded this run still dedupe on a later retry.
        _save_work_index(work_index)
        return report

    _save_work_index(work_index)

    logger.info(
        "ingest_assistant: created=%d deduped=%d linked=%d skipped=%d used=%d "
        "plan_linked=%d (exec=%s)",
        report.created,
        report.deduped,
        report.linked,
        report.skipped,
        report.used,
        report.plan_linked,
        exec_id,
    )
    return report


async def _register_artifact(
    execute_tool,
    backend,
    config: WheelerConfig,
    *,
    path: str,
    artifact_type: str,
    description: str,
    exec_id: str,
    report: ImportReport,
) -> str | None:
    """Register a file (project.md or a data artifact) as an in-place graph node.

    Registers via ``ensure_artifact`` (deduped on path, points at the LIVE file),
    stamps the service tag, and links the node ``-[WAS_GENERATED_BY]-> exec_id``.
    The WAS_GENERATED_BY edge's newness is the created/deduped signal (a new edge
    means a first-time registration this run), so re-harvest counts as deduped and
    the idempotency assertion holds. Best-effort: any failure returns None and
    never raises, so an artifact problem cannot abort the harvest. Returns the
    node id.
    """
    if not path or not Path(path).exists():
        return None
    try:
        result = json.loads(
            await execute_tool(
                "ensure_artifact",
                {
                    "path": path,
                    "artifact_type": artifact_type,
                    "description": description,
                    "service": _SERVICE_TAG,
                    "tier": "generated",
                },
                config,
            )
        )
    except Exception:
        logger.warning(
            "ingest_assistant: ensure_artifact raised for %s (best-effort)",
            path,
            exc_info=True,
        )
        return None
    node_id = result.get("node_id")
    if not node_id or "error" in result:
        logger.warning("ingest_assistant: ensure_artifact failed for %s", path)
        report.skipped += 1
        return None
    # ensure_artifact does not forward `service` into create_node, so stamp it
    # (mirrors register_output_artifact step 3) so these artifact nodes are
    # service-scoped-queryable like the Findings, not left un-tagged.
    try:
        await execute_tool(
            "update_node", {"node_id": node_id, "service": _SERVICE_TAG}, config
        )
    except Exception:
        logger.warning(
            "ingest_assistant: service stamp failed for %s (best-effort)",
            node_id,
            exc_info=True,
        )
    # Provenance + created/deduped signal. Distinguish "edge already existed"
    # (a genuine re-harvest dedupe) from "the link write failed" (transient), so a
    # flaky first pass is not mislabeled deduped and then counted created on the
    # next pass: a pre-existing edge is deduped, a fresh edge is created, and a
    # failed link is skipped (surfaced, not silently counted as either).
    if exec_id:
        if await _edge_exists(backend, node_id, "WAS_GENERATED_BY", exec_id):
            report.deduped += 1
        elif await _link_once(backend, config, node_id, "WAS_GENERATED_BY", exec_id):
            report.created += 1
            report.linked += 1
        else:
            logger.warning(
                "ingest_assistant: WAS_GENERATED_BY link failed for %s", node_id
            )
            report.skipped += 1
    return node_id


async def _ingest_work_item(
    *,
    backend,
    execute_tool,
    config: WheelerConfig,
    item: WorkItem,
    mission_slug: str,
    exec_id: str,
    doc_id: str | None,
    link_to: str | None,
    session_id: str,
    work_index: dict[str, str],
    report: ImportReport,
) -> None:
    """Harvest one completed work item into a Finding + its data artifacts.

    The Finding's description is the Results summary; the Assessment verdict,
    status, and root cause are parked in the queryable custom bag. Deduped across
    harvests on ``work_key`` = ``<mission-slug>/<work-slug>``. Provenance: Finding
    ``-[WAS_GENERATED_BY]-> Execution``, ``-[AROSE_FROM]-> the mission Document``
    (and the seed link target); each data artifact ``-[WAS_GENERATED_BY]->
    Execution`` and the Finding ``-[WAS_DERIVED_FROM]-> it``.
    """
    work_key = f"{mission_slug}/{item.slug}"
    finding_id = await _find_finding_by_work_key(backend, config, work_key, work_index)
    if finding_id:
        report.deduped += 1
    else:
        # Confidence reflects the honest verdict; an autonomous-loop result is not
        # asserted as high-confidence (LLM-generated Findings are low-stability).
        confidence = {
            "accomplished": 0.6,
            "partial": 0.4,
        }.get(item.verdict, 0.3)
        add_args: dict[str, Any] = {
            "description": (item.result_summary or item.goal or item.title)[:2000],
            "title": (item.title or item.slug)[:100],
            "confidence": confidence,
            "artifact_type": "assistant-work",
            "session_id": session_id,
            "service": _SERVICE_TAG,
        }
        result = json.loads(await execute_tool("add_finding", add_args, config))
        finding_id = result.get("node_id")
        if not finding_id or "error" in result:
            logger.warning(
                "ingest_assistant: add_finding failed for work %r", work_key
            )
            report.skipped += 1
            return
        report.created += 1
        # Record in the persisted index immediately (belt-and-suspenders with the
        # in-graph stamp below), so a later re-harvest dedupes this item even if
        # the custom_work_key stamp write fails.
        work_index[work_key] = finding_id
        # add_finding does not forward custom into create_node: stamp the work
        # metadata (the dedupe key + the verdict bag) via update_node so they are
        # queryable (custom_work_key / custom_verdict / custom_status).
        await _stamp_custom(
            execute_tool,
            config,
            finding_id,
            {
                "work_key": work_key,
                "work_slug": item.slug,
                "status": item.status,
                "verdict": item.verdict,
                "root_cause": item.root_cause[:500],
                "service": _SERVICE_TAG,
            },
        )

    # Provenance: Finding WAS_GENERATED_BY the run; AROSE_FROM the mission Document
    # (and the seed Question/Plan). All link_once-guarded, so re-harvest is a no-op.
    if exec_id and await _link_once(
        backend, config, finding_id, "WAS_GENERATED_BY", exec_id
    ):
        report.linked += 1
    if doc_id and await _link_once(backend, config, finding_id, "AROSE_FROM", doc_id):
        report.linked += 1
    if link_to and await _link_once(
        backend, config, finding_id, "AROSE_FROM", link_to
    ):
        report.linked += 1

    # Each computed data artifact -> a Dataset/Script node WAS_GENERATED_BY the
    # run; the Finding WAS_DERIVED_FROM it (the result was computed from the data).
    for data_path in item.data_files:
        data_id = await _register_artifact(
            execute_tool,
            backend,
            config,
            path=data_path,
            artifact_type=_artifact_type_for(Path(data_path)),
            description=f"{item.slug} artifact: {Path(data_path).name}"[:200],
            exec_id=exec_id,
            report=report,
        )
        if data_id and await _link_once(
            backend, config, finding_id, "WAS_DERIVED_FROM", data_id
        ):
            report.linked += 1


async def _stamp_custom(
    execute_tool, config: WheelerConfig, node_id: str, custom: dict[str, Any]
) -> None:
    """Stamp custom-bag scalars onto an existing node via update_node.

    add_finding does not forward ``custom`` into create_node, so the bag is
    applied with a follow-up update_node. ``custom`` is a first-class NodeBase
    field (update_node's allow-list accepts it) and the backend flattens it to
    discrete ``custom_<key>`` props on write, so ``custom_work_key`` /
    ``custom_verdict`` are stored AND queryable. A ``service`` key is lifted to the
    first-class field. Best-effort: a failure here never breaks the harvest.
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
    if len(update_args) == 1:
        return
    try:
        result = json.loads(await execute_tool("update_node", update_args, config))
        if "error" in result:
            logger.warning(
                "ingest_assistant: custom-bag update failed for %s: %s",
                node_id,
                result,
            )
    except Exception:
        logger.warning(
            "ingest_assistant: custom-bag update raised for %s (best-effort)",
            node_id,
            exc_info=True,
        )
