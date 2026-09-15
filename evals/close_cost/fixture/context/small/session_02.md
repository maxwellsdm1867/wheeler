# Prior session 2 of 2

Transcript of an earlier working session on the history-kernel analysis.

### Step 1: fitting the one-lag kernel

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell20    0.166  0.046   0.075  0.256  39        4000
cell08    0.159  0.012   0.136  0.182  56        2000
cell15    0.082  0.039   0.005  0.159  58        500
cell23    0.208  0.013   0.183  0.232  51        2000
cell12    0.217  0.030   0.158  0.277  44        2000
cell12    0.176  0.021   0.136  0.216  56        500
cell12    0.221  0.019   0.183  0.258  44        4000
cell01    0.082  0.018   0.047  0.117  38        500
cell17    0.184  0.011   0.163  0.204  39        4000
cell21    0.181  0.035   0.112  0.250  38        4000
cell04    0.288  0.029   0.232  0.344  52        2000
cell19    0.085  0.045   -0.003  0.172  44        500
```

While fitting the one-lag kernel for cell22, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.175, stderr 0.015, n = 42). While comparing per-cell orderings for cell24, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.270, stderr 0.049, n = 39). While fitting the one-lag kernel for cell16, two cells fell out of the usable range (coefficient 0.215, stderr 0.047, n = 56). While bootstrapping the CI for cell09, the coefficient tracked epoch count more closely than duration (coefficient 0.091, stderr 0.032, n = 46). While segmenting epochs for cell08, the CI narrowed by roughly a tenth (coefficient 0.189, stderr 0.046, n = 51). While bootstrapping the CI for cell03, two cells fell out of the usable range (coefficient 0.293, stderr 0.019, n = 57).

### Step 2: segmenting epochs

While auditing the holding potential column for cell22, the CI narrowed by roughly a tenth (coefficient 0.295, stderr 0.037, n = 39). While bootstrapping the CI for cell20, the estimate moved less than one standard error (coefficient 0.092, stderr 0.039, n = 39). While segmenting epochs for cell23, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.248, stderr 0.042, n = 44). While checking residual autocorrelation for cell15, the CI narrowed by roughly a tenth (coefficient 0.250, stderr 0.019, n = 41). Parking this until the re-segmentation lands.

While bootstrapping the CI for cell12, nothing in the figure changed at print size (coefficient 0.216, stderr 0.048, n = 39). While re-exporting the raw traces for cell20, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.113, stderr 0.039, n = 41). While comparing per-cell orderings for cell07, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.126, stderr 0.029, n = 50).

While bootstrapping the CI for cell18, nothing in the figure changed at print size (coefficient 0.099, stderr 0.050, n = 41). While bootstrapping the CI for cell03, two cells fell out of the usable range (coefficient 0.265, stderr 0.025, n = 42). While auditing the holding potential column for cell16, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.204, stderr 0.048, n = 48). Noted and moved on; it does not change the decision.

While fitting the one-lag kernel for cell05, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.145, stderr 0.047, n = 49). While fitting the one-lag kernel for cell02, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.109, stderr 0.030, n = 54). While fitting the one-lag kernel for cell21, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.260, stderr 0.018, n = 38).

### Step 3: checking residual autocorrelation

While comparing per-cell orderings for cell02, the ordering of cells was preserved (coefficient 0.155, stderr 0.038, n = 54). While fitting the one-lag kernel for cell11, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.091, stderr 0.030, n = 56). While checking residual autocorrelation for cell10, two cells fell out of the usable range (coefficient 0.244, stderr 0.023, n = 54).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell14    0.303  0.043   0.220  0.387  47        4000
cell16    0.089  0.048   -0.005  0.184  43        500
cell10    0.226  0.044   0.140  0.311  42        4000
cell07    0.268  0.018   0.233  0.304  46        4000
cell19    0.253  0.034   0.186  0.320  38        1000
cell18    0.102  0.039   0.026  0.178  56        2000
cell15    0.133  0.021   0.091  0.176  46        2000
cell19    0.200  0.030   0.141  0.259  43        500
cell09    0.234  0.015   0.204  0.264  40        1000
```

### Step 4: re-exporting the raw traces

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell22    0.195  0.023   0.150  0.240  39        4000
cell05    0.120  0.048   0.025  0.214  53        1000
cell01    0.260  0.042   0.178  0.342  57        4000
cell23    0.135  0.050   0.038  0.232  51        500
cell22    0.291  0.016   0.261  0.322  45        4000
cell16    0.188  0.033   0.124  0.253  49        500
cell23    0.287  0.048   0.194  0.381  42        2000
cell07    0.253  0.024   0.205  0.300  40        2000
cell04    0.114  0.038   0.038  0.189  42        2000
cell19    0.282  0.042   0.200  0.365  53        1000
cell08    0.185  0.011   0.163  0.206  45        2000
cell15    0.263  0.020   0.223  0.303  50        4000
cell05    0.113  0.016   0.082  0.145  47        1000
```

While bootstrapping the CI for cell13, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.295, stderr 0.035, n = 41). While comparing per-cell orderings for cell06, the estimate moved less than one standard error (coefficient 0.142, stderr 0.037, n = 38). While re-exporting the raw traces for cell18, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.235, stderr 0.030, n = 55). While fitting the one-lag kernel for cell13, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.101, stderr 0.021, n = 55). While fitting the one-lag kernel for cell20, two cells fell out of the usable range (coefficient 0.177, stderr 0.046, n = 58). While re-exporting the raw traces for cell14, the ordering of cells was preserved (coefficient 0.133, stderr 0.033, n = 55). Flagging it so it does not get rediscovered next week.

### Step 5: comparing per-cell orderings

While fitting the one-lag kernel for cell11, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.258, stderr 0.046, n = 43). While comparing per-cell orderings for cell06, the estimate moved less than one standard error (coefficient 0.170, stderr 0.049, n = 38). While segmenting epochs for cell05, two cells fell out of the usable range (coefficient 0.246, stderr 0.043, n = 39). While checking residual autocorrelation for cell03, the coefficient tracked epoch count more closely than duration (coefficient 0.129, stderr 0.020, n = 45). While re-exporting the raw traces for cell16, the coefficient tracked epoch count more closely than duration (coefficient 0.273, stderr 0.021, n = 38). While segmenting epochs for cell02, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.179, stderr 0.029, n = 54). Parking this until the re-segmentation lands.

While segmenting epochs for cell21, the coefficient tracked epoch count more closely than duration (coefficient 0.214, stderr 0.044, n = 45). While segmenting epochs for cell18, the CI narrowed by roughly a tenth (coefficient 0.222, stderr 0.039, n = 40). While auditing the holding potential column for cell20, two cells fell out of the usable range (coefficient 0.132, stderr 0.013, n = 52). While checking residual autocorrelation for cell01, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.264, stderr 0.025, n = 44).

While auditing the holding potential column for cell17, the ordering of cells was preserved (coefficient 0.128, stderr 0.029, n = 56). While re-exporting the raw traces for cell06, the CI narrowed by roughly a tenth (coefficient 0.095, stderr 0.047, n = 50). While checking residual autocorrelation for cell01, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.116, stderr 0.017, n = 38). While fitting the one-lag kernel for cell21, the estimate moved less than one standard error (coefficient 0.103, stderr 0.023, n = 43). While re-exporting the raw traces for cell02, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.169, stderr 0.024, n = 54).

### Step 6: auditing the holding potential column

While checking residual autocorrelation for cell02, nothing in the figure changed at print size (coefficient 0.221, stderr 0.039, n = 46). While checking residual autocorrelation for cell20, the estimate moved less than one standard error (coefficient 0.212, stderr 0.045, n = 41). While segmenting epochs for cell17, two cells fell out of the usable range (coefficient 0.143, stderr 0.022, n = 42). This is the part that will need a real statistical argument.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell20    0.235  0.025   0.186  0.284  41        1000
cell22    0.083  0.023   0.037  0.129  38        500
cell12    0.180  0.024   0.133  0.228  41        1000
cell02    0.257  0.034   0.191  0.324  53        2000
cell10    0.121  0.046   0.031  0.211  54        4000
cell11    0.138  0.027   0.084  0.191  52        500
cell17    0.268  0.020   0.228  0.308  45        4000
cell22    0.088  0.047   -0.004  0.180  52        4000
cell12    0.215  0.031   0.154  0.275  53        4000
cell18    0.111  0.015   0.082  0.140  44        2000
cell08    0.130  0.017   0.097  0.164  41        500
cell03    0.193  0.028   0.138  0.247  57        2000
cell23    0.117  0.032   0.054  0.180  47        500
```

### Step 7: re-exporting the raw traces

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell10    0.240  0.025   0.190  0.289  39        4000
cell04    0.133  0.034   0.066  0.199  40        2000
cell24    0.194  0.042   0.110  0.277  52        4000
cell11    0.279  0.020   0.239  0.319  46        1000
cell23    0.124  0.037   0.053  0.196  38        1000
cell06    0.142  0.047   0.050  0.235  47        2000
cell24    0.274  0.017   0.240  0.308  43        2000
cell19    0.242  0.031   0.181  0.303  46        500
cell05    0.223  0.017   0.189  0.257  43        500
cell13    0.223  0.020   0.183  0.263  50        500
cell11    0.255  0.048   0.160  0.350  57        1000
cell06    0.236  0.034   0.170  0.302  38        2000
cell07    0.138  0.013   0.113  0.163  39        500
```

```python
coefs = fit_per_cell(rows, threshold=0.41)
lo, hi = ci(coefs, seed=26)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 8: re-running with a tighter segmentation threshold

While auditing the holding potential column for cell04, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.117, stderr 0.012, n = 53). While checking residual autocorrelation for cell17, the coefficient tracked epoch count more closely than duration (coefficient 0.139, stderr 0.047, n = 47). While fitting the one-lag kernel for cell13, the coefficient tracked epoch count more closely than duration (coefficient 0.089, stderr 0.033, n = 51). While comparing per-cell orderings for cell24, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.234, stderr 0.026, n = 45).

While fitting the one-lag kernel for cell03, the estimate moved less than one standard error (coefficient 0.134, stderr 0.048, n = 40). While checking residual autocorrelation for cell01, two cells fell out of the usable range (coefficient 0.248, stderr 0.041, n = 58). While auditing the holding potential column for cell24, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.094, stderr 0.029, n = 58). While fitting the one-lag kernel for cell21, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.175, stderr 0.032, n = 39). While fitting the one-lag kernel for cell05, two cells fell out of the usable range (coefficient 0.208, stderr 0.016, n = 49). While fitting the one-lag kernel for cell12, nothing in the figure changed at print size (coefficient 0.159, stderr 0.012, n = 57).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell10    0.081  0.044   -0.005  0.166  54        500
cell21    0.109  0.016   0.078  0.140  42        500
cell10    0.164  0.042   0.082  0.247  41        500
cell06    0.084  0.027   0.031  0.137  53        500
cell12    0.222  0.041   0.142  0.302  58        4000
cell22    0.197  0.042   0.115  0.279  48        4000
cell13    0.250  0.012   0.226  0.273  57        4000
cell10    0.278  0.033   0.213  0.343  58        2000
cell20    0.142  0.025   0.093  0.190  55        4000
```

### Step 9: segmenting epochs

While re-exporting the raw traces for cell07, the CI narrowed by roughly a tenth (coefficient 0.205, stderr 0.041, n = 46). While fitting the one-lag kernel for cell11, two cells fell out of the usable range (coefficient 0.166, stderr 0.037, n = 53). While fitting the one-lag kernel for cell03, nothing in the figure changed at print size (coefficient 0.140, stderr 0.048, n = 55).

While re-running with a tighter segmentation threshold for cell11, the estimate moved less than one standard error (coefficient 0.149, stderr 0.045, n = 45). While checking residual autocorrelation for cell23, the CI narrowed by roughly a tenth (coefficient 0.228, stderr 0.050, n = 43). While auditing the holding potential column for cell10, nothing in the figure changed at print size (coefficient 0.197, stderr 0.022, n = 50). While comparing per-cell orderings for cell10, the coefficient tracked epoch count more closely than duration (coefficient 0.136, stderr 0.043, n = 39). While re-exporting the raw traces for cell08, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.163, stderr 0.047, n = 52). While fitting the one-lag kernel for cell07, the estimate moved less than one standard error (coefficient 0.205, stderr 0.016, n = 41).

While segmenting epochs for cell02, two cells fell out of the usable range (coefficient 0.288, stderr 0.045, n = 47). While segmenting epochs for cell18, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.201, stderr 0.028, n = 42). While re-exporting the raw traces for cell02, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.202, stderr 0.020, n = 55).

### Step 10: comparing per-cell orderings

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell14    0.095  0.043   0.012  0.179  51        500
cell13    0.193  0.021   0.152  0.234  58        4000
cell11    0.167  0.043   0.083  0.252  45        4000
cell22    0.285  0.019   0.248  0.323  47        500
cell22    0.087  0.021   0.046  0.128  48        500
cell12    0.306  0.029   0.250  0.362  51        2000
cell13    0.217  0.010   0.197  0.237  43        1000
cell03    0.095  0.026   0.044  0.146  52        1000
cell22    0.292  0.020   0.252  0.333  45        1000
cell16    0.124  0.030   0.065  0.183  41        500
cell03    0.154  0.029   0.097  0.211  42        4000
cell23    0.102  0.037   0.030  0.174  38        1000
cell24    0.183  0.014   0.156  0.210  38        2000
cell11    0.281  0.027   0.228  0.333  47        1000
```

```python
coefs = fit_per_cell(rows, threshold=0.45)
lo, hi = ci(coefs, seed=45)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell11    0.199  0.045   0.112  0.286  53        500
cell23    0.205  0.032   0.143  0.267  54        4000
cell01    0.136  0.025   0.087  0.185  40        2000
cell04    0.161  0.026   0.111  0.211  55        1000
cell19    0.227  0.024   0.180  0.274  41        4000
cell14    0.278  0.011   0.256  0.300  43        2000
```

### Step 11: bootstrapping the CI

While segmenting epochs for cell17, the estimate moved less than one standard error (coefficient 0.253, stderr 0.026, n = 46). While segmenting epochs for cell08, nothing in the figure changed at print size (coefficient 0.101, stderr 0.041, n = 46). While re-exporting the raw traces for cell17, the CI narrowed by roughly a tenth (coefficient 0.271, stderr 0.023, n = 42). While bootstrapping the CI for cell17, the coefficient tracked epoch count more closely than duration (coefficient 0.145, stderr 0.024, n = 53).

While re-exporting the raw traces for cell11, the estimate moved less than one standard error (coefficient 0.113, stderr 0.015, n = 46). While fitting the one-lag kernel for cell10, two cells fell out of the usable range (coefficient 0.214, stderr 0.045, n = 48). While auditing the holding potential column for cell06, the coefficient tracked epoch count more closely than duration (coefficient 0.285, stderr 0.047, n = 54).

While re-running with a tighter segmentation threshold for cell14, two cells fell out of the usable range (coefficient 0.083, stderr 0.023, n = 41). While bootstrapping the CI for cell16, the estimate moved less than one standard error (coefficient 0.134, stderr 0.010, n = 41). While comparing per-cell orderings for cell07, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.117, stderr 0.028, n = 41). While checking residual autocorrelation for cell01, the estimate moved less than one standard error (coefficient 0.262, stderr 0.044, n = 42).

### Step 12: checking residual autocorrelation

```python
coefs = fit_per_cell(rows, threshold=0.31)
lo, hi = ci(coefs, seed=17)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell16    0.193  0.022   0.151  0.235  41        1000
cell24    0.226  0.024   0.179  0.273  39        1000
cell15    0.269  0.011   0.247  0.291  50        1000
cell06    0.089  0.030   0.031  0.147  55        500
cell24    0.126  0.013   0.101  0.152  42        1000
cell20    0.235  0.028   0.179  0.290  50        500
cell16    0.242  0.012   0.220  0.265  45        1000
cell18    0.265  0.017   0.231  0.298  56        2000
cell19    0.090  0.011   0.068  0.112  58        2000
cell05    0.218  0.012   0.194  0.241  44        4000
cell19    0.233  0.045   0.144  0.322  54        1000
cell08    0.218  0.028   0.164  0.273  46        500
cell18    0.202  0.020   0.163  0.240  56        500
cell21    0.264  0.047   0.172  0.356  56        4000
```

### Step 13: re-exporting the raw traces

While comparing per-cell orderings for cell13, the coefficient tracked epoch count more closely than duration (coefficient 0.232, stderr 0.012, n = 43). While re-exporting the raw traces for cell08, the CI narrowed by roughly a tenth (coefficient 0.173, stderr 0.018, n = 57). While bootstrapping the CI for cell24, the CI narrowed by roughly a tenth (coefficient 0.264, stderr 0.020, n = 49). While auditing the holding potential column for cell22, the ordering of cells was preserved (coefficient 0.283, stderr 0.048, n = 53).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell10    0.111  0.050   0.013  0.208  44        2000
cell07    0.209  0.012   0.185  0.233  47        500
cell22    0.138  0.027   0.085  0.192  50        4000
cell12    0.288  0.042   0.206  0.369  45        4000
cell08    0.090  0.048   -0.004  0.184  54        2000
cell17    0.236  0.011   0.215  0.258  52        4000
cell21    0.289  0.014   0.262  0.317  53        1000
cell06    0.221  0.035   0.152  0.290  41        2000
cell06    0.139  0.036   0.069  0.209  47        1000
cell24    0.274  0.029   0.216  0.332  48        2000
cell19    0.248  0.045   0.160  0.337  54        2000
cell21    0.110  0.012   0.087  0.134  44        4000
cell17    0.218  0.025   0.169  0.267  54        1000
cell08    0.292  0.041   0.211  0.372  41        4000
```

While re-running with a tighter segmentation threshold for cell08, nothing in the figure changed at print size (coefficient 0.308, stderr 0.040, n = 39). While segmenting epochs for cell01, nothing in the figure changed at print size (coefficient 0.141, stderr 0.010, n = 44). While re-running with a tighter segmentation threshold for cell05, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.148, stderr 0.027, n = 49). While auditing the holding potential column for cell03, the coefficient tracked epoch count more closely than duration (coefficient 0.253, stderr 0.016, n = 43). While comparing per-cell orderings for cell07, the ordering of cells was preserved (coefficient 0.220, stderr 0.033, n = 58). Noted and moved on; it does not change the decision.

### Step 14: re-running with a tighter segmentation threshold

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell01    0.124  0.034   0.058  0.190  50        2000
cell03    0.146  0.042   0.063  0.229  47        1000
cell13    0.224  0.034   0.158  0.291  53        2000
cell06    0.082  0.025   0.033  0.131  57        2000
cell01    0.114  0.035   0.045  0.182  39        2000
cell06    0.181  0.015   0.151  0.212  46        500
cell05    0.089  0.044   0.002  0.176  56        4000
cell13    0.121  0.032   0.059  0.184  57        2000
cell01    0.157  0.024   0.109  0.205  58        500
cell18    0.180  0.017   0.148  0.212  45        2000
cell15    0.221  0.048   0.127  0.315  41        1000
cell14    0.281  0.023   0.235  0.326  39        1000
cell24    0.109  0.049   0.014  0.205  49        500
cell10    0.189  0.016   0.158  0.221  48        4000
```

While auditing the holding potential column for cell23, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.243, stderr 0.039, n = 58). While segmenting epochs for cell03, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.272, stderr 0.019, n = 44). While checking residual autocorrelation for cell20, nothing in the figure changed at print size (coefficient 0.304, stderr 0.021, n = 53). While auditing the holding potential column for cell24, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.304, stderr 0.031, n = 58). Noted and moved on; it does not change the decision.

### Step 15: bootstrapping the CI

While fitting the one-lag kernel for cell16, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.119, stderr 0.044, n = 44). While re-running with a tighter segmentation threshold for cell06, the coefficient tracked epoch count more closely than duration (coefficient 0.174, stderr 0.028, n = 41). While re-exporting the raw traces for cell19, the coefficient tracked epoch count more closely than duration (coefficient 0.141, stderr 0.019, n = 39).

```python
coefs = fit_per_cell(rows, threshold=0.47)
lo, hi = ci(coefs, seed=25)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell01    0.168  0.034   0.101  0.235  48        1000
cell23    0.268  0.042   0.185  0.351  51        1000
cell10    0.124  0.034   0.058  0.190  58        2000
cell18    0.105  0.026   0.053  0.157  55        500
cell05    0.163  0.034   0.097  0.230  56        500
cell23    0.186  0.017   0.153  0.220  58        500
cell02    0.158  0.027   0.106  0.210  38        2000
cell22    0.125  0.037   0.054  0.197  51        2000
cell06    0.197  0.043   0.112  0.282  58        500
cell08    0.265  0.043   0.181  0.349  52        2000
cell10    0.091  0.020   0.053  0.129  39        2000
cell23    0.110  0.014   0.082  0.137  51        4000
```

```python
coefs = fit_per_cell(rows, threshold=0.73)
lo, hi = ci(coefs, seed=54)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 16: re-exporting the raw traces

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell05    0.288  0.038   0.213  0.362  55        4000
cell13    0.086  0.017   0.053  0.119  47        500
cell24    0.247  0.023   0.201  0.292  52        2000
cell16    0.112  0.032   0.050  0.175  52        4000
cell15    0.098  0.015   0.068  0.128  52        2000
cell21    0.177  0.015   0.147  0.207  57        2000
cell16    0.143  0.019   0.106  0.180  47        1000
cell19    0.268  0.044   0.181  0.354  53        2000
cell08    0.095  0.039   0.018  0.171  54        500
cell17    0.185  0.015   0.155  0.215  50        2000
cell24    0.094  0.047   0.002  0.185  46        2000
cell21    0.085  0.037   0.013  0.157  53        4000
cell02    0.286  0.042   0.203  0.369  42        1000
cell21    0.124  0.013   0.098  0.150  50        1000
```

```python
coefs = fit_per_cell(rows, threshold=0.36)
lo, hi = ci(coefs, seed=52)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While auditing the holding potential column for cell09, the ordering of cells was preserved (coefficient 0.206, stderr 0.012, n = 56). While checking residual autocorrelation for cell18, the ordering of cells was preserved (coefficient 0.305, stderr 0.028, n = 58). While re-exporting the raw traces for cell21, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.102, stderr 0.042, n = 47).

### Step 17: re-running with a tighter segmentation threshold

While re-exporting the raw traces for cell17, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.178, stderr 0.021, n = 53). While comparing per-cell orderings for cell23, the CI narrowed by roughly a tenth (coefficient 0.290, stderr 0.038, n = 55). While bootstrapping the CI for cell11, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.183, stderr 0.029, n = 38). While checking residual autocorrelation for cell09, nothing in the figure changed at print size (coefficient 0.186, stderr 0.018, n = 52). While bootstrapping the CI for cell08, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.196, stderr 0.046, n = 58).

While segmenting epochs for cell19, the ordering of cells was preserved (coefficient 0.134, stderr 0.045, n = 49). While re-exporting the raw traces for cell17, the estimate moved less than one standard error (coefficient 0.270, stderr 0.046, n = 54). While auditing the holding potential column for cell07, the CI narrowed by roughly a tenth (coefficient 0.244, stderr 0.020, n = 51). While re-exporting the raw traces for cell17, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.225, stderr 0.024, n = 54).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell16    0.148  0.020   0.108  0.187  43        1000
cell08    0.252  0.031   0.191  0.313  40        1000
cell04    0.120  0.038   0.044  0.195  47        500
cell15    0.216  0.014   0.189  0.243  43        2000
cell16    0.192  0.028   0.137  0.247  45        500
cell22    0.161  0.014   0.134  0.189  47        2000
cell04    0.241  0.048   0.146  0.336  38        4000
cell19    0.237  0.013   0.212  0.262  45        500
cell10    0.256  0.044   0.170  0.343  40        2000
cell05    0.237  0.024   0.189  0.284  41        1000
cell21    0.193  0.021   0.152  0.233  42        4000
cell04    0.309  0.033   0.245  0.373  38        4000
cell17    0.262  0.027   0.209  0.315  50        500
```

### Step 18: re-exporting the raw traces

While fitting the one-lag kernel for cell05, two cells fell out of the usable range (coefficient 0.082, stderr 0.041, n = 55). While segmenting epochs for cell11, nothing in the figure changed at print size (coefficient 0.102, stderr 0.039, n = 53). While re-exporting the raw traces for cell09, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.088, stderr 0.010, n = 53). While auditing the holding potential column for cell13, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.157, stderr 0.034, n = 47).

```python
coefs = fit_per_cell(rows, threshold=0.63)
lo, hi = ci(coefs, seed=20)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While fitting the one-lag kernel for cell03, the ordering of cells was preserved (coefficient 0.099, stderr 0.045, n = 49). While fitting the one-lag kernel for cell18, the estimate moved less than one standard error (coefficient 0.237, stderr 0.018, n = 58). While auditing the holding potential column for cell02, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.238, stderr 0.013, n = 51).

While checking residual autocorrelation for cell04, the ordering of cells was preserved (coefficient 0.128, stderr 0.049, n = 39). While bootstrapping the CI for cell21, two cells fell out of the usable range (coefficient 0.253, stderr 0.034, n = 46). While re-exporting the raw traces for cell07, nothing in the figure changed at print size (coefficient 0.211, stderr 0.023, n = 40). While re-exporting the raw traces for cell01, the CI narrowed by roughly a tenth (coefficient 0.152, stderr 0.035, n = 54). While re-running with a tighter segmentation threshold for cell07, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.255, stderr 0.036, n = 55). This is the part that will need a real statistical argument.

### Step 19: re-running with a tighter segmentation threshold

```python
coefs = fit_per_cell(rows, threshold=0.52)
lo, hi = ci(coefs, seed=38)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While segmenting epochs for cell19, two cells fell out of the usable range (coefficient 0.309, stderr 0.035, n = 58). While auditing the holding potential column for cell11, the ordering of cells was preserved (coefficient 0.081, stderr 0.041, n = 46). While comparing per-cell orderings for cell02, the estimate moved less than one standard error (coefficient 0.305, stderr 0.043, n = 54).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell04    0.287  0.049   0.191  0.382  45        2000
cell19    0.147  0.040   0.069  0.226  51        2000
cell22    0.168  0.015   0.139  0.196  52        1000
cell22    0.095  0.041   0.014  0.176  54        4000
cell09    0.250  0.035   0.182  0.318  58        1000
cell02    0.228  0.042   0.145  0.310  48        1000
cell21    0.183  0.041   0.103  0.263  40        4000
cell14    0.135  0.025   0.086  0.184  40        1000
cell18    0.248  0.031   0.188  0.309  56        4000
cell07    0.191  0.013   0.165  0.217  56        1000
cell04    0.268  0.011   0.247  0.289  43        2000
cell21    0.113  0.027   0.060  0.166  51        4000
```

While segmenting epochs for cell23, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.241, stderr 0.023, n = 42). While bootstrapping the CI for cell07, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.302, stderr 0.019, n = 51). While fitting the one-lag kernel for cell06, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.167, stderr 0.018, n = 58). While comparing per-cell orderings for cell06, the coefficient tracked epoch count more closely than duration (coefficient 0.087, stderr 0.012, n = 47). While comparing per-cell orderings for cell09, the estimate moved less than one standard error (coefficient 0.185, stderr 0.024, n = 49).

### Step 20: segmenting epochs

While re-running with a tighter segmentation threshold for cell23, the ordering of cells was preserved (coefficient 0.171, stderr 0.045, n = 47). While re-exporting the raw traces for cell13, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.135, stderr 0.025, n = 48). While re-exporting the raw traces for cell08, the coefficient tracked epoch count more closely than duration (coefficient 0.191, stderr 0.039, n = 38). While fitting the one-lag kernel for cell13, nothing in the figure changed at print size (coefficient 0.146, stderr 0.041, n = 51). While checking residual autocorrelation for cell06, nothing in the figure changed at print size (coefficient 0.180, stderr 0.023, n = 44). While bootstrapping the CI for cell18, the estimate moved less than one standard error (coefficient 0.299, stderr 0.012, n = 53).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell09    0.254  0.024   0.206  0.302  50        2000
cell18    0.180  0.049   0.084  0.276  39        500
cell22    0.096  0.045   0.009  0.184  46        500
cell10    0.276  0.041   0.197  0.356  47        2000
cell09    0.232  0.042   0.151  0.314  48        2000
cell05    0.209  0.011   0.188  0.230  56        500
cell23    0.208  0.044   0.121  0.294  40        2000
cell19    0.184  0.027   0.130  0.238  51        1000
```

### Step 21: auditing the holding potential column

While checking residual autocorrelation for cell11, two cells fell out of the usable range (coefficient 0.087, stderr 0.022, n = 43). While re-exporting the raw traces for cell21, the ordering of cells was preserved (coefficient 0.213, stderr 0.016, n = 47). While fitting the one-lag kernel for cell18, the estimate moved less than one standard error (coefficient 0.196, stderr 0.041, n = 40). While re-exporting the raw traces for cell02, two cells fell out of the usable range (coefficient 0.136, stderr 0.026, n = 47). While checking residual autocorrelation for cell09, nothing in the figure changed at print size (coefficient 0.217, stderr 0.012, n = 47). While segmenting epochs for cell19, nothing in the figure changed at print size (coefficient 0.140, stderr 0.028, n = 56). Flagging it so it does not get rediscovered next week.

While fitting the one-lag kernel for cell19, the estimate moved less than one standard error (coefficient 0.171, stderr 0.034, n = 58). While fitting the one-lag kernel for cell12, the ordering of cells was preserved (coefficient 0.245, stderr 0.038, n = 46). While re-exporting the raw traces for cell17, the coefficient tracked epoch count more closely than duration (coefficient 0.082, stderr 0.042, n = 51). While fitting the one-lag kernel for cell22, the CI narrowed by roughly a tenth (coefficient 0.202, stderr 0.030, n = 40). While segmenting epochs for cell17, the estimate moved less than one standard error (coefficient 0.291, stderr 0.044, n = 48).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell24    0.191  0.047   0.098  0.284  48        4000
cell01    0.276  0.048   0.181  0.371  44        1000
cell01    0.310  0.017   0.277  0.342  40        2000
cell10    0.108  0.025   0.059  0.157  39        2000
cell07    0.248  0.024   0.201  0.296  40        500
cell20    0.281  0.016   0.249  0.312  38        1000
cell07    0.209  0.029   0.152  0.267  46        4000
cell24    0.141  0.027   0.088  0.194  43        500
```

While checking residual autocorrelation for cell22, nothing in the figure changed at print size (coefficient 0.081, stderr 0.039, n = 53). While auditing the holding potential column for cell07, nothing in the figure changed at print size (coefficient 0.219, stderr 0.011, n = 42). While bootstrapping the CI for cell05, two cells fell out of the usable range (coefficient 0.231, stderr 0.017, n = 42). While auditing the holding potential column for cell01, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.129, stderr 0.024, n = 50). While comparing per-cell orderings for cell24, the estimate moved less than one standard error (coefficient 0.130, stderr 0.034, n = 39). While re-running with a tighter segmentation threshold for cell22, the coefficient tracked epoch count more closely than duration (coefficient 0.101, stderr 0.020, n = 42).

### Step 22: re-running with a tighter segmentation threshold

While auditing the holding potential column for cell21, nothing in the figure changed at print size (coefficient 0.153, stderr 0.011, n = 51). While re-running with a tighter segmentation threshold for cell03, the coefficient tracked epoch count more closely than duration (coefficient 0.107, stderr 0.034, n = 46). While checking residual autocorrelation for cell13, two cells fell out of the usable range (coefficient 0.227, stderr 0.048, n = 51). Worth noting for the writeup, though not a result on its own.

```python
coefs = fit_per_cell(rows, threshold=0.31)
lo, hi = ci(coefs, seed=23)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 23: segmenting epochs

While auditing the holding potential column for cell17, the estimate moved less than one standard error (coefficient 0.307, stderr 0.028, n = 42). While re-exporting the raw traces for cell23, the CI narrowed by roughly a tenth (coefficient 0.105, stderr 0.014, n = 44). While checking residual autocorrelation for cell15, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.081, stderr 0.036, n = 39). While re-exporting the raw traces for cell02, the CI narrowed by roughly a tenth (coefficient 0.192, stderr 0.040, n = 47). Flagging it so it does not get rediscovered next week.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell18    0.212  0.029   0.156  0.268  52        2000
cell02    0.183  0.014   0.157  0.210  58        4000
cell12    0.202  0.021   0.160  0.243  45        4000
cell23    0.153  0.029   0.095  0.211  50        500
cell13    0.113  0.035   0.044  0.183  52        500
cell24    0.136  0.014   0.109  0.162  52        1000
cell04    0.202  0.041   0.121  0.283  44        500
```

While comparing per-cell orderings for cell04, the estimate moved less than one standard error (coefficient 0.098, stderr 0.046, n = 51). While re-running with a tighter segmentation threshold for cell13, the CI narrowed by roughly a tenth (coefficient 0.218, stderr 0.029, n = 57). While re-exporting the raw traces for cell04, the CI narrowed by roughly a tenth (coefficient 0.156, stderr 0.033, n = 50). While re-exporting the raw traces for cell03, the ordering of cells was preserved (coefficient 0.120, stderr 0.044, n = 50). While segmenting epochs for cell18, the ordering of cells was preserved (coefficient 0.252, stderr 0.047, n = 50).

While re-exporting the raw traces for cell12, nothing in the figure changed at print size (coefficient 0.287, stderr 0.040, n = 38). While segmenting epochs for cell22, two cells fell out of the usable range (coefficient 0.193, stderr 0.040, n = 47). While re-exporting the raw traces for cell08, the CI narrowed by roughly a tenth (coefficient 0.148, stderr 0.015, n = 39). While re-exporting the raw traces for cell02, the CI narrowed by roughly a tenth (coefficient 0.209, stderr 0.047, n = 39). Worth noting for the writeup, though not a result on its own.

### Step 24: comparing per-cell orderings

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell15    0.126  0.028   0.071  0.182  58        4000
cell11    0.179  0.033   0.114  0.244  43        1000
cell16    0.096  0.019   0.059  0.133  56        500
cell19    0.189  0.040   0.111  0.266  38        1000
cell03    0.126  0.045   0.039  0.214  53        4000
cell09    0.236  0.019   0.200  0.273  49        2000
cell19    0.165  0.021   0.123  0.206  42        2000
cell20    0.169  0.048   0.076  0.263  51        4000
cell03    0.278  0.038   0.204  0.351  47        1000
cell22    0.168  0.035   0.100  0.236  43        4000
```

While comparing per-cell orderings for cell03, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.234, stderr 0.028, n = 39). While comparing per-cell orderings for cell23, the coefficient tracked epoch count more closely than duration (coefficient 0.136, stderr 0.026, n = 41). While fitting the one-lag kernel for cell04, nothing in the figure changed at print size (coefficient 0.264, stderr 0.038, n = 57). While comparing per-cell orderings for cell06, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.167, stderr 0.022, n = 40). Worth noting for the writeup, though not a result on its own.

While segmenting epochs for cell01, nothing in the figure changed at print size (coefficient 0.113, stderr 0.027, n = 53). While re-running with a tighter segmentation threshold for cell09, nothing in the figure changed at print size (coefficient 0.083, stderr 0.019, n = 56). While checking residual autocorrelation for cell21, two cells fell out of the usable range (coefficient 0.305, stderr 0.029, n = 51). While fitting the one-lag kernel for cell20, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.291, stderr 0.020, n = 38).

### Step 25: comparing per-cell orderings

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell08    0.144  0.039   0.067  0.221  47        4000
cell06    0.297  0.033   0.233  0.361  58        4000
cell18    0.134  0.049   0.038  0.231  44        1000
cell13    0.297  0.032   0.234  0.361  47        1000
cell18    0.111  0.045   0.024  0.198  55        4000
cell10    0.163  0.041   0.082  0.243  46        4000
cell18    0.145  0.046   0.055  0.235  52        500
cell07    0.192  0.020   0.153  0.231  57        1000
cell20    0.207  0.027   0.155  0.259  49        500
cell19    0.227  0.029   0.169  0.284  43        4000
cell17    0.156  0.026   0.105  0.207  41        500
```

While re-exporting the raw traces for cell04, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.120, stderr 0.034, n = 42). While re-exporting the raw traces for cell21, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.293, stderr 0.046, n = 54). While fitting the one-lag kernel for cell04, the coefficient tracked epoch count more closely than duration (coefficient 0.211, stderr 0.034, n = 54). While fitting the one-lag kernel for cell21, the estimate moved less than one standard error (coefficient 0.138, stderr 0.028, n = 52). While bootstrapping the CI for cell06, the coefficient tracked epoch count more closely than duration (coefficient 0.166, stderr 0.015, n = 53).

### Step 26: auditing the holding potential column

```python
coefs = fit_per_cell(rows, threshold=0.71)
lo, hi = ci(coefs, seed=71)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While fitting the one-lag kernel for cell15, the estimate moved less than one standard error (coefficient 0.214, stderr 0.048, n = 51). While checking residual autocorrelation for cell19, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.270, stderr 0.012, n = 48). While checking residual autocorrelation for cell24, nothing in the figure changed at print size (coefficient 0.310, stderr 0.045, n = 54). While checking residual autocorrelation for cell19, nothing in the figure changed at print size (coefficient 0.171, stderr 0.013, n = 52). While auditing the holding potential column for cell12, the estimate moved less than one standard error (coefficient 0.143, stderr 0.013, n = 49). While segmenting epochs for cell21, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.238, stderr 0.012, n = 57).

### Step 27: segmenting epochs

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell06    0.245  0.034   0.178  0.312  39        2000
cell08    0.285  0.042   0.202  0.368  42        1000
cell10    0.197  0.014   0.169  0.225  42        500
cell14    0.228  0.013   0.203  0.253  54        1000
cell06    0.126  0.041   0.046  0.207  48        2000
cell05    0.265  0.036   0.195  0.336  57        1000
cell21    0.112  0.039   0.036  0.188  52        4000
cell01    0.297  0.017   0.264  0.331  52        500
```

While checking residual autocorrelation for cell01, the CI narrowed by roughly a tenth (coefficient 0.240, stderr 0.032, n = 39). While fitting the one-lag kernel for cell13, the estimate moved less than one standard error (coefficient 0.203, stderr 0.025, n = 53). While comparing per-cell orderings for cell22, two cells fell out of the usable range (coefficient 0.195, stderr 0.043, n = 49). While re-running with a tighter segmentation threshold for cell09, the estimate moved less than one standard error (coefficient 0.083, stderr 0.013, n = 45).

While segmenting epochs for cell08, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.265, stderr 0.039, n = 48). While fitting the one-lag kernel for cell02, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.265, stderr 0.020, n = 57). While re-running with a tighter segmentation threshold for cell11, the CI narrowed by roughly a tenth (coefficient 0.184, stderr 0.022, n = 47). While bootstrapping the CI for cell23, the CI narrowed by roughly a tenth (coefficient 0.149, stderr 0.047, n = 48). While segmenting epochs for cell07, the coefficient tracked epoch count more closely than duration (coefficient 0.272, stderr 0.012, n = 55). While re-exporting the raw traces for cell11, the ordering of cells was preserved (coefficient 0.281, stderr 0.038, n = 48).

While auditing the holding potential column for cell15, the estimate moved less than one standard error (coefficient 0.275, stderr 0.029, n = 46). While re-running with a tighter segmentation threshold for cell11, nothing in the figure changed at print size (coefficient 0.171, stderr 0.038, n = 45). While re-running with a tighter segmentation threshold for cell14, the CI narrowed by roughly a tenth (coefficient 0.090, stderr 0.021, n = 47). While bootstrapping the CI for cell22, the estimate moved less than one standard error (coefficient 0.251, stderr 0.014, n = 46). While checking residual autocorrelation for cell16, the ordering of cells was preserved (coefficient 0.200, stderr 0.036, n = 53). While fitting the one-lag kernel for cell24, two cells fell out of the usable range (coefficient 0.184, stderr 0.016, n = 52).

### Step 28: fitting the one-lag kernel

While fitting the one-lag kernel for cell07, the CI narrowed by roughly a tenth (coefficient 0.244, stderr 0.025, n = 58). While segmenting epochs for cell01, the estimate moved less than one standard error (coefficient 0.291, stderr 0.036, n = 40). While segmenting epochs for cell14, nothing in the figure changed at print size (coefficient 0.236, stderr 0.023, n = 42). This is the part that will need a real statistical argument.

While re-exporting the raw traces for cell15, the CI narrowed by roughly a tenth (coefficient 0.105, stderr 0.034, n = 52). While fitting the one-lag kernel for cell02, the coefficient tracked epoch count more closely than duration (coefficient 0.213, stderr 0.014, n = 53). While auditing the holding potential column for cell01, the coefficient tracked epoch count more closely than duration (coefficient 0.164, stderr 0.049, n = 39). While bootstrapping the CI for cell04, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.194, stderr 0.034, n = 56). While comparing per-cell orderings for cell09, the coefficient tracked epoch count more closely than duration (coefficient 0.083, stderr 0.034, n = 48). While auditing the holding potential column for cell06, the coefficient tracked epoch count more closely than duration (coefficient 0.130, stderr 0.016, n = 57).

### Step 29: auditing the holding potential column

While bootstrapping the CI for cell08, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.092, stderr 0.034, n = 49). While fitting the one-lag kernel for cell06, the estimate moved less than one standard error (coefficient 0.256, stderr 0.034, n = 47). While fitting the one-lag kernel for cell09, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.228, stderr 0.020, n = 58). While segmenting epochs for cell14, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.090, stderr 0.019, n = 46). This is the part that will need a real statistical argument.

While bootstrapping the CI for cell08, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.207, stderr 0.025, n = 48). While re-running with a tighter segmentation threshold for cell22, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.257, stderr 0.039, n = 43). While checking residual autocorrelation for cell07, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.115, stderr 0.037, n = 54). While auditing the holding potential column for cell24, the CI narrowed by roughly a tenth (coefficient 0.098, stderr 0.045, n = 42).

```python
coefs = fit_per_cell(rows, threshold=0.68)
lo, hi = ci(coefs, seed=3)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell01    0.201  0.036   0.131  0.270  44        1000
cell05    0.105  0.025   0.056  0.154  47        4000
cell07    0.132  0.028   0.077  0.186  38        4000
cell20    0.181  0.048   0.087  0.274  56        1000
cell17    0.243  0.048   0.150  0.337  54        500
cell24    0.279  0.024   0.232  0.327  46        4000
cell06    0.160  0.043   0.076  0.244  52        1000
cell23    0.306  0.030   0.247  0.365  55        1000
cell01    0.149  0.020   0.109  0.189  45        500
```

### Step 30: comparing per-cell orderings

While bootstrapping the CI for cell06, the ordering of cells was preserved (coefficient 0.204, stderr 0.041, n = 50). While bootstrapping the CI for cell23, nothing in the figure changed at print size (coefficient 0.242, stderr 0.048, n = 40). While re-running with a tighter segmentation threshold for cell22, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.142, stderr 0.029, n = 44). While checking residual autocorrelation for cell09, the coefficient tracked epoch count more closely than duration (coefficient 0.172, stderr 0.014, n = 41).

While bootstrapping the CI for cell09, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.229, stderr 0.012, n = 52). While checking residual autocorrelation for cell03, two cells fell out of the usable range (coefficient 0.256, stderr 0.012, n = 46). While fitting the one-lag kernel for cell02, the CI narrowed by roughly a tenth (coefficient 0.210, stderr 0.026, n = 46). While fitting the one-lag kernel for cell06, nothing in the figure changed at print size (coefficient 0.128, stderr 0.033, n = 50). Noted and moved on; it does not change the decision.

```python
coefs = fit_per_cell(rows, threshold=0.57)
lo, hi = ci(coefs, seed=74)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 31: fitting the one-lag kernel

```python
coefs = fit_per_cell(rows, threshold=0.51)
lo, hi = ci(coefs, seed=74)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```python
coefs = fit_per_cell(rows, threshold=0.49)
lo, hi = ci(coefs, seed=9)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 32: auditing the holding potential column

While checking residual autocorrelation for cell13, two cells fell out of the usable range (coefficient 0.275, stderr 0.038, n = 54). While re-running with a tighter segmentation threshold for cell23, the estimate moved less than one standard error (coefficient 0.256, stderr 0.048, n = 50). While segmenting epochs for cell09, two cells fell out of the usable range (coefficient 0.088, stderr 0.047, n = 46). While auditing the holding potential column for cell21, the CI narrowed by roughly a tenth (coefficient 0.258, stderr 0.041, n = 55). While fitting the one-lag kernel for cell14, the CI narrowed by roughly a tenth (coefficient 0.174, stderr 0.023, n = 38).

```python
coefs = fit_per_cell(rows, threshold=0.39)
lo, hi = ci(coefs, seed=19)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

