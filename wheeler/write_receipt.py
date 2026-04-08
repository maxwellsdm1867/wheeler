"""Write receipt tracking for Wheeler's triple-write system.

Each mutation records which storage layers (graph, JSON, synthesis)
succeeded. Incomplete writes are queued for later repair.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WriteReceipt:
    """Record of which layers were written for a single node mutation."""

    node_id: str
    label: str
    timestamp: str
    graph: bool
    json: bool
    synthesis: bool

    @property
    def complete(self) -> bool:
        return self.graph and self.json and self.synthesis


class RepairQueue:
    """Append-only JSONL queue for incomplete triple-writes."""

    def __init__(self, log_dir: Path) -> None:
        self._path = log_dir / "repair_queue.jsonl"

    def enqueue(self, receipt: WriteReceipt) -> None:
        """Append an incomplete receipt to the repair queue.

        Complete receipts (all three layers succeeded) are silently skipped.
        """
        if receipt.complete:
            return
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._path, "a") as f:
                f.write(json.dumps(asdict(receipt)) + "\n")
            logger.info(
                "Queued incomplete write for %s (graph=%s, json=%s, synthesis=%s)",
                receipt.node_id,
                receipt.graph,
                receipt.json,
                receipt.synthesis,
            )
        except Exception:
            logger.error(
                "Failed to enqueue repair for %s", receipt.node_id, exc_info=True
            )

    def pending(self) -> list[dict]:
        """Read all pending repair entries."""
        if not self._path.exists():
            return []
        entries: list[dict] = []
        for line in self._path.read_text().strip().split("\n"):
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return entries

    def clear(self) -> None:
        """Remove the queue file after successful repair."""
        if self._path.exists():
            self._path.unlink()
            logger.info("Repair queue cleared")
