"""Find and drive the local Neo4j instances a user already has.

Neo4j Desktop allows exactly ONE running local instance through its UI. The
server has no such limit: give each instance its own ports and several run side
by side, which is what lets one project per window each hold its own graph.

Getting there needs the `bin/neo4j` script, and the reason people conclude they
"do not have the CLI" is that it is unfindable rather than absent. Every Desktop
instance ships one, under a directory named by an opaque uuid, and it needs a
JRE that Desktop bundles somewhere else again and never puts on PATH. This module
does that lookup so a user never types either path.

Read-only except for `start`/`stop`, which shell out to the instance's own
script rather than reimplementing anything.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
import os
from pathlib import Path
import re
import subprocess

logger = logging.getLogger(__name__)

# Desktop 2 on macOS. Desktop 1 used a different tree, and Linux/Windows differ
# again; each is tried in turn and a miss simply yields no instances.
_DESKTOP_ROOTS = (
    "Library/Application Support/neo4j-desktop/Application/Data/dbmss",
    "Library/Application Support/Neo4j Desktop/Application/relate-data/dbmss",
    ".config/Neo4j Desktop/Application/relate-data/dbmss",
    "AppData/Roaming/Neo4j Desktop/Application/relate-data/dbmss",
)

# Every port an Enterprise instance binds, measured rather than assumed. A
# standalone server with no cluster configured still binds routing, backup,
# cluster, raft and discovery, so moving only `bolt` produces a second instance
# that dies on a port the user never configured and cannot find in their conf.
PORT_SETTINGS = (
    ("bolt", "server.bolt.listen_address", 7687),
    ("http", "server.http.listen_address", 7474),
    ("routing", "server.routing.listen_address", 7688),
    ("backup", "server.backup.listen_address", 6362),
    ("cluster", "server.cluster.listen_address", 6000),
    ("raft", "server.cluster.raft.listen_address", 7000),
    ("discovery", "server.discovery.listen_address", 5000),
)


@dataclass
class Instance:
    """One Neo4j Desktop DBMS, its databases, and the ports it will bind."""

    path: Path
    ports: dict[str, int] = field(default_factory=dict)
    databases: list[str] = field(default_factory=list)

    @property
    def id(self) -> str:
        return self.path.name

    @property
    def short_id(self) -> str:
        """`dbms-90e5c13c-…` -> `90e5c13c`, which is what a human can hold."""
        stem = self.id.removeprefix("dbms-")
        return stem.split("-", 1)[0] or stem

    @property
    def bolt_uri(self) -> str:
        return f"bolt://localhost:{self.ports.get('bolt', 7687)}"

    @property
    def script(self) -> Path:
        return self.path / "bin" / "neo4j"


def desktop_root() -> Path | None:
    """The directory holding Desktop's DBMS instances, or None."""
    home = Path.home()
    for candidate in _DESKTOP_ROOTS:
        path = home / candidate
        if path.is_dir():
            return path
    return None


def java_home() -> str | None:
    """The JRE Desktop bundles. Never on PATH, and `bin/neo4j` refuses without it."""
    root = desktop_root()
    if root is None:
        return None
    # .../Application/Data/dbmss -> .../Application/Cache/runtime/<jre>/…/Home
    cache = root.parent.parent / "Cache" / "runtime"
    if not cache.is_dir():
        return None
    for java in sorted(cache.glob("*/*/Contents/Home/bin/java")):
        return str(java.parent.parent)
    # Some layouts drop the extra level.
    for java in sorted(cache.glob("*/Contents/Home/bin/java")):
        return str(java.parent.parent)
    return None


def _parse_ports(conf: Path) -> dict[str, int]:
    """Ports this instance will bind: explicit settings, else the documented default."""
    text = conf.read_text() if conf.exists() else ""
    ports: dict[str, int] = {}
    for name, setting, default in PORT_SETTINGS:
        match = re.search(rf"^{re.escape(setting)}\s*=\s*\S*?:(\d+)\s*$", text, re.M)
        ports[name] = int(match.group(1)) if match else default
    return ports


def instances() -> list[Instance]:
    """Every Desktop instance on this machine, sorted by id."""
    root = desktop_root()
    if root is None:
        return []
    found: list[Instance] = []
    for path in sorted(root.glob("dbms-*")):
        if not path.is_dir():
            continue
        databases = []
        data = path / "data" / "databases"
        if data.is_dir():
            databases = sorted(
                p.name for p in data.iterdir() if p.is_dir() and p.name != "system"
            )
        found.append(
            Instance(
                path=path,
                ports=_parse_ports(path / "conf" / "neo4j.conf"),
                databases=databases,
            )
        )
    return found


def find(name: str) -> Instance | None:
    """Resolve an instance by id, short id, or a DATABASE it holds.

    Accepting a database name is the point: `wheeler db start wheelermasked`
    is memorable in a way that `dbms-90e5c13c-95b9-45e4-bf36-fbe708de15b1`
    never will be.
    """
    wanted = name.strip()
    found = instances()
    for inst in found:
        if wanted in (inst.id, inst.short_id):
            return inst
    matches = [i for i in found if wanted in i.databases]
    return matches[0] if len(matches) == 1 else None


def port_conflicts(found: list[Instance] | None = None) -> list[tuple[str, int, list[str]]]:
    """Ports claimed by more than one instance, so they cannot run together.

    Reported per port rather than per instance: the useful sentence is "three
    instances all want 7687", not "this instance conflicts".
    """
    found = found if found is not None else instances()
    conflicts = []
    for name, _setting, _default in PORT_SETTINGS:
        claims: dict[int, list[str]] = {}
        for inst in found:
            claims.setdefault(inst.ports.get(name, 0), []).append(inst.short_id)
        for port, owners in claims.items():
            if len(owners) > 1:
                conflicts.append((name, port, owners))
    return conflicts


def _run(inst: Instance, verb: str, timeout: float = 180.0) -> tuple[int, str]:
    """Run `bin/neo4j <verb>` with the bundled JRE. Returns (returncode, output)."""
    home = java_home()
    if home is None:
        return 1, (
            "Could not find the JRE that Neo4j Desktop bundles, so `bin/neo4j` "
            "cannot start. Start the instance once from the Desktop UI, or set "
            "JAVA_HOME to a Java 21 runtime."
        )
    if not inst.script.exists():
        return 1, f"No neo4j script at {inst.script}"
    try:
        result = subprocess.run(
            [str(inst.script), verb],
            env={**os.environ, "JAVA_HOME": home},
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return 1, f"`neo4j {verb}` did not finish within {timeout:.0f}s"
    return result.returncode, (result.stdout + result.stderr).strip()


def status(inst: Instance) -> bool:
    """Whether this instance reports itself running."""
    code, out = _run(inst, "status", timeout=60.0)
    return code == 0 and "is running" in out.lower()


def start(inst: Instance) -> tuple[bool, str]:
    code, out = _run(inst, "start")
    return code == 0, out


def stop(inst: Instance) -> tuple[bool, str]:
    code, out = _run(inst, "stop")
    return code == 0, out


def assign_ports(
    found: list[Instance] | None = None, *, stride: int = 10
) -> list[tuple[Instance, dict[str, int]]]:
    """Plan a non-colliding port set per instance. Pure: writes nothing.

    The FIRST instance keeps the stock ports, so anything already pointed at
    7687 keeps working and only the surplus instances move. A stride of 10 keeps
    each instance's seven ports in one contiguous band, which makes a stray
    `lsof` line attributable at a glance.

    Returns [(instance, {port_name: port})] for every instance, changed or not;
    callers diff against `instance.ports` to see what actually moves.
    """
    found = found if found is not None else instances()
    plan: list[tuple[Instance, dict[str, int]]] = []
    for index, inst in enumerate(found):
        plan.append(
            (inst, {name: base + index * stride for name, _s, base in PORT_SETTINGS})
        )
    return plan


def _rewrite_conf(conf: Path, wanted: dict[str, int]) -> list[str]:
    """Set every port in *wanted*, returning the human-readable changes."""
    setting_for = {name: setting for name, setting, _d in PORT_SETTINGS}
    lines = conf.read_text().splitlines()
    changes: list[str] = []

    for name, port in wanted.items():
        setting = setting_for[name]
        # Backup binds on all interfaces by default; the rest are loopback-form.
        value = f"0.0.0.0:{port}" if name == "backup" else f":{port}"
        target = f"{setting}={value}"
        active = re.compile(rf"^{re.escape(setting)}\s*=.*$")
        commented = re.compile(rf"^#\s*{re.escape(setting)}\s*=.*$")

        for i, line in enumerate(lines):
            if active.match(line):
                if line.strip() != target:
                    changes.append(f"{setting}: {line.split('=', 1)[1]} -> {value}")
                    lines[i] = target
                break
        else:
            # Uncomment in place so the setting stays beside its explanation.
            for i, line in enumerate(lines):
                if commented.match(line):
                    changes.append(f"{setting}: (default) -> {value}")
                    lines[i] = target
                    break
            else:
                changes.append(f"{setting}: (added) -> {value}")
                lines.append(target)

    if changes:
        conf.write_text("\n".join(lines) + "\n")
    return changes


def apply_ports(
    plan: list[tuple[Instance, dict[str, int]]],
) -> list[tuple[Instance, list[str]]]:
    """Write a plan from `assign_ports`. Backs each conf up once, then rewrites.

    Idempotent: re-running produces no changes, because `_rewrite_conf` compares
    before writing.
    """
    results = []
    for inst, wanted in plan:
        conf = inst.path / "conf" / "neo4j.conf"
        if not conf.exists():
            results.append((inst, [f"!! no neo4j.conf at {conf}"]))
            continue
        backup = conf.with_suffix(".conf.wheeler-bak")
        if not backup.exists():
            backup.write_text(conf.read_text())
        results.append((inst, _rewrite_conf(conf, wanted)))
    return results


def stale_bindings(plan: list[tuple[Instance, dict[str, int]]]) -> list[str]:
    """Stored credentials whose URI names a bolt port no instance will serve.

    The regression this exists for: moving an instance's ports silently breaks
    every project pointed at the old one, and the breakage surfaces later as an
    unreachable graph rather than as anything connected to the port change.
    Checked against the keychain because that is where project connections now
    live; a project pinning a bare `uri:` in its own wheeler.yaml is reported by
    `wheeler db instances` instead, since there is no registry of those.
    """
    from wheeler import credentials

    serving = {ports["bolt"] for _inst, ports in plan}
    stale: list[str] = []
    for name in credentials.list_profiles():
        record = credentials.load(name) or {}
        uri = record.get("uri", "")
        match = re.search(r":(\d+)\s*$", uri)
        if not match or "localhost" not in uri and "127.0.0.1" not in uri:
            continue  # remote or portless: not ours to worry about
        if int(match.group(1)) not in serving:
            stale.append(f"{name} -> {uri}")
    return stale


def _local_port(uri: str) -> int | None:
    """The bolt port of a LOCAL uri, or None when it is remote or unparseable."""
    if not uri or not re.search(r"//(localhost|127\.0\.0\.1|\[::1\])(:|$)", uri):
        return None
    match = re.search(r":(\d+)\s*/?$", uri)
    return int(match.group(1)) if match else 7687


def explain_target(uri: str, database: str = "") -> list[str]:
    """Why a local graph is unreachable, as steps rather than symptoms.

    The generic advice ("open Neo4j Desktop and press Start") stopped being true
    the moment several instances existed: Desktop starts ONE, and it is very
    likely not the one this project needs. This resolves the project's port to an
    actual instance and names the command for THAT one.

    Returns [] for a remote target, where none of this applies.
    """
    port = _local_port(uri)
    if port is None:
        return []

    found = instances()
    if not found:
        return [
            f"Nothing is listening on port {port} and no Neo4j Desktop instances "
            "were found on this machine.",
            "Install Neo4j Desktop, or point this project at another graph "
            "(wheeler init --graph cloud).",
        ]

    serving = [i for i in found if i.ports.get("bolt") == port]
    if not serving:
        offered = ", ".join(f"{i.short_id}:{i.ports['bolt']}" for i in found)
        return [
            f"No local instance is configured to serve port {port}.",
            f"Instances on this machine: {offered}.",
            "Repoint this project with `wheeler db use <database>`, or give the "
            "instances distinct ports with `wheeler db assign-ports`.",
        ]

    inst = serving[0]
    lines: list[str] = []
    if not status(inst):
        lines.append(
            f"Instance {inst.short_id} serves port {port} but is NOT running."
        )
        lines.append(f"Start it with:  wheeler db start {inst.short_id}")
    else:
        lines.append(f"Instance {inst.short_id} is running on port {port}.")

    if database and inst.databases and database not in inst.databases:
        lines.append(
            f"It has no database {database!r} (it has: "
            f"{', '.join(inst.databases)})."
        )
        lines.append(f"Create it with:  wheeler db create {database}")
    return lines
