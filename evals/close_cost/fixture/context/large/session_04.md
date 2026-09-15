# Prior session 4 of 20

Transcript of an earlier working session on the history-kernel analysis.

### Step 1: auditing the holding potential column

While checking residual autocorrelation for cell08, nothing in the figure changed at print size (coefficient 0.180, stderr 0.026, n = 53). While segmenting epochs for cell12, the estimate moved less than one standard error (coefficient 0.177, stderr 0.026, n = 54). While comparing per-cell orderings for cell17, two cells fell out of the usable range (coefficient 0.134, stderr 0.026, n = 54). While auditing the holding potential column for cell18, two cells fell out of the usable range (coefficient 0.273, stderr 0.031, n = 54). While bootstrapping the CI for cell07, the coefficient tracked epoch count more closely than duration (coefficient 0.176, stderr 0.027, n = 55).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell06    0.234  0.020   0.194  0.274  58        4000
cell06    0.266  0.042   0.184  0.348  51        4000
cell20    0.166  0.050   0.069  0.263  54        500
cell22    0.166  0.040   0.088  0.244  49        2000
cell19    0.285  0.038   0.211  0.360  47        4000
cell21    0.284  0.015   0.255  0.314  55        1000
cell13    0.260  0.047   0.168  0.352  47        2000
cell19    0.308  0.037   0.236  0.380  53        4000
cell13    0.216  0.024   0.169  0.264  57        4000
cell19    0.106  0.047   0.013  0.198  46        4000
cell22    0.194  0.015   0.165  0.223  54        1000
cell01    0.167  0.043   0.083  0.251  58        4000
cell02    0.213  0.031   0.152  0.275  40        1000
```

While auditing the holding potential column for cell10, nothing in the figure changed at print size (coefficient 0.263, stderr 0.027, n = 46). While segmenting epochs for cell22, the coefficient tracked epoch count more closely than duration (coefficient 0.192, stderr 0.042, n = 51). While re-running with a tighter segmentation threshold for cell15, nothing in the figure changed at print size (coefficient 0.234, stderr 0.027, n = 58). While re-running with a tighter segmentation threshold for cell10, nothing in the figure changed at print size (coefficient 0.099, stderr 0.019, n = 58). While fitting the one-lag kernel for cell04, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.266, stderr 0.049, n = 58). While fitting the one-lag kernel for cell18, nothing in the figure changed at print size (coefficient 0.290, stderr 0.037, n = 49).

### Step 2: segmenting epochs

While re-running with a tighter segmentation threshold for cell11, two cells fell out of the usable range (coefficient 0.186, stderr 0.018, n = 42). While re-running with a tighter segmentation threshold for cell23, two cells fell out of the usable range (coefficient 0.123, stderr 0.044, n = 47). While re-exporting the raw traces for cell24, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.125, stderr 0.027, n = 58). While bootstrapping the CI for cell21, two cells fell out of the usable range (coefficient 0.147, stderr 0.033, n = 52). While re-running with a tighter segmentation threshold for cell01, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.138, stderr 0.035, n = 50). While bootstrapping the CI for cell20, the CI narrowed by roughly a tenth (coefficient 0.198, stderr 0.038, n = 52). This is the part that will need a real statistical argument.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell02    0.296  0.021   0.254  0.338  42        4000
cell02    0.115  0.043   0.030  0.200  49        500
cell22    0.197  0.011   0.176  0.219  42        1000
cell01    0.266  0.039   0.190  0.341  53        4000
cell02    0.309  0.037   0.237  0.380  49        4000
cell17    0.175  0.035   0.107  0.243  56        1000
cell14    0.203  0.023   0.157  0.249  58        4000
cell16    0.191  0.041   0.110  0.272  45        4000
cell18    0.292  0.032   0.229  0.355  53        2000
cell20    0.261  0.011   0.240  0.282  55        4000
cell05    0.155  0.039   0.079  0.232  41        4000
cell20    0.245  0.040   0.166  0.324  56        1000
cell20    0.143  0.030   0.085  0.201  50        4000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell22    0.087  0.024   0.041  0.133  51        1000
cell04    0.119  0.042   0.038  0.201  53        1000
cell10    0.173  0.026   0.121  0.224  47        500
cell03    0.262  0.023   0.217  0.307  51        4000
cell03    0.195  0.022   0.151  0.239  58        500
cell21    0.175  0.010   0.155  0.195  44        2000
cell12    0.140  0.023   0.094  0.186  56        2000
cell11    0.221  0.028   0.166  0.276  53        1000
cell23    0.309  0.011   0.286  0.331  43        2000
cell22    0.199  0.030   0.139  0.258  46        500
cell20    0.155  0.033   0.091  0.220  58        4000
cell23    0.236  0.016   0.205  0.268  40        4000
cell03    0.233  0.049   0.137  0.329  57        1000
cell15    0.227  0.012   0.204  0.250  42        2000
```

While re-exporting the raw traces for cell22, the estimate moved less than one standard error (coefficient 0.252, stderr 0.027, n = 42). While auditing the holding potential column for cell09, the coefficient tracked epoch count more closely than duration (coefficient 0.108, stderr 0.044, n = 39). While auditing the holding potential column for cell22, the ordering of cells was preserved (coefficient 0.221, stderr 0.020, n = 40). While re-running with a tighter segmentation threshold for cell07, nothing in the figure changed at print size (coefficient 0.107, stderr 0.045, n = 43). While checking residual autocorrelation for cell24, the CI narrowed by roughly a tenth (coefficient 0.248, stderr 0.039, n = 54). While auditing the holding potential column for cell02, the CI narrowed by roughly a tenth (coefficient 0.185, stderr 0.026, n = 58).

### Step 3: auditing the holding potential column

While comparing per-cell orderings for cell21, the coefficient tracked epoch count more closely than duration (coefficient 0.105, stderr 0.044, n = 43). While checking residual autocorrelation for cell22, the coefficient tracked epoch count more closely than duration (coefficient 0.266, stderr 0.030, n = 40). While segmenting epochs for cell01, nothing in the figure changed at print size (coefficient 0.184, stderr 0.038, n = 49). While auditing the holding potential column for cell11, the ordering of cells was preserved (coefficient 0.308, stderr 0.041, n = 40). While re-running with a tighter segmentation threshold for cell07, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.129, stderr 0.013, n = 58). While checking residual autocorrelation for cell18, nothing in the figure changed at print size (coefficient 0.208, stderr 0.013, n = 40).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell18    0.250  0.011   0.229  0.271  49        2000
cell12    0.308  0.045   0.221  0.396  52        1000
cell04    0.243  0.029   0.187  0.299  45        1000
cell06    0.182  0.039   0.105  0.259  58        2000
cell10    0.236  0.030   0.177  0.295  43        4000
cell23    0.172  0.024   0.124  0.219  56        2000
cell03    0.202  0.023   0.156  0.247  44        1000
cell11    0.259  0.020   0.220  0.298  38        500
cell02    0.189  0.043   0.105  0.272  46        4000
cell21    0.291  0.028   0.236  0.346  42        4000
cell08    0.161  0.044   0.074  0.247  39        1000
cell01    0.296  0.028   0.241  0.350  53        500
cell13    0.172  0.030   0.114  0.230  48        2000
```

```python
coefs = fit_per_cell(rows, threshold=0.31)
lo, hi = ci(coefs, seed=79)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 4: bootstrapping the CI

While fitting the one-lag kernel for cell14, nothing in the figure changed at print size (coefficient 0.202, stderr 0.035, n = 53). While re-running with a tighter segmentation threshold for cell16, the estimate moved less than one standard error (coefficient 0.280, stderr 0.034, n = 46). While comparing per-cell orderings for cell04, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.282, stderr 0.036, n = 50). While segmenting epochs for cell03, nothing in the figure changed at print size (coefficient 0.229, stderr 0.031, n = 41). Flagging it so it does not get rediscovered next week.

While comparing per-cell orderings for cell05, the estimate moved less than one standard error (coefficient 0.162, stderr 0.025, n = 46). While fitting the one-lag kernel for cell07, the coefficient tracked epoch count more closely than duration (coefficient 0.144, stderr 0.027, n = 55). While auditing the holding potential column for cell21, the CI narrowed by roughly a tenth (coefficient 0.293, stderr 0.034, n = 46). While checking residual autocorrelation for cell07, two cells fell out of the usable range (coefficient 0.222, stderr 0.042, n = 57). Noted and moved on; it does not change the decision.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell06    0.147  0.014   0.121  0.174  55        2000
cell07    0.296  0.024   0.248  0.344  50        4000
cell24    0.261  0.023   0.217  0.306  48        4000
cell04    0.105  0.022   0.062  0.147  56        2000
cell15    0.209  0.023   0.163  0.254  57        1000
cell15    0.126  0.022   0.084  0.169  57        500
cell21    0.179  0.017   0.146  0.212  51        500
cell15    0.109  0.021   0.069  0.150  53        1000
cell01    0.176  0.025   0.128  0.225  39        1000
```

### Step 5: bootstrapping the CI

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell06    0.184  0.034   0.118  0.250  43        500
cell02    0.206  0.048   0.112  0.301  49        500
cell04    0.229  0.029   0.174  0.285  51        4000
cell20    0.169  0.046   0.078  0.259  50        4000
cell03    0.200  0.035   0.132  0.268  40        4000
cell11    0.258  0.023   0.214  0.303  57        1000
cell06    0.166  0.030   0.108  0.224  57        4000
cell01    0.251  0.024   0.205  0.297  53        2000
cell20    0.099  0.019   0.062  0.137  57        500
cell17    0.158  0.018   0.124  0.193  40        4000
cell05    0.081  0.024   0.034  0.127  47        4000
```

```python
coefs = fit_per_cell(rows, threshold=0.30)
lo, hi = ci(coefs, seed=53)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While re-running with a tighter segmentation threshold for cell02, nothing in the figure changed at print size (coefficient 0.290, stderr 0.048, n = 50). While bootstrapping the CI for cell08, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.197, stderr 0.032, n = 47). While re-exporting the raw traces for cell03, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.211, stderr 0.047, n = 42). Flagging it so it does not get rediscovered next week.

### Step 6: comparing per-cell orderings

```python
coefs = fit_per_cell(rows, threshold=0.54)
lo, hi = ci(coefs, seed=80)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While fitting the one-lag kernel for cell07, the estimate moved less than one standard error (coefficient 0.121, stderr 0.027, n = 41). While auditing the holding potential column for cell08, the CI narrowed by roughly a tenth (coefficient 0.095, stderr 0.045, n = 46). While bootstrapping the CI for cell11, the CI narrowed by roughly a tenth (coefficient 0.300, stderr 0.028, n = 58). While re-exporting the raw traces for cell17, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.297, stderr 0.049, n = 43). While bootstrapping the CI for cell07, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.190, stderr 0.028, n = 39).

While re-exporting the raw traces for cell14, two cells fell out of the usable range (coefficient 0.113, stderr 0.014, n = 44). While fitting the one-lag kernel for cell22, two cells fell out of the usable range (coefficient 0.114, stderr 0.027, n = 46). While bootstrapping the CI for cell14, two cells fell out of the usable range (coefficient 0.202, stderr 0.015, n = 47). While comparing per-cell orderings for cell11, the ordering of cells was preserved (coefficient 0.082, stderr 0.039, n = 47).

While auditing the holding potential column for cell03, two cells fell out of the usable range (coefficient 0.215, stderr 0.020, n = 44). While auditing the holding potential column for cell08, two cells fell out of the usable range (coefficient 0.251, stderr 0.030, n = 42). While checking residual autocorrelation for cell03, the CI narrowed by roughly a tenth (coefficient 0.287, stderr 0.011, n = 55).

### Step 7: re-running with a tighter segmentation threshold

While checking residual autocorrelation for cell20, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.129, stderr 0.029, n = 40). While checking residual autocorrelation for cell05, two cells fell out of the usable range (coefficient 0.158, stderr 0.026, n = 44). While re-running with a tighter segmentation threshold for cell01, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.207, stderr 0.012, n = 58). While auditing the holding potential column for cell13, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.087, stderr 0.038, n = 52). While checking residual autocorrelation for cell08, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.092, stderr 0.038, n = 48). While checking residual autocorrelation for cell23, the estimate moved less than one standard error (coefficient 0.095, stderr 0.042, n = 57).

```python
coefs = fit_per_cell(rows, threshold=0.45)
lo, hi = ci(coefs, seed=45)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 8: checking residual autocorrelation

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell15    0.249  0.042   0.166  0.331  51        1000
cell13    0.105  0.039   0.029  0.181  38        2000
cell24    0.086  0.038   0.011  0.161  55        500
cell14    0.201  0.049   0.105  0.298  41        4000
cell10    0.154  0.016   0.123  0.185  43        500
cell09    0.138  0.034   0.072  0.204  45        500
cell15    0.178  0.020   0.138  0.217  55        2000
cell13    0.292  0.047   0.200  0.384  43        4000
cell04    0.166  0.037   0.094  0.239  45        2000
cell08    0.223  0.028   0.169  0.277  46        2000
cell22    0.293  0.045   0.206  0.381  52        1000
```

While bootstrapping the CI for cell21, two cells fell out of the usable range (coefficient 0.149, stderr 0.036, n = 54). While comparing per-cell orderings for cell19, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.217, stderr 0.023, n = 50). While comparing per-cell orderings for cell20, the ordering of cells was preserved (coefficient 0.216, stderr 0.014, n = 58). While segmenting epochs for cell06, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.116, stderr 0.020, n = 53). While auditing the holding potential column for cell19, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.179, stderr 0.031, n = 47). While auditing the holding potential column for cell19, the ordering of cells was preserved (coefficient 0.302, stderr 0.028, n = 46). Noted and moved on; it does not change the decision.

While re-running with a tighter segmentation threshold for cell16, the estimate moved less than one standard error (coefficient 0.228, stderr 0.027, n = 55). While segmenting epochs for cell02, nothing in the figure changed at print size (coefficient 0.177, stderr 0.050, n = 54). While bootstrapping the CI for cell18, two cells fell out of the usable range (coefficient 0.189, stderr 0.043, n = 52). While re-running with a tighter segmentation threshold for cell15, the ordering of cells was preserved (coefficient 0.088, stderr 0.035, n = 39). While checking residual autocorrelation for cell01, the coefficient tracked epoch count more closely than duration (coefficient 0.248, stderr 0.049, n = 55). While fitting the one-lag kernel for cell09, nothing in the figure changed at print size (coefficient 0.178, stderr 0.032, n = 43).

### Step 9: re-running with a tighter segmentation threshold

While segmenting epochs for cell18, the CI narrowed by roughly a tenth (coefficient 0.187, stderr 0.025, n = 39). While re-exporting the raw traces for cell06, the CI narrowed by roughly a tenth (coefficient 0.202, stderr 0.045, n = 55). While re-running with a tighter segmentation threshold for cell19, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.250, stderr 0.017, n = 45). While auditing the holding potential column for cell13, the estimate moved less than one standard error (coefficient 0.174, stderr 0.050, n = 50). This is the part that will need a real statistical argument.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell14    0.135  0.028   0.080  0.190  46        2000
cell15    0.156  0.035   0.087  0.224  38        2000
cell13    0.115  0.031   0.053  0.176  43        1000
cell22    0.263  0.049   0.166  0.360  52        1000
cell21    0.188  0.039   0.111  0.265  42        4000
cell18    0.098  0.044   0.012  0.183  41        1000
cell07    0.302  0.020   0.262  0.341  39        1000
cell03    0.146  0.028   0.091  0.201  58        4000
cell10    0.309  0.037   0.236  0.382  47        1000
cell03    0.288  0.043   0.203  0.373  56        2000
cell21    0.162  0.018   0.127  0.197  54        4000
cell22    0.222  0.049   0.127  0.318  54        1000
cell14    0.226  0.027   0.173  0.278  52        4000
cell09    0.181  0.014   0.154  0.208  56        500
```

```python
coefs = fit_per_cell(rows, threshold=0.35)
lo, hi = ci(coefs, seed=32)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 10: segmenting epochs

While segmenting epochs for cell09, the coefficient tracked epoch count more closely than duration (coefficient 0.156, stderr 0.023, n = 51). While segmenting epochs for cell01, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.276, stderr 0.041, n = 54). While comparing per-cell orderings for cell17, the CI narrowed by roughly a tenth (coefficient 0.105, stderr 0.045, n = 47). While re-exporting the raw traces for cell21, the coefficient tracked epoch count more closely than duration (coefficient 0.083, stderr 0.040, n = 45). While bootstrapping the CI for cell04, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.150, stderr 0.037, n = 56).

While comparing per-cell orderings for cell01, the ordering of cells was preserved (coefficient 0.134, stderr 0.018, n = 53). While segmenting epochs for cell01, the ordering of cells was preserved (coefficient 0.107, stderr 0.047, n = 55). While comparing per-cell orderings for cell10, the ordering of cells was preserved (coefficient 0.265, stderr 0.027, n = 51). While checking residual autocorrelation for cell03, the ordering of cells was preserved (coefficient 0.120, stderr 0.026, n = 44). While fitting the one-lag kernel for cell01, the coefficient tracked epoch count more closely than duration (coefficient 0.211, stderr 0.033, n = 41).

### Step 11: re-running with a tighter segmentation threshold

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell15    0.217  0.049   0.121  0.312  50        1000
cell11    0.196  0.031   0.136  0.256  42        2000
cell24    0.229  0.023   0.185  0.274  40        500
cell03    0.125  0.025   0.077  0.174  47        4000
cell01    0.131  0.031   0.070  0.193  47        2000
cell02    0.292  0.030   0.234  0.350  55        2000
cell19    0.276  0.045   0.188  0.364  40        500
```

While segmenting epochs for cell15, two cells fell out of the usable range (coefficient 0.216, stderr 0.043, n = 56). While fitting the one-lag kernel for cell10, the estimate moved less than one standard error (coefficient 0.121, stderr 0.027, n = 42). While checking residual autocorrelation for cell18, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.278, stderr 0.044, n = 47). This is the part that will need a real statistical argument.

While fitting the one-lag kernel for cell03, the coefficient tracked epoch count more closely than duration (coefficient 0.104, stderr 0.017, n = 50). While re-running with a tighter segmentation threshold for cell12, the estimate moved less than one standard error (coefficient 0.125, stderr 0.014, n = 53). While auditing the holding potential column for cell07, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.194, stderr 0.029, n = 48). While comparing per-cell orderings for cell24, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.293, stderr 0.042, n = 47). While auditing the holding potential column for cell21, the ordering of cells was preserved (coefficient 0.171, stderr 0.026, n = 55).

### Step 12: segmenting epochs

While bootstrapping the CI for cell17, the CI narrowed by roughly a tenth (coefficient 0.155, stderr 0.012, n = 54). While comparing per-cell orderings for cell07, the CI narrowed by roughly a tenth (coefficient 0.247, stderr 0.020, n = 57). While fitting the one-lag kernel for cell07, the coefficient tracked epoch count more closely than duration (coefficient 0.149, stderr 0.048, n = 54). While re-running with a tighter segmentation threshold for cell06, the CI narrowed by roughly a tenth (coefficient 0.146, stderr 0.041, n = 41). While bootstrapping the CI for cell17, the CI narrowed by roughly a tenth (coefficient 0.147, stderr 0.012, n = 46).

```python
coefs = fit_per_cell(rows, threshold=0.79)
lo, hi = ci(coefs, seed=2)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 13: fitting the one-lag kernel

While comparing per-cell orderings for cell05, the coefficient tracked epoch count more closely than duration (coefficient 0.242, stderr 0.042, n = 56). While auditing the holding potential column for cell04, the ordering of cells was preserved (coefficient 0.177, stderr 0.050, n = 40). While comparing per-cell orderings for cell11, nothing in the figure changed at print size (coefficient 0.258, stderr 0.010, n = 56).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell06    0.086  0.016   0.055  0.116  42        2000
cell21    0.257  0.020   0.217  0.297  51        2000
cell04    0.234  0.021   0.193  0.275  51        2000
cell13    0.085  0.012   0.062  0.108  52        4000
cell05    0.268  0.041   0.187  0.349  45        2000
cell01    0.257  0.034   0.191  0.323  39        500
cell06    0.210  0.016   0.178  0.242  57        500
cell16    0.242  0.043   0.158  0.325  41        500
cell11    0.154  0.032   0.092  0.216  40        2000
cell09    0.083  0.014   0.055  0.111  52        1000
cell02    0.304  0.041   0.224  0.383  58        1000
cell04    0.244  0.038   0.169  0.319  41        2000
cell03    0.241  0.022   0.197  0.285  38        4000
```

While re-running with a tighter segmentation threshold for cell06, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.266, stderr 0.050, n = 40). While re-exporting the raw traces for cell14, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.125, stderr 0.015, n = 54). While auditing the holding potential column for cell04, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.184, stderr 0.010, n = 44). While segmenting epochs for cell19, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.229, stderr 0.016, n = 41). While re-running with a tighter segmentation threshold for cell06, the coefficient tracked epoch count more closely than duration (coefficient 0.158, stderr 0.044, n = 40). Flagging it so it does not get rediscovered next week.

While comparing per-cell orderings for cell03, nothing in the figure changed at print size (coefficient 0.303, stderr 0.025, n = 54). While comparing per-cell orderings for cell05, the estimate moved less than one standard error (coefficient 0.103, stderr 0.034, n = 58). While re-running with a tighter segmentation threshold for cell15, two cells fell out of the usable range (coefficient 0.171, stderr 0.040, n = 52). While checking residual autocorrelation for cell13, the ordering of cells was preserved (coefficient 0.235, stderr 0.049, n = 54). Noted and moved on; it does not change the decision.

### Step 14: segmenting epochs

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell17    0.231  0.039   0.155  0.307  46        500
cell02    0.159  0.037   0.087  0.231  39        4000
cell14    0.081  0.024   0.035  0.128  44        500
cell21    0.167  0.012   0.143  0.190  45        500
cell12    0.193  0.019   0.156  0.230  55        2000
cell11    0.121  0.038   0.046  0.195  56        4000
cell15    0.181  0.042   0.099  0.263  52        4000
cell24    0.171  0.032   0.109  0.233  39        2000
cell24    0.261  0.026   0.211  0.312  43        4000
cell05    0.210  0.016   0.179  0.242  44        4000
cell13    0.127  0.031   0.066  0.189  57        4000
cell19    0.214  0.042   0.132  0.296  56        2000
cell13    0.114  0.019   0.077  0.152  58        4000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell13    0.252  0.031   0.191  0.313  39        500
cell18    0.239  0.021   0.197  0.280  38        1000
cell21    0.112  0.034   0.045  0.179  55        2000
cell14    0.218  0.015   0.187  0.248  54        500
cell04    0.244  0.042   0.161  0.326  57        4000
cell15    0.303  0.044   0.216  0.389  46        4000
cell22    0.272  0.014   0.244  0.300  54        1000
cell10    0.125  0.039   0.048  0.202  55        500
cell08    0.141  0.020   0.102  0.180  54        4000
cell14    0.179  0.044   0.092  0.265  49        500
cell04    0.133  0.037   0.061  0.205  39        2000
cell03    0.101  0.046   0.011  0.191  54        500
cell24    0.162  0.028   0.107  0.216  43        1000
cell16    0.171  0.043   0.087  0.255  39        2000
```

### Step 15: re-exporting the raw traces

While re-running with a tighter segmentation threshold for cell19, the estimate moved less than one standard error (coefficient 0.187, stderr 0.046, n = 58). While re-exporting the raw traces for cell09, the ordering of cells was preserved (coefficient 0.110, stderr 0.018, n = 47). While auditing the holding potential column for cell21, the estimate moved less than one standard error (coefficient 0.154, stderr 0.048, n = 53). While auditing the holding potential column for cell22, the estimate moved less than one standard error (coefficient 0.096, stderr 0.042, n = 53). While bootstrapping the CI for cell23, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.168, stderr 0.036, n = 56). While bootstrapping the CI for cell15, the CI narrowed by roughly a tenth (coefficient 0.240, stderr 0.036, n = 58). Worth noting for the writeup, though not a result on its own.

While bootstrapping the CI for cell09, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.231, stderr 0.039, n = 38). While checking residual autocorrelation for cell14, nothing in the figure changed at print size (coefficient 0.294, stderr 0.046, n = 53). While re-running with a tighter segmentation threshold for cell03, the ordering of cells was preserved (coefficient 0.169, stderr 0.045, n = 52). While auditing the holding potential column for cell21, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.100, stderr 0.037, n = 47). While comparing per-cell orderings for cell02, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.232, stderr 0.034, n = 43). While checking residual autocorrelation for cell23, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.250, stderr 0.021, n = 58). Worth noting for the writeup, though not a result on its own.

While auditing the holding potential column for cell08, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.302, stderr 0.021, n = 44). While bootstrapping the CI for cell15, the ordering of cells was preserved (coefficient 0.272, stderr 0.029, n = 47). While bootstrapping the CI for cell12, the ordering of cells was preserved (coefficient 0.081, stderr 0.031, n = 50).

While comparing per-cell orderings for cell02, the ordering of cells was preserved (coefficient 0.186, stderr 0.017, n = 39). While bootstrapping the CI for cell05, the estimate moved less than one standard error (coefficient 0.239, stderr 0.015, n = 41). While re-exporting the raw traces for cell18, two cells fell out of the usable range (coefficient 0.248, stderr 0.020, n = 51). While segmenting epochs for cell08, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.283, stderr 0.030, n = 38). While re-running with a tighter segmentation threshold for cell08, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.138, stderr 0.038, n = 48). While re-exporting the raw traces for cell05, the estimate moved less than one standard error (coefficient 0.087, stderr 0.019, n = 56).

### Step 16: checking residual autocorrelation

While bootstrapping the CI for cell12, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.140, stderr 0.029, n = 52). While comparing per-cell orderings for cell05, the estimate moved less than one standard error (coefficient 0.093, stderr 0.021, n = 40). While re-running with a tighter segmentation threshold for cell24, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.083, stderr 0.028, n = 38). Worth noting for the writeup, though not a result on its own.

While re-running with a tighter segmentation threshold for cell15, the ordering of cells was preserved (coefficient 0.241, stderr 0.040, n = 45). While comparing per-cell orderings for cell10, the coefficient tracked epoch count more closely than duration (coefficient 0.225, stderr 0.031, n = 50). While fitting the one-lag kernel for cell21, the coefficient tracked epoch count more closely than duration (coefficient 0.261, stderr 0.027, n = 53). While fitting the one-lag kernel for cell02, two cells fell out of the usable range (coefficient 0.255, stderr 0.019, n = 40). While segmenting epochs for cell10, the estimate moved less than one standard error (coefficient 0.118, stderr 0.041, n = 57). While segmenting epochs for cell01, the CI narrowed by roughly a tenth (coefficient 0.127, stderr 0.036, n = 46).

```python
coefs = fit_per_cell(rows, threshold=0.63)
lo, hi = ci(coefs, seed=45)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 17: fitting the one-lag kernel

While fitting the one-lag kernel for cell16, nothing in the figure changed at print size (coefficient 0.242, stderr 0.026, n = 39). While auditing the holding potential column for cell10, the ordering of cells was preserved (coefficient 0.109, stderr 0.047, n = 47). While re-running with a tighter segmentation threshold for cell20, nothing in the figure changed at print size (coefficient 0.190, stderr 0.034, n = 46). While bootstrapping the CI for cell08, two cells fell out of the usable range (coefficient 0.102, stderr 0.029, n = 57). While re-exporting the raw traces for cell04, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.146, stderr 0.044, n = 46). Worth noting for the writeup, though not a result on its own.

```python
coefs = fit_per_cell(rows, threshold=0.74)
lo, hi = ci(coefs, seed=91)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```python
coefs = fit_per_cell(rows, threshold=0.36)
lo, hi = ci(coefs, seed=33)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While auditing the holding potential column for cell06, the CI narrowed by roughly a tenth (coefficient 0.250, stderr 0.031, n = 58). While bootstrapping the CI for cell22, the ordering of cells was preserved (coefficient 0.301, stderr 0.043, n = 47). While auditing the holding potential column for cell09, the ordering of cells was preserved (coefficient 0.201, stderr 0.020, n = 44).

### Step 18: segmenting epochs

While re-running with a tighter segmentation threshold for cell09, nothing in the figure changed at print size (coefficient 0.216, stderr 0.015, n = 55). While checking residual autocorrelation for cell07, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.140, stderr 0.012, n = 51). While re-running with a tighter segmentation threshold for cell05, the CI narrowed by roughly a tenth (coefficient 0.189, stderr 0.026, n = 48). While bootstrapping the CI for cell19, the ordering of cells was preserved (coefficient 0.245, stderr 0.012, n = 56). While comparing per-cell orderings for cell01, the estimate moved less than one standard error (coefficient 0.211, stderr 0.048, n = 53). While auditing the holding potential column for cell06, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.131, stderr 0.035, n = 54). Parking this until the re-segmentation lands.

While bootstrapping the CI for cell20, the ordering of cells was preserved (coefficient 0.299, stderr 0.011, n = 57). While re-running with a tighter segmentation threshold for cell14, two cells fell out of the usable range (coefficient 0.296, stderr 0.032, n = 54). While auditing the holding potential column for cell24, the ordering of cells was preserved (coefficient 0.127, stderr 0.044, n = 53). While segmenting epochs for cell23, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.296, stderr 0.049, n = 46). While bootstrapping the CI for cell23, the coefficient tracked epoch count more closely than duration (coefficient 0.202, stderr 0.012, n = 57). Parking this until the re-segmentation lands.

While fitting the one-lag kernel for cell19, the CI narrowed by roughly a tenth (coefficient 0.224, stderr 0.017, n = 47). While auditing the holding potential column for cell07, the ordering of cells was preserved (coefficient 0.102, stderr 0.039, n = 58). While fitting the one-lag kernel for cell21, two cells fell out of the usable range (coefficient 0.248, stderr 0.037, n = 58). While segmenting epochs for cell03, the estimate moved less than one standard error (coefficient 0.102, stderr 0.024, n = 58). While re-exporting the raw traces for cell12, the coefficient tracked epoch count more closely than duration (coefficient 0.121, stderr 0.019, n = 44).

### Step 19: auditing the holding potential column

While checking residual autocorrelation for cell07, the coefficient tracked epoch count more closely than duration (coefficient 0.181, stderr 0.012, n = 39). While segmenting epochs for cell16, the estimate moved less than one standard error (coefficient 0.113, stderr 0.036, n = 49). While fitting the one-lag kernel for cell04, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.283, stderr 0.028, n = 49). While re-running with a tighter segmentation threshold for cell20, nothing in the figure changed at print size (coefficient 0.217, stderr 0.034, n = 53). While checking residual autocorrelation for cell13, the estimate moved less than one standard error (coefficient 0.183, stderr 0.049, n = 43).

While segmenting epochs for cell12, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.180, stderr 0.031, n = 38). While bootstrapping the CI for cell10, the coefficient tracked epoch count more closely than duration (coefficient 0.238, stderr 0.014, n = 53). While segmenting epochs for cell12, nothing in the figure changed at print size (coefficient 0.085, stderr 0.014, n = 45). While segmenting epochs for cell23, two cells fell out of the usable range (coefficient 0.083, stderr 0.031, n = 45).

While re-exporting the raw traces for cell07, the ordering of cells was preserved (coefficient 0.157, stderr 0.031, n = 45). While comparing per-cell orderings for cell12, the coefficient tracked epoch count more closely than duration (coefficient 0.225, stderr 0.043, n = 51). While re-exporting the raw traces for cell24, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.088, stderr 0.036, n = 49). While bootstrapping the CI for cell22, the ordering of cells was preserved (coefficient 0.177, stderr 0.026, n = 46). While re-running with a tighter segmentation threshold for cell17, two cells fell out of the usable range (coefficient 0.235, stderr 0.047, n = 54). This is the part that will need a real statistical argument.

```python
coefs = fit_per_cell(rows, threshold=0.44)
lo, hi = ci(coefs, seed=98)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 20: re-running with a tighter segmentation threshold

While re-running with a tighter segmentation threshold for cell17, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.129, stderr 0.015, n = 41). While fitting the one-lag kernel for cell06, two cells fell out of the usable range (coefficient 0.309, stderr 0.030, n = 50). While comparing per-cell orderings for cell09, the ordering of cells was preserved (coefficient 0.238, stderr 0.022, n = 57).

While fitting the one-lag kernel for cell11, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.113, stderr 0.027, n = 47). While comparing per-cell orderings for cell19, the ordering of cells was preserved (coefficient 0.192, stderr 0.012, n = 53). While checking residual autocorrelation for cell23, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.127, stderr 0.014, n = 58).

```python
coefs = fit_per_cell(rows, threshold=0.79)
lo, hi = ci(coefs, seed=97)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 21: checking residual autocorrelation

While fitting the one-lag kernel for cell02, two cells fell out of the usable range (coefficient 0.308, stderr 0.021, n = 44). While bootstrapping the CI for cell16, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.143, stderr 0.047, n = 49). While checking residual autocorrelation for cell18, nothing in the figure changed at print size (coefficient 0.164, stderr 0.015, n = 53). While re-running with a tighter segmentation threshold for cell10, the ordering of cells was preserved (coefficient 0.306, stderr 0.045, n = 46). While bootstrapping the CI for cell11, the estimate moved less than one standard error (coefficient 0.296, stderr 0.034, n = 58). While comparing per-cell orderings for cell22, nothing in the figure changed at print size (coefficient 0.081, stderr 0.019, n = 39).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell16    0.282  0.046   0.191  0.372  57        500
cell15    0.115  0.031   0.054  0.176  42        4000
cell11    0.089  0.013   0.064  0.115  39        2000
cell14    0.288  0.034   0.222  0.354  47        1000
cell23    0.181  0.038   0.107  0.255  58        2000
cell10    0.178  0.042   0.095  0.261  40        500
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell22    0.216  0.030   0.157  0.274  58        1000
cell09    0.293  0.022   0.251  0.336  48        500
cell01    0.167  0.043   0.083  0.250  44        1000
cell16    0.117  0.049   0.020  0.213  44        2000
cell05    0.244  0.023   0.199  0.289  44        500
cell24    0.136  0.040   0.058  0.215  50        500
cell17    0.123  0.012   0.099  0.147  47        2000
cell11    0.220  0.034   0.154  0.287  48        2000
cell03    0.086  0.020   0.048  0.125  38        500
cell18    0.220  0.035   0.152  0.288  50        4000
cell09    0.172  0.020   0.133  0.211  38        1000
cell04    0.142  0.021   0.101  0.183  46        4000
cell21    0.258  0.028   0.203  0.313  57        2000
cell13    0.209  0.030   0.151  0.268  53        1000
```

While comparing per-cell orderings for cell02, nothing in the figure changed at print size (coefficient 0.129, stderr 0.011, n = 52). While comparing per-cell orderings for cell09, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.105, stderr 0.020, n = 51). While auditing the holding potential column for cell18, the coefficient tracked epoch count more closely than duration (coefficient 0.217, stderr 0.013, n = 58). While checking residual autocorrelation for cell05, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.188, stderr 0.028, n = 38). While re-running with a tighter segmentation threshold for cell16, two cells fell out of the usable range (coefficient 0.143, stderr 0.016, n = 44).

### Step 22: re-exporting the raw traces

While re-exporting the raw traces for cell21, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.121, stderr 0.025, n = 50). While re-running with a tighter segmentation threshold for cell23, nothing in the figure changed at print size (coefficient 0.111, stderr 0.011, n = 50). While checking residual autocorrelation for cell22, two cells fell out of the usable range (coefficient 0.231, stderr 0.014, n = 48). While re-exporting the raw traces for cell09, the CI narrowed by roughly a tenth (coefficient 0.204, stderr 0.045, n = 56). While checking residual autocorrelation for cell20, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.092, stderr 0.031, n = 55).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell03    0.262  0.044   0.175  0.349  49        2000
cell01    0.262  0.031   0.201  0.322  54        4000
cell12    0.228  0.019   0.190  0.266  53        500
cell01    0.279  0.017   0.245  0.313  45        1000
cell15    0.147  0.043   0.062  0.232  57        2000
cell01    0.185  0.040   0.106  0.263  39        500
cell03    0.154  0.018   0.118  0.190  52        500
cell08    0.124  0.025   0.075  0.173  51        1000
cell13    0.266  0.045   0.177  0.354  56        1000
```

### Step 23: re-running with a tighter segmentation threshold

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell06    0.227  0.025   0.178  0.277  44        4000
cell10    0.114  0.011   0.093  0.134  53        4000
cell13    0.271  0.039   0.195  0.347  55        2000
cell12    0.193  0.032   0.131  0.255  44        4000
cell06    0.177  0.016   0.146  0.208  49        1000
cell01    0.281  0.012   0.258  0.304  52        4000
cell15    0.105  0.049   0.009  0.201  55        2000
cell01    0.170  0.049   0.074  0.267  41        2000
cell19    0.275  0.034   0.208  0.343  44        2000
cell22    0.294  0.017   0.260  0.328  45        2000
cell20    0.303  0.045   0.214  0.392  49        2000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell12    0.219  0.047   0.127  0.311  44        1000
cell24    0.293  0.045   0.205  0.381  39        2000
cell10    0.115  0.044   0.028  0.202  58        500
cell12    0.210  0.021   0.168  0.252  51        1000
cell19    0.163  0.030   0.104  0.221  44        500
cell20    0.304  0.012   0.281  0.327  41        500
cell05    0.250  0.022   0.207  0.292  46        4000
cell02    0.190  0.028   0.134  0.245  50        1000
cell13    0.094  0.026   0.042  0.146  41        1000
cell01    0.112  0.011   0.090  0.133  57        2000
cell24    0.233  0.047   0.141  0.326  48        500
cell13    0.123  0.049   0.028  0.218  43        500
cell04    0.252  0.017   0.219  0.285  56        1000
```

While fitting the one-lag kernel for cell06, the coefficient tracked epoch count more closely than duration (coefficient 0.267, stderr 0.047, n = 45). While bootstrapping the CI for cell04, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.239, stderr 0.045, n = 58). While segmenting epochs for cell16, the CI narrowed by roughly a tenth (coefficient 0.244, stderr 0.049, n = 46). While comparing per-cell orderings for cell19, nothing in the figure changed at print size (coefficient 0.293, stderr 0.033, n = 38). While comparing per-cell orderings for cell05, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.148, stderr 0.042, n = 40). While checking residual autocorrelation for cell17, the coefficient tracked epoch count more closely than duration (coefficient 0.202, stderr 0.044, n = 47).

### Step 24: fitting the one-lag kernel

While fitting the one-lag kernel for cell06, the ordering of cells was preserved (coefficient 0.163, stderr 0.017, n = 38). While re-exporting the raw traces for cell02, the coefficient tracked epoch count more closely than duration (coefficient 0.181, stderr 0.013, n = 51). While re-running with a tighter segmentation threshold for cell07, two cells fell out of the usable range (coefficient 0.173, stderr 0.030, n = 39).

While segmenting epochs for cell12, nothing in the figure changed at print size (coefficient 0.237, stderr 0.019, n = 53). While segmenting epochs for cell12, two cells fell out of the usable range (coefficient 0.238, stderr 0.041, n = 52). While comparing per-cell orderings for cell18, the ordering of cells was preserved (coefficient 0.159, stderr 0.027, n = 42). While auditing the holding potential column for cell21, the coefficient tracked epoch count more closely than duration (coefficient 0.297, stderr 0.021, n = 55). While checking residual autocorrelation for cell02, the coefficient tracked epoch count more closely than duration (coefficient 0.197, stderr 0.037, n = 44). While bootstrapping the CI for cell22, the ordering of cells was preserved (coefficient 0.254, stderr 0.017, n = 43).

### Step 25: fitting the one-lag kernel

While re-running with a tighter segmentation threshold for cell08, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.182, stderr 0.011, n = 48). While fitting the one-lag kernel for cell12, the ordering of cells was preserved (coefficient 0.245, stderr 0.037, n = 53). While checking residual autocorrelation for cell22, two cells fell out of the usable range (coefficient 0.290, stderr 0.034, n = 39). While checking residual autocorrelation for cell19, nothing in the figure changed at print size (coefficient 0.194, stderr 0.017, n = 45). While re-exporting the raw traces for cell12, the coefficient tracked epoch count more closely than duration (coefficient 0.142, stderr 0.013, n = 49). Worth noting for the writeup, though not a result on its own.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell06    0.310  0.048   0.217  0.403  42        500
cell24    0.081  0.019   0.044  0.118  42        500
cell12    0.213  0.048   0.119  0.307  57        1000
cell21    0.160  0.042   0.077  0.242  52        1000
cell02    0.114  0.025   0.065  0.163  46        1000
cell14    0.233  0.017   0.201  0.266  53        4000
cell15    0.220  0.021   0.178  0.262  44        2000
cell03    0.252  0.018   0.216  0.289  43        1000
cell04    0.143  0.023   0.098  0.187  40        1000
cell09    0.245  0.016   0.213  0.277  50        500
cell05    0.220  0.022   0.177  0.264  48        4000
cell08    0.096  0.017   0.062  0.129  55        2000
cell03    0.221  0.012   0.197  0.246  52        500
```

### Step 26: comparing per-cell orderings

While bootstrapping the CI for cell06, nothing in the figure changed at print size (coefficient 0.262, stderr 0.050, n = 51). While auditing the holding potential column for cell06, nothing in the figure changed at print size (coefficient 0.243, stderr 0.032, n = 56). While fitting the one-lag kernel for cell24, the CI narrowed by roughly a tenth (coefficient 0.144, stderr 0.016, n = 38). While segmenting epochs for cell17, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.143, stderr 0.020, n = 42). Parking this until the re-segmentation lands.

While fitting the one-lag kernel for cell17, the CI narrowed by roughly a tenth (coefficient 0.197, stderr 0.028, n = 40). While re-exporting the raw traces for cell05, the ordering of cells was preserved (coefficient 0.263, stderr 0.042, n = 57). While checking residual autocorrelation for cell02, the estimate moved less than one standard error (coefficient 0.140, stderr 0.028, n = 51). While segmenting epochs for cell05, the estimate moved less than one standard error (coefficient 0.251, stderr 0.011, n = 39). While checking residual autocorrelation for cell02, the coefficient tracked epoch count more closely than duration (coefficient 0.194, stderr 0.030, n = 50). While checking residual autocorrelation for cell21, the coefficient tracked epoch count more closely than duration (coefficient 0.187, stderr 0.017, n = 47). Noted and moved on; it does not change the decision.

While bootstrapping the CI for cell20, the ordering of cells was preserved (coefficient 0.086, stderr 0.049, n = 54). While segmenting epochs for cell22, the estimate moved less than one standard error (coefficient 0.297, stderr 0.020, n = 53). While fitting the one-lag kernel for cell14, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.146, stderr 0.021, n = 44). While fitting the one-lag kernel for cell17, the estimate moved less than one standard error (coefficient 0.185, stderr 0.023, n = 49).

### Step 27: re-exporting the raw traces

While auditing the holding potential column for cell09, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.167, stderr 0.024, n = 46). While checking residual autocorrelation for cell10, the ordering of cells was preserved (coefficient 0.155, stderr 0.044, n = 46). While re-exporting the raw traces for cell15, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.216, stderr 0.046, n = 44). While checking residual autocorrelation for cell07, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.107, stderr 0.042, n = 43). While re-running with a tighter segmentation threshold for cell17, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.266, stderr 0.046, n = 50). While comparing per-cell orderings for cell17, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.100, stderr 0.029, n = 48). This is the part that will need a real statistical argument.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell12    0.292  0.019   0.255  0.329  45        2000
cell11    0.272  0.026   0.220  0.324  45        4000
cell21    0.304  0.042   0.223  0.386  53        2000
cell14    0.302  0.041   0.221  0.383  42        2000
cell10    0.272  0.043   0.188  0.357  46        500
cell23    0.115  0.043   0.030  0.200  48        500
```

While re-exporting the raw traces for cell20, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.217, stderr 0.046, n = 58). While segmenting epochs for cell12, the coefficient tracked epoch count more closely than duration (coefficient 0.272, stderr 0.050, n = 54). While re-running with a tighter segmentation threshold for cell13, the CI narrowed by roughly a tenth (coefficient 0.248, stderr 0.042, n = 50). While bootstrapping the CI for cell08, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.116, stderr 0.045, n = 44).

```python
coefs = fit_per_cell(rows, threshold=0.49)
lo, hi = ci(coefs, seed=37)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 28: auditing the holding potential column

While re-exporting the raw traces for cell07, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.138, stderr 0.050, n = 41). While re-exporting the raw traces for cell14, the ordering of cells was preserved (coefficient 0.178, stderr 0.016, n = 52). While segmenting epochs for cell05, the ordering of cells was preserved (coefficient 0.202, stderr 0.015, n = 40). This is the part that will need a real statistical argument.

```python
coefs = fit_per_cell(rows, threshold=0.77)
lo, hi = ci(coefs, seed=58)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 29: auditing the holding potential column

While checking residual autocorrelation for cell03, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.195, stderr 0.029, n = 40). While bootstrapping the CI for cell06, the ordering of cells was preserved (coefficient 0.253, stderr 0.015, n = 42). While re-running with a tighter segmentation threshold for cell12, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.235, stderr 0.040, n = 43). While segmenting epochs for cell06, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.192, stderr 0.011, n = 58). While auditing the holding potential column for cell12, the CI narrowed by roughly a tenth (coefficient 0.308, stderr 0.012, n = 44). While checking residual autocorrelation for cell06, the estimate moved less than one standard error (coefficient 0.096, stderr 0.014, n = 49). Parking this until the re-segmentation lands.

While bootstrapping the CI for cell12, the coefficient tracked epoch count more closely than duration (coefficient 0.213, stderr 0.013, n = 55). While re-exporting the raw traces for cell18, the estimate moved less than one standard error (coefficient 0.118, stderr 0.043, n = 39). While bootstrapping the CI for cell06, the coefficient tracked epoch count more closely than duration (coefficient 0.187, stderr 0.016, n = 50). While re-exporting the raw traces for cell13, two cells fell out of the usable range (coefficient 0.236, stderr 0.044, n = 46). While fitting the one-lag kernel for cell19, the coefficient tracked epoch count more closely than duration (coefficient 0.153, stderr 0.013, n = 47). Parking this until the re-segmentation lands.

While comparing per-cell orderings for cell05, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.161, stderr 0.016, n = 44). While re-exporting the raw traces for cell23, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.249, stderr 0.024, n = 55). While segmenting epochs for cell22, the coefficient tracked epoch count more closely than duration (coefficient 0.283, stderr 0.026, n = 46). While auditing the holding potential column for cell20, the CI narrowed by roughly a tenth (coefficient 0.155, stderr 0.031, n = 51).

### Step 30: comparing per-cell orderings

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell02    0.147  0.034   0.080  0.214  45        2000
cell20    0.171  0.024   0.124  0.219  49        2000
cell09    0.218  0.014   0.189  0.246  58        2000
cell04    0.117  0.037   0.046  0.189  56        1000
cell19    0.280  0.022   0.237  0.323  42        1000
cell09    0.167  0.023   0.122  0.213  55        500
cell15    0.282  0.010   0.262  0.302  45        500
cell22    0.136  0.028   0.080  0.191  54        500
cell12    0.158  0.013   0.133  0.183  58        2000
cell14    0.138  0.010   0.117  0.158  38        1000
cell17    0.289  0.013   0.264  0.315  39        4000
cell14    0.235  0.042   0.152  0.318  47        4000
cell05    0.185  0.031   0.125  0.246  42        4000
```

While fitting the one-lag kernel for cell04, the estimate moved less than one standard error (coefficient 0.085, stderr 0.044, n = 43). While comparing per-cell orderings for cell23, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.285, stderr 0.035, n = 39). While checking residual autocorrelation for cell18, the ordering of cells was preserved (coefficient 0.269, stderr 0.035, n = 57). While comparing per-cell orderings for cell18, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.306, stderr 0.017, n = 50). While checking residual autocorrelation for cell23, the CI narrowed by roughly a tenth (coefficient 0.309, stderr 0.045, n = 42).

While comparing per-cell orderings for cell11, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.231, stderr 0.048, n = 57). While re-exporting the raw traces for cell09, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.157, stderr 0.035, n = 41). While auditing the holding potential column for cell01, nothing in the figure changed at print size (coefficient 0.191, stderr 0.034, n = 40).

While re-running with a tighter segmentation threshold for cell17, the CI narrowed by roughly a tenth (coefficient 0.252, stderr 0.039, n = 58). While re-running with a tighter segmentation threshold for cell05, two cells fell out of the usable range (coefficient 0.295, stderr 0.042, n = 41). While fitting the one-lag kernel for cell01, the estimate moved less than one standard error (coefficient 0.143, stderr 0.046, n = 38). While re-exporting the raw traces for cell24, the CI narrowed by roughly a tenth (coefficient 0.273, stderr 0.030, n = 48).

### Step 31: auditing the holding potential column

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell03    0.102  0.017   0.069  0.135  48        4000
cell11    0.103  0.041   0.023  0.184  42        500
cell14    0.143  0.013   0.118  0.167  38        1000
cell18    0.186  0.035   0.116  0.255  40        500
cell14    0.111  0.047   0.019  0.203  40        4000
cell22    0.203  0.031   0.143  0.264  48        4000
cell23    0.278  0.044   0.193  0.364  49        4000
cell14    0.147  0.049   0.051  0.242  52        2000
cell09    0.090  0.012   0.067  0.114  40        4000
cell14    0.237  0.015   0.207  0.266  50        500
cell22    0.250  0.043   0.165  0.334  57        2000
```

While segmenting epochs for cell16, two cells fell out of the usable range (coefficient 0.221, stderr 0.045, n = 54). While comparing per-cell orderings for cell23, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.181, stderr 0.040, n = 48). While re-exporting the raw traces for cell19, the estimate moved less than one standard error (coefficient 0.285, stderr 0.020, n = 52). While segmenting epochs for cell20, the coefficient tracked epoch count more closely than duration (coefficient 0.239, stderr 0.046, n = 41). While auditing the holding potential column for cell24, two cells fell out of the usable range (coefficient 0.087, stderr 0.038, n = 46). While comparing per-cell orderings for cell22, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.102, stderr 0.021, n = 38).

```python
coefs = fit_per_cell(rows, threshold=0.72)
lo, hi = ci(coefs, seed=28)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While segmenting epochs for cell11, two cells fell out of the usable range (coefficient 0.118, stderr 0.022, n = 53). While fitting the one-lag kernel for cell24, nothing in the figure changed at print size (coefficient 0.229, stderr 0.042, n = 39). While re-exporting the raw traces for cell18, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.146, stderr 0.035, n = 53).

### Step 32: fitting the one-lag kernel

While fitting the one-lag kernel for cell24, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.237, stderr 0.015, n = 47). While bootstrapping the CI for cell06, nothing in the figure changed at print size (coefficient 0.202, stderr 0.022, n = 55). While auditing the holding potential column for cell24, two cells fell out of the usable range (coefficient 0.280, stderr 0.036, n = 46). While segmenting epochs for cell15, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.130, stderr 0.038, n = 46).

While re-exporting the raw traces for cell11, the coefficient tracked epoch count more closely than duration (coefficient 0.219, stderr 0.045, n = 56). While comparing per-cell orderings for cell22, the CI narrowed by roughly a tenth (coefficient 0.306, stderr 0.045, n = 58). While re-exporting the raw traces for cell10, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.205, stderr 0.046, n = 57). While auditing the holding potential column for cell07, the coefficient tracked epoch count more closely than duration (coefficient 0.165, stderr 0.015, n = 45). While fitting the one-lag kernel for cell16, the CI narrowed by roughly a tenth (coefficient 0.207, stderr 0.022, n = 57). While re-exporting the raw traces for cell14, two cells fell out of the usable range (coefficient 0.104, stderr 0.034, n = 58).

### Step 33: bootstrapping the CI

While auditing the holding potential column for cell24, the coefficient tracked epoch count more closely than duration (coefficient 0.090, stderr 0.045, n = 54). While auditing the holding potential column for cell04, the ordering of cells was preserved (coefficient 0.209, stderr 0.030, n = 49). While re-exporting the raw traces for cell14, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.269, stderr 0.027, n = 51). While auditing the holding potential column for cell03, the CI narrowed by roughly a tenth (coefficient 0.223, stderr 0.050, n = 45).

```python
coefs = fit_per_cell(rows, threshold=0.78)
lo, hi = ci(coefs, seed=27)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell08    0.306  0.044   0.221  0.392  53        1000
cell21    0.295  0.046   0.206  0.385  43        2000
cell16    0.112  0.045   0.024  0.200  44        2000
cell23    0.116  0.015   0.087  0.146  48        1000
cell20    0.267  0.038   0.193  0.342  52        500
cell12    0.217  0.019   0.180  0.255  40        500
cell15    0.248  0.034   0.182  0.314  38        4000
cell19    0.179  0.022   0.136  0.222  50        4000
cell15    0.239  0.022   0.195  0.282  39        500
```

### Step 34: checking residual autocorrelation

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell12    0.129  0.049   0.034  0.225  53        4000
cell21    0.188  0.043   0.105  0.272  51        1000
cell08    0.240  0.041   0.160  0.319  47        2000
cell23    0.279  0.034   0.213  0.345  47        4000
cell19    0.189  0.046   0.099  0.279  58        1000
cell07    0.189  0.020   0.150  0.227  38        2000
cell13    0.281  0.032   0.218  0.344  42        2000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell14    0.086  0.014   0.058  0.114  54        4000
cell08    0.116  0.031   0.055  0.177  44        500
cell14    0.209  0.015   0.180  0.239  52        2000
cell20    0.174  0.021   0.134  0.215  54        4000
cell04    0.302  0.018   0.266  0.338  39        4000
cell23    0.182  0.022   0.138  0.226  53        1000
cell16    0.141  0.044   0.055  0.227  42        2000
cell08    0.163  0.048   0.069  0.257  58        1000
cell19    0.107  0.040   0.028  0.185  43        2000
```

While re-running with a tighter segmentation threshold for cell13, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.204, stderr 0.029, n = 50). While checking residual autocorrelation for cell20, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.153, stderr 0.038, n = 57). While re-exporting the raw traces for cell03, the estimate moved less than one standard error (coefficient 0.126, stderr 0.012, n = 56). While re-exporting the raw traces for cell15, the coefficient tracked epoch count more closely than duration (coefficient 0.126, stderr 0.026, n = 48).

While fitting the one-lag kernel for cell17, the estimate moved less than one standard error (coefficient 0.300, stderr 0.043, n = 53). While comparing per-cell orderings for cell07, nothing in the figure changed at print size (coefficient 0.189, stderr 0.044, n = 46). While segmenting epochs for cell12, nothing in the figure changed at print size (coefficient 0.226, stderr 0.045, n = 48). While re-running with a tighter segmentation threshold for cell12, the coefficient tracked epoch count more closely than duration (coefficient 0.170, stderr 0.034, n = 39). While checking residual autocorrelation for cell20, two cells fell out of the usable range (coefficient 0.185, stderr 0.038, n = 51).

### Step 35: checking residual autocorrelation

While re-exporting the raw traces for cell20, nothing in the figure changed at print size (coefficient 0.302, stderr 0.030, n = 48). While auditing the holding potential column for cell20, the coefficient tracked epoch count more closely than duration (coefficient 0.183, stderr 0.043, n = 47). While re-running with a tighter segmentation threshold for cell11, the ordering of cells was preserved (coefficient 0.205, stderr 0.046, n = 58). While auditing the holding potential column for cell20, nothing in the figure changed at print size (coefficient 0.191, stderr 0.019, n = 53).

While re-running with a tighter segmentation threshold for cell14, the estimate moved less than one standard error (coefficient 0.139, stderr 0.032, n = 54). While bootstrapping the CI for cell24, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.281, stderr 0.027, n = 54). While re-running with a tighter segmentation threshold for cell21, nothing in the figure changed at print size (coefficient 0.291, stderr 0.046, n = 51). While checking residual autocorrelation for cell15, the coefficient tracked epoch count more closely than duration (coefficient 0.206, stderr 0.023, n = 40). While checking residual autocorrelation for cell13, the CI narrowed by roughly a tenth (coefficient 0.100, stderr 0.028, n = 56). While re-exporting the raw traces for cell10, nothing in the figure changed at print size (coefficient 0.146, stderr 0.019, n = 49).

While comparing per-cell orderings for cell02, the coefficient tracked epoch count more closely than duration (coefficient 0.177, stderr 0.033, n = 49). While fitting the one-lag kernel for cell13, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.132, stderr 0.017, n = 38). While re-exporting the raw traces for cell16, two cells fell out of the usable range (coefficient 0.220, stderr 0.011, n = 56). Flagging it so it does not get rediscovered next week.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell13    0.152  0.036   0.082  0.223  41        4000
cell14    0.122  0.025   0.074  0.170  49        4000
cell05    0.115  0.039   0.038  0.191  53        1000
cell11    0.158  0.040   0.080  0.237  40        4000
cell01    0.277  0.010   0.257  0.296  49        500
cell16    0.103  0.035   0.034  0.172  53        4000
cell19    0.134  0.045   0.047  0.221  45        500
cell06    0.172  0.017   0.139  0.206  41        4000
```

### Step 36: comparing per-cell orderings

While fitting the one-lag kernel for cell10, the estimate moved less than one standard error (coefficient 0.237, stderr 0.016, n = 43). While checking residual autocorrelation for cell11, two cells fell out of the usable range (coefficient 0.248, stderr 0.023, n = 44). While comparing per-cell orderings for cell24, the coefficient tracked epoch count more closely than duration (coefficient 0.175, stderr 0.019, n = 40).

While checking residual autocorrelation for cell05, the estimate moved less than one standard error (coefficient 0.171, stderr 0.037, n = 47). While segmenting epochs for cell10, nothing in the figure changed at print size (coefficient 0.218, stderr 0.020, n = 54). While auditing the holding potential column for cell05, the coefficient tracked epoch count more closely than duration (coefficient 0.233, stderr 0.021, n = 50). While auditing the holding potential column for cell21, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.164, stderr 0.028, n = 56).

### Step 37: segmenting epochs

```python
coefs = fit_per_cell(rows, threshold=0.53)
lo, hi = ci(coefs, seed=73)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```python
coefs = fit_per_cell(rows, threshold=0.33)
lo, hi = ci(coefs, seed=83)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While re-running with a tighter segmentation threshold for cell02, nothing in the figure changed at print size (coefficient 0.241, stderr 0.042, n = 45). While fitting the one-lag kernel for cell18, the coefficient tracked epoch count more closely than duration (coefficient 0.159, stderr 0.043, n = 48). While auditing the holding potential column for cell20, the estimate moved less than one standard error (coefficient 0.244, stderr 0.022, n = 45). While fitting the one-lag kernel for cell01, the ordering of cells was preserved (coefficient 0.170, stderr 0.010, n = 57). While bootstrapping the CI for cell02, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.252, stderr 0.047, n = 50).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell09    0.086  0.026   0.035  0.137  41        500
cell06    0.264  0.035   0.195  0.333  57        2000
cell20    0.266  0.028   0.210  0.322  46        4000
cell24    0.168  0.045   0.080  0.255  40        500
cell01    0.284  0.013   0.259  0.309  40        1000
cell12    0.238  0.025   0.189  0.287  55        2000
cell09    0.238  0.022   0.195  0.281  49        4000
cell23    0.142  0.031   0.082  0.201  55        2000
cell07    0.181  0.030   0.123  0.239  44        4000
cell10    0.248  0.025   0.199  0.297  38        1000
```

