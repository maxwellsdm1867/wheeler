"""Legacy-install vs `wh`-plugin collision: detection, refusal, migration.

Claude Code namespaces plugin skills as `/<plugin>:<skill>`, so the plugin
named `wh` serves `/wh:plan`, which is exactly what a legacy
`~/.claude/commands/wh/plan.md` already owns. Proven by canary: the legacy
file WINS and nothing reports the conflict. These tests pin the three
behaviours that make that loud: detection, a refusing `install()`, and
`wheeler migrate-to-plugin`.

Everything is redirected at tmp_path via the same `fake_home` / `fake_data`
fixtures used by tests/test_installer.py. No test touches the real ~/.claude.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

import wheeler.cli as topcli  # registers doctor / migrate-to-plugin on the app
import wheeler.installer as installer

runner = CliRunner()


# ---------------------------------------------------------------------------
# fixtures (mirrors tests/test_installer.py so both files stay hermetic)
# ---------------------------------------------------------------------------


@pytest.fixture()
def fake_home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    claude_dir = home / ".claude"
    claude_dir.mkdir(parents=True)

    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    monkeypatch.setattr(installer, "INSTALL_BASE", claude_dir)
    monkeypatch.setattr(installer, "MANIFEST_PATH", claude_dir / "wheeler-manifest.json")
    return home


@pytest.fixture()
def fake_data(tmp_path):
    data = tmp_path / "_data"
    cmds = data / "commands"
    agents = data / "agents"
    hooks = data / "hooks"
    cmds.mkdir(parents=True)
    agents.mkdir(parents=True)
    hooks.mkdir(parents=True)

    (cmds / "discuss.md").write_text("# discuss\nplaceholder")
    (cmds / "plan.md").write_text("# plan\nplaceholder")
    (agents / "wheeler-worker.md").write_text("# worker\nplaceholder")
    (hooks / "wheeler-check-update.js").write_text("// update hook")
    (hooks / "wheeler-statusline.js").write_text("// statusline hook")
    (data / "mcp.json").write_text(json.dumps({"mcpServers": {}}))
    return data


def _enable_plugin(home: Path, key: str = "wh@wheeler", value: bool = True) -> None:
    """Write an enabledPlugins entry the way Claude Code does."""
    path = home / ".claude" / "settings.json"
    settings = json.loads(path.read_text()) if path.exists() else {}
    settings.setdefault("enabledPlugins", {})[key] = value
    settings.setdefault("extraKnownMarketplaces", {})["wheeler"] = {
        "source": {"source": "github", "repo": "maxwellsdm1867/wheeler"}
    }
    path.write_text(json.dumps(settings, indent=2))


def _install_plugin_record(home: Path, key: str = "wh@wheeler", scope: str = "user") -> None:
    """Write the plugins/installed_plugins.json record Claude Code keeps."""
    path = home / ".claude" / "plugins" / "installed_plugins.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "version": 2,
                "plugins": {key: [{"scope": scope, "version": "0.13.0"}]},
            }
        )
    )


# ---------------------------------------------------------------------------
# detect_plugin
# ---------------------------------------------------------------------------


def test_detect_plugin_absent(fake_home):
    status = installer.detect_plugin()
    assert status.present is False
    assert status.active is False
    assert "not installed" in status.describe()


def test_detect_plugin_from_enabled_plugins(fake_home):
    _enable_plugin(fake_home)

    status = installer.detect_plugin()
    assert status.enabled is True
    assert status.active is True
    assert status.keys == ("wh@wheeler",)
    assert "enabledPlugins:user" in status.scopes
    assert "wheeler" in status.marketplaces


def test_detect_plugin_from_settings_local(fake_home):
    """settings.local.json is a real scope and must be read too."""
    (fake_home / ".claude" / "settings.local.json").write_text(
        json.dumps({"enabledPlugins": {"wh@wheeler": True}})
    )

    status = installer.detect_plugin()
    assert status.active is True
    assert "enabledPlugins:user-local" in status.scopes


def test_detect_plugin_from_project_scope(fake_home, tmp_path):
    project = tmp_path / "proj"
    (project / ".claude").mkdir(parents=True)
    (project / ".claude" / "settings.json").write_text(
        json.dumps({"enabledPlugins": {"wh@wheeler": True}})
    )

    assert installer.detect_plugin().active is False  # user scope only
    assert installer.detect_plugin(project_dir=project).active is True


def test_detect_plugin_from_installed_plugins_json(fake_home):
    """A plugin installed but not in enabledPlugins still serves commands."""
    _install_plugin_record(fake_home)

    status = installer.detect_plugin()
    assert status.installed is True
    assert status.active is True
    assert "installed:user" in status.scopes


def test_detect_plugin_explicitly_disabled_is_not_active(fake_home):
    _enable_plugin(fake_home, value=False)
    _install_plugin_record(fake_home)

    status = installer.detect_plugin()
    assert status.present is True
    assert status.disabled is True
    assert status.active is False, "a disabled plugin cannot be shadowed"


def test_detect_plugin_matches_any_marketplace(fake_home):
    """Any plugin named `wh` owns /wh:, whatever marketplace shipped it."""
    _enable_plugin(fake_home, key="wh@someone-elses-fork")

    status = installer.detect_plugin()
    assert status.active is True
    assert status.keys == ("wh@someone-elses-fork",)


def test_detect_plugin_ignores_other_plugins(fake_home):
    _enable_plugin(fake_home, key="wheeler-docs@wheeler")

    assert installer.detect_plugin().present is False


def test_detect_plugin_survives_malformed_settings(fake_home):
    (fake_home / ".claude" / "settings.json").write_text("NOT JSON {{{")

    assert installer.detect_plugin().present is False


# ---------------------------------------------------------------------------
# legacy_status
# ---------------------------------------------------------------------------


def test_legacy_status_absent(fake_home):
    legacy = installer.legacy_status()
    assert legacy.present is False
    assert legacy.describe() == "no legacy install"


def test_legacy_status_reads_manifest(fake_home, fake_data, monkeypatch):
    monkeypatch.setattr(installer, "_get_data_path", lambda: fake_data)
    installer.install()

    legacy = installer.legacy_status()
    assert legacy.present is True
    assert legacy.has_manifest is True
    assert set(legacy.commands) == {"discuss", "plan"}
    assert legacy.missing == ()
    assert legacy.untracked_commands == ()


def test_legacy_status_flags_untracked_commands(fake_home):
    """A pre-manifest install still shadows the plugin, so report it."""
    cmd_dir = fake_home / ".claude" / "commands" / "wh"
    cmd_dir.mkdir(parents=True)
    (cmd_dir / "plan.md").write_text("# stale")

    legacy = installer.legacy_status()
    assert legacy.present is True
    assert legacy.has_manifest is False
    assert legacy.untracked_commands == ("plan",)


def test_legacy_status_reports_missing_manifest_files(fake_home, fake_data, monkeypatch):
    monkeypatch.setattr(installer, "_get_data_path", lambda: fake_data)
    installer.install()
    (fake_home / ".claude" / "commands" / "wh" / "plan.md").unlink()

    legacy = installer.legacy_status()
    assert "commands/wh/plan.md" in legacy.missing


# ---------------------------------------------------------------------------
# install refuses to shadow
# ---------------------------------------------------------------------------


def test_install_refuses_when_plugin_enabled(fake_home, fake_data, monkeypatch):
    monkeypatch.setattr(installer, "_get_data_path", lambda: fake_data)
    _enable_plugin(fake_home)

    with pytest.raises(installer.PluginShadowError) as exc:
        installer.install()

    message = str(exc.value)
    assert "SHADOWS" in message
    assert "wheeler migrate-to-plugin" in message, "message must name the fix"
    assert "wheeler install --force" in message, "message must name the escape hatch"
    assert not (fake_home / ".claude" / "commands" / "wh").exists(), "wrote files anyway"


def test_install_refuses_when_plugin_installed_only(fake_home, fake_data, monkeypatch):
    monkeypatch.setattr(installer, "_get_data_path", lambda: fake_data)
    _install_plugin_record(fake_home)

    with pytest.raises(installer.PluginShadowError):
        installer.install()


def test_install_force_overrides_refusal(fake_home, fake_data, monkeypatch):
    monkeypatch.setattr(installer, "_get_data_path", lambda: fake_data)
    _enable_plugin(fake_home)

    files = installer.install(force=True)

    assert len(files) == 5
    assert (fake_home / ".claude" / "commands" / "wh" / "plan.md").exists()


def test_install_allowed_when_plugin_disabled(fake_home, fake_data, monkeypatch):
    monkeypatch.setattr(installer, "_get_data_path", lambda: fake_data)
    _enable_plugin(fake_home, value=False)

    files = installer.install()
    assert len(files) == 5


def test_shadowing_message_names_colliding_acts(fake_home, fake_data, monkeypatch):
    monkeypatch.setattr(installer, "_get_data_path", lambda: fake_data)
    installer.install()
    _enable_plugin(fake_home)

    message = installer.shadowing_message(
        installer.detect_plugin(), installer.legacy_status()
    )
    assert "/wh:discuss" in message
    assert "2 act names" in message


def test_shadowing_message_leads_with_recognizable_acts(fake_home):
    """Sorted-first would lead with /wh:CLAUDE, which reads like a bug report."""
    cmd_dir = fake_home / ".claude" / "commands" / "wh"
    cmd_dir.mkdir(parents=True)
    for name in ("CLAUDE.md", "add.md", "plan.md", "execute.md"):
        (cmd_dir / name).write_text("# act")

    assert installer._example_acts(installer.legacy_status())[0] == "plan"


def test_cli_install_refuses_and_prints_fix(fake_home, fake_data, monkeypatch):
    monkeypatch.setattr(installer, "_get_data_path", lambda: fake_data)
    _enable_plugin(fake_home)

    result = runner.invoke(topcli.app, ["install"])

    assert result.exit_code == 1
    assert "Refusing to install" in result.stdout
    assert "migrate-to-plugin" in result.stdout


def test_cli_install_force_warns(fake_home, fake_data, monkeypatch):
    monkeypatch.setattr(installer, "_get_data_path", lambda: fake_data)
    _enable_plugin(fake_home)

    result = runner.invoke(topcli.app, ["install", "--force"])

    assert result.exit_code == 0
    assert "shadow" in result.stdout
    assert "migrate-to-plugin" in result.stdout


def test_update_reinstalls_with_force(tmp_path, monkeypatch):
    """update() must not be blocked by the shadowing refusal: a half-applied
    upgrade is worse than a consistent legacy tree."""
    calls: list[list[str]] = []

    def fake_run(cmd, *args, **kwargs):
        calls.append([str(c) for c in cmd])

        class Result:
            returncode = 0

        return Result()

    monkeypatch.setattr(installer.subprocess, "run", fake_run)
    monkeypatch.setattr(installer, "backup_local_mods", lambda: None)
    monkeypatch.setattr(installer, "VERSION_CACHE_PATH", tmp_path / "vc.json")

    installer.update(source="uv")

    wheeler_bin = str(Path(installer.sys.executable).parent / "wheeler")
    assert [wheeler_bin, "install", "--force"] in calls


# ---------------------------------------------------------------------------
# migrate_to_plugin
# ---------------------------------------------------------------------------


def test_migrate_removes_legacy_tree(fake_home, fake_data, monkeypatch):
    monkeypatch.setattr(installer, "_get_data_path", lambda: fake_data)
    installer.install()

    result = installer.migrate_to_plugin()

    assert result.migrated is True
    assert len(result.removed) == 5
    assert not (fake_home / ".claude" / "commands" / "wh").exists()
    assert not (fake_home / ".claude" / "wheeler-manifest.json").exists()
    settings = json.loads((fake_home / ".claude" / "settings.json").read_text())
    assert "statusLine" not in settings
    commands = [
        h["command"]
        for entry in settings["hooks"]["SessionStart"]
        for h in entry.get("hooks", [])
    ]
    assert not any("wheeler-check-update" in c for c in commands)


def test_migrate_removes_untracked_acts(fake_home):
    """Act files with no manifest entry shadow the plugin too."""
    cmd_dir = fake_home / ".claude" / "commands" / "wh"
    cmd_dir.mkdir(parents=True)
    (cmd_dir / "plan.md").write_text("# stale pre-manifest copy")

    result = installer.migrate_to_plugin()

    assert result.migrated is True
    assert result.removed == ()
    assert result.removed_untracked == ("commands/wh/plan.md",)
    assert not cmd_dir.exists()


def test_migrate_keeps_untracked_when_asked(fake_home):
    cmd_dir = fake_home / ".claude" / "commands" / "wh"
    cmd_dir.mkdir(parents=True)
    (cmd_dir / "plan.md").write_text("# stale")

    result = installer.migrate_to_plugin(remove_untracked=False)

    assert result.removed_untracked == ()
    assert (cmd_dir / "plan.md").exists()


def test_migrate_is_safe_with_nothing_installed(fake_home):
    result = installer.migrate_to_plugin()

    assert result.migrated is False
    assert result.removed == ()
    assert result.next_steps == (
        installer.MARKETPLACE_ADD_CMD,
        installer.PLUGIN_INSTALL_CMD,
    )


def test_migrate_is_idempotent(fake_home, fake_data, monkeypatch):
    monkeypatch.setattr(installer, "_get_data_path", lambda: fake_data)
    installer.install()

    first = installer.migrate_to_plugin()
    second = installer.migrate_to_plugin()

    assert first.migrated is True
    assert second.migrated is False
    assert second.removed == ()


def test_migrate_does_not_require_the_plugin(fake_home, fake_data, monkeypatch):
    """Migration must work before the plugin is installed, and say what to run."""
    monkeypatch.setattr(installer, "_get_data_path", lambda: fake_data)
    installer.install()

    result = installer.migrate_to_plugin()

    assert result.plugin.active is False
    assert result.next_steps == (
        installer.MARKETPLACE_ADD_CMD,
        installer.PLUGIN_INSTALL_CMD,
    )


# ---------------------------------------------------------------------------
# wheeler migrate-to-plugin (CLI)
# ---------------------------------------------------------------------------


def test_cli_migrate_lists_then_removes(fake_home, fake_data, monkeypatch):
    monkeypatch.setattr(installer, "_get_data_path", lambda: fake_data)
    installer.install()

    result = runner.invoke(topcli.app, ["migrate-to-plugin", "--yes"])

    assert result.exit_code == 0
    assert "plan.md" in result.stdout
    assert "/plugin marketplace add maxwellsdm1867/wheeler" in result.stdout
    assert "/plugin install wh@wheeler" in result.stdout
    assert not (fake_home / ".claude" / "commands" / "wh").exists()


def test_cli_migrate_dry_run_removes_nothing(fake_home, fake_data, monkeypatch):
    monkeypatch.setattr(installer, "_get_data_path", lambda: fake_data)
    installer.install()

    result = runner.invoke(topcli.app, ["migrate-to-plugin", "--dry-run"])

    assert result.exit_code == 0
    assert "Dry run" in result.stdout
    assert (fake_home / ".claude" / "commands" / "wh" / "plan.md").exists()


def test_cli_migrate_nothing_to_do(fake_home):
    result = runner.invoke(topcli.app, ["migrate-to-plugin"])

    assert result.exit_code == 0
    assert "Nothing to migrate" in result.stdout
    assert "/plugin install wh@wheeler" in result.stdout


def test_cli_migrate_declined_keeps_files(fake_home, fake_data, monkeypatch):
    monkeypatch.setattr(installer, "_get_data_path", lambda: fake_data)
    installer.install()

    result = runner.invoke(topcli.app, ["migrate-to-plugin"], input="n\n")

    assert result.exit_code == 0
    assert "Cancelled" in result.stdout
    assert (fake_home / ".claude" / "commands" / "wh" / "plan.md").exists()


# ---------------------------------------------------------------------------
# wheeler doctor
# ---------------------------------------------------------------------------


def _doctor(monkeypatch, unreachable: bool = True):
    """Run doctor with the Neo4j probe stubbed so it stays offline."""
    if unreachable:
        monkeypatch.setattr(
            topcli, "_probe_neo4j", lambda cfg: (False, False, "connection refused")
        )
    return runner.invoke(topcli.app, ["doctor"])


def test_doctor_reports_shadowing(fake_home, fake_data, monkeypatch):
    monkeypatch.setattr(installer, "_get_data_path", lambda: fake_data)
    installer.install()
    _enable_plugin(fake_home)

    result = _doctor(monkeypatch)

    assert result.exit_code == 0
    plain = " ".join(result.stdout.split())
    assert "shadowing" in plain
    assert "wheeler migrate-to-plugin" in plain


def test_doctor_reports_plugin_only(fake_home, monkeypatch):
    _enable_plugin(fake_home)

    result = _doctor(monkeypatch)

    plain = " ".join(result.stdout.split())
    assert "wh plugin" in plain
    assert "no legacy install" in plain
    assert "shadowing" not in plain


def test_doctor_reports_neither_installed(fake_home, monkeypatch):
    result = _doctor(monkeypatch)

    plain = " ".join(result.stdout.split())
    assert "none installed by either path" in plain


def test_doctor_reports_uri_and_tls(fake_home, monkeypatch):
    from wheeler.config import WheelerConfig

    cfg = WheelerConfig()
    cfg.neo4j.uri = "neo4j+s://abc123.databases.neo4j.io"
    monkeypatch.setattr("wheeler.config.load_config", lambda *a, **k: cfg)
    monkeypatch.setattr(topcli, "_probe_neo4j", lambda c: (True, True, ""))

    result = runner.invoke(topcli.app, ["doctor"])

    plain = " ".join(result.stdout.split())
    assert "neo4j+s://abc123.databases.neo4j.io" in plain
    assert "TLS" in plain
    assert "no TLS" not in plain


def test_doctor_reports_plaintext_bolt(fake_home, monkeypatch):
    from wheeler.config import WheelerConfig

    cfg = WheelerConfig()
    cfg.neo4j.uri = "bolt://localhost:7687"
    monkeypatch.setattr("wheeler.config.load_config", lambda *a, **k: cfg)
    monkeypatch.setattr(topcli, "_probe_neo4j", lambda c: (True, True, ""))

    result = runner.invoke(topcli.app, ["doctor"])

    assert "no TLS" in " ".join(result.stdout.split())


def test_doctor_reports_isolation_tag_mode(fake_home, monkeypatch):
    from wheeler.config import WheelerConfig

    cfg = WheelerConfig()
    cfg.neo4j.project_tag = "retina"
    monkeypatch.setattr("wheeler.config.load_config", lambda *a, **k: cfg)
    monkeypatch.setattr(topcli, "_probe_neo4j", lambda c: (True, True, ""))

    result = runner.invoke(topcli.app, ["doctor"])

    plain = " ".join(result.stdout.split())
    assert "_wheeler_project='retina'" in plain


def test_doctor_reports_isolation_downgrade(fake_home, monkeypatch):
    """A dedicated database that is not usable is the Aura free-tier case:
    ensure_database() silently falls back to tag mode."""
    from wheeler.config import WheelerConfig

    cfg = WheelerConfig()
    cfg.neo4j.database = "retina"
    cfg.project.name = "retina-project"
    monkeypatch.setattr("wheeler.config.load_config", lambda *a, **k: cfg)
    monkeypatch.setattr(
        topcli, "_probe_neo4j", lambda c: (True, False, "database 'retina' not found")
    )

    result = runner.invoke(topcli.app, ["doctor"])

    plain = " ".join(result.stdout.split())
    assert "downgraded" in plain
    assert "retina-project" in plain


# ---------------------------------------------------------------------------
# URI helpers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "uri,tls",
    [
        ("bolt://localhost:7687", False),
        ("neo4j://localhost:7687", False),
        ("bolt+s://host:7687", True),
        ("bolt+ssc://host:7687", True),
        ("neo4j+s://abc.databases.neo4j.io", True),
        ("neo4j+ssc://abc.databases.neo4j.io", True),
        ("NEO4J+S://abc.databases.neo4j.io", True),
        ("garbage", False),
    ],
)
def test_uri_is_tls(uri, tls):
    assert topcli._uri_is_tls(uri) is tls


def test_isolation_model_dedicated_database():
    from wheeler.config import WheelerConfig

    cfg = WheelerConfig()
    cfg.neo4j.database = "retina"
    mode, detail = topcli._isolation_model(cfg, database_ok=True)
    assert mode == "database"
    assert "retina" in detail


def test_isolation_model_no_namespacing():
    from wheeler.config import WheelerConfig

    cfg = WheelerConfig()
    mode, _ = topcli._isolation_model(cfg, database_ok=True)
    assert mode == "none"


def test_isolation_model_tag_from_project_name():
    """ensure_database() sets the tag from project.name at runtime, so doctor
    must report tag mode even before that happens."""
    from wheeler.config import WheelerConfig

    cfg = WheelerConfig()
    cfg.project.name = "retina"
    mode, detail = topcli._isolation_model(cfg, database_ok=True)
    assert mode == "tag"
    assert "retina" in detail


# ---------------------------------------------------------------------------
# wheeler uninstall points at the plugin
# ---------------------------------------------------------------------------


def test_cli_uninstall_points_at_the_plugin(fake_home, fake_data, monkeypatch):
    monkeypatch.setattr(installer, "_get_data_path", lambda: fake_data)
    installer.install()

    result = runner.invoke(topcli.app, ["uninstall"])

    assert result.exit_code == 0
    assert "/plugin install wh@wheeler" in result.stdout


def test_cli_uninstall_quiet_when_plugin_already_serves_acts(
    fake_home, fake_data, monkeypatch
):
    monkeypatch.setattr(installer, "_get_data_path", lambda: fake_data)
    installer.install()
    _enable_plugin(fake_home)

    result = runner.invoke(topcli.app, ["uninstall"])

    assert result.exit_code == 0
    assert "/plugin install" not in result.stdout, "plugin is already installed"


def test_plugin_advice_flags_shadowing(fake_home, fake_data, monkeypatch):
    monkeypatch.setattr(installer, "_get_data_path", lambda: fake_data)
    installer.install()
    _enable_plugin(fake_home)

    advice = installer.plugin_advice(
        installer.detect_plugin(), installer.legacy_status()
    )
    assert advice is not None
    assert "SHADOWS" in advice


def test_plugin_advice_silent_when_consistent(fake_home):
    _enable_plugin(fake_home)

    assert (
        installer.plugin_advice(installer.detect_plugin(), installer.legacy_status())
        is None
    )


# ---------------------------------------------------------------------------
# the invariant: Wheeler never silently leaves both paths active
# ---------------------------------------------------------------------------


def _both_active() -> bool:
    """True when a legacy tree AND an active wh plugin coexist."""
    return installer.legacy_status().present and installer.detect_plugin().active


def test_both_paths_are_never_simultaneously_active(fake_home, fake_data, monkeypatch):
    """Walk the whole state machine: no supported operation leaves the
    shadowing state in place unannounced.

    Wheeler cannot stop a user from running `/plugin install wh@wheeler` on a
    machine that already has the legacy tree, so the invariant is not "this
    state is impossible". It is: Wheeler never CREATES it, and whenever it
    exists Wheeler says so. Both halves are asserted here.
    """
    monkeypatch.setattr(installer, "_get_data_path", lambda: fake_data)

    # 1. plugin first, then a legacy install: refused, nothing written.
    _enable_plugin(fake_home)
    with pytest.raises(installer.PluginShadowError):
        installer.install()
    assert _both_active() is False

    # 2. legacy first, then the plugin appears out from under us (the user ran
    #    /plugin install). Wheeler did not create this, but must report it.
    (fake_home / ".claude" / "settings.json").write_text(json.dumps({}))
    installer.install()
    assert _both_active() is False
    _enable_plugin(fake_home)
    assert _both_active() is True
    doctor = runner.invoke(topcli.app, ["doctor"])
    assert "shadowing" in " ".join(doctor.stdout.split()), "unannounced shadowing"

    # 3. a reinstall on top of that state still refuses.
    with pytest.raises(installer.PluginShadowError):
        installer.install()

    # 4. --force is the only way through, and it announces itself.
    forced = runner.invoke(topcli.app, ["install", "--force"])
    assert forced.exit_code == 0
    assert "shadow" in forced.stdout
    assert _both_active() is True

    # 5. migration resolves it for good, and stays resolved.
    installer.migrate_to_plugin()
    assert _both_active() is False
    installer.migrate_to_plugin()
    assert _both_active() is False


def test_install_never_writes_files_when_it_refuses(fake_home, fake_data, monkeypatch):
    """The refusal is a precondition, not a rollback: no partial tree, no
    manifest, no hook or MCP registration."""
    monkeypatch.setattr(installer, "_get_data_path", lambda: fake_data)
    _enable_plugin(fake_home)

    with pytest.raises(installer.PluginShadowError):
        installer.install()

    claude = fake_home / ".claude"
    assert not (claude / "commands").exists()
    assert not (claude / "agents").exists()
    assert not (claude / "hooks").exists()
    assert not (claude / "wheeler-manifest.json").exists()
    settings = json.loads((claude / "settings.json").read_text())
    assert "mcpServers" not in settings
    assert "hooks" not in settings
    assert "statusLine" not in settings


# ---------------------------------------------------------------------------
# doctor: which layer supplied each Neo4j field
#
# `wheeler.config.keychain_record` is patched rather than `neo4j_sources`, so
# the REAL source-resolution logic runs and the row is tested against it. The
# user's actual OS keychain is never read or written.
# ---------------------------------------------------------------------------


def _no_yaml(monkeypatch):
    """Pretend there is no wheeler.yaml, so `default` is the fallback layer."""
    monkeypatch.setattr("wheeler.config.find_config_file", lambda *a, **k: None)


def _stub_keychain(monkeypatch, record):
    monkeypatch.setattr("wheeler.config.keychain_record", lambda *a, **k: record)


def test_doctor_credential_source_all_defaults(fake_home, monkeypatch):
    """Nothing stored, nothing configured: a value, not a warning."""
    _no_yaml(monkeypatch)
    _stub_keychain(monkeypatch, None)
    for var in ("NEO4J_URI", "NEO4J_USERNAME", "NEO4J_PASSWORD", "NEO4J_DATABASE"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(topcli, "_probe_neo4j", lambda c: (True, True, ""))

    result = runner.invoke(topcli.app, ["doctor"])

    plain = " ".join(result.stdout.split())
    assert "all built-in defaults" in plain
    assert "=default" not in plain, "collapsed, not four field=default pairs"
    assert "shadowed by env" not in plain


def test_doctor_credential_source_from_keychain(fake_home, monkeypatch):
    """A stored credential that is winning is reported per field."""
    _no_yaml(monkeypatch)
    _stub_keychain(
        monkeypatch,
        {
            "uri": "neo4j+s://abc.databases.neo4j.io",
            "username": "neo4j",
            "password": "hunter2",
            "database": "neo4j",
        },
    )
    for var in ("NEO4J_URI", "NEO4J_USERNAME", "NEO4J_PASSWORD", "NEO4J_DATABASE"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(topcli, "_probe_neo4j", lambda c: (True, True, ""))

    result = runner.invoke(topcli.app, ["doctor"])

    plain = " ".join(result.stdout.split())
    assert "uri=keychain" in plain
    assert "password=keychain" in plain
    assert "shadowed by env" not in plain, "nothing is overriding it"
    assert "hunter2" not in result.stdout, "doctor must never print the password"


def test_doctor_credential_source_shadowed_by_env(fake_home, monkeypatch):
    """The support question: `wheeler login` stored fine, and Wheeler still
    connects to localhost because NEO4J_URI is exported."""
    _no_yaml(monkeypatch)
    _stub_keychain(
        monkeypatch,
        {
            "uri": "neo4j+s://abc.databases.neo4j.io",
            "username": "neo4j",
            "password": "hunter2",
            "database": "neo4j",
        },
    )
    monkeypatch.setenv("NEO4J_URI", "bolt://localhost:7687")
    for var in ("NEO4J_USERNAME", "NEO4J_PASSWORD", "NEO4J_DATABASE"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(topcli, "_probe_neo4j", lambda c: (True, True, ""))

    result = runner.invoke(topcli.app, ["doctor"])

    plain = " ".join(result.stdout.split())
    assert "uri=env" in plain, "env won for uri"
    assert "password=keychain" in plain, "and the keychain still won for the rest"
    assert "shadowed by env" in plain
    assert "NEO4J_URI" in plain, "the warning must name the variable to unset"
    assert "hunter2" not in result.stdout


def test_doctor_credential_row_survives_a_broken_keychain(fake_home, monkeypatch):
    """A keyring that raises must not take the whole doctor table down."""
    def boom(*a, **k):
        raise RuntimeError("keyring backend unavailable")

    monkeypatch.setattr("wheeler.config.neo4j_sources", boom)
    monkeypatch.setattr(topcli, "_probe_neo4j", lambda c: (True, True, ""))

    result = runner.invoke(topcli.app, ["doctor"])

    assert result.exit_code == 0
    plain = " ".join(result.stdout.split())
    assert "keyring backend unavailable" in plain
