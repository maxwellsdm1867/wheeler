# Prior session 15 of 20

Transcript of an earlier working session on the history-kernel analysis.

### Step 1: re-exporting the raw traces

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell20    0.296  0.027   0.243  0.349  46        1000
cell24    0.165  0.041   0.085  0.245  45        4000
cell24    0.287  0.012   0.264  0.310  47        500
cell21    0.258  0.014   0.230  0.287  58        2000
cell18    0.188  0.049   0.091  0.284  47        500
cell13    0.176  0.019   0.139  0.214  44        1000
cell01    0.104  0.049   0.009  0.199  51        4000
cell19    0.240  0.017   0.207  0.273  55        4000
cell22    0.196  0.018   0.161  0.231  57        2000
cell07    0.273  0.038   0.199  0.348  52        4000
```

While re-running with a tighter segmentation threshold for cell08, the estimate moved less than one standard error (coefficient 0.194, stderr 0.022, n = 56). While fitting the one-lag kernel for cell16, the estimate moved less than one standard error (coefficient 0.149, stderr 0.045, n = 56). While bootstrapping the CI for cell07, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.082, stderr 0.048, n = 48).

While bootstrapping the CI for cell13, the ordering of cells was preserved (coefficient 0.128, stderr 0.035, n = 48). While checking residual autocorrelation for cell18, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.196, stderr 0.020, n = 49). While fitting the one-lag kernel for cell15, the estimate moved less than one standard error (coefficient 0.185, stderr 0.013, n = 51). While auditing the holding potential column for cell16, the CI narrowed by roughly a tenth (coefficient 0.156, stderr 0.016, n = 55). While segmenting epochs for cell02, nothing in the figure changed at print size (coefficient 0.170, stderr 0.039, n = 44).

While segmenting epochs for cell18, nothing in the figure changed at print size (coefficient 0.121, stderr 0.026, n = 44). While checking residual autocorrelation for cell18, the estimate moved less than one standard error (coefficient 0.224, stderr 0.035, n = 55). While checking residual autocorrelation for cell22, the estimate moved less than one standard error (coefficient 0.186, stderr 0.022, n = 48). While auditing the holding potential column for cell01, the estimate moved less than one standard error (coefficient 0.271, stderr 0.048, n = 38). While fitting the one-lag kernel for cell16, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.114, stderr 0.045, n = 45). While re-running with a tighter segmentation threshold for cell05, the CI narrowed by roughly a tenth (coefficient 0.103, stderr 0.050, n = 48).

### Step 2: checking residual autocorrelation

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell22    0.303  0.042   0.220  0.386  58        4000
cell20    0.105  0.030   0.047  0.163  43        1000
cell15    0.170  0.012   0.146  0.195  48        500
cell03    0.143  0.032   0.080  0.206  53        500
cell10    0.174  0.050   0.077  0.272  38        500
cell03    0.216  0.043   0.131  0.301  49        1000
cell03    0.152  0.027   0.099  0.204  43        1000
cell05    0.190  0.040   0.112  0.269  47        500
cell16    0.293  0.049   0.197  0.389  53        4000
cell06    0.292  0.013   0.267  0.317  48        500
cell17    0.201  0.012   0.177  0.225  47        2000
cell06    0.103  0.036   0.032  0.173  40        4000
cell17    0.281  0.045   0.194  0.369  40        500
```

While segmenting epochs for cell09, nothing in the figure changed at print size (coefficient 0.139, stderr 0.017, n = 56). While comparing per-cell orderings for cell01, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.294, stderr 0.038, n = 53). While comparing per-cell orderings for cell16, the estimate moved less than one standard error (coefficient 0.082, stderr 0.040, n = 52).

### Step 3: bootstrapping the CI

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell13    0.291  0.044   0.204  0.377  40        4000
cell22    0.192  0.022   0.149  0.235  58        4000
cell04    0.086  0.032   0.023  0.148  49        500
cell23    0.141  0.033   0.077  0.205  53        4000
cell23    0.186  0.046   0.095  0.276  42        2000
cell15    0.295  0.038   0.221  0.369  44        4000
cell16    0.244  0.045   0.156  0.333  42        4000
cell03    0.287  0.035   0.218  0.357  57        500
cell23    0.180  0.012   0.156  0.203  46        2000
cell13    0.182  0.020   0.143  0.221  53        500
cell03    0.256  0.033   0.192  0.320  58        1000
cell14    0.105  0.019   0.068  0.142  39        4000
cell08    0.285  0.021   0.245  0.326  47        1000
cell02    0.192  0.012   0.170  0.215  58        1000
```

While fitting the one-lag kernel for cell17, the CI narrowed by roughly a tenth (coefficient 0.283, stderr 0.030, n = 38). While re-exporting the raw traces for cell21, the coefficient tracked epoch count more closely than duration (coefficient 0.089, stderr 0.028, n = 38). While re-running with a tighter segmentation threshold for cell08, nothing in the figure changed at print size (coefficient 0.239, stderr 0.022, n = 41). While re-exporting the raw traces for cell23, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.134, stderr 0.017, n = 47). While re-exporting the raw traces for cell01, the CI narrowed by roughly a tenth (coefficient 0.301, stderr 0.044, n = 58). This is the part that will need a real statistical argument.

### Step 4: comparing per-cell orderings

While re-exporting the raw traces for cell23, the CI narrowed by roughly a tenth (coefficient 0.211, stderr 0.025, n = 43). While re-running with a tighter segmentation threshold for cell19, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.276, stderr 0.022, n = 40). While fitting the one-lag kernel for cell05, two cells fell out of the usable range (coefficient 0.152, stderr 0.036, n = 43). While fitting the one-lag kernel for cell22, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.131, stderr 0.041, n = 52). Noted and moved on; it does not change the decision.

While auditing the holding potential column for cell14, the coefficient tracked epoch count more closely than duration (coefficient 0.168, stderr 0.043, n = 51). While auditing the holding potential column for cell03, the ordering of cells was preserved (coefficient 0.213, stderr 0.045, n = 43). While segmenting epochs for cell21, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.295, stderr 0.044, n = 47). This is the part that will need a real statistical argument.

### Step 5: auditing the holding potential column

While checking residual autocorrelation for cell11, the estimate moved less than one standard error (coefficient 0.239, stderr 0.048, n = 53). While auditing the holding potential column for cell24, two cells fell out of the usable range (coefficient 0.152, stderr 0.015, n = 51). While auditing the holding potential column for cell09, the estimate moved less than one standard error (coefficient 0.130, stderr 0.017, n = 58). While re-exporting the raw traces for cell12, two cells fell out of the usable range (coefficient 0.296, stderr 0.045, n = 51).

```python
coefs = fit_per_cell(rows, threshold=0.68)
lo, hi = ci(coefs, seed=19)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While bootstrapping the CI for cell11, the CI narrowed by roughly a tenth (coefficient 0.234, stderr 0.041, n = 45). While checking residual autocorrelation for cell03, the estimate moved less than one standard error (coefficient 0.225, stderr 0.040, n = 40). While checking residual autocorrelation for cell22, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.129, stderr 0.032, n = 46). While comparing per-cell orderings for cell19, the coefficient tracked epoch count more closely than duration (coefficient 0.208, stderr 0.018, n = 40).

### Step 6: segmenting epochs

While re-exporting the raw traces for cell03, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.285, stderr 0.029, n = 50). While bootstrapping the CI for cell15, the ordering of cells was preserved (coefficient 0.108, stderr 0.022, n = 57). While re-running with a tighter segmentation threshold for cell06, the CI narrowed by roughly a tenth (coefficient 0.288, stderr 0.018, n = 51). While fitting the one-lag kernel for cell20, the coefficient tracked epoch count more closely than duration (coefficient 0.143, stderr 0.029, n = 39). While re-running with a tighter segmentation threshold for cell08, two cells fell out of the usable range (coefficient 0.088, stderr 0.011, n = 38).

While bootstrapping the CI for cell19, two cells fell out of the usable range (coefficient 0.098, stderr 0.022, n = 45). While segmenting epochs for cell22, the CI narrowed by roughly a tenth (coefficient 0.272, stderr 0.016, n = 38). While re-exporting the raw traces for cell14, nothing in the figure changed at print size (coefficient 0.083, stderr 0.019, n = 38). While comparing per-cell orderings for cell03, the ordering of cells was preserved (coefficient 0.147, stderr 0.050, n = 39). Noted and moved on; it does not change the decision.

### Step 7: re-exporting the raw traces

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell06    0.291  0.037   0.219  0.364  46        1000
cell01    0.158  0.038   0.083  0.233  44        500
cell14    0.250  0.026   0.198  0.301  56        1000
cell17    0.180  0.027   0.128  0.232  43        500
cell22    0.087  0.024   0.040  0.134  54        2000
cell04    0.197  0.031   0.136  0.259  52        500
cell02    0.159  0.050   0.062  0.256  53        4000
cell22    0.251  0.024   0.205  0.298  48        4000
cell06    0.134  0.048   0.040  0.229  45        500
cell16    0.142  0.016   0.111  0.173  45        500
cell17    0.251  0.013   0.226  0.275  54        2000
cell04    0.105  0.021   0.064  0.147  55        4000
cell06    0.299  0.020   0.260  0.338  58        4000
```

While checking residual autocorrelation for cell10, the ordering of cells was preserved (coefficient 0.090, stderr 0.042, n = 44). While segmenting epochs for cell08, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.080, stderr 0.011, n = 55). While segmenting epochs for cell22, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.154, stderr 0.011, n = 47). While segmenting epochs for cell20, the CI narrowed by roughly a tenth (coefficient 0.160, stderr 0.032, n = 51). While auditing the holding potential column for cell11, the CI narrowed by roughly a tenth (coefficient 0.186, stderr 0.016, n = 50). While bootstrapping the CI for cell02, the estimate moved less than one standard error (coefficient 0.127, stderr 0.043, n = 48). This is the part that will need a real statistical argument.

While re-exporting the raw traces for cell19, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.093, stderr 0.034, n = 54). While bootstrapping the CI for cell21, the coefficient tracked epoch count more closely than duration (coefficient 0.284, stderr 0.022, n = 55). While auditing the holding potential column for cell24, the estimate moved less than one standard error (coefficient 0.180, stderr 0.043, n = 43). Worth noting for the writeup, though not a result on its own.

While comparing per-cell orderings for cell05, the CI narrowed by roughly a tenth (coefficient 0.216, stderr 0.045, n = 54). While auditing the holding potential column for cell05, nothing in the figure changed at print size (coefficient 0.104, stderr 0.044, n = 45). While checking residual autocorrelation for cell11, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.223, stderr 0.043, n = 53). While checking residual autocorrelation for cell12, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.169, stderr 0.032, n = 54). While re-running with a tighter segmentation threshold for cell02, the estimate moved less than one standard error (coefficient 0.171, stderr 0.047, n = 53).

### Step 8: re-exporting the raw traces

While fitting the one-lag kernel for cell05, nothing in the figure changed at print size (coefficient 0.309, stderr 0.041, n = 47). While re-exporting the raw traces for cell22, the estimate moved less than one standard error (coefficient 0.093, stderr 0.014, n = 44). While re-exporting the raw traces for cell01, nothing in the figure changed at print size (coefficient 0.198, stderr 0.036, n = 40). While checking residual autocorrelation for cell04, the coefficient tracked epoch count more closely than duration (coefficient 0.218, stderr 0.048, n = 57). While comparing per-cell orderings for cell24, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.129, stderr 0.028, n = 48). Worth noting for the writeup, though not a result on its own.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell05    0.096  0.033   0.030  0.161  38        500
cell01    0.218  0.031   0.157  0.279  45        500
cell11    0.103  0.021   0.063  0.144  41        500
cell02    0.088  0.010   0.067  0.108  38        500
cell23    0.146  0.021   0.105  0.186  54        1000
cell01    0.212  0.015   0.182  0.242  51        4000
cell13    0.176  0.029   0.119  0.232  39        2000
cell14    0.114  0.032   0.050  0.178  46        2000
cell15    0.248  0.019   0.211  0.286  46        1000
cell17    0.175  0.026   0.124  0.225  46        2000
cell05    0.233  0.023   0.189  0.277  46        500
cell11    0.219  0.042   0.137  0.301  43        1000
```

### Step 9: re-running with a tighter segmentation threshold

```python
coefs = fit_per_cell(rows, threshold=0.49)
lo, hi = ci(coefs, seed=63)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While checking residual autocorrelation for cell07, nothing in the figure changed at print size (coefficient 0.149, stderr 0.025, n = 48). While comparing per-cell orderings for cell07, nothing in the figure changed at print size (coefficient 0.267, stderr 0.019, n = 51). While fitting the one-lag kernel for cell17, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.286, stderr 0.049, n = 49). While auditing the holding potential column for cell09, the CI narrowed by roughly a tenth (coefficient 0.200, stderr 0.027, n = 44). This is the part that will need a real statistical argument.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell20    0.172  0.012   0.148  0.195  46        1000
cell24    0.296  0.044   0.210  0.382  41        500
cell16    0.245  0.021   0.205  0.286  49        500
cell08    0.306  0.020   0.267  0.346  51        4000
cell12    0.161  0.011   0.139  0.183  55        500
cell21    0.116  0.015   0.087  0.145  39        1000
cell16    0.290  0.049   0.194  0.386  47        500
cell14    0.150  0.027   0.096  0.204  44        4000
cell22    0.260  0.032   0.197  0.323  39        2000
cell03    0.094  0.023   0.049  0.139  47        2000
```

While checking residual autocorrelation for cell15, the estimate moved less than one standard error (coefficient 0.234, stderr 0.021, n = 56). While auditing the holding potential column for cell10, the coefficient tracked epoch count more closely than duration (coefficient 0.307, stderr 0.016, n = 45). While segmenting epochs for cell04, the ordering of cells was preserved (coefficient 0.276, stderr 0.020, n = 54). While fitting the one-lag kernel for cell04, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.102, stderr 0.012, n = 49). While segmenting epochs for cell18, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.131, stderr 0.034, n = 49). While auditing the holding potential column for cell18, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.306, stderr 0.047, n = 47). Flagging it so it does not get rediscovered next week.

### Step 10: auditing the holding potential column

While re-exporting the raw traces for cell17, the CI narrowed by roughly a tenth (coefficient 0.275, stderr 0.050, n = 49). While segmenting epochs for cell22, the CI narrowed by roughly a tenth (coefficient 0.195, stderr 0.040, n = 46). While auditing the holding potential column for cell08, two cells fell out of the usable range (coefficient 0.135, stderr 0.027, n = 48). Parking this until the re-segmentation lands.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell23    0.188  0.025   0.139  0.237  57        500
cell10    0.097  0.038   0.023  0.171  42        2000
cell10    0.262  0.024   0.214  0.310  42        500
cell07    0.217  0.047   0.125  0.309  49        2000
cell17    0.278  0.045   0.191  0.365  42        1000
cell05    0.154  0.023   0.109  0.199  53        1000
cell09    0.247  0.027   0.195  0.300  57        1000
cell16    0.259  0.047   0.166  0.351  43        4000
```

### Step 11: checking residual autocorrelation

While fitting the one-lag kernel for cell22, two cells fell out of the usable range (coefficient 0.226, stderr 0.016, n = 57). While bootstrapping the CI for cell12, the estimate moved less than one standard error (coefficient 0.184, stderr 0.012, n = 57). While comparing per-cell orderings for cell10, the estimate moved less than one standard error (coefficient 0.117, stderr 0.049, n = 55). Worth noting for the writeup, though not a result on its own.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell24    0.215  0.014   0.188  0.242  51        1000
cell13    0.295  0.048   0.200  0.390  42        4000
cell12    0.248  0.014   0.221  0.275  43        2000
cell15    0.116  0.017   0.082  0.150  58        4000
cell16    0.308  0.042   0.226  0.389  56        500
cell18    0.082  0.018   0.046  0.117  50        2000
cell16    0.105  0.020   0.065  0.145  50        4000
cell04    0.215  0.035   0.147  0.284  57        2000
cell18    0.202  0.010   0.182  0.222  58        2000
```

### Step 12: comparing per-cell orderings

While auditing the holding potential column for cell03, nothing in the figure changed at print size (coefficient 0.226, stderr 0.031, n = 52). While re-running with a tighter segmentation threshold for cell19, the CI narrowed by roughly a tenth (coefficient 0.192, stderr 0.043, n = 47). While fitting the one-lag kernel for cell20, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.310, stderr 0.027, n = 51). While fitting the one-lag kernel for cell01, the estimate moved less than one standard error (coefficient 0.230, stderr 0.032, n = 38).

While auditing the holding potential column for cell22, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.092, stderr 0.024, n = 58). While re-running with a tighter segmentation threshold for cell08, two cells fell out of the usable range (coefficient 0.119, stderr 0.048, n = 56). While segmenting epochs for cell16, the coefficient tracked epoch count more closely than duration (coefficient 0.169, stderr 0.034, n = 39). While segmenting epochs for cell13, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.285, stderr 0.025, n = 53). While fitting the one-lag kernel for cell18, the estimate moved less than one standard error (coefficient 0.276, stderr 0.026, n = 42). Worth noting for the writeup, though not a result on its own.

While segmenting epochs for cell22, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.226, stderr 0.048, n = 52). While segmenting epochs for cell04, two cells fell out of the usable range (coefficient 0.267, stderr 0.021, n = 44). While re-running with a tighter segmentation threshold for cell07, the estimate moved less than one standard error (coefficient 0.140, stderr 0.030, n = 45). Flagging it so it does not get rediscovered next week.

### Step 13: segmenting epochs

While comparing per-cell orderings for cell16, the ordering of cells was preserved (coefficient 0.090, stderr 0.027, n = 44). While re-exporting the raw traces for cell02, the CI narrowed by roughly a tenth (coefficient 0.099, stderr 0.046, n = 49). While fitting the one-lag kernel for cell15, the estimate moved less than one standard error (coefficient 0.114, stderr 0.013, n = 55). While re-exporting the raw traces for cell23, the ordering of cells was preserved (coefficient 0.286, stderr 0.033, n = 52). This is the part that will need a real statistical argument.

While auditing the holding potential column for cell14, the estimate moved less than one standard error (coefficient 0.203, stderr 0.011, n = 38). While bootstrapping the CI for cell01, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.226, stderr 0.041, n = 43). While segmenting epochs for cell07, the ordering of cells was preserved (coefficient 0.152, stderr 0.027, n = 48).

### Step 14: re-running with a tighter segmentation threshold

While comparing per-cell orderings for cell05, two cells fell out of the usable range (coefficient 0.234, stderr 0.032, n = 58). While re-exporting the raw traces for cell15, two cells fell out of the usable range (coefficient 0.125, stderr 0.028, n = 43). While re-running with a tighter segmentation threshold for cell12, two cells fell out of the usable range (coefficient 0.204, stderr 0.023, n = 48). While comparing per-cell orderings for cell09, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.196, stderr 0.023, n = 53). While comparing per-cell orderings for cell17, the coefficient tracked epoch count more closely than duration (coefficient 0.080, stderr 0.017, n = 38).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell01    0.266  0.027   0.213  0.319  57        4000
cell22    0.157  0.025   0.107  0.206  38        500
cell16    0.207  0.033   0.143  0.271  46        1000
cell10    0.305  0.032   0.243  0.367  45        500
cell16    0.126  0.045   0.038  0.215  52        4000
cell04    0.238  0.040   0.159  0.317  54        4000
cell18    0.308  0.018   0.273  0.342  57        4000
cell21    0.240  0.049   0.144  0.336  50        2000
cell07    0.244  0.037   0.171  0.317  46        2000
cell14    0.129  0.042   0.047  0.212  55        1000
cell07    0.213  0.048   0.119  0.307  43        1000
cell05    0.262  0.028   0.206  0.317  51        1000
cell17    0.173  0.032   0.110  0.236  42        4000
```

```python
coefs = fit_per_cell(rows, threshold=0.34)
lo, hi = ci(coefs, seed=85)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 15: re-exporting the raw traces

```python
coefs = fit_per_cell(rows, threshold=0.51)
lo, hi = ci(coefs, seed=46)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While re-running with a tighter segmentation threshold for cell13, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.282, stderr 0.035, n = 42). While re-running with a tighter segmentation threshold for cell01, the coefficient tracked epoch count more closely than duration (coefficient 0.270, stderr 0.036, n = 53). While re-exporting the raw traces for cell23, nothing in the figure changed at print size (coefficient 0.085, stderr 0.043, n = 58). While auditing the holding potential column for cell04, the CI narrowed by roughly a tenth (coefficient 0.101, stderr 0.035, n = 41). While re-running with a tighter segmentation threshold for cell21, the ordering of cells was preserved (coefficient 0.152, stderr 0.033, n = 41). Noted and moved on; it does not change the decision.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell03    0.123  0.036   0.053  0.193  42        2000
cell01    0.251  0.049   0.155  0.347  54        2000
cell17    0.260  0.035   0.192  0.328  48        500
cell21    0.140  0.036   0.070  0.211  45        4000
cell03    0.295  0.013   0.271  0.320  57        1000
cell20    0.272  0.038   0.199  0.346  42        500
```

### Step 16: auditing the holding potential column

While checking residual autocorrelation for cell12, the ordering of cells was preserved (coefficient 0.170, stderr 0.020, n = 40). While re-running with a tighter segmentation threshold for cell08, the CI narrowed by roughly a tenth (coefficient 0.135, stderr 0.016, n = 51). While re-running with a tighter segmentation threshold for cell10, two cells fell out of the usable range (coefficient 0.300, stderr 0.042, n = 48). While re-running with a tighter segmentation threshold for cell15, two cells fell out of the usable range (coefficient 0.181, stderr 0.041, n = 40). While checking residual autocorrelation for cell03, nothing in the figure changed at print size (coefficient 0.214, stderr 0.049, n = 53).

While segmenting epochs for cell01, the estimate moved less than one standard error (coefficient 0.230, stderr 0.029, n = 47). While bootstrapping the CI for cell11, two cells fell out of the usable range (coefficient 0.100, stderr 0.026, n = 57). While comparing per-cell orderings for cell16, the coefficient tracked epoch count more closely than duration (coefficient 0.248, stderr 0.047, n = 55). While re-running with a tighter segmentation threshold for cell12, nothing in the figure changed at print size (coefficient 0.190, stderr 0.029, n = 47). While re-exporting the raw traces for cell13, the ordering of cells was preserved (coefficient 0.254, stderr 0.028, n = 56). While re-running with a tighter segmentation threshold for cell13, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.154, stderr 0.039, n = 54).

While auditing the holding potential column for cell01, the coefficient tracked epoch count more closely than duration (coefficient 0.165, stderr 0.012, n = 46). While auditing the holding potential column for cell04, the estimate moved less than one standard error (coefficient 0.240, stderr 0.049, n = 38). While comparing per-cell orderings for cell05, the coefficient tracked epoch count more closely than duration (coefficient 0.289, stderr 0.049, n = 43).

### Step 17: re-exporting the raw traces

While re-running with a tighter segmentation threshold for cell10, the estimate moved less than one standard error (coefficient 0.114, stderr 0.011, n = 39). While bootstrapping the CI for cell13, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.104, stderr 0.022, n = 56). While re-exporting the raw traces for cell06, the coefficient tracked epoch count more closely than duration (coefficient 0.255, stderr 0.024, n = 51). While fitting the one-lag kernel for cell08, two cells fell out of the usable range (coefficient 0.161, stderr 0.012, n = 56). While re-exporting the raw traces for cell18, the estimate moved less than one standard error (coefficient 0.246, stderr 0.024, n = 57). While comparing per-cell orderings for cell09, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.297, stderr 0.028, n = 42). Noted and moved on; it does not change the decision.

While comparing per-cell orderings for cell03, the ordering of cells was preserved (coefficient 0.281, stderr 0.032, n = 43). While checking residual autocorrelation for cell09, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.251, stderr 0.016, n = 49). While checking residual autocorrelation for cell02, the estimate moved less than one standard error (coefficient 0.267, stderr 0.047, n = 42). While fitting the one-lag kernel for cell14, the CI narrowed by roughly a tenth (coefficient 0.176, stderr 0.049, n = 38). While checking residual autocorrelation for cell24, the coefficient tracked epoch count more closely than duration (coefficient 0.104, stderr 0.044, n = 51). This is the part that will need a real statistical argument.

While segmenting epochs for cell02, the estimate moved less than one standard error (coefficient 0.156, stderr 0.023, n = 39). While re-exporting the raw traces for cell22, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.309, stderr 0.013, n = 55). While bootstrapping the CI for cell23, the CI narrowed by roughly a tenth (coefficient 0.261, stderr 0.034, n = 44). While auditing the holding potential column for cell18, the ordering of cells was preserved (coefficient 0.197, stderr 0.029, n = 46).

While re-exporting the raw traces for cell01, the ordering of cells was preserved (coefficient 0.304, stderr 0.012, n = 43). While re-running with a tighter segmentation threshold for cell05, two cells fell out of the usable range (coefficient 0.290, stderr 0.011, n = 44). While segmenting epochs for cell10, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.171, stderr 0.038, n = 47). While comparing per-cell orderings for cell10, nothing in the figure changed at print size (coefficient 0.093, stderr 0.016, n = 44). While re-exporting the raw traces for cell24, the CI narrowed by roughly a tenth (coefficient 0.117, stderr 0.034, n = 56). While fitting the one-lag kernel for cell05, nothing in the figure changed at print size (coefficient 0.191, stderr 0.020, n = 43).

### Step 18: checking residual autocorrelation

While auditing the holding potential column for cell20, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.099, stderr 0.038, n = 40). While auditing the holding potential column for cell18, the ordering of cells was preserved (coefficient 0.304, stderr 0.023, n = 43). While comparing per-cell orderings for cell19, the CI narrowed by roughly a tenth (coefficient 0.171, stderr 0.048, n = 54). While re-running with a tighter segmentation threshold for cell12, the CI narrowed by roughly a tenth (coefficient 0.135, stderr 0.024, n = 56). While re-running with a tighter segmentation threshold for cell17, the CI narrowed by roughly a tenth (coefficient 0.259, stderr 0.029, n = 58). This is the part that will need a real statistical argument.

While fitting the one-lag kernel for cell22, the coefficient tracked epoch count more closely than duration (coefficient 0.116, stderr 0.020, n = 46). While re-running with a tighter segmentation threshold for cell13, nothing in the figure changed at print size (coefficient 0.159, stderr 0.048, n = 45). While auditing the holding potential column for cell09, two cells fell out of the usable range (coefficient 0.185, stderr 0.016, n = 42). While re-running with a tighter segmentation threshold for cell20, the estimate moved less than one standard error (coefficient 0.247, stderr 0.020, n = 42).

### Step 19: comparing per-cell orderings

While comparing per-cell orderings for cell24, the ordering of cells was preserved (coefficient 0.286, stderr 0.030, n = 47). While comparing per-cell orderings for cell14, nothing in the figure changed at print size (coefficient 0.204, stderr 0.045, n = 56). While comparing per-cell orderings for cell17, the coefficient tracked epoch count more closely than duration (coefficient 0.083, stderr 0.038, n = 49). This is the part that will need a real statistical argument.

While re-exporting the raw traces for cell02, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.300, stderr 0.026, n = 56). While auditing the holding potential column for cell20, the coefficient tracked epoch count more closely than duration (coefficient 0.309, stderr 0.034, n = 56). While auditing the holding potential column for cell17, two cells fell out of the usable range (coefficient 0.281, stderr 0.045, n = 43). While checking residual autocorrelation for cell08, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.148, stderr 0.044, n = 46). While fitting the one-lag kernel for cell11, the ordering of cells was preserved (coefficient 0.093, stderr 0.042, n = 44).

```python
coefs = fit_per_cell(rows, threshold=0.44)
lo, hi = ci(coefs, seed=48)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 20: auditing the holding potential column

```python
coefs = fit_per_cell(rows, threshold=0.34)
lo, hi = ci(coefs, seed=1)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While fitting the one-lag kernel for cell02, the ordering of cells was preserved (coefficient 0.290, stderr 0.045, n = 46). While bootstrapping the CI for cell13, the ordering of cells was preserved (coefficient 0.227, stderr 0.013, n = 46). While re-running with a tighter segmentation threshold for cell13, the ordering of cells was preserved (coefficient 0.084, stderr 0.034, n = 42). Parking this until the re-segmentation lands.

### Step 21: comparing per-cell orderings

While segmenting epochs for cell07, the ordering of cells was preserved (coefficient 0.234, stderr 0.020, n = 58). While checking residual autocorrelation for cell13, the CI narrowed by roughly a tenth (coefficient 0.096, stderr 0.021, n = 58). While checking residual autocorrelation for cell20, the coefficient tracked epoch count more closely than duration (coefficient 0.280, stderr 0.042, n = 52). While checking residual autocorrelation for cell04, two cells fell out of the usable range (coefficient 0.170, stderr 0.029, n = 44). While segmenting epochs for cell01, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.145, stderr 0.038, n = 40).

While checking residual autocorrelation for cell17, two cells fell out of the usable range (coefficient 0.094, stderr 0.013, n = 54). While auditing the holding potential column for cell05, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.267, stderr 0.019, n = 56). While re-exporting the raw traces for cell09, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.307, stderr 0.033, n = 53). While fitting the one-lag kernel for cell23, nothing in the figure changed at print size (coefficient 0.143, stderr 0.040, n = 39). While bootstrapping the CI for cell01, the estimate moved less than one standard error (coefficient 0.142, stderr 0.025, n = 44). While segmenting epochs for cell23, two cells fell out of the usable range (coefficient 0.170, stderr 0.021, n = 53).

### Step 22: auditing the holding potential column

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell02    0.155  0.037   0.082  0.227  39        2000
cell24    0.264  0.033   0.199  0.328  40        500
cell16    0.218  0.030   0.160  0.276  41        1000
cell22    0.091  0.046   0.001  0.181  52        2000
cell18    0.268  0.037   0.196  0.341  42        4000
cell15    0.161  0.049   0.065  0.258  57        500
cell06    0.219  0.018   0.185  0.254  52        4000
cell16    0.259  0.013   0.234  0.284  47        2000
cell04    0.127  0.011   0.105  0.149  56        2000
```

```python
coefs = fit_per_cell(rows, threshold=0.72)
lo, hi = ci(coefs, seed=36)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 23: auditing the holding potential column

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell12    0.146  0.028   0.092  0.200  53        1000
cell09    0.266  0.046   0.176  0.357  54        1000
cell07    0.140  0.043   0.055  0.224  42        4000
cell04    0.276  0.032   0.213  0.340  44        2000
cell24    0.123  0.020   0.084  0.162  45        1000
cell22    0.246  0.027   0.193  0.299  47        4000
cell05    0.292  0.033   0.228  0.356  39        1000
cell01    0.296  0.027   0.244  0.349  54        500
cell07    0.298  0.048   0.204  0.391  48        1000
cell02    0.093  0.021   0.052  0.134  43        4000
cell18    0.180  0.044   0.094  0.266  54        1000
cell24    0.126  0.018   0.091  0.160  54        500
```

While re-running with a tighter segmentation threshold for cell21, two cells fell out of the usable range (coefficient 0.123, stderr 0.019, n = 39). While checking residual autocorrelation for cell24, nothing in the figure changed at print size (coefficient 0.174, stderr 0.028, n = 39). While re-running with a tighter segmentation threshold for cell22, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.133, stderr 0.034, n = 44). While re-running with a tighter segmentation threshold for cell05, the estimate moved less than one standard error (coefficient 0.179, stderr 0.018, n = 54). While re-exporting the raw traces for cell21, the coefficient tracked epoch count more closely than duration (coefficient 0.202, stderr 0.019, n = 43). While fitting the one-lag kernel for cell20, the ordering of cells was preserved (coefficient 0.174, stderr 0.022, n = 57).

While re-running with a tighter segmentation threshold for cell09, the CI narrowed by roughly a tenth (coefficient 0.275, stderr 0.025, n = 46). While fitting the one-lag kernel for cell04, the CI narrowed by roughly a tenth (coefficient 0.218, stderr 0.035, n = 39). While segmenting epochs for cell05, two cells fell out of the usable range (coefficient 0.296, stderr 0.011, n = 51). While segmenting epochs for cell05, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.270, stderr 0.020, n = 54). While fitting the one-lag kernel for cell02, nothing in the figure changed at print size (coefficient 0.100, stderr 0.028, n = 43).

### Step 24: re-exporting the raw traces

While auditing the holding potential column for cell18, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.120, stderr 0.021, n = 51). While re-exporting the raw traces for cell20, nothing in the figure changed at print size (coefficient 0.199, stderr 0.018, n = 41). While auditing the holding potential column for cell07, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.096, stderr 0.019, n = 38). While comparing per-cell orderings for cell14, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.175, stderr 0.014, n = 56). While auditing the holding potential column for cell16, nothing in the figure changed at print size (coefficient 0.103, stderr 0.012, n = 38). While re-running with a tighter segmentation threshold for cell05, the ordering of cells was preserved (coefficient 0.195, stderr 0.043, n = 48).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell18    0.127  0.035   0.058  0.196  48        2000
cell07    0.187  0.033   0.123  0.251  43        4000
cell12    0.217  0.040   0.139  0.296  45        500
cell15    0.288  0.028   0.234  0.343  45        4000
cell16    0.190  0.011   0.168  0.211  58        4000
cell12    0.257  0.039   0.180  0.333  47        2000
cell09    0.132  0.039   0.055  0.209  58        4000
cell04    0.150  0.043   0.065  0.234  44        4000
cell22    0.263  0.016   0.231  0.294  56        500
cell20    0.157  0.012   0.134  0.181  45        500
cell16    0.297  0.031   0.236  0.358  58        500
```

While auditing the holding potential column for cell12, the CI narrowed by roughly a tenth (coefficient 0.155, stderr 0.031, n = 55). While segmenting epochs for cell17, the coefficient tracked epoch count more closely than duration (coefficient 0.143, stderr 0.038, n = 51). While segmenting epochs for cell03, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.282, stderr 0.019, n = 47).

While re-exporting the raw traces for cell01, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.160, stderr 0.023, n = 48). While re-exporting the raw traces for cell08, the ordering of cells was preserved (coefficient 0.228, stderr 0.048, n = 51). While auditing the holding potential column for cell13, nothing in the figure changed at print size (coefficient 0.221, stderr 0.048, n = 55). While comparing per-cell orderings for cell11, the estimate moved less than one standard error (coefficient 0.123, stderr 0.015, n = 49). While re-running with a tighter segmentation threshold for cell11, the coefficient tracked epoch count more closely than duration (coefficient 0.118, stderr 0.035, n = 52). While comparing per-cell orderings for cell17, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.265, stderr 0.017, n = 38).

### Step 25: re-running with a tighter segmentation threshold

While re-running with a tighter segmentation threshold for cell05, the CI narrowed by roughly a tenth (coefficient 0.166, stderr 0.015, n = 46). While re-exporting the raw traces for cell13, the estimate moved less than one standard error (coefficient 0.122, stderr 0.016, n = 54). While re-running with a tighter segmentation threshold for cell15, nothing in the figure changed at print size (coefficient 0.142, stderr 0.016, n = 48). While checking residual autocorrelation for cell21, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.294, stderr 0.019, n = 45). While bootstrapping the CI for cell12, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.296, stderr 0.040, n = 39). While re-exporting the raw traces for cell08, the coefficient tracked epoch count more closely than duration (coefficient 0.278, stderr 0.016, n = 39). Flagging it so it does not get rediscovered next week.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell10    0.115  0.046   0.025  0.205  54        500
cell09    0.239  0.042   0.157  0.321  58        1000
cell15    0.180  0.013   0.155  0.205  38        1000
cell07    0.211  0.018   0.175  0.247  42        1000
cell18    0.218  0.011   0.197  0.239  38        500
cell08    0.199  0.034   0.133  0.264  45        500
cell01    0.227  0.017   0.193  0.261  50        500
cell20    0.220  0.049   0.124  0.315  38        4000
cell21    0.083  0.040   0.006  0.161  41        2000
cell04    0.175  0.032   0.112  0.238  56        2000
cell16    0.196  0.018   0.160  0.231  40        2000
```

```python
coefs = fit_per_cell(rows, threshold=0.57)
lo, hi = ci(coefs, seed=56)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 26: bootstrapping the CI

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell05    0.303  0.045   0.214  0.392  52        500
cell04    0.293  0.017   0.260  0.326  56        2000
cell08    0.095  0.011   0.074  0.116  51        2000
cell02    0.199  0.024   0.151  0.246  38        1000
cell05    0.147  0.039   0.069  0.224  43        4000
cell04    0.185  0.033   0.121  0.249  43        4000
cell24    0.275  0.012   0.251  0.299  56        4000
cell22    0.146  0.037   0.073  0.219  57        1000
cell07    0.226  0.018   0.191  0.261  52        2000
cell16    0.103  0.026   0.051  0.154  53        500
cell20    0.117  0.045   0.029  0.205  55        2000
cell10    0.301  0.034   0.234  0.369  39        2000
```

While auditing the holding potential column for cell05, nothing in the figure changed at print size (coefficient 0.215, stderr 0.024, n = 47). While segmenting epochs for cell19, the coefficient tracked epoch count more closely than duration (coefficient 0.132, stderr 0.035, n = 53). While re-running with a tighter segmentation threshold for cell14, nothing in the figure changed at print size (coefficient 0.263, stderr 0.022, n = 43). While auditing the holding potential column for cell13, the CI narrowed by roughly a tenth (coefficient 0.127, stderr 0.014, n = 45). Parking this until the re-segmentation lands.

While re-running with a tighter segmentation threshold for cell01, nothing in the figure changed at print size (coefficient 0.267, stderr 0.038, n = 47). While checking residual autocorrelation for cell21, two cells fell out of the usable range (coefficient 0.114, stderr 0.028, n = 42). While re-running with a tighter segmentation threshold for cell14, the coefficient tracked epoch count more closely than duration (coefficient 0.124, stderr 0.017, n = 53). This is the part that will need a real statistical argument.

While fitting the one-lag kernel for cell16, the estimate moved less than one standard error (coefficient 0.211, stderr 0.033, n = 44). While re-running with a tighter segmentation threshold for cell07, the estimate moved less than one standard error (coefficient 0.271, stderr 0.040, n = 56). While bootstrapping the CI for cell05, two cells fell out of the usable range (coefficient 0.156, stderr 0.039, n = 48). While fitting the one-lag kernel for cell08, the coefficient tracked epoch count more closely than duration (coefficient 0.213, stderr 0.038, n = 53). While re-exporting the raw traces for cell16, the estimate moved less than one standard error (coefficient 0.149, stderr 0.021, n = 49). While auditing the holding potential column for cell11, the estimate moved less than one standard error (coefficient 0.257, stderr 0.011, n = 48). This is the part that will need a real statistical argument.

### Step 27: re-running with a tighter segmentation threshold

While comparing per-cell orderings for cell04, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.179, stderr 0.038, n = 57). While bootstrapping the CI for cell14, two cells fell out of the usable range (coefficient 0.144, stderr 0.045, n = 53). While comparing per-cell orderings for cell07, the coefficient tracked epoch count more closely than duration (coefficient 0.227, stderr 0.032, n = 41). While auditing the holding potential column for cell19, two cells fell out of the usable range (coefficient 0.105, stderr 0.038, n = 48). This is the part that will need a real statistical argument.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell10    0.114  0.019   0.076  0.152  38        4000
cell10    0.170  0.024   0.123  0.216  53        4000
cell16    0.124  0.012   0.100  0.147  48        4000
cell03    0.287  0.018   0.251  0.322  51        4000
cell19    0.165  0.033   0.100  0.229  45        500
cell21    0.268  0.044   0.181  0.355  39        2000
cell10    0.296  0.025   0.246  0.345  49        500
cell04    0.302  0.017   0.268  0.336  41        4000
cell18    0.111  0.036   0.040  0.182  43        1000
cell10    0.108  0.021   0.067  0.149  56        1000
cell09    0.285  0.028   0.231  0.340  58        4000
cell15    0.279  0.034   0.213  0.344  49        4000
cell06    0.207  0.047   0.114  0.300  40        500
cell16    0.239  0.026   0.188  0.289  48        4000
```

### Step 28: segmenting epochs

While segmenting epochs for cell21, the CI narrowed by roughly a tenth (coefficient 0.139, stderr 0.022, n = 52). While checking residual autocorrelation for cell12, nothing in the figure changed at print size (coefficient 0.265, stderr 0.014, n = 56). While auditing the holding potential column for cell24, the CI narrowed by roughly a tenth (coefficient 0.220, stderr 0.031, n = 41). Worth noting for the writeup, though not a result on its own.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell06    0.298  0.032   0.237  0.360  53        500
cell03    0.205  0.045   0.117  0.293  48        4000
cell02    0.219  0.014   0.193  0.246  45        1000
cell16    0.255  0.014   0.227  0.282  58        1000
cell22    0.287  0.011   0.266  0.308  48        4000
cell21    0.275  0.014   0.249  0.302  47        1000
cell04    0.144  0.024   0.097  0.191  54        1000
cell14    0.292  0.021   0.252  0.333  43        4000
cell19    0.111  0.021   0.069  0.153  38        2000
cell19    0.235  0.027   0.181  0.289  39        2000
cell07    0.275  0.025   0.226  0.325  39        2000
cell13    0.099  0.047   0.006  0.192  40        500
cell03    0.093  0.025   0.044  0.142  51        4000
```

### Step 29: segmenting epochs

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell24    0.196  0.021   0.155  0.238  57        2000
cell01    0.244  0.025   0.196  0.293  52        2000
cell06    0.257  0.036   0.186  0.328  43        2000
cell16    0.090  0.046   -0.001  0.180  57        4000
cell22    0.230  0.028   0.176  0.284  45        1000
cell19    0.270  0.017   0.236  0.303  46        4000
cell15    0.157  0.023   0.111  0.202  57        1000
cell02    0.141  0.044   0.054  0.227  55        1000
cell05    0.140  0.028   0.086  0.194  54        2000
cell13    0.091  0.046   0.002  0.181  42        4000
cell22    0.130  0.021   0.089  0.171  53        4000
cell01    0.141  0.017   0.108  0.174  53        500
```

While auditing the holding potential column for cell20, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.104, stderr 0.014, n = 41). While bootstrapping the CI for cell05, the coefficient tracked epoch count more closely than duration (coefficient 0.307, stderr 0.027, n = 45). While auditing the holding potential column for cell19, the coefficient tracked epoch count more closely than duration (coefficient 0.250, stderr 0.024, n = 51). While comparing per-cell orderings for cell04, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.165, stderr 0.036, n = 39).

While fitting the one-lag kernel for cell17, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.273, stderr 0.043, n = 38). While re-exporting the raw traces for cell17, the CI narrowed by roughly a tenth (coefficient 0.085, stderr 0.025, n = 42). While segmenting epochs for cell05, two cells fell out of the usable range (coefficient 0.241, stderr 0.032, n = 50). Parking this until the re-segmentation lands.

```python
coefs = fit_per_cell(rows, threshold=0.58)
lo, hi = ci(coefs, seed=2)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 30: auditing the holding potential column

```python
coefs = fit_per_cell(rows, threshold=0.79)
lo, hi = ci(coefs, seed=59)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While re-running with a tighter segmentation threshold for cell04, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.296, stderr 0.013, n = 48). While comparing per-cell orderings for cell09, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.194, stderr 0.049, n = 38). While re-exporting the raw traces for cell04, nothing in the figure changed at print size (coefficient 0.182, stderr 0.047, n = 56).

While bootstrapping the CI for cell24, nothing in the figure changed at print size (coefficient 0.098, stderr 0.030, n = 50). While comparing per-cell orderings for cell23, nothing in the figure changed at print size (coefficient 0.285, stderr 0.035, n = 49). While fitting the one-lag kernel for cell16, the estimate moved less than one standard error (coefficient 0.089, stderr 0.039, n = 56). While re-running with a tighter segmentation threshold for cell11, the coefficient tracked epoch count more closely than duration (coefficient 0.306, stderr 0.048, n = 47).

### Step 31: re-running with a tighter segmentation threshold

```python
coefs = fit_per_cell(rows, threshold=0.38)
lo, hi = ci(coefs, seed=97)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```python
coefs = fit_per_cell(rows, threshold=0.54)
lo, hi = ci(coefs, seed=99)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```python
coefs = fit_per_cell(rows, threshold=0.41)
lo, hi = ci(coefs, seed=51)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While fitting the one-lag kernel for cell16, the coefficient tracked epoch count more closely than duration (coefficient 0.286, stderr 0.026, n = 50). While auditing the holding potential column for cell14, the estimate moved less than one standard error (coefficient 0.235, stderr 0.019, n = 55). While segmenting epochs for cell11, the estimate moved less than one standard error (coefficient 0.199, stderr 0.030, n = 57). While fitting the one-lag kernel for cell20, the estimate moved less than one standard error (coefficient 0.307, stderr 0.035, n = 55). While checking residual autocorrelation for cell13, the coefficient tracked epoch count more closely than duration (coefficient 0.286, stderr 0.040, n = 58). This is the part that will need a real statistical argument.

### Step 32: re-exporting the raw traces

```python
coefs = fit_per_cell(rows, threshold=0.47)
lo, hi = ci(coefs, seed=97)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell10    0.188  0.039   0.111  0.265  46        2000
cell02    0.290  0.034   0.224  0.357  56        2000
cell12    0.206  0.050   0.109  0.304  42        500
cell05    0.203  0.024   0.155  0.250  40        4000
cell04    0.142  0.027   0.088  0.195  48        2000
cell13    0.109  0.032   0.046  0.171  49        1000
cell23    0.261  0.049   0.165  0.357  42        2000
cell13    0.227  0.017   0.194  0.261  44        2000
cell10    0.270  0.016   0.239  0.302  41        1000
cell23    0.269  0.033   0.204  0.334  45        2000
cell22    0.094  0.040   0.015  0.172  54        500
cell17    0.087  0.021   0.045  0.128  52        500
```

### Step 33: re-running with a tighter segmentation threshold

While auditing the holding potential column for cell16, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.119, stderr 0.014, n = 43). While bootstrapping the CI for cell21, the estimate moved less than one standard error (coefficient 0.089, stderr 0.034, n = 44). While fitting the one-lag kernel for cell16, the coefficient tracked epoch count more closely than duration (coefficient 0.232, stderr 0.045, n = 48). This is the part that will need a real statistical argument.

While checking residual autocorrelation for cell07, the CI narrowed by roughly a tenth (coefficient 0.248, stderr 0.029, n = 52). While re-exporting the raw traces for cell15, the coefficient tracked epoch count more closely than duration (coefficient 0.188, stderr 0.043, n = 54). While auditing the holding potential column for cell16, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.242, stderr 0.025, n = 57).

While fitting the one-lag kernel for cell10, the coefficient tracked epoch count more closely than duration (coefficient 0.233, stderr 0.027, n = 49). While re-running with a tighter segmentation threshold for cell06, two cells fell out of the usable range (coefficient 0.188, stderr 0.033, n = 57). While fitting the one-lag kernel for cell06, the coefficient tracked epoch count more closely than duration (coefficient 0.163, stderr 0.048, n = 52).

While segmenting epochs for cell21, the CI narrowed by roughly a tenth (coefficient 0.277, stderr 0.014, n = 51). While fitting the one-lag kernel for cell16, the CI narrowed by roughly a tenth (coefficient 0.237, stderr 0.034, n = 41). While checking residual autocorrelation for cell13, the ordering of cells was preserved (coefficient 0.267, stderr 0.042, n = 41). While segmenting epochs for cell14, two cells fell out of the usable range (coefficient 0.113, stderr 0.016, n = 48). While bootstrapping the CI for cell19, the estimate moved less than one standard error (coefficient 0.190, stderr 0.046, n = 56). Worth noting for the writeup, though not a result on its own.

### Step 34: bootstrapping the CI

```python
coefs = fit_per_cell(rows, threshold=0.31)
lo, hi = ci(coefs, seed=84)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell08    0.153  0.030   0.095  0.211  46        4000
cell19    0.133  0.035   0.064  0.201  40        4000
cell02    0.233  0.011   0.211  0.254  41        1000
cell08    0.295  0.043   0.210  0.380  50        1000
cell03    0.300  0.015   0.272  0.329  44        1000
cell05    0.195  0.029   0.138  0.251  58        2000
cell24    0.202  0.026   0.151  0.252  40        500
cell10    0.197  0.050   0.100  0.294  38        500
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell09    0.226  0.017   0.193  0.258  51        4000
cell06    0.204  0.042   0.122  0.286  53        2000
cell10    0.110  0.013   0.085  0.136  46        500
cell02    0.273  0.018   0.237  0.308  55        1000
cell06    0.196  0.044   0.110  0.283  45        2000
cell20    0.209  0.041   0.130  0.289  41        1000
cell16    0.204  0.022   0.161  0.247  57        500
cell11    0.103  0.016   0.071  0.134  56        1000
cell24    0.144  0.020   0.105  0.183  49        1000
cell14    0.166  0.048   0.071  0.260  51        2000
cell06    0.212  0.020   0.172  0.252  55        500
```

### Step 35: auditing the holding potential column

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell21    0.247  0.033   0.182  0.312  46        500
cell02    0.222  0.014   0.194  0.249  57        1000
cell07    0.082  0.050   -0.016  0.180  53        4000
cell22    0.204  0.036   0.133  0.275  53        4000
cell03    0.197  0.039   0.121  0.274  48        500
cell05    0.191  0.012   0.167  0.216  45        500
```

While segmenting epochs for cell11, the coefficient tracked epoch count more closely than duration (coefficient 0.251, stderr 0.026, n = 51). While comparing per-cell orderings for cell19, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.233, stderr 0.040, n = 42). While re-exporting the raw traces for cell09, the CI narrowed by roughly a tenth (coefficient 0.175, stderr 0.025, n = 56). While checking residual autocorrelation for cell11, the estimate moved less than one standard error (coefficient 0.264, stderr 0.046, n = 47). While re-running with a tighter segmentation threshold for cell24, two cells fell out of the usable range (coefficient 0.205, stderr 0.030, n = 39).

While re-running with a tighter segmentation threshold for cell14, two cells fell out of the usable range (coefficient 0.274, stderr 0.022, n = 51). While bootstrapping the CI for cell07, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.171, stderr 0.039, n = 49). While checking residual autocorrelation for cell01, the ordering of cells was preserved (coefficient 0.156, stderr 0.029, n = 57). While comparing per-cell orderings for cell09, the CI narrowed by roughly a tenth (coefficient 0.153, stderr 0.017, n = 51). While comparing per-cell orderings for cell01, two cells fell out of the usable range (coefficient 0.252, stderr 0.045, n = 38). While segmenting epochs for cell12, the estimate moved less than one standard error (coefficient 0.251, stderr 0.032, n = 39). Noted and moved on; it does not change the decision.

### Step 36: bootstrapping the CI

While segmenting epochs for cell10, the ordering of cells was preserved (coefficient 0.228, stderr 0.025, n = 42). While segmenting epochs for cell09, the CI narrowed by roughly a tenth (coefficient 0.174, stderr 0.018, n = 43). While segmenting epochs for cell03, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.249, stderr 0.031, n = 52). While re-exporting the raw traces for cell04, the ordering of cells was preserved (coefficient 0.298, stderr 0.010, n = 42).

```python
coefs = fit_per_cell(rows, threshold=0.46)
lo, hi = ci(coefs, seed=46)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While auditing the holding potential column for cell01, nothing in the figure changed at print size (coefficient 0.290, stderr 0.017, n = 40). While comparing per-cell orderings for cell21, the CI narrowed by roughly a tenth (coefficient 0.190, stderr 0.047, n = 39). While checking residual autocorrelation for cell14, two cells fell out of the usable range (coefficient 0.134, stderr 0.012, n = 51). While re-exporting the raw traces for cell06, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.168, stderr 0.049, n = 54). While comparing per-cell orderings for cell07, the CI narrowed by roughly a tenth (coefficient 0.239, stderr 0.029, n = 40).

### Step 37: checking residual autocorrelation

While re-running with a tighter segmentation threshold for cell20, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.121, stderr 0.034, n = 48). While re-running with a tighter segmentation threshold for cell13, nothing in the figure changed at print size (coefficient 0.087, stderr 0.033, n = 43). While re-exporting the raw traces for cell18, two cells fell out of the usable range (coefficient 0.147, stderr 0.032, n = 39). While re-running with a tighter segmentation threshold for cell02, the estimate moved less than one standard error (coefficient 0.141, stderr 0.045, n = 38). While comparing per-cell orderings for cell22, the estimate moved less than one standard error (coefficient 0.297, stderr 0.023, n = 45).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell06    0.158  0.049   0.061  0.255  50        500
cell10    0.272  0.018   0.236  0.308  45        1000
cell17    0.230  0.023   0.184  0.275  57        4000
cell13    0.238  0.047   0.146  0.330  50        1000
cell04    0.111  0.029   0.053  0.168  52        2000
cell01    0.262  0.020   0.223  0.300  48        2000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell19    0.301  0.015   0.271  0.331  58        1000
cell02    0.086  0.030   0.027  0.146  47        1000
cell11    0.200  0.012   0.177  0.224  39        2000
cell09    0.114  0.032   0.052  0.176  40        1000
cell24    0.160  0.041   0.079  0.241  43        4000
cell16    0.085  0.016   0.053  0.117  45        1000
cell05    0.208  0.042   0.127  0.290  48        2000
cell21    0.148  0.049   0.052  0.245  55        500
cell18    0.308  0.016   0.277  0.340  38        1000
cell09    0.245  0.016   0.214  0.276  53        2000
cell13    0.260  0.049   0.165  0.356  44        2000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell01    0.299  0.045   0.212  0.387  39        1000
cell14    0.235  0.046   0.144  0.326  56        500
cell07    0.107  0.042   0.025  0.189  43        4000
cell13    0.250  0.030   0.192  0.308  41        1000
cell06    0.102  0.028   0.047  0.156  46        2000
cell14    0.108  0.028   0.053  0.162  49        1000
```

### Step 38: auditing the holding potential column

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell22    0.135  0.047   0.043  0.228  51        4000
cell23    0.297  0.015   0.268  0.326  53        2000
cell07    0.280  0.034   0.214  0.347  40        4000
cell23    0.212  0.011   0.191  0.233  44        500
cell11    0.173  0.011   0.151  0.194  39        4000
cell24    0.208  0.011   0.186  0.231  48        500
cell09    0.125  0.028   0.070  0.180  44        4000
cell04    0.298  0.028   0.242  0.353  47        2000
cell04    0.282  0.024   0.235  0.328  39        1000
cell05    0.167  0.028   0.112  0.222  52        1000
cell12    0.142  0.014   0.116  0.169  50        1000
cell10    0.082  0.023   0.037  0.126  39        1000
cell05    0.258  0.036   0.188  0.328  52        1000
cell18    0.154  0.036   0.084  0.224  52        1000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell17    0.283  0.040   0.206  0.361  40        1000
cell21    0.099  0.026   0.049  0.150  38        500
cell17    0.205  0.050   0.108  0.303  41        2000
cell24    0.137  0.020   0.097  0.176  58        500
cell03    0.148  0.025   0.099  0.198  41        4000
cell14    0.184  0.032   0.122  0.247  54        4000
cell22    0.219  0.017   0.186  0.252  49        4000
```

```python
coefs = fit_per_cell(rows, threshold=0.56)
lo, hi = ci(coefs, seed=40)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 39: comparing per-cell orderings

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell19    0.154  0.018   0.119  0.190  56        2000
cell17    0.142  0.049   0.047  0.238  58        1000
cell03    0.128  0.035   0.060  0.196  53        4000
cell03    0.132  0.037   0.059  0.205  38        500
cell21    0.261  0.032   0.199  0.324  49        500
cell06    0.092  0.020   0.053  0.131  43        4000
cell11    0.097  0.038   0.022  0.171  49        4000
cell24    0.263  0.048   0.169  0.358  39        2000
cell14    0.287  0.033   0.222  0.352  38        1000
cell19    0.088  0.042   0.006  0.169  51        1000
cell23    0.081  0.041   0.002  0.161  44        2000
cell11    0.303  0.028   0.248  0.357  54        4000
```

While comparing per-cell orderings for cell18, the CI narrowed by roughly a tenth (coefficient 0.279, stderr 0.020, n = 40). While fitting the one-lag kernel for cell21, the CI narrowed by roughly a tenth (coefficient 0.209, stderr 0.024, n = 40). While bootstrapping the CI for cell01, the estimate moved less than one standard error (coefficient 0.120, stderr 0.016, n = 42). While auditing the holding potential column for cell14, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.146, stderr 0.024, n = 55). While bootstrapping the CI for cell19, nothing in the figure changed at print size (coefficient 0.210, stderr 0.027, n = 48). While auditing the holding potential column for cell03, the CI narrowed by roughly a tenth (coefficient 0.177, stderr 0.026, n = 55). Noted and moved on; it does not change the decision.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell04    0.231  0.049   0.135  0.327  41        4000
cell03    0.166  0.029   0.110  0.222  42        4000
cell16    0.259  0.044   0.174  0.345  50        1000
cell20    0.159  0.037   0.087  0.231  40        2000
cell18    0.271  0.039   0.194  0.348  46        4000
cell15    0.140  0.049   0.044  0.237  42        1000
cell17    0.161  0.013   0.135  0.187  43        4000
cell03    0.305  0.011   0.284  0.325  46        1000
cell21    0.306  0.029   0.248  0.363  43        4000
cell07    0.305  0.013   0.280  0.331  45        4000
```

### Step 40: re-exporting the raw traces

While segmenting epochs for cell11, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.208, stderr 0.035, n = 46). While auditing the holding potential column for cell02, the estimate moved less than one standard error (coefficient 0.295, stderr 0.018, n = 44). While comparing per-cell orderings for cell01, two cells fell out of the usable range (coefficient 0.196, stderr 0.046, n = 48).

While segmenting epochs for cell12, the estimate moved less than one standard error (coefficient 0.182, stderr 0.028, n = 43). While bootstrapping the CI for cell22, the coefficient tracked epoch count more closely than duration (coefficient 0.250, stderr 0.018, n = 44). While re-running with a tighter segmentation threshold for cell17, the ordering of cells was preserved (coefficient 0.134, stderr 0.013, n = 43). While auditing the holding potential column for cell19, the coefficient tracked epoch count more closely than duration (coefficient 0.221, stderr 0.048, n = 43). While checking residual autocorrelation for cell04, the ordering of cells was preserved (coefficient 0.257, stderr 0.012, n = 50). Noted and moved on; it does not change the decision.

While comparing per-cell orderings for cell13, the coefficient tracked epoch count more closely than duration (coefficient 0.172, stderr 0.033, n = 45). While comparing per-cell orderings for cell10, the coefficient tracked epoch count more closely than duration (coefficient 0.146, stderr 0.045, n = 48). While re-exporting the raw traces for cell20, two cells fell out of the usable range (coefficient 0.125, stderr 0.027, n = 47). While checking residual autocorrelation for cell17, the coefficient tracked epoch count more closely than duration (coefficient 0.294, stderr 0.028, n = 54).

### Step 41: fitting the one-lag kernel

While comparing per-cell orderings for cell16, two cells fell out of the usable range (coefficient 0.129, stderr 0.045, n = 45). While re-exporting the raw traces for cell11, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.125, stderr 0.044, n = 49). While auditing the holding potential column for cell04, two cells fell out of the usable range (coefficient 0.247, stderr 0.030, n = 53).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell22    0.147  0.036   0.076  0.218  46        500
cell19    0.296  0.036   0.225  0.366  42        2000
cell18    0.106  0.012   0.083  0.129  54        500
cell07    0.223  0.045   0.136  0.311  45        1000
cell14    0.149  0.037   0.076  0.221  53        4000
cell06    0.306  0.021   0.265  0.347  47        2000
cell13    0.248  0.034   0.182  0.315  48        4000
cell18    0.143  0.025   0.095  0.192  41        500
cell19    0.168  0.026   0.116  0.220  38        2000
cell14    0.144  0.023   0.099  0.190  41        1000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell11    0.086  0.024   0.039  0.134  47        2000
cell19    0.246  0.034   0.178  0.313  53        1000
cell07    0.138  0.045   0.050  0.225  58        4000
cell01    0.234  0.016   0.203  0.265  43        2000
cell18    0.295  0.041   0.214  0.376  39        1000
cell19    0.163  0.013   0.138  0.188  53        500
cell10    0.169  0.013   0.143  0.194  42        4000
cell03    0.302  0.036   0.232  0.372  46        4000
```

