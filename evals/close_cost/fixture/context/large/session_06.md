# Prior session 6 of 20

Transcript of an earlier working session on the history-kernel analysis.

### Step 1: re-running with a tighter segmentation threshold

While comparing per-cell orderings for cell12, the ordering of cells was preserved (coefficient 0.090, stderr 0.027, n = 55). While checking residual autocorrelation for cell24, the coefficient tracked epoch count more closely than duration (coefficient 0.130, stderr 0.022, n = 41). While auditing the holding potential column for cell17, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.228, stderr 0.026, n = 40).

While re-exporting the raw traces for cell04, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.136, stderr 0.018, n = 57). While segmenting epochs for cell03, nothing in the figure changed at print size (coefficient 0.193, stderr 0.045, n = 54). While segmenting epochs for cell06, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.135, stderr 0.034, n = 52). While segmenting epochs for cell04, the ordering of cells was preserved (coefficient 0.112, stderr 0.021, n = 44). While fitting the one-lag kernel for cell18, the CI narrowed by roughly a tenth (coefficient 0.218, stderr 0.034, n = 57).

### Step 2: checking residual autocorrelation

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell03    0.156  0.044   0.070  0.241  56        4000
cell01    0.227  0.021   0.185  0.269  43        2000
cell14    0.111  0.047   0.018  0.204  52        500
cell18    0.187  0.043   0.102  0.271  55        1000
cell13    0.222  0.034   0.155  0.288  46        500
cell10    0.232  0.021   0.190  0.273  54        2000
cell13    0.214  0.022   0.170  0.257  58        2000
cell02    0.175  0.019   0.138  0.211  39        500
cell07    0.299  0.033   0.235  0.363  46        4000
cell23    0.203  0.034   0.135  0.270  58        1000
cell13    0.105  0.045   0.017  0.192  50        4000
cell10    0.248  0.020   0.209  0.288  56        2000
```

While re-exporting the raw traces for cell08, the estimate moved less than one standard error (coefficient 0.233, stderr 0.014, n = 58). While auditing the holding potential column for cell01, two cells fell out of the usable range (coefficient 0.224, stderr 0.020, n = 40). While fitting the one-lag kernel for cell04, the CI narrowed by roughly a tenth (coefficient 0.173, stderr 0.027, n = 48). While segmenting epochs for cell04, the estimate moved less than one standard error (coefficient 0.230, stderr 0.045, n = 42). While re-running with a tighter segmentation threshold for cell14, the CI narrowed by roughly a tenth (coefficient 0.163, stderr 0.043, n = 41).

While re-exporting the raw traces for cell19, the CI narrowed by roughly a tenth (coefficient 0.286, stderr 0.033, n = 54). While bootstrapping the CI for cell14, the estimate moved less than one standard error (coefficient 0.294, stderr 0.042, n = 43). While re-exporting the raw traces for cell07, the coefficient tracked epoch count more closely than duration (coefficient 0.101, stderr 0.045, n = 47). While re-exporting the raw traces for cell22, the coefficient tracked epoch count more closely than duration (coefficient 0.170, stderr 0.035, n = 43). While checking residual autocorrelation for cell08, two cells fell out of the usable range (coefficient 0.180, stderr 0.050, n = 42). While fitting the one-lag kernel for cell17, the ordering of cells was preserved (coefficient 0.225, stderr 0.033, n = 51).

While re-exporting the raw traces for cell23, two cells fell out of the usable range (coefficient 0.281, stderr 0.034, n = 53). While re-exporting the raw traces for cell05, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.089, stderr 0.011, n = 48). While segmenting epochs for cell17, the ordering of cells was preserved (coefficient 0.238, stderr 0.034, n = 46). While segmenting epochs for cell02, the coefficient tracked epoch count more closely than duration (coefficient 0.237, stderr 0.030, n = 38). Worth noting for the writeup, though not a result on its own.

### Step 3: bootstrapping the CI

```python
coefs = fit_per_cell(rows, threshold=0.75)
lo, hi = ci(coefs, seed=11)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While auditing the holding potential column for cell04, the ordering of cells was preserved (coefficient 0.145, stderr 0.044, n = 38). While fitting the one-lag kernel for cell04, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.243, stderr 0.019, n = 53). While fitting the one-lag kernel for cell15, the coefficient tracked epoch count more closely than duration (coefficient 0.153, stderr 0.041, n = 55).

### Step 4: checking residual autocorrelation

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell18    0.278  0.025   0.230  0.326  47        1000
cell03    0.255  0.011   0.234  0.276  58        4000
cell20    0.253  0.012   0.229  0.276  54        2000
cell04    0.139  0.013   0.113  0.166  48        1000
cell02    0.273  0.022   0.230  0.315  39        4000
cell22    0.300  0.016   0.268  0.331  45        2000
cell19    0.131  0.022   0.088  0.174  54        4000
cell22    0.256  0.032   0.193  0.318  39        1000
cell13    0.138  0.025   0.089  0.186  47        4000
cell02    0.155  0.027   0.102  0.207  54        4000
cell13    0.295  0.014   0.267  0.322  58        2000
```

While auditing the holding potential column for cell15, two cells fell out of the usable range (coefficient 0.204, stderr 0.037, n = 54). While comparing per-cell orderings for cell17, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.162, stderr 0.050, n = 40). While fitting the one-lag kernel for cell12, the CI narrowed by roughly a tenth (coefficient 0.129, stderr 0.042, n = 46). While re-running with a tighter segmentation threshold for cell23, nothing in the figure changed at print size (coefficient 0.113, stderr 0.016, n = 46).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell10    0.236  0.045   0.147  0.325  57        500
cell22    0.293  0.042   0.211  0.375  52        500
cell09    0.140  0.037   0.067  0.213  42        500
cell02    0.160  0.043   0.076  0.244  41        2000
cell20    0.256  0.040   0.177  0.334  52        1000
cell07    0.228  0.049   0.132  0.325  52        2000
cell13    0.294  0.015   0.264  0.324  54        500
cell13    0.122  0.043   0.038  0.205  42        2000
```

### Step 5: re-exporting the raw traces

```python
coefs = fit_per_cell(rows, threshold=0.50)
lo, hi = ci(coefs, seed=7)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While re-running with a tighter segmentation threshold for cell14, two cells fell out of the usable range (coefficient 0.160, stderr 0.043, n = 47). While checking residual autocorrelation for cell01, the coefficient tracked epoch count more closely than duration (coefficient 0.130, stderr 0.027, n = 41). While comparing per-cell orderings for cell07, the coefficient tracked epoch count more closely than duration (coefficient 0.090, stderr 0.024, n = 49). While re-running with a tighter segmentation threshold for cell16, the coefficient tracked epoch count more closely than duration (coefficient 0.295, stderr 0.047, n = 41). Parking this until the re-segmentation lands.

While segmenting epochs for cell19, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.137, stderr 0.037, n = 51). While checking residual autocorrelation for cell16, the estimate moved less than one standard error (coefficient 0.266, stderr 0.046, n = 44). While fitting the one-lag kernel for cell20, nothing in the figure changed at print size (coefficient 0.253, stderr 0.048, n = 41). While bootstrapping the CI for cell05, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.200, stderr 0.042, n = 42).

While comparing per-cell orderings for cell10, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.250, stderr 0.046, n = 53). While segmenting epochs for cell02, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.209, stderr 0.042, n = 40). While bootstrapping the CI for cell01, the ordering of cells was preserved (coefficient 0.160, stderr 0.023, n = 38).

### Step 6: re-exporting the raw traces

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell01    0.084  0.041   0.005  0.164  40        1000
cell16    0.236  0.027   0.184  0.289  43        2000
cell12    0.119  0.046   0.029  0.208  53        4000
cell24    0.135  0.014   0.107  0.162  42        500
cell12    0.243  0.033   0.178  0.309  40        2000
cell05    0.150  0.030   0.092  0.209  42        500
cell09    0.277  0.015   0.248  0.306  47        500
cell16    0.163  0.037   0.090  0.236  49        2000
cell03    0.087  0.049   -0.008  0.183  55        1000
cell10    0.151  0.046   0.060  0.241  41        2000
cell14    0.263  0.017   0.230  0.296  47        4000
```

While segmenting epochs for cell10, the coefficient tracked epoch count more closely than duration (coefficient 0.118, stderr 0.030, n = 43). While re-running with a tighter segmentation threshold for cell20, the coefficient tracked epoch count more closely than duration (coefficient 0.192, stderr 0.048, n = 48). While comparing per-cell orderings for cell12, the CI narrowed by roughly a tenth (coefficient 0.262, stderr 0.022, n = 55). While re-running with a tighter segmentation threshold for cell06, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.105, stderr 0.049, n = 47). While fitting the one-lag kernel for cell16, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.208, stderr 0.031, n = 49). While re-exporting the raw traces for cell04, the CI narrowed by roughly a tenth (coefficient 0.146, stderr 0.020, n = 47).

### Step 7: re-running with a tighter segmentation threshold

While re-exporting the raw traces for cell04, the ordering of cells was preserved (coefficient 0.130, stderr 0.049, n = 58). While fitting the one-lag kernel for cell06, the coefficient tracked epoch count more closely than duration (coefficient 0.286, stderr 0.024, n = 46). While re-exporting the raw traces for cell19, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.187, stderr 0.011, n = 46). While comparing per-cell orderings for cell02, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.124, stderr 0.026, n = 54).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell12    0.122  0.040   0.043  0.201  52        500
cell09    0.155  0.011   0.133  0.177  38        4000
cell10    0.091  0.013   0.066  0.116  56        500
cell24    0.108  0.044   0.022  0.195  51        1000
cell19    0.156  0.032   0.093  0.219  42        1000
cell24    0.224  0.038   0.150  0.298  56        2000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell20    0.167  0.049   0.071  0.262  46        2000
cell05    0.295  0.033   0.230  0.359  45        4000
cell09    0.156  0.040   0.077  0.236  42        2000
cell20    0.206  0.013   0.181  0.232  41        4000
cell18    0.229  0.033   0.165  0.294  43        500
cell19    0.162  0.033   0.098  0.226  44        1000
cell06    0.190  0.043   0.107  0.274  41        500
```

### Step 8: segmenting epochs

While re-exporting the raw traces for cell18, the estimate moved less than one standard error (coefficient 0.168, stderr 0.049, n = 45). While fitting the one-lag kernel for cell01, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.189, stderr 0.042, n = 49). While re-exporting the raw traces for cell10, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.220, stderr 0.048, n = 50).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell09    0.177  0.039   0.100  0.254  55        500
cell09    0.186  0.021   0.145  0.227  54        2000
cell02    0.131  0.036   0.060  0.202  46        500
cell10    0.144  0.012   0.120  0.169  38        2000
cell02    0.111  0.017   0.077  0.145  44        500
cell05    0.167  0.015   0.137  0.197  53        1000
cell10    0.237  0.044   0.149  0.324  56        500
cell12    0.201  0.033   0.136  0.265  46        2000
cell06    0.211  0.012   0.188  0.235  41        4000
cell13    0.098  0.030   0.039  0.156  50        500
```

While bootstrapping the CI for cell04, the coefficient tracked epoch count more closely than duration (coefficient 0.225, stderr 0.035, n = 40). While comparing per-cell orderings for cell07, the ordering of cells was preserved (coefficient 0.193, stderr 0.011, n = 41). While auditing the holding potential column for cell19, the coefficient tracked epoch count more closely than duration (coefficient 0.208, stderr 0.029, n = 56).

### Step 9: checking residual autocorrelation

While comparing per-cell orderings for cell16, the ordering of cells was preserved (coefficient 0.203, stderr 0.049, n = 57). While bootstrapping the CI for cell10, the coefficient tracked epoch count more closely than duration (coefficient 0.100, stderr 0.019, n = 44). While bootstrapping the CI for cell23, the estimate moved less than one standard error (coefficient 0.084, stderr 0.046, n = 47). While comparing per-cell orderings for cell23, the estimate moved less than one standard error (coefficient 0.108, stderr 0.026, n = 39).

While auditing the holding potential column for cell06, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.211, stderr 0.031, n = 54). While re-exporting the raw traces for cell17, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.233, stderr 0.039, n = 45). While fitting the one-lag kernel for cell16, the CI narrowed by roughly a tenth (coefficient 0.168, stderr 0.011, n = 58).

### Step 10: auditing the holding potential column

While auditing the holding potential column for cell18, two cells fell out of the usable range (coefficient 0.168, stderr 0.023, n = 48). While comparing per-cell orderings for cell02, the estimate moved less than one standard error (coefficient 0.246, stderr 0.019, n = 54). While comparing per-cell orderings for cell23, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.124, stderr 0.016, n = 49). While comparing per-cell orderings for cell08, two cells fell out of the usable range (coefficient 0.139, stderr 0.017, n = 49). While comparing per-cell orderings for cell07, the coefficient tracked epoch count more closely than duration (coefficient 0.129, stderr 0.012, n = 39). Flagging it so it does not get rediscovered next week.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell24    0.233  0.045   0.144  0.321  38        2000
cell20    0.081  0.012   0.058  0.103  51        2000
cell21    0.211  0.045   0.124  0.299  43        500
cell12    0.120  0.017   0.087  0.154  56        1000
cell07    0.155  0.039   0.079  0.231  51        1000
cell21    0.210  0.034   0.144  0.277  52        4000
cell24    0.156  0.040   0.077  0.234  50        2000
cell01    0.177  0.022   0.134  0.220  52        4000
cell08    0.298  0.034   0.231  0.365  44        4000
cell16    0.154  0.033   0.089  0.218  51        2000
cell02    0.108  0.021   0.067  0.149  51        2000
cell02    0.247  0.047   0.154  0.339  45        2000
cell02    0.173  0.021   0.131  0.214  47        1000
cell04    0.307  0.032   0.245  0.370  53        500
```

### Step 11: re-exporting the raw traces

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell09    0.223  0.033   0.158  0.288  56        1000
cell04    0.150  0.015   0.121  0.179  46        2000
cell19    0.267  0.037   0.194  0.340  38        4000
cell07    0.299  0.045   0.211  0.387  53        4000
cell21    0.236  0.010   0.216  0.257  51        2000
cell13    0.262  0.025   0.213  0.310  53        2000
cell08    0.103  0.019   0.065  0.140  48        500
cell15    0.253  0.036   0.183  0.323  52        500
cell04    0.291  0.045   0.203  0.380  44        4000
```

While checking residual autocorrelation for cell19, the CI narrowed by roughly a tenth (coefficient 0.201, stderr 0.010, n = 44). While re-running with a tighter segmentation threshold for cell04, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.216, stderr 0.037, n = 38). While checking residual autocorrelation for cell23, nothing in the figure changed at print size (coefficient 0.126, stderr 0.015, n = 50). While re-exporting the raw traces for cell13, two cells fell out of the usable range (coefficient 0.259, stderr 0.020, n = 47). While checking residual autocorrelation for cell09, nothing in the figure changed at print size (coefficient 0.205, stderr 0.047, n = 41). While re-exporting the raw traces for cell04, the ordering of cells was preserved (coefficient 0.301, stderr 0.012, n = 50). Worth noting for the writeup, though not a result on its own.

### Step 12: re-running with a tighter segmentation threshold

While segmenting epochs for cell10, the ordering of cells was preserved (coefficient 0.207, stderr 0.019, n = 44). While checking residual autocorrelation for cell17, two cells fell out of the usable range (coefficient 0.086, stderr 0.038, n = 41). While auditing the holding potential column for cell06, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.256, stderr 0.014, n = 58). While comparing per-cell orderings for cell04, the estimate moved less than one standard error (coefficient 0.259, stderr 0.019, n = 45). While fitting the one-lag kernel for cell12, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.108, stderr 0.032, n = 57). Flagging it so it does not get rediscovered next week.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell21    0.205  0.031   0.144  0.266  52        4000
cell01    0.083  0.012   0.060  0.106  40        500
cell20    0.274  0.020   0.235  0.314  43        4000
cell01    0.247  0.011   0.225  0.269  41        4000
cell08    0.220  0.011   0.198  0.242  56        4000
cell05    0.160  0.017   0.127  0.194  44        500
cell10    0.164  0.024   0.117  0.211  44        2000
cell10    0.162  0.028   0.107  0.217  58        4000
cell16    0.274  0.049   0.179  0.370  57        1000
cell15    0.108  0.018   0.072  0.144  53        500
cell20    0.155  0.027   0.101  0.208  40        2000
cell09    0.135  0.027   0.082  0.188  46        2000
cell06    0.204  0.039   0.127  0.280  45        2000
cell05    0.289  0.021   0.248  0.331  56        4000
```

While segmenting epochs for cell05, the estimate moved less than one standard error (coefficient 0.205, stderr 0.013, n = 43). While auditing the holding potential column for cell18, the CI narrowed by roughly a tenth (coefficient 0.150, stderr 0.040, n = 45). While auditing the holding potential column for cell18, the coefficient tracked epoch count more closely than duration (coefficient 0.168, stderr 0.034, n = 38). While bootstrapping the CI for cell11, the coefficient tracked epoch count more closely than duration (coefficient 0.187, stderr 0.043, n = 42). While bootstrapping the CI for cell16, two cells fell out of the usable range (coefficient 0.244, stderr 0.036, n = 40). While comparing per-cell orderings for cell15, the estimate moved less than one standard error (coefficient 0.174, stderr 0.015, n = 51).

### Step 13: re-exporting the raw traces

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell24    0.306  0.026   0.255  0.356  53        500
cell21    0.254  0.018   0.219  0.288  50        2000
cell15    0.232  0.036   0.161  0.303  51        4000
cell22    0.166  0.015   0.136  0.196  57        4000
cell20    0.179  0.029   0.122  0.237  40        4000
cell20    0.304  0.044   0.219  0.390  51        2000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell02    0.291  0.035   0.222  0.360  57        2000
cell10    0.243  0.011   0.222  0.265  40        4000
cell14    0.128  0.039   0.051  0.204  57        1000
cell16    0.094  0.042   0.012  0.177  38        2000
cell01    0.094  0.011   0.073  0.116  40        1000
cell19    0.169  0.018   0.134  0.204  39        500
cell04    0.181  0.021   0.140  0.221  48        1000
cell11    0.206  0.024   0.158  0.254  42        500
cell13    0.201  0.037   0.128  0.273  39        2000
cell05    0.146  0.041   0.065  0.226  57        1000
```

While checking residual autocorrelation for cell17, two cells fell out of the usable range (coefficient 0.133, stderr 0.047, n = 42). While segmenting epochs for cell05, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.258, stderr 0.035, n = 57). While segmenting epochs for cell20, the estimate moved less than one standard error (coefficient 0.122, stderr 0.035, n = 42). While bootstrapping the CI for cell16, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.171, stderr 0.021, n = 57). Worth noting for the writeup, though not a result on its own.

### Step 14: fitting the one-lag kernel

```python
coefs = fit_per_cell(rows, threshold=0.30)
lo, hi = ci(coefs, seed=43)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```python
coefs = fit_per_cell(rows, threshold=0.45)
lo, hi = ci(coefs, seed=79)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While checking residual autocorrelation for cell11, the estimate moved less than one standard error (coefficient 0.110, stderr 0.016, n = 51). While segmenting epochs for cell05, the coefficient tracked epoch count more closely than duration (coefficient 0.147, stderr 0.018, n = 40). While fitting the one-lag kernel for cell22, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.239, stderr 0.040, n = 55). While fitting the one-lag kernel for cell07, two cells fell out of the usable range (coefficient 0.180, stderr 0.023, n = 39). While auditing the holding potential column for cell23, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.127, stderr 0.034, n = 40). While re-running with a tighter segmentation threshold for cell19, the estimate moved less than one standard error (coefficient 0.283, stderr 0.018, n = 51).

### Step 15: re-running with a tighter segmentation threshold

While auditing the holding potential column for cell04, the ordering of cells was preserved (coefficient 0.155, stderr 0.033, n = 44). While checking residual autocorrelation for cell13, the CI narrowed by roughly a tenth (coefficient 0.218, stderr 0.018, n = 51). While fitting the one-lag kernel for cell22, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.200, stderr 0.019, n = 50). While auditing the holding potential column for cell19, the estimate moved less than one standard error (coefficient 0.281, stderr 0.050, n = 52). While fitting the one-lag kernel for cell04, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.218, stderr 0.033, n = 52). While checking residual autocorrelation for cell14, the coefficient tracked epoch count more closely than duration (coefficient 0.111, stderr 0.050, n = 39).

While re-running with a tighter segmentation threshold for cell10, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.151, stderr 0.011, n = 38). While re-exporting the raw traces for cell17, nothing in the figure changed at print size (coefficient 0.083, stderr 0.048, n = 52). While checking residual autocorrelation for cell01, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.256, stderr 0.011, n = 38). While fitting the one-lag kernel for cell09, the estimate moved less than one standard error (coefficient 0.279, stderr 0.034, n = 42). While checking residual autocorrelation for cell12, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.099, stderr 0.040, n = 48). While re-running with a tighter segmentation threshold for cell14, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.100, stderr 0.039, n = 40).

While re-running with a tighter segmentation threshold for cell15, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.099, stderr 0.049, n = 53). While re-running with a tighter segmentation threshold for cell01, the estimate moved less than one standard error (coefficient 0.227, stderr 0.018, n = 48). While segmenting epochs for cell20, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.250, stderr 0.023, n = 57). While segmenting epochs for cell10, the estimate moved less than one standard error (coefficient 0.119, stderr 0.026, n = 46). While re-running with a tighter segmentation threshold for cell04, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.204, stderr 0.024, n = 42). While bootstrapping the CI for cell22, the coefficient tracked epoch count more closely than duration (coefficient 0.262, stderr 0.048, n = 39).

While segmenting epochs for cell15, the ordering of cells was preserved (coefficient 0.175, stderr 0.031, n = 52). While re-running with a tighter segmentation threshold for cell24, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.185, stderr 0.018, n = 41). While re-exporting the raw traces for cell10, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.248, stderr 0.041, n = 48). While auditing the holding potential column for cell06, two cells fell out of the usable range (coefficient 0.103, stderr 0.048, n = 55). While checking residual autocorrelation for cell07, nothing in the figure changed at print size (coefficient 0.239, stderr 0.024, n = 46). Parking this until the re-segmentation lands.

### Step 16: fitting the one-lag kernel

While bootstrapping the CI for cell02, nothing in the figure changed at print size (coefficient 0.147, stderr 0.013, n = 38). While bootstrapping the CI for cell21, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.223, stderr 0.010, n = 43). While comparing per-cell orderings for cell02, the ordering of cells was preserved (coefficient 0.274, stderr 0.043, n = 45). While re-running with a tighter segmentation threshold for cell01, nothing in the figure changed at print size (coefficient 0.087, stderr 0.026, n = 47). Noted and moved on; it does not change the decision.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell18    0.140  0.025   0.090  0.190  44        4000
cell15    0.108  0.029   0.052  0.164  56        500
cell17    0.244  0.023   0.199  0.289  43        4000
cell23    0.163  0.036   0.093  0.234  38        2000
cell09    0.180  0.020   0.141  0.219  57        2000
cell01    0.105  0.029   0.048  0.161  45        1000
cell19    0.223  0.038   0.149  0.297  45        4000
cell24    0.124  0.031   0.064  0.185  40        1000
cell03    0.208  0.013   0.182  0.234  42        500
```

While comparing per-cell orderings for cell19, the CI narrowed by roughly a tenth (coefficient 0.091, stderr 0.028, n = 38). While fitting the one-lag kernel for cell08, the coefficient tracked epoch count more closely than duration (coefficient 0.168, stderr 0.015, n = 45). While auditing the holding potential column for cell24, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.210, stderr 0.017, n = 38).

```python
coefs = fit_per_cell(rows, threshold=0.65)
lo, hi = ci(coefs, seed=10)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 17: bootstrapping the CI

While auditing the holding potential column for cell21, the CI narrowed by roughly a tenth (coefficient 0.164, stderr 0.026, n = 55). While comparing per-cell orderings for cell02, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.206, stderr 0.032, n = 51). While re-running with a tighter segmentation threshold for cell16, the estimate moved less than one standard error (coefficient 0.158, stderr 0.020, n = 47). While fitting the one-lag kernel for cell23, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.242, stderr 0.030, n = 58). While fitting the one-lag kernel for cell11, the ordering of cells was preserved (coefficient 0.092, stderr 0.012, n = 38).

While re-running with a tighter segmentation threshold for cell06, the CI narrowed by roughly a tenth (coefficient 0.109, stderr 0.026, n = 45). While bootstrapping the CI for cell19, the coefficient tracked epoch count more closely than duration (coefficient 0.153, stderr 0.047, n = 39). While segmenting epochs for cell10, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.115, stderr 0.011, n = 47). While fitting the one-lag kernel for cell24, the CI narrowed by roughly a tenth (coefficient 0.294, stderr 0.032, n = 53). While bootstrapping the CI for cell06, the estimate moved less than one standard error (coefficient 0.197, stderr 0.044, n = 51). While re-exporting the raw traces for cell22, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.226, stderr 0.033, n = 44).

While re-running with a tighter segmentation threshold for cell16, nothing in the figure changed at print size (coefficient 0.307, stderr 0.028, n = 57). While checking residual autocorrelation for cell06, the CI narrowed by roughly a tenth (coefficient 0.226, stderr 0.050, n = 49). While segmenting epochs for cell12, nothing in the figure changed at print size (coefficient 0.232, stderr 0.021, n = 48). While fitting the one-lag kernel for cell05, the estimate moved less than one standard error (coefficient 0.241, stderr 0.025, n = 51).

While bootstrapping the CI for cell15, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.163, stderr 0.041, n = 58). While bootstrapping the CI for cell10, the coefficient tracked epoch count more closely than duration (coefficient 0.290, stderr 0.015, n = 40). While fitting the one-lag kernel for cell21, two cells fell out of the usable range (coefficient 0.307, stderr 0.038, n = 42). While re-exporting the raw traces for cell14, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.297, stderr 0.016, n = 46).

### Step 18: re-exporting the raw traces

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell09    0.179  0.037   0.107  0.252  55        500
cell07    0.255  0.048   0.161  0.349  45        1000
cell18    0.192  0.015   0.162  0.221  53        1000
cell08    0.213  0.043   0.130  0.297  46        1000
cell13    0.245  0.042   0.163  0.328  55        2000
cell01    0.125  0.043   0.040  0.210  44        500
cell13    0.216  0.035   0.147  0.285  44        1000
cell17    0.241  0.038   0.167  0.316  55        4000
cell08    0.119  0.043   0.035  0.203  52        500
cell16    0.097  0.012   0.073  0.121  46        500
cell07    0.300  0.022   0.257  0.343  48        500
cell23    0.160  0.017   0.127  0.192  51        4000
cell03    0.145  0.023   0.100  0.191  44        500
cell15    0.225  0.050   0.128  0.323  43        2000
```

While re-exporting the raw traces for cell10, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.243, stderr 0.017, n = 50). While auditing the holding potential column for cell23, the estimate moved less than one standard error (coefficient 0.279, stderr 0.044, n = 53). While fitting the one-lag kernel for cell14, two cells fell out of the usable range (coefficient 0.278, stderr 0.026, n = 49). While fitting the one-lag kernel for cell09, the coefficient tracked epoch count more closely than duration (coefficient 0.298, stderr 0.040, n = 40). While checking residual autocorrelation for cell09, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.238, stderr 0.034, n = 38).

While checking residual autocorrelation for cell12, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.135, stderr 0.021, n = 42). While bootstrapping the CI for cell20, the ordering of cells was preserved (coefficient 0.278, stderr 0.048, n = 44). While re-exporting the raw traces for cell09, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.304, stderr 0.044, n = 48). While fitting the one-lag kernel for cell03, the ordering of cells was preserved (coefficient 0.302, stderr 0.048, n = 43). While fitting the one-lag kernel for cell23, the coefficient tracked epoch count more closely than duration (coefficient 0.260, stderr 0.040, n = 53). While comparing per-cell orderings for cell22, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.249, stderr 0.040, n = 50). This is the part that will need a real statistical argument.

### Step 19: re-exporting the raw traces

While bootstrapping the CI for cell09, the coefficient tracked epoch count more closely than duration (coefficient 0.141, stderr 0.041, n = 57). While re-running with a tighter segmentation threshold for cell08, nothing in the figure changed at print size (coefficient 0.232, stderr 0.014, n = 51). While auditing the holding potential column for cell23, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.137, stderr 0.034, n = 57). While re-running with a tighter segmentation threshold for cell12, the CI narrowed by roughly a tenth (coefficient 0.114, stderr 0.032, n = 38).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell14    0.148  0.027   0.095  0.201  58        1000
cell03    0.138  0.017   0.103  0.172  58        2000
cell19    0.299  0.015   0.270  0.328  41        4000
cell03    0.283  0.040   0.205  0.361  51        1000
cell21    0.267  0.043   0.183  0.350  48        4000
cell02    0.303  0.048   0.209  0.397  50        4000
cell21    0.158  0.010   0.137  0.178  50        2000
cell22    0.258  0.039   0.181  0.335  53        4000
```

While fitting the one-lag kernel for cell23, the estimate moved less than one standard error (coefficient 0.157, stderr 0.039, n = 49). While segmenting epochs for cell22, nothing in the figure changed at print size (coefficient 0.125, stderr 0.043, n = 40). While comparing per-cell orderings for cell13, nothing in the figure changed at print size (coefficient 0.089, stderr 0.014, n = 56). While fitting the one-lag kernel for cell12, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.171, stderr 0.047, n = 44).

While checking residual autocorrelation for cell23, two cells fell out of the usable range (coefficient 0.273, stderr 0.049, n = 48). While re-exporting the raw traces for cell15, the ordering of cells was preserved (coefficient 0.284, stderr 0.012, n = 56). While re-exporting the raw traces for cell13, the estimate moved less than one standard error (coefficient 0.142, stderr 0.018, n = 48). While checking residual autocorrelation for cell03, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.119, stderr 0.013, n = 52). While segmenting epochs for cell05, the estimate moved less than one standard error (coefficient 0.165, stderr 0.027, n = 56).

### Step 20: fitting the one-lag kernel

```python
coefs = fit_per_cell(rows, threshold=0.65)
lo, hi = ci(coefs, seed=67)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell16    0.252  0.022   0.209  0.295  54        2000
cell02    0.108  0.031   0.048  0.168  45        2000
cell06    0.254  0.025   0.205  0.304  48        4000
cell18    0.104  0.017   0.072  0.137  46        500
cell05    0.153  0.049   0.056  0.250  55        4000
cell22    0.282  0.038   0.207  0.357  45        1000
cell24    0.256  0.044   0.169  0.342  46        500
cell04    0.220  0.038   0.146  0.294  44        500
cell16    0.171  0.043   0.086  0.255  56        1000
cell19    0.128  0.019   0.091  0.164  39        500
cell04    0.273  0.010   0.253  0.293  52        2000
cell15    0.259  0.022   0.215  0.302  47        1000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell24    0.207  0.021   0.165  0.249  48        2000
cell04    0.206  0.049   0.111  0.302  44        1000
cell17    0.184  0.025   0.134  0.234  51        4000
cell08    0.186  0.045   0.098  0.274  40        500
cell20    0.184  0.049   0.087  0.281  52        1000
cell19    0.244  0.018   0.209  0.278  53        2000
cell16    0.200  0.042   0.119  0.282  43        2000
cell16    0.095  0.025   0.045  0.145  42        2000
cell14    0.111  0.043   0.025  0.196  41        2000
cell03    0.103  0.019   0.065  0.141  56        1000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell24    0.145  0.028   0.090  0.201  49        500
cell12    0.252  0.024   0.206  0.298  40        500
cell03    0.085  0.035   0.016  0.154  56        4000
cell03    0.161  0.029   0.105  0.218  42        500
cell15    0.176  0.021   0.135  0.218  49        500
cell22    0.104  0.035   0.035  0.172  56        4000
cell17    0.147  0.032   0.085  0.209  51        500
```

### Step 21: fitting the one-lag kernel

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell19    0.252  0.040   0.172  0.331  44        1000
cell07    0.308  0.010   0.288  0.328  44        4000
cell17    0.088  0.049   -0.007  0.184  52        500
cell19    0.176  0.041   0.096  0.256  48        1000
cell19    0.237  0.014   0.210  0.264  42        1000
cell01    0.310  0.023   0.265  0.355  41        500
cell16    0.280  0.028   0.226  0.334  50        2000
cell14    0.276  0.042   0.194  0.357  55        2000
cell02    0.175  0.022   0.132  0.219  58        1000
cell03    0.100  0.017   0.067  0.134  49        1000
cell15    0.287  0.043   0.202  0.372  39        1000
cell24    0.296  0.042   0.212  0.379  41        4000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell01    0.257  0.033   0.194  0.321  53        500
cell17    0.083  0.035   0.014  0.152  40        500
cell10    0.295  0.038   0.221  0.369  42        500
cell17    0.218  0.034   0.151  0.284  38        1000
cell19    0.089  0.042   0.006  0.172  57        2000
cell17    0.158  0.045   0.070  0.246  45        500
cell10    0.121  0.014   0.092  0.149  47        500
cell18    0.216  0.032   0.152  0.279  51        2000
cell06    0.160  0.020   0.121  0.198  50        1000
```

While comparing per-cell orderings for cell07, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.209, stderr 0.033, n = 53). While comparing per-cell orderings for cell09, nothing in the figure changed at print size (coefficient 0.107, stderr 0.041, n = 51). While re-running with a tighter segmentation threshold for cell24, the estimate moved less than one standard error (coefficient 0.116, stderr 0.027, n = 45). While re-running with a tighter segmentation threshold for cell15, the ordering of cells was preserved (coefficient 0.190, stderr 0.046, n = 42). While bootstrapping the CI for cell02, the estimate moved less than one standard error (coefficient 0.245, stderr 0.034, n = 52). While re-exporting the raw traces for cell13, the ordering of cells was preserved (coefficient 0.290, stderr 0.049, n = 58). Worth noting for the writeup, though not a result on its own.

### Step 22: fitting the one-lag kernel

While checking residual autocorrelation for cell15, the coefficient tracked epoch count more closely than duration (coefficient 0.207, stderr 0.038, n = 46). While segmenting epochs for cell19, two cells fell out of the usable range (coefficient 0.164, stderr 0.032, n = 39). While re-exporting the raw traces for cell17, the CI narrowed by roughly a tenth (coefficient 0.180, stderr 0.036, n = 44). While bootstrapping the CI for cell16, the ordering of cells was preserved (coefficient 0.254, stderr 0.023, n = 50). While segmenting epochs for cell12, the CI narrowed by roughly a tenth (coefficient 0.162, stderr 0.045, n = 42). Noted and moved on; it does not change the decision.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell05    0.133  0.031   0.072  0.194  48        500
cell17    0.102  0.027   0.049  0.154  48        2000
cell09    0.276  0.026   0.226  0.327  45        1000
cell04    0.197  0.037   0.125  0.269  47        500
cell13    0.083  0.024   0.037  0.130  38        1000
cell14    0.098  0.025   0.049  0.147  48        1000
cell03    0.083  0.037   0.011  0.155  42        500
```

While segmenting epochs for cell13, the CI narrowed by roughly a tenth (coefficient 0.264, stderr 0.042, n = 53). While checking residual autocorrelation for cell11, the coefficient tracked epoch count more closely than duration (coefficient 0.306, stderr 0.023, n = 39). While segmenting epochs for cell02, the coefficient tracked epoch count more closely than duration (coefficient 0.278, stderr 0.047, n = 43). While re-running with a tighter segmentation threshold for cell12, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.163, stderr 0.018, n = 54). While comparing per-cell orderings for cell22, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.136, stderr 0.021, n = 56). While comparing per-cell orderings for cell13, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.258, stderr 0.024, n = 50).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell08    0.155  0.014   0.129  0.182  39        1000
cell15    0.189  0.045   0.100  0.278  38        1000
cell08    0.287  0.018   0.251  0.322  38        1000
cell07    0.162  0.036   0.092  0.232  52        500
cell20    0.139  0.022   0.095  0.182  41        1000
cell10    0.294  0.027   0.241  0.347  52        500
cell17    0.181  0.047   0.089  0.273  45        2000
cell11    0.237  0.031   0.176  0.298  49        4000
```

### Step 23: bootstrapping the CI

While checking residual autocorrelation for cell12, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.226, stderr 0.045, n = 58). While segmenting epochs for cell24, two cells fell out of the usable range (coefficient 0.099, stderr 0.013, n = 40). While auditing the holding potential column for cell15, the estimate moved less than one standard error (coefficient 0.189, stderr 0.038, n = 43). While fitting the one-lag kernel for cell06, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.137, stderr 0.022, n = 46). While re-exporting the raw traces for cell03, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.111, stderr 0.018, n = 39). While auditing the holding potential column for cell13, two cells fell out of the usable range (coefficient 0.111, stderr 0.044, n = 48).

While comparing per-cell orderings for cell12, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.149, stderr 0.024, n = 50). While segmenting epochs for cell15, the coefficient tracked epoch count more closely than duration (coefficient 0.102, stderr 0.034, n = 44). While bootstrapping the CI for cell08, nothing in the figure changed at print size (coefficient 0.110, stderr 0.040, n = 54). While fitting the one-lag kernel for cell20, nothing in the figure changed at print size (coefficient 0.091, stderr 0.029, n = 45). While comparing per-cell orderings for cell23, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.089, stderr 0.014, n = 41). While auditing the holding potential column for cell01, the CI narrowed by roughly a tenth (coefficient 0.095, stderr 0.037, n = 41).

While segmenting epochs for cell06, two cells fell out of the usable range (coefficient 0.158, stderr 0.037, n = 54). While fitting the one-lag kernel for cell22, two cells fell out of the usable range (coefficient 0.301, stderr 0.040, n = 38). While fitting the one-lag kernel for cell15, the ordering of cells was preserved (coefficient 0.208, stderr 0.028, n = 58). While re-running with a tighter segmentation threshold for cell10, the coefficient tracked epoch count more closely than duration (coefficient 0.204, stderr 0.019, n = 42). Parking this until the re-segmentation lands.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell03    0.183  0.048   0.089  0.277  41        500
cell03    0.167  0.033   0.102  0.232  42        1000
cell04    0.281  0.018   0.246  0.316  45        1000
cell16    0.265  0.014   0.238  0.292  38        2000
cell14    0.162  0.021   0.121  0.203  46        1000
cell01    0.152  0.038   0.077  0.227  38        4000
cell17    0.165  0.041   0.084  0.246  56        1000
cell02    0.221  0.013   0.195  0.246  38        500
cell24    0.287  0.035   0.219  0.355  51        1000
cell23    0.176  0.045   0.088  0.265  55        4000
cell23    0.123  0.018   0.087  0.159  50        1000
```

### Step 24: auditing the holding potential column

While re-running with a tighter segmentation threshold for cell23, the CI narrowed by roughly a tenth (coefficient 0.156, stderr 0.028, n = 41). While comparing per-cell orderings for cell13, the coefficient tracked epoch count more closely than duration (coefficient 0.149, stderr 0.034, n = 57). While segmenting epochs for cell03, the coefficient tracked epoch count more closely than duration (coefficient 0.203, stderr 0.021, n = 46). While comparing per-cell orderings for cell01, the ordering of cells was preserved (coefficient 0.083, stderr 0.011, n = 54). While comparing per-cell orderings for cell03, two cells fell out of the usable range (coefficient 0.163, stderr 0.028, n = 47). Noted and moved on; it does not change the decision.

While auditing the holding potential column for cell02, the ordering of cells was preserved (coefficient 0.208, stderr 0.036, n = 49). While checking residual autocorrelation for cell06, nothing in the figure changed at print size (coefficient 0.278, stderr 0.027, n = 40). While re-exporting the raw traces for cell05, the coefficient tracked epoch count more closely than duration (coefficient 0.111, stderr 0.035, n = 53). While auditing the holding potential column for cell17, the CI narrowed by roughly a tenth (coefficient 0.193, stderr 0.024, n = 40). While bootstrapping the CI for cell22, the coefficient tracked epoch count more closely than duration (coefficient 0.215, stderr 0.035, n = 57). While fitting the one-lag kernel for cell10, nothing in the figure changed at print size (coefficient 0.245, stderr 0.018, n = 45). This is the part that will need a real statistical argument.

While re-running with a tighter segmentation threshold for cell10, nothing in the figure changed at print size (coefficient 0.206, stderr 0.040, n = 50). While fitting the one-lag kernel for cell04, nothing in the figure changed at print size (coefficient 0.263, stderr 0.016, n = 50). While checking residual autocorrelation for cell01, the ordering of cells was preserved (coefficient 0.106, stderr 0.042, n = 58). While comparing per-cell orderings for cell20, the ordering of cells was preserved (coefficient 0.176, stderr 0.021, n = 49). While re-exporting the raw traces for cell13, the ordering of cells was preserved (coefficient 0.133, stderr 0.020, n = 38).

While auditing the holding potential column for cell21, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.245, stderr 0.030, n = 56). While auditing the holding potential column for cell08, two cells fell out of the usable range (coefficient 0.225, stderr 0.039, n = 41). While re-running with a tighter segmentation threshold for cell20, the ordering of cells was preserved (coefficient 0.164, stderr 0.044, n = 58). While re-running with a tighter segmentation threshold for cell06, nothing in the figure changed at print size (coefficient 0.224, stderr 0.048, n = 46). Worth noting for the writeup, though not a result on its own.

### Step 25: comparing per-cell orderings

```python
coefs = fit_per_cell(rows, threshold=0.32)
lo, hi = ci(coefs, seed=80)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell04    0.224  0.037   0.150  0.297  49        500
cell05    0.174  0.024   0.127  0.221  51        1000
cell12    0.190  0.015   0.160  0.219  45        500
cell02    0.159  0.038   0.086  0.233  52        1000
cell14    0.112  0.045   0.025  0.200  55        2000
cell04    0.188  0.029   0.131  0.244  39        2000
cell01    0.309  0.016   0.277  0.341  49        2000
cell06    0.281  0.024   0.235  0.327  51        500
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell24    0.215  0.041   0.135  0.295  39        2000
cell22    0.207  0.039   0.130  0.284  52        2000
cell10    0.148  0.027   0.096  0.200  47        500
cell14    0.125  0.041   0.045  0.206  38        500
cell04    0.188  0.032   0.124  0.252  42        1000
cell21    0.300  0.031   0.239  0.361  52        4000
cell21    0.081  0.027   0.029  0.134  51        4000
cell05    0.229  0.025   0.180  0.277  38        2000
cell01    0.254  0.012   0.231  0.276  41        4000
cell14    0.144  0.043   0.060  0.228  48        2000
cell14    0.165  0.017   0.131  0.199  43        4000
cell10    0.220  0.043   0.136  0.305  39        4000
cell03    0.301  0.049   0.205  0.396  56        4000
cell03    0.141  0.018   0.105  0.176  50        500
```

### Step 26: comparing per-cell orderings

While checking residual autocorrelation for cell09, the CI narrowed by roughly a tenth (coefficient 0.263, stderr 0.015, n = 43). While auditing the holding potential column for cell01, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.295, stderr 0.039, n = 47). While comparing per-cell orderings for cell12, two cells fell out of the usable range (coefficient 0.234, stderr 0.034, n = 57). While auditing the holding potential column for cell20, the ordering of cells was preserved (coefficient 0.206, stderr 0.032, n = 47).

While bootstrapping the CI for cell12, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.257, stderr 0.045, n = 45). While bootstrapping the CI for cell06, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.228, stderr 0.044, n = 52). While bootstrapping the CI for cell15, the CI narrowed by roughly a tenth (coefficient 0.292, stderr 0.039, n = 54). While checking residual autocorrelation for cell15, two cells fell out of the usable range (coefficient 0.225, stderr 0.014, n = 47).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell24    0.271  0.046   0.181  0.360  42        500
cell09    0.143  0.033   0.078  0.208  49        4000
cell03    0.283  0.030   0.224  0.342  54        500
cell17    0.202  0.036   0.131  0.273  52        4000
cell19    0.109  0.041   0.029  0.189  56        500
cell03    0.151  0.029   0.094  0.208  48        4000
cell23    0.139  0.038   0.064  0.214  46        4000
cell20    0.231  0.034   0.164  0.298  50        2000
cell09    0.152  0.016   0.120  0.184  51        2000
cell03    0.306  0.038   0.231  0.381  57        4000
cell24    0.189  0.012   0.165  0.212  51        2000
cell18    0.285  0.015   0.256  0.315  51        1000
```

### Step 27: fitting the one-lag kernel

While re-exporting the raw traces for cell02, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.267, stderr 0.031, n = 57). While checking residual autocorrelation for cell21, two cells fell out of the usable range (coefficient 0.110, stderr 0.027, n = 47). While auditing the holding potential column for cell24, nothing in the figure changed at print size (coefficient 0.170, stderr 0.031, n = 56). While segmenting epochs for cell15, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.243, stderr 0.036, n = 52).

While fitting the one-lag kernel for cell02, the CI narrowed by roughly a tenth (coefficient 0.238, stderr 0.028, n = 55). While checking residual autocorrelation for cell20, the ordering of cells was preserved (coefficient 0.222, stderr 0.022, n = 42). While checking residual autocorrelation for cell06, the CI narrowed by roughly a tenth (coefficient 0.304, stderr 0.039, n = 50). While checking residual autocorrelation for cell07, nothing in the figure changed at print size (coefficient 0.182, stderr 0.031, n = 54). While fitting the one-lag kernel for cell02, two cells fell out of the usable range (coefficient 0.179, stderr 0.012, n = 50). While re-running with a tighter segmentation threshold for cell23, nothing in the figure changed at print size (coefficient 0.164, stderr 0.020, n = 54).

While comparing per-cell orderings for cell16, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.217, stderr 0.048, n = 43). While auditing the holding potential column for cell04, nothing in the figure changed at print size (coefficient 0.215, stderr 0.021, n = 45). While checking residual autocorrelation for cell03, the CI narrowed by roughly a tenth (coefficient 0.241, stderr 0.013, n = 39). While segmenting epochs for cell16, nothing in the figure changed at print size (coefficient 0.243, stderr 0.015, n = 47). While comparing per-cell orderings for cell05, two cells fell out of the usable range (coefficient 0.206, stderr 0.040, n = 45). While comparing per-cell orderings for cell06, nothing in the figure changed at print size (coefficient 0.170, stderr 0.047, n = 39).

While checking residual autocorrelation for cell18, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.114, stderr 0.038, n = 47). While auditing the holding potential column for cell10, the estimate moved less than one standard error (coefficient 0.227, stderr 0.040, n = 43). While checking residual autocorrelation for cell15, the coefficient tracked epoch count more closely than duration (coefficient 0.210, stderr 0.024, n = 43). While fitting the one-lag kernel for cell22, the coefficient tracked epoch count more closely than duration (coefficient 0.165, stderr 0.028, n = 42). While checking residual autocorrelation for cell18, the CI narrowed by roughly a tenth (coefficient 0.098, stderr 0.037, n = 53). Parking this until the re-segmentation lands.

### Step 28: bootstrapping the CI

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell10    0.240  0.021   0.198  0.281  50        1000
cell20    0.272  0.042   0.189  0.355  45        4000
cell17    0.185  0.016   0.154  0.216  41        1000
cell17    0.260  0.015   0.231  0.289  38        2000
cell12    0.285  0.024   0.238  0.332  38        1000
cell02    0.132  0.049   0.037  0.227  55        500
cell03    0.208  0.043   0.123  0.293  44        2000
cell03    0.089  0.017   0.055  0.122  57        4000
cell12    0.097  0.011   0.076  0.119  55        4000
cell08    0.265  0.018   0.230  0.300  54        1000
```

While auditing the holding potential column for cell19, the coefficient tracked epoch count more closely than duration (coefficient 0.296, stderr 0.011, n = 49). While checking residual autocorrelation for cell23, the estimate moved less than one standard error (coefficient 0.236, stderr 0.041, n = 46). While re-exporting the raw traces for cell13, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.108, stderr 0.011, n = 51). While checking residual autocorrelation for cell01, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.136, stderr 0.021, n = 38). While checking residual autocorrelation for cell09, the estimate moved less than one standard error (coefficient 0.246, stderr 0.012, n = 58). This is the part that will need a real statistical argument.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell10    0.153  0.015   0.124  0.182  44        2000
cell06    0.111  0.029   0.054  0.169  54        2000
cell03    0.231  0.037   0.159  0.303  46        2000
cell19    0.267  0.020   0.228  0.305  56        500
cell20    0.111  0.037   0.039  0.184  44        4000
cell13    0.237  0.037   0.163  0.310  57        4000
cell19    0.145  0.039   0.068  0.222  48        500
cell13    0.228  0.043   0.144  0.312  38        2000
cell18    0.088  0.026   0.037  0.139  45        1000
```

While fitting the one-lag kernel for cell16, the ordering of cells was preserved (coefficient 0.294, stderr 0.027, n = 58). While checking residual autocorrelation for cell09, the estimate moved less than one standard error (coefficient 0.119, stderr 0.022, n = 46). While fitting the one-lag kernel for cell17, the CI narrowed by roughly a tenth (coefficient 0.226, stderr 0.026, n = 39). While re-exporting the raw traces for cell04, the estimate moved less than one standard error (coefficient 0.149, stderr 0.028, n = 51). While re-exporting the raw traces for cell17, the ordering of cells was preserved (coefficient 0.180, stderr 0.017, n = 38). While re-running with a tighter segmentation threshold for cell09, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.170, stderr 0.047, n = 51). Noted and moved on; it does not change the decision.

### Step 29: fitting the one-lag kernel

While re-running with a tighter segmentation threshold for cell04, the ordering of cells was preserved (coefficient 0.112, stderr 0.017, n = 41). While fitting the one-lag kernel for cell01, two cells fell out of the usable range (coefficient 0.131, stderr 0.023, n = 48). While auditing the holding potential column for cell16, the CI narrowed by roughly a tenth (coefficient 0.141, stderr 0.048, n = 43). While re-exporting the raw traces for cell04, nothing in the figure changed at print size (coefficient 0.096, stderr 0.043, n = 54). While fitting the one-lag kernel for cell11, the estimate moved less than one standard error (coefficient 0.221, stderr 0.038, n = 47).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell11    0.160  0.026   0.109  0.212  58        2000
cell21    0.291  0.022   0.247  0.335  46        1000
cell01    0.217  0.026   0.167  0.267  41        500
cell11    0.082  0.032   0.018  0.145  58        500
cell11    0.185  0.048   0.090  0.280  57        2000
cell02    0.278  0.027   0.225  0.331  39        500
cell14    0.281  0.036   0.210  0.352  48        1000
cell15    0.137  0.023   0.092  0.182  54        500
cell13    0.159  0.021   0.118  0.199  40        1000
cell06    0.170  0.019   0.133  0.208  54        1000
```

### Step 30: fitting the one-lag kernel

While fitting the one-lag kernel for cell10, the ordering of cells was preserved (coefficient 0.200, stderr 0.047, n = 53). While fitting the one-lag kernel for cell06, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.174, stderr 0.029, n = 55). While re-exporting the raw traces for cell19, two cells fell out of the usable range (coefficient 0.104, stderr 0.015, n = 38). While checking residual autocorrelation for cell19, two cells fell out of the usable range (coefficient 0.287, stderr 0.042, n = 46). While re-running with a tighter segmentation threshold for cell22, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.215, stderr 0.024, n = 47). While re-exporting the raw traces for cell19, the coefficient tracked epoch count more closely than duration (coefficient 0.173, stderr 0.024, n = 52).

```python
coefs = fit_per_cell(rows, threshold=0.32)
lo, hi = ci(coefs, seed=17)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```python
coefs = fit_per_cell(rows, threshold=0.59)
lo, hi = ci(coefs, seed=79)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 31: auditing the holding potential column

While re-exporting the raw traces for cell06, nothing in the figure changed at print size (coefficient 0.286, stderr 0.016, n = 58). While segmenting epochs for cell05, nothing in the figure changed at print size (coefficient 0.234, stderr 0.047, n = 52). While auditing the holding potential column for cell06, nothing in the figure changed at print size (coefficient 0.272, stderr 0.036, n = 45). While auditing the holding potential column for cell18, the ordering of cells was preserved (coefficient 0.164, stderr 0.013, n = 56). While auditing the holding potential column for cell17, two cells fell out of the usable range (coefficient 0.188, stderr 0.018, n = 39).

While comparing per-cell orderings for cell12, the ordering of cells was preserved (coefficient 0.295, stderr 0.020, n = 50). While auditing the holding potential column for cell19, the coefficient tracked epoch count more closely than duration (coefficient 0.172, stderr 0.036, n = 56). While re-running with a tighter segmentation threshold for cell15, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.185, stderr 0.042, n = 45). While auditing the holding potential column for cell01, two cells fell out of the usable range (coefficient 0.284, stderr 0.018, n = 48). While checking residual autocorrelation for cell05, the CI narrowed by roughly a tenth (coefficient 0.202, stderr 0.032, n = 41).

While re-exporting the raw traces for cell03, the CI narrowed by roughly a tenth (coefficient 0.171, stderr 0.024, n = 43). While re-running with a tighter segmentation threshold for cell08, the estimate moved less than one standard error (coefficient 0.206, stderr 0.021, n = 56). While fitting the one-lag kernel for cell12, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.238, stderr 0.028, n = 49). While bootstrapping the CI for cell17, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.273, stderr 0.023, n = 42). While re-exporting the raw traces for cell01, nothing in the figure changed at print size (coefficient 0.080, stderr 0.046, n = 41). While segmenting epochs for cell24, nothing in the figure changed at print size (coefficient 0.123, stderr 0.025, n = 47).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell15    0.247  0.050   0.150  0.345  58        500
cell14    0.207  0.034   0.140  0.273  47        500
cell03    0.140  0.026   0.090  0.190  43        2000
cell11    0.099  0.030   0.039  0.158  42        4000
cell14    0.236  0.050   0.139  0.334  49        1000
cell13    0.092  0.015   0.062  0.122  56        1000
cell13    0.146  0.026   0.096  0.197  52        500
cell06    0.205  0.013   0.180  0.229  47        1000
cell18    0.182  0.027   0.129  0.235  47        4000
cell18    0.159  0.033   0.094  0.224  53        500
cell16    0.170  0.014   0.143  0.197  39        1000
cell15    0.176  0.016   0.145  0.206  45        2000
cell01    0.145  0.024   0.097  0.192  38        500
cell12    0.303  0.029   0.247  0.360  53        4000
```

### Step 32: checking residual autocorrelation

While re-exporting the raw traces for cell06, the CI narrowed by roughly a tenth (coefficient 0.127, stderr 0.035, n = 45). While fitting the one-lag kernel for cell21, the estimate moved less than one standard error (coefficient 0.128, stderr 0.022, n = 43). While comparing per-cell orderings for cell24, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.162, stderr 0.023, n = 48). Flagging it so it does not get rediscovered next week.

While re-running with a tighter segmentation threshold for cell10, the coefficient tracked epoch count more closely than duration (coefficient 0.294, stderr 0.013, n = 50). While segmenting epochs for cell18, the CI narrowed by roughly a tenth (coefficient 0.134, stderr 0.026, n = 55). While checking residual autocorrelation for cell04, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.097, stderr 0.050, n = 52). While bootstrapping the CI for cell17, the ordering of cells was preserved (coefficient 0.290, stderr 0.033, n = 38). While checking residual autocorrelation for cell21, nothing in the figure changed at print size (coefficient 0.222, stderr 0.031, n = 50). While fitting the one-lag kernel for cell23, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.241, stderr 0.019, n = 38).

```python
coefs = fit_per_cell(rows, threshold=0.70)
lo, hi = ci(coefs, seed=34)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 33: re-exporting the raw traces

While re-running with a tighter segmentation threshold for cell07, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.250, stderr 0.014, n = 54). While re-exporting the raw traces for cell12, the CI narrowed by roughly a tenth (coefficient 0.086, stderr 0.033, n = 46). While re-exporting the raw traces for cell24, the ordering of cells was preserved (coefficient 0.210, stderr 0.026, n = 41). While checking residual autocorrelation for cell15, nothing in the figure changed at print size (coefficient 0.172, stderr 0.048, n = 52). While fitting the one-lag kernel for cell05, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.134, stderr 0.025, n = 53). While segmenting epochs for cell02, the estimate moved less than one standard error (coefficient 0.197, stderr 0.015, n = 52). This is the part that will need a real statistical argument.

While re-exporting the raw traces for cell10, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.213, stderr 0.033, n = 39). While segmenting epochs for cell09, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.177, stderr 0.030, n = 48). While re-exporting the raw traces for cell11, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.119, stderr 0.041, n = 43). While re-exporting the raw traces for cell18, the coefficient tracked epoch count more closely than duration (coefficient 0.240, stderr 0.024, n = 51). While auditing the holding potential column for cell21, the estimate moved less than one standard error (coefficient 0.102, stderr 0.040, n = 56).

### Step 34: checking residual autocorrelation

```python
coefs = fit_per_cell(rows, threshold=0.57)
lo, hi = ci(coefs, seed=48)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```python
coefs = fit_per_cell(rows, threshold=0.63)
lo, hi = ci(coefs, seed=4)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 35: fitting the one-lag kernel

While checking residual autocorrelation for cell15, nothing in the figure changed at print size (coefficient 0.081, stderr 0.044, n = 55). While bootstrapping the CI for cell16, two cells fell out of the usable range (coefficient 0.162, stderr 0.022, n = 58). While bootstrapping the CI for cell04, nothing in the figure changed at print size (coefficient 0.141, stderr 0.038, n = 44). While checking residual autocorrelation for cell18, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.253, stderr 0.040, n = 42). While auditing the holding potential column for cell23, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.272, stderr 0.022, n = 39). While auditing the holding potential column for cell17, the CI narrowed by roughly a tenth (coefficient 0.113, stderr 0.044, n = 50).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell20    0.103  0.032   0.040  0.166  42        500
cell13    0.197  0.016   0.167  0.228  52        4000
cell05    0.103  0.026   0.052  0.154  53        2000
cell24    0.200  0.032   0.137  0.263  53        2000
cell21    0.269  0.014   0.241  0.297  50        1000
cell10    0.273  0.019   0.236  0.310  42        4000
cell07    0.205  0.029   0.148  0.262  40        1000
cell15    0.202  0.015   0.174  0.231  58        1000
```

While checking residual autocorrelation for cell10, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.212, stderr 0.034, n = 56). While checking residual autocorrelation for cell10, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.118, stderr 0.027, n = 41). While comparing per-cell orderings for cell20, the ordering of cells was preserved (coefficient 0.135, stderr 0.039, n = 52). Parking this until the re-segmentation lands.

### Step 36: re-exporting the raw traces

While re-running with a tighter segmentation threshold for cell16, the coefficient tracked epoch count more closely than duration (coefficient 0.087, stderr 0.020, n = 40). While auditing the holding potential column for cell10, nothing in the figure changed at print size (coefficient 0.082, stderr 0.032, n = 39). While comparing per-cell orderings for cell10, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.093, stderr 0.046, n = 44). While fitting the one-lag kernel for cell05, the CI narrowed by roughly a tenth (coefficient 0.283, stderr 0.045, n = 52). While re-running with a tighter segmentation threshold for cell04, nothing in the figure changed at print size (coefficient 0.166, stderr 0.039, n = 48). Flagging it so it does not get rediscovered next week.

While bootstrapping the CI for cell23, nothing in the figure changed at print size (coefficient 0.183, stderr 0.031, n = 55). While checking residual autocorrelation for cell01, the ordering of cells was preserved (coefficient 0.108, stderr 0.046, n = 38). While bootstrapping the CI for cell04, the estimate moved less than one standard error (coefficient 0.178, stderr 0.035, n = 56). While comparing per-cell orderings for cell13, the coefficient tracked epoch count more closely than duration (coefficient 0.128, stderr 0.036, n = 46). While auditing the holding potential column for cell01, the estimate moved less than one standard error (coefficient 0.134, stderr 0.043, n = 52).

While fitting the one-lag kernel for cell10, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.266, stderr 0.032, n = 48). While segmenting epochs for cell20, the ordering of cells was preserved (coefficient 0.179, stderr 0.032, n = 48). While comparing per-cell orderings for cell24, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.289, stderr 0.022, n = 41). Noted and moved on; it does not change the decision.

While segmenting epochs for cell20, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.157, stderr 0.020, n = 39). While bootstrapping the CI for cell21, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.229, stderr 0.027, n = 49). While comparing per-cell orderings for cell22, two cells fell out of the usable range (coefficient 0.295, stderr 0.024, n = 38). While checking residual autocorrelation for cell08, the estimate moved less than one standard error (coefficient 0.220, stderr 0.049, n = 58). While bootstrapping the CI for cell14, the ordering of cells was preserved (coefficient 0.224, stderr 0.027, n = 52).

