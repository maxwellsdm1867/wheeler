# Prior session 19 of 20

Transcript of an earlier working session on the history-kernel analysis.

### Step 1: checking residual autocorrelation

While fitting the one-lag kernel for cell06, two cells fell out of the usable range (coefficient 0.211, stderr 0.035, n = 50). While segmenting epochs for cell16, the estimate moved less than one standard error (coefficient 0.087, stderr 0.049, n = 56). While fitting the one-lag kernel for cell01, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.206, stderr 0.010, n = 50). While comparing per-cell orderings for cell17, the coefficient tracked epoch count more closely than duration (coefficient 0.303, stderr 0.050, n = 53). This is the part that will need a real statistical argument.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell14    0.158  0.045   0.071  0.245  51        500
cell23    0.122  0.026   0.071  0.172  51        2000
cell10    0.301  0.034   0.234  0.368  57        1000
cell09    0.127  0.024   0.079  0.175  48        4000
cell21    0.276  0.016   0.244  0.307  56        4000
cell01    0.177  0.020   0.139  0.216  57        4000
cell05    0.232  0.044   0.145  0.318  53        2000
cell22    0.082  0.045   -0.005  0.170  39        500
cell03    0.185  0.028   0.130  0.240  50        2000
cell04    0.128  0.033   0.063  0.193  44        1000
cell18    0.163  0.036   0.092  0.235  43        2000
cell15    0.153  0.045   0.065  0.242  54        2000
```

### Step 2: comparing per-cell orderings

While segmenting epochs for cell02, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.169, stderr 0.028, n = 50). While re-exporting the raw traces for cell12, the estimate moved less than one standard error (coefficient 0.093, stderr 0.048, n = 46). While checking residual autocorrelation for cell10, nothing in the figure changed at print size (coefficient 0.169, stderr 0.049, n = 41). While segmenting epochs for cell01, nothing in the figure changed at print size (coefficient 0.136, stderr 0.037, n = 43). While auditing the holding potential column for cell20, the estimate moved less than one standard error (coefficient 0.268, stderr 0.012, n = 44). While comparing per-cell orderings for cell18, the CI narrowed by roughly a tenth (coefficient 0.097, stderr 0.046, n = 51).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell08    0.224  0.012   0.200  0.248  42        2000
cell24    0.233  0.033   0.169  0.297  38        500
cell12    0.241  0.024   0.193  0.289  49        4000
cell24    0.306  0.044   0.219  0.393  39        2000
cell06    0.168  0.049   0.072  0.263  58        1000
cell21    0.244  0.024   0.198  0.291  52        2000
cell13    0.135  0.040   0.057  0.212  54        500
cell03    0.099  0.023   0.054  0.144  57        1000
cell24    0.147  0.046   0.057  0.238  48        2000
```

While comparing per-cell orderings for cell13, the ordering of cells was preserved (coefficient 0.297, stderr 0.047, n = 54). While bootstrapping the CI for cell07, nothing in the figure changed at print size (coefficient 0.116, stderr 0.040, n = 54). While comparing per-cell orderings for cell20, the ordering of cells was preserved (coefficient 0.214, stderr 0.015, n = 46). This is the part that will need a real statistical argument.

### Step 3: checking residual autocorrelation

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell11    0.198  0.012   0.176  0.221  43        2000
cell19    0.177  0.021   0.135  0.219  42        2000
cell02    0.304  0.035   0.235  0.372  51        2000
cell23    0.091  0.029   0.033  0.148  44        2000
cell03    0.294  0.042   0.211  0.378  51        2000
cell10    0.217  0.048   0.123  0.311  39        2000
cell18    0.296  0.015   0.267  0.324  45        500
cell16    0.299  0.036   0.228  0.370  55        2000
```

While re-exporting the raw traces for cell06, two cells fell out of the usable range (coefficient 0.302, stderr 0.033, n = 42). While bootstrapping the CI for cell02, nothing in the figure changed at print size (coefficient 0.275, stderr 0.034, n = 56). While fitting the one-lag kernel for cell04, the CI narrowed by roughly a tenth (coefficient 0.276, stderr 0.022, n = 49). While bootstrapping the CI for cell10, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.166, stderr 0.034, n = 44). Worth noting for the writeup, though not a result on its own.

While re-running with a tighter segmentation threshold for cell10, the CI narrowed by roughly a tenth (coefficient 0.248, stderr 0.042, n = 48). While re-exporting the raw traces for cell20, nothing in the figure changed at print size (coefficient 0.099, stderr 0.031, n = 58). While auditing the holding potential column for cell24, the coefficient tracked epoch count more closely than duration (coefficient 0.115, stderr 0.021, n = 50).

```python
coefs = fit_per_cell(rows, threshold=0.69)
lo, hi = ci(coefs, seed=22)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 4: re-exporting the raw traces

While checking residual autocorrelation for cell07, the CI narrowed by roughly a tenth (coefficient 0.126, stderr 0.022, n = 58). While auditing the holding potential column for cell21, the coefficient tracked epoch count more closely than duration (coefficient 0.131, stderr 0.027, n = 57). While checking residual autocorrelation for cell11, the ordering of cells was preserved (coefficient 0.266, stderr 0.023, n = 44). While auditing the holding potential column for cell13, the coefficient tracked epoch count more closely than duration (coefficient 0.139, stderr 0.036, n = 54). While auditing the holding potential column for cell06, the estimate moved less than one standard error (coefficient 0.302, stderr 0.013, n = 42). While re-running with a tighter segmentation threshold for cell09, the CI narrowed by roughly a tenth (coefficient 0.255, stderr 0.045, n = 44). Parking this until the re-segmentation lands.

While segmenting epochs for cell21, the estimate moved less than one standard error (coefficient 0.216, stderr 0.040, n = 57). While re-exporting the raw traces for cell03, two cells fell out of the usable range (coefficient 0.144, stderr 0.018, n = 48). While bootstrapping the CI for cell22, the estimate moved less than one standard error (coefficient 0.243, stderr 0.049, n = 57). While fitting the one-lag kernel for cell15, the CI narrowed by roughly a tenth (coefficient 0.260, stderr 0.046, n = 55). While re-exporting the raw traces for cell18, two cells fell out of the usable range (coefficient 0.205, stderr 0.046, n = 56). While bootstrapping the CI for cell04, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.273, stderr 0.020, n = 53).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell14    0.156  0.039   0.079  0.233  38        2000
cell12    0.087  0.015   0.057  0.117  42        2000
cell13    0.111  0.043   0.026  0.196  43        1000
cell07    0.252  0.014   0.224  0.281  56        4000
cell03    0.168  0.019   0.131  0.205  47        500
cell20    0.081  0.033   0.015  0.146  58        4000
cell02    0.127  0.041   0.047  0.207  46        2000
cell13    0.257  0.024   0.210  0.304  52        500
cell17    0.226  0.046   0.137  0.316  46        2000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell23    0.255  0.032   0.192  0.318  39        500
cell13    0.243  0.035   0.175  0.311  54        1000
cell04    0.103  0.015   0.074  0.131  54        500
cell16    0.160  0.014   0.132  0.188  43        2000
cell19    0.113  0.028   0.059  0.167  38        500
cell06    0.168  0.045   0.081  0.256  38        2000
cell05    0.211  0.034   0.144  0.277  39        500
cell01    0.279  0.036   0.209  0.350  39        4000
cell09    0.242  0.023   0.197  0.287  52        2000
cell10    0.280  0.019   0.242  0.317  42        1000
```

### Step 5: comparing per-cell orderings

```python
coefs = fit_per_cell(rows, threshold=0.62)
lo, hi = ci(coefs, seed=37)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While fitting the one-lag kernel for cell03, the estimate moved less than one standard error (coefficient 0.272, stderr 0.035, n = 39). While re-running with a tighter segmentation threshold for cell21, the ordering of cells was preserved (coefficient 0.278, stderr 0.036, n = 42). While auditing the holding potential column for cell24, the estimate moved less than one standard error (coefficient 0.195, stderr 0.049, n = 54). While segmenting epochs for cell11, the CI narrowed by roughly a tenth (coefficient 0.295, stderr 0.022, n = 54).

While segmenting epochs for cell22, the ordering of cells was preserved (coefficient 0.284, stderr 0.042, n = 57). While comparing per-cell orderings for cell22, the ordering of cells was preserved (coefficient 0.101, stderr 0.049, n = 54). While bootstrapping the CI for cell11, the CI narrowed by roughly a tenth (coefficient 0.199, stderr 0.035, n = 54). While auditing the holding potential column for cell24, the CI narrowed by roughly a tenth (coefficient 0.152, stderr 0.023, n = 47). While checking residual autocorrelation for cell16, the CI narrowed by roughly a tenth (coefficient 0.114, stderr 0.040, n = 50). While re-exporting the raw traces for cell05, the estimate moved less than one standard error (coefficient 0.142, stderr 0.039, n = 52).

While bootstrapping the CI for cell13, two cells fell out of the usable range (coefficient 0.120, stderr 0.040, n = 47). While comparing per-cell orderings for cell11, the estimate moved less than one standard error (coefficient 0.158, stderr 0.046, n = 39). While bootstrapping the CI for cell02, nothing in the figure changed at print size (coefficient 0.231, stderr 0.010, n = 41). While auditing the holding potential column for cell24, the CI narrowed by roughly a tenth (coefficient 0.170, stderr 0.034, n = 45). While auditing the holding potential column for cell07, the coefficient tracked epoch count more closely than duration (coefficient 0.264, stderr 0.011, n = 55). While comparing per-cell orderings for cell21, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.205, stderr 0.024, n = 40). Parking this until the re-segmentation lands.

### Step 6: bootstrapping the CI

While comparing per-cell orderings for cell22, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.097, stderr 0.020, n = 42). While re-running with a tighter segmentation threshold for cell03, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.213, stderr 0.014, n = 43). While segmenting epochs for cell14, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.269, stderr 0.027, n = 41). While fitting the one-lag kernel for cell17, two cells fell out of the usable range (coefficient 0.100, stderr 0.012, n = 39). While fitting the one-lag kernel for cell09, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.282, stderr 0.044, n = 52). While re-exporting the raw traces for cell07, two cells fell out of the usable range (coefficient 0.151, stderr 0.020, n = 42).

While fitting the one-lag kernel for cell16, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.188, stderr 0.039, n = 47). While auditing the holding potential column for cell05, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.304, stderr 0.027, n = 53). While comparing per-cell orderings for cell17, nothing in the figure changed at print size (coefficient 0.171, stderr 0.016, n = 38). Noted and moved on; it does not change the decision.

### Step 7: comparing per-cell orderings

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell07    0.292  0.038   0.217  0.366  47        500
cell19    0.193  0.019   0.155  0.230  50        500
cell01    0.116  0.045   0.028  0.205  38        500
cell07    0.306  0.013   0.281  0.332  38        1000
cell05    0.175  0.025   0.127  0.223  45        2000
cell03    0.241  0.023   0.196  0.285  52        4000
cell15    0.161  0.047   0.069  0.253  41        4000
```

While fitting the one-lag kernel for cell20, the CI narrowed by roughly a tenth (coefficient 0.192, stderr 0.031, n = 48). While comparing per-cell orderings for cell19, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.125, stderr 0.030, n = 44). While bootstrapping the CI for cell22, the CI narrowed by roughly a tenth (coefficient 0.091, stderr 0.017, n = 48). While auditing the holding potential column for cell12, nothing in the figure changed at print size (coefficient 0.132, stderr 0.049, n = 39). While re-running with a tighter segmentation threshold for cell05, the estimate moved less than one standard error (coefficient 0.152, stderr 0.027, n = 38).

### Step 8: re-running with a tighter segmentation threshold

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell10    0.189  0.019   0.151  0.226  38        2000
cell18    0.250  0.048   0.156  0.344  46        4000
cell02    0.142  0.050   0.045  0.240  48        1000
cell21    0.101  0.035   0.033  0.169  51        2000
cell09    0.169  0.021   0.128  0.210  48        2000
cell16    0.208  0.035   0.139  0.277  44        500
cell16    0.228  0.011   0.205  0.250  53        2000
cell24    0.279  0.032   0.216  0.342  58        1000
cell10    0.080  0.030   0.021  0.140  44        4000
```

While checking residual autocorrelation for cell02, the ordering of cells was preserved (coefficient 0.301, stderr 0.015, n = 40). While comparing per-cell orderings for cell22, the ordering of cells was preserved (coefficient 0.203, stderr 0.012, n = 40). While re-exporting the raw traces for cell14, the ordering of cells was preserved (coefficient 0.275, stderr 0.021, n = 48). While auditing the holding potential column for cell11, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.246, stderr 0.033, n = 46). While re-running with a tighter segmentation threshold for cell09, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.098, stderr 0.035, n = 51). While re-exporting the raw traces for cell07, the coefficient tracked epoch count more closely than duration (coefficient 0.111, stderr 0.025, n = 41).

### Step 9: auditing the holding potential column

While fitting the one-lag kernel for cell08, the coefficient tracked epoch count more closely than duration (coefficient 0.289, stderr 0.044, n = 54). While re-running with a tighter segmentation threshold for cell06, the estimate moved less than one standard error (coefficient 0.200, stderr 0.031, n = 39). While re-exporting the raw traces for cell04, two cells fell out of the usable range (coefficient 0.097, stderr 0.040, n = 44). While bootstrapping the CI for cell18, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.269, stderr 0.017, n = 41). Flagging it so it does not get rediscovered next week.

While checking residual autocorrelation for cell02, the CI narrowed by roughly a tenth (coefficient 0.217, stderr 0.048, n = 52). While bootstrapping the CI for cell12, the coefficient tracked epoch count more closely than duration (coefficient 0.307, stderr 0.040, n = 52). While comparing per-cell orderings for cell12, the coefficient tracked epoch count more closely than duration (coefficient 0.119, stderr 0.025, n = 50).

While auditing the holding potential column for cell24, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.097, stderr 0.012, n = 46). While checking residual autocorrelation for cell10, the estimate moved less than one standard error (coefficient 0.128, stderr 0.041, n = 53). While fitting the one-lag kernel for cell10, the estimate moved less than one standard error (coefficient 0.230, stderr 0.031, n = 50). While checking residual autocorrelation for cell03, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.266, stderr 0.049, n = 44). While comparing per-cell orderings for cell13, the CI narrowed by roughly a tenth (coefficient 0.220, stderr 0.020, n = 57). While segmenting epochs for cell12, nothing in the figure changed at print size (coefficient 0.246, stderr 0.047, n = 47). Noted and moved on; it does not change the decision.

While fitting the one-lag kernel for cell21, the coefficient tracked epoch count more closely than duration (coefficient 0.208, stderr 0.028, n = 41). While re-running with a tighter segmentation threshold for cell03, nothing in the figure changed at print size (coefficient 0.112, stderr 0.012, n = 46). While auditing the holding potential column for cell02, nothing in the figure changed at print size (coefficient 0.229, stderr 0.035, n = 40). While checking residual autocorrelation for cell11, the ordering of cells was preserved (coefficient 0.240, stderr 0.048, n = 53). This is the part that will need a real statistical argument.

### Step 10: auditing the holding potential column

While checking residual autocorrelation for cell11, the coefficient tracked epoch count more closely than duration (coefficient 0.134, stderr 0.022, n = 55). While segmenting epochs for cell06, the ordering of cells was preserved (coefficient 0.179, stderr 0.035, n = 49). While checking residual autocorrelation for cell06, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.126, stderr 0.032, n = 41). This is the part that will need a real statistical argument.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell09    0.106  0.035   0.038  0.174  39        1000
cell09    0.205  0.022   0.161  0.248  46        2000
cell05    0.201  0.041   0.120  0.281  42        2000
cell07    0.272  0.020   0.233  0.312  40        4000
cell12    0.190  0.033   0.127  0.254  42        4000
cell11    0.209  0.016   0.177  0.241  52        1000
cell02    0.196  0.025   0.146  0.245  41        2000
cell23    0.119  0.010   0.100  0.139  43        1000
cell12    0.171  0.014   0.144  0.197  48        1000
cell19    0.173  0.013   0.148  0.198  49        2000
cell11    0.207  0.026   0.156  0.259  51        4000
cell12    0.201  0.041   0.120  0.282  56        2000
cell12    0.272  0.018   0.238  0.307  50        1000
```

### Step 11: re-running with a tighter segmentation threshold

While re-running with a tighter segmentation threshold for cell23, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.082, stderr 0.028, n = 55). While re-exporting the raw traces for cell10, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.241, stderr 0.040, n = 43). While re-running with a tighter segmentation threshold for cell14, the ordering of cells was preserved (coefficient 0.141, stderr 0.031, n = 57). While checking residual autocorrelation for cell02, two cells fell out of the usable range (coefficient 0.240, stderr 0.012, n = 38). While fitting the one-lag kernel for cell10, the CI narrowed by roughly a tenth (coefficient 0.162, stderr 0.039, n = 57). Noted and moved on; it does not change the decision.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell04    0.222  0.027   0.169  0.275  53        500
cell03    0.296  0.038   0.222  0.370  57        2000
cell16    0.154  0.016   0.122  0.186  45        4000
cell04    0.188  0.021   0.148  0.228  39        2000
cell06    0.271  0.033   0.206  0.337  57        2000
cell05    0.151  0.017   0.117  0.184  44        1000
cell16    0.165  0.022   0.122  0.208  52        4000
cell08    0.303  0.038   0.229  0.377  53        2000
cell02    0.207  0.029   0.150  0.264  47        4000
```

```python
coefs = fit_per_cell(rows, threshold=0.77)
lo, hi = ci(coefs, seed=68)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```python
coefs = fit_per_cell(rows, threshold=0.73)
lo, hi = ci(coefs, seed=27)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 12: comparing per-cell orderings

While re-exporting the raw traces for cell06, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.199, stderr 0.036, n = 52). While bootstrapping the CI for cell07, the coefficient tracked epoch count more closely than duration (coefficient 0.124, stderr 0.029, n = 57). While fitting the one-lag kernel for cell20, the CI narrowed by roughly a tenth (coefficient 0.121, stderr 0.042, n = 48). While re-exporting the raw traces for cell23, the estimate moved less than one standard error (coefficient 0.182, stderr 0.044, n = 41).

While bootstrapping the CI for cell15, the coefficient tracked epoch count more closely than duration (coefficient 0.255, stderr 0.029, n = 41). While segmenting epochs for cell10, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.178, stderr 0.026, n = 48). While segmenting epochs for cell07, the CI narrowed by roughly a tenth (coefficient 0.160, stderr 0.027, n = 57). While checking residual autocorrelation for cell18, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.211, stderr 0.047, n = 38).

While segmenting epochs for cell08, nothing in the figure changed at print size (coefficient 0.300, stderr 0.020, n = 55). While bootstrapping the CI for cell23, two cells fell out of the usable range (coefficient 0.120, stderr 0.033, n = 53). While re-exporting the raw traces for cell04, the coefficient tracked epoch count more closely than duration (coefficient 0.307, stderr 0.047, n = 44). While segmenting epochs for cell15, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.199, stderr 0.036, n = 52). While fitting the one-lag kernel for cell04, two cells fell out of the usable range (coefficient 0.263, stderr 0.034, n = 44). While auditing the holding potential column for cell14, the ordering of cells was preserved (coefficient 0.139, stderr 0.042, n = 43).

```python
coefs = fit_per_cell(rows, threshold=0.62)
lo, hi = ci(coefs, seed=12)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 13: re-exporting the raw traces

While segmenting epochs for cell03, the coefficient tracked epoch count more closely than duration (coefficient 0.123, stderr 0.048, n = 49). While auditing the holding potential column for cell16, the coefficient tracked epoch count more closely than duration (coefficient 0.300, stderr 0.031, n = 49). While auditing the holding potential column for cell11, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.131, stderr 0.017, n = 56). While fitting the one-lag kernel for cell21, two cells fell out of the usable range (coefficient 0.213, stderr 0.010, n = 50). While re-running with a tighter segmentation threshold for cell09, the estimate moved less than one standard error (coefficient 0.184, stderr 0.038, n = 42). Parking this until the re-segmentation lands.

```python
coefs = fit_per_cell(rows, threshold=0.35)
lo, hi = ci(coefs, seed=29)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 14: comparing per-cell orderings

While bootstrapping the CI for cell07, the coefficient tracked epoch count more closely than duration (coefficient 0.231, stderr 0.037, n = 49). While auditing the holding potential column for cell05, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.211, stderr 0.039, n = 56). While fitting the one-lag kernel for cell08, the coefficient tracked epoch count more closely than duration (coefficient 0.184, stderr 0.026, n = 41).

While re-running with a tighter segmentation threshold for cell23, the CI narrowed by roughly a tenth (coefficient 0.165, stderr 0.017, n = 58). While bootstrapping the CI for cell08, the estimate moved less than one standard error (coefficient 0.296, stderr 0.029, n = 50). While segmenting epochs for cell01, nothing in the figure changed at print size (coefficient 0.160, stderr 0.016, n = 51). Noted and moved on; it does not change the decision.

### Step 15: re-exporting the raw traces

```python
coefs = fit_per_cell(rows, threshold=0.62)
lo, hi = ci(coefs, seed=22)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell02    0.161  0.039   0.086  0.237  51        2000
cell13    0.105  0.012   0.082  0.128  57        500
cell23    0.180  0.031   0.120  0.241  53        2000
cell24    0.133  0.033   0.068  0.197  40        500
cell21    0.106  0.041   0.026  0.187  54        1000
cell14    0.284  0.036   0.214  0.354  38        4000
cell18    0.099  0.037   0.027  0.171  38        2000
cell05    0.218  0.040   0.139  0.297  39        1000
cell23    0.131  0.011   0.109  0.152  58        2000
cell07    0.288  0.015   0.260  0.317  51        4000
cell11    0.196  0.046   0.105  0.287  46        2000
cell18    0.132  0.033   0.067  0.197  58        500
cell24    0.190  0.039   0.114  0.266  50        4000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell15    0.195  0.019   0.158  0.233  42        1000
cell20    0.257  0.050   0.160  0.355  44        4000
cell08    0.106  0.019   0.069  0.143  47        2000
cell19    0.099  0.047   0.006  0.192  39        1000
cell18    0.263  0.030   0.204  0.323  38        1000
cell12    0.224  0.022   0.180  0.267  56        500
cell19    0.206  0.027   0.153  0.260  44        1000
cell23    0.095  0.044   0.008  0.181  55        500
cell19    0.208  0.022   0.164  0.252  52        2000
cell01    0.155  0.049   0.058  0.252  54        4000
cell16    0.101  0.047   0.009  0.194  48        4000
cell15    0.194  0.025   0.146  0.243  44        2000
cell17    0.274  0.047   0.181  0.366  45        500
```

While comparing per-cell orderings for cell11, two cells fell out of the usable range (coefficient 0.260, stderr 0.010, n = 46). While segmenting epochs for cell16, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.194, stderr 0.048, n = 38). While segmenting epochs for cell21, nothing in the figure changed at print size (coefficient 0.263, stderr 0.048, n = 52). While bootstrapping the CI for cell02, nothing in the figure changed at print size (coefficient 0.132, stderr 0.045, n = 49). While comparing per-cell orderings for cell10, two cells fell out of the usable range (coefficient 0.278, stderr 0.029, n = 42). Parking this until the re-segmentation lands.

### Step 16: bootstrapping the CI

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell22    0.140  0.043   0.056  0.224  40        4000
cell21    0.195  0.032   0.132  0.259  57        1000
cell16    0.259  0.046   0.169  0.349  48        1000
cell01    0.149  0.027   0.096  0.202  44        1000
cell03    0.119  0.020   0.080  0.157  45        2000
cell01    0.293  0.017   0.259  0.327  45        4000
cell11    0.199  0.022   0.157  0.242  49        500
cell08    0.195  0.024   0.148  0.242  51        4000
cell15    0.292  0.023   0.248  0.336  46        500
cell09    0.187  0.013   0.160  0.213  38        2000
cell14    0.257  0.034   0.191  0.324  45        4000
cell11    0.254  0.047   0.161  0.347  55        4000
cell06    0.135  0.048   0.041  0.230  45        1000
cell17    0.259  0.018   0.225  0.294  49        1000
```

While bootstrapping the CI for cell22, two cells fell out of the usable range (coefficient 0.294, stderr 0.020, n = 39). While re-exporting the raw traces for cell12, nothing in the figure changed at print size (coefficient 0.103, stderr 0.031, n = 48). While re-exporting the raw traces for cell21, the estimate moved less than one standard error (coefficient 0.293, stderr 0.027, n = 38). While re-running with a tighter segmentation threshold for cell14, the coefficient tracked epoch count more closely than duration (coefficient 0.267, stderr 0.019, n = 53).

```python
coefs = fit_per_cell(rows, threshold=0.60)
lo, hi = ci(coefs, seed=62)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While auditing the holding potential column for cell19, nothing in the figure changed at print size (coefficient 0.170, stderr 0.028, n = 52). While segmenting epochs for cell04, the estimate moved less than one standard error (coefficient 0.127, stderr 0.020, n = 47). While auditing the holding potential column for cell12, two cells fell out of the usable range (coefficient 0.288, stderr 0.015, n = 42). While bootstrapping the CI for cell12, the estimate moved less than one standard error (coefficient 0.133, stderr 0.031, n = 52). While comparing per-cell orderings for cell07, the estimate moved less than one standard error (coefficient 0.125, stderr 0.030, n = 53). Flagging it so it does not get rediscovered next week.

### Step 17: re-exporting the raw traces

```python
coefs = fit_per_cell(rows, threshold=0.70)
lo, hi = ci(coefs, seed=98)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```python
coefs = fit_per_cell(rows, threshold=0.58)
lo, hi = ci(coefs, seed=48)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 18: fitting the one-lag kernel

While re-exporting the raw traces for cell07, the coefficient tracked epoch count more closely than duration (coefficient 0.156, stderr 0.012, n = 52). While checking residual autocorrelation for cell24, the estimate moved less than one standard error (coefficient 0.230, stderr 0.047, n = 54). While checking residual autocorrelation for cell16, nothing in the figure changed at print size (coefficient 0.229, stderr 0.039, n = 43). While re-running with a tighter segmentation threshold for cell13, the estimate moved less than one standard error (coefficient 0.254, stderr 0.020, n = 42). Flagging it so it does not get rediscovered next week.

While auditing the holding potential column for cell22, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.264, stderr 0.026, n = 55). While fitting the one-lag kernel for cell20, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.207, stderr 0.011, n = 44). While auditing the holding potential column for cell23, nothing in the figure changed at print size (coefficient 0.086, stderr 0.029, n = 40). Flagging it so it does not get rediscovered next week.

While checking residual autocorrelation for cell13, the ordering of cells was preserved (coefficient 0.094, stderr 0.014, n = 50). While fitting the one-lag kernel for cell21, the coefficient tracked epoch count more closely than duration (coefficient 0.198, stderr 0.025, n = 41). While comparing per-cell orderings for cell22, the ordering of cells was preserved (coefficient 0.211, stderr 0.038, n = 49). While comparing per-cell orderings for cell22, the CI narrowed by roughly a tenth (coefficient 0.127, stderr 0.044, n = 40).

### Step 19: re-running with a tighter segmentation threshold

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell08    0.095  0.028   0.040  0.150  44        2000
cell23    0.191  0.035   0.123  0.259  49        4000
cell24    0.244  0.016   0.212  0.275  54        2000
cell05    0.217  0.014   0.189  0.245  46        500
cell18    0.198  0.026   0.148  0.249  48        1000
cell18    0.093  0.024   0.047  0.140  55        2000
cell03    0.247  0.023   0.201  0.293  52        1000
cell05    0.294  0.048   0.199  0.389  54        2000
cell11    0.187  0.034   0.121  0.253  50        1000
cell07    0.177  0.026   0.126  0.227  51        500
cell01    0.126  0.018   0.092  0.161  38        4000
```

While comparing per-cell orderings for cell17, the estimate moved less than one standard error (coefficient 0.307, stderr 0.029, n = 51). While re-exporting the raw traces for cell21, nothing in the figure changed at print size (coefficient 0.289, stderr 0.044, n = 40). While segmenting epochs for cell07, the CI narrowed by roughly a tenth (coefficient 0.235, stderr 0.045, n = 51).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell20    0.216  0.024   0.170  0.262  46        1000
cell14    0.145  0.022   0.103  0.188  58        4000
cell10    0.241  0.011   0.219  0.263  56        1000
cell15    0.126  0.015   0.096  0.156  52        4000
cell02    0.284  0.018   0.249  0.319  39        2000
cell24    0.122  0.034   0.056  0.188  38        500
cell13    0.225  0.011   0.204  0.247  52        500
cell08    0.263  0.041   0.183  0.343  47        1000
cell02    0.093  0.035   0.024  0.162  46        1000
cell03    0.271  0.045   0.184  0.359  47        500
cell19    0.201  0.023   0.156  0.246  40        1000
cell02    0.117  0.024   0.070  0.163  47        500
```

### Step 20: segmenting epochs

```python
coefs = fit_per_cell(rows, threshold=0.79)
lo, hi = ci(coefs, seed=59)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While fitting the one-lag kernel for cell09, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.157, stderr 0.038, n = 41). While bootstrapping the CI for cell01, the coefficient tracked epoch count more closely than duration (coefficient 0.252, stderr 0.024, n = 51). While re-exporting the raw traces for cell19, the estimate moved less than one standard error (coefficient 0.279, stderr 0.011, n = 58). While re-running with a tighter segmentation threshold for cell07, the CI narrowed by roughly a tenth (coefficient 0.150, stderr 0.021, n = 57). Flagging it so it does not get rediscovered next week.

While fitting the one-lag kernel for cell14, the coefficient tracked epoch count more closely than duration (coefficient 0.105, stderr 0.024, n = 38). While re-exporting the raw traces for cell16, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.306, stderr 0.033, n = 38). While auditing the holding potential column for cell01, the estimate moved less than one standard error (coefficient 0.172, stderr 0.018, n = 51). While checking residual autocorrelation for cell20, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.161, stderr 0.038, n = 44). While checking residual autocorrelation for cell14, the CI narrowed by roughly a tenth (coefficient 0.277, stderr 0.037, n = 53). Worth noting for the writeup, though not a result on its own.

### Step 21: bootstrapping the CI

```python
coefs = fit_per_cell(rows, threshold=0.73)
lo, hi = ci(coefs, seed=84)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While segmenting epochs for cell01, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.266, stderr 0.040, n = 55). While checking residual autocorrelation for cell24, the coefficient tracked epoch count more closely than duration (coefficient 0.241, stderr 0.010, n = 42). While checking residual autocorrelation for cell09, the CI narrowed by roughly a tenth (coefficient 0.149, stderr 0.043, n = 56). While re-running with a tighter segmentation threshold for cell19, the estimate moved less than one standard error (coefficient 0.227, stderr 0.016, n = 45). Noted and moved on; it does not change the decision.

While checking residual autocorrelation for cell24, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.264, stderr 0.044, n = 45). While auditing the holding potential column for cell14, the coefficient tracked epoch count more closely than duration (coefficient 0.108, stderr 0.047, n = 51). While bootstrapping the CI for cell03, nothing in the figure changed at print size (coefficient 0.266, stderr 0.037, n = 49). While auditing the holding potential column for cell17, the ordering of cells was preserved (coefficient 0.294, stderr 0.036, n = 48). While comparing per-cell orderings for cell08, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.185, stderr 0.038, n = 53). While bootstrapping the CI for cell07, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.181, stderr 0.023, n = 52).

```python
coefs = fit_per_cell(rows, threshold=0.41)
lo, hi = ci(coefs, seed=74)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 22: re-running with a tighter segmentation threshold

```python
coefs = fit_per_cell(rows, threshold=0.47)
lo, hi = ci(coefs, seed=7)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell20    0.286  0.034   0.220  0.351  57        1000
cell05    0.263  0.030   0.204  0.322  56        1000
cell20    0.167  0.018   0.132  0.201  52        1000
cell13    0.124  0.011   0.102  0.146  53        1000
cell24    0.256  0.034   0.190  0.323  47        1000
cell22    0.172  0.045   0.083  0.260  56        2000
cell18    0.224  0.033   0.160  0.288  43        500
cell10    0.175  0.033   0.110  0.241  56        2000
cell15    0.133  0.035   0.065  0.202  45        2000
cell03    0.161  0.029   0.103  0.218  54        500
cell01    0.120  0.020   0.081  0.159  54        1000
cell08    0.212  0.035   0.143  0.280  50        1000
```

### Step 23: segmenting epochs

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell07    0.194  0.029   0.137  0.251  46        1000
cell01    0.103  0.043   0.020  0.187  58        500
cell03    0.255  0.031   0.194  0.315  52        2000
cell07    0.308  0.022   0.266  0.351  51        2000
cell02    0.109  0.025   0.061  0.157  51        1000
cell15    0.150  0.019   0.114  0.187  46        2000
cell12    0.254  0.014   0.227  0.281  45        1000
cell04    0.103  0.050   0.006  0.200  51        2000
cell17    0.176  0.040   0.098  0.254  54        1000
cell20    0.142  0.029   0.086  0.199  41        4000
cell11    0.292  0.016   0.261  0.323  43        2000
cell11    0.300  0.039   0.223  0.376  55        2000
cell12    0.205  0.027   0.152  0.257  52        2000
```

While fitting the one-lag kernel for cell24, nothing in the figure changed at print size (coefficient 0.260, stderr 0.020, n = 51). While auditing the holding potential column for cell11, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.141, stderr 0.015, n = 58). While fitting the one-lag kernel for cell09, nothing in the figure changed at print size (coefficient 0.221, stderr 0.035, n = 47). This is the part that will need a real statistical argument.

While comparing per-cell orderings for cell11, nothing in the figure changed at print size (coefficient 0.241, stderr 0.039, n = 50). While bootstrapping the CI for cell14, the coefficient tracked epoch count more closely than duration (coefficient 0.269, stderr 0.035, n = 41). While re-exporting the raw traces for cell23, nothing in the figure changed at print size (coefficient 0.271, stderr 0.012, n = 40). While re-running with a tighter segmentation threshold for cell22, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.101, stderr 0.035, n = 41). Noted and moved on; it does not change the decision.

While re-running with a tighter segmentation threshold for cell17, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.301, stderr 0.034, n = 53). While comparing per-cell orderings for cell02, the coefficient tracked epoch count more closely than duration (coefficient 0.208, stderr 0.046, n = 38). While comparing per-cell orderings for cell15, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.299, stderr 0.045, n = 44). Noted and moved on; it does not change the decision.

### Step 24: auditing the holding potential column

While auditing the holding potential column for cell08, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.096, stderr 0.041, n = 41). While segmenting epochs for cell05, nothing in the figure changed at print size (coefficient 0.228, stderr 0.037, n = 48). While comparing per-cell orderings for cell23, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.273, stderr 0.022, n = 57). While fitting the one-lag kernel for cell09, the ordering of cells was preserved (coefficient 0.133, stderr 0.036, n = 56).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell16    0.121  0.016   0.090  0.153  42        1000
cell01    0.197  0.020   0.157  0.237  54        2000
cell02    0.091  0.022   0.048  0.135  47        500
cell08    0.221  0.035   0.152  0.289  56        4000
cell22    0.241  0.026   0.190  0.291  51        1000
cell17    0.179  0.033   0.113  0.244  54        500
cell02    0.231  0.028   0.177  0.286  56        4000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell15    0.208  0.025   0.160  0.256  57        500
cell24    0.280  0.025   0.231  0.330  48        500
cell05    0.222  0.039   0.146  0.298  53        2000
cell17    0.174  0.043   0.088  0.259  58        500
cell10    0.123  0.048   0.029  0.218  50        1000
cell02    0.200  0.036   0.130  0.270  42        2000
cell11    0.240  0.025   0.190  0.289  55        4000
cell19    0.251  0.017   0.217  0.285  55        1000
cell12    0.283  0.020   0.243  0.323  50        1000
```

While fitting the one-lag kernel for cell14, the coefficient tracked epoch count more closely than duration (coefficient 0.200, stderr 0.021, n = 54). While comparing per-cell orderings for cell20, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.285, stderr 0.025, n = 43). While re-exporting the raw traces for cell17, the ordering of cells was preserved (coefficient 0.288, stderr 0.045, n = 47).

### Step 25: re-exporting the raw traces

```python
coefs = fit_per_cell(rows, threshold=0.41)
lo, hi = ci(coefs, seed=42)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While auditing the holding potential column for cell21, the ordering of cells was preserved (coefficient 0.291, stderr 0.041, n = 45). While bootstrapping the CI for cell11, the coefficient tracked epoch count more closely than duration (coefficient 0.179, stderr 0.032, n = 56). While re-running with a tighter segmentation threshold for cell22, the coefficient tracked epoch count more closely than duration (coefficient 0.183, stderr 0.034, n = 49). While segmenting epochs for cell11, the ordering of cells was preserved (coefficient 0.136, stderr 0.042, n = 51). While re-running with a tighter segmentation threshold for cell24, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.279, stderr 0.030, n = 51). While re-exporting the raw traces for cell05, the ordering of cells was preserved (coefficient 0.136, stderr 0.016, n = 38). Worth noting for the writeup, though not a result on its own.

While bootstrapping the CI for cell11, the ordering of cells was preserved (coefficient 0.186, stderr 0.044, n = 41). While fitting the one-lag kernel for cell04, two cells fell out of the usable range (coefficient 0.233, stderr 0.049, n = 57). While bootstrapping the CI for cell11, two cells fell out of the usable range (coefficient 0.263, stderr 0.049, n = 53).

While bootstrapping the CI for cell17, two cells fell out of the usable range (coefficient 0.103, stderr 0.035, n = 47). While bootstrapping the CI for cell17, the ordering of cells was preserved (coefficient 0.263, stderr 0.035, n = 47). While fitting the one-lag kernel for cell15, the CI narrowed by roughly a tenth (coefficient 0.105, stderr 0.014, n = 54). While checking residual autocorrelation for cell01, two cells fell out of the usable range (coefficient 0.301, stderr 0.014, n = 44). While fitting the one-lag kernel for cell14, the coefficient tracked epoch count more closely than duration (coefficient 0.162, stderr 0.033, n = 57). While comparing per-cell orderings for cell16, nothing in the figure changed at print size (coefficient 0.266, stderr 0.045, n = 49). Parking this until the re-segmentation lands.

### Step 26: re-running with a tighter segmentation threshold

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell03    0.141  0.038   0.067  0.215  55        4000
cell20    0.159  0.017   0.125  0.194  39        1000
cell08    0.192  0.027   0.138  0.246  48        500
cell10    0.269  0.016   0.239  0.300  38        500
cell07    0.150  0.023   0.104  0.195  45        2000
cell07    0.153  0.015   0.123  0.183  40        1000
cell16    0.219  0.041   0.139  0.299  42        4000
cell12    0.248  0.035   0.179  0.317  56        4000
cell07    0.155  0.026   0.103  0.206  51        2000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell18    0.098  0.044   0.012  0.185  47        2000
cell10    0.125  0.047   0.032  0.218  51        500
cell18    0.238  0.034   0.173  0.304  50        500
cell14    0.267  0.025   0.218  0.316  50        4000
cell13    0.209  0.034   0.142  0.276  56        1000
cell01    0.214  0.048   0.120  0.308  50        500
cell05    0.226  0.032   0.164  0.288  40        1000
cell18    0.180  0.040   0.102  0.257  47        2000
cell11    0.215  0.038   0.139  0.290  40        4000
```

While fitting the one-lag kernel for cell12, the ordering of cells was preserved (coefficient 0.252, stderr 0.027, n = 46). While re-exporting the raw traces for cell20, the ordering of cells was preserved (coefficient 0.207, stderr 0.045, n = 45). While bootstrapping the CI for cell12, two cells fell out of the usable range (coefficient 0.216, stderr 0.044, n = 47). While checking residual autocorrelation for cell19, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.094, stderr 0.029, n = 40). While checking residual autocorrelation for cell04, the CI narrowed by roughly a tenth (coefficient 0.232, stderr 0.035, n = 58).

While bootstrapping the CI for cell22, the ordering of cells was preserved (coefficient 0.274, stderr 0.049, n = 41). While fitting the one-lag kernel for cell05, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.119, stderr 0.043, n = 44). While fitting the one-lag kernel for cell08, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.168, stderr 0.017, n = 56). While auditing the holding potential column for cell13, the ordering of cells was preserved (coefficient 0.124, stderr 0.047, n = 49).

### Step 27: fitting the one-lag kernel

```python
coefs = fit_per_cell(rows, threshold=0.77)
lo, hi = ci(coefs, seed=68)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell21    0.276  0.048   0.182  0.369  42        500
cell16    0.306  0.040   0.227  0.384  53        500
cell16    0.236  0.050   0.139  0.333  38        500
cell01    0.224  0.039   0.148  0.299  56        1000
cell14    0.086  0.023   0.041  0.131  38        1000
cell21    0.298  0.013   0.271  0.324  52        500
cell18    0.296  0.037   0.224  0.368  40        500
cell20    0.252  0.022   0.209  0.296  49        2000
cell16    0.186  0.011   0.164  0.207  52        4000
cell11    0.247  0.019   0.209  0.285  47        2000
cell06    0.301  0.044   0.215  0.387  57        500
cell04    0.154  0.038   0.080  0.229  57        1000
```

While fitting the one-lag kernel for cell20, the estimate moved less than one standard error (coefficient 0.190, stderr 0.031, n = 56). While bootstrapping the CI for cell02, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.287, stderr 0.027, n = 40). While segmenting epochs for cell07, the CI narrowed by roughly a tenth (coefficient 0.141, stderr 0.042, n = 46).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell05    0.299  0.035   0.230  0.367  43        4000
cell16    0.122  0.037   0.050  0.195  44        1000
cell11    0.182  0.039   0.107  0.258  50        4000
cell13    0.204  0.018   0.169  0.239  56        1000
cell03    0.305  0.025   0.255  0.354  54        2000
cell05    0.093  0.014   0.066  0.119  51        500
cell11    0.199  0.033   0.133  0.264  45        4000
```

### Step 28: bootstrapping the CI

```python
coefs = fit_per_cell(rows, threshold=0.47)
lo, hi = ci(coefs, seed=66)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell20    0.100  0.038   0.025  0.175  51        2000
cell19    0.273  0.019   0.235  0.311  52        4000
cell03    0.192  0.023   0.146  0.238  52        4000
cell04    0.123  0.039   0.046  0.200  58        4000
cell01    0.154  0.037   0.081  0.227  55        500
cell12    0.308  0.032   0.246  0.371  40        500
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell22    0.209  0.036   0.138  0.280  53        1000
cell11    0.196  0.016   0.164  0.227  38        4000
cell17    0.176  0.035   0.107  0.245  43        2000
cell20    0.133  0.033   0.068  0.198  46        4000
cell22    0.173  0.036   0.102  0.244  39        500
cell19    0.199  0.021   0.157  0.241  42        500
cell09    0.236  0.019   0.198  0.274  41        4000
cell12    0.201  0.047   0.108  0.294  49        500
cell11    0.093  0.040   0.014  0.172  41        4000
cell13    0.272  0.023   0.228  0.316  53        500
cell14    0.148  0.043   0.063  0.232  51        4000
cell08    0.292  0.011   0.271  0.314  55        2000
cell13    0.173  0.019   0.136  0.210  46        500
cell19    0.238  0.011   0.216  0.260  55        2000
```

### Step 29: re-exporting the raw traces

While segmenting epochs for cell04, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.103, stderr 0.015, n = 51). While checking residual autocorrelation for cell22, the ordering of cells was preserved (coefficient 0.259, stderr 0.027, n = 42). While comparing per-cell orderings for cell02, the CI narrowed by roughly a tenth (coefficient 0.129, stderr 0.024, n = 43). While bootstrapping the CI for cell12, two cells fell out of the usable range (coefficient 0.120, stderr 0.045, n = 39). While re-exporting the raw traces for cell20, nothing in the figure changed at print size (coefficient 0.195, stderr 0.022, n = 41). While segmenting epochs for cell09, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.258, stderr 0.033, n = 52).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell17    0.090  0.016   0.059  0.122  51        1000
cell02    0.284  0.040   0.206  0.361  39        2000
cell09    0.290  0.010   0.269  0.310  38        500
cell03    0.089  0.020   0.049  0.129  48        1000
cell02    0.222  0.023   0.176  0.268  48        500
cell11    0.137  0.045   0.049  0.226  43        4000
cell07    0.231  0.018   0.195  0.266  38        1000
cell23    0.107  0.029   0.051  0.163  41        4000
cell23    0.224  0.020   0.185  0.264  40        4000
cell17    0.256  0.017   0.224  0.289  42        500
cell11    0.232  0.024   0.184  0.279  43        2000
cell06    0.285  0.048   0.190  0.380  38        2000
cell14    0.176  0.017   0.142  0.210  38        1000
cell11    0.082  0.040   0.004  0.160  46        500
```

### Step 30: segmenting epochs

While bootstrapping the CI for cell06, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.297, stderr 0.020, n = 43). While fitting the one-lag kernel for cell12, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.146, stderr 0.015, n = 54). While checking residual autocorrelation for cell19, two cells fell out of the usable range (coefficient 0.224, stderr 0.013, n = 44). While segmenting epochs for cell20, the estimate moved less than one standard error (coefficient 0.101, stderr 0.035, n = 57).

While re-running with a tighter segmentation threshold for cell09, the ordering of cells was preserved (coefficient 0.172, stderr 0.021, n = 57). While comparing per-cell orderings for cell06, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.084, stderr 0.040, n = 40). While re-exporting the raw traces for cell08, the coefficient tracked epoch count more closely than duration (coefficient 0.306, stderr 0.012, n = 57).

### Step 31: re-running with a tighter segmentation threshold

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell02    0.156  0.030   0.097  0.215  57        1000
cell18    0.153  0.047   0.060  0.245  48        500
cell01    0.148  0.039   0.071  0.225  45        1000
cell01    0.289  0.027   0.236  0.343  51        4000
cell22    0.161  0.042   0.079  0.242  55        2000
cell11    0.117  0.031   0.057  0.178  43        500
cell21    0.234  0.014   0.207  0.261  56        500
cell03    0.167  0.017   0.133  0.200  56        500
cell14    0.107  0.026   0.057  0.158  53        2000
cell12    0.298  0.034   0.231  0.365  54        2000
cell07    0.102  0.034   0.036  0.168  39        4000
cell08    0.210  0.030   0.152  0.269  39        500
cell07    0.103  0.026   0.051  0.155  43        1000
```

While bootstrapping the CI for cell04, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.196, stderr 0.024, n = 44). While checking residual autocorrelation for cell12, the ordering of cells was preserved (coefficient 0.142, stderr 0.032, n = 52). While checking residual autocorrelation for cell20, the coefficient tracked epoch count more closely than duration (coefficient 0.310, stderr 0.019, n = 52). While bootstrapping the CI for cell02, the CI narrowed by roughly a tenth (coefficient 0.195, stderr 0.046, n = 39). While fitting the one-lag kernel for cell16, two cells fell out of the usable range (coefficient 0.258, stderr 0.021, n = 47).

### Step 32: auditing the holding potential column

While fitting the one-lag kernel for cell12, the ordering of cells was preserved (coefficient 0.302, stderr 0.016, n = 40). While re-running with a tighter segmentation threshold for cell16, two cells fell out of the usable range (coefficient 0.169, stderr 0.023, n = 41). While auditing the holding potential column for cell09, the estimate moved less than one standard error (coefficient 0.273, stderr 0.044, n = 44).

While comparing per-cell orderings for cell15, the CI narrowed by roughly a tenth (coefficient 0.169, stderr 0.046, n = 43). While segmenting epochs for cell16, nothing in the figure changed at print size (coefficient 0.081, stderr 0.027, n = 48). While auditing the holding potential column for cell12, the ordering of cells was preserved (coefficient 0.283, stderr 0.038, n = 40). While fitting the one-lag kernel for cell11, nothing in the figure changed at print size (coefficient 0.203, stderr 0.033, n = 39). While checking residual autocorrelation for cell15, the CI narrowed by roughly a tenth (coefficient 0.105, stderr 0.027, n = 38). While re-running with a tighter segmentation threshold for cell02, two cells fell out of the usable range (coefficient 0.170, stderr 0.018, n = 49).

While comparing per-cell orderings for cell09, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.133, stderr 0.046, n = 45). While re-exporting the raw traces for cell13, the CI narrowed by roughly a tenth (coefficient 0.091, stderr 0.039, n = 49). While checking residual autocorrelation for cell13, the CI narrowed by roughly a tenth (coefficient 0.154, stderr 0.015, n = 50). While fitting the one-lag kernel for cell20, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.181, stderr 0.049, n = 55). While comparing per-cell orderings for cell12, the ordering of cells was preserved (coefficient 0.307, stderr 0.014, n = 46). While re-running with a tighter segmentation threshold for cell01, nothing in the figure changed at print size (coefficient 0.121, stderr 0.043, n = 50). Flagging it so it does not get rediscovered next week.

### Step 33: re-running with a tighter segmentation threshold

While re-running with a tighter segmentation threshold for cell03, the coefficient tracked epoch count more closely than duration (coefficient 0.263, stderr 0.011, n = 44). While checking residual autocorrelation for cell15, the coefficient tracked epoch count more closely than duration (coefficient 0.280, stderr 0.040, n = 48). While re-exporting the raw traces for cell13, the coefficient tracked epoch count more closely than duration (coefficient 0.189, stderr 0.021, n = 41). While auditing the holding potential column for cell12, the estimate moved less than one standard error (coefficient 0.125, stderr 0.011, n = 41). While bootstrapping the CI for cell04, the CI narrowed by roughly a tenth (coefficient 0.216, stderr 0.043, n = 49). Parking this until the re-segmentation lands.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell24    0.117  0.036   0.046  0.188  50        1000
cell05    0.218  0.026   0.167  0.269  58        500
cell02    0.131  0.026   0.080  0.183  53        500
cell08    0.244  0.042   0.161  0.326  56        500
cell19    0.098  0.045   0.010  0.186  46        500
cell12    0.279  0.027   0.227  0.331  52        4000
cell11    0.193  0.022   0.151  0.235  42        2000
cell14    0.295  0.020   0.257  0.334  47        1000
```

### Step 34: re-running with a tighter segmentation threshold

```python
coefs = fit_per_cell(rows, threshold=0.70)
lo, hi = ci(coefs, seed=12)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell08    0.122  0.036   0.052  0.193  48        1000
cell12    0.157  0.032   0.094  0.220  48        500
cell20    0.179  0.040   0.101  0.256  46        2000
cell09    0.100  0.022   0.056  0.143  45        500
cell20    0.119  0.025   0.069  0.169  40        4000
cell24    0.231  0.035   0.162  0.300  55        1000
cell08    0.151  0.038   0.077  0.226  56        4000
```

### Step 35: checking residual autocorrelation

```python
coefs = fit_per_cell(rows, threshold=0.47)
lo, hi = ci(coefs, seed=67)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While fitting the one-lag kernel for cell21, the ordering of cells was preserved (coefficient 0.238, stderr 0.023, n = 48). While re-running with a tighter segmentation threshold for cell03, nothing in the figure changed at print size (coefficient 0.235, stderr 0.046, n = 48). While checking residual autocorrelation for cell19, the coefficient tracked epoch count more closely than duration (coefficient 0.237, stderr 0.021, n = 39). While re-exporting the raw traces for cell07, the ordering of cells was preserved (coefficient 0.206, stderr 0.038, n = 53).

While segmenting epochs for cell16, the coefficient tracked epoch count more closely than duration (coefficient 0.141, stderr 0.018, n = 46). While re-exporting the raw traces for cell14, the CI narrowed by roughly a tenth (coefficient 0.246, stderr 0.042, n = 40). While checking residual autocorrelation for cell09, nothing in the figure changed at print size (coefficient 0.275, stderr 0.025, n = 58). While checking residual autocorrelation for cell12, nothing in the figure changed at print size (coefficient 0.228, stderr 0.024, n = 58). While segmenting epochs for cell14, the coefficient tracked epoch count more closely than duration (coefficient 0.266, stderr 0.036, n = 54).

While segmenting epochs for cell23, two cells fell out of the usable range (coefficient 0.300, stderr 0.048, n = 44). While segmenting epochs for cell16, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.162, stderr 0.048, n = 38). While comparing per-cell orderings for cell04, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.084, stderr 0.017, n = 43). While fitting the one-lag kernel for cell18, the coefficient tracked epoch count more closely than duration (coefficient 0.308, stderr 0.047, n = 40). While segmenting epochs for cell18, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.124, stderr 0.027, n = 43). While comparing per-cell orderings for cell17, the estimate moved less than one standard error (coefficient 0.096, stderr 0.021, n = 47).

### Step 36: re-running with a tighter segmentation threshold

While bootstrapping the CI for cell13, two cells fell out of the usable range (coefficient 0.223, stderr 0.032, n = 41). While re-running with a tighter segmentation threshold for cell18, the estimate moved less than one standard error (coefficient 0.192, stderr 0.045, n = 53). While segmenting epochs for cell15, the coefficient tracked epoch count more closely than duration (coefficient 0.082, stderr 0.049, n = 44). This is the part that will need a real statistical argument.

While re-running with a tighter segmentation threshold for cell19, the CI narrowed by roughly a tenth (coefficient 0.230, stderr 0.020, n = 54). While re-running with a tighter segmentation threshold for cell22, the ordering of cells was preserved (coefficient 0.255, stderr 0.036, n = 47). While re-running with a tighter segmentation threshold for cell02, nothing in the figure changed at print size (coefficient 0.238, stderr 0.024, n = 50). While bootstrapping the CI for cell04, the coefficient tracked epoch count more closely than duration (coefficient 0.098, stderr 0.019, n = 47). While bootstrapping the CI for cell07, the CI narrowed by roughly a tenth (coefficient 0.128, stderr 0.041, n = 56). While auditing the holding potential column for cell16, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.154, stderr 0.050, n = 53). Parking this until the re-segmentation lands.

While re-exporting the raw traces for cell22, the estimate moved less than one standard error (coefficient 0.283, stderr 0.016, n = 46). While fitting the one-lag kernel for cell13, the CI narrowed by roughly a tenth (coefficient 0.109, stderr 0.011, n = 56). While bootstrapping the CI for cell24, the estimate moved less than one standard error (coefficient 0.282, stderr 0.025, n = 45). While comparing per-cell orderings for cell20, the CI narrowed by roughly a tenth (coefficient 0.141, stderr 0.012, n = 38). While auditing the holding potential column for cell05, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.191, stderr 0.035, n = 44).

While re-running with a tighter segmentation threshold for cell20, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.086, stderr 0.025, n = 41). While comparing per-cell orderings for cell16, the coefficient tracked epoch count more closely than duration (coefficient 0.114, stderr 0.041, n = 51). While checking residual autocorrelation for cell24, the estimate moved less than one standard error (coefficient 0.253, stderr 0.041, n = 41).

### Step 37: comparing per-cell orderings

While comparing per-cell orderings for cell03, the coefficient tracked epoch count more closely than duration (coefficient 0.262, stderr 0.020, n = 43). While re-exporting the raw traces for cell04, the estimate moved less than one standard error (coefficient 0.118, stderr 0.023, n = 46). While re-running with a tighter segmentation threshold for cell07, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.290, stderr 0.031, n = 46). This is the part that will need a real statistical argument.

While bootstrapping the CI for cell20, the CI narrowed by roughly a tenth (coefficient 0.081, stderr 0.021, n = 44). While bootstrapping the CI for cell19, the ordering of cells was preserved (coefficient 0.113, stderr 0.044, n = 50). While re-running with a tighter segmentation threshold for cell04, two cells fell out of the usable range (coefficient 0.307, stderr 0.034, n = 56). While fitting the one-lag kernel for cell17, the ordering of cells was preserved (coefficient 0.308, stderr 0.049, n = 53). While comparing per-cell orderings for cell08, two cells fell out of the usable range (coefficient 0.256, stderr 0.028, n = 43). While auditing the holding potential column for cell03, the ordering of cells was preserved (coefficient 0.186, stderr 0.019, n = 48). This is the part that will need a real statistical argument.

While segmenting epochs for cell04, the CI narrowed by roughly a tenth (coefficient 0.266, stderr 0.043, n = 57). While re-exporting the raw traces for cell22, nothing in the figure changed at print size (coefficient 0.227, stderr 0.026, n = 47). While comparing per-cell orderings for cell10, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.086, stderr 0.038, n = 48). While auditing the holding potential column for cell01, two cells fell out of the usable range (coefficient 0.143, stderr 0.034, n = 47). Noted and moved on; it does not change the decision.

### Step 38: segmenting epochs

While auditing the holding potential column for cell19, the coefficient tracked epoch count more closely than duration (coefficient 0.240, stderr 0.043, n = 53). While re-exporting the raw traces for cell23, the coefficient tracked epoch count more closely than duration (coefficient 0.087, stderr 0.029, n = 50). While re-running with a tighter segmentation threshold for cell11, the ordering of cells was preserved (coefficient 0.181, stderr 0.033, n = 57). While re-exporting the raw traces for cell05, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.293, stderr 0.022, n = 54).

While re-exporting the raw traces for cell04, the CI narrowed by roughly a tenth (coefficient 0.255, stderr 0.018, n = 49). While auditing the holding potential column for cell20, the estimate moved less than one standard error (coefficient 0.298, stderr 0.019, n = 53). While bootstrapping the CI for cell09, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.189, stderr 0.014, n = 41). While segmenting epochs for cell11, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.194, stderr 0.032, n = 56). Flagging it so it does not get rediscovered next week.

### Step 39: auditing the holding potential column

While checking residual autocorrelation for cell21, the estimate moved less than one standard error (coefficient 0.203, stderr 0.018, n = 52). While bootstrapping the CI for cell03, the estimate moved less than one standard error (coefficient 0.160, stderr 0.034, n = 56). While comparing per-cell orderings for cell14, the ordering of cells was preserved (coefficient 0.095, stderr 0.047, n = 45). Noted and moved on; it does not change the decision.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell08    0.195  0.015   0.166  0.224  52        1000
cell16    0.128  0.050   0.031  0.226  40        1000
cell04    0.258  0.030   0.199  0.318  40        1000
cell14    0.158  0.033   0.094  0.223  48        500
cell21    0.210  0.046   0.119  0.300  50        1000
cell04    0.227  0.028   0.172  0.281  45        1000
cell08    0.094  0.012   0.071  0.117  50        2000
cell24    0.211  0.045   0.122  0.299  46        4000
cell11    0.129  0.045   0.041  0.217  45        4000
cell02    0.267  0.040   0.190  0.345  51        1000
cell18    0.233  0.046   0.142  0.324  41        2000
```

### Step 40: fitting the one-lag kernel

While checking residual autocorrelation for cell06, the coefficient tracked epoch count more closely than duration (coefficient 0.212, stderr 0.035, n = 49). While comparing per-cell orderings for cell02, nothing in the figure changed at print size (coefficient 0.184, stderr 0.019, n = 45). While re-exporting the raw traces for cell24, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.295, stderr 0.037, n = 45). While checking residual autocorrelation for cell03, the coefficient tracked epoch count more closely than duration (coefficient 0.092, stderr 0.046, n = 54).

While fitting the one-lag kernel for cell24, the ordering of cells was preserved (coefficient 0.082, stderr 0.011, n = 42). While bootstrapping the CI for cell09, the coefficient tracked epoch count more closely than duration (coefficient 0.162, stderr 0.034, n = 52). While bootstrapping the CI for cell06, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.154, stderr 0.010, n = 43). Parking this until the re-segmentation lands.

While auditing the holding potential column for cell17, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.187, stderr 0.048, n = 55). While segmenting epochs for cell07, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.099, stderr 0.035, n = 40). While bootstrapping the CI for cell09, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.274, stderr 0.025, n = 48). While bootstrapping the CI for cell15, the ordering of cells was preserved (coefficient 0.264, stderr 0.030, n = 49). While re-exporting the raw traces for cell01, the CI narrowed by roughly a tenth (coefficient 0.129, stderr 0.018, n = 57).

