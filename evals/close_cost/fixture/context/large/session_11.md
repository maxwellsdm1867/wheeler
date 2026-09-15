# Prior session 11 of 20

Transcript of an earlier working session on the history-kernel analysis.

### Step 1: bootstrapping the CI

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell09    0.185  0.025   0.137  0.233  58        1000
cell02    0.145  0.047   0.052  0.238  44        4000
cell06    0.292  0.046   0.202  0.383  54        4000
cell12    0.211  0.048   0.117  0.305  49        4000
cell02    0.200  0.028   0.146  0.255  51        4000
cell06    0.276  0.044   0.190  0.362  48        1000
cell17    0.177  0.042   0.095  0.259  49        2000
cell09    0.252  0.037   0.179  0.325  51        500
cell21    0.282  0.020   0.243  0.322  47        2000
cell01    0.106  0.023   0.060  0.152  56        2000
cell13    0.089  0.020   0.049  0.129  47        1000
cell03    0.193  0.037   0.121  0.265  57        2000
cell17    0.093  0.040   0.015  0.170  44        2000
```

While fitting the one-lag kernel for cell12, two cells fell out of the usable range (coefficient 0.296, stderr 0.036, n = 41). While re-running with a tighter segmentation threshold for cell10, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.272, stderr 0.048, n = 47). While checking residual autocorrelation for cell24, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.198, stderr 0.042, n = 57). While auditing the holding potential column for cell10, the CI narrowed by roughly a tenth (coefficient 0.256, stderr 0.020, n = 46). Noted and moved on; it does not change the decision.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell16    0.110  0.031   0.050  0.170  49        500
cell24    0.100  0.019   0.063  0.137  57        2000
cell06    0.109  0.037   0.036  0.181  49        1000
cell08    0.158  0.025   0.108  0.207  38        4000
cell13    0.233  0.020   0.193  0.273  44        4000
cell24    0.197  0.037   0.124  0.270  48        2000
cell02    0.237  0.049   0.140  0.334  38        1000
cell13    0.121  0.014   0.093  0.148  58        4000
cell21    0.208  0.014   0.180  0.237  50        1000
cell24    0.108  0.043   0.024  0.193  55        1000
cell10    0.088  0.021   0.047  0.128  45        2000
cell24    0.163  0.010   0.144  0.183  50        500
cell21    0.233  0.021   0.191  0.274  58        2000
cell19    0.213  0.029   0.155  0.270  44        500
```

While fitting the one-lag kernel for cell23, the estimate moved less than one standard error (coefficient 0.309, stderr 0.044, n = 55). While fitting the one-lag kernel for cell23, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.194, stderr 0.036, n = 41). While re-exporting the raw traces for cell14, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.149, stderr 0.030, n = 38). This is the part that will need a real statistical argument.

### Step 2: re-exporting the raw traces

While checking residual autocorrelation for cell11, the ordering of cells was preserved (coefficient 0.101, stderr 0.015, n = 53). While segmenting epochs for cell03, the CI narrowed by roughly a tenth (coefficient 0.281, stderr 0.013, n = 43). While checking residual autocorrelation for cell08, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.193, stderr 0.015, n = 40). While segmenting epochs for cell13, nothing in the figure changed at print size (coefficient 0.136, stderr 0.048, n = 42). Flagging it so it does not get rediscovered next week.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell11    0.268  0.022   0.225  0.311  49        500
cell18    0.161  0.018   0.125  0.197  50        500
cell03    0.215  0.027   0.161  0.269  51        500
cell18    0.241  0.045   0.152  0.330  51        4000
cell16    0.222  0.025   0.172  0.271  41        1000
cell04    0.305  0.050   0.207  0.402  50        1000
cell19    0.309  0.014   0.281  0.337  43        4000
cell16    0.109  0.034   0.042  0.176  39        500
cell08    0.230  0.044   0.144  0.317  40        2000
cell07    0.123  0.020   0.084  0.161  39        500
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell17    0.234  0.023   0.187  0.280  53        500
cell16    0.197  0.029   0.139  0.255  52        500
cell04    0.104  0.013   0.079  0.130  39        1000
cell15    0.302  0.017   0.268  0.336  39        500
cell15    0.157  0.040   0.079  0.235  49        2000
cell03    0.096  0.026   0.045  0.147  38        500
cell21    0.235  0.043   0.151  0.318  55        1000
cell03    0.206  0.016   0.175  0.238  57        2000
cell14    0.140  0.010   0.120  0.160  42        500
cell09    0.199  0.036   0.129  0.269  50        4000
```

```python
coefs = fit_per_cell(rows, threshold=0.77)
lo, hi = ci(coefs, seed=0)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 3: segmenting epochs

```python
coefs = fit_per_cell(rows, threshold=0.71)
lo, hi = ci(coefs, seed=67)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While re-running with a tighter segmentation threshold for cell07, two cells fell out of the usable range (coefficient 0.242, stderr 0.032, n = 40). While checking residual autocorrelation for cell16, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.147, stderr 0.028, n = 46). While fitting the one-lag kernel for cell23, nothing in the figure changed at print size (coefficient 0.128, stderr 0.012, n = 38). While re-running with a tighter segmentation threshold for cell15, the estimate moved less than one standard error (coefficient 0.277, stderr 0.048, n = 52). While fitting the one-lag kernel for cell04, nothing in the figure changed at print size (coefficient 0.121, stderr 0.030, n = 50). Parking this until the re-segmentation lands.

### Step 4: auditing the holding potential column

While checking residual autocorrelation for cell22, nothing in the figure changed at print size (coefficient 0.163, stderr 0.027, n = 44). While bootstrapping the CI for cell19, the estimate moved less than one standard error (coefficient 0.131, stderr 0.022, n = 49). While checking residual autocorrelation for cell03, two cells fell out of the usable range (coefficient 0.206, stderr 0.020, n = 58).

While re-exporting the raw traces for cell01, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.262, stderr 0.045, n = 54). While re-exporting the raw traces for cell03, two cells fell out of the usable range (coefficient 0.301, stderr 0.022, n = 39). While bootstrapping the CI for cell06, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.310, stderr 0.028, n = 46). While segmenting epochs for cell12, the estimate moved less than one standard error (coefficient 0.157, stderr 0.047, n = 40). While comparing per-cell orderings for cell05, the coefficient tracked epoch count more closely than duration (coefficient 0.304, stderr 0.032, n = 52). While bootstrapping the CI for cell06, the coefficient tracked epoch count more closely than duration (coefficient 0.181, stderr 0.050, n = 56).

While auditing the holding potential column for cell19, the CI narrowed by roughly a tenth (coefficient 0.239, stderr 0.027, n = 41). While re-exporting the raw traces for cell20, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.281, stderr 0.013, n = 57). While bootstrapping the CI for cell23, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.125, stderr 0.040, n = 52). While segmenting epochs for cell20, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.186, stderr 0.011, n = 55). While re-running with a tighter segmentation threshold for cell14, two cells fell out of the usable range (coefficient 0.239, stderr 0.040, n = 53). While auditing the holding potential column for cell07, the ordering of cells was preserved (coefficient 0.200, stderr 0.012, n = 48).

### Step 5: comparing per-cell orderings

While bootstrapping the CI for cell17, the ordering of cells was preserved (coefficient 0.213, stderr 0.035, n = 39). While fitting the one-lag kernel for cell24, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.099, stderr 0.022, n = 42). While segmenting epochs for cell15, nothing in the figure changed at print size (coefficient 0.203, stderr 0.023, n = 51). While fitting the one-lag kernel for cell13, the coefficient tracked epoch count more closely than duration (coefficient 0.113, stderr 0.049, n = 38). Worth noting for the writeup, though not a result on its own.

While re-running with a tighter segmentation threshold for cell23, the ordering of cells was preserved (coefficient 0.119, stderr 0.015, n = 58). While re-running with a tighter segmentation threshold for cell04, nothing in the figure changed at print size (coefficient 0.196, stderr 0.018, n = 56). While re-exporting the raw traces for cell24, the CI narrowed by roughly a tenth (coefficient 0.183, stderr 0.031, n = 58). While fitting the one-lag kernel for cell08, the estimate moved less than one standard error (coefficient 0.214, stderr 0.015, n = 38). While fitting the one-lag kernel for cell01, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.223, stderr 0.012, n = 50). While checking residual autocorrelation for cell11, the CI narrowed by roughly a tenth (coefficient 0.219, stderr 0.034, n = 46).

While re-running with a tighter segmentation threshold for cell10, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.245, stderr 0.024, n = 50). While re-running with a tighter segmentation threshold for cell04, nothing in the figure changed at print size (coefficient 0.179, stderr 0.024, n = 38). While re-running with a tighter segmentation threshold for cell03, two cells fell out of the usable range (coefficient 0.163, stderr 0.031, n = 39). While comparing per-cell orderings for cell10, the ordering of cells was preserved (coefficient 0.251, stderr 0.014, n = 42). Worth noting for the writeup, though not a result on its own.

While re-running with a tighter segmentation threshold for cell01, the estimate moved less than one standard error (coefficient 0.086, stderr 0.029, n = 47). While auditing the holding potential column for cell02, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.249, stderr 0.011, n = 54). While fitting the one-lag kernel for cell14, the coefficient tracked epoch count more closely than duration (coefficient 0.109, stderr 0.045, n = 42). While comparing per-cell orderings for cell19, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.293, stderr 0.025, n = 44). While checking residual autocorrelation for cell19, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.134, stderr 0.042, n = 51). While comparing per-cell orderings for cell13, the ordering of cells was preserved (coefficient 0.122, stderr 0.036, n = 39).

### Step 6: auditing the holding potential column

While bootstrapping the CI for cell08, two cells fell out of the usable range (coefficient 0.274, stderr 0.025, n = 39). While fitting the one-lag kernel for cell09, two cells fell out of the usable range (coefficient 0.287, stderr 0.021, n = 43). While checking residual autocorrelation for cell23, the estimate moved less than one standard error (coefficient 0.186, stderr 0.039, n = 51).

While segmenting epochs for cell06, nothing in the figure changed at print size (coefficient 0.174, stderr 0.020, n = 45). While re-exporting the raw traces for cell17, nothing in the figure changed at print size (coefficient 0.114, stderr 0.018, n = 39). While auditing the holding potential column for cell20, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.212, stderr 0.018, n = 54). While re-running with a tighter segmentation threshold for cell10, the coefficient tracked epoch count more closely than duration (coefficient 0.233, stderr 0.034, n = 42).

### Step 7: segmenting epochs

While re-running with a tighter segmentation threshold for cell11, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.239, stderr 0.013, n = 54). While re-exporting the raw traces for cell06, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.095, stderr 0.021, n = 47). While checking residual autocorrelation for cell22, the CI narrowed by roughly a tenth (coefficient 0.199, stderr 0.041, n = 38). While checking residual autocorrelation for cell09, two cells fell out of the usable range (coefficient 0.290, stderr 0.049, n = 55). While checking residual autocorrelation for cell03, the coefficient tracked epoch count more closely than duration (coefficient 0.229, stderr 0.015, n = 53). While fitting the one-lag kernel for cell12, the estimate moved less than one standard error (coefficient 0.239, stderr 0.020, n = 45). Worth noting for the writeup, though not a result on its own.

While checking residual autocorrelation for cell12, the estimate moved less than one standard error (coefficient 0.288, stderr 0.049, n = 43). While fitting the one-lag kernel for cell15, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.169, stderr 0.017, n = 40). While checking residual autocorrelation for cell19, the coefficient tracked epoch count more closely than duration (coefficient 0.276, stderr 0.011, n = 54). While segmenting epochs for cell08, the estimate moved less than one standard error (coefficient 0.102, stderr 0.035, n = 50). While segmenting epochs for cell07, the estimate moved less than one standard error (coefficient 0.259, stderr 0.018, n = 47).

### Step 8: segmenting epochs

While comparing per-cell orderings for cell19, the CI narrowed by roughly a tenth (coefficient 0.273, stderr 0.025, n = 39). While fitting the one-lag kernel for cell04, the CI narrowed by roughly a tenth (coefficient 0.243, stderr 0.028, n = 44). While checking residual autocorrelation for cell10, the CI narrowed by roughly a tenth (coefficient 0.124, stderr 0.038, n = 45). While bootstrapping the CI for cell02, the coefficient tracked epoch count more closely than duration (coefficient 0.194, stderr 0.016, n = 52). While bootstrapping the CI for cell20, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.216, stderr 0.037, n = 55). Noted and moved on; it does not change the decision.

While re-running with a tighter segmentation threshold for cell04, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.235, stderr 0.032, n = 41). While re-exporting the raw traces for cell02, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.281, stderr 0.031, n = 51). While fitting the one-lag kernel for cell16, the CI narrowed by roughly a tenth (coefficient 0.242, stderr 0.039, n = 50). While checking residual autocorrelation for cell16, two cells fell out of the usable range (coefficient 0.102, stderr 0.041, n = 47).

### Step 9: auditing the holding potential column

While checking residual autocorrelation for cell03, nothing in the figure changed at print size (coefficient 0.190, stderr 0.032, n = 51). While segmenting epochs for cell11, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.118, stderr 0.048, n = 53). While re-exporting the raw traces for cell12, the ordering of cells was preserved (coefficient 0.161, stderr 0.047, n = 53).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell19    0.268  0.025   0.219  0.317  51        2000
cell14    0.159  0.011   0.138  0.180  53        2000
cell23    0.236  0.015   0.207  0.265  41        1000
cell07    0.182  0.038   0.108  0.257  41        500
cell11    0.181  0.029   0.124  0.238  49        500
cell23    0.096  0.038   0.022  0.170  58        2000
cell18    0.226  0.012   0.203  0.249  40        2000
cell17    0.181  0.044   0.095  0.268  51        4000
cell01    0.239  0.033   0.175  0.303  56        1000
cell22    0.287  0.027   0.235  0.340  48        2000
cell10    0.230  0.033   0.164  0.295  54        500
```

While auditing the holding potential column for cell19, the estimate moved less than one standard error (coefficient 0.260, stderr 0.018, n = 48). While fitting the one-lag kernel for cell06, the ordering of cells was preserved (coefficient 0.238, stderr 0.026, n = 58). While segmenting epochs for cell10, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.292, stderr 0.016, n = 57). Noted and moved on; it does not change the decision.

While fitting the one-lag kernel for cell18, the ordering of cells was preserved (coefficient 0.239, stderr 0.023, n = 58). While checking residual autocorrelation for cell14, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.271, stderr 0.038, n = 50). While bootstrapping the CI for cell08, the estimate moved less than one standard error (coefficient 0.104, stderr 0.039, n = 53). Worth noting for the writeup, though not a result on its own.

### Step 10: bootstrapping the CI

While checking residual autocorrelation for cell24, the ordering of cells was preserved (coefficient 0.138, stderr 0.044, n = 57). While fitting the one-lag kernel for cell14, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.188, stderr 0.044, n = 49). While bootstrapping the CI for cell20, two cells fell out of the usable range (coefficient 0.269, stderr 0.022, n = 56). While segmenting epochs for cell13, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.208, stderr 0.031, n = 44).

While bootstrapping the CI for cell22, the estimate moved less than one standard error (coefficient 0.152, stderr 0.010, n = 50). While re-exporting the raw traces for cell12, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.152, stderr 0.018, n = 51). While comparing per-cell orderings for cell01, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.110, stderr 0.022, n = 46).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell02    0.264  0.034   0.199  0.330  39        500
cell18    0.175  0.027   0.123  0.227  49        4000
cell19    0.110  0.044   0.024  0.196  51        1000
cell23    0.213  0.019   0.177  0.250  52        2000
cell09    0.238  0.032   0.175  0.300  47        1000
cell02    0.111  0.019   0.075  0.148  40        500
cell01    0.102  0.022   0.058  0.145  39        2000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell23    0.196  0.012   0.172  0.219  53        500
cell13    0.290  0.033   0.225  0.355  50        2000
cell15    0.115  0.043   0.031  0.199  48        4000
cell03    0.195  0.045   0.106  0.283  42        1000
cell05    0.082  0.031   0.021  0.143  43        4000
cell13    0.243  0.018   0.208  0.278  53        2000
cell20    0.095  0.031   0.034  0.156  50        500
cell10    0.228  0.044   0.141  0.315  55        4000
cell23    0.236  0.022   0.193  0.280  48        500
cell16    0.293  0.011   0.271  0.316  47        1000
```

### Step 11: re-exporting the raw traces

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell05    0.188  0.026   0.138  0.238  49        2000
cell08    0.286  0.023   0.241  0.331  40        500
cell02    0.154  0.022   0.110  0.198  53        2000
cell06    0.290  0.026   0.238  0.342  52        4000
cell23    0.276  0.032   0.213  0.340  48        4000
cell11    0.174  0.049   0.079  0.270  40        1000
cell21    0.267  0.046   0.177  0.357  58        1000
cell16    0.214  0.043   0.130  0.298  56        2000
cell24    0.115  0.031   0.053  0.177  45        1000
cell17    0.240  0.017   0.207  0.273  48        1000
cell12    0.090  0.046   -0.001  0.181  44        500
cell18    0.205  0.034   0.139  0.271  54        4000
```

While segmenting epochs for cell02, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.154, stderr 0.029, n = 47). While re-exporting the raw traces for cell20, nothing in the figure changed at print size (coefficient 0.081, stderr 0.034, n = 51). While re-running with a tighter segmentation threshold for cell15, the coefficient tracked epoch count more closely than duration (coefficient 0.164, stderr 0.029, n = 47). While auditing the holding potential column for cell12, two cells fell out of the usable range (coefficient 0.089, stderr 0.033, n = 41). While fitting the one-lag kernel for cell17, the coefficient tracked epoch count more closely than duration (coefficient 0.107, stderr 0.016, n = 53). Worth noting for the writeup, though not a result on its own.

While comparing per-cell orderings for cell06, the estimate moved less than one standard error (coefficient 0.269, stderr 0.045, n = 51). While fitting the one-lag kernel for cell24, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.103, stderr 0.050, n = 52). While segmenting epochs for cell01, the coefficient tracked epoch count more closely than duration (coefficient 0.093, stderr 0.039, n = 38). While comparing per-cell orderings for cell16, the ordering of cells was preserved (coefficient 0.126, stderr 0.049, n = 57). While bootstrapping the CI for cell16, nothing in the figure changed at print size (coefficient 0.089, stderr 0.015, n = 45).

```python
coefs = fit_per_cell(rows, threshold=0.58)
lo, hi = ci(coefs, seed=65)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 12: fitting the one-lag kernel

While auditing the holding potential column for cell03, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.287, stderr 0.050, n = 56). While auditing the holding potential column for cell18, nothing in the figure changed at print size (coefficient 0.110, stderr 0.034, n = 58). While re-exporting the raw traces for cell03, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.156, stderr 0.037, n = 56). While re-running with a tighter segmentation threshold for cell22, the coefficient tracked epoch count more closely than duration (coefficient 0.192, stderr 0.044, n = 44). While fitting the one-lag kernel for cell22, the ordering of cells was preserved (coefficient 0.176, stderr 0.038, n = 51). While comparing per-cell orderings for cell21, the coefficient tracked epoch count more closely than duration (coefficient 0.104, stderr 0.046, n = 47).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell12    0.279  0.047   0.187  0.370  48        1000
cell16    0.152  0.015   0.122  0.182  54        2000
cell04    0.201  0.041   0.121  0.281  49        4000
cell21    0.128  0.015   0.099  0.157  43        2000
cell05    0.230  0.038   0.155  0.304  52        500
cell18    0.220  0.029   0.162  0.277  56        500
cell06    0.207  0.015   0.177  0.237  41        1000
cell05    0.083  0.030   0.025  0.141  41        500
cell17    0.255  0.022   0.212  0.297  40        2000
cell21    0.271  0.019   0.234  0.307  54        500
cell22    0.195  0.013   0.170  0.221  57        4000
cell21    0.155  0.023   0.109  0.200  53        1000
cell10    0.295  0.019   0.258  0.332  48        1000
cell03    0.141  0.030   0.082  0.200  47        1000
```

While bootstrapping the CI for cell10, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.238, stderr 0.031, n = 45). While bootstrapping the CI for cell23, two cells fell out of the usable range (coefficient 0.092, stderr 0.041, n = 47). While checking residual autocorrelation for cell10, nothing in the figure changed at print size (coefficient 0.210, stderr 0.031, n = 58). While fitting the one-lag kernel for cell13, the CI narrowed by roughly a tenth (coefficient 0.089, stderr 0.017, n = 51). While segmenting epochs for cell03, the CI narrowed by roughly a tenth (coefficient 0.269, stderr 0.035, n = 38). Noted and moved on; it does not change the decision.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell08    0.148  0.031   0.087  0.209  47        4000
cell05    0.215  0.027   0.162  0.267  42        2000
cell22    0.097  0.046   0.008  0.186  44        1000
cell05    0.188  0.038   0.113  0.264  44        1000
cell07    0.235  0.020   0.196  0.274  51        4000
cell11    0.298  0.016   0.267  0.328  45        1000
cell10    0.115  0.049   0.020  0.211  39        4000
cell10    0.226  0.032   0.165  0.288  47        500
cell21    0.305  0.035   0.236  0.373  57        2000
cell16    0.125  0.043   0.040  0.209  57        2000
cell14    0.234  0.034   0.168  0.299  48        2000
```

### Step 13: checking residual autocorrelation

While checking residual autocorrelation for cell09, the coefficient tracked epoch count more closely than duration (coefficient 0.156, stderr 0.016, n = 54). While auditing the holding potential column for cell17, the estimate moved less than one standard error (coefficient 0.101, stderr 0.012, n = 55). While comparing per-cell orderings for cell24, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.207, stderr 0.041, n = 56).

While comparing per-cell orderings for cell23, the CI narrowed by roughly a tenth (coefficient 0.259, stderr 0.047, n = 46). While auditing the holding potential column for cell07, two cells fell out of the usable range (coefficient 0.222, stderr 0.040, n = 39). While bootstrapping the CI for cell01, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.080, stderr 0.010, n = 51). While comparing per-cell orderings for cell07, the estimate moved less than one standard error (coefficient 0.292, stderr 0.017, n = 44). Flagging it so it does not get rediscovered next week.

### Step 14: fitting the one-lag kernel

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell20    0.215  0.050   0.118  0.313  40        1000
cell11    0.127  0.034   0.060  0.194  50        4000
cell24    0.125  0.028   0.070  0.181  51        2000
cell08    0.143  0.012   0.119  0.167  43        500
cell19    0.285  0.017   0.252  0.319  51        500
cell18    0.202  0.015   0.174  0.231  50        1000
cell09    0.308  0.038   0.234  0.382  55        2000
cell14    0.254  0.020   0.214  0.294  55        4000
```

While bootstrapping the CI for cell10, two cells fell out of the usable range (coefficient 0.091, stderr 0.011, n = 47). While checking residual autocorrelation for cell01, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.254, stderr 0.040, n = 47). While comparing per-cell orderings for cell01, the ordering of cells was preserved (coefficient 0.104, stderr 0.019, n = 44). While re-exporting the raw traces for cell05, the ordering of cells was preserved (coefficient 0.226, stderr 0.026, n = 54). While auditing the holding potential column for cell24, the CI narrowed by roughly a tenth (coefficient 0.091, stderr 0.033, n = 56).

### Step 15: re-exporting the raw traces

While auditing the holding potential column for cell10, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.259, stderr 0.035, n = 44). While comparing per-cell orderings for cell20, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.179, stderr 0.040, n = 54). While re-running with a tighter segmentation threshold for cell05, the estimate moved less than one standard error (coefficient 0.095, stderr 0.030, n = 44). While bootstrapping the CI for cell01, the ordering of cells was preserved (coefficient 0.271, stderr 0.022, n = 41). While re-running with a tighter segmentation threshold for cell08, the estimate moved less than one standard error (coefficient 0.276, stderr 0.046, n = 51). Worth noting for the writeup, though not a result on its own.

While checking residual autocorrelation for cell21, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.187, stderr 0.016, n = 47). While bootstrapping the CI for cell21, the ordering of cells was preserved (coefficient 0.275, stderr 0.027, n = 54). While auditing the holding potential column for cell19, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.221, stderr 0.038, n = 51).

### Step 16: auditing the holding potential column

While checking residual autocorrelation for cell19, the estimate moved less than one standard error (coefficient 0.224, stderr 0.029, n = 51). While re-exporting the raw traces for cell17, the estimate moved less than one standard error (coefficient 0.098, stderr 0.022, n = 57). While comparing per-cell orderings for cell03, the estimate moved less than one standard error (coefficient 0.147, stderr 0.043, n = 54).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell11    0.195  0.029   0.138  0.252  42        1000
cell19    0.156  0.024   0.108  0.203  55        2000
cell06    0.217  0.014   0.189  0.245  48        4000
cell09    0.211  0.011   0.191  0.232  57        1000
cell06    0.184  0.034   0.117  0.250  39        4000
cell23    0.298  0.012   0.274  0.322  46        1000
cell09    0.225  0.015   0.196  0.254  47        2000
cell08    0.143  0.046   0.052  0.234  57        2000
cell12    0.270  0.033   0.206  0.335  49        500
```

While re-exporting the raw traces for cell02, the CI narrowed by roughly a tenth (coefficient 0.120, stderr 0.048, n = 41). While auditing the holding potential column for cell24, the estimate moved less than one standard error (coefficient 0.302, stderr 0.024, n = 42). While bootstrapping the CI for cell15, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.288, stderr 0.032, n = 44). While auditing the holding potential column for cell12, the ordering of cells was preserved (coefficient 0.158, stderr 0.022, n = 47). While bootstrapping the CI for cell13, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.285, stderr 0.033, n = 44). While checking residual autocorrelation for cell12, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.139, stderr 0.011, n = 45). Worth noting for the writeup, though not a result on its own.

### Step 17: checking residual autocorrelation

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell05    0.126  0.013   0.100  0.151  48        4000
cell17    0.204  0.017   0.171  0.238  50        4000
cell08    0.273  0.017   0.239  0.307  46        4000
cell03    0.155  0.033   0.091  0.220  57        500
cell19    0.096  0.021   0.055  0.137  55        1000
cell07    0.231  0.043   0.146  0.316  55        4000
cell03    0.085  0.021   0.043  0.127  52        1000
cell23    0.238  0.011   0.217  0.259  49        500
cell14    0.179  0.030   0.119  0.238  39        4000
cell14    0.166  0.039   0.089  0.243  39        4000
```

```python
coefs = fit_per_cell(rows, threshold=0.36)
lo, hi = ci(coefs, seed=6)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While segmenting epochs for cell12, the ordering of cells was preserved (coefficient 0.176, stderr 0.039, n = 58). While re-exporting the raw traces for cell08, two cells fell out of the usable range (coefficient 0.120, stderr 0.034, n = 45). While segmenting epochs for cell08, the estimate moved less than one standard error (coefficient 0.306, stderr 0.017, n = 53). While checking residual autocorrelation for cell08, the estimate moved less than one standard error (coefficient 0.180, stderr 0.013, n = 56).

While comparing per-cell orderings for cell23, the CI narrowed by roughly a tenth (coefficient 0.241, stderr 0.025, n = 38). While re-running with a tighter segmentation threshold for cell20, the estimate moved less than one standard error (coefficient 0.232, stderr 0.030, n = 47). While segmenting epochs for cell06, the ordering of cells was preserved (coefficient 0.116, stderr 0.012, n = 44).

### Step 18: re-running with a tighter segmentation threshold

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell01    0.168  0.050   0.070  0.265  57        1000
cell14    0.270  0.029   0.213  0.327  58        2000
cell11    0.175  0.050   0.078  0.273  51        2000
cell12    0.090  0.015   0.061  0.120  58        500
cell24    0.192  0.033   0.126  0.257  47        4000
cell04    0.136  0.038   0.062  0.210  46        500
cell04    0.181  0.017   0.148  0.214  52        1000
cell24    0.188  0.036   0.118  0.258  55        4000
cell15    0.097  0.034   0.030  0.164  58        500
cell16    0.228  0.027   0.175  0.282  55        500
cell01    0.299  0.036   0.229  0.369  48        4000
cell17    0.294  0.041   0.215  0.374  54        1000
cell13    0.129  0.029   0.073  0.186  38        2000
cell10    0.165  0.011   0.144  0.187  56        2000
```

```python
coefs = fit_per_cell(rows, threshold=0.43)
lo, hi = ci(coefs, seed=35)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell03    0.252  0.012   0.229  0.275  53        1000
cell20    0.155  0.038   0.081  0.230  51        2000
cell10    0.207  0.013   0.182  0.233  56        2000
cell05    0.086  0.038   0.011  0.161  57        1000
cell06    0.113  0.040   0.035  0.191  51        2000
cell18    0.241  0.041   0.160  0.322  46        4000
cell21    0.135  0.046   0.044  0.226  46        2000
cell19    0.159  0.031   0.098  0.220  50        1000
cell13    0.250  0.038   0.175  0.324  42        2000
cell14    0.307  0.016   0.276  0.339  53        2000
cell11    0.091  0.046   0.001  0.181  55        4000
cell06    0.162  0.036   0.091  0.233  42        1000
cell12    0.084  0.048   -0.010  0.178  51        2000
cell07    0.307  0.038   0.233  0.382  51        500
```

While auditing the holding potential column for cell15, nothing in the figure changed at print size (coefficient 0.161, stderr 0.020, n = 40). While re-running with a tighter segmentation threshold for cell17, the ordering of cells was preserved (coefficient 0.184, stderr 0.023, n = 48). While fitting the one-lag kernel for cell12, two cells fell out of the usable range (coefficient 0.241, stderr 0.046, n = 41). This is the part that will need a real statistical argument.

### Step 19: bootstrapping the CI

```python
coefs = fit_per_cell(rows, threshold=0.43)
lo, hi = ci(coefs, seed=45)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While comparing per-cell orderings for cell10, the CI narrowed by roughly a tenth (coefficient 0.288, stderr 0.030, n = 51). While comparing per-cell orderings for cell04, the coefficient tracked epoch count more closely than duration (coefficient 0.206, stderr 0.044, n = 56). While re-running with a tighter segmentation threshold for cell14, the estimate moved less than one standard error (coefficient 0.114, stderr 0.028, n = 58). While re-running with a tighter segmentation threshold for cell05, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.113, stderr 0.012, n = 45).

While segmenting epochs for cell16, the CI narrowed by roughly a tenth (coefficient 0.148, stderr 0.043, n = 46). While comparing per-cell orderings for cell21, the ordering of cells was preserved (coefficient 0.208, stderr 0.023, n = 52). While fitting the one-lag kernel for cell12, two cells fell out of the usable range (coefficient 0.183, stderr 0.031, n = 46). While segmenting epochs for cell11, the coefficient tracked epoch count more closely than duration (coefficient 0.107, stderr 0.020, n = 38). While fitting the one-lag kernel for cell19, two cells fell out of the usable range (coefficient 0.185, stderr 0.039, n = 40). While re-exporting the raw traces for cell08, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.220, stderr 0.047, n = 54).

### Step 20: segmenting epochs

```python
coefs = fit_per_cell(rows, threshold=0.47)
lo, hi = ci(coefs, seed=20)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While bootstrapping the CI for cell17, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.256, stderr 0.017, n = 51). While segmenting epochs for cell01, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.272, stderr 0.050, n = 53). While bootstrapping the CI for cell24, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.254, stderr 0.042, n = 41). While re-running with a tighter segmentation threshold for cell14, the ordering of cells was preserved (coefficient 0.293, stderr 0.040, n = 54). While fitting the one-lag kernel for cell17, the CI narrowed by roughly a tenth (coefficient 0.186, stderr 0.047, n = 38). While re-running with a tighter segmentation threshold for cell22, the estimate moved less than one standard error (coefficient 0.272, stderr 0.046, n = 46).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell22    0.259  0.038   0.184  0.335  44        1000
cell16    0.235  0.036   0.164  0.305  51        4000
cell02    0.115  0.042   0.032  0.199  45        4000
cell23    0.164  0.036   0.093  0.235  42        4000
cell19    0.162  0.014   0.134  0.191  39        500
cell15    0.133  0.032   0.070  0.196  43        500
cell04    0.112  0.028   0.058  0.166  45        2000
cell11    0.083  0.028   0.027  0.138  51        2000
cell21    0.292  0.044   0.207  0.378  55        2000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell07    0.219  0.019   0.181  0.257  55        4000
cell09    0.171  0.011   0.149  0.193  50        2000
cell18    0.119  0.014   0.091  0.147  43        4000
cell24    0.127  0.041   0.046  0.207  52        500
cell16    0.106  0.012   0.083  0.129  46        1000
cell08    0.135  0.010   0.116  0.155  56        4000
```

### Step 21: checking residual autocorrelation

```python
coefs = fit_per_cell(rows, threshold=0.59)
lo, hi = ci(coefs, seed=5)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While auditing the holding potential column for cell13, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.185, stderr 0.044, n = 58). While segmenting epochs for cell16, the ordering of cells was preserved (coefficient 0.108, stderr 0.025, n = 50). While fitting the one-lag kernel for cell10, the coefficient tracked epoch count more closely than duration (coefficient 0.089, stderr 0.033, n = 40). While bootstrapping the CI for cell09, two cells fell out of the usable range (coefficient 0.129, stderr 0.022, n = 57). While checking residual autocorrelation for cell06, nothing in the figure changed at print size (coefficient 0.219, stderr 0.037, n = 56).

While comparing per-cell orderings for cell11, the ordering of cells was preserved (coefficient 0.237, stderr 0.028, n = 39). While re-running with a tighter segmentation threshold for cell01, the coefficient tracked epoch count more closely than duration (coefficient 0.095, stderr 0.012, n = 39). While re-exporting the raw traces for cell01, the estimate moved less than one standard error (coefficient 0.098, stderr 0.034, n = 38). While checking residual autocorrelation for cell07, two cells fell out of the usable range (coefficient 0.182, stderr 0.015, n = 58). While auditing the holding potential column for cell14, the estimate moved less than one standard error (coefficient 0.251, stderr 0.019, n = 53). While fitting the one-lag kernel for cell13, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.246, stderr 0.031, n = 57).

### Step 22: fitting the one-lag kernel

```python
coefs = fit_per_cell(rows, threshold=0.49)
lo, hi = ci(coefs, seed=53)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```python
coefs = fit_per_cell(rows, threshold=0.37)
lo, hi = ci(coefs, seed=57)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```python
coefs = fit_per_cell(rows, threshold=0.79)
lo, hi = ci(coefs, seed=8)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 23: fitting the one-lag kernel

```python
coefs = fit_per_cell(rows, threshold=0.45)
lo, hi = ci(coefs, seed=2)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While re-exporting the raw traces for cell22, the CI narrowed by roughly a tenth (coefficient 0.082, stderr 0.033, n = 39). While re-exporting the raw traces for cell14, the CI narrowed by roughly a tenth (coefficient 0.235, stderr 0.012, n = 46). While comparing per-cell orderings for cell10, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.307, stderr 0.040, n = 55). While fitting the one-lag kernel for cell22, the estimate moved less than one standard error (coefficient 0.083, stderr 0.046, n = 54). While segmenting epochs for cell23, nothing in the figure changed at print size (coefficient 0.309, stderr 0.016, n = 51).

While re-exporting the raw traces for cell17, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.302, stderr 0.028, n = 39). While bootstrapping the CI for cell05, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.244, stderr 0.025, n = 56). While re-exporting the raw traces for cell17, nothing in the figure changed at print size (coefficient 0.204, stderr 0.028, n = 48). While re-exporting the raw traces for cell06, the coefficient tracked epoch count more closely than duration (coefficient 0.150, stderr 0.025, n = 52). While re-exporting the raw traces for cell22, the ordering of cells was preserved (coefficient 0.272, stderr 0.030, n = 47). While re-exporting the raw traces for cell10, the ordering of cells was preserved (coefficient 0.161, stderr 0.018, n = 52). This is the part that will need a real statistical argument.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell22    0.145  0.045   0.057  0.234  55        2000
cell18    0.192  0.047   0.101  0.284  45        1000
cell17    0.084  0.038   0.010  0.158  51        2000
cell19    0.186  0.033   0.121  0.251  43        4000
cell11    0.171  0.024   0.125  0.217  41        1000
cell23    0.239  0.038   0.165  0.314  55        2000
cell16    0.203  0.021   0.162  0.244  45        2000
cell06    0.271  0.019   0.234  0.307  41        4000
```

### Step 24: segmenting epochs

While bootstrapping the CI for cell20, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.162, stderr 0.028, n = 43). While segmenting epochs for cell19, nothing in the figure changed at print size (coefficient 0.301, stderr 0.035, n = 40). While bootstrapping the CI for cell22, the ordering of cells was preserved (coefficient 0.161, stderr 0.018, n = 42). While comparing per-cell orderings for cell18, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.149, stderr 0.025, n = 49). While fitting the one-lag kernel for cell01, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.110, stderr 0.033, n = 44). While re-running with a tighter segmentation threshold for cell16, the coefficient tracked epoch count more closely than duration (coefficient 0.131, stderr 0.024, n = 41).

```python
coefs = fit_per_cell(rows, threshold=0.42)
lo, hi = ci(coefs, seed=84)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```python
coefs = fit_per_cell(rows, threshold=0.33)
lo, hi = ci(coefs, seed=14)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While bootstrapping the CI for cell02, the coefficient tracked epoch count more closely than duration (coefficient 0.166, stderr 0.011, n = 51). While re-exporting the raw traces for cell16, the coefficient tracked epoch count more closely than duration (coefficient 0.182, stderr 0.013, n = 41). While bootstrapping the CI for cell05, the coefficient tracked epoch count more closely than duration (coefficient 0.103, stderr 0.040, n = 54). While segmenting epochs for cell09, two cells fell out of the usable range (coefficient 0.303, stderr 0.019, n = 58). While re-exporting the raw traces for cell22, the coefficient tracked epoch count more closely than duration (coefficient 0.108, stderr 0.032, n = 47). Parking this until the re-segmentation lands.

### Step 25: re-exporting the raw traces

While segmenting epochs for cell07, the CI narrowed by roughly a tenth (coefficient 0.226, stderr 0.037, n = 47). While checking residual autocorrelation for cell23, the CI narrowed by roughly a tenth (coefficient 0.205, stderr 0.044, n = 48). While fitting the one-lag kernel for cell14, the estimate moved less than one standard error (coefficient 0.217, stderr 0.041, n = 46).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell11    0.194  0.026   0.142  0.245  38        1000
cell18    0.236  0.040   0.158  0.315  47        1000
cell07    0.210  0.044   0.123  0.296  41        4000
cell08    0.107  0.041   0.026  0.188  45        500
cell01    0.291  0.043   0.206  0.376  49        2000
cell03    0.193  0.019   0.156  0.229  52        1000
cell15    0.214  0.033   0.149  0.278  55        1000
cell07    0.284  0.034   0.217  0.350  49        1000
```

```python
coefs = fit_per_cell(rows, threshold=0.57)
lo, hi = ci(coefs, seed=20)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 26: checking residual autocorrelation

While fitting the one-lag kernel for cell03, two cells fell out of the usable range (coefficient 0.213, stderr 0.040, n = 48). While fitting the one-lag kernel for cell03, the coefficient tracked epoch count more closely than duration (coefficient 0.138, stderr 0.040, n = 54). While checking residual autocorrelation for cell09, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.235, stderr 0.012, n = 45).

While re-exporting the raw traces for cell11, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.213, stderr 0.041, n = 54). While re-exporting the raw traces for cell04, nothing in the figure changed at print size (coefficient 0.150, stderr 0.043, n = 51). While segmenting epochs for cell05, nothing in the figure changed at print size (coefficient 0.116, stderr 0.028, n = 45). While fitting the one-lag kernel for cell15, the estimate moved less than one standard error (coefficient 0.285, stderr 0.040, n = 41). While bootstrapping the CI for cell05, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.263, stderr 0.027, n = 56). While bootstrapping the CI for cell03, two cells fell out of the usable range (coefficient 0.306, stderr 0.039, n = 58).

While re-exporting the raw traces for cell11, the estimate moved less than one standard error (coefficient 0.227, stderr 0.042, n = 48). While bootstrapping the CI for cell03, the CI narrowed by roughly a tenth (coefficient 0.139, stderr 0.048, n = 52). While comparing per-cell orderings for cell15, two cells fell out of the usable range (coefficient 0.138, stderr 0.028, n = 58). While re-running with a tighter segmentation threshold for cell10, nothing in the figure changed at print size (coefficient 0.121, stderr 0.038, n = 55). While fitting the one-lag kernel for cell16, the coefficient tracked epoch count more closely than duration (coefficient 0.089, stderr 0.032, n = 55).

### Step 27: re-exporting the raw traces

While bootstrapping the CI for cell01, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.268, stderr 0.044, n = 56). While fitting the one-lag kernel for cell13, nothing in the figure changed at print size (coefficient 0.191, stderr 0.040, n = 51). While comparing per-cell orderings for cell06, the CI narrowed by roughly a tenth (coefficient 0.290, stderr 0.012, n = 57). Parking this until the re-segmentation lands.

While auditing the holding potential column for cell19, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.210, stderr 0.016, n = 54). While auditing the holding potential column for cell02, the coefficient tracked epoch count more closely than duration (coefficient 0.144, stderr 0.031, n = 39). While fitting the one-lag kernel for cell10, two cells fell out of the usable range (coefficient 0.126, stderr 0.042, n = 49). While bootstrapping the CI for cell24, nothing in the figure changed at print size (coefficient 0.223, stderr 0.041, n = 44). While segmenting epochs for cell16, two cells fell out of the usable range (coefficient 0.202, stderr 0.019, n = 57). While checking residual autocorrelation for cell15, two cells fell out of the usable range (coefficient 0.285, stderr 0.046, n = 44).

While auditing the holding potential column for cell04, the estimate moved less than one standard error (coefficient 0.243, stderr 0.023, n = 49). While fitting the one-lag kernel for cell04, two cells fell out of the usable range (coefficient 0.293, stderr 0.044, n = 57). While segmenting epochs for cell06, the coefficient tracked epoch count more closely than duration (coefficient 0.233, stderr 0.018, n = 56). While bootstrapping the CI for cell09, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.169, stderr 0.038, n = 43). Parking this until the re-segmentation lands.

### Step 28: bootstrapping the CI

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell18    0.113  0.032   0.051  0.175  57        500
cell11    0.174  0.047   0.083  0.266  51        1000
cell23    0.195  0.049   0.100  0.291  39        500
cell03    0.134  0.047   0.041  0.226  58        500
cell02    0.295  0.035   0.225  0.364  47        1000
cell02    0.201  0.048   0.106  0.296  40        2000
cell05    0.283  0.032   0.219  0.347  58        500
cell24    0.277  0.023   0.231  0.323  43        1000
cell14    0.269  0.033   0.205  0.333  54        500
cell18    0.210  0.044   0.124  0.295  43        1000
```

While segmenting epochs for cell19, nothing in the figure changed at print size (coefficient 0.268, stderr 0.049, n = 58). While re-exporting the raw traces for cell18, the ordering of cells was preserved (coefficient 0.246, stderr 0.036, n = 42). While re-exporting the raw traces for cell03, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.134, stderr 0.014, n = 56). Noted and moved on; it does not change the decision.

### Step 29: bootstrapping the CI

While comparing per-cell orderings for cell01, the coefficient tracked epoch count more closely than duration (coefficient 0.298, stderr 0.016, n = 51). While auditing the holding potential column for cell08, the estimate moved less than one standard error (coefficient 0.121, stderr 0.034, n = 53). While segmenting epochs for cell07, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.231, stderr 0.014, n = 51).

While fitting the one-lag kernel for cell11, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.166, stderr 0.044, n = 43). While auditing the holding potential column for cell18, the estimate moved less than one standard error (coefficient 0.307, stderr 0.025, n = 50). While re-running with a tighter segmentation threshold for cell04, nothing in the figure changed at print size (coefficient 0.201, stderr 0.020, n = 54). While re-running with a tighter segmentation threshold for cell22, the CI narrowed by roughly a tenth (coefficient 0.127, stderr 0.011, n = 57). While fitting the one-lag kernel for cell09, the coefficient tracked epoch count more closely than duration (coefficient 0.215, stderr 0.014, n = 41).

While re-running with a tighter segmentation threshold for cell18, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.121, stderr 0.033, n = 40). While bootstrapping the CI for cell01, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.123, stderr 0.049, n = 42). While auditing the holding potential column for cell18, nothing in the figure changed at print size (coefficient 0.196, stderr 0.033, n = 46).

While re-running with a tighter segmentation threshold for cell13, the coefficient tracked epoch count more closely than duration (coefficient 0.267, stderr 0.036, n = 39). While re-running with a tighter segmentation threshold for cell22, the coefficient tracked epoch count more closely than duration (coefficient 0.233, stderr 0.020, n = 39). While segmenting epochs for cell02, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.175, stderr 0.031, n = 56). While bootstrapping the CI for cell24, the CI narrowed by roughly a tenth (coefficient 0.219, stderr 0.014, n = 53). While re-running with a tighter segmentation threshold for cell03, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.288, stderr 0.035, n = 58). While comparing per-cell orderings for cell24, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.296, stderr 0.048, n = 55). Parking this until the re-segmentation lands.

### Step 30: bootstrapping the CI

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell17    0.084  0.041   0.004  0.164  49        4000
cell19    0.309  0.013   0.283  0.334  38        4000
cell12    0.227  0.045   0.139  0.316  40        500
cell07    0.181  0.033   0.116  0.247  50        2000
cell11    0.143  0.028   0.089  0.198  56        1000
cell08    0.194  0.022   0.151  0.237  40        4000
cell02    0.124  0.038   0.050  0.198  54        500
cell15    0.277  0.018   0.243  0.312  53        1000
cell23    0.131  0.034   0.064  0.198  47        500
cell08    0.299  0.032   0.236  0.362  47        500
cell09    0.289  0.014   0.262  0.316  43        4000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell17    0.113  0.026   0.061  0.165  38        500
cell08    0.301  0.028   0.246  0.356  52        500
cell19    0.170  0.046   0.080  0.260  47        500
cell22    0.135  0.018   0.099  0.170  43        2000
cell19    0.171  0.034   0.105  0.237  49        500
cell22    0.166  0.044   0.081  0.252  45        1000
cell23    0.203  0.035   0.134  0.271  50        500
cell04    0.166  0.016   0.135  0.197  39        1000
cell18    0.295  0.014   0.269  0.322  48        500
cell17    0.252  0.017   0.218  0.285  54        500
```

While re-running with a tighter segmentation threshold for cell22, two cells fell out of the usable range (coefficient 0.235, stderr 0.041, n = 47). While auditing the holding potential column for cell01, the coefficient tracked epoch count more closely than duration (coefficient 0.155, stderr 0.031, n = 45). While comparing per-cell orderings for cell16, the ordering of cells was preserved (coefficient 0.297, stderr 0.020, n = 50). While bootstrapping the CI for cell17, the CI narrowed by roughly a tenth (coefficient 0.290, stderr 0.048, n = 44). While re-exporting the raw traces for cell22, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.090, stderr 0.018, n = 56).

### Step 31: segmenting epochs

While comparing per-cell orderings for cell10, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.244, stderr 0.037, n = 44). While checking residual autocorrelation for cell04, the ordering of cells was preserved (coefficient 0.185, stderr 0.021, n = 46). While segmenting epochs for cell21, the coefficient tracked epoch count more closely than duration (coefficient 0.211, stderr 0.027, n = 48). While bootstrapping the CI for cell18, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.265, stderr 0.010, n = 53). While re-exporting the raw traces for cell13, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.165, stderr 0.044, n = 50). Parking this until the re-segmentation lands.

While fitting the one-lag kernel for cell12, the CI narrowed by roughly a tenth (coefficient 0.099, stderr 0.029, n = 51). While fitting the one-lag kernel for cell23, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.294, stderr 0.018, n = 54). While re-running with a tighter segmentation threshold for cell12, the estimate moved less than one standard error (coefficient 0.125, stderr 0.021, n = 45).

While bootstrapping the CI for cell03, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.177, stderr 0.018, n = 47). While comparing per-cell orderings for cell22, the CI narrowed by roughly a tenth (coefficient 0.084, stderr 0.023, n = 47). While segmenting epochs for cell03, the CI narrowed by roughly a tenth (coefficient 0.203, stderr 0.017, n = 58). While bootstrapping the CI for cell02, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.188, stderr 0.014, n = 57). While fitting the one-lag kernel for cell17, the ordering of cells was preserved (coefficient 0.276, stderr 0.017, n = 39). While re-exporting the raw traces for cell11, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.095, stderr 0.013, n = 57).

```python
coefs = fit_per_cell(rows, threshold=0.33)
lo, hi = ci(coefs, seed=42)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 32: auditing the holding potential column

While re-running with a tighter segmentation threshold for cell08, the estimate moved less than one standard error (coefficient 0.300, stderr 0.020, n = 48). While auditing the holding potential column for cell08, the CI narrowed by roughly a tenth (coefficient 0.260, stderr 0.020, n = 52). While segmenting epochs for cell10, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.100, stderr 0.016, n = 40). While auditing the holding potential column for cell08, the CI narrowed by roughly a tenth (coefficient 0.088, stderr 0.045, n = 45). While comparing per-cell orderings for cell19, the estimate moved less than one standard error (coefficient 0.165, stderr 0.046, n = 44). While bootstrapping the CI for cell06, two cells fell out of the usable range (coefficient 0.144, stderr 0.016, n = 57). Flagging it so it does not get rediscovered next week.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell06    0.275  0.041   0.195  0.354  39        500
cell06    0.168  0.032   0.105  0.231  51        500
cell24    0.119  0.019   0.081  0.156  40        2000
cell23    0.157  0.041   0.076  0.238  46        1000
cell20    0.105  0.032   0.042  0.168  49        2000
cell10    0.267  0.041   0.187  0.347  57        2000
```

While re-exporting the raw traces for cell04, the estimate moved less than one standard error (coefficient 0.132, stderr 0.014, n = 38). While segmenting epochs for cell14, the coefficient tracked epoch count more closely than duration (coefficient 0.301, stderr 0.039, n = 50). While comparing per-cell orderings for cell17, the ordering of cells was preserved (coefficient 0.224, stderr 0.046, n = 41). While re-exporting the raw traces for cell14, the estimate moved less than one standard error (coefficient 0.195, stderr 0.040, n = 47). While segmenting epochs for cell02, the estimate moved less than one standard error (coefficient 0.219, stderr 0.024, n = 49).

### Step 33: bootstrapping the CI

While re-exporting the raw traces for cell07, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.087, stderr 0.018, n = 47). While checking residual autocorrelation for cell04, the estimate moved less than one standard error (coefficient 0.105, stderr 0.023, n = 49). While re-running with a tighter segmentation threshold for cell05, two cells fell out of the usable range (coefficient 0.115, stderr 0.021, n = 54). While checking residual autocorrelation for cell15, the estimate moved less than one standard error (coefficient 0.094, stderr 0.037, n = 58). While re-running with a tighter segmentation threshold for cell18, two cells fell out of the usable range (coefficient 0.156, stderr 0.011, n = 44).

While segmenting epochs for cell01, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.305, stderr 0.020, n = 58). While segmenting epochs for cell02, the estimate moved less than one standard error (coefficient 0.091, stderr 0.037, n = 45). While segmenting epochs for cell13, the CI narrowed by roughly a tenth (coefficient 0.140, stderr 0.012, n = 43).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell02    0.082  0.040   0.004  0.160  43        2000
cell17    0.267  0.040   0.189  0.346  47        4000
cell12    0.162  0.029   0.104  0.219  44        4000
cell12    0.108  0.048   0.015  0.201  47        2000
cell01    0.211  0.016   0.178  0.243  50        2000
cell03    0.292  0.044   0.206  0.378  39        2000
cell23    0.271  0.050   0.173  0.369  58        1000
cell15    0.086  0.017   0.053  0.119  43        4000
cell24    0.177  0.038   0.102  0.252  50        4000
cell22    0.157  0.048   0.062  0.252  44        500
cell03    0.124  0.047   0.033  0.216  38        1000
cell05    0.118  0.017   0.085  0.150  47        2000
cell17    0.150  0.031   0.089  0.211  49        4000
cell11    0.302  0.039   0.226  0.378  48        500
```

### Step 34: auditing the holding potential column

While auditing the holding potential column for cell12, nothing in the figure changed at print size (coefficient 0.265, stderr 0.043, n = 51). While bootstrapping the CI for cell07, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.228, stderr 0.039, n = 58). While re-running with a tighter segmentation threshold for cell10, nothing in the figure changed at print size (coefficient 0.249, stderr 0.022, n = 38). While bootstrapping the CI for cell23, the CI narrowed by roughly a tenth (coefficient 0.134, stderr 0.024, n = 50). While re-running with a tighter segmentation threshold for cell24, the estimate moved less than one standard error (coefficient 0.212, stderr 0.030, n = 43). While segmenting epochs for cell17, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.262, stderr 0.024, n = 55). Noted and moved on; it does not change the decision.

While segmenting epochs for cell20, two cells fell out of the usable range (coefficient 0.222, stderr 0.029, n = 54). While re-running with a tighter segmentation threshold for cell24, the coefficient tracked epoch count more closely than duration (coefficient 0.149, stderr 0.014, n = 42). While re-running with a tighter segmentation threshold for cell16, the CI narrowed by roughly a tenth (coefficient 0.160, stderr 0.015, n = 44). While re-running with a tighter segmentation threshold for cell19, the ordering of cells was preserved (coefficient 0.292, stderr 0.040, n = 58). While comparing per-cell orderings for cell08, the coefficient tracked epoch count more closely than duration (coefficient 0.163, stderr 0.045, n = 54). While bootstrapping the CI for cell07, the coefficient tracked epoch count more closely than duration (coefficient 0.142, stderr 0.019, n = 55).

### Step 35: segmenting epochs

While comparing per-cell orderings for cell22, the CI narrowed by roughly a tenth (coefficient 0.198, stderr 0.032, n = 39). While auditing the holding potential column for cell07, nothing in the figure changed at print size (coefficient 0.236, stderr 0.044, n = 45). While segmenting epochs for cell13, two cells fell out of the usable range (coefficient 0.248, stderr 0.048, n = 56). While fitting the one-lag kernel for cell06, nothing in the figure changed at print size (coefficient 0.176, stderr 0.019, n = 51). While re-running with a tighter segmentation threshold for cell02, the ordering of cells was preserved (coefficient 0.234, stderr 0.035, n = 50).

```python
coefs = fit_per_cell(rows, threshold=0.46)
lo, hi = ci(coefs, seed=74)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 36: re-running with a tighter segmentation threshold

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell09    0.258  0.037   0.187  0.330  41        500
cell01    0.288  0.028   0.233  0.344  57        1000
cell23    0.086  0.028   0.032  0.140  40        1000
cell05    0.211  0.017   0.177  0.245  55        2000
cell05    0.282  0.037   0.210  0.355  40        1000
cell01    0.135  0.028   0.081  0.190  50        2000
cell22    0.142  0.044   0.055  0.228  55        4000
cell13    0.308  0.029   0.252  0.364  56        500
```

While segmenting epochs for cell18, the ordering of cells was preserved (coefficient 0.229, stderr 0.020, n = 57). While fitting the one-lag kernel for cell09, nothing in the figure changed at print size (coefficient 0.282, stderr 0.037, n = 46). While comparing per-cell orderings for cell13, the coefficient tracked epoch count more closely than duration (coefficient 0.283, stderr 0.039, n = 56).

```python
coefs = fit_per_cell(rows, threshold=0.39)
lo, hi = ci(coefs, seed=23)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell09    0.117  0.029   0.060  0.174  40        1000
cell06    0.200  0.026   0.149  0.251  47        1000
cell16    0.216  0.017   0.182  0.249  39        2000
cell13    0.211  0.027   0.159  0.264  56        2000
cell03    0.102  0.029   0.045  0.158  43        500
cell22    0.227  0.020   0.188  0.266  40        1000
cell14    0.268  0.025   0.219  0.318  49        2000
cell10    0.294  0.033   0.228  0.359  52        2000
cell05    0.276  0.034   0.210  0.342  39        2000
cell24    0.295  0.034   0.227  0.362  44        2000
cell17    0.098  0.034   0.031  0.164  52        4000
cell06    0.235  0.041   0.154  0.317  49        1000
cell23    0.286  0.021   0.245  0.327  45        500
cell01    0.287  0.050   0.190  0.384  52        500
```

### Step 37: auditing the holding potential column

While bootstrapping the CI for cell18, the ordering of cells was preserved (coefficient 0.288, stderr 0.044, n = 52). While comparing per-cell orderings for cell01, the coefficient tracked epoch count more closely than duration (coefficient 0.089, stderr 0.048, n = 40). While re-running with a tighter segmentation threshold for cell15, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.179, stderr 0.043, n = 49).

While checking residual autocorrelation for cell05, the ordering of cells was preserved (coefficient 0.106, stderr 0.033, n = 44). While re-exporting the raw traces for cell05, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.303, stderr 0.012, n = 38). While comparing per-cell orderings for cell16, the CI narrowed by roughly a tenth (coefficient 0.127, stderr 0.037, n = 40). While bootstrapping the CI for cell24, the ordering of cells was preserved (coefficient 0.083, stderr 0.031, n = 41). While comparing per-cell orderings for cell07, the coefficient tracked epoch count more closely than duration (coefficient 0.181, stderr 0.015, n = 58). Parking this until the re-segmentation lands.

While checking residual autocorrelation for cell14, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.146, stderr 0.022, n = 47). While segmenting epochs for cell11, the coefficient tracked epoch count more closely than duration (coefficient 0.303, stderr 0.034, n = 52). While comparing per-cell orderings for cell04, the coefficient tracked epoch count more closely than duration (coefficient 0.173, stderr 0.017, n = 43). While auditing the holding potential column for cell21, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.267, stderr 0.016, n = 45). While auditing the holding potential column for cell23, nothing in the figure changed at print size (coefficient 0.097, stderr 0.049, n = 46).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell12    0.144  0.030   0.085  0.203  51        2000
cell05    0.160  0.019   0.121  0.198  55        4000
cell17    0.219  0.037   0.147  0.291  45        4000
cell06    0.233  0.017   0.199  0.266  41        2000
cell03    0.272  0.013   0.247  0.296  53        1000
cell11    0.117  0.039   0.040  0.194  40        1000
cell22    0.304  0.037   0.232  0.376  50        4000
cell05    0.257  0.022   0.213  0.300  49        1000
cell16    0.211  0.039   0.135  0.287  54        1000
```

### Step 38: re-running with a tighter segmentation threshold

While re-running with a tighter segmentation threshold for cell03, the ordering of cells was preserved (coefficient 0.106, stderr 0.019, n = 39). While segmenting epochs for cell11, the estimate moved less than one standard error (coefficient 0.270, stderr 0.024, n = 49). While comparing per-cell orderings for cell15, the estimate moved less than one standard error (coefficient 0.125, stderr 0.022, n = 54). Noted and moved on; it does not change the decision.

While comparing per-cell orderings for cell23, two cells fell out of the usable range (coefficient 0.253, stderr 0.036, n = 42). While fitting the one-lag kernel for cell01, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.160, stderr 0.011, n = 38). While comparing per-cell orderings for cell08, the CI narrowed by roughly a tenth (coefficient 0.181, stderr 0.022, n = 40). While comparing per-cell orderings for cell18, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.310, stderr 0.018, n = 53).

