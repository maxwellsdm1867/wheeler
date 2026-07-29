"""A registered metric, loader or optimizer must be OFFERABLE, not just usable.

`services.default.yaml` points the `llmsr-discover` contract's `metric` port at
`wheeler.integrations.llmsr.metrics:available` through `options_from`, so that
the interview offers whatever the scientist registered instead of a hardcoded
`[nmse, mse]`. That wiring is only worth having if `available()` actually sees
the scientist's modules: a listing that reported the built-ins alone would leave
a registered metric exactly as invisible as the hardcoded list did, which is the
bug the port was added to fix.

These tests pin that end to end, in a FRESH interpreter for the listing calls,
because the failure mode is process-scoped: once anything in the process has
called `load_user_metrics()`, the registry is populated and a broken
`available()` looks correct. Running in-process would hide it.
"""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]

_USER_MODULE = {
    "metrics": textwrap.dedent(
        """
        import numpy as np
        from wheeler.integrations.llmsr.metrics import (
            REGRESSION, Metric, register_metric,
        )

        def _mae(y_pred, y_true):
            return float(np.mean(np.abs(np.asarray(y_pred) - np.asarray(y_true))))

        register_metric(Metric(
            key="scientist_mae", label="Scientist MAE", data_shape=REGRESSION,
            lower_is_better=True, loss=_mae, report=_mae,
        ))
        """
    ),
    "loaders": textwrap.dedent(
        """
        from wheeler.integrations.llmsr.loaders import (
            Loader, get_loader, register_loader,
        )

        register_loader(Loader(
            key="scientist_csv", label="Scientist CSV",
            load=lambda request: get_loader("csv").load(request),
        ))
        """
    ),
    "optimizers": textwrap.dedent(
        """
        from wheeler.integrations.llmsr.optimizers import (
            Optimizer, get_optimizer, register_optimizer,
        )

        register_optimizer(Optimizer(
            key="scientist_powell", label="Scientist Powell",
            minimize=get_optimizer("powell").minimize,
        ))
        """
    ),
}


def _run(project: Path, code: str) -> str:
    """Run `code` in a fresh interpreter, cwd'd into `project`."""
    proc = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(code)],
        cwd=project,
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin", "HOME": str(project), "PYTHONPATH": str(REPO)},
    )
    assert proc.returncode == 0, f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
    return proc.stdout.strip()


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / ".wheeler" / "llmsr").mkdir(parents=True)
    return tmp_path


@pytest.mark.parametrize(
    ("kind", "registered"),
    [
        ("metrics", "scientist_mae"),
        ("loaders", "scientist_csv"),
        ("optimizers", "scientist_powell"),
    ],
)
def test_available_sees_the_scientists_registration(project, kind, registered):
    """`available()` imports the user modules, so a registration is offerable.

    This is the assertion the `options_from` port depends on. Before the fix,
    every one of these returned the built-ins only.
    """
    (project / ".wheeler" / "llmsr" / f"{kind}.py").write_text(_USER_MODULE[kind])

    listed = json.loads(_run(project, f"""
        import json
        from wheeler.integrations.llmsr import {kind} as mod
        print(json.dumps(mod.available()))
    """))

    assert registered in listed, (
        f"{kind}.available() did not import the scientist's module: {listed}. "
        "The options_from port would offer only the built-ins."
    )


@pytest.mark.parametrize("kind", ["metrics", "loaders", "optimizers"])
def test_a_broken_user_module_does_not_take_down_the_listing(project, kind):
    """One unimportable file must not make the interview unanswerable.

    `load_user_*()` is the call that REPORTS failures. `available()` is a
    listing, and a listing that raised would turn one bad file into a dead
    command, so it degrades to the registrations it does have.
    """
    (project / ".wheeler" / "llmsr" / f"{kind}.py").write_text(
        "raise RuntimeError('this module is broken on purpose')\n"
    )

    listed = json.loads(_run(project, f"""
        import json
        from wheeler.integrations.llmsr import {kind} as mod
        print(json.dumps(mod.available()))
    """))

    assert listed, f"{kind}.available() returned nothing for a broken source"


def test_the_metric_port_offers_a_registered_metric(project):
    """End to end through the real contract: the port, not just the callable.

    Guards the whole chain that made the hardcoded `[nmse, mse]` a bug:
    services.default.yaml -> options_from -> metrics:available -> the registry.
    """
    (project / ".wheeler" / "llmsr" / "metrics.py").write_text(_USER_MODULE["metrics"])

    options = json.loads(_run(project, """
        import json
        from wheeler.integrations.registry import load_services
        from wheeler.integrations.invocation import input_ports

        contract = next(
            c for c in load_services(None) if c.id == "llmsr-discover"
        )
        port = next(p for p in input_ports(contract) if p.name == "metric")
        print(json.dumps(list(port.options)))
    """))

    assert "scientist_mae" in options, (
        f"the metric port still offers a frozen list: {options}"
    )
    assert {"mse", "nmse"} <= set(options), (
        f"the built-ins must survive alongside the registration: {options}"
    )
