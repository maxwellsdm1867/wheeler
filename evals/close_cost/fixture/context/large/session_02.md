# Prior session 2 of 20

Transcript of an earlier working session on the history-kernel analysis.

### Step 1: bootstrapping the CI

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell23    0.202  0.011   0.180  0.223  54        500
cell04    0.086  0.026   0.034  0.137  46        4000
cell17    0.215  0.017   0.181  0.249  48        2000
cell16    0.302  0.015   0.272  0.332  54        500
cell06    0.302  0.030   0.243  0.361  53        4000
cell24    0.245  0.039   0.168  0.322  48        4000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell07    0.265  0.048   0.170  0.360  49        1000
cell11    0.176  0.031   0.116  0.236  52        500
cell15    0.176  0.049   0.080  0.271  56        2000
cell03    0.177  0.023   0.132  0.222  45        1000
cell18    0.142  0.041   0.061  0.223  48        1000
cell13    0.145  0.021   0.103  0.187  44        1000
cell08    0.208  0.017   0.175  0.242  45        2000
cell05    0.220  0.034   0.154  0.286  55        4000
cell08    0.086  0.014   0.058  0.114  54        2000
```

While comparing per-cell orderings for cell23, the CI narrowed by roughly a tenth (coefficient 0.231, stderr 0.039, n = 51). While checking residual autocorrelation for cell10, the coefficient tracked epoch count more closely than duration (coefficient 0.207, stderr 0.025, n = 53). While auditing the holding potential column for cell23, the coefficient tracked epoch count more closely than duration (coefficient 0.094, stderr 0.018, n = 51). Noted and moved on; it does not change the decision.

### Step 2: comparing per-cell orderings

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell20    0.250  0.016   0.219  0.281  39        500
cell14    0.138  0.012   0.115  0.161  39        1000
cell15    0.193  0.017   0.159  0.227  51        500
cell21    0.136  0.033   0.071  0.201  48        4000
cell24    0.222  0.020   0.183  0.262  54        500
cell12    0.105  0.030   0.045  0.164  40        1000
cell23    0.118  0.039   0.042  0.195  43        2000
cell09    0.218  0.013   0.192  0.243  50        500
cell03    0.259  0.027   0.205  0.313  43        4000
cell01    0.111  0.029   0.054  0.169  38        2000
cell12    0.191  0.026   0.140  0.243  53        1000
cell13    0.143  0.021   0.102  0.184  53        1000
cell01    0.217  0.014   0.190  0.244  57        2000
cell23    0.158  0.021   0.117  0.198  45        4000
```

While fitting the one-lag kernel for cell24, the coefficient tracked epoch count more closely than duration (coefficient 0.087, stderr 0.042, n = 58). While checking residual autocorrelation for cell23, the CI narrowed by roughly a tenth (coefficient 0.268, stderr 0.012, n = 52). While re-exporting the raw traces for cell14, nothing in the figure changed at print size (coefficient 0.114, stderr 0.020, n = 58). While bootstrapping the CI for cell24, the ordering of cells was preserved (coefficient 0.106, stderr 0.027, n = 43).

While auditing the holding potential column for cell06, the ordering of cells was preserved (coefficient 0.150, stderr 0.016, n = 45). While segmenting epochs for cell07, the estimate moved less than one standard error (coefficient 0.227, stderr 0.047, n = 38). While auditing the holding potential column for cell13, the CI narrowed by roughly a tenth (coefficient 0.085, stderr 0.011, n = 50). Flagging it so it does not get rediscovered next week.

While auditing the holding potential column for cell24, the estimate moved less than one standard error (coefficient 0.114, stderr 0.022, n = 51). While fitting the one-lag kernel for cell03, the ordering of cells was preserved (coefficient 0.240, stderr 0.025, n = 38). While comparing per-cell orderings for cell03, two cells fell out of the usable range (coefficient 0.197, stderr 0.047, n = 47).

### Step 3: bootstrapping the CI

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell04    0.180  0.023   0.134  0.226  40        1000
cell09    0.275  0.037   0.202  0.347  45        500
cell24    0.147  0.030   0.089  0.205  53        2000
cell08    0.217  0.033   0.152  0.282  55        500
cell07    0.302  0.030   0.243  0.362  39        2000
cell12    0.251  0.036   0.180  0.321  54        4000
cell08    0.144  0.019   0.108  0.181  49        1000
cell20    0.269  0.017   0.236  0.302  39        2000
cell18    0.130  0.030   0.071  0.188  58        2000
cell23    0.200  0.022   0.156  0.244  43        500
```

While comparing per-cell orderings for cell07, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.218, stderr 0.032, n = 47). While bootstrapping the CI for cell16, the estimate moved less than one standard error (coefficient 0.150, stderr 0.015, n = 55). While checking residual autocorrelation for cell03, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.209, stderr 0.013, n = 38). While auditing the holding potential column for cell21, the coefficient tracked epoch count more closely than duration (coefficient 0.195, stderr 0.046, n = 57). While re-exporting the raw traces for cell09, the CI narrowed by roughly a tenth (coefficient 0.169, stderr 0.024, n = 49). While checking residual autocorrelation for cell17, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.191, stderr 0.041, n = 57). Worth noting for the writeup, though not a result on its own.

While re-exporting the raw traces for cell05, the CI narrowed by roughly a tenth (coefficient 0.122, stderr 0.013, n = 44). While checking residual autocorrelation for cell05, nothing in the figure changed at print size (coefficient 0.299, stderr 0.022, n = 57). While segmenting epochs for cell17, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.116, stderr 0.039, n = 53).

While comparing per-cell orderings for cell12, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.290, stderr 0.025, n = 58). While re-running with a tighter segmentation threshold for cell12, the ordering of cells was preserved (coefficient 0.107, stderr 0.042, n = 41). While re-running with a tighter segmentation threshold for cell07, nothing in the figure changed at print size (coefficient 0.305, stderr 0.033, n = 55). While comparing per-cell orderings for cell05, the ordering of cells was preserved (coefficient 0.128, stderr 0.013, n = 45). While re-exporting the raw traces for cell11, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.153, stderr 0.022, n = 50).

### Step 4: auditing the holding potential column

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell02    0.166  0.017   0.131  0.200  38        500
cell23    0.272  0.015   0.242  0.302  49        1000
cell21    0.291  0.020   0.252  0.331  46        4000
cell09    0.146  0.011   0.124  0.169  39        1000
cell14    0.087  0.041   0.007  0.167  53        2000
cell18    0.214  0.027   0.161  0.267  41        2000
```

While auditing the holding potential column for cell16, the coefficient tracked epoch count more closely than duration (coefficient 0.195, stderr 0.024, n = 53). While segmenting epochs for cell10, the CI narrowed by roughly a tenth (coefficient 0.219, stderr 0.026, n = 52). While fitting the one-lag kernel for cell03, the CI narrowed by roughly a tenth (coefficient 0.302, stderr 0.023, n = 49). Noted and moved on; it does not change the decision.

### Step 5: segmenting epochs

While re-running with a tighter segmentation threshold for cell11, the estimate moved less than one standard error (coefficient 0.174, stderr 0.018, n = 50). While checking residual autocorrelation for cell09, the estimate moved less than one standard error (coefficient 0.191, stderr 0.022, n = 43). While re-exporting the raw traces for cell03, nothing in the figure changed at print size (coefficient 0.226, stderr 0.018, n = 43). While fitting the one-lag kernel for cell14, two cells fell out of the usable range (coefficient 0.300, stderr 0.044, n = 46). While auditing the holding potential column for cell21, the estimate moved less than one standard error (coefficient 0.308, stderr 0.033, n = 58). Parking this until the re-segmentation lands.

While fitting the one-lag kernel for cell03, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.092, stderr 0.031, n = 54). While fitting the one-lag kernel for cell22, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.265, stderr 0.034, n = 49). While checking residual autocorrelation for cell02, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.141, stderr 0.011, n = 42). While segmenting epochs for cell19, the coefficient tracked epoch count more closely than duration (coefficient 0.119, stderr 0.014, n = 50). While re-running with a tighter segmentation threshold for cell06, the estimate moved less than one standard error (coefficient 0.151, stderr 0.042, n = 50).

### Step 6: checking residual autocorrelation

While segmenting epochs for cell08, two cells fell out of the usable range (coefficient 0.239, stderr 0.031, n = 51). While segmenting epochs for cell09, the estimate moved less than one standard error (coefficient 0.158, stderr 0.044, n = 42). While re-running with a tighter segmentation threshold for cell02, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.181, stderr 0.014, n = 47). While re-exporting the raw traces for cell10, nothing in the figure changed at print size (coefficient 0.250, stderr 0.049, n = 49). While checking residual autocorrelation for cell12, the coefficient tracked epoch count more closely than duration (coefficient 0.154, stderr 0.040, n = 58). While re-running with a tighter segmentation threshold for cell10, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.123, stderr 0.047, n = 51).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell19    0.104  0.043   0.020  0.188  48        500
cell10    0.098  0.016   0.066  0.131  50        1000
cell03    0.162  0.024   0.114  0.209  55        1000
cell08    0.293  0.047   0.201  0.385  45        4000
cell10    0.269  0.029   0.213  0.325  44        500
cell12    0.250  0.037   0.179  0.322  38        4000
cell17    0.153  0.019   0.116  0.190  51        4000
cell21    0.304  0.016   0.273  0.334  38        1000
cell17    0.174  0.037   0.101  0.247  49        2000
cell24    0.296  0.031   0.236  0.356  56        1000
cell10    0.182  0.027   0.130  0.235  39        4000
cell03    0.259  0.017   0.225  0.293  47        2000
```

### Step 7: comparing per-cell orderings

While segmenting epochs for cell11, the coefficient tracked epoch count more closely than duration (coefficient 0.159, stderr 0.011, n = 38). While auditing the holding potential column for cell12, two cells fell out of the usable range (coefficient 0.169, stderr 0.019, n = 56). While fitting the one-lag kernel for cell10, the estimate moved less than one standard error (coefficient 0.275, stderr 0.041, n = 42). While re-running with a tighter segmentation threshold for cell24, the coefficient tracked epoch count more closely than duration (coefficient 0.164, stderr 0.020, n = 50). While comparing per-cell orderings for cell15, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.150, stderr 0.041, n = 47). While re-exporting the raw traces for cell15, the coefficient tracked epoch count more closely than duration (coefficient 0.279, stderr 0.016, n = 57).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell21    0.221  0.019   0.183  0.259  55        500
cell16    0.217  0.016   0.185  0.249  58        2000
cell19    0.170  0.016   0.139  0.202  39        4000
cell22    0.216  0.023   0.170  0.261  57        4000
cell21    0.220  0.047   0.128  0.311  57        500
cell16    0.129  0.021   0.088  0.170  40        4000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell09    0.281  0.023   0.236  0.327  41        2000
cell02    0.168  0.031   0.107  0.229  45        500
cell01    0.213  0.035   0.145  0.281  45        2000
cell21    0.124  0.046   0.035  0.214  40        2000
cell24    0.272  0.049   0.176  0.367  40        500
cell23    0.306  0.035   0.238  0.374  48        2000
cell19    0.262  0.040   0.185  0.340  39        1000
cell14    0.217  0.024   0.169  0.264  43        4000
cell13    0.184  0.028   0.129  0.238  49        4000
cell02    0.084  0.017   0.050  0.118  40        4000
cell05    0.204  0.010   0.185  0.224  41        1000
cell09    0.148  0.048   0.054  0.242  51        4000
cell13    0.231  0.021   0.190  0.271  54        4000
cell02    0.300  0.045   0.212  0.387  51        1000
```

### Step 8: re-running with a tighter segmentation threshold

While re-exporting the raw traces for cell20, the ordering of cells was preserved (coefficient 0.194, stderr 0.045, n = 52). While comparing per-cell orderings for cell22, the CI narrowed by roughly a tenth (coefficient 0.151, stderr 0.019, n = 50). While auditing the holding potential column for cell02, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.250, stderr 0.027, n = 58). While fitting the one-lag kernel for cell14, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.277, stderr 0.032, n = 52). While comparing per-cell orderings for cell16, two cells fell out of the usable range (coefficient 0.277, stderr 0.015, n = 56).

While re-running with a tighter segmentation threshold for cell10, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.249, stderr 0.033, n = 52). While bootstrapping the CI for cell18, the estimate moved less than one standard error (coefficient 0.237, stderr 0.028, n = 44). While checking residual autocorrelation for cell09, the coefficient tracked epoch count more closely than duration (coefficient 0.286, stderr 0.050, n = 51). While re-running with a tighter segmentation threshold for cell24, the CI narrowed by roughly a tenth (coefficient 0.159, stderr 0.016, n = 41).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell11    0.291  0.017   0.257  0.324  52        2000
cell09    0.094  0.029   0.037  0.151  39        500
cell08    0.157  0.048   0.063  0.251  56        1000
cell21    0.122  0.031   0.062  0.182  57        4000
cell06    0.262  0.026   0.211  0.313  51        2000
cell06    0.255  0.013   0.229  0.281  41        4000
cell19    0.271  0.049   0.175  0.367  52        1000
cell07    0.305  0.013   0.279  0.331  48        500
cell16    0.081  0.036   0.011  0.152  46        1000
```

### Step 9: bootstrapping the CI

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell12    0.229  0.032   0.166  0.292  44        500
cell08    0.195  0.034   0.129  0.262  49        1000
cell10    0.239  0.047   0.147  0.332  54        1000
cell20    0.168  0.039   0.092  0.245  49        4000
cell22    0.285  0.047   0.194  0.376  41        2000
cell01    0.143  0.030   0.085  0.201  39        2000
cell11    0.232  0.031   0.170  0.293  46        1000
cell09    0.267  0.021   0.226  0.308  56        1000
cell03    0.224  0.037   0.152  0.296  54        1000
cell03    0.229  0.030   0.169  0.289  48        2000
cell06    0.308  0.020   0.269  0.348  45        2000
cell03    0.215  0.029   0.157  0.272  51        1000
```

```python
coefs = fit_per_cell(rows, threshold=0.71)
lo, hi = ci(coefs, seed=40)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While auditing the holding potential column for cell08, the ordering of cells was preserved (coefficient 0.257, stderr 0.047, n = 50). While comparing per-cell orderings for cell06, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.113, stderr 0.025, n = 57). While fitting the one-lag kernel for cell06, the coefficient tracked epoch count more closely than duration (coefficient 0.262, stderr 0.019, n = 39).

### Step 10: fitting the one-lag kernel

While bootstrapping the CI for cell13, the CI narrowed by roughly a tenth (coefficient 0.138, stderr 0.045, n = 55). While checking residual autocorrelation for cell24, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.125, stderr 0.016, n = 49). While re-exporting the raw traces for cell13, the coefficient tracked epoch count more closely than duration (coefficient 0.161, stderr 0.015, n = 46). While comparing per-cell orderings for cell14, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.185, stderr 0.028, n = 41). While segmenting epochs for cell04, the estimate moved less than one standard error (coefficient 0.132, stderr 0.044, n = 54).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell19    0.113  0.034   0.047  0.180  55        500
cell11    0.106  0.047   0.014  0.199  40        2000
cell07    0.289  0.022   0.247  0.332  47        2000
cell11    0.109  0.034   0.043  0.176  45        500
cell03    0.301  0.043   0.217  0.385  46        4000
cell07    0.213  0.038   0.139  0.286  47        1000
cell08    0.180  0.025   0.130  0.229  57        2000
cell18    0.286  0.035   0.218  0.355  43        4000
cell02    0.208  0.045   0.119  0.297  39        2000
```

While segmenting epochs for cell23, the CI narrowed by roughly a tenth (coefficient 0.144, stderr 0.010, n = 40). While fitting the one-lag kernel for cell09, the coefficient tracked epoch count more closely than duration (coefficient 0.213, stderr 0.029, n = 41). While re-exporting the raw traces for cell17, the coefficient tracked epoch count more closely than duration (coefficient 0.191, stderr 0.016, n = 40).

### Step 11: segmenting epochs

While fitting the one-lag kernel for cell13, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.237, stderr 0.022, n = 53). While comparing per-cell orderings for cell18, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.203, stderr 0.033, n = 38). While auditing the holding potential column for cell10, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.253, stderr 0.036, n = 56). While segmenting epochs for cell13, the coefficient tracked epoch count more closely than duration (coefficient 0.082, stderr 0.012, n = 53). Noted and moved on; it does not change the decision.

While comparing per-cell orderings for cell11, nothing in the figure changed at print size (coefficient 0.256, stderr 0.042, n = 47). While auditing the holding potential column for cell04, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.199, stderr 0.027, n = 51). While re-running with a tighter segmentation threshold for cell05, the estimate moved less than one standard error (coefficient 0.245, stderr 0.041, n = 53).

### Step 12: bootstrapping the CI

While fitting the one-lag kernel for cell21, the coefficient tracked epoch count more closely than duration (coefficient 0.162, stderr 0.013, n = 44). While auditing the holding potential column for cell19, the coefficient tracked epoch count more closely than duration (coefficient 0.275, stderr 0.044, n = 55). While checking residual autocorrelation for cell21, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.135, stderr 0.032, n = 46). While comparing per-cell orderings for cell06, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.186, stderr 0.018, n = 42).

While auditing the holding potential column for cell05, the estimate moved less than one standard error (coefficient 0.302, stderr 0.021, n = 43). While re-running with a tighter segmentation threshold for cell16, the coefficient tracked epoch count more closely than duration (coefficient 0.183, stderr 0.048, n = 57). While re-running with a tighter segmentation threshold for cell24, nothing in the figure changed at print size (coefficient 0.262, stderr 0.040, n = 58). While bootstrapping the CI for cell22, two cells fell out of the usable range (coefficient 0.248, stderr 0.029, n = 50). While fitting the one-lag kernel for cell23, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.155, stderr 0.049, n = 55).

### Step 13: segmenting epochs

While comparing per-cell orderings for cell06, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.098, stderr 0.048, n = 48). While auditing the holding potential column for cell04, the CI narrowed by roughly a tenth (coefficient 0.177, stderr 0.028, n = 41). While bootstrapping the CI for cell11, the ordering of cells was preserved (coefficient 0.309, stderr 0.017, n = 49). This is the part that will need a real statistical argument.

```python
coefs = fit_per_cell(rows, threshold=0.59)
lo, hi = ci(coefs, seed=35)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 14: bootstrapping the CI

While comparing per-cell orderings for cell18, the coefficient tracked epoch count more closely than duration (coefficient 0.252, stderr 0.039, n = 43). While comparing per-cell orderings for cell05, two cells fell out of the usable range (coefficient 0.131, stderr 0.031, n = 39). While segmenting epochs for cell13, the ordering of cells was preserved (coefficient 0.308, stderr 0.028, n = 49). While fitting the one-lag kernel for cell07, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.106, stderr 0.037, n = 53). While segmenting epochs for cell13, the coefficient tracked epoch count more closely than duration (coefficient 0.216, stderr 0.038, n = 44).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell05    0.210  0.047   0.119  0.302  41        4000
cell21    0.224  0.045   0.136  0.312  54        500
cell18    0.093  0.049   -0.003  0.189  46        2000
cell11    0.161  0.023   0.116  0.207  49        500
cell09    0.099  0.020   0.059  0.138  45        500
cell08    0.108  0.049   0.013  0.204  51        1000
```

While checking residual autocorrelation for cell13, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.189, stderr 0.026, n = 38). While comparing per-cell orderings for cell06, the CI narrowed by roughly a tenth (coefficient 0.135, stderr 0.029, n = 52). While checking residual autocorrelation for cell19, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.211, stderr 0.049, n = 49). While checking residual autocorrelation for cell05, nothing in the figure changed at print size (coefficient 0.191, stderr 0.029, n = 41). While bootstrapping the CI for cell19, the ordering of cells was preserved (coefficient 0.189, stderr 0.023, n = 55). This is the part that will need a real statistical argument.

While bootstrapping the CI for cell09, the coefficient tracked epoch count more closely than duration (coefficient 0.087, stderr 0.045, n = 55). While re-exporting the raw traces for cell13, the ordering of cells was preserved (coefficient 0.093, stderr 0.016, n = 54). While re-running with a tighter segmentation threshold for cell23, the estimate moved less than one standard error (coefficient 0.291, stderr 0.032, n = 45). While auditing the holding potential column for cell23, two cells fell out of the usable range (coefficient 0.248, stderr 0.048, n = 41). Worth noting for the writeup, though not a result on its own.

### Step 15: bootstrapping the CI

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell03    0.295  0.044   0.208  0.382  53        500
cell13    0.163  0.039   0.087  0.239  44        500
cell19    0.196  0.017   0.162  0.230  53        500
cell04    0.183  0.033   0.119  0.247  57        4000
cell12    0.164  0.023   0.118  0.210  58        500
cell07    0.302  0.039   0.227  0.378  41        1000
cell15    0.088  0.044   0.002  0.173  40        2000
cell09    0.154  0.032   0.091  0.217  53        4000
cell01    0.252  0.041   0.171  0.332  57        2000
cell22    0.120  0.021   0.080  0.161  42        4000
cell23    0.220  0.024   0.172  0.267  46        2000
cell07    0.289  0.035   0.220  0.358  57        4000
```

While bootstrapping the CI for cell05, the estimate moved less than one standard error (coefficient 0.291, stderr 0.044, n = 52). While re-running with a tighter segmentation threshold for cell07, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.082, stderr 0.026, n = 49). While re-exporting the raw traces for cell22, the estimate moved less than one standard error (coefficient 0.101, stderr 0.019, n = 54). While auditing the holding potential column for cell23, the coefficient tracked epoch count more closely than duration (coefficient 0.192, stderr 0.037, n = 53). While re-running with a tighter segmentation threshold for cell11, two cells fell out of the usable range (coefficient 0.141, stderr 0.016, n = 43). Worth noting for the writeup, though not a result on its own.

### Step 16: segmenting epochs

```python
coefs = fit_per_cell(rows, threshold=0.45)
lo, hi = ci(coefs, seed=13)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell10    0.267  0.023   0.223  0.312  40        2000
cell02    0.184  0.027   0.130  0.237  54        2000
cell01    0.116  0.019   0.080  0.152  55        500
cell19    0.233  0.035   0.165  0.301  54        2000
cell11    0.266  0.026   0.215  0.316  42        4000
cell04    0.297  0.042   0.214  0.381  42        4000
cell18    0.228  0.021   0.187  0.269  54        4000
cell13    0.270  0.029   0.212  0.327  46        500
cell07    0.128  0.040   0.049  0.207  58        500
cell01    0.264  0.018   0.228  0.299  40        4000
cell05    0.179  0.044   0.093  0.264  40        500
cell07    0.210  0.049   0.113  0.306  47        4000
cell13    0.141  0.011   0.120  0.162  47        500
cell09    0.141  0.033   0.077  0.205  58        2000
```

```python
coefs = fit_per_cell(rows, threshold=0.54)
lo, hi = ci(coefs, seed=35)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While bootstrapping the CI for cell06, the CI narrowed by roughly a tenth (coefficient 0.153, stderr 0.030, n = 52). While comparing per-cell orderings for cell04, the estimate moved less than one standard error (coefficient 0.231, stderr 0.031, n = 43). While comparing per-cell orderings for cell24, the coefficient tracked epoch count more closely than duration (coefficient 0.304, stderr 0.011, n = 55). While re-running with a tighter segmentation threshold for cell06, nothing in the figure changed at print size (coefficient 0.198, stderr 0.033, n = 55). While re-running with a tighter segmentation threshold for cell17, the coefficient tracked epoch count more closely than duration (coefficient 0.191, stderr 0.045, n = 44). While fitting the one-lag kernel for cell15, the coefficient tracked epoch count more closely than duration (coefficient 0.227, stderr 0.048, n = 49). Worth noting for the writeup, though not a result on its own.

### Step 17: bootstrapping the CI

While bootstrapping the CI for cell13, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.128, stderr 0.019, n = 41). While re-running with a tighter segmentation threshold for cell18, the estimate moved less than one standard error (coefficient 0.211, stderr 0.047, n = 46). While auditing the holding potential column for cell06, the CI narrowed by roughly a tenth (coefficient 0.123, stderr 0.043, n = 45). While comparing per-cell orderings for cell04, the coefficient tracked epoch count more closely than duration (coefficient 0.238, stderr 0.031, n = 39).

While bootstrapping the CI for cell22, the coefficient tracked epoch count more closely than duration (coefficient 0.300, stderr 0.031, n = 57). While auditing the holding potential column for cell17, nothing in the figure changed at print size (coefficient 0.164, stderr 0.032, n = 46). While bootstrapping the CI for cell07, the coefficient tracked epoch count more closely than duration (coefficient 0.224, stderr 0.031, n = 48). While checking residual autocorrelation for cell16, the coefficient tracked epoch count more closely than duration (coefficient 0.190, stderr 0.037, n = 46). While comparing per-cell orderings for cell04, two cells fell out of the usable range (coefficient 0.297, stderr 0.016, n = 56). Flagging it so it does not get rediscovered next week.

### Step 18: checking residual autocorrelation

While re-running with a tighter segmentation threshold for cell13, the CI narrowed by roughly a tenth (coefficient 0.106, stderr 0.013, n = 49). While comparing per-cell orderings for cell21, the estimate moved less than one standard error (coefficient 0.108, stderr 0.016, n = 51). While re-running with a tighter segmentation threshold for cell01, nothing in the figure changed at print size (coefficient 0.124, stderr 0.024, n = 51). While checking residual autocorrelation for cell24, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.129, stderr 0.031, n = 46). While re-exporting the raw traces for cell16, nothing in the figure changed at print size (coefficient 0.236, stderr 0.046, n = 58). Noted and moved on; it does not change the decision.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell11    0.117  0.011   0.095  0.140  40        2000
cell02    0.087  0.022   0.044  0.130  44        2000
cell04    0.160  0.049   0.065  0.255  56        2000
cell18    0.171  0.017   0.137  0.204  41        1000
cell23    0.228  0.016   0.197  0.259  40        500
cell11    0.112  0.044   0.026  0.197  48        4000
cell21    0.081  0.012   0.058  0.104  46        500
cell15    0.091  0.040   0.013  0.169  48        500
cell07    0.209  0.011   0.186  0.231  50        500
cell20    0.112  0.041   0.031  0.193  51        1000
cell17    0.256  0.033   0.190  0.321  45        4000
```

### Step 19: segmenting epochs

While auditing the holding potential column for cell05, two cells fell out of the usable range (coefficient 0.145, stderr 0.019, n = 48). While bootstrapping the CI for cell18, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.088, stderr 0.042, n = 58). While auditing the holding potential column for cell19, the coefficient tracked epoch count more closely than duration (coefficient 0.236, stderr 0.012, n = 54). While segmenting epochs for cell12, the coefficient tracked epoch count more closely than duration (coefficient 0.302, stderr 0.018, n = 57). While re-exporting the raw traces for cell01, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.217, stderr 0.022, n = 42). While segmenting epochs for cell03, two cells fell out of the usable range (coefficient 0.174, stderr 0.022, n = 48). Noted and moved on; it does not change the decision.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell16    0.269  0.015   0.239  0.299  53        4000
cell08    0.251  0.026   0.199  0.302  39        4000
cell12    0.296  0.042   0.214  0.378  56        4000
cell12    0.211  0.040   0.132  0.291  39        500
cell02    0.273  0.024   0.227  0.319  46        500
cell17    0.128  0.040   0.050  0.205  56        4000
cell16    0.110  0.050   0.013  0.208  40        2000
cell23    0.211  0.034   0.145  0.278  51        4000
cell14    0.239  0.028   0.184  0.293  41        1000
cell13    0.307  0.030   0.248  0.367  48        4000
cell15    0.277  0.022   0.234  0.319  43        500
cell03    0.269  0.022   0.226  0.313  53        4000
cell24    0.202  0.025   0.153  0.251  40        4000
```

While fitting the one-lag kernel for cell24, the estimate moved less than one standard error (coefficient 0.239, stderr 0.024, n = 51). While segmenting epochs for cell24, the estimate moved less than one standard error (coefficient 0.192, stderr 0.034, n = 40). While re-exporting the raw traces for cell24, two cells fell out of the usable range (coefficient 0.091, stderr 0.048, n = 40). While re-running with a tighter segmentation threshold for cell08, two cells fell out of the usable range (coefficient 0.190, stderr 0.017, n = 44). While bootstrapping the CI for cell13, nothing in the figure changed at print size (coefficient 0.197, stderr 0.046, n = 52). While re-exporting the raw traces for cell04, two cells fell out of the usable range (coefficient 0.267, stderr 0.015, n = 49).

### Step 20: fitting the one-lag kernel

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell03    0.145  0.050   0.047  0.242  40        500
cell14    0.146  0.025   0.097  0.195  39        500
cell10    0.237  0.025   0.188  0.287  56        500
cell08    0.237  0.029   0.180  0.293  43        2000
cell20    0.202  0.033   0.138  0.265  53        4000
cell14    0.112  0.025   0.062  0.161  58        4000
cell22    0.187  0.021   0.145  0.229  40        4000
cell03    0.285  0.027   0.233  0.337  44        500
cell18    0.085  0.039   0.009  0.162  53        4000
cell12    0.265  0.042   0.183  0.348  56        500
cell12    0.206  0.042   0.124  0.288  47        4000
cell09    0.126  0.042   0.044  0.209  58        500
cell09    0.117  0.044   0.031  0.204  45        4000
cell12    0.289  0.025   0.240  0.338  57        1000
```

While auditing the holding potential column for cell17, two cells fell out of the usable range (coefficient 0.234, stderr 0.038, n = 55). While fitting the one-lag kernel for cell13, the estimate moved less than one standard error (coefficient 0.141, stderr 0.046, n = 55). While auditing the holding potential column for cell06, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.246, stderr 0.020, n = 42). This is the part that will need a real statistical argument.

```python
coefs = fit_per_cell(rows, threshold=0.38)
lo, hi = ci(coefs, seed=44)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 21: fitting the one-lag kernel

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell15    0.277  0.041   0.196  0.357  48        1000
cell19    0.183  0.044   0.097  0.268  39        500
cell05    0.268  0.013   0.243  0.293  50        4000
cell17    0.090  0.028   0.036  0.144  51        500
cell09    0.236  0.037   0.163  0.309  43        4000
cell20    0.139  0.014   0.111  0.168  45        1000
cell07    0.094  0.017   0.061  0.127  49        4000
cell22    0.204  0.044   0.118  0.290  47        1000
cell04    0.131  0.022   0.088  0.175  39        1000
cell23    0.244  0.016   0.212  0.277  38        4000
cell10    0.264  0.030   0.205  0.323  38        1000
```

While comparing per-cell orderings for cell18, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.209, stderr 0.038, n = 51). While re-running with a tighter segmentation threshold for cell02, nothing in the figure changed at print size (coefficient 0.241, stderr 0.022, n = 51). While segmenting epochs for cell10, the estimate moved less than one standard error (coefficient 0.295, stderr 0.037, n = 58). While checking residual autocorrelation for cell03, nothing in the figure changed at print size (coefficient 0.307, stderr 0.037, n = 50). While re-running with a tighter segmentation threshold for cell21, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.225, stderr 0.043, n = 39).

While comparing per-cell orderings for cell01, the ordering of cells was preserved (coefficient 0.206, stderr 0.028, n = 41). While auditing the holding potential column for cell02, the ordering of cells was preserved (coefficient 0.094, stderr 0.027, n = 56). While auditing the holding potential column for cell07, the coefficient tracked epoch count more closely than duration (coefficient 0.123, stderr 0.020, n = 51). While re-exporting the raw traces for cell13, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.195, stderr 0.029, n = 44). While checking residual autocorrelation for cell24, the CI narrowed by roughly a tenth (coefficient 0.117, stderr 0.044, n = 39). This is the part that will need a real statistical argument.

### Step 22: checking residual autocorrelation

While auditing the holding potential column for cell12, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.084, stderr 0.036, n = 56). While segmenting epochs for cell02, the estimate moved less than one standard error (coefficient 0.141, stderr 0.044, n = 41). While fitting the one-lag kernel for cell05, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.154, stderr 0.022, n = 40). While comparing per-cell orderings for cell11, the CI narrowed by roughly a tenth (coefficient 0.242, stderr 0.020, n = 57).

While re-exporting the raw traces for cell11, nothing in the figure changed at print size (coefficient 0.281, stderr 0.047, n = 45). While segmenting epochs for cell20, the CI narrowed by roughly a tenth (coefficient 0.235, stderr 0.027, n = 40). While re-exporting the raw traces for cell05, nothing in the figure changed at print size (coefficient 0.118, stderr 0.023, n = 42). Flagging it so it does not get rediscovered next week.

### Step 23: bootstrapping the CI

While segmenting epochs for cell02, two cells fell out of the usable range (coefficient 0.225, stderr 0.044, n = 43). While segmenting epochs for cell07, the CI narrowed by roughly a tenth (coefficient 0.199, stderr 0.015, n = 53). While segmenting epochs for cell08, two cells fell out of the usable range (coefficient 0.139, stderr 0.045, n = 44). While checking residual autocorrelation for cell13, two cells fell out of the usable range (coefficient 0.174, stderr 0.019, n = 38). While bootstrapping the CI for cell02, the CI narrowed by roughly a tenth (coefficient 0.259, stderr 0.050, n = 39). While comparing per-cell orderings for cell19, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.146, stderr 0.030, n = 58). Flagging it so it does not get rediscovered next week.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell04    0.086  0.030   0.028  0.144  50        500
cell18    0.146  0.011   0.126  0.167  50        4000
cell09    0.103  0.021   0.062  0.143  47        500
cell16    0.116  0.025   0.067  0.165  51        500
cell01    0.222  0.011   0.202  0.243  45        1000
cell16    0.286  0.024   0.239  0.334  54        2000
cell19    0.162  0.033   0.098  0.226  51        1000
cell20    0.270  0.044   0.185  0.356  50        4000
cell21    0.144  0.039   0.067  0.220  44        2000
cell14    0.083  0.018   0.047  0.119  50        500
cell22    0.133  0.048   0.039  0.228  55        500
```

### Step 24: comparing per-cell orderings

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell23    0.186  0.030   0.128  0.244  50        2000
cell14    0.146  0.039   0.069  0.223  44        500
cell17    0.221  0.031   0.160  0.282  48        2000
cell15    0.085  0.030   0.026  0.143  41        2000
cell16    0.156  0.011   0.135  0.177  53        500
cell13    0.175  0.046   0.085  0.265  51        2000
cell20    0.205  0.029   0.148  0.262  41        2000
cell02    0.210  0.023   0.165  0.256  53        4000
cell19    0.308  0.016   0.277  0.338  55        1000
cell02    0.088  0.047   -0.005  0.180  47        1000
cell02    0.189  0.015   0.160  0.218  53        1000
```

While re-running with a tighter segmentation threshold for cell14, the estimate moved less than one standard error (coefficient 0.161, stderr 0.015, n = 41). While segmenting epochs for cell17, the ordering of cells was preserved (coefficient 0.155, stderr 0.022, n = 47). While re-exporting the raw traces for cell21, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.139, stderr 0.014, n = 53). While checking residual autocorrelation for cell24, nothing in the figure changed at print size (coefficient 0.305, stderr 0.017, n = 47). While re-exporting the raw traces for cell17, the CI narrowed by roughly a tenth (coefficient 0.127, stderr 0.033, n = 40). While auditing the holding potential column for cell11, the estimate moved less than one standard error (coefficient 0.165, stderr 0.041, n = 41). Noted and moved on; it does not change the decision.

### Step 25: checking residual autocorrelation

While checking residual autocorrelation for cell09, the ordering of cells was preserved (coefficient 0.255, stderr 0.010, n = 38). While segmenting epochs for cell21, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.152, stderr 0.017, n = 57). While checking residual autocorrelation for cell21, the estimate moved less than one standard error (coefficient 0.111, stderr 0.036, n = 38). While checking residual autocorrelation for cell23, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.139, stderr 0.017, n = 44). While comparing per-cell orderings for cell01, two cells fell out of the usable range (coefficient 0.308, stderr 0.011, n = 40). This is the part that will need a real statistical argument.

While comparing per-cell orderings for cell09, two cells fell out of the usable range (coefficient 0.201, stderr 0.041, n = 51). While fitting the one-lag kernel for cell24, two cells fell out of the usable range (coefficient 0.144, stderr 0.043, n = 40). While auditing the holding potential column for cell21, the coefficient tracked epoch count more closely than duration (coefficient 0.285, stderr 0.034, n = 46). While comparing per-cell orderings for cell13, the ordering of cells was preserved (coefficient 0.149, stderr 0.046, n = 47). While re-exporting the raw traces for cell11, the ordering of cells was preserved (coefficient 0.147, stderr 0.031, n = 41). This is the part that will need a real statistical argument.

While checking residual autocorrelation for cell10, the ordering of cells was preserved (coefficient 0.106, stderr 0.040, n = 49). While auditing the holding potential column for cell13, nothing in the figure changed at print size (coefficient 0.208, stderr 0.036, n = 44). While comparing per-cell orderings for cell08, the CI narrowed by roughly a tenth (coefficient 0.231, stderr 0.045, n = 40). While comparing per-cell orderings for cell22, two cells fell out of the usable range (coefficient 0.116, stderr 0.048, n = 49). While fitting the one-lag kernel for cell02, the ordering of cells was preserved (coefficient 0.104, stderr 0.041, n = 47). While bootstrapping the CI for cell07, the CI narrowed by roughly a tenth (coefficient 0.170, stderr 0.035, n = 46).

### Step 26: checking residual autocorrelation

While re-exporting the raw traces for cell07, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.099, stderr 0.021, n = 56). While comparing per-cell orderings for cell08, the CI narrowed by roughly a tenth (coefficient 0.112, stderr 0.021, n = 50). While segmenting epochs for cell10, the CI narrowed by roughly a tenth (coefficient 0.113, stderr 0.035, n = 39). This is the part that will need a real statistical argument.

While segmenting epochs for cell04, nothing in the figure changed at print size (coefficient 0.275, stderr 0.021, n = 55). While re-exporting the raw traces for cell20, nothing in the figure changed at print size (coefficient 0.174, stderr 0.011, n = 40). While comparing per-cell orderings for cell19, nothing in the figure changed at print size (coefficient 0.161, stderr 0.043, n = 57). Worth noting for the writeup, though not a result on its own.

```python
coefs = fit_per_cell(rows, threshold=0.49)
lo, hi = ci(coefs, seed=22)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 27: comparing per-cell orderings

While re-running with a tighter segmentation threshold for cell15, the estimate moved less than one standard error (coefficient 0.265, stderr 0.012, n = 58). While re-running with a tighter segmentation threshold for cell23, the coefficient tracked epoch count more closely than duration (coefficient 0.260, stderr 0.042, n = 57). While re-running with a tighter segmentation threshold for cell09, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.085, stderr 0.049, n = 56).

```python
coefs = fit_per_cell(rows, threshold=0.41)
lo, hi = ci(coefs, seed=67)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While comparing per-cell orderings for cell18, nothing in the figure changed at print size (coefficient 0.287, stderr 0.026, n = 50). While re-exporting the raw traces for cell03, nothing in the figure changed at print size (coefficient 0.102, stderr 0.047, n = 49). While comparing per-cell orderings for cell09, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.304, stderr 0.014, n = 41). While fitting the one-lag kernel for cell17, the ordering of cells was preserved (coefficient 0.160, stderr 0.029, n = 46).

While auditing the holding potential column for cell20, the coefficient tracked epoch count more closely than duration (coefficient 0.164, stderr 0.039, n = 39). While fitting the one-lag kernel for cell17, the coefficient tracked epoch count more closely than duration (coefficient 0.277, stderr 0.027, n = 38). While re-exporting the raw traces for cell15, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.140, stderr 0.044, n = 48). While auditing the holding potential column for cell07, the CI narrowed by roughly a tenth (coefficient 0.300, stderr 0.048, n = 47). While auditing the holding potential column for cell17, two cells fell out of the usable range (coefficient 0.292, stderr 0.036, n = 55).

### Step 28: bootstrapping the CI

While checking residual autocorrelation for cell09, nothing in the figure changed at print size (coefficient 0.273, stderr 0.029, n = 58). While segmenting epochs for cell23, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.133, stderr 0.012, n = 43). While comparing per-cell orderings for cell20, the ordering of cells was preserved (coefficient 0.178, stderr 0.010, n = 46). While re-running with a tighter segmentation threshold for cell15, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.117, stderr 0.012, n = 47). While re-exporting the raw traces for cell21, nothing in the figure changed at print size (coefficient 0.142, stderr 0.012, n = 38). While bootstrapping the CI for cell09, the coefficient tracked epoch count more closely than duration (coefficient 0.260, stderr 0.019, n = 45). This is the part that will need a real statistical argument.

While checking residual autocorrelation for cell10, the CI narrowed by roughly a tenth (coefficient 0.177, stderr 0.013, n = 42). While re-exporting the raw traces for cell13, the CI narrowed by roughly a tenth (coefficient 0.292, stderr 0.015, n = 55). While re-running with a tighter segmentation threshold for cell05, the estimate moved less than one standard error (coefficient 0.117, stderr 0.021, n = 58). While bootstrapping the CI for cell04, nothing in the figure changed at print size (coefficient 0.222, stderr 0.049, n = 39). While auditing the holding potential column for cell12, the CI narrowed by roughly a tenth (coefficient 0.101, stderr 0.026, n = 41). While re-exporting the raw traces for cell11, the ordering of cells was preserved (coefficient 0.187, stderr 0.042, n = 39). This is the part that will need a real statistical argument.

### Step 29: comparing per-cell orderings

While comparing per-cell orderings for cell10, the ordering of cells was preserved (coefficient 0.175, stderr 0.041, n = 49). While auditing the holding potential column for cell23, the estimate moved less than one standard error (coefficient 0.127, stderr 0.031, n = 53). While re-running with a tighter segmentation threshold for cell24, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.171, stderr 0.029, n = 45). While segmenting epochs for cell01, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.292, stderr 0.026, n = 48).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell14    0.158  0.037   0.086  0.230  48        4000
cell24    0.283  0.022   0.241  0.326  39        1000
cell15    0.175  0.010   0.155  0.195  38        4000
cell20    0.213  0.019   0.175  0.251  57        4000
cell13    0.171  0.029   0.114  0.228  42        4000
cell24    0.289  0.027   0.235  0.342  58        500
```

### Step 30: fitting the one-lag kernel

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell05    0.241  0.026   0.190  0.292  51        1000
cell21    0.201  0.032   0.138  0.264  53        1000
cell09    0.293  0.010   0.273  0.313  47        2000
cell19    0.241  0.030   0.183  0.299  50        2000
cell23    0.114  0.043   0.031  0.198  47        2000
cell02    0.280  0.024   0.232  0.328  55        1000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell18    0.157  0.018   0.122  0.192  42        500
cell05    0.244  0.040   0.165  0.323  54        500
cell17    0.237  0.019   0.199  0.275  43        1000
cell16    0.254  0.014   0.227  0.280  55        1000
cell01    0.090  0.028   0.035  0.144  43        500
cell18    0.140  0.025   0.092  0.188  41        2000
cell12    0.106  0.014   0.078  0.134  53        500
cell01    0.167  0.018   0.133  0.202  57        500
cell03    0.118  0.013   0.092  0.144  55        500
cell17    0.292  0.019   0.254  0.330  49        4000
cell15    0.208  0.022   0.165  0.251  54        500
cell24    0.224  0.014   0.196  0.251  57        2000
```

```python
coefs = fit_per_cell(rows, threshold=0.54)
lo, hi = ci(coefs, seed=43)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```python
coefs = fit_per_cell(rows, threshold=0.59)
lo, hi = ci(coefs, seed=34)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 31: bootstrapping the CI

While re-exporting the raw traces for cell22, nothing in the figure changed at print size (coefficient 0.127, stderr 0.035, n = 51). While re-exporting the raw traces for cell07, the coefficient tracked epoch count more closely than duration (coefficient 0.266, stderr 0.048, n = 40). While fitting the one-lag kernel for cell05, the ordering of cells was preserved (coefficient 0.281, stderr 0.028, n = 57). While re-running with a tighter segmentation threshold for cell11, the CI narrowed by roughly a tenth (coefficient 0.106, stderr 0.034, n = 51). While comparing per-cell orderings for cell06, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.101, stderr 0.014, n = 51). While checking residual autocorrelation for cell02, two cells fell out of the usable range (coefficient 0.217, stderr 0.015, n = 38).

While re-exporting the raw traces for cell18, the ordering of cells was preserved (coefficient 0.246, stderr 0.021, n = 51). While segmenting epochs for cell14, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.241, stderr 0.040, n = 47). While fitting the one-lag kernel for cell16, nothing in the figure changed at print size (coefficient 0.253, stderr 0.040, n = 47). While bootstrapping the CI for cell23, two cells fell out of the usable range (coefficient 0.298, stderr 0.047, n = 51).

### Step 32: bootstrapping the CI

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell09    0.158  0.043   0.073  0.243  47        1000
cell18    0.279  0.014   0.252  0.306  40        1000
cell02    0.187  0.030   0.129  0.246  50        4000
cell05    0.162  0.017   0.129  0.194  47        2000
cell07    0.261  0.033   0.196  0.325  58        1000
cell21    0.181  0.014   0.155  0.208  45        4000
cell06    0.193  0.039   0.116  0.269  53        2000
cell10    0.166  0.022   0.123  0.208  50        500
cell18    0.219  0.039   0.143  0.295  46        500
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell08    0.108  0.022   0.065  0.151  44        500
cell10    0.282  0.039   0.207  0.358  44        2000
cell21    0.297  0.035   0.228  0.366  53        2000
cell13    0.259  0.022   0.216  0.302  54        1000
cell23    0.234  0.034   0.168  0.301  58        500
cell19    0.183  0.012   0.159  0.206  49        4000
cell15    0.174  0.035   0.105  0.243  58        2000
```

While re-running with a tighter segmentation threshold for cell13, nothing in the figure changed at print size (coefficient 0.248, stderr 0.018, n = 58). While re-running with a tighter segmentation threshold for cell01, the coefficient tracked epoch count more closely than duration (coefficient 0.300, stderr 0.048, n = 39). While re-exporting the raw traces for cell12, two cells fell out of the usable range (coefficient 0.294, stderr 0.028, n = 46). While checking residual autocorrelation for cell18, the CI narrowed by roughly a tenth (coefficient 0.113, stderr 0.017, n = 45). While checking residual autocorrelation for cell24, the estimate moved less than one standard error (coefficient 0.161, stderr 0.029, n = 54). Flagging it so it does not get rediscovered next week.

### Step 33: re-running with a tighter segmentation threshold

While re-exporting the raw traces for cell15, nothing in the figure changed at print size (coefficient 0.139, stderr 0.042, n = 39). While segmenting epochs for cell06, the coefficient tracked epoch count more closely than duration (coefficient 0.285, stderr 0.021, n = 46). While re-running with a tighter segmentation threshold for cell01, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.099, stderr 0.018, n = 43). While fitting the one-lag kernel for cell16, two cells fell out of the usable range (coefficient 0.167, stderr 0.012, n = 45). While fitting the one-lag kernel for cell06, the coefficient tracked epoch count more closely than duration (coefficient 0.135, stderr 0.014, n = 47).

```python
coefs = fit_per_cell(rows, threshold=0.59)
lo, hi = ci(coefs, seed=4)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 34: bootstrapping the CI

While re-exporting the raw traces for cell08, the ordering of cells was preserved (coefficient 0.264, stderr 0.023, n = 50). While comparing per-cell orderings for cell13, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.251, stderr 0.027, n = 49). While comparing per-cell orderings for cell05, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.157, stderr 0.035, n = 56). While comparing per-cell orderings for cell22, the coefficient tracked epoch count more closely than duration (coefficient 0.215, stderr 0.037, n = 48). While fitting the one-lag kernel for cell14, nothing in the figure changed at print size (coefficient 0.176, stderr 0.016, n = 56). While auditing the holding potential column for cell20, the coefficient tracked epoch count more closely than duration (coefficient 0.148, stderr 0.024, n = 44).

While re-running with a tighter segmentation threshold for cell21, the ordering of cells was preserved (coefficient 0.295, stderr 0.027, n = 39). While auditing the holding potential column for cell03, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.291, stderr 0.045, n = 39). While checking residual autocorrelation for cell06, nothing in the figure changed at print size (coefficient 0.094, stderr 0.013, n = 53). Parking this until the re-segmentation lands.

While checking residual autocorrelation for cell18, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.293, stderr 0.046, n = 50). While comparing per-cell orderings for cell01, nothing in the figure changed at print size (coefficient 0.143, stderr 0.045, n = 55). While segmenting epochs for cell01, the CI narrowed by roughly a tenth (coefficient 0.133, stderr 0.014, n = 46). While fitting the one-lag kernel for cell01, two cells fell out of the usable range (coefficient 0.235, stderr 0.032, n = 58). While re-running with a tighter segmentation threshold for cell17, the coefficient tracked epoch count more closely than duration (coefficient 0.309, stderr 0.049, n = 53). While re-running with a tighter segmentation threshold for cell14, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.125, stderr 0.034, n = 38). Noted and moved on; it does not change the decision.

### Step 35: segmenting epochs

While checking residual autocorrelation for cell22, nothing in the figure changed at print size (coefficient 0.201, stderr 0.023, n = 48). While auditing the holding potential column for cell18, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.107, stderr 0.035, n = 44). While re-running with a tighter segmentation threshold for cell01, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.134, stderr 0.030, n = 42). Parking this until the re-segmentation lands.

While re-running with a tighter segmentation threshold for cell03, nothing in the figure changed at print size (coefficient 0.137, stderr 0.038, n = 57). While re-running with a tighter segmentation threshold for cell04, the CI narrowed by roughly a tenth (coefficient 0.150, stderr 0.012, n = 58). While segmenting epochs for cell07, the estimate moved less than one standard error (coefficient 0.170, stderr 0.013, n = 41). While fitting the one-lag kernel for cell15, the CI narrowed by roughly a tenth (coefficient 0.281, stderr 0.042, n = 45). While re-exporting the raw traces for cell22, the CI narrowed by roughly a tenth (coefficient 0.223, stderr 0.019, n = 47). While comparing per-cell orderings for cell09, two cells fell out of the usable range (coefficient 0.186, stderr 0.012, n = 42). This is the part that will need a real statistical argument.

### Step 36: re-running with a tighter segmentation threshold

While checking residual autocorrelation for cell20, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.230, stderr 0.036, n = 47). While re-running with a tighter segmentation threshold for cell10, two cells fell out of the usable range (coefficient 0.148, stderr 0.028, n = 48). While checking residual autocorrelation for cell17, the estimate moved less than one standard error (coefficient 0.206, stderr 0.041, n = 41). While re-running with a tighter segmentation threshold for cell19, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.227, stderr 0.021, n = 50). While fitting the one-lag kernel for cell12, the estimate moved less than one standard error (coefficient 0.129, stderr 0.041, n = 52). While segmenting epochs for cell20, two cells fell out of the usable range (coefficient 0.217, stderr 0.026, n = 48). This is the part that will need a real statistical argument.

While fitting the one-lag kernel for cell23, nothing in the figure changed at print size (coefficient 0.147, stderr 0.023, n = 51). While checking residual autocorrelation for cell22, the ordering of cells was preserved (coefficient 0.204, stderr 0.049, n = 43). While checking residual autocorrelation for cell04, the coefficient tracked epoch count more closely than duration (coefficient 0.150, stderr 0.028, n = 39). While segmenting epochs for cell21, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.183, stderr 0.022, n = 58). While re-running with a tighter segmentation threshold for cell19, the coefficient tracked epoch count more closely than duration (coefficient 0.238, stderr 0.038, n = 43). While bootstrapping the CI for cell08, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.206, stderr 0.047, n = 48). Worth noting for the writeup, though not a result on its own.

### Step 37: auditing the holding potential column

While re-running with a tighter segmentation threshold for cell16, the ordering of cells was preserved (coefficient 0.289, stderr 0.015, n = 50). While re-exporting the raw traces for cell04, the CI narrowed by roughly a tenth (coefficient 0.272, stderr 0.011, n = 50). While comparing per-cell orderings for cell18, nothing in the figure changed at print size (coefficient 0.192, stderr 0.021, n = 42). While checking residual autocorrelation for cell05, the ordering of cells was preserved (coefficient 0.187, stderr 0.034, n = 38). While comparing per-cell orderings for cell15, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.234, stderr 0.014, n = 45). While segmenting epochs for cell06, the ordering of cells was preserved (coefficient 0.083, stderr 0.037, n = 57). Flagging it so it does not get rediscovered next week.

While comparing per-cell orderings for cell13, the ordering of cells was preserved (coefficient 0.144, stderr 0.047, n = 58). While comparing per-cell orderings for cell17, the CI narrowed by roughly a tenth (coefficient 0.221, stderr 0.011, n = 56). While comparing per-cell orderings for cell02, the coefficient tracked epoch count more closely than duration (coefficient 0.248, stderr 0.031, n = 43). While comparing per-cell orderings for cell19, the CI narrowed by roughly a tenth (coefficient 0.160, stderr 0.017, n = 54). While auditing the holding potential column for cell05, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.098, stderr 0.012, n = 56).

While auditing the holding potential column for cell19, the ordering of cells was preserved (coefficient 0.119, stderr 0.049, n = 58). While auditing the holding potential column for cell04, the coefficient tracked epoch count more closely than duration (coefficient 0.242, stderr 0.044, n = 44). While checking residual autocorrelation for cell01, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.230, stderr 0.023, n = 38). While comparing per-cell orderings for cell09, nothing in the figure changed at print size (coefficient 0.293, stderr 0.042, n = 51). While comparing per-cell orderings for cell15, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.148, stderr 0.028, n = 58). While comparing per-cell orderings for cell05, two cells fell out of the usable range (coefficient 0.213, stderr 0.033, n = 41).

```python
coefs = fit_per_cell(rows, threshold=0.34)
lo, hi = ci(coefs, seed=7)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 38: comparing per-cell orderings

While fitting the one-lag kernel for cell13, nothing in the figure changed at print size (coefficient 0.186, stderr 0.017, n = 54). While checking residual autocorrelation for cell23, nothing in the figure changed at print size (coefficient 0.157, stderr 0.037, n = 47). While fitting the one-lag kernel for cell19, the coefficient tracked epoch count more closely than duration (coefficient 0.292, stderr 0.020, n = 41). While checking residual autocorrelation for cell02, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.158, stderr 0.029, n = 49).

While segmenting epochs for cell01, the estimate moved less than one standard error (coefficient 0.100, stderr 0.036, n = 48). While fitting the one-lag kernel for cell19, the estimate moved less than one standard error (coefficient 0.088, stderr 0.022, n = 42). While checking residual autocorrelation for cell21, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.297, stderr 0.031, n = 41). Flagging it so it does not get rediscovered next week.

While bootstrapping the CI for cell18, the ordering of cells was preserved (coefficient 0.292, stderr 0.039, n = 55). While auditing the holding potential column for cell18, the coefficient tracked epoch count more closely than duration (coefficient 0.162, stderr 0.025, n = 55). While bootstrapping the CI for cell13, nothing in the figure changed at print size (coefficient 0.179, stderr 0.040, n = 52).

### Step 39: checking residual autocorrelation

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell01    0.106  0.018   0.070  0.142  50        500
cell15    0.184  0.031   0.123  0.246  47        2000
cell05    0.171  0.032   0.109  0.233  39        1000
cell07    0.303  0.010   0.283  0.323  50        500
cell21    0.181  0.045   0.094  0.269  49        2000
cell11    0.271  0.033   0.206  0.336  57        1000
cell18    0.299  0.024   0.252  0.346  51        500
cell08    0.276  0.029   0.220  0.332  54        4000
cell19    0.123  0.045   0.034  0.212  43        1000
cell03    0.287  0.023   0.241  0.332  56        4000
cell19    0.301  0.026   0.251  0.351  54        500
```

While fitting the one-lag kernel for cell17, the coefficient tracked epoch count more closely than duration (coefficient 0.280, stderr 0.017, n = 51). While checking residual autocorrelation for cell17, the CI narrowed by roughly a tenth (coefficient 0.108, stderr 0.033, n = 42). While re-running with a tighter segmentation threshold for cell01, two cells fell out of the usable range (coefficient 0.138, stderr 0.038, n = 57). This is the part that will need a real statistical argument.

While auditing the holding potential column for cell07, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.173, stderr 0.031, n = 56). While bootstrapping the CI for cell08, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.226, stderr 0.046, n = 39). While segmenting epochs for cell14, the coefficient tracked epoch count more closely than duration (coefficient 0.084, stderr 0.017, n = 55). Parking this until the re-segmentation lands.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell13    0.260  0.044   0.174  0.345  53        2000
cell02    0.174  0.032   0.112  0.236  56        2000
cell14    0.303  0.047   0.211  0.395  58        500
cell03    0.085  0.015   0.057  0.114  51        500
cell11    0.295  0.032   0.233  0.356  54        2000
cell13    0.161  0.015   0.132  0.189  41        500
cell16    0.226  0.014   0.199  0.253  49        2000
cell19    0.112  0.019   0.075  0.149  50        1000
cell09    0.148  0.040   0.069  0.227  45        1000
cell15    0.189  0.016   0.158  0.220  38        1000
cell04    0.197  0.019   0.160  0.234  40        4000
cell24    0.309  0.044   0.222  0.397  55        4000
cell24    0.185  0.038   0.110  0.260  40        500
cell23    0.081  0.028   0.025  0.136  45        1000
```

### Step 40: segmenting epochs

While checking residual autocorrelation for cell15, the CI narrowed by roughly a tenth (coefficient 0.150, stderr 0.030, n = 38). While checking residual autocorrelation for cell23, the estimate moved less than one standard error (coefficient 0.166, stderr 0.032, n = 53). While bootstrapping the CI for cell19, two cells fell out of the usable range (coefficient 0.263, stderr 0.028, n = 54). While auditing the holding potential column for cell11, the ordering of cells was preserved (coefficient 0.251, stderr 0.020, n = 43). While checking residual autocorrelation for cell17, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.202, stderr 0.041, n = 49). While comparing per-cell orderings for cell04, the ordering of cells was preserved (coefficient 0.088, stderr 0.025, n = 51).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell01    0.250  0.030   0.190  0.309  51        1000
cell07    0.309  0.037   0.237  0.381  42        500
cell12    0.203  0.047   0.112  0.295  39        500
cell08    0.176  0.021   0.135  0.217  41        500
cell21    0.145  0.049   0.049  0.241  40        2000
cell15    0.108  0.011   0.086  0.129  54        4000
cell07    0.138  0.045   0.049  0.227  53        500
cell10    0.114  0.022   0.070  0.158  44        4000
```

While segmenting epochs for cell15, nothing in the figure changed at print size (coefficient 0.212, stderr 0.015, n = 54). While comparing per-cell orderings for cell24, the coefficient tracked epoch count more closely than duration (coefficient 0.118, stderr 0.019, n = 39). While checking residual autocorrelation for cell02, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.253, stderr 0.018, n = 45). While fitting the one-lag kernel for cell02, the coefficient tracked epoch count more closely than duration (coefficient 0.310, stderr 0.012, n = 51). While auditing the holding potential column for cell23, two cells fell out of the usable range (coefficient 0.159, stderr 0.031, n = 56).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell13    0.126  0.041   0.045  0.208  47        2000
cell17    0.163  0.022   0.121  0.206  45        500
cell08    0.184  0.021   0.144  0.224  58        1000
cell03    0.145  0.014   0.117  0.173  57        500
cell22    0.105  0.016   0.073  0.137  57        500
cell12    0.290  0.023   0.245  0.334  56        2000
cell11    0.211  0.028   0.157  0.265  40        500
cell07    0.181  0.012   0.158  0.204  45        2000
cell01    0.124  0.025   0.075  0.173  48        2000
cell09    0.121  0.026   0.070  0.172  45        1000
cell17    0.138  0.045   0.051  0.226  56        2000
```

