# Results: vmn_lag1_history_counts

Date: 2026-09-12

The fitted lag-1 coefficient is negative for most cells (fig01) and the
population mean is reliably below zero (fig05). The count history kernel
returns to baseline within a few bins (fig03). Counts are over-dispersed
relative to Poisson (fig06), and cells with higher baseline rates show less
suppression (fig08). Adding the lag-1 term improves held-out log-likelihood in
every cell (fig10).

Tables: `data/history_fit_params.csv`, `data/lag1_counts_by_cell.csv`,
`data/bootstrap_ci.csv`, `data/summary_table.csv`.
