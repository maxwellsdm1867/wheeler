# Methods

Recordings were made in whole-cell voltage clamp at a holding potential of
-60 mV. Epochs were segmented by the stimulus marker channel and counted with
`scripts/load_epochs.py`.

The one-lag history kernel is fit per cell by least squares on the epoch count
series. Confidence intervals come from a 2000-resample bootstrap over epochs,
stratified by cell. No pooling across cells is performed at the fit stage: the
coefficient is estimated per cell and only summarized afterwards.

Figures are rendered by `scripts/make_figs.py` into `figures/`.
