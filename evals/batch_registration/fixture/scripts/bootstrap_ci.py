"""Bootstrap 95% CI for the population-mean lag-1 coefficient.

Resamples cells with replacement (2000 draws, seed 7) and writes
``data/bootstrap_ci.csv``.
"""

import csv
import random
import statistics

N_BOOT = 2000


def bootstrap_mean(values, n_boot=N_BOOT, seed=7):
    rng = random.Random(seed)
    means = []
    for _ in range(n_boot):
        draw = [rng.choice(values) for _ in values]
        means.append(statistics.fmean(draw))
    means.sort()
    lo = means[int(0.025 * n_boot)]
    hi = means[int(0.975 * n_boot)]
    return statistics.fmean(values), lo, hi


def write_ci(rows, path):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["quantity", "estimate", "ci_lo", "ci_hi", "n_boot"])
        w.writerows(rows)
