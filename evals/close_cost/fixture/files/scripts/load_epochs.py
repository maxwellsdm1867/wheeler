"""Load one cell's epochs from the raw export."""

import csv
from pathlib import Path

RAW = Path("data/epochs_cell01.csv")


def load(path: Path = RAW) -> list[dict]:
    with path.open() as fh:
        return [dict(row) for row in csv.DictReader(fh)]


if __name__ == "__main__":
    rows = load()
    print(f"loaded {len(rows)} epochs")
