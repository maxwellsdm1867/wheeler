"""Markdown renderer for Wheeler knowledge graph nodes.

Renders Pydantic node models as pretty markdown for human reading
via ``wh show``.

``render_synthesis`` produces Obsidian-compatible markdown with YAML
frontmatter for the synthesis/ directory (human-browsable layer).
"""

from __future__ import annotations

import re

from wheeler.models import (
    DatasetModel,
    DocumentModel,
    ExecutionModel,
    FindingModel,
    HypothesisModel,
    NodeBase,
    OpenQuestionModel,
    PaperModel,
    ResearchNoteModel,
    ScriptModel,
)


def _fmt_date(iso: str) -> str:
    """Return just the date portion of an ISO timestamp."""
    if not iso:
        return ""
    return iso.split("T")[0]


def _tags_line(tags: list[str]) -> str:
    """Return a formatted tags line, or empty string if no tags."""
    if not tags:
        return ""
    return f"\n*Tags*: {', '.join(tags)}\n"


# ---------------------------------------------------------------------------
# Type-specific renderers
# ---------------------------------------------------------------------------


def _render_finding(m: FindingModel) -> str:
    parts: list[str] = [f"# Finding [{m.id}]", ""]

    meta: list[str] = []
    if m.confidence:
        meta.append(f"**Confidence**: {m.confidence}")
    if m.tier:
        meta.append(f"**Tier**: {m.tier}")
    date = _fmt_date(m.created)
    if date:
        meta.append(f"**Created**: {date}")
    if meta:
        parts.append(" | ".join(meta))
        parts.append("")

    if m.description:
        parts.append(m.description)
        parts.append("")

    tags = _tags_line(m.tags)
    if tags:
        parts.append(tags.strip())
        parts.append("")

    return "\n".join(parts).rstrip() + "\n"


def _render_hypothesis(m: HypothesisModel) -> str:
    parts: list[str] = [f"# Hypothesis [{m.id}]", ""]

    meta: list[str] = []
    if m.status:
        meta.append(f"**Status**: {m.status}")
    if m.tier:
        meta.append(f"**Tier**: {m.tier}")
    date = _fmt_date(m.created)
    if date:
        meta.append(f"**Created**: {date}")
    if meta:
        parts.append(" | ".join(meta))
        parts.append("")

    if m.statement:
        parts.append(m.statement)
        parts.append("")

    tags = _tags_line(m.tags)
    if tags:
        parts.append(tags.strip())
        parts.append("")

    return "\n".join(parts).rstrip() + "\n"


def _render_open_question(m: OpenQuestionModel) -> str:
    parts: list[str] = [f"# Open Question [{m.id}]", ""]

    meta: list[str] = []
    if m.priority:
        meta.append(f"**Priority**: {m.priority}")
    if m.tier:
        meta.append(f"**Tier**: {m.tier}")
    date = _fmt_date(m.created)
    if date:
        meta.append(f"**Added**: {date}")
    if meta:
        parts.append(" | ".join(meta))
        parts.append("")

    if m.question:
        parts.append(m.question)
        parts.append("")

    tags = _tags_line(m.tags)
    if tags:
        parts.append(tags.strip())
        parts.append("")

    return "\n".join(parts).rstrip() + "\n"


def _render_paper(m: PaperModel) -> str:
    parts: list[str] = [f"# Paper [{m.id}]", ""]

    meta: list[str] = []
    if m.authors:
        meta.append(f"**Authors**: {m.authors}")
    if m.year:
        meta.append(f"**Year**: {m.year}")
    if m.tier:
        meta.append(f"**Tier**: {m.tier}")
    if meta:
        parts.append(" | ".join(meta))
    if m.doi:
        parts.append(f"**DOI**: {m.doi}")
    if meta or m.doi:
        parts.append("")

    if m.title:
        parts.append(m.title)
        parts.append("")

    tags = _tags_line(m.tags)
    if tags:
        parts.append(tags.strip())
        parts.append("")

    return "\n".join(parts).rstrip() + "\n"


def _render_dataset(m: DatasetModel) -> str:
    parts: list[str] = [f"# Dataset [{m.id}]", ""]

    meta: list[str] = []
    if m.path:
        meta.append(f"**Path**: {m.path}")
    if m.data_type:
        meta.append(f"**Type**: {m.data_type}")
    if m.tier:
        meta.append(f"**Tier**: {m.tier}")
    if meta:
        parts.append(" | ".join(meta))
        parts.append("")

    if m.description:
        parts.append(m.description)
        parts.append("")

    tags = _tags_line(m.tags)
    if tags:
        parts.append(tags.strip())
        parts.append("")

    return "\n".join(parts).rstrip() + "\n"


def _render_document(m: DocumentModel) -> str:
    parts: list[str] = [f"# Document [{m.id}]", ""]

    meta: list[str] = []
    if m.path:
        meta.append(f"**Path**: {m.path}")
    if m.section:
        meta.append(f"**Section**: {m.section}")
    if m.status:
        meta.append(f"**Status**: {m.status}")
    if m.tier:
        meta.append(f"**Tier**: {m.tier}")
    if meta:
        parts.append(" | ".join(meta))
        parts.append("")

    if m.title:
        parts.append(m.title)
        parts.append("")

    tags = _tags_line(m.tags)
    if tags:
        parts.append(tags.strip())
        parts.append("")

    return "\n".join(parts).rstrip() + "\n"


def _render_script(m: ScriptModel) -> str:
    parts: list[str] = [f"# Script [{m.id}]", ""]

    if m.path:
        parts.append(f"**Path**: {m.path}")
    lang_str = ""
    if m.language:
        lang_str = m.language
        if m.version:
            lang_str += f" {m.version}"
        parts.append(f"**Language**: {lang_str}")
    if m.hash:
        parts.append(f"**Hash**: {m.hash}")

    parts.append("")

    tags = _tags_line(m.tags)
    if tags:
        parts.append(tags.strip())
        parts.append("")

    return "\n".join(parts).rstrip() + "\n"


def _render_execution(m: ExecutionModel) -> str:
    parts: list[str] = [f"# Execution [{m.id}]", ""]

    meta: list[str] = []
    if m.kind:
        meta.append(f"**Kind**: {m.kind}")
    if m.status:
        meta.append(f"**Status**: {m.status}")
    if m.agent_id:
        meta.append(f"**Agent**: {m.agent_id}")
    if meta:
        parts.append(" | ".join(meta))
        parts.append("")

    if m.description:
        parts.append(m.description)
        parts.append("")

    started = _fmt_date(m.started_at)
    ended = _fmt_date(m.ended_at)
    if started:
        parts.append(f"**Started**: {started}")
    if ended:
        parts.append(f"**Ended**: {ended}")
    if started or ended:
        parts.append("")

    tags = _tags_line(m.tags)
    if tags:
        parts.append(tags.strip())
        parts.append("")

    return "\n".join(parts).rstrip() + "\n"


def _render_note(m: ResearchNoteModel) -> str:
    parts: list[str] = [f"# Research Note [{m.id}]", ""]

    meta: list[str] = []
    if m.tier:
        meta.append(f"**Tier**: {m.tier}")
    date = _fmt_date(m.created)
    if date:
        meta.append(f"**Created**: {date}")
    if meta:
        parts.append(" | ".join(meta))
        parts.append("")

    if m.title:
        parts.append(f"**{m.title}**")
        parts.append("")

    if m.content:
        parts.append(m.content)
        parts.append("")

    if m.context:
        parts.append(f"*Context*: {m.context}")
        parts.append("")

    tags = _tags_line(m.tags)
    if tags:
        parts.append(tags.strip())
        parts.append("")

    return "\n".join(parts).rstrip() + "\n"


def _render_generic(m: NodeBase) -> str:
    """Fallback renderer for Plan, etc."""
    type_name = m.type
    parts: list[str] = [f"# {type_name} [{m.id}]", ""]

    meta: list[str] = []
    if m.tier:
        meta.append(f"**Tier**: {m.tier}")
    date = _fmt_date(m.created)
    if date:
        meta.append(f"**Created**: {date}")
    if meta:
        parts.append(" | ".join(meta))

    # Show extra fields beyond what NodeBase defines
    base_fields = {"id", "type", "tier", "created", "updated", "tags"}
    extra = {
        k: v
        for k, v in m.model_dump().items()
        if k not in base_fields and v not in ("", 0, None, [])
    }
    for key, val in extra.items():
        label = key.replace("_", " ").title()
        parts.append(f"**{label}**: {val}")

    parts.append("")

    tags = _tags_line(m.tags)
    if tags:
        parts.append(tags.strip())
        parts.append("")

    return "\n".join(parts).rstrip() + "\n"


# ---------------------------------------------------------------------------
# Dispatch table
# ---------------------------------------------------------------------------

_RENDERERS: dict[str, object] = {
    "Finding": _render_finding,
    "Hypothesis": _render_hypothesis,
    "OpenQuestion": _render_open_question,
    "Paper": _render_paper,
    "Dataset": _render_dataset,
    "Document": _render_document,
    "Script": _render_script,
    "Execution": _render_execution,
    "ResearchNote": _render_note,
}


def render_node(model: NodeBase) -> str:
    """Render a knowledge node as formatted markdown."""
    renderer = _RENDERERS.get(model.type)
    if renderer is not None:
        return renderer(model)  # type: ignore[operator]
    return _render_generic(model)


# ---------------------------------------------------------------------------
# Synthesis renderer (Obsidian-compatible markdown with YAML frontmatter)
# ---------------------------------------------------------------------------

# Regex to find node ID references like [F-3a2b] and convert to [[F-3a2b]]
_NODE_ID_RE = re.compile(r"\[([A-Z]{1,2}-[0-9a-f]{4,8})\]")


def _obsidian_backlinks(text: str) -> str:
    """Convert [F-3a2b] citations to Obsidian [[F-3a2b]] backlinks."""
    return _NODE_ID_RE.sub(r"[[\1]]", text)


def render_synthesis(
    model: NodeBase,
    relationships: list[dict] | None = None,
) -> str:
    """Render a node as Obsidian-compatible markdown with YAML frontmatter.

    Parameters
    ----------
    model
        The knowledge node to render.
    relationships
        Optional list of relationship dicts with keys:
        ``source_id``, ``target_id``, ``relationship``, ``target_label``,
        ``target_title``.  Used to build a Relationships section.
    """
    # YAML frontmatter
    fm: dict = {
        "id": model.id,
        "type": model.type,
        "tier": model.tier,
    }
    if model.created:
        fm["created"] = model.created.split("T")[0] if "T" in model.created else model.created
    if model.tags:
        fm["tags"] = model.tags
    if model.stability:
        fm["stability"] = model.stability

    # Add type-specific frontmatter
    if isinstance(model, FindingModel):
        fm["confidence"] = model.confidence
        if model.artifact_type:
            fm["artifact_type"] = model.artifact_type
        if model.source:
            fm["source"] = model.source
    elif isinstance(model, HypothesisModel):
        fm["status"] = model.status
    elif isinstance(model, OpenQuestionModel):
        fm["priority"] = model.priority
    elif isinstance(model, PaperModel):
        if model.year:
            fm["year"] = model.year
        if model.doi:
            fm["doi"] = model.doi

    # Build frontmatter string
    fm_lines = ["---"]
    for key, val in fm.items():
        if isinstance(val, list):
            fm_lines.append(f"{key}:")
            for item in val:
                fm_lines.append(f"  - {item}")
        else:
            fm_lines.append(f"{key}: {val}")
    fm_lines.append("---")
    fm_lines.append("")

    # Body: reuse existing render_node output, convert to Obsidian backlinks
    body = render_node(model)
    body = _obsidian_backlinks(body)

    # Artifact embed
    if isinstance(model, FindingModel) and model.path:
        body += f"\n![{model.artifact_type or 'artifact'}]({model.path})\n"

    # Source attribution
    if isinstance(model, FindingModel) and model.source:
        body += f"\n*Source*: {model.source}\n"

    # Relationships section
    if relationships:
        body += "\n## Relationships\n\n"
        for rel in relationships:
            target_id = rel.get("target_id", "")
            rel_type = rel.get("relationship", "")
            target_title = rel.get("target_title", "")
            direction = rel.get("direction", "outgoing")

            if direction == "outgoing":
                line = f"- **{rel_type}** [[{target_id}]]"
            else:
                line = f"- [[{rel.get('source_id', '')}]] **{rel_type}** this"

            if target_title:
                line += f" ({target_title})"
            body += line + "\n"

    return "\n".join(fm_lines) + body
