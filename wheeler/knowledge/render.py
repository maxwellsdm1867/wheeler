"""Markdown renderer for Wheeler knowledge graph nodes.

Renders Pydantic node models as pretty markdown for human reading
via ``wh show``.
"""

from __future__ import annotations

from wheeler.models import (
    AnalysisModel,
    DatasetModel,
    DocumentModel,
    FindingModel,
    HypothesisModel,
    NodeBase,
    OpenQuestionModel,
    PaperModel,
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


def _render_analysis(m: AnalysisModel) -> str:
    parts: list[str] = [f"# Analysis [{m.id}]", ""]

    if m.script_path:
        lang_parts = [f"**Script**: {m.script_path}"]
        parts.append(" | ".join(lang_parts))
    lang_str = ""
    if m.language:
        lang_str = m.language
        if m.language_version:
            lang_str += f" {m.language_version}"
        parts.append(f"**Language**: {lang_str}")
    if m.script_hash:
        parts.append(f"**Hash**: {m.script_hash}")
    date = _fmt_date(m.executed_at)
    if date:
        parts.append(f"**Executed**: {date}")
    if m.output_path:
        parts.append(f"**Output**: {m.output_path}")
    if m.parameters:
        parts.append(f"**Parameters**: {m.parameters}")

    parts.append("")

    tags = _tags_line(m.tags)
    if tags:
        parts.append(tags.strip())
        parts.append("")

    return "\n".join(parts).rstrip() + "\n"


def _render_generic(m: NodeBase) -> str:
    """Fallback renderer for Experiment, Plan, CellType, Task, etc."""
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
    "Analysis": _render_analysis,
}


def render_node(model: NodeBase) -> str:
    """Render a knowledge node as formatted markdown."""
    renderer = _RENDERERS.get(model.type)
    if renderer is not None:
        return renderer(model)  # type: ignore[operator]
    return _render_generic(model)
