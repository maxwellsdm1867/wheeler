# Prior session 1 of 2

Transcript of an earlier working session on the history-kernel analysis.

### Step 1: segmenting epochs

While fitting the one-lag kernel for cell14, nothing in the figure changed at print size (coefficient 0.287, stderr 0.036, n = 45). While segmenting epochs for cell15, nothing in the figure changed at print size (coefficient 0.287, stderr 0.024, n = 51). While re-exporting the raw traces for cell16, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.124, stderr 0.046, n = 56). While bootstrapping the CI for cell02, the estimate moved less than one standard error (coefficient 0.290, stderr 0.044, n = 50). While comparing per-cell orderings for cell13, the CI narrowed by roughly a tenth (coefficient 0.113, stderr 0.039, n = 42). While fitting the one-lag kernel for cell24, the CI narrowed by roughly a tenth (coefficient 0.190, stderr 0.035, n = 43).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell10    0.144  0.047   0.052  0.236  49        500
cell17    0.183  0.030   0.124  0.241  56        4000
cell13    0.207  0.021   0.165  0.249  40        1000
cell04    0.108  0.018   0.073  0.143  39        500
cell14    0.294  0.024   0.246  0.342  44        1000
cell18    0.308  0.021   0.268  0.348  55        2000
cell02    0.251  0.049   0.154  0.348  46        1000
cell04    0.246  0.016   0.215  0.277  40        1000
```

### Step 2: bootstrapping the CI

```python
coefs = fit_per_cell(rows, threshold=0.33)
lo, hi = ci(coefs, seed=59)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While fitting the one-lag kernel for cell14, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.299, stderr 0.039, n = 49). While bootstrapping the CI for cell24, two cells fell out of the usable range (coefficient 0.203, stderr 0.024, n = 42). While segmenting epochs for cell13, two cells fell out of the usable range (coefficient 0.298, stderr 0.036, n = 50). While re-running with a tighter segmentation threshold for cell24, the estimate moved less than one standard error (coefficient 0.147, stderr 0.013, n = 58). While bootstrapping the CI for cell15, the CI narrowed by roughly a tenth (coefficient 0.305, stderr 0.043, n = 44).

### Step 3: re-running with a tighter segmentation threshold

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell21    0.232  0.046   0.142  0.322  58        500
cell09    0.217  0.017   0.183  0.250  39        4000
cell17    0.219  0.029   0.162  0.275  47        2000
cell06    0.296  0.042   0.213  0.378  43        4000
cell01    0.222  0.046   0.131  0.313  55        500
cell07    0.283  0.030   0.224  0.342  41        4000
cell14    0.091  0.045   0.002  0.180  39        4000
cell18    0.121  0.013   0.096  0.146  53        2000
```

While fitting the one-lag kernel for cell01, the estimate moved less than one standard error (coefficient 0.293, stderr 0.045, n = 47). While re-exporting the raw traces for cell07, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.130, stderr 0.035, n = 46). While fitting the one-lag kernel for cell03, two cells fell out of the usable range (coefficient 0.296, stderr 0.049, n = 52). While auditing the holding potential column for cell09, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.267, stderr 0.026, n = 40). While checking residual autocorrelation for cell11, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.265, stderr 0.040, n = 56). Worth noting for the writeup, though not a result on its own.

While fitting the one-lag kernel for cell07, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.114, stderr 0.037, n = 40). While fitting the one-lag kernel for cell04, the ordering of cells was preserved (coefficient 0.276, stderr 0.028, n = 45). While auditing the holding potential column for cell11, the ordering of cells was preserved (coefficient 0.119, stderr 0.033, n = 40). While checking residual autocorrelation for cell15, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.289, stderr 0.044, n = 38). While bootstrapping the CI for cell02, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.183, stderr 0.019, n = 49). Worth noting for the writeup, though not a result on its own.

### Step 4: re-exporting the raw traces

While segmenting epochs for cell17, nothing in the figure changed at print size (coefficient 0.106, stderr 0.039, n = 38). While auditing the holding potential column for cell24, the estimate moved less than one standard error (coefficient 0.127, stderr 0.045, n = 55). While checking residual autocorrelation for cell18, the ordering of cells was preserved (coefficient 0.244, stderr 0.019, n = 43).

While segmenting epochs for cell15, nothing in the figure changed at print size (coefficient 0.086, stderr 0.012, n = 43). While comparing per-cell orderings for cell05, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.167, stderr 0.048, n = 49). While bootstrapping the CI for cell04, two cells fell out of the usable range (coefficient 0.108, stderr 0.047, n = 44). While bootstrapping the CI for cell01, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.104, stderr 0.031, n = 48). This is the part that will need a real statistical argument.

While re-exporting the raw traces for cell19, nothing in the figure changed at print size (coefficient 0.253, stderr 0.013, n = 45). While re-exporting the raw traces for cell13, the coefficient tracked epoch count more closely than duration (coefficient 0.114, stderr 0.028, n = 48). While checking residual autocorrelation for cell02, nothing in the figure changed at print size (coefficient 0.249, stderr 0.021, n = 49).

### Step 5: fitting the one-lag kernel

While re-exporting the raw traces for cell13, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.267, stderr 0.028, n = 51). While checking residual autocorrelation for cell14, the CI narrowed by roughly a tenth (coefficient 0.149, stderr 0.042, n = 54). While comparing per-cell orderings for cell24, the ordering of cells was preserved (coefficient 0.095, stderr 0.014, n = 58). While re-exporting the raw traces for cell23, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.191, stderr 0.031, n = 43). While comparing per-cell orderings for cell03, the CI narrowed by roughly a tenth (coefficient 0.294, stderr 0.033, n = 47). While fitting the one-lag kernel for cell23, the coefficient tracked epoch count more closely than duration (coefficient 0.111, stderr 0.045, n = 55).

While segmenting epochs for cell04, the coefficient tracked epoch count more closely than duration (coefficient 0.175, stderr 0.034, n = 44). While re-exporting the raw traces for cell23, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.241, stderr 0.042, n = 54). While re-exporting the raw traces for cell16, the coefficient tracked epoch count more closely than duration (coefficient 0.167, stderr 0.022, n = 48). While re-exporting the raw traces for cell24, two cells fell out of the usable range (coefficient 0.083, stderr 0.035, n = 45). While re-running with a tighter segmentation threshold for cell01, the coefficient tracked epoch count more closely than duration (coefficient 0.140, stderr 0.018, n = 54). While fitting the one-lag kernel for cell24, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.235, stderr 0.037, n = 52).

### Step 6: fitting the one-lag kernel

While checking residual autocorrelation for cell03, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.230, stderr 0.043, n = 53). While checking residual autocorrelation for cell13, the CI narrowed by roughly a tenth (coefficient 0.300, stderr 0.024, n = 46). While auditing the holding potential column for cell19, the CI narrowed by roughly a tenth (coefficient 0.284, stderr 0.029, n = 42). While auditing the holding potential column for cell08, two cells fell out of the usable range (coefficient 0.147, stderr 0.012, n = 51).

While comparing per-cell orderings for cell23, nothing in the figure changed at print size (coefficient 0.202, stderr 0.048, n = 40). While bootstrapping the CI for cell02, the ordering of cells was preserved (coefficient 0.222, stderr 0.024, n = 38). While bootstrapping the CI for cell08, the CI narrowed by roughly a tenth (coefficient 0.118, stderr 0.030, n = 47). While auditing the holding potential column for cell03, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.233, stderr 0.019, n = 57). While re-running with a tighter segmentation threshold for cell12, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.294, stderr 0.045, n = 58). While checking residual autocorrelation for cell01, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.198, stderr 0.015, n = 39).

### Step 7: comparing per-cell orderings

While fitting the one-lag kernel for cell19, the estimate moved less than one standard error (coefficient 0.223, stderr 0.038, n = 49). While fitting the one-lag kernel for cell16, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.136, stderr 0.045, n = 48). While auditing the holding potential column for cell05, the estimate moved less than one standard error (coefficient 0.159, stderr 0.021, n = 48). While re-exporting the raw traces for cell10, the estimate moved less than one standard error (coefficient 0.159, stderr 0.021, n = 46). While segmenting epochs for cell15, two cells fell out of the usable range (coefficient 0.168, stderr 0.035, n = 41).

While comparing per-cell orderings for cell01, two cells fell out of the usable range (coefficient 0.157, stderr 0.015, n = 50). While comparing per-cell orderings for cell07, the ordering of cells was preserved (coefficient 0.255, stderr 0.049, n = 49). While re-exporting the raw traces for cell02, nothing in the figure changed at print size (coefficient 0.099, stderr 0.017, n = 57). While bootstrapping the CI for cell02, two cells fell out of the usable range (coefficient 0.293, stderr 0.032, n = 43). Noted and moved on; it does not change the decision.

While re-running with a tighter segmentation threshold for cell10, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.290, stderr 0.034, n = 54). While bootstrapping the CI for cell15, two cells fell out of the usable range (coefficient 0.179, stderr 0.050, n = 58). While auditing the holding potential column for cell23, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.310, stderr 0.042, n = 47). While re-exporting the raw traces for cell08, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.266, stderr 0.048, n = 45). While re-exporting the raw traces for cell18, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.308, stderr 0.048, n = 53). This is the part that will need a real statistical argument.

### Step 8: re-exporting the raw traces

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell20    0.153  0.028   0.098  0.209  54        500
cell16    0.297  0.024   0.251  0.344  43        4000
cell18    0.261  0.043   0.178  0.345  58        500
cell08    0.107  0.035   0.037  0.176  40        4000
cell13    0.289  0.022   0.247  0.331  53        2000
cell19    0.289  0.044   0.203  0.376  47        500
cell03    0.247  0.028   0.192  0.303  51        500
cell23    0.264  0.015   0.235  0.293  46        2000
```

While checking residual autocorrelation for cell07, the coefficient tracked epoch count more closely than duration (coefficient 0.194, stderr 0.017, n = 42). While checking residual autocorrelation for cell14, the estimate moved less than one standard error (coefficient 0.219, stderr 0.045, n = 57). While bootstrapping the CI for cell07, the estimate moved less than one standard error (coefficient 0.228, stderr 0.036, n = 46). While bootstrapping the CI for cell20, the coefficient tracked epoch count more closely than duration (coefficient 0.307, stderr 0.020, n = 58). While fitting the one-lag kernel for cell20, nothing in the figure changed at print size (coefficient 0.300, stderr 0.043, n = 54). While checking residual autocorrelation for cell19, nothing in the figure changed at print size (coefficient 0.139, stderr 0.018, n = 50). Flagging it so it does not get rediscovered next week.

While checking residual autocorrelation for cell22, two cells fell out of the usable range (coefficient 0.171, stderr 0.025, n = 57). While fitting the one-lag kernel for cell04, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.192, stderr 0.041, n = 38). While re-running with a tighter segmentation threshold for cell06, two cells fell out of the usable range (coefficient 0.146, stderr 0.011, n = 43). While checking residual autocorrelation for cell22, nothing in the figure changed at print size (coefficient 0.100, stderr 0.026, n = 46). While bootstrapping the CI for cell18, the ordering of cells was preserved (coefficient 0.208, stderr 0.043, n = 58). While re-running with a tighter segmentation threshold for cell24, the estimate moved less than one standard error (coefficient 0.216, stderr 0.049, n = 38).

```python
coefs = fit_per_cell(rows, threshold=0.72)
lo, hi = ci(coefs, seed=18)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 9: comparing per-cell orderings

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell24    0.257  0.033   0.193  0.322  45        2000
cell16    0.246  0.033   0.181  0.311  54        1000
cell04    0.117  0.021   0.076  0.158  57        4000
cell21    0.267  0.013   0.241  0.293  57        2000
cell11    0.271  0.043   0.186  0.355  45        4000
cell23    0.141  0.043   0.057  0.225  42        500
cell19    0.210  0.047   0.118  0.302  54        500
cell21    0.174  0.039   0.098  0.251  50        1000
```

While bootstrapping the CI for cell07, nothing in the figure changed at print size (coefficient 0.204, stderr 0.011, n = 45). While fitting the one-lag kernel for cell07, nothing in the figure changed at print size (coefficient 0.161, stderr 0.017, n = 41). While bootstrapping the CI for cell03, the CI narrowed by roughly a tenth (coefficient 0.156, stderr 0.023, n = 40). While comparing per-cell orderings for cell24, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.138, stderr 0.034, n = 50). Parking this until the re-segmentation lands.

```python
coefs = fit_per_cell(rows, threshold=0.38)
lo, hi = ci(coefs, seed=38)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 10: fitting the one-lag kernel

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell02    0.299  0.042   0.217  0.381  47        500
cell10    0.174  0.050   0.076  0.271  56        4000
cell15    0.110  0.031   0.048  0.171  43        1000
cell12    0.193  0.025   0.145  0.242  41        4000
cell09    0.175  0.030   0.116  0.233  43        4000
cell12    0.193  0.028   0.139  0.248  51        4000
cell16    0.265  0.030   0.205  0.325  56        4000
cell13    0.120  0.044   0.034  0.206  49        4000
cell22    0.286  0.024   0.239  0.334  47        4000
cell08    0.108  0.015   0.078  0.138  47        500
cell21    0.248  0.019   0.211  0.286  57        1000
```

While re-running with a tighter segmentation threshold for cell02, the ordering of cells was preserved (coefficient 0.284, stderr 0.030, n = 53). While segmenting epochs for cell13, the estimate moved less than one standard error (coefficient 0.168, stderr 0.036, n = 58). While auditing the holding potential column for cell08, nothing in the figure changed at print size (coefficient 0.211, stderr 0.034, n = 42).

### Step 11: fitting the one-lag kernel

While re-exporting the raw traces for cell08, the CI narrowed by roughly a tenth (coefficient 0.257, stderr 0.022, n = 42). While re-exporting the raw traces for cell22, the estimate moved less than one standard error (coefficient 0.189, stderr 0.039, n = 49). While auditing the holding potential column for cell13, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.138, stderr 0.013, n = 55). While comparing per-cell orderings for cell08, the estimate moved less than one standard error (coefficient 0.197, stderr 0.018, n = 50).

While segmenting epochs for cell22, nothing in the figure changed at print size (coefficient 0.221, stderr 0.025, n = 45). While checking residual autocorrelation for cell24, the CI narrowed by roughly a tenth (coefficient 0.295, stderr 0.027, n = 49). While auditing the holding potential column for cell07, the estimate moved less than one standard error (coefficient 0.149, stderr 0.012, n = 39). While checking residual autocorrelation for cell18, the coefficient tracked epoch count more closely than duration (coefficient 0.267, stderr 0.019, n = 47). Flagging it so it does not get rediscovered next week.

```python
coefs = fit_per_cell(rows, threshold=0.57)
lo, hi = ci(coefs, seed=97)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 12: re-exporting the raw traces

While auditing the holding potential column for cell18, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.230, stderr 0.048, n = 56). While auditing the holding potential column for cell01, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.203, stderr 0.021, n = 56). While bootstrapping the CI for cell13, the CI narrowed by roughly a tenth (coefficient 0.186, stderr 0.030, n = 58).

While segmenting epochs for cell21, the coefficient tracked epoch count more closely than duration (coefficient 0.232, stderr 0.033, n = 42). While auditing the holding potential column for cell14, the ordering of cells was preserved (coefficient 0.142, stderr 0.027, n = 53). While fitting the one-lag kernel for cell03, the estimate moved less than one standard error (coefficient 0.100, stderr 0.049, n = 52). While comparing per-cell orderings for cell13, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.197, stderr 0.036, n = 40).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell14    0.248  0.022   0.205  0.292  51        4000
cell23    0.299  0.028   0.244  0.355  57        1000
cell19    0.081  0.026   0.029  0.133  54        2000
cell08    0.095  0.037   0.023  0.167  56        500
cell19    0.150  0.013   0.124  0.175  44        2000
cell12    0.178  0.016   0.147  0.209  44        4000
cell20    0.185  0.035   0.116  0.254  50        2000
cell10    0.169  0.018   0.134  0.204  47        4000
cell17    0.096  0.026   0.046  0.146  58        2000
cell05    0.115  0.045   0.026  0.203  58        4000
cell19    0.298  0.039   0.222  0.374  47        500
cell22    0.284  0.027   0.232  0.336  41        4000
cell17    0.261  0.038   0.187  0.335  57        500
cell12    0.102  0.020   0.062  0.141  40        2000
```

### Step 13: auditing the holding potential column

While bootstrapping the CI for cell08, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.177, stderr 0.015, n = 47). While auditing the holding potential column for cell22, the ordering of cells was preserved (coefficient 0.210, stderr 0.043, n = 47). While re-exporting the raw traces for cell08, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.144, stderr 0.027, n = 52). Parking this until the re-segmentation lands.

While checking residual autocorrelation for cell08, the CI narrowed by roughly a tenth (coefficient 0.124, stderr 0.046, n = 45). While segmenting epochs for cell19, the CI narrowed by roughly a tenth (coefficient 0.104, stderr 0.034, n = 40). While auditing the holding potential column for cell09, the CI narrowed by roughly a tenth (coefficient 0.262, stderr 0.031, n = 52). While re-running with a tighter segmentation threshold for cell06, the CI narrowed by roughly a tenth (coefficient 0.115, stderr 0.047, n = 50). While fitting the one-lag kernel for cell18, the CI narrowed by roughly a tenth (coefficient 0.214, stderr 0.022, n = 50). While comparing per-cell orderings for cell04, the coefficient tracked epoch count more closely than duration (coefficient 0.173, stderr 0.050, n = 45). Flagging it so it does not get rediscovered next week.

While segmenting epochs for cell03, nothing in the figure changed at print size (coefficient 0.103, stderr 0.012, n = 54). While re-running with a tighter segmentation threshold for cell16, the estimate moved less than one standard error (coefficient 0.281, stderr 0.041, n = 43). While fitting the one-lag kernel for cell20, nothing in the figure changed at print size (coefficient 0.179, stderr 0.031, n = 53). While re-running with a tighter segmentation threshold for cell24, nothing in the figure changed at print size (coefficient 0.284, stderr 0.031, n = 54). While fitting the one-lag kernel for cell09, the coefficient tracked epoch count more closely than duration (coefficient 0.154, stderr 0.046, n = 44).

While comparing per-cell orderings for cell15, the estimate moved less than one standard error (coefficient 0.267, stderr 0.026, n = 50). While auditing the holding potential column for cell02, nothing in the figure changed at print size (coefficient 0.162, stderr 0.020, n = 55). While bootstrapping the CI for cell03, the estimate moved less than one standard error (coefficient 0.154, stderr 0.037, n = 38). While auditing the holding potential column for cell10, the CI narrowed by roughly a tenth (coefficient 0.221, stderr 0.039, n = 46). While re-exporting the raw traces for cell09, nothing in the figure changed at print size (coefficient 0.104, stderr 0.013, n = 42).

### Step 14: auditing the holding potential column

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell16    0.177  0.044   0.089  0.264  58        1000
cell03    0.102  0.018   0.066  0.137  44        2000
cell22    0.272  0.018   0.236  0.308  38        1000
cell17    0.155  0.040   0.076  0.234  56        2000
cell22    0.214  0.015   0.185  0.244  50        1000
cell23    0.290  0.016   0.260  0.321  58        500
cell05    0.097  0.042   0.015  0.178  42        4000
cell02    0.202  0.013   0.177  0.227  58        500
```

While comparing per-cell orderings for cell13, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.280, stderr 0.029, n = 47). While re-running with a tighter segmentation threshold for cell11, the coefficient tracked epoch count more closely than duration (coefficient 0.089, stderr 0.050, n = 45). While segmenting epochs for cell15, the coefficient tracked epoch count more closely than duration (coefficient 0.281, stderr 0.049, n = 50).

While bootstrapping the CI for cell11, the ordering of cells was preserved (coefficient 0.231, stderr 0.023, n = 47). While comparing per-cell orderings for cell17, the ordering of cells was preserved (coefficient 0.301, stderr 0.016, n = 39). While comparing per-cell orderings for cell23, the CI narrowed by roughly a tenth (coefficient 0.213, stderr 0.021, n = 58). While auditing the holding potential column for cell11, the CI narrowed by roughly a tenth (coefficient 0.265, stderr 0.029, n = 58). While bootstrapping the CI for cell22, the CI narrowed by roughly a tenth (coefficient 0.178, stderr 0.021, n = 42). While fitting the one-lag kernel for cell22, two cells fell out of the usable range (coefficient 0.167, stderr 0.024, n = 52). Noted and moved on; it does not change the decision.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell04    0.099  0.047   0.006  0.192  53        1000
cell14    0.145  0.026   0.094  0.197  55        1000
cell07    0.180  0.012   0.156  0.204  47        500
cell18    0.297  0.035   0.229  0.365  56        4000
cell21    0.262  0.019   0.225  0.299  41        4000
cell16    0.087  0.040   0.009  0.165  53        2000
cell03    0.235  0.025   0.186  0.284  45        1000
cell09    0.210  0.022   0.166  0.253  40        2000
cell15    0.281  0.023   0.237  0.326  55        1000
```

### Step 15: re-exporting the raw traces

While fitting the one-lag kernel for cell15, the ordering of cells was preserved (coefficient 0.160, stderr 0.040, n = 57). While auditing the holding potential column for cell05, the coefficient tracked epoch count more closely than duration (coefficient 0.236, stderr 0.038, n = 40). While fitting the one-lag kernel for cell13, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.108, stderr 0.017, n = 49). While segmenting epochs for cell20, the ordering of cells was preserved (coefficient 0.221, stderr 0.034, n = 58). While auditing the holding potential column for cell01, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.152, stderr 0.046, n = 57). Worth noting for the writeup, though not a result on its own.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell24    0.185  0.028   0.129  0.240  44        500
cell08    0.186  0.032   0.123  0.248  41        1000
cell18    0.166  0.023   0.121  0.210  41        1000
cell11    0.081  0.025   0.031  0.130  45        2000
cell06    0.155  0.033   0.091  0.218  43        1000
cell21    0.123  0.035   0.055  0.190  52        1000
cell22    0.097  0.024   0.049  0.145  43        2000
cell20    0.149  0.044   0.062  0.236  42        500
cell10    0.306  0.010   0.286  0.327  46        4000
cell15    0.102  0.024   0.055  0.149  46        4000
cell18    0.254  0.028   0.199  0.310  39        4000
cell07    0.081  0.012   0.057  0.104  38        2000
```

While checking residual autocorrelation for cell05, the CI narrowed by roughly a tenth (coefficient 0.246, stderr 0.021, n = 58). While re-running with a tighter segmentation threshold for cell02, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.284, stderr 0.027, n = 53). While re-running with a tighter segmentation threshold for cell12, the CI narrowed by roughly a tenth (coefficient 0.144, stderr 0.027, n = 53). Flagging it so it does not get rediscovered next week.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell15    0.239  0.017   0.205  0.273  38        2000
cell03    0.085  0.030   0.026  0.144  56        500
cell20    0.186  0.023   0.140  0.231  47        2000
cell18    0.085  0.046   -0.005  0.176  48        1000
cell21    0.302  0.049   0.205  0.399  54        500
cell20    0.235  0.025   0.187  0.283  49        1000
cell06    0.139  0.015   0.109  0.169  38        2000
cell14    0.121  0.014   0.094  0.149  44        2000
cell10    0.249  0.020   0.210  0.288  42        500
```

### Step 16: checking residual autocorrelation

While re-exporting the raw traces for cell01, the estimate moved less than one standard error (coefficient 0.146, stderr 0.015, n = 41). While re-exporting the raw traces for cell15, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.128, stderr 0.015, n = 40). While checking residual autocorrelation for cell08, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.304, stderr 0.018, n = 48). Noted and moved on; it does not change the decision.

While auditing the holding potential column for cell03, the estimate moved less than one standard error (coefficient 0.166, stderr 0.022, n = 39). While fitting the one-lag kernel for cell10, the coefficient tracked epoch count more closely than duration (coefficient 0.295, stderr 0.042, n = 39). While re-running with a tighter segmentation threshold for cell03, nothing in the figure changed at print size (coefficient 0.211, stderr 0.012, n = 42). While auditing the holding potential column for cell07, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.307, stderr 0.027, n = 49). While checking residual autocorrelation for cell15, the ordering of cells was preserved (coefficient 0.134, stderr 0.030, n = 43). While re-exporting the raw traces for cell22, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.182, stderr 0.040, n = 38). Parking this until the re-segmentation lands.

While re-exporting the raw traces for cell10, nothing in the figure changed at print size (coefficient 0.146, stderr 0.044, n = 50). While bootstrapping the CI for cell03, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.115, stderr 0.022, n = 53). While comparing per-cell orderings for cell15, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.116, stderr 0.014, n = 56). While comparing per-cell orderings for cell18, the coefficient tracked epoch count more closely than duration (coefficient 0.118, stderr 0.028, n = 47). While re-running with a tighter segmentation threshold for cell09, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.103, stderr 0.044, n = 40).

While segmenting epochs for cell02, nothing in the figure changed at print size (coefficient 0.081, stderr 0.024, n = 42). While segmenting epochs for cell02, the CI narrowed by roughly a tenth (coefficient 0.184, stderr 0.038, n = 54). While re-exporting the raw traces for cell13, the ordering of cells was preserved (coefficient 0.111, stderr 0.021, n = 54). While comparing per-cell orderings for cell21, the ordering of cells was preserved (coefficient 0.203, stderr 0.029, n = 56). While segmenting epochs for cell16, the estimate moved less than one standard error (coefficient 0.160, stderr 0.018, n = 50).

### Step 17: checking residual autocorrelation

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell13    0.143  0.030   0.084  0.202  47        500
cell02    0.165  0.043   0.080  0.250  45        4000
cell17    0.218  0.022   0.176  0.260  40        2000
cell05    0.235  0.032   0.172  0.297  52        2000
cell19    0.279  0.011   0.257  0.300  57        2000
cell20    0.122  0.029   0.065  0.179  51        4000
cell14    0.136  0.021   0.095  0.177  39        2000
```

While comparing per-cell orderings for cell23, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.088, stderr 0.046, n = 48). While re-exporting the raw traces for cell18, nothing in the figure changed at print size (coefficient 0.145, stderr 0.011, n = 47). While comparing per-cell orderings for cell19, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.176, stderr 0.017, n = 52). While comparing per-cell orderings for cell04, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.120, stderr 0.047, n = 41). While comparing per-cell orderings for cell10, the coefficient tracked epoch count more closely than duration (coefficient 0.104, stderr 0.031, n = 49). While bootstrapping the CI for cell03, the coefficient tracked epoch count more closely than duration (coefficient 0.273, stderr 0.032, n = 46). This is the part that will need a real statistical argument.

### Step 18: re-exporting the raw traces

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell23    0.127  0.049   0.031  0.222  53        2000
cell15    0.220  0.018   0.185  0.255  44        2000
cell15    0.157  0.042   0.074  0.240  54        1000
cell18    0.124  0.041   0.043  0.205  41        2000
cell13    0.181  0.021   0.140  0.222  56        1000
cell05    0.155  0.022   0.113  0.198  48        1000
cell15    0.145  0.033   0.079  0.210  47        1000
cell04    0.132  0.046   0.041  0.222  41        500
cell14    0.208  0.020   0.168  0.248  52        2000
cell14    0.142  0.030   0.084  0.201  39        4000
cell14    0.216  0.013   0.192  0.241  45        500
```

While comparing per-cell orderings for cell10, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.217, stderr 0.037, n = 57). While bootstrapping the CI for cell01, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.126, stderr 0.043, n = 52). While bootstrapping the CI for cell19, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.181, stderr 0.042, n = 43). While re-running with a tighter segmentation threshold for cell11, the ordering of cells was preserved (coefficient 0.239, stderr 0.017, n = 39). While bootstrapping the CI for cell22, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.237, stderr 0.049, n = 53). While checking residual autocorrelation for cell01, two cells fell out of the usable range (coefficient 0.220, stderr 0.026, n = 39).

### Step 19: re-running with a tighter segmentation threshold

While auditing the holding potential column for cell03, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.126, stderr 0.012, n = 43). While fitting the one-lag kernel for cell17, the CI narrowed by roughly a tenth (coefficient 0.189, stderr 0.044, n = 45). While auditing the holding potential column for cell08, two cells fell out of the usable range (coefficient 0.111, stderr 0.048, n = 55). While bootstrapping the CI for cell21, the ordering of cells was preserved (coefficient 0.195, stderr 0.024, n = 41). While fitting the one-lag kernel for cell03, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.286, stderr 0.012, n = 47). This is the part that will need a real statistical argument.

While comparing per-cell orderings for cell08, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.166, stderr 0.035, n = 44). While fitting the one-lag kernel for cell22, the CI narrowed by roughly a tenth (coefficient 0.271, stderr 0.013, n = 46). While auditing the holding potential column for cell16, the CI narrowed by roughly a tenth (coefficient 0.105, stderr 0.028, n = 44). While fitting the one-lag kernel for cell17, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.083, stderr 0.045, n = 55). While fitting the one-lag kernel for cell01, nothing in the figure changed at print size (coefficient 0.237, stderr 0.012, n = 46). While re-exporting the raw traces for cell02, nothing in the figure changed at print size (coefficient 0.212, stderr 0.047, n = 52).

While bootstrapping the CI for cell20, two cells fell out of the usable range (coefficient 0.165, stderr 0.036, n = 55). While re-running with a tighter segmentation threshold for cell17, two cells fell out of the usable range (coefficient 0.239, stderr 0.020, n = 49). While fitting the one-lag kernel for cell15, two cells fell out of the usable range (coefficient 0.132, stderr 0.023, n = 56). While re-running with a tighter segmentation threshold for cell17, two cells fell out of the usable range (coefficient 0.197, stderr 0.025, n = 45).

While auditing the holding potential column for cell10, the estimate moved less than one standard error (coefficient 0.202, stderr 0.024, n = 57). While segmenting epochs for cell22, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.204, stderr 0.040, n = 40). While checking residual autocorrelation for cell01, the CI narrowed by roughly a tenth (coefficient 0.237, stderr 0.014, n = 43). While fitting the one-lag kernel for cell18, the coefficient tracked epoch count more closely than duration (coefficient 0.241, stderr 0.048, n = 51). While re-exporting the raw traces for cell08, the coefficient tracked epoch count more closely than duration (coefficient 0.188, stderr 0.019, n = 42). While auditing the holding potential column for cell03, the coefficient tracked epoch count more closely than duration (coefficient 0.092, stderr 0.015, n = 52). Noted and moved on; it does not change the decision.

### Step 20: bootstrapping the CI

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell22    0.152  0.037   0.080  0.224  54        1000
cell20    0.180  0.027   0.126  0.233  47        2000
cell03    0.212  0.042   0.130  0.293  51        4000
cell06    0.136  0.014   0.107  0.164  49        4000
cell01    0.145  0.014   0.116  0.173  38        2000
cell07    0.165  0.034   0.099  0.231  56        500
cell15    0.302  0.050   0.205  0.399  58        500
```

```python
coefs = fit_per_cell(rows, threshold=0.46)
lo, hi = ci(coefs, seed=42)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While re-exporting the raw traces for cell09, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.159, stderr 0.011, n = 49). While bootstrapping the CI for cell10, the CI narrowed by roughly a tenth (coefficient 0.243, stderr 0.022, n = 56). While fitting the one-lag kernel for cell02, the coefficient tracked epoch count more closely than duration (coefficient 0.233, stderr 0.047, n = 55). Noted and moved on; it does not change the decision.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell07    0.228  0.031   0.168  0.288  53        500
cell09    0.089  0.041   0.009  0.169  52        500
cell10    0.254  0.013   0.228  0.280  49        4000
cell20    0.228  0.032   0.165  0.291  54        1000
cell04    0.210  0.013   0.185  0.234  42        4000
cell19    0.240  0.039   0.163  0.317  58        500
```

### Step 21: re-running with a tighter segmentation threshold

```python
coefs = fit_per_cell(rows, threshold=0.31)
lo, hi = ci(coefs, seed=42)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While auditing the holding potential column for cell18, nothing in the figure changed at print size (coefficient 0.245, stderr 0.032, n = 48). While fitting the one-lag kernel for cell12, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.129, stderr 0.045, n = 51). While fitting the one-lag kernel for cell23, the CI narrowed by roughly a tenth (coefficient 0.087, stderr 0.018, n = 56). While auditing the holding potential column for cell21, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.241, stderr 0.037, n = 56). While checking residual autocorrelation for cell17, the estimate moved less than one standard error (coefficient 0.161, stderr 0.021, n = 53). While re-exporting the raw traces for cell02, the coefficient tracked epoch count more closely than duration (coefficient 0.130, stderr 0.026, n = 53). Flagging it so it does not get rediscovered next week.

While re-exporting the raw traces for cell08, the ordering of cells was preserved (coefficient 0.179, stderr 0.032, n = 56). While bootstrapping the CI for cell23, nothing in the figure changed at print size (coefficient 0.261, stderr 0.033, n = 43). While auditing the holding potential column for cell16, the ordering of cells was preserved (coefficient 0.265, stderr 0.017, n = 53). Noted and moved on; it does not change the decision.

### Step 22: re-exporting the raw traces

While auditing the holding potential column for cell24, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.202, stderr 0.024, n = 56). While fitting the one-lag kernel for cell06, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.299, stderr 0.047, n = 57). While fitting the one-lag kernel for cell03, the estimate moved less than one standard error (coefficient 0.082, stderr 0.043, n = 52). This is the part that will need a real statistical argument.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell04    0.271  0.024   0.225  0.317  52        4000
cell08    0.182  0.024   0.134  0.230  43        1000
cell01    0.226  0.016   0.195  0.257  40        1000
cell18    0.241  0.029   0.186  0.297  51        4000
cell01    0.234  0.029   0.178  0.290  41        500
cell08    0.080  0.027   0.026  0.134  48        2000
cell15    0.239  0.024   0.192  0.286  52        4000
```

### Step 23: segmenting epochs

While bootstrapping the CI for cell16, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.084, stderr 0.049, n = 48). While bootstrapping the CI for cell01, nothing in the figure changed at print size (coefficient 0.108, stderr 0.034, n = 45). While segmenting epochs for cell01, nothing in the figure changed at print size (coefficient 0.216, stderr 0.049, n = 51). While fitting the one-lag kernel for cell12, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.149, stderr 0.048, n = 56).

While comparing per-cell orderings for cell02, nothing in the figure changed at print size (coefficient 0.258, stderr 0.032, n = 49). While re-exporting the raw traces for cell17, the coefficient tracked epoch count more closely than duration (coefficient 0.260, stderr 0.023, n = 51). While checking residual autocorrelation for cell09, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.224, stderr 0.018, n = 41). While fitting the one-lag kernel for cell05, two cells fell out of the usable range (coefficient 0.161, stderr 0.015, n = 44). While segmenting epochs for cell23, two cells fell out of the usable range (coefficient 0.088, stderr 0.015, n = 40). While fitting the one-lag kernel for cell05, the estimate moved less than one standard error (coefficient 0.293, stderr 0.030, n = 49).

### Step 24: fitting the one-lag kernel

While fitting the one-lag kernel for cell23, nothing in the figure changed at print size (coefficient 0.124, stderr 0.032, n = 50). While comparing per-cell orderings for cell22, the CI narrowed by roughly a tenth (coefficient 0.232, stderr 0.023, n = 55). While auditing the holding potential column for cell18, the coefficient tracked epoch count more closely than duration (coefficient 0.091, stderr 0.040, n = 54). While auditing the holding potential column for cell01, the CI narrowed by roughly a tenth (coefficient 0.163, stderr 0.037, n = 55). While fitting the one-lag kernel for cell05, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.293, stderr 0.034, n = 38). While re-running with a tighter segmentation threshold for cell24, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.245, stderr 0.048, n = 41). Parking this until the re-segmentation lands.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell09    0.226  0.023   0.182  0.271  39        2000
cell15    0.296  0.046   0.206  0.385  48        500
cell07    0.273  0.016   0.242  0.304  46        1000
cell02    0.116  0.047   0.024  0.208  48        4000
cell01    0.243  0.044   0.158  0.329  44        2000
cell02    0.162  0.042   0.079  0.244  58        4000
cell18    0.126  0.012   0.103  0.149  42        500
cell11    0.118  0.028   0.064  0.173  38        1000
cell22    0.227  0.013   0.201  0.252  44        1000
cell14    0.184  0.025   0.135  0.232  47        4000
```

### Step 25: segmenting epochs

While re-exporting the raw traces for cell21, nothing in the figure changed at print size (coefficient 0.123, stderr 0.036, n = 43). While comparing per-cell orderings for cell13, two cells fell out of the usable range (coefficient 0.300, stderr 0.028, n = 54). While re-running with a tighter segmentation threshold for cell03, the estimate moved less than one standard error (coefficient 0.186, stderr 0.011, n = 44). While auditing the holding potential column for cell19, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.200, stderr 0.044, n = 45). While checking residual autocorrelation for cell15, two cells fell out of the usable range (coefficient 0.274, stderr 0.043, n = 52).

While fitting the one-lag kernel for cell22, the estimate moved less than one standard error (coefficient 0.163, stderr 0.015, n = 58). While fitting the one-lag kernel for cell15, nothing in the figure changed at print size (coefficient 0.309, stderr 0.032, n = 49). While checking residual autocorrelation for cell10, two cells fell out of the usable range (coefficient 0.082, stderr 0.032, n = 57). Flagging it so it does not get rediscovered next week.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell10    0.084  0.012   0.060  0.108  41        2000
cell01    0.284  0.045   0.196  0.372  48        4000
cell03    0.160  0.036   0.089  0.231  55        1000
cell16    0.183  0.044   0.096  0.271  39        500
cell07    0.293  0.043   0.208  0.378  51        2000
cell05    0.262  0.044   0.175  0.349  53        1000
cell19    0.188  0.021   0.147  0.230  51        4000
cell14    0.137  0.043   0.052  0.222  53        500
cell18    0.221  0.012   0.198  0.244  55        500
cell20    0.189  0.025   0.139  0.239  46        1000
```

### Step 26: auditing the holding potential column

While auditing the holding potential column for cell02, the CI narrowed by roughly a tenth (coefficient 0.291, stderr 0.030, n = 51). While auditing the holding potential column for cell01, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.145, stderr 0.028, n = 57). While auditing the holding potential column for cell11, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.094, stderr 0.011, n = 50).

```python
coefs = fit_per_cell(rows, threshold=0.31)
lo, hi = ci(coefs, seed=36)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 27: segmenting epochs

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell18    0.309  0.015   0.280  0.338  51        1000
cell17    0.296  0.021   0.255  0.337  46        500
cell11    0.102  0.023   0.057  0.146  46        1000
cell24    0.167  0.049   0.071  0.263  44        2000
cell13    0.184  0.031   0.123  0.244  52        1000
cell02    0.169  0.018   0.133  0.204  40        1000
cell20    0.258  0.034   0.191  0.326  52        4000
cell18    0.225  0.020   0.187  0.264  42        2000
cell13    0.228  0.033   0.163  0.293  52        500
cell20    0.194  0.021   0.153  0.235  38        2000
```

While re-exporting the raw traces for cell06, nothing in the figure changed at print size (coefficient 0.128, stderr 0.032, n = 41). While comparing per-cell orderings for cell11, the estimate moved less than one standard error (coefficient 0.168, stderr 0.045, n = 42). While auditing the holding potential column for cell06, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.196, stderr 0.011, n = 54).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell14    0.148  0.017   0.115  0.182  38        500
cell13    0.278  0.039   0.201  0.355  41        1000
cell01    0.276  0.011   0.254  0.297  39        1000
cell08    0.275  0.049   0.178  0.372  47        2000
cell11    0.268  0.034   0.202  0.334  57        500
cell13    0.207  0.024   0.159  0.254  46        4000
cell23    0.213  0.049   0.117  0.309  38        500
cell10    0.123  0.040   0.046  0.201  55        4000
cell18    0.284  0.044   0.198  0.370  58        4000
cell24    0.223  0.037   0.150  0.295  50        4000
cell11    0.086  0.043   0.002  0.170  54        2000
```

### Step 28: re-running with a tighter segmentation threshold

While comparing per-cell orderings for cell07, nothing in the figure changed at print size (coefficient 0.265, stderr 0.012, n = 45). While re-running with a tighter segmentation threshold for cell12, the ordering of cells was preserved (coefficient 0.196, stderr 0.023, n = 57). While re-exporting the raw traces for cell16, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.183, stderr 0.023, n = 42). While checking residual autocorrelation for cell12, nothing in the figure changed at print size (coefficient 0.292, stderr 0.039, n = 43). While auditing the holding potential column for cell15, the CI narrowed by roughly a tenth (coefficient 0.214, stderr 0.031, n = 53). Parking this until the re-segmentation lands.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell01    0.210  0.042   0.128  0.293  46        1000
cell18    0.144  0.035   0.076  0.212  51        500
cell19    0.114  0.017   0.080  0.148  40        500
cell04    0.158  0.018   0.123  0.192  41        2000
cell24    0.229  0.044   0.143  0.314  50        4000
cell17    0.223  0.046   0.132  0.313  44        500
cell06    0.245  0.036   0.173  0.316  51        500
cell04    0.264  0.044   0.178  0.350  38        2000
cell23    0.304  0.046   0.215  0.394  55        2000
```

While re-exporting the raw traces for cell07, the CI narrowed by roughly a tenth (coefficient 0.112, stderr 0.016, n = 41). While re-running with a tighter segmentation threshold for cell09, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.248, stderr 0.017, n = 48). While re-running with a tighter segmentation threshold for cell08, the estimate moved less than one standard error (coefficient 0.163, stderr 0.012, n = 47). While comparing per-cell orderings for cell21, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.257, stderr 0.019, n = 41).

```python
coefs = fit_per_cell(rows, threshold=0.34)
lo, hi = ci(coefs, seed=88)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 29: re-running with a tighter segmentation threshold

While checking residual autocorrelation for cell20, nothing in the figure changed at print size (coefficient 0.105, stderr 0.041, n = 49). While bootstrapping the CI for cell18, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.100, stderr 0.023, n = 57). While fitting the one-lag kernel for cell18, two cells fell out of the usable range (coefficient 0.295, stderr 0.033, n = 54). Parking this until the re-segmentation lands.

While fitting the one-lag kernel for cell09, two cells fell out of the usable range (coefficient 0.109, stderr 0.045, n = 58). While checking residual autocorrelation for cell12, the coefficient tracked epoch count more closely than duration (coefficient 0.182, stderr 0.050, n = 58). While re-running with a tighter segmentation threshold for cell12, the estimate moved less than one standard error (coefficient 0.084, stderr 0.044, n = 51). While comparing per-cell orderings for cell01, the estimate moved less than one standard error (coefficient 0.286, stderr 0.029, n = 40).

### Step 30: re-running with a tighter segmentation threshold

While fitting the one-lag kernel for cell05, two cells fell out of the usable range (coefficient 0.206, stderr 0.019, n = 48). While comparing per-cell orderings for cell12, the ordering of cells was preserved (coefficient 0.173, stderr 0.018, n = 53). While re-running with a tighter segmentation threshold for cell09, the estimate moved less than one standard error (coefficient 0.288, stderr 0.012, n = 57). While re-running with a tighter segmentation threshold for cell12, the coefficient tracked epoch count more closely than duration (coefficient 0.226, stderr 0.038, n = 57). While fitting the one-lag kernel for cell23, the ordering of cells was preserved (coefficient 0.122, stderr 0.047, n = 48). This is the part that will need a real statistical argument.

While bootstrapping the CI for cell13, the coefficient tracked epoch count more closely than duration (coefficient 0.229, stderr 0.039, n = 48). While auditing the holding potential column for cell15, two cells fell out of the usable range (coefficient 0.182, stderr 0.036, n = 57). While fitting the one-lag kernel for cell11, the ordering of cells was preserved (coefficient 0.287, stderr 0.034, n = 54). While fitting the one-lag kernel for cell03, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.244, stderr 0.043, n = 42). Parking this until the re-segmentation lands.

```python
coefs = fit_per_cell(rows, threshold=0.73)
lo, hi = ci(coefs, seed=18)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

