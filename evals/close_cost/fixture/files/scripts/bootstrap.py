"""Bootstrap confidence intervals for the kernel coefficient."""

import random

N_RESAMPLES = 2000


def resample(values: list[float], rng: random.Random) -> list[float]:
    return [rng.choice(values) for _ in values]


def ci(values: list[float], seed: int = 0) -> tuple[float, float]:
    rng = random.Random(seed)
    means = []
    for _ in range(N_RESAMPLES):
        draw = resample(values, rng)
        means.append(sum(draw) / len(draw))
    means.sort()
    lo = means[int(0.025 * len(means))]
    hi = means[int(0.975 * len(means))]
    return lo, hi
