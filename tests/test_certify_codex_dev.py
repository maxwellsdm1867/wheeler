"""Tests for the strict Codex development-environment certification command."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).parents[1] / "scripts" / "certify-codex-dev.py"
SPEC = importlib.util.spec_from_file_location("certify_codex_dev", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
certify = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = certify
SPEC.loader.exec_module(certify)


def _make_skill_tree(root: Path, count: int = 39) -> None:
    for index in range(count):
        name = f"skill-{index:02d}"
        skill = root / "skills" / name
        skill.mkdir(parents=True, exist_ok=True)
        (skill / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: Test skill {index}\n---\n"
        )


def test_project_skills_requires_exact_canonical_surface(tmp_path, monkeypatch):
    _make_skill_tree(tmp_path)
    visible = tmp_path / ".agents" / "skills"
    visible.mkdir(parents=True)
    for source in (tmp_path / "skills").glob("*/SKILL.md"):
        destination = visible / source.parent.name
        destination.mkdir()
        (destination / "SKILL.md").write_text(source.read_text())
    monkeypatch.setattr(certify.os.path, "samefile", lambda left, right: True)

    assert len(certify.verify_project_skills(tmp_path)) == 39

    (visible / "skill-00" / "SKILL.md").unlink()
    with pytest.raises(certify.CertificationError, match="differs"):
        certify.verify_project_skills(tmp_path)


def test_project_skills_rejects_detached_copy(tmp_path, monkeypatch):
    _make_skill_tree(tmp_path)
    visible = tmp_path / ".agents" / "skills"
    visible.mkdir(parents=True)
    for source in (tmp_path / "skills").glob("*/SKILL.md"):
        destination = visible / source.parent.name
        destination.mkdir()
        (destination / "SKILL.md").write_text(source.read_text())
    monkeypatch.setattr(certify.os.path, "samefile", lambda left, right: False)

    with pytest.raises(certify.CertificationError, match="separate copy"):
        certify.verify_project_skills(tmp_path)


@pytest.mark.parametrize(
    "old, new, message",
    [
        ("name: skill-00", "name: wrong-name", "expected 'skill-00'"),
        ("description: Test skill 0", "", "no non-empty description"),
    ],
)
def test_project_skills_validate_required_frontmatter(
    tmp_path, monkeypatch, old, new, message
):
    _make_skill_tree(tmp_path)
    visible = tmp_path / ".agents" / "skills"
    visible.mkdir(parents=True)
    for source in (tmp_path / "skills").glob("*/SKILL.md"):
        destination = visible / source.parent.name
        destination.mkdir()
        text = source.read_text()
        if source.parent.name == "skill-00":
            text = text.replace(old, new)
        (destination / "SKILL.md").write_text(text)
    monkeypatch.setattr(certify.os.path, "samefile", lambda left, right: True)

    with pytest.raises(certify.CertificationError, match=message):
        certify.verify_project_skills(tmp_path)


@pytest.mark.asyncio
async def test_mcp_surface_and_codex_start_act_are_strict(tmp_path):
    config = tmp_path / ".codex" / "config.toml"
    config.parent.mkdir()
    lines = [certify.GENERATED_CONFIG_MARKER]
    for name in certify.EXPECTED_SERVERS:
        lines.extend(
            [
                f"[mcp_servers.{name}]",
                'command = "/absolute/uv"',
                (
                    'args = ["run", "--frozen", "--project", "/checkout", '
                    f'"python", "-m", "{certify.SERVER_MODULES[name]}"]'
                ).replace("/checkout", str(tmp_path).replace("\\", "\\\\")),
                "enabled = true",
            ]
        )
    config.write_text("\n".join(lines))
    surfaces_by_server = {}
    offset = 0
    for name, count in certify.EXPECTED_SERVERS.items():
        surfaces_by_server[name] = {
            f"tool-{index}" for index in range(offset, offset + count)
        }
        offset += count

    async def probe(command, args, *, call_start, environment):
        server = next(name for name, module in certify.SERVER_MODULES.items() if module == args[-1])
        act = (
            {"name": "wh:start", "host": "codex", "body": "Start Wheeler."}
            if call_start
            else None
        )
        query_result = {"results": [{"value": 1}], "count": 1} if call_start else None
        return surfaces_by_server[server], act, query_result

    surfaces = await certify.verify_mcp_surface(
        config, neo4j_env={}, probe=probe
    )
    assert sum(len(names) for names in surfaces.values()) == 53

    surfaces_by_server["wheeler_ops"] = set()
    with pytest.raises(certify.CertificationError, match="expected 10"):
        await certify.verify_mcp_surface(config, neo4j_env={}, probe=probe)


def test_generated_command_rejects_released_uvx_package():
    with pytest.raises(certify.CertificationError, match="uvx"):
        certify._validate_generated_command(
            "wheeler_core",
            "/usr/bin/uvx",
            ["--from", "wheeler", "wheeler-core-mcp"],
            Path("/checkout"),
        )


def test_generated_command_rejects_stale_checkout(tmp_path):
    stale = tmp_path / "other-clone"
    args = [
        "run",
        "--frozen",
        "--project",
        str(stale),
        "python",
        "-m",
        "wheeler.mcp_core",
    ]
    with pytest.raises(certify.CertificationError, match="different checkout"):
        certify._validate_generated_command(
            "wheeler_core", "/usr/bin/uv", args, tmp_path
        )


def test_cli_does_not_allow_e2e_subset_override():
    with pytest.raises(SystemExit):
        certify._parser().parse_args(["--e2e-target", "tests/e2e/test_one.py"])


def test_neo4j_check_requires_return_one_result():
    certify._verify_neo4j_result({"results": [{"value": 1}], "count": 1})
    with pytest.raises(certify.CertificationError, match="Neo4j RETURN 1 failed"):
        certify._verify_neo4j_result({"error": "unauthorized", "results": [], "count": 0})


def _runner_with_xml(xml: str, returncode: int = 0):
    def runner(command, **kwargs):
        report_arg = next(arg for arg in command if arg.startswith("--junitxml="))
        Path(report_arg.split("=", 1)[1]).write_text(xml)
        return subprocess.CompletedProcess(command, returncode, stdout="", stderr="")

    return runner


def _launcher(root: Path):
    return {
        "command": "/usr/bin/uv",
        "args": [
            "run",
            "--frozen",
            "--project",
            str(root),
            "python",
            "-m",
            "wheeler.mcp_core",
        ],
    }


def test_e2e_requires_nonempty_all_passed_run(tmp_path):
    result = certify.run_e2e(
        tmp_path,
        launcher=_launcher(tmp_path),
        runner=_runner_with_xml('<testsuite tests="3" failures="0" errors="0" skipped="0"/>'),
    )
    assert result == certify.E2EResult(3, 3, 0, 0, 0)


@pytest.mark.parametrize(
    "xml, message",
    [
        ('<testsuite tests="0" failures="0" errors="0" skipped="0"/>', "tests=0"),
        ('<testsuite tests="3" failures="0" errors="0" skipped="1"/>', "skipped=1"),
        ('<testsuite tests="3" failures="1" errors="0" skipped="0"/>', "failures=1"),
    ],
)
def test_e2e_rejects_empty_skipped_or_failed_runs(tmp_path, xml, message):
    with pytest.raises(certify.CertificationError, match=message):
        certify.run_e2e(
            tmp_path,
            launcher=_launcher(tmp_path),
            runner=_runner_with_xml(xml),
        )


def test_e2e_failure_output_redacts_password(tmp_path):
    secret = "do-not-print-this"

    def runner(command, **kwargs):
        return subprocess.CompletedProcess(command, 4, stdout="", stderr=f"bad {secret}")

    with pytest.raises(certify.CertificationError) as caught:
        certify.run_e2e(
            tmp_path,
            launcher=_launcher(tmp_path),
            secrets=(secret,),
            runner=runner,
        )
    assert secret not in str(caught.value)
    assert "[REDACTED]" in str(caught.value)
