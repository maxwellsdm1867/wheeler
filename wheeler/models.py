"""Pydantic v2 models for Wheeler knowledge graph node types."""

from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Discriminator, TypeAdapter


class ChangeEntry(BaseModel):
    """One field-level change recorded in a node's change log."""

    timestamp: str
    action: str  # "created", "tier_changed", "invalidated", "cleared"
    changes: dict[str, list] = {}  # {"field": [old_value, new_value]}
    actor: str = "system"
    reason: str = ""


class NodeBase(BaseModel):
    """Common fields shared by all knowledge graph nodes."""

    model_config = {"extra": "allow"}

    id: str
    type: str
    tier: str = "generated"
    created: str = ""
    updated: str = ""
    tags: list[str] = []
    stability: float = 0.0
    stale: bool = False
    stale_since: str = ""
    session_id: str = ""
    display_name: str = ""
    change_log: list[ChangeEntry] = []

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
    path: str = ""  # optional: path to artifact (figure, table, CSV)
    artifact_type: str = ""  # figure, table, number, csv, etc.
    source: str = ""  # who/what produced this (e.g., collaborator name, paper ID)
    hash: str = ""


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
    hash: str = ""


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
    hash: str = ""


class ScriptModel(NodeBase):
    type: Literal["Script"] = "Script"
    path: str = ""
    hash: str = ""
    language: str = ""
    version: str = ""


class ExecutionModel(NodeBase):
    type: Literal["Execution"] = "Execution"
    kind: str = ""
    agent_id: str = "wheeler"
    status: str = "completed"
    started_at: str = ""
    ended_at: str = ""
    description: str = ""


class PlanModel(NodeBase):
    type: Literal["Plan"] = "Plan"
    title: str = ""
    path: str = ""
    status: str = ""
    hash: str = ""


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
    # Retrieval quality metrics
    context_nodes_used: int = 0       # nodes retrieved and actually cited
    context_nodes_retrieved: int = 0  # total nodes retrieved
    context_precision: float = 0.0    # used / retrieved (0.0 if none retrieved)
    coverage_gaps: list[str] = []     # keywords in output not backed by graph nodes


# ---------------------------------------------------------------------------
# Prefix ↔ label mappings (canonical source of truth for the node type system)
# ---------------------------------------------------------------------------

PREFIX_TO_LABEL: dict[str, str] = {
    "PL": "Plan",
    "F": "Finding",
    "H": "Hypothesis",
    "Q": "OpenQuestion",
    "S": "Script",
    "X": "Execution",
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
        ScriptModel,
        ExecutionModel,
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
    "Script": ScriptModel,
    "Execution": ExecutionModel,
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
    if isinstance(node, ScriptModel):
        return f"Script: {node.path}"[:100]
    if isinstance(node, PlanModel):
        return (node.title[:100] if node.title else f"Plan ({node.status})")
    if isinstance(node, ExecutionModel):
        return (node.description[:100] if node.description else f"Execution ({node.kind})")
    if isinstance(node, ResearchNoteModel):
        return (node.title[:100] if node.title else node.content[:100])
    if isinstance(node, LedgerModel):
        return f"Ledger: {node.mode} ({node.pass_rate:.0%} pass)"[:100]
    return node.id
