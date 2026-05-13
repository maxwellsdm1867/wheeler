"""Tests for wheeler.portability -- path rewriting, secret scanning,
git discovery, manifest signatures.

All tests are pure Python (no graph, no Neo4j, no live network).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from wheeler.portability import (
    absolutize,
    compute_manifest_signature,
    discover_external_reference,
    iter_path_fields,
    relativize,
    scan_for_secrets,
)


# ---------------------------------------------------------------------------
# relativize
# ---------------------------------------------------------------------------


class TestRelativize:
    def test_path_inside_project_root(self, tmp_path: Path) -> None:
        """A path inside project_root gets the ${PROJECT}/ sentinel prefix."""
        project_root = tmp_path / "myproject"
        project_root.mkdir()
        file_path = str(project_root / "data" / "results.csv")
        result, inside = relativize(file_path, project_root)
        assert inside is True
        assert result == "${PROJECT}/data/results.csv"

    def test_path_outside_project_root(self, tmp_path: Path) -> None:
        """A path outside project_root is returned unchanged."""
        project_root = tmp_path / "myproject"
        project_root.mkdir()
        outside = str(tmp_path / "other" / "file.txt")
        result, inside = relativize(outside, project_root)
        assert inside is False
        assert result == outside

    def test_path_exactly_project_root(self, tmp_path: Path) -> None:
        """A path equal to project_root itself returns '${PROJECT}/' with trailing slash."""
        project_root = tmp_path / "myproject"
        project_root.mkdir()
        result, inside = relativize(str(project_root), project_root)
        assert inside is True
        assert result == "${PROJECT}/"

    def test_roundtrip_with_absolutize(self, tmp_path: Path) -> None:
        """relativize followed by absolutize round-trips to the original absolute path."""
        project_root = tmp_path / "myproject"
        project_root.mkdir()
        original = str(project_root / "scripts" / "run.py")
        stored, _ = relativize(original, project_root)
        recovered = absolutize(stored, project_root)
        # Both should resolve to the same absolute path.
        assert Path(recovered).resolve() == Path(original).resolve()

    def test_deeply_nested_path(self, tmp_path: Path) -> None:
        """A deeply nested path inside project_root is correctly relativized."""
        project_root = tmp_path / "proj"
        project_root.mkdir()
        file_path = str(project_root / "a" / "b" / "c" / "d.txt")
        result, inside = relativize(file_path, project_root)
        assert inside is True
        assert result == "${PROJECT}/a/b/c/d.txt"

    def test_symlink_resolves_correctly(self, tmp_path: Path) -> None:
        """Path resolution follows symlinks when checking containment."""
        project_root = tmp_path / "proj"
        project_root.mkdir()
        target_dir = tmp_path / "target"
        target_dir.mkdir()
        link = project_root / "link"
        link.symlink_to(target_dir)
        # The resolved symlink points outside project_root.
        file_inside_symlink = str(link / "file.txt")
        result, inside = relativize(file_inside_symlink, project_root)
        # After resolve(), link/file.txt -> target/file.txt which is outside proj/
        assert inside is False


# ---------------------------------------------------------------------------
# absolutize
# ---------------------------------------------------------------------------


class TestAbsolutize:
    def test_project_sentinel_prefix(self, tmp_path: Path) -> None:
        """${PROJECT}/foo is joined with project_root to produce an absolute path."""
        project_root = tmp_path / "myproject"
        project_root.mkdir()
        stored = "${PROJECT}/data/file.csv"
        result = absolutize(stored, project_root)
        expected = str(project_root.resolve() / "data" / "file.csv")
        assert result == expected

    def test_external_absolute_path_passes_through(self, tmp_path: Path) -> None:
        """An absolute path without the sentinel passes through unchanged."""
        project_root = tmp_path / "myproject"
        project_root.mkdir()
        external = "/some/external/data.csv"
        result = absolutize(external, project_root)
        assert result == external

    def test_plain_string_passes_through(self, tmp_path: Path) -> None:
        """A plain string (no sentinel, no leading slash) passes through unchanged."""
        project_root = tmp_path / "proj"
        result = absolutize("relative/path.txt", project_root)
        assert result == "relative/path.txt"

    def test_empty_suffix_returns_project_root(self, tmp_path: Path) -> None:
        """${PROJECT}/ (trailing slash only) resolves to project_root itself."""
        project_root = tmp_path / "proj"
        project_root.mkdir()
        result = absolutize("${PROJECT}/", project_root)
        # Should be project_root / "" which is project_root itself.
        assert Path(result).resolve() == project_root.resolve()


# ---------------------------------------------------------------------------
# iter_path_fields
# ---------------------------------------------------------------------------


class TestIterPathFields:
    @pytest.mark.parametrize("label", ["Finding", "Dataset", "Document", "Script", "Plan"])
    def test_known_labels_yield_path(self, label: str) -> None:
        fields = list(iter_path_fields(label))
        assert fields == ["path"]

    @pytest.mark.parametrize("label", ["Hypothesis", "OpenQuestion", "Paper", "Execution", "ResearchNote", "Ledger"])
    def test_unknown_labels_yield_nothing(self, label: str) -> None:
        fields = list(iter_path_fields(label))
        assert fields == []


# ---------------------------------------------------------------------------
# scan_for_secrets
# ---------------------------------------------------------------------------


class TestScanForSecrets:
    def test_catches_anthropic_api_key_literal(self) -> None:
        content = b"ANTHROPIC_API_KEY=sk-ant-xxxx\n"
        hits = scan_for_secrets(content, "config.env")
        names = [h[0] for h in hits]
        assert "ANTHROPIC_API_KEY" in names

    def test_catches_api_anthropic_com_url(self) -> None:
        content = b"base_url = 'https://api.anthropic.com/v1'\n"
        hits = scan_for_secrets(content, "client.py")
        names = [h[0] for h in hits]
        assert "api.anthropic.com" in names

    def test_catches_import_anthropic(self) -> None:
        content = b"import anthropic\nclient = anthropic.Client()\n"
        hits = scan_for_secrets(content, "agent.py")
        names = [h[0] for h in hits]
        assert "import anthropic" in names

    def test_catches_from_anthropic_import(self) -> None:
        content = b"from anthropic import Anthropic\n"
        hits = scan_for_secrets(content, "agent.py")
        names = [h[0] for h in hits]
        assert "from anthropic import" in names

    def test_catches_anthropic_anthropic_instantiation(self) -> None:
        content = b"client = anthropic.Anthropic()\n"
        hits = scan_for_secrets(content, "tool.py")
        names = [h[0] for h in hits]
        assert "anthropic.Anthropic()" in names

    def test_catches_sk_ant_token(self) -> None:
        content = b"token = 'sk-ant-api03-abcDEF1234567890'\n"
        hits = scan_for_secrets(content, "secrets.env")
        names = [h[0] for h in hits]
        assert "sk-ant-token" in names

    def test_clean_content_returns_empty(self) -> None:
        content = b"x = 1\nprint('hello world')\n"
        hits = scan_for_secrets(content, "script.py")
        assert hits == []

    def test_binary_safe_decoding(self) -> None:
        """Bytes with high-latin1 chars do not crash the scanner."""
        content = b"\xff\xfe" + b"ANTHROPIC_API_KEY=oops\n"
        hits = scan_for_secrets(content, "binary.bin")
        names = [h[0] for h in hits]
        assert "ANTHROPIC_API_KEY" in names

    def test_snippet_field_is_populated(self) -> None:
        """Each hit includes a non-empty snippet of the matched text."""
        content = b"sk-ant-api03-realtoken123\n"
        hits = scan_for_secrets(content, "creds.txt")
        assert hits
        for _name, snippet in hits:
            assert snippet


# ---------------------------------------------------------------------------
# discover_external_reference
# ---------------------------------------------------------------------------


def _make_git_repo(path: Path) -> None:
    """Initialise a git repo at path with a single commit."""
    subprocess.run(["git", "init", str(path)], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(path), "config", "user.email", "test@example.com"],
        check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(path), "config", "user.name", "Test"],
        check=True, capture_output=True,
    )
    # Create a file and commit it so HEAD exists.
    readme = path / "README.txt"
    readme.write_text("init\n")
    subprocess.run(["git", "-C", str(path), "add", "."], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(path), "commit", "-m", "init"],
        check=True, capture_output=True,
    )


class TestDiscoverExternalReference:
    def test_returns_dict_inside_git_repo(self, tmp_path: Path) -> None:
        """A file inside a git repo returns a dict with git_remote and git_commit."""
        repo = tmp_path / "repo"
        repo.mkdir()
        _make_git_repo(repo)
        file_path = str(repo / "README.txt")
        result = discover_external_reference(file_path)
        assert result is not None
        assert result["path"] == file_path
        assert "git_remote" in result  # empty string is fine for a local repo
        assert "git_commit" in result
        assert len(result["git_commit"]) == 40  # full SHA
        assert isinstance(result["git_dirty"], bool)

    def test_returns_none_for_plain_directory(self, tmp_path: Path) -> None:
        """A directory without a .git folder returns None."""
        plain_dir = tmp_path / "plain"
        plain_dir.mkdir()
        file_path = str(plain_dir / "data.csv")
        # File doesn't exist, should return None.
        result = discover_external_reference(file_path)
        assert result is None

    def test_returns_none_for_nonexistent_path(self, tmp_path: Path) -> None:
        """A path that does not exist on disk returns None."""
        result = discover_external_reference(str(tmp_path / "no_such_file.txt"))
        assert result is None

    def test_git_dirty_is_false_for_clean_repo(self, tmp_path: Path) -> None:
        """A clean repo (no uncommitted changes) reports git_dirty=False."""
        repo = tmp_path / "clean_repo"
        repo.mkdir()
        _make_git_repo(repo)
        file_path = str(repo / "README.txt")
        result = discover_external_reference(file_path)
        assert result is not None
        assert result["git_dirty"] is False

    def test_git_dirty_is_true_for_dirty_repo(self, tmp_path: Path) -> None:
        """A repo with uncommitted changes reports git_dirty=True."""
        repo = tmp_path / "dirty_repo"
        repo.mkdir()
        _make_git_repo(repo)
        (repo / "untracked.txt").write_text("new file\n")
        file_path = str(repo / "README.txt")
        result = discover_external_reference(file_path)
        assert result is not None
        assert result["git_dirty"] is True


# ---------------------------------------------------------------------------
# compute_manifest_signature
# ---------------------------------------------------------------------------


class TestComputeManifestSignature:
    def test_signature_is_stable_under_key_reordering(self) -> None:
        """The signature does not depend on dict insertion order."""
        manifest_a = {"b": 2, "a": 1, "c": 3}
        manifest_b = {"c": 3, "a": 1, "b": 2}
        assert compute_manifest_signature(manifest_a) == compute_manifest_signature(manifest_b)

    def test_signature_changes_when_content_changes(self) -> None:
        """Changing any value produces a different signature."""
        manifest = {"key": "value", "num": 42}
        sig1 = compute_manifest_signature(manifest)
        manifest_changed = {"key": "value", "num": 43}
        sig2 = compute_manifest_signature(manifest_changed)
        assert sig1 != sig2

    def test_manifest_signature_field_excluded_from_computation(self) -> None:
        """A pre-existing manifest_signature field is excluded from the digest."""
        manifest_unsigned = {"a": 1, "b": 2}
        sig_unsigned = compute_manifest_signature(manifest_unsigned)
        manifest_signed = {"a": 1, "b": 2, "manifest_signature": sig_unsigned}
        sig_resigned = compute_manifest_signature(manifest_signed)
        assert sig_unsigned == sig_resigned

    def test_signature_format_is_sha256_prefixed(self) -> None:
        """The returned string starts with 'sha256:' followed by 64 hex chars."""
        sig = compute_manifest_signature({"x": 1})
        assert sig.startswith("sha256:")
        hex_part = sig[len("sha256:"):]
        assert len(hex_part) == 64
        assert all(c in "0123456789abcdef" for c in hex_part)

    def test_empty_manifest_is_stable(self) -> None:
        """An empty manifest dict produces a consistent signature."""
        sig1 = compute_manifest_signature({})
        sig2 = compute_manifest_signature({})
        assert sig1 == sig2

    def test_nested_values_are_included(self) -> None:
        """Nested dicts and lists affect the signature."""
        m1 = {"meta": {"version": 1}}
        m2 = {"meta": {"version": 2}}
        assert compute_manifest_signature(m1) != compute_manifest_signature(m2)

    def test_signature_consistent_with_manual_computation(self) -> None:
        """Cross-check against a manual SHA-256 computation."""
        import hashlib

        manifest = {"z": "end", "a": "start"}
        expected_payload = json.dumps({"a": "start", "z": "end"}, sort_keys=True).encode("utf-8")
        expected_hex = hashlib.sha256(expected_payload).hexdigest()
        assert compute_manifest_signature(manifest) == f"sha256:{expected_hex}"
