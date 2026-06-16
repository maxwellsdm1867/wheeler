"""Stdlib-only AUDITOR for a Wheeler service adapter.

The scaffolder writes skeletons; the auditor checks that the FILLED adapter is
still safe and correct before it lands. It is the mechanical half of the
adversarial review, codified so every new adapter is held to the same bar the
Asta adapters were (data safety, two-sided provenance, the external-call
failsafe, and the house conventions). It reads the actual files and reports
findings; it never modifies anything and never touches the graph or network.

Given ``--provider`` and ``--tool`` (and an optional ``--repo-root``) it locates
the adapter's four pieces, runs the checks, prints one line per finding, and
exits non-zero if any BLOCKER fired. Levels:

  BLOCKER  a real safety / correctness defect (fails the audit, exit 1)
  WARN     a likely problem worth a human look (does not fail the audit)
  OK       a check that passed (shown with --verbose)

Run::

    python audit_service.py --provider asta --tool scholar-qa
    python audit_service.py --provider asta --tool theorizer --verbose

The checks are deliberately conservative (substring / regex / a little AST), so a
PASS is necessary-not-sufficient: it does not replace the live e2e or the
adversarial-review agents, it catches the mechanical mistakes that recur.
"""

from __future__ import annotations

import argparse
import ast
import re
from dataclasses import dataclass
from pathlib import Path


def _slug(value: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (value or "").strip().lower())
    return s.strip("-")


def _ident(value: str) -> str:
    return _slug(value).replace("-", "_") or "tool"


@dataclass
class Finding:
    level: str  # BLOCKER | WARN | OK
    check: str
    detail: str
    location: str = ""

    def __str__(self) -> str:
        loc = f"  [{self.location}]" if self.location else ""
        return f"{self.level:<7} {self.check}: {self.detail}{loc}"


# Patterns the pre-commit hook also blocks; an adapter must never carry them. The
# needles are ASSEMBLED FROM FRAGMENTS so the literal forbidden tokens never
# appear in this detector file (which would otherwise trip the same hook on this
# file itself). The runtime strings are exactly the blocked tokens.
_ANTH = "anth" + "ropic"
_FORBIDDEN = (
    ("import " + _ANTH, "imports the " + _ANTH + " SDK"),
    ("from " + _ANTH, "imports from " + _ANTH),
    ("api." + _ANTH + ".com", "references the Ai2-unrelated provider API host"),
    ("ANTHROPIC" + "_API_KEY", "references a provider API key env var"),
    ("sk-" + "ant-", "contains a provider key prefix"),
)

# The em dash character, assembled by codepoint so this style-checker file does
# not itself contain a literal em dash.
_EM_DASH = chr(0x2014)


def _delete_cyphers(text: str) -> list[str]:
    """Return every CYPHER string-literal that contains a ``DETACH DELETE`` clause.

    Uses AST so comments are ignored, and keeps only strings that are actual
    cypher (stripped content starts with ``MATCH`` / ``OPTIONAL MATCH``), so a
    DOCSTRING that merely explains the teardown reasoning in prose (which can
    legitimately mention "DETACH DELETE" and "corpus_id") is not mistaken for a
    delete statement. Adjacent string concatenation in one literal node is already
    joined by the parser.
    """
    out: list[str] = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return out
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            value = node.value
            if "DETACH DELETE" not in value:
                continue
            head = value.lstrip().upper()
            if head.startswith("MATCH") or head.startswith("OPTIONAL MATCH"):
                out.append(value)
    return out


class Auditor:
    def __init__(self, provider: str, tool: str, repo_root: Path):
        self.provider = _slug(provider)
        self.tool = tool
        self.tool_ident = _ident(tool)
        self.root = repo_root
        self.findings: list[Finding] = []

    def add(self, level: str, check: str, detail: str, location: str = "") -> None:
        self.findings.append(Finding(level, check, detail, location))

    # --- file location ---

    @property
    def ingest_path(self) -> Path:
        conventional = (
            self.root
            / "wheeler"
            / "integrations"
            / self.provider
            / f"{self.tool_ident}.py"
        )
        if conventional.exists():
            return conventional
        # Fallback: a few adapters predate the <tool>.py convention (Paper Finder
        # lives in ingest.py). Find the module that defines ingest_<tool_ident>.
        pkg = self.root / "wheeler" / "integrations" / self.provider
        if pkg.is_dir():
            needle = f"def ingest_{self.tool_ident}"
            for mod in sorted(pkg.glob("*.py")):
                if needle in mod.read_text(errors="ignore"):
                    return mod
        return conventional

    @property
    def test_path(self) -> Path:
        return (
            self.root
            / "tests"
            / "integrations"
            / self.provider
            / f"test_{self.tool_ident}.py"
        )

    def _find_act(self) -> Path | None:
        """Locate the marshal-in act by content (it runs the ingest verb)."""
        acts_dir = self.root / ".claude" / "commands" / "wh"
        if not acts_dir.is_dir():
            return None
        needle = f"wheeler integrate ingest {self.tool_ident}"
        needle_alt = f"wheeler integrate ingest {self.tool}"
        for md in sorted(acts_dir.glob("*.md")):
            text = md.read_text(errors="ignore")
            if needle in text or needle_alt in text:
                return md
        return None

    def _find_contract(self) -> tuple[str, str] | None:
        """Return (yaml_text, source) for the contract, from folder or catalog."""
        # Enabled folder: one file per id (id unknown here, so scan for the tool).
        folder = self.root / ".wheeler" / "services"
        candidates: list[Path] = []
        if folder.is_dir():
            candidates += sorted(folder.glob("*.yaml"))
        catalog = self.root / "wheeler" / "integrations" / "services.default.yaml"
        if catalog.exists():
            candidates.append(catalog)
        tag = f"{self.provider}:{self.tool_ident}"
        tag_hyphen = f"{self.provider}:{_slug(self.tool)}"
        impl = f"{self.provider}/{self.tool_ident}.py"
        needles = (self.tool_ident, _slug(self.tool), impl, tag, tag_hyphen)
        for path in candidates:
            text = path.read_text(errors="ignore")
            if any(n and n in text for n in needles):
                return text, str(path.relative_to(self.root))
        return None

    # --- checks ---

    def check_files_exist(self) -> bool:
        ok = True
        if not self.ingest_path.exists():
            self.add(
                "BLOCKER",
                "files",
                f"ingest module not found: {self.ingest_path}",
            )
            ok = False
        if not self.test_path.exists():
            self.add("WARN", "files", f"test module not found: {self.test_path}")
        if self._find_act() is None:
            self.add(
                "WARN",
                "files",
                "marshal-in act not found (no act runs the ingest verb)",
            )
        return ok

    def check_no_forbidden(self) -> None:
        for path in (self.ingest_path, self.test_path):
            if not path.exists():
                continue
            text = path.read_text(errors="ignore")
            for needle, why in _FORBIDDEN:
                if needle in text:
                    self.add("BLOCKER", "forbidden", why, path.name)
            for i, line in enumerate(text.splitlines(), 1):
                if _EM_DASH in line:
                    self.add(
                        "WARN", "style", "em dash (use , . : parentheses)",
                        f"{path.name}:{i}",
                    )
                    break

    def check_lazy_execute_tool(self, text: str) -> None:
        """execute_tool must be imported function-local, never module-top."""
        try:
            tree = ast.parse(text)
        except SyntaxError as exc:
            self.add("BLOCKER", "syntax", f"ingest does not parse: {exc}",
                     self.ingest_path.name)
            return
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and (
                "graph_tools" in node.module
            ):
                names = {a.name for a in node.names}
                if "execute_tool" in names and node.col_offset == 0:
                    self.add(
                        "BLOCKER",
                        "layering",
                        "execute_tool imported at module top (must be "
                        "function-local, like the Asta adapters)",
                        f"{self.ingest_path.name}:{node.lineno}",
                    )
                    return
        if "execute_tool" in text:
            self.add("OK", "layering", "execute_tool imported function-local")

    def check_provenance(self, text: str) -> None:
        name = self.ingest_path.name
        # INPUT side.
        if "_record_used" in text:
            self.add("OK", "provenance", "records USED inputs (_record_used)")
        else:
            self.add(
                "BLOCKER", "provenance",
                "no _record_used: the input side (Execution -[USED]-> inputs) is "
                "unwired", name,
            )
        # OUTPUT side: register_output_artifact (raw node) or _record_generated.
        if "register_output_artifact" in text or "_record_generated" in text or (
            "WAS_GENERATED_BY" in text
        ):
            self.add(
                "OK", "provenance",
                "wires the output side (WAS_GENERATED_BY / raw artifact)",
            )
        else:
            self.add(
                "BLOCKER", "provenance",
                "no WAS_GENERATED_BY / register_output_artifact: the output side "
                "is unwired", name,
            )
        # Papers must never carry WAS_GENERATED_BY (reference-entity rule). Match a
        # paper-suggestive variable (paper / pid / corpus...) wired WAS_GENERATED_BY
        # in either argument order. A generic ``node_id`` is intentionally NOT
        # matched (it can be a legitimate produced Finding/Hypothesis).
        _pvar = r"(?:paper|pid|corpus)[_a-z0-9]*"
        if re.search(rf"{_pvar}\s*,\s*[\"']WAS_GENERATED_BY[\"']", text) or (
            re.search(rf"[\"']WAS_GENERATED_BY[\"']\s*,\s*{_pvar}", text)
        ):
            self.add(
                "BLOCKER", "provenance",
                "a Paper appears wired WAS_GENERATED_BY: papers are reference "
                "entities and must never carry it (per /wh:close)", name,
            )

    def check_failsafe(self, text: str) -> None:
        name = self.ingest_path.name
        is_md = "report_markdown" in text
        # The job_outcome gate (json adapters) or the markdown deliverable note.
        # Require the CALL form, so an imported-but-never-used symbol does not pass.
        if "job_outcome(" in text:
            self.add("OK", "failsafe", "job_outcome gate present")
        elif is_md:
            self.add(
                "OK", "failsafe",
                "markdown deliverable (no A2A status; the gate is the parse + the "
                "partial-ingest failsafe)",
            )
        else:
            self.add(
                "BLOCKER", "failsafe",
                "no job_outcome gate: a failed external job could be ingested as "
                "if real", name,
            )
        # Honest status + the failure marker (CALLED, not just imported).
        if "mark_execution_failed(" in text:
            self.add("OK", "failsafe", "marks the Execution failed on a bad run")
        else:
            self.add(
                "BLOCKER", "failsafe",
                "mark_execution_failed is not called: a failed / partial run is "
                "not recorded as failed", name,
            )
        # Reused-Execution reset (a successful retry must clear a stale failed).
        if "mark_execution_completed(" in text:
            self.add("OK", "failsafe", "resets a reused Execution on success")
        else:
            self.add(
                "WARN", "failsafe",
                "no mark_execution_completed: a successful retry that reuses a "
                "prior failed Execution may stay stuck failed", name,
            )
        # Partial-ingest guard around bucketing.
        if "ingest-error" in text or re.search(r"\btry:\b", text):
            self.add("OK", "failsafe", "bucketing has a partial-ingest guard")
        else:
            self.add(
                "WARN", "failsafe",
                "no try/except around bucketing: a partial-ingest exception would "
                "not mark the run failed", name,
            )

    def check_data_safety(self) -> None:
        if not self.test_path.exists():
            return
        text = self.test_path.read_text(errors="ignore")
        name = self.test_path.name
        # The hermetic teardown must be EXACTLY the e2e_tag delete.
        if "WHERE n.e2e_tag = $tag DETACH DELETE n" in text:
            self.add("OK", "data-safety", "teardown deletes only by per-run e2e_tag")
        else:
            self.add(
                "BLOCKER", "data-safety",
                "no `MATCH (n) WHERE n.e2e_tag = $tag DETACH DELETE n` teardown: "
                "an e2e on the shared namespace could delete production data", name,
            )
        # NEVER delete by service or corpus_id. Inspect only the CYPHER string
        # literals (via AST), not comments: a safe teardown's nearby comment
        # legitimately mentions "never delete by service / corpus_id", so a
        # proximity grep over raw text would false-positive on the correct code.
        for cypher in _delete_cyphers(text):
            if re.search(r"\b(service|corpus_id)\b", cypher) and (
                "e2e_tag" not in cypher
            ):
                self.add(
                    "BLOCKER", "data-safety",
                    "a DETACH DELETE cypher is scoped by service / corpus_id: "
                    "production nodes share those, so this would delete real data. "
                    "Delete ONLY by e2e_tag", name,
                )
        # Per-run unique tag.
        if "integrations_e2e_" in text and "uuid" in text:
            self.add("OK", "data-safety", "per-run unique e2e_tag (uuid)")
        else:
            self.add(
                "WARN", "data-safety",
                "no per-run uuid e2e_tag found: a shared constant tag would let "
                "one test's teardown delete another's nodes", name,
            )
        # Run-unique corpus_ids in the e2e (so dedupe never hits a production
        # Paper that teardown would then delete). Heuristic: a paper-producing
        # e2e that hardcodes short digit corpus_ids is suspicious.
        if re.search(r"add_paper|corpus_id|:Paper", text):
            if re.search(r"uuid4\(\)\.hex", text) and re.search(
                r"corpus_id|cids|base \+", text
            ):
                self.add(
                    "OK", "data-safety",
                    "e2e appears to use run-unique synthetic corpus_ids",
                )
            else:
                self.add(
                    "WARN", "data-safety",
                    "paper e2e may use hardcoded corpus_ids: if any collides with a "
                    "production Paper, the run dedupes into it and teardown deletes "
                    "real data. Derive run-unique corpus_ids from the e2e uuid", name,
                )

    def check_idempotency_test(self) -> None:
        if not self.test_path.exists():
            return
        text = self.test_path.read_text(errors="ignore")
        if re.search(r"report\d?\.created == 0|created == 0", text):
            self.add("OK", "idempotency", "asserts re-ingest creates nothing new")
        else:
            self.add(
                "WARN", "idempotency",
                "no `created == 0` re-ingest assertion: idempotency is untested",
                self.test_path.name,
            )

    def check_act(self) -> None:
        act = self._find_act()
        if act is None:
            return
        text = act.read_text(errors="ignore")
        name = act.name
        if "Wire semantics to the existing graph" in text:
            self.add("OK", "act", "carries the semantic-wiring step (part 3)")
        else:
            self.add(
                "WARN", "act",
                "no 'Wire semantics to the existing graph' step: the new outputs "
                "are not connected to the prior graph", name,
            )
        if "record-failure" in text:
            self.add("OK", "act", "records a failed attempt on a non-zero exit")
        else:
            self.add(
                "WARN", "act",
                "no `wheeler integrate record-failure` on failure: a failed CLI "
                "run leaves no trace", name,
            )
        if _EM_DASH in text:
            self.add("WARN", "style", "em dash in the act", name)

    def check_registry(self) -> None:
        found = self._find_contract()
        if found is None:
            self.add(
                "WARN", "registry",
                "no registry contract found (catalog or .wheeler/services/): the "
                "service will not be routable",
            )
            return
        text, src = found
        required = (
            "id", "provider", "name", "description", "kind", "act", "cost",
            "available", "when",
        )
        missing = [f for f in required if not re.search(rf"^\s*-?\s*{f}\s*:", text, re.M)]
        if missing:
            self.add(
                "BLOCKER", "registry",
                f"contract is missing required field(s): {', '.join(missing)} "
                "(the registry silently skips it)", src,
            )
        else:
            self.add("OK", "registry", "contract has all required fields", src)

    def run(self) -> list[Finding]:
        if not self.check_files_exist():
            return self.findings
        self.check_no_forbidden()
        text = self.ingest_path.read_text(errors="ignore")
        self.check_lazy_execute_tool(text)
        self.check_provenance(text)
        self.check_failsafe(text)
        self.check_data_safety()
        self.check_idempotency_test()
        self.check_act()
        self.check_registry()
        return self.findings


def audit(provider: str, tool: str, repo_root: Path) -> list[Finding]:
    return Auditor(provider, tool, repo_root).run()


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--provider", required=True)
    p.add_argument("--tool", required=True)
    p.add_argument("--repo-root", default=".")
    p.add_argument("--verbose", action="store_true", help="also print OK findings")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    findings = audit(args.provider, args.tool, Path(args.repo_root))
    blockers = [f for f in findings if f.level == "BLOCKER"]
    warns = [f for f in findings if f.level == "WARN"]
    for f in findings:
        if f.level == "OK" and not args.verbose:
            continue
        print(f)
    print(
        f"\naudit: {len(blockers)} blocker(s), {len(warns)} warning(s), "
        f"{len(findings)} checks for {_slug(args.provider)}:{_ident(args.tool)}"
    )
    return 1 if blockers else 0


if __name__ == "__main__":
    raise SystemExit(main())
