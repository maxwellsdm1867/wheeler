# Prior session 10 of 20

Transcript of an earlier working session on the history-kernel analysis.

### Step 1: checking residual autocorrelation

While auditing the holding potential column for cell04, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.167, stderr 0.023, n = 49). While checking residual autocorrelation for cell17, nothing in the figure changed at print size (coefficient 0.252, stderr 0.044, n = 56). While fitting the one-lag kernel for cell03, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.193, stderr 0.032, n = 44). While auditing the holding potential column for cell19, the CI narrowed by roughly a tenth (coefficient 0.108, stderr 0.045, n = 38). While bootstrapping the CI for cell03, the estimate moved less than one standard error (coefficient 0.201, stderr 0.025, n = 53). While fitting the one-lag kernel for cell17, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.179, stderr 0.032, n = 41). Noted and moved on; it does not change the decision.

While comparing per-cell orderings for cell03, nothing in the figure changed at print size (coefficient 0.157, stderr 0.045, n = 39). While fitting the one-lag kernel for cell03, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.162, stderr 0.037, n = 58). While re-running with a tighter segmentation threshold for cell07, the CI narrowed by roughly a tenth (coefficient 0.229, stderr 0.019, n = 56). While segmenting epochs for cell19, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.306, stderr 0.031, n = 53). While re-running with a tighter segmentation threshold for cell03, the estimate moved less than one standard error (coefficient 0.230, stderr 0.022, n = 50). While re-exporting the raw traces for cell01, the coefficient tracked epoch count more closely than duration (coefficient 0.256, stderr 0.021, n = 38).

While bootstrapping the CI for cell18, the CI narrowed by roughly a tenth (coefficient 0.208, stderr 0.049, n = 45). While checking residual autocorrelation for cell14, nothing in the figure changed at print size (coefficient 0.181, stderr 0.017, n = 48). While bootstrapping the CI for cell06, the estimate moved less than one standard error (coefficient 0.148, stderr 0.016, n = 52). While checking residual autocorrelation for cell06, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.302, stderr 0.022, n = 58). Parking this until the re-segmentation lands.

### Step 2: auditing the holding potential column

While checking residual autocorrelation for cell05, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.199, stderr 0.024, n = 52). While checking residual autocorrelation for cell04, two cells fell out of the usable range (coefficient 0.235, stderr 0.041, n = 44). While fitting the one-lag kernel for cell09, nothing in the figure changed at print size (coefficient 0.144, stderr 0.050, n = 45). While fitting the one-lag kernel for cell06, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.192, stderr 0.050, n = 50). While auditing the holding potential column for cell13, the estimate moved less than one standard error (coefficient 0.138, stderr 0.031, n = 41). While fitting the one-lag kernel for cell13, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.242, stderr 0.024, n = 51). Parking this until the re-segmentation lands.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell12    0.155  0.023   0.110  0.200  53        2000
cell24    0.225  0.039   0.148  0.302  44        500
cell10    0.236  0.036   0.165  0.306  38        500
cell17    0.263  0.012   0.239  0.287  42        4000
cell14    0.100  0.029   0.044  0.156  38        2000
cell08    0.276  0.032   0.214  0.339  45        4000
cell02    0.175  0.028   0.120  0.231  42        4000
cell22    0.252  0.024   0.205  0.300  39        2000
cell04    0.298  0.016   0.267  0.328  57        500
cell14    0.272  0.016   0.241  0.302  47        2000
cell14    0.195  0.016   0.164  0.225  52        4000
cell03    0.217  0.014   0.190  0.245  48        500
cell12    0.130  0.043   0.045  0.214  40        4000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell16    0.295  0.048   0.201  0.390  57        1000
cell11    0.151  0.033   0.087  0.216  51        500
cell14    0.084  0.015   0.055  0.113  41        500
cell12    0.289  0.014   0.261  0.316  45        500
cell21    0.090  0.021   0.049  0.132  55        500
cell16    0.173  0.038   0.098  0.248  46        1000
cell17    0.176  0.047   0.084  0.268  45        4000
cell24    0.178  0.020   0.139  0.217  42        4000
cell18    0.302  0.047   0.209  0.394  56        500
cell18    0.266  0.039   0.190  0.342  50        2000
cell06    0.112  0.046   0.022  0.203  40        1000
```

While auditing the holding potential column for cell24, the ordering of cells was preserved (coefficient 0.111, stderr 0.039, n = 54). While checking residual autocorrelation for cell20, two cells fell out of the usable range (coefficient 0.119, stderr 0.026, n = 57). While re-running with a tighter segmentation threshold for cell19, the estimate moved less than one standard error (coefficient 0.170, stderr 0.012, n = 47). While re-running with a tighter segmentation threshold for cell19, the estimate moved less than one standard error (coefficient 0.122, stderr 0.029, n = 42). This is the part that will need a real statistical argument.

### Step 3: re-running with a tighter segmentation threshold

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell02    0.149  0.021   0.109  0.189  50        1000
cell07    0.237  0.013   0.212  0.263  51        1000
cell18    0.097  0.019   0.060  0.135  50        2000
cell13    0.307  0.034   0.241  0.374  40        500
cell23    0.179  0.031   0.118  0.239  40        1000
cell22    0.272  0.018   0.237  0.307  58        500
cell19    0.117  0.023   0.073  0.161  44        1000
cell06    0.223  0.040   0.144  0.303  52        500
cell01    0.159  0.042   0.077  0.240  54        4000
cell05    0.287  0.010   0.266  0.307  49        500
cell06    0.154  0.028   0.098  0.209  40        500
cell10    0.089  0.036   0.019  0.160  49        4000
cell05    0.264  0.047   0.172  0.356  53        2000
```

While comparing per-cell orderings for cell18, the CI narrowed by roughly a tenth (coefficient 0.121, stderr 0.016, n = 42). While comparing per-cell orderings for cell10, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.279, stderr 0.023, n = 49). While bootstrapping the CI for cell23, the estimate moved less than one standard error (coefficient 0.248, stderr 0.037, n = 38). Flagging it so it does not get rediscovered next week.

### Step 4: checking residual autocorrelation

While checking residual autocorrelation for cell17, the coefficient tracked epoch count more closely than duration (coefficient 0.112, stderr 0.042, n = 48). While comparing per-cell orderings for cell22, the estimate moved less than one standard error (coefficient 0.257, stderr 0.020, n = 43). While re-running with a tighter segmentation threshold for cell04, nothing in the figure changed at print size (coefficient 0.171, stderr 0.041, n = 48). While re-running with a tighter segmentation threshold for cell03, two cells fell out of the usable range (coefficient 0.284, stderr 0.045, n = 50). While re-running with a tighter segmentation threshold for cell24, the estimate moved less than one standard error (coefficient 0.251, stderr 0.033, n = 46).

While comparing per-cell orderings for cell17, the CI narrowed by roughly a tenth (coefficient 0.289, stderr 0.039, n = 39). While auditing the holding potential column for cell24, the estimate moved less than one standard error (coefficient 0.127, stderr 0.039, n = 41). While segmenting epochs for cell08, the CI narrowed by roughly a tenth (coefficient 0.141, stderr 0.038, n = 52). While re-running with a tighter segmentation threshold for cell03, the coefficient tracked epoch count more closely than duration (coefficient 0.087, stderr 0.038, n = 46). While re-exporting the raw traces for cell24, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.100, stderr 0.022, n = 48).

While bootstrapping the CI for cell01, nothing in the figure changed at print size (coefficient 0.307, stderr 0.049, n = 53). While auditing the holding potential column for cell21, nothing in the figure changed at print size (coefficient 0.245, stderr 0.049, n = 50). While checking residual autocorrelation for cell06, the ordering of cells was preserved (coefficient 0.308, stderr 0.045, n = 56). While auditing the holding potential column for cell17, two cells fell out of the usable range (coefficient 0.301, stderr 0.033, n = 43). While bootstrapping the CI for cell23, the estimate moved less than one standard error (coefficient 0.178, stderr 0.031, n = 55). This is the part that will need a real statistical argument.

While checking residual autocorrelation for cell03, the CI narrowed by roughly a tenth (coefficient 0.135, stderr 0.018, n = 51). While bootstrapping the CI for cell14, nothing in the figure changed at print size (coefficient 0.089, stderr 0.014, n = 55). While auditing the holding potential column for cell02, the ordering of cells was preserved (coefficient 0.153, stderr 0.044, n = 53). While re-running with a tighter segmentation threshold for cell15, the coefficient tracked epoch count more closely than duration (coefficient 0.300, stderr 0.031, n = 57). While fitting the one-lag kernel for cell04, the ordering of cells was preserved (coefficient 0.235, stderr 0.045, n = 47). Flagging it so it does not get rediscovered next week.

### Step 5: re-running with a tighter segmentation threshold

While re-exporting the raw traces for cell14, two cells fell out of the usable range (coefficient 0.178, stderr 0.040, n = 57). While re-running with a tighter segmentation threshold for cell02, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.205, stderr 0.036, n = 54). While segmenting epochs for cell21, the estimate moved less than one standard error (coefficient 0.101, stderr 0.026, n = 57). While fitting the one-lag kernel for cell09, the coefficient tracked epoch count more closely than duration (coefficient 0.244, stderr 0.027, n = 40). While re-exporting the raw traces for cell16, nothing in the figure changed at print size (coefficient 0.259, stderr 0.035, n = 42).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell09    0.081  0.019   0.043  0.118  48        2000
cell11    0.097  0.039   0.022  0.173  47        4000
cell04    0.124  0.033   0.060  0.188  38        2000
cell21    0.254  0.032   0.191  0.316  47        500
cell01    0.153  0.044   0.067  0.239  54        2000
cell19    0.090  0.012   0.066  0.113  54        500
cell23    0.213  0.043   0.129  0.297  47        500
cell20    0.228  0.034   0.161  0.296  43        2000
cell13    0.112  0.049   0.017  0.207  54        500
cell12    0.170  0.011   0.147  0.192  44        500
cell13    0.173  0.023   0.128  0.217  44        1000
cell08    0.095  0.014   0.068  0.122  43        4000
cell03    0.297  0.014   0.270  0.325  46        500
cell02    0.090  0.029   0.032  0.148  41        2000
```

While auditing the holding potential column for cell20, the coefficient tracked epoch count more closely than duration (coefficient 0.175, stderr 0.039, n = 38). While segmenting epochs for cell09, two cells fell out of the usable range (coefficient 0.256, stderr 0.013, n = 45). While fitting the one-lag kernel for cell09, the ordering of cells was preserved (coefficient 0.200, stderr 0.034, n = 52). While re-running with a tighter segmentation threshold for cell18, the estimate moved less than one standard error (coefficient 0.195, stderr 0.026, n = 54). While re-exporting the raw traces for cell06, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.182, stderr 0.013, n = 49). Parking this until the re-segmentation lands.

While bootstrapping the CI for cell10, nothing in the figure changed at print size (coefficient 0.087, stderr 0.044, n = 41). While bootstrapping the CI for cell16, nothing in the figure changed at print size (coefficient 0.161, stderr 0.049, n = 48). While re-exporting the raw traces for cell19, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.226, stderr 0.048, n = 42). While checking residual autocorrelation for cell04, two cells fell out of the usable range (coefficient 0.254, stderr 0.021, n = 41). While re-running with a tighter segmentation threshold for cell11, the estimate moved less than one standard error (coefficient 0.132, stderr 0.043, n = 49).

### Step 6: checking residual autocorrelation

While checking residual autocorrelation for cell22, nothing in the figure changed at print size (coefficient 0.086, stderr 0.045, n = 49). While re-exporting the raw traces for cell08, the estimate moved less than one standard error (coefficient 0.209, stderr 0.030, n = 57). While re-exporting the raw traces for cell22, nothing in the figure changed at print size (coefficient 0.305, stderr 0.023, n = 44). While re-running with a tighter segmentation threshold for cell03, the estimate moved less than one standard error (coefficient 0.130, stderr 0.024, n = 42). While segmenting epochs for cell22, the estimate moved less than one standard error (coefficient 0.305, stderr 0.024, n = 50). Worth noting for the writeup, though not a result on its own.

While checking residual autocorrelation for cell16, the ordering of cells was preserved (coefficient 0.297, stderr 0.025, n = 58). While auditing the holding potential column for cell07, the estimate moved less than one standard error (coefficient 0.142, stderr 0.013, n = 40). While comparing per-cell orderings for cell02, nothing in the figure changed at print size (coefficient 0.099, stderr 0.024, n = 45). While re-exporting the raw traces for cell15, the ordering of cells was preserved (coefficient 0.241, stderr 0.032, n = 40). While bootstrapping the CI for cell01, the ordering of cells was preserved (coefficient 0.195, stderr 0.044, n = 38). While re-running with a tighter segmentation threshold for cell08, the CI narrowed by roughly a tenth (coefficient 0.090, stderr 0.025, n = 50).

While auditing the holding potential column for cell24, the CI narrowed by roughly a tenth (coefficient 0.251, stderr 0.020, n = 54). While segmenting epochs for cell24, nothing in the figure changed at print size (coefficient 0.087, stderr 0.031, n = 57). While bootstrapping the CI for cell24, the CI narrowed by roughly a tenth (coefficient 0.207, stderr 0.047, n = 41). Worth noting for the writeup, though not a result on its own.

While segmenting epochs for cell02, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.285, stderr 0.033, n = 50). While checking residual autocorrelation for cell21, nothing in the figure changed at print size (coefficient 0.288, stderr 0.021, n = 49). While bootstrapping the CI for cell12, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.288, stderr 0.035, n = 44). While re-running with a tighter segmentation threshold for cell12, the coefficient tracked epoch count more closely than duration (coefficient 0.231, stderr 0.039, n = 51). While re-running with a tighter segmentation threshold for cell05, nothing in the figure changed at print size (coefficient 0.171, stderr 0.046, n = 55). This is the part that will need a real statistical argument.

### Step 7: re-exporting the raw traces

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell11    0.276  0.038   0.202  0.350  38        1000
cell01    0.262  0.029   0.205  0.319  45        500
cell19    0.091  0.025   0.042  0.140  39        2000
cell22    0.190  0.013   0.164  0.216  45        500
cell17    0.231  0.022   0.187  0.274  52        500
cell10    0.237  0.015   0.208  0.267  48        4000
cell01    0.219  0.030   0.160  0.279  46        1000
```

While re-exporting the raw traces for cell02, the estimate moved less than one standard error (coefficient 0.210, stderr 0.025, n = 58). While auditing the holding potential column for cell18, the estimate moved less than one standard error (coefficient 0.300, stderr 0.023, n = 42). While re-running with a tighter segmentation threshold for cell15, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.142, stderr 0.018, n = 42). While re-running with a tighter segmentation threshold for cell24, the ordering of cells was preserved (coefficient 0.142, stderr 0.038, n = 53). While segmenting epochs for cell09, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.162, stderr 0.012, n = 56).

```python
coefs = fit_per_cell(rows, threshold=0.76)
lo, hi = ci(coefs, seed=70)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While checking residual autocorrelation for cell11, the ordering of cells was preserved (coefficient 0.107, stderr 0.036, n = 47). While checking residual autocorrelation for cell21, the CI narrowed by roughly a tenth (coefficient 0.123, stderr 0.010, n = 47). While segmenting epochs for cell02, the estimate moved less than one standard error (coefficient 0.081, stderr 0.049, n = 40). While auditing the holding potential column for cell22, the ordering of cells was preserved (coefficient 0.214, stderr 0.031, n = 46). Noted and moved on; it does not change the decision.

### Step 8: fitting the one-lag kernel

While segmenting epochs for cell20, the estimate moved less than one standard error (coefficient 0.262, stderr 0.040, n = 48). While checking residual autocorrelation for cell21, the coefficient tracked epoch count more closely than duration (coefficient 0.086, stderr 0.027, n = 55). While checking residual autocorrelation for cell11, two cells fell out of the usable range (coefficient 0.271, stderr 0.028, n = 47).

While fitting the one-lag kernel for cell22, nothing in the figure changed at print size (coefficient 0.291, stderr 0.025, n = 49). While re-running with a tighter segmentation threshold for cell12, the estimate moved less than one standard error (coefficient 0.223, stderr 0.025, n = 47). While checking residual autocorrelation for cell02, the estimate moved less than one standard error (coefficient 0.193, stderr 0.048, n = 48).

### Step 9: auditing the holding potential column

While re-exporting the raw traces for cell21, the CI narrowed by roughly a tenth (coefficient 0.154, stderr 0.023, n = 52). While checking residual autocorrelation for cell23, nothing in the figure changed at print size (coefficient 0.122, stderr 0.018, n = 41). While segmenting epochs for cell18, the ordering of cells was preserved (coefficient 0.170, stderr 0.010, n = 50).

While bootstrapping the CI for cell13, the ordering of cells was preserved (coefficient 0.235, stderr 0.050, n = 50). While fitting the one-lag kernel for cell08, nothing in the figure changed at print size (coefficient 0.254, stderr 0.017, n = 45). While comparing per-cell orderings for cell06, nothing in the figure changed at print size (coefficient 0.286, stderr 0.014, n = 49). While re-exporting the raw traces for cell05, the CI narrowed by roughly a tenth (coefficient 0.303, stderr 0.030, n = 42). While bootstrapping the CI for cell01, two cells fell out of the usable range (coefficient 0.210, stderr 0.016, n = 55). While re-exporting the raw traces for cell03, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.222, stderr 0.014, n = 53).

### Step 10: comparing per-cell orderings

```python
coefs = fit_per_cell(rows, threshold=0.75)
lo, hi = ci(coefs, seed=24)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell14    0.130  0.025   0.081  0.179  39        2000
cell20    0.141  0.013   0.116  0.166  53        4000
cell17    0.154  0.034   0.087  0.222  54        4000
cell16    0.260  0.034   0.193  0.326  51        1000
cell19    0.133  0.049   0.037  0.229  57        4000
cell12    0.258  0.039   0.181  0.335  54        1000
cell06    0.162  0.028   0.107  0.217  49        1000
cell03    0.240  0.017   0.208  0.273  45        2000
cell18    0.302  0.022   0.258  0.345  39        1000
cell24    0.145  0.018   0.110  0.181  47        4000
cell18    0.279  0.019   0.242  0.316  50        4000
cell08    0.191  0.033   0.126  0.256  53        500
```

While re-running with a tighter segmentation threshold for cell24, the coefficient tracked epoch count more closely than duration (coefficient 0.179, stderr 0.045, n = 51). While re-running with a tighter segmentation threshold for cell03, the estimate moved less than one standard error (coefficient 0.187, stderr 0.021, n = 47). While checking residual autocorrelation for cell02, the ordering of cells was preserved (coefficient 0.161, stderr 0.047, n = 56). While re-running with a tighter segmentation threshold for cell13, two cells fell out of the usable range (coefficient 0.159, stderr 0.026, n = 44). While auditing the holding potential column for cell08, the coefficient tracked epoch count more closely than duration (coefficient 0.183, stderr 0.012, n = 53).

While checking residual autocorrelation for cell08, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.252, stderr 0.025, n = 56). While bootstrapping the CI for cell23, the ordering of cells was preserved (coefficient 0.183, stderr 0.029, n = 42). While re-running with a tighter segmentation threshold for cell19, two cells fell out of the usable range (coefficient 0.095, stderr 0.037, n = 57).

### Step 11: comparing per-cell orderings

```python
coefs = fit_per_cell(rows, threshold=0.78)
lo, hi = ci(coefs, seed=76)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While fitting the one-lag kernel for cell02, two cells fell out of the usable range (coefficient 0.263, stderr 0.031, n = 52). While re-running with a tighter segmentation threshold for cell06, the CI narrowed by roughly a tenth (coefficient 0.107, stderr 0.019, n = 50). While re-running with a tighter segmentation threshold for cell10, two cells fell out of the usable range (coefficient 0.264, stderr 0.037, n = 47). While segmenting epochs for cell15, the coefficient tracked epoch count more closely than duration (coefficient 0.164, stderr 0.020, n = 56). While checking residual autocorrelation for cell06, the estimate moved less than one standard error (coefficient 0.119, stderr 0.042, n = 50). This is the part that will need a real statistical argument.

While comparing per-cell orderings for cell02, nothing in the figure changed at print size (coefficient 0.173, stderr 0.039, n = 50). While segmenting epochs for cell20, nothing in the figure changed at print size (coefficient 0.225, stderr 0.026, n = 38). While bootstrapping the CI for cell22, two cells fell out of the usable range (coefficient 0.269, stderr 0.041, n = 39). While re-exporting the raw traces for cell15, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.192, stderr 0.022, n = 39).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell12    0.295  0.041   0.214  0.375  49        1000
cell14    0.090  0.032   0.027  0.154  53        500
cell19    0.285  0.014   0.257  0.313  40        1000
cell10    0.175  0.011   0.154  0.197  49        2000
cell01    0.157  0.012   0.135  0.180  39        500
cell12    0.216  0.041   0.136  0.296  45        4000
cell13    0.195  0.022   0.152  0.239  46        500
cell23    0.164  0.021   0.123  0.205  47        500
cell22    0.201  0.046   0.111  0.291  57        500
```

### Step 12: auditing the holding potential column

While re-exporting the raw traces for cell10, the ordering of cells was preserved (coefficient 0.103, stderr 0.024, n = 51). While re-exporting the raw traces for cell06, nothing in the figure changed at print size (coefficient 0.109, stderr 0.047, n = 51). While checking residual autocorrelation for cell24, the CI narrowed by roughly a tenth (coefficient 0.231, stderr 0.024, n = 39). While checking residual autocorrelation for cell08, nothing in the figure changed at print size (coefficient 0.190, stderr 0.047, n = 38). While auditing the holding potential column for cell19, the CI narrowed by roughly a tenth (coefficient 0.120, stderr 0.016, n = 57). Parking this until the re-segmentation lands.

While checking residual autocorrelation for cell19, nothing in the figure changed at print size (coefficient 0.081, stderr 0.018, n = 55). While segmenting epochs for cell24, the coefficient tracked epoch count more closely than duration (coefficient 0.185, stderr 0.016, n = 48). While fitting the one-lag kernel for cell23, the ordering of cells was preserved (coefficient 0.241, stderr 0.038, n = 40). While comparing per-cell orderings for cell08, the CI narrowed by roughly a tenth (coefficient 0.119, stderr 0.012, n = 53).

### Step 13: bootstrapping the CI

```python
coefs = fit_per_cell(rows, threshold=0.79)
lo, hi = ci(coefs, seed=67)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```python
coefs = fit_per_cell(rows, threshold=0.53)
lo, hi = ci(coefs, seed=39)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell09    0.134  0.028   0.079  0.190  39        500
cell01    0.228  0.028   0.173  0.283  46        4000
cell24    0.150  0.018   0.115  0.185  58        4000
cell19    0.303  0.035   0.235  0.371  46        2000
cell19    0.127  0.030   0.068  0.186  57        1000
cell22    0.237  0.018   0.201  0.273  53        4000
cell14    0.293  0.044   0.207  0.379  46        4000
cell09    0.279  0.022   0.235  0.322  40        2000
cell21    0.133  0.040   0.054  0.212  58        500
cell20    0.238  0.011   0.215  0.260  45        500
cell09    0.286  0.034   0.219  0.352  54        1000
cell04    0.082  0.024   0.036  0.129  53        1000
cell08    0.178  0.020   0.138  0.217  52        1000
cell19    0.156  0.043   0.072  0.239  47        1000
```

While fitting the one-lag kernel for cell21, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.249, stderr 0.034, n = 49). While checking residual autocorrelation for cell24, nothing in the figure changed at print size (coefficient 0.119, stderr 0.042, n = 48). While fitting the one-lag kernel for cell19, the estimate moved less than one standard error (coefficient 0.212, stderr 0.034, n = 52).

### Step 14: bootstrapping the CI

While segmenting epochs for cell01, the coefficient tracked epoch count more closely than duration (coefficient 0.306, stderr 0.045, n = 50). While re-running with a tighter segmentation threshold for cell11, the coefficient tracked epoch count more closely than duration (coefficient 0.240, stderr 0.024, n = 50). While segmenting epochs for cell23, nothing in the figure changed at print size (coefficient 0.294, stderr 0.028, n = 57). While checking residual autocorrelation for cell18, nothing in the figure changed at print size (coefficient 0.122, stderr 0.031, n = 44). While checking residual autocorrelation for cell02, the coefficient tracked epoch count more closely than duration (coefficient 0.128, stderr 0.011, n = 43). While checking residual autocorrelation for cell19, nothing in the figure changed at print size (coefficient 0.262, stderr 0.016, n = 47).

While fitting the one-lag kernel for cell20, two cells fell out of the usable range (coefficient 0.101, stderr 0.044, n = 57). While re-exporting the raw traces for cell10, the CI narrowed by roughly a tenth (coefficient 0.283, stderr 0.029, n = 51). While auditing the holding potential column for cell13, the estimate moved less than one standard error (coefficient 0.164, stderr 0.016, n = 56). While bootstrapping the CI for cell10, the CI narrowed by roughly a tenth (coefficient 0.238, stderr 0.036, n = 38).

### Step 15: segmenting epochs

While comparing per-cell orderings for cell23, the estimate moved less than one standard error (coefficient 0.259, stderr 0.014, n = 55). While comparing per-cell orderings for cell04, two cells fell out of the usable range (coefficient 0.277, stderr 0.045, n = 44). While segmenting epochs for cell20, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.101, stderr 0.020, n = 55). While fitting the one-lag kernel for cell12, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.150, stderr 0.032, n = 45). While re-exporting the raw traces for cell11, the estimate moved less than one standard error (coefficient 0.264, stderr 0.050, n = 44).

While fitting the one-lag kernel for cell21, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.085, stderr 0.048, n = 42). While bootstrapping the CI for cell06, two cells fell out of the usable range (coefficient 0.180, stderr 0.021, n = 41). While auditing the holding potential column for cell13, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.182, stderr 0.015, n = 38). While bootstrapping the CI for cell02, two cells fell out of the usable range (coefficient 0.266, stderr 0.041, n = 41). While checking residual autocorrelation for cell24, two cells fell out of the usable range (coefficient 0.294, stderr 0.032, n = 48). While bootstrapping the CI for cell20, the estimate moved less than one standard error (coefficient 0.134, stderr 0.045, n = 45). This is the part that will need a real statistical argument.

### Step 16: fitting the one-lag kernel

While bootstrapping the CI for cell17, the coefficient tracked epoch count more closely than duration (coefficient 0.134, stderr 0.018, n = 42). While bootstrapping the CI for cell16, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.301, stderr 0.045, n = 55). While checking residual autocorrelation for cell01, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.160, stderr 0.038, n = 47). While re-exporting the raw traces for cell08, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.133, stderr 0.031, n = 41). While auditing the holding potential column for cell18, the CI narrowed by roughly a tenth (coefficient 0.264, stderr 0.034, n = 43). While comparing per-cell orderings for cell15, the coefficient tracked epoch count more closely than duration (coefficient 0.304, stderr 0.019, n = 38). Worth noting for the writeup, though not a result on its own.

While re-exporting the raw traces for cell09, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.127, stderr 0.013, n = 58). While fitting the one-lag kernel for cell02, two cells fell out of the usable range (coefficient 0.215, stderr 0.045, n = 55). While re-exporting the raw traces for cell05, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.308, stderr 0.021, n = 58). While segmenting epochs for cell04, the CI narrowed by roughly a tenth (coefficient 0.288, stderr 0.023, n = 49).

### Step 17: segmenting epochs

While comparing per-cell orderings for cell22, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.286, stderr 0.037, n = 38). While re-exporting the raw traces for cell23, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.254, stderr 0.047, n = 49). While checking residual autocorrelation for cell21, two cells fell out of the usable range (coefficient 0.224, stderr 0.036, n = 45). Parking this until the re-segmentation lands.

While fitting the one-lag kernel for cell10, the estimate moved less than one standard error (coefficient 0.252, stderr 0.027, n = 57). While re-running with a tighter segmentation threshold for cell19, the ordering of cells was preserved (coefficient 0.156, stderr 0.049, n = 51). While segmenting epochs for cell24, two cells fell out of the usable range (coefficient 0.136, stderr 0.017, n = 39). While bootstrapping the CI for cell20, the ordering of cells was preserved (coefficient 0.092, stderr 0.023, n = 44). While auditing the holding potential column for cell22, the coefficient tracked epoch count more closely than duration (coefficient 0.188, stderr 0.015, n = 52). While bootstrapping the CI for cell15, the coefficient tracked epoch count more closely than duration (coefficient 0.153, stderr 0.024, n = 54).

While auditing the holding potential column for cell16, the ordering of cells was preserved (coefficient 0.306, stderr 0.020, n = 54). While segmenting epochs for cell04, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.081, stderr 0.017, n = 49). While bootstrapping the CI for cell16, the CI narrowed by roughly a tenth (coefficient 0.164, stderr 0.023, n = 46). While fitting the one-lag kernel for cell03, the ordering of cells was preserved (coefficient 0.157, stderr 0.042, n = 53).

### Step 18: re-running with a tighter segmentation threshold

While re-exporting the raw traces for cell24, the coefficient tracked epoch count more closely than duration (coefficient 0.250, stderr 0.034, n = 57). While segmenting epochs for cell20, two cells fell out of the usable range (coefficient 0.091, stderr 0.012, n = 45). While segmenting epochs for cell06, the estimate moved less than one standard error (coefficient 0.247, stderr 0.028, n = 38). While bootstrapping the CI for cell19, nothing in the figure changed at print size (coefficient 0.292, stderr 0.026, n = 43). While auditing the holding potential column for cell21, nothing in the figure changed at print size (coefficient 0.172, stderr 0.043, n = 50). While re-running with a tighter segmentation threshold for cell07, two cells fell out of the usable range (coefficient 0.278, stderr 0.037, n = 46).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell17    0.212  0.022   0.170  0.255  55        2000
cell20    0.122  0.025   0.072  0.172  57        4000
cell05    0.212  0.050   0.114  0.309  57        4000
cell12    0.289  0.034   0.222  0.357  47        2000
cell19    0.110  0.017   0.076  0.145  41        2000
cell23    0.194  0.045   0.106  0.282  58        2000
cell07    0.268  0.050   0.171  0.366  50        2000
cell07    0.297  0.045   0.209  0.386  42        500
cell16    0.230  0.017   0.197  0.263  57        4000
cell18    0.135  0.020   0.096  0.175  57        4000
cell04    0.176  0.025   0.127  0.225  41        4000
cell24    0.248  0.014   0.220  0.276  44        4000
cell14    0.180  0.043   0.096  0.264  49        2000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell09    0.212  0.044   0.125  0.299  51        500
cell20    0.154  0.040   0.076  0.232  52        2000
cell17    0.098  0.024   0.052  0.144  53        500
cell09    0.223  0.029   0.166  0.281  50        500
cell15    0.171  0.039   0.095  0.248  56        1000
cell10    0.099  0.037   0.026  0.171  57        4000
cell04    0.080  0.024   0.034  0.126  38        4000
cell22    0.082  0.045   -0.005  0.170  41        4000
```

### Step 19: re-exporting the raw traces

```python
coefs = fit_per_cell(rows, threshold=0.71)
lo, hi = ci(coefs, seed=63)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```python
coefs = fit_per_cell(rows, threshold=0.78)
lo, hi = ci(coefs, seed=95)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```python
coefs = fit_per_cell(rows, threshold=0.65)
lo, hi = ci(coefs, seed=42)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While checking residual autocorrelation for cell07, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.141, stderr 0.042, n = 45). While fitting the one-lag kernel for cell16, the ordering of cells was preserved (coefficient 0.190, stderr 0.023, n = 47). While fitting the one-lag kernel for cell22, the coefficient tracked epoch count more closely than duration (coefficient 0.284, stderr 0.035, n = 41). While comparing per-cell orderings for cell18, the coefficient tracked epoch count more closely than duration (coefficient 0.137, stderr 0.024, n = 55). While fitting the one-lag kernel for cell05, nothing in the figure changed at print size (coefficient 0.114, stderr 0.013, n = 53). While re-exporting the raw traces for cell19, nothing in the figure changed at print size (coefficient 0.141, stderr 0.037, n = 56). This is the part that will need a real statistical argument.

### Step 20: comparing per-cell orderings

```python
coefs = fit_per_cell(rows, threshold=0.77)
lo, hi = ci(coefs, seed=72)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While fitting the one-lag kernel for cell04, nothing in the figure changed at print size (coefficient 0.132, stderr 0.035, n = 47). While bootstrapping the CI for cell03, nothing in the figure changed at print size (coefficient 0.128, stderr 0.037, n = 46). While re-exporting the raw traces for cell06, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.275, stderr 0.016, n = 42). While fitting the one-lag kernel for cell03, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.270, stderr 0.030, n = 45). While checking residual autocorrelation for cell13, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.244, stderr 0.020, n = 48). Parking this until the re-segmentation lands.

### Step 21: fitting the one-lag kernel

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell05    0.271  0.011   0.249  0.293  51        1000
cell11    0.239  0.018   0.204  0.273  46        4000
cell22    0.244  0.028   0.190  0.298  58        1000
cell21    0.108  0.041   0.027  0.189  54        4000
cell07    0.145  0.032   0.084  0.207  42        1000
cell16    0.115  0.042   0.033  0.197  51        1000
cell07    0.081  0.041   0.001  0.161  48        500
cell06    0.202  0.032   0.139  0.266  43        1000
cell22    0.197  0.031   0.137  0.258  50        2000
cell03    0.266  0.027   0.213  0.318  44        500
```

```python
coefs = fit_per_cell(rows, threshold=0.52)
lo, hi = ci(coefs, seed=29)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 22: bootstrapping the CI

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell04    0.179  0.018   0.144  0.214  42        2000
cell15    0.217  0.018   0.181  0.253  43        500
cell20    0.306  0.032   0.242  0.369  45        500
cell11    0.113  0.050   0.015  0.211  45        1000
cell09    0.205  0.014   0.179  0.232  52        1000
cell16    0.213  0.020   0.174  0.252  49        500
cell20    0.278  0.026   0.227  0.328  54        2000
cell11    0.227  0.045   0.138  0.315  40        1000
cell11    0.287  0.037   0.214  0.360  47        500
cell09    0.250  0.034   0.183  0.317  57        1000
cell18    0.301  0.021   0.259  0.342  57        1000
```

While bootstrapping the CI for cell23, nothing in the figure changed at print size (coefficient 0.124, stderr 0.014, n = 56). While re-running with a tighter segmentation threshold for cell20, the ordering of cells was preserved (coefficient 0.156, stderr 0.026, n = 54). While checking residual autocorrelation for cell01, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.193, stderr 0.015, n = 45). While auditing the holding potential column for cell09, two cells fell out of the usable range (coefficient 0.214, stderr 0.033, n = 49). While checking residual autocorrelation for cell15, nothing in the figure changed at print size (coefficient 0.273, stderr 0.040, n = 52). While re-exporting the raw traces for cell14, the estimate moved less than one standard error (coefficient 0.169, stderr 0.027, n = 38).

### Step 23: fitting the one-lag kernel

While bootstrapping the CI for cell10, the estimate moved less than one standard error (coefficient 0.111, stderr 0.035, n = 43). While checking residual autocorrelation for cell01, nothing in the figure changed at print size (coefficient 0.088, stderr 0.048, n = 44). While re-exporting the raw traces for cell04, the CI narrowed by roughly a tenth (coefficient 0.106, stderr 0.037, n = 43). This is the part that will need a real statistical argument.

While auditing the holding potential column for cell03, nothing in the figure changed at print size (coefficient 0.228, stderr 0.022, n = 38). While re-exporting the raw traces for cell20, the ordering of cells was preserved (coefficient 0.220, stderr 0.049, n = 57). While re-running with a tighter segmentation threshold for cell16, the CI narrowed by roughly a tenth (coefficient 0.183, stderr 0.017, n = 46). While segmenting epochs for cell15, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.207, stderr 0.036, n = 41). Parking this until the re-segmentation lands.

While re-exporting the raw traces for cell04, the coefficient tracked epoch count more closely than duration (coefficient 0.256, stderr 0.044, n = 49). While fitting the one-lag kernel for cell23, the ordering of cells was preserved (coefficient 0.203, stderr 0.045, n = 39). While fitting the one-lag kernel for cell18, the estimate moved less than one standard error (coefficient 0.272, stderr 0.031, n = 43). While auditing the holding potential column for cell23, the ordering of cells was preserved (coefficient 0.213, stderr 0.024, n = 57). Noted and moved on; it does not change the decision.

While comparing per-cell orderings for cell14, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.307, stderr 0.043, n = 41). While re-running with a tighter segmentation threshold for cell18, two cells fell out of the usable range (coefficient 0.182, stderr 0.033, n = 40). While fitting the one-lag kernel for cell03, the CI narrowed by roughly a tenth (coefficient 0.178, stderr 0.012, n = 52). While re-running with a tighter segmentation threshold for cell11, two cells fell out of the usable range (coefficient 0.293, stderr 0.017, n = 58).

### Step 24: re-running with a tighter segmentation threshold

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell04    0.103  0.037   0.030  0.176  58        4000
cell05    0.121  0.016   0.089  0.154  50        2000
cell02    0.196  0.044   0.111  0.282  43        1000
cell19    0.194  0.029   0.138  0.250  46        2000
cell07    0.243  0.014   0.215  0.271  46        1000
cell20    0.149  0.017   0.116  0.182  40        4000
cell02    0.113  0.017   0.079  0.147  40        1000
cell03    0.084  0.012   0.060  0.108  53        500
cell11    0.093  0.012   0.069  0.118  47        2000
cell12    0.161  0.045   0.074  0.249  45        2000
```

While segmenting epochs for cell06, nothing in the figure changed at print size (coefficient 0.085, stderr 0.020, n = 49). While auditing the holding potential column for cell17, the estimate moved less than one standard error (coefficient 0.178, stderr 0.042, n = 46). While comparing per-cell orderings for cell17, nothing in the figure changed at print size (coefficient 0.119, stderr 0.014, n = 53). While fitting the one-lag kernel for cell20, the coefficient tracked epoch count more closely than duration (coefficient 0.271, stderr 0.022, n = 55). Flagging it so it does not get rediscovered next week.

While checking residual autocorrelation for cell17, two cells fell out of the usable range (coefficient 0.084, stderr 0.050, n = 40). While comparing per-cell orderings for cell11, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.263, stderr 0.050, n = 45). While segmenting epochs for cell09, two cells fell out of the usable range (coefficient 0.247, stderr 0.048, n = 54). While fitting the one-lag kernel for cell11, the CI narrowed by roughly a tenth (coefficient 0.127, stderr 0.040, n = 40). This is the part that will need a real statistical argument.

### Step 25: re-running with a tighter segmentation threshold

While segmenting epochs for cell10, nothing in the figure changed at print size (coefficient 0.186, stderr 0.039, n = 39). While bootstrapping the CI for cell19, the CI narrowed by roughly a tenth (coefficient 0.151, stderr 0.022, n = 38). While re-exporting the raw traces for cell22, the estimate moved less than one standard error (coefficient 0.133, stderr 0.010, n = 53). While checking residual autocorrelation for cell19, the ordering of cells was preserved (coefficient 0.299, stderr 0.033, n = 53). Parking this until the re-segmentation lands.

While auditing the holding potential column for cell04, the ordering of cells was preserved (coefficient 0.160, stderr 0.036, n = 52). While bootstrapping the CI for cell15, the coefficient tracked epoch count more closely than duration (coefficient 0.259, stderr 0.024, n = 55). While re-running with a tighter segmentation threshold for cell05, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.300, stderr 0.015, n = 50). While auditing the holding potential column for cell20, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.274, stderr 0.044, n = 45). While re-running with a tighter segmentation threshold for cell22, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.235, stderr 0.032, n = 50). Noted and moved on; it does not change the decision.

```python
coefs = fit_per_cell(rows, threshold=0.65)
lo, hi = ci(coefs, seed=88)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 26: fitting the one-lag kernel

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell13    0.308  0.026   0.258  0.358  58        4000
cell12    0.226  0.022   0.183  0.270  42        4000
cell24    0.111  0.043   0.028  0.195  56        1000
cell12    0.134  0.039   0.058  0.210  50        2000
cell22    0.291  0.046   0.201  0.381  41        500
cell23    0.128  0.026   0.077  0.180  39        4000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell14    0.138  0.014   0.111  0.165  57        2000
cell03    0.179  0.030   0.120  0.239  58        1000
cell03    0.103  0.029   0.047  0.159  43        4000
cell19    0.180  0.044   0.094  0.266  44        2000
cell13    0.114  0.024   0.067  0.162  44        2000
cell18    0.155  0.033   0.090  0.219  46        2000
cell01    0.127  0.032   0.064  0.189  46        4000
cell04    0.177  0.019   0.140  0.215  41        2000
```

While bootstrapping the CI for cell16, the ordering of cells was preserved (coefficient 0.122, stderr 0.043, n = 45). While fitting the one-lag kernel for cell01, the coefficient tracked epoch count more closely than duration (coefficient 0.212, stderr 0.020, n = 54). While comparing per-cell orderings for cell09, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.266, stderr 0.035, n = 52). While checking residual autocorrelation for cell16, the estimate moved less than one standard error (coefficient 0.194, stderr 0.036, n = 47). While auditing the holding potential column for cell07, the ordering of cells was preserved (coefficient 0.099, stderr 0.041, n = 45). Worth noting for the writeup, though not a result on its own.

### Step 27: fitting the one-lag kernel

While re-running with a tighter segmentation threshold for cell13, the coefficient tracked epoch count more closely than duration (coefficient 0.277, stderr 0.030, n = 56). While comparing per-cell orderings for cell02, nothing in the figure changed at print size (coefficient 0.110, stderr 0.024, n = 43). While segmenting epochs for cell11, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.278, stderr 0.019, n = 47). While re-exporting the raw traces for cell02, the ordering of cells was preserved (coefficient 0.117, stderr 0.040, n = 41).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell14    0.262  0.019   0.224  0.300  41        1000
cell02    0.118  0.044   0.032  0.204  56        1000
cell04    0.090  0.029   0.032  0.148  42        2000
cell08    0.272  0.034   0.206  0.338  58        2000
cell20    0.248  0.026   0.198  0.298  56        2000
cell23    0.208  0.014   0.181  0.235  44        2000
cell05    0.156  0.021   0.115  0.197  41        2000
cell11    0.222  0.033   0.158  0.286  53        500
cell21    0.248  0.025   0.198  0.298  56        1000
cell04    0.231  0.036   0.160  0.301  43        1000
cell21    0.156  0.014   0.129  0.184  47        500
```

### Step 28: comparing per-cell orderings

While fitting the one-lag kernel for cell06, nothing in the figure changed at print size (coefficient 0.085, stderr 0.018, n = 54). While auditing the holding potential column for cell03, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.211, stderr 0.045, n = 49). While bootstrapping the CI for cell02, two cells fell out of the usable range (coefficient 0.291, stderr 0.046, n = 54). While auditing the holding potential column for cell02, nothing in the figure changed at print size (coefficient 0.257, stderr 0.045, n = 38). While bootstrapping the CI for cell09, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.210, stderr 0.042, n = 57).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell13    0.241  0.025   0.192  0.290  52        500
cell04    0.088  0.026   0.037  0.140  41        2000
cell13    0.226  0.018   0.191  0.261  40        1000
cell24    0.104  0.040   0.026  0.182  41        1000
cell02    0.126  0.027   0.072  0.179  52        500
cell04    0.229  0.022   0.185  0.272  57        500
```

### Step 29: checking residual autocorrelation

While re-exporting the raw traces for cell08, two cells fell out of the usable range (coefficient 0.106, stderr 0.028, n = 58). While checking residual autocorrelation for cell03, two cells fell out of the usable range (coefficient 0.260, stderr 0.044, n = 47). While re-exporting the raw traces for cell10, the estimate moved less than one standard error (coefficient 0.263, stderr 0.018, n = 41). While auditing the holding potential column for cell24, the ordering of cells was preserved (coefficient 0.162, stderr 0.039, n = 44). Noted and moved on; it does not change the decision.

While bootstrapping the CI for cell19, the coefficient tracked epoch count more closely than duration (coefficient 0.133, stderr 0.041, n = 39). While auditing the holding potential column for cell21, two cells fell out of the usable range (coefficient 0.266, stderr 0.010, n = 39). While re-exporting the raw traces for cell23, the estimate moved less than one standard error (coefficient 0.191, stderr 0.020, n = 41).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell03    0.152  0.047   0.059  0.245  53        2000
cell16    0.125  0.039   0.048  0.202  42        2000
cell22    0.155  0.048   0.061  0.248  41        1000
cell05    0.236  0.022   0.193  0.279  41        2000
cell20    0.205  0.047   0.112  0.297  56        500
cell06    0.232  0.010   0.212  0.251  48        2000
```

While checking residual autocorrelation for cell24, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.286, stderr 0.032, n = 51). While comparing per-cell orderings for cell22, two cells fell out of the usable range (coefficient 0.165, stderr 0.041, n = 53). While comparing per-cell orderings for cell05, nothing in the figure changed at print size (coefficient 0.201, stderr 0.047, n = 56).

### Step 30: re-running with a tighter segmentation threshold

```python
coefs = fit_per_cell(rows, threshold=0.47)
lo, hi = ci(coefs, seed=61)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell18    0.256  0.049   0.160  0.352  53        500
cell20    0.270  0.014   0.243  0.296  48        1000
cell18    0.256  0.035   0.188  0.324  44        1000
cell20    0.088  0.034   0.022  0.154  52        4000
cell06    0.108  0.012   0.085  0.130  55        1000
cell21    0.262  0.018   0.226  0.298  46        2000
cell06    0.128  0.013   0.103  0.154  50        500
cell06    0.260  0.049   0.164  0.356  44        1000
cell23    0.090  0.048   -0.004  0.184  56        1000
```

While checking residual autocorrelation for cell10, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.197, stderr 0.033, n = 42). While fitting the one-lag kernel for cell13, the ordering of cells was preserved (coefficient 0.153, stderr 0.037, n = 52). While re-exporting the raw traces for cell06, the estimate moved less than one standard error (coefficient 0.090, stderr 0.048, n = 49). While comparing per-cell orderings for cell09, nothing in the figure changed at print size (coefficient 0.239, stderr 0.047, n = 41).

While re-exporting the raw traces for cell20, two cells fell out of the usable range (coefficient 0.194, stderr 0.030, n = 55). While re-running with a tighter segmentation threshold for cell05, the CI narrowed by roughly a tenth (coefficient 0.221, stderr 0.010, n = 44). While auditing the holding potential column for cell15, two cells fell out of the usable range (coefficient 0.243, stderr 0.016, n = 42). While fitting the one-lag kernel for cell02, nothing in the figure changed at print size (coefficient 0.287, stderr 0.021, n = 40). While checking residual autocorrelation for cell03, two cells fell out of the usable range (coefficient 0.306, stderr 0.039, n = 39).

### Step 31: segmenting epochs

While comparing per-cell orderings for cell01, the estimate moved less than one standard error (coefficient 0.274, stderr 0.049, n = 39). While re-running with a tighter segmentation threshold for cell03, nothing in the figure changed at print size (coefficient 0.279, stderr 0.041, n = 53). While comparing per-cell orderings for cell23, the ordering of cells was preserved (coefficient 0.244, stderr 0.039, n = 42).

While re-exporting the raw traces for cell07, the CI narrowed by roughly a tenth (coefficient 0.080, stderr 0.022, n = 39). While segmenting epochs for cell04, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.204, stderr 0.015, n = 43). While fitting the one-lag kernel for cell08, the ordering of cells was preserved (coefficient 0.274, stderr 0.015, n = 47). While comparing per-cell orderings for cell13, the CI narrowed by roughly a tenth (coefficient 0.121, stderr 0.011, n = 55). While re-running with a tighter segmentation threshold for cell06, nothing in the figure changed at print size (coefficient 0.206, stderr 0.015, n = 47). Noted and moved on; it does not change the decision.

While re-running with a tighter segmentation threshold for cell03, two cells fell out of the usable range (coefficient 0.267, stderr 0.027, n = 39). While fitting the one-lag kernel for cell05, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.119, stderr 0.010, n = 38). While comparing per-cell orderings for cell13, nothing in the figure changed at print size (coefficient 0.254, stderr 0.018, n = 54). While segmenting epochs for cell16, nothing in the figure changed at print size (coefficient 0.220, stderr 0.037, n = 55). While re-exporting the raw traces for cell16, nothing in the figure changed at print size (coefficient 0.228, stderr 0.021, n = 58).

While segmenting epochs for cell16, the estimate moved less than one standard error (coefficient 0.211, stderr 0.040, n = 40). While re-running with a tighter segmentation threshold for cell07, two cells fell out of the usable range (coefficient 0.256, stderr 0.013, n = 56). While checking residual autocorrelation for cell16, the CI narrowed by roughly a tenth (coefficient 0.097, stderr 0.029, n = 49).

### Step 32: comparing per-cell orderings

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell16    0.275  0.047   0.182  0.368  47        1000
cell06    0.190  0.034   0.124  0.257  46        2000
cell08    0.222  0.022   0.180  0.264  58        1000
cell15    0.220  0.047   0.128  0.311  40        4000
cell17    0.144  0.039   0.067  0.221  58        2000
cell21    0.186  0.033   0.123  0.250  47        2000
cell12    0.247  0.039   0.170  0.323  44        500
cell13    0.299  0.048   0.205  0.392  38        500
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell11    0.084  0.044   -0.003  0.171  53        1000
cell16    0.136  0.029   0.078  0.193  44        2000
cell13    0.183  0.027   0.131  0.236  49        500
cell12    0.207  0.026   0.155  0.259  48        500
cell24    0.186  0.016   0.154  0.218  43        2000
cell06    0.090  0.014   0.061  0.118  47        500
cell17    0.086  0.044   -0.001  0.173  41        500
cell15    0.245  0.028   0.190  0.299  47        1000
cell16    0.201  0.043   0.116  0.286  38        500
cell11    0.306  0.024   0.260  0.352  53        1000
```

### Step 33: comparing per-cell orderings

```python
coefs = fit_per_cell(rows, threshold=0.55)
lo, hi = ci(coefs, seed=92)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While checking residual autocorrelation for cell08, the coefficient tracked epoch count more closely than duration (coefficient 0.238, stderr 0.020, n = 40). While bootstrapping the CI for cell18, nothing in the figure changed at print size (coefficient 0.092, stderr 0.014, n = 58). While re-exporting the raw traces for cell23, the estimate moved less than one standard error (coefficient 0.305, stderr 0.040, n = 44). While re-running with a tighter segmentation threshold for cell14, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.145, stderr 0.033, n = 50). While comparing per-cell orderings for cell19, the coefficient tracked epoch count more closely than duration (coefficient 0.172, stderr 0.019, n = 42). While fitting the one-lag kernel for cell17, the ordering of cells was preserved (coefficient 0.281, stderr 0.029, n = 53).

### Step 34: segmenting epochs

While comparing per-cell orderings for cell17, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.169, stderr 0.036, n = 48). While re-exporting the raw traces for cell13, the coefficient tracked epoch count more closely than duration (coefficient 0.089, stderr 0.020, n = 52). While auditing the holding potential column for cell24, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.236, stderr 0.034, n = 56). While fitting the one-lag kernel for cell09, the coefficient tracked epoch count more closely than duration (coefficient 0.258, stderr 0.046, n = 42).

While segmenting epochs for cell17, the ordering of cells was preserved (coefficient 0.201, stderr 0.026, n = 50). While bootstrapping the CI for cell19, the estimate moved less than one standard error (coefficient 0.207, stderr 0.048, n = 41). While comparing per-cell orderings for cell07, two cells fell out of the usable range (coefficient 0.299, stderr 0.027, n = 50).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell18    0.188  0.021   0.148  0.229  39        4000
cell15    0.164  0.045   0.076  0.251  38        500
cell15    0.230  0.011   0.209  0.252  43        2000
cell23    0.143  0.048   0.050  0.237  39        1000
cell14    0.148  0.019   0.110  0.186  39        2000
cell09    0.270  0.011   0.249  0.291  48        2000
cell05    0.275  0.011   0.253  0.297  55        500
```

### Step 35: checking residual autocorrelation

While checking residual autocorrelation for cell13, the CI narrowed by roughly a tenth (coefficient 0.245, stderr 0.046, n = 47). While bootstrapping the CI for cell08, the CI narrowed by roughly a tenth (coefficient 0.295, stderr 0.036, n = 40). While checking residual autocorrelation for cell18, nothing in the figure changed at print size (coefficient 0.268, stderr 0.017, n = 54). Parking this until the re-segmentation lands.

While fitting the one-lag kernel for cell19, the coefficient tracked epoch count more closely than duration (coefficient 0.084, stderr 0.040, n = 54). While re-exporting the raw traces for cell06, the coefficient tracked epoch count more closely than duration (coefficient 0.217, stderr 0.037, n = 44). While bootstrapping the CI for cell05, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.182, stderr 0.033, n = 43).

While re-exporting the raw traces for cell08, the coefficient tracked epoch count more closely than duration (coefficient 0.247, stderr 0.049, n = 47). While fitting the one-lag kernel for cell13, the coefficient tracked epoch count more closely than duration (coefficient 0.139, stderr 0.028, n = 47). While auditing the holding potential column for cell09, the estimate moved less than one standard error (coefficient 0.103, stderr 0.024, n = 58). While re-running with a tighter segmentation threshold for cell22, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.117, stderr 0.028, n = 50). While fitting the one-lag kernel for cell09, the coefficient tracked epoch count more closely than duration (coefficient 0.155, stderr 0.010, n = 43). Worth noting for the writeup, though not a result on its own.

```python
coefs = fit_per_cell(rows, threshold=0.39)
lo, hi = ci(coefs, seed=62)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 36: auditing the holding potential column

While bootstrapping the CI for cell09, the estimate moved less than one standard error (coefficient 0.182, stderr 0.026, n = 51). While auditing the holding potential column for cell06, the ordering of cells was preserved (coefficient 0.105, stderr 0.028, n = 38). While segmenting epochs for cell09, the CI narrowed by roughly a tenth (coefficient 0.138, stderr 0.019, n = 45). While segmenting epochs for cell12, the coefficient tracked epoch count more closely than duration (coefficient 0.199, stderr 0.027, n = 48). While auditing the holding potential column for cell02, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.303, stderr 0.041, n = 42).

While checking residual autocorrelation for cell01, the coefficient tracked epoch count more closely than duration (coefficient 0.273, stderr 0.014, n = 44). While segmenting epochs for cell23, nothing in the figure changed at print size (coefficient 0.149, stderr 0.021, n = 44). While comparing per-cell orderings for cell04, the CI narrowed by roughly a tenth (coefficient 0.192, stderr 0.022, n = 44). While checking residual autocorrelation for cell05, two cells fell out of the usable range (coefficient 0.091, stderr 0.037, n = 44). While re-running with a tighter segmentation threshold for cell19, two cells fell out of the usable range (coefficient 0.101, stderr 0.020, n = 50). While checking residual autocorrelation for cell12, two cells fell out of the usable range (coefficient 0.226, stderr 0.039, n = 55).

While segmenting epochs for cell10, two cells fell out of the usable range (coefficient 0.244, stderr 0.044, n = 48). While re-running with a tighter segmentation threshold for cell12, nothing in the figure changed at print size (coefficient 0.206, stderr 0.048, n = 53). While re-running with a tighter segmentation threshold for cell03, nothing in the figure changed at print size (coefficient 0.090, stderr 0.024, n = 57). While re-exporting the raw traces for cell07, the ordering of cells was preserved (coefficient 0.210, stderr 0.034, n = 47).

While auditing the holding potential column for cell14, two cells fell out of the usable range (coefficient 0.246, stderr 0.019, n = 48). While auditing the holding potential column for cell17, the ordering of cells was preserved (coefficient 0.100, stderr 0.043, n = 46). While fitting the one-lag kernel for cell07, nothing in the figure changed at print size (coefficient 0.123, stderr 0.011, n = 46). While re-exporting the raw traces for cell05, nothing in the figure changed at print size (coefficient 0.129, stderr 0.027, n = 54). While re-running with a tighter segmentation threshold for cell16, the ordering of cells was preserved (coefficient 0.304, stderr 0.034, n = 52). While checking residual autocorrelation for cell04, the coefficient tracked epoch count more closely than duration (coefficient 0.237, stderr 0.039, n = 58).

### Step 37: segmenting epochs

```python
coefs = fit_per_cell(rows, threshold=0.55)
lo, hi = ci(coefs, seed=82)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While segmenting epochs for cell17, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.171, stderr 0.020, n = 42). While segmenting epochs for cell08, the coefficient tracked epoch count more closely than duration (coefficient 0.181, stderr 0.046, n = 45). While re-exporting the raw traces for cell20, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.199, stderr 0.019, n = 47). While bootstrapping the CI for cell18, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.174, stderr 0.034, n = 51). While auditing the holding potential column for cell05, nothing in the figure changed at print size (coefficient 0.182, stderr 0.037, n = 52).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell17    0.123  0.036   0.052  0.194  47        500
cell23    0.193  0.040   0.114  0.273  57        1000
cell07    0.196  0.010   0.176  0.216  51        2000
cell07    0.105  0.027   0.053  0.158  58        1000
cell11    0.156  0.015   0.127  0.186  41        4000
cell17    0.214  0.019   0.176  0.252  45        2000
cell02    0.142  0.034   0.076  0.209  47        1000
cell05    0.300  0.035   0.231  0.369  52        4000
cell08    0.210  0.044   0.125  0.296  53        500
```

While comparing per-cell orderings for cell08, the coefficient tracked epoch count more closely than duration (coefficient 0.292, stderr 0.040, n = 46). While checking residual autocorrelation for cell07, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.268, stderr 0.026, n = 52). While segmenting epochs for cell01, the coefficient tracked epoch count more closely than duration (coefficient 0.147, stderr 0.032, n = 55).

### Step 38: re-running with a tighter segmentation threshold

While auditing the holding potential column for cell19, the CI narrowed by roughly a tenth (coefficient 0.224, stderr 0.012, n = 50). While re-running with a tighter segmentation threshold for cell09, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.098, stderr 0.012, n = 39). While checking residual autocorrelation for cell05, the coefficient tracked epoch count more closely than duration (coefficient 0.274, stderr 0.013, n = 55).

While re-running with a tighter segmentation threshold for cell23, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.227, stderr 0.028, n = 54). While re-running with a tighter segmentation threshold for cell10, two cells fell out of the usable range (coefficient 0.123, stderr 0.030, n = 50). While bootstrapping the CI for cell08, the coefficient tracked epoch count more closely than duration (coefficient 0.260, stderr 0.039, n = 54). While comparing per-cell orderings for cell12, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.217, stderr 0.022, n = 57). While re-exporting the raw traces for cell20, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.247, stderr 0.022, n = 50). Worth noting for the writeup, though not a result on its own.

### Step 39: comparing per-cell orderings

While comparing per-cell orderings for cell18, the CI narrowed by roughly a tenth (coefficient 0.165, stderr 0.047, n = 56). While auditing the holding potential column for cell17, the estimate moved less than one standard error (coefficient 0.192, stderr 0.011, n = 43). While re-exporting the raw traces for cell08, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.144, stderr 0.028, n = 51). Noted and moved on; it does not change the decision.

While comparing per-cell orderings for cell24, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.305, stderr 0.017, n = 45). While re-running with a tighter segmentation threshold for cell02, the ordering of cells was preserved (coefficient 0.240, stderr 0.034, n = 58). While checking residual autocorrelation for cell06, nothing in the figure changed at print size (coefficient 0.260, stderr 0.026, n = 49). While segmenting epochs for cell13, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.167, stderr 0.012, n = 41). While fitting the one-lag kernel for cell07, the CI narrowed by roughly a tenth (coefficient 0.135, stderr 0.041, n = 54).

While segmenting epochs for cell11, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.129, stderr 0.033, n = 44). While segmenting epochs for cell19, the coefficient tracked epoch count more closely than duration (coefficient 0.279, stderr 0.021, n = 45). While auditing the holding potential column for cell14, the estimate moved less than one standard error (coefficient 0.114, stderr 0.018, n = 57). Noted and moved on; it does not change the decision.

