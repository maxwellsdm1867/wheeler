# Methods: vmn_lag1_history_counts

Date: 2026-09-12

## Recordings

Twelve ON-parasol retinal ganglion cells recorded in loose-patch under a
full-field white-noise stimulus (8 ms frames, 50% contrast). Each cell
contributed between 40 and 60 epochs of 4 s.

## Binning

Spikes were binned at 20 ms (`scripts/load_epochs.py`). Counts from all epochs
of a cell were concatenated for fitting.

## Model

The lag-1 count history model is a Poisson GLM with a single history term,

    log E[n_t] = b0 + b1 * n_(t-1),

fit by Newton steps on the Poisson log-likelihood
(`scripts/fit_lag1_history.py`). Held-out log-likelihood used a 5-fold split
over epochs.

## Bootstrap

The population coefficient was bootstrapped by resampling cells with
replacement, 2000 draws (`scripts/bootstrap_ci.py`).
