"""Pydantic v2 models for Wheeler knowledge graph node types."""

from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Discriminator, TypeAdapter


class NodeBase(BaseModel):
    """Common fields shared by all knowledge graph nodes."""

    model_config = {"extra": "allow"}

    id: str
    type: str
    tier: str = "generated"
    created: str = ""
    updated: str = ""
    tags: list[str] = []

    @property
    def file_name(self) -> str:
        return f"{self.id}.json"


# ---------------------------------------------------------------------------
# Concrete node models
# ---------------------------------------------------------------------------


class FindingModel(NodeBase):
    type: Literal["Finding"] = "Finding"
    description: str = ""
    confidence: float = 0.0


class HypothesisModel(NodeBase):
    type: Literal["Hypothesis"] = "Hypothesis"
    statement: str = ""
    status: str = "open"


class OpenQuestionModel(NodeBase):
    type: Literal["OpenQuestion"] = "OpenQuestion"
    question: str = ""
    priority: int = 5


class DatasetModel(NodeBase):
    type: Literal["Dataset"] = "Dataset"
    path: str = ""
    data_type: str = ""
    description: str = ""


class PaperModel(NodeBase):
    type: Literal["Paper"] = "Paper"
    title: str = ""
    authors: str = ""
    doi: str = ""
    year: int = 0


class DocumentModel(NodeBase):
    type: Literal["Document"] = "Document"
    title: str = ""
    path: str = ""
    section: str = ""
    status: str = "draft"


class AnalysisModel(NodeBase):
    type: Literal["Analysis"] = "Analysis"
    script_path: str = ""
    script_hash: str = ""
    language: str = ""
    language_version: str = ""
    parameters: str = ""
    output_path: str = ""
    output_hash: str = ""
    executed_at: str = ""


class PlanModel(NodeBase):
    type: Literal["Plan"] = "Plan"
    status: str = ""


class ResearchNoteModel(NodeBase):
    type: Literal["ResearchNote"] = "ResearchNote"
    title: str = ""
    content: str = ""
    context: str = ""  # what prompted this note


class LedgerModel(NodeBase):
    type: Literal["Ledger"] = "Ledger"
    mode: str = ""  # which Wheeler act produced this (execute, write, etc.)
    prompt_summary: str = ""
    citations_found: list[str] = []
    citations_valid: list[str] = []
    citations_invalid: list[str] = []
    citations_missing_provenance: list[str] = []
    citations_stale: list[str] = []
    ungrounded: bool = False
    pass_rate: float = 0.0


# ---------------------------------------------------------------------------
# Prefix ↔ label mappings (canonical source of truth for the node type system)
# ---------------------------------------------------------------------------

PREFIX_TO_LABEL: dict[str, str] = {
    "PL": "Plan",
    "F": "Finding",
    "H": "Hypothesis",
    "Q": "OpenQuestion",
    "A": "Analysis",
    "D": "Dataset",
    "P": "Paper",
    "W": "Document",
    "N": "ResearchNote",
    "L": "Ledger",
}

LABEL_TO_PREFIX: dict[str, str] = {v: k for k, v in PREFIX_TO_LABEL.items()}

NODE_LABELS: list[str] = list(PREFIX_TO_LABEL.values())


# ---------------------------------------------------------------------------
# Discriminated union over all node types
# ---------------------------------------------------------------------------

KnowledgeNode = Annotated[
    Union[
        FindingModel,
        HypothesisModel,
        OpenQuestionModel,
        DatasetModel,
        PaperModel,
        DocumentModel,
        AnalysisModel,
        PlanModel,
        ResearchNoteModel,
        LedgerModel,
    ],
    Discriminator("type"),
]

KNOWLEDGE_NODE_ADAPTER: TypeAdapter[KnowledgeNode] = TypeAdapter(KnowledgeNode)

# ---------------------------------------------------------------------------
# Label -> model class mapping
# ---------------------------------------------------------------------------

_LABEL_TO_MODEL: dict[str, type[NodeBase]] = {
    "Finding": FindingModel,
    "Hypothesis": HypothesisModel,
    "OpenQuestion": OpenQuestionModel,
    "Dataset": DatasetModel,
    "Paper": PaperModel,
    "Document": DocumentModel,
    "Analysis": AnalysisModel,
    "Plan": PlanModel,
    "ResearchNote": ResearchNoteModel,
    "Ledger": LedgerModel,
}


def model_for_label(label: str) -> type[NodeBase]:
    """Return the Pydantic model class for a given node label.

    Raises ``KeyError`` if the label is not recognised.
    """
    return _LABEL_TO_MODEL[label]


# ---------------------------------------------------------------------------
# Human-readable title extraction
# ---------------------------------------------------------------------------


def title_for_node(node: NodeBase) -> str:
    """Extract a short title (~100 chars) from a node's primary content field."""
    if isinstance(node, FindingModel):
        return node.description[:100]
    if isinstance(node, HypothesisModel):
        return node.statement[:100]
    if isinstance(node, OpenQuestionModel):
        return node.question[:100]
    if isinstance(node, PaperModel):
        return node.title[:100]
    if isinstance(node, DocumentModel):
        return node.title[:100]
    if isinstance(node, DatasetModel):
        return node.description[:100]
    if isinstance(node, AnalysisModel):
        return f"Analysis: {node.script_path}"[:100]
    if isinstance(node, ResearchNoteModel):
        return (node.title[:100] if node.title else node.content[:100])
    if isinstance(node, LedgerModel):
        return f"Ledger: {node.mode} ({node.pass_rate:.0%} pass)"[:100]
    return node.id
