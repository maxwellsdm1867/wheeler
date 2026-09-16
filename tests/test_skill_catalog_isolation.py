"""Learned node procedures must never become host startup skill entries."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests import test_lesson_flow as flow
from wheeler import build_plugin
from wheeler.skill_discovery import discover_skills

lesson_project = flow.lesson_project


async def test_capturing_a_lesson_does_not_change_either_host_catalog(lesson_project):
    config, backend, root = lesson_project
    (root / "pyproject.toml").write_text('[project]\nversion = "0.16.0"\n')
    before = build_plugin.build_plugin_files(root)
    marker = "PRIVATE_LEARNED_BODY_a3916724"
    saved = await flow.capture(config, name="audit-node-bound-procedure", instructions=marker)
    path = Path(saved["path"])
    assert path.is_relative_to(root / ".notes" / "lessons")
    assert marker in path.read_text()
    for catalog in ("skills", ".claude/skills", ".agents/skills", ".codex/skills"):
        assert not path.is_relative_to(root / catalog)
        assert not list((root / catalog).rglob("SKILL.md"))

    after = build_plugin.build_plugin_files(root)
    assert after == before
    assert marker not in json.dumps(after)
    assert "audit-node-bound-procedure" not in json.dumps(after)

    # The accepted procedure is usable, but the graph delivers metadata only.
    found = await discover_skills(["D-retinadb"], config, backend)
    assert [s["id"] for s in found["linked_skills"]] == [saved["node_id"]]
    assert marker not in json.dumps(found)
    assert "instructions" not in found["linked_skills"][0]


@pytest.mark.parametrize("host", ["claude", "codex"])
def test_hosts_discover_only_shipped_catalog_and_defer_lesson_body(host):
    files = build_plugin.build_plugin_files()
    manifest_path = (build_plugin.CLAUDE_MANIFEST if host == "claude"
                     else build_plugin.CODEX_MANIFEST)
    manifest = json.loads(files[manifest_path])
    # Claude uses the standard skills/ convention; Codex declares it explicitly.
    assert Path(manifest.get("skills", "./skills/")) == Path("skills")
    stub = files["skills/lesson/SKILL.md"]
    assert 'name="lesson"' in stub and "get_act" in stub
    assert "You are Wheeler, deciding how a correction should persist" not in stub
    assert ".notes/lessons/" not in stub
    # No startup hook or shipped subagent preloads learned procedure content.
    for path, content in files.items():
        if path.startswith("hooks/"):
            assert ".notes/lessons" not in content
        if path.startswith("agents/") and path.endswith(".md"):
            frontmatter = content.split("---", 2)[1] if content.startswith("---") else ""
            assert "skills:" not in frontmatter
