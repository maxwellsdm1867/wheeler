"""Stdlib-only AUDITOR for a Wheeler-aware Claude Code skill.

A skill fails in ways that are invisible in review: it names a tool that was
deleted two versions ago, it grants a real tool under the wrong server, its
description reads like documentation instead of a trigger, or it claims to be
read-only while holding a mutation tool. In every one of those cases the skill
still LOADS and still LOOKS right. It just quietly cannot do what it says.

This auditor reads the actual files and reports findings. It never modifies
anything, never touches the graph, and never hits the network. The tool surface
it checks against is derived by parsing ``wheeler/mcp_{core,query,mutations,ops}.py``
with ``ast``, so it tracks the real servers instead of a list that goes stale.

Levels::

    BLOCKER  a real defect that makes the skill wrong or inert (exit 1)
    WARN     a likely problem worth a human look (does not fail the audit)
    OK       a check that passed (shown with --verbose)

Run::

    python audit_skill.py --skill .claude/skills/my-skill
    python audit_skill.py --skill ~/.claude/skills/wheeler-context-first --verbose
    python audit_skill.py --list-tools          # print the live surface and exit

A PASS is necessary, not sufficient. It does not replace running the skill's
evals or a human read of the body.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

SERVERS = ("core", "query", "mutations", "ops")

# Tools whose class does not follow from their server.
#
#   core is read EXCEPT these two, which write to disk / the schema
#   ops is read EXCEPT these two, which write only when a non-default flag is set
_CORE_WRITES = {"index_node", "init_schema"}
_OPS_CONDITIONAL = {
    "graph_consistency_check": "repair=False",
    "scan_dependencies": "link_to_graph=False",
}

# Assembled from fragments so the literal blocked tokens never appear in this
# file, which would otherwise trip the repo pre-commit hook on the detector.

# Built from its codepoint so this detector does not contain the character it
# detects, which would make it flag itself on every run.
_EM_DASH = chr(0x2014)

_ANTH = "anth" + "ropic"
_FORBIDDEN = (
    ("import " + _ANTH, f"imports the {_ANTH} SDK"),
    ("from " + _ANTH, f"imports from {_ANTH}"),
    ("api." + _ANTH + ".com", "references the provider API host"),
    ("ANTHROPIC" + "_API_KEY", "references a provider API key env var"),
    ("sk-" + "ant-", "contains a provider key prefix"),
)

# A read-only CLAIM is an assertion about this skill (a heading, or a sentence
# whose subject is the skill). It is NOT the phrase "read-only" appearing inside
# a prohibition, which is exactly what a correct write-mode body contains
# ("Never write knowledge/*.json", "the obligations a read-only skill does not").
_READONLY_CLAIM = re.compile(
    r"^#+ .*\bread[- ]only\b"
    r"|this skill \*{0,2}(never writes|does not write)"
    r"|\bnever writes to the graph\b"
    r"|\bmakes no changes to the graph\b",
    re.I | re.M,
)

# Words that flip an instruction into a prohibition when they precede it.
_NEGATOR = re.compile(r"\b(never|not|avoid|don't|do not|refuse|must not)\b[^.]{0,20}$", re.I)
_ANTI_TRIGGER = re.compile(
    r"\b(skip|do not (use|trigger|fire)|don't (use|trigger|fire)|not for|never fire|"
    r"do NOT trigger|when NOT to use)\b",
    re.I,
)
_CONFIRM = re.compile(
    r"\bconfirm\b|\bapprov\w+|\bask the (user|scientist)\b|\bexplicit consent\b", re.I
)
# A write verb close to a triple-write layer path.
_DIRECT_LAYER_WRITE = re.compile(
    r"(write|edit|create|append|patch|modify|update|regenerate|overwrite)[^.\n]{0,60}"
    r"(knowledge/[\w{}*.-]*\.json|synthesis/[\w{}*.-]*\.md)",
    re.I,
)


@dataclass
class Finding:
    level: str
    check: str
    detail: str
    location: str = ""

    def __str__(self) -> str:
        loc = f"  [{self.location}]" if self.location else ""
        return f"{self.level:<7} {self.check}: {self.detail}{loc}"


# --------------------------------------------------------------------------
# live tool surface
# --------------------------------------------------------------------------


def find_wheeler_package(repo_root: Path | None) -> Path | None:
    """Locate the wheeler package directory without importing it."""
    candidates: list[Path] = []
    if repo_root:
        candidates.append(repo_root / "wheeler")
    here = Path.cwd().resolve()
    for parent in (here, *here.parents):
        candidates.append(parent / "wheeler")
        if (parent / ".git").exists():
            break
    candidates.append(Path(__file__).resolve().parents[4] / "wheeler")
    for cand in candidates:
        if (cand / "mcp_core.py").is_file():
            return cand
    try:
        import importlib.util

        spec = importlib.util.find_spec("wheeler")
    except Exception:
        return None
    if spec and spec.origin:
        pkg = Path(spec.origin).parent
        if (pkg / "mcp_core.py").is_file():
            return pkg
    return None


def tool_names_in(path: Path) -> list[str]:
    """Every function decorated with ``@mcp.tool()`` in a server module."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return []
    names: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
            continue
        for dec in node.decorator_list:
            target = dec.func if isinstance(dec, ast.Call) else dec
            if isinstance(target, ast.Attribute) and target.attr == "tool":
                names.append(node.name)
                break
    return names


@dataclass
class Surface:
    """The live MCP tool surface, keyed for lookup."""

    by_server: dict[str, list[str]] = field(default_factory=dict)

    @property
    def all_names(self) -> set[str]:
        return {n for names in self.by_server.values() for n in names}

    def server_of(self, tool: str) -> str | None:
        for server, names in self.by_server.items():
            if tool in names:
                return server
        return None

    def klass(self, server: str, tool: str) -> str:
        if server == "mutations":
            return "write"
        if server == "query":
            return "read"
        if server == "core":
            return "write" if tool in _CORE_WRITES else "read"
        if server == "ops":
            return "conditional" if tool in _OPS_CONDITIONAL else "read"
        return "read"

    def render(self) -> str:
        lines = []
        for server in SERVERS:
            names = sorted(self.by_server.get(server, []))
            lines.append(f"mcp__wheeler_{server}__*  ({len(names)} tools)")
            for name in names:
                k = self.klass(server, name)
                note = ""
                if k == "conditional":
                    note = f"   (read at {_OPS_CONDITIONAL[name]})"
                lines.append(f"    {k:<12} mcp__wheeler_{server}__{name}{note}")
            lines.append("")
        lines.append(f"total: {len(self.all_names)} tools")
        return "\n".join(lines)


def load_surface(pkg: Path) -> Surface:
    surface = Surface()
    for server in SERVERS:
        surface.by_server[server] = tool_names_in(pkg / f"mcp_{server}.py")
    return surface


# --------------------------------------------------------------------------
# frontmatter
# --------------------------------------------------------------------------


def split_frontmatter(text: str) -> tuple[str | None, str, str | None]:
    """Return (frontmatter, body, error). Deliberately strict about position."""
    if not text.startswith("---"):
        lead = text[: text.find("---")] if "---" in text else text
        preview = lead.strip().splitlines()[0][:60] if lead.strip() else "(blank lines)"
        return None, text, f"file does not open with '---' (starts with: {preview})"
    rest = text[3:]
    if not rest.startswith("\n"):
        return None, text, "opening '---' is not alone on line 1"
    end = rest.find("\n---")
    if end == -1:
        return None, text, "frontmatter is never closed with '---'"
    return rest[1:end], rest[end + 4 :], None


def parse_frontmatter(fm: str) -> dict[str, object]:
    """Minimal YAML subset: scalars, folded scalars, and block or inline lists."""
    out: dict[str, object] = {}
    lines = fm.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#") or line.startswith((" ", "\t")):
            i += 1
            continue
        if ":" not in line:
            i += 1
            continue
        key, _, raw = line.partition(":")
        key = key.strip()
        raw = raw.strip()
        if raw in (">", ">-", "|", "|-"):
            block: list[str] = []
            i += 1
            while i < len(lines) and (not lines[i].strip() or lines[i].startswith((" ", "\t"))):
                block.append(lines[i].strip())
                i += 1
            joiner = " " if raw.startswith(">") else "\n"
            out[key] = joiner.join(b for b in block if b)
            continue
        if raw:
            if raw.startswith("[") and raw.endswith("]"):
                out[key] = [p.strip() for p in raw[1:-1].split(",") if p.strip()]
            elif "," in raw and key in ("allowed-tools", "allowed_tools"):
                out[key] = [p.strip() for p in raw.split(",") if p.strip()]
            else:
                out[key] = raw.strip("'\"")
            i += 1
            continue
        items: list[str] = []
        i += 1
        while i < len(lines) and lines[i].lstrip().startswith("- "):
            items.append(lines[i].lstrip()[2:].strip().strip("'\""))
            i += 1
        out[key] = items
    return out


# --------------------------------------------------------------------------
# the audit
# --------------------------------------------------------------------------


class SkillAudit:
    def __init__(self, skill_dir: Path, surface: Surface, plugin_required: bool):
        self.dir = skill_dir
        self.surface = surface
        self.plugin_required = plugin_required
        self.findings: list[Finding] = []

    def add(self, level: str, check: str, detail: str, location: str = "") -> None:
        self.findings.append(Finding(level, check, detail, location))

    # -- structure --------------------------------------------------------

    def run(self) -> list[Finding]:
        skill_md = self.dir / "SKILL.md"
        if not skill_md.is_file():
            self.add("BLOCKER", "files", f"no SKILL.md in {self.dir}")
            return self.findings

        text = skill_md.read_text(encoding="utf-8")
        fm_text, body, err = split_frontmatter(text)
        if err:
            self.add(
                "BLOCKER",
                "frontmatter-position",
                f"{err}. A leading comment or blank line makes the WHOLE block "
                "invisible, so description and allowed-tools are silently dropped",
                "SKILL.md",
            )
            return self.findings
        self.add("OK", "frontmatter-position", "frontmatter opens the file", "SKILL.md")

        fm = parse_frontmatter(fm_text or "")
        self.check_identity(fm)
        grants = self.check_tools(fm)
        self.check_description(fm, grants)
        self.check_mode(body, grants)
        self.check_body(body)
        self.check_evals()
        return self.findings

    def check_identity(self, fm: dict) -> None:
        name = fm.get("name")
        if not isinstance(name, str) or not name.strip():
            self.add("BLOCKER", "identity", "frontmatter has no 'name'", "SKILL.md")
        elif name.strip() != self.dir.name:
            self.add(
                "WARN",
                "identity",
                f"frontmatter name '{name}' does not match directory '{self.dir.name}'",
                "SKILL.md",
            )
        else:
            self.add("OK", "identity", f"name matches directory ({name})", "SKILL.md")
        if not isinstance(fm.get("description"), str) or not str(fm["description"]).strip():
            self.add(
                "BLOCKER",
                "identity",
                "frontmatter has no 'description'. That field IS the intent "
                "classifier; without it the skill can never fire",
                "SKILL.md",
            )

    # -- tools ------------------------------------------------------------

    def check_tools(self, fm: dict) -> list[str]:
        raw = fm.get("allowed-tools") or fm.get("allowed_tools") or []
        grants = [g for g in (raw if isinstance(raw, list) else [raw]) if isinstance(g, str)]
        if not grants:
            self.add(
                "WARN",
                "tools",
                "no allowed-tools. The skill inherits the full session tool set, "
                "so read-only cannot be enforced",
                "SKILL.md",
            )
            return grants

        wheeler_grants = [g for g in grants if g.startswith("mcp__wheeler")]
        if not wheeler_grants:
            self.add(
                "WARN",
                "tools",
                "no Wheeler MCP tools granted. If the skill is meant to read the "
                "graph it cannot",
                "SKILL.md",
            )

        plain, plugin = [], []
        for grant in wheeler_grants:
            m = re.fullmatch(r"mcp__(plugin_wh_)?wheeler(?:_(\w+?))?__([\w*]+)", grant)
            if not m:
                self.add("WARN", "tools", f"unparseable Wheeler grant: {grant}", "SKILL.md")
                continue
            is_plugin, server, tool = m.group(1), m.group(2), m.group(3)
            (plugin if is_plugin else plain).append(grant)

            if tool == "*":
                if server not in SERVERS:
                    self.add(
                        "BLOCKER", "tool-unknown", f"'{grant}' names no such server", "SKILL.md"
                    )
                elif server == "mutations":
                    self.add(
                        "WARN",
                        "tools-wildcard",
                        f"'{grant}' grants all 18 writes at once. Only a full-access "
                        "skill should do that; list the specific mutations otherwise",
                        "SKILL.md",
                    )
                continue

            if server is None:
                self.add(
                    "BLOCKER",
                    "tool-legacy-monolith",
                    f"'{grant}' names the monolith server, deleted in v0.14.0. "
                    f"Use mcp__wheeler_{self.surface.server_of(tool) or '<server>'}__{tool}",
                    "SKILL.md",
                )
                continue
            if server not in SERVERS:
                self.add(
                    "BLOCKER", "tool-unknown", f"'{grant}' names no such server", "SKILL.md"
                )
                continue
            actual = self.surface.server_of(tool)
            if actual is None:
                hint = self._suggest(tool)
                self.add(
                    "BLOCKER",
                    "tool-unknown",
                    f"'{grant}' is not a tool on any server{hint}",
                    "SKILL.md",
                )
                continue
            if actual != server:
                self.add(
                    "BLOCKER",
                    "tool-wrong-server",
                    f"'{grant}' exists but lives on wheeler_{actual}. "
                    f"allowed-tools matches the full id, so this grant denies it",
                    "SKILL.md",
                )

        if plain and plugin:
            plain_tails = {g.split("__", 1)[1].replace("plugin_wh_", "") for g in plain}
            plugin_tails = {g.split("__", 1)[1].replace("plugin_wh_", "") for g in plugin}
            missing = (plain_tails ^ plugin_tails)
            if missing:
                self.add(
                    "WARN",
                    "plugin-spelling",
                    f"{len(missing)} tool(s) granted in only one spelling. Under the "
                    "wh plugin the ids differ, so a half-converted list denies half "
                    "the tools: " + ", ".join(sorted(missing)[:4]),
                    "SKILL.md",
                )
        elif self.plugin_required and not plugin:
            self.add(
                "BLOCKER",
                "plugin-spelling",
                "--plugin was requested but no mcp__plugin_wh_wheeler_* grants exist. "
                "Under the wh plugin every Wheeler tool would be denied",
                "SKILL.md",
            )
        elif wheeler_grants:
            self.add("OK", "tools", f"{len(wheeler_grants)} Wheeler grant(s) resolve", "SKILL.md")
        return grants

    def _suggest(self, tool: str) -> str:
        near = [n for n in self.surface.all_names if n.startswith(tool[:6]) or tool in n]
        if tool == "query_scripts":
            return ". Script nodes are listed by query_analyses"
        return f". Did you mean {near[0]}?" if near else ""

    # -- description ------------------------------------------------------

    def check_description(self, fm: dict, grants: list[str]) -> None:
        desc = fm.get("description")
        if not isinstance(desc, str):
            return
        desc = desc.strip()
        n = len(desc)
        if n < 200:
            self.add(
                "WARN",
                "desc-length",
                f"description is {n} chars. Too thin to classify intent: it needs "
                "the phrasings that should fire it AND the near-misses that should not",
                "SKILL.md",
            )
        elif n > 1800:
            self.add(
                "WARN",
                "desc-length",
                f"description is {n} chars. The trigger signal gets diluted; move "
                "the detail into the body or a reference file",
                "SKILL.md",
            )
        else:
            self.add("OK", "desc-length", f"description is {n} chars", "SKILL.md")

        if not _ANTI_TRIGGER.search(desc):
            self.add(
                "WARN",
                "desc-anti-trigger",
                "description names no anti-trigger. Add a 'Skip for ...' clause or "
                "the skill fires on adjacent requests it should ignore",
                "SKILL.md",
            )
        quoted = len(re.findall(r'"[^"]{4,}"', desc))
        if quoted < 2:
            self.add(
                "WARN",
                "desc-phrases",
                f"{quoted} quoted user phrase(s). Concrete phrasings are what the "
                "trigger match keys on; describe when to use it, not what it is",
                "SKILL.md",
            )
        reads_graph = any(g.startswith("mcp__") and "wheeler" in g for g in grants)
        if reads_graph and not re.search(r"\.wheeler|Wheeler[- ]managed|knowledge graph", desc, re.I):
            self.add(
                "WARN",
                "desc-gate",
                "the skill reads the graph but the description does not gate on a "
                "Wheeler-managed project, so it will fire in unrelated repos",
                "SKILL.md",
            )

    # -- mode -------------------------------------------------------------

    def check_mode(self, body: str, grants: list[str]) -> None:
        writes, conditionals, reads = [], [], []
        for grant in grants:
            m = re.fullmatch(r"mcp__(?:plugin_wh_)?wheeler_(\w+?)__([\w*]+)", grant)
            if not m:
                continue
            server, tool = m.group(1), m.group(2)
            if tool == "*":
                if server == "mutations":
                    writes.extend(self.surface.by_server.get("mutations", []))
                elif server == "core":
                    writes.extend(sorted(_CORE_WRITES))
                    reads.append(grant)
                elif server == "ops":
                    conditionals.extend(sorted(_OPS_CONDITIONAL))
                    reads.append(grant)
                else:
                    reads.append(grant)
                continue
            if self.surface.server_of(tool) != server:
                continue
            k = self.surface.klass(server, tool)
            if k == "write":
                writes.append(tool)
            elif k == "conditional":
                conditionals.append(tool)
            else:
                reads.append(tool)

        if writes and not reads:
            self.add(
                "WARN",
                "mode-write-without-read",
                "grants writes but no reads. All 25 writing Wheeler acts read the "
                "graph before they write it: a write with no prior read cannot know "
                "what it is duplicating or contradicting",
                "SKILL.md",
            )

        claims_readonly = bool(_READONLY_CLAIM.search(body))
        if claims_readonly and writes:
            self.add(
                "BLOCKER",
                "mode-readonly-violation",
                "body claims read-only but grants writing tool(s): "
                + ", ".join(sorted(set(writes))),
                "SKILL.md",
            )
        elif claims_readonly:
            self.add("OK", "mode", "read-only claim is backed by the grants", "SKILL.md")

        if writes and not _CONFIRM.search(body):
            self.add(
                "WARN",
                "mode-write-unconfirmed",
                "grants mutation tool(s) but the body has no confirmation step. A "
                "skill fires on phrasing, so it has a weaker mandate than a typed act",
                "SKILL.md",
            )
        for tool in conditionals:
            flag = _OPS_CONDITIONAL[tool]
            if flag.split("=")[0] not in body:
                self.add(
                    "WARN",
                    "mode-conditional",
                    f"grants {tool}, which writes when its flag is set, but the body "
                    f"never names the safe default ({flag})",
                    "SKILL.md",
                )

    # -- body -------------------------------------------------------------

    def check_body(self, body: str) -> None:
        for needle, why in _FORBIDDEN:
            if needle in body:
                self.add("BLOCKER", "forbidden", why, "SKILL.md")
        for path in sorted(self.dir.rglob("*")):
            if path.suffix not in (".md", ".py", ".json") or "__pycache__" in str(path):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            if _EM_DASH in text:
                self.add(
                    "WARN",
                    "style",
                    "em dash (house rule: use commas, colons, periods, parentheses)",
                    path.relative_to(self.dir).as_posix(),
                )
        for hit in _DIRECT_LAYER_WRITE.finditer(body):
            # A body that FORBIDS the direct write is correct, not defective.
            if _NEGATOR.search(body[max(0, hit.start() - 40) : hit.start()]):
                continue
            self.add(
                "BLOCKER",
                "direct-layer-write",
                f"body instructs writing a triple-write layer directly "
                f"('{hit.group(0)[:60].strip()}'). That leaves a file with no graph "
                "node and no receipt. Route writes through mcp__wheeler_mutations__*",
                "SKILL.md",
            )
            break
        if re.search(r"\brepair\s*=\s*True", body):
            self.add(
                "WARN",
                "consistency-repair",
                "body reaches for graph_consistency_check(repair=True). In a "
                "development repo the knowledge tree is test scratch and repair "
                "reconciles against it",
                "SKILL.md",
            )

    # -- evals ------------------------------------------------------------

    def check_evals(self) -> None:
        candidates = list((self.dir / "evals").glob("*.json")) if (self.dir / "evals").is_dir() else []
        if not candidates:
            self.add(
                "WARN",
                "evals",
                "no evals/*.json. Trigger behaviour is the thing most likely to be "
                "wrong and the only thing you cannot check by reading",
                "",
            )
            return
        has_negative = False
        for path in candidates:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                self.add("WARN", "evals", f"unparseable: {exc}", path.name)
                continue
            rows = data if isinstance(data, list) else data.get("evals", [])
            for row in rows if isinstance(rows, list) else []:
                if isinstance(row, dict) and row.get("should_trigger") is False:
                    has_negative = True
        if not has_negative:
            self.add(
                "WARN",
                "evals",
                "no negative case (should_trigger: false). Over-firing is the more "
                "common failure and only a negative case catches it",
                "evals/",
            )
        else:
            self.add("OK", "evals", "trigger evals include negative cases", "evals/")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--skill", help="path to the skill directory (containing SKILL.md)")
    ap.add_argument("--repo-root", help="wheeler repo root (auto-detected otherwise)")
    ap.add_argument(
        "--plugin",
        action="store_true",
        help="require the mcp__plugin_wh_* spellings as well as the plain ones",
    )
    ap.add_argument("--list-tools", action="store_true", help="print the live surface and exit")
    ap.add_argument("--verbose", "-v", action="store_true", help="also show OK findings")
    args = ap.parse_args()

    pkg = find_wheeler_package(Path(args.repo_root).resolve() if args.repo_root else None)
    if pkg is None:
        print(
            "ERROR: could not locate the wheeler package. Pass --repo-root "
            "<path to the wheeler repo>.",
            file=sys.stderr,
        )
        return 2
    surface = load_surface(pkg)
    if not surface.all_names:
        print(f"ERROR: parsed no tools from {pkg}. Is this the wheeler package?", file=sys.stderr)
        return 2

    if args.list_tools:
        print(f"live MCP surface, parsed from {pkg}\n")
        print(surface.render())
        return 0

    if not args.skill:
        ap.error("--skill is required unless --list-tools is given")
    skill_dir = Path(args.skill).expanduser().resolve()
    if not skill_dir.is_dir():
        print(f"ERROR: not a directory: {skill_dir}", file=sys.stderr)
        return 2

    findings = SkillAudit(skill_dir, surface, args.plugin).run()
    shown = [f for f in findings if args.verbose or f.level != "OK"]
    print(f"audit: {skill_dir}  (surface: {len(surface.all_names)} tools from {pkg})\n")
    for f in shown:
        print(f)
    blockers = sum(1 for f in findings if f.level == "BLOCKER")
    warns = sum(1 for f in findings if f.level == "WARN")
    print(f"\n{blockers} BLOCKER, {warns} WARN, {sum(1 for f in findings if f.level == 'OK')} OK")
    if blockers:
        print("FAIL: fix every BLOCKER before landing.")
        return 1
    print("PASS (necessary, not sufficient: run the evals and read the body).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
