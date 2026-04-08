"""Tests for wheeler.write_receipt module."""

import json

import pytest

from wheeler.write_receipt import RepairQueue, WriteReceipt


class TestWriteReceipt:
    def test_complete_receipt(self):
        r = WriteReceipt(
            node_id="F-abc12345",
            label="Finding",
            timestamp="2026-04-08",
            graph=True,
            json=True,
            synthesis=True,
        )
        assert r.complete is True

    def test_incomplete_receipt(self):
        r = WriteReceipt(
            node_id="F-abc12345",
            label="Finding",
            timestamp="2026-04-08",
            graph=True,
            json=True,
            synthesis=False,
        )
        assert r.complete is False

    def test_all_false_is_incomplete(self):
        r = WriteReceipt(
            node_id="F-abc12345",
            label="Finding",
            timestamp="2026-04-08",
            graph=False,
            json=False,
            synthesis=False,
        )
        assert r.complete is False

    def test_frozen_dataclass(self):
        r = WriteReceipt(
            node_id="F-abc12345",
            label="Finding",
            timestamp="2026-04-08",
            graph=True,
            json=True,
            synthesis=True,
        )
        with pytest.raises(AttributeError):
            r.graph = False  # type: ignore[misc]


class TestRepairQueue:
    def test_complete_receipt_not_enqueued(self, tmp_path):
        queue = RepairQueue(tmp_path)
        r = WriteReceipt(
            node_id="F-abc12345",
            label="Finding",
            timestamp="2026-04-08",
            graph=True,
            json=True,
            synthesis=True,
        )
        queue.enqueue(r)
        assert queue.pending() == []

    def test_incomplete_receipt_enqueued(self, tmp_path):
        queue = RepairQueue(tmp_path)
        r = WriteReceipt(
            node_id="F-abc12345",
            label="Finding",
            timestamp="2026-04-08",
            graph=True,
            json=True,
            synthesis=False,
        )
        queue.enqueue(r)
        pending = queue.pending()
        assert len(pending) == 1
        assert pending[0]["node_id"] == "F-abc12345"
        assert pending[0]["synthesis"] is False

    def test_multiple_enqueues(self, tmp_path):
        queue = RepairQueue(tmp_path)
        for i in range(3):
            r = WriteReceipt(
                node_id=f"F-{i:08d}",
                label="Finding",
                timestamp="2026-04-08",
                graph=True,
                json=False,
                synthesis=False,
            )
            queue.enqueue(r)
        assert len(queue.pending()) == 3

    def test_clear_removes_queue(self, tmp_path):
        queue = RepairQueue(tmp_path)
        r = WriteReceipt(
            node_id="F-abc12345",
            label="Finding",
            timestamp="2026-04-08",
            graph=True,
            json=False,
            synthesis=False,
        )
        queue.enqueue(r)
        assert len(queue.pending()) == 1
        queue.clear()
        assert queue.pending() == []

    def test_pending_empty_when_no_file(self, tmp_path):
        queue = RepairQueue(tmp_path)
        assert queue.pending() == []

    def test_enqueue_creates_parent_directories(self, tmp_path):
        nested = tmp_path / "deep" / "nested"
        queue = RepairQueue(nested)
        r = WriteReceipt(
            node_id="H-abc12345",
            label="Hypothesis",
            timestamp="2026-04-08",
            graph=True,
            json=False,
            synthesis=False,
        )
        queue.enqueue(r)
        assert len(queue.pending()) == 1
        assert nested.exists()

    def test_clear_when_no_file_is_noop(self, tmp_path):
        queue = RepairQueue(tmp_path)
        queue.clear()  # should not raise
        assert queue.pending() == []

    def test_jsonl_format(self, tmp_path):
        queue = RepairQueue(tmp_path)
        r = WriteReceipt(
            node_id="F-abc12345",
            label="Finding",
            timestamp="2026-04-08T12:00:00",
            graph=True,
            json=False,
            synthesis=False,
        )
        queue.enqueue(r)
        raw = (tmp_path / "repair_queue.jsonl").read_text()
        parsed = json.loads(raw.strip())
        assert parsed == {
            "node_id": "F-abc12345",
            "label": "Finding",
            "timestamp": "2026-04-08T12:00:00",
            "graph": True,
            "json": False,
            "synthesis": False,
        }
