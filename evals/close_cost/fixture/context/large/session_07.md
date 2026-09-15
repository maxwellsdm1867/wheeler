# Prior session 7 of 20

Transcript of an earlier working session on the history-kernel analysis.

### Step 1: fitting the one-lag kernel

While re-exporting the raw traces for cell18, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.089, stderr 0.018, n = 43). While comparing per-cell orderings for cell19, the CI narrowed by roughly a tenth (coefficient 0.220, stderr 0.035, n = 53). While fitting the one-lag kernel for cell20, nothing in the figure changed at print size (coefficient 0.253, stderr 0.049, n = 39). While bootstrapping the CI for cell09, the ordering of cells was preserved (coefficient 0.131, stderr 0.016, n = 39). While re-running with a tighter segmentation threshold for cell15, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.107, stderr 0.040, n = 41).

While segmenting epochs for cell05, the ordering of cells was preserved (coefficient 0.116, stderr 0.025, n = 41). While segmenting epochs for cell22, two cells fell out of the usable range (coefficient 0.301, stderr 0.021, n = 44). While bootstrapping the CI for cell03, the estimate moved less than one standard error (coefficient 0.081, stderr 0.034, n = 51). While auditing the holding potential column for cell10, the CI narrowed by roughly a tenth (coefficient 0.171, stderr 0.047, n = 53). While bootstrapping the CI for cell06, two cells fell out of the usable range (coefficient 0.299, stderr 0.049, n = 57). While segmenting epochs for cell23, two cells fell out of the usable range (coefficient 0.297, stderr 0.043, n = 44).

### Step 2: segmenting epochs

While re-running with a tighter segmentation threshold for cell03, the ordering of cells was preserved (coefficient 0.225, stderr 0.027, n = 49). While re-running with a tighter segmentation threshold for cell11, two cells fell out of the usable range (coefficient 0.175, stderr 0.030, n = 51). While fitting the one-lag kernel for cell23, two cells fell out of the usable range (coefficient 0.218, stderr 0.027, n = 41). While checking residual autocorrelation for cell05, the estimate moved less than one standard error (coefficient 0.085, stderr 0.035, n = 46). While bootstrapping the CI for cell01, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.193, stderr 0.050, n = 46). While checking residual autocorrelation for cell11, the coefficient tracked epoch count more closely than duration (coefficient 0.234, stderr 0.041, n = 51). Noted and moved on; it does not change the decision.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell08    0.085  0.049   -0.011  0.182  50        500
cell09    0.094  0.010   0.074  0.114  47        2000
cell19    0.138  0.043   0.054  0.222  45        2000
cell15    0.309  0.040   0.231  0.387  53        4000
cell21    0.292  0.012   0.268  0.316  47        1000
cell11    0.094  0.016   0.063  0.124  48        500
cell04    0.165  0.018   0.130  0.200  43        2000
cell08    0.236  0.050   0.138  0.334  44        1000
cell04    0.122  0.045   0.035  0.210  44        500
cell01    0.306  0.020   0.266  0.345  50        2000
cell10    0.253  0.010   0.233  0.273  54        500
cell12    0.121  0.038   0.046  0.195  39        2000
cell23    0.248  0.029   0.191  0.306  49        1000
```

```python
coefs = fit_per_cell(rows, threshold=0.56)
lo, hi = ci(coefs, seed=69)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 3: comparing per-cell orderings

```python
coefs = fit_per_cell(rows, threshold=0.51)
lo, hi = ci(coefs, seed=97)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```python
coefs = fit_per_cell(rows, threshold=0.77)
lo, hi = ci(coefs, seed=93)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While fitting the one-lag kernel for cell18, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.295, stderr 0.011, n = 55). While auditing the holding potential column for cell04, two cells fell out of the usable range (coefficient 0.261, stderr 0.050, n = 57). While auditing the holding potential column for cell23, the estimate moved less than one standard error (coefficient 0.308, stderr 0.030, n = 42). While bootstrapping the CI for cell10, the CI narrowed by roughly a tenth (coefficient 0.273, stderr 0.041, n = 54). While bootstrapping the CI for cell17, two cells fell out of the usable range (coefficient 0.283, stderr 0.030, n = 44). While re-running with a tighter segmentation threshold for cell16, the estimate moved less than one standard error (coefficient 0.167, stderr 0.038, n = 46).

### Step 4: comparing per-cell orderings

While auditing the holding potential column for cell21, the coefficient tracked epoch count more closely than duration (coefficient 0.121, stderr 0.013, n = 58). While segmenting epochs for cell13, the coefficient tracked epoch count more closely than duration (coefficient 0.178, stderr 0.036, n = 38). While bootstrapping the CI for cell01, two cells fell out of the usable range (coefficient 0.171, stderr 0.017, n = 58). While fitting the one-lag kernel for cell11, the estimate moved less than one standard error (coefficient 0.162, stderr 0.040, n = 55). Worth noting for the writeup, though not a result on its own.

```python
coefs = fit_per_cell(rows, threshold=0.64)
lo, hi = ci(coefs, seed=88)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 5: segmenting epochs

While checking residual autocorrelation for cell09, nothing in the figure changed at print size (coefficient 0.099, stderr 0.024, n = 52). While auditing the holding potential column for cell08, the coefficient tracked epoch count more closely than duration (coefficient 0.098, stderr 0.026, n = 38). While checking residual autocorrelation for cell19, nothing in the figure changed at print size (coefficient 0.180, stderr 0.039, n = 54). While bootstrapping the CI for cell08, nothing in the figure changed at print size (coefficient 0.230, stderr 0.020, n = 41).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell16    0.250  0.045   0.162  0.338  45        500
cell04    0.126  0.043   0.041  0.210  54        1000
cell04    0.222  0.035   0.152  0.291  45        4000
cell19    0.136  0.032   0.073  0.200  55        1000
cell06    0.146  0.039   0.071  0.222  57        4000
cell13    0.299  0.040   0.220  0.377  49        500
cell18    0.285  0.022   0.241  0.329  42        2000
cell15    0.189  0.042   0.107  0.272  55        1000
cell17    0.160  0.013   0.133  0.186  55        1000
cell15    0.198  0.023   0.153  0.244  46        2000
cell12    0.243  0.041   0.163  0.322  45        1000
cell23    0.142  0.011   0.120  0.163  47        4000
cell23    0.207  0.019   0.169  0.244  40        1000
```

While fitting the one-lag kernel for cell19, the CI narrowed by roughly a tenth (coefficient 0.122, stderr 0.044, n = 52). While fitting the one-lag kernel for cell07, the CI narrowed by roughly a tenth (coefficient 0.190, stderr 0.016, n = 43). While re-running with a tighter segmentation threshold for cell07, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.280, stderr 0.031, n = 45).

While checking residual autocorrelation for cell19, two cells fell out of the usable range (coefficient 0.279, stderr 0.048, n = 41). While segmenting epochs for cell17, the ordering of cells was preserved (coefficient 0.190, stderr 0.034, n = 45). While bootstrapping the CI for cell04, the estimate moved less than one standard error (coefficient 0.131, stderr 0.035, n = 44).

### Step 6: bootstrapping the CI

While auditing the holding potential column for cell12, the ordering of cells was preserved (coefficient 0.179, stderr 0.041, n = 45). While checking residual autocorrelation for cell11, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.126, stderr 0.035, n = 38). While checking residual autocorrelation for cell22, the estimate moved less than one standard error (coefficient 0.158, stderr 0.041, n = 44). Worth noting for the writeup, though not a result on its own.

While re-running with a tighter segmentation threshold for cell13, the ordering of cells was preserved (coefficient 0.086, stderr 0.029, n = 53). While re-running with a tighter segmentation threshold for cell20, the ordering of cells was preserved (coefficient 0.115, stderr 0.030, n = 47). While comparing per-cell orderings for cell20, the estimate moved less than one standard error (coefficient 0.091, stderr 0.033, n = 43). While fitting the one-lag kernel for cell09, two cells fell out of the usable range (coefficient 0.153, stderr 0.042, n = 48). Worth noting for the writeup, though not a result on its own.

While re-running with a tighter segmentation threshold for cell09, the ordering of cells was preserved (coefficient 0.305, stderr 0.029, n = 41). While bootstrapping the CI for cell11, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.249, stderr 0.013, n = 55). While re-running with a tighter segmentation threshold for cell24, two cells fell out of the usable range (coefficient 0.267, stderr 0.039, n = 54). While bootstrapping the CI for cell18, the ordering of cells was preserved (coefficient 0.215, stderr 0.014, n = 52). While re-running with a tighter segmentation threshold for cell14, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.237, stderr 0.042, n = 44). While auditing the holding potential column for cell15, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.141, stderr 0.019, n = 45). Flagging it so it does not get rediscovered next week.

### Step 7: bootstrapping the CI

While comparing per-cell orderings for cell07, the estimate moved less than one standard error (coefficient 0.149, stderr 0.039, n = 43). While re-exporting the raw traces for cell23, the ordering of cells was preserved (coefficient 0.291, stderr 0.023, n = 45). While comparing per-cell orderings for cell15, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.115, stderr 0.042, n = 39). While segmenting epochs for cell14, the coefficient tracked epoch count more closely than duration (coefficient 0.153, stderr 0.042, n = 53). Noted and moved on; it does not change the decision.

While re-exporting the raw traces for cell20, the estimate moved less than one standard error (coefficient 0.201, stderr 0.031, n = 52). While bootstrapping the CI for cell11, the ordering of cells was preserved (coefficient 0.165, stderr 0.038, n = 52). While bootstrapping the CI for cell11, two cells fell out of the usable range (coefficient 0.195, stderr 0.046, n = 40). While comparing per-cell orderings for cell09, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.181, stderr 0.012, n = 50). While comparing per-cell orderings for cell05, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.260, stderr 0.019, n = 54). Parking this until the re-segmentation lands.

### Step 8: re-exporting the raw traces

```python
coefs = fit_per_cell(rows, threshold=0.53)
lo, hi = ci(coefs, seed=76)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell16    0.199  0.032   0.135  0.262  48        2000
cell15    0.264  0.039   0.189  0.340  46        2000
cell05    0.080  0.021   0.038  0.122  40        2000
cell01    0.107  0.034   0.041  0.173  48        2000
cell20    0.297  0.030   0.238  0.356  58        500
cell05    0.292  0.020   0.252  0.331  49        500
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell08    0.140  0.039   0.064  0.216  51        500
cell15    0.106  0.047   0.014  0.198  50        4000
cell14    0.192  0.017   0.158  0.226  53        4000
cell15    0.300  0.018   0.264  0.336  38        4000
cell20    0.174  0.045   0.085  0.263  51        1000
cell12    0.247  0.048   0.152  0.341  55        4000
cell09    0.242  0.047   0.149  0.335  51        1000
cell06    0.247  0.039   0.171  0.323  48        4000
cell04    0.234  0.035   0.166  0.302  41        2000
cell15    0.201  0.030   0.142  0.259  40        4000
cell20    0.157  0.047   0.066  0.249  43        2000
cell22    0.291  0.035   0.223  0.359  48        1000
cell18    0.108  0.045   0.020  0.196  42        2000
```

```python
coefs = fit_per_cell(rows, threshold=0.73)
lo, hi = ci(coefs, seed=88)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 9: re-running with a tighter segmentation threshold

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell17    0.102  0.017   0.068  0.136  40        2000
cell04    0.237  0.011   0.216  0.258  56        500
cell22    0.213  0.045   0.124  0.302  39        2000
cell08    0.167  0.047   0.074  0.260  41        2000
cell24    0.259  0.049   0.163  0.354  39        500
cell20    0.140  0.039   0.064  0.217  40        500
cell20    0.116  0.040   0.037  0.194  38        4000
cell10    0.146  0.040   0.068  0.224  52        500
cell19    0.248  0.041   0.168  0.328  43        500
cell19    0.122  0.016   0.090  0.153  56        500
cell22    0.270  0.049   0.173  0.367  58        1000
cell08    0.177  0.027   0.125  0.230  53        4000
cell19    0.120  0.040   0.042  0.199  38        2000
```

```python
coefs = fit_per_cell(rows, threshold=0.62)
lo, hi = ci(coefs, seed=87)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 10: checking residual autocorrelation

While comparing per-cell orderings for cell06, two cells fell out of the usable range (coefficient 0.142, stderr 0.044, n = 48). While re-exporting the raw traces for cell01, the ordering of cells was preserved (coefficient 0.303, stderr 0.042, n = 43). While re-exporting the raw traces for cell05, the coefficient tracked epoch count more closely than duration (coefficient 0.089, stderr 0.019, n = 46). While auditing the holding potential column for cell11, the ordering of cells was preserved (coefficient 0.128, stderr 0.025, n = 44). While segmenting epochs for cell14, nothing in the figure changed at print size (coefficient 0.144, stderr 0.015, n = 56). While auditing the holding potential column for cell22, the coefficient tracked epoch count more closely than duration (coefficient 0.096, stderr 0.036, n = 48).

While auditing the holding potential column for cell24, the CI narrowed by roughly a tenth (coefficient 0.097, stderr 0.015, n = 41). While re-exporting the raw traces for cell21, nothing in the figure changed at print size (coefficient 0.173, stderr 0.048, n = 56). While auditing the holding potential column for cell12, the ordering of cells was preserved (coefficient 0.212, stderr 0.044, n = 49). While re-running with a tighter segmentation threshold for cell08, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.219, stderr 0.039, n = 38). While fitting the one-lag kernel for cell06, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.122, stderr 0.017, n = 43).

While bootstrapping the CI for cell21, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.161, stderr 0.033, n = 39). While bootstrapping the CI for cell14, the CI narrowed by roughly a tenth (coefficient 0.297, stderr 0.011, n = 43). While auditing the holding potential column for cell11, the ordering of cells was preserved (coefficient 0.217, stderr 0.016, n = 55).

### Step 11: auditing the holding potential column

While segmenting epochs for cell18, two cells fell out of the usable range (coefficient 0.094, stderr 0.044, n = 47). While re-running with a tighter segmentation threshold for cell17, two cells fell out of the usable range (coefficient 0.256, stderr 0.026, n = 56). While re-running with a tighter segmentation threshold for cell09, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.125, stderr 0.036, n = 56).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell23    0.242  0.028   0.187  0.296  44        2000
cell05    0.178  0.019   0.141  0.215  46        4000
cell23    0.305  0.012   0.281  0.329  49        2000
cell09    0.279  0.015   0.250  0.308  50        500
cell17    0.090  0.012   0.066  0.114  43        1000
cell15    0.181  0.049   0.084  0.278  48        4000
cell18    0.158  0.019   0.120  0.195  43        2000
cell19    0.254  0.039   0.178  0.330  41        2000
cell18    0.177  0.015   0.146  0.207  47        500
cell17    0.113  0.032   0.050  0.176  39        1000
cell16    0.210  0.012   0.187  0.233  56        4000
cell21    0.264  0.023   0.219  0.308  44        2000
```

While segmenting epochs for cell10, the ordering of cells was preserved (coefficient 0.174, stderr 0.047, n = 50). While bootstrapping the CI for cell09, the ordering of cells was preserved (coefficient 0.277, stderr 0.018, n = 52). While bootstrapping the CI for cell05, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.173, stderr 0.040, n = 58). While fitting the one-lag kernel for cell21, two cells fell out of the usable range (coefficient 0.091, stderr 0.018, n = 42).

### Step 12: re-running with a tighter segmentation threshold

While auditing the holding potential column for cell23, nothing in the figure changed at print size (coefficient 0.083, stderr 0.014, n = 44). While fitting the one-lag kernel for cell17, the estimate moved less than one standard error (coefficient 0.185, stderr 0.034, n = 48). While segmenting epochs for cell24, the CI narrowed by roughly a tenth (coefficient 0.119, stderr 0.017, n = 52). While bootstrapping the CI for cell09, two cells fell out of the usable range (coefficient 0.148, stderr 0.048, n = 55). While segmenting epochs for cell10, the CI narrowed by roughly a tenth (coefficient 0.174, stderr 0.046, n = 56). While fitting the one-lag kernel for cell18, two cells fell out of the usable range (coefficient 0.149, stderr 0.035, n = 54).

While comparing per-cell orderings for cell22, two cells fell out of the usable range (coefficient 0.143, stderr 0.041, n = 55). While comparing per-cell orderings for cell12, nothing in the figure changed at print size (coefficient 0.105, stderr 0.029, n = 40). While re-exporting the raw traces for cell20, the ordering of cells was preserved (coefficient 0.225, stderr 0.027, n = 56). While bootstrapping the CI for cell04, nothing in the figure changed at print size (coefficient 0.247, stderr 0.025, n = 50).

While checking residual autocorrelation for cell11, two cells fell out of the usable range (coefficient 0.180, stderr 0.038, n = 56). While checking residual autocorrelation for cell19, the ordering of cells was preserved (coefficient 0.119, stderr 0.022, n = 43). While auditing the holding potential column for cell20, the coefficient tracked epoch count more closely than duration (coefficient 0.229, stderr 0.032, n = 56). While comparing per-cell orderings for cell22, the CI narrowed by roughly a tenth (coefficient 0.227, stderr 0.033, n = 50). Parking this until the re-segmentation lands.

### Step 13: bootstrapping the CI

```python
coefs = fit_per_cell(rows, threshold=0.64)
lo, hi = ci(coefs, seed=35)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell07    0.165  0.013   0.140  0.191  45        2000
cell12    0.307  0.047   0.215  0.399  56        1000
cell17    0.181  0.013   0.156  0.207  53        4000
cell23    0.128  0.027   0.074  0.182  53        2000
cell07    0.218  0.013   0.193  0.244  51        1000
cell04    0.245  0.024   0.199  0.292  39        2000
cell12    0.211  0.022   0.168  0.255  43        2000
cell16    0.164  0.035   0.096  0.233  53        500
cell23    0.134  0.016   0.103  0.165  58        1000
cell20    0.144  0.043   0.059  0.229  56        500
```

```python
coefs = fit_per_cell(rows, threshold=0.52)
lo, hi = ci(coefs, seed=39)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 14: comparing per-cell orderings

While comparing per-cell orderings for cell19, nothing in the figure changed at print size (coefficient 0.289, stderr 0.042, n = 57). While segmenting epochs for cell14, nothing in the figure changed at print size (coefficient 0.095, stderr 0.039, n = 47). While comparing per-cell orderings for cell20, the ordering of cells was preserved (coefficient 0.156, stderr 0.035, n = 40). While re-exporting the raw traces for cell05, nothing in the figure changed at print size (coefficient 0.234, stderr 0.042, n = 49). While re-exporting the raw traces for cell01, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.237, stderr 0.026, n = 38). While comparing per-cell orderings for cell01, nothing in the figure changed at print size (coefficient 0.273, stderr 0.020, n = 46).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell13    0.266  0.026   0.215  0.316  45        2000
cell01    0.278  0.019   0.241  0.316  48        1000
cell21    0.301  0.012   0.278  0.325  48        500
cell10    0.189  0.049   0.093  0.284  47        2000
cell06    0.295  0.046   0.205  0.385  42        4000
cell05    0.276  0.013   0.250  0.303  55        500
cell18    0.185  0.013   0.159  0.210  54        500
cell19    0.113  0.026   0.062  0.163  57        4000
cell09    0.249  0.018   0.214  0.284  42        500
cell17    0.128  0.020   0.089  0.167  47        2000
cell21    0.096  0.023   0.051  0.142  43        4000
cell11    0.126  0.035   0.058  0.195  41        2000
cell01    0.204  0.013   0.179  0.228  58        2000
cell22    0.216  0.028   0.161  0.272  42        4000
```

### Step 15: fitting the one-lag kernel

While fitting the one-lag kernel for cell19, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.274, stderr 0.025, n = 39). While bootstrapping the CI for cell04, the estimate moved less than one standard error (coefficient 0.106, stderr 0.019, n = 41). While re-running with a tighter segmentation threshold for cell16, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.186, stderr 0.030, n = 51). While bootstrapping the CI for cell20, the CI narrowed by roughly a tenth (coefficient 0.123, stderr 0.017, n = 49). While segmenting epochs for cell22, nothing in the figure changed at print size (coefficient 0.124, stderr 0.033, n = 56). Worth noting for the writeup, though not a result on its own.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell08    0.287  0.014   0.259  0.314  51        1000
cell02    0.275  0.041   0.194  0.356  42        500
cell04    0.198  0.023   0.153  0.243  42        4000
cell05    0.243  0.046   0.153  0.333  41        2000
cell16    0.171  0.042   0.088  0.253  56        2000
cell14    0.147  0.014   0.120  0.175  48        4000
```

### Step 16: comparing per-cell orderings

While bootstrapping the CI for cell17, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.211, stderr 0.019, n = 39). While re-running with a tighter segmentation threshold for cell16, two cells fell out of the usable range (coefficient 0.169, stderr 0.029, n = 41). While bootstrapping the CI for cell20, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.102, stderr 0.022, n = 39). While re-exporting the raw traces for cell07, the CI narrowed by roughly a tenth (coefficient 0.081, stderr 0.041, n = 46). While auditing the holding potential column for cell04, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.113, stderr 0.043, n = 58).

```python
coefs = fit_per_cell(rows, threshold=0.69)
lo, hi = ci(coefs, seed=99)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 17: segmenting epochs

While checking residual autocorrelation for cell06, the coefficient tracked epoch count more closely than duration (coefficient 0.223, stderr 0.021, n = 56). While bootstrapping the CI for cell23, two cells fell out of the usable range (coefficient 0.167, stderr 0.030, n = 49). While re-exporting the raw traces for cell20, the estimate moved less than one standard error (coefficient 0.300, stderr 0.037, n = 44). While fitting the one-lag kernel for cell04, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.172, stderr 0.041, n = 43). While auditing the holding potential column for cell02, the ordering of cells was preserved (coefficient 0.234, stderr 0.036, n = 39). While auditing the holding potential column for cell24, nothing in the figure changed at print size (coefficient 0.181, stderr 0.043, n = 51).

```python
coefs = fit_per_cell(rows, threshold=0.41)
lo, hi = ci(coefs, seed=64)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While segmenting epochs for cell16, nothing in the figure changed at print size (coefficient 0.307, stderr 0.013, n = 46). While fitting the one-lag kernel for cell06, the estimate moved less than one standard error (coefficient 0.184, stderr 0.017, n = 40). While checking residual autocorrelation for cell08, nothing in the figure changed at print size (coefficient 0.218, stderr 0.015, n = 55). While segmenting epochs for cell15, nothing in the figure changed at print size (coefficient 0.148, stderr 0.044, n = 52).

While re-exporting the raw traces for cell10, nothing in the figure changed at print size (coefficient 0.123, stderr 0.013, n = 46). While bootstrapping the CI for cell16, nothing in the figure changed at print size (coefficient 0.136, stderr 0.043, n = 38). While bootstrapping the CI for cell07, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.155, stderr 0.015, n = 45).

### Step 18: segmenting epochs

While checking residual autocorrelation for cell13, the CI narrowed by roughly a tenth (coefficient 0.106, stderr 0.024, n = 55). While comparing per-cell orderings for cell11, nothing in the figure changed at print size (coefficient 0.279, stderr 0.016, n = 52). While comparing per-cell orderings for cell04, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.252, stderr 0.036, n = 42). While re-running with a tighter segmentation threshold for cell21, the estimate moved less than one standard error (coefficient 0.097, stderr 0.022, n = 41). While re-running with a tighter segmentation threshold for cell22, the CI narrowed by roughly a tenth (coefficient 0.285, stderr 0.024, n = 51). While checking residual autocorrelation for cell09, the coefficient tracked epoch count more closely than duration (coefficient 0.130, stderr 0.015, n = 53).

While re-running with a tighter segmentation threshold for cell19, the estimate moved less than one standard error (coefficient 0.160, stderr 0.041, n = 38). While segmenting epochs for cell05, nothing in the figure changed at print size (coefficient 0.202, stderr 0.026, n = 43). While comparing per-cell orderings for cell08, nothing in the figure changed at print size (coefficient 0.245, stderr 0.044, n = 39). While checking residual autocorrelation for cell10, nothing in the figure changed at print size (coefficient 0.288, stderr 0.047, n = 49).

### Step 19: re-running with a tighter segmentation threshold

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell05    0.287  0.048   0.194  0.381  58        2000
cell09    0.109  0.041   0.028  0.189  57        2000
cell02    0.242  0.020   0.202  0.282  42        2000
cell09    0.084  0.034   0.019  0.150  57        500
cell24    0.272  0.048   0.177  0.367  43        4000
cell09    0.128  0.023   0.083  0.173  48        1000
cell14    0.294  0.011   0.273  0.315  43        2000
```

While bootstrapping the CI for cell23, the CI narrowed by roughly a tenth (coefficient 0.133, stderr 0.020, n = 57). While re-running with a tighter segmentation threshold for cell24, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.210, stderr 0.042, n = 58). While re-running with a tighter segmentation threshold for cell14, two cells fell out of the usable range (coefficient 0.099, stderr 0.042, n = 58). While re-exporting the raw traces for cell13, two cells fell out of the usable range (coefficient 0.281, stderr 0.038, n = 47). While re-running with a tighter segmentation threshold for cell11, the coefficient tracked epoch count more closely than duration (coefficient 0.084, stderr 0.011, n = 53). While fitting the one-lag kernel for cell21, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.103, stderr 0.030, n = 40).

### Step 20: auditing the holding potential column

While segmenting epochs for cell01, the coefficient tracked epoch count more closely than duration (coefficient 0.172, stderr 0.025, n = 47). While comparing per-cell orderings for cell15, two cells fell out of the usable range (coefficient 0.248, stderr 0.049, n = 43). While re-exporting the raw traces for cell15, the coefficient tracked epoch count more closely than duration (coefficient 0.214, stderr 0.036, n = 56). While fitting the one-lag kernel for cell16, nothing in the figure changed at print size (coefficient 0.301, stderr 0.029, n = 57).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell15    0.283  0.015   0.253  0.313  53        500
cell13    0.142  0.013   0.117  0.168  57        2000
cell20    0.230  0.015   0.200  0.259  38        1000
cell22    0.170  0.015   0.141  0.200  53        500
cell23    0.252  0.035   0.184  0.320  42        2000
cell14    0.098  0.030   0.040  0.156  53        500
cell20    0.110  0.019   0.073  0.148  40        2000
cell23    0.273  0.013   0.248  0.298  43        500
cell05    0.272  0.040   0.193  0.350  39        1000
cell13    0.100  0.049   0.003  0.197  52        4000
cell09    0.175  0.016   0.144  0.205  42        1000
cell22    0.239  0.023   0.195  0.284  51        2000
```

### Step 21: comparing per-cell orderings

While checking residual autocorrelation for cell15, the CI narrowed by roughly a tenth (coefficient 0.265, stderr 0.033, n = 51). While comparing per-cell orderings for cell15, the CI narrowed by roughly a tenth (coefficient 0.161, stderr 0.031, n = 56). While segmenting epochs for cell18, nothing in the figure changed at print size (coefficient 0.105, stderr 0.034, n = 48). Worth noting for the writeup, though not a result on its own.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell10    0.286  0.036   0.216  0.357  56        2000
cell22    0.191  0.035   0.123  0.259  43        1000
cell10    0.173  0.037   0.100  0.247  50        500
cell13    0.250  0.038   0.176  0.323  55        1000
cell17    0.160  0.024   0.113  0.207  53        1000
cell04    0.091  0.022   0.048  0.133  44        500
cell24    0.195  0.037   0.121  0.268  56        500
cell16    0.214  0.019   0.177  0.250  51        2000
cell08    0.081  0.028   0.027  0.135  53        1000
cell17    0.197  0.021   0.155  0.239  39        1000
cell11    0.163  0.033   0.099  0.227  55        2000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell18    0.104  0.042   0.023  0.186  50        1000
cell22    0.158  0.029   0.101  0.216  44        1000
cell20    0.115  0.019   0.077  0.152  43        4000
cell21    0.122  0.048   0.027  0.216  44        4000
cell15    0.298  0.031   0.238  0.358  38        1000
cell20    0.092  0.044   0.006  0.177  40        4000
cell17    0.113  0.015   0.084  0.141  52        4000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell18    0.163  0.050   0.065  0.260  57        500
cell11    0.238  0.033   0.174  0.302  46        2000
cell14    0.107  0.045   0.019  0.195  54        2000
cell09    0.143  0.012   0.120  0.166  44        4000
cell03    0.164  0.024   0.116  0.212  45        1000
cell21    0.275  0.047   0.183  0.367  39        1000
```

### Step 22: auditing the holding potential column

While comparing per-cell orderings for cell22, the coefficient tracked epoch count more closely than duration (coefficient 0.236, stderr 0.034, n = 58). While re-running with a tighter segmentation threshold for cell15, the estimate moved less than one standard error (coefficient 0.281, stderr 0.047, n = 48). While segmenting epochs for cell07, the CI narrowed by roughly a tenth (coefficient 0.257, stderr 0.028, n = 45). While auditing the holding potential column for cell02, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.203, stderr 0.019, n = 55).

While segmenting epochs for cell06, the ordering of cells was preserved (coefficient 0.249, stderr 0.014, n = 56). While re-running with a tighter segmentation threshold for cell23, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.123, stderr 0.018, n = 41). While fitting the one-lag kernel for cell18, the ordering of cells was preserved (coefficient 0.153, stderr 0.038, n = 58). While re-running with a tighter segmentation threshold for cell18, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.264, stderr 0.039, n = 39). While re-running with a tighter segmentation threshold for cell07, nothing in the figure changed at print size (coefficient 0.270, stderr 0.036, n = 56). While fitting the one-lag kernel for cell15, the estimate moved less than one standard error (coefficient 0.281, stderr 0.023, n = 51).

### Step 23: comparing per-cell orderings

While re-running with a tighter segmentation threshold for cell01, nothing in the figure changed at print size (coefficient 0.225, stderr 0.047, n = 55). While comparing per-cell orderings for cell06, the ordering of cells was preserved (coefficient 0.114, stderr 0.050, n = 50). While re-exporting the raw traces for cell08, the coefficient tracked epoch count more closely than duration (coefficient 0.301, stderr 0.039, n = 53). While segmenting epochs for cell22, two cells fell out of the usable range (coefficient 0.231, stderr 0.041, n = 41). This is the part that will need a real statistical argument.

```python
coefs = fit_per_cell(rows, threshold=0.68)
lo, hi = ci(coefs, seed=74)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While segmenting epochs for cell23, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.161, stderr 0.037, n = 55). While fitting the one-lag kernel for cell21, the ordering of cells was preserved (coefficient 0.188, stderr 0.026, n = 41). While fitting the one-lag kernel for cell17, two cells fell out of the usable range (coefficient 0.300, stderr 0.035, n = 57). While checking residual autocorrelation for cell06, the coefficient tracked epoch count more closely than duration (coefficient 0.186, stderr 0.014, n = 44).

While segmenting epochs for cell14, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.156, stderr 0.037, n = 38). While re-exporting the raw traces for cell11, two cells fell out of the usable range (coefficient 0.103, stderr 0.037, n = 55). While re-running with a tighter segmentation threshold for cell02, the CI narrowed by roughly a tenth (coefficient 0.160, stderr 0.011, n = 50). While re-running with a tighter segmentation threshold for cell14, the estimate moved less than one standard error (coefficient 0.114, stderr 0.019, n = 48). While comparing per-cell orderings for cell19, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.201, stderr 0.011, n = 42). While re-running with a tighter segmentation threshold for cell21, the CI narrowed by roughly a tenth (coefficient 0.250, stderr 0.017, n = 50). This is the part that will need a real statistical argument.

### Step 24: segmenting epochs

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell18    0.204  0.022   0.160  0.248  47        2000
cell11    0.152  0.036   0.080  0.223  53        1000
cell18    0.186  0.049   0.089  0.282  43        1000
cell01    0.193  0.049   0.098  0.289  51        4000
cell05    0.097  0.026   0.045  0.148  55        1000
cell18    0.205  0.043   0.121  0.289  42        1000
cell14    0.097  0.018   0.063  0.132  49        4000
cell09    0.080  0.043   -0.004  0.164  47        2000
cell11    0.174  0.026   0.123  0.226  39        2000
cell09    0.094  0.048   0.000  0.188  49        2000
cell10    0.246  0.046   0.156  0.336  58        1000
cell13    0.099  0.042   0.017  0.181  46        4000
cell24    0.194  0.012   0.171  0.218  44        500
cell02    0.136  0.025   0.086  0.186  56        4000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell22    0.179  0.050   0.082  0.277  44        4000
cell02    0.263  0.028   0.207  0.318  45        4000
cell17    0.182  0.013   0.156  0.207  44        500
cell19    0.305  0.042   0.223  0.387  53        500
cell05    0.276  0.022   0.233  0.319  57        4000
cell22    0.181  0.045   0.093  0.270  42        2000
cell02    0.127  0.050   0.029  0.225  57        2000
cell01    0.150  0.034   0.084  0.216  39        1000
cell16    0.109  0.021   0.067  0.152  45        500
cell18    0.216  0.049   0.119  0.313  41        4000
cell07    0.254  0.024   0.207  0.301  41        4000
cell13    0.135  0.017   0.101  0.169  40        1000
```

While auditing the holding potential column for cell07, the ordering of cells was preserved (coefficient 0.094, stderr 0.030, n = 40). While bootstrapping the CI for cell14, two cells fell out of the usable range (coefficient 0.248, stderr 0.020, n = 48). While re-exporting the raw traces for cell02, the CI narrowed by roughly a tenth (coefficient 0.081, stderr 0.016, n = 58). While segmenting epochs for cell05, the coefficient tracked epoch count more closely than duration (coefficient 0.128, stderr 0.027, n = 51). While bootstrapping the CI for cell12, two cells fell out of the usable range (coefficient 0.194, stderr 0.044, n = 57). While segmenting epochs for cell23, the coefficient tracked epoch count more closely than duration (coefficient 0.226, stderr 0.042, n = 53). Parking this until the re-segmentation lands.

### Step 25: fitting the one-lag kernel

```python
coefs = fit_per_cell(rows, threshold=0.73)
lo, hi = ci(coefs, seed=7)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```python
coefs = fit_per_cell(rows, threshold=0.70)
lo, hi = ci(coefs, seed=65)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell02    0.152  0.020   0.113  0.191  39        1000
cell05    0.153  0.023   0.108  0.197  56        2000
cell04    0.246  0.039   0.170  0.322  42        2000
cell10    0.291  0.043   0.207  0.375  45        2000
cell23    0.116  0.032   0.052  0.179  51        2000
cell11    0.132  0.043   0.047  0.216  44        4000
cell13    0.184  0.030   0.125  0.242  50        500
cell11    0.223  0.018   0.188  0.259  46        500
cell02    0.156  0.017   0.122  0.190  53        1000
cell06    0.185  0.022   0.142  0.228  54        500
cell20    0.173  0.012   0.149  0.197  41        4000
cell08    0.093  0.031   0.032  0.155  56        4000
cell09    0.126  0.019   0.088  0.164  53        500
cell06    0.299  0.033   0.234  0.364  49        500
```

While re-running with a tighter segmentation threshold for cell19, the estimate moved less than one standard error (coefficient 0.120, stderr 0.022, n = 43). While fitting the one-lag kernel for cell22, two cells fell out of the usable range (coefficient 0.093, stderr 0.030, n = 46). While re-running with a tighter segmentation threshold for cell14, the ordering of cells was preserved (coefficient 0.281, stderr 0.016, n = 49). While re-running with a tighter segmentation threshold for cell23, nothing in the figure changed at print size (coefficient 0.167, stderr 0.013, n = 55). While fitting the one-lag kernel for cell17, the estimate moved less than one standard error (coefficient 0.181, stderr 0.017, n = 54). While checking residual autocorrelation for cell19, the ordering of cells was preserved (coefficient 0.251, stderr 0.017, n = 54).

### Step 26: segmenting epochs

```python
coefs = fit_per_cell(rows, threshold=0.38)
lo, hi = ci(coefs, seed=5)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```python
coefs = fit_per_cell(rows, threshold=0.78)
lo, hi = ci(coefs, seed=76)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While comparing per-cell orderings for cell16, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.155, stderr 0.038, n = 50). While comparing per-cell orderings for cell14, nothing in the figure changed at print size (coefficient 0.283, stderr 0.023, n = 52). While comparing per-cell orderings for cell20, the CI narrowed by roughly a tenth (coefficient 0.309, stderr 0.041, n = 57). While re-running with a tighter segmentation threshold for cell15, two cells fell out of the usable range (coefficient 0.100, stderr 0.016, n = 44). While re-running with a tighter segmentation threshold for cell17, the coefficient tracked epoch count more closely than duration (coefficient 0.234, stderr 0.011, n = 46). While comparing per-cell orderings for cell18, the estimate moved less than one standard error (coefficient 0.200, stderr 0.015, n = 52). Flagging it so it does not get rediscovered next week.

While re-running with a tighter segmentation threshold for cell15, two cells fell out of the usable range (coefficient 0.212, stderr 0.041, n = 43). While comparing per-cell orderings for cell05, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.112, stderr 0.017, n = 41). While bootstrapping the CI for cell21, the ordering of cells was preserved (coefficient 0.179, stderr 0.041, n = 47).

### Step 27: fitting the one-lag kernel

While fitting the one-lag kernel for cell01, two cells fell out of the usable range (coefficient 0.140, stderr 0.022, n = 48). While checking residual autocorrelation for cell20, the estimate moved less than one standard error (coefficient 0.293, stderr 0.033, n = 41). While comparing per-cell orderings for cell02, two cells fell out of the usable range (coefficient 0.144, stderr 0.037, n = 57).

While segmenting epochs for cell18, the CI narrowed by roughly a tenth (coefficient 0.159, stderr 0.026, n = 44). While segmenting epochs for cell16, the coefficient tracked epoch count more closely than duration (coefficient 0.242, stderr 0.015, n = 56). While re-exporting the raw traces for cell10, the CI narrowed by roughly a tenth (coefficient 0.188, stderr 0.038, n = 38). While bootstrapping the CI for cell15, the estimate moved less than one standard error (coefficient 0.208, stderr 0.024, n = 47). While bootstrapping the CI for cell19, nothing in the figure changed at print size (coefficient 0.228, stderr 0.041, n = 44). While comparing per-cell orderings for cell04, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.254, stderr 0.046, n = 43). Worth noting for the writeup, though not a result on its own.

```python
coefs = fit_per_cell(rows, threshold=0.64)
lo, hi = ci(coefs, seed=16)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell16    0.131  0.034   0.063  0.198  54        500
cell23    0.127  0.034   0.060  0.194  43        1000
cell12    0.216  0.011   0.196  0.237  42        500
cell06    0.130  0.045   0.042  0.218  57        500
cell20    0.084  0.018   0.049  0.119  40        2000
cell16    0.099  0.016   0.067  0.131  42        1000
cell21    0.238  0.021   0.197  0.280  53        1000
cell20    0.261  0.029   0.203  0.318  52        4000
cell05    0.107  0.012   0.084  0.130  46        2000
cell20    0.297  0.042   0.216  0.379  50        4000
cell12    0.144  0.030   0.084  0.204  38        1000
cell19    0.292  0.027   0.240  0.344  44        2000
```

### Step 28: fitting the one-lag kernel

```python
coefs = fit_per_cell(rows, threshold=0.50)
lo, hi = ci(coefs, seed=24)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While checking residual autocorrelation for cell14, nothing in the figure changed at print size (coefficient 0.249, stderr 0.013, n = 48). While re-exporting the raw traces for cell03, the estimate moved less than one standard error (coefficient 0.234, stderr 0.013, n = 53). While re-running with a tighter segmentation threshold for cell23, two cells fell out of the usable range (coefficient 0.284, stderr 0.036, n = 43). While comparing per-cell orderings for cell20, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.182, stderr 0.030, n = 50). While bootstrapping the CI for cell07, the CI narrowed by roughly a tenth (coefficient 0.138, stderr 0.012, n = 49). While auditing the holding potential column for cell08, the CI narrowed by roughly a tenth (coefficient 0.251, stderr 0.022, n = 50).

While comparing per-cell orderings for cell11, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.137, stderr 0.039, n = 55). While comparing per-cell orderings for cell21, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.212, stderr 0.015, n = 44). While re-running with a tighter segmentation threshold for cell12, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.109, stderr 0.026, n = 48). While bootstrapping the CI for cell02, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.169, stderr 0.016, n = 48). While auditing the holding potential column for cell13, the ordering of cells was preserved (coefficient 0.124, stderr 0.025, n = 51).

### Step 29: comparing per-cell orderings

While fitting the one-lag kernel for cell12, the coefficient tracked epoch count more closely than duration (coefficient 0.105, stderr 0.018, n = 55). While bootstrapping the CI for cell07, the ordering of cells was preserved (coefficient 0.155, stderr 0.025, n = 43). While checking residual autocorrelation for cell21, the ordering of cells was preserved (coefficient 0.101, stderr 0.019, n = 43). While re-exporting the raw traces for cell11, the estimate moved less than one standard error (coefficient 0.132, stderr 0.030, n = 42). While segmenting epochs for cell22, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.166, stderr 0.027, n = 57). Flagging it so it does not get rediscovered next week.

```python
coefs = fit_per_cell(rows, threshold=0.44)
lo, hi = ci(coefs, seed=0)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While re-exporting the raw traces for cell20, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.237, stderr 0.018, n = 54). While re-running with a tighter segmentation threshold for cell24, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.173, stderr 0.044, n = 52). While segmenting epochs for cell19, the estimate moved less than one standard error (coefficient 0.126, stderr 0.025, n = 40). While checking residual autocorrelation for cell22, the ordering of cells was preserved (coefficient 0.085, stderr 0.020, n = 45). While fitting the one-lag kernel for cell03, two cells fell out of the usable range (coefficient 0.270, stderr 0.012, n = 58). While re-running with a tighter segmentation threshold for cell22, the coefficient tracked epoch count more closely than duration (coefficient 0.245, stderr 0.028, n = 56). This is the part that will need a real statistical argument.

### Step 30: comparing per-cell orderings

While checking residual autocorrelation for cell24, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.094, stderr 0.022, n = 56). While fitting the one-lag kernel for cell03, the CI narrowed by roughly a tenth (coefficient 0.181, stderr 0.014, n = 44). While bootstrapping the CI for cell10, two cells fell out of the usable range (coefficient 0.279, stderr 0.013, n = 52). While comparing per-cell orderings for cell06, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.202, stderr 0.027, n = 57). While segmenting epochs for cell11, the CI narrowed by roughly a tenth (coefficient 0.080, stderr 0.016, n = 41). While re-exporting the raw traces for cell02, the ordering of cells was preserved (coefficient 0.304, stderr 0.039, n = 47). Flagging it so it does not get rediscovered next week.

While checking residual autocorrelation for cell20, nothing in the figure changed at print size (coefficient 0.187, stderr 0.026, n = 42). While re-exporting the raw traces for cell24, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.149, stderr 0.018, n = 39). While checking residual autocorrelation for cell20, the ordering of cells was preserved (coefficient 0.192, stderr 0.032, n = 38). While checking residual autocorrelation for cell23, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.169, stderr 0.050, n = 43).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell10    0.218  0.011   0.195  0.240  48        2000
cell11    0.293  0.035   0.225  0.361  42        2000
cell07    0.236  0.045   0.147  0.325  43        500
cell02    0.152  0.041   0.072  0.232  57        2000
cell19    0.250  0.045   0.163  0.337  50        1000
cell11    0.255  0.041   0.175  0.335  57        2000
cell12    0.174  0.043   0.089  0.259  55        500
cell19    0.208  0.047   0.116  0.299  48        1000
cell06    0.285  0.017   0.251  0.318  53        2000
cell13    0.310  0.017   0.277  0.342  58        2000
cell24    0.204  0.027   0.150  0.257  39        500
cell11    0.178  0.039   0.102  0.254  53        4000
cell23    0.231  0.046   0.140  0.322  48        2000
cell08    0.243  0.047   0.151  0.334  54        4000
```

### Step 31: re-running with a tighter segmentation threshold

While comparing per-cell orderings for cell16, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.141, stderr 0.029, n = 47). While fitting the one-lag kernel for cell14, two cells fell out of the usable range (coefficient 0.215, stderr 0.029, n = 52). While re-exporting the raw traces for cell15, two cells fell out of the usable range (coefficient 0.289, stderr 0.018, n = 43).

While comparing per-cell orderings for cell14, the coefficient tracked epoch count more closely than duration (coefficient 0.218, stderr 0.018, n = 56). While re-running with a tighter segmentation threshold for cell11, nothing in the figure changed at print size (coefficient 0.230, stderr 0.035, n = 43). While checking residual autocorrelation for cell02, two cells fell out of the usable range (coefficient 0.238, stderr 0.043, n = 58). While auditing the holding potential column for cell23, nothing in the figure changed at print size (coefficient 0.176, stderr 0.042, n = 44). While re-exporting the raw traces for cell11, two cells fell out of the usable range (coefficient 0.275, stderr 0.015, n = 47).

### Step 32: re-exporting the raw traces

While re-exporting the raw traces for cell09, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.167, stderr 0.028, n = 46). While bootstrapping the CI for cell11, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.296, stderr 0.033, n = 52). While checking residual autocorrelation for cell16, the CI narrowed by roughly a tenth (coefficient 0.218, stderr 0.026, n = 58). While re-exporting the raw traces for cell21, the ordering of cells was preserved (coefficient 0.254, stderr 0.026, n = 50).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell06    0.118  0.013   0.093  0.143  39        500
cell21    0.092  0.048   -0.002  0.186  54        500
cell17    0.116  0.040   0.037  0.195  39        500
cell13    0.287  0.035   0.220  0.355  54        4000
cell02    0.264  0.011   0.243  0.284  50        500
cell13    0.123  0.025   0.074  0.172  38        4000
cell15    0.146  0.041   0.064  0.227  39        2000
cell12    0.235  0.049   0.140  0.331  51        4000
cell15    0.228  0.019   0.190  0.266  40        2000
cell10    0.298  0.048   0.205  0.392  55        1000
```

While auditing the holding potential column for cell03, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.093, stderr 0.022, n = 39). While checking residual autocorrelation for cell07, the CI narrowed by roughly a tenth (coefficient 0.301, stderr 0.037, n = 45). While checking residual autocorrelation for cell08, two cells fell out of the usable range (coefficient 0.244, stderr 0.029, n = 38). While comparing per-cell orderings for cell02, the ordering of cells was preserved (coefficient 0.122, stderr 0.037, n = 56). While auditing the holding potential column for cell15, nothing in the figure changed at print size (coefficient 0.239, stderr 0.014, n = 50). While auditing the holding potential column for cell22, the ordering of cells was preserved (coefficient 0.219, stderr 0.049, n = 48).

### Step 33: comparing per-cell orderings

While auditing the holding potential column for cell19, the coefficient tracked epoch count more closely than duration (coefficient 0.285, stderr 0.037, n = 50). While re-running with a tighter segmentation threshold for cell21, nothing in the figure changed at print size (coefficient 0.291, stderr 0.028, n = 47). While segmenting epochs for cell08, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.084, stderr 0.012, n = 55). Worth noting for the writeup, though not a result on its own.

While checking residual autocorrelation for cell08, two cells fell out of the usable range (coefficient 0.212, stderr 0.030, n = 56). While checking residual autocorrelation for cell14, the estimate moved less than one standard error (coefficient 0.126, stderr 0.015, n = 46). While fitting the one-lag kernel for cell24, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.299, stderr 0.027, n = 45). While checking residual autocorrelation for cell24, two cells fell out of the usable range (coefficient 0.259, stderr 0.012, n = 53). While segmenting epochs for cell03, two cells fell out of the usable range (coefficient 0.236, stderr 0.022, n = 56). Parking this until the re-segmentation lands.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell06    0.100  0.029   0.043  0.158  49        500
cell22    0.098  0.033   0.033  0.163  49        1000
cell19    0.107  0.023   0.063  0.151  51        4000
cell23    0.281  0.012   0.257  0.305  43        2000
cell05    0.181  0.044   0.096  0.267  58        500
cell22    0.136  0.040   0.057  0.215  48        2000
cell10    0.202  0.046   0.112  0.293  51        500
cell10    0.126  0.044   0.039  0.212  53        500
cell22    0.262  0.034   0.196  0.327  39        2000
cell21    0.196  0.019   0.160  0.232  56        2000
cell06    0.302  0.044   0.216  0.388  58        500
cell05    0.082  0.047   -0.009  0.174  49        2000
cell12    0.132  0.011   0.110  0.155  47        2000
cell09    0.229  0.031   0.169  0.290  55        2000
```

### Step 34: bootstrapping the CI

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell16    0.153  0.012   0.128  0.177  43        2000
cell19    0.108  0.027   0.056  0.160  57        500
cell16    0.098  0.018   0.063  0.133  39        1000
cell12    0.148  0.013   0.121  0.174  40        4000
cell02    0.092  0.046   0.002  0.182  54        4000
cell17    0.250  0.016   0.219  0.281  42        500
cell15    0.233  0.034   0.166  0.301  54        1000
cell06    0.131  0.039   0.056  0.207  44        2000
cell24    0.218  0.026   0.168  0.268  52        500
cell08    0.288  0.026   0.237  0.340  49        2000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell11    0.234  0.043   0.150  0.318  56        1000
cell10    0.127  0.042   0.045  0.208  55        2000
cell04    0.280  0.032   0.218  0.343  38        500
cell06    0.305  0.048   0.211  0.399  46        4000
cell22    0.205  0.031   0.144  0.265  46        4000
cell16    0.262  0.025   0.213  0.311  57        500
cell05    0.264  0.014   0.237  0.291  54        500
cell24    0.204  0.040   0.126  0.282  38        500
cell12    0.109  0.024   0.061  0.157  46        500
cell09    0.170  0.035   0.102  0.239  46        2000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell02    0.174  0.048   0.080  0.269  57        1000
cell10    0.120  0.040   0.042  0.198  41        2000
cell13    0.286  0.012   0.263  0.309  49        500
cell13    0.243  0.019   0.205  0.280  52        500
cell04    0.264  0.040   0.185  0.342  42        2000
cell12    0.249  0.041   0.170  0.329  39        2000
cell16    0.271  0.033   0.207  0.335  54        500
```

While re-exporting the raw traces for cell22, the coefficient tracked epoch count more closely than duration (coefficient 0.265, stderr 0.017, n = 51). While bootstrapping the CI for cell21, the estimate moved less than one standard error (coefficient 0.261, stderr 0.047, n = 48). While checking residual autocorrelation for cell05, the CI narrowed by roughly a tenth (coefficient 0.284, stderr 0.030, n = 55). While auditing the holding potential column for cell11, the CI narrowed by roughly a tenth (coefficient 0.192, stderr 0.024, n = 48). Parking this until the re-segmentation lands.

### Step 35: bootstrapping the CI

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell05    0.119  0.038   0.043  0.194  56        2000
cell03    0.234  0.042   0.150  0.317  58        4000
cell06    0.105  0.016   0.074  0.136  42        2000
cell18    0.189  0.024   0.142  0.236  42        500
cell07    0.167  0.021   0.126  0.207  42        500
cell22    0.160  0.030   0.101  0.219  56        2000
cell02    0.196  0.036   0.126  0.266  58        1000
cell20    0.167  0.027   0.114  0.220  38        4000
cell23    0.214  0.031   0.153  0.275  46        1000
```

While auditing the holding potential column for cell01, the estimate moved less than one standard error (coefficient 0.286, stderr 0.017, n = 50). While checking residual autocorrelation for cell14, the ordering of cells was preserved (coefficient 0.233, stderr 0.049, n = 40). While re-running with a tighter segmentation threshold for cell11, the coefficient tracked epoch count more closely than duration (coefficient 0.208, stderr 0.041, n = 43). While fitting the one-lag kernel for cell01, the CI narrowed by roughly a tenth (coefficient 0.103, stderr 0.050, n = 54). While re-exporting the raw traces for cell15, the coefficient tracked epoch count more closely than duration (coefficient 0.226, stderr 0.045, n = 41). Noted and moved on; it does not change the decision.

### Step 36: fitting the one-lag kernel

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell03    0.283  0.038   0.209  0.357  44        1000
cell14    0.087  0.019   0.049  0.125  41        1000
cell10    0.081  0.028   0.025  0.136  39        4000
cell08    0.258  0.031   0.198  0.319  55        500
cell23    0.146  0.048   0.052  0.240  55        2000
cell17    0.286  0.019   0.249  0.323  58        500
cell23    0.137  0.033   0.073  0.202  43        4000
```

While re-running with a tighter segmentation threshold for cell06, the ordering of cells was preserved (coefficient 0.299, stderr 0.036, n = 56). While re-running with a tighter segmentation threshold for cell08, the estimate moved less than one standard error (coefficient 0.163, stderr 0.047, n = 40). While fitting the one-lag kernel for cell24, the ordering of cells was preserved (coefficient 0.208, stderr 0.012, n = 45).

While segmenting epochs for cell02, nothing in the figure changed at print size (coefficient 0.124, stderr 0.035, n = 49). While checking residual autocorrelation for cell16, the ordering of cells was preserved (coefficient 0.264, stderr 0.014, n = 58). While auditing the holding potential column for cell15, the coefficient tracked epoch count more closely than duration (coefficient 0.195, stderr 0.043, n = 50). This is the part that will need a real statistical argument.

### Step 37: re-running with a tighter segmentation threshold

While segmenting epochs for cell13, the CI narrowed by roughly a tenth (coefficient 0.226, stderr 0.045, n = 45). While segmenting epochs for cell05, the estimate moved less than one standard error (coefficient 0.302, stderr 0.027, n = 55). While comparing per-cell orderings for cell09, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.136, stderr 0.028, n = 58).

While segmenting epochs for cell15, nothing in the figure changed at print size (coefficient 0.173, stderr 0.019, n = 49). While auditing the holding potential column for cell17, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.230, stderr 0.029, n = 52). While segmenting epochs for cell02, the CI narrowed by roughly a tenth (coefficient 0.202, stderr 0.044, n = 40). While segmenting epochs for cell08, two cells fell out of the usable range (coefficient 0.084, stderr 0.015, n = 50). While segmenting epochs for cell15, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.306, stderr 0.032, n = 44). While re-exporting the raw traces for cell21, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.221, stderr 0.022, n = 39).

While re-exporting the raw traces for cell24, the estimate moved less than one standard error (coefficient 0.144, stderr 0.027, n = 39). While bootstrapping the CI for cell16, the ordering of cells was preserved (coefficient 0.227, stderr 0.040, n = 51). While fitting the one-lag kernel for cell08, the coefficient tracked epoch count more closely than duration (coefficient 0.091, stderr 0.037, n = 46). While fitting the one-lag kernel for cell18, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.089, stderr 0.037, n = 40). Flagging it so it does not get rediscovered next week.

While comparing per-cell orderings for cell16, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.260, stderr 0.042, n = 39). While comparing per-cell orderings for cell03, the estimate moved less than one standard error (coefficient 0.108, stderr 0.029, n = 44). While comparing per-cell orderings for cell05, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.187, stderr 0.047, n = 38). While fitting the one-lag kernel for cell22, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.129, stderr 0.047, n = 58). While comparing per-cell orderings for cell11, nothing in the figure changed at print size (coefficient 0.197, stderr 0.031, n = 52). While checking residual autocorrelation for cell17, the ordering of cells was preserved (coefficient 0.082, stderr 0.035, n = 40).

### Step 38: auditing the holding potential column

While checking residual autocorrelation for cell04, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.210, stderr 0.039, n = 54). While comparing per-cell orderings for cell10, the estimate moved less than one standard error (coefficient 0.183, stderr 0.025, n = 50). While bootstrapping the CI for cell12, two cells fell out of the usable range (coefficient 0.140, stderr 0.039, n = 47). While re-running with a tighter segmentation threshold for cell05, the coefficient tracked epoch count more closely than duration (coefficient 0.182, stderr 0.027, n = 39). While comparing per-cell orderings for cell09, nothing in the figure changed at print size (coefficient 0.147, stderr 0.029, n = 52). While auditing the holding potential column for cell15, the ordering of cells was preserved (coefficient 0.190, stderr 0.037, n = 53).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell13    0.180  0.047   0.088  0.272  43        2000
cell17    0.214  0.049   0.117  0.310  56        2000
cell21    0.182  0.026   0.131  0.232  46        2000
cell15    0.285  0.030   0.227  0.344  50        4000
cell15    0.101  0.045   0.012  0.189  41        500
cell23    0.277  0.049   0.181  0.373  46        1000
cell19    0.283  0.028   0.229  0.338  46        2000
cell06    0.220  0.018   0.185  0.256  53        4000
cell13    0.253  0.035   0.185  0.321  57        2000
```

```python
coefs = fit_per_cell(rows, threshold=0.40)
lo, hi = ci(coefs, seed=32)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 39: re-exporting the raw traces

```python
coefs = fit_per_cell(rows, threshold=0.68)
lo, hi = ci(coefs, seed=88)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While auditing the holding potential column for cell21, the ordering of cells was preserved (coefficient 0.265, stderr 0.018, n = 47). While bootstrapping the CI for cell07, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.135, stderr 0.015, n = 42). While fitting the one-lag kernel for cell04, two cells fell out of the usable range (coefficient 0.136, stderr 0.017, n = 49). While bootstrapping the CI for cell06, nothing in the figure changed at print size (coefficient 0.308, stderr 0.048, n = 44). While checking residual autocorrelation for cell20, the estimate moved less than one standard error (coefficient 0.241, stderr 0.041, n = 51). While fitting the one-lag kernel for cell10, the CI narrowed by roughly a tenth (coefficient 0.172, stderr 0.048, n = 47).

```python
coefs = fit_per_cell(rows, threshold=0.71)
lo, hi = ci(coefs, seed=57)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While re-exporting the raw traces for cell19, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.206, stderr 0.017, n = 58). While bootstrapping the CI for cell08, nothing in the figure changed at print size (coefficient 0.102, stderr 0.018, n = 42). While fitting the one-lag kernel for cell12, two cells fell out of the usable range (coefficient 0.149, stderr 0.038, n = 55). While checking residual autocorrelation for cell23, the coefficient tracked epoch count more closely than duration (coefficient 0.203, stderr 0.042, n = 56). While bootstrapping the CI for cell10, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.126, stderr 0.012, n = 44).

### Step 40: auditing the holding potential column

While checking residual autocorrelation for cell22, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.249, stderr 0.030, n = 46). While bootstrapping the CI for cell12, nothing in the figure changed at print size (coefficient 0.125, stderr 0.040, n = 43). While bootstrapping the CI for cell10, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.234, stderr 0.018, n = 44). Flagging it so it does not get rediscovered next week.

While bootstrapping the CI for cell11, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.101, stderr 0.042, n = 53). While auditing the holding potential column for cell15, the coefficient tracked epoch count more closely than duration (coefficient 0.097, stderr 0.021, n = 45). While re-running with a tighter segmentation threshold for cell03, the estimate moved less than one standard error (coefficient 0.149, stderr 0.031, n = 53).

### Step 41: re-exporting the raw traces

While bootstrapping the CI for cell15, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.287, stderr 0.019, n = 39). While comparing per-cell orderings for cell23, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.243, stderr 0.016, n = 55). While comparing per-cell orderings for cell19, the estimate moved less than one standard error (coefficient 0.109, stderr 0.029, n = 54).

```python
coefs = fit_per_cell(rows, threshold=0.76)
lo, hi = ci(coefs, seed=84)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

