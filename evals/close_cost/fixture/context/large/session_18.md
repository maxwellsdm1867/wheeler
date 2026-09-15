# Prior session 18 of 20

Transcript of an earlier working session on the history-kernel analysis.

### Step 1: bootstrapping the CI

While fitting the one-lag kernel for cell15, the estimate moved less than one standard error (coefficient 0.103, stderr 0.044, n = 48). While fitting the one-lag kernel for cell21, two cells fell out of the usable range (coefficient 0.280, stderr 0.032, n = 58). While re-running with a tighter segmentation threshold for cell03, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.175, stderr 0.012, n = 44). While re-exporting the raw traces for cell17, the CI narrowed by roughly a tenth (coefficient 0.196, stderr 0.022, n = 58). While re-exporting the raw traces for cell23, two cells fell out of the usable range (coefficient 0.091, stderr 0.012, n = 41). While re-running with a tighter segmentation threshold for cell15, the CI narrowed by roughly a tenth (coefficient 0.174, stderr 0.041, n = 43). Noted and moved on; it does not change the decision.

```python
coefs = fit_per_cell(rows, threshold=0.77)
lo, hi = ci(coefs, seed=61)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While re-exporting the raw traces for cell21, the CI narrowed by roughly a tenth (coefficient 0.229, stderr 0.047, n = 43). While fitting the one-lag kernel for cell21, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.248, stderr 0.018, n = 41). While fitting the one-lag kernel for cell15, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.188, stderr 0.027, n = 51). While re-running with a tighter segmentation threshold for cell11, two cells fell out of the usable range (coefficient 0.265, stderr 0.026, n = 40). Worth noting for the writeup, though not a result on its own.

```python
coefs = fit_per_cell(rows, threshold=0.41)
lo, hi = ci(coefs, seed=74)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 2: segmenting epochs

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell03    0.172  0.025   0.123  0.221  43        2000
cell13    0.140  0.020   0.101  0.179  51        4000
cell14    0.203  0.031   0.141  0.264  56        4000
cell24    0.125  0.043   0.040  0.210  49        1000
cell03    0.310  0.041   0.229  0.390  45        1000
cell21    0.207  0.024   0.160  0.254  49        4000
cell15    0.243  0.018   0.208  0.277  45        4000
cell24    0.271  0.011   0.250  0.292  44        4000
cell08    0.119  0.035   0.051  0.187  39        1000
cell22    0.306  0.020   0.266  0.345  55        1000
cell07    0.209  0.014   0.183  0.236  50        1000
cell22    0.105  0.030   0.046  0.165  47        500
```

```python
coefs = fit_per_cell(rows, threshold=0.42)
lo, hi = ci(coefs, seed=18)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```python
coefs = fit_per_cell(rows, threshold=0.46)
lo, hi = ci(coefs, seed=37)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 3: re-running with a tighter segmentation threshold

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell04    0.189  0.046   0.099  0.280  50        4000
cell01    0.116  0.024   0.069  0.162  42        4000
cell05    0.241  0.038   0.166  0.316  47        1000
cell10    0.166  0.025   0.117  0.215  41        1000
cell04    0.238  0.011   0.217  0.259  38        4000
cell15    0.235  0.047   0.143  0.326  56        1000
cell13    0.103  0.040   0.025  0.181  58        2000
cell16    0.256  0.031   0.195  0.318  58        500
cell05    0.132  0.018   0.096  0.168  40        4000
cell12    0.137  0.040   0.058  0.215  50        500
cell12    0.300  0.045   0.211  0.389  43        2000
```

While checking residual autocorrelation for cell24, the ordering of cells was preserved (coefficient 0.104, stderr 0.014, n = 38). While bootstrapping the CI for cell02, the estimate moved less than one standard error (coefficient 0.305, stderr 0.033, n = 47). While bootstrapping the CI for cell13, the estimate moved less than one standard error (coefficient 0.228, stderr 0.045, n = 50). While re-exporting the raw traces for cell16, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.282, stderr 0.047, n = 39).

While re-running with a tighter segmentation threshold for cell01, the CI narrowed by roughly a tenth (coefficient 0.117, stderr 0.044, n = 52). While comparing per-cell orderings for cell02, the coefficient tracked epoch count more closely than duration (coefficient 0.204, stderr 0.030, n = 51). While segmenting epochs for cell05, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.158, stderr 0.031, n = 51). While checking residual autocorrelation for cell02, the CI narrowed by roughly a tenth (coefficient 0.104, stderr 0.032, n = 52). While bootstrapping the CI for cell13, the CI narrowed by roughly a tenth (coefficient 0.302, stderr 0.010, n = 44). While checking residual autocorrelation for cell12, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.112, stderr 0.050, n = 54).

### Step 4: fitting the one-lag kernel

While auditing the holding potential column for cell16, two cells fell out of the usable range (coefficient 0.285, stderr 0.025, n = 49). While checking residual autocorrelation for cell13, the CI narrowed by roughly a tenth (coefficient 0.175, stderr 0.042, n = 55). While comparing per-cell orderings for cell11, two cells fell out of the usable range (coefficient 0.115, stderr 0.028, n = 43). While segmenting epochs for cell14, the coefficient tracked epoch count more closely than duration (coefficient 0.241, stderr 0.025, n = 47).

While comparing per-cell orderings for cell04, the CI narrowed by roughly a tenth (coefficient 0.228, stderr 0.011, n = 45). While re-running with a tighter segmentation threshold for cell17, the estimate moved less than one standard error (coefficient 0.146, stderr 0.024, n = 40). While auditing the holding potential column for cell17, the coefficient tracked epoch count more closely than duration (coefficient 0.282, stderr 0.032, n = 58).

While comparing per-cell orderings for cell17, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.276, stderr 0.047, n = 58). While bootstrapping the CI for cell01, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.299, stderr 0.022, n = 38). While re-running with a tighter segmentation threshold for cell05, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.278, stderr 0.015, n = 42). While re-exporting the raw traces for cell02, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.288, stderr 0.013, n = 47). While re-exporting the raw traces for cell23, nothing in the figure changed at print size (coefficient 0.305, stderr 0.017, n = 54). While bootstrapping the CI for cell10, the CI narrowed by roughly a tenth (coefficient 0.297, stderr 0.030, n = 58).

### Step 5: comparing per-cell orderings

While segmenting epochs for cell17, the estimate moved less than one standard error (coefficient 0.273, stderr 0.037, n = 51). While auditing the holding potential column for cell01, the coefficient tracked epoch count more closely than duration (coefficient 0.234, stderr 0.034, n = 52). While re-running with a tighter segmentation threshold for cell10, the ordering of cells was preserved (coefficient 0.177, stderr 0.013, n = 57). While comparing per-cell orderings for cell19, the coefficient tracked epoch count more closely than duration (coefficient 0.180, stderr 0.012, n = 54). While re-exporting the raw traces for cell05, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.149, stderr 0.046, n = 48). While comparing per-cell orderings for cell17, the coefficient tracked epoch count more closely than duration (coefficient 0.268, stderr 0.020, n = 53). Parking this until the re-segmentation lands.

While re-running with a tighter segmentation threshold for cell13, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.248, stderr 0.044, n = 41). While re-running with a tighter segmentation threshold for cell01, the CI narrowed by roughly a tenth (coefficient 0.214, stderr 0.034, n = 58). While fitting the one-lag kernel for cell20, nothing in the figure changed at print size (coefficient 0.260, stderr 0.021, n = 55). While comparing per-cell orderings for cell09, the estimate moved less than one standard error (coefficient 0.221, stderr 0.020, n = 52). Flagging it so it does not get rediscovered next week.

### Step 6: auditing the holding potential column

While checking residual autocorrelation for cell03, the CI narrowed by roughly a tenth (coefficient 0.310, stderr 0.034, n = 43). While re-running with a tighter segmentation threshold for cell13, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.103, stderr 0.047, n = 41). While re-exporting the raw traces for cell17, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.150, stderr 0.029, n = 53). While re-exporting the raw traces for cell13, the ordering of cells was preserved (coefficient 0.286, stderr 0.028, n = 38). While checking residual autocorrelation for cell21, the coefficient tracked epoch count more closely than duration (coefficient 0.298, stderr 0.024, n = 43). While bootstrapping the CI for cell12, nothing in the figure changed at print size (coefficient 0.219, stderr 0.030, n = 44). This is the part that will need a real statistical argument.

While bootstrapping the CI for cell22, the coefficient tracked epoch count more closely than duration (coefficient 0.162, stderr 0.027, n = 57). While re-exporting the raw traces for cell20, the CI narrowed by roughly a tenth (coefficient 0.101, stderr 0.029, n = 52). While fitting the one-lag kernel for cell18, two cells fell out of the usable range (coefficient 0.248, stderr 0.039, n = 43).

While fitting the one-lag kernel for cell09, the CI narrowed by roughly a tenth (coefficient 0.211, stderr 0.013, n = 38). While comparing per-cell orderings for cell08, the coefficient tracked epoch count more closely than duration (coefficient 0.261, stderr 0.048, n = 46). While bootstrapping the CI for cell15, the ordering of cells was preserved (coefficient 0.145, stderr 0.033, n = 49).

### Step 7: segmenting epochs

While comparing per-cell orderings for cell19, nothing in the figure changed at print size (coefficient 0.196, stderr 0.050, n = 48). While re-exporting the raw traces for cell08, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.127, stderr 0.037, n = 46). While checking residual autocorrelation for cell07, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.301, stderr 0.027, n = 40). While segmenting epochs for cell20, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.261, stderr 0.024, n = 43).

While checking residual autocorrelation for cell16, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.228, stderr 0.036, n = 50). While comparing per-cell orderings for cell03, nothing in the figure changed at print size (coefficient 0.111, stderr 0.037, n = 57). While auditing the holding potential column for cell12, the coefficient tracked epoch count more closely than duration (coefficient 0.201, stderr 0.016, n = 52).

While fitting the one-lag kernel for cell14, two cells fell out of the usable range (coefficient 0.255, stderr 0.015, n = 40). While bootstrapping the CI for cell04, the CI narrowed by roughly a tenth (coefficient 0.203, stderr 0.016, n = 41). While bootstrapping the CI for cell20, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.219, stderr 0.050, n = 39). While bootstrapping the CI for cell01, the coefficient tracked epoch count more closely than duration (coefficient 0.112, stderr 0.050, n = 55). Flagging it so it does not get rediscovered next week.

```python
coefs = fit_per_cell(rows, threshold=0.50)
lo, hi = ci(coefs, seed=35)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 8: re-running with a tighter segmentation threshold

```python
coefs = fit_per_cell(rows, threshold=0.74)
lo, hi = ci(coefs, seed=43)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell20    0.268  0.038   0.194  0.341  45        4000
cell24    0.081  0.041   0.000  0.161  57        500
cell09    0.251  0.030   0.193  0.309  55        500
cell19    0.161  0.050   0.063  0.259  42        2000
cell08    0.218  0.027   0.165  0.272  52        2000
cell17    0.217  0.042   0.136  0.298  55        500
cell12    0.148  0.013   0.122  0.174  38        1000
cell22    0.158  0.048   0.064  0.251  42        2000
cell01    0.171  0.029   0.114  0.228  52        2000
cell16    0.102  0.034   0.035  0.169  47        2000
```

While segmenting epochs for cell18, the CI narrowed by roughly a tenth (coefficient 0.083, stderr 0.021, n = 46). While auditing the holding potential column for cell08, nothing in the figure changed at print size (coefficient 0.080, stderr 0.048, n = 48). While segmenting epochs for cell04, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.145, stderr 0.019, n = 41). While checking residual autocorrelation for cell18, two cells fell out of the usable range (coefficient 0.168, stderr 0.012, n = 46). While re-exporting the raw traces for cell09, the ordering of cells was preserved (coefficient 0.216, stderr 0.041, n = 39). While comparing per-cell orderings for cell11, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.134, stderr 0.029, n = 40).

### Step 9: bootstrapping the CI

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell20    0.089  0.019   0.052  0.126  38        500
cell01    0.181  0.021   0.139  0.222  50        4000
cell08    0.118  0.039   0.042  0.194  45        1000
cell20    0.249  0.027   0.195  0.303  48        1000
cell13    0.272  0.041   0.191  0.353  41        500
cell10    0.151  0.014   0.124  0.177  39        500
cell11    0.309  0.033   0.244  0.374  47        1000
cell01    0.177  0.013   0.152  0.202  57        2000
cell08    0.236  0.045   0.149  0.324  56        4000
cell14    0.252  0.046   0.162  0.342  51        2000
cell15    0.203  0.037   0.131  0.275  55        1000
cell23    0.199  0.018   0.163  0.236  41        4000
```

While re-exporting the raw traces for cell05, nothing in the figure changed at print size (coefficient 0.214, stderr 0.043, n = 45). While fitting the one-lag kernel for cell10, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.279, stderr 0.011, n = 43). While checking residual autocorrelation for cell11, the estimate moved less than one standard error (coefficient 0.238, stderr 0.021, n = 56). While fitting the one-lag kernel for cell06, the CI narrowed by roughly a tenth (coefficient 0.199, stderr 0.017, n = 56). While checking residual autocorrelation for cell02, the ordering of cells was preserved (coefficient 0.209, stderr 0.028, n = 57). While auditing the holding potential column for cell18, the estimate moved less than one standard error (coefficient 0.155, stderr 0.043, n = 41). This is the part that will need a real statistical argument.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell24    0.109  0.039   0.032  0.185  42        500
cell02    0.149  0.019   0.112  0.187  57        1000
cell21    0.248  0.042   0.165  0.331  56        1000
cell16    0.123  0.040   0.045  0.201  56        500
cell04    0.212  0.028   0.157  0.267  38        4000
cell09    0.138  0.042   0.056  0.220  58        4000
cell02    0.180  0.040   0.102  0.257  45        2000
cell17    0.164  0.041   0.084  0.244  39        500
```

While re-exporting the raw traces for cell24, nothing in the figure changed at print size (coefficient 0.206, stderr 0.015, n = 55). While comparing per-cell orderings for cell22, the ordering of cells was preserved (coefficient 0.151, stderr 0.038, n = 52). While auditing the holding potential column for cell12, nothing in the figure changed at print size (coefficient 0.265, stderr 0.035, n = 49). While segmenting epochs for cell12, the coefficient tracked epoch count more closely than duration (coefficient 0.265, stderr 0.041, n = 54). While comparing per-cell orderings for cell21, the estimate moved less than one standard error (coefficient 0.301, stderr 0.013, n = 39).

### Step 10: re-running with a tighter segmentation threshold

While checking residual autocorrelation for cell03, the estimate moved less than one standard error (coefficient 0.289, stderr 0.017, n = 40). While bootstrapping the CI for cell23, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.097, stderr 0.028, n = 54). While re-running with a tighter segmentation threshold for cell21, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.192, stderr 0.042, n = 57). While segmenting epochs for cell14, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.300, stderr 0.024, n = 58). While checking residual autocorrelation for cell03, the coefficient tracked epoch count more closely than duration (coefficient 0.195, stderr 0.034, n = 55).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell06    0.189  0.046   0.098  0.279  43        2000
cell23    0.110  0.044   0.024  0.197  43        1000
cell18    0.306  0.040   0.228  0.384  44        4000
cell15    0.119  0.022   0.076  0.163  52        500
cell14    0.118  0.018   0.083  0.153  46        2000
cell01    0.297  0.042   0.215  0.379  38        2000
cell06    0.305  0.011   0.284  0.326  38        2000
cell16    0.232  0.046   0.141  0.323  41        2000
cell14    0.302  0.011   0.281  0.323  57        4000
cell07    0.194  0.023   0.148  0.240  48        2000
```

While bootstrapping the CI for cell12, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.208, stderr 0.029, n = 51). While checking residual autocorrelation for cell06, the ordering of cells was preserved (coefficient 0.192, stderr 0.014, n = 48). While checking residual autocorrelation for cell12, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.268, stderr 0.025, n = 43). While checking residual autocorrelation for cell09, the estimate moved less than one standard error (coefficient 0.143, stderr 0.031, n = 38). While bootstrapping the CI for cell10, the CI narrowed by roughly a tenth (coefficient 0.126, stderr 0.032, n = 52). While re-running with a tighter segmentation threshold for cell22, nothing in the figure changed at print size (coefficient 0.237, stderr 0.049, n = 55).

### Step 11: comparing per-cell orderings

```python
coefs = fit_per_cell(rows, threshold=0.32)
lo, hi = ci(coefs, seed=31)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell06    0.231  0.042   0.149  0.314  51        1000
cell15    0.161  0.012   0.137  0.184  49        2000
cell09    0.185  0.023   0.140  0.230  56        4000
cell05    0.199  0.010   0.179  0.219  39        2000
cell05    0.209  0.039   0.133  0.286  45        500
cell21    0.258  0.020   0.219  0.298  49        4000
cell16    0.228  0.014   0.200  0.257  50        1000
cell10    0.128  0.011   0.107  0.149  43        4000
cell12    0.309  0.028   0.254  0.363  42        500
cell18    0.227  0.044   0.140  0.314  40        4000
cell15    0.203  0.025   0.154  0.252  45        4000
cell24    0.102  0.034   0.034  0.169  41        1000
cell04    0.208  0.042   0.125  0.291  58        1000
```

While checking residual autocorrelation for cell19, the ordering of cells was preserved (coefficient 0.145, stderr 0.030, n = 56). While comparing per-cell orderings for cell09, two cells fell out of the usable range (coefficient 0.218, stderr 0.021, n = 39). While re-running with a tighter segmentation threshold for cell10, the coefficient tracked epoch count more closely than duration (coefficient 0.310, stderr 0.017, n = 45). While segmenting epochs for cell07, two cells fell out of the usable range (coefficient 0.132, stderr 0.033, n = 56).

### Step 12: fitting the one-lag kernel

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell13    0.081  0.022   0.038  0.125  55        2000
cell06    0.186  0.044   0.100  0.273  54        2000
cell08    0.223  0.023   0.178  0.267  44        4000
cell04    0.248  0.043   0.163  0.333  39        500
cell20    0.221  0.039   0.145  0.298  58        2000
cell11    0.246  0.016   0.216  0.277  45        4000
cell02    0.235  0.028   0.181  0.289  48        2000
cell12    0.195  0.012   0.172  0.218  56        2000
cell12    0.220  0.011   0.199  0.242  47        2000
cell19    0.102  0.018   0.066  0.139  49        500
cell10    0.271  0.044   0.185  0.357  48        2000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell19    0.256  0.034   0.190  0.322  42        2000
cell17    0.120  0.042   0.038  0.202  52        4000
cell09    0.211  0.025   0.162  0.259  46        2000
cell07    0.084  0.045   -0.004  0.172  57        2000
cell12    0.228  0.022   0.184  0.271  52        2000
cell07    0.129  0.038   0.054  0.204  57        1000
cell09    0.140  0.037   0.067  0.212  40        1000
cell21    0.196  0.033   0.130  0.262  47        4000
cell14    0.251  0.036   0.180  0.323  45        4000
cell16    0.169  0.014   0.143  0.196  53        500
```

```python
coefs = fit_per_cell(rows, threshold=0.34)
lo, hi = ci(coefs, seed=11)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While bootstrapping the CI for cell10, nothing in the figure changed at print size (coefficient 0.213, stderr 0.013, n = 43). While comparing per-cell orderings for cell15, nothing in the figure changed at print size (coefficient 0.298, stderr 0.032, n = 58). While checking residual autocorrelation for cell13, two cells fell out of the usable range (coefficient 0.144, stderr 0.038, n = 57). Flagging it so it does not get rediscovered next week.

### Step 13: re-exporting the raw traces

While checking residual autocorrelation for cell23, the coefficient tracked epoch count more closely than duration (coefficient 0.309, stderr 0.040, n = 56). While re-running with a tighter segmentation threshold for cell13, the CI narrowed by roughly a tenth (coefficient 0.305, stderr 0.024, n = 51). While auditing the holding potential column for cell23, nothing in the figure changed at print size (coefficient 0.098, stderr 0.046, n = 52). While checking residual autocorrelation for cell10, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.141, stderr 0.025, n = 38). While fitting the one-lag kernel for cell20, the CI narrowed by roughly a tenth (coefficient 0.103, stderr 0.014, n = 38). While comparing per-cell orderings for cell18, the CI narrowed by roughly a tenth (coefficient 0.132, stderr 0.027, n = 40).

While bootstrapping the CI for cell04, the coefficient tracked epoch count more closely than duration (coefficient 0.202, stderr 0.035, n = 55). While comparing per-cell orderings for cell07, the CI narrowed by roughly a tenth (coefficient 0.175, stderr 0.015, n = 46). While auditing the holding potential column for cell23, two cells fell out of the usable range (coefficient 0.231, stderr 0.023, n = 44). While bootstrapping the CI for cell07, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.090, stderr 0.017, n = 44). While comparing per-cell orderings for cell03, the estimate moved less than one standard error (coefficient 0.109, stderr 0.011, n = 50).

### Step 14: re-exporting the raw traces

While bootstrapping the CI for cell03, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.225, stderr 0.045, n = 51). While segmenting epochs for cell05, nothing in the figure changed at print size (coefficient 0.275, stderr 0.031, n = 55). While fitting the one-lag kernel for cell22, nothing in the figure changed at print size (coefficient 0.147, stderr 0.012, n = 55). While bootstrapping the CI for cell14, nothing in the figure changed at print size (coefficient 0.131, stderr 0.049, n = 39). Parking this until the re-segmentation lands.

While bootstrapping the CI for cell17, nothing in the figure changed at print size (coefficient 0.217, stderr 0.027, n = 49). While segmenting epochs for cell05, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.303, stderr 0.010, n = 40). While re-running with a tighter segmentation threshold for cell12, the ordering of cells was preserved (coefficient 0.186, stderr 0.044, n = 42). While re-running with a tighter segmentation threshold for cell12, the ordering of cells was preserved (coefficient 0.287, stderr 0.032, n = 56). Noted and moved on; it does not change the decision.

### Step 15: re-running with a tighter segmentation threshold

While re-exporting the raw traces for cell01, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.097, stderr 0.038, n = 57). While bootstrapping the CI for cell11, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.244, stderr 0.022, n = 51). While re-exporting the raw traces for cell17, the CI narrowed by roughly a tenth (coefficient 0.181, stderr 0.040, n = 50). While segmenting epochs for cell17, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.269, stderr 0.031, n = 39). While auditing the holding potential column for cell13, nothing in the figure changed at print size (coefficient 0.272, stderr 0.041, n = 54). While fitting the one-lag kernel for cell22, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.218, stderr 0.026, n = 39).

While bootstrapping the CI for cell15, nothing in the figure changed at print size (coefficient 0.242, stderr 0.044, n = 55). While re-running with a tighter segmentation threshold for cell05, the CI narrowed by roughly a tenth (coefficient 0.198, stderr 0.038, n = 56). While re-exporting the raw traces for cell14, nothing in the figure changed at print size (coefficient 0.119, stderr 0.031, n = 51). While fitting the one-lag kernel for cell13, two cells fell out of the usable range (coefficient 0.250, stderr 0.033, n = 53). While fitting the one-lag kernel for cell17, the coefficient tracked epoch count more closely than duration (coefficient 0.157, stderr 0.012, n = 46). Worth noting for the writeup, though not a result on its own.

### Step 16: auditing the holding potential column

While auditing the holding potential column for cell08, nothing in the figure changed at print size (coefficient 0.204, stderr 0.026, n = 49). While segmenting epochs for cell14, the CI narrowed by roughly a tenth (coefficient 0.302, stderr 0.036, n = 38). While bootstrapping the CI for cell05, two cells fell out of the usable range (coefficient 0.099, stderr 0.047, n = 45).

While comparing per-cell orderings for cell02, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.305, stderr 0.016, n = 50). While comparing per-cell orderings for cell17, the CI narrowed by roughly a tenth (coefficient 0.280, stderr 0.030, n = 50). While re-running with a tighter segmentation threshold for cell17, the CI narrowed by roughly a tenth (coefficient 0.155, stderr 0.011, n = 42). While auditing the holding potential column for cell08, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.275, stderr 0.041, n = 41).

While re-exporting the raw traces for cell15, the estimate moved less than one standard error (coefficient 0.182, stderr 0.048, n = 48). While bootstrapping the CI for cell21, nothing in the figure changed at print size (coefficient 0.227, stderr 0.050, n = 42). While segmenting epochs for cell11, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.161, stderr 0.015, n = 47). While segmenting epochs for cell14, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.089, stderr 0.027, n = 51). Noted and moved on; it does not change the decision.

While comparing per-cell orderings for cell22, two cells fell out of the usable range (coefficient 0.109, stderr 0.046, n = 51). While checking residual autocorrelation for cell12, nothing in the figure changed at print size (coefficient 0.144, stderr 0.011, n = 41). While auditing the holding potential column for cell10, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.083, stderr 0.027, n = 48). While fitting the one-lag kernel for cell06, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.124, stderr 0.039, n = 45). While fitting the one-lag kernel for cell10, the CI narrowed by roughly a tenth (coefficient 0.171, stderr 0.048, n = 48).

### Step 17: bootstrapping the CI

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell01    0.177  0.010   0.157  0.197  44        500
cell24    0.102  0.028   0.047  0.158  45        500
cell07    0.243  0.028   0.188  0.299  55        4000
cell12    0.266  0.046   0.176  0.356  57        2000
cell11    0.104  0.023   0.059  0.150  51        500
cell08    0.300  0.012   0.277  0.323  51        2000
cell01    0.096  0.030   0.037  0.154  43        2000
cell02    0.174  0.016   0.144  0.205  50        500
cell19    0.304  0.044   0.218  0.390  53        500
cell10    0.213  0.022   0.169  0.257  45        500
cell12    0.161  0.050   0.064  0.258  44        2000
cell06    0.214  0.034   0.147  0.282  49        500
cell13    0.293  0.016   0.262  0.325  51        1000
cell22    0.251  0.045   0.163  0.339  50        4000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell23    0.256  0.037   0.183  0.329  49        2000
cell02    0.087  0.011   0.066  0.108  50        2000
cell21    0.141  0.020   0.102  0.181  56        1000
cell11    0.241  0.038   0.167  0.315  38        4000
cell23    0.117  0.015   0.087  0.148  39        4000
cell14    0.275  0.018   0.239  0.311  38        2000
cell02    0.228  0.014   0.201  0.256  56        2000
cell21    0.139  0.015   0.110  0.168  51        500
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell12    0.269  0.037   0.196  0.341  40        2000
cell03    0.187  0.022   0.144  0.230  40        500
cell23    0.120  0.017   0.087  0.153  43        500
cell03    0.144  0.038   0.069  0.219  45        2000
cell22    0.294  0.020   0.256  0.333  43        1000
cell16    0.158  0.043   0.073  0.243  42        4000
cell02    0.086  0.036   0.016  0.156  49        2000
cell11    0.182  0.022   0.139  0.225  45        500
cell02    0.123  0.047   0.032  0.215  56        500
cell22    0.277  0.013   0.250  0.303  38        2000
cell17    0.140  0.031   0.079  0.200  58        4000
cell22    0.085  0.030   0.027  0.144  54        1000
cell12    0.248  0.011   0.226  0.270  46        1000
```

### Step 18: re-running with a tighter segmentation threshold

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell03    0.140  0.029   0.084  0.196  47        4000
cell11    0.091  0.025   0.043  0.140  39        1000
cell04    0.104  0.012   0.081  0.127  54        500
cell22    0.196  0.036   0.127  0.266  50        4000
cell18    0.137  0.013   0.111  0.162  42        500
cell09    0.219  0.018   0.184  0.255  47        1000
```

While bootstrapping the CI for cell06, the ordering of cells was preserved (coefficient 0.272, stderr 0.020, n = 39). While checking residual autocorrelation for cell04, the ordering of cells was preserved (coefficient 0.240, stderr 0.023, n = 58). While fitting the one-lag kernel for cell09, the ordering of cells was preserved (coefficient 0.276, stderr 0.040, n = 40). While auditing the holding potential column for cell09, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.199, stderr 0.032, n = 40). While re-running with a tighter segmentation threshold for cell19, the ordering of cells was preserved (coefficient 0.244, stderr 0.011, n = 56).

### Step 19: re-running with a tighter segmentation threshold

While segmenting epochs for cell15, two cells fell out of the usable range (coefficient 0.235, stderr 0.025, n = 58). While re-exporting the raw traces for cell17, the coefficient tracked epoch count more closely than duration (coefficient 0.140, stderr 0.042, n = 39). While checking residual autocorrelation for cell12, the estimate moved less than one standard error (coefficient 0.093, stderr 0.027, n = 40).

```python
coefs = fit_per_cell(rows, threshold=0.73)
lo, hi = ci(coefs, seed=94)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While segmenting epochs for cell20, nothing in the figure changed at print size (coefficient 0.158, stderr 0.013, n = 56). While comparing per-cell orderings for cell18, two cells fell out of the usable range (coefficient 0.090, stderr 0.012, n = 41). While re-running with a tighter segmentation threshold for cell08, the ordering of cells was preserved (coefficient 0.154, stderr 0.030, n = 58). While comparing per-cell orderings for cell16, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.273, stderr 0.026, n = 44).

### Step 20: re-running with a tighter segmentation threshold

```python
coefs = fit_per_cell(rows, threshold=0.45)
lo, hi = ci(coefs, seed=27)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While comparing per-cell orderings for cell09, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.203, stderr 0.016, n = 54). While fitting the one-lag kernel for cell08, the coefficient tracked epoch count more closely than duration (coefficient 0.288, stderr 0.038, n = 50). While fitting the one-lag kernel for cell13, nothing in the figure changed at print size (coefficient 0.160, stderr 0.024, n = 49).

While auditing the holding potential column for cell07, the CI narrowed by roughly a tenth (coefficient 0.202, stderr 0.017, n = 56). While segmenting epochs for cell14, the coefficient tracked epoch count more closely than duration (coefficient 0.293, stderr 0.017, n = 41). While fitting the one-lag kernel for cell19, the CI narrowed by roughly a tenth (coefficient 0.278, stderr 0.046, n = 38). While checking residual autocorrelation for cell24, the coefficient tracked epoch count more closely than duration (coefficient 0.099, stderr 0.025, n = 56). Flagging it so it does not get rediscovered next week.

### Step 21: segmenting epochs

While re-exporting the raw traces for cell03, two cells fell out of the usable range (coefficient 0.277, stderr 0.031, n = 50). While fitting the one-lag kernel for cell07, the coefficient tracked epoch count more closely than duration (coefficient 0.123, stderr 0.037, n = 52). While auditing the holding potential column for cell22, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.155, stderr 0.037, n = 50).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell12    0.222  0.021   0.180  0.264  39        1000
cell15    0.138  0.027   0.085  0.192  45        2000
cell08    0.182  0.042   0.099  0.264  48        2000
cell16    0.091  0.016   0.059  0.123  57        4000
cell06    0.103  0.027   0.050  0.155  48        1000
cell07    0.248  0.028   0.193  0.302  38        1000
cell03    0.132  0.021   0.091  0.173  38        500
cell23    0.291  0.049   0.195  0.388  47        4000
cell18    0.081  0.032   0.018  0.143  42        1000
cell10    0.080  0.031   0.020  0.141  54        500
cell06    0.100  0.026   0.049  0.151  38        4000
cell22    0.182  0.011   0.161  0.203  44        500
cell21    0.173  0.042   0.090  0.255  40        500
cell13    0.258  0.016   0.228  0.289  53        4000
```

### Step 22: bootstrapping the CI

While comparing per-cell orderings for cell19, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.150, stderr 0.043, n = 50). While re-exporting the raw traces for cell07, the ordering of cells was preserved (coefficient 0.162, stderr 0.010, n = 39). While re-exporting the raw traces for cell17, the estimate moved less than one standard error (coefficient 0.114, stderr 0.022, n = 54).

While comparing per-cell orderings for cell05, the ordering of cells was preserved (coefficient 0.275, stderr 0.022, n = 55). While fitting the one-lag kernel for cell10, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.201, stderr 0.018, n = 50). While re-exporting the raw traces for cell23, two cells fell out of the usable range (coefficient 0.123, stderr 0.038, n = 53). While comparing per-cell orderings for cell01, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.117, stderr 0.040, n = 42).

### Step 23: comparing per-cell orderings

While checking residual autocorrelation for cell15, the CI narrowed by roughly a tenth (coefficient 0.213, stderr 0.027, n = 42). While fitting the one-lag kernel for cell20, the estimate moved less than one standard error (coefficient 0.278, stderr 0.042, n = 53). While bootstrapping the CI for cell02, the coefficient tracked epoch count more closely than duration (coefficient 0.184, stderr 0.024, n = 58). While re-exporting the raw traces for cell20, nothing in the figure changed at print size (coefficient 0.269, stderr 0.046, n = 55).

While re-running with a tighter segmentation threshold for cell01, the ordering of cells was preserved (coefficient 0.241, stderr 0.032, n = 48). While bootstrapping the CI for cell14, the ordering of cells was preserved (coefficient 0.086, stderr 0.034, n = 57). While checking residual autocorrelation for cell23, the estimate moved less than one standard error (coefficient 0.299, stderr 0.013, n = 52). While auditing the holding potential column for cell07, the coefficient tracked epoch count more closely than duration (coefficient 0.236, stderr 0.040, n = 50). While re-running with a tighter segmentation threshold for cell18, nothing in the figure changed at print size (coefficient 0.114, stderr 0.011, n = 47). This is the part that will need a real statistical argument.

While segmenting epochs for cell03, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.092, stderr 0.038, n = 41). While fitting the one-lag kernel for cell13, the CI narrowed by roughly a tenth (coefficient 0.300, stderr 0.018, n = 46). While checking residual autocorrelation for cell21, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.274, stderr 0.050, n = 39). While fitting the one-lag kernel for cell11, two cells fell out of the usable range (coefficient 0.235, stderr 0.036, n = 44).

While checking residual autocorrelation for cell21, the coefficient tracked epoch count more closely than duration (coefficient 0.293, stderr 0.048, n = 45). While re-running with a tighter segmentation threshold for cell04, the CI narrowed by roughly a tenth (coefficient 0.223, stderr 0.014, n = 40). While auditing the holding potential column for cell23, nothing in the figure changed at print size (coefficient 0.107, stderr 0.019, n = 48). While re-running with a tighter segmentation threshold for cell21, the ordering of cells was preserved (coefficient 0.127, stderr 0.048, n = 49). This is the part that will need a real statistical argument.

### Step 24: auditing the holding potential column

```python
coefs = fit_per_cell(rows, threshold=0.55)
lo, hi = ci(coefs, seed=83)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```python
coefs = fit_per_cell(rows, threshold=0.70)
lo, hi = ci(coefs, seed=94)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While fitting the one-lag kernel for cell14, the coefficient tracked epoch count more closely than duration (coefficient 0.156, stderr 0.046, n = 49). While comparing per-cell orderings for cell15, the ordering of cells was preserved (coefficient 0.202, stderr 0.026, n = 51). While re-exporting the raw traces for cell15, the CI narrowed by roughly a tenth (coefficient 0.289, stderr 0.022, n = 40). Parking this until the re-segmentation lands.

### Step 25: auditing the holding potential column

While comparing per-cell orderings for cell23, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.214, stderr 0.016, n = 48). While comparing per-cell orderings for cell17, the coefficient tracked epoch count more closely than duration (coefficient 0.307, stderr 0.022, n = 57). While checking residual autocorrelation for cell03, the estimate moved less than one standard error (coefficient 0.133, stderr 0.042, n = 43). While checking residual autocorrelation for cell16, the estimate moved less than one standard error (coefficient 0.138, stderr 0.015, n = 39). While auditing the holding potential column for cell19, the ordering of cells was preserved (coefficient 0.103, stderr 0.024, n = 47). Parking this until the re-segmentation lands.

While bootstrapping the CI for cell18, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.223, stderr 0.049, n = 40). While comparing per-cell orderings for cell09, the estimate moved less than one standard error (coefficient 0.148, stderr 0.050, n = 48). While bootstrapping the CI for cell13, nothing in the figure changed at print size (coefficient 0.159, stderr 0.048, n = 39). While re-exporting the raw traces for cell07, the coefficient tracked epoch count more closely than duration (coefficient 0.144, stderr 0.038, n = 52). While re-running with a tighter segmentation threshold for cell05, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.267, stderr 0.023, n = 49). While checking residual autocorrelation for cell06, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.237, stderr 0.047, n = 41). Flagging it so it does not get rediscovered next week.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell23    0.090  0.037   0.017  0.162  57        4000
cell24    0.246  0.019   0.209  0.283  50        2000
cell15    0.166  0.025   0.116  0.216  49        1000
cell23    0.080  0.011   0.059  0.102  47        1000
cell22    0.308  0.012   0.285  0.331  51        1000
cell20    0.130  0.048   0.037  0.224  50        500
cell06    0.120  0.047   0.027  0.212  57        500
```

```python
coefs = fit_per_cell(rows, threshold=0.68)
lo, hi = ci(coefs, seed=59)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 26: segmenting epochs

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell09    0.111  0.024   0.064  0.157  50        1000
cell04    0.155  0.027   0.103  0.208  50        4000
cell20    0.198  0.022   0.155  0.241  55        500
cell03    0.192  0.044   0.107  0.278  47        2000
cell20    0.155  0.023   0.111  0.199  41        4000
cell17    0.161  0.027   0.108  0.214  44        2000
cell20    0.291  0.034   0.225  0.358  39        500
cell17    0.162  0.029   0.105  0.219  45        500
cell01    0.182  0.022   0.139  0.225  51        1000
cell17    0.263  0.025   0.214  0.311  50        1000
cell05    0.238  0.043   0.153  0.322  58        1000
```

```python
coefs = fit_per_cell(rows, threshold=0.64)
lo, hi = ci(coefs, seed=85)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 27: auditing the holding potential column

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell02    0.290  0.041   0.210  0.369  45        4000
cell13    0.108  0.049   0.012  0.204  50        1000
cell22    0.139  0.021   0.098  0.181  56        2000
cell18    0.195  0.032   0.133  0.256  48        4000
cell03    0.157  0.045   0.068  0.245  38        1000
cell12    0.285  0.015   0.257  0.314  50        500
cell20    0.153  0.042   0.070  0.236  38        500
cell16    0.299  0.036   0.229  0.369  53        4000
```

```python
coefs = fit_per_cell(rows, threshold=0.72)
lo, hi = ci(coefs, seed=22)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```python
coefs = fit_per_cell(rows, threshold=0.48)
lo, hi = ci(coefs, seed=63)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 28: bootstrapping the CI

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell14    0.218  0.028   0.163  0.273  47        1000
cell21    0.231  0.021   0.191  0.271  52        500
cell24    0.176  0.038   0.102  0.251  50        500
cell13    0.262  0.036   0.190  0.333  49        4000
cell11    0.214  0.033   0.149  0.280  53        500
cell03    0.152  0.040   0.073  0.230  45        1000
cell08    0.246  0.016   0.214  0.277  56        1000
cell10    0.122  0.045   0.034  0.210  55        2000
cell23    0.182  0.029   0.125  0.238  44        1000
cell01    0.084  0.018   0.049  0.119  38        1000
cell05    0.298  0.015   0.268  0.328  53        500
cell22    0.248  0.015   0.219  0.277  55        2000
```

While segmenting epochs for cell08, nothing in the figure changed at print size (coefficient 0.284, stderr 0.041, n = 53). While checking residual autocorrelation for cell06, two cells fell out of the usable range (coefficient 0.149, stderr 0.044, n = 54). While fitting the one-lag kernel for cell09, the ordering of cells was preserved (coefficient 0.097, stderr 0.038, n = 55). While re-exporting the raw traces for cell14, the ordering of cells was preserved (coefficient 0.195, stderr 0.019, n = 47). While fitting the one-lag kernel for cell18, the estimate moved less than one standard error (coefficient 0.209, stderr 0.015, n = 45). While re-running with a tighter segmentation threshold for cell23, the ordering of cells was preserved (coefficient 0.178, stderr 0.050, n = 46). This is the part that will need a real statistical argument.

### Step 29: comparing per-cell orderings

While fitting the one-lag kernel for cell09, the ordering of cells was preserved (coefficient 0.081, stderr 0.012, n = 51). While comparing per-cell orderings for cell10, the estimate moved less than one standard error (coefficient 0.196, stderr 0.030, n = 39). While re-exporting the raw traces for cell24, the ordering of cells was preserved (coefficient 0.296, stderr 0.016, n = 47). While comparing per-cell orderings for cell03, two cells fell out of the usable range (coefficient 0.211, stderr 0.038, n = 39).

While segmenting epochs for cell08, nothing in the figure changed at print size (coefficient 0.208, stderr 0.047, n = 56). While comparing per-cell orderings for cell02, the CI narrowed by roughly a tenth (coefficient 0.228, stderr 0.030, n = 48). While re-exporting the raw traces for cell19, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.117, stderr 0.039, n = 58). While auditing the holding potential column for cell17, the coefficient tracked epoch count more closely than duration (coefficient 0.207, stderr 0.043, n = 42). While segmenting epochs for cell05, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.244, stderr 0.013, n = 42). While segmenting epochs for cell05, two cells fell out of the usable range (coefficient 0.273, stderr 0.011, n = 49).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell20    0.178  0.032   0.116  0.241  38        500
cell22    0.248  0.032   0.185  0.312  50        2000
cell04    0.183  0.023   0.138  0.228  57        1000
cell17    0.255  0.032   0.193  0.317  57        4000
cell12    0.234  0.025   0.185  0.284  55        2000
cell20    0.154  0.031   0.093  0.215  43        4000
cell07    0.189  0.049   0.092  0.286  40        2000
```

### Step 30: re-exporting the raw traces

While checking residual autocorrelation for cell22, the coefficient tracked epoch count more closely than duration (coefficient 0.094, stderr 0.017, n = 52). While auditing the holding potential column for cell14, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.305, stderr 0.046, n = 55). While auditing the holding potential column for cell03, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.181, stderr 0.031, n = 38). While comparing per-cell orderings for cell05, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.087, stderr 0.016, n = 46). Worth noting for the writeup, though not a result on its own.

While checking residual autocorrelation for cell10, the estimate moved less than one standard error (coefficient 0.109, stderr 0.046, n = 56). While comparing per-cell orderings for cell24, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.163, stderr 0.018, n = 52). While comparing per-cell orderings for cell10, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.137, stderr 0.040, n = 42). While comparing per-cell orderings for cell09, the coefficient tracked epoch count more closely than duration (coefficient 0.242, stderr 0.034, n = 48).

### Step 31: bootstrapping the CI

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell04    0.290  0.023   0.245  0.335  52        1000
cell07    0.155  0.035   0.087  0.223  52        1000
cell16    0.235  0.039   0.159  0.312  38        2000
cell16    0.227  0.033   0.163  0.291  54        1000
cell06    0.242  0.042   0.159  0.325  44        4000
cell24    0.310  0.014   0.282  0.337  50        2000
cell24    0.157  0.027   0.103  0.210  55        4000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell03    0.187  0.030   0.129  0.245  51        2000
cell23    0.240  0.027   0.187  0.293  57        2000
cell04    0.156  0.030   0.097  0.214  52        1000
cell02    0.201  0.040   0.123  0.279  57        4000
cell18    0.227  0.022   0.183  0.271  41        500
cell02    0.283  0.030   0.225  0.341  43        2000
cell19    0.210  0.035   0.140  0.279  44        4000
cell20    0.108  0.037   0.036  0.180  44        500
cell09    0.197  0.021   0.156  0.238  47        1000
cell17    0.184  0.012   0.160  0.209  58        2000
cell15    0.175  0.048   0.081  0.269  41        1000
```

While re-exporting the raw traces for cell04, nothing in the figure changed at print size (coefficient 0.305, stderr 0.021, n = 54). While re-running with a tighter segmentation threshold for cell19, the coefficient tracked epoch count more closely than duration (coefficient 0.306, stderr 0.021, n = 42). While segmenting epochs for cell17, the ordering of cells was preserved (coefficient 0.259, stderr 0.049, n = 57). While re-exporting the raw traces for cell17, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.294, stderr 0.049, n = 57). While auditing the holding potential column for cell19, the CI narrowed by roughly a tenth (coefficient 0.279, stderr 0.043, n = 48). Parking this until the re-segmentation lands.

While auditing the holding potential column for cell12, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.254, stderr 0.031, n = 55). While fitting the one-lag kernel for cell05, nothing in the figure changed at print size (coefficient 0.095, stderr 0.041, n = 44). While re-running with a tighter segmentation threshold for cell19, nothing in the figure changed at print size (coefficient 0.261, stderr 0.036, n = 54). While auditing the holding potential column for cell15, the CI narrowed by roughly a tenth (coefficient 0.132, stderr 0.037, n = 41).

### Step 32: fitting the one-lag kernel

While fitting the one-lag kernel for cell17, nothing in the figure changed at print size (coefficient 0.119, stderr 0.014, n = 44). While auditing the holding potential column for cell01, nothing in the figure changed at print size (coefficient 0.236, stderr 0.023, n = 53). While segmenting epochs for cell24, the estimate moved less than one standard error (coefficient 0.090, stderr 0.022, n = 50). While checking residual autocorrelation for cell23, the coefficient tracked epoch count more closely than duration (coefficient 0.142, stderr 0.016, n = 38).

While auditing the holding potential column for cell13, the coefficient tracked epoch count more closely than duration (coefficient 0.221, stderr 0.049, n = 58). While comparing per-cell orderings for cell18, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.124, stderr 0.026, n = 43). While checking residual autocorrelation for cell12, the CI narrowed by roughly a tenth (coefficient 0.308, stderr 0.047, n = 45). While segmenting epochs for cell09, the ordering of cells was preserved (coefficient 0.137, stderr 0.048, n = 47). While re-exporting the raw traces for cell15, two cells fell out of the usable range (coefficient 0.182, stderr 0.046, n = 41).

While comparing per-cell orderings for cell18, the CI narrowed by roughly a tenth (coefficient 0.161, stderr 0.020, n = 45). While comparing per-cell orderings for cell17, the CI narrowed by roughly a tenth (coefficient 0.215, stderr 0.036, n = 38). While re-exporting the raw traces for cell13, the coefficient tracked epoch count more closely than duration (coefficient 0.113, stderr 0.017, n = 44).

While checking residual autocorrelation for cell08, the coefficient tracked epoch count more closely than duration (coefficient 0.112, stderr 0.023, n = 46). While comparing per-cell orderings for cell08, the estimate moved less than one standard error (coefficient 0.149, stderr 0.045, n = 42). While auditing the holding potential column for cell22, the ordering of cells was preserved (coefficient 0.157, stderr 0.041, n = 51). While segmenting epochs for cell05, the estimate moved less than one standard error (coefficient 0.150, stderr 0.041, n = 39). While segmenting epochs for cell21, the CI narrowed by roughly a tenth (coefficient 0.093, stderr 0.035, n = 55).

### Step 33: bootstrapping the CI

While auditing the holding potential column for cell16, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.297, stderr 0.023, n = 40). While fitting the one-lag kernel for cell18, the coefficient tracked epoch count more closely than duration (coefficient 0.170, stderr 0.015, n = 40). While fitting the one-lag kernel for cell16, the estimate moved less than one standard error (coefficient 0.189, stderr 0.050, n = 38). While comparing per-cell orderings for cell14, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.290, stderr 0.023, n = 42). While re-running with a tighter segmentation threshold for cell04, the estimate moved less than one standard error (coefficient 0.298, stderr 0.031, n = 56). While checking residual autocorrelation for cell23, two cells fell out of the usable range (coefficient 0.150, stderr 0.034, n = 52).

While comparing per-cell orderings for cell15, two cells fell out of the usable range (coefficient 0.249, stderr 0.034, n = 58). While fitting the one-lag kernel for cell17, nothing in the figure changed at print size (coefficient 0.172, stderr 0.040, n = 51). While comparing per-cell orderings for cell18, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.165, stderr 0.034, n = 41).

While segmenting epochs for cell02, two cells fell out of the usable range (coefficient 0.177, stderr 0.039, n = 48). While fitting the one-lag kernel for cell19, the estimate moved less than one standard error (coefficient 0.273, stderr 0.041, n = 56). While re-exporting the raw traces for cell11, nothing in the figure changed at print size (coefficient 0.083, stderr 0.027, n = 48). While auditing the holding potential column for cell15, nothing in the figure changed at print size (coefficient 0.131, stderr 0.017, n = 50). While re-running with a tighter segmentation threshold for cell02, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.087, stderr 0.050, n = 49).

### Step 34: checking residual autocorrelation

While auditing the holding potential column for cell05, nothing in the figure changed at print size (coefficient 0.200, stderr 0.036, n = 39). While auditing the holding potential column for cell19, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.177, stderr 0.013, n = 41). While re-exporting the raw traces for cell24, the ordering of cells was preserved (coefficient 0.248, stderr 0.048, n = 43). While bootstrapping the CI for cell19, the coefficient tracked epoch count more closely than duration (coefficient 0.305, stderr 0.040, n = 49). While comparing per-cell orderings for cell18, nothing in the figure changed at print size (coefficient 0.246, stderr 0.016, n = 58). While fitting the one-lag kernel for cell14, the ordering of cells was preserved (coefficient 0.132, stderr 0.023, n = 52).

While re-exporting the raw traces for cell15, the CI narrowed by roughly a tenth (coefficient 0.082, stderr 0.025, n = 50). While bootstrapping the CI for cell10, the estimate moved less than one standard error (coefficient 0.151, stderr 0.037, n = 38). While re-exporting the raw traces for cell05, the CI narrowed by roughly a tenth (coefficient 0.107, stderr 0.040, n = 48). While auditing the holding potential column for cell11, nothing in the figure changed at print size (coefficient 0.162, stderr 0.015, n = 57).

```python
coefs = fit_per_cell(rows, threshold=0.35)
lo, hi = ci(coefs, seed=3)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While comparing per-cell orderings for cell23, the estimate moved less than one standard error (coefficient 0.283, stderr 0.048, n = 38). While bootstrapping the CI for cell23, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.288, stderr 0.037, n = 46). While auditing the holding potential column for cell16, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.183, stderr 0.043, n = 46). While re-running with a tighter segmentation threshold for cell09, the ordering of cells was preserved (coefficient 0.307, stderr 0.028, n = 45). While fitting the one-lag kernel for cell17, the estimate moved less than one standard error (coefficient 0.265, stderr 0.045, n = 47). While fitting the one-lag kernel for cell15, nothing in the figure changed at print size (coefficient 0.168, stderr 0.017, n = 48). Noted and moved on; it does not change the decision.

### Step 35: segmenting epochs

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell21    0.183  0.031   0.122  0.243  54        4000
cell22    0.126  0.032   0.062  0.189  49        500
cell12    0.198  0.042   0.116  0.280  52        1000
cell11    0.085  0.032   0.022  0.148  43        1000
cell22    0.307  0.043   0.222  0.392  39        4000
cell03    0.204  0.033   0.139  0.269  58        4000
cell23    0.153  0.022   0.109  0.197  58        500
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell23    0.222  0.028   0.167  0.278  50        2000
cell21    0.270  0.044   0.184  0.356  45        4000
cell01    0.236  0.048   0.141  0.331  53        4000
cell01    0.309  0.036   0.239  0.379  57        500
cell05    0.086  0.040   0.006  0.165  54        1000
cell19    0.278  0.029   0.220  0.335  57        500
cell11    0.297  0.046   0.207  0.386  54        1000
cell20    0.259  0.038   0.185  0.333  56        2000
cell08    0.106  0.041   0.027  0.186  43        1000
```

While auditing the holding potential column for cell02, the ordering of cells was preserved (coefficient 0.089, stderr 0.045, n = 56). While bootstrapping the CI for cell12, nothing in the figure changed at print size (coefficient 0.178, stderr 0.025, n = 48). While auditing the holding potential column for cell03, the ordering of cells was preserved (coefficient 0.111, stderr 0.031, n = 51). While re-exporting the raw traces for cell15, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.112, stderr 0.023, n = 42). Noted and moved on; it does not change the decision.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell24    0.274  0.039   0.198  0.351  47        1000
cell17    0.147  0.025   0.098  0.197  51        4000
cell10    0.286  0.045   0.197  0.374  51        1000
cell02    0.279  0.018   0.243  0.315  54        4000
cell14    0.203  0.048   0.109  0.298  41        2000
cell22    0.123  0.014   0.097  0.150  52        4000
```

### Step 36: segmenting epochs

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell20    0.256  0.019   0.218  0.294  52        2000
cell06    0.230  0.047   0.139  0.321  47        1000
cell09    0.197  0.018   0.161  0.232  56        2000
cell24    0.239  0.027   0.187  0.291  40        2000
cell15    0.084  0.042   0.001  0.166  42        1000
cell14    0.172  0.023   0.127  0.217  49        1000
cell09    0.196  0.035   0.129  0.264  38        2000
```

While checking residual autocorrelation for cell03, the estimate moved less than one standard error (coefficient 0.193, stderr 0.034, n = 51). While comparing per-cell orderings for cell05, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.134, stderr 0.046, n = 55). While fitting the one-lag kernel for cell24, the estimate moved less than one standard error (coefficient 0.197, stderr 0.048, n = 56). This is the part that will need a real statistical argument.

### Step 37: bootstrapping the CI

While comparing per-cell orderings for cell23, the estimate moved less than one standard error (coefficient 0.085, stderr 0.026, n = 52). While re-exporting the raw traces for cell22, two cells fell out of the usable range (coefficient 0.226, stderr 0.016, n = 57). While re-running with a tighter segmentation threshold for cell04, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.196, stderr 0.047, n = 44). While fitting the one-lag kernel for cell01, the ordering of cells was preserved (coefficient 0.121, stderr 0.016, n = 40).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell04    0.273  0.038   0.198  0.348  50        1000
cell15    0.227  0.014   0.199  0.255  39        4000
cell10    0.155  0.020   0.117  0.194  56        2000
cell03    0.189  0.016   0.157  0.221  55        2000
cell21    0.227  0.016   0.195  0.259  52        4000
cell11    0.273  0.039   0.197  0.350  51        2000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell15    0.305  0.032   0.242  0.368  57        500
cell22    0.216  0.020   0.177  0.256  40        2000
cell02    0.174  0.019   0.138  0.211  54        1000
cell05    0.198  0.033   0.133  0.264  42        500
cell15    0.286  0.012   0.262  0.310  54        1000
cell10    0.186  0.040   0.107  0.264  45        4000
cell06    0.083  0.038   0.009  0.157  41        1000
cell17    0.144  0.031   0.083  0.206  43        1000
```

While bootstrapping the CI for cell05, the ordering of cells was preserved (coefficient 0.137, stderr 0.041, n = 38). While segmenting epochs for cell22, the CI narrowed by roughly a tenth (coefficient 0.127, stderr 0.030, n = 57). While comparing per-cell orderings for cell21, the ordering of cells was preserved (coefficient 0.276, stderr 0.038, n = 48).

### Step 38: segmenting epochs

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell15    0.217  0.018   0.182  0.253  54        1000
cell14    0.258  0.024   0.211  0.304  46        4000
cell19    0.237  0.029   0.180  0.294  45        500
cell06    0.212  0.039   0.134  0.289  54        2000
cell20    0.090  0.034   0.022  0.157  46        500
cell12    0.280  0.019   0.244  0.317  53        500
cell11    0.118  0.033   0.053  0.184  55        2000
cell03    0.266  0.039   0.190  0.343  38        4000
cell03    0.240  0.013   0.215  0.265  38        4000
cell21    0.152  0.012   0.128  0.176  45        1000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell14    0.139  0.015   0.110  0.168  58        4000
cell15    0.091  0.033   0.027  0.156  49        1000
cell20    0.254  0.034   0.187  0.321  49        4000
cell04    0.304  0.023   0.258  0.350  42        2000
cell20    0.250  0.042   0.168  0.332  55        2000
cell05    0.153  0.018   0.117  0.188  46        4000
cell03    0.297  0.035   0.227  0.366  50        2000
cell06    0.102  0.030   0.043  0.161  58        1000
cell11    0.130  0.015   0.101  0.159  57        1000
cell03    0.084  0.021   0.041  0.126  45        500
cell10    0.240  0.027   0.188  0.292  56        1000
cell02    0.160  0.041   0.079  0.241  57        4000
```

### Step 39: re-running with a tighter segmentation threshold

While bootstrapping the CI for cell02, the coefficient tracked epoch count more closely than duration (coefficient 0.155, stderr 0.017, n = 53). While fitting the one-lag kernel for cell18, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.155, stderr 0.020, n = 51). While comparing per-cell orderings for cell15, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.198, stderr 0.043, n = 50). Flagging it so it does not get rediscovered next week.

While comparing per-cell orderings for cell14, the ordering of cells was preserved (coefficient 0.126, stderr 0.018, n = 57). While segmenting epochs for cell11, two cells fell out of the usable range (coefficient 0.184, stderr 0.044, n = 45). While re-running with a tighter segmentation threshold for cell14, the coefficient tracked epoch count more closely than duration (coefficient 0.181, stderr 0.036, n = 50). While comparing per-cell orderings for cell01, the coefficient tracked epoch count more closely than duration (coefficient 0.150, stderr 0.035, n = 44).

### Step 40: auditing the holding potential column

While checking residual autocorrelation for cell03, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.265, stderr 0.031, n = 47). While fitting the one-lag kernel for cell21, two cells fell out of the usable range (coefficient 0.234, stderr 0.011, n = 40). While segmenting epochs for cell04, two cells fell out of the usable range (coefficient 0.294, stderr 0.046, n = 46). While segmenting epochs for cell19, the estimate moved less than one standard error (coefficient 0.130, stderr 0.047, n = 52). While re-running with a tighter segmentation threshold for cell24, two cells fell out of the usable range (coefficient 0.217, stderr 0.013, n = 46).

While bootstrapping the CI for cell19, the CI narrowed by roughly a tenth (coefficient 0.094, stderr 0.025, n = 42). While segmenting epochs for cell21, the coefficient tracked epoch count more closely than duration (coefficient 0.213, stderr 0.035, n = 46). While comparing per-cell orderings for cell01, nothing in the figure changed at print size (coefficient 0.084, stderr 0.035, n = 54). While re-running with a tighter segmentation threshold for cell03, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.238, stderr 0.021, n = 38). While fitting the one-lag kernel for cell20, the coefficient tracked epoch count more closely than duration (coefficient 0.106, stderr 0.017, n = 54).

### Step 41: bootstrapping the CI

While bootstrapping the CI for cell21, the ordering of cells was preserved (coefficient 0.205, stderr 0.030, n = 53). While comparing per-cell orderings for cell05, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.109, stderr 0.025, n = 54). While comparing per-cell orderings for cell09, the coefficient tracked epoch count more closely than duration (coefficient 0.248, stderr 0.031, n = 55). While checking residual autocorrelation for cell20, the CI narrowed by roughly a tenth (coefficient 0.261, stderr 0.025, n = 53). While re-running with a tighter segmentation threshold for cell06, the estimate moved less than one standard error (coefficient 0.251, stderr 0.022, n = 39).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell11    0.194  0.012   0.170  0.218  41        2000
cell08    0.276  0.019   0.238  0.314  53        1000
cell16    0.135  0.026   0.084  0.186  55        4000
cell22    0.119  0.020   0.080  0.158  56        1000
cell05    0.233  0.027   0.179  0.286  53        4000
cell24    0.247  0.024   0.200  0.294  53        4000
cell12    0.140  0.036   0.069  0.212  51        1000
cell13    0.248  0.036   0.177  0.319  53        4000
cell23    0.258  0.037   0.186  0.331  45        2000
```

While auditing the holding potential column for cell16, the ordering of cells was preserved (coefficient 0.098, stderr 0.041, n = 47). While comparing per-cell orderings for cell17, nothing in the figure changed at print size (coefficient 0.279, stderr 0.022, n = 55). While checking residual autocorrelation for cell04, nothing in the figure changed at print size (coefficient 0.244, stderr 0.023, n = 55). While auditing the holding potential column for cell12, the estimate moved less than one standard error (coefficient 0.160, stderr 0.017, n = 46). While re-running with a tighter segmentation threshold for cell11, the coefficient tracked epoch count more closely than duration (coefficient 0.090, stderr 0.047, n = 54).

```python
coefs = fit_per_cell(rows, threshold=0.64)
lo, hi = ci(coefs, seed=29)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

