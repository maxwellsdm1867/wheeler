"""Count events and compute the Fano factor per cell.

Writes ``data/lag1_counts_by_cell.csv`` (n_events, mean, var, fano) and the
per-cell event times for cell 01 (``data/event_times_cell01.csv``).
"""

import csv
import statistics


def fano(counts):
    m = statistics.fmean(counts)
    v = statistics.pvariance(counts)
    return v / m if m > 0 else float("nan")


def summarize(counts_by_cell):
    rows = []
    for cell, vec in sorted(counts_by_cell.items()):
        rows.append([cell, sum(vec), statistics.fmean(vec), statistics.pvariance(vec), fano(vec)])
    return rows


def write_summary(rows, path):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["cell_id", "n_events", "mean_count", "var_count", "fano"])
        w.writerows(rows)
