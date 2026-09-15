"""Fit a lag-1 spike-count history model per cell.

Model: log E[n_t] = b0 + b1 * n_{t-1}. Fit by Newton steps on the Poisson
log-likelihood. Writes ``data/history_fit_params.csv``.
"""

import csv
import math


def fit_lag1(counts, n_iter=25):
    """Return (b0, b1, loglik) for one count vector."""
    x = counts[:-1]
    y = counts[1:]
    b0, b1 = math.log(max(sum(y) / len(y), 1e-3)), 0.0
    for _ in range(n_iter):
        mu = [math.exp(b0 + b1 * xi) for xi in x]
        g0 = sum(yi - mi for yi, mi in zip(y, mu))
        g1 = sum((yi - mi) * xi for yi, mi, xi in zip(y, mu, x))
        h00 = sum(mu)
        h01 = sum(mi * xi for mi, xi in zip(mu, x))
        h11 = sum(mi * xi * xi for mi, xi in zip(mu, x))
        det = h00 * h11 - h01 * h01
        if det <= 0:
            break
        b0 += (h11 * g0 - h01 * g1) / det
        b1 += (-h01 * g0 + h00 * g1) / det
    mu = [math.exp(b0 + b1 * xi) for xi in x]
    ll = sum(yi * math.log(mi) - mi for yi, mi in zip(y, mu))
    return b0, b1, ll


def write_params(rows, path):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["cell_id", "b0", "b1", "loglik"])
        w.writerows(rows)
