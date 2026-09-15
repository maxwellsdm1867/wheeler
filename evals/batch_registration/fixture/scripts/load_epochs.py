"""Load raw epochs and bin spikes into fixed-width count vectors.

Reads ``data/raw_epochs_cell01.csv`` style tables (one row per spike) and
returns a dict of cell id -> list of per-bin spike counts.
"""

import csv
from collections import defaultdict

BIN_MS = 20.0


def load_counts(path, bin_ms=BIN_MS):
    """Return {cell_id: [count per bin]} for one raw epoch file."""
    spikes = defaultdict(list)
    with open(path) as f:
        for row in csv.DictReader(f):
            spikes[row["cell_id"]].append(float(row["spike_time_ms"]))
    counts = {}
    for cell, times in spikes.items():
        n_bins = int(max(times) // bin_ms) + 1
        vec = [0] * n_bins
        for t in times:
            vec[int(t // bin_ms)] += 1
        counts[cell] = vec
    return counts


if __name__ == "__main__":
    import sys

    c = load_counts(sys.argv[1])
    print({k: len(v) for k, v in c.items()})
