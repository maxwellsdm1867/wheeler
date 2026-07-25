"""Regression test for issue #88: llmsr CLI vanished when scipy was absent.

`wheeler llmsr --help` reported `No such command 'llmsr'` on a build where the
engine WAS shipped. Chain:

    wheeler/tools/cli.py         guarded `from ...llmsr.cli import llmsr_app`
      -> llmsr/cli.py            `from .vendor import buffer as buffer_mod`
        -> vendor/buffer.py:28   `import scipy`   <-- ModuleNotFoundError
    caught by `except ImportError: pass`  ->  the group never registered

scipy is the optional `[llmsr]` extra, not a hard dependency, and buffer.py used
it for exactly one call. So a top-level import there made the ENTIRE llmsr CLI
(including `init` / `prompt` / `best`, which never touch softmax) hard-require an
optional package, and the guarded registration then hid the reason.

This is invisible in a dev checkout because the test and dev extras pull scipy
in. Guarding it therefore requires either denying scipy explicitly or checking
the import statements statically. Both are done below.

Two independent guards:
  1. No module in the llmsr package may import scipy at module top level.
     `fit.py` shows the intended pattern: a function-local import.
  2. The llmsr CLI must import with scipy genuinely unavailable.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

import pytest

LLMSR_PKG = Path(__file__).resolve().parents[2] / "wheeler" / "integrations" / "llmsr"


def _toplevel_scipy_importers() -> list[str]:
    """Return 'relpath:lineno' for every MODULE-LEVEL scipy import."""
    offenders: list[str] = []
    for path in sorted(LLMSR_PKG.rglob("*.py")):
        tree = ast.parse(path.read_text(), filename=str(path))
        # Only module-level statements: a function-local import is the pattern
        # we WANT, so walking the whole tree would flag the good case too.
        for node in tree.body:
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            if any(n == "scipy" or n.startswith("scipy.") for n in names):
                rel = path.relative_to(LLMSR_PKG.parents[2])
                offenders.append(f"{rel}:{node.lineno}")
    return offenders


def test_no_top_level_scipy_import_in_llmsr_package() -> None:
    """scipy is optional, so importing the package must not require it."""
    offenders = _toplevel_scipy_importers()

    assert offenders == [], (
        "scipy is the optional [llmsr] extra, but it is imported at MODULE TOP "
        f"LEVEL in: {', '.join(offenders)}. That makes the whole llmsr CLI "
        "unimportable without scipy, and because wheeler/tools/cli.py registers "
        "the group inside a guarded try/except ImportError, `wheeler llmsr` then "
        "reports 'No such command' with no hint. Import scipy inside the "
        "function that needs it, as wheeler/integrations/llmsr/fit.py does."
    )


def test_llmsr_cli_imports_without_scipy() -> None:
    """The engine must import with scipy genuinely denied, not merely present."""
    program = """
import sys

class _DenyScipy:
    def find_spec(self, name, path=None, target=None):
        if name == "scipy" or name.startswith("scipy."):
            raise ModuleNotFoundError("No module named 'scipy'", name="scipy")
        return None

sys.meta_path.insert(0, _DenyScipy())
for _m in [k for k in list(sys.modules) if k.startswith("scipy")]:
    del sys.modules[_m]

import wheeler.integrations.llmsr.cli as m
print("OK", m.__name__)
"""
    result = subprocess.run(
        [sys.executable, "-c", program],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).resolve().parents[2]),
    )

    assert result.returncode == 0, (
        "wheeler.integrations.llmsr.cli must import when scipy is absent, "
        "because scipy is an optional extra. It failed:\n"
        f"{result.stderr[-2500:]}"
    )
    assert "OK" in result.stdout


def test_llmsr_command_group_is_registered() -> None:
    """`wheeler llmsr` must resolve, never 'No such command'."""
    from typer.main import get_command

    from wheeler.tools.cli import app

    command = get_command(app)
    subcommands = getattr(command, "commands", {})

    assert "llmsr" in subcommands, (
        "The `llmsr` command group is not registered on the Typer app. It must "
        "resolve either to the real engine or to the diagnostic stub, so the "
        "user never sees a bare 'No such command' with no explanation."
    )


@pytest.mark.parametrize("subcommand", ["init", "prompt", "submit", "best"])
def test_llmsr_subcommands_present(subcommand: str) -> None:
    """The workflow's verbs must exist once the engine imports."""
    from typer.main import get_command

    from wheeler.tools.cli import app

    llmsr = getattr(get_command(app), "commands", {}).get("llmsr")
    assert llmsr is not None, "llmsr group missing entirely"

    names = set(getattr(llmsr, "commands", {}))
    assert subcommand in names, (
        f"`wheeler llmsr {subcommand}` is missing. Present: {sorted(names)}. "
        "The /wh:llmsr-discover workflow calls init, prompt, submit, and best."
    )
