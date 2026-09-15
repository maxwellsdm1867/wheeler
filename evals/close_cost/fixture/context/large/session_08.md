# Prior session 8 of 20

Transcript of an earlier working session on the history-kernel analysis.

### Step 1: bootstrapping the CI

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell08    0.234  0.029   0.176  0.291  44        500
cell18    0.132  0.025   0.082  0.181  42        2000
cell07    0.135  0.019   0.099  0.172  57        1000
cell12    0.293  0.042   0.210  0.375  57        4000
cell19    0.246  0.032   0.183  0.309  52        500
cell16    0.142  0.021   0.100  0.183  49        2000
cell10    0.109  0.042   0.027  0.190  38        500
cell10    0.084  0.016   0.054  0.115  57        1000
cell02    0.222  0.039   0.146  0.298  48        4000
cell04    0.211  0.033   0.147  0.275  46        2000
cell11    0.308  0.049   0.212  0.405  53        4000
cell18    0.268  0.043   0.184  0.353  58        500
cell09    0.116  0.025   0.068  0.165  46        1000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell06    0.134  0.026   0.083  0.184  40        500
cell21    0.272  0.030   0.213  0.330  54        2000
cell01    0.295  0.030   0.235  0.355  54        4000
cell14    0.200  0.031   0.139  0.261  41        2000
cell12    0.184  0.036   0.114  0.254  54        500
cell03    0.226  0.022   0.183  0.269  39        1000
cell23    0.126  0.045   0.038  0.214  44        500
cell24    0.083  0.038   0.008  0.158  49        4000
cell03    0.149  0.011   0.127  0.171  40        500
cell06    0.244  0.019   0.205  0.282  44        1000
cell08    0.135  0.032   0.073  0.198  44        2000
cell18    0.214  0.034   0.147  0.281  44        4000
```

While re-running with a tighter segmentation threshold for cell16, the coefficient tracked epoch count more closely than duration (coefficient 0.142, stderr 0.030, n = 49). While comparing per-cell orderings for cell05, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.287, stderr 0.029, n = 56). While re-running with a tighter segmentation threshold for cell16, nothing in the figure changed at print size (coefficient 0.277, stderr 0.041, n = 51). While auditing the holding potential column for cell20, the ordering of cells was preserved (coefficient 0.169, stderr 0.022, n = 47). While comparing per-cell orderings for cell16, the estimate moved less than one standard error (coefficient 0.175, stderr 0.049, n = 42). While segmenting epochs for cell20, the CI narrowed by roughly a tenth (coefficient 0.224, stderr 0.024, n = 45). Parking this until the re-segmentation lands.

While segmenting epochs for cell23, the CI narrowed by roughly a tenth (coefficient 0.081, stderr 0.028, n = 40). While bootstrapping the CI for cell03, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.202, stderr 0.013, n = 51). While comparing per-cell orderings for cell22, two cells fell out of the usable range (coefficient 0.276, stderr 0.025, n = 53). While re-running with a tighter segmentation threshold for cell06, two cells fell out of the usable range (coefficient 0.295, stderr 0.038, n = 54).

### Step 2: re-exporting the raw traces

While bootstrapping the CI for cell22, two cells fell out of the usable range (coefficient 0.131, stderr 0.025, n = 41). While comparing per-cell orderings for cell24, the ordering of cells was preserved (coefficient 0.139, stderr 0.029, n = 45). While checking residual autocorrelation for cell13, nothing in the figure changed at print size (coefficient 0.253, stderr 0.027, n = 41). While bootstrapping the CI for cell05, two cells fell out of the usable range (coefficient 0.229, stderr 0.031, n = 56). While re-exporting the raw traces for cell16, the estimate moved less than one standard error (coefficient 0.302, stderr 0.026, n = 46).

While re-running with a tighter segmentation threshold for cell24, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.167, stderr 0.015, n = 56). While comparing per-cell orderings for cell08, the estimate moved less than one standard error (coefficient 0.131, stderr 0.019, n = 39). While auditing the holding potential column for cell10, two cells fell out of the usable range (coefficient 0.306, stderr 0.034, n = 55). While fitting the one-lag kernel for cell02, the CI narrowed by roughly a tenth (coefficient 0.293, stderr 0.042, n = 39). While bootstrapping the CI for cell21, the estimate moved less than one standard error (coefficient 0.179, stderr 0.015, n = 51). Worth noting for the writeup, though not a result on its own.

While re-exporting the raw traces for cell17, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.213, stderr 0.014, n = 47). While segmenting epochs for cell23, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.219, stderr 0.014, n = 51). While auditing the holding potential column for cell11, two cells fell out of the usable range (coefficient 0.197, stderr 0.025, n = 41). While bootstrapping the CI for cell02, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.091, stderr 0.025, n = 44). While comparing per-cell orderings for cell21, the CI narrowed by roughly a tenth (coefficient 0.304, stderr 0.031, n = 57).

### Step 3: segmenting epochs

While checking residual autocorrelation for cell19, the ordering of cells was preserved (coefficient 0.141, stderr 0.036, n = 50). While segmenting epochs for cell01, the coefficient tracked epoch count more closely than duration (coefficient 0.117, stderr 0.023, n = 54). While segmenting epochs for cell12, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.176, stderr 0.040, n = 44). While comparing per-cell orderings for cell22, the CI narrowed by roughly a tenth (coefficient 0.205, stderr 0.024, n = 41).

While auditing the holding potential column for cell16, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.164, stderr 0.045, n = 50). While comparing per-cell orderings for cell20, the coefficient tracked epoch count more closely than duration (coefficient 0.236, stderr 0.012, n = 41). While re-exporting the raw traces for cell11, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.281, stderr 0.018, n = 49). While bootstrapping the CI for cell24, the coefficient tracked epoch count more closely than duration (coefficient 0.241, stderr 0.028, n = 39). Flagging it so it does not get rediscovered next week.

While comparing per-cell orderings for cell09, nothing in the figure changed at print size (coefficient 0.266, stderr 0.030, n = 49). While segmenting epochs for cell04, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.239, stderr 0.049, n = 50). While re-running with a tighter segmentation threshold for cell02, the estimate moved less than one standard error (coefficient 0.153, stderr 0.036, n = 55). While re-running with a tighter segmentation threshold for cell22, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.108, stderr 0.028, n = 44). While re-running with a tighter segmentation threshold for cell10, the estimate moved less than one standard error (coefficient 0.137, stderr 0.022, n = 57). Worth noting for the writeup, though not a result on its own.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell22    0.259  0.012   0.235  0.283  43        500
cell04    0.173  0.027   0.120  0.226  48        500
cell18    0.204  0.033   0.140  0.269  49        4000
cell22    0.116  0.042   0.033  0.198  48        4000
cell18    0.251  0.011   0.229  0.273  57        1000
cell13    0.299  0.017   0.265  0.333  56        1000
cell03    0.183  0.048   0.089  0.276  39        2000
cell04    0.135  0.036   0.064  0.207  50        2000
```

### Step 4: auditing the holding potential column

While re-exporting the raw traces for cell16, the CI narrowed by roughly a tenth (coefficient 0.288, stderr 0.020, n = 55). While segmenting epochs for cell23, the coefficient tracked epoch count more closely than duration (coefficient 0.295, stderr 0.034, n = 47). While fitting the one-lag kernel for cell06, the ordering of cells was preserved (coefficient 0.212, stderr 0.015, n = 44).

While bootstrapping the CI for cell21, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.113, stderr 0.040, n = 50). While checking residual autocorrelation for cell02, the CI narrowed by roughly a tenth (coefficient 0.284, stderr 0.046, n = 48). While auditing the holding potential column for cell18, the ordering of cells was preserved (coefficient 0.096, stderr 0.011, n = 57). Noted and moved on; it does not change the decision.

### Step 5: bootstrapping the CI

While re-running with a tighter segmentation threshold for cell23, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.180, stderr 0.045, n = 41). While re-exporting the raw traces for cell17, the CI narrowed by roughly a tenth (coefficient 0.111, stderr 0.028, n = 41). While checking residual autocorrelation for cell06, the CI narrowed by roughly a tenth (coefficient 0.209, stderr 0.030, n = 44). While re-exporting the raw traces for cell18, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.268, stderr 0.030, n = 42).

While re-exporting the raw traces for cell02, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.139, stderr 0.050, n = 38). While re-exporting the raw traces for cell01, the ordering of cells was preserved (coefficient 0.213, stderr 0.033, n = 40). While checking residual autocorrelation for cell16, the CI narrowed by roughly a tenth (coefficient 0.126, stderr 0.044, n = 39).

### Step 6: comparing per-cell orderings

While fitting the one-lag kernel for cell16, nothing in the figure changed at print size (coefficient 0.096, stderr 0.028, n = 50). While fitting the one-lag kernel for cell17, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.171, stderr 0.043, n = 49). While bootstrapping the CI for cell05, the CI narrowed by roughly a tenth (coefficient 0.149, stderr 0.022, n = 44). While comparing per-cell orderings for cell07, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.268, stderr 0.016, n = 43).

While segmenting epochs for cell07, the CI narrowed by roughly a tenth (coefficient 0.187, stderr 0.013, n = 39). While auditing the holding potential column for cell13, the ordering of cells was preserved (coefficient 0.159, stderr 0.011, n = 47). While re-exporting the raw traces for cell19, the coefficient tracked epoch count more closely than duration (coefficient 0.189, stderr 0.029, n = 38). While bootstrapping the CI for cell08, the CI narrowed by roughly a tenth (coefficient 0.241, stderr 0.019, n = 50). While segmenting epochs for cell06, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.101, stderr 0.036, n = 38). While comparing per-cell orderings for cell04, the estimate moved less than one standard error (coefficient 0.292, stderr 0.022, n = 44). Worth noting for the writeup, though not a result on its own.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell03    0.243  0.041   0.162  0.323  51        1000
cell07    0.199  0.046   0.109  0.289  38        2000
cell21    0.309  0.025   0.259  0.358  46        1000
cell20    0.102  0.022   0.058  0.146  43        2000
cell01    0.116  0.043   0.031  0.200  57        4000
cell07    0.183  0.024   0.135  0.231  51        1000
cell22    0.186  0.033   0.120  0.252  43        500
cell02    0.205  0.021   0.164  0.246  47        1000
cell02    0.207  0.018   0.172  0.242  39        1000
cell18    0.138  0.021   0.097  0.179  43        4000
cell07    0.303  0.022   0.260  0.345  56        4000
cell10    0.183  0.033   0.119  0.247  50        2000
cell19    0.177  0.020   0.138  0.217  44        500
cell05    0.287  0.022   0.244  0.331  38        1000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell14    0.101  0.028   0.046  0.157  53        1000
cell21    0.192  0.012   0.169  0.214  50        4000
cell11    0.086  0.040   0.009  0.164  43        2000
cell18    0.260  0.029   0.203  0.317  39        2000
cell13    0.202  0.021   0.160  0.244  45        1000
cell08    0.185  0.050   0.088  0.282  39        500
cell11    0.183  0.024   0.136  0.230  47        1000
cell08    0.233  0.013   0.207  0.259  54        4000
cell02    0.116  0.022   0.072  0.160  41        2000
cell20    0.222  0.030   0.164  0.281  57        1000
cell17    0.291  0.032   0.229  0.353  49        1000
cell15    0.090  0.014   0.063  0.117  47        2000
cell19    0.185  0.019   0.148  0.222  55        500
cell06    0.186  0.034   0.120  0.252  56        500
```

### Step 7: re-exporting the raw traces

```python
coefs = fit_per_cell(rows, threshold=0.62)
lo, hi = ci(coefs, seed=39)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While auditing the holding potential column for cell13, the estimate moved less than one standard error (coefficient 0.135, stderr 0.015, n = 54). While checking residual autocorrelation for cell09, the CI narrowed by roughly a tenth (coefficient 0.236, stderr 0.029, n = 39). While checking residual autocorrelation for cell02, the CI narrowed by roughly a tenth (coefficient 0.235, stderr 0.041, n = 44). While checking residual autocorrelation for cell08, nothing in the figure changed at print size (coefficient 0.307, stderr 0.014, n = 49). While segmenting epochs for cell05, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.273, stderr 0.027, n = 54). Parking this until the re-segmentation lands.

### Step 8: bootstrapping the CI

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell17    0.242  0.043   0.157  0.326  48        1000
cell13    0.104  0.014   0.078  0.131  41        2000
cell24    0.275  0.038   0.201  0.348  57        2000
cell04    0.254  0.012   0.230  0.278  48        4000
cell22    0.224  0.044   0.137  0.311  53        4000
cell23    0.265  0.041   0.185  0.344  45        1000
```

While fitting the one-lag kernel for cell17, the ordering of cells was preserved (coefficient 0.175, stderr 0.033, n = 53). While checking residual autocorrelation for cell15, the estimate moved less than one standard error (coefficient 0.304, stderr 0.039, n = 47). While segmenting epochs for cell01, the estimate moved less than one standard error (coefficient 0.306, stderr 0.037, n = 52). While bootstrapping the CI for cell07, the CI narrowed by roughly a tenth (coefficient 0.162, stderr 0.021, n = 43). While bootstrapping the CI for cell02, the ordering of cells was preserved (coefficient 0.191, stderr 0.030, n = 38).

### Step 9: comparing per-cell orderings

While bootstrapping the CI for cell01, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.175, stderr 0.036, n = 57). While bootstrapping the CI for cell09, the ordering of cells was preserved (coefficient 0.081, stderr 0.022, n = 51). While auditing the holding potential column for cell22, nothing in the figure changed at print size (coefficient 0.203, stderr 0.025, n = 49). While checking residual autocorrelation for cell15, the ordering of cells was preserved (coefficient 0.250, stderr 0.040, n = 57). While bootstrapping the CI for cell06, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.304, stderr 0.018, n = 40). While comparing per-cell orderings for cell06, the ordering of cells was preserved (coefficient 0.297, stderr 0.035, n = 42). Flagging it so it does not get rediscovered next week.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell17    0.285  0.020   0.247  0.324  47        4000
cell23    0.275  0.024   0.227  0.322  48        4000
cell19    0.130  0.018   0.094  0.166  39        1000
cell05    0.202  0.043   0.119  0.285  50        1000
cell12    0.277  0.021   0.236  0.318  49        2000
cell16    0.201  0.046   0.111  0.291  44        2000
cell19    0.134  0.015   0.104  0.164  40        500
cell10    0.097  0.018   0.061  0.133  42        4000
cell22    0.276  0.016   0.244  0.307  39        1000
cell01    0.271  0.027   0.218  0.323  38        2000
cell03    0.083  0.015   0.055  0.112  58        2000
cell14    0.168  0.020   0.130  0.207  54        4000
```

While auditing the holding potential column for cell04, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.243, stderr 0.044, n = 54). While fitting the one-lag kernel for cell14, nothing in the figure changed at print size (coefficient 0.176, stderr 0.038, n = 39). While re-running with a tighter segmentation threshold for cell12, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.189, stderr 0.022, n = 57).

While re-exporting the raw traces for cell21, the ordering of cells was preserved (coefficient 0.265, stderr 0.043, n = 39). While bootstrapping the CI for cell15, the estimate moved less than one standard error (coefficient 0.224, stderr 0.027, n = 41). While auditing the holding potential column for cell19, the coefficient tracked epoch count more closely than duration (coefficient 0.308, stderr 0.029, n = 48). While bootstrapping the CI for cell13, nothing in the figure changed at print size (coefficient 0.105, stderr 0.023, n = 57). While comparing per-cell orderings for cell07, nothing in the figure changed at print size (coefficient 0.099, stderr 0.044, n = 50). While re-running with a tighter segmentation threshold for cell23, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.178, stderr 0.036, n = 47). Flagging it so it does not get rediscovered next week.

### Step 10: auditing the holding potential column

While bootstrapping the CI for cell01, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.127, stderr 0.032, n = 39). While fitting the one-lag kernel for cell14, the estimate moved less than one standard error (coefficient 0.226, stderr 0.028, n = 38). While checking residual autocorrelation for cell05, two cells fell out of the usable range (coefficient 0.307, stderr 0.025, n = 46). While comparing per-cell orderings for cell12, the CI narrowed by roughly a tenth (coefficient 0.129, stderr 0.035, n = 43).

While checking residual autocorrelation for cell10, two cells fell out of the usable range (coefficient 0.282, stderr 0.020, n = 57). While bootstrapping the CI for cell04, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.168, stderr 0.046, n = 48). While bootstrapping the CI for cell08, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.119, stderr 0.045, n = 38).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell16    0.144  0.042   0.061  0.226  53        1000
cell18    0.221  0.033   0.157  0.285  39        4000
cell09    0.229  0.025   0.180  0.278  49        2000
cell04    0.177  0.020   0.138  0.216  49        1000
cell22    0.302  0.036   0.230  0.373  40        1000
cell11    0.119  0.047   0.026  0.211  38        4000
```

### Step 11: segmenting epochs

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell19    0.253  0.024   0.205  0.301  54        2000
cell21    0.264  0.016   0.233  0.295  50        2000
cell23    0.280  0.029   0.223  0.338  57        500
cell17    0.109  0.050   0.012  0.206  43        1000
cell16    0.146  0.037   0.074  0.219  52        4000
cell13    0.152  0.047   0.061  0.244  49        4000
cell24    0.247  0.020   0.208  0.285  47        2000
cell15    0.261  0.012   0.237  0.285  58        500
cell07    0.284  0.042   0.202  0.366  48        500
cell18    0.081  0.032   0.019  0.143  51        2000
```

While re-running with a tighter segmentation threshold for cell16, the estimate moved less than one standard error (coefficient 0.285, stderr 0.025, n = 38). While bootstrapping the CI for cell18, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.214, stderr 0.022, n = 55). While checking residual autocorrelation for cell06, nothing in the figure changed at print size (coefficient 0.153, stderr 0.031, n = 49). While comparing per-cell orderings for cell23, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.186, stderr 0.030, n = 45). While checking residual autocorrelation for cell01, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.105, stderr 0.030, n = 55).

### Step 12: segmenting epochs

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell05    0.103  0.012   0.080  0.126  54        500
cell06    0.087  0.025   0.038  0.136  47        1000
cell12    0.180  0.044   0.093  0.266  54        500
cell01    0.282  0.039   0.207  0.358  56        1000
cell15    0.208  0.045   0.120  0.295  49        500
cell15    0.231  0.040   0.153  0.310  46        4000
cell06    0.280  0.044   0.195  0.366  52        1000
cell15    0.241  0.038   0.167  0.316  52        1000
cell07    0.180  0.024   0.132  0.228  55        4000
cell17    0.182  0.014   0.155  0.209  47        1000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell13    0.124  0.046   0.033  0.215  47        2000
cell24    0.085  0.034   0.018  0.152  56        500
cell14    0.152  0.027   0.099  0.205  39        1000
cell02    0.250  0.038   0.176  0.324  43        500
cell06    0.153  0.041   0.072  0.233  57        2000
cell20    0.152  0.039   0.076  0.228  48        4000
cell18    0.122  0.041   0.042  0.201  52        2000
```

### Step 13: auditing the holding potential column

While re-running with a tighter segmentation threshold for cell15, two cells fell out of the usable range (coefficient 0.099, stderr 0.023, n = 51). While bootstrapping the CI for cell24, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.282, stderr 0.021, n = 53). While re-exporting the raw traces for cell04, the coefficient tracked epoch count more closely than duration (coefficient 0.095, stderr 0.012, n = 51). While fitting the one-lag kernel for cell05, two cells fell out of the usable range (coefficient 0.095, stderr 0.023, n = 39). While auditing the holding potential column for cell19, the coefficient tracked epoch count more closely than duration (coefficient 0.286, stderr 0.020, n = 42).

```python
coefs = fit_per_cell(rows, threshold=0.39)
lo, hi = ci(coefs, seed=87)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```python
coefs = fit_per_cell(rows, threshold=0.62)
lo, hi = ci(coefs, seed=69)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell03    0.095  0.030   0.036  0.155  41        500
cell10    0.227  0.016   0.195  0.258  54        500
cell15    0.284  0.011   0.261  0.306  45        1000
cell16    0.292  0.028   0.237  0.348  50        500
cell18    0.139  0.031   0.079  0.200  51        2000
cell19    0.278  0.019   0.241  0.316  49        2000
cell05    0.219  0.023   0.174  0.263  58        2000
cell20    0.259  0.017   0.226  0.293  51        2000
cell22    0.186  0.021   0.145  0.227  53        1000
cell02    0.106  0.014   0.078  0.135  45        2000
cell21    0.175  0.046   0.086  0.265  38        2000
cell11    0.134  0.012   0.110  0.158  52        1000
cell16    0.305  0.022   0.262  0.349  41        1000
cell05    0.191  0.013   0.164  0.217  57        4000
```

### Step 14: fitting the one-lag kernel

While fitting the one-lag kernel for cell01, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.236, stderr 0.030, n = 54). While auditing the holding potential column for cell21, the CI narrowed by roughly a tenth (coefficient 0.198, stderr 0.018, n = 51). While bootstrapping the CI for cell02, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.208, stderr 0.024, n = 43). While segmenting epochs for cell15, the estimate moved less than one standard error (coefficient 0.182, stderr 0.023, n = 52). Noted and moved on; it does not change the decision.

While checking residual autocorrelation for cell13, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.134, stderr 0.023, n = 48). While re-running with a tighter segmentation threshold for cell08, nothing in the figure changed at print size (coefficient 0.273, stderr 0.036, n = 41). While comparing per-cell orderings for cell04, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.092, stderr 0.030, n = 41). While segmenting epochs for cell19, nothing in the figure changed at print size (coefficient 0.303, stderr 0.024, n = 49).

While bootstrapping the CI for cell16, the CI narrowed by roughly a tenth (coefficient 0.198, stderr 0.037, n = 40). While auditing the holding potential column for cell19, nothing in the figure changed at print size (coefficient 0.210, stderr 0.013, n = 53). While re-running with a tighter segmentation threshold for cell06, two cells fell out of the usable range (coefficient 0.202, stderr 0.037, n = 49). While re-running with a tighter segmentation threshold for cell05, the CI narrowed by roughly a tenth (coefficient 0.137, stderr 0.019, n = 56). This is the part that will need a real statistical argument.

While re-running with a tighter segmentation threshold for cell08, the estimate moved less than one standard error (coefficient 0.243, stderr 0.049, n = 48). While auditing the holding potential column for cell03, the CI narrowed by roughly a tenth (coefficient 0.225, stderr 0.013, n = 52). While fitting the one-lag kernel for cell05, nothing in the figure changed at print size (coefficient 0.175, stderr 0.022, n = 51). While re-running with a tighter segmentation threshold for cell17, the estimate moved less than one standard error (coefficient 0.174, stderr 0.015, n = 50).

### Step 15: comparing per-cell orderings

While re-exporting the raw traces for cell14, the CI narrowed by roughly a tenth (coefficient 0.112, stderr 0.048, n = 49). While re-running with a tighter segmentation threshold for cell13, two cells fell out of the usable range (coefficient 0.119, stderr 0.041, n = 52). While segmenting epochs for cell13, the ordering of cells was preserved (coefficient 0.208, stderr 0.049, n = 56). While fitting the one-lag kernel for cell03, the coefficient tracked epoch count more closely than duration (coefficient 0.126, stderr 0.034, n = 53). While auditing the holding potential column for cell20, two cells fell out of the usable range (coefficient 0.302, stderr 0.029, n = 45).

While re-running with a tighter segmentation threshold for cell15, the ordering of cells was preserved (coefficient 0.203, stderr 0.030, n = 43). While comparing per-cell orderings for cell04, the CI narrowed by roughly a tenth (coefficient 0.248, stderr 0.022, n = 49). While auditing the holding potential column for cell20, the coefficient tracked epoch count more closely than duration (coefficient 0.130, stderr 0.047, n = 45). This is the part that will need a real statistical argument.

```python
coefs = fit_per_cell(rows, threshold=0.53)
lo, hi = ci(coefs, seed=99)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 16: re-exporting the raw traces

While segmenting epochs for cell08, the ordering of cells was preserved (coefficient 0.117, stderr 0.036, n = 42). While segmenting epochs for cell13, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.183, stderr 0.033, n = 41). While bootstrapping the CI for cell21, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.134, stderr 0.035, n = 52). While re-running with a tighter segmentation threshold for cell17, two cells fell out of the usable range (coefficient 0.157, stderr 0.047, n = 54). While bootstrapping the CI for cell16, the coefficient tracked epoch count more closely than duration (coefficient 0.094, stderr 0.017, n = 51).

While auditing the holding potential column for cell14, the ordering of cells was preserved (coefficient 0.108, stderr 0.037, n = 40). While auditing the holding potential column for cell17, the estimate moved less than one standard error (coefficient 0.190, stderr 0.046, n = 50). While comparing per-cell orderings for cell04, nothing in the figure changed at print size (coefficient 0.275, stderr 0.023, n = 47). While bootstrapping the CI for cell16, the estimate moved less than one standard error (coefficient 0.112, stderr 0.036, n = 47).

While checking residual autocorrelation for cell04, two cells fell out of the usable range (coefficient 0.290, stderr 0.031, n = 50). While checking residual autocorrelation for cell02, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.252, stderr 0.024, n = 58). While fitting the one-lag kernel for cell11, the ordering of cells was preserved (coefficient 0.246, stderr 0.036, n = 44). While bootstrapping the CI for cell17, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.237, stderr 0.012, n = 45).

While bootstrapping the CI for cell20, the coefficient tracked epoch count more closely than duration (coefficient 0.269, stderr 0.017, n = 39). While fitting the one-lag kernel for cell18, the ordering of cells was preserved (coefficient 0.096, stderr 0.040, n = 43). While auditing the holding potential column for cell09, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.133, stderr 0.033, n = 56). While re-running with a tighter segmentation threshold for cell06, two cells fell out of the usable range (coefficient 0.210, stderr 0.039, n = 47). While re-running with a tighter segmentation threshold for cell14, nothing in the figure changed at print size (coefficient 0.255, stderr 0.040, n = 56). Parking this until the re-segmentation lands.

### Step 17: comparing per-cell orderings

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell11    0.285  0.020   0.246  0.324  50        1000
cell10    0.126  0.013   0.100  0.152  49        500
cell09    0.120  0.024   0.073  0.168  53        500
cell13    0.093  0.039   0.018  0.169  54        1000
cell15    0.277  0.019   0.239  0.314  41        500
cell15    0.273  0.025   0.223  0.323  49        500
cell05    0.179  0.017   0.146  0.213  54        500
cell09    0.184  0.015   0.155  0.213  40        500
cell12    0.206  0.021   0.165  0.247  51        2000
cell22    0.110  0.041   0.029  0.191  40        500
cell17    0.242  0.033   0.176  0.308  54        500
cell18    0.227  0.031   0.166  0.287  48        2000
cell12    0.170  0.048   0.077  0.263  49        500
```

While segmenting epochs for cell02, the CI narrowed by roughly a tenth (coefficient 0.090, stderr 0.025, n = 51). While re-exporting the raw traces for cell06, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.091, stderr 0.015, n = 47). While auditing the holding potential column for cell22, the CI narrowed by roughly a tenth (coefficient 0.162, stderr 0.031, n = 44). While checking residual autocorrelation for cell22, the estimate moved less than one standard error (coefficient 0.157, stderr 0.049, n = 48).

### Step 18: comparing per-cell orderings

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell04    0.089  0.012   0.066  0.113  43        500
cell02    0.137  0.015   0.107  0.167  38        4000
cell02    0.087  0.030   0.030  0.145  38        2000
cell02    0.097  0.024   0.049  0.144  47        4000
cell19    0.282  0.022   0.240  0.325  58        2000
cell14    0.096  0.012   0.072  0.120  40        4000
cell01    0.091  0.018   0.056  0.126  55        2000
cell10    0.286  0.027   0.232  0.339  42        1000
cell17    0.142  0.019   0.105  0.179  39        1000
cell06    0.231  0.033   0.166  0.296  52        4000
cell08    0.172  0.038   0.097  0.247  51        500
```

While checking residual autocorrelation for cell16, the CI narrowed by roughly a tenth (coefficient 0.120, stderr 0.033, n = 53). While segmenting epochs for cell13, nothing in the figure changed at print size (coefficient 0.290, stderr 0.023, n = 46). While re-exporting the raw traces for cell15, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.113, stderr 0.021, n = 51). While bootstrapping the CI for cell01, the coefficient tracked epoch count more closely than duration (coefficient 0.235, stderr 0.018, n = 39). While segmenting epochs for cell05, the CI narrowed by roughly a tenth (coefficient 0.259, stderr 0.011, n = 42). While fitting the one-lag kernel for cell13, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.232, stderr 0.038, n = 55). This is the part that will need a real statistical argument.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell09    0.231  0.036   0.161  0.302  56        500
cell04    0.142  0.026   0.090  0.194  54        4000
cell14    0.291  0.011   0.270  0.311  38        500
cell16    0.273  0.025   0.224  0.322  54        2000
cell08    0.148  0.041   0.068  0.227  38        500
cell23    0.268  0.042   0.186  0.351  56        1000
cell15    0.160  0.029   0.104  0.216  52        4000
cell04    0.206  0.019   0.169  0.242  57        500
cell02    0.259  0.043   0.175  0.343  46        4000
cell19    0.241  0.042   0.159  0.323  47        2000
cell09    0.116  0.035   0.048  0.184  56        4000
cell02    0.207  0.030   0.148  0.267  48        2000
```

While auditing the holding potential column for cell22, the coefficient tracked epoch count more closely than duration (coefficient 0.137, stderr 0.029, n = 40). While fitting the one-lag kernel for cell01, two cells fell out of the usable range (coefficient 0.241, stderr 0.017, n = 46). While re-running with a tighter segmentation threshold for cell15, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.159, stderr 0.015, n = 43). While checking residual autocorrelation for cell22, the coefficient tracked epoch count more closely than duration (coefficient 0.298, stderr 0.048, n = 38). While segmenting epochs for cell05, the CI narrowed by roughly a tenth (coefficient 0.215, stderr 0.029, n = 54). Worth noting for the writeup, though not a result on its own.

### Step 19: re-running with a tighter segmentation threshold

While checking residual autocorrelation for cell07, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.136, stderr 0.023, n = 57). While segmenting epochs for cell06, the CI narrowed by roughly a tenth (coefficient 0.205, stderr 0.026, n = 40). While re-running with a tighter segmentation threshold for cell02, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.200, stderr 0.023, n = 41).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell19    0.223  0.010   0.203  0.242  41        4000
cell20    0.271  0.045   0.183  0.358  55        1000
cell01    0.220  0.042   0.138  0.302  40        1000
cell02    0.293  0.050   0.195  0.391  39        500
cell14    0.132  0.029   0.075  0.188  41        1000
cell04    0.259  0.023   0.214  0.305  42        1000
cell23    0.198  0.030   0.140  0.257  51        4000
cell18    0.289  0.023   0.245  0.334  44        2000
cell06    0.136  0.029   0.079  0.193  51        1000
cell17    0.131  0.015   0.101  0.160  55        500
cell21    0.239  0.038   0.166  0.313  41        4000
cell15    0.266  0.020   0.226  0.306  49        2000
cell23    0.189  0.044   0.102  0.276  45        500
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell21    0.197  0.019   0.161  0.234  46        4000
cell01    0.159  0.036   0.090  0.229  39        1000
cell04    0.086  0.026   0.034  0.138  46        500
cell24    0.233  0.036   0.162  0.304  54        500
cell06    0.112  0.023   0.067  0.156  43        2000
cell01    0.122  0.046   0.031  0.213  57        4000
cell10    0.082  0.018   0.047  0.117  43        1000
cell03    0.267  0.026   0.216  0.319  40        500
cell10    0.270  0.038   0.195  0.344  48        1000
cell09    0.157  0.011   0.136  0.178  42        4000
```

```python
coefs = fit_per_cell(rows, threshold=0.35)
lo, hi = ci(coefs, seed=61)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 20: bootstrapping the CI

While auditing the holding potential column for cell13, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.085, stderr 0.046, n = 43). While re-exporting the raw traces for cell22, the estimate moved less than one standard error (coefficient 0.282, stderr 0.035, n = 54). While fitting the one-lag kernel for cell23, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.179, stderr 0.013, n = 52). While segmenting epochs for cell02, two cells fell out of the usable range (coefficient 0.264, stderr 0.040, n = 43). While re-exporting the raw traces for cell23, the CI narrowed by roughly a tenth (coefficient 0.107, stderr 0.018, n = 50). While fitting the one-lag kernel for cell02, the ordering of cells was preserved (coefficient 0.207, stderr 0.022, n = 47). Noted and moved on; it does not change the decision.

While auditing the holding potential column for cell11, the CI narrowed by roughly a tenth (coefficient 0.164, stderr 0.044, n = 44). While segmenting epochs for cell18, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.114, stderr 0.046, n = 54). While re-exporting the raw traces for cell23, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.113, stderr 0.042, n = 49). While checking residual autocorrelation for cell19, nothing in the figure changed at print size (coefficient 0.235, stderr 0.024, n = 38). While bootstrapping the CI for cell22, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.173, stderr 0.045, n = 48). While auditing the holding potential column for cell09, the coefficient tracked epoch count more closely than duration (coefficient 0.271, stderr 0.037, n = 43).

While re-exporting the raw traces for cell17, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.309, stderr 0.031, n = 53). While re-exporting the raw traces for cell14, nothing in the figure changed at print size (coefficient 0.158, stderr 0.028, n = 58). While auditing the holding potential column for cell19, the coefficient tracked epoch count more closely than duration (coefficient 0.234, stderr 0.015, n = 47). While bootstrapping the CI for cell04, the coefficient tracked epoch count more closely than duration (coefficient 0.198, stderr 0.036, n = 48).

### Step 21: checking residual autocorrelation

While segmenting epochs for cell12, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.209, stderr 0.027, n = 40). While re-running with a tighter segmentation threshold for cell16, nothing in the figure changed at print size (coefficient 0.261, stderr 0.035, n = 45). While fitting the one-lag kernel for cell07, nothing in the figure changed at print size (coefficient 0.138, stderr 0.040, n = 55). While auditing the holding potential column for cell22, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.252, stderr 0.038, n = 51). While comparing per-cell orderings for cell08, the estimate moved less than one standard error (coefficient 0.284, stderr 0.023, n = 46). While comparing per-cell orderings for cell05, two cells fell out of the usable range (coefficient 0.168, stderr 0.039, n = 53). Worth noting for the writeup, though not a result on its own.

```python
coefs = fit_per_cell(rows, threshold=0.47)
lo, hi = ci(coefs, seed=84)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 22: fitting the one-lag kernel

```python
coefs = fit_per_cell(rows, threshold=0.54)
lo, hi = ci(coefs, seed=28)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While fitting the one-lag kernel for cell19, the estimate moved less than one standard error (coefficient 0.299, stderr 0.014, n = 52). While re-exporting the raw traces for cell24, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.291, stderr 0.048, n = 54). While re-exporting the raw traces for cell12, the coefficient tracked epoch count more closely than duration (coefficient 0.112, stderr 0.043, n = 51). While fitting the one-lag kernel for cell06, the estimate moved less than one standard error (coefficient 0.261, stderr 0.018, n = 44).

### Step 23: comparing per-cell orderings

While comparing per-cell orderings for cell13, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.308, stderr 0.032, n = 56). While re-exporting the raw traces for cell06, the CI narrowed by roughly a tenth (coefficient 0.306, stderr 0.019, n = 43). While auditing the holding potential column for cell11, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.127, stderr 0.029, n = 38). While comparing per-cell orderings for cell23, the CI narrowed by roughly a tenth (coefficient 0.172, stderr 0.021, n = 44). While auditing the holding potential column for cell23, the coefficient tracked epoch count more closely than duration (coefficient 0.229, stderr 0.022, n = 57). While auditing the holding potential column for cell20, the ordering of cells was preserved (coefficient 0.082, stderr 0.037, n = 53).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell23    0.131  0.010   0.111  0.151  55        2000
cell21    0.305  0.038   0.231  0.379  56        2000
cell18    0.206  0.025   0.157  0.256  50        500
cell04    0.281  0.010   0.260  0.301  57        500
cell06    0.268  0.049   0.172  0.364  57        2000
cell08    0.119  0.035   0.050  0.188  40        4000
cell12    0.194  0.047   0.102  0.286  43        500
cell08    0.174  0.031   0.113  0.235  50        500
cell17    0.176  0.011   0.155  0.198  38        4000
cell10    0.227  0.034   0.160  0.293  49        1000
cell13    0.269  0.010   0.249  0.289  49        4000
cell18    0.084  0.040   0.005  0.163  50        2000
cell04    0.085  0.023   0.040  0.131  55        500
cell17    0.105  0.015   0.076  0.134  56        4000
```

### Step 24: segmenting epochs

While comparing per-cell orderings for cell09, nothing in the figure changed at print size (coefficient 0.310, stderr 0.033, n = 50). While checking residual autocorrelation for cell01, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.090, stderr 0.048, n = 42). While checking residual autocorrelation for cell10, the CI narrowed by roughly a tenth (coefficient 0.214, stderr 0.030, n = 43). While auditing the holding potential column for cell14, the coefficient tracked epoch count more closely than duration (coefficient 0.137, stderr 0.049, n = 51).

While bootstrapping the CI for cell03, the CI narrowed by roughly a tenth (coefficient 0.264, stderr 0.025, n = 48). While fitting the one-lag kernel for cell19, the coefficient tracked epoch count more closely than duration (coefficient 0.213, stderr 0.029, n = 52). While checking residual autocorrelation for cell09, the coefficient tracked epoch count more closely than duration (coefficient 0.097, stderr 0.018, n = 45). Noted and moved on; it does not change the decision.

```python
coefs = fit_per_cell(rows, threshold=0.54)
lo, hi = ci(coefs, seed=82)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While re-running with a tighter segmentation threshold for cell05, the coefficient tracked epoch count more closely than duration (coefficient 0.087, stderr 0.037, n = 50). While checking residual autocorrelation for cell15, the ordering of cells was preserved (coefficient 0.160, stderr 0.016, n = 39). While bootstrapping the CI for cell03, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.190, stderr 0.013, n = 57). While auditing the holding potential column for cell20, two cells fell out of the usable range (coefficient 0.104, stderr 0.022, n = 53). While re-running with a tighter segmentation threshold for cell21, the estimate moved less than one standard error (coefficient 0.098, stderr 0.046, n = 51). While checking residual autocorrelation for cell05, the CI narrowed by roughly a tenth (coefficient 0.227, stderr 0.045, n = 57).

### Step 25: segmenting epochs

While comparing per-cell orderings for cell04, the CI narrowed by roughly a tenth (coefficient 0.235, stderr 0.031, n = 49). While auditing the holding potential column for cell11, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.262, stderr 0.041, n = 54). While re-running with a tighter segmentation threshold for cell06, two cells fell out of the usable range (coefficient 0.260, stderr 0.029, n = 50). While re-exporting the raw traces for cell08, two cells fell out of the usable range (coefficient 0.220, stderr 0.010, n = 58). While comparing per-cell orderings for cell08, nothing in the figure changed at print size (coefficient 0.210, stderr 0.017, n = 54). While comparing per-cell orderings for cell11, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.232, stderr 0.014, n = 53).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell04    0.177  0.034   0.110  0.245  51        4000
cell24    0.187  0.037   0.114  0.259  55        2000
cell24    0.161  0.041   0.080  0.241  49        500
cell15    0.277  0.027   0.224  0.330  49        2000
cell15    0.303  0.044   0.216  0.389  47        2000
cell12    0.116  0.047   0.024  0.208  52        500
cell13    0.303  0.011   0.282  0.325  55        2000
cell17    0.175  0.031   0.115  0.236  42        2000
cell16    0.087  0.010   0.067  0.108  49        4000
cell02    0.150  0.017   0.116  0.184  50        1000
cell23    0.238  0.040   0.159  0.316  51        2000
cell19    0.215  0.041   0.135  0.294  50        500
cell15    0.296  0.018   0.260  0.332  42        500
```

### Step 26: auditing the holding potential column

While auditing the holding potential column for cell13, nothing in the figure changed at print size (coefficient 0.134, stderr 0.038, n = 50). While re-running with a tighter segmentation threshold for cell10, the estimate moved less than one standard error (coefficient 0.192, stderr 0.033, n = 43). While bootstrapping the CI for cell24, nothing in the figure changed at print size (coefficient 0.170, stderr 0.010, n = 41). While bootstrapping the CI for cell02, the ordering of cells was preserved (coefficient 0.275, stderr 0.021, n = 54). While checking residual autocorrelation for cell22, the estimate moved less than one standard error (coefficient 0.134, stderr 0.011, n = 55). While comparing per-cell orderings for cell24, two cells fell out of the usable range (coefficient 0.149, stderr 0.024, n = 45).

```python
coefs = fit_per_cell(rows, threshold=0.53)
lo, hi = ci(coefs, seed=91)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While fitting the one-lag kernel for cell11, two cells fell out of the usable range (coefficient 0.141, stderr 0.036, n = 39). While checking residual autocorrelation for cell10, nothing in the figure changed at print size (coefficient 0.133, stderr 0.028, n = 41). While checking residual autocorrelation for cell20, the CI narrowed by roughly a tenth (coefficient 0.300, stderr 0.050, n = 40). Flagging it so it does not get rediscovered next week.

While re-running with a tighter segmentation threshold for cell16, two cells fell out of the usable range (coefficient 0.255, stderr 0.031, n = 41). While comparing per-cell orderings for cell21, the coefficient tracked epoch count more closely than duration (coefficient 0.110, stderr 0.028, n = 58). While checking residual autocorrelation for cell05, nothing in the figure changed at print size (coefficient 0.150, stderr 0.037, n = 48). While re-exporting the raw traces for cell21, nothing in the figure changed at print size (coefficient 0.226, stderr 0.041, n = 48). While checking residual autocorrelation for cell18, the estimate moved less than one standard error (coefficient 0.144, stderr 0.049, n = 40).

### Step 27: fitting the one-lag kernel

While auditing the holding potential column for cell05, the estimate moved less than one standard error (coefficient 0.268, stderr 0.015, n = 54). While re-exporting the raw traces for cell21, nothing in the figure changed at print size (coefficient 0.256, stderr 0.042, n = 42). While re-exporting the raw traces for cell23, the coefficient tracked epoch count more closely than duration (coefficient 0.122, stderr 0.037, n = 51). While bootstrapping the CI for cell02, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.195, stderr 0.023, n = 38).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell12    0.215  0.036   0.144  0.286  56        1000
cell11    0.284  0.011   0.263  0.306  42        500
cell20    0.087  0.035   0.018  0.156  41        1000
cell15    0.085  0.029   0.028  0.141  49        1000
cell15    0.239  0.012   0.215  0.263  58        1000
cell22    0.098  0.018   0.063  0.133  47        500
cell10    0.224  0.019   0.187  0.261  51        1000
cell24    0.152  0.031   0.092  0.212  54        500
cell14    0.188  0.011   0.167  0.209  43        2000
cell12    0.128  0.047   0.037  0.219  46        2000
cell22    0.256  0.035   0.187  0.325  46        1000
cell04    0.126  0.038   0.052  0.200  45        1000
```

While bootstrapping the CI for cell06, nothing in the figure changed at print size (coefficient 0.222, stderr 0.017, n = 51). While bootstrapping the CI for cell19, two cells fell out of the usable range (coefficient 0.178, stderr 0.044, n = 40). While checking residual autocorrelation for cell08, two cells fell out of the usable range (coefficient 0.114, stderr 0.033, n = 52). This is the part that will need a real statistical argument.

While re-running with a tighter segmentation threshold for cell15, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.276, stderr 0.022, n = 44). While re-exporting the raw traces for cell11, the estimate moved less than one standard error (coefficient 0.161, stderr 0.049, n = 58). While segmenting epochs for cell01, the CI narrowed by roughly a tenth (coefficient 0.158, stderr 0.041, n = 42). While comparing per-cell orderings for cell22, nothing in the figure changed at print size (coefficient 0.185, stderr 0.023, n = 50). While re-exporting the raw traces for cell01, the coefficient tracked epoch count more closely than duration (coefficient 0.221, stderr 0.024, n = 53). While segmenting epochs for cell09, two cells fell out of the usable range (coefficient 0.306, stderr 0.039, n = 49).

### Step 28: comparing per-cell orderings

While bootstrapping the CI for cell23, the estimate moved less than one standard error (coefficient 0.152, stderr 0.035, n = 53). While bootstrapping the CI for cell01, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.086, stderr 0.043, n = 41). While segmenting epochs for cell01, nothing in the figure changed at print size (coefficient 0.284, stderr 0.049, n = 46).

While re-running with a tighter segmentation threshold for cell06, the estimate moved less than one standard error (coefficient 0.271, stderr 0.018, n = 43). While segmenting epochs for cell13, the CI narrowed by roughly a tenth (coefficient 0.259, stderr 0.047, n = 40). While re-exporting the raw traces for cell13, two cells fell out of the usable range (coefficient 0.219, stderr 0.041, n = 53). While fitting the one-lag kernel for cell22, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.228, stderr 0.044, n = 53). While auditing the holding potential column for cell10, nothing in the figure changed at print size (coefficient 0.253, stderr 0.027, n = 43).

While checking residual autocorrelation for cell21, the estimate moved less than one standard error (coefficient 0.121, stderr 0.019, n = 56). While fitting the one-lag kernel for cell13, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.082, stderr 0.048, n = 52). While re-exporting the raw traces for cell10, nothing in the figure changed at print size (coefficient 0.247, stderr 0.039, n = 56). While re-exporting the raw traces for cell12, the CI narrowed by roughly a tenth (coefficient 0.082, stderr 0.038, n = 49). While auditing the holding potential column for cell20, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.179, stderr 0.048, n = 43). While re-running with a tighter segmentation threshold for cell01, two cells fell out of the usable range (coefficient 0.084, stderr 0.010, n = 41).

While re-exporting the raw traces for cell10, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.288, stderr 0.033, n = 47). While auditing the holding potential column for cell21, the estimate moved less than one standard error (coefficient 0.081, stderr 0.029, n = 53). While auditing the holding potential column for cell22, nothing in the figure changed at print size (coefficient 0.179, stderr 0.027, n = 55). While bootstrapping the CI for cell11, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.309, stderr 0.030, n = 44). Parking this until the re-segmentation lands.

### Step 29: comparing per-cell orderings

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell08    0.088  0.037   0.015  0.161  58        2000
cell06    0.221  0.020   0.181  0.260  55        2000
cell16    0.180  0.024   0.134  0.227  48        500
cell10    0.220  0.028   0.165  0.275  46        1000
cell02    0.153  0.019   0.116  0.190  56        2000
cell14    0.292  0.012   0.268  0.316  56        1000
cell05    0.216  0.022   0.173  0.259  54        1000
cell01    0.100  0.043   0.016  0.184  40        2000
cell09    0.124  0.021   0.082  0.165  54        500
cell08    0.166  0.028   0.112  0.220  40        1000
cell19    0.289  0.011   0.267  0.311  41        500
cell17    0.222  0.038   0.147  0.297  42        2000
cell03    0.094  0.016   0.063  0.125  52        1000
cell14    0.288  0.027   0.235  0.340  49        2000
```

While bootstrapping the CI for cell07, nothing in the figure changed at print size (coefficient 0.147, stderr 0.043, n = 55). While comparing per-cell orderings for cell19, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.210, stderr 0.038, n = 45). While bootstrapping the CI for cell22, nothing in the figure changed at print size (coefficient 0.308, stderr 0.026, n = 40). While auditing the holding potential column for cell15, the ordering of cells was preserved (coefficient 0.101, stderr 0.014, n = 39). While comparing per-cell orderings for cell04, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.102, stderr 0.031, n = 54). While re-exporting the raw traces for cell12, the CI narrowed by roughly a tenth (coefficient 0.310, stderr 0.030, n = 40). Parking this until the re-segmentation lands.

### Step 30: re-running with a tighter segmentation threshold

```python
coefs = fit_per_cell(rows, threshold=0.67)
lo, hi = ci(coefs, seed=77)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While comparing per-cell orderings for cell21, the ordering of cells was preserved (coefficient 0.265, stderr 0.021, n = 40). While re-exporting the raw traces for cell19, two cells fell out of the usable range (coefficient 0.099, stderr 0.021, n = 55). While auditing the holding potential column for cell04, nothing in the figure changed at print size (coefficient 0.201, stderr 0.019, n = 38). While re-running with a tighter segmentation threshold for cell21, two cells fell out of the usable range (coefficient 0.281, stderr 0.044, n = 54). While comparing per-cell orderings for cell11, two cells fell out of the usable range (coefficient 0.099, stderr 0.011, n = 38).

While auditing the holding potential column for cell10, the coefficient tracked epoch count more closely than duration (coefficient 0.232, stderr 0.030, n = 51). While auditing the holding potential column for cell05, the ordering of cells was preserved (coefficient 0.186, stderr 0.017, n = 50). While re-running with a tighter segmentation threshold for cell17, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.152, stderr 0.015, n = 40). While re-running with a tighter segmentation threshold for cell15, the CI narrowed by roughly a tenth (coefficient 0.171, stderr 0.017, n = 52). While re-running with a tighter segmentation threshold for cell04, the estimate moved less than one standard error (coefficient 0.145, stderr 0.048, n = 47).

While comparing per-cell orderings for cell19, two cells fell out of the usable range (coefficient 0.199, stderr 0.028, n = 42). While checking residual autocorrelation for cell02, two cells fell out of the usable range (coefficient 0.213, stderr 0.023, n = 57). While re-running with a tighter segmentation threshold for cell18, the ordering of cells was preserved (coefficient 0.095, stderr 0.036, n = 43). While checking residual autocorrelation for cell19, nothing in the figure changed at print size (coefficient 0.227, stderr 0.050, n = 48). This is the part that will need a real statistical argument.

### Step 31: bootstrapping the CI

While auditing the holding potential column for cell14, the ordering of cells was preserved (coefficient 0.188, stderr 0.027, n = 43). While segmenting epochs for cell02, nothing in the figure changed at print size (coefficient 0.244, stderr 0.017, n = 43). While auditing the holding potential column for cell11, two cells fell out of the usable range (coefficient 0.215, stderr 0.016, n = 43). While comparing per-cell orderings for cell06, nothing in the figure changed at print size (coefficient 0.222, stderr 0.016, n = 42).

While bootstrapping the CI for cell06, nothing in the figure changed at print size (coefficient 0.176, stderr 0.037, n = 47). While re-exporting the raw traces for cell16, the estimate moved less than one standard error (coefficient 0.097, stderr 0.015, n = 40). While bootstrapping the CI for cell13, the coefficient tracked epoch count more closely than duration (coefficient 0.093, stderr 0.013, n = 42). While auditing the holding potential column for cell15, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.120, stderr 0.045, n = 57). While bootstrapping the CI for cell03, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.187, stderr 0.025, n = 53).

### Step 32: segmenting epochs

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell06    0.308  0.029   0.252  0.365  49        2000
cell13    0.168  0.030   0.110  0.226  51        1000
cell22    0.235  0.019   0.198  0.272  50        1000
cell08    0.156  0.041   0.076  0.235  46        1000
cell09    0.185  0.026   0.134  0.235  49        2000
cell22    0.082  0.017   0.048  0.115  52        4000
cell21    0.250  0.041   0.170  0.329  42        1000
cell12    0.112  0.030   0.054  0.171  39        500
cell20    0.262  0.021   0.221  0.304  45        500
cell15    0.278  0.044   0.191  0.364  53        500
cell06    0.252  0.032   0.189  0.316  51        500
cell21    0.168  0.037   0.096  0.240  38        500
cell24    0.199  0.037   0.126  0.272  56        4000
```

While re-running with a tighter segmentation threshold for cell19, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.158, stderr 0.022, n = 49). While checking residual autocorrelation for cell24, the coefficient tracked epoch count more closely than duration (coefficient 0.133, stderr 0.026, n = 56). While auditing the holding potential column for cell11, nothing in the figure changed at print size (coefficient 0.286, stderr 0.047, n = 39). While bootstrapping the CI for cell17, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.233, stderr 0.011, n = 54). Parking this until the re-segmentation lands.

```python
coefs = fit_per_cell(rows, threshold=0.53)
lo, hi = ci(coefs, seed=90)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While fitting the one-lag kernel for cell02, the estimate moved less than one standard error (coefficient 0.275, stderr 0.024, n = 44). While comparing per-cell orderings for cell10, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.228, stderr 0.011, n = 41). While re-running with a tighter segmentation threshold for cell06, the CI narrowed by roughly a tenth (coefficient 0.268, stderr 0.028, n = 46). While checking residual autocorrelation for cell21, the coefficient tracked epoch count more closely than duration (coefficient 0.171, stderr 0.026, n = 54). While fitting the one-lag kernel for cell10, nothing in the figure changed at print size (coefficient 0.250, stderr 0.043, n = 53). While checking residual autocorrelation for cell18, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.108, stderr 0.027, n = 43). Worth noting for the writeup, though not a result on its own.

### Step 33: comparing per-cell orderings

While auditing the holding potential column for cell12, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.280, stderr 0.026, n = 45). While bootstrapping the CI for cell12, the coefficient tracked epoch count more closely than duration (coefficient 0.203, stderr 0.034, n = 43). While segmenting epochs for cell10, the CI narrowed by roughly a tenth (coefficient 0.254, stderr 0.037, n = 58). While re-running with a tighter segmentation threshold for cell15, the coefficient tracked epoch count more closely than duration (coefficient 0.208, stderr 0.035, n = 49). While checking residual autocorrelation for cell17, the estimate moved less than one standard error (coefficient 0.274, stderr 0.021, n = 57). While segmenting epochs for cell12, the coefficient tracked epoch count more closely than duration (coefficient 0.290, stderr 0.049, n = 48).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell10    0.241  0.041   0.162  0.321  54        1000
cell21    0.244  0.011   0.222  0.267  55        500
cell08    0.237  0.030   0.178  0.296  39        500
cell16    0.288  0.028   0.234  0.343  53        2000
cell07    0.197  0.012   0.173  0.220  51        1000
cell03    0.307  0.040   0.229  0.384  41        1000
cell02    0.132  0.041   0.051  0.213  41        500
cell13    0.146  0.028   0.091  0.201  53        500
cell09    0.243  0.014   0.216  0.270  46        1000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell03    0.289  0.026   0.238  0.340  52        1000
cell12    0.111  0.048   0.018  0.204  45        2000
cell19    0.221  0.030   0.162  0.280  41        2000
cell10    0.106  0.026   0.055  0.157  49        500
cell05    0.298  0.023   0.254  0.343  56        2000
cell02    0.147  0.045   0.059  0.235  46        500
```

### Step 34: checking residual autocorrelation

While re-exporting the raw traces for cell07, the coefficient tracked epoch count more closely than duration (coefficient 0.123, stderr 0.021, n = 47). While bootstrapping the CI for cell11, two cells fell out of the usable range (coefficient 0.265, stderr 0.048, n = 54). While comparing per-cell orderings for cell07, the estimate moved less than one standard error (coefficient 0.309, stderr 0.018, n = 48). While auditing the holding potential column for cell13, the CI narrowed by roughly a tenth (coefficient 0.199, stderr 0.048, n = 42). While comparing per-cell orderings for cell08, the estimate moved less than one standard error (coefficient 0.157, stderr 0.011, n = 46). While segmenting epochs for cell22, the ordering of cells was preserved (coefficient 0.204, stderr 0.033, n = 41). Parking this until the re-segmentation lands.

While re-running with a tighter segmentation threshold for cell15, two cells fell out of the usable range (coefficient 0.228, stderr 0.030, n = 53). While bootstrapping the CI for cell13, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.268, stderr 0.046, n = 46). While fitting the one-lag kernel for cell15, the ordering of cells was preserved (coefficient 0.211, stderr 0.033, n = 41).

While segmenting epochs for cell17, the coefficient tracked epoch count more closely than duration (coefficient 0.169, stderr 0.033, n = 42). While re-running with a tighter segmentation threshold for cell22, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.170, stderr 0.014, n = 55). While comparing per-cell orderings for cell19, nothing in the figure changed at print size (coefficient 0.222, stderr 0.031, n = 53). This is the part that will need a real statistical argument.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell03    0.202  0.012   0.179  0.226  40        2000
cell02    0.261  0.034   0.194  0.328  51        500
cell20    0.284  0.022   0.241  0.328  51        4000
cell17    0.250  0.036   0.179  0.321  44        4000
cell11    0.256  0.040   0.178  0.334  51        4000
cell03    0.265  0.035   0.197  0.334  50        2000
cell11    0.157  0.010   0.137  0.178  48        1000
cell22    0.187  0.018   0.152  0.222  46        2000
cell06    0.283  0.048   0.190  0.376  47        2000
cell05    0.179  0.032   0.116  0.243  49        1000
cell06    0.118  0.040   0.039  0.197  53        2000
cell10    0.131  0.033   0.065  0.196  57        1000
```

### Step 35: fitting the one-lag kernel

```python
coefs = fit_per_cell(rows, threshold=0.53)
lo, hi = ci(coefs, seed=84)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```python
coefs = fit_per_cell(rows, threshold=0.77)
lo, hi = ci(coefs, seed=49)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 36: auditing the holding potential column

While segmenting epochs for cell13, the estimate moved less than one standard error (coefficient 0.127, stderr 0.048, n = 43). While auditing the holding potential column for cell01, the ordering of cells was preserved (coefficient 0.087, stderr 0.046, n = 38). While auditing the holding potential column for cell04, nothing in the figure changed at print size (coefficient 0.286, stderr 0.011, n = 49). Flagging it so it does not get rediscovered next week.

While comparing per-cell orderings for cell15, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.213, stderr 0.044, n = 52). While bootstrapping the CI for cell13, two cells fell out of the usable range (coefficient 0.261, stderr 0.045, n = 45). While re-exporting the raw traces for cell24, nothing in the figure changed at print size (coefficient 0.187, stderr 0.021, n = 40). While comparing per-cell orderings for cell18, the estimate moved less than one standard error (coefficient 0.260, stderr 0.019, n = 53). While bootstrapping the CI for cell20, the coefficient tracked epoch count more closely than duration (coefficient 0.264, stderr 0.029, n = 48). While bootstrapping the CI for cell13, the estimate moved less than one standard error (coefficient 0.195, stderr 0.017, n = 51).

```python
coefs = fit_per_cell(rows, threshold=0.36)
lo, hi = ci(coefs, seed=61)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 37: checking residual autocorrelation

```python
coefs = fit_per_cell(rows, threshold=0.38)
lo, hi = ci(coefs, seed=7)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While segmenting epochs for cell09, the CI narrowed by roughly a tenth (coefficient 0.242, stderr 0.023, n = 58). While fitting the one-lag kernel for cell22, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.123, stderr 0.040, n = 40). While fitting the one-lag kernel for cell05, the coefficient tracked epoch count more closely than duration (coefficient 0.200, stderr 0.017, n = 49). While fitting the one-lag kernel for cell14, nothing in the figure changed at print size (coefficient 0.200, stderr 0.025, n = 58). While segmenting epochs for cell06, two cells fell out of the usable range (coefficient 0.238, stderr 0.030, n = 55). While comparing per-cell orderings for cell04, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.158, stderr 0.046, n = 44).

While comparing per-cell orderings for cell16, the estimate moved less than one standard error (coefficient 0.227, stderr 0.010, n = 42). While re-running with a tighter segmentation threshold for cell13, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.239, stderr 0.040, n = 52). While bootstrapping the CI for cell11, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.228, stderr 0.021, n = 44). Parking this until the re-segmentation lands.

While checking residual autocorrelation for cell06, the coefficient tracked epoch count more closely than duration (coefficient 0.237, stderr 0.025, n = 58). While bootstrapping the CI for cell21, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.126, stderr 0.039, n = 55). While re-running with a tighter segmentation threshold for cell16, the CI narrowed by roughly a tenth (coefficient 0.176, stderr 0.033, n = 39).

