# Prior session 3 of 20

Transcript of an earlier working session on the history-kernel analysis.

### Step 1: fitting the one-lag kernel

While re-exporting the raw traces for cell09, the CI narrowed by roughly a tenth (coefficient 0.086, stderr 0.046, n = 38). While bootstrapping the CI for cell23, the estimate moved less than one standard error (coefficient 0.242, stderr 0.041, n = 41). While fitting the one-lag kernel for cell24, the CI narrowed by roughly a tenth (coefficient 0.163, stderr 0.033, n = 54).

While re-exporting the raw traces for cell05, the CI narrowed by roughly a tenth (coefficient 0.129, stderr 0.039, n = 50). While checking residual autocorrelation for cell17, the estimate moved less than one standard error (coefficient 0.146, stderr 0.036, n = 39). While bootstrapping the CI for cell16, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.253, stderr 0.013, n = 47). While fitting the one-lag kernel for cell16, two cells fell out of the usable range (coefficient 0.090, stderr 0.039, n = 43).

### Step 2: auditing the holding potential column

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell23    0.277  0.035   0.207  0.346  50        1000
cell23    0.309  0.016   0.278  0.341  42        4000
cell23    0.089  0.020   0.050  0.128  46        4000
cell09    0.306  0.027   0.254  0.359  42        2000
cell12    0.119  0.017   0.085  0.152  52        2000
cell08    0.285  0.013   0.260  0.310  40        4000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell06    0.274  0.024   0.228  0.321  54        2000
cell13    0.218  0.016   0.188  0.249  58        4000
cell05    0.255  0.039   0.178  0.331  55        4000
cell05    0.154  0.017   0.121  0.188  54        500
cell04    0.251  0.033   0.187  0.315  50        1000
cell07    0.118  0.014   0.090  0.145  41        4000
cell06    0.219  0.022   0.176  0.263  44        1000
```

While re-running with a tighter segmentation threshold for cell13, the coefficient tracked epoch count more closely than duration (coefficient 0.245, stderr 0.047, n = 46). While checking residual autocorrelation for cell07, the coefficient tracked epoch count more closely than duration (coefficient 0.197, stderr 0.043, n = 43). While comparing per-cell orderings for cell24, the CI narrowed by roughly a tenth (coefficient 0.207, stderr 0.018, n = 46). While auditing the holding potential column for cell09, the estimate moved less than one standard error (coefficient 0.233, stderr 0.042, n = 50).

### Step 3: auditing the holding potential column

While segmenting epochs for cell08, the CI narrowed by roughly a tenth (coefficient 0.271, stderr 0.011, n = 50). While checking residual autocorrelation for cell08, the coefficient tracked epoch count more closely than duration (coefficient 0.230, stderr 0.012, n = 55). While bootstrapping the CI for cell20, the ordering of cells was preserved (coefficient 0.263, stderr 0.040, n = 53). While comparing per-cell orderings for cell10, the coefficient tracked epoch count more closely than duration (coefficient 0.235, stderr 0.028, n = 42). While fitting the one-lag kernel for cell22, nothing in the figure changed at print size (coefficient 0.202, stderr 0.011, n = 43). Parking this until the re-segmentation lands.

While re-running with a tighter segmentation threshold for cell02, nothing in the figure changed at print size (coefficient 0.171, stderr 0.023, n = 55). While comparing per-cell orderings for cell04, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.123, stderr 0.016, n = 50). While segmenting epochs for cell17, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.215, stderr 0.026, n = 55).

While auditing the holding potential column for cell01, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.176, stderr 0.048, n = 40). While bootstrapping the CI for cell18, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.268, stderr 0.038, n = 57). While fitting the one-lag kernel for cell21, the ordering of cells was preserved (coefficient 0.138, stderr 0.018, n = 39). While comparing per-cell orderings for cell11, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.147, stderr 0.017, n = 53). While re-exporting the raw traces for cell01, nothing in the figure changed at print size (coefficient 0.183, stderr 0.023, n = 47). While re-running with a tighter segmentation threshold for cell23, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.278, stderr 0.025, n = 52). Parking this until the re-segmentation lands.

### Step 4: re-exporting the raw traces

While segmenting epochs for cell20, the estimate moved less than one standard error (coefficient 0.136, stderr 0.047, n = 38). While comparing per-cell orderings for cell17, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.154, stderr 0.015, n = 54). While bootstrapping the CI for cell20, the coefficient tracked epoch count more closely than duration (coefficient 0.093, stderr 0.013, n = 43). While fitting the one-lag kernel for cell03, the estimate moved less than one standard error (coefficient 0.209, stderr 0.037, n = 48).

While comparing per-cell orderings for cell18, the ordering of cells was preserved (coefficient 0.209, stderr 0.017, n = 43). While re-exporting the raw traces for cell01, the coefficient tracked epoch count more closely than duration (coefficient 0.170, stderr 0.020, n = 56). While fitting the one-lag kernel for cell14, two cells fell out of the usable range (coefficient 0.203, stderr 0.041, n = 41). While auditing the holding potential column for cell07, the CI narrowed by roughly a tenth (coefficient 0.207, stderr 0.035, n = 45). Parking this until the re-segmentation lands.

While checking residual autocorrelation for cell04, the CI narrowed by roughly a tenth (coefficient 0.289, stderr 0.027, n = 56). While fitting the one-lag kernel for cell22, the estimate moved less than one standard error (coefficient 0.140, stderr 0.041, n = 39). While fitting the one-lag kernel for cell20, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.220, stderr 0.039, n = 40). While re-running with a tighter segmentation threshold for cell12, the estimate moved less than one standard error (coefficient 0.157, stderr 0.049, n = 53). While re-running with a tighter segmentation threshold for cell13, the ordering of cells was preserved (coefficient 0.197, stderr 0.014, n = 57). While fitting the one-lag kernel for cell21, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.188, stderr 0.048, n = 43). Flagging it so it does not get rediscovered next week.

```python
coefs = fit_per_cell(rows, threshold=0.76)
lo, hi = ci(coefs, seed=4)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 5: bootstrapping the CI

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell16    0.145  0.046   0.055  0.235  42        500
cell22    0.116  0.019   0.079  0.152  38        2000
cell11    0.238  0.017   0.205  0.271  50        2000
cell16    0.263  0.033   0.198  0.329  51        500
cell18    0.110  0.040   0.031  0.189  40        2000
cell16    0.173  0.038   0.099  0.248  45        1000
cell14    0.298  0.035   0.229  0.367  49        500
```

```python
coefs = fit_per_cell(rows, threshold=0.33)
lo, hi = ci(coefs, seed=14)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```python
coefs = fit_per_cell(rows, threshold=0.36)
lo, hi = ci(coefs, seed=87)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```python
coefs = fit_per_cell(rows, threshold=0.59)
lo, hi = ci(coefs, seed=61)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 6: auditing the holding potential column

While bootstrapping the CI for cell06, the estimate moved less than one standard error (coefficient 0.223, stderr 0.040, n = 48). While segmenting epochs for cell24, the CI narrowed by roughly a tenth (coefficient 0.149, stderr 0.013, n = 38). While checking residual autocorrelation for cell01, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.122, stderr 0.021, n = 45).

```python
coefs = fit_per_cell(rows, threshold=0.71)
lo, hi = ci(coefs, seed=73)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 7: segmenting epochs

While bootstrapping the CI for cell08, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.268, stderr 0.015, n = 39). While bootstrapping the CI for cell05, the estimate moved less than one standard error (coefficient 0.306, stderr 0.020, n = 46). While auditing the holding potential column for cell09, the ordering of cells was preserved (coefficient 0.308, stderr 0.012, n = 47). While re-exporting the raw traces for cell13, two cells fell out of the usable range (coefficient 0.127, stderr 0.016, n = 54). While re-exporting the raw traces for cell06, the estimate moved less than one standard error (coefficient 0.192, stderr 0.010, n = 54).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell14    0.298  0.014   0.270  0.325  58        2000
cell23    0.124  0.011   0.102  0.147  54        4000
cell24    0.163  0.021   0.122  0.204  50        500
cell20    0.089  0.034   0.022  0.157  39        4000
cell06    0.110  0.042   0.028  0.192  43        1000
cell08    0.276  0.042   0.194  0.358  43        1000
cell05    0.244  0.016   0.213  0.275  41        500
cell10    0.222  0.047   0.130  0.314  43        2000
```

```python
coefs = fit_per_cell(rows, threshold=0.73)
lo, hi = ci(coefs, seed=39)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 8: bootstrapping the CI

While comparing per-cell orderings for cell06, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.090, stderr 0.047, n = 58). While checking residual autocorrelation for cell13, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.178, stderr 0.019, n = 46). While re-exporting the raw traces for cell01, the coefficient tracked epoch count more closely than duration (coefficient 0.169, stderr 0.020, n = 49). While fitting the one-lag kernel for cell06, the estimate moved less than one standard error (coefficient 0.098, stderr 0.036, n = 45). While bootstrapping the CI for cell01, the estimate moved less than one standard error (coefficient 0.111, stderr 0.024, n = 41).

While segmenting epochs for cell16, the estimate moved less than one standard error (coefficient 0.116, stderr 0.019, n = 53). While comparing per-cell orderings for cell16, the estimate moved less than one standard error (coefficient 0.200, stderr 0.018, n = 38). While fitting the one-lag kernel for cell03, two cells fell out of the usable range (coefficient 0.274, stderr 0.045, n = 39). While auditing the holding potential column for cell02, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.146, stderr 0.029, n = 48). While fitting the one-lag kernel for cell19, two cells fell out of the usable range (coefficient 0.275, stderr 0.013, n = 41). While bootstrapping the CI for cell01, the ordering of cells was preserved (coefficient 0.165, stderr 0.028, n = 42).

```python
coefs = fit_per_cell(rows, threshold=0.65)
lo, hi = ci(coefs, seed=42)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 9: comparing per-cell orderings

While checking residual autocorrelation for cell04, the estimate moved less than one standard error (coefficient 0.275, stderr 0.047, n = 51). While segmenting epochs for cell03, the CI narrowed by roughly a tenth (coefficient 0.285, stderr 0.034, n = 41). While checking residual autocorrelation for cell07, the estimate moved less than one standard error (coefficient 0.189, stderr 0.033, n = 38). While re-exporting the raw traces for cell07, nothing in the figure changed at print size (coefficient 0.189, stderr 0.040, n = 52). While comparing per-cell orderings for cell07, nothing in the figure changed at print size (coefficient 0.105, stderr 0.010, n = 40).

While fitting the one-lag kernel for cell20, two cells fell out of the usable range (coefficient 0.122, stderr 0.015, n = 45). While fitting the one-lag kernel for cell02, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.209, stderr 0.015, n = 51). While comparing per-cell orderings for cell22, the coefficient tracked epoch count more closely than duration (coefficient 0.111, stderr 0.021, n = 45). While auditing the holding potential column for cell02, the CI narrowed by roughly a tenth (coefficient 0.113, stderr 0.040, n = 45). Worth noting for the writeup, though not a result on its own.

While re-exporting the raw traces for cell10, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.122, stderr 0.035, n = 50). While fitting the one-lag kernel for cell19, the coefficient tracked epoch count more closely than duration (coefficient 0.169, stderr 0.037, n = 57). While auditing the holding potential column for cell21, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.244, stderr 0.039, n = 41). While fitting the one-lag kernel for cell23, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.227, stderr 0.022, n = 51). While fitting the one-lag kernel for cell14, two cells fell out of the usable range (coefficient 0.308, stderr 0.044, n = 52). While re-running with a tighter segmentation threshold for cell07, the CI narrowed by roughly a tenth (coefficient 0.094, stderr 0.011, n = 56). This is the part that will need a real statistical argument.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell02    0.193  0.048   0.100  0.287  56        2000
cell08    0.146  0.046   0.056  0.236  46        4000
cell15    0.148  0.021   0.108  0.188  51        2000
cell22    0.130  0.015   0.099  0.160  38        4000
cell03    0.159  0.033   0.094  0.223  39        500
cell18    0.084  0.014   0.058  0.111  58        500
```

### Step 10: segmenting epochs

While segmenting epochs for cell04, the estimate moved less than one standard error (coefficient 0.119, stderr 0.016, n = 41). While re-running with a tighter segmentation threshold for cell16, two cells fell out of the usable range (coefficient 0.305, stderr 0.039, n = 42). While bootstrapping the CI for cell24, the coefficient tracked epoch count more closely than duration (coefficient 0.166, stderr 0.050, n = 43). While bootstrapping the CI for cell18, nothing in the figure changed at print size (coefficient 0.155, stderr 0.016, n = 40). While segmenting epochs for cell16, the estimate moved less than one standard error (coefficient 0.190, stderr 0.024, n = 41). While checking residual autocorrelation for cell20, the coefficient tracked epoch count more closely than duration (coefficient 0.131, stderr 0.035, n = 43). Worth noting for the writeup, though not a result on its own.

While re-exporting the raw traces for cell05, the estimate moved less than one standard error (coefficient 0.210, stderr 0.046, n = 55). While comparing per-cell orderings for cell02, two cells fell out of the usable range (coefficient 0.129, stderr 0.046, n = 46). While segmenting epochs for cell22, the estimate moved less than one standard error (coefficient 0.139, stderr 0.018, n = 45). While checking residual autocorrelation for cell02, two cells fell out of the usable range (coefficient 0.108, stderr 0.017, n = 55). While auditing the holding potential column for cell24, nothing in the figure changed at print size (coefficient 0.151, stderr 0.026, n = 49). While comparing per-cell orderings for cell22, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.271, stderr 0.027, n = 55).

While comparing per-cell orderings for cell06, the CI narrowed by roughly a tenth (coefficient 0.293, stderr 0.036, n = 42). While fitting the one-lag kernel for cell15, the ordering of cells was preserved (coefficient 0.105, stderr 0.044, n = 38). While segmenting epochs for cell23, the CI narrowed by roughly a tenth (coefficient 0.275, stderr 0.021, n = 41). While auditing the holding potential column for cell11, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.139, stderr 0.048, n = 46).

### Step 11: bootstrapping the CI

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell11    0.290  0.029   0.233  0.348  45        500
cell22    0.187  0.019   0.150  0.223  46        500
cell12    0.090  0.013   0.064  0.116  58        4000
cell07    0.272  0.033   0.207  0.336  55        1000
cell20    0.238  0.048   0.143  0.333  50        1000
cell05    0.279  0.035   0.211  0.347  55        4000
cell06    0.197  0.034   0.131  0.263  42        1000
cell15    0.152  0.025   0.103  0.201  47        1000
cell22    0.232  0.011   0.211  0.253  56        4000
cell18    0.165  0.043   0.081  0.249  54        4000
cell22    0.275  0.047   0.183  0.367  49        4000
cell21    0.166  0.014   0.139  0.193  57        1000
cell14    0.199  0.015   0.170  0.229  54        2000
cell03    0.309  0.013   0.284  0.334  47        2000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell24    0.188  0.038   0.114  0.262  54        4000
cell18    0.219  0.032   0.156  0.282  49        500
cell22    0.213  0.050   0.116  0.311  52        4000
cell18    0.194  0.021   0.152  0.235  53        4000
cell03    0.203  0.037   0.130  0.276  53        500
cell21    0.218  0.047   0.127  0.310  44        4000
cell11    0.123  0.021   0.082  0.165  51        500
```

### Step 12: comparing per-cell orderings

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell05    0.113  0.012   0.089  0.137  42        1000
cell23    0.245  0.020   0.207  0.284  52        1000
cell24    0.271  0.038   0.197  0.345  51        4000
cell13    0.179  0.028   0.124  0.235  38        4000
cell22    0.229  0.042   0.146  0.311  41        4000
cell03    0.222  0.037   0.149  0.295  39        500
cell07    0.238  0.034   0.171  0.306  47        1000
cell05    0.167  0.040   0.090  0.245  48        4000
cell09    0.156  0.012   0.132  0.179  43        500
cell03    0.288  0.023   0.243  0.333  55        1000
cell13    0.296  0.021   0.254  0.338  57        2000
cell08    0.286  0.018   0.251  0.322  48        1000
cell17    0.215  0.014   0.186  0.243  47        4000
```

While auditing the holding potential column for cell16, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.159, stderr 0.038, n = 41). While re-running with a tighter segmentation threshold for cell11, the coefficient tracked epoch count more closely than duration (coefficient 0.169, stderr 0.018, n = 51). While fitting the one-lag kernel for cell11, the estimate moved less than one standard error (coefficient 0.212, stderr 0.034, n = 48).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell04    0.126  0.044   0.039  0.213  58        1000
cell07    0.194  0.028   0.140  0.248  45        500
cell03    0.249  0.032   0.186  0.312  49        1000
cell07    0.295  0.029   0.238  0.351  47        2000
cell23    0.105  0.044   0.018  0.192  55        4000
cell14    0.265  0.019   0.228  0.301  50        4000
```

```python
coefs = fit_per_cell(rows, threshold=0.79)
lo, hi = ci(coefs, seed=34)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 13: bootstrapping the CI

While checking residual autocorrelation for cell08, the CI narrowed by roughly a tenth (coefficient 0.173, stderr 0.034, n = 49). While re-running with a tighter segmentation threshold for cell22, the ordering of cells was preserved (coefficient 0.274, stderr 0.019, n = 45). While fitting the one-lag kernel for cell19, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.136, stderr 0.043, n = 49).

While re-running with a tighter segmentation threshold for cell12, two cells fell out of the usable range (coefficient 0.262, stderr 0.013, n = 47). While auditing the holding potential column for cell06, the ordering of cells was preserved (coefficient 0.097, stderr 0.022, n = 53). While checking residual autocorrelation for cell14, the coefficient tracked epoch count more closely than duration (coefficient 0.166, stderr 0.049, n = 54). While checking residual autocorrelation for cell12, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.136, stderr 0.024, n = 43).

While re-exporting the raw traces for cell21, nothing in the figure changed at print size (coefficient 0.285, stderr 0.049, n = 40). While bootstrapping the CI for cell21, the coefficient tracked epoch count more closely than duration (coefficient 0.230, stderr 0.030, n = 41). While segmenting epochs for cell18, the coefficient tracked epoch count more closely than duration (coefficient 0.170, stderr 0.037, n = 40). While bootstrapping the CI for cell23, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.290, stderr 0.021, n = 44).

### Step 14: bootstrapping the CI

```python
coefs = fit_per_cell(rows, threshold=0.72)
lo, hi = ci(coefs, seed=23)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While segmenting epochs for cell10, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.141, stderr 0.043, n = 48). While comparing per-cell orderings for cell22, two cells fell out of the usable range (coefficient 0.122, stderr 0.042, n = 40). While re-exporting the raw traces for cell16, nothing in the figure changed at print size (coefficient 0.207, stderr 0.013, n = 38).

### Step 15: checking residual autocorrelation

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell22    0.300  0.038   0.225  0.375  48        1000
cell01    0.136  0.014   0.109  0.162  48        1000
cell04    0.266  0.026   0.214  0.317  39        4000
cell06    0.157  0.047   0.066  0.249  47        500
cell17    0.103  0.010   0.083  0.122  52        1000
cell20    0.157  0.022   0.114  0.201  58        500
cell07    0.114  0.028   0.059  0.170  56        1000
cell15    0.283  0.010   0.263  0.303  41        4000
cell18    0.207  0.019   0.170  0.243  42        2000
cell23    0.174  0.015   0.144  0.204  58        1000
```

While auditing the holding potential column for cell21, the ordering of cells was preserved (coefficient 0.232, stderr 0.015, n = 45). While comparing per-cell orderings for cell01, the ordering of cells was preserved (coefficient 0.174, stderr 0.011, n = 51). While re-running with a tighter segmentation threshold for cell15, the coefficient tracked epoch count more closely than duration (coefficient 0.304, stderr 0.035, n = 40). While re-exporting the raw traces for cell02, the ordering of cells was preserved (coefficient 0.099, stderr 0.041, n = 49). While auditing the holding potential column for cell12, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.145, stderr 0.016, n = 43). While re-running with a tighter segmentation threshold for cell19, nothing in the figure changed at print size (coefficient 0.284, stderr 0.045, n = 45).

While fitting the one-lag kernel for cell15, the estimate moved less than one standard error (coefficient 0.105, stderr 0.011, n = 51). While re-running with a tighter segmentation threshold for cell12, the ordering of cells was preserved (coefficient 0.197, stderr 0.022, n = 50). While bootstrapping the CI for cell01, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.207, stderr 0.024, n = 57).

### Step 16: bootstrapping the CI

While auditing the holding potential column for cell05, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.176, stderr 0.023, n = 41). While checking residual autocorrelation for cell04, the estimate moved less than one standard error (coefficient 0.255, stderr 0.037, n = 40). While fitting the one-lag kernel for cell03, the estimate moved less than one standard error (coefficient 0.149, stderr 0.034, n = 56). While checking residual autocorrelation for cell08, the CI narrowed by roughly a tenth (coefficient 0.233, stderr 0.012, n = 55). While bootstrapping the CI for cell03, the ordering of cells was preserved (coefficient 0.143, stderr 0.012, n = 41). While auditing the holding potential column for cell24, the estimate moved less than one standard error (coefficient 0.105, stderr 0.028, n = 54). This is the part that will need a real statistical argument.

While auditing the holding potential column for cell04, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.278, stderr 0.022, n = 46). While auditing the holding potential column for cell07, nothing in the figure changed at print size (coefficient 0.212, stderr 0.028, n = 42). While segmenting epochs for cell04, the coefficient tracked epoch count more closely than duration (coefficient 0.271, stderr 0.024, n = 55). While checking residual autocorrelation for cell06, the coefficient tracked epoch count more closely than duration (coefficient 0.245, stderr 0.042, n = 52).

While segmenting epochs for cell17, the CI narrowed by roughly a tenth (coefficient 0.211, stderr 0.033, n = 58). While fitting the one-lag kernel for cell18, two cells fell out of the usable range (coefficient 0.173, stderr 0.013, n = 53). While checking residual autocorrelation for cell08, the CI narrowed by roughly a tenth (coefficient 0.258, stderr 0.028, n = 47). While comparing per-cell orderings for cell13, nothing in the figure changed at print size (coefficient 0.251, stderr 0.022, n = 58). This is the part that will need a real statistical argument.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell06    0.134  0.029   0.077  0.191  47        1000
cell03    0.138  0.033   0.073  0.202  38        2000
cell05    0.241  0.012   0.217  0.264  52        4000
cell03    0.152  0.015   0.122  0.181  55        2000
cell18    0.264  0.044   0.178  0.351  58        2000
cell13    0.199  0.014   0.171  0.227  38        500
cell06    0.183  0.018   0.149  0.218  54        2000
cell19    0.137  0.033   0.072  0.202  49        1000
cell14    0.297  0.022   0.255  0.340  47        2000
cell08    0.088  0.048   -0.006  0.183  50        4000
cell14    0.250  0.025   0.200  0.300  53        2000
cell17    0.234  0.035   0.166  0.303  50        4000
cell01    0.120  0.045   0.031  0.209  39        4000
```

### Step 17: checking residual autocorrelation

While re-exporting the raw traces for cell16, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.295, stderr 0.048, n = 58). While checking residual autocorrelation for cell01, the ordering of cells was preserved (coefficient 0.115, stderr 0.019, n = 49). While checking residual autocorrelation for cell20, two cells fell out of the usable range (coefficient 0.291, stderr 0.022, n = 38). While auditing the holding potential column for cell23, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.215, stderr 0.030, n = 49). While auditing the holding potential column for cell22, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.151, stderr 0.046, n = 56). While fitting the one-lag kernel for cell10, the CI narrowed by roughly a tenth (coefficient 0.169, stderr 0.019, n = 57).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell24    0.305  0.049   0.208  0.402  38        1000
cell03    0.151  0.030   0.092  0.209  55        500
cell21    0.160  0.020   0.120  0.199  50        500
cell01    0.191  0.025   0.142  0.240  40        2000
cell13    0.162  0.027   0.110  0.214  46        2000
cell14    0.303  0.046   0.213  0.394  49        500
cell04    0.181  0.026   0.129  0.232  38        1000
cell14    0.150  0.050   0.053  0.247  49        500
cell11    0.197  0.034   0.130  0.264  54        1000
```

While comparing per-cell orderings for cell10, the estimate moved less than one standard error (coefficient 0.152, stderr 0.026, n = 51). While re-exporting the raw traces for cell23, the CI narrowed by roughly a tenth (coefficient 0.246, stderr 0.045, n = 54). While bootstrapping the CI for cell13, the CI narrowed by roughly a tenth (coefficient 0.142, stderr 0.027, n = 48). While checking residual autocorrelation for cell02, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.264, stderr 0.037, n = 53). While segmenting epochs for cell20, the ordering of cells was preserved (coefficient 0.283, stderr 0.030, n = 52).

While re-running with a tighter segmentation threshold for cell04, two cells fell out of the usable range (coefficient 0.209, stderr 0.019, n = 52). While fitting the one-lag kernel for cell09, the coefficient tracked epoch count more closely than duration (coefficient 0.166, stderr 0.049, n = 43). While bootstrapping the CI for cell20, the coefficient tracked epoch count more closely than duration (coefficient 0.094, stderr 0.034, n = 54). While re-running with a tighter segmentation threshold for cell22, the estimate moved less than one standard error (coefficient 0.284, stderr 0.049, n = 38). While re-exporting the raw traces for cell15, nothing in the figure changed at print size (coefficient 0.095, stderr 0.044, n = 41). This is the part that will need a real statistical argument.

### Step 18: fitting the one-lag kernel

While fitting the one-lag kernel for cell14, the estimate moved less than one standard error (coefficient 0.114, stderr 0.038, n = 47). While bootstrapping the CI for cell21, the ordering of cells was preserved (coefficient 0.208, stderr 0.033, n = 49). While fitting the one-lag kernel for cell11, the coefficient tracked epoch count more closely than duration (coefficient 0.294, stderr 0.031, n = 38). While checking residual autocorrelation for cell02, nothing in the figure changed at print size (coefficient 0.235, stderr 0.013, n = 41). While fitting the one-lag kernel for cell09, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.139, stderr 0.011, n = 51). While comparing per-cell orderings for cell03, two cells fell out of the usable range (coefficient 0.219, stderr 0.021, n = 39).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell24    0.096  0.022   0.054  0.138  38        2000
cell04    0.152  0.028   0.097  0.208  52        1000
cell11    0.184  0.026   0.133  0.236  41        4000
cell16    0.258  0.046   0.169  0.348  38        2000
cell02    0.105  0.019   0.068  0.142  55        2000
cell17    0.247  0.019   0.211  0.284  53        2000
cell16    0.310  0.025   0.261  0.358  53        500
cell09    0.224  0.015   0.193  0.254  57        1000
cell03    0.119  0.047   0.026  0.212  49        1000
cell10    0.169  0.034   0.102  0.235  51        4000
cell21    0.123  0.014   0.095  0.150  44        4000
cell09    0.295  0.025   0.245  0.344  47        2000
cell05    0.110  0.028   0.055  0.165  49        4000
```

While bootstrapping the CI for cell03, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.142, stderr 0.017, n = 48). While checking residual autocorrelation for cell23, the ordering of cells was preserved (coefficient 0.161, stderr 0.046, n = 46). While auditing the holding potential column for cell13, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.177, stderr 0.018, n = 54). While checking residual autocorrelation for cell13, the CI narrowed by roughly a tenth (coefficient 0.189, stderr 0.011, n = 52). While segmenting epochs for cell02, the CI narrowed by roughly a tenth (coefficient 0.183, stderr 0.024, n = 51).

While re-exporting the raw traces for cell19, nothing in the figure changed at print size (coefficient 0.137, stderr 0.021, n = 47). While bootstrapping the CI for cell03, the CI narrowed by roughly a tenth (coefficient 0.090, stderr 0.036, n = 40). While re-running with a tighter segmentation threshold for cell13, the CI narrowed by roughly a tenth (coefficient 0.278, stderr 0.011, n = 56).

### Step 19: fitting the one-lag kernel

While fitting the one-lag kernel for cell02, two cells fell out of the usable range (coefficient 0.151, stderr 0.037, n = 48). While re-exporting the raw traces for cell09, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.178, stderr 0.013, n = 56). While segmenting epochs for cell14, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.212, stderr 0.032, n = 48). While fitting the one-lag kernel for cell17, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.129, stderr 0.013, n = 47).

While bootstrapping the CI for cell05, the ordering of cells was preserved (coefficient 0.159, stderr 0.036, n = 42). While bootstrapping the CI for cell12, the CI narrowed by roughly a tenth (coefficient 0.166, stderr 0.031, n = 39). While auditing the holding potential column for cell13, the estimate moved less than one standard error (coefficient 0.120, stderr 0.026, n = 42). While auditing the holding potential column for cell09, the estimate moved less than one standard error (coefficient 0.133, stderr 0.025, n = 46).

While checking residual autocorrelation for cell01, the CI narrowed by roughly a tenth (coefficient 0.158, stderr 0.044, n = 55). While checking residual autocorrelation for cell05, the coefficient tracked epoch count more closely than duration (coefficient 0.210, stderr 0.012, n = 53). While re-exporting the raw traces for cell21, the CI narrowed by roughly a tenth (coefficient 0.080, stderr 0.028, n = 49). While re-exporting the raw traces for cell23, two cells fell out of the usable range (coefficient 0.308, stderr 0.044, n = 48). Worth noting for the writeup, though not a result on its own.

### Step 20: re-exporting the raw traces

While fitting the one-lag kernel for cell19, the ordering of cells was preserved (coefficient 0.253, stderr 0.037, n = 45). While fitting the one-lag kernel for cell03, the ordering of cells was preserved (coefficient 0.260, stderr 0.013, n = 52). While re-running with a tighter segmentation threshold for cell19, nothing in the figure changed at print size (coefficient 0.115, stderr 0.049, n = 50). While segmenting epochs for cell11, the CI narrowed by roughly a tenth (coefficient 0.260, stderr 0.036, n = 50).

While re-exporting the raw traces for cell04, nothing in the figure changed at print size (coefficient 0.124, stderr 0.042, n = 54). While segmenting epochs for cell24, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.182, stderr 0.045, n = 40). While auditing the holding potential column for cell04, nothing in the figure changed at print size (coefficient 0.231, stderr 0.029, n = 39). While auditing the holding potential column for cell24, the coefficient tracked epoch count more closely than duration (coefficient 0.155, stderr 0.012, n = 49). While segmenting epochs for cell03, two cells fell out of the usable range (coefficient 0.127, stderr 0.025, n = 48). While checking residual autocorrelation for cell01, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.158, stderr 0.013, n = 56).

While bootstrapping the CI for cell01, the ordering of cells was preserved (coefficient 0.211, stderr 0.029, n = 38). While fitting the one-lag kernel for cell23, the ordering of cells was preserved (coefficient 0.196, stderr 0.048, n = 54). While re-running with a tighter segmentation threshold for cell14, nothing in the figure changed at print size (coefficient 0.084, stderr 0.017, n = 49). While bootstrapping the CI for cell08, two cells fell out of the usable range (coefficient 0.104, stderr 0.048, n = 43). While fitting the one-lag kernel for cell09, two cells fell out of the usable range (coefficient 0.207, stderr 0.039, n = 52).

### Step 21: checking residual autocorrelation

While fitting the one-lag kernel for cell16, two cells fell out of the usable range (coefficient 0.215, stderr 0.027, n = 47). While bootstrapping the CI for cell06, the ordering of cells was preserved (coefficient 0.108, stderr 0.044, n = 39). While bootstrapping the CI for cell20, two cells fell out of the usable range (coefficient 0.172, stderr 0.018, n = 53).

While fitting the one-lag kernel for cell04, the CI narrowed by roughly a tenth (coefficient 0.177, stderr 0.016, n = 57). While auditing the holding potential column for cell19, the ordering of cells was preserved (coefficient 0.286, stderr 0.040, n = 54). While re-exporting the raw traces for cell02, two cells fell out of the usable range (coefficient 0.272, stderr 0.014, n = 42). While re-running with a tighter segmentation threshold for cell05, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.283, stderr 0.030, n = 41). While auditing the holding potential column for cell17, the CI narrowed by roughly a tenth (coefficient 0.220, stderr 0.043, n = 58). While fitting the one-lag kernel for cell18, the coefficient tracked epoch count more closely than duration (coefficient 0.255, stderr 0.022, n = 41).

While checking residual autocorrelation for cell24, the CI narrowed by roughly a tenth (coefficient 0.171, stderr 0.034, n = 58). While bootstrapping the CI for cell13, two cells fell out of the usable range (coefficient 0.122, stderr 0.026, n = 46). While bootstrapping the CI for cell07, the ordering of cells was preserved (coefficient 0.239, stderr 0.042, n = 42). While auditing the holding potential column for cell11, two cells fell out of the usable range (coefficient 0.110, stderr 0.020, n = 51). Noted and moved on; it does not change the decision.

```python
coefs = fit_per_cell(rows, threshold=0.35)
lo, hi = ci(coefs, seed=10)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 22: bootstrapping the CI

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell22    0.118  0.012   0.095  0.142  39        1000
cell10    0.225  0.049   0.128  0.322  44        4000
cell14    0.307  0.014   0.279  0.335  53        500
cell23    0.305  0.044   0.219  0.391  50        2000
cell10    0.170  0.043   0.087  0.254  52        500
cell02    0.246  0.040   0.169  0.324  48        1000
cell09    0.235  0.035   0.167  0.304  58        4000
cell13    0.165  0.032   0.102  0.227  51        2000
cell12    0.163  0.020   0.124  0.201  52        500
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell18    0.194  0.039   0.116  0.271  38        500
cell18    0.216  0.031   0.155  0.276  50        1000
cell11    0.303  0.026   0.253  0.354  57        2000
cell12    0.222  0.025   0.173  0.272  53        1000
cell24    0.208  0.046   0.118  0.298  56        1000
cell22    0.234  0.038   0.159  0.309  46        1000
cell04    0.288  0.028   0.233  0.343  47        1000
```

While re-exporting the raw traces for cell08, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.274, stderr 0.029, n = 51). While comparing per-cell orderings for cell13, the ordering of cells was preserved (coefficient 0.084, stderr 0.041, n = 42). While re-exporting the raw traces for cell20, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.098, stderr 0.039, n = 57). Noted and moved on; it does not change the decision.

### Step 23: comparing per-cell orderings

```python
coefs = fit_per_cell(rows, threshold=0.75)
lo, hi = ci(coefs, seed=68)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While re-running with a tighter segmentation threshold for cell15, the CI narrowed by roughly a tenth (coefficient 0.180, stderr 0.033, n = 58). While auditing the holding potential column for cell14, the estimate moved less than one standard error (coefficient 0.094, stderr 0.044, n = 42). While checking residual autocorrelation for cell10, the CI narrowed by roughly a tenth (coefficient 0.212, stderr 0.023, n = 56). While checking residual autocorrelation for cell15, two cells fell out of the usable range (coefficient 0.241, stderr 0.015, n = 39). Worth noting for the writeup, though not a result on its own.

While comparing per-cell orderings for cell13, nothing in the figure changed at print size (coefficient 0.144, stderr 0.037, n = 40). While segmenting epochs for cell05, the estimate moved less than one standard error (coefficient 0.118, stderr 0.012, n = 51). While fitting the one-lag kernel for cell05, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.095, stderr 0.043, n = 51).

### Step 24: checking residual autocorrelation

While bootstrapping the CI for cell06, the ordering of cells was preserved (coefficient 0.291, stderr 0.030, n = 41). While fitting the one-lag kernel for cell03, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.157, stderr 0.025, n = 40). While checking residual autocorrelation for cell18, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.208, stderr 0.038, n = 41).

While re-exporting the raw traces for cell06, nothing in the figure changed at print size (coefficient 0.138, stderr 0.037, n = 55). While fitting the one-lag kernel for cell17, the CI narrowed by roughly a tenth (coefficient 0.147, stderr 0.043, n = 42). While bootstrapping the CI for cell22, the coefficient tracked epoch count more closely than duration (coefficient 0.240, stderr 0.014, n = 43). While bootstrapping the CI for cell02, nothing in the figure changed at print size (coefficient 0.227, stderr 0.049, n = 53). Parking this until the re-segmentation lands.

### Step 25: comparing per-cell orderings

While re-running with a tighter segmentation threshold for cell12, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.276, stderr 0.023, n = 45). While checking residual autocorrelation for cell09, nothing in the figure changed at print size (coefficient 0.183, stderr 0.034, n = 54). While bootstrapping the CI for cell12, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.090, stderr 0.026, n = 44). While fitting the one-lag kernel for cell23, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.102, stderr 0.045, n = 45). While segmenting epochs for cell23, the CI narrowed by roughly a tenth (coefficient 0.215, stderr 0.050, n = 57). While re-running with a tighter segmentation threshold for cell16, the CI narrowed by roughly a tenth (coefficient 0.306, stderr 0.016, n = 56).

While auditing the holding potential column for cell18, the CI narrowed by roughly a tenth (coefficient 0.161, stderr 0.036, n = 43). While auditing the holding potential column for cell06, the estimate moved less than one standard error (coefficient 0.221, stderr 0.042, n = 48). While re-exporting the raw traces for cell08, two cells fell out of the usable range (coefficient 0.265, stderr 0.021, n = 39). While segmenting epochs for cell03, the coefficient tracked epoch count more closely than duration (coefficient 0.307, stderr 0.011, n = 40). While comparing per-cell orderings for cell05, the estimate moved less than one standard error (coefficient 0.251, stderr 0.037, n = 43). While bootstrapping the CI for cell07, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.155, stderr 0.015, n = 50). Flagging it so it does not get rediscovered next week.

### Step 26: bootstrapping the CI

While fitting the one-lag kernel for cell04, nothing in the figure changed at print size (coefficient 0.232, stderr 0.036, n = 56). While checking residual autocorrelation for cell12, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.160, stderr 0.047, n = 53). While fitting the one-lag kernel for cell04, two cells fell out of the usable range (coefficient 0.171, stderr 0.021, n = 51). While re-exporting the raw traces for cell12, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.252, stderr 0.049, n = 58). Flagging it so it does not get rediscovered next week.

While bootstrapping the CI for cell23, two cells fell out of the usable range (coefficient 0.228, stderr 0.036, n = 57). While bootstrapping the CI for cell16, the coefficient tracked epoch count more closely than duration (coefficient 0.168, stderr 0.013, n = 51). While segmenting epochs for cell18, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.233, stderr 0.035, n = 45). While re-exporting the raw traces for cell08, the estimate moved less than one standard error (coefficient 0.308, stderr 0.040, n = 58). While segmenting epochs for cell14, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.136, stderr 0.036, n = 42). While re-running with a tighter segmentation threshold for cell21, the ordering of cells was preserved (coefficient 0.302, stderr 0.023, n = 40).

While re-running with a tighter segmentation threshold for cell12, nothing in the figure changed at print size (coefficient 0.243, stderr 0.037, n = 56). While auditing the holding potential column for cell18, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.274, stderr 0.020, n = 56). While auditing the holding potential column for cell02, two cells fell out of the usable range (coefficient 0.117, stderr 0.020, n = 56). While auditing the holding potential column for cell02, the ordering of cells was preserved (coefficient 0.220, stderr 0.032, n = 39).

### Step 27: auditing the holding potential column

```python
coefs = fit_per_cell(rows, threshold=0.48)
lo, hi = ci(coefs, seed=23)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While auditing the holding potential column for cell03, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.153, stderr 0.037, n = 48). While re-exporting the raw traces for cell08, two cells fell out of the usable range (coefficient 0.175, stderr 0.045, n = 55). While re-running with a tighter segmentation threshold for cell08, the ordering of cells was preserved (coefficient 0.146, stderr 0.016, n = 49). While auditing the holding potential column for cell07, the ordering of cells was preserved (coefficient 0.128, stderr 0.014, n = 54). While auditing the holding potential column for cell09, two cells fell out of the usable range (coefficient 0.201, stderr 0.023, n = 52). While fitting the one-lag kernel for cell12, the coefficient tracked epoch count more closely than duration (coefficient 0.149, stderr 0.030, n = 51).

While segmenting epochs for cell21, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.190, stderr 0.037, n = 47). While segmenting epochs for cell20, the estimate moved less than one standard error (coefficient 0.276, stderr 0.016, n = 42). While fitting the one-lag kernel for cell10, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.237, stderr 0.020, n = 52). While bootstrapping the CI for cell01, the CI narrowed by roughly a tenth (coefficient 0.253, stderr 0.042, n = 56). While fitting the one-lag kernel for cell19, the estimate moved less than one standard error (coefficient 0.227, stderr 0.021, n = 45). While fitting the one-lag kernel for cell12, two cells fell out of the usable range (coefficient 0.267, stderr 0.033, n = 47). Flagging it so it does not get rediscovered next week.

### Step 28: fitting the one-lag kernel

```python
coefs = fit_per_cell(rows, threshold=0.61)
lo, hi = ci(coefs, seed=74)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While auditing the holding potential column for cell24, two cells fell out of the usable range (coefficient 0.125, stderr 0.048, n = 47). While bootstrapping the CI for cell05, two cells fell out of the usable range (coefficient 0.298, stderr 0.028, n = 49). While re-running with a tighter segmentation threshold for cell11, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.220, stderr 0.048, n = 51). While auditing the holding potential column for cell03, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.097, stderr 0.020, n = 58). While checking residual autocorrelation for cell13, the CI narrowed by roughly a tenth (coefficient 0.130, stderr 0.050, n = 50). While comparing per-cell orderings for cell09, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.215, stderr 0.012, n = 39).

### Step 29: bootstrapping the CI

```python
coefs = fit_per_cell(rows, threshold=0.42)
lo, hi = ci(coefs, seed=47)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell01    0.253  0.050   0.155  0.350  48        1000
cell18    0.131  0.049   0.035  0.227  49        2000
cell19    0.094  0.044   0.009  0.180  41        500
cell19    0.210  0.048   0.115  0.304  53        500
cell21    0.176  0.050   0.078  0.273  46        1000
cell05    0.201  0.026   0.150  0.252  57        500
cell04    0.100  0.032   0.037  0.162  40        1000
cell15    0.254  0.030   0.195  0.313  48        4000
cell07    0.137  0.013   0.112  0.161  40        1000
cell15    0.087  0.012   0.063  0.111  58        1000
cell06    0.308  0.012   0.285  0.331  44        2000
cell17    0.230  0.032   0.167  0.292  48        500
cell19    0.084  0.043   0.000  0.168  38        4000
```

### Step 30: comparing per-cell orderings

While re-running with a tighter segmentation threshold for cell16, the ordering of cells was preserved (coefficient 0.168, stderr 0.039, n = 54). While checking residual autocorrelation for cell19, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.257, stderr 0.049, n = 46). While auditing the holding potential column for cell04, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.250, stderr 0.049, n = 57). While segmenting epochs for cell07, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.235, stderr 0.041, n = 49). While checking residual autocorrelation for cell04, nothing in the figure changed at print size (coefficient 0.294, stderr 0.038, n = 46). While auditing the holding potential column for cell09, the coefficient tracked epoch count more closely than duration (coefficient 0.181, stderr 0.044, n = 40).

While bootstrapping the CI for cell12, the CI narrowed by roughly a tenth (coefficient 0.264, stderr 0.012, n = 53). While comparing per-cell orderings for cell09, two cells fell out of the usable range (coefficient 0.289, stderr 0.011, n = 55). While comparing per-cell orderings for cell15, the ordering of cells was preserved (coefficient 0.299, stderr 0.040, n = 55). While auditing the holding potential column for cell21, the ordering of cells was preserved (coefficient 0.201, stderr 0.017, n = 42).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell16    0.251  0.025   0.202  0.300  57        2000
cell21    0.178  0.046   0.088  0.269  47        2000
cell11    0.288  0.021   0.247  0.329  40        2000
cell17    0.210  0.048   0.117  0.304  50        500
cell06    0.283  0.013   0.257  0.310  42        2000
cell20    0.085  0.043   0.001  0.170  40        1000
cell03    0.299  0.019   0.263  0.336  52        500
```

While re-running with a tighter segmentation threshold for cell14, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.107, stderr 0.031, n = 47). While fitting the one-lag kernel for cell02, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.083, stderr 0.042, n = 40). While bootstrapping the CI for cell20, the coefficient tracked epoch count more closely than duration (coefficient 0.117, stderr 0.034, n = 41). While segmenting epochs for cell02, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.128, stderr 0.024, n = 41). Parking this until the re-segmentation lands.

### Step 31: checking residual autocorrelation

While checking residual autocorrelation for cell21, two cells fell out of the usable range (coefficient 0.102, stderr 0.029, n = 46). While bootstrapping the CI for cell19, the estimate moved less than one standard error (coefficient 0.244, stderr 0.049, n = 44). While re-exporting the raw traces for cell09, the CI narrowed by roughly a tenth (coefficient 0.298, stderr 0.036, n = 50).

While re-running with a tighter segmentation threshold for cell16, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.242, stderr 0.025, n = 58). While auditing the holding potential column for cell04, the estimate moved less than one standard error (coefficient 0.118, stderr 0.050, n = 57). While re-exporting the raw traces for cell07, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.098, stderr 0.045, n = 40). While re-running with a tighter segmentation threshold for cell01, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.125, stderr 0.033, n = 38). This is the part that will need a real statistical argument.

While auditing the holding potential column for cell18, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.121, stderr 0.049, n = 49). While comparing per-cell orderings for cell19, two cells fell out of the usable range (coefficient 0.108, stderr 0.019, n = 39). While bootstrapping the CI for cell23, the estimate moved less than one standard error (coefficient 0.110, stderr 0.050, n = 49).

While fitting the one-lag kernel for cell07, the CI narrowed by roughly a tenth (coefficient 0.165, stderr 0.047, n = 53). While auditing the holding potential column for cell11, nothing in the figure changed at print size (coefficient 0.264, stderr 0.016, n = 39). While bootstrapping the CI for cell03, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.278, stderr 0.046, n = 58). Worth noting for the writeup, though not a result on its own.

### Step 32: segmenting epochs

While checking residual autocorrelation for cell20, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.288, stderr 0.025, n = 38). While re-running with a tighter segmentation threshold for cell06, the estimate moved less than one standard error (coefficient 0.107, stderr 0.020, n = 57). While bootstrapping the CI for cell12, nothing in the figure changed at print size (coefficient 0.103, stderr 0.020, n = 46).

While auditing the holding potential column for cell17, two cells fell out of the usable range (coefficient 0.091, stderr 0.048, n = 38). While auditing the holding potential column for cell19, two cells fell out of the usable range (coefficient 0.139, stderr 0.013, n = 42). While re-exporting the raw traces for cell20, nothing in the figure changed at print size (coefficient 0.099, stderr 0.025, n = 58). While re-running with a tighter segmentation threshold for cell16, two cells fell out of the usable range (coefficient 0.164, stderr 0.045, n = 44). While auditing the holding potential column for cell08, the estimate moved less than one standard error (coefficient 0.189, stderr 0.021, n = 53).

### Step 33: re-running with a tighter segmentation threshold

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell15    0.215  0.014   0.189  0.242  56        4000
cell18    0.246  0.013   0.222  0.271  58        2000
cell21    0.178  0.015   0.148  0.207  47        4000
cell02    0.237  0.024   0.189  0.284  45        500
cell19    0.128  0.014   0.100  0.157  46        4000
cell02    0.140  0.011   0.119  0.161  41        500
cell16    0.308  0.037   0.236  0.380  56        1000
cell01    0.200  0.016   0.169  0.231  38        2000
cell11    0.109  0.040   0.031  0.188  46        2000
cell20    0.228  0.019   0.190  0.266  41        500
cell10    0.299  0.012   0.275  0.322  57        500
cell17    0.225  0.029   0.169  0.281  52        2000
cell03    0.151  0.032   0.087  0.214  55        2000
```

While fitting the one-lag kernel for cell20, the coefficient tracked epoch count more closely than duration (coefficient 0.260, stderr 0.019, n = 38). While auditing the holding potential column for cell05, the estimate moved less than one standard error (coefficient 0.150, stderr 0.035, n = 48). While comparing per-cell orderings for cell01, the coefficient tracked epoch count more closely than duration (coefficient 0.162, stderr 0.031, n = 45). While fitting the one-lag kernel for cell01, the CI narrowed by roughly a tenth (coefficient 0.218, stderr 0.030, n = 51). While bootstrapping the CI for cell21, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.190, stderr 0.028, n = 45).

### Step 34: re-running with a tighter segmentation threshold

```python
coefs = fit_per_cell(rows, threshold=0.69)
lo, hi = ci(coefs, seed=64)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```python
coefs = fit_per_cell(rows, threshold=0.61)
lo, hi = ci(coefs, seed=46)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 35: comparing per-cell orderings

While checking residual autocorrelation for cell03, the coefficient tracked epoch count more closely than duration (coefficient 0.182, stderr 0.024, n = 38). While fitting the one-lag kernel for cell17, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.201, stderr 0.018, n = 49). While segmenting epochs for cell04, the ordering of cells was preserved (coefficient 0.189, stderr 0.020, n = 45). While comparing per-cell orderings for cell24, the estimate moved less than one standard error (coefficient 0.261, stderr 0.020, n = 48). While comparing per-cell orderings for cell23, the estimate moved less than one standard error (coefficient 0.222, stderr 0.037, n = 51). While comparing per-cell orderings for cell18, the coefficient tracked epoch count more closely than duration (coefficient 0.181, stderr 0.047, n = 54).

While segmenting epochs for cell03, nothing in the figure changed at print size (coefficient 0.110, stderr 0.047, n = 48). While bootstrapping the CI for cell07, the estimate moved less than one standard error (coefficient 0.120, stderr 0.026, n = 51). While segmenting epochs for cell21, the CI narrowed by roughly a tenth (coefficient 0.294, stderr 0.028, n = 42). While checking residual autocorrelation for cell22, the estimate moved less than one standard error (coefficient 0.290, stderr 0.045, n = 51). While re-running with a tighter segmentation threshold for cell20, the CI narrowed by roughly a tenth (coefficient 0.276, stderr 0.021, n = 46). While fitting the one-lag kernel for cell12, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.117, stderr 0.041, n = 44). Parking this until the re-segmentation lands.

While re-exporting the raw traces for cell09, the ordering of cells was preserved (coefficient 0.300, stderr 0.039, n = 48). While checking residual autocorrelation for cell04, nothing in the figure changed at print size (coefficient 0.135, stderr 0.020, n = 43). While auditing the holding potential column for cell12, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.250, stderr 0.030, n = 42).

While segmenting epochs for cell17, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.203, stderr 0.019, n = 42). While checking residual autocorrelation for cell05, the CI narrowed by roughly a tenth (coefficient 0.104, stderr 0.023, n = 50). While comparing per-cell orderings for cell24, nothing in the figure changed at print size (coefficient 0.243, stderr 0.049, n = 56). While comparing per-cell orderings for cell11, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.106, stderr 0.047, n = 44). While re-running with a tighter segmentation threshold for cell23, the ordering of cells was preserved (coefficient 0.164, stderr 0.014, n = 44).

### Step 36: re-running with a tighter segmentation threshold

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell03    0.258  0.010   0.238  0.278  46        4000
cell01    0.269  0.042   0.187  0.350  53        4000
cell14    0.206  0.029   0.149  0.263  55        4000
cell15    0.089  0.017   0.055  0.122  42        1000
cell04    0.230  0.045   0.142  0.317  44        500
cell08    0.283  0.028   0.229  0.337  38        1000
cell12    0.116  0.016   0.084  0.148  41        500
cell22    0.098  0.011   0.076  0.121  42        500
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell02    0.205  0.037   0.131  0.278  46        4000
cell09    0.265  0.045   0.177  0.354  42        500
cell12    0.130  0.034   0.064  0.197  46        1000
cell14    0.145  0.020   0.106  0.184  58        2000
cell04    0.194  0.034   0.127  0.261  57        4000
cell22    0.197  0.030   0.138  0.256  47        500
cell06    0.235  0.026   0.185  0.285  52        2000
cell06    0.215  0.013   0.189  0.241  56        500
cell10    0.160  0.033   0.095  0.225  38        1000
cell22    0.141  0.028   0.086  0.196  58        2000
cell21    0.215  0.050   0.118  0.312  55        500
cell23    0.189  0.032   0.127  0.252  47        4000
```

While comparing per-cell orderings for cell06, the estimate moved less than one standard error (coefficient 0.105, stderr 0.010, n = 45). While re-running with a tighter segmentation threshold for cell23, the ordering of cells was preserved (coefficient 0.090, stderr 0.026, n = 53). While re-exporting the raw traces for cell04, the ordering of cells was preserved (coefficient 0.242, stderr 0.024, n = 48). While re-running with a tighter segmentation threshold for cell04, the estimate moved less than one standard error (coefficient 0.172, stderr 0.035, n = 56). While re-running with a tighter segmentation threshold for cell20, the ordering of cells was preserved (coefficient 0.294, stderr 0.014, n = 47). Noted and moved on; it does not change the decision.

```python
coefs = fit_per_cell(rows, threshold=0.44)
lo, hi = ci(coefs, seed=44)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 37: checking residual autocorrelation

While auditing the holding potential column for cell06, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.233, stderr 0.020, n = 52). While re-exporting the raw traces for cell13, the CI narrowed by roughly a tenth (coefficient 0.147, stderr 0.019, n = 40). While bootstrapping the CI for cell23, the estimate moved less than one standard error (coefficient 0.255, stderr 0.023, n = 44). While re-exporting the raw traces for cell17, nothing in the figure changed at print size (coefficient 0.171, stderr 0.025, n = 40). While auditing the holding potential column for cell16, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.122, stderr 0.020, n = 51).

While checking residual autocorrelation for cell05, the coefficient tracked epoch count more closely than duration (coefficient 0.202, stderr 0.024, n = 44). While checking residual autocorrelation for cell24, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.114, stderr 0.011, n = 40). While segmenting epochs for cell03, the ordering of cells was preserved (coefficient 0.298, stderr 0.043, n = 41). While auditing the holding potential column for cell10, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.285, stderr 0.037, n = 56).

### Step 38: re-running with a tighter segmentation threshold

While auditing the holding potential column for cell03, the ordering of cells was preserved (coefficient 0.175, stderr 0.040, n = 53). While segmenting epochs for cell18, the CI narrowed by roughly a tenth (coefficient 0.124, stderr 0.032, n = 57). While checking residual autocorrelation for cell08, nothing in the figure changed at print size (coefficient 0.142, stderr 0.045, n = 44). While checking residual autocorrelation for cell09, two cells fell out of the usable range (coefficient 0.249, stderr 0.038, n = 43). Flagging it so it does not get rediscovered next week.

While re-running with a tighter segmentation threshold for cell12, nothing in the figure changed at print size (coefficient 0.149, stderr 0.034, n = 44). While comparing per-cell orderings for cell12, nothing in the figure changed at print size (coefficient 0.149, stderr 0.037, n = 55). While comparing per-cell orderings for cell03, nothing in the figure changed at print size (coefficient 0.242, stderr 0.039, n = 58). While re-running with a tighter segmentation threshold for cell20, the ordering of cells was preserved (coefficient 0.170, stderr 0.035, n = 58). While re-exporting the raw traces for cell07, the coefficient tracked epoch count more closely than duration (coefficient 0.286, stderr 0.033, n = 45). Noted and moved on; it does not change the decision.

### Step 39: re-exporting the raw traces

```python
coefs = fit_per_cell(rows, threshold=0.43)
lo, hi = ci(coefs, seed=45)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While comparing per-cell orderings for cell08, nothing in the figure changed at print size (coefficient 0.256, stderr 0.012, n = 44). While checking residual autocorrelation for cell04, two cells fell out of the usable range (coefficient 0.119, stderr 0.049, n = 48). While re-running with a tighter segmentation threshold for cell19, the estimate moved less than one standard error (coefficient 0.286, stderr 0.036, n = 43). While re-exporting the raw traces for cell24, the CI narrowed by roughly a tenth (coefficient 0.081, stderr 0.046, n = 56). While auditing the holding potential column for cell21, the estimate moved less than one standard error (coefficient 0.105, stderr 0.035, n = 51). Parking this until the re-segmentation lands.

### Step 40: auditing the holding potential column

While re-running with a tighter segmentation threshold for cell10, the ordering of cells was preserved (coefficient 0.122, stderr 0.015, n = 46). While re-exporting the raw traces for cell08, nothing in the figure changed at print size (coefficient 0.163, stderr 0.033, n = 54). While fitting the one-lag kernel for cell01, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.213, stderr 0.016, n = 41). Worth noting for the writeup, though not a result on its own.

```python
coefs = fit_per_cell(rows, threshold=0.52)
lo, hi = ci(coefs, seed=57)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 41: re-running with a tighter segmentation threshold

While auditing the holding potential column for cell08, the ordering of cells was preserved (coefficient 0.258, stderr 0.042, n = 50). While segmenting epochs for cell03, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.271, stderr 0.039, n = 51). While re-running with a tighter segmentation threshold for cell12, two cells fell out of the usable range (coefficient 0.199, stderr 0.025, n = 45). While comparing per-cell orderings for cell11, the coefficient tracked epoch count more closely than duration (coefficient 0.088, stderr 0.032, n = 51).

While comparing per-cell orderings for cell11, the ordering of cells was preserved (coefficient 0.131, stderr 0.019, n = 40). While checking residual autocorrelation for cell13, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.096, stderr 0.038, n = 51). While re-exporting the raw traces for cell17, two cells fell out of the usable range (coefficient 0.092, stderr 0.033, n = 48). While checking residual autocorrelation for cell17, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.102, stderr 0.046, n = 44). While checking residual autocorrelation for cell10, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.282, stderr 0.029, n = 47). While bootstrapping the CI for cell13, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.086, stderr 0.017, n = 42). Flagging it so it does not get rediscovered next week.

### Step 42: fitting the one-lag kernel

```python
coefs = fit_per_cell(rows, threshold=0.59)
lo, hi = ci(coefs, seed=29)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While auditing the holding potential column for cell14, two cells fell out of the usable range (coefficient 0.174, stderr 0.031, n = 38). While checking residual autocorrelation for cell15, the estimate moved less than one standard error (coefficient 0.088, stderr 0.017, n = 38). While checking residual autocorrelation for cell18, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.094, stderr 0.015, n = 41).

While checking residual autocorrelation for cell08, two cells fell out of the usable range (coefficient 0.213, stderr 0.018, n = 56). While re-running with a tighter segmentation threshold for cell18, the coefficient tracked epoch count more closely than duration (coefficient 0.254, stderr 0.016, n = 47). While re-running with a tighter segmentation threshold for cell24, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.191, stderr 0.010, n = 54). While re-exporting the raw traces for cell10, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.193, stderr 0.025, n = 51). While re-running with a tighter segmentation threshold for cell22, two cells fell out of the usable range (coefficient 0.157, stderr 0.030, n = 50). While re-exporting the raw traces for cell02, nothing in the figure changed at print size (coefficient 0.134, stderr 0.044, n = 46). Parking this until the re-segmentation lands.

While re-running with a tighter segmentation threshold for cell11, the ordering of cells was preserved (coefficient 0.155, stderr 0.039, n = 41). While auditing the holding potential column for cell09, the estimate moved less than one standard error (coefficient 0.244, stderr 0.049, n = 47). While re-running with a tighter segmentation threshold for cell07, the CI narrowed by roughly a tenth (coefficient 0.212, stderr 0.045, n = 39). While fitting the one-lag kernel for cell02, the ordering of cells was preserved (coefficient 0.123, stderr 0.048, n = 38).

