# Prior session 5 of 20

Transcript of an earlier working session on the history-kernel analysis.

### Step 1: re-exporting the raw traces

While segmenting epochs for cell05, the estimate moved less than one standard error (coefficient 0.152, stderr 0.017, n = 45). While auditing the holding potential column for cell17, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.144, stderr 0.018, n = 50). While checking residual autocorrelation for cell02, the estimate moved less than one standard error (coefficient 0.246, stderr 0.019, n = 49). While fitting the one-lag kernel for cell02, nothing in the figure changed at print size (coefficient 0.120, stderr 0.013, n = 39). While re-exporting the raw traces for cell13, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.147, stderr 0.049, n = 41).

While re-exporting the raw traces for cell19, nothing in the figure changed at print size (coefficient 0.203, stderr 0.021, n = 38). While re-running with a tighter segmentation threshold for cell13, the coefficient tracked epoch count more closely than duration (coefficient 0.285, stderr 0.034, n = 41). While segmenting epochs for cell02, the estimate moved less than one standard error (coefficient 0.183, stderr 0.020, n = 53). Parking this until the re-segmentation lands.

### Step 2: fitting the one-lag kernel

```python
coefs = fit_per_cell(rows, threshold=0.73)
lo, hi = ci(coefs, seed=55)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```python
coefs = fit_per_cell(rows, threshold=0.69)
lo, hi = ci(coefs, seed=35)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 3: comparing per-cell orderings

While segmenting epochs for cell12, the coefficient tracked epoch count more closely than duration (coefficient 0.167, stderr 0.033, n = 40). While checking residual autocorrelation for cell24, the ordering of cells was preserved (coefficient 0.216, stderr 0.028, n = 50). While checking residual autocorrelation for cell06, two cells fell out of the usable range (coefficient 0.227, stderr 0.034, n = 47).

While auditing the holding potential column for cell22, two cells fell out of the usable range (coefficient 0.305, stderr 0.032, n = 42). While re-running with a tighter segmentation threshold for cell23, the coefficient tracked epoch count more closely than duration (coefficient 0.249, stderr 0.041, n = 48). While checking residual autocorrelation for cell14, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.252, stderr 0.047, n = 53).

### Step 4: re-exporting the raw traces

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell18    0.228  0.050   0.130  0.325  54        500
cell03    0.236  0.025   0.186  0.286  51        500
cell01    0.224  0.040   0.146  0.302  56        1000
cell19    0.309  0.018   0.274  0.345  45        500
cell08    0.127  0.014   0.100  0.154  51        2000
cell12    0.276  0.022   0.233  0.320  40        2000
cell12    0.192  0.024   0.146  0.239  41        500
cell13    0.105  0.048   0.011  0.199  53        500
```

```python
coefs = fit_per_cell(rows, threshold=0.70)
lo, hi = ci(coefs, seed=81)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell12    0.127  0.041   0.047  0.207  49        500
cell04    0.251  0.028   0.197  0.305  39        1000
cell12    0.189  0.010   0.170  0.209  39        2000
cell05    0.179  0.033   0.114  0.244  38        2000
cell15    0.105  0.038   0.030  0.180  39        2000
cell06    0.138  0.045   0.049  0.226  45        2000
cell06    0.229  0.022   0.187  0.272  56        1000
```

### Step 5: checking residual autocorrelation

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell22    0.268  0.031   0.206  0.329  57        500
cell21    0.171  0.016   0.139  0.202  48        2000
cell22    0.246  0.041   0.165  0.327  45        2000
cell16    0.187  0.016   0.156  0.218  39        1000
cell12    0.248  0.045   0.159  0.337  48        2000
cell16    0.304  0.042   0.222  0.386  52        4000
cell09    0.110  0.030   0.052  0.168  45        2000
cell20    0.200  0.016   0.168  0.231  48        1000
cell09    0.284  0.044   0.197  0.371  57        4000
cell17    0.308  0.014   0.280  0.336  46        2000
cell14    0.201  0.039   0.124  0.277  46        500
cell13    0.249  0.018   0.213  0.285  51        2000
cell24    0.192  0.039   0.116  0.268  51        500
```

```python
coefs = fit_per_cell(rows, threshold=0.38)
lo, hi = ci(coefs, seed=44)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 6: auditing the holding potential column

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell23    0.106  0.024   0.059  0.154  49        2000
cell24    0.089  0.026   0.038  0.139  58        2000
cell14    0.189  0.030   0.131  0.247  40        4000
cell05    0.254  0.050   0.156  0.351  42        4000
cell04    0.279  0.033   0.214  0.344  54        1000
cell10    0.177  0.049   0.081  0.274  39        4000
cell12    0.232  0.024   0.186  0.279  44        4000
cell08    0.135  0.029   0.078  0.193  57        500
cell13    0.168  0.048   0.074  0.262  46        500
cell09    0.172  0.020   0.132  0.212  48        4000
cell07    0.253  0.027   0.201  0.305  39        2000
cell14    0.201  0.033   0.137  0.265  39        1000
cell01    0.130  0.017   0.097  0.163  48        4000
cell16    0.198  0.034   0.132  0.265  39        500
```

While auditing the holding potential column for cell07, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.274, stderr 0.043, n = 39). While checking residual autocorrelation for cell21, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.120, stderr 0.041, n = 48). While re-exporting the raw traces for cell16, the CI narrowed by roughly a tenth (coefficient 0.204, stderr 0.023, n = 47).

While segmenting epochs for cell13, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.204, stderr 0.022, n = 44). While checking residual autocorrelation for cell07, two cells fell out of the usable range (coefficient 0.254, stderr 0.018, n = 57). While re-exporting the raw traces for cell10, the estimate moved less than one standard error (coefficient 0.260, stderr 0.013, n = 43). While bootstrapping the CI for cell10, the CI narrowed by roughly a tenth (coefficient 0.168, stderr 0.041, n = 40). While auditing the holding potential column for cell04, the CI narrowed by roughly a tenth (coefficient 0.278, stderr 0.045, n = 56). While auditing the holding potential column for cell12, nothing in the figure changed at print size (coefficient 0.258, stderr 0.042, n = 40).

### Step 7: checking residual autocorrelation

While bootstrapping the CI for cell13, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.236, stderr 0.030, n = 58). While re-running with a tighter segmentation threshold for cell05, nothing in the figure changed at print size (coefficient 0.146, stderr 0.033, n = 48). While segmenting epochs for cell01, the coefficient tracked epoch count more closely than duration (coefficient 0.236, stderr 0.028, n = 44). While re-running with a tighter segmentation threshold for cell20, two cells fell out of the usable range (coefficient 0.206, stderr 0.036, n = 47).

While fitting the one-lag kernel for cell03, two cells fell out of the usable range (coefficient 0.103, stderr 0.026, n = 56). While segmenting epochs for cell18, the estimate moved less than one standard error (coefficient 0.210, stderr 0.014, n = 48). While re-running with a tighter segmentation threshold for cell03, the estimate moved less than one standard error (coefficient 0.139, stderr 0.045, n = 54). While fitting the one-lag kernel for cell21, the estimate moved less than one standard error (coefficient 0.164, stderr 0.049, n = 46). While re-exporting the raw traces for cell11, the coefficient tracked epoch count more closely than duration (coefficient 0.114, stderr 0.016, n = 46).

While comparing per-cell orderings for cell10, the CI narrowed by roughly a tenth (coefficient 0.178, stderr 0.050, n = 40). While fitting the one-lag kernel for cell10, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.105, stderr 0.015, n = 48). While segmenting epochs for cell01, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.111, stderr 0.045, n = 45). While checking residual autocorrelation for cell23, two cells fell out of the usable range (coefficient 0.128, stderr 0.044, n = 52). While fitting the one-lag kernel for cell08, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.239, stderr 0.010, n = 44). While segmenting epochs for cell06, nothing in the figure changed at print size (coefficient 0.167, stderr 0.026, n = 40). This is the part that will need a real statistical argument.

While bootstrapping the CI for cell01, the CI narrowed by roughly a tenth (coefficient 0.249, stderr 0.020, n = 38). While fitting the one-lag kernel for cell08, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.155, stderr 0.045, n = 45). While bootstrapping the CI for cell09, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.197, stderr 0.027, n = 44). While checking residual autocorrelation for cell23, the coefficient tracked epoch count more closely than duration (coefficient 0.174, stderr 0.010, n = 50). Parking this until the re-segmentation lands.

### Step 8: re-running with a tighter segmentation threshold

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell07    0.125  0.050   0.027  0.223  47        2000
cell09    0.103  0.040   0.025  0.182  50        500
cell09    0.208  0.040   0.131  0.286  48        4000
cell15    0.209  0.013   0.185  0.234  53        2000
cell13    0.260  0.030   0.201  0.319  41        2000
cell17    0.127  0.028   0.073  0.182  39        500
cell07    0.172  0.022   0.128  0.216  41        500
cell17    0.266  0.033   0.201  0.330  56        4000
```

While comparing per-cell orderings for cell14, the ordering of cells was preserved (coefficient 0.273, stderr 0.027, n = 55). While segmenting epochs for cell24, the CI narrowed by roughly a tenth (coefficient 0.097, stderr 0.024, n = 57). While comparing per-cell orderings for cell18, nothing in the figure changed at print size (coefficient 0.150, stderr 0.043, n = 56). While segmenting epochs for cell01, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.178, stderr 0.047, n = 51). While fitting the one-lag kernel for cell18, nothing in the figure changed at print size (coefficient 0.259, stderr 0.038, n = 56). Worth noting for the writeup, though not a result on its own.

### Step 9: re-running with a tighter segmentation threshold

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell11    0.277  0.038   0.203  0.351  51        1000
cell05    0.146  0.043   0.061  0.231  43        1000
cell15    0.251  0.028   0.195  0.306  42        4000
cell18    0.199  0.012   0.176  0.222  55        2000
cell23    0.115  0.049   0.018  0.211  55        2000
cell08    0.092  0.030   0.033  0.152  47        1000
cell18    0.124  0.034   0.057  0.191  42        500
cell21    0.137  0.029   0.081  0.193  50        500
cell07    0.254  0.029   0.198  0.311  49        500
cell06    0.249  0.010   0.229  0.270  54        4000
cell24    0.197  0.038   0.123  0.271  57        1000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell03    0.086  0.022   0.043  0.130  41        500
cell11    0.197  0.027   0.144  0.250  46        500
cell15    0.155  0.033   0.091  0.218  52        4000
cell10    0.115  0.016   0.084  0.147  50        4000
cell07    0.133  0.048   0.038  0.228  53        500
cell19    0.199  0.034   0.133  0.265  53        4000
cell13    0.219  0.033   0.156  0.283  54        4000
cell16    0.149  0.012   0.126  0.172  46        1000
cell12    0.092  0.019   0.056  0.129  56        2000
cell24    0.117  0.037   0.045  0.189  51        2000
cell08    0.132  0.010   0.113  0.152  58        2000
cell20    0.143  0.034   0.078  0.209  57        1000
```

While re-running with a tighter segmentation threshold for cell20, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.195, stderr 0.023, n = 55). While re-exporting the raw traces for cell24, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.088, stderr 0.031, n = 49). While comparing per-cell orderings for cell08, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.188, stderr 0.035, n = 56). While re-exporting the raw traces for cell02, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.141, stderr 0.017, n = 46). While re-running with a tighter segmentation threshold for cell19, the estimate moved less than one standard error (coefficient 0.222, stderr 0.012, n = 51). While fitting the one-lag kernel for cell20, the CI narrowed by roughly a tenth (coefficient 0.235, stderr 0.032, n = 44). Noted and moved on; it does not change the decision.

While checking residual autocorrelation for cell06, nothing in the figure changed at print size (coefficient 0.294, stderr 0.048, n = 40). While comparing per-cell orderings for cell01, nothing in the figure changed at print size (coefficient 0.219, stderr 0.018, n = 53). While checking residual autocorrelation for cell20, the estimate moved less than one standard error (coefficient 0.224, stderr 0.045, n = 44). Flagging it so it does not get rediscovered next week.

### Step 10: comparing per-cell orderings

```python
coefs = fit_per_cell(rows, threshold=0.55)
lo, hi = ci(coefs, seed=74)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While auditing the holding potential column for cell24, nothing in the figure changed at print size (coefficient 0.176, stderr 0.049, n = 46). While re-exporting the raw traces for cell13, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.234, stderr 0.012, n = 51). While re-running with a tighter segmentation threshold for cell07, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.247, stderr 0.033, n = 52). While checking residual autocorrelation for cell18, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.279, stderr 0.012, n = 55). While re-running with a tighter segmentation threshold for cell20, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.128, stderr 0.011, n = 38).

```python
coefs = fit_per_cell(rows, threshold=0.33)
lo, hi = ci(coefs, seed=98)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 11: segmenting epochs

While bootstrapping the CI for cell19, the CI narrowed by roughly a tenth (coefficient 0.172, stderr 0.030, n = 42). While re-exporting the raw traces for cell03, two cells fell out of the usable range (coefficient 0.229, stderr 0.034, n = 44). While fitting the one-lag kernel for cell12, the estimate moved less than one standard error (coefficient 0.095, stderr 0.010, n = 56). While bootstrapping the CI for cell08, the coefficient tracked epoch count more closely than duration (coefficient 0.157, stderr 0.010, n = 57). While segmenting epochs for cell07, the coefficient tracked epoch count more closely than duration (coefficient 0.135, stderr 0.040, n = 47).

While re-running with a tighter segmentation threshold for cell11, the estimate moved less than one standard error (coefficient 0.275, stderr 0.031, n = 49). While segmenting epochs for cell16, nothing in the figure changed at print size (coefficient 0.226, stderr 0.046, n = 47). While comparing per-cell orderings for cell12, two cells fell out of the usable range (coefficient 0.257, stderr 0.016, n = 51).

```python
coefs = fit_per_cell(rows, threshold=0.52)
lo, hi = ci(coefs, seed=1)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 12: segmenting epochs

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell03    0.245  0.035   0.176  0.313  54        500
cell24    0.115  0.035   0.047  0.183  42        2000
cell08    0.237  0.046   0.146  0.328  47        500
cell15    0.281  0.043   0.197  0.366  44        4000
cell18    0.117  0.036   0.047  0.188  49        2000
cell12    0.264  0.017   0.230  0.297  54        4000
cell23    0.107  0.045   0.019  0.194  51        500
cell03    0.131  0.040   0.052  0.209  55        4000
cell24    0.111  0.032   0.048  0.175  54        2000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell03    0.201  0.013   0.175  0.227  43        500
cell22    0.258  0.042   0.176  0.341  53        500
cell02    0.301  0.046   0.211  0.391  46        500
cell15    0.172  0.022   0.129  0.216  54        4000
cell20    0.108  0.022   0.065  0.151  46        4000
cell18    0.179  0.033   0.114  0.244  48        2000
```

```python
coefs = fit_per_cell(rows, threshold=0.33)
lo, hi = ci(coefs, seed=41)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```python
coefs = fit_per_cell(rows, threshold=0.72)
lo, hi = ci(coefs, seed=16)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 13: comparing per-cell orderings

```python
coefs = fit_per_cell(rows, threshold=0.68)
lo, hi = ci(coefs, seed=92)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While fitting the one-lag kernel for cell11, the coefficient tracked epoch count more closely than duration (coefficient 0.145, stderr 0.015, n = 50). While bootstrapping the CI for cell23, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.245, stderr 0.034, n = 45). While re-running with a tighter segmentation threshold for cell09, nothing in the figure changed at print size (coefficient 0.099, stderr 0.043, n = 48). While re-running with a tighter segmentation threshold for cell11, two cells fell out of the usable range (coefficient 0.274, stderr 0.047, n = 49). Worth noting for the writeup, though not a result on its own.

While checking residual autocorrelation for cell10, nothing in the figure changed at print size (coefficient 0.199, stderr 0.032, n = 45). While bootstrapping the CI for cell03, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.185, stderr 0.049, n = 38). While comparing per-cell orderings for cell18, the coefficient tracked epoch count more closely than duration (coefficient 0.129, stderr 0.018, n = 48). While auditing the holding potential column for cell17, the coefficient tracked epoch count more closely than duration (coefficient 0.155, stderr 0.024, n = 57). Worth noting for the writeup, though not a result on its own.

### Step 14: comparing per-cell orderings

While re-exporting the raw traces for cell12, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.264, stderr 0.042, n = 51). While auditing the holding potential column for cell15, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.216, stderr 0.036, n = 58). While comparing per-cell orderings for cell07, the CI narrowed by roughly a tenth (coefficient 0.183, stderr 0.048, n = 53). While re-running with a tighter segmentation threshold for cell21, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.125, stderr 0.043, n = 47). While re-running with a tighter segmentation threshold for cell01, the ordering of cells was preserved (coefficient 0.103, stderr 0.037, n = 44).

While re-exporting the raw traces for cell05, nothing in the figure changed at print size (coefficient 0.162, stderr 0.016, n = 53). While comparing per-cell orderings for cell06, the CI narrowed by roughly a tenth (coefficient 0.087, stderr 0.031, n = 42). While fitting the one-lag kernel for cell11, two cells fell out of the usable range (coefficient 0.122, stderr 0.030, n = 49). While auditing the holding potential column for cell19, the ordering of cells was preserved (coefficient 0.263, stderr 0.022, n = 39). While segmenting epochs for cell12, the CI narrowed by roughly a tenth (coefficient 0.215, stderr 0.022, n = 44). Worth noting for the writeup, though not a result on its own.

While comparing per-cell orderings for cell23, nothing in the figure changed at print size (coefficient 0.205, stderr 0.036, n = 55). While checking residual autocorrelation for cell23, the estimate moved less than one standard error (coefficient 0.280, stderr 0.040, n = 56). While re-running with a tighter segmentation threshold for cell20, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.248, stderr 0.041, n = 46). While re-exporting the raw traces for cell10, nothing in the figure changed at print size (coefficient 0.156, stderr 0.039, n = 58). While bootstrapping the CI for cell10, the coefficient tracked epoch count more closely than duration (coefficient 0.214, stderr 0.038, n = 52). Worth noting for the writeup, though not a result on its own.

While checking residual autocorrelation for cell01, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.253, stderr 0.041, n = 44). While bootstrapping the CI for cell23, the coefficient tracked epoch count more closely than duration (coefficient 0.099, stderr 0.021, n = 44). While checking residual autocorrelation for cell08, the estimate moved less than one standard error (coefficient 0.159, stderr 0.010, n = 41). Noted and moved on; it does not change the decision.

### Step 15: bootstrapping the CI

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell13    0.293  0.020   0.254  0.333  40        4000
cell09    0.219  0.047   0.127  0.311  57        2000
cell23    0.140  0.023   0.095  0.186  48        500
cell13    0.260  0.021   0.218  0.302  53        4000
cell12    0.224  0.033   0.159  0.289  54        500
cell24    0.281  0.018   0.246  0.316  51        500
cell21    0.083  0.036   0.013  0.152  55        2000
cell13    0.233  0.013   0.207  0.259  42        500
cell19    0.191  0.024   0.144  0.238  58        2000
cell01    0.245  0.021   0.203  0.286  40        1000
cell24    0.280  0.020   0.242  0.319  53        2000
cell10    0.278  0.048   0.185  0.372  55        1000
```

While fitting the one-lag kernel for cell11, the estimate moved less than one standard error (coefficient 0.248, stderr 0.036, n = 52). While auditing the holding potential column for cell04, the coefficient tracked epoch count more closely than duration (coefficient 0.142, stderr 0.015, n = 43). While bootstrapping the CI for cell19, the ordering of cells was preserved (coefficient 0.087, stderr 0.027, n = 54). While comparing per-cell orderings for cell01, nothing in the figure changed at print size (coefficient 0.094, stderr 0.040, n = 43). While re-exporting the raw traces for cell19, the coefficient tracked epoch count more closely than duration (coefficient 0.119, stderr 0.012, n = 54). While fitting the one-lag kernel for cell10, nothing in the figure changed at print size (coefficient 0.267, stderr 0.013, n = 58). Parking this until the re-segmentation lands.

While comparing per-cell orderings for cell17, the ordering of cells was preserved (coefficient 0.260, stderr 0.011, n = 53). While segmenting epochs for cell19, the ordering of cells was preserved (coefficient 0.245, stderr 0.047, n = 51). While auditing the holding potential column for cell22, the estimate moved less than one standard error (coefficient 0.288, stderr 0.020, n = 38). While segmenting epochs for cell17, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.204, stderr 0.042, n = 42). Noted and moved on; it does not change the decision.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell13    0.200  0.043   0.116  0.284  56        500
cell05    0.165  0.020   0.125  0.205  48        2000
cell17    0.216  0.046   0.126  0.307  38        2000
cell23    0.164  0.019   0.126  0.201  55        4000
cell04    0.307  0.015   0.277  0.337  42        2000
cell24    0.131  0.034   0.065  0.198  49        4000
cell19    0.087  0.036   0.017  0.157  58        4000
cell24    0.269  0.037   0.196  0.343  58        4000
cell15    0.275  0.020   0.236  0.315  45        2000
cell14    0.092  0.042   0.010  0.173  47        500
cell06    0.087  0.041   0.007  0.168  49        2000
cell13    0.266  0.016   0.234  0.297  49        1000
cell22    0.281  0.026   0.231  0.332  38        500
```

### Step 16: checking residual autocorrelation

While re-exporting the raw traces for cell20, the coefficient tracked epoch count more closely than duration (coefficient 0.253, stderr 0.021, n = 54). While fitting the one-lag kernel for cell21, two cells fell out of the usable range (coefficient 0.219, stderr 0.037, n = 39). While comparing per-cell orderings for cell11, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.304, stderr 0.022, n = 44). While auditing the holding potential column for cell03, nothing in the figure changed at print size (coefficient 0.134, stderr 0.044, n = 49). While comparing per-cell orderings for cell17, the estimate moved less than one standard error (coefficient 0.308, stderr 0.043, n = 57). This is the part that will need a real statistical argument.

While segmenting epochs for cell13, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.302, stderr 0.036, n = 39). While re-running with a tighter segmentation threshold for cell02, the CI narrowed by roughly a tenth (coefficient 0.239, stderr 0.031, n = 49). While re-running with a tighter segmentation threshold for cell04, two cells fell out of the usable range (coefficient 0.225, stderr 0.034, n = 50). While re-exporting the raw traces for cell08, two cells fell out of the usable range (coefficient 0.095, stderr 0.045, n = 48). While auditing the holding potential column for cell16, the CI narrowed by roughly a tenth (coefficient 0.160, stderr 0.029, n = 40). While checking residual autocorrelation for cell04, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.166, stderr 0.025, n = 55).

While auditing the holding potential column for cell07, the coefficient tracked epoch count more closely than duration (coefficient 0.227, stderr 0.019, n = 41). While re-exporting the raw traces for cell01, the ordering of cells was preserved (coefficient 0.200, stderr 0.029, n = 57). While fitting the one-lag kernel for cell07, the ordering of cells was preserved (coefficient 0.179, stderr 0.022, n = 44). While segmenting epochs for cell03, the CI narrowed by roughly a tenth (coefficient 0.214, stderr 0.011, n = 40). While checking residual autocorrelation for cell11, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.116, stderr 0.020, n = 57). While auditing the holding potential column for cell04, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.160, stderr 0.027, n = 57).

While bootstrapping the CI for cell05, the estimate moved less than one standard error (coefficient 0.237, stderr 0.037, n = 46). While bootstrapping the CI for cell08, the coefficient tracked epoch count more closely than duration (coefficient 0.144, stderr 0.018, n = 51). While re-exporting the raw traces for cell10, the CI narrowed by roughly a tenth (coefficient 0.092, stderr 0.024, n = 47). While comparing per-cell orderings for cell09, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.291, stderr 0.010, n = 45). While bootstrapping the CI for cell16, nothing in the figure changed at print size (coefficient 0.186, stderr 0.020, n = 40). While fitting the one-lag kernel for cell20, nothing in the figure changed at print size (coefficient 0.268, stderr 0.018, n = 46).

### Step 17: bootstrapping the CI

```python
coefs = fit_per_cell(rows, threshold=0.48)
lo, hi = ci(coefs, seed=15)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While bootstrapping the CI for cell02, two cells fell out of the usable range (coefficient 0.112, stderr 0.041, n = 49). While bootstrapping the CI for cell14, the estimate moved less than one standard error (coefficient 0.274, stderr 0.032, n = 43). While fitting the one-lag kernel for cell21, the estimate moved less than one standard error (coefficient 0.269, stderr 0.017, n = 56).

### Step 18: comparing per-cell orderings

While re-running with a tighter segmentation threshold for cell03, the estimate moved less than one standard error (coefficient 0.176, stderr 0.035, n = 46). While segmenting epochs for cell12, the CI narrowed by roughly a tenth (coefficient 0.177, stderr 0.046, n = 56). While re-exporting the raw traces for cell01, two cells fell out of the usable range (coefficient 0.136, stderr 0.029, n = 55).

While bootstrapping the CI for cell18, the estimate moved less than one standard error (coefficient 0.099, stderr 0.027, n = 40). While auditing the holding potential column for cell05, the estimate moved less than one standard error (coefficient 0.123, stderr 0.047, n = 45). While re-exporting the raw traces for cell18, the ordering of cells was preserved (coefficient 0.151, stderr 0.039, n = 51). While auditing the holding potential column for cell11, the ordering of cells was preserved (coefficient 0.148, stderr 0.027, n = 38). While comparing per-cell orderings for cell24, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.228, stderr 0.042, n = 49).

```python
coefs = fit_per_cell(rows, threshold=0.54)
lo, hi = ci(coefs, seed=93)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 19: checking residual autocorrelation

While segmenting epochs for cell23, the coefficient tracked epoch count more closely than duration (coefficient 0.237, stderr 0.034, n = 46). While comparing per-cell orderings for cell22, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.131, stderr 0.019, n = 43). While re-exporting the raw traces for cell05, the coefficient tracked epoch count more closely than duration (coefficient 0.291, stderr 0.048, n = 44). While checking residual autocorrelation for cell07, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.289, stderr 0.023, n = 47). Flagging it so it does not get rediscovered next week.

While re-running with a tighter segmentation threshold for cell17, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.189, stderr 0.045, n = 42). While re-exporting the raw traces for cell01, the ordering of cells was preserved (coefficient 0.233, stderr 0.039, n = 44). While comparing per-cell orderings for cell03, the estimate moved less than one standard error (coefficient 0.100, stderr 0.031, n = 45). While segmenting epochs for cell19, the estimate moved less than one standard error (coefficient 0.231, stderr 0.027, n = 46).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell10    0.249  0.039   0.173  0.324  43        4000
cell23    0.206  0.033   0.141  0.270  47        4000
cell13    0.184  0.030   0.126  0.243  46        4000
cell15    0.118  0.047   0.025  0.211  47        4000
cell01    0.302  0.037   0.230  0.375  49        4000
cell24    0.092  0.023   0.046  0.137  40        2000
cell02    0.171  0.013   0.146  0.197  46        500
cell02    0.197  0.034   0.130  0.263  51        500
cell18    0.105  0.032   0.042  0.168  51        2000
cell21    0.226  0.025   0.177  0.276  38        4000
cell08    0.276  0.024   0.228  0.323  55        500
cell06    0.091  0.049   -0.004  0.187  44        500
cell23    0.255  0.011   0.232  0.277  50        2000
cell04    0.124  0.044   0.038  0.209  51        1000
```

### Step 20: re-running with a tighter segmentation threshold

```python
coefs = fit_per_cell(rows, threshold=0.75)
lo, hi = ci(coefs, seed=59)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While bootstrapping the CI for cell02, the ordering of cells was preserved (coefficient 0.195, stderr 0.018, n = 49). While auditing the holding potential column for cell23, the coefficient tracked epoch count more closely than duration (coefficient 0.309, stderr 0.023, n = 53). While bootstrapping the CI for cell20, the ordering of cells was preserved (coefficient 0.238, stderr 0.014, n = 42). While auditing the holding potential column for cell14, nothing in the figure changed at print size (coefficient 0.110, stderr 0.015, n = 45). While fitting the one-lag kernel for cell09, the CI narrowed by roughly a tenth (coefficient 0.162, stderr 0.011, n = 43).

### Step 21: checking residual autocorrelation

While fitting the one-lag kernel for cell02, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.295, stderr 0.046, n = 48). While auditing the holding potential column for cell17, the coefficient tracked epoch count more closely than duration (coefficient 0.254, stderr 0.014, n = 41). While auditing the holding potential column for cell23, the CI narrowed by roughly a tenth (coefficient 0.175, stderr 0.036, n = 39). While comparing per-cell orderings for cell10, the CI narrowed by roughly a tenth (coefficient 0.151, stderr 0.033, n = 51). While auditing the holding potential column for cell21, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.253, stderr 0.021, n = 52).

While re-exporting the raw traces for cell03, nothing in the figure changed at print size (coefficient 0.274, stderr 0.042, n = 44). While segmenting epochs for cell11, the estimate moved less than one standard error (coefficient 0.149, stderr 0.038, n = 55). While re-exporting the raw traces for cell21, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.098, stderr 0.035, n = 51). While fitting the one-lag kernel for cell06, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.295, stderr 0.034, n = 52). While comparing per-cell orderings for cell02, the CI narrowed by roughly a tenth (coefficient 0.106, stderr 0.013, n = 38). While bootstrapping the CI for cell24, the coefficient tracked epoch count more closely than duration (coefficient 0.140, stderr 0.014, n = 51).

While re-exporting the raw traces for cell22, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.110, stderr 0.013, n = 52). While segmenting epochs for cell01, the estimate moved less than one standard error (coefficient 0.285, stderr 0.039, n = 50). While segmenting epochs for cell04, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.198, stderr 0.033, n = 50). This is the part that will need a real statistical argument.

### Step 22: bootstrapping the CI

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell02    0.184  0.023   0.138  0.229  53        1000
cell02    0.180  0.021   0.140  0.221  55        2000
cell22    0.270  0.044   0.184  0.356  40        4000
cell11    0.294  0.037   0.221  0.367  41        500
cell18    0.204  0.033   0.139  0.269  57        500
cell18    0.275  0.031   0.213  0.336  52        2000
cell01    0.286  0.046   0.195  0.376  38        1000
cell22    0.124  0.033   0.060  0.189  38        500
cell21    0.286  0.036   0.216  0.357  40        500
cell03    0.267  0.048   0.172  0.361  50        2000
```

While checking residual autocorrelation for cell12, the CI narrowed by roughly a tenth (coefficient 0.150, stderr 0.049, n = 44). While segmenting epochs for cell05, nothing in the figure changed at print size (coefficient 0.268, stderr 0.037, n = 51). While comparing per-cell orderings for cell22, the CI narrowed by roughly a tenth (coefficient 0.123, stderr 0.039, n = 57). While fitting the one-lag kernel for cell23, the estimate moved less than one standard error (coefficient 0.204, stderr 0.040, n = 51). While segmenting epochs for cell07, two cells fell out of the usable range (coefficient 0.199, stderr 0.031, n = 40).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell14    0.095  0.013   0.069  0.120  51        2000
cell22    0.225  0.047   0.132  0.317  57        2000
cell07    0.226  0.022   0.183  0.270  57        1000
cell24    0.279  0.019   0.241  0.317  44        2000
cell08    0.283  0.041   0.201  0.364  48        2000
cell04    0.116  0.043   0.032  0.201  45        1000
cell19    0.280  0.037   0.208  0.353  52        1000
cell06    0.107  0.034   0.040  0.173  53        2000
cell18    0.151  0.038   0.077  0.226  52        4000
```

While segmenting epochs for cell13, the estimate moved less than one standard error (coefficient 0.123, stderr 0.042, n = 49). While re-running with a tighter segmentation threshold for cell08, the estimate moved less than one standard error (coefficient 0.234, stderr 0.042, n = 53). While segmenting epochs for cell16, nothing in the figure changed at print size (coefficient 0.246, stderr 0.021, n = 58). While fitting the one-lag kernel for cell21, two cells fell out of the usable range (coefficient 0.270, stderr 0.026, n = 43). While comparing per-cell orderings for cell01, nothing in the figure changed at print size (coefficient 0.213, stderr 0.020, n = 56). While comparing per-cell orderings for cell22, the ordering of cells was preserved (coefficient 0.268, stderr 0.014, n = 42).

### Step 23: auditing the holding potential column

While segmenting epochs for cell03, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.207, stderr 0.038, n = 42). While segmenting epochs for cell13, the ordering of cells was preserved (coefficient 0.087, stderr 0.043, n = 49). While segmenting epochs for cell15, the estimate moved less than one standard error (coefficient 0.163, stderr 0.042, n = 52).

While bootstrapping the CI for cell03, two cells fell out of the usable range (coefficient 0.119, stderr 0.026, n = 42). While re-exporting the raw traces for cell10, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.270, stderr 0.049, n = 43). While re-running with a tighter segmentation threshold for cell02, two cells fell out of the usable range (coefficient 0.238, stderr 0.019, n = 45). While re-exporting the raw traces for cell10, the estimate moved less than one standard error (coefficient 0.114, stderr 0.046, n = 44). Flagging it so it does not get rediscovered next week.

### Step 24: re-running with a tighter segmentation threshold

While auditing the holding potential column for cell01, the ordering of cells was preserved (coefficient 0.164, stderr 0.036, n = 41). While auditing the holding potential column for cell21, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.120, stderr 0.017, n = 53). While fitting the one-lag kernel for cell13, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.276, stderr 0.017, n = 48). While bootstrapping the CI for cell14, the coefficient tracked epoch count more closely than duration (coefficient 0.205, stderr 0.026, n = 53). Worth noting for the writeup, though not a result on its own.

While checking residual autocorrelation for cell01, the CI narrowed by roughly a tenth (coefficient 0.239, stderr 0.021, n = 55). While re-running with a tighter segmentation threshold for cell08, the coefficient tracked epoch count more closely than duration (coefficient 0.179, stderr 0.020, n = 44). While segmenting epochs for cell07, the estimate moved less than one standard error (coefficient 0.105, stderr 0.019, n = 57). While re-exporting the raw traces for cell08, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.279, stderr 0.040, n = 51). While re-exporting the raw traces for cell19, the estimate moved less than one standard error (coefficient 0.157, stderr 0.018, n = 49). While segmenting epochs for cell10, the ordering of cells was preserved (coefficient 0.273, stderr 0.040, n = 39).

```python
coefs = fit_per_cell(rows, threshold=0.59)
lo, hi = ci(coefs, seed=10)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While re-running with a tighter segmentation threshold for cell14, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.296, stderr 0.034, n = 49). While fitting the one-lag kernel for cell14, the CI narrowed by roughly a tenth (coefficient 0.099, stderr 0.026, n = 54). While auditing the holding potential column for cell16, the coefficient tracked epoch count more closely than duration (coefficient 0.138, stderr 0.046, n = 55). While bootstrapping the CI for cell10, the coefficient tracked epoch count more closely than duration (coefficient 0.082, stderr 0.036, n = 54). While re-exporting the raw traces for cell03, the coefficient tracked epoch count more closely than duration (coefficient 0.264, stderr 0.018, n = 50). Noted and moved on; it does not change the decision.

### Step 25: re-running with a tighter segmentation threshold

While fitting the one-lag kernel for cell18, nothing in the figure changed at print size (coefficient 0.227, stderr 0.024, n = 51). While comparing per-cell orderings for cell16, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.288, stderr 0.023, n = 43). While fitting the one-lag kernel for cell06, nothing in the figure changed at print size (coefficient 0.219, stderr 0.011, n = 49). While re-exporting the raw traces for cell19, nothing in the figure changed at print size (coefficient 0.121, stderr 0.046, n = 49).

While comparing per-cell orderings for cell24, nothing in the figure changed at print size (coefficient 0.207, stderr 0.026, n = 47). While re-running with a tighter segmentation threshold for cell15, nothing in the figure changed at print size (coefficient 0.158, stderr 0.027, n = 55). While checking residual autocorrelation for cell06, the ordering of cells was preserved (coefficient 0.260, stderr 0.022, n = 40). While re-exporting the raw traces for cell10, the ordering of cells was preserved (coefficient 0.253, stderr 0.047, n = 40). While comparing per-cell orderings for cell13, two cells fell out of the usable range (coefficient 0.154, stderr 0.011, n = 39).

```python
coefs = fit_per_cell(rows, threshold=0.57)
lo, hi = ci(coefs, seed=49)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 26: fitting the one-lag kernel

While comparing per-cell orderings for cell23, two cells fell out of the usable range (coefficient 0.201, stderr 0.031, n = 53). While segmenting epochs for cell05, nothing in the figure changed at print size (coefficient 0.241, stderr 0.040, n = 46). While segmenting epochs for cell03, the ordering of cells was preserved (coefficient 0.259, stderr 0.031, n = 51).

While re-running with a tighter segmentation threshold for cell22, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.252, stderr 0.036, n = 50). While re-running with a tighter segmentation threshold for cell23, the CI narrowed by roughly a tenth (coefficient 0.158, stderr 0.048, n = 53). While checking residual autocorrelation for cell15, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.118, stderr 0.049, n = 44). This is the part that will need a real statistical argument.

```python
coefs = fit_per_cell(rows, threshold=0.68)
lo, hi = ci(coefs, seed=31)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While comparing per-cell orderings for cell14, the CI narrowed by roughly a tenth (coefficient 0.131, stderr 0.028, n = 42). While re-exporting the raw traces for cell06, the coefficient tracked epoch count more closely than duration (coefficient 0.080, stderr 0.033, n = 42). While bootstrapping the CI for cell12, two cells fell out of the usable range (coefficient 0.262, stderr 0.048, n = 46). While checking residual autocorrelation for cell19, the ordering of cells was preserved (coefficient 0.139, stderr 0.037, n = 47). While comparing per-cell orderings for cell18, the CI narrowed by roughly a tenth (coefficient 0.225, stderr 0.014, n = 42). While fitting the one-lag kernel for cell15, two cells fell out of the usable range (coefficient 0.138, stderr 0.045, n = 42).

### Step 27: comparing per-cell orderings

While re-exporting the raw traces for cell24, the estimate moved less than one standard error (coefficient 0.188, stderr 0.045, n = 48). While segmenting epochs for cell11, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.172, stderr 0.035, n = 38). While re-running with a tighter segmentation threshold for cell03, the estimate moved less than one standard error (coefficient 0.299, stderr 0.024, n = 47). While re-running with a tighter segmentation threshold for cell23, the ordering of cells was preserved (coefficient 0.092, stderr 0.045, n = 39). Worth noting for the writeup, though not a result on its own.

While bootstrapping the CI for cell21, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.244, stderr 0.014, n = 50). While segmenting epochs for cell14, two cells fell out of the usable range (coefficient 0.180, stderr 0.035, n = 48). While bootstrapping the CI for cell10, two cells fell out of the usable range (coefficient 0.196, stderr 0.018, n = 44). Parking this until the re-segmentation lands.

### Step 28: re-running with a tighter segmentation threshold

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell11    0.280  0.013   0.254  0.307  38        500
cell08    0.085  0.028   0.030  0.140  56        500
cell22    0.109  0.040   0.031  0.187  40        1000
cell09    0.289  0.037   0.216  0.362  38        4000
cell24    0.281  0.028   0.226  0.336  43        500
cell24    0.247  0.034   0.179  0.314  56        1000
cell16    0.219  0.032   0.157  0.282  42        2000
```

While comparing per-cell orderings for cell05, nothing in the figure changed at print size (coefficient 0.096, stderr 0.040, n = 47). While checking residual autocorrelation for cell16, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.252, stderr 0.047, n = 47). While re-running with a tighter segmentation threshold for cell09, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.113, stderr 0.029, n = 54). While auditing the holding potential column for cell04, two cells fell out of the usable range (coefficient 0.086, stderr 0.050, n = 48).

### Step 29: bootstrapping the CI

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell02    0.208  0.034   0.140  0.275  58        2000
cell20    0.309  0.026   0.258  0.360  42        2000
cell12    0.173  0.032   0.110  0.235  43        1000
cell06    0.239  0.043   0.155  0.323  46        500
cell19    0.135  0.041   0.054  0.215  57        2000
cell10    0.088  0.014   0.060  0.115  53        500
cell02    0.221  0.021   0.180  0.261  51        2000
cell07    0.176  0.011   0.154  0.198  43        500
cell17    0.207  0.025   0.159  0.256  44        2000
```

```python
coefs = fit_per_cell(rows, threshold=0.43)
lo, hi = ci(coefs, seed=69)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 30: segmenting epochs

While re-running with a tighter segmentation threshold for cell21, the ordering of cells was preserved (coefficient 0.118, stderr 0.032, n = 51). While comparing per-cell orderings for cell16, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.198, stderr 0.034, n = 52). While checking residual autocorrelation for cell21, the CI narrowed by roughly a tenth (coefficient 0.267, stderr 0.020, n = 49). Worth noting for the writeup, though not a result on its own.

While re-running with a tighter segmentation threshold for cell03, the coefficient tracked epoch count more closely than duration (coefficient 0.226, stderr 0.010, n = 42). While bootstrapping the CI for cell20, nothing in the figure changed at print size (coefficient 0.235, stderr 0.044, n = 46). While re-running with a tighter segmentation threshold for cell17, the coefficient tracked epoch count more closely than duration (coefficient 0.179, stderr 0.040, n = 49). Parking this until the re-segmentation lands.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell17    0.216  0.041   0.136  0.297  38        2000
cell05    0.228  0.030   0.170  0.287  50        4000
cell14    0.287  0.012   0.263  0.311  53        4000
cell18    0.100  0.047   0.008  0.191  48        2000
cell12    0.285  0.048   0.190  0.380  54        4000
cell14    0.143  0.024   0.096  0.191  54        4000
cell22    0.294  0.011   0.272  0.315  45        4000
cell14    0.158  0.033   0.094  0.222  50        1000
cell03    0.208  0.030   0.148  0.267  43        4000
cell17    0.187  0.032   0.124  0.249  39        1000
cell12    0.095  0.044   0.008  0.182  51        4000
cell01    0.206  0.049   0.110  0.302  40        2000
cell01    0.176  0.044   0.089  0.263  44        500
```

While auditing the holding potential column for cell14, nothing in the figure changed at print size (coefficient 0.249, stderr 0.032, n = 38). While re-exporting the raw traces for cell02, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.293, stderr 0.019, n = 49). While fitting the one-lag kernel for cell05, the CI narrowed by roughly a tenth (coefficient 0.183, stderr 0.038, n = 45). While comparing per-cell orderings for cell13, nothing in the figure changed at print size (coefficient 0.226, stderr 0.038, n = 57). While bootstrapping the CI for cell13, nothing in the figure changed at print size (coefficient 0.161, stderr 0.030, n = 50). While fitting the one-lag kernel for cell24, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.303, stderr 0.020, n = 53). Worth noting for the writeup, though not a result on its own.

### Step 31: fitting the one-lag kernel

```python
coefs = fit_per_cell(rows, threshold=0.71)
lo, hi = ci(coefs, seed=51)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While re-exporting the raw traces for cell20, the ordering of cells was preserved (coefficient 0.185, stderr 0.025, n = 41). While auditing the holding potential column for cell13, the CI narrowed by roughly a tenth (coefficient 0.109, stderr 0.035, n = 50). While segmenting epochs for cell23, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.166, stderr 0.044, n = 46). While re-running with a tighter segmentation threshold for cell07, the ordering of cells was preserved (coefficient 0.280, stderr 0.013, n = 44). While re-exporting the raw traces for cell08, two cells fell out of the usable range (coefficient 0.094, stderr 0.018, n = 41). While segmenting epochs for cell20, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.182, stderr 0.018, n = 44). Flagging it so it does not get rediscovered next week.

While comparing per-cell orderings for cell12, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.271, stderr 0.036, n = 38). While re-running with a tighter segmentation threshold for cell08, the coefficient tracked epoch count more closely than duration (coefficient 0.142, stderr 0.017, n = 55). While auditing the holding potential column for cell10, the ordering of cells was preserved (coefficient 0.146, stderr 0.031, n = 55). While re-running with a tighter segmentation threshold for cell05, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.289, stderr 0.013, n = 52). While comparing per-cell orderings for cell19, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.163, stderr 0.046, n = 52). While segmenting epochs for cell19, the CI narrowed by roughly a tenth (coefficient 0.140, stderr 0.050, n = 42). Worth noting for the writeup, though not a result on its own.

### Step 32: fitting the one-lag kernel

While auditing the holding potential column for cell08, the estimate moved less than one standard error (coefficient 0.171, stderr 0.025, n = 44). While checking residual autocorrelation for cell21, nothing in the figure changed at print size (coefficient 0.126, stderr 0.043, n = 40). While fitting the one-lag kernel for cell12, the ordering of cells was preserved (coefficient 0.118, stderr 0.043, n = 47). While comparing per-cell orderings for cell08, two cells fell out of the usable range (coefficient 0.309, stderr 0.032, n = 39). While auditing the holding potential column for cell13, the CI narrowed by roughly a tenth (coefficient 0.309, stderr 0.016, n = 49). Parking this until the re-segmentation lands.

While comparing per-cell orderings for cell20, the CI narrowed by roughly a tenth (coefficient 0.257, stderr 0.041, n = 48). While fitting the one-lag kernel for cell20, the ordering of cells was preserved (coefficient 0.116, stderr 0.041, n = 51). While segmenting epochs for cell13, the ordering of cells was preserved (coefficient 0.245, stderr 0.034, n = 52). While fitting the one-lag kernel for cell04, the estimate moved less than one standard error (coefficient 0.227, stderr 0.022, n = 50).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell18    0.278  0.047   0.186  0.371  54        1000
cell10    0.086  0.041   0.004  0.167  57        4000
cell07    0.081  0.043   -0.003  0.166  45        4000
cell05    0.155  0.032   0.093  0.217  52        4000
cell08    0.271  0.030   0.213  0.330  58        2000
cell18    0.305  0.044   0.219  0.391  45        4000
cell02    0.102  0.013   0.077  0.126  49        500
cell19    0.129  0.040   0.052  0.207  41        4000
cell20    0.200  0.030   0.141  0.259  57        500
cell18    0.217  0.024   0.170  0.264  51        2000
cell03    0.297  0.019   0.261  0.334  48        1000
cell19    0.204  0.028   0.150  0.258  45        2000
cell09    0.257  0.019   0.219  0.295  46        500
cell12    0.252  0.033   0.187  0.318  45        2000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell20    0.299  0.043   0.214  0.383  45        2000
cell15    0.256  0.021   0.215  0.298  58        2000
cell21    0.172  0.017   0.138  0.205  47        500
cell21    0.191  0.018   0.155  0.227  44        2000
cell05    0.088  0.028   0.033  0.142  49        500
cell08    0.252  0.049   0.155  0.349  40        2000
cell03    0.165  0.037   0.092  0.238  46        1000
```

### Step 33: re-exporting the raw traces

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell22    0.087  0.048   -0.007  0.181  42        1000
cell16    0.176  0.044   0.089  0.263  58        4000
cell21    0.165  0.049   0.070  0.261  52        1000
cell19    0.148  0.023   0.103  0.192  56        1000
cell24    0.243  0.031   0.182  0.304  57        500
cell19    0.262  0.025   0.212  0.311  58        2000
cell13    0.207  0.023   0.162  0.253  49        2000
cell24    0.265  0.043   0.181  0.350  40        4000
cell05    0.134  0.046   0.045  0.224  58        4000
```

While fitting the one-lag kernel for cell19, the ordering of cells was preserved (coefficient 0.219, stderr 0.036, n = 56). While auditing the holding potential column for cell05, the estimate moved less than one standard error (coefficient 0.284, stderr 0.033, n = 51). While re-exporting the raw traces for cell10, nothing in the figure changed at print size (coefficient 0.276, stderr 0.036, n = 52). While re-running with a tighter segmentation threshold for cell19, the coefficient tracked epoch count more closely than duration (coefficient 0.171, stderr 0.028, n = 56). Worth noting for the writeup, though not a result on its own.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell01    0.143  0.041   0.063  0.224  45        500
cell17    0.272  0.042   0.190  0.354  45        1000
cell24    0.207  0.049   0.111  0.303  49        4000
cell15    0.170  0.027   0.117  0.223  46        500
cell07    0.159  0.036   0.088  0.229  51        2000
cell18    0.109  0.043   0.024  0.194  51        2000
cell04    0.213  0.013   0.187  0.240  58        2000
cell13    0.212  0.012   0.188  0.236  41        500
```

While segmenting epochs for cell12, the ordering of cells was preserved (coefficient 0.132, stderr 0.035, n = 49). While segmenting epochs for cell11, the estimate moved less than one standard error (coefficient 0.183, stderr 0.044, n = 41). While auditing the holding potential column for cell11, the CI narrowed by roughly a tenth (coefficient 0.148, stderr 0.044, n = 43). While segmenting epochs for cell07, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.105, stderr 0.015, n = 38). While comparing per-cell orderings for cell22, the estimate moved less than one standard error (coefficient 0.136, stderr 0.033, n = 50). This is the part that will need a real statistical argument.

### Step 34: bootstrapping the CI

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell11    0.309  0.010   0.290  0.329  53        4000
cell23    0.137  0.018   0.100  0.173  46        2000
cell01    0.090  0.032   0.028  0.152  55        500
cell16    0.161  0.034   0.095  0.228  43        2000
cell12    0.093  0.020   0.055  0.132  48        1000
cell13    0.167  0.024   0.120  0.214  41        1000
cell14    0.176  0.041   0.095  0.256  38        2000
cell11    0.151  0.026   0.100  0.201  43        2000
cell17    0.126  0.030   0.067  0.185  43        4000
cell22    0.206  0.033   0.142  0.271  38        500
cell01    0.275  0.030   0.216  0.334  52        500
cell22    0.180  0.047   0.087  0.272  52        4000
cell09    0.118  0.036   0.048  0.188  47        2000
```

While re-exporting the raw traces for cell09, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.158, stderr 0.041, n = 51). While re-running with a tighter segmentation threshold for cell24, two cells fell out of the usable range (coefficient 0.138, stderr 0.045, n = 49). While fitting the one-lag kernel for cell24, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.270, stderr 0.039, n = 56). Noted and moved on; it does not change the decision.

```python
coefs = fit_per_cell(rows, threshold=0.52)
lo, hi = ci(coefs, seed=69)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell12    0.211  0.028   0.156  0.265  38        4000
cell07    0.234  0.043   0.150  0.319  43        2000
cell20    0.238  0.043   0.155  0.322  41        2000
cell06    0.084  0.031   0.023  0.145  39        1000
cell07    0.245  0.016   0.214  0.277  38        1000
cell08    0.236  0.041   0.156  0.316  47        1000
```

### Step 35: fitting the one-lag kernel

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell18    0.228  0.018   0.193  0.262  52        2000
cell09    0.095  0.033   0.030  0.160  44        1000
cell11    0.213  0.043   0.128  0.297  46        4000
cell23    0.137  0.030   0.078  0.195  46        4000
cell21    0.179  0.025   0.129  0.229  38        1000
cell15    0.112  0.028   0.056  0.167  56        2000
```

While comparing per-cell orderings for cell23, nothing in the figure changed at print size (coefficient 0.240, stderr 0.010, n = 40). While comparing per-cell orderings for cell11, nothing in the figure changed at print size (coefficient 0.154, stderr 0.031, n = 38). While checking residual autocorrelation for cell17, nothing in the figure changed at print size (coefficient 0.283, stderr 0.048, n = 48). While fitting the one-lag kernel for cell24, nothing in the figure changed at print size (coefficient 0.225, stderr 0.024, n = 45). While bootstrapping the CI for cell21, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.111, stderr 0.041, n = 44).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell24    0.273  0.034   0.206  0.340  40        1000
cell22    0.098  0.029   0.041  0.155  38        2000
cell12    0.217  0.039   0.141  0.293  40        500
cell09    0.158  0.030   0.100  0.216  57        500
cell22    0.183  0.027   0.131  0.235  50        4000
cell14    0.180  0.018   0.145  0.215  38        4000
cell08    0.263  0.026   0.212  0.315  40        500
cell12    0.273  0.013   0.247  0.299  45        1000
```

While auditing the holding potential column for cell21, two cells fell out of the usable range (coefficient 0.252, stderr 0.019, n = 49). While auditing the holding potential column for cell02, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.228, stderr 0.026, n = 42). While segmenting epochs for cell06, two cells fell out of the usable range (coefficient 0.212, stderr 0.019, n = 55). While segmenting epochs for cell22, the ordering of cells was preserved (coefficient 0.276, stderr 0.034, n = 50). While checking residual autocorrelation for cell14, nothing in the figure changed at print size (coefficient 0.282, stderr 0.023, n = 44). While re-running with a tighter segmentation threshold for cell17, the ordering of cells was preserved (coefficient 0.136, stderr 0.020, n = 39). Flagging it so it does not get rediscovered next week.

### Step 36: auditing the holding potential column

While re-exporting the raw traces for cell10, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.275, stderr 0.037, n = 42). While comparing per-cell orderings for cell10, nothing in the figure changed at print size (coefficient 0.288, stderr 0.021, n = 46). While segmenting epochs for cell09, two cells fell out of the usable range (coefficient 0.269, stderr 0.043, n = 57). While re-exporting the raw traces for cell21, the CI narrowed by roughly a tenth (coefficient 0.145, stderr 0.029, n = 55). While comparing per-cell orderings for cell13, two cells fell out of the usable range (coefficient 0.092, stderr 0.035, n = 47).

```python
coefs = fit_per_cell(rows, threshold=0.70)
lo, hi = ci(coefs, seed=73)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 37: re-running with a tighter segmentation threshold

While auditing the holding potential column for cell20, two cells fell out of the usable range (coefficient 0.107, stderr 0.036, n = 41). While checking residual autocorrelation for cell09, the estimate moved less than one standard error (coefficient 0.119, stderr 0.021, n = 51). While segmenting epochs for cell18, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.257, stderr 0.042, n = 56). While fitting the one-lag kernel for cell12, two cells fell out of the usable range (coefficient 0.257, stderr 0.046, n = 44). While segmenting epochs for cell21, the coefficient tracked epoch count more closely than duration (coefficient 0.282, stderr 0.015, n = 56).

While auditing the holding potential column for cell23, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.251, stderr 0.039, n = 53). While fitting the one-lag kernel for cell03, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.291, stderr 0.050, n = 39). While fitting the one-lag kernel for cell13, nothing in the figure changed at print size (coefficient 0.087, stderr 0.036, n = 54). While re-exporting the raw traces for cell23, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.088, stderr 0.041, n = 49). While segmenting epochs for cell24, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.249, stderr 0.014, n = 43). This is the part that will need a real statistical argument.

### Step 38: re-running with a tighter segmentation threshold

```python
coefs = fit_per_cell(rows, threshold=0.53)
lo, hi = ci(coefs, seed=87)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While bootstrapping the CI for cell01, the estimate moved less than one standard error (coefficient 0.272, stderr 0.049, n = 52). While checking residual autocorrelation for cell04, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.087, stderr 0.028, n = 58). While re-exporting the raw traces for cell06, nothing in the figure changed at print size (coefficient 0.278, stderr 0.018, n = 51). While auditing the holding potential column for cell24, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.215, stderr 0.011, n = 55). While checking residual autocorrelation for cell15, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.238, stderr 0.018, n = 45).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell06    0.186  0.046   0.096  0.277  47        4000
cell03    0.201  0.017   0.167  0.235  47        2000
cell03    0.275  0.017   0.242  0.309  52        2000
cell23    0.129  0.026   0.078  0.181  54        4000
cell04    0.111  0.024   0.064  0.158  45        1000
cell02    0.292  0.019   0.255  0.328  47        2000
cell07    0.157  0.016   0.126  0.188  50        2000
cell13    0.134  0.016   0.102  0.166  41        4000
cell13    0.278  0.027   0.224  0.331  46        2000
cell12    0.170  0.015   0.141  0.199  53        500
cell03    0.297  0.026   0.245  0.349  41        4000
```

### Step 39: re-exporting the raw traces

While comparing per-cell orderings for cell10, nothing in the figure changed at print size (coefficient 0.117, stderr 0.020, n = 53). While auditing the holding potential column for cell13, the coefficient tracked epoch count more closely than duration (coefficient 0.101, stderr 0.042, n = 40). While auditing the holding potential column for cell01, two cells fell out of the usable range (coefficient 0.251, stderr 0.042, n = 38). While auditing the holding potential column for cell20, nothing in the figure changed at print size (coefficient 0.219, stderr 0.024, n = 43). While bootstrapping the CI for cell22, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.290, stderr 0.012, n = 41). Worth noting for the writeup, though not a result on its own.

While auditing the holding potential column for cell14, the ordering of cells was preserved (coefficient 0.268, stderr 0.038, n = 45). While re-running with a tighter segmentation threshold for cell20, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.211, stderr 0.023, n = 41). While re-exporting the raw traces for cell12, the estimate moved less than one standard error (coefficient 0.163, stderr 0.019, n = 57). While re-exporting the raw traces for cell03, nothing in the figure changed at print size (coefficient 0.243, stderr 0.039, n = 58).

While re-exporting the raw traces for cell10, the coefficient tracked epoch count more closely than duration (coefficient 0.215, stderr 0.035, n = 49). While checking residual autocorrelation for cell01, the coefficient tracked epoch count more closely than duration (coefficient 0.152, stderr 0.036, n = 57). While bootstrapping the CI for cell13, the estimate moved less than one standard error (coefficient 0.254, stderr 0.011, n = 38). While checking residual autocorrelation for cell20, nothing in the figure changed at print size (coefficient 0.264, stderr 0.036, n = 54). While bootstrapping the CI for cell01, two cells fell out of the usable range (coefficient 0.259, stderr 0.048, n = 56). While fitting the one-lag kernel for cell14, two cells fell out of the usable range (coefficient 0.118, stderr 0.030, n = 52).

### Step 40: checking residual autocorrelation

While segmenting epochs for cell23, two cells fell out of the usable range (coefficient 0.184, stderr 0.036, n = 53). While re-running with a tighter segmentation threshold for cell04, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.159, stderr 0.038, n = 42). While comparing per-cell orderings for cell03, the coefficient tracked epoch count more closely than duration (coefficient 0.121, stderr 0.046, n = 50). While re-exporting the raw traces for cell21, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.221, stderr 0.020, n = 40). While bootstrapping the CI for cell19, the ordering of cells was preserved (coefficient 0.210, stderr 0.028, n = 54).

While fitting the one-lag kernel for cell18, nothing in the figure changed at print size (coefficient 0.247, stderr 0.035, n = 55). While checking residual autocorrelation for cell07, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.089, stderr 0.012, n = 38). While bootstrapping the CI for cell03, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.131, stderr 0.035, n = 53).

