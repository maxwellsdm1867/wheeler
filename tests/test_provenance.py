"""Tests for wheeler.graph.provenance module."""

import tempfile
from pathlib import Path

import pytest

from wheeler.graph.provenance import (
    AnalysisProvenance,
    StaleAnalysis,
    hash_file,
)


class TestHashFile:
    def test_hash_known_content(self, tmp_path):
        f = tmp_path / "test.m"
        f.write_text("hello world")
        h = hash_file(f)
        assert isinstance(h, str)
        assert len(h) == 64  # SHA-256 hex digest

    def test_hash_deterministic(self, tmp_path):
        f = tmp_path / "test.m"
        f.write_text("deterministic content")
        assert hash_file(f) == hash_file(f)

    def test_hash_changes_with_content(self, tmp_path):
        f = tmp_path / "test.m"
        f.write_text("version 1")
        h1 = hash_file(f)
        f.write_text("version 2")
        h2 = hash_file(f)
        assert h1 != h2

    def test_hash_empty_file(self, tmp_path):
        f = tmp_path / "empty.m"
        f.write_text("")
        h = hash_file(f)
        assert len(h) == 64

    def test_hash_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            hash_file("/nonexistent/file.m")


class TestAnalysisProvenance:
    def test_create_minimal(self):
        prov = AnalysisProvenance(
            script_path="/path/to/script.m",
            script_hash="abc123",
            language="matlab",
        )
        assert prov.script_path == "/path/to/script.m"
        assert prov.language == "matlab"
        assert prov.language_version == ""
        assert prov.parameters == ""

    def test_create_full(self):
        prov = AnalysisProvenance(
            script_path="/path/to/script.py",
            script_hash="def456",
            language="python",
            language_version="3.11",
            parameters="--threshold 0.5",
            output_path="/path/to/output.csv",
            output_hash="ghi789",
        )
        assert prov.language_version == "3.11"
        assert prov.output_hash == "ghi789"


class TestStaleAnalysis:
    def test_create(self):
        s = StaleAnalysis(
            node_id="A-abcd1234",
            script_path="/path/to/script.m",
            stored_hash="old_hash",
            current_hash="new_hash",
        )
        assert s.node_id == "A-abcd1234"
        assert s.stored_hash != s.current_hash

    def test_missing_file(self):
        s = StaleAnalysis(
            node_id="A-abcd1234",
            script_path="/missing/script.m",
            stored_hash="old_hash",
            current_hash="FILE_NOT_FOUND",
        )
        assert s.current_hash == "FILE_NOT_FOUND"
