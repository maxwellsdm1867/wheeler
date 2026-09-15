# Prior session 12 of 20

Transcript of an earlier working session on the history-kernel analysis.

### Step 1: auditing the holding potential column

While bootstrapping the CI for cell05, the coefficient tracked epoch count more closely than duration (coefficient 0.119, stderr 0.014, n = 47). While auditing the holding potential column for cell13, the ordering of cells was preserved (coefficient 0.180, stderr 0.017, n = 51). While re-exporting the raw traces for cell08, the ordering of cells was preserved (coefficient 0.282, stderr 0.023, n = 56).

While comparing per-cell orderings for cell11, the CI narrowed by roughly a tenth (coefficient 0.277, stderr 0.044, n = 55). While comparing per-cell orderings for cell20, the estimate moved less than one standard error (coefficient 0.176, stderr 0.040, n = 47). While bootstrapping the CI for cell17, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.139, stderr 0.048, n = 41). While segmenting epochs for cell01, the CI narrowed by roughly a tenth (coefficient 0.115, stderr 0.019, n = 38). This is the part that will need a real statistical argument.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell20    0.204  0.037   0.131  0.277  42        1000
cell10    0.102  0.045   0.015  0.190  48        1000
cell07    0.236  0.037   0.163  0.310  57        500
cell15    0.161  0.042   0.079  0.243  53        4000
cell24    0.164  0.016   0.132  0.196  49        4000
cell13    0.291  0.031   0.231  0.351  55        500
```

### Step 2: bootstrapping the CI

While re-running with a tighter segmentation threshold for cell15, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.115, stderr 0.026, n = 49). While auditing the holding potential column for cell02, the coefficient tracked epoch count more closely than duration (coefficient 0.142, stderr 0.023, n = 50). While auditing the holding potential column for cell05, the CI narrowed by roughly a tenth (coefficient 0.201, stderr 0.035, n = 38). While auditing the holding potential column for cell14, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.259, stderr 0.026, n = 40). This is the part that will need a real statistical argument.

While segmenting epochs for cell23, the estimate moved less than one standard error (coefficient 0.305, stderr 0.046, n = 56). While comparing per-cell orderings for cell07, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.159, stderr 0.028, n = 46). While re-running with a tighter segmentation threshold for cell13, nothing in the figure changed at print size (coefficient 0.083, stderr 0.033, n = 42).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell09    0.083  0.043   -0.000  0.167  44        1000
cell17    0.217  0.039   0.141  0.293  39        500
cell14    0.172  0.029   0.115  0.228  41        500
cell14    0.138  0.042   0.056  0.219  39        1000
cell15    0.219  0.041   0.138  0.299  41        4000
cell06    0.231  0.043   0.146  0.315  51        4000
cell04    0.155  0.043   0.071  0.239  44        500
cell03    0.234  0.030   0.176  0.292  55        4000
```

### Step 3: checking residual autocorrelation

While comparing per-cell orderings for cell17, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.088, stderr 0.025, n = 49). While fitting the one-lag kernel for cell13, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.277, stderr 0.042, n = 44). While bootstrapping the CI for cell13, nothing in the figure changed at print size (coefficient 0.299, stderr 0.037, n = 45).

While re-exporting the raw traces for cell06, the coefficient tracked epoch count more closely than duration (coefficient 0.166, stderr 0.026, n = 57). While bootstrapping the CI for cell04, the ordering of cells was preserved (coefficient 0.165, stderr 0.031, n = 48). While checking residual autocorrelation for cell04, the coefficient tracked epoch count more closely than duration (coefficient 0.199, stderr 0.016, n = 58). While auditing the holding potential column for cell19, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.235, stderr 0.014, n = 39).

While fitting the one-lag kernel for cell07, the coefficient tracked epoch count more closely than duration (coefficient 0.202, stderr 0.042, n = 43). While checking residual autocorrelation for cell19, nothing in the figure changed at print size (coefficient 0.104, stderr 0.015, n = 41). While checking residual autocorrelation for cell02, the coefficient tracked epoch count more closely than duration (coefficient 0.292, stderr 0.026, n = 42). While comparing per-cell orderings for cell18, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.136, stderr 0.024, n = 41). While segmenting epochs for cell19, the CI narrowed by roughly a tenth (coefficient 0.208, stderr 0.023, n = 56). While auditing the holding potential column for cell11, two cells fell out of the usable range (coefficient 0.175, stderr 0.010, n = 53).

### Step 4: segmenting epochs

While comparing per-cell orderings for cell03, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.257, stderr 0.048, n = 46). While fitting the one-lag kernel for cell04, the CI narrowed by roughly a tenth (coefficient 0.104, stderr 0.042, n = 47). While re-running with a tighter segmentation threshold for cell16, the coefficient tracked epoch count more closely than duration (coefficient 0.239, stderr 0.012, n = 45). Noted and moved on; it does not change the decision.

```python
coefs = fit_per_cell(rows, threshold=0.66)
lo, hi = ci(coefs, seed=49)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```python
coefs = fit_per_cell(rows, threshold=0.50)
lo, hi = ci(coefs, seed=71)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While bootstrapping the CI for cell15, nothing in the figure changed at print size (coefficient 0.104, stderr 0.042, n = 44). While fitting the one-lag kernel for cell12, nothing in the figure changed at print size (coefficient 0.158, stderr 0.047, n = 50). While fitting the one-lag kernel for cell19, the coefficient tracked epoch count more closely than duration (coefficient 0.196, stderr 0.022, n = 42). While comparing per-cell orderings for cell21, the CI narrowed by roughly a tenth (coefficient 0.242, stderr 0.017, n = 45). While bootstrapping the CI for cell13, the estimate moved less than one standard error (coefficient 0.190, stderr 0.044, n = 46).

### Step 5: bootstrapping the CI

While re-running with a tighter segmentation threshold for cell05, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.305, stderr 0.029, n = 48). While comparing per-cell orderings for cell22, the coefficient tracked epoch count more closely than duration (coefficient 0.296, stderr 0.036, n = 51). While auditing the holding potential column for cell16, nothing in the figure changed at print size (coefficient 0.302, stderr 0.046, n = 46). While auditing the holding potential column for cell02, the ordering of cells was preserved (coefficient 0.119, stderr 0.021, n = 49). Parking this until the re-segmentation lands.

While bootstrapping the CI for cell02, the ordering of cells was preserved (coefficient 0.171, stderr 0.037, n = 56). While checking residual autocorrelation for cell02, the estimate moved less than one standard error (coefficient 0.121, stderr 0.035, n = 58). While re-running with a tighter segmentation threshold for cell03, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.164, stderr 0.049, n = 42). While segmenting epochs for cell14, nothing in the figure changed at print size (coefficient 0.132, stderr 0.043, n = 51). While auditing the holding potential column for cell16, the CI narrowed by roughly a tenth (coefficient 0.155, stderr 0.029, n = 47).

### Step 6: re-exporting the raw traces

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell08    0.104  0.036   0.033  0.175  38        4000
cell12    0.256  0.014   0.229  0.283  56        1000
cell11    0.241  0.033   0.175  0.306  47        2000
cell09    0.088  0.043   0.004  0.173  48        2000
cell20    0.188  0.041   0.108  0.268  45        4000
cell14    0.097  0.048   0.003  0.190  55        2000
cell10    0.277  0.023   0.232  0.322  55        1000
cell20    0.308  0.043   0.224  0.393  45        2000
cell03    0.090  0.044   0.003  0.176  49        500
cell13    0.288  0.025   0.238  0.337  48        500
cell09    0.285  0.018   0.249  0.321  52        4000
cell07    0.173  0.020   0.135  0.212  43        1000
```

While fitting the one-lag kernel for cell07, the ordering of cells was preserved (coefficient 0.097, stderr 0.030, n = 42). While auditing the holding potential column for cell07, the CI narrowed by roughly a tenth (coefficient 0.168, stderr 0.025, n = 58). While checking residual autocorrelation for cell09, the ordering of cells was preserved (coefficient 0.194, stderr 0.033, n = 47).

### Step 7: fitting the one-lag kernel

While bootstrapping the CI for cell06, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.309, stderr 0.010, n = 51). While re-running with a tighter segmentation threshold for cell22, two cells fell out of the usable range (coefficient 0.111, stderr 0.049, n = 52). While segmenting epochs for cell06, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.093, stderr 0.036, n = 41). While re-exporting the raw traces for cell09, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.272, stderr 0.037, n = 46). While segmenting epochs for cell09, the CI narrowed by roughly a tenth (coefficient 0.153, stderr 0.011, n = 50). While fitting the one-lag kernel for cell12, the CI narrowed by roughly a tenth (coefficient 0.305, stderr 0.020, n = 38).

```python
coefs = fit_per_cell(rows, threshold=0.65)
lo, hi = ci(coefs, seed=41)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While bootstrapping the CI for cell10, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.231, stderr 0.017, n = 40). While auditing the holding potential column for cell08, two cells fell out of the usable range (coefficient 0.120, stderr 0.044, n = 44). While re-running with a tighter segmentation threshold for cell12, nothing in the figure changed at print size (coefficient 0.242, stderr 0.031, n = 49). While fitting the one-lag kernel for cell19, the coefficient tracked epoch count more closely than duration (coefficient 0.101, stderr 0.014, n = 39). While fitting the one-lag kernel for cell04, the CI narrowed by roughly a tenth (coefficient 0.189, stderr 0.031, n = 50). Noted and moved on; it does not change the decision.

### Step 8: checking residual autocorrelation

While fitting the one-lag kernel for cell03, two cells fell out of the usable range (coefficient 0.188, stderr 0.018, n = 46). While auditing the holding potential column for cell24, the CI narrowed by roughly a tenth (coefficient 0.292, stderr 0.025, n = 50). While re-running with a tighter segmentation threshold for cell08, the coefficient tracked epoch count more closely than duration (coefficient 0.090, stderr 0.047, n = 48). While checking residual autocorrelation for cell06, two cells fell out of the usable range (coefficient 0.148, stderr 0.023, n = 56). While re-exporting the raw traces for cell02, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.092, stderr 0.040, n = 44).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell24    0.219  0.019   0.182  0.256  46        4000
cell02    0.121  0.013   0.097  0.146  58        2000
cell07    0.220  0.044   0.134  0.307  49        500
cell13    0.132  0.028   0.078  0.186  55        1000
cell17    0.261  0.041   0.180  0.342  57        1000
cell05    0.148  0.032   0.086  0.210  47        4000
cell11    0.279  0.046   0.188  0.370  43        1000
cell02    0.307  0.048   0.213  0.401  45        500
cell16    0.106  0.049   0.010  0.202  38        1000
cell08    0.247  0.042   0.164  0.329  48        2000
cell06    0.152  0.010   0.132  0.173  56        1000
cell22    0.269  0.016   0.237  0.301  40        500
cell04    0.284  0.039   0.207  0.361  40        500
cell02    0.163  0.037   0.091  0.235  55        2000
```

While re-running with a tighter segmentation threshold for cell19, the ordering of cells was preserved (coefficient 0.187, stderr 0.021, n = 56). While re-running with a tighter segmentation threshold for cell18, the CI narrowed by roughly a tenth (coefficient 0.216, stderr 0.043, n = 46). While re-running with a tighter segmentation threshold for cell05, the coefficient tracked epoch count more closely than duration (coefficient 0.094, stderr 0.044, n = 50). Worth noting for the writeup, though not a result on its own.

While checking residual autocorrelation for cell22, the CI narrowed by roughly a tenth (coefficient 0.093, stderr 0.043, n = 55). While comparing per-cell orderings for cell09, nothing in the figure changed at print size (coefficient 0.228, stderr 0.017, n = 40). While fitting the one-lag kernel for cell06, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.094, stderr 0.038, n = 44). While comparing per-cell orderings for cell17, nothing in the figure changed at print size (coefficient 0.121, stderr 0.045, n = 42). While bootstrapping the CI for cell03, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.248, stderr 0.039, n = 45).

### Step 9: checking residual autocorrelation

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell02    0.192  0.040   0.115  0.270  53        500
cell10    0.192  0.029   0.135  0.248  50        4000
cell12    0.256  0.050   0.158  0.354  48        500
cell04    0.141  0.046   0.051  0.230  39        4000
cell03    0.135  0.039   0.059  0.211  48        4000
cell07    0.300  0.020   0.261  0.340  41        4000
cell14    0.277  0.021   0.235  0.319  53        500
cell12    0.185  0.041   0.105  0.264  56        4000
```

While re-exporting the raw traces for cell04, the estimate moved less than one standard error (coefficient 0.209, stderr 0.012, n = 49). While auditing the holding potential column for cell08, the estimate moved less than one standard error (coefficient 0.090, stderr 0.016, n = 52). While re-running with a tighter segmentation threshold for cell23, the CI narrowed by roughly a tenth (coefficient 0.302, stderr 0.030, n = 54). While bootstrapping the CI for cell20, the ordering of cells was preserved (coefficient 0.230, stderr 0.026, n = 49). Flagging it so it does not get rediscovered next week.

While checking residual autocorrelation for cell24, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.182, stderr 0.033, n = 38). While comparing per-cell orderings for cell19, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.283, stderr 0.040, n = 57). While fitting the one-lag kernel for cell24, the CI narrowed by roughly a tenth (coefficient 0.151, stderr 0.032, n = 44). While auditing the holding potential column for cell16, the ordering of cells was preserved (coefficient 0.148, stderr 0.048, n = 40). While auditing the holding potential column for cell21, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.086, stderr 0.040, n = 57). While comparing per-cell orderings for cell14, the estimate moved less than one standard error (coefficient 0.172, stderr 0.011, n = 42). Noted and moved on; it does not change the decision.

```python
coefs = fit_per_cell(rows, threshold=0.45)
lo, hi = ci(coefs, seed=31)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 10: segmenting epochs

While comparing per-cell orderings for cell16, the CI narrowed by roughly a tenth (coefficient 0.192, stderr 0.021, n = 58). While auditing the holding potential column for cell07, the CI narrowed by roughly a tenth (coefficient 0.245, stderr 0.028, n = 45). While auditing the holding potential column for cell09, the estimate moved less than one standard error (coefficient 0.184, stderr 0.028, n = 38).

While re-running with a tighter segmentation threshold for cell09, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.189, stderr 0.049, n = 54). While bootstrapping the CI for cell04, two cells fell out of the usable range (coefficient 0.304, stderr 0.046, n = 53). While re-running with a tighter segmentation threshold for cell15, nothing in the figure changed at print size (coefficient 0.227, stderr 0.043, n = 40). While fitting the one-lag kernel for cell24, the estimate moved less than one standard error (coefficient 0.119, stderr 0.013, n = 58). Worth noting for the writeup, though not a result on its own.

```python
coefs = fit_per_cell(rows, threshold=0.73)
lo, hi = ci(coefs, seed=71)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 11: fitting the one-lag kernel

While segmenting epochs for cell08, the CI narrowed by roughly a tenth (coefficient 0.152, stderr 0.010, n = 44). While comparing per-cell orderings for cell22, the ordering of cells was preserved (coefficient 0.081, stderr 0.041, n = 50). While bootstrapping the CI for cell12, two cells fell out of the usable range (coefficient 0.159, stderr 0.045, n = 52). While checking residual autocorrelation for cell24, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.229, stderr 0.047, n = 52). While segmenting epochs for cell23, nothing in the figure changed at print size (coefficient 0.141, stderr 0.050, n = 52).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell08    0.101  0.036   0.030  0.171  56        1000
cell17    0.173  0.032   0.110  0.235  41        4000
cell10    0.093  0.041   0.012  0.175  38        4000
cell08    0.169  0.032   0.107  0.232  53        1000
cell15    0.182  0.030   0.124  0.241  39        500
cell01    0.178  0.016   0.146  0.210  54        4000
cell15    0.089  0.038   0.015  0.163  40        4000
cell20    0.163  0.010   0.143  0.183  56        1000
cell07    0.267  0.029   0.210  0.324  55        1000
cell13    0.196  0.040   0.117  0.274  40        2000
cell02    0.199  0.019   0.163  0.236  52        2000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell13    0.185  0.046   0.095  0.275  42        500
cell18    0.113  0.043   0.029  0.196  57        4000
cell02    0.091  0.045   0.002  0.180  52        500
cell17    0.245  0.029   0.188  0.302  53        4000
cell10    0.208  0.050   0.110  0.305  56        500
cell21    0.222  0.016   0.191  0.253  43        1000
cell13    0.279  0.020   0.240  0.317  55        4000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell11    0.211  0.011   0.189  0.233  43        500
cell12    0.275  0.029   0.219  0.331  40        4000
cell07    0.281  0.041   0.201  0.361  51        1000
cell18    0.253  0.020   0.213  0.292  52        2000
cell16    0.300  0.018   0.265  0.335  44        1000
cell12    0.196  0.014   0.169  0.224  45        500
cell03    0.229  0.017   0.196  0.262  58        1000
cell03    0.089  0.036   0.020  0.159  53        500
cell09    0.153  0.048   0.059  0.247  54        2000
cell06    0.143  0.021   0.102  0.185  46        500
cell03    0.123  0.026   0.072  0.173  50        2000
```

### Step 12: fitting the one-lag kernel

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell17    0.088  0.043   0.005  0.171  48        2000
cell19    0.133  0.047   0.040  0.226  58        500
cell13    0.286  0.027   0.232  0.340  54        1000
cell07    0.197  0.034   0.131  0.263  50        2000
cell01    0.115  0.044   0.030  0.201  53        1000
cell11    0.293  0.045   0.205  0.382  56        1000
cell21    0.171  0.029   0.114  0.228  49        500
cell03    0.184  0.025   0.136  0.232  42        4000
cell08    0.100  0.022   0.057  0.144  54        1000
cell24    0.257  0.044   0.170  0.344  41        500
cell22    0.258  0.013   0.233  0.283  53        500
cell10    0.129  0.023   0.084  0.174  50        500
cell18    0.251  0.031   0.190  0.312  46        500
```

While comparing per-cell orderings for cell17, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.187, stderr 0.047, n = 52). While re-exporting the raw traces for cell22, the ordering of cells was preserved (coefficient 0.175, stderr 0.035, n = 53). While comparing per-cell orderings for cell15, nothing in the figure changed at print size (coefficient 0.243, stderr 0.033, n = 55). While segmenting epochs for cell17, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.177, stderr 0.012, n = 55). Worth noting for the writeup, though not a result on its own.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell03    0.270  0.042   0.188  0.351  41        2000
cell02    0.152  0.046   0.061  0.243  47        500
cell01    0.146  0.031   0.086  0.206  51        1000
cell14    0.105  0.031   0.044  0.166  46        4000
cell11    0.196  0.011   0.174  0.217  57        500
cell08    0.249  0.043   0.165  0.333  41        1000
cell07    0.159  0.042   0.076  0.242  52        2000
```

While auditing the holding potential column for cell14, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.187, stderr 0.038, n = 47). While comparing per-cell orderings for cell13, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.207, stderr 0.020, n = 48). While fitting the one-lag kernel for cell02, the estimate moved less than one standard error (coefficient 0.128, stderr 0.034, n = 46). While re-running with a tighter segmentation threshold for cell07, the coefficient tracked epoch count more closely than duration (coefficient 0.158, stderr 0.038, n = 45). While auditing the holding potential column for cell02, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.269, stderr 0.034, n = 40). Noted and moved on; it does not change the decision.

### Step 13: re-running with a tighter segmentation threshold

While auditing the holding potential column for cell19, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.145, stderr 0.022, n = 40). While fitting the one-lag kernel for cell04, two cells fell out of the usable range (coefficient 0.282, stderr 0.036, n = 38). While segmenting epochs for cell11, nothing in the figure changed at print size (coefficient 0.138, stderr 0.039, n = 58). This is the part that will need a real statistical argument.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell15    0.205  0.019   0.169  0.241  43        2000
cell24    0.302  0.047   0.211  0.394  58        2000
cell10    0.096  0.018   0.061  0.130  47        500
cell11    0.214  0.030   0.154  0.273  47        4000
cell22    0.097  0.037   0.024  0.169  39        2000
cell22    0.143  0.013   0.117  0.169  58        1000
cell19    0.302  0.043   0.218  0.386  50        1000
cell06    0.292  0.030   0.233  0.350  43        500
cell08    0.179  0.037   0.106  0.252  46        2000
cell18    0.125  0.046   0.035  0.216  39        4000
cell21    0.174  0.011   0.153  0.194  43        4000
cell16    0.221  0.028   0.166  0.276  52        500
cell16    0.111  0.038   0.038  0.185  42        2000
cell08    0.202  0.012   0.177  0.226  50        1000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell19    0.145  0.045   0.056  0.234  45        4000
cell10    0.218  0.013   0.193  0.244  46        1000
cell18    0.088  0.043   0.004  0.172  49        500
cell24    0.082  0.037   0.010  0.153  39        1000
cell22    0.091  0.036   0.020  0.161  43        4000
cell06    0.279  0.037   0.206  0.351  56        500
cell18    0.150  0.026   0.099  0.202  57        4000
cell17    0.309  0.025   0.260  0.358  52        1000
cell18    0.168  0.014   0.140  0.196  42        500
cell05    0.246  0.031   0.185  0.307  46        4000
cell07    0.267  0.049   0.170  0.363  43        4000
cell06    0.235  0.046   0.146  0.325  47        500
cell04    0.306  0.026   0.254  0.357  41        500
cell08    0.175  0.050   0.078  0.272  47        2000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell02    0.182  0.025   0.133  0.231  40        500
cell07    0.212  0.050   0.114  0.309  54        2000
cell09    0.105  0.021   0.064  0.146  45        1000
cell20    0.298  0.044   0.212  0.383  45        500
cell06    0.125  0.010   0.105  0.146  55        4000
cell07    0.252  0.030   0.193  0.311  51        4000
cell07    0.154  0.031   0.093  0.215  52        4000
cell17    0.225  0.025   0.177  0.274  40        2000
cell07    0.201  0.017   0.168  0.233  57        1000
cell07    0.213  0.036   0.143  0.284  48        500
cell23    0.092  0.041   0.011  0.173  56        500
cell14    0.219  0.033   0.155  0.284  43        2000
cell23    0.147  0.030   0.088  0.206  56        4000
```

### Step 14: auditing the holding potential column

While auditing the holding potential column for cell04, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.080, stderr 0.013, n = 44). While checking residual autocorrelation for cell24, the CI narrowed by roughly a tenth (coefficient 0.309, stderr 0.027, n = 38). While re-running with a tighter segmentation threshold for cell13, nothing in the figure changed at print size (coefficient 0.091, stderr 0.029, n = 44). This is the part that will need a real statistical argument.

While checking residual autocorrelation for cell19, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.161, stderr 0.020, n = 40). While comparing per-cell orderings for cell15, two cells fell out of the usable range (coefficient 0.089, stderr 0.023, n = 58). While auditing the holding potential column for cell13, nothing in the figure changed at print size (coefficient 0.281, stderr 0.037, n = 40). While comparing per-cell orderings for cell20, the CI narrowed by roughly a tenth (coefficient 0.287, stderr 0.039, n = 39). While re-exporting the raw traces for cell10, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.210, stderr 0.030, n = 56). Flagging it so it does not get rediscovered next week.

```python
coefs = fit_per_cell(rows, threshold=0.62)
lo, hi = ci(coefs, seed=77)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```python
coefs = fit_per_cell(rows, threshold=0.50)
lo, hi = ci(coefs, seed=35)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 15: segmenting epochs

While fitting the one-lag kernel for cell19, the ordering of cells was preserved (coefficient 0.265, stderr 0.036, n = 41). While bootstrapping the CI for cell21, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.152, stderr 0.047, n = 40). While re-exporting the raw traces for cell21, the CI narrowed by roughly a tenth (coefficient 0.101, stderr 0.013, n = 50). While bootstrapping the CI for cell12, the coefficient tracked epoch count more closely than duration (coefficient 0.225, stderr 0.016, n = 53). Flagging it so it does not get rediscovered next week.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell05    0.279  0.045   0.192  0.366  56        1000
cell23    0.291  0.041   0.210  0.373  44        1000
cell17    0.130  0.030   0.071  0.189  50        2000
cell03    0.292  0.014   0.265  0.318  48        1000
cell20    0.091  0.018   0.056  0.126  56        1000
cell20    0.126  0.030   0.067  0.185  47        500
cell11    0.158  0.023   0.114  0.203  45        4000
cell17    0.209  0.049   0.114  0.304  55        500
cell13    0.227  0.043   0.142  0.311  43        2000
```

While auditing the holding potential column for cell19, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.245, stderr 0.047, n = 39). While re-running with a tighter segmentation threshold for cell04, nothing in the figure changed at print size (coefficient 0.269, stderr 0.035, n = 47). While re-exporting the raw traces for cell06, the ordering of cells was preserved (coefficient 0.283, stderr 0.040, n = 39). While comparing per-cell orderings for cell12, the CI narrowed by roughly a tenth (coefficient 0.149, stderr 0.013, n = 42). While re-running with a tighter segmentation threshold for cell10, the CI narrowed by roughly a tenth (coefficient 0.155, stderr 0.029, n = 39).

### Step 16: segmenting epochs

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell04    0.125  0.037   0.051  0.198  47        4000
cell18    0.186  0.049   0.091  0.282  49        1000
cell01    0.146  0.046   0.055  0.237  40        2000
cell13    0.147  0.015   0.117  0.177  52        2000
cell17    0.257  0.021   0.215  0.299  52        2000
cell07    0.150  0.030   0.092  0.208  53        500
cell12    0.127  0.012   0.104  0.150  42        2000
cell08    0.110  0.030   0.052  0.168  42        4000
cell18    0.145  0.013   0.120  0.171  52        1000
cell05    0.203  0.028   0.148  0.258  39        1000
cell23    0.126  0.044   0.040  0.211  58        500
cell18    0.239  0.013   0.214  0.263  55        4000
cell09    0.268  0.017   0.234  0.301  56        500
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell21    0.234  0.031   0.172  0.295  52        1000
cell07    0.156  0.026   0.105  0.207  42        1000
cell12    0.106  0.032   0.044  0.169  45        1000
cell11    0.193  0.029   0.136  0.250  57        2000
cell03    0.299  0.049   0.203  0.396  53        1000
cell14    0.132  0.041   0.052  0.213  56        2000
cell19    0.205  0.034   0.138  0.273  45        500
cell19    0.229  0.013   0.203  0.255  54        2000
cell21    0.249  0.033   0.184  0.315  58        2000
cell17    0.161  0.011   0.139  0.182  53        1000
```

While checking residual autocorrelation for cell13, the CI narrowed by roughly a tenth (coefficient 0.180, stderr 0.043, n = 42). While re-running with a tighter segmentation threshold for cell04, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.194, stderr 0.043, n = 50). While comparing per-cell orderings for cell08, the estimate moved less than one standard error (coefficient 0.188, stderr 0.040, n = 55). While re-exporting the raw traces for cell03, the estimate moved less than one standard error (coefficient 0.301, stderr 0.033, n = 42).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell24    0.272  0.020   0.232  0.311  45        4000
cell07    0.126  0.031   0.065  0.186  54        4000
cell04    0.302  0.031   0.241  0.364  48        2000
cell11    0.135  0.041   0.054  0.216  54        2000
cell16    0.294  0.050   0.197  0.391  57        1000
cell14    0.183  0.037   0.109  0.256  41        1000
cell01    0.181  0.017   0.148  0.213  56        2000
cell04    0.117  0.011   0.095  0.140  41        2000
```

### Step 17: re-exporting the raw traces

```python
coefs = fit_per_cell(rows, threshold=0.44)
lo, hi = ci(coefs, seed=98)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```python
coefs = fit_per_cell(rows, threshold=0.34)
lo, hi = ci(coefs, seed=30)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell11    0.276  0.046   0.187  0.366  41        2000
cell22    0.228  0.030   0.169  0.287  46        500
cell02    0.261  0.017   0.228  0.295  48        500
cell19    0.250  0.048   0.156  0.344  45        4000
cell23    0.303  0.032   0.240  0.366  55        1000
cell09    0.231  0.040   0.152  0.310  40        4000
cell19    0.094  0.034   0.027  0.161  41        500
cell11    0.163  0.043   0.079  0.248  45        4000
```

### Step 18: re-running with a tighter segmentation threshold

While auditing the holding potential column for cell01, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.176, stderr 0.042, n = 40). While auditing the holding potential column for cell10, nothing in the figure changed at print size (coefficient 0.235, stderr 0.047, n = 44). While re-running with a tighter segmentation threshold for cell22, nothing in the figure changed at print size (coefficient 0.176, stderr 0.049, n = 43). While bootstrapping the CI for cell11, nothing in the figure changed at print size (coefficient 0.290, stderr 0.020, n = 58). Parking this until the re-segmentation lands.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell20    0.250  0.040   0.171  0.329  40        4000
cell22    0.287  0.047   0.194  0.381  50        1000
cell01    0.188  0.040   0.110  0.266  43        2000
cell17    0.173  0.049   0.076  0.269  39        2000
cell11    0.200  0.048   0.106  0.295  49        2000
cell10    0.233  0.037   0.161  0.305  56        2000
cell08    0.247  0.035   0.178  0.317  52        1000
cell14    0.276  0.042   0.194  0.357  57        4000
cell05    0.309  0.027   0.256  0.362  44        2000
cell13    0.276  0.021   0.235  0.316  54        500
cell07    0.192  0.041   0.111  0.273  52        4000
```

While bootstrapping the CI for cell13, two cells fell out of the usable range (coefficient 0.142, stderr 0.038, n = 44). While comparing per-cell orderings for cell18, the CI narrowed by roughly a tenth (coefficient 0.296, stderr 0.030, n = 56). While comparing per-cell orderings for cell10, two cells fell out of the usable range (coefficient 0.099, stderr 0.025, n = 44). While comparing per-cell orderings for cell10, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.256, stderr 0.023, n = 56). While re-running with a tighter segmentation threshold for cell06, the estimate moved less than one standard error (coefficient 0.203, stderr 0.011, n = 44).

### Step 19: auditing the holding potential column

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell11    0.154  0.037   0.081  0.227  53        4000
cell01    0.227  0.037   0.156  0.299  40        500
cell06    0.111  0.048   0.016  0.207  49        2000
cell07    0.113  0.015   0.084  0.142  53        1000
cell08    0.288  0.045   0.200  0.376  39        1000
cell04    0.231  0.045   0.144  0.319  49        4000
cell03    0.240  0.012   0.217  0.262  53        4000
cell14    0.090  0.030   0.032  0.148  46        500
cell12    0.225  0.038   0.150  0.299  38        4000
cell11    0.285  0.022   0.242  0.329  39        1000
cell08    0.264  0.025   0.215  0.313  38        2000
```

```python
coefs = fit_per_cell(rows, threshold=0.65)
lo, hi = ci(coefs, seed=82)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 20: checking residual autocorrelation

While re-running with a tighter segmentation threshold for cell07, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.263, stderr 0.017, n = 39). While fitting the one-lag kernel for cell14, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.190, stderr 0.014, n = 45). While auditing the holding potential column for cell10, the coefficient tracked epoch count more closely than duration (coefficient 0.292, stderr 0.044, n = 44).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell04    0.221  0.037   0.148  0.294  58        1000
cell12    0.107  0.012   0.083  0.132  56        1000
cell05    0.246  0.049   0.151  0.341  47        2000
cell12    0.216  0.020   0.176  0.255  56        2000
cell18    0.119  0.032   0.057  0.181  39        1000
cell09    0.097  0.041   0.017  0.178  42        500
cell01    0.287  0.013   0.262  0.312  55        4000
cell22    0.238  0.026   0.187  0.289  44        1000
cell23    0.244  0.044   0.157  0.330  57        4000
```

### Step 21: comparing per-cell orderings

While bootstrapping the CI for cell22, the estimate moved less than one standard error (coefficient 0.157, stderr 0.014, n = 46). While checking residual autocorrelation for cell03, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.217, stderr 0.011, n = 48). While checking residual autocorrelation for cell05, the CI narrowed by roughly a tenth (coefficient 0.230, stderr 0.037, n = 54). While segmenting epochs for cell17, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.262, stderr 0.050, n = 47). While comparing per-cell orderings for cell18, the estimate moved less than one standard error (coefficient 0.129, stderr 0.016, n = 53).

While checking residual autocorrelation for cell20, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.221, stderr 0.033, n = 56). While auditing the holding potential column for cell03, the ordering of cells was preserved (coefficient 0.216, stderr 0.029, n = 55). While comparing per-cell orderings for cell12, two cells fell out of the usable range (coefficient 0.237, stderr 0.033, n = 41). While re-running with a tighter segmentation threshold for cell14, two cells fell out of the usable range (coefficient 0.221, stderr 0.016, n = 44).

While fitting the one-lag kernel for cell22, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.270, stderr 0.023, n = 41). While auditing the holding potential column for cell12, two cells fell out of the usable range (coefficient 0.088, stderr 0.025, n = 48). While re-exporting the raw traces for cell18, the estimate moved less than one standard error (coefficient 0.092, stderr 0.026, n = 44). Noted and moved on; it does not change the decision.

While auditing the holding potential column for cell21, the CI narrowed by roughly a tenth (coefficient 0.273, stderr 0.019, n = 43). While auditing the holding potential column for cell04, the estimate moved less than one standard error (coefficient 0.181, stderr 0.038, n = 53). While re-running with a tighter segmentation threshold for cell11, the estimate moved less than one standard error (coefficient 0.305, stderr 0.046, n = 42). While bootstrapping the CI for cell20, the ordering of cells was preserved (coefficient 0.186, stderr 0.049, n = 54). Flagging it so it does not get rediscovered next week.

### Step 22: auditing the holding potential column

While re-exporting the raw traces for cell04, two cells fell out of the usable range (coefficient 0.206, stderr 0.014, n = 41). While re-exporting the raw traces for cell03, two cells fell out of the usable range (coefficient 0.106, stderr 0.028, n = 52). While re-running with a tighter segmentation threshold for cell21, the ordering of cells was preserved (coefficient 0.287, stderr 0.032, n = 54). While bootstrapping the CI for cell19, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.182, stderr 0.013, n = 49).

While checking residual autocorrelation for cell07, nothing in the figure changed at print size (coefficient 0.306, stderr 0.023, n = 56). While fitting the one-lag kernel for cell11, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.176, stderr 0.037, n = 56). While checking residual autocorrelation for cell15, the CI narrowed by roughly a tenth (coefficient 0.295, stderr 0.032, n = 39). While comparing per-cell orderings for cell02, two cells fell out of the usable range (coefficient 0.308, stderr 0.039, n = 41). While re-running with a tighter segmentation threshold for cell02, nothing in the figure changed at print size (coefficient 0.302, stderr 0.012, n = 57).

### Step 23: segmenting epochs

While segmenting epochs for cell14, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.117, stderr 0.021, n = 42). While fitting the one-lag kernel for cell17, nothing in the figure changed at print size (coefficient 0.119, stderr 0.050, n = 48). While re-exporting the raw traces for cell11, the ordering of cells was preserved (coefficient 0.249, stderr 0.026, n = 50). While comparing per-cell orderings for cell05, the estimate moved less than one standard error (coefficient 0.285, stderr 0.039, n = 44). Worth noting for the writeup, though not a result on its own.

While auditing the holding potential column for cell07, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.239, stderr 0.012, n = 55). While checking residual autocorrelation for cell09, the estimate moved less than one standard error (coefficient 0.264, stderr 0.027, n = 51). While re-running with a tighter segmentation threshold for cell04, the ordering of cells was preserved (coefficient 0.202, stderr 0.030, n = 39). While checking residual autocorrelation for cell01, the CI narrowed by roughly a tenth (coefficient 0.221, stderr 0.044, n = 43). While bootstrapping the CI for cell03, the coefficient tracked epoch count more closely than duration (coefficient 0.303, stderr 0.035, n = 51). Noted and moved on; it does not change the decision.

While fitting the one-lag kernel for cell12, the CI narrowed by roughly a tenth (coefficient 0.088, stderr 0.030, n = 49). While comparing per-cell orderings for cell20, the estimate moved less than one standard error (coefficient 0.222, stderr 0.014, n = 57). While checking residual autocorrelation for cell22, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.301, stderr 0.047, n = 54). While segmenting epochs for cell11, the coefficient tracked epoch count more closely than duration (coefficient 0.190, stderr 0.010, n = 43). While fitting the one-lag kernel for cell15, nothing in the figure changed at print size (coefficient 0.260, stderr 0.029, n = 53). While checking residual autocorrelation for cell19, two cells fell out of the usable range (coefficient 0.163, stderr 0.016, n = 55).

While checking residual autocorrelation for cell23, the coefficient tracked epoch count more closely than duration (coefficient 0.097, stderr 0.012, n = 42). While comparing per-cell orderings for cell16, the estimate moved less than one standard error (coefficient 0.106, stderr 0.034, n = 55). While segmenting epochs for cell19, two cells fell out of the usable range (coefficient 0.085, stderr 0.012, n = 58). Parking this until the re-segmentation lands.

### Step 24: fitting the one-lag kernel

While segmenting epochs for cell06, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.298, stderr 0.029, n = 44). While fitting the one-lag kernel for cell07, the coefficient tracked epoch count more closely than duration (coefficient 0.104, stderr 0.037, n = 47). While fitting the one-lag kernel for cell24, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.234, stderr 0.015, n = 49). While comparing per-cell orderings for cell14, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.162, stderr 0.040, n = 55). While checking residual autocorrelation for cell21, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.137, stderr 0.022, n = 51). While comparing per-cell orderings for cell20, two cells fell out of the usable range (coefficient 0.111, stderr 0.040, n = 51).

While comparing per-cell orderings for cell06, the ordering of cells was preserved (coefficient 0.142, stderr 0.044, n = 49). While segmenting epochs for cell19, the coefficient tracked epoch count more closely than duration (coefficient 0.297, stderr 0.030, n = 53). While comparing per-cell orderings for cell18, the ordering of cells was preserved (coefficient 0.202, stderr 0.022, n = 53). While checking residual autocorrelation for cell10, the coefficient tracked epoch count more closely than duration (coefficient 0.157, stderr 0.026, n = 40). Worth noting for the writeup, though not a result on its own.

### Step 25: bootstrapping the CI

While auditing the holding potential column for cell19, the coefficient tracked epoch count more closely than duration (coefficient 0.190, stderr 0.035, n = 51). While checking residual autocorrelation for cell24, the ordering of cells was preserved (coefficient 0.245, stderr 0.023, n = 41). While auditing the holding potential column for cell03, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.263, stderr 0.034, n = 45). While comparing per-cell orderings for cell13, the coefficient tracked epoch count more closely than duration (coefficient 0.229, stderr 0.013, n = 55). While bootstrapping the CI for cell11, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.188, stderr 0.013, n = 43). Worth noting for the writeup, though not a result on its own.

While bootstrapping the CI for cell01, two cells fell out of the usable range (coefficient 0.293, stderr 0.022, n = 40). While checking residual autocorrelation for cell20, the estimate moved less than one standard error (coefficient 0.173, stderr 0.015, n = 40). While auditing the holding potential column for cell15, the coefficient tracked epoch count more closely than duration (coefficient 0.161, stderr 0.043, n = 56). While bootstrapping the CI for cell12, the estimate moved less than one standard error (coefficient 0.259, stderr 0.021, n = 44). Noted and moved on; it does not change the decision.

### Step 26: bootstrapping the CI

While bootstrapping the CI for cell01, the CI narrowed by roughly a tenth (coefficient 0.307, stderr 0.015, n = 40). While auditing the holding potential column for cell15, the estimate moved less than one standard error (coefficient 0.181, stderr 0.033, n = 40). While bootstrapping the CI for cell09, two cells fell out of the usable range (coefficient 0.246, stderr 0.037, n = 45). While fitting the one-lag kernel for cell24, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.110, stderr 0.044, n = 41). While comparing per-cell orderings for cell19, the coefficient tracked epoch count more closely than duration (coefficient 0.245, stderr 0.036, n = 40). This is the part that will need a real statistical argument.

While segmenting epochs for cell16, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.159, stderr 0.043, n = 45). While auditing the holding potential column for cell10, the estimate moved less than one standard error (coefficient 0.244, stderr 0.049, n = 53). While comparing per-cell orderings for cell22, the ordering of cells was preserved (coefficient 0.291, stderr 0.038, n = 55). While fitting the one-lag kernel for cell14, the CI narrowed by roughly a tenth (coefficient 0.085, stderr 0.037, n = 55). Noted and moved on; it does not change the decision.

While bootstrapping the CI for cell04, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.203, stderr 0.027, n = 48). While re-exporting the raw traces for cell10, the ordering of cells was preserved (coefficient 0.158, stderr 0.041, n = 38). While checking residual autocorrelation for cell22, the estimate moved less than one standard error (coefficient 0.188, stderr 0.041, n = 44). While checking residual autocorrelation for cell07, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.279, stderr 0.025, n = 40).

### Step 27: re-running with a tighter segmentation threshold

While checking residual autocorrelation for cell10, the ordering of cells was preserved (coefficient 0.241, stderr 0.048, n = 38). While checking residual autocorrelation for cell09, the coefficient tracked epoch count more closely than duration (coefficient 0.150, stderr 0.020, n = 41). While bootstrapping the CI for cell24, the ordering of cells was preserved (coefficient 0.139, stderr 0.016, n = 52).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell03    0.156  0.024   0.109  0.204  51        1000
cell15    0.261  0.025   0.212  0.309  50        4000
cell11    0.300  0.032   0.237  0.363  38        4000
cell17    0.137  0.028   0.082  0.191  48        500
cell11    0.183  0.015   0.153  0.212  39        1000
cell01    0.245  0.012   0.221  0.269  49        2000
cell02    0.106  0.034   0.040  0.172  54        4000
```

### Step 28: re-exporting the raw traces

While comparing per-cell orderings for cell18, the ordering of cells was preserved (coefficient 0.213, stderr 0.025, n = 46). While re-exporting the raw traces for cell21, the ordering of cells was preserved (coefficient 0.264, stderr 0.045, n = 54). While re-exporting the raw traces for cell12, the coefficient tracked epoch count more closely than duration (coefficient 0.215, stderr 0.020, n = 55). While auditing the holding potential column for cell14, the CI narrowed by roughly a tenth (coefficient 0.162, stderr 0.041, n = 52). While segmenting epochs for cell18, the ordering of cells was preserved (coefficient 0.255, stderr 0.032, n = 49). While segmenting epochs for cell21, two cells fell out of the usable range (coefficient 0.161, stderr 0.021, n = 40). Worth noting for the writeup, though not a result on its own.

While auditing the holding potential column for cell24, two cells fell out of the usable range (coefficient 0.160, stderr 0.046, n = 48). While segmenting epochs for cell18, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.165, stderr 0.048, n = 45). While auditing the holding potential column for cell06, the coefficient tracked epoch count more closely than duration (coefficient 0.274, stderr 0.017, n = 43). While checking residual autocorrelation for cell14, two cells fell out of the usable range (coefficient 0.117, stderr 0.027, n = 58).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell02    0.273  0.022   0.231  0.315  54        500
cell09    0.154  0.035   0.086  0.222  56        4000
cell17    0.237  0.031   0.175  0.299  54        500
cell09    0.262  0.032   0.199  0.325  51        1000
cell02    0.215  0.050   0.118  0.312  51        500
cell01    0.229  0.033   0.164  0.294  38        500
```

While fitting the one-lag kernel for cell16, the CI narrowed by roughly a tenth (coefficient 0.237, stderr 0.014, n = 38). While segmenting epochs for cell12, the CI narrowed by roughly a tenth (coefficient 0.272, stderr 0.020, n = 46). While re-running with a tighter segmentation threshold for cell24, the CI narrowed by roughly a tenth (coefficient 0.303, stderr 0.028, n = 57). While auditing the holding potential column for cell14, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.227, stderr 0.014, n = 41).

### Step 29: fitting the one-lag kernel

While bootstrapping the CI for cell24, the CI narrowed by roughly a tenth (coefficient 0.131, stderr 0.029, n = 42). While bootstrapping the CI for cell09, two cells fell out of the usable range (coefficient 0.288, stderr 0.040, n = 51). While auditing the holding potential column for cell12, nothing in the figure changed at print size (coefficient 0.128, stderr 0.023, n = 38). While checking residual autocorrelation for cell23, the coefficient tracked epoch count more closely than duration (coefficient 0.134, stderr 0.011, n = 47). Parking this until the re-segmentation lands.

While re-running with a tighter segmentation threshold for cell13, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.165, stderr 0.017, n = 56). While fitting the one-lag kernel for cell06, two cells fell out of the usable range (coefficient 0.232, stderr 0.017, n = 54). While comparing per-cell orderings for cell22, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.282, stderr 0.037, n = 54). While re-exporting the raw traces for cell09, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.087, stderr 0.036, n = 46). This is the part that will need a real statistical argument.

While bootstrapping the CI for cell03, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.297, stderr 0.042, n = 53). While fitting the one-lag kernel for cell08, the ordering of cells was preserved (coefficient 0.144, stderr 0.035, n = 58). While bootstrapping the CI for cell23, the ordering of cells was preserved (coefficient 0.185, stderr 0.025, n = 53). This is the part that will need a real statistical argument.

### Step 30: segmenting epochs

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell15    0.111  0.028   0.056  0.167  48        2000
cell19    0.299  0.031   0.239  0.360  50        1000
cell14    0.237  0.026   0.186  0.288  54        500
cell02    0.231  0.035   0.162  0.301  39        4000
cell10    0.167  0.025   0.118  0.217  48        1000
cell02    0.162  0.045   0.074  0.250  53        4000
```

While bootstrapping the CI for cell23, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.112, stderr 0.042, n = 46). While re-exporting the raw traces for cell18, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.111, stderr 0.033, n = 44). While fitting the one-lag kernel for cell02, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.081, stderr 0.020, n = 49). While checking residual autocorrelation for cell11, nothing in the figure changed at print size (coefficient 0.206, stderr 0.032, n = 54). While segmenting epochs for cell14, the estimate moved less than one standard error (coefficient 0.162, stderr 0.031, n = 41). Worth noting for the writeup, though not a result on its own.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell21    0.240  0.031   0.180  0.301  39        2000
cell18    0.307  0.040   0.228  0.387  39        500
cell08    0.148  0.034   0.083  0.214  49        1000
cell18    0.125  0.025   0.077  0.173  46        4000
cell21    0.161  0.035   0.094  0.229  53        2000
cell12    0.102  0.016   0.071  0.133  52        1000
cell19    0.264  0.022   0.220  0.308  52        500
cell09    0.167  0.045   0.078  0.256  58        500
cell24    0.185  0.013   0.159  0.211  56        500
cell14    0.239  0.041   0.159  0.319  57        500
cell02    0.243  0.049   0.146  0.340  38        2000
```

While auditing the holding potential column for cell21, the coefficient tracked epoch count more closely than duration (coefficient 0.159, stderr 0.032, n = 52). While checking residual autocorrelation for cell22, the CI narrowed by roughly a tenth (coefficient 0.221, stderr 0.028, n = 39). While comparing per-cell orderings for cell09, the CI narrowed by roughly a tenth (coefficient 0.104, stderr 0.019, n = 54). While fitting the one-lag kernel for cell05, the estimate moved less than one standard error (coefficient 0.153, stderr 0.016, n = 47). While fitting the one-lag kernel for cell13, nothing in the figure changed at print size (coefficient 0.160, stderr 0.048, n = 45). While re-exporting the raw traces for cell20, the estimate moved less than one standard error (coefficient 0.305, stderr 0.042, n = 38).

### Step 31: fitting the one-lag kernel

While re-running with a tighter segmentation threshold for cell12, the coefficient tracked epoch count more closely than duration (coefficient 0.285, stderr 0.035, n = 46). While re-exporting the raw traces for cell11, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.260, stderr 0.029, n = 39). While comparing per-cell orderings for cell12, the coefficient tracked epoch count more closely than duration (coefficient 0.228, stderr 0.027, n = 53). While re-running with a tighter segmentation threshold for cell09, the coefficient tracked epoch count more closely than duration (coefficient 0.305, stderr 0.034, n = 46).

While bootstrapping the CI for cell19, nothing in the figure changed at print size (coefficient 0.111, stderr 0.022, n = 43). While re-exporting the raw traces for cell21, the ordering of cells was preserved (coefficient 0.164, stderr 0.033, n = 49). While checking residual autocorrelation for cell12, the CI narrowed by roughly a tenth (coefficient 0.233, stderr 0.025, n = 42). While checking residual autocorrelation for cell05, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.180, stderr 0.037, n = 46). While bootstrapping the CI for cell22, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.266, stderr 0.017, n = 46).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell14    0.114  0.019   0.078  0.151  46        500
cell13    0.211  0.027   0.159  0.263  55        500
cell02    0.245  0.014   0.217  0.274  56        500
cell23    0.213  0.030   0.155  0.271  41        1000
cell01    0.124  0.035   0.055  0.193  52        2000
cell24    0.290  0.026   0.238  0.341  40        1000
```

```python
coefs = fit_per_cell(rows, threshold=0.53)
lo, hi = ci(coefs, seed=82)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 32: checking residual autocorrelation

While checking residual autocorrelation for cell13, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.187, stderr 0.048, n = 45). While bootstrapping the CI for cell10, the ordering of cells was preserved (coefficient 0.088, stderr 0.018, n = 55). While re-running with a tighter segmentation threshold for cell03, the CI narrowed by roughly a tenth (coefficient 0.159, stderr 0.017, n = 40). While bootstrapping the CI for cell23, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.108, stderr 0.037, n = 57). Parking this until the re-segmentation lands.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell09    0.115  0.042   0.032  0.198  40        1000
cell14    0.094  0.017   0.060  0.128  58        4000
cell19    0.224  0.022   0.181  0.266  57        2000
cell19    0.237  0.043   0.153  0.320  52        500
cell21    0.143  0.010   0.123  0.164  42        1000
cell09    0.218  0.021   0.178  0.259  48        1000
cell22    0.096  0.043   0.012  0.179  58        1000
cell08    0.152  0.028   0.098  0.206  58        1000
cell02    0.274  0.043   0.189  0.359  51        4000
cell21    0.124  0.047   0.031  0.217  49        2000
cell22    0.219  0.037   0.147  0.291  46        4000
cell16    0.241  0.027   0.187  0.295  55        2000
cell04    0.266  0.047   0.174  0.358  54        500
```

### Step 33: fitting the one-lag kernel

While segmenting epochs for cell17, the CI narrowed by roughly a tenth (coefficient 0.262, stderr 0.049, n = 39). While auditing the holding potential column for cell03, the coefficient tracked epoch count more closely than duration (coefficient 0.290, stderr 0.010, n = 52). While checking residual autocorrelation for cell07, two cells fell out of the usable range (coefficient 0.092, stderr 0.047, n = 58). Noted and moved on; it does not change the decision.

While fitting the one-lag kernel for cell23, the CI narrowed by roughly a tenth (coefficient 0.124, stderr 0.021, n = 54). While re-running with a tighter segmentation threshold for cell20, the estimate moved less than one standard error (coefficient 0.140, stderr 0.039, n = 52). While re-exporting the raw traces for cell12, the coefficient tracked epoch count more closely than duration (coefficient 0.096, stderr 0.046, n = 48). While checking residual autocorrelation for cell12, the CI narrowed by roughly a tenth (coefficient 0.167, stderr 0.042, n = 57). While bootstrapping the CI for cell22, the CI narrowed by roughly a tenth (coefficient 0.163, stderr 0.028, n = 57). While auditing the holding potential column for cell14, nothing in the figure changed at print size (coefficient 0.127, stderr 0.030, n = 54).

While checking residual autocorrelation for cell07, the ordering of cells was preserved (coefficient 0.210, stderr 0.013, n = 47). While comparing per-cell orderings for cell07, the CI narrowed by roughly a tenth (coefficient 0.300, stderr 0.028, n = 43). While bootstrapping the CI for cell23, the coefficient tracked epoch count more closely than duration (coefficient 0.227, stderr 0.034, n = 48). This is the part that will need a real statistical argument.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell24    0.291  0.011   0.268  0.313  51        2000
cell07    0.280  0.014   0.252  0.307  44        4000
cell01    0.300  0.048   0.205  0.395  55        1000
cell23    0.125  0.027   0.073  0.178  58        2000
cell08    0.276  0.049   0.181  0.371  50        4000
cell17    0.179  0.030   0.121  0.237  43        2000
cell19    0.281  0.024   0.233  0.329  55        1000
```

### Step 34: segmenting epochs

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell13    0.300  0.029   0.243  0.356  40        4000
cell15    0.173  0.018   0.138  0.208  49        4000
cell18    0.119  0.023   0.074  0.163  42        2000
cell02    0.254  0.038   0.180  0.329  54        1000
cell14    0.305  0.015   0.275  0.335  40        2000
cell06    0.177  0.029   0.121  0.234  51        2000
cell22    0.111  0.014   0.083  0.139  49        4000
cell01    0.257  0.014   0.230  0.284  54        1000
cell16    0.165  0.022   0.121  0.208  48        500
cell10    0.211  0.035   0.141  0.280  52        2000
cell13    0.104  0.011   0.083  0.125  42        1000
cell18    0.162  0.028   0.107  0.217  43        1000
cell13    0.162  0.024   0.116  0.209  46        1000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell04    0.089  0.040   0.011  0.168  57        4000
cell07    0.181  0.042   0.098  0.265  40        2000
cell09    0.197  0.042   0.115  0.279  48        1000
cell18    0.266  0.037   0.194  0.339  51        2000
cell04    0.248  0.019   0.209  0.286  58        2000
cell23    0.243  0.017   0.211  0.276  40        500
cell11    0.178  0.027   0.124  0.232  43        2000
cell16    0.172  0.039   0.095  0.249  41        4000
cell01    0.190  0.039   0.114  0.265  39        1000
cell15    0.238  0.046   0.148  0.328  50        1000
```

While re-exporting the raw traces for cell19, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.268, stderr 0.034, n = 46). While checking residual autocorrelation for cell07, two cells fell out of the usable range (coefficient 0.162, stderr 0.032, n = 51). While segmenting epochs for cell18, the CI narrowed by roughly a tenth (coefficient 0.290, stderr 0.050, n = 43). Parking this until the re-segmentation lands.

While re-running with a tighter segmentation threshold for cell02, the estimate moved less than one standard error (coefficient 0.097, stderr 0.031, n = 49). While comparing per-cell orderings for cell09, the ordering of cells was preserved (coefficient 0.250, stderr 0.028, n = 39). While segmenting epochs for cell09, nothing in the figure changed at print size (coefficient 0.085, stderr 0.014, n = 51). While bootstrapping the CI for cell14, the coefficient tracked epoch count more closely than duration (coefficient 0.152, stderr 0.015, n = 48).

### Step 35: auditing the holding potential column

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell01    0.244  0.025   0.195  0.293  46        1000
cell11    0.124  0.026   0.074  0.175  49        4000
cell08    0.133  0.012   0.110  0.157  44        4000
cell05    0.116  0.033   0.051  0.180  48        1000
cell18    0.175  0.027   0.122  0.228  54        1000
cell22    0.307  0.019   0.270  0.344  39        4000
cell01    0.305  0.014   0.277  0.333  39        2000
cell17    0.244  0.026   0.192  0.296  45        1000
cell22    0.217  0.025   0.169  0.265  46        4000
cell15    0.231  0.038   0.155  0.306  55        2000
cell12    0.114  0.023   0.070  0.158  53        2000
cell19    0.246  0.040   0.168  0.324  49        4000
cell04    0.229  0.028   0.175  0.283  39        2000
```

While checking residual autocorrelation for cell06, the ordering of cells was preserved (coefficient 0.236, stderr 0.014, n = 54). While segmenting epochs for cell17, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.172, stderr 0.031, n = 45). While comparing per-cell orderings for cell07, the ordering of cells was preserved (coefficient 0.096, stderr 0.048, n = 38).

### Step 36: checking residual autocorrelation

While fitting the one-lag kernel for cell10, nothing in the figure changed at print size (coefficient 0.288, stderr 0.042, n = 38). While re-exporting the raw traces for cell07, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.301, stderr 0.045, n = 40). While checking residual autocorrelation for cell22, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.139, stderr 0.024, n = 54). While segmenting epochs for cell16, two cells fell out of the usable range (coefficient 0.108, stderr 0.042, n = 55). While re-running with a tighter segmentation threshold for cell23, the ordering of cells was preserved (coefficient 0.089, stderr 0.045, n = 47). While re-running with a tighter segmentation threshold for cell16, the estimate moved less than one standard error (coefficient 0.156, stderr 0.046, n = 48).

While re-running with a tighter segmentation threshold for cell07, the estimate moved less than one standard error (coefficient 0.190, stderr 0.031, n = 55). While comparing per-cell orderings for cell21, two cells fell out of the usable range (coefficient 0.280, stderr 0.025, n = 56). While re-running with a tighter segmentation threshold for cell20, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.137, stderr 0.028, n = 45). While fitting the one-lag kernel for cell22, the estimate moved less than one standard error (coefficient 0.214, stderr 0.021, n = 56).

While bootstrapping the CI for cell20, the coefficient tracked epoch count more closely than duration (coefficient 0.086, stderr 0.019, n = 55). While segmenting epochs for cell12, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.287, stderr 0.034, n = 42). While re-exporting the raw traces for cell21, nothing in the figure changed at print size (coefficient 0.226, stderr 0.044, n = 49).

### Step 37: re-exporting the raw traces

While fitting the one-lag kernel for cell08, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.209, stderr 0.043, n = 41). While comparing per-cell orderings for cell12, nothing in the figure changed at print size (coefficient 0.140, stderr 0.013, n = 47). While re-running with a tighter segmentation threshold for cell10, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.252, stderr 0.019, n = 56). While bootstrapping the CI for cell07, the estimate moved less than one standard error (coefficient 0.135, stderr 0.035, n = 42). While re-running with a tighter segmentation threshold for cell19, nothing in the figure changed at print size (coefficient 0.215, stderr 0.021, n = 41). While auditing the holding potential column for cell12, two cells fell out of the usable range (coefficient 0.135, stderr 0.023, n = 53).

While segmenting epochs for cell02, the coefficient tracked epoch count more closely than duration (coefficient 0.210, stderr 0.030, n = 49). While auditing the holding potential column for cell08, two cells fell out of the usable range (coefficient 0.282, stderr 0.018, n = 53). While re-exporting the raw traces for cell14, two cells fell out of the usable range (coefficient 0.084, stderr 0.036, n = 46). While re-exporting the raw traces for cell12, two cells fell out of the usable range (coefficient 0.246, stderr 0.026, n = 51). While checking residual autocorrelation for cell19, the ordering of cells was preserved (coefficient 0.146, stderr 0.043, n = 43). Parking this until the re-segmentation lands.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell10    0.111  0.026   0.060  0.162  43        4000
cell02    0.231  0.050   0.133  0.328  55        1000
cell18    0.179  0.022   0.135  0.222  42        2000
cell15    0.165  0.034   0.098  0.232  39        4000
cell19    0.167  0.048   0.073  0.262  46        2000
cell24    0.125  0.028   0.071  0.179  41        500
cell20    0.184  0.025   0.135  0.233  39        4000
cell20    0.283  0.041   0.202  0.363  44        1000
cell03    0.196  0.035   0.127  0.265  56        1000
cell24    0.180  0.034   0.113  0.247  49        2000
cell21    0.100  0.048   0.006  0.195  50        2000
cell02    0.176  0.028   0.122  0.230  44        1000
cell09    0.215  0.050   0.117  0.312  38        2000
```

### Step 38: fitting the one-lag kernel

While segmenting epochs for cell16, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.154, stderr 0.039, n = 54). While re-exporting the raw traces for cell18, the CI narrowed by roughly a tenth (coefficient 0.164, stderr 0.047, n = 46). While comparing per-cell orderings for cell03, the estimate moved less than one standard error (coefficient 0.129, stderr 0.046, n = 48). While checking residual autocorrelation for cell13, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.287, stderr 0.023, n = 41). While segmenting epochs for cell22, the estimate moved less than one standard error (coefficient 0.189, stderr 0.023, n = 50). While fitting the one-lag kernel for cell16, nothing in the figure changed at print size (coefficient 0.211, stderr 0.040, n = 55). Worth noting for the writeup, though not a result on its own.

While auditing the holding potential column for cell24, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.227, stderr 0.038, n = 49). While auditing the holding potential column for cell20, the estimate moved less than one standard error (coefficient 0.140, stderr 0.037, n = 45). While checking residual autocorrelation for cell20, nothing in the figure changed at print size (coefficient 0.121, stderr 0.047, n = 58). While auditing the holding potential column for cell23, the estimate moved less than one standard error (coefficient 0.166, stderr 0.046, n = 57). While checking residual autocorrelation for cell12, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.152, stderr 0.038, n = 44). While re-exporting the raw traces for cell02, the estimate moved less than one standard error (coefficient 0.221, stderr 0.034, n = 42). Parking this until the re-segmentation lands.

While comparing per-cell orderings for cell18, the coefficient tracked epoch count more closely than duration (coefficient 0.150, stderr 0.013, n = 55). While segmenting epochs for cell08, the CI narrowed by roughly a tenth (coefficient 0.095, stderr 0.012, n = 51). While checking residual autocorrelation for cell23, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.244, stderr 0.015, n = 40). Noted and moved on; it does not change the decision.

While checking residual autocorrelation for cell14, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.148, stderr 0.027, n = 43). While comparing per-cell orderings for cell16, nothing in the figure changed at print size (coefficient 0.296, stderr 0.024, n = 47). While segmenting epochs for cell12, the estimate moved less than one standard error (coefficient 0.183, stderr 0.036, n = 54). While bootstrapping the CI for cell20, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.177, stderr 0.032, n = 48). While re-exporting the raw traces for cell08, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.296, stderr 0.044, n = 44).

