from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest


SCRIPT = Path(__file__).parents[1] / "scripts" / "configure-codex-dev.py"
SPEC = importlib.util.spec_from_file_location("configure_codex_dev", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
configure_codex_dev = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = configure_codex_dev
SPEC.loader.exec_module(configure_codex_dev)


def make_checkout(tmp_path: Path) -> Path:
    root = tmp_path / "Wheeler checkout with spaces"
    (root / "skills" / "start").mkdir(parents=True)
    (root / "skills" / "start" / "SKILL.md").write_text("---\nname: start\n---\n")
    (root / "pyproject.toml").write_text('[project]\nname = "wheeler"\n')
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    return root


@pytest.mark.parametrize(
    ("system", "environment", "version", "expected"),
    [
        ("Windows", {}, "", "windows"),
        ("Darwin", {}, "", "macos"),
        ("Linux", {}, "Linux version 6.8", "linux"),
        ("Linux", {"WSL_DISTRO_NAME": "Ubuntu"}, "", "wsl"),
        ("Linux", {}, "Linux microsoft-standard-WSL2", "wsl"),
    ],
)
def test_detect_host(system, environment, version, expected):
    assert (
        configure_codex_dev.detect_host(
            system=system, environ=environment, proc_version=version
        )
        == expected
    )


def test_render_native_config_round_trips_paths_and_uses_editable_checkout(tmp_path):
    root = make_checkout(tmp_path)
    uv = root / "tool bin" / "uv"
    launcher = configure_codex_dev.Launcher(str(uv), (), str(root))

    parsed = tomllib.loads(configure_codex_dev.render_config(launcher))

    assert set(parsed["mcp_servers"]) == set(configure_codex_dev.SERVER_MODULES)
    for name, module in configure_codex_dev.SERVER_MODULES.items():
        server = parsed["mcp_servers"][name]
        assert server["command"] == str(uv)
        assert server["args"] == [
            "run",
            "--frozen",
            "--project",
            str(root),
            "python",
            "-m",
            module,
        ]
        assert "uvx" not in server["command"]
        assert not any("password" in arg.lower() for arg in server["args"])


def test_render_windows_paths_are_valid_toml():
    launcher = configure_codex_dev.Launcher(
        r"C:\Program Files\uv\uv.exe", (), r"C:\Users\Mak and Nguyen\wheeler"
    )
    parsed = tomllib.loads(configure_codex_dev.render_config(launcher))
    server = parsed["mcp_servers"]["wheeler_core"]
    assert server["command"] == r"C:\Program Files\uv\uv.exe"
    assert server["args"][3] == r"C:\Users\Mak and Nguyen\wheeler"


def test_wsl_launcher_keeps_argument_boundaries_without_shell_quoting(tmp_path, monkeypatch):
    root = make_checkout(tmp_path)
    answers = iter(
        (
            "Ubuntu Dev",
            "/mnt/c/Users/Mak and Nguyen/wheeler",
            "/home/research user",
            "/opt/home brew/bin/uv",
        )
    )
    monkeypatch.setattr(configure_codex_dev, "_run_text", lambda argv: next(answers))

    launcher = configure_codex_dev._windows_wsl_launcher(
        root, uv=None, distro=None, wsl_command=r"C:\Windows\System32\wsl.exe"
    )
    parsed = tomllib.loads(configure_codex_dev.render_config(launcher))
    args = parsed["mcp_servers"]["wheeler_core"]["args"]

    assert args[:4] == [
        "-d",
        "Ubuntu Dev",
        "--exec",
        "/usr/bin/env",
    ]
    assert args[4].startswith("UV_PROJECT_ENVIRONMENT=/home/research user/.cache/wheeler/codex-dev/")
    assert args[5] == "/opt/home brew/bin/uv"
    assert "/mnt/c/" not in args[4]
    assert args[9] == "/mnt/c/Users/Mak and Nguyen/wheeler"
    assert "bash" not in args
    assert "-lc" not in args


def test_wsl_launcher_finds_homebrew_uv_outside_noninteractive_path(tmp_path, monkeypatch):
    root = make_checkout(tmp_path)

    def fake_run(argv):
        if "wslpath" in argv:
            return "/mnt/c/work/wheeler"
        if "printf %s \"$HOME\"" in argv:
            return "/home/scientist"
        if "command -v uv" in argv:
            raise configure_codex_dev.ConfigurationError("not on PATH")
        if "wheeler-uv-probe" in argv:
            assert "/home/other-user" not in argv
            return "/home/linuxbrew/.linuxbrew/bin/uv"
        raise AssertionError(argv)

    monkeypatch.setattr(configure_codex_dev, "_run_text", fake_run)
    launcher = configure_codex_dev._windows_wsl_launcher(
        root,
        uv=None,
        distro="Ubuntu",
        wsl_command=r"C:\Windows\System32\wsl.exe",
    )

    assert "/home/linuxbrew/.linuxbrew/bin/uv" in launcher.prefix_args
    environment = next(
        item for item in launcher.prefix_args if item.startswith("UV_PROJECT_ENVIRONMENT=")
    )
    assert environment.startswith(
        "UV_PROJECT_ENVIRONMENT=/home/scientist/.cache/wheeler/codex-dev/"
    )


def test_git_exclude_uses_rev_parse_result_for_worktree_layout(tmp_path, monkeypatch):
    root = make_checkout(tmp_path)
    common_exclude = tmp_path / "main.git" / "info" / "exclude"
    monkeypatch.setattr(
        configure_codex_dev, "_run_text", lambda argv: str(common_exclude)
    )

    resolved = configure_codex_dev.resolve_git_exclude(root)

    assert resolved == common_exclude.resolve()
    assert resolved != root / ".git" / "info" / "exclude"


@pytest.mark.skipif(os.name == "nt", reason="asserts Unix relative-symlink behavior")
def test_configure_creates_local_link_excludes_and_idempotent_config(tmp_path):
    root = make_checkout(tmp_path)
    uv = tmp_path / "bin" / "uv"
    uv.parent.mkdir()
    uv.touch()

    first = configure_codex_dev.configure(
        root, host="linux", uv=str(uv), wsl_distro=None, force=False, dry_run=False
    )
    second = configure_codex_dev.configure(
        root, host="linux", uv=str(uv), wsl_distro=None, force=False, dry_run=False
    )

    assert "created .agents/skills link" in first
    assert "kept existing .agents/skills link" in second
    assert (root / ".agents" / "skills").resolve() == (root / "skills").resolve()
    exclude_path = configure_codex_dev.resolve_git_exclude(root)
    excludes = exclude_path.read_text()
    assert excludes.count("/.agents/") == 1
    assert excludes.count("/.codex/") == 1
    assert tomllib.loads((root / ".codex" / "config.toml").read_text())


def test_existing_hand_written_config_is_preserved(tmp_path):
    root = make_checkout(tmp_path)
    (root / ".codex").mkdir()
    original = "# custom configuration\n[mcp_servers.mine]\ncommand = \"mine\"\n"
    (root / ".codex" / "config.toml").write_text(original)
    uv = tmp_path / "uv"
    uv.touch()

    with pytest.raises(configure_codex_dev.ConfigurationError, match="differs"):
        configure_codex_dev.configure(
            root,
            host="linux",
            uv=str(uv),
            wsl_distro=None,
            force=False,
            dry_run=False,
        )

    assert (root / ".codex" / "config.toml").read_text() == original
    assert not (root / ".agents").exists()
    excludes = configure_codex_dev.resolve_git_exclude(root).read_text()
    assert "/.codex/" not in excludes


def test_git_exclude_failure_happens_before_any_local_write(tmp_path, monkeypatch):
    root = make_checkout(tmp_path)
    uv = tmp_path / "uv"
    uv.touch()

    def fail_resolution(project_root):
        raise configure_codex_dev.ConfigurationError("cannot resolve git metadata")

    monkeypatch.setattr(configure_codex_dev, "resolve_git_exclude", fail_resolution)

    with pytest.raises(configure_codex_dev.ConfigurationError, match="git metadata"):
        configure_codex_dev.configure(
            root,
            host="linux",
            uv=str(uv),
            wsl_distro=None,
            force=False,
            dry_run=False,
        )

    assert not (root / ".agents").exists()
    assert not (root / ".codex").exists()


def test_force_never_replaces_a_real_skills_directory(tmp_path):
    root = make_checkout(tmp_path)
    local_skills = root / ".agents" / "skills"
    local_skills.mkdir(parents=True)
    sentinel = local_skills / "keep.txt"
    sentinel.write_text("user data")

    with pytest.raises(configure_codex_dev.ConfigurationError, match="real directory"):
        configure_codex_dev.ensure_skill_link(root, force=True, dry_run=False)

    assert sentinel.read_text() == "user data"
