"""The llmsr `metric` port must offer the metrics that are actually registered.

The registry is OPEN: a scientist registers their own metric and the search can
optimize it. The service contract used to hardcode ``options: [nmse, mse]``, so
that metric was invisible to the interview no matter what it was called. The port
now asks the registry (``options_from``), and these tests pin that wiring from
the llmsr side.

Registry isolation comes from this directory's conftest: each test runs in a
scratch project and the process-wide registry is restored afterwards.
"""

from __future__ import annotations

from pathlib import Path

from wheeler.integrations.invocation import input_ports, validate_request
from wheeler.integrations.llmsr import metrics as metrics_mod
from wheeler.integrations.registry import catalog_services


def _llmsr_contract():
    return next(c for c in catalog_services() if c.id == "llmsr-discover")


def _metric_port():
    return {p.name: p for p in input_ports(_llmsr_contract())}["metric"]


def _register(key: str) -> None:
    metrics_mod.register_metric(
        metrics_mod.Metric(
            key=key,
            label=f"{key} (test)",
            data_shape=metrics_mod.REGRESSION,
            lower_is_better=True,
            loss=lambda y_pred, y_true: 0.0,
            report=lambda y_pred, y_true: 0.0,
        )
    )


class TestMetricPort:
    def test_builtins_are_always_offered(self):
        assert {"mse", "nmse"} <= set(_metric_port().options)

    def test_a_registered_metric_becomes_offerable(self):
        assert "spikeloss" not in _metric_port().options
        _register("spikeloss")
        assert "spikeloss" in _metric_port().options

    def test_a_registered_metric_validates_as_an_answer(self):
        _register("spikeloss")
        contract = _llmsr_contract()
        request = {"dataset": "D-1", "metric": "spikeloss"}
        assert validate_request(contract, request).ok is True
        # and an unregistered one is still rejected: the port stayed a choice
        assert validate_request(contract, {"dataset": "D-1", "metric": "nope"}).ok is False

    def test_a_project_metrics_file_is_offerable_once_loaded(self):
        """The scientist's real path: a metric declared in the project's
        ``.wheeler/llmsr/metrics.py``. It becomes offerable once the registry has
        imported it. NOTE: ``available()`` does not import the userland sources
        itself, so a caller that has not run ``load_user_metrics()`` in its own
        process still sees only the built-ins (see llmsr/CLAUDE.md)."""
        source = Path(".wheeler/llmsr/metrics.py")
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(
            "from wheeler.integrations.llmsr.metrics import (\n"
            "    REGRESSION, Metric, register_metric,\n"
            ")\n"
            "register_metric(Metric(key='userland', label='userland',\n"
            "                       data_shape=REGRESSION, lower_is_better=True,\n"
            "                       loss=lambda p, t: 0.0, report=lambda p, t: 0.0))\n"
        )
        assert metrics_mod.load_user_metrics() == []
        assert "userland" in _metric_port().options
