# Prior session 1 of 20

Transcript of an earlier working session on the history-kernel analysis.

### Step 1: comparing per-cell orderings

```python
coefs = fit_per_cell(rows, threshold=0.72)
lo, hi = ci(coefs, seed=37)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While re-exporting the raw traces for cell16, the estimate moved less than one standard error (coefficient 0.096, stderr 0.034, n = 55). While checking residual autocorrelation for cell15, the ordering of cells was preserved (coefficient 0.214, stderr 0.032, n = 38). While segmenting epochs for cell03, the ordering of cells was preserved (coefficient 0.145, stderr 0.048, n = 52).

While comparing per-cell orderings for cell08, the ordering of cells was preserved (coefficient 0.251, stderr 0.046, n = 41). While auditing the holding potential column for cell16, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.190, stderr 0.048, n = 55). While re-running with a tighter segmentation threshold for cell05, two cells fell out of the usable range (coefficient 0.229, stderr 0.039, n = 54). This is the part that will need a real statistical argument.

### Step 2: re-running with a tighter segmentation threshold

While segmenting epochs for cell24, the CI narrowed by roughly a tenth (coefficient 0.270, stderr 0.035, n = 48). While auditing the holding potential column for cell09, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.223, stderr 0.016, n = 55). While bootstrapping the CI for cell05, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.309, stderr 0.043, n = 47). While auditing the holding potential column for cell08, the ordering of cells was preserved (coefficient 0.089, stderr 0.036, n = 47). While bootstrapping the CI for cell13, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.181, stderr 0.041, n = 49).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell09    0.292  0.025   0.243  0.341  51        2000
cell23    0.141  0.022   0.098  0.184  47        1000
cell17    0.184  0.045   0.097  0.271  54        1000
cell22    0.298  0.029   0.241  0.356  50        2000
cell16    0.232  0.030   0.172  0.291  46        4000
cell14    0.302  0.023   0.257  0.346  38        1000
cell20    0.187  0.025   0.138  0.236  42        4000
```

While bootstrapping the CI for cell04, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.231, stderr 0.029, n = 54). While segmenting epochs for cell17, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.097, stderr 0.050, n = 52). While bootstrapping the CI for cell20, the estimate moved less than one standard error (coefficient 0.089, stderr 0.038, n = 51). While checking residual autocorrelation for cell15, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.093, stderr 0.035, n = 50). While bootstrapping the CI for cell23, the ordering of cells was preserved (coefficient 0.174, stderr 0.031, n = 40).

### Step 3: fitting the one-lag kernel

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell08    0.302  0.014   0.275  0.329  50        2000
cell13    0.200  0.046   0.109  0.291  44        500
cell19    0.088  0.040   0.010  0.166  50        2000
cell11    0.296  0.041   0.217  0.376  43        4000
cell18    0.194  0.016   0.163  0.225  44        4000
cell20    0.277  0.034   0.210  0.344  56        500
cell01    0.121  0.035   0.053  0.189  55        500
```

While checking residual autocorrelation for cell02, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.180, stderr 0.040, n = 53). While checking residual autocorrelation for cell06, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.259, stderr 0.016, n = 50). While segmenting epochs for cell02, the estimate moved less than one standard error (coefficient 0.222, stderr 0.050, n = 53). While re-running with a tighter segmentation threshold for cell07, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.133, stderr 0.011, n = 58).

### Step 4: re-exporting the raw traces

While re-running with a tighter segmentation threshold for cell16, the CI narrowed by roughly a tenth (coefficient 0.138, stderr 0.039, n = 46). While re-exporting the raw traces for cell07, the estimate moved less than one standard error (coefficient 0.187, stderr 0.035, n = 39). While comparing per-cell orderings for cell18, the coefficient tracked epoch count more closely than duration (coefficient 0.289, stderr 0.018, n = 51).

While checking residual autocorrelation for cell24, the estimate moved less than one standard error (coefficient 0.281, stderr 0.038, n = 47). While segmenting epochs for cell20, the CI narrowed by roughly a tenth (coefficient 0.228, stderr 0.034, n = 48). While comparing per-cell orderings for cell23, the CI narrowed by roughly a tenth (coefficient 0.173, stderr 0.014, n = 41). While auditing the holding potential column for cell16, two cells fell out of the usable range (coefficient 0.107, stderr 0.041, n = 58). While fitting the one-lag kernel for cell12, the estimate moved less than one standard error (coefficient 0.277, stderr 0.045, n = 51). While checking residual autocorrelation for cell11, the coefficient tracked epoch count more closely than duration (coefficient 0.208, stderr 0.040, n = 43).

While checking residual autocorrelation for cell08, the ordering of cells was preserved (coefficient 0.240, stderr 0.046, n = 51). While segmenting epochs for cell03, nothing in the figure changed at print size (coefficient 0.188, stderr 0.040, n = 38). While checking residual autocorrelation for cell15, the CI narrowed by roughly a tenth (coefficient 0.127, stderr 0.039, n = 47). While bootstrapping the CI for cell23, the ordering of cells was preserved (coefficient 0.181, stderr 0.044, n = 58). While fitting the one-lag kernel for cell18, two cells fell out of the usable range (coefficient 0.087, stderr 0.019, n = 42). While checking residual autocorrelation for cell22, the coefficient tracked epoch count more closely than duration (coefficient 0.187, stderr 0.033, n = 45).

### Step 5: auditing the holding potential column

While comparing per-cell orderings for cell20, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.267, stderr 0.011, n = 48). While checking residual autocorrelation for cell06, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.302, stderr 0.022, n = 58). While auditing the holding potential column for cell20, nothing in the figure changed at print size (coefficient 0.230, stderr 0.015, n = 39). While re-exporting the raw traces for cell02, the ordering of cells was preserved (coefficient 0.212, stderr 0.025, n = 42).

While auditing the holding potential column for cell11, nothing in the figure changed at print size (coefficient 0.175, stderr 0.018, n = 47). While segmenting epochs for cell15, the ordering of cells was preserved (coefficient 0.269, stderr 0.031, n = 57). While checking residual autocorrelation for cell21, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.288, stderr 0.037, n = 38). While segmenting epochs for cell22, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.228, stderr 0.021, n = 44). This is the part that will need a real statistical argument.

While bootstrapping the CI for cell11, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.089, stderr 0.011, n = 56). While re-running with a tighter segmentation threshold for cell04, the estimate moved less than one standard error (coefficient 0.251, stderr 0.022, n = 54). While auditing the holding potential column for cell15, the estimate moved less than one standard error (coefficient 0.233, stderr 0.026, n = 40). While segmenting epochs for cell12, the ordering of cells was preserved (coefficient 0.134, stderr 0.018, n = 58). While re-running with a tighter segmentation threshold for cell24, the coefficient tracked epoch count more closely than duration (coefficient 0.134, stderr 0.012, n = 38).

### Step 6: fitting the one-lag kernel

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell24    0.176  0.046   0.086  0.266  44        4000
cell10    0.298  0.025   0.249  0.346  40        1000
cell11    0.224  0.018   0.188  0.260  47        2000
cell16    0.291  0.026   0.241  0.342  57        4000
cell14    0.290  0.036   0.219  0.360  51        4000
cell05    0.298  0.020   0.260  0.336  45        500
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell20    0.228  0.018   0.192  0.263  47        2000
cell13    0.112  0.019   0.074  0.149  52        1000
cell08    0.146  0.048   0.052  0.240  45        1000
cell06    0.146  0.015   0.116  0.176  58        4000
cell21    0.199  0.023   0.154  0.245  57        4000
cell14    0.128  0.037   0.056  0.199  56        1000
```

While checking residual autocorrelation for cell16, the ordering of cells was preserved (coefficient 0.110, stderr 0.046, n = 56). While fitting the one-lag kernel for cell18, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.205, stderr 0.029, n = 55). While auditing the holding potential column for cell05, nothing in the figure changed at print size (coefficient 0.204, stderr 0.011, n = 38).

While re-running with a tighter segmentation threshold for cell09, the ordering of cells was preserved (coefficient 0.214, stderr 0.016, n = 51). While segmenting epochs for cell06, the estimate moved less than one standard error (coefficient 0.241, stderr 0.035, n = 46). While checking residual autocorrelation for cell17, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.267, stderr 0.015, n = 47). While auditing the holding potential column for cell06, two cells fell out of the usable range (coefficient 0.279, stderr 0.016, n = 49). While segmenting epochs for cell22, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.131, stderr 0.022, n = 57). While segmenting epochs for cell16, nothing in the figure changed at print size (coefficient 0.259, stderr 0.047, n = 53).

### Step 7: comparing per-cell orderings

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell22    0.230  0.020   0.192  0.268  48        2000
cell21    0.239  0.048   0.145  0.333  51        2000
cell18    0.172  0.011   0.151  0.193  44        2000
cell02    0.274  0.040   0.196  0.352  53        2000
cell15    0.254  0.046   0.164  0.345  52        4000
cell07    0.233  0.028   0.177  0.289  48        1000
cell12    0.213  0.011   0.193  0.234  42        2000
cell16    0.247  0.043   0.163  0.330  39        2000
cell15    0.166  0.020   0.127  0.204  45        1000
cell10    0.087  0.037   0.014  0.160  55        4000
cell01    0.273  0.019   0.237  0.310  42        500
```

While comparing per-cell orderings for cell23, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.224, stderr 0.040, n = 47). While comparing per-cell orderings for cell16, the coefficient tracked epoch count more closely than duration (coefficient 0.144, stderr 0.021, n = 49). While auditing the holding potential column for cell08, the CI narrowed by roughly a tenth (coefficient 0.168, stderr 0.018, n = 41). While segmenting epochs for cell10, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.289, stderr 0.047, n = 46).

While fitting the one-lag kernel for cell22, the coefficient tracked epoch count more closely than duration (coefficient 0.166, stderr 0.024, n = 53). While fitting the one-lag kernel for cell22, two cells fell out of the usable range (coefficient 0.211, stderr 0.047, n = 42). While comparing per-cell orderings for cell22, the estimate moved less than one standard error (coefficient 0.249, stderr 0.012, n = 56). While segmenting epochs for cell02, the ordering of cells was preserved (coefficient 0.272, stderr 0.029, n = 44). While segmenting epochs for cell06, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.263, stderr 0.044, n = 56). While re-exporting the raw traces for cell14, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.278, stderr 0.020, n = 46).

### Step 8: auditing the holding potential column

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell07    0.238  0.021   0.196  0.280  38        500
cell04    0.236  0.018   0.201  0.271  49        2000
cell05    0.175  0.018   0.139  0.210  57        500
cell03    0.134  0.011   0.112  0.156  45        4000
cell02    0.198  0.042   0.115  0.281  49        2000
cell17    0.308  0.044   0.223  0.394  46        2000
cell22    0.135  0.027   0.082  0.187  49        4000
cell02    0.135  0.013   0.109  0.161  51        1000
cell08    0.101  0.044   0.015  0.187  46        2000
cell13    0.220  0.040   0.142  0.298  55        1000
cell22    0.244  0.045   0.156  0.332  39        500
cell13    0.230  0.012   0.206  0.253  41        4000
```

While auditing the holding potential column for cell21, the coefficient tracked epoch count more closely than duration (coefficient 0.179, stderr 0.043, n = 50). While re-running with a tighter segmentation threshold for cell24, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.193, stderr 0.015, n = 39). While fitting the one-lag kernel for cell14, the ordering of cells was preserved (coefficient 0.199, stderr 0.042, n = 52). While auditing the holding potential column for cell22, two cells fell out of the usable range (coefficient 0.134, stderr 0.030, n = 54). While re-running with a tighter segmentation threshold for cell23, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.259, stderr 0.047, n = 48).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell15    0.229  0.025   0.181  0.277  44        4000
cell14    0.105  0.031   0.044  0.165  50        1000
cell22    0.286  0.024   0.239  0.332  58        1000
cell08    0.289  0.050   0.191  0.387  50        2000
cell02    0.223  0.024   0.177  0.270  55        1000
cell08    0.160  0.028   0.106  0.215  58        1000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell06    0.228  0.014   0.200  0.256  53        2000
cell13    0.206  0.046   0.115  0.297  46        4000
cell18    0.114  0.041   0.034  0.195  39        500
cell02    0.155  0.028   0.100  0.211  39        500
cell20    0.157  0.022   0.114  0.201  55        1000
cell02    0.290  0.044   0.205  0.376  48        1000
cell14    0.248  0.043   0.164  0.333  44        1000
cell18    0.142  0.018   0.107  0.177  41        500
cell07    0.183  0.023   0.138  0.229  39        2000
```

### Step 9: bootstrapping the CI

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell03    0.242  0.050   0.144  0.339  55        2000
cell05    0.253  0.026   0.202  0.305  43        4000
cell08    0.286  0.046   0.196  0.376  47        1000
cell10    0.111  0.048   0.017  0.205  46        1000
cell10    0.236  0.030   0.177  0.296  54        1000
cell11    0.164  0.012   0.139  0.188  58        4000
cell15    0.211  0.013   0.186  0.235  58        4000
cell16    0.274  0.043   0.190  0.358  41        2000
cell10    0.258  0.035   0.189  0.326  49        1000
cell07    0.200  0.040   0.121  0.278  43        4000
cell16    0.090  0.044   0.004  0.176  56        4000
cell06    0.081  0.041   -0.000  0.162  43        4000
```

While re-exporting the raw traces for cell16, the estimate moved less than one standard error (coefficient 0.082, stderr 0.025, n = 55). While checking residual autocorrelation for cell18, the ordering of cells was preserved (coefficient 0.304, stderr 0.022, n = 58). While segmenting epochs for cell13, the CI narrowed by roughly a tenth (coefficient 0.119, stderr 0.034, n = 56). While fitting the one-lag kernel for cell14, the estimate moved less than one standard error (coefficient 0.282, stderr 0.047, n = 46).

While re-exporting the raw traces for cell03, the ordering of cells was preserved (coefficient 0.095, stderr 0.019, n = 44). While comparing per-cell orderings for cell22, the ordering of cells was preserved (coefficient 0.238, stderr 0.019, n = 42). While segmenting epochs for cell18, the estimate moved less than one standard error (coefficient 0.215, stderr 0.048, n = 55). While checking residual autocorrelation for cell02, two cells fell out of the usable range (coefficient 0.256, stderr 0.015, n = 46). While fitting the one-lag kernel for cell22, the CI narrowed by roughly a tenth (coefficient 0.150, stderr 0.036, n = 39). While bootstrapping the CI for cell08, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.114, stderr 0.044, n = 42). Worth noting for the writeup, though not a result on its own.

While re-running with a tighter segmentation threshold for cell18, the CI narrowed by roughly a tenth (coefficient 0.099, stderr 0.016, n = 44). While auditing the holding potential column for cell22, nothing in the figure changed at print size (coefficient 0.150, stderr 0.040, n = 44). While checking residual autocorrelation for cell18, the estimate moved less than one standard error (coefficient 0.289, stderr 0.029, n = 45). While fitting the one-lag kernel for cell22, the ordering of cells was preserved (coefficient 0.249, stderr 0.028, n = 55). While bootstrapping the CI for cell17, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.133, stderr 0.048, n = 43). Parking this until the re-segmentation lands.

### Step 10: re-exporting the raw traces

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell01    0.190  0.041   0.110  0.271  41        500
cell05    0.159  0.039   0.083  0.235  55        4000
cell12    0.102  0.027   0.050  0.155  44        4000
cell07    0.104  0.046   0.013  0.194  47        2000
cell15    0.195  0.015   0.165  0.225  53        2000
cell08    0.114  0.040   0.036  0.191  55        1000
cell11    0.265  0.039   0.189  0.341  48        4000
cell04    0.203  0.023   0.158  0.248  55        2000
cell10    0.223  0.012   0.200  0.246  40        2000
cell15    0.301  0.012   0.278  0.324  41        2000
cell09    0.155  0.036   0.083  0.226  41        1000
cell12    0.187  0.035   0.118  0.257  39        500
cell22    0.295  0.011   0.273  0.316  55        1000
```

```python
coefs = fit_per_cell(rows, threshold=0.49)
lo, hi = ci(coefs, seed=85)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell11    0.226  0.029   0.170  0.283  55        4000
cell24    0.100  0.019   0.063  0.137  48        4000
cell18    0.131  0.020   0.091  0.170  52        500
cell10    0.308  0.018   0.273  0.343  40        500
cell24    0.104  0.038   0.029  0.178  49        1000
cell09    0.298  0.027   0.245  0.351  55        500
cell02    0.309  0.048   0.214  0.403  56        2000
cell21    0.246  0.031   0.186  0.305  51        4000
cell15    0.192  0.038   0.118  0.266  40        500
cell14    0.220  0.029   0.164  0.276  45        2000
```

While fitting the one-lag kernel for cell14, the coefficient tracked epoch count more closely than duration (coefficient 0.139, stderr 0.036, n = 43). While re-exporting the raw traces for cell09, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.140, stderr 0.021, n = 53). While bootstrapping the CI for cell03, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.135, stderr 0.043, n = 38). Flagging it so it does not get rediscovered next week.

### Step 11: bootstrapping the CI

While segmenting epochs for cell02, the CI narrowed by roughly a tenth (coefficient 0.129, stderr 0.042, n = 55). While comparing per-cell orderings for cell13, nothing in the figure changed at print size (coefficient 0.092, stderr 0.044, n = 56). While checking residual autocorrelation for cell22, two cells fell out of the usable range (coefficient 0.159, stderr 0.022, n = 47). While comparing per-cell orderings for cell01, nothing in the figure changed at print size (coefficient 0.310, stderr 0.046, n = 51). While checking residual autocorrelation for cell01, nothing in the figure changed at print size (coefficient 0.230, stderr 0.045, n = 56). Flagging it so it does not get rediscovered next week.

While fitting the one-lag kernel for cell15, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.256, stderr 0.038, n = 40). While bootstrapping the CI for cell24, two cells fell out of the usable range (coefficient 0.121, stderr 0.033, n = 42). While re-running with a tighter segmentation threshold for cell11, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.296, stderr 0.018, n = 40). While re-exporting the raw traces for cell01, two cells fell out of the usable range (coefficient 0.130, stderr 0.015, n = 52). While bootstrapping the CI for cell13, the coefficient tracked epoch count more closely than duration (coefficient 0.160, stderr 0.025, n = 45).

### Step 12: auditing the holding potential column

```python
coefs = fit_per_cell(rows, threshold=0.56)
lo, hi = ci(coefs, seed=41)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While auditing the holding potential column for cell06, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.133, stderr 0.039, n = 53). While re-exporting the raw traces for cell08, the coefficient tracked epoch count more closely than duration (coefficient 0.081, stderr 0.024, n = 46). While re-exporting the raw traces for cell22, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.089, stderr 0.025, n = 53).

While segmenting epochs for cell21, the coefficient tracked epoch count more closely than duration (coefficient 0.171, stderr 0.028, n = 49). While fitting the one-lag kernel for cell02, nothing in the figure changed at print size (coefficient 0.268, stderr 0.036, n = 40). While re-running with a tighter segmentation threshold for cell14, the coefficient tracked epoch count more closely than duration (coefficient 0.287, stderr 0.039, n = 43).

### Step 13: checking residual autocorrelation

While re-running with a tighter segmentation threshold for cell13, the ordering of cells was preserved (coefficient 0.232, stderr 0.037, n = 54). While bootstrapping the CI for cell10, the CI narrowed by roughly a tenth (coefficient 0.130, stderr 0.028, n = 57). While comparing per-cell orderings for cell24, the CI narrowed by roughly a tenth (coefficient 0.129, stderr 0.022, n = 40).

While re-running with a tighter segmentation threshold for cell12, the ordering of cells was preserved (coefficient 0.224, stderr 0.028, n = 57). While auditing the holding potential column for cell11, the estimate moved less than one standard error (coefficient 0.217, stderr 0.030, n = 44). While segmenting epochs for cell24, the coefficient tracked epoch count more closely than duration (coefficient 0.178, stderr 0.030, n = 55). While bootstrapping the CI for cell02, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.081, stderr 0.048, n = 40). While comparing per-cell orderings for cell10, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.239, stderr 0.027, n = 40).

### Step 14: auditing the holding potential column

While checking residual autocorrelation for cell07, the estimate moved less than one standard error (coefficient 0.180, stderr 0.013, n = 42). While checking residual autocorrelation for cell02, the coefficient tracked epoch count more closely than duration (coefficient 0.229, stderr 0.030, n = 57). While auditing the holding potential column for cell12, the CI narrowed by roughly a tenth (coefficient 0.127, stderr 0.040, n = 47). While segmenting epochs for cell01, the estimate moved less than one standard error (coefficient 0.092, stderr 0.041, n = 42). While bootstrapping the CI for cell21, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.180, stderr 0.018, n = 44). Parking this until the re-segmentation lands.

While fitting the one-lag kernel for cell04, nothing in the figure changed at print size (coefficient 0.274, stderr 0.019, n = 45). While segmenting epochs for cell24, the CI narrowed by roughly a tenth (coefficient 0.307, stderr 0.014, n = 39). While fitting the one-lag kernel for cell10, the CI narrowed by roughly a tenth (coefficient 0.141, stderr 0.050, n = 55). Noted and moved on; it does not change the decision.

### Step 15: fitting the one-lag kernel

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell02    0.191  0.011   0.170  0.213  41        4000
cell02    0.301  0.023   0.257  0.345  43        500
cell09    0.223  0.013   0.198  0.249  40        1000
cell17    0.274  0.028   0.220  0.329  56        1000
cell04    0.309  0.039   0.234  0.385  53        4000
cell11    0.124  0.014   0.096  0.152  50        2000
cell23    0.175  0.048   0.082  0.269  42        4000
cell21    0.139  0.037   0.066  0.211  41        1000
cell05    0.166  0.039   0.089  0.243  47        500
cell05    0.293  0.016   0.261  0.325  47        4000
cell24    0.088  0.050   -0.009  0.185  54        1000
cell23    0.110  0.032   0.047  0.173  56        2000
cell19    0.283  0.048   0.190  0.377  52        4000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell12    0.164  0.048   0.070  0.258  45        4000
cell08    0.264  0.027   0.212  0.316  48        500
cell17    0.111  0.039   0.034  0.188  42        4000
cell15    0.264  0.043   0.179  0.348  41        500
cell14    0.164  0.028   0.109  0.219  50        4000
cell11    0.200  0.041   0.119  0.281  47        1000
cell23    0.175  0.032   0.112  0.239  47        500
```

While comparing per-cell orderings for cell13, the estimate moved less than one standard error (coefficient 0.205, stderr 0.039, n = 51). While fitting the one-lag kernel for cell09, the ordering of cells was preserved (coefficient 0.123, stderr 0.047, n = 56). While re-exporting the raw traces for cell20, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.149, stderr 0.046, n = 53). While auditing the holding potential column for cell04, the coefficient tracked epoch count more closely than duration (coefficient 0.110, stderr 0.039, n = 57). While checking residual autocorrelation for cell07, the ordering of cells was preserved (coefficient 0.175, stderr 0.047, n = 57).

While checking residual autocorrelation for cell06, nothing in the figure changed at print size (coefficient 0.130, stderr 0.042, n = 47). While checking residual autocorrelation for cell24, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.106, stderr 0.036, n = 50). While re-exporting the raw traces for cell11, nothing in the figure changed at print size (coefficient 0.258, stderr 0.030, n = 58). While comparing per-cell orderings for cell01, the estimate moved less than one standard error (coefficient 0.255, stderr 0.012, n = 55). While bootstrapping the CI for cell19, the CI narrowed by roughly a tenth (coefficient 0.143, stderr 0.017, n = 50). While bootstrapping the CI for cell21, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.267, stderr 0.040, n = 47).

### Step 16: re-exporting the raw traces

While re-exporting the raw traces for cell23, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.174, stderr 0.028, n = 47). While comparing per-cell orderings for cell21, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.307, stderr 0.017, n = 51). While re-running with a tighter segmentation threshold for cell05, the coefficient tracked epoch count more closely than duration (coefficient 0.167, stderr 0.045, n = 47). While checking residual autocorrelation for cell24, the ordering of cells was preserved (coefficient 0.183, stderr 0.023, n = 51). While re-exporting the raw traces for cell13, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.120, stderr 0.018, n = 50). While re-running with a tighter segmentation threshold for cell17, nothing in the figure changed at print size (coefficient 0.257, stderr 0.017, n = 50).

While re-running with a tighter segmentation threshold for cell01, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.166, stderr 0.046, n = 38). While re-exporting the raw traces for cell13, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.227, stderr 0.010, n = 40). While re-exporting the raw traces for cell24, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.113, stderr 0.020, n = 57). While comparing per-cell orderings for cell13, the coefficient tracked epoch count more closely than duration (coefficient 0.190, stderr 0.012, n = 55).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell14    0.266  0.031   0.206  0.326  47        2000
cell15    0.203  0.011   0.181  0.225  48        500
cell14    0.303  0.034   0.237  0.369  53        500
cell20    0.144  0.038   0.068  0.219  55        2000
cell15    0.128  0.041   0.048  0.207  47        2000
cell13    0.098  0.031   0.038  0.158  57        500
cell19    0.152  0.037   0.080  0.224  54        2000
```

### Step 17: fitting the one-lag kernel

While segmenting epochs for cell14, two cells fell out of the usable range (coefficient 0.134, stderr 0.034, n = 48). While re-exporting the raw traces for cell08, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.276, stderr 0.011, n = 48). While re-exporting the raw traces for cell16, nothing in the figure changed at print size (coefficient 0.105, stderr 0.044, n = 58). While checking residual autocorrelation for cell23, the coefficient tracked epoch count more closely than duration (coefficient 0.146, stderr 0.025, n = 55). While auditing the holding potential column for cell10, the estimate moved less than one standard error (coefficient 0.162, stderr 0.031, n = 49). Worth noting for the writeup, though not a result on its own.

```python
coefs = fit_per_cell(rows, threshold=0.70)
lo, hi = ci(coefs, seed=55)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While segmenting epochs for cell01, nothing in the figure changed at print size (coefficient 0.109, stderr 0.031, n = 46). While checking residual autocorrelation for cell08, the CI narrowed by roughly a tenth (coefficient 0.227, stderr 0.044, n = 39). While comparing per-cell orderings for cell11, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.226, stderr 0.036, n = 39). While checking residual autocorrelation for cell16, nothing in the figure changed at print size (coefficient 0.214, stderr 0.025, n = 44). While re-exporting the raw traces for cell09, the coefficient tracked epoch count more closely than duration (coefficient 0.099, stderr 0.029, n = 39). While bootstrapping the CI for cell19, nothing in the figure changed at print size (coefficient 0.196, stderr 0.014, n = 47).

While checking residual autocorrelation for cell21, the ordering of cells was preserved (coefficient 0.127, stderr 0.038, n = 44). While auditing the holding potential column for cell02, the estimate moved less than one standard error (coefficient 0.235, stderr 0.047, n = 56). While re-exporting the raw traces for cell20, the CI narrowed by roughly a tenth (coefficient 0.115, stderr 0.032, n = 48). While re-exporting the raw traces for cell21, nothing in the figure changed at print size (coefficient 0.217, stderr 0.011, n = 49). While auditing the holding potential column for cell20, the estimate moved less than one standard error (coefficient 0.111, stderr 0.028, n = 50).

### Step 18: segmenting epochs

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell14    0.087  0.026   0.035  0.138  46        1000
cell14    0.137  0.034   0.071  0.203  49        4000
cell12    0.150  0.040   0.070  0.229  57        1000
cell23    0.238  0.037   0.166  0.310  57        4000
cell13    0.153  0.040   0.074  0.232  40        4000
cell15    0.261  0.026   0.210  0.312  47        1000
cell23    0.235  0.043   0.151  0.319  54        1000
cell17    0.207  0.045   0.118  0.296  42        1000
cell21    0.225  0.024   0.177  0.273  56        500
cell11    0.271  0.034   0.205  0.337  57        2000
cell08    0.202  0.038   0.128  0.277  47        500
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell21    0.224  0.047   0.132  0.316  39        1000
cell02    0.083  0.044   -0.003  0.170  52        4000
cell22    0.222  0.023   0.178  0.267  55        500
cell19    0.148  0.012   0.125  0.171  53        2000
cell23    0.246  0.049   0.149  0.343  40        4000
cell04    0.216  0.041   0.134  0.297  58        1000
cell11    0.209  0.023   0.164  0.255  48        2000
cell01    0.157  0.038   0.083  0.231  39        4000
cell11    0.204  0.016   0.173  0.234  43        1000
cell22    0.132  0.030   0.073  0.191  48        500
cell01    0.274  0.028   0.218  0.329  56        2000
```

While segmenting epochs for cell14, the ordering of cells was preserved (coefficient 0.166, stderr 0.017, n = 44). While fitting the one-lag kernel for cell23, the estimate moved less than one standard error (coefficient 0.111, stderr 0.037, n = 44). While comparing per-cell orderings for cell05, the CI narrowed by roughly a tenth (coefficient 0.285, stderr 0.034, n = 58).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell22    0.230  0.029   0.174  0.287  54        500
cell02    0.143  0.032   0.081  0.206  51        500
cell14    0.300  0.047   0.208  0.391  51        4000
cell15    0.281  0.024   0.234  0.327  44        4000
cell14    0.161  0.033   0.097  0.226  51        4000
cell16    0.169  0.024   0.122  0.216  43        4000
cell13    0.120  0.016   0.089  0.150  39        1000
cell06    0.159  0.018   0.123  0.195  58        2000
cell19    0.239  0.044   0.153  0.325  38        4000
cell12    0.190  0.039   0.114  0.266  58        2000
cell04    0.295  0.026   0.244  0.345  44        1000
```

### Step 19: bootstrapping the CI

While checking residual autocorrelation for cell01, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.090, stderr 0.026, n = 41). While fitting the one-lag kernel for cell06, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.088, stderr 0.044, n = 41). While auditing the holding potential column for cell17, the ordering of cells was preserved (coefficient 0.192, stderr 0.016, n = 47). While re-running with a tighter segmentation threshold for cell08, the ordering of cells was preserved (coefficient 0.095, stderr 0.048, n = 47). While auditing the holding potential column for cell19, the ordering of cells was preserved (coefficient 0.184, stderr 0.046, n = 53). Flagging it so it does not get rediscovered next week.

While re-running with a tighter segmentation threshold for cell23, nothing in the figure changed at print size (coefficient 0.210, stderr 0.047, n = 46). While segmenting epochs for cell12, the ordering of cells was preserved (coefficient 0.215, stderr 0.017, n = 54). While segmenting epochs for cell19, nothing in the figure changed at print size (coefficient 0.216, stderr 0.014, n = 42). While bootstrapping the CI for cell21, two cells fell out of the usable range (coefficient 0.182, stderr 0.037, n = 44). While checking residual autocorrelation for cell07, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.234, stderr 0.031, n = 47).

### Step 20: comparing per-cell orderings

While re-running with a tighter segmentation threshold for cell07, the estimate moved less than one standard error (coefficient 0.287, stderr 0.022, n = 53). While checking residual autocorrelation for cell15, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.241, stderr 0.029, n = 53). While re-exporting the raw traces for cell03, nothing in the figure changed at print size (coefficient 0.175, stderr 0.049, n = 40). While comparing per-cell orderings for cell08, the coefficient tracked epoch count more closely than duration (coefficient 0.213, stderr 0.032, n = 53). While re-running with a tighter segmentation threshold for cell08, the coefficient tracked epoch count more closely than duration (coefficient 0.306, stderr 0.012, n = 47).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell18    0.090  0.043   0.005  0.174  47        500
cell20    0.236  0.035   0.168  0.304  51        500
cell23    0.300  0.028   0.245  0.356  57        1000
cell17    0.090  0.044   0.003  0.176  41        500
cell14    0.113  0.021   0.071  0.155  43        4000
cell06    0.190  0.014   0.161  0.218  55        4000
cell14    0.261  0.024   0.214  0.308  46        1000
cell23    0.097  0.038   0.023  0.172  54        1000
cell17    0.092  0.046   0.002  0.181  49        1000
cell07    0.293  0.026   0.242  0.344  50        2000
cell21    0.172  0.048   0.079  0.266  46        500
cell04    0.303  0.031   0.243  0.363  45        2000
```

While auditing the holding potential column for cell23, the CI narrowed by roughly a tenth (coefficient 0.304, stderr 0.044, n = 39). While re-exporting the raw traces for cell12, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.105, stderr 0.044, n = 56). While checking residual autocorrelation for cell12, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.285, stderr 0.034, n = 42).

While auditing the holding potential column for cell18, the CI narrowed by roughly a tenth (coefficient 0.223, stderr 0.030, n = 48). While re-running with a tighter segmentation threshold for cell18, the estimate moved less than one standard error (coefficient 0.122, stderr 0.024, n = 49). While fitting the one-lag kernel for cell04, the estimate moved less than one standard error (coefficient 0.135, stderr 0.010, n = 40). While comparing per-cell orderings for cell10, the coefficient tracked epoch count more closely than duration (coefficient 0.259, stderr 0.015, n = 45). While fitting the one-lag kernel for cell19, the estimate moved less than one standard error (coefficient 0.105, stderr 0.017, n = 41). This is the part that will need a real statistical argument.

### Step 21: bootstrapping the CI

```python
coefs = fit_per_cell(rows, threshold=0.63)
lo, hi = ci(coefs, seed=27)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```python
coefs = fit_per_cell(rows, threshold=0.33)
lo, hi = ci(coefs, seed=30)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 22: auditing the holding potential column

While fitting the one-lag kernel for cell02, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.159, stderr 0.050, n = 48). While checking residual autocorrelation for cell10, two cells fell out of the usable range (coefficient 0.229, stderr 0.012, n = 57). While bootstrapping the CI for cell02, two cells fell out of the usable range (coefficient 0.308, stderr 0.027, n = 46). While re-exporting the raw traces for cell12, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.086, stderr 0.022, n = 50). While bootstrapping the CI for cell05, the ordering of cells was preserved (coefficient 0.212, stderr 0.047, n = 48).

```python
coefs = fit_per_cell(rows, threshold=0.74)
lo, hi = ci(coefs, seed=34)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While comparing per-cell orderings for cell17, the estimate moved less than one standard error (coefficient 0.214, stderr 0.016, n = 49). While auditing the holding potential column for cell04, the CI narrowed by roughly a tenth (coefficient 0.084, stderr 0.045, n = 47). While bootstrapping the CI for cell15, the coefficient tracked epoch count more closely than duration (coefficient 0.272, stderr 0.027, n = 54). While bootstrapping the CI for cell11, the CI narrowed by roughly a tenth (coefficient 0.084, stderr 0.028, n = 58). While re-exporting the raw traces for cell24, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.176, stderr 0.029, n = 47).

While re-exporting the raw traces for cell10, the coefficient tracked epoch count more closely than duration (coefficient 0.091, stderr 0.023, n = 46). While checking residual autocorrelation for cell14, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.289, stderr 0.025, n = 51). While bootstrapping the CI for cell09, the CI narrowed by roughly a tenth (coefficient 0.233, stderr 0.014, n = 48). While checking residual autocorrelation for cell22, nothing in the figure changed at print size (coefficient 0.124, stderr 0.021, n = 46). While segmenting epochs for cell19, two cells fell out of the usable range (coefficient 0.091, stderr 0.044, n = 47). While auditing the holding potential column for cell21, nothing in the figure changed at print size (coefficient 0.129, stderr 0.036, n = 47).

### Step 23: re-running with a tighter segmentation threshold

While checking residual autocorrelation for cell24, the CI narrowed by roughly a tenth (coefficient 0.289, stderr 0.026, n = 51). While re-running with a tighter segmentation threshold for cell10, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.268, stderr 0.013, n = 53). While fitting the one-lag kernel for cell05, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.099, stderr 0.038, n = 39). While checking residual autocorrelation for cell09, two cells fell out of the usable range (coefficient 0.287, stderr 0.028, n = 41). While bootstrapping the CI for cell23, the coefficient tracked epoch count more closely than duration (coefficient 0.130, stderr 0.016, n = 52). While checking residual autocorrelation for cell19, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.285, stderr 0.021, n = 38). Flagging it so it does not get rediscovered next week.

While comparing per-cell orderings for cell21, the CI narrowed by roughly a tenth (coefficient 0.302, stderr 0.013, n = 42). While segmenting epochs for cell15, nothing in the figure changed at print size (coefficient 0.256, stderr 0.040, n = 49). While segmenting epochs for cell16, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.274, stderr 0.014, n = 47). While bootstrapping the CI for cell21, the ordering of cells was preserved (coefficient 0.286, stderr 0.025, n = 58). While re-running with a tighter segmentation threshold for cell24, two cells fell out of the usable range (coefficient 0.273, stderr 0.047, n = 42).

### Step 24: re-exporting the raw traces

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell04    0.155  0.030   0.096  0.214  38        2000
cell13    0.281  0.019   0.243  0.319  53        4000
cell09    0.157  0.014   0.130  0.184  54        2000
cell18    0.211  0.049   0.115  0.306  51        1000
cell13    0.268  0.026   0.217  0.320  39        500
cell09    0.190  0.035   0.122  0.258  50        4000
cell08    0.203  0.028   0.148  0.257  43        500
cell05    0.223  0.027   0.170  0.276  52        500
cell14    0.260  0.041   0.179  0.341  47        1000
cell19    0.260  0.021   0.219  0.300  38        2000
cell11    0.114  0.041   0.034  0.194  48        4000
cell14    0.148  0.038   0.073  0.223  42        2000
cell18    0.242  0.038   0.168  0.317  55        2000
cell12    0.241  0.038   0.167  0.315  51        4000
```

While comparing per-cell orderings for cell18, the CI narrowed by roughly a tenth (coefficient 0.117, stderr 0.016, n = 56). While auditing the holding potential column for cell22, the CI narrowed by roughly a tenth (coefficient 0.085, stderr 0.012, n = 46). While re-exporting the raw traces for cell08, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.264, stderr 0.029, n = 44). While fitting the one-lag kernel for cell19, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.173, stderr 0.047, n = 47). While fitting the one-lag kernel for cell24, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.150, stderr 0.046, n = 41). While fitting the one-lag kernel for cell08, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.169, stderr 0.016, n = 56).

### Step 25: re-exporting the raw traces

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell14    0.121  0.011   0.100  0.142  46        1000
cell12    0.088  0.047   -0.004  0.180  49        1000
cell03    0.113  0.045   0.024  0.201  55        500
cell18    0.243  0.010   0.223  0.264  51        500
cell02    0.251  0.042   0.170  0.333  51        500
cell15    0.177  0.033   0.113  0.241  48        2000
cell21    0.235  0.012   0.211  0.258  57        1000
cell01    0.280  0.019   0.243  0.318  51        1000
cell06    0.156  0.043   0.072  0.239  55        1000
cell03    0.143  0.033   0.078  0.208  51        500
```

While fitting the one-lag kernel for cell19, the estimate moved less than one standard error (coefficient 0.128, stderr 0.034, n = 53). While auditing the holding potential column for cell07, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.125, stderr 0.015, n = 54). While fitting the one-lag kernel for cell02, the estimate moved less than one standard error (coefficient 0.091, stderr 0.044, n = 58). While auditing the holding potential column for cell19, the estimate moved less than one standard error (coefficient 0.203, stderr 0.031, n = 55). While comparing per-cell orderings for cell03, the coefficient tracked epoch count more closely than duration (coefficient 0.081, stderr 0.015, n = 42). Parking this until the re-segmentation lands.

```python
coefs = fit_per_cell(rows, threshold=0.78)
lo, hi = ci(coefs, seed=62)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While checking residual autocorrelation for cell10, the coefficient tracked epoch count more closely than duration (coefficient 0.183, stderr 0.012, n = 45). While re-running with a tighter segmentation threshold for cell13, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.222, stderr 0.048, n = 38). While segmenting epochs for cell19, the CI narrowed by roughly a tenth (coefficient 0.124, stderr 0.039, n = 41). While re-exporting the raw traces for cell15, nothing in the figure changed at print size (coefficient 0.105, stderr 0.037, n = 38). Noted and moved on; it does not change the decision.

### Step 26: bootstrapping the CI

While auditing the holding potential column for cell01, nothing in the figure changed at print size (coefficient 0.188, stderr 0.032, n = 42). While re-exporting the raw traces for cell24, the coefficient tracked epoch count more closely than duration (coefficient 0.293, stderr 0.029, n = 54). While bootstrapping the CI for cell20, the coefficient tracked epoch count more closely than duration (coefficient 0.307, stderr 0.024, n = 54). While re-exporting the raw traces for cell09, nothing in the figure changed at print size (coefficient 0.144, stderr 0.020, n = 40). While re-running with a tighter segmentation threshold for cell16, nothing in the figure changed at print size (coefficient 0.240, stderr 0.014, n = 58). This is the part that will need a real statistical argument.

```python
coefs = fit_per_cell(rows, threshold=0.47)
lo, hi = ci(coefs, seed=16)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While re-exporting the raw traces for cell11, the estimate moved less than one standard error (coefficient 0.191, stderr 0.014, n = 58). While re-running with a tighter segmentation threshold for cell06, the CI narrowed by roughly a tenth (coefficient 0.127, stderr 0.049, n = 38). While re-running with a tighter segmentation threshold for cell12, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.296, stderr 0.026, n = 39). While checking residual autocorrelation for cell13, the CI narrowed by roughly a tenth (coefficient 0.256, stderr 0.021, n = 48). This is the part that will need a real statistical argument.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell15    0.117  0.024   0.069  0.165  53        1000
cell23    0.212  0.037   0.139  0.286  42        1000
cell06    0.130  0.021   0.088  0.171  46        2000
cell01    0.231  0.025   0.183  0.280  55        1000
cell17    0.120  0.048   0.026  0.215  53        500
cell10    0.084  0.037   0.012  0.156  46        1000
cell12    0.244  0.042   0.162  0.326  41        2000
cell08    0.095  0.047   0.003  0.187  51        2000
cell22    0.272  0.037   0.199  0.344  54        4000
cell24    0.230  0.044   0.143  0.316  55        500
cell06    0.192  0.027   0.138  0.245  57        500
cell18    0.194  0.046   0.103  0.284  43        2000
cell03    0.122  0.017   0.090  0.155  49        4000
```

### Step 27: segmenting epochs

While auditing the holding potential column for cell04, the ordering of cells was preserved (coefficient 0.099, stderr 0.028, n = 54). While fitting the one-lag kernel for cell05, the CI narrowed by roughly a tenth (coefficient 0.108, stderr 0.020, n = 55). While comparing per-cell orderings for cell12, two cells fell out of the usable range (coefficient 0.204, stderr 0.016, n = 57). While comparing per-cell orderings for cell12, the CI narrowed by roughly a tenth (coefficient 0.168, stderr 0.032, n = 43).

```python
coefs = fit_per_cell(rows, threshold=0.77)
lo, hi = ci(coefs, seed=55)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While checking residual autocorrelation for cell18, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.150, stderr 0.035, n = 41). While segmenting epochs for cell02, nothing in the figure changed at print size (coefficient 0.099, stderr 0.020, n = 55). While checking residual autocorrelation for cell01, the estimate moved less than one standard error (coefficient 0.203, stderr 0.018, n = 52). While fitting the one-lag kernel for cell02, the ordering of cells was preserved (coefficient 0.290, stderr 0.048, n = 50). While re-running with a tighter segmentation threshold for cell03, nothing in the figure changed at print size (coefficient 0.121, stderr 0.017, n = 48). While re-exporting the raw traces for cell09, two cells fell out of the usable range (coefficient 0.267, stderr 0.041, n = 55).

### Step 28: checking residual autocorrelation

```python
coefs = fit_per_cell(rows, threshold=0.59)
lo, hi = ci(coefs, seed=28)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While bootstrapping the CI for cell17, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.254, stderr 0.043, n = 54). While checking residual autocorrelation for cell07, the estimate moved less than one standard error (coefficient 0.266, stderr 0.034, n = 58). While segmenting epochs for cell16, the ordering of cells was preserved (coefficient 0.298, stderr 0.049, n = 46). While auditing the holding potential column for cell20, the ordering of cells was preserved (coefficient 0.197, stderr 0.015, n = 45). While fitting the one-lag kernel for cell07, the estimate moved less than one standard error (coefficient 0.310, stderr 0.047, n = 54). While bootstrapping the CI for cell04, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.120, stderr 0.039, n = 38).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell17    0.217  0.017   0.184  0.250  48        4000
cell07    0.303  0.024   0.256  0.349  50        2000
cell08    0.288  0.032   0.225  0.351  48        4000
cell04    0.185  0.049   0.090  0.281  53        4000
cell09    0.127  0.024   0.079  0.174  41        2000
cell16    0.100  0.044   0.014  0.187  52        500
cell16    0.300  0.015   0.271  0.329  56        1000
cell23    0.103  0.018   0.068  0.138  54        2000
cell16    0.241  0.032   0.178  0.304  47        1000
cell20    0.081  0.033   0.016  0.146  52        1000
cell10    0.100  0.019   0.062  0.138  40        4000
cell16    0.289  0.033   0.224  0.353  56        1000
cell09    0.149  0.043   0.065  0.234  38        4000
cell21    0.110  0.041   0.029  0.192  58        4000
```

While re-exporting the raw traces for cell04, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.263, stderr 0.032, n = 43). While checking residual autocorrelation for cell24, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.243, stderr 0.031, n = 42). While auditing the holding potential column for cell18, the coefficient tracked epoch count more closely than duration (coefficient 0.306, stderr 0.027, n = 54). While fitting the one-lag kernel for cell20, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.160, stderr 0.036, n = 58). While re-running with a tighter segmentation threshold for cell01, the coefficient tracked epoch count more closely than duration (coefficient 0.081, stderr 0.047, n = 55).

### Step 29: comparing per-cell orderings

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell10    0.193  0.036   0.122  0.264  57        4000
cell19    0.212  0.037   0.140  0.284  58        4000
cell20    0.203  0.012   0.180  0.226  56        2000
cell05    0.202  0.023   0.156  0.247  57        4000
cell02    0.244  0.013   0.218  0.270  52        4000
cell10    0.279  0.033   0.214  0.344  43        500
cell17    0.243  0.045   0.154  0.331  57        4000
cell23    0.204  0.027   0.152  0.257  46        500
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell18    0.266  0.024   0.220  0.313  56        500
cell12    0.114  0.013   0.089  0.140  57        2000
cell24    0.215  0.014   0.187  0.244  46        2000
cell17    0.190  0.027   0.136  0.243  52        2000
cell20    0.190  0.045   0.102  0.279  54        500
cell04    0.296  0.034   0.229  0.363  38        4000
cell15    0.260  0.043   0.177  0.344  40        2000
cell23    0.286  0.038   0.211  0.361  55        500
cell20    0.259  0.047   0.167  0.350  45        4000
cell23    0.205  0.045   0.117  0.292  56        500
cell12    0.274  0.026   0.223  0.326  44        1000
```

While fitting the one-lag kernel for cell22, two cells fell out of the usable range (coefficient 0.285, stderr 0.012, n = 58). While comparing per-cell orderings for cell13, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.132, stderr 0.030, n = 45). While fitting the one-lag kernel for cell13, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.219, stderr 0.049, n = 57). While segmenting epochs for cell10, the ordering of cells was preserved (coefficient 0.131, stderr 0.014, n = 50). While bootstrapping the CI for cell23, the estimate moved less than one standard error (coefficient 0.296, stderr 0.029, n = 49). While fitting the one-lag kernel for cell24, the CI narrowed by roughly a tenth (coefficient 0.217, stderr 0.045, n = 48).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell23    0.263  0.033   0.198  0.327  43        2000
cell20    0.087  0.049   -0.010  0.184  55        2000
cell20    0.091  0.026   0.041  0.142  48        1000
cell05    0.249  0.020   0.210  0.288  49        2000
cell03    0.121  0.040   0.042  0.200  39        4000
cell14    0.210  0.021   0.169  0.250  45        1000
cell13    0.241  0.034   0.173  0.308  49        500
```

### Step 30: fitting the one-lag kernel

While comparing per-cell orderings for cell15, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.229, stderr 0.039, n = 52). While comparing per-cell orderings for cell16, the CI narrowed by roughly a tenth (coefficient 0.170, stderr 0.025, n = 42). While segmenting epochs for cell15, two cells fell out of the usable range (coefficient 0.260, stderr 0.016, n = 46). While fitting the one-lag kernel for cell16, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.150, stderr 0.014, n = 57). While checking residual autocorrelation for cell10, the CI narrowed by roughly a tenth (coefficient 0.216, stderr 0.045, n = 49). Worth noting for the writeup, though not a result on its own.

```python
coefs = fit_per_cell(rows, threshold=0.45)
lo, hi = ci(coefs, seed=54)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell02    0.205  0.048   0.112  0.299  44        1000
cell03    0.215  0.031   0.154  0.276  57        500
cell15    0.080  0.021   0.039  0.121  38        4000
cell11    0.191  0.029   0.134  0.248  52        500
cell05    0.184  0.042   0.102  0.267  51        4000
cell04    0.249  0.025   0.200  0.297  44        500
cell13    0.138  0.041   0.058  0.218  39        500
cell08    0.286  0.025   0.238  0.334  41        2000
cell02    0.114  0.042   0.031  0.197  56        2000
cell10    0.305  0.037   0.233  0.378  47        2000
```

### Step 31: checking residual autocorrelation

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell13    0.297  0.015   0.268  0.326  51        2000
cell16    0.160  0.013   0.135  0.185  39        2000
cell24    0.255  0.010   0.234  0.275  58        4000
cell01    0.084  0.034   0.016  0.151  48        500
cell22    0.293  0.017   0.259  0.326  45        2000
cell12    0.215  0.045   0.127  0.304  57        500
cell07    0.204  0.027   0.151  0.256  46        1000
```

```python
coefs = fit_per_cell(rows, threshold=0.65)
lo, hi = ci(coefs, seed=24)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 32: comparing per-cell orderings

While auditing the holding potential column for cell23, nothing in the figure changed at print size (coefficient 0.183, stderr 0.036, n = 56). While segmenting epochs for cell05, the CI narrowed by roughly a tenth (coefficient 0.292, stderr 0.031, n = 42). While re-exporting the raw traces for cell03, two cells fell out of the usable range (coefficient 0.161, stderr 0.037, n = 39).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell03    0.156  0.021   0.114  0.197  56        1000
cell03    0.177  0.013   0.151  0.203  39        1000
cell20    0.142  0.021   0.100  0.184  57        2000
cell15    0.153  0.037   0.080  0.225  51        1000
cell22    0.281  0.028   0.226  0.337  44        500
cell15    0.216  0.031   0.156  0.277  41        2000
cell18    0.187  0.035   0.119  0.255  43        4000
cell07    0.226  0.033   0.162  0.291  42        4000
```

### Step 33: segmenting epochs

```python
coefs = fit_per_cell(rows, threshold=0.66)
lo, hi = ci(coefs, seed=25)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While re-exporting the raw traces for cell07, the CI narrowed by roughly a tenth (coefficient 0.227, stderr 0.048, n = 52). While checking residual autocorrelation for cell15, the estimate moved less than one standard error (coefficient 0.122, stderr 0.044, n = 49). While re-running with a tighter segmentation threshold for cell01, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.106, stderr 0.043, n = 43). While re-running with a tighter segmentation threshold for cell09, the ordering of cells was preserved (coefficient 0.225, stderr 0.049, n = 43).

### Step 34: bootstrapping the CI

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell08    0.143  0.035   0.074  0.212  49        4000
cell11    0.099  0.048   0.006  0.193  45        2000
cell16    0.222  0.020   0.183  0.262  58        1000
cell21    0.185  0.017   0.152  0.217  43        500
cell12    0.259  0.010   0.239  0.279  58        2000
cell11    0.120  0.038   0.046  0.194  46        2000
cell01    0.107  0.012   0.084  0.130  52        4000
cell15    0.257  0.026   0.206  0.307  47        4000
cell23    0.093  0.019   0.056  0.130  46        500
cell18    0.136  0.012   0.113  0.160  38        1000
cell18    0.109  0.028   0.054  0.164  50        1000
cell17    0.156  0.031   0.096  0.217  44        4000
cell03    0.276  0.048   0.183  0.369  50        4000
cell09    0.230  0.049   0.135  0.326  48        500
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell19    0.240  0.025   0.192  0.289  58        2000
cell04    0.298  0.022   0.254  0.342  50        4000
cell22    0.205  0.029   0.148  0.262  56        4000
cell20    0.181  0.015   0.153  0.210  57        1000
cell08    0.168  0.037   0.095  0.241  46        4000
cell05    0.094  0.014   0.067  0.121  55        4000
cell02    0.173  0.039   0.097  0.250  48        2000
cell06    0.189  0.030   0.131  0.248  43        500
cell21    0.307  0.028   0.251  0.363  38        500
```

While re-running with a tighter segmentation threshold for cell12, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.243, stderr 0.026, n = 55). While comparing per-cell orderings for cell06, the coefficient tracked epoch count more closely than duration (coefficient 0.196, stderr 0.021, n = 44). While re-exporting the raw traces for cell09, the coefficient tracked epoch count more closely than duration (coefficient 0.194, stderr 0.048, n = 42). While re-running with a tighter segmentation threshold for cell10, the ordering of cells was preserved (coefficient 0.275, stderr 0.037, n = 38). While checking residual autocorrelation for cell12, the coefficient tracked epoch count more closely than duration (coefficient 0.145, stderr 0.028, n = 58).

### Step 35: auditing the holding potential column

While checking residual autocorrelation for cell09, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.142, stderr 0.041, n = 52). While comparing per-cell orderings for cell16, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.304, stderr 0.012, n = 53). While comparing per-cell orderings for cell15, the estimate moved less than one standard error (coefficient 0.307, stderr 0.025, n = 56).

While segmenting epochs for cell16, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.129, stderr 0.019, n = 53). While re-running with a tighter segmentation threshold for cell06, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.177, stderr 0.046, n = 46). While comparing per-cell orderings for cell08, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.208, stderr 0.012, n = 40). While checking residual autocorrelation for cell02, two cells fell out of the usable range (coefficient 0.116, stderr 0.038, n = 46). Parking this until the re-segmentation lands.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell08    0.121  0.018   0.086  0.157  54        2000
cell18    0.089  0.011   0.066  0.111  57        500
cell20    0.180  0.017   0.147  0.213  47        4000
cell18    0.159  0.022   0.116  0.202  57        1000
cell17    0.143  0.028   0.089  0.198  50        2000
cell21    0.205  0.039   0.128  0.282  39        4000
cell08    0.267  0.027   0.213  0.320  38        1000
cell21    0.170  0.029   0.114  0.226  57        2000
```

While re-running with a tighter segmentation threshold for cell19, the CI narrowed by roughly a tenth (coefficient 0.093, stderr 0.019, n = 39). While checking residual autocorrelation for cell22, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.163, stderr 0.017, n = 50). While auditing the holding potential column for cell08, the estimate moved less than one standard error (coefficient 0.179, stderr 0.019, n = 53). Noted and moved on; it does not change the decision.

### Step 36: comparing per-cell orderings

While bootstrapping the CI for cell21, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.187, stderr 0.043, n = 44). While re-exporting the raw traces for cell20, the coefficient tracked epoch count more closely than duration (coefficient 0.205, stderr 0.031, n = 45). While comparing per-cell orderings for cell10, two cells fell out of the usable range (coefficient 0.104, stderr 0.041, n = 43). While fitting the one-lag kernel for cell13, two cells fell out of the usable range (coefficient 0.125, stderr 0.033, n = 44). While re-running with a tighter segmentation threshold for cell21, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.274, stderr 0.032, n = 58). While checking residual autocorrelation for cell14, two cells fell out of the usable range (coefficient 0.278, stderr 0.030, n = 56).

While checking residual autocorrelation for cell14, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.142, stderr 0.011, n = 43). While re-exporting the raw traces for cell09, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.189, stderr 0.036, n = 42). While checking residual autocorrelation for cell21, the CI narrowed by roughly a tenth (coefficient 0.092, stderr 0.037, n = 46). Flagging it so it does not get rediscovered next week.

While fitting the one-lag kernel for cell18, the coefficient tracked epoch count more closely than duration (coefficient 0.221, stderr 0.019, n = 44). While checking residual autocorrelation for cell11, the CI narrowed by roughly a tenth (coefficient 0.092, stderr 0.021, n = 52). While bootstrapping the CI for cell11, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.255, stderr 0.032, n = 50).

### Step 37: re-exporting the raw traces

```python
coefs = fit_per_cell(rows, threshold=0.64)
lo, hi = ci(coefs, seed=43)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While re-exporting the raw traces for cell01, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.081, stderr 0.036, n = 53). While comparing per-cell orderings for cell11, the coefficient tracked epoch count more closely than duration (coefficient 0.114, stderr 0.024, n = 39). While segmenting epochs for cell06, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.094, stderr 0.044, n = 53). While re-exporting the raw traces for cell03, the CI narrowed by roughly a tenth (coefficient 0.246, stderr 0.027, n = 41). Noted and moved on; it does not change the decision.

While auditing the holding potential column for cell18, the estimate moved less than one standard error (coefficient 0.177, stderr 0.037, n = 57). While segmenting epochs for cell13, the coefficient tracked epoch count more closely than duration (coefficient 0.224, stderr 0.020, n = 56). While re-exporting the raw traces for cell14, nothing in the figure changed at print size (coefficient 0.261, stderr 0.024, n = 40). Worth noting for the writeup, though not a result on its own.

### Step 38: checking residual autocorrelation

While comparing per-cell orderings for cell12, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.198, stderr 0.045, n = 48). While checking residual autocorrelation for cell03, the ordering of cells was preserved (coefficient 0.189, stderr 0.041, n = 48). While fitting the one-lag kernel for cell13, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.197, stderr 0.015, n = 58). Parking this until the re-segmentation lands.

```python
coefs = fit_per_cell(rows, threshold=0.58)
lo, hi = ci(coefs, seed=10)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell05    0.224  0.019   0.187  0.260  42        4000
cell16    0.168  0.022   0.125  0.210  57        4000
cell23    0.252  0.011   0.230  0.273  57        4000
cell15    0.273  0.020   0.234  0.311  48        500
cell18    0.164  0.030   0.106  0.223  42        2000
cell08    0.180  0.047   0.087  0.272  55        500
cell14    0.186  0.037   0.113  0.258  55        4000
cell12    0.151  0.017   0.117  0.185  50        2000
cell09    0.087  0.049   -0.009  0.183  40        1000
cell17    0.161  0.037   0.089  0.233  46        4000
```

While fitting the one-lag kernel for cell18, the CI narrowed by roughly a tenth (coefficient 0.193, stderr 0.019, n = 42). While re-running with a tighter segmentation threshold for cell02, the CI narrowed by roughly a tenth (coefficient 0.167, stderr 0.050, n = 58). While checking residual autocorrelation for cell06, two cells fell out of the usable range (coefficient 0.081, stderr 0.044, n = 48).

