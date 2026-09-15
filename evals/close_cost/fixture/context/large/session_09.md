# Prior session 9 of 20

Transcript of an earlier working session on the history-kernel analysis.

### Step 1: re-exporting the raw traces

While segmenting epochs for cell04, the ordering of cells was preserved (coefficient 0.212, stderr 0.042, n = 58). While segmenting epochs for cell22, the coefficient tracked epoch count more closely than duration (coefficient 0.239, stderr 0.047, n = 53). While fitting the one-lag kernel for cell05, the CI narrowed by roughly a tenth (coefficient 0.282, stderr 0.013, n = 46).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell03    0.267  0.036   0.196  0.338  54        4000
cell04    0.271  0.037   0.198  0.344  44        4000
cell24    0.101  0.015   0.073  0.130  58        1000
cell07    0.134  0.035   0.064  0.203  45        500
cell21    0.122  0.025   0.074  0.171  50        1000
cell15    0.261  0.015   0.232  0.290  47        4000
cell14    0.160  0.037   0.087  0.232  50        1000
cell07    0.164  0.012   0.141  0.187  39        2000
cell16    0.185  0.017   0.151  0.218  54        500
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell05    0.226  0.022   0.182  0.271  54        500
cell09    0.096  0.022   0.053  0.138  41        1000
cell17    0.256  0.013   0.230  0.281  49        500
cell13    0.151  0.021   0.110  0.191  54        500
cell12    0.096  0.049   0.000  0.191  53        500
cell04    0.131  0.049   0.035  0.227  39        1000
cell16    0.262  0.046   0.172  0.352  42        2000
cell23    0.253  0.029   0.196  0.310  38        1000
cell19    0.155  0.039   0.079  0.232  41        4000
cell21    0.280  0.024   0.232  0.327  41        500
cell18    0.088  0.016   0.058  0.119  48        2000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell19    0.204  0.015   0.175  0.234  39        500
cell22    0.264  0.012   0.240  0.287  47        2000
cell02    0.152  0.045   0.064  0.240  40        4000
cell03    0.181  0.048   0.088  0.274  56        500
cell11    0.284  0.034   0.216  0.352  40        4000
cell06    0.175  0.030   0.116  0.235  45        1000
cell18    0.286  0.046   0.196  0.375  47        500
cell17    0.255  0.043   0.171  0.339  42        4000
```

### Step 2: auditing the holding potential column

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell02    0.108  0.041   0.028  0.189  58        500
cell19    0.179  0.037   0.105  0.252  51        4000
cell06    0.272  0.044   0.186  0.358  57        500
cell19    0.224  0.042   0.141  0.306  39        500
cell16    0.223  0.024   0.176  0.269  44        500
cell10    0.271  0.028   0.216  0.327  42        4000
cell02    0.153  0.033   0.088  0.218  53        500
cell16    0.255  0.042   0.173  0.338  48        500
cell22    0.273  0.038   0.199  0.348  58        500
```

While checking residual autocorrelation for cell22, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.248, stderr 0.011, n = 41). While comparing per-cell orderings for cell13, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.137, stderr 0.020, n = 56). While auditing the holding potential column for cell21, the estimate moved less than one standard error (coefficient 0.125, stderr 0.045, n = 46).

### Step 3: fitting the one-lag kernel

```python
coefs = fit_per_cell(rows, threshold=0.70)
lo, hi = ci(coefs, seed=91)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell16    0.111  0.019   0.074  0.147  55        4000
cell15    0.305  0.029   0.248  0.362  46        1000
cell09    0.246  0.040   0.167  0.325  39        500
cell11    0.136  0.023   0.091  0.182  55        1000
cell13    0.141  0.012   0.119  0.164  52        2000
cell20    0.136  0.014   0.109  0.163  41        500
cell18    0.261  0.034   0.194  0.329  38        500
cell15    0.261  0.046   0.170  0.351  48        4000
```

### Step 4: checking residual autocorrelation

While re-running with a tighter segmentation threshold for cell16, the coefficient tracked epoch count more closely than duration (coefficient 0.095, stderr 0.030, n = 44). While re-exporting the raw traces for cell19, the estimate moved less than one standard error (coefficient 0.241, stderr 0.046, n = 41). While checking residual autocorrelation for cell05, the estimate moved less than one standard error (coefficient 0.294, stderr 0.011, n = 58). While checking residual autocorrelation for cell01, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.269, stderr 0.045, n = 58). While re-running with a tighter segmentation threshold for cell07, the ordering of cells was preserved (coefficient 0.099, stderr 0.017, n = 54). While auditing the holding potential column for cell13, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.180, stderr 0.030, n = 56).

```python
coefs = fit_per_cell(rows, threshold=0.51)
lo, hi = ci(coefs, seed=43)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell03    0.201  0.034   0.134  0.268  49        4000
cell16    0.131  0.026   0.080  0.181  41        1000
cell17    0.247  0.045   0.158  0.336  48        500
cell12    0.146  0.030   0.087  0.205  41        1000
cell02    0.154  0.026   0.103  0.206  54        1000
cell15    0.298  0.020   0.259  0.337  55        2000
cell01    0.200  0.016   0.168  0.232  50        4000
cell13    0.227  0.036   0.156  0.299  50        500
cell18    0.254  0.037   0.182  0.326  43        500
cell06    0.163  0.026   0.113  0.213  46        500
```

### Step 5: checking residual autocorrelation

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell14    0.126  0.019   0.089  0.163  51        2000
cell02    0.086  0.032   0.023  0.148  56        1000
cell04    0.249  0.041   0.170  0.329  44        4000
cell22    0.288  0.031   0.229  0.348  46        2000
cell20    0.128  0.027   0.074  0.181  39        500
cell17    0.086  0.031   0.025  0.147  42        1000
cell13    0.210  0.032   0.148  0.272  44        2000
cell19    0.187  0.043   0.103  0.272  46        2000
cell15    0.112  0.011   0.089  0.134  39        2000
```

While re-exporting the raw traces for cell08, the CI narrowed by roughly a tenth (coefficient 0.247, stderr 0.015, n = 58). While segmenting epochs for cell07, the estimate moved less than one standard error (coefficient 0.104, stderr 0.011, n = 44). While checking residual autocorrelation for cell04, nothing in the figure changed at print size (coefficient 0.268, stderr 0.036, n = 41).

While segmenting epochs for cell07, the CI narrowed by roughly a tenth (coefficient 0.093, stderr 0.011, n = 47). While auditing the holding potential column for cell17, nothing in the figure changed at print size (coefficient 0.265, stderr 0.034, n = 53). While re-exporting the raw traces for cell11, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.091, stderr 0.040, n = 40). While segmenting epochs for cell01, two cells fell out of the usable range (coefficient 0.084, stderr 0.034, n = 42). While checking residual autocorrelation for cell04, two cells fell out of the usable range (coefficient 0.110, stderr 0.021, n = 41). Parking this until the re-segmentation lands.

### Step 6: fitting the one-lag kernel

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell15    0.196  0.045   0.108  0.284  58        4000
cell14    0.195  0.011   0.173  0.216  48        2000
cell23    0.261  0.041   0.181  0.341  54        2000
cell21    0.264  0.044   0.178  0.350  58        4000
cell16    0.125  0.025   0.075  0.175  49        500
cell05    0.213  0.050   0.115  0.310  44        1000
cell23    0.220  0.021   0.178  0.262  39        1000
cell01    0.235  0.031   0.175  0.295  44        1000
cell21    0.106  0.021   0.065  0.147  41        500
cell02    0.191  0.045   0.103  0.280  54        1000
cell05    0.300  0.036   0.229  0.370  40        2000
cell02    0.173  0.025   0.124  0.221  40        4000
cell06    0.208  0.036   0.138  0.278  48        500
```

While auditing the holding potential column for cell10, two cells fell out of the usable range (coefficient 0.161, stderr 0.015, n = 41). While comparing per-cell orderings for cell02, the CI narrowed by roughly a tenth (coefficient 0.199, stderr 0.043, n = 43). While bootstrapping the CI for cell03, nothing in the figure changed at print size (coefficient 0.153, stderr 0.038, n = 44). While segmenting epochs for cell12, two cells fell out of the usable range (coefficient 0.147, stderr 0.039, n = 43). While fitting the one-lag kernel for cell05, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.105, stderr 0.039, n = 38). While segmenting epochs for cell22, two cells fell out of the usable range (coefficient 0.309, stderr 0.038, n = 56). Flagging it so it does not get rediscovered next week.

While fitting the one-lag kernel for cell22, nothing in the figure changed at print size (coefficient 0.127, stderr 0.044, n = 46). While bootstrapping the CI for cell17, two cells fell out of the usable range (coefficient 0.116, stderr 0.024, n = 51). While auditing the holding potential column for cell24, the coefficient tracked epoch count more closely than duration (coefficient 0.230, stderr 0.023, n = 50). While bootstrapping the CI for cell16, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.235, stderr 0.011, n = 38). While segmenting epochs for cell13, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.184, stderr 0.026, n = 51). While re-exporting the raw traces for cell19, nothing in the figure changed at print size (coefficient 0.125, stderr 0.030, n = 51). Worth noting for the writeup, though not a result on its own.

While re-running with a tighter segmentation threshold for cell24, the CI narrowed by roughly a tenth (coefficient 0.147, stderr 0.037, n = 58). While checking residual autocorrelation for cell14, the coefficient tracked epoch count more closely than duration (coefficient 0.133, stderr 0.034, n = 45). While segmenting epochs for cell05, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.302, stderr 0.017, n = 56). While comparing per-cell orderings for cell22, the coefficient tracked epoch count more closely than duration (coefficient 0.226, stderr 0.020, n = 51). While checking residual autocorrelation for cell12, nothing in the figure changed at print size (coefficient 0.270, stderr 0.012, n = 54).

### Step 7: checking residual autocorrelation

While auditing the holding potential column for cell01, the ordering of cells was preserved (coefficient 0.263, stderr 0.046, n = 53). While segmenting epochs for cell11, the ordering of cells was preserved (coefficient 0.288, stderr 0.038, n = 46). While fitting the one-lag kernel for cell16, the coefficient tracked epoch count more closely than duration (coefficient 0.085, stderr 0.029, n = 39).

While auditing the holding potential column for cell09, the CI narrowed by roughly a tenth (coefficient 0.189, stderr 0.038, n = 39). While re-running with a tighter segmentation threshold for cell11, the coefficient tracked epoch count more closely than duration (coefficient 0.169, stderr 0.036, n = 48). While auditing the holding potential column for cell12, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.245, stderr 0.027, n = 48). While comparing per-cell orderings for cell16, the CI narrowed by roughly a tenth (coefficient 0.272, stderr 0.031, n = 52).

### Step 8: auditing the holding potential column

While comparing per-cell orderings for cell13, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.089, stderr 0.037, n = 45). While segmenting epochs for cell22, nothing in the figure changed at print size (coefficient 0.216, stderr 0.021, n = 52). While re-exporting the raw traces for cell10, two cells fell out of the usable range (coefficient 0.240, stderr 0.017, n = 42). While segmenting epochs for cell21, the ordering of cells was preserved (coefficient 0.203, stderr 0.049, n = 44). While segmenting epochs for cell04, the coefficient tracked epoch count more closely than duration (coefficient 0.263, stderr 0.037, n = 46). Parking this until the re-segmentation lands.

While auditing the holding potential column for cell06, the coefficient tracked epoch count more closely than duration (coefficient 0.090, stderr 0.012, n = 39). While comparing per-cell orderings for cell20, nothing in the figure changed at print size (coefficient 0.157, stderr 0.046, n = 46). While comparing per-cell orderings for cell09, nothing in the figure changed at print size (coefficient 0.163, stderr 0.031, n = 46). Flagging it so it does not get rediscovered next week.

### Step 9: bootstrapping the CI

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell22    0.125  0.012   0.102  0.149  55        500
cell21    0.179  0.032   0.117  0.242  55        500
cell06    0.111  0.015   0.083  0.140  52        4000
cell14    0.198  0.026   0.146  0.249  57        2000
cell13    0.171  0.040   0.092  0.249  38        2000
cell05    0.222  0.010   0.202  0.242  48        2000
cell03    0.132  0.043   0.048  0.215  46        2000
cell16    0.103  0.020   0.064  0.143  56        2000
```

While auditing the holding potential column for cell18, nothing in the figure changed at print size (coefficient 0.168, stderr 0.021, n = 46). While fitting the one-lag kernel for cell05, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.250, stderr 0.049, n = 58). While fitting the one-lag kernel for cell14, two cells fell out of the usable range (coefficient 0.209, stderr 0.035, n = 47). While segmenting epochs for cell10, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.237, stderr 0.031, n = 42). Worth noting for the writeup, though not a result on its own.

```python
coefs = fit_per_cell(rows, threshold=0.37)
lo, hi = ci(coefs, seed=75)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While re-exporting the raw traces for cell12, two cells fell out of the usable range (coefficient 0.221, stderr 0.016, n = 55). While comparing per-cell orderings for cell08, the coefficient tracked epoch count more closely than duration (coefficient 0.155, stderr 0.011, n = 56). While checking residual autocorrelation for cell12, the estimate moved less than one standard error (coefficient 0.250, stderr 0.046, n = 53). Noted and moved on; it does not change the decision.

### Step 10: segmenting epochs

While checking residual autocorrelation for cell15, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.249, stderr 0.043, n = 47). While re-running with a tighter segmentation threshold for cell21, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.257, stderr 0.027, n = 53). While bootstrapping the CI for cell22, two cells fell out of the usable range (coefficient 0.251, stderr 0.018, n = 40). While re-exporting the raw traces for cell13, two cells fell out of the usable range (coefficient 0.134, stderr 0.019, n = 44).

```python
coefs = fit_per_cell(rows, threshold=0.36)
lo, hi = ci(coefs, seed=38)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While checking residual autocorrelation for cell21, two cells fell out of the usable range (coefficient 0.192, stderr 0.047, n = 56). While bootstrapping the CI for cell04, two cells fell out of the usable range (coefficient 0.146, stderr 0.049, n = 45). While bootstrapping the CI for cell15, the coefficient tracked epoch count more closely than duration (coefficient 0.130, stderr 0.050, n = 42). While segmenting epochs for cell23, the coefficient tracked epoch count more closely than duration (coefficient 0.101, stderr 0.027, n = 54). While comparing per-cell orderings for cell04, the ordering of cells was preserved (coefficient 0.301, stderr 0.011, n = 58).

```python
coefs = fit_per_cell(rows, threshold=0.67)
lo, hi = ci(coefs, seed=19)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 11: checking residual autocorrelation

```python
coefs = fit_per_cell(rows, threshold=0.36)
lo, hi = ci(coefs, seed=65)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While auditing the holding potential column for cell11, the estimate moved less than one standard error (coefficient 0.201, stderr 0.028, n = 40). While checking residual autocorrelation for cell04, two cells fell out of the usable range (coefficient 0.125, stderr 0.010, n = 50). While bootstrapping the CI for cell20, the estimate moved less than one standard error (coefficient 0.157, stderr 0.012, n = 49). Flagging it so it does not get rediscovered next week.

### Step 12: re-exporting the raw traces

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell16    0.186  0.038   0.111  0.260  57        4000
cell14    0.199  0.047   0.107  0.291  43        500
cell16    0.232  0.023   0.186  0.277  52        4000
cell03    0.087  0.030   0.027  0.146  42        500
cell23    0.306  0.035   0.237  0.376  58        500
cell17    0.295  0.042   0.213  0.377  45        500
cell21    0.193  0.017   0.158  0.227  57        500
cell11    0.258  0.026   0.206  0.310  48        4000
```

While comparing per-cell orderings for cell10, the estimate moved less than one standard error (coefficient 0.167, stderr 0.018, n = 40). While fitting the one-lag kernel for cell16, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.302, stderr 0.042, n = 43). While checking residual autocorrelation for cell01, the CI narrowed by roughly a tenth (coefficient 0.218, stderr 0.041, n = 42).

### Step 13: auditing the holding potential column

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell21    0.116  0.018   0.080  0.152  50        2000
cell22    0.199  0.014   0.171  0.228  52        4000
cell22    0.222  0.032   0.160  0.284  46        1000
cell09    0.266  0.023   0.220  0.312  48        4000
cell10    0.149  0.045   0.061  0.237  57        500
cell17    0.108  0.013   0.084  0.133  54        1000
cell15    0.129  0.018   0.094  0.165  45        500
cell14    0.146  0.019   0.110  0.183  45        1000
cell06    0.087  0.023   0.041  0.133  47        1000
cell20    0.118  0.026   0.067  0.168  38        4000
```

While segmenting epochs for cell01, two cells fell out of the usable range (coefficient 0.133, stderr 0.041, n = 38). While comparing per-cell orderings for cell07, the coefficient tracked epoch count more closely than duration (coefficient 0.236, stderr 0.024, n = 56). While auditing the holding potential column for cell09, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.198, stderr 0.038, n = 53).

While segmenting epochs for cell14, the ordering of cells was preserved (coefficient 0.088, stderr 0.036, n = 53). While bootstrapping the CI for cell20, the ordering of cells was preserved (coefficient 0.202, stderr 0.018, n = 49). While fitting the one-lag kernel for cell10, the coefficient tracked epoch count more closely than duration (coefficient 0.187, stderr 0.018, n = 49). While segmenting epochs for cell01, the coefficient tracked epoch count more closely than duration (coefficient 0.164, stderr 0.040, n = 48). While re-exporting the raw traces for cell17, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.226, stderr 0.010, n = 48). While auditing the holding potential column for cell16, the estimate moved less than one standard error (coefficient 0.185, stderr 0.033, n = 43).

### Step 14: fitting the one-lag kernel

While bootstrapping the CI for cell05, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.225, stderr 0.016, n = 54). While re-running with a tighter segmentation threshold for cell17, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.167, stderr 0.038, n = 40). While auditing the holding potential column for cell08, the ordering of cells was preserved (coefficient 0.196, stderr 0.015, n = 43). Noted and moved on; it does not change the decision.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell20    0.179  0.034   0.112  0.247  54        4000
cell20    0.172  0.032   0.109  0.235  45        2000
cell11    0.250  0.018   0.214  0.285  56        4000
cell24    0.161  0.034   0.095  0.227  42        4000
cell07    0.273  0.020   0.233  0.313  44        4000
cell10    0.157  0.039   0.081  0.232  47        2000
cell21    0.158  0.037   0.084  0.231  47        2000
cell18    0.292  0.029   0.235  0.349  44        2000
cell08    0.301  0.025   0.251  0.350  43        2000
cell13    0.088  0.041   0.009  0.168  55        500
cell20    0.301  0.045   0.213  0.390  49        500
```

```python
coefs = fit_per_cell(rows, threshold=0.35)
lo, hi = ci(coefs, seed=54)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While auditing the holding potential column for cell21, two cells fell out of the usable range (coefficient 0.275, stderr 0.033, n = 50). While checking residual autocorrelation for cell07, the CI narrowed by roughly a tenth (coefficient 0.252, stderr 0.032, n = 41). While auditing the holding potential column for cell17, two cells fell out of the usable range (coefficient 0.250, stderr 0.035, n = 44). While comparing per-cell orderings for cell06, two cells fell out of the usable range (coefficient 0.190, stderr 0.040, n = 56). This is the part that will need a real statistical argument.

### Step 15: bootstrapping the CI

While bootstrapping the CI for cell11, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.107, stderr 0.037, n = 46). While segmenting epochs for cell13, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.098, stderr 0.024, n = 56). While checking residual autocorrelation for cell19, the coefficient tracked epoch count more closely than duration (coefficient 0.222, stderr 0.043, n = 43).

While auditing the holding potential column for cell14, two cells fell out of the usable range (coefficient 0.193, stderr 0.022, n = 43). While comparing per-cell orderings for cell19, nothing in the figure changed at print size (coefficient 0.254, stderr 0.020, n = 39). While segmenting epochs for cell11, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.261, stderr 0.049, n = 50). While re-exporting the raw traces for cell07, two cells fell out of the usable range (coefficient 0.145, stderr 0.025, n = 50). While fitting the one-lag kernel for cell06, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.248, stderr 0.020, n = 43). While auditing the holding potential column for cell22, the coefficient tracked epoch count more closely than duration (coefficient 0.261, stderr 0.043, n = 39).

### Step 16: checking residual autocorrelation

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell04    0.228  0.045   0.140  0.315  47        1000
cell08    0.093  0.043   0.009  0.176  48        4000
cell21    0.239  0.046   0.148  0.330  51        500
cell13    0.164  0.031   0.104  0.225  56        2000
cell21    0.202  0.032   0.140  0.263  43        500
cell20    0.265  0.017   0.231  0.299  52        4000
cell05    0.146  0.015   0.117  0.174  56        2000
cell16    0.199  0.038   0.124  0.273  46        500
cell21    0.092  0.028   0.038  0.147  55        500
cell23    0.118  0.046   0.027  0.208  46        4000
cell09    0.160  0.029   0.103  0.217  53        2000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell22    0.223  0.050   0.125  0.321  43        2000
cell20    0.155  0.033   0.091  0.219  45        2000
cell13    0.185  0.010   0.165  0.205  42        1000
cell13    0.225  0.022   0.182  0.269  56        4000
cell15    0.102  0.014   0.075  0.129  58        500
cell11    0.243  0.030   0.183  0.302  40        1000
cell03    0.188  0.029   0.132  0.244  57        500
cell22    0.202  0.038   0.127  0.276  46        4000
cell06    0.213  0.010   0.193  0.234  48        1000
cell17    0.300  0.015   0.271  0.329  55        500
cell11    0.129  0.023   0.084  0.174  48        2000
cell03    0.164  0.046   0.073  0.254  51        500
cell15    0.208  0.050   0.110  0.305  49        1000
```

While checking residual autocorrelation for cell16, the coefficient tracked epoch count more closely than duration (coefficient 0.270, stderr 0.023, n = 38). While re-running with a tighter segmentation threshold for cell15, the coefficient tracked epoch count more closely than duration (coefficient 0.135, stderr 0.043, n = 57). While checking residual autocorrelation for cell13, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.195, stderr 0.036, n = 49). This is the part that will need a real statistical argument.

While segmenting epochs for cell01, the CI narrowed by roughly a tenth (coefficient 0.160, stderr 0.039, n = 44). While bootstrapping the CI for cell02, nothing in the figure changed at print size (coefficient 0.225, stderr 0.018, n = 46). While auditing the holding potential column for cell02, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.106, stderr 0.023, n = 43). While comparing per-cell orderings for cell10, two cells fell out of the usable range (coefficient 0.295, stderr 0.038, n = 55). While bootstrapping the CI for cell11, the CI narrowed by roughly a tenth (coefficient 0.307, stderr 0.017, n = 45). While auditing the holding potential column for cell19, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.262, stderr 0.017, n = 55).

### Step 17: checking residual autocorrelation

While bootstrapping the CI for cell08, two cells fell out of the usable range (coefficient 0.124, stderr 0.049, n = 40). While checking residual autocorrelation for cell17, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.162, stderr 0.013, n = 42). While checking residual autocorrelation for cell20, nothing in the figure changed at print size (coefficient 0.090, stderr 0.028, n = 55). While re-exporting the raw traces for cell09, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.293, stderr 0.012, n = 44). While checking residual autocorrelation for cell02, the ordering of cells was preserved (coefficient 0.305, stderr 0.011, n = 38). Parking this until the re-segmentation lands.

While auditing the holding potential column for cell04, the ordering of cells was preserved (coefficient 0.161, stderr 0.018, n = 53). While re-exporting the raw traces for cell15, nothing in the figure changed at print size (coefficient 0.137, stderr 0.039, n = 45). While re-running with a tighter segmentation threshold for cell11, nothing in the figure changed at print size (coefficient 0.232, stderr 0.017, n = 51).

While segmenting epochs for cell10, the ordering of cells was preserved (coefficient 0.273, stderr 0.032, n = 57). While re-exporting the raw traces for cell20, the estimate moved less than one standard error (coefficient 0.256, stderr 0.029, n = 48). While re-exporting the raw traces for cell15, the CI narrowed by roughly a tenth (coefficient 0.213, stderr 0.035, n = 56). While bootstrapping the CI for cell12, the CI narrowed by roughly a tenth (coefficient 0.271, stderr 0.015, n = 42). While segmenting epochs for cell03, the CI narrowed by roughly a tenth (coefficient 0.308, stderr 0.044, n = 54).

### Step 18: re-running with a tighter segmentation threshold

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell05    0.142  0.040   0.063  0.220  43        1000
cell23    0.267  0.024   0.220  0.314  41        2000
cell20    0.176  0.037   0.104  0.248  45        2000
cell11    0.210  0.030   0.151  0.270  58        4000
cell04    0.231  0.035   0.162  0.300  52        2000
cell05    0.201  0.050   0.103  0.299  44        1000
cell20    0.102  0.015   0.072  0.131  49        500
cell05    0.220  0.049   0.125  0.315  39        2000
cell22    0.241  0.016   0.210  0.272  38        2000
cell10    0.301  0.018   0.267  0.335  57        500
cell21    0.168  0.021   0.127  0.210  49        1000
cell01    0.227  0.050   0.129  0.324  53        2000
cell20    0.269  0.038   0.194  0.344  49        500
cell22    0.163  0.037   0.090  0.235  49        2000
```

While bootstrapping the CI for cell07, the ordering of cells was preserved (coefficient 0.259, stderr 0.025, n = 55). While segmenting epochs for cell15, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.184, stderr 0.025, n = 48). While comparing per-cell orderings for cell13, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.305, stderr 0.044, n = 40). Noted and moved on; it does not change the decision.

### Step 19: fitting the one-lag kernel

While re-running with a tighter segmentation threshold for cell03, the estimate moved less than one standard error (coefficient 0.145, stderr 0.045, n = 38). While checking residual autocorrelation for cell20, the estimate moved less than one standard error (coefficient 0.128, stderr 0.045, n = 53). While checking residual autocorrelation for cell23, the coefficient tracked epoch count more closely than duration (coefficient 0.102, stderr 0.019, n = 43). While auditing the holding potential column for cell18, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.092, stderr 0.043, n = 54). While comparing per-cell orderings for cell18, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.241, stderr 0.039, n = 52).

While comparing per-cell orderings for cell18, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.183, stderr 0.032, n = 55). While bootstrapping the CI for cell17, the ordering of cells was preserved (coefficient 0.171, stderr 0.019, n = 53). While re-exporting the raw traces for cell04, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.225, stderr 0.047, n = 56). While segmenting epochs for cell07, the CI narrowed by roughly a tenth (coefficient 0.164, stderr 0.024, n = 49). Flagging it so it does not get rediscovered next week.

### Step 20: comparing per-cell orderings

While fitting the one-lag kernel for cell13, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.290, stderr 0.033, n = 48). While bootstrapping the CI for cell14, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.189, stderr 0.036, n = 46). While auditing the holding potential column for cell07, the ordering of cells was preserved (coefficient 0.117, stderr 0.027, n = 56). While auditing the holding potential column for cell22, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.140, stderr 0.011, n = 39). While bootstrapping the CI for cell17, nothing in the figure changed at print size (coefficient 0.244, stderr 0.014, n = 43).

While re-running with a tighter segmentation threshold for cell09, the estimate moved less than one standard error (coefficient 0.143, stderr 0.026, n = 40). While fitting the one-lag kernel for cell08, the ordering of cells was preserved (coefficient 0.253, stderr 0.027, n = 49). While comparing per-cell orderings for cell20, the estimate moved less than one standard error (coefficient 0.254, stderr 0.026, n = 45). While segmenting epochs for cell09, the coefficient tracked epoch count more closely than duration (coefficient 0.270, stderr 0.022, n = 46). Noted and moved on; it does not change the decision.

While comparing per-cell orderings for cell11, two cells fell out of the usable range (coefficient 0.281, stderr 0.022, n = 38). While checking residual autocorrelation for cell13, the ordering of cells was preserved (coefficient 0.173, stderr 0.028, n = 54). While re-exporting the raw traces for cell16, the ordering of cells was preserved (coefficient 0.184, stderr 0.030, n = 56). This is the part that will need a real statistical argument.

### Step 21: bootstrapping the CI

```python
coefs = fit_per_cell(rows, threshold=0.50)
lo, hi = ci(coefs, seed=66)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While fitting the one-lag kernel for cell16, the CI narrowed by roughly a tenth (coefficient 0.283, stderr 0.022, n = 50). While comparing per-cell orderings for cell10, nothing in the figure changed at print size (coefficient 0.303, stderr 0.016, n = 38). While segmenting epochs for cell04, two cells fell out of the usable range (coefficient 0.143, stderr 0.038, n = 40). While re-exporting the raw traces for cell12, nothing in the figure changed at print size (coefficient 0.136, stderr 0.021, n = 44). While segmenting epochs for cell08, the coefficient tracked epoch count more closely than duration (coefficient 0.290, stderr 0.016, n = 55). This is the part that will need a real statistical argument.

### Step 22: checking residual autocorrelation

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell07    0.284  0.012   0.261  0.308  42        1000
cell23    0.307  0.032   0.244  0.369  49        500
cell14    0.285  0.039   0.209  0.362  41        500
cell12    0.111  0.034   0.044  0.178  54        2000
cell14    0.134  0.028   0.080  0.188  50        1000
cell14    0.179  0.037   0.106  0.252  38        1000
cell01    0.301  0.030   0.242  0.360  55        1000
cell07    0.165  0.024   0.118  0.212  43        1000
cell10    0.263  0.033   0.198  0.328  39        500
```

```python
coefs = fit_per_cell(rows, threshold=0.80)
lo, hi = ci(coefs, seed=87)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While bootstrapping the CI for cell10, the estimate moved less than one standard error (coefficient 0.237, stderr 0.045, n = 41). While re-exporting the raw traces for cell18, two cells fell out of the usable range (coefficient 0.202, stderr 0.019, n = 49). While auditing the holding potential column for cell13, two cells fell out of the usable range (coefficient 0.267, stderr 0.012, n = 38). While re-exporting the raw traces for cell11, the estimate moved less than one standard error (coefficient 0.216, stderr 0.035, n = 53). While comparing per-cell orderings for cell24, the coefficient tracked epoch count more closely than duration (coefficient 0.193, stderr 0.048, n = 43). While bootstrapping the CI for cell23, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.158, stderr 0.032, n = 43). Noted and moved on; it does not change the decision.

While bootstrapping the CI for cell05, the coefficient tracked epoch count more closely than duration (coefficient 0.149, stderr 0.024, n = 42). While comparing per-cell orderings for cell22, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.290, stderr 0.046, n = 54). While auditing the holding potential column for cell20, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.111, stderr 0.018, n = 39).

### Step 23: checking residual autocorrelation

```python
coefs = fit_per_cell(rows, threshold=0.56)
lo, hi = ci(coefs, seed=78)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While re-exporting the raw traces for cell03, nothing in the figure changed at print size (coefficient 0.268, stderr 0.011, n = 55). While segmenting epochs for cell09, the CI narrowed by roughly a tenth (coefficient 0.243, stderr 0.022, n = 56). While comparing per-cell orderings for cell15, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.097, stderr 0.019, n = 41). While re-exporting the raw traces for cell13, nothing in the figure changed at print size (coefficient 0.177, stderr 0.013, n = 48).

### Step 24: bootstrapping the CI

```python
coefs = fit_per_cell(rows, threshold=0.48)
lo, hi = ci(coefs, seed=36)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While segmenting epochs for cell07, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.103, stderr 0.031, n = 55). While auditing the holding potential column for cell09, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.307, stderr 0.022, n = 38). While fitting the one-lag kernel for cell08, nothing in the figure changed at print size (coefficient 0.184, stderr 0.039, n = 38). While comparing per-cell orderings for cell08, the estimate moved less than one standard error (coefficient 0.305, stderr 0.034, n = 43).

While re-running with a tighter segmentation threshold for cell04, the CI narrowed by roughly a tenth (coefficient 0.194, stderr 0.020, n = 47). While re-running with a tighter segmentation threshold for cell14, the ordering of cells was preserved (coefficient 0.235, stderr 0.043, n = 40). While comparing per-cell orderings for cell12, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.121, stderr 0.029, n = 38). While comparing per-cell orderings for cell01, the coefficient tracked epoch count more closely than duration (coefficient 0.234, stderr 0.043, n = 45).

```python
coefs = fit_per_cell(rows, threshold=0.38)
lo, hi = ci(coefs, seed=70)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 25: re-exporting the raw traces

While bootstrapping the CI for cell23, two cells fell out of the usable range (coefficient 0.267, stderr 0.016, n = 39). While fitting the one-lag kernel for cell21, the estimate moved less than one standard error (coefficient 0.176, stderr 0.029, n = 51). While checking residual autocorrelation for cell06, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.289, stderr 0.019, n = 48). While bootstrapping the CI for cell24, the estimate moved less than one standard error (coefficient 0.110, stderr 0.012, n = 47). Parking this until the re-segmentation lands.

```python
coefs = fit_per_cell(rows, threshold=0.67)
lo, hi = ci(coefs, seed=45)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell19    0.189  0.045   0.100  0.278  43        4000
cell18    0.135  0.036   0.064  0.205  45        1000
cell10    0.195  0.031   0.133  0.256  40        2000
cell24    0.151  0.013   0.125  0.177  58        1000
cell08    0.299  0.011   0.278  0.321  56        1000
cell08    0.164  0.046   0.073  0.254  47        1000
cell11    0.092  0.044   0.007  0.178  45        1000
cell21    0.186  0.033   0.122  0.250  55        2000
cell07    0.260  0.025   0.210  0.310  56        2000
cell06    0.293  0.046   0.203  0.382  43        1000
cell07    0.256  0.043   0.171  0.341  43        2000
```

### Step 26: bootstrapping the CI

```python
coefs = fit_per_cell(rows, threshold=0.37)
lo, hi = ci(coefs, seed=0)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While fitting the one-lag kernel for cell18, the CI narrowed by roughly a tenth (coefficient 0.192, stderr 0.028, n = 44). While auditing the holding potential column for cell03, the estimate moved less than one standard error (coefficient 0.176, stderr 0.023, n = 50). While comparing per-cell orderings for cell23, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.206, stderr 0.012, n = 40). While re-running with a tighter segmentation threshold for cell13, the ordering of cells was preserved (coefficient 0.182, stderr 0.016, n = 45). While auditing the holding potential column for cell22, the ordering of cells was preserved (coefficient 0.123, stderr 0.036, n = 39).

### Step 27: segmenting epochs

While checking residual autocorrelation for cell07, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.293, stderr 0.031, n = 44). While checking residual autocorrelation for cell09, the CI narrowed by roughly a tenth (coefficient 0.198, stderr 0.026, n = 45). While comparing per-cell orderings for cell04, the estimate moved less than one standard error (coefficient 0.177, stderr 0.016, n = 39). While comparing per-cell orderings for cell10, the CI narrowed by roughly a tenth (coefficient 0.133, stderr 0.019, n = 48). While re-running with a tighter segmentation threshold for cell24, the estimate moved less than one standard error (coefficient 0.100, stderr 0.032, n = 43).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell07    0.144  0.048   0.050  0.238  58        2000
cell17    0.250  0.011   0.229  0.271  44        4000
cell14    0.097  0.023   0.052  0.142  58        2000
cell09    0.209  0.018   0.174  0.244  48        2000
cell05    0.132  0.025   0.084  0.180  53        2000
cell07    0.225  0.045   0.137  0.312  39        4000
cell01    0.247  0.043   0.163  0.332  43        4000
cell03    0.125  0.027   0.072  0.179  57        2000
```

While auditing the holding potential column for cell14, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.114, stderr 0.039, n = 47). While bootstrapping the CI for cell02, the estimate moved less than one standard error (coefficient 0.103, stderr 0.010, n = 39). While fitting the one-lag kernel for cell22, the coefficient tracked epoch count more closely than duration (coefficient 0.216, stderr 0.038, n = 46). While bootstrapping the CI for cell12, the coefficient tracked epoch count more closely than duration (coefficient 0.220, stderr 0.028, n = 54). While segmenting epochs for cell05, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.238, stderr 0.019, n = 43).

### Step 28: fitting the one-lag kernel

While re-exporting the raw traces for cell21, the estimate moved less than one standard error (coefficient 0.300, stderr 0.049, n = 47). While checking residual autocorrelation for cell23, the ordering of cells was preserved (coefficient 0.256, stderr 0.038, n = 50). While re-running with a tighter segmentation threshold for cell16, the CI narrowed by roughly a tenth (coefficient 0.229, stderr 0.021, n = 55). While bootstrapping the CI for cell20, the estimate moved less than one standard error (coefficient 0.119, stderr 0.011, n = 50).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell07    0.155  0.044   0.069  0.241  41        2000
cell12    0.241  0.027   0.188  0.295  57        2000
cell10    0.117  0.030   0.058  0.176  51        4000
cell11    0.214  0.011   0.193  0.235  38        500
cell03    0.189  0.016   0.158  0.220  55        500
cell08    0.304  0.011   0.283  0.325  44        4000
cell07    0.279  0.029   0.222  0.337  51        2000
cell20    0.244  0.037   0.171  0.318  38        2000
```

```python
coefs = fit_per_cell(rows, threshold=0.73)
lo, hi = ci(coefs, seed=97)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While auditing the holding potential column for cell23, two cells fell out of the usable range (coefficient 0.130, stderr 0.042, n = 51). While re-running with a tighter segmentation threshold for cell17, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.293, stderr 0.049, n = 52). While segmenting epochs for cell11, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.215, stderr 0.030, n = 58). While checking residual autocorrelation for cell03, the ordering of cells was preserved (coefficient 0.088, stderr 0.011, n = 38). While auditing the holding potential column for cell19, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.114, stderr 0.040, n = 41). Flagging it so it does not get rediscovered next week.

### Step 29: checking residual autocorrelation

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell24    0.134  0.037   0.061  0.206  39        500
cell02    0.262  0.012   0.239  0.284  50        500
cell16    0.272  0.029   0.215  0.329  54        1000
cell06    0.268  0.025   0.220  0.317  50        4000
cell05    0.117  0.028   0.062  0.173  46        4000
cell01    0.180  0.029   0.124  0.235  53        2000
cell03    0.098  0.038   0.023  0.173  43        2000
cell23    0.254  0.021   0.212  0.295  57        500
cell13    0.149  0.021   0.108  0.191  45        4000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell13    0.199  0.018   0.163  0.235  47        2000
cell06    0.255  0.040   0.177  0.334  51        2000
cell10    0.289  0.024   0.243  0.335  58        1000
cell20    0.257  0.027   0.204  0.311  53        1000
cell17    0.130  0.010   0.111  0.150  39        1000
cell12    0.278  0.022   0.234  0.322  44        500
cell01    0.114  0.029   0.057  0.171  39        500
cell19    0.165  0.030   0.106  0.225  52        1000
cell04    0.147  0.031   0.085  0.208  54        4000
cell06    0.171  0.027   0.119  0.224  44        2000
cell01    0.274  0.040   0.195  0.352  48        4000
cell05    0.272  0.016   0.242  0.303  45        1000
cell17    0.298  0.021   0.257  0.339  38        1000
```

While checking residual autocorrelation for cell20, the estimate moved less than one standard error (coefficient 0.129, stderr 0.012, n = 51). While re-running with a tighter segmentation threshold for cell24, the CI narrowed by roughly a tenth (coefficient 0.164, stderr 0.032, n = 40). While checking residual autocorrelation for cell05, two cells fell out of the usable range (coefficient 0.091, stderr 0.040, n = 46). While comparing per-cell orderings for cell08, the coefficient tracked epoch count more closely than duration (coefficient 0.302, stderr 0.024, n = 55). While auditing the holding potential column for cell12, the ordering of cells was preserved (coefficient 0.116, stderr 0.044, n = 39).

### Step 30: re-exporting the raw traces

```python
coefs = fit_per_cell(rows, threshold=0.78)
lo, hi = ci(coefs, seed=27)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell10    0.260  0.021   0.219  0.300  55        2000
cell22    0.107  0.048   0.013  0.200  50        2000
cell11    0.260  0.045   0.172  0.347  56        500
cell20    0.141  0.025   0.092  0.190  48        4000
cell18    0.203  0.041   0.122  0.284  55        500
cell16    0.198  0.034   0.131  0.265  46        1000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell20    0.254  0.012   0.231  0.277  46        1000
cell07    0.174  0.044   0.088  0.259  58        4000
cell03    0.270  0.017   0.237  0.303  46        1000
cell22    0.109  0.029   0.052  0.166  46        4000
cell11    0.277  0.040   0.199  0.355  53        4000
cell04    0.127  0.045   0.039  0.216  52        4000
cell16    0.098  0.043   0.014  0.182  56        1000
cell12    0.106  0.027   0.053  0.159  41        500
cell06    0.238  0.038   0.163  0.312  57        500
cell22    0.152  0.039   0.075  0.229  41        2000
cell21    0.221  0.032   0.158  0.284  38        4000
```

### Step 31: auditing the holding potential column

While re-exporting the raw traces for cell10, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.220, stderr 0.050, n = 42). While fitting the one-lag kernel for cell08, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.082, stderr 0.046, n = 45). While auditing the holding potential column for cell11, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.109, stderr 0.020, n = 47). While segmenting epochs for cell21, nothing in the figure changed at print size (coefficient 0.281, stderr 0.043, n = 42). Noted and moved on; it does not change the decision.

While checking residual autocorrelation for cell19, two cells fell out of the usable range (coefficient 0.310, stderr 0.038, n = 50). While re-exporting the raw traces for cell21, the coefficient tracked epoch count more closely than duration (coefficient 0.234, stderr 0.046, n = 57). While segmenting epochs for cell14, nothing in the figure changed at print size (coefficient 0.185, stderr 0.036, n = 43). While segmenting epochs for cell22, the estimate moved less than one standard error (coefficient 0.207, stderr 0.017, n = 40). While segmenting epochs for cell01, two cells fell out of the usable range (coefficient 0.082, stderr 0.016, n = 46). While re-running with a tighter segmentation threshold for cell20, the ordering of cells was preserved (coefficient 0.090, stderr 0.021, n = 47). Parking this until the re-segmentation lands.

While bootstrapping the CI for cell20, two cells fell out of the usable range (coefficient 0.117, stderr 0.038, n = 42). While bootstrapping the CI for cell13, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.233, stderr 0.034, n = 57). While re-exporting the raw traces for cell20, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.095, stderr 0.040, n = 47). While comparing per-cell orderings for cell01, nothing in the figure changed at print size (coefficient 0.263, stderr 0.023, n = 50). While segmenting epochs for cell09, the CI narrowed by roughly a tenth (coefficient 0.148, stderr 0.016, n = 38). While re-running with a tighter segmentation threshold for cell18, the coefficient tracked epoch count more closely than duration (coefficient 0.182, stderr 0.048, n = 51).

### Step 32: auditing the holding potential column

While comparing per-cell orderings for cell12, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.171, stderr 0.047, n = 40). While auditing the holding potential column for cell12, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.203, stderr 0.013, n = 45). While segmenting epochs for cell13, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.229, stderr 0.013, n = 48). While re-exporting the raw traces for cell04, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.256, stderr 0.011, n = 49). While re-exporting the raw traces for cell03, the coefficient tracked epoch count more closely than duration (coefficient 0.090, stderr 0.040, n = 56). This is the part that will need a real statistical argument.

While segmenting epochs for cell17, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.100, stderr 0.043, n = 47). While bootstrapping the CI for cell17, the CI narrowed by roughly a tenth (coefficient 0.259, stderr 0.016, n = 46). While fitting the one-lag kernel for cell05, nothing in the figure changed at print size (coefficient 0.238, stderr 0.031, n = 45).

While bootstrapping the CI for cell12, nothing in the figure changed at print size (coefficient 0.276, stderr 0.045, n = 54). While checking residual autocorrelation for cell07, two cells fell out of the usable range (coefficient 0.281, stderr 0.023, n = 56). While re-exporting the raw traces for cell09, the CI narrowed by roughly a tenth (coefficient 0.091, stderr 0.020, n = 44). While checking residual autocorrelation for cell13, nothing in the figure changed at print size (coefficient 0.233, stderr 0.024, n = 40). While bootstrapping the CI for cell14, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.184, stderr 0.022, n = 50). Noted and moved on; it does not change the decision.

While auditing the holding potential column for cell22, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.138, stderr 0.018, n = 48). While checking residual autocorrelation for cell05, the coefficient tracked epoch count more closely than duration (coefficient 0.270, stderr 0.013, n = 52). While checking residual autocorrelation for cell08, the CI narrowed by roughly a tenth (coefficient 0.151, stderr 0.043, n = 54). While re-exporting the raw traces for cell23, nothing in the figure changed at print size (coefficient 0.154, stderr 0.012, n = 41). While auditing the holding potential column for cell22, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.089, stderr 0.033, n = 48). While auditing the holding potential column for cell17, the coefficient tracked epoch count more closely than duration (coefficient 0.237, stderr 0.021, n = 44).

### Step 33: comparing per-cell orderings

While re-running with a tighter segmentation threshold for cell22, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.099, stderr 0.023, n = 51). While fitting the one-lag kernel for cell15, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.259, stderr 0.025, n = 40). While bootstrapping the CI for cell18, two cells fell out of the usable range (coefficient 0.266, stderr 0.031, n = 47). While segmenting epochs for cell04, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.265, stderr 0.041, n = 53).

While checking residual autocorrelation for cell05, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.173, stderr 0.022, n = 47). While auditing the holding potential column for cell17, the ordering of cells was preserved (coefficient 0.159, stderr 0.043, n = 38). While re-running with a tighter segmentation threshold for cell17, the CI narrowed by roughly a tenth (coefficient 0.115, stderr 0.041, n = 43). While comparing per-cell orderings for cell12, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.103, stderr 0.043, n = 45). Worth noting for the writeup, though not a result on its own.

### Step 34: re-running with a tighter segmentation threshold

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell23    0.257  0.034   0.191  0.323  44        4000
cell15    0.218  0.025   0.168  0.268  45        1000
cell02    0.260  0.019   0.222  0.297  46        4000
cell20    0.093  0.014   0.066  0.120  50        1000
cell14    0.108  0.049   0.012  0.204  57        1000
cell24    0.124  0.047   0.031  0.216  53        2000
cell22    0.310  0.036   0.240  0.379  53        2000
cell07    0.133  0.031   0.072  0.195  40        4000
cell22    0.094  0.015   0.064  0.123  41        2000
cell12    0.284  0.034   0.218  0.350  46        2000
cell14    0.134  0.044   0.047  0.221  38        4000
cell01    0.180  0.030   0.122  0.238  48        2000
cell15    0.111  0.040   0.033  0.190  58        1000
```

```python
coefs = fit_per_cell(rows, threshold=0.38)
lo, hi = ci(coefs, seed=84)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While checking residual autocorrelation for cell12, the ordering of cells was preserved (coefficient 0.286, stderr 0.047, n = 56). While bootstrapping the CI for cell18, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.133, stderr 0.021, n = 44). While comparing per-cell orderings for cell09, nothing in the figure changed at print size (coefficient 0.257, stderr 0.050, n = 39).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell05    0.178  0.019   0.142  0.215  47        2000
cell02    0.093  0.044   0.007  0.179  48        1000
cell11    0.194  0.041   0.113  0.275  39        500
cell01    0.303  0.046   0.212  0.394  43        4000
cell03    0.270  0.032   0.207  0.332  56        4000
cell16    0.202  0.027   0.149  0.255  54        500
cell04    0.118  0.028   0.063  0.173  52        2000
cell09    0.249  0.018   0.214  0.283  46        500
cell02    0.213  0.025   0.165  0.262  53        1000
cell06    0.092  0.035   0.023  0.161  46        1000
cell23    0.165  0.044   0.078  0.252  49        4000
cell06    0.225  0.043   0.140  0.310  52        4000
```

### Step 35: re-running with a tighter segmentation threshold

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell18    0.283  0.029   0.226  0.339  44        500
cell11    0.309  0.041   0.228  0.390  50        2000
cell06    0.196  0.024   0.150  0.243  39        1000
cell20    0.129  0.027   0.076  0.183  45        1000
cell22    0.116  0.032   0.052  0.180  43        1000
cell22    0.169  0.032   0.107  0.232  50        1000
cell08    0.290  0.038   0.215  0.366  43        4000
cell12    0.193  0.031   0.133  0.253  48        2000
```

While fitting the one-lag kernel for cell18, the CI narrowed by roughly a tenth (coefficient 0.094, stderr 0.020, n = 54). While checking residual autocorrelation for cell02, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.249, stderr 0.011, n = 48). While re-running with a tighter segmentation threshold for cell13, the coefficient tracked epoch count more closely than duration (coefficient 0.175, stderr 0.049, n = 57). While auditing the holding potential column for cell15, nothing in the figure changed at print size (coefficient 0.215, stderr 0.046, n = 45). While fitting the one-lag kernel for cell10, two cells fell out of the usable range (coefficient 0.225, stderr 0.045, n = 53). While checking residual autocorrelation for cell04, nothing in the figure changed at print size (coefficient 0.276, stderr 0.030, n = 39).

### Step 36: re-running with a tighter segmentation threshold

While segmenting epochs for cell20, two cells fell out of the usable range (coefficient 0.171, stderr 0.021, n = 54). While comparing per-cell orderings for cell23, the coefficient tracked epoch count more closely than duration (coefficient 0.298, stderr 0.047, n = 58). While re-exporting the raw traces for cell11, the CI narrowed by roughly a tenth (coefficient 0.176, stderr 0.024, n = 47).

While bootstrapping the CI for cell07, the CI narrowed by roughly a tenth (coefficient 0.102, stderr 0.011, n = 56). While bootstrapping the CI for cell17, nothing in the figure changed at print size (coefficient 0.151, stderr 0.046, n = 57). While auditing the holding potential column for cell20, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.177, stderr 0.035, n = 39). Worth noting for the writeup, though not a result on its own.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell05    0.137  0.029   0.081  0.194  49        2000
cell12    0.125  0.033   0.060  0.189  55        2000
cell23    0.300  0.040   0.222  0.378  53        2000
cell24    0.126  0.021   0.085  0.167  53        4000
cell16    0.285  0.045   0.197  0.373  43        4000
cell09    0.224  0.027   0.172  0.276  38        1000
cell19    0.175  0.018   0.140  0.209  46        4000
```

### Step 37: comparing per-cell orderings

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell11    0.131  0.028   0.076  0.186  47        2000
cell17    0.113  0.050   0.015  0.211  42        1000
cell14    0.241  0.048   0.146  0.335  53        1000
cell10    0.310  0.014   0.281  0.338  52        4000
cell19    0.105  0.040   0.026  0.184  39        2000
cell20    0.214  0.041   0.133  0.295  56        1000
cell22    0.184  0.018   0.149  0.219  40        4000
cell03    0.251  0.011   0.229  0.273  40        500
cell22    0.089  0.021   0.048  0.129  40        4000
```

```python
coefs = fit_per_cell(rows, threshold=0.40)
lo, hi = ci(coefs, seed=44)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While segmenting epochs for cell14, the coefficient tracked epoch count more closely than duration (coefficient 0.116, stderr 0.050, n = 56). While auditing the holding potential column for cell22, nothing in the figure changed at print size (coefficient 0.226, stderr 0.025, n = 48). While re-running with a tighter segmentation threshold for cell02, the coefficient tracked epoch count more closely than duration (coefficient 0.133, stderr 0.043, n = 41). Noted and moved on; it does not change the decision.

### Step 38: checking residual autocorrelation

While re-running with a tighter segmentation threshold for cell20, the ordering of cells was preserved (coefficient 0.220, stderr 0.034, n = 53). While auditing the holding potential column for cell07, nothing in the figure changed at print size (coefficient 0.301, stderr 0.040, n = 44). While re-exporting the raw traces for cell09, the estimate moved less than one standard error (coefficient 0.244, stderr 0.033, n = 54). While auditing the holding potential column for cell22, nothing in the figure changed at print size (coefficient 0.266, stderr 0.019, n = 45).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell15    0.207  0.031   0.145  0.268  46        4000
cell14    0.211  0.031   0.150  0.273  50        2000
cell15    0.239  0.044   0.154  0.325  46        2000
cell04    0.137  0.018   0.102  0.172  51        500
cell07    0.143  0.044   0.056  0.229  44        500
cell04    0.189  0.018   0.154  0.225  44        2000
cell22    0.270  0.020   0.230  0.310  40        2000
cell04    0.084  0.030   0.026  0.142  53        2000
cell05    0.232  0.031   0.172  0.292  42        4000
cell09    0.097  0.024   0.051  0.144  41        1000
cell16    0.202  0.034   0.135  0.269  51        2000
cell06    0.297  0.024   0.250  0.344  43        4000
cell06    0.215  0.013   0.188  0.241  56        1000
```

While auditing the holding potential column for cell13, the coefficient tracked epoch count more closely than duration (coefficient 0.242, stderr 0.021, n = 46). While bootstrapping the CI for cell11, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.170, stderr 0.045, n = 44). While fitting the one-lag kernel for cell04, the coefficient tracked epoch count more closely than duration (coefficient 0.275, stderr 0.036, n = 54). While bootstrapping the CI for cell01, nothing in the figure changed at print size (coefficient 0.119, stderr 0.048, n = 40).

### Step 39: re-running with a tighter segmentation threshold

While bootstrapping the CI for cell20, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.088, stderr 0.024, n = 57). While fitting the one-lag kernel for cell20, the ordering of cells was preserved (coefficient 0.123, stderr 0.034, n = 44). While re-running with a tighter segmentation threshold for cell09, the estimate moved less than one standard error (coefficient 0.137, stderr 0.032, n = 40). While comparing per-cell orderings for cell10, nothing in the figure changed at print size (coefficient 0.192, stderr 0.038, n = 57). Flagging it so it does not get rediscovered next week.

While comparing per-cell orderings for cell13, the ordering of cells was preserved (coefficient 0.267, stderr 0.039, n = 42). While checking residual autocorrelation for cell06, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.183, stderr 0.015, n = 54). While auditing the holding potential column for cell20, two cells fell out of the usable range (coefficient 0.109, stderr 0.033, n = 48).

While comparing per-cell orderings for cell14, two cells fell out of the usable range (coefficient 0.193, stderr 0.029, n = 50). While fitting the one-lag kernel for cell21, the ordering of cells was preserved (coefficient 0.093, stderr 0.034, n = 48). While re-exporting the raw traces for cell24, two cells fell out of the usable range (coefficient 0.257, stderr 0.042, n = 42). While bootstrapping the CI for cell13, nothing in the figure changed at print size (coefficient 0.280, stderr 0.032, n = 43).

### Step 40: checking residual autocorrelation

While fitting the one-lag kernel for cell08, the coefficient tracked epoch count more closely than duration (coefficient 0.203, stderr 0.016, n = 43). While re-running with a tighter segmentation threshold for cell18, the ordering of cells was preserved (coefficient 0.093, stderr 0.034, n = 50). While segmenting epochs for cell16, the estimate moved less than one standard error (coefficient 0.283, stderr 0.038, n = 49). While checking residual autocorrelation for cell21, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.248, stderr 0.031, n = 58).

While segmenting epochs for cell17, nothing in the figure changed at print size (coefficient 0.242, stderr 0.031, n = 50). While comparing per-cell orderings for cell07, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.084, stderr 0.039, n = 57). While checking residual autocorrelation for cell19, nothing in the figure changed at print size (coefficient 0.205, stderr 0.021, n = 53). Parking this until the re-segmentation lands.

### Step 41: segmenting epochs

While re-exporting the raw traces for cell21, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.084, stderr 0.012, n = 57). While comparing per-cell orderings for cell10, the estimate moved less than one standard error (coefficient 0.150, stderr 0.041, n = 39). While auditing the holding potential column for cell04, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.258, stderr 0.019, n = 51). Worth noting for the writeup, though not a result on its own.

While comparing per-cell orderings for cell21, the ordering of cells was preserved (coefficient 0.213, stderr 0.010, n = 48). While auditing the holding potential column for cell14, two cells fell out of the usable range (coefficient 0.257, stderr 0.015, n = 46). While checking residual autocorrelation for cell21, nothing in the figure changed at print size (coefficient 0.303, stderr 0.050, n = 53). While bootstrapping the CI for cell09, nothing in the figure changed at print size (coefficient 0.220, stderr 0.042, n = 44). While comparing per-cell orderings for cell10, the CI narrowed by roughly a tenth (coefficient 0.233, stderr 0.044, n = 50). While fitting the one-lag kernel for cell02, two cells fell out of the usable range (coefficient 0.166, stderr 0.028, n = 47).

```python
coefs = fit_per_cell(rows, threshold=0.74)
lo, hi = ci(coefs, seed=63)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While re-running with a tighter segmentation threshold for cell13, the coefficient tracked epoch count more closely than duration (coefficient 0.287, stderr 0.027, n = 47). While re-exporting the raw traces for cell02, nothing in the figure changed at print size (coefficient 0.201, stderr 0.039, n = 39). While re-running with a tighter segmentation threshold for cell23, the coefficient tracked epoch count more closely than duration (coefficient 0.139, stderr 0.026, n = 52). While bootstrapping the CI for cell06, the estimate moved less than one standard error (coefficient 0.172, stderr 0.048, n = 49). While auditing the holding potential column for cell07, the coefficient tracked epoch count more closely than duration (coefficient 0.273, stderr 0.038, n = 42). While comparing per-cell orderings for cell19, the coefficient tracked epoch count more closely than duration (coefficient 0.217, stderr 0.021, n = 41). Parking this until the re-segmentation lands.

### Step 42: re-running with a tighter segmentation threshold

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell02    0.258  0.023   0.214  0.303  38        1000
cell15    0.153  0.019   0.116  0.190  42        2000
cell02    0.272  0.045   0.183  0.361  58        1000
cell08    0.094  0.030   0.035  0.153  58        2000
cell10    0.218  0.029   0.161  0.274  41        4000
cell15    0.165  0.039   0.090  0.241  58        4000
cell20    0.101  0.040   0.023  0.178  56        1000
cell09    0.085  0.013   0.061  0.110  58        500
cell09    0.227  0.015   0.198  0.256  42        500
cell18    0.281  0.016   0.250  0.313  52        4000
```

While auditing the holding potential column for cell20, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.218, stderr 0.028, n = 52). While bootstrapping the CI for cell18, the estimate moved less than one standard error (coefficient 0.304, stderr 0.014, n = 57). While re-exporting the raw traces for cell07, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.227, stderr 0.033, n = 45). While bootstrapping the CI for cell24, the estimate moved less than one standard error (coefficient 0.222, stderr 0.031, n = 41).

### Step 43: auditing the holding potential column

While re-running with a tighter segmentation threshold for cell11, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.228, stderr 0.044, n = 58). While fitting the one-lag kernel for cell09, nothing in the figure changed at print size (coefficient 0.228, stderr 0.044, n = 43). While re-exporting the raw traces for cell16, nothing in the figure changed at print size (coefficient 0.207, stderr 0.019, n = 54). While re-running with a tighter segmentation threshold for cell07, the ordering of cells was preserved (coefficient 0.177, stderr 0.039, n = 57). While re-running with a tighter segmentation threshold for cell24, the coefficient tracked epoch count more closely than duration (coefficient 0.227, stderr 0.019, n = 41).

While segmenting epochs for cell10, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.291, stderr 0.020, n = 45). While re-exporting the raw traces for cell19, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.271, stderr 0.049, n = 45). While re-running with a tighter segmentation threshold for cell04, two cells fell out of the usable range (coefficient 0.210, stderr 0.050, n = 41). While fitting the one-lag kernel for cell02, the coefficient tracked epoch count more closely than duration (coefficient 0.275, stderr 0.019, n = 38). While comparing per-cell orderings for cell20, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.185, stderr 0.041, n = 54).

