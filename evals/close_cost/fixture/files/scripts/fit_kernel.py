"""Fit the one-lag history kernel per cell."""

import csv
from pathlib import Path

OUT = Path("data/kernel_params.csv")


def fit(rows: list[dict]) -> dict:
    n = max(len(rows), 1)
    mean = sum(float(r["count"]) for r in rows) / n
    return {"mean_count": mean, "n": n}


def write(params: dict, path: Path = OUT) -> None:
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=sorted(params))
        w.writeheader()
        w.writerow(params)
