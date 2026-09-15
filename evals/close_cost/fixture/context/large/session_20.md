# Prior session 20 of 20

Transcript of an earlier working session on the history-kernel analysis.

### Step 1: bootstrapping the CI

While bootstrapping the CI for cell21, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.280, stderr 0.027, n = 44). While re-running with a tighter segmentation threshold for cell15, the CI narrowed by roughly a tenth (coefficient 0.173, stderr 0.042, n = 38). While auditing the holding potential column for cell19, the estimate moved less than one standard error (coefficient 0.219, stderr 0.030, n = 42). While re-exporting the raw traces for cell12, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.257, stderr 0.036, n = 45). While checking residual autocorrelation for cell07, two cells fell out of the usable range (coefficient 0.228, stderr 0.042, n = 41). While auditing the holding potential column for cell18, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.096, stderr 0.022, n = 53).

While checking residual autocorrelation for cell12, two cells fell out of the usable range (coefficient 0.168, stderr 0.016, n = 54). While re-exporting the raw traces for cell15, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.088, stderr 0.038, n = 46). While checking residual autocorrelation for cell03, the coefficient tracked epoch count more closely than duration (coefficient 0.235, stderr 0.024, n = 39). While comparing per-cell orderings for cell02, the CI narrowed by roughly a tenth (coefficient 0.281, stderr 0.022, n = 42). While comparing per-cell orderings for cell05, the ordering of cells was preserved (coefficient 0.125, stderr 0.047, n = 49). While checking residual autocorrelation for cell17, two cells fell out of the usable range (coefficient 0.122, stderr 0.033, n = 50).

While checking residual autocorrelation for cell23, the estimate moved less than one standard error (coefficient 0.165, stderr 0.031, n = 49). While re-exporting the raw traces for cell06, the CI narrowed by roughly a tenth (coefficient 0.152, stderr 0.023, n = 38). While bootstrapping the CI for cell17, the estimate moved less than one standard error (coefficient 0.163, stderr 0.016, n = 56). While segmenting epochs for cell12, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.206, stderr 0.015, n = 55). While re-running with a tighter segmentation threshold for cell13, the CI narrowed by roughly a tenth (coefficient 0.118, stderr 0.044, n = 42). While re-running with a tighter segmentation threshold for cell24, nothing in the figure changed at print size (coefficient 0.308, stderr 0.050, n = 54).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell12    0.120  0.036   0.049  0.191  56        500
cell05    0.263  0.013   0.237  0.289  43        500
cell16    0.192  0.045   0.103  0.280  41        4000
cell22    0.165  0.016   0.135  0.196  42        500
cell14    0.263  0.044   0.177  0.349  40        1000
cell06    0.141  0.026   0.090  0.193  58        500
cell08    0.081  0.046   -0.008  0.170  42        4000
cell21    0.252  0.047   0.160  0.344  52        4000
cell11    0.223  0.014   0.196  0.251  40        500
```

### Step 2: checking residual autocorrelation

```python
coefs = fit_per_cell(rows, threshold=0.32)
lo, hi = ci(coefs, seed=52)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While bootstrapping the CI for cell05, the ordering of cells was preserved (coefficient 0.182, stderr 0.022, n = 51). While bootstrapping the CI for cell03, the coefficient tracked epoch count more closely than duration (coefficient 0.167, stderr 0.022, n = 40). While bootstrapping the CI for cell07, nothing in the figure changed at print size (coefficient 0.234, stderr 0.029, n = 47). While comparing per-cell orderings for cell04, the estimate moved less than one standard error (coefficient 0.133, stderr 0.010, n = 49). Parking this until the re-segmentation lands.

```python
coefs = fit_per_cell(rows, threshold=0.68)
lo, hi = ci(coefs, seed=3)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 3: re-running with a tighter segmentation threshold

```python
coefs = fit_per_cell(rows, threshold=0.36)
lo, hi = ci(coefs, seed=48)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While comparing per-cell orderings for cell19, the CI narrowed by roughly a tenth (coefficient 0.241, stderr 0.016, n = 51). While bootstrapping the CI for cell08, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.086, stderr 0.013, n = 44). While checking residual autocorrelation for cell10, the CI narrowed by roughly a tenth (coefficient 0.278, stderr 0.019, n = 45).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell21    0.123  0.023   0.078  0.167  48        4000
cell01    0.296  0.022   0.253  0.339  39        4000
cell07    0.292  0.043   0.208  0.377  48        2000
cell17    0.096  0.033   0.031  0.161  44        4000
cell03    0.180  0.045   0.091  0.269  40        1000
cell20    0.273  0.011   0.251  0.295  57        4000
cell16    0.194  0.032   0.132  0.257  44        1000
cell19    0.162  0.011   0.139  0.184  51        4000
cell12    0.303  0.016   0.270  0.335  38        4000
cell18    0.300  0.016   0.270  0.331  52        500
cell22    0.189  0.041   0.109  0.269  47        500
cell21    0.086  0.047   -0.006  0.178  48        4000
```

### Step 4: re-exporting the raw traces

While segmenting epochs for cell14, two cells fell out of the usable range (coefficient 0.164, stderr 0.018, n = 45). While re-exporting the raw traces for cell08, the coefficient tracked epoch count more closely than duration (coefficient 0.107, stderr 0.042, n = 52). While re-exporting the raw traces for cell20, the coefficient tracked epoch count more closely than duration (coefficient 0.130, stderr 0.035, n = 44). While bootstrapping the CI for cell07, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.218, stderr 0.034, n = 58). While comparing per-cell orderings for cell10, the CI narrowed by roughly a tenth (coefficient 0.278, stderr 0.042, n = 49). While re-running with a tighter segmentation threshold for cell01, the coefficient tracked epoch count more closely than duration (coefficient 0.276, stderr 0.041, n = 58).

While re-exporting the raw traces for cell01, the coefficient tracked epoch count more closely than duration (coefficient 0.209, stderr 0.024, n = 45). While auditing the holding potential column for cell23, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.200, stderr 0.047, n = 49). While fitting the one-lag kernel for cell20, the CI narrowed by roughly a tenth (coefficient 0.259, stderr 0.044, n = 58). While fitting the one-lag kernel for cell24, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.088, stderr 0.033, n = 54). Worth noting for the writeup, though not a result on its own.

While auditing the holding potential column for cell08, the ordering of cells was preserved (coefficient 0.138, stderr 0.035, n = 47). While segmenting epochs for cell11, the estimate moved less than one standard error (coefficient 0.210, stderr 0.020, n = 39). While comparing per-cell orderings for cell02, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.193, stderr 0.038, n = 50). While comparing per-cell orderings for cell14, two cells fell out of the usable range (coefficient 0.156, stderr 0.046, n = 55). Noted and moved on; it does not change the decision.

### Step 5: re-exporting the raw traces

While fitting the one-lag kernel for cell08, the estimate moved less than one standard error (coefficient 0.202, stderr 0.022, n = 49). While auditing the holding potential column for cell10, the coefficient tracked epoch count more closely than duration (coefficient 0.301, stderr 0.046, n = 48). While re-exporting the raw traces for cell04, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.119, stderr 0.036, n = 52). While comparing per-cell orderings for cell17, two cells fell out of the usable range (coefficient 0.138, stderr 0.034, n = 50). While fitting the one-lag kernel for cell05, two cells fell out of the usable range (coefficient 0.187, stderr 0.049, n = 46). While segmenting epochs for cell10, the estimate moved less than one standard error (coefficient 0.142, stderr 0.042, n = 57).

While bootstrapping the CI for cell04, nothing in the figure changed at print size (coefficient 0.217, stderr 0.036, n = 38). While re-running with a tighter segmentation threshold for cell13, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.252, stderr 0.020, n = 47). While auditing the holding potential column for cell22, the ordering of cells was preserved (coefficient 0.091, stderr 0.022, n = 43). While re-exporting the raw traces for cell24, the estimate moved less than one standard error (coefficient 0.128, stderr 0.043, n = 50). Parking this until the re-segmentation lands.

```python
coefs = fit_per_cell(rows, threshold=0.55)
lo, hi = ci(coefs, seed=38)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While re-running with a tighter segmentation threshold for cell18, the ordering of cells was preserved (coefficient 0.274, stderr 0.046, n = 50). While auditing the holding potential column for cell05, nothing in the figure changed at print size (coefficient 0.114, stderr 0.044, n = 49). While re-exporting the raw traces for cell18, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.135, stderr 0.032, n = 49).

### Step 6: bootstrapping the CI

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell20    0.186  0.023   0.141  0.232  49        1000
cell06    0.106  0.013   0.082  0.131  38        2000
cell03    0.282  0.017   0.248  0.316  50        4000
cell04    0.178  0.040   0.100  0.256  50        4000
cell01    0.160  0.012   0.138  0.183  47        4000
cell06    0.157  0.015   0.127  0.187  53        1000
cell03    0.178  0.018   0.143  0.214  40        1000
cell16    0.103  0.034   0.036  0.171  51        2000
cell17    0.232  0.013   0.207  0.257  51        1000
cell23    0.194  0.041   0.114  0.274  53        2000
cell14    0.302  0.014   0.275  0.329  52        1000
cell23    0.118  0.022   0.075  0.162  54        1000
cell10    0.085  0.016   0.053  0.117  47        4000
cell01    0.206  0.041   0.126  0.286  53        2000
```

While re-running with a tighter segmentation threshold for cell20, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.091, stderr 0.022, n = 50). While segmenting epochs for cell08, the coefficient tracked epoch count more closely than duration (coefficient 0.225, stderr 0.038, n = 44). While fitting the one-lag kernel for cell17, the estimate moved less than one standard error (coefficient 0.198, stderr 0.047, n = 39).

```python
coefs = fit_per_cell(rows, threshold=0.74)
lo, hi = ci(coefs, seed=34)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```python
coefs = fit_per_cell(rows, threshold=0.48)
lo, hi = ci(coefs, seed=28)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 7: auditing the holding potential column

While comparing per-cell orderings for cell12, the ordering of cells was preserved (coefficient 0.309, stderr 0.017, n = 51). While segmenting epochs for cell10, the estimate moved less than one standard error (coefficient 0.117, stderr 0.036, n = 46). While comparing per-cell orderings for cell11, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.145, stderr 0.027, n = 46). While re-exporting the raw traces for cell05, two cells fell out of the usable range (coefficient 0.110, stderr 0.040, n = 52). While segmenting epochs for cell23, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.196, stderr 0.039, n = 45). While checking residual autocorrelation for cell05, the estimate moved less than one standard error (coefficient 0.132, stderr 0.028, n = 48). Worth noting for the writeup, though not a result on its own.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell08    0.106  0.014   0.079  0.133  39        1000
cell07    0.310  0.018   0.274  0.345  46        500
cell03    0.199  0.015   0.169  0.229  45        4000
cell17    0.162  0.010   0.142  0.182  38        2000
cell22    0.199  0.045   0.111  0.288  44        4000
cell14    0.275  0.027   0.223  0.327  46        2000
cell08    0.141  0.024   0.094  0.187  42        2000
cell08    0.302  0.039   0.226  0.378  47        4000
cell19    0.261  0.048   0.168  0.355  51        4000
cell02    0.249  0.015   0.219  0.279  49        2000
cell17    0.119  0.019   0.082  0.156  58        4000
cell08    0.264  0.042   0.182  0.346  44        2000
```

While fitting the one-lag kernel for cell08, the coefficient tracked epoch count more closely than duration (coefficient 0.197, stderr 0.018, n = 47). While bootstrapping the CI for cell16, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.237, stderr 0.047, n = 51). While fitting the one-lag kernel for cell04, nothing in the figure changed at print size (coefficient 0.119, stderr 0.048, n = 38). While comparing per-cell orderings for cell03, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.302, stderr 0.037, n = 49). This is the part that will need a real statistical argument.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell17    0.206  0.028   0.151  0.261  48        1000
cell16    0.233  0.013   0.206  0.259  47        1000
cell08    0.151  0.036   0.081  0.222  44        500
cell06    0.146  0.029   0.088  0.204  46        1000
cell24    0.172  0.012   0.148  0.196  50        1000
cell12    0.147  0.023   0.101  0.192  55        500
cell17    0.185  0.040   0.108  0.263  48        500
cell19    0.133  0.038   0.058  0.208  51        500
cell05    0.083  0.010   0.063  0.103  45        2000
cell22    0.162  0.031   0.101  0.222  58        1000
cell11    0.210  0.033   0.146  0.273  53        2000
cell11    0.113  0.044   0.027  0.199  49        4000
cell01    0.198  0.048   0.103  0.292  45        4000
```

### Step 8: checking residual autocorrelation

```python
coefs = fit_per_cell(rows, threshold=0.35)
lo, hi = ci(coefs, seed=55)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While checking residual autocorrelation for cell24, nothing in the figure changed at print size (coefficient 0.171, stderr 0.011, n = 50). While bootstrapping the CI for cell15, the estimate moved less than one standard error (coefficient 0.223, stderr 0.013, n = 57). While auditing the holding potential column for cell23, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.298, stderr 0.024, n = 55). While bootstrapping the CI for cell01, the CI narrowed by roughly a tenth (coefficient 0.213, stderr 0.029, n = 53). While segmenting epochs for cell12, two cells fell out of the usable range (coefficient 0.286, stderr 0.011, n = 38).

### Step 9: auditing the holding potential column

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell24    0.090  0.020   0.052  0.129  45        2000
cell23    0.160  0.032   0.098  0.222  53        4000
cell07    0.190  0.029   0.134  0.247  42        2000
cell21    0.203  0.013   0.178  0.229  50        1000
cell19    0.208  0.045   0.119  0.297  49        2000
cell09    0.113  0.014   0.085  0.140  42        500
cell11    0.308  0.012   0.285  0.331  54        4000
cell09    0.117  0.036   0.047  0.187  57        4000
cell11    0.162  0.012   0.139  0.185  39        1000
cell23    0.251  0.017   0.217  0.285  42        1000
cell02    0.142  0.013   0.117  0.166  53        1000
cell18    0.267  0.034   0.200  0.334  41        4000
```

While comparing per-cell orderings for cell03, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.136, stderr 0.039, n = 45). While checking residual autocorrelation for cell12, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.123, stderr 0.035, n = 39). While checking residual autocorrelation for cell08, the ordering of cells was preserved (coefficient 0.267, stderr 0.014, n = 49). Worth noting for the writeup, though not a result on its own.

### Step 10: re-exporting the raw traces

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell18    0.086  0.022   0.044  0.129  54        2000
cell03    0.197  0.020   0.157  0.236  48        1000
cell16    0.113  0.033   0.048  0.178  45        4000
cell19    0.109  0.022   0.067  0.152  51        2000
cell07    0.259  0.031   0.198  0.320  42        500
cell16    0.182  0.044   0.096  0.268  53        500
cell20    0.296  0.026   0.244  0.348  42        4000
cell18    0.188  0.033   0.124  0.252  38        1000
cell07    0.105  0.030   0.046  0.164  44        500
cell21    0.278  0.033   0.213  0.343  48        4000
cell22    0.184  0.028   0.130  0.239  38        1000
cell24    0.195  0.034   0.129  0.261  39        1000
```

While re-exporting the raw traces for cell11, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.245, stderr 0.046, n = 39). While re-exporting the raw traces for cell13, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.219, stderr 0.025, n = 50). While re-exporting the raw traces for cell12, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.298, stderr 0.015, n = 42). While checking residual autocorrelation for cell07, two cells fell out of the usable range (coefficient 0.202, stderr 0.026, n = 44).

```python
coefs = fit_per_cell(rows, threshold=0.60)
lo, hi = ci(coefs, seed=31)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 11: segmenting epochs

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell24    0.257  0.023   0.212  0.301  46        1000
cell10    0.285  0.041   0.205  0.366  57        4000
cell04    0.248  0.017   0.215  0.281  48        500
cell07    0.272  0.047   0.179  0.364  45        2000
cell13    0.236  0.050   0.139  0.334  51        500
cell22    0.237  0.025   0.188  0.285  51        500
cell22    0.173  0.022   0.131  0.215  53        1000
cell14    0.227  0.049   0.131  0.324  50        500
```

While auditing the holding potential column for cell18, nothing in the figure changed at print size (coefficient 0.127, stderr 0.021, n = 57). While segmenting epochs for cell09, the estimate moved less than one standard error (coefficient 0.186, stderr 0.019, n = 40). While re-exporting the raw traces for cell02, the ordering of cells was preserved (coefficient 0.257, stderr 0.026, n = 45). While comparing per-cell orderings for cell21, the ordering of cells was preserved (coefficient 0.182, stderr 0.040, n = 38). While auditing the holding potential column for cell06, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.179, stderr 0.043, n = 52). While comparing per-cell orderings for cell02, the coefficient tracked epoch count more closely than duration (coefficient 0.252, stderr 0.018, n = 51). This is the part that will need a real statistical argument.

While segmenting epochs for cell17, the CI narrowed by roughly a tenth (coefficient 0.146, stderr 0.037, n = 56). While comparing per-cell orderings for cell04, the CI narrowed by roughly a tenth (coefficient 0.204, stderr 0.037, n = 49). While comparing per-cell orderings for cell17, nothing in the figure changed at print size (coefficient 0.143, stderr 0.021, n = 46). While fitting the one-lag kernel for cell07, the coefficient tracked epoch count more closely than duration (coefficient 0.159, stderr 0.016, n = 44). While re-exporting the raw traces for cell02, the ordering of cells was preserved (coefficient 0.179, stderr 0.018, n = 41). Flagging it so it does not get rediscovered next week.

While bootstrapping the CI for cell17, the CI narrowed by roughly a tenth (coefficient 0.107, stderr 0.026, n = 42). While fitting the one-lag kernel for cell21, the ordering of cells was preserved (coefficient 0.244, stderr 0.036, n = 39). While segmenting epochs for cell17, the ordering of cells was preserved (coefficient 0.279, stderr 0.032, n = 56). While bootstrapping the CI for cell09, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.303, stderr 0.034, n = 48). While fitting the one-lag kernel for cell11, the estimate moved less than one standard error (coefficient 0.198, stderr 0.010, n = 55).

### Step 12: segmenting epochs

```python
coefs = fit_per_cell(rows, threshold=0.61)
lo, hi = ci(coefs, seed=27)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While segmenting epochs for cell12, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.102, stderr 0.034, n = 47). While re-exporting the raw traces for cell14, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.134, stderr 0.046, n = 49). While auditing the holding potential column for cell03, the coefficient tracked epoch count more closely than duration (coefficient 0.134, stderr 0.034, n = 48).

### Step 13: segmenting epochs

While bootstrapping the CI for cell14, the ordering of cells was preserved (coefficient 0.221, stderr 0.047, n = 54). While fitting the one-lag kernel for cell24, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.216, stderr 0.017, n = 51). While fitting the one-lag kernel for cell06, the ordering of cells was preserved (coefficient 0.143, stderr 0.020, n = 54). While auditing the holding potential column for cell22, nothing in the figure changed at print size (coefficient 0.128, stderr 0.024, n = 55). While bootstrapping the CI for cell08, the estimate moved less than one standard error (coefficient 0.268, stderr 0.050, n = 40). While re-running with a tighter segmentation threshold for cell15, the CI narrowed by roughly a tenth (coefficient 0.287, stderr 0.019, n = 40). Flagging it so it does not get rediscovered next week.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell01    0.171  0.020   0.132  0.210  50        1000
cell23    0.227  0.043   0.143  0.311  43        4000
cell22    0.223  0.027   0.171  0.276  39        500
cell01    0.111  0.020   0.072  0.149  42        1000
cell03    0.267  0.012   0.243  0.290  41        2000
cell04    0.226  0.037   0.152  0.299  41        500
cell13    0.189  0.033   0.125  0.253  49        500
cell10    0.300  0.013   0.276  0.325  40        2000
cell17    0.168  0.032   0.107  0.230  38        1000
```

While fitting the one-lag kernel for cell09, two cells fell out of the usable range (coefficient 0.215, stderr 0.037, n = 51). While segmenting epochs for cell14, nothing in the figure changed at print size (coefficient 0.105, stderr 0.048, n = 39). While checking residual autocorrelation for cell09, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.244, stderr 0.013, n = 46).

While bootstrapping the CI for cell22, the coefficient tracked epoch count more closely than duration (coefficient 0.097, stderr 0.019, n = 51). While checking residual autocorrelation for cell24, the ordering of cells was preserved (coefficient 0.098, stderr 0.011, n = 38). While segmenting epochs for cell14, two cells fell out of the usable range (coefficient 0.103, stderr 0.048, n = 48). While re-exporting the raw traces for cell02, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.273, stderr 0.049, n = 49). While checking residual autocorrelation for cell22, nothing in the figure changed at print size (coefficient 0.249, stderr 0.032, n = 43). Worth noting for the writeup, though not a result on its own.

### Step 14: re-exporting the raw traces

While segmenting epochs for cell11, the estimate moved less than one standard error (coefficient 0.129, stderr 0.032, n = 57). While comparing per-cell orderings for cell13, the ordering of cells was preserved (coefficient 0.210, stderr 0.040, n = 57). While re-running with a tighter segmentation threshold for cell15, the estimate moved less than one standard error (coefficient 0.243, stderr 0.019, n = 44). While fitting the one-lag kernel for cell19, the ordering of cells was preserved (coefficient 0.252, stderr 0.031, n = 42). While segmenting epochs for cell09, nothing in the figure changed at print size (coefficient 0.138, stderr 0.014, n = 57). Worth noting for the writeup, though not a result on its own.

While auditing the holding potential column for cell05, two cells fell out of the usable range (coefficient 0.281, stderr 0.024, n = 52). While segmenting epochs for cell13, two cells fell out of the usable range (coefficient 0.084, stderr 0.029, n = 50). While bootstrapping the CI for cell22, two cells fell out of the usable range (coefficient 0.204, stderr 0.028, n = 51). While re-exporting the raw traces for cell11, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.158, stderr 0.043, n = 53). Parking this until the re-segmentation lands.

While auditing the holding potential column for cell14, the estimate moved less than one standard error (coefficient 0.291, stderr 0.047, n = 41). While segmenting epochs for cell18, the ordering of cells was preserved (coefficient 0.183, stderr 0.043, n = 50). While comparing per-cell orderings for cell19, the ordering of cells was preserved (coefficient 0.100, stderr 0.044, n = 42). While re-exporting the raw traces for cell17, two cells fell out of the usable range (coefficient 0.211, stderr 0.039, n = 41). While segmenting epochs for cell11, two cells fell out of the usable range (coefficient 0.244, stderr 0.024, n = 41).

### Step 15: checking residual autocorrelation

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell24    0.126  0.023   0.081  0.170  53        2000
cell09    0.247  0.046   0.158  0.337  46        2000
cell02    0.290  0.045   0.201  0.378  44        2000
cell16    0.093  0.039   0.017  0.169  43        2000
cell05    0.285  0.041   0.204  0.365  48        1000
cell23    0.127  0.017   0.094  0.161  46        500
cell05    0.092  0.029   0.035  0.149  46        4000
cell01    0.082  0.046   -0.008  0.173  52        2000
cell22    0.173  0.044   0.088  0.258  48        4000
```

While checking residual autocorrelation for cell14, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.173, stderr 0.022, n = 58). While checking residual autocorrelation for cell23, the coefficient tracked epoch count more closely than duration (coefficient 0.210, stderr 0.019, n = 41). While bootstrapping the CI for cell06, the ordering of cells was preserved (coefficient 0.231, stderr 0.022, n = 54). While auditing the holding potential column for cell20, two cells fell out of the usable range (coefficient 0.131, stderr 0.047, n = 48). While bootstrapping the CI for cell17, the CI narrowed by roughly a tenth (coefficient 0.259, stderr 0.013, n = 46). While checking residual autocorrelation for cell07, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.100, stderr 0.047, n = 54). Flagging it so it does not get rediscovered next week.

While comparing per-cell orderings for cell12, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.178, stderr 0.036, n = 56). While re-running with a tighter segmentation threshold for cell11, the ordering of cells was preserved (coefficient 0.133, stderr 0.042, n = 45). While bootstrapping the CI for cell07, nothing in the figure changed at print size (coefficient 0.147, stderr 0.039, n = 40). While re-exporting the raw traces for cell02, the ordering of cells was preserved (coefficient 0.157, stderr 0.020, n = 45). While segmenting epochs for cell08, nothing in the figure changed at print size (coefficient 0.253, stderr 0.020, n = 49).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell24    0.081  0.041   0.002  0.161  57        500
cell17    0.142  0.026   0.092  0.193  55        2000
cell17    0.264  0.029   0.206  0.321  56        500
cell23    0.125  0.011   0.103  0.147  56        1000
cell16    0.125  0.019   0.088  0.162  52        4000
cell24    0.251  0.043   0.166  0.335  51        2000
cell21    0.089  0.049   -0.007  0.185  45        4000
```

### Step 16: comparing per-cell orderings

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell01    0.265  0.014   0.238  0.293  44        1000
cell05    0.162  0.028   0.108  0.216  52        1000
cell12    0.172  0.041   0.092  0.252  38        4000
cell23    0.113  0.033   0.048  0.178  47        500
cell16    0.119  0.038   0.044  0.193  55        2000
cell12    0.216  0.012   0.192  0.240  38        500
cell05    0.128  0.031   0.068  0.188  44        2000
cell01    0.121  0.048   0.028  0.214  54        1000
cell14    0.292  0.030   0.234  0.350  49        4000
cell18    0.266  0.018   0.230  0.301  51        1000
cell09    0.251  0.014   0.223  0.279  41        1000
cell19    0.093  0.028   0.037  0.148  39        1000
cell20    0.297  0.013   0.271  0.324  39        1000
cell20    0.144  0.034   0.078  0.210  54        500
```

While checking residual autocorrelation for cell07, the CI narrowed by roughly a tenth (coefficient 0.226, stderr 0.014, n = 51). While auditing the holding potential column for cell23, two cells fell out of the usable range (coefficient 0.138, stderr 0.025, n = 46). While re-running with a tighter segmentation threshold for cell13, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.208, stderr 0.022, n = 53). While checking residual autocorrelation for cell11, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.207, stderr 0.044, n = 42). While comparing per-cell orderings for cell18, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.111, stderr 0.048, n = 53).

### Step 17: re-exporting the raw traces

```python
coefs = fit_per_cell(rows, threshold=0.74)
lo, hi = ci(coefs, seed=12)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell01    0.203  0.019   0.166  0.241  52        1000
cell02    0.090  0.026   0.038  0.142  58        500
cell07    0.161  0.037   0.090  0.233  41        500
cell15    0.095  0.032   0.032  0.158  41        500
cell07    0.123  0.047   0.032  0.214  54        1000
cell21    0.301  0.034   0.234  0.368  58        4000
cell09    0.279  0.019   0.241  0.317  54        1000
cell02    0.161  0.047   0.069  0.253  57        1000
cell18    0.183  0.033   0.118  0.248  52        2000
```

While bootstrapping the CI for cell17, nothing in the figure changed at print size (coefficient 0.114, stderr 0.026, n = 53). While segmenting epochs for cell17, the ordering of cells was preserved (coefficient 0.296, stderr 0.020, n = 47). While auditing the holding potential column for cell20, two cells fell out of the usable range (coefficient 0.204, stderr 0.024, n = 57). While auditing the holding potential column for cell20, the estimate moved less than one standard error (coefficient 0.213, stderr 0.019, n = 48). While re-exporting the raw traces for cell04, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.116, stderr 0.044, n = 55).

While checking residual autocorrelation for cell03, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.087, stderr 0.044, n = 41). While re-exporting the raw traces for cell06, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.197, stderr 0.011, n = 58). While auditing the holding potential column for cell10, nothing in the figure changed at print size (coefficient 0.215, stderr 0.026, n = 52).

### Step 18: bootstrapping the CI

While segmenting epochs for cell04, two cells fell out of the usable range (coefficient 0.093, stderr 0.027, n = 39). While re-exporting the raw traces for cell18, the estimate moved less than one standard error (coefficient 0.294, stderr 0.031, n = 49). While fitting the one-lag kernel for cell17, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.137, stderr 0.016, n = 43). While re-exporting the raw traces for cell14, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.236, stderr 0.029, n = 52). While auditing the holding potential column for cell23, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.114, stderr 0.040, n = 40). While auditing the holding potential column for cell08, the coefficient tracked epoch count more closely than duration (coefficient 0.086, stderr 0.014, n = 58). This is the part that will need a real statistical argument.

While re-running with a tighter segmentation threshold for cell11, the ordering of cells was preserved (coefficient 0.301, stderr 0.035, n = 38). While segmenting epochs for cell20, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.194, stderr 0.040, n = 43). While fitting the one-lag kernel for cell14, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.165, stderr 0.018, n = 52).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell21    0.113  0.034   0.046  0.180  53        1000
cell05    0.127  0.045   0.038  0.216  54        500
cell06    0.285  0.039   0.209  0.361  58        2000
cell06    0.117  0.038   0.042  0.193  39        4000
cell10    0.138  0.042   0.056  0.220  57        2000
cell12    0.170  0.010   0.150  0.190  50        1000
cell23    0.270  0.011   0.249  0.292  49        1000
```

### Step 19: comparing per-cell orderings

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell02    0.198  0.022   0.154  0.241  45        4000
cell07    0.102  0.019   0.065  0.139  49        4000
cell02    0.114  0.023   0.069  0.159  45        4000
cell11    0.291  0.029   0.235  0.348  45        1000
cell01    0.239  0.041   0.159  0.319  53        1000
cell22    0.275  0.019   0.237  0.313  53        4000
cell15    0.284  0.022   0.242  0.327  55        1000
cell08    0.164  0.021   0.123  0.205  50        4000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell17    0.293  0.021   0.251  0.335  41        1000
cell22    0.216  0.033   0.151  0.280  50        1000
cell02    0.294  0.026   0.243  0.344  53        2000
cell10    0.242  0.011   0.220  0.265  46        2000
cell06    0.173  0.040   0.095  0.250  43        500
cell11    0.248  0.011   0.226  0.270  43        4000
cell13    0.172  0.038   0.097  0.246  41        500
cell12    0.235  0.036   0.165  0.305  51        500
cell24    0.294  0.032   0.232  0.357  42        4000
cell22    0.256  0.045   0.168  0.343  57        500
cell13    0.272  0.012   0.248  0.297  48        500
cell03    0.179  0.040   0.100  0.258  55        1000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell07    0.197  0.013   0.171  0.222  51        2000
cell09    0.293  0.041   0.212  0.374  55        500
cell06    0.193  0.013   0.168  0.218  41        1000
cell02    0.252  0.033   0.188  0.316  47        1000
cell07    0.286  0.028   0.232  0.340  45        4000
cell03    0.257  0.042   0.175  0.339  54        2000
cell14    0.227  0.023   0.182  0.273  57        4000
cell16    0.131  0.038   0.057  0.204  46        2000
cell18    0.287  0.015   0.258  0.315  51        4000
cell12    0.110  0.047   0.019  0.201  50        500
cell13    0.152  0.046   0.062  0.243  46        1000
cell12    0.147  0.016   0.116  0.178  47        4000
cell23    0.174  0.019   0.138  0.211  55        2000
cell02    0.171  0.031   0.111  0.232  39        500
```

### Step 20: re-exporting the raw traces

```python
coefs = fit_per_cell(rows, threshold=0.58)
lo, hi = ci(coefs, seed=81)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell10    0.196  0.034   0.130  0.262  57        4000
cell01    0.273  0.022   0.230  0.316  44        500
cell24    0.242  0.042   0.159  0.324  52        500
cell19    0.226  0.014   0.198  0.254  50        4000
cell12    0.232  0.020   0.192  0.272  44        500
cell07    0.204  0.015   0.174  0.233  43        2000
cell01    0.090  0.035   0.022  0.158  50        4000
cell05    0.192  0.033   0.128  0.256  40        1000
cell03    0.086  0.042   0.004  0.168  45        2000
cell05    0.167  0.027   0.114  0.220  48        500
cell04    0.285  0.027   0.233  0.337  43        500
cell14    0.268  0.039   0.192  0.344  57        1000
cell17    0.143  0.045   0.055  0.230  53        4000
cell16    0.085  0.013   0.059  0.111  42        1000
```

```python
coefs = fit_per_cell(rows, threshold=0.35)
lo, hi = ci(coefs, seed=52)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell24    0.130  0.018   0.095  0.166  40        1000
cell20    0.281  0.011   0.260  0.303  41        500
cell10    0.204  0.032   0.141  0.266  43        1000
cell04    0.240  0.037   0.168  0.312  50        4000
cell06    0.146  0.022   0.103  0.189  39        1000
cell10    0.096  0.021   0.054  0.138  43        2000
cell06    0.264  0.045   0.176  0.351  42        500
cell13    0.152  0.047   0.060  0.244  54        4000
cell15    0.261  0.013   0.236  0.287  46        4000
cell01    0.172  0.032   0.110  0.234  38        500
cell11    0.151  0.024   0.103  0.199  43        4000
```

### Step 21: bootstrapping the CI

While auditing the holding potential column for cell16, the ordering of cells was preserved (coefficient 0.298, stderr 0.040, n = 38). While segmenting epochs for cell20, nothing in the figure changed at print size (coefficient 0.121, stderr 0.050, n = 47). While re-running with a tighter segmentation threshold for cell11, the estimate moved less than one standard error (coefficient 0.267, stderr 0.023, n = 41). While fitting the one-lag kernel for cell10, the estimate moved less than one standard error (coefficient 0.125, stderr 0.037, n = 54). While comparing per-cell orderings for cell10, the estimate moved less than one standard error (coefficient 0.198, stderr 0.036, n = 50).

```python
coefs = fit_per_cell(rows, threshold=0.40)
lo, hi = ci(coefs, seed=57)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 22: bootstrapping the CI

While bootstrapping the CI for cell01, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.117, stderr 0.033, n = 51). While fitting the one-lag kernel for cell16, the ordering of cells was preserved (coefficient 0.120, stderr 0.015, n = 50). While comparing per-cell orderings for cell03, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.214, stderr 0.042, n = 55). While segmenting epochs for cell16, the estimate moved less than one standard error (coefficient 0.146, stderr 0.023, n = 56). While bootstrapping the CI for cell04, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.117, stderr 0.023, n = 58).

While checking residual autocorrelation for cell18, two cells fell out of the usable range (coefficient 0.276, stderr 0.043, n = 56). While comparing per-cell orderings for cell22, nothing in the figure changed at print size (coefficient 0.222, stderr 0.021, n = 55). While checking residual autocorrelation for cell14, nothing in the figure changed at print size (coefficient 0.246, stderr 0.030, n = 52). While comparing per-cell orderings for cell04, the coefficient tracked epoch count more closely than duration (coefficient 0.191, stderr 0.028, n = 50). While re-running with a tighter segmentation threshold for cell14, the ordering of cells was preserved (coefficient 0.123, stderr 0.036, n = 57).

While auditing the holding potential column for cell07, nothing in the figure changed at print size (coefficient 0.161, stderr 0.048, n = 43). While checking residual autocorrelation for cell11, the coefficient tracked epoch count more closely than duration (coefficient 0.308, stderr 0.032, n = 40). While comparing per-cell orderings for cell07, the coefficient tracked epoch count more closely than duration (coefficient 0.236, stderr 0.026, n = 58). While bootstrapping the CI for cell10, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.096, stderr 0.027, n = 57). While re-exporting the raw traces for cell19, two cells fell out of the usable range (coefficient 0.238, stderr 0.017, n = 48). While bootstrapping the CI for cell22, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.285, stderr 0.047, n = 47).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell18    0.234  0.026   0.183  0.284  51        4000
cell24    0.130  0.025   0.082  0.178  58        1000
cell20    0.119  0.037   0.045  0.192  51        500
cell14    0.100  0.011   0.079  0.122  52        4000
cell10    0.223  0.012   0.200  0.245  50        4000
cell01    0.308  0.017   0.275  0.340  53        4000
cell23    0.208  0.034   0.141  0.275  40        2000
```

### Step 23: re-running with a tighter segmentation threshold

While fitting the one-lag kernel for cell23, two cells fell out of the usable range (coefficient 0.130, stderr 0.019, n = 57). While re-exporting the raw traces for cell15, the coefficient tracked epoch count more closely than duration (coefficient 0.283, stderr 0.041, n = 58). While comparing per-cell orderings for cell08, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.309, stderr 0.031, n = 53). While checking residual autocorrelation for cell02, the CI narrowed by roughly a tenth (coefficient 0.138, stderr 0.033, n = 56). While auditing the holding potential column for cell07, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.176, stderr 0.022, n = 41). While bootstrapping the CI for cell05, the coefficient tracked epoch count more closely than duration (coefficient 0.158, stderr 0.030, n = 58).

While re-running with a tighter segmentation threshold for cell06, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.159, stderr 0.045, n = 58). While comparing per-cell orderings for cell21, the ordering of cells was preserved (coefficient 0.210, stderr 0.025, n = 41). While segmenting epochs for cell17, the coefficient tracked epoch count more closely than duration (coefficient 0.200, stderr 0.011, n = 50). While re-running with a tighter segmentation threshold for cell11, two cells fell out of the usable range (coefficient 0.295, stderr 0.013, n = 41). While segmenting epochs for cell08, two cells fell out of the usable range (coefficient 0.176, stderr 0.028, n = 41).

While re-exporting the raw traces for cell17, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.309, stderr 0.017, n = 56). While re-exporting the raw traces for cell12, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.123, stderr 0.033, n = 50). While re-exporting the raw traces for cell15, the CI narrowed by roughly a tenth (coefficient 0.283, stderr 0.041, n = 43). While fitting the one-lag kernel for cell13, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.204, stderr 0.024, n = 49). While bootstrapping the CI for cell09, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.242, stderr 0.014, n = 41). While bootstrapping the CI for cell02, the CI narrowed by roughly a tenth (coefficient 0.269, stderr 0.014, n = 46). Parking this until the re-segmentation lands.

### Step 24: comparing per-cell orderings

While bootstrapping the CI for cell18, the CI narrowed by roughly a tenth (coefficient 0.152, stderr 0.040, n = 49). While re-running with a tighter segmentation threshold for cell06, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.245, stderr 0.012, n = 51). While fitting the one-lag kernel for cell10, nothing in the figure changed at print size (coefficient 0.106, stderr 0.010, n = 53). While re-exporting the raw traces for cell10, the CI narrowed by roughly a tenth (coefficient 0.192, stderr 0.027, n = 44). While checking residual autocorrelation for cell06, two cells fell out of the usable range (coefficient 0.107, stderr 0.020, n = 58). While comparing per-cell orderings for cell08, the CI narrowed by roughly a tenth (coefficient 0.085, stderr 0.043, n = 40).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell22    0.102  0.045   0.014  0.190  52        500
cell13    0.090  0.028   0.036  0.144  53        500
cell16    0.260  0.013   0.234  0.287  42        500
cell05    0.132  0.034   0.066  0.199  49        500
cell04    0.262  0.028   0.207  0.316  50        500
cell08    0.264  0.023   0.219  0.309  47        2000
cell15    0.246  0.039   0.170  0.322  45        4000
cell09    0.134  0.028   0.080  0.189  47        1000
cell06    0.212  0.030   0.154  0.271  53        4000
cell08    0.283  0.044   0.198  0.369  56        1000
cell16    0.271  0.027   0.219  0.323  51        500
cell04    0.114  0.023   0.069  0.160  40        1000
cell14    0.115  0.034   0.048  0.182  55        2000
cell24    0.305  0.048   0.211  0.399  57        500
```

### Step 25: segmenting epochs

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell12    0.173  0.035   0.104  0.242  44        1000
cell20    0.133  0.017   0.100  0.167  40        1000
cell07    0.254  0.047   0.162  0.346  42        500
cell09    0.157  0.012   0.134  0.180  46        2000
cell16    0.160  0.030   0.102  0.218  48        4000
cell01    0.220  0.014   0.192  0.247  47        4000
```

While checking residual autocorrelation for cell06, the ordering of cells was preserved (coefficient 0.301, stderr 0.016, n = 43). While auditing the holding potential column for cell03, the estimate moved less than one standard error (coefficient 0.126, stderr 0.032, n = 50). While segmenting epochs for cell19, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.148, stderr 0.019, n = 45).

```python
coefs = fit_per_cell(rows, threshold=0.45)
lo, hi = ci(coefs, seed=27)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell21    0.190  0.025   0.141  0.239  43        500
cell04    0.147  0.037   0.074  0.220  41        4000
cell11    0.188  0.020   0.149  0.227  51        2000
cell22    0.092  0.012   0.068  0.115  45        500
cell01    0.287  0.015   0.257  0.317  39        2000
cell13    0.228  0.017   0.194  0.262  56        4000
cell24    0.163  0.035   0.095  0.231  52        1000
cell05    0.282  0.036   0.212  0.352  51        500
cell16    0.106  0.034   0.040  0.172  40        1000
cell10    0.235  0.032   0.173  0.297  47        4000
cell06    0.158  0.015   0.128  0.187  44        1000
cell04    0.102  0.031   0.041  0.164  39        2000
```

### Step 26: checking residual autocorrelation

While comparing per-cell orderings for cell10, the coefficient tracked epoch count more closely than duration (coefficient 0.191, stderr 0.028, n = 57). While bootstrapping the CI for cell13, two cells fell out of the usable range (coefficient 0.239, stderr 0.013, n = 46). While segmenting epochs for cell08, two cells fell out of the usable range (coefficient 0.116, stderr 0.020, n = 52).

While segmenting epochs for cell13, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.171, stderr 0.025, n = 45). While segmenting epochs for cell03, the CI narrowed by roughly a tenth (coefficient 0.164, stderr 0.027, n = 53). While re-running with a tighter segmentation threshold for cell13, the coefficient tracked epoch count more closely than duration (coefficient 0.170, stderr 0.047, n = 52). While checking residual autocorrelation for cell06, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.141, stderr 0.011, n = 47). Flagging it so it does not get rediscovered next week.

### Step 27: comparing per-cell orderings

While segmenting epochs for cell03, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.124, stderr 0.033, n = 39). While checking residual autocorrelation for cell16, the coefficient tracked epoch count more closely than duration (coefficient 0.213, stderr 0.046, n = 56). While comparing per-cell orderings for cell10, the ordering of cells was preserved (coefficient 0.254, stderr 0.033, n = 40). Parking this until the re-segmentation lands.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell02    0.244  0.047   0.151  0.336  43        2000
cell20    0.148  0.034   0.082  0.214  57        2000
cell08    0.159  0.019   0.121  0.197  40        500
cell15    0.285  0.029   0.227  0.342  47        1000
cell23    0.134  0.011   0.112  0.156  49        4000
cell08    0.129  0.018   0.094  0.165  51        2000
cell17    0.081  0.042   -0.000  0.163  57        4000
cell12    0.089  0.020   0.050  0.129  44        2000
cell06    0.283  0.042   0.202  0.365  55        2000
cell13    0.232  0.042   0.150  0.314  54        2000
cell16    0.253  0.023   0.208  0.299  48        4000
```

While comparing per-cell orderings for cell16, the estimate moved less than one standard error (coefficient 0.307, stderr 0.042, n = 47). While re-running with a tighter segmentation threshold for cell14, nothing in the figure changed at print size (coefficient 0.284, stderr 0.030, n = 52). While re-exporting the raw traces for cell06, the coefficient tracked epoch count more closely than duration (coefficient 0.188, stderr 0.020, n = 56).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell17    0.099  0.038   0.024  0.174  40        4000
cell18    0.081  0.010   0.061  0.101  55        4000
cell18    0.090  0.027   0.037  0.143  51        4000
cell02    0.101  0.047   0.009  0.192  39        1000
cell14    0.224  0.048   0.130  0.318  49        2000
cell15    0.274  0.040   0.197  0.352  44        500
cell12    0.260  0.046   0.169  0.351  55        1000
```

### Step 28: checking residual autocorrelation

```python
coefs = fit_per_cell(rows, threshold=0.80)
lo, hi = ci(coefs, seed=5)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell14    0.125  0.034   0.059  0.191  49        2000
cell05    0.226  0.027   0.173  0.279  48        1000
cell17    0.275  0.037   0.202  0.348  47        4000
cell01    0.291  0.043   0.207  0.375  56        1000
cell22    0.260  0.041   0.178  0.341  44        500
cell06    0.179  0.013   0.154  0.204  42        1000
cell05    0.310  0.024   0.262  0.357  50        4000
cell22    0.233  0.028   0.178  0.287  58        2000
cell04    0.192  0.012   0.168  0.216  40        4000
cell19    0.174  0.042   0.091  0.257  45        500
```

While comparing per-cell orderings for cell22, two cells fell out of the usable range (coefficient 0.105, stderr 0.047, n = 51). While auditing the holding potential column for cell24, nothing in the figure changed at print size (coefficient 0.095, stderr 0.013, n = 51). While auditing the holding potential column for cell10, nothing in the figure changed at print size (coefficient 0.151, stderr 0.040, n = 50). While re-exporting the raw traces for cell12, the CI narrowed by roughly a tenth (coefficient 0.087, stderr 0.037, n = 41). While re-running with a tighter segmentation threshold for cell05, the CI narrowed by roughly a tenth (coefficient 0.226, stderr 0.012, n = 57). While re-running with a tighter segmentation threshold for cell06, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.272, stderr 0.031, n = 48). This is the part that will need a real statistical argument.

While bootstrapping the CI for cell04, the coefficient tracked epoch count more closely than duration (coefficient 0.215, stderr 0.020, n = 58). While re-exporting the raw traces for cell15, the coefficient tracked epoch count more closely than duration (coefficient 0.270, stderr 0.016, n = 46). While segmenting epochs for cell19, nothing in the figure changed at print size (coefficient 0.260, stderr 0.033, n = 47). While bootstrapping the CI for cell20, the estimate moved less than one standard error (coefficient 0.211, stderr 0.041, n = 51).

### Step 29: checking residual autocorrelation

```python
coefs = fit_per_cell(rows, threshold=0.45)
lo, hi = ci(coefs, seed=29)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell05    0.201  0.048   0.107  0.294  41        4000
cell06    0.264  0.029   0.207  0.320  41        500
cell13    0.289  0.019   0.251  0.327  47        2000
cell12    0.243  0.046   0.152  0.334  42        500
cell20    0.283  0.036   0.212  0.353  38        1000
cell06    0.187  0.029   0.130  0.244  58        2000
cell15    0.269  0.020   0.229  0.309  38        1000
cell02    0.145  0.021   0.103  0.186  46        500
cell17    0.284  0.030   0.225  0.343  58        4000
cell05    0.239  0.017   0.207  0.272  48        2000
cell01    0.264  0.016   0.233  0.296  45        1000
cell12    0.298  0.015   0.269  0.328  41        2000
```

While fitting the one-lag kernel for cell06, the ordering of cells was preserved (coefficient 0.171, stderr 0.018, n = 56). While checking residual autocorrelation for cell03, the CI narrowed by roughly a tenth (coefficient 0.216, stderr 0.021, n = 57). While bootstrapping the CI for cell21, the ordering of cells was preserved (coefficient 0.300, stderr 0.013, n = 53). While auditing the holding potential column for cell12, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.081, stderr 0.035, n = 40). While comparing per-cell orderings for cell16, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.245, stderr 0.035, n = 55).

### Step 30: re-running with a tighter segmentation threshold

While checking residual autocorrelation for cell16, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.160, stderr 0.027, n = 38). While fitting the one-lag kernel for cell08, the CI narrowed by roughly a tenth (coefficient 0.144, stderr 0.017, n = 38). While re-exporting the raw traces for cell07, the coefficient tracked epoch count more closely than duration (coefficient 0.262, stderr 0.014, n = 55). While comparing per-cell orderings for cell14, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.175, stderr 0.042, n = 54).

```python
coefs = fit_per_cell(rows, threshold=0.39)
lo, hi = ci(coefs, seed=16)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 31: comparing per-cell orderings

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell16    0.220  0.031   0.159  0.280  38        4000
cell05    0.210  0.047   0.119  0.302  43        2000
cell12    0.086  0.011   0.064  0.109  38        2000
cell01    0.189  0.020   0.150  0.229  54        4000
cell22    0.236  0.032   0.174  0.298  38        500
cell12    0.286  0.019   0.249  0.324  49        4000
cell24    0.246  0.035   0.177  0.315  47        4000
cell14    0.192  0.021   0.150  0.233  58        500
cell04    0.212  0.035   0.144  0.281  42        2000
cell18    0.208  0.014   0.180  0.236  49        1000
cell08    0.217  0.015   0.186  0.247  56        1000
cell07    0.181  0.039   0.103  0.258  40        4000
cell07    0.299  0.045   0.211  0.387  53        4000
cell18    0.102  0.026   0.051  0.153  43        1000
```

While re-running with a tighter segmentation threshold for cell16, the ordering of cells was preserved (coefficient 0.210, stderr 0.036, n = 51). While bootstrapping the CI for cell11, nothing in the figure changed at print size (coefficient 0.299, stderr 0.026, n = 54). While re-exporting the raw traces for cell20, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.140, stderr 0.047, n = 39). While re-running with a tighter segmentation threshold for cell05, nothing in the figure changed at print size (coefficient 0.117, stderr 0.011, n = 54). While fitting the one-lag kernel for cell12, the estimate moved less than one standard error (coefficient 0.158, stderr 0.050, n = 41). Worth noting for the writeup, though not a result on its own.

### Step 32: bootstrapping the CI

While auditing the holding potential column for cell09, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.275, stderr 0.039, n = 47). While re-exporting the raw traces for cell15, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.216, stderr 0.040, n = 48). While re-exporting the raw traces for cell06, the coefficient tracked epoch count more closely than duration (coefficient 0.150, stderr 0.011, n = 49). While comparing per-cell orderings for cell03, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.230, stderr 0.047, n = 48). While comparing per-cell orderings for cell11, the ordering of cells was preserved (coefficient 0.101, stderr 0.040, n = 44). While fitting the one-lag kernel for cell20, nothing in the figure changed at print size (coefficient 0.108, stderr 0.020, n = 54). Flagging it so it does not get rediscovered next week.

While bootstrapping the CI for cell03, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.254, stderr 0.019, n = 57). While fitting the one-lag kernel for cell20, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.228, stderr 0.024, n = 56). While bootstrapping the CI for cell09, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.233, stderr 0.027, n = 51). While auditing the holding potential column for cell01, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.090, stderr 0.050, n = 57). While auditing the holding potential column for cell08, the estimate moved less than one standard error (coefficient 0.242, stderr 0.020, n = 41).

While re-exporting the raw traces for cell05, two cells fell out of the usable range (coefficient 0.106, stderr 0.042, n = 48). While re-running with a tighter segmentation threshold for cell09, nothing in the figure changed at print size (coefficient 0.297, stderr 0.018, n = 56). While bootstrapping the CI for cell12, the CI narrowed by roughly a tenth (coefficient 0.197, stderr 0.048, n = 54). Parking this until the re-segmentation lands.

### Step 33: checking residual autocorrelation

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell11    0.212  0.026   0.161  0.263  43        4000
cell20    0.236  0.038   0.162  0.311  54        1000
cell16    0.207  0.011   0.186  0.228  49        1000
cell05    0.211  0.028   0.155  0.266  58        1000
cell23    0.193  0.035   0.124  0.261  52        2000
cell13    0.133  0.045   0.045  0.220  42        2000
cell18    0.275  0.049   0.178  0.371  43        500
cell21    0.244  0.019   0.206  0.283  49        4000
cell24    0.203  0.038   0.129  0.277  50        2000
cell01    0.169  0.050   0.072  0.267  42        4000
cell06    0.116  0.047   0.025  0.208  42        4000
cell21    0.142  0.013   0.116  0.168  49        4000
```

While comparing per-cell orderings for cell03, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.084, stderr 0.026, n = 53). While segmenting epochs for cell19, the CI narrowed by roughly a tenth (coefficient 0.141, stderr 0.040, n = 56). While comparing per-cell orderings for cell20, the coefficient tracked epoch count more closely than duration (coefficient 0.135, stderr 0.036, n = 47). While re-running with a tighter segmentation threshold for cell22, the CI narrowed by roughly a tenth (coefficient 0.231, stderr 0.027, n = 49). Parking this until the re-segmentation lands.

While comparing per-cell orderings for cell14, two cells fell out of the usable range (coefficient 0.299, stderr 0.020, n = 47). While checking residual autocorrelation for cell13, the CI narrowed by roughly a tenth (coefficient 0.111, stderr 0.050, n = 47). While segmenting epochs for cell02, the CI narrowed by roughly a tenth (coefficient 0.270, stderr 0.036, n = 54). While checking residual autocorrelation for cell10, the CI narrowed by roughly a tenth (coefficient 0.191, stderr 0.020, n = 43). While comparing per-cell orderings for cell22, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.116, stderr 0.040, n = 53). While bootstrapping the CI for cell02, the coefficient tracked epoch count more closely than duration (coefficient 0.183, stderr 0.033, n = 58).

### Step 34: auditing the holding potential column

While auditing the holding potential column for cell03, the CI narrowed by roughly a tenth (coefficient 0.188, stderr 0.015, n = 51). While fitting the one-lag kernel for cell07, two cells fell out of the usable range (coefficient 0.226, stderr 0.026, n = 43). While auditing the holding potential column for cell08, two cells fell out of the usable range (coefficient 0.246, stderr 0.018, n = 51). While auditing the holding potential column for cell16, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.264, stderr 0.012, n = 57). Flagging it so it does not get rediscovered next week.

While checking residual autocorrelation for cell15, the estimate moved less than one standard error (coefficient 0.244, stderr 0.039, n = 56). While comparing per-cell orderings for cell14, two cells fell out of the usable range (coefficient 0.194, stderr 0.049, n = 46). While comparing per-cell orderings for cell06, the ordering of cells was preserved (coefficient 0.210, stderr 0.015, n = 43). While re-exporting the raw traces for cell09, the estimate moved less than one standard error (coefficient 0.203, stderr 0.029, n = 56). While comparing per-cell orderings for cell13, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.213, stderr 0.049, n = 40).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell10    0.149  0.026   0.099  0.200  51        4000
cell23    0.117  0.016   0.085  0.149  40        4000
cell24    0.093  0.038   0.019  0.167  57        1000
cell04    0.098  0.013   0.071  0.124  48        2000
cell02    0.241  0.035   0.173  0.310  57        1000
cell09    0.168  0.029   0.111  0.225  57        1000
cell20    0.253  0.038   0.180  0.327  42        4000
cell04    0.287  0.011   0.266  0.308  47        500
cell20    0.273  0.036   0.203  0.344  50        2000
cell08    0.131  0.027   0.078  0.184  43        500
```

### Step 35: checking residual autocorrelation

While auditing the holding potential column for cell23, the CI narrowed by roughly a tenth (coefficient 0.098, stderr 0.017, n = 38). While checking residual autocorrelation for cell01, the CI narrowed by roughly a tenth (coefficient 0.125, stderr 0.016, n = 50). While re-running with a tighter segmentation threshold for cell07, two cells fell out of the usable range (coefficient 0.144, stderr 0.035, n = 40). While auditing the holding potential column for cell09, two cells fell out of the usable range (coefficient 0.208, stderr 0.011, n = 56).

While bootstrapping the CI for cell14, the estimate moved less than one standard error (coefficient 0.283, stderr 0.046, n = 39). While comparing per-cell orderings for cell20, the ordering of cells was preserved (coefficient 0.189, stderr 0.045, n = 55). While bootstrapping the CI for cell14, two cells fell out of the usable range (coefficient 0.181, stderr 0.024, n = 56). While comparing per-cell orderings for cell08, the ordering of cells was preserved (coefficient 0.149, stderr 0.033, n = 45).

While bootstrapping the CI for cell12, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.291, stderr 0.031, n = 55). While auditing the holding potential column for cell10, the estimate moved less than one standard error (coefficient 0.137, stderr 0.028, n = 46). While re-running with a tighter segmentation threshold for cell04, two cells fell out of the usable range (coefficient 0.127, stderr 0.011, n = 58). While comparing per-cell orderings for cell02, the coefficient tracked epoch count more closely than duration (coefficient 0.280, stderr 0.044, n = 47). This is the part that will need a real statistical argument.

### Step 36: re-exporting the raw traces

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell13    0.181  0.010   0.161  0.201  56        4000
cell17    0.224  0.044   0.138  0.310  51        500
cell21    0.299  0.019   0.262  0.336  38        2000
cell15    0.307  0.040   0.229  0.384  48        4000
cell11    0.155  0.039   0.078  0.231  58        500
cell23    0.157  0.041   0.076  0.237  51        4000
cell14    0.133  0.046   0.043  0.223  58        4000
cell12    0.302  0.036   0.231  0.372  55        2000
cell06    0.258  0.031   0.197  0.319  50        1000
```

While auditing the holding potential column for cell17, the coefficient tracked epoch count more closely than duration (coefficient 0.274, stderr 0.011, n = 40). While segmenting epochs for cell05, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.124, stderr 0.029, n = 42). While auditing the holding potential column for cell16, nothing in the figure changed at print size (coefficient 0.173, stderr 0.027, n = 55).

While re-exporting the raw traces for cell21, nothing in the figure changed at print size (coefficient 0.138, stderr 0.010, n = 55). While comparing per-cell orderings for cell11, the coefficient tracked epoch count more closely than duration (coefficient 0.160, stderr 0.046, n = 46). While comparing per-cell orderings for cell14, two cells fell out of the usable range (coefficient 0.162, stderr 0.043, n = 56). While re-exporting the raw traces for cell07, the estimate moved less than one standard error (coefficient 0.308, stderr 0.020, n = 48). While re-running with a tighter segmentation threshold for cell09, the CI narrowed by roughly a tenth (coefficient 0.155, stderr 0.044, n = 52).

While segmenting epochs for cell05, the CI narrowed by roughly a tenth (coefficient 0.096, stderr 0.049, n = 53). While checking residual autocorrelation for cell04, the CI narrowed by roughly a tenth (coefficient 0.221, stderr 0.032, n = 44). While re-exporting the raw traces for cell19, the CI narrowed by roughly a tenth (coefficient 0.158, stderr 0.037, n = 41). While re-exporting the raw traces for cell23, the estimate moved less than one standard error (coefficient 0.124, stderr 0.040, n = 55). While checking residual autocorrelation for cell22, nothing in the figure changed at print size (coefficient 0.178, stderr 0.024, n = 45). While auditing the holding potential column for cell15, the ordering of cells was preserved (coefficient 0.115, stderr 0.017, n = 52).

### Step 37: checking residual autocorrelation

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell16    0.093  0.016   0.061  0.125  45        1000
cell21    0.177  0.018   0.141  0.213  43        500
cell09    0.275  0.035   0.207  0.342  43        1000
cell12    0.232  0.015   0.202  0.262  42        500
cell06    0.186  0.026   0.135  0.238  55        500
cell06    0.099  0.047   0.008  0.191  48        2000
cell23    0.260  0.037   0.187  0.333  40        1000
cell02    0.125  0.012   0.101  0.148  52        2000
cell20    0.154  0.030   0.095  0.213  56        4000
cell13    0.161  0.037   0.088  0.233  43        1000
cell02    0.101  0.045   0.013  0.189  49        500
```

```python
coefs = fit_per_cell(rows, threshold=0.70)
lo, hi = ci(coefs, seed=59)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell16    0.224  0.013   0.199  0.250  46        4000
cell05    0.139  0.014   0.111  0.167  41        4000
cell13    0.098  0.023   0.052  0.144  51        2000
cell06    0.279  0.011   0.257  0.302  44        500
cell01    0.251  0.022   0.208  0.294  38        500
cell15    0.108  0.017   0.074  0.142  41        500
cell01    0.212  0.017   0.179  0.245  39        1000
cell23    0.265  0.032   0.203  0.327  46        500
cell24    0.253  0.038   0.180  0.327  48        1000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell13    0.267  0.031   0.207  0.327  47        2000
cell05    0.230  0.040   0.152  0.307  53        500
cell23    0.198  0.042   0.115  0.280  39        500
cell04    0.154  0.042   0.072  0.236  41        500
cell14    0.118  0.012   0.094  0.141  56        500
cell20    0.116  0.031   0.055  0.176  47        500
cell03    0.114  0.012   0.091  0.137  44        1000
cell12    0.164  0.043   0.079  0.248  40        4000
cell13    0.230  0.025   0.181  0.280  58        2000
cell24    0.090  0.032   0.028  0.152  49        1000
```

