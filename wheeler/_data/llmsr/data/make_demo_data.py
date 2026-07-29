"""Regenerate the synthetic demo tables that ship beside the bundled specs.

Run it from anywhere::

    python wheeler/_data/llmsr/data/make_demo_data.py [--out DIR]

These tables are NOT the LLM-SR paper's data, which is not vendored here. They
are generated from laws written in this file, so the answer a search is supposed
to find is checked in beside the question, and a demo can be re-derived rather
than trusted.

Two rules the generator holds to, both so the shipped CSVs can be regenerated and
compared:

- **No random number generator.** Sample positions come from an additive
  recurrence on irrational constants and the measurement noise from an integer
  LCG. Both are exact arithmetic in Python, so they do not depend on the numpy
  version that happens to be installed.
- **Fixed formatting.** Every cell is written with six decimals, so a last-bit
  difference in a libm ``exp`` on some other platform cannot change the file.

``tests/integrations/llmsr/test_bundled.py`` reruns this and compares against the
checked-in tables.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

# Fractional parts of sqrt(2), sqrt(3), sqrt(5), sqrt(7): an additive recurrence
# on these fills a box far more evenly than independent uniform draws, and does
# it with no RNG state to depend on.
_ALPHAS = (
    math.sqrt(2.0) % 1.0,
    math.sqrt(3.0) % 1.0,
    math.sqrt(5.0) % 1.0,
    math.sqrt(7.0) % 1.0,
)


def _unit(index: int, dimension: int) -> float:
    """The ``dimension``-th coordinate of sample ``index``, in [0, 1)."""
    return ((index + 1) * _ALPHAS[dimension % len(_ALPHAS)]) % 1.0


class _Noise:
    """A plain integer LCG: reproducible everywhere, to the bit."""

    def __init__(self, seed: int) -> None:
        self._state = seed

    def next(self, scale: float) -> float:
        """One symmetric draw in ``[-scale, +scale]``."""
        self._state = (1103515245 * self._state + 12345) % 2147483648
        return scale * (2.0 * (self._state / 2147483648.0) - 1.0)


def _row(values: list[float]) -> str:
    return ",".join(f"{v:.6f}" for v in values)


def bactgrow_rows(
    n: int, *, seed: int, gain: float = 1.0, temp_opt: float = 37.0
) -> list[list[float]]:
    """Growth rate from density, substrate, temperature and pH.

    The law is Monod uptake times a temperature optimum times a pH optimum::

        growth = gain * b * s / (0.4 + s)
                 * exp(-(temp - temp_opt)**2 / 50)
                 * exp(-(pH - 7.0)**2 / 1.5)

    ``gain`` and ``temp_opt`` are what a strain varies: same FORM, different
    constants, which is the situation ``--group-by`` exists for.
    """
    noise = _Noise(seed)
    rows = []
    for i in range(n):
        b = 0.1 + 1.9 * _unit(i, 0)
        s = 0.05 + 2.95 * _unit(i, 1)
        temp = 20.0 + 25.0 * _unit(i, 2)
        ph = 5.0 + 4.0 * _unit(i, 3)
        growth = (
            gain
            * b
            * s / (0.4 + s)
            * math.exp(-((temp - temp_opt) ** 2) / 50.0)
            * math.exp(-((ph - 7.0) ** 2) / 1.5)
        )
        # A 1% measurement error, so the table has a noise floor a search must
        # not try to fit below.
        rows.append([b, s, temp, ph, growth * (1.0 + noise.next(0.01))])
    return rows


def oscillator_rows(n: int, *, seed: int) -> list[list[float]]:
    """Acceleration of a damped cubic (Duffing) oscillator::

        a = -2.5 * x - 0.35 * v - 0.6 * x**3

    ``t`` is recorded and handed to the equation but does not appear in the law:
    the system is autonomous. A correct form drops it, which is part of what the
    demo is for.
    """
    noise = _Noise(seed)
    rows = []
    for i in range(n):
        t = 10.0 * _unit(i, 0)
        x = -2.0 + 4.0 * _unit(i, 1)
        v = -3.0 + 6.0 * _unit(i, 2)
        a = -2.5 * x - 0.35 * v - 0.6 * x**3
        rows.append([t, x, v, a + noise.next(0.02)])
    return rows


def write_all(out_dir: Path) -> list[Path]:
    """Write every demo table. Returns the paths, in a stable order."""
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    plain = out_dir / "bactgrow_demo.csv"
    lines = ["b,s,temp,pH,growth"]
    lines += [_row(r) for r in bactgrow_rows(120, seed=20250729)]
    plain.write_text("\n".join(lines) + "\n")
    written.append(plain)

    # Three strains sharing the FORM and differing in two constants: the gain and
    # where the temperature optimum sits.
    strains = out_dir / "bactgrow_strains_demo.csv"
    lines = ["strain,b,s,temp,pH,growth"]
    for name, gain, temp_opt, seed in (
        ("K12", 1.0, 37.0, 11), ("B", 0.62, 33.5, 22), ("W3110", 1.45, 40.0, 33),
    ):
        for row in bactgrow_rows(60, seed=seed, gain=gain, temp_opt=temp_opt):
            lines.append(f"{name},{_row(row)}")
    strains.write_text("\n".join(lines) + "\n")
    written.append(strains)

    oscillator = out_dir / "oscillator_demo.csv"
    lines = ["t,x,v,a"]
    lines += [_row(r) for r in oscillator_rows(150, seed=4242)]
    oscillator.write_text("\n".join(lines) + "\n")
    written.append(oscillator)

    return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="where to write the tables (default: beside this script)",
    )
    args = parser.parse_args()
    for path in write_all(args.out):
        print(path)


if __name__ == "__main__":
    main()
