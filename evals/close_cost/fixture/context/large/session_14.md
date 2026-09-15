# Prior session 14 of 20

Transcript of an earlier working session on the history-kernel analysis.

### Step 1: re-exporting the raw traces

While auditing the holding potential column for cell24, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.176, stderr 0.040, n = 47). While re-running with a tighter segmentation threshold for cell03, nothing in the figure changed at print size (coefficient 0.229, stderr 0.040, n = 42). While bootstrapping the CI for cell15, nothing in the figure changed at print size (coefficient 0.309, stderr 0.031, n = 52). While segmenting epochs for cell20, the CI narrowed by roughly a tenth (coefficient 0.216, stderr 0.046, n = 41). While fitting the one-lag kernel for cell22, the ordering of cells was preserved (coefficient 0.147, stderr 0.016, n = 45). This is the part that will need a real statistical argument.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell03    0.143  0.040   0.065  0.221  53        4000
cell15    0.106  0.012   0.083  0.129  52        1000
cell11    0.276  0.013   0.250  0.302  53        500
cell13    0.134  0.043   0.050  0.217  57        4000
cell04    0.092  0.028   0.036  0.147  54        1000
cell02    0.089  0.014   0.061  0.117  50        2000
cell18    0.293  0.047   0.202  0.384  51        2000
cell24    0.234  0.027   0.182  0.287  51        500
cell18    0.261  0.024   0.215  0.308  56        1000
cell18    0.098  0.050   0.001  0.195  55        4000
cell18    0.095  0.029   0.038  0.152  44        4000
```

### Step 2: segmenting epochs

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell22    0.208  0.027   0.154  0.261  48        4000
cell17    0.265  0.013   0.240  0.289  57        500
cell07    0.191  0.044   0.104  0.278  38        1000
cell05    0.306  0.010   0.286  0.326  40        1000
cell01    0.097  0.042   0.014  0.179  43        4000
cell15    0.229  0.036   0.159  0.299  58        2000
cell01    0.182  0.042   0.100  0.263  40        500
cell11    0.187  0.049   0.090  0.284  51        2000
cell08    0.274  0.020   0.235  0.312  52        500
cell16    0.168  0.014   0.142  0.195  46        500
cell06    0.083  0.040   0.005  0.162  46        1000
cell14    0.180  0.040   0.101  0.259  38        500
```

While auditing the holding potential column for cell04, nothing in the figure changed at print size (coefficient 0.290, stderr 0.045, n = 56). While auditing the holding potential column for cell11, nothing in the figure changed at print size (coefficient 0.098, stderr 0.018, n = 47). While segmenting epochs for cell01, the estimate moved less than one standard error (coefficient 0.135, stderr 0.028, n = 48).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell02    0.211  0.017   0.178  0.243  43        500
cell08    0.104  0.033   0.039  0.169  47        1000
cell06    0.100  0.050   0.003  0.198  39        1000
cell22    0.144  0.044   0.058  0.231  38        2000
cell03    0.214  0.045   0.126  0.302  45        2000
cell15    0.154  0.039   0.077  0.230  45        500
cell08    0.127  0.038   0.053  0.201  47        4000
cell06    0.227  0.046   0.138  0.317  43        500
```

```python
coefs = fit_per_cell(rows, threshold=0.45)
lo, hi = ci(coefs, seed=63)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 3: checking residual autocorrelation

While fitting the one-lag kernel for cell21, the ordering of cells was preserved (coefficient 0.301, stderr 0.015, n = 56). While re-exporting the raw traces for cell16, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.107, stderr 0.046, n = 49). While auditing the holding potential column for cell23, the estimate moved less than one standard error (coefficient 0.118, stderr 0.030, n = 38). While checking residual autocorrelation for cell17, two cells fell out of the usable range (coefficient 0.085, stderr 0.032, n = 49). While checking residual autocorrelation for cell05, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.284, stderr 0.020, n = 50).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell11    0.153  0.028   0.098  0.209  54        2000
cell15    0.198  0.044   0.112  0.284  56        2000
cell06    0.160  0.040   0.082  0.238  50        500
cell14    0.247  0.041   0.166  0.328  48        1000
cell08    0.244  0.035   0.176  0.311  58        1000
cell08    0.242  0.030   0.182  0.301  38        500
cell15    0.232  0.025   0.183  0.280  43        2000
cell09    0.266  0.021   0.225  0.307  42        1000
cell02    0.194  0.037   0.121  0.267  46        2000
```

```python
coefs = fit_per_cell(rows, threshold=0.45)
lo, hi = ci(coefs, seed=55)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell08    0.274  0.018   0.238  0.310  39        2000
cell18    0.174  0.013   0.149  0.199  40        1000
cell03    0.272  0.038   0.198  0.346  43        4000
cell19    0.223  0.040   0.144  0.301  46        1000
cell11    0.234  0.039   0.157  0.312  42        2000
cell24    0.296  0.029   0.239  0.353  58        1000
cell22    0.163  0.012   0.138  0.187  51        4000
```

### Step 4: comparing per-cell orderings

While segmenting epochs for cell03, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.212, stderr 0.025, n = 49). While fitting the one-lag kernel for cell03, nothing in the figure changed at print size (coefficient 0.171, stderr 0.027, n = 41). While re-running with a tighter segmentation threshold for cell07, two cells fell out of the usable range (coefficient 0.285, stderr 0.042, n = 39). While segmenting epochs for cell02, nothing in the figure changed at print size (coefficient 0.258, stderr 0.035, n = 43).

```python
coefs = fit_per_cell(rows, threshold=0.54)
lo, hi = ci(coefs, seed=61)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While bootstrapping the CI for cell02, the coefficient tracked epoch count more closely than duration (coefficient 0.252, stderr 0.016, n = 39). While segmenting epochs for cell19, the estimate moved less than one standard error (coefficient 0.243, stderr 0.041, n = 49). While bootstrapping the CI for cell05, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.146, stderr 0.015, n = 43). While bootstrapping the CI for cell06, the coefficient tracked epoch count more closely than duration (coefficient 0.114, stderr 0.034, n = 53). While comparing per-cell orderings for cell15, nothing in the figure changed at print size (coefficient 0.190, stderr 0.015, n = 48). While segmenting epochs for cell19, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.161, stderr 0.033, n = 48).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell02    0.259  0.032   0.197  0.321  45        1000
cell10    0.213  0.030   0.155  0.271  57        500
cell19    0.149  0.049   0.054  0.245  40        4000
cell09    0.090  0.021   0.049  0.132  50        500
cell09    0.197  0.013   0.171  0.223  44        2000
cell05    0.088  0.032   0.025  0.152  46        500
cell13    0.202  0.023   0.157  0.247  46        4000
```

### Step 5: checking residual autocorrelation

While checking residual autocorrelation for cell11, the CI narrowed by roughly a tenth (coefficient 0.267, stderr 0.020, n = 52). While bootstrapping the CI for cell13, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.187, stderr 0.013, n = 51). While segmenting epochs for cell05, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.114, stderr 0.016, n = 57).

While segmenting epochs for cell16, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.278, stderr 0.017, n = 40). While fitting the one-lag kernel for cell08, the coefficient tracked epoch count more closely than duration (coefficient 0.292, stderr 0.048, n = 52). While re-running with a tighter segmentation threshold for cell05, the ordering of cells was preserved (coefficient 0.200, stderr 0.049, n = 53). While segmenting epochs for cell14, the CI narrowed by roughly a tenth (coefficient 0.164, stderr 0.021, n = 56). While segmenting epochs for cell14, the coefficient tracked epoch count more closely than duration (coefficient 0.098, stderr 0.032, n = 55). While comparing per-cell orderings for cell17, the coefficient tracked epoch count more closely than duration (coefficient 0.280, stderr 0.018, n = 47).

```python
coefs = fit_per_cell(rows, threshold=0.51)
lo, hi = ci(coefs, seed=16)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While comparing per-cell orderings for cell11, the CI narrowed by roughly a tenth (coefficient 0.217, stderr 0.027, n = 40). While comparing per-cell orderings for cell21, the estimate moved less than one standard error (coefficient 0.238, stderr 0.036, n = 41). While comparing per-cell orderings for cell12, two cells fell out of the usable range (coefficient 0.101, stderr 0.045, n = 41). While auditing the holding potential column for cell06, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.130, stderr 0.017, n = 49). While bootstrapping the CI for cell22, the CI narrowed by roughly a tenth (coefficient 0.191, stderr 0.040, n = 58). While auditing the holding potential column for cell18, the coefficient tracked epoch count more closely than duration (coefficient 0.295, stderr 0.048, n = 39). Parking this until the re-segmentation lands.

### Step 6: auditing the holding potential column

While checking residual autocorrelation for cell08, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.103, stderr 0.041, n = 48). While auditing the holding potential column for cell19, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.150, stderr 0.038, n = 46). While segmenting epochs for cell01, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.291, stderr 0.038, n = 38). While re-running with a tighter segmentation threshold for cell07, two cells fell out of the usable range (coefficient 0.190, stderr 0.029, n = 43). While checking residual autocorrelation for cell11, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.279, stderr 0.019, n = 41). Flagging it so it does not get rediscovered next week.

While re-running with a tighter segmentation threshold for cell09, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.248, stderr 0.016, n = 55). While re-exporting the raw traces for cell03, the ordering of cells was preserved (coefficient 0.210, stderr 0.045, n = 57). While checking residual autocorrelation for cell07, nothing in the figure changed at print size (coefficient 0.092, stderr 0.046, n = 53). While re-running with a tighter segmentation threshold for cell01, the coefficient tracked epoch count more closely than duration (coefficient 0.128, stderr 0.038, n = 56). While auditing the holding potential column for cell03, the coefficient tracked epoch count more closely than duration (coefficient 0.192, stderr 0.048, n = 43).

### Step 7: fitting the one-lag kernel

While bootstrapping the CI for cell01, the ordering of cells was preserved (coefficient 0.193, stderr 0.025, n = 40). While auditing the holding potential column for cell02, the coefficient tracked epoch count more closely than duration (coefficient 0.267, stderr 0.028, n = 57). While fitting the one-lag kernel for cell14, two cells fell out of the usable range (coefficient 0.277, stderr 0.022, n = 39). While checking residual autocorrelation for cell14, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.145, stderr 0.014, n = 45). While re-running with a tighter segmentation threshold for cell21, the ordering of cells was preserved (coefficient 0.300, stderr 0.024, n = 55). While bootstrapping the CI for cell17, the ordering of cells was preserved (coefficient 0.246, stderr 0.035, n = 45).

While checking residual autocorrelation for cell19, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.155, stderr 0.019, n = 52). While re-exporting the raw traces for cell20, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.292, stderr 0.031, n = 43). While bootstrapping the CI for cell05, nothing in the figure changed at print size (coefficient 0.105, stderr 0.043, n = 47).

### Step 8: re-running with a tighter segmentation threshold

While segmenting epochs for cell24, the ordering of cells was preserved (coefficient 0.111, stderr 0.036, n = 52). While re-running with a tighter segmentation threshold for cell22, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.272, stderr 0.015, n = 57). While re-exporting the raw traces for cell24, the coefficient tracked epoch count more closely than duration (coefficient 0.105, stderr 0.044, n = 39). While comparing per-cell orderings for cell20, the CI narrowed by roughly a tenth (coefficient 0.165, stderr 0.025, n = 47). While segmenting epochs for cell24, the coefficient tracked epoch count more closely than duration (coefficient 0.143, stderr 0.037, n = 38). While auditing the holding potential column for cell22, two cells fell out of the usable range (coefficient 0.232, stderr 0.031, n = 51). Noted and moved on; it does not change the decision.

While checking residual autocorrelation for cell13, the estimate moved less than one standard error (coefficient 0.276, stderr 0.045, n = 47). While re-running with a tighter segmentation threshold for cell15, the CI narrowed by roughly a tenth (coefficient 0.172, stderr 0.027, n = 54). While auditing the holding potential column for cell17, the estimate moved less than one standard error (coefficient 0.201, stderr 0.018, n = 55). While bootstrapping the CI for cell21, the ordering of cells was preserved (coefficient 0.086, stderr 0.017, n = 44). While comparing per-cell orderings for cell01, the coefficient tracked epoch count more closely than duration (coefficient 0.169, stderr 0.027, n = 46). Worth noting for the writeup, though not a result on its own.

While fitting the one-lag kernel for cell24, the CI narrowed by roughly a tenth (coefficient 0.179, stderr 0.026, n = 51). While checking residual autocorrelation for cell21, two cells fell out of the usable range (coefficient 0.136, stderr 0.039, n = 53). While auditing the holding potential column for cell09, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.277, stderr 0.012, n = 51).

### Step 9: fitting the one-lag kernel

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell21    0.294  0.019   0.257  0.331  38        2000
cell14    0.126  0.013   0.102  0.151  41        1000
cell01    0.236  0.026   0.186  0.287  55        500
cell01    0.228  0.040   0.150  0.305  54        2000
cell01    0.305  0.015   0.275  0.335  49        4000
cell18    0.143  0.031   0.082  0.203  52        4000
cell24    0.306  0.023   0.262  0.351  41        500
cell09    0.223  0.016   0.192  0.254  45        1000
cell01    0.301  0.037   0.229  0.374  53        1000
cell19    0.252  0.022   0.209  0.294  52        1000
cell24    0.137  0.041   0.057  0.217  53        4000
cell16    0.304  0.020   0.266  0.343  43        4000
cell01    0.270  0.017   0.237  0.303  54        500
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell11    0.223  0.020   0.183  0.263  40        1000
cell13    0.119  0.038   0.045  0.192  56        2000
cell19    0.277  0.030   0.217  0.336  54        500
cell11    0.203  0.010   0.183  0.223  49        2000
cell02    0.148  0.014   0.121  0.176  40        1000
cell04    0.252  0.047   0.160  0.344  53        4000
cell12    0.230  0.044   0.143  0.316  43        500
cell01    0.220  0.011   0.199  0.241  46        4000
cell03    0.214  0.023   0.170  0.258  39        1000
cell11    0.199  0.015   0.170  0.229  55        4000
cell01    0.126  0.025   0.076  0.176  45        500
cell09    0.243  0.042   0.161  0.324  57        2000
cell23    0.266  0.041   0.185  0.346  42        2000
cell07    0.138  0.025   0.089  0.187  50        2000
```

While auditing the holding potential column for cell24, the estimate moved less than one standard error (coefficient 0.308, stderr 0.026, n = 53). While comparing per-cell orderings for cell04, nothing in the figure changed at print size (coefficient 0.205, stderr 0.038, n = 52). While re-exporting the raw traces for cell02, the CI narrowed by roughly a tenth (coefficient 0.309, stderr 0.020, n = 40). While segmenting epochs for cell19, nothing in the figure changed at print size (coefficient 0.110, stderr 0.024, n = 58). While re-exporting the raw traces for cell12, two cells fell out of the usable range (coefficient 0.228, stderr 0.021, n = 52). While re-running with a tighter segmentation threshold for cell20, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.191, stderr 0.039, n = 50).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell24    0.296  0.018   0.261  0.331  47        4000
cell14    0.128  0.036   0.057  0.199  51        2000
cell21    0.128  0.036   0.058  0.199  45        500
cell23    0.164  0.040   0.085  0.244  57        500
cell11    0.167  0.050   0.070  0.265  47        2000
cell02    0.085  0.040   0.006  0.163  45        2000
cell12    0.142  0.022   0.100  0.184  40        4000
cell13    0.148  0.044   0.062  0.233  48        1000
cell02    0.262  0.015   0.233  0.292  53        2000
cell08    0.121  0.033   0.056  0.186  47        500
cell08    0.251  0.046   0.162  0.341  52        2000
```

### Step 10: bootstrapping the CI

While bootstrapping the CI for cell02, the ordering of cells was preserved (coefficient 0.289, stderr 0.022, n = 40). While re-running with a tighter segmentation threshold for cell13, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.173, stderr 0.018, n = 38). While re-running with a tighter segmentation threshold for cell18, the estimate moved less than one standard error (coefficient 0.284, stderr 0.014, n = 42).

```python
coefs = fit_per_cell(rows, threshold=0.42)
lo, hi = ci(coefs, seed=5)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While re-exporting the raw traces for cell14, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.305, stderr 0.029, n = 48). While comparing per-cell orderings for cell23, the coefficient tracked epoch count more closely than duration (coefficient 0.122, stderr 0.042, n = 38). While segmenting epochs for cell20, nothing in the figure changed at print size (coefficient 0.266, stderr 0.035, n = 53). While comparing per-cell orderings for cell16, two cells fell out of the usable range (coefficient 0.206, stderr 0.039, n = 48). While segmenting epochs for cell23, the estimate moved less than one standard error (coefficient 0.158, stderr 0.019, n = 38). While bootstrapping the CI for cell03, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.137, stderr 0.026, n = 46). This is the part that will need a real statistical argument.

```python
coefs = fit_per_cell(rows, threshold=0.70)
lo, hi = ci(coefs, seed=81)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 11: segmenting epochs

While re-running with a tighter segmentation threshold for cell17, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.232, stderr 0.026, n = 56). While bootstrapping the CI for cell02, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.272, stderr 0.024, n = 51). While auditing the holding potential column for cell12, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.093, stderr 0.011, n = 44). While re-running with a tighter segmentation threshold for cell11, the ordering of cells was preserved (coefficient 0.081, stderr 0.022, n = 52).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell06    0.208  0.049   0.111  0.304  56        1000
cell16    0.184  0.019   0.148  0.220  40        500
cell23    0.207  0.041   0.126  0.288  55        4000
cell05    0.150  0.042   0.068  0.231  44        500
cell18    0.227  0.042   0.145  0.310  58        1000
cell04    0.305  0.047   0.213  0.397  51        1000
cell03    0.136  0.017   0.102  0.169  41        1000
cell20    0.094  0.016   0.063  0.125  41        4000
cell05    0.302  0.024   0.255  0.349  53        1000
cell13    0.123  0.028   0.068  0.178  54        1000
cell10    0.203  0.016   0.172  0.234  45        500
```

### Step 12: auditing the holding potential column

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell01    0.292  0.022   0.250  0.335  45        500
cell08    0.162  0.016   0.131  0.193  46        500
cell11    0.275  0.040   0.197  0.353  53        1000
cell03    0.225  0.031   0.164  0.286  47        2000
cell08    0.211  0.035   0.142  0.279  41        1000
cell06    0.190  0.027   0.137  0.243  48        4000
cell20    0.243  0.041   0.164  0.323  43        1000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell11    0.217  0.021   0.176  0.259  55        4000
cell23    0.305  0.040   0.227  0.383  39        4000
cell03    0.155  0.046   0.064  0.246  48        4000
cell08    0.207  0.020   0.168  0.247  57        2000
cell20    0.242  0.045   0.153  0.330  52        2000
cell07    0.103  0.037   0.031  0.175  46        1000
cell08    0.167  0.010   0.146  0.187  46        500
cell08    0.297  0.018   0.261  0.332  53        500
cell14    0.276  0.029   0.220  0.332  50        2000
cell22    0.119  0.020   0.080  0.158  53        500
cell20    0.093  0.021   0.052  0.134  55        1000
cell11    0.180  0.026   0.128  0.231  45        500
cell15    0.281  0.010   0.261  0.302  53        2000
cell17    0.129  0.015   0.100  0.158  44        4000
```

While comparing per-cell orderings for cell19, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.164, stderr 0.048, n = 53). While fitting the one-lag kernel for cell16, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.117, stderr 0.050, n = 45). While re-exporting the raw traces for cell06, the CI narrowed by roughly a tenth (coefficient 0.149, stderr 0.012, n = 47).

### Step 13: re-exporting the raw traces

While bootstrapping the CI for cell12, the estimate moved less than one standard error (coefficient 0.156, stderr 0.042, n = 42). While checking residual autocorrelation for cell12, the ordering of cells was preserved (coefficient 0.194, stderr 0.031, n = 57). While checking residual autocorrelation for cell05, the CI narrowed by roughly a tenth (coefficient 0.219, stderr 0.024, n = 56). While re-running with a tighter segmentation threshold for cell07, the estimate moved less than one standard error (coefficient 0.217, stderr 0.048, n = 48). While segmenting epochs for cell05, the coefficient tracked epoch count more closely than duration (coefficient 0.201, stderr 0.033, n = 51). While auditing the holding potential column for cell18, the CI narrowed by roughly a tenth (coefficient 0.094, stderr 0.026, n = 49). Parking this until the re-segmentation lands.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell13    0.088  0.029   0.031  0.145  41        4000
cell05    0.288  0.050   0.190  0.386  52        500
cell14    0.117  0.017   0.083  0.150  48        500
cell19    0.228  0.035   0.160  0.297  53        500
cell13    0.144  0.023   0.098  0.190  54        1000
cell11    0.098  0.041   0.018  0.178  43        500
cell13    0.148  0.015   0.118  0.179  51        2000
```

### Step 14: re-exporting the raw traces

While auditing the holding potential column for cell24, two cells fell out of the usable range (coefficient 0.178, stderr 0.048, n = 53). While re-running with a tighter segmentation threshold for cell09, the ordering of cells was preserved (coefficient 0.278, stderr 0.016, n = 40). While bootstrapping the CI for cell03, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.111, stderr 0.039, n = 43).

```python
coefs = fit_per_cell(rows, threshold=0.60)
lo, hi = ci(coefs, seed=6)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While bootstrapping the CI for cell05, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.291, stderr 0.030, n = 38). While checking residual autocorrelation for cell05, the estimate moved less than one standard error (coefficient 0.235, stderr 0.038, n = 41). While segmenting epochs for cell05, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.111, stderr 0.024, n = 45). While segmenting epochs for cell22, the ordering of cells was preserved (coefficient 0.114, stderr 0.012, n = 57).

While re-exporting the raw traces for cell20, nothing in the figure changed at print size (coefficient 0.125, stderr 0.047, n = 54). While bootstrapping the CI for cell04, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.176, stderr 0.029, n = 44). While checking residual autocorrelation for cell13, the CI narrowed by roughly a tenth (coefficient 0.185, stderr 0.048, n = 48). While comparing per-cell orderings for cell19, nothing in the figure changed at print size (coefficient 0.155, stderr 0.012, n = 45). Parking this until the re-segmentation lands.

### Step 15: auditing the holding potential column

While segmenting epochs for cell22, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.218, stderr 0.046, n = 44). While fitting the one-lag kernel for cell04, the coefficient tracked epoch count more closely than duration (coefficient 0.093, stderr 0.020, n = 58). While auditing the holding potential column for cell20, the estimate moved less than one standard error (coefficient 0.092, stderr 0.018, n = 49). While checking residual autocorrelation for cell16, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.245, stderr 0.019, n = 39). This is the part that will need a real statistical argument.

```python
coefs = fit_per_cell(rows, threshold=0.68)
lo, hi = ci(coefs, seed=0)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While auditing the holding potential column for cell22, the coefficient tracked epoch count more closely than duration (coefficient 0.147, stderr 0.033, n = 45). While re-running with a tighter segmentation threshold for cell03, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.180, stderr 0.021, n = 45). While segmenting epochs for cell24, the ordering of cells was preserved (coefficient 0.208, stderr 0.047, n = 48). While re-running with a tighter segmentation threshold for cell17, nothing in the figure changed at print size (coefficient 0.217, stderr 0.035, n = 48). Noted and moved on; it does not change the decision.

### Step 16: re-exporting the raw traces

While comparing per-cell orderings for cell10, the coefficient tracked epoch count more closely than duration (coefficient 0.108, stderr 0.022, n = 58). While checking residual autocorrelation for cell17, the CI narrowed by roughly a tenth (coefficient 0.299, stderr 0.025, n = 48). While re-exporting the raw traces for cell11, nothing in the figure changed at print size (coefficient 0.267, stderr 0.032, n = 48). While auditing the holding potential column for cell02, nothing in the figure changed at print size (coefficient 0.275, stderr 0.038, n = 39). This is the part that will need a real statistical argument.

While segmenting epochs for cell23, the coefficient tracked epoch count more closely than duration (coefficient 0.290, stderr 0.013, n = 57). While re-exporting the raw traces for cell24, two cells fell out of the usable range (coefficient 0.143, stderr 0.011, n = 53). While bootstrapping the CI for cell16, nothing in the figure changed at print size (coefficient 0.094, stderr 0.040, n = 43). While re-running with a tighter segmentation threshold for cell14, two cells fell out of the usable range (coefficient 0.123, stderr 0.040, n = 50). While checking residual autocorrelation for cell22, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.195, stderr 0.017, n = 48). While checking residual autocorrelation for cell01, the coefficient tracked epoch count more closely than duration (coefficient 0.280, stderr 0.024, n = 55). Parking this until the re-segmentation lands.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell12    0.300  0.043   0.215  0.385  44        500
cell15    0.297  0.018   0.262  0.331  46        1000
cell22    0.208  0.047   0.116  0.300  44        2000
cell14    0.118  0.015   0.089  0.147  40        500
cell21    0.156  0.038   0.081  0.230  52        500
cell17    0.300  0.012   0.276  0.325  49        500
cell11    0.145  0.027   0.092  0.197  57        500
cell08    0.212  0.013   0.187  0.237  54        500
```

### Step 17: comparing per-cell orderings

While fitting the one-lag kernel for cell21, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.275, stderr 0.039, n = 44). While segmenting epochs for cell14, the ordering of cells was preserved (coefficient 0.300, stderr 0.021, n = 51). While bootstrapping the CI for cell03, nothing in the figure changed at print size (coefficient 0.253, stderr 0.040, n = 46). Noted and moved on; it does not change the decision.

```python
coefs = fit_per_cell(rows, threshold=0.41)
lo, hi = ci(coefs, seed=15)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell02    0.178  0.045   0.089  0.267  51        2000
cell14    0.198  0.043   0.113  0.283  50        500
cell03    0.088  0.039   0.010  0.165  47        500
cell16    0.160  0.034   0.094  0.227  43        2000
cell18    0.274  0.049   0.177  0.370  40        1000
cell09    0.226  0.038   0.150  0.301  55        1000
cell07    0.166  0.015   0.138  0.195  56        2000
cell06    0.268  0.038   0.194  0.342  58        500
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell15    0.222  0.037   0.150  0.295  50        4000
cell06    0.173  0.021   0.133  0.214  54        2000
cell15    0.177  0.021   0.136  0.218  53        1000
cell06    0.205  0.020   0.166  0.243  44        2000
cell21    0.092  0.019   0.054  0.130  51        4000
cell20    0.084  0.014   0.056  0.111  49        2000
cell02    0.175  0.048   0.081  0.269  40        2000
cell17    0.287  0.032   0.224  0.351  44        4000
cell16    0.249  0.047   0.157  0.341  47        500
cell07    0.224  0.031   0.164  0.284  54        4000
cell18    0.173  0.038   0.098  0.248  57        1000
cell12    0.298  0.047   0.206  0.390  38        4000
cell10    0.270  0.012   0.247  0.292  41        1000
cell02    0.141  0.018   0.106  0.177  47        2000
```

### Step 18: segmenting epochs

While re-exporting the raw traces for cell06, the ordering of cells was preserved (coefficient 0.179, stderr 0.048, n = 49). While fitting the one-lag kernel for cell02, two cells fell out of the usable range (coefficient 0.128, stderr 0.041, n = 53). While comparing per-cell orderings for cell12, nothing in the figure changed at print size (coefficient 0.244, stderr 0.033, n = 58). While checking residual autocorrelation for cell15, the CI narrowed by roughly a tenth (coefficient 0.142, stderr 0.049, n = 44). While segmenting epochs for cell08, the coefficient tracked epoch count more closely than duration (coefficient 0.131, stderr 0.029, n = 53). While checking residual autocorrelation for cell21, the estimate moved less than one standard error (coefficient 0.245, stderr 0.046, n = 40). Parking this until the re-segmentation lands.

While re-exporting the raw traces for cell15, two cells fell out of the usable range (coefficient 0.210, stderr 0.033, n = 51). While segmenting epochs for cell19, the CI narrowed by roughly a tenth (coefficient 0.149, stderr 0.031, n = 53). While checking residual autocorrelation for cell03, the CI narrowed by roughly a tenth (coefficient 0.160, stderr 0.036, n = 54). While re-exporting the raw traces for cell20, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.156, stderr 0.039, n = 51). While auditing the holding potential column for cell03, the coefficient tracked epoch count more closely than duration (coefficient 0.247, stderr 0.027, n = 47).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell18    0.160  0.037   0.089  0.232  41        1000
cell11    0.115  0.029   0.058  0.171  46        2000
cell20    0.158  0.046   0.068  0.249  40        1000
cell16    0.229  0.045   0.142  0.317  49        1000
cell02    0.171  0.016   0.141  0.202  52        4000
cell12    0.216  0.042   0.134  0.299  43        1000
cell04    0.177  0.017   0.144  0.210  41        500
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell24    0.191  0.040   0.112  0.270  42        500
cell07    0.258  0.047   0.167  0.350  51        2000
cell09    0.185  0.036   0.115  0.255  42        1000
cell15    0.146  0.040   0.067  0.224  46        1000
cell02    0.129  0.030   0.070  0.188  52        1000
cell13    0.269  0.011   0.248  0.290  42        1000
cell09    0.275  0.038   0.200  0.350  56        2000
cell13    0.198  0.047   0.107  0.290  48        4000
cell13    0.172  0.037   0.101  0.244  47        4000
cell17    0.301  0.044   0.214  0.387  51        2000
cell16    0.103  0.036   0.033  0.173  48        4000
cell13    0.288  0.045   0.199  0.376  51        2000
```

### Step 19: re-running with a tighter segmentation threshold

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell02    0.256  0.037   0.183  0.329  54        4000
cell07    0.167  0.021   0.126  0.207  48        500
cell23    0.237  0.017   0.204  0.270  51        4000
cell07    0.172  0.032   0.110  0.233  58        1000
cell06    0.162  0.048   0.068  0.257  54        4000
cell22    0.096  0.034   0.030  0.163  39        2000
cell03    0.187  0.047   0.095  0.279  48        2000
cell16    0.245  0.041   0.165  0.325  49        1000
cell10    0.093  0.049   -0.003  0.189  39        2000
cell21    0.309  0.044   0.223  0.395  46        1000
cell19    0.096  0.015   0.068  0.125  53        4000
cell18    0.200  0.017   0.166  0.234  53        4000
cell02    0.258  0.029   0.202  0.314  47        500
```

While fitting the one-lag kernel for cell06, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.262, stderr 0.030, n = 56). While re-running with a tighter segmentation threshold for cell13, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.299, stderr 0.030, n = 53). While bootstrapping the CI for cell15, the CI narrowed by roughly a tenth (coefficient 0.141, stderr 0.013, n = 47). While checking residual autocorrelation for cell13, the CI narrowed by roughly a tenth (coefficient 0.140, stderr 0.029, n = 52). While re-running with a tighter segmentation threshold for cell23, the coefficient tracked epoch count more closely than duration (coefficient 0.231, stderr 0.014, n = 51). While segmenting epochs for cell23, the CI narrowed by roughly a tenth (coefficient 0.289, stderr 0.020, n = 49). Noted and moved on; it does not change the decision.

While fitting the one-lag kernel for cell08, the estimate moved less than one standard error (coefficient 0.097, stderr 0.033, n = 57). While segmenting epochs for cell04, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.164, stderr 0.046, n = 46). While bootstrapping the CI for cell05, the estimate moved less than one standard error (coefficient 0.108, stderr 0.031, n = 56).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell01    0.177  0.013   0.151  0.202  38        1000
cell10    0.198  0.013   0.172  0.224  38        2000
cell06    0.168  0.045   0.080  0.255  52        2000
cell14    0.208  0.011   0.187  0.229  39        1000
cell22    0.233  0.034   0.168  0.299  47        500
cell02    0.249  0.017   0.216  0.282  43        4000
```

### Step 20: fitting the one-lag kernel

While bootstrapping the CI for cell05, the CI narrowed by roughly a tenth (coefficient 0.116, stderr 0.020, n = 38). While auditing the holding potential column for cell23, the CI narrowed by roughly a tenth (coefficient 0.099, stderr 0.039, n = 43). While comparing per-cell orderings for cell01, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.153, stderr 0.020, n = 56). Noted and moved on; it does not change the decision.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell16    0.298  0.037   0.227  0.370  53        1000
cell12    0.097  0.014   0.071  0.124  47        500
cell06    0.138  0.048   0.043  0.232  51        1000
cell01    0.224  0.019   0.186  0.262  57        2000
cell14    0.111  0.017   0.079  0.144  40        1000
cell01    0.262  0.013   0.237  0.287  43        2000
cell14    0.253  0.039   0.177  0.329  52        1000
cell21    0.248  0.032   0.185  0.312  47        1000
cell03    0.239  0.044   0.153  0.325  51        1000
cell21    0.132  0.029   0.076  0.189  49        1000
cell05    0.161  0.023   0.117  0.206  45        2000
cell23    0.305  0.024   0.259  0.352  54        1000
cell08    0.288  0.048   0.195  0.381  46        2000
```

While comparing per-cell orderings for cell02, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.169, stderr 0.028, n = 42). While comparing per-cell orderings for cell21, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.214, stderr 0.046, n = 55). While segmenting epochs for cell17, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.205, stderr 0.023, n = 49).

### Step 21: comparing per-cell orderings

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell16    0.261  0.018   0.225  0.296  53        4000
cell07    0.271  0.045   0.182  0.359  50        500
cell02    0.120  0.039   0.044  0.197  42        4000
cell16    0.105  0.040   0.026  0.184  54        2000
cell20    0.296  0.043   0.211  0.381  54        500
cell03    0.113  0.025   0.063  0.163  39        4000
cell24    0.100  0.047   0.007  0.192  39        2000
cell22    0.157  0.017   0.124  0.190  53        1000
cell02    0.254  0.038   0.180  0.328  45        2000
cell22    0.183  0.019   0.145  0.221  56        4000
cell03    0.168  0.043   0.082  0.253  42        500
cell12    0.207  0.025   0.159  0.255  42        500
```

While comparing per-cell orderings for cell02, the coefficient tracked epoch count more closely than duration (coefficient 0.238, stderr 0.028, n = 45). While segmenting epochs for cell16, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.144, stderr 0.026, n = 48). While segmenting epochs for cell23, two cells fell out of the usable range (coefficient 0.241, stderr 0.010, n = 50). While checking residual autocorrelation for cell13, two cells fell out of the usable range (coefficient 0.309, stderr 0.021, n = 55). This is the part that will need a real statistical argument.

### Step 22: re-exporting the raw traces

While auditing the holding potential column for cell24, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.141, stderr 0.030, n = 49). While checking residual autocorrelation for cell02, the estimate moved less than one standard error (coefficient 0.105, stderr 0.021, n = 41). While segmenting epochs for cell17, the ordering of cells was preserved (coefficient 0.098, stderr 0.047, n = 54). While re-exporting the raw traces for cell19, the coefficient tracked epoch count more closely than duration (coefficient 0.184, stderr 0.042, n = 38). While bootstrapping the CI for cell09, the estimate moved less than one standard error (coefficient 0.134, stderr 0.014, n = 53).

While comparing per-cell orderings for cell16, the estimate moved less than one standard error (coefficient 0.134, stderr 0.022, n = 58). While comparing per-cell orderings for cell24, nothing in the figure changed at print size (coefficient 0.213, stderr 0.043, n = 57). While comparing per-cell orderings for cell09, the estimate moved less than one standard error (coefficient 0.135, stderr 0.040, n = 42). While comparing per-cell orderings for cell12, the estimate moved less than one standard error (coefficient 0.119, stderr 0.038, n = 43). Worth noting for the writeup, though not a result on its own.

### Step 23: auditing the holding potential column

While segmenting epochs for cell22, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.091, stderr 0.011, n = 40). While comparing per-cell orderings for cell17, the ordering of cells was preserved (coefficient 0.240, stderr 0.036, n = 57). While checking residual autocorrelation for cell20, two cells fell out of the usable range (coefficient 0.094, stderr 0.011, n = 45). While fitting the one-lag kernel for cell02, nothing in the figure changed at print size (coefficient 0.304, stderr 0.036, n = 48). Noted and moved on; it does not change the decision.

While segmenting epochs for cell06, the ordering of cells was preserved (coefficient 0.153, stderr 0.039, n = 52). While bootstrapping the CI for cell18, the ordering of cells was preserved (coefficient 0.206, stderr 0.021, n = 57). While checking residual autocorrelation for cell10, the coefficient tracked epoch count more closely than duration (coefficient 0.275, stderr 0.044, n = 40). While fitting the one-lag kernel for cell17, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.142, stderr 0.042, n = 38). While bootstrapping the CI for cell14, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.196, stderr 0.036, n = 47). While fitting the one-lag kernel for cell08, nothing in the figure changed at print size (coefficient 0.149, stderr 0.044, n = 56). Worth noting for the writeup, though not a result on its own.

While auditing the holding potential column for cell10, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.085, stderr 0.043, n = 54). While re-running with a tighter segmentation threshold for cell20, two cells fell out of the usable range (coefficient 0.114, stderr 0.039, n = 54). While fitting the one-lag kernel for cell23, two cells fell out of the usable range (coefficient 0.161, stderr 0.011, n = 52). While comparing per-cell orderings for cell04, two cells fell out of the usable range (coefficient 0.298, stderr 0.040, n = 46). While comparing per-cell orderings for cell23, two cells fell out of the usable range (coefficient 0.170, stderr 0.043, n = 46). While bootstrapping the CI for cell19, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.293, stderr 0.020, n = 50).

### Step 24: re-running with a tighter segmentation threshold

While bootstrapping the CI for cell05, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.170, stderr 0.026, n = 46). While bootstrapping the CI for cell24, the CI narrowed by roughly a tenth (coefficient 0.202, stderr 0.048, n = 53). While auditing the holding potential column for cell03, the coefficient tracked epoch count more closely than duration (coefficient 0.095, stderr 0.031, n = 38). While comparing per-cell orderings for cell12, the coefficient tracked epoch count more closely than duration (coefficient 0.110, stderr 0.027, n = 42). While re-running with a tighter segmentation threshold for cell22, the ordering of cells was preserved (coefficient 0.219, stderr 0.013, n = 46). Parking this until the re-segmentation lands.

```python
coefs = fit_per_cell(rows, threshold=0.31)
lo, hi = ci(coefs, seed=26)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While segmenting epochs for cell20, the CI narrowed by roughly a tenth (coefficient 0.295, stderr 0.020, n = 57). While checking residual autocorrelation for cell02, the CI narrowed by roughly a tenth (coefficient 0.250, stderr 0.011, n = 48). While fitting the one-lag kernel for cell19, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.155, stderr 0.042, n = 40). While re-running with a tighter segmentation threshold for cell06, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.241, stderr 0.048, n = 57). This is the part that will need a real statistical argument.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell05    0.225  0.026   0.174  0.276  46        500
cell19    0.193  0.018   0.158  0.228  42        4000
cell16    0.187  0.017   0.155  0.220  48        4000
cell21    0.224  0.011   0.201  0.246  54        1000
cell21    0.233  0.041   0.152  0.314  54        500
cell21    0.137  0.043   0.053  0.221  51        2000
cell01    0.108  0.048   0.014  0.202  47        4000
cell17    0.179  0.035   0.110  0.247  46        4000
cell12    0.212  0.010   0.192  0.232  57        2000
cell20    0.307  0.039   0.231  0.382  53        1000
cell20    0.264  0.044   0.178  0.351  46        2000
cell20    0.121  0.018   0.086  0.156  42        2000
```

### Step 25: auditing the holding potential column

While auditing the holding potential column for cell07, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.151, stderr 0.017, n = 42). While re-exporting the raw traces for cell11, the estimate moved less than one standard error (coefficient 0.193, stderr 0.010, n = 50). While segmenting epochs for cell01, the coefficient tracked epoch count more closely than duration (coefficient 0.230, stderr 0.047, n = 52). While checking residual autocorrelation for cell14, the ordering of cells was preserved (coefficient 0.104, stderr 0.026, n = 48). While re-exporting the raw traces for cell12, the coefficient tracked epoch count more closely than duration (coefficient 0.270, stderr 0.047, n = 50).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell10    0.253  0.016   0.221  0.286  43        4000
cell18    0.241  0.037   0.167  0.314  46        4000
cell15    0.219  0.044   0.132  0.306  47        1000
cell12    0.170  0.029   0.113  0.227  48        500
cell21    0.309  0.036   0.239  0.380  56        4000
cell23    0.160  0.039   0.083  0.236  57        2000
cell09    0.204  0.022   0.162  0.246  48        500
cell23    0.118  0.046   0.028  0.208  54        1000
cell14    0.289  0.035   0.221  0.356  46        2000
cell05    0.115  0.039   0.038  0.192  40        2000
```

While comparing per-cell orderings for cell03, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.092, stderr 0.045, n = 54). While checking residual autocorrelation for cell06, the estimate moved less than one standard error (coefficient 0.212, stderr 0.014, n = 46). While bootstrapping the CI for cell06, the ordering of cells was preserved (coefficient 0.117, stderr 0.019, n = 51). Parking this until the re-segmentation lands.

### Step 26: re-exporting the raw traces

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell04    0.292  0.038   0.217  0.366  55        1000
cell21    0.261  0.024   0.214  0.307  43        4000
cell03    0.287  0.011   0.266  0.309  51        2000
cell17    0.123  0.016   0.092  0.154  53        1000
cell16    0.282  0.016   0.250  0.313  49        500
cell12    0.224  0.010   0.204  0.245  49        500
cell13    0.160  0.019   0.122  0.198  57        4000
cell12    0.171  0.029   0.114  0.229  57        1000
cell18    0.291  0.026   0.239  0.342  44        1000
cell02    0.196  0.041   0.117  0.276  53        2000
cell11    0.170  0.027   0.117  0.222  56        500
cell08    0.249  0.012   0.226  0.272  42        4000
cell04    0.179  0.023   0.134  0.224  43        2000
```

While re-running with a tighter segmentation threshold for cell01, nothing in the figure changed at print size (coefficient 0.253, stderr 0.032, n = 51). While re-exporting the raw traces for cell19, two cells fell out of the usable range (coefficient 0.160, stderr 0.026, n = 47). While bootstrapping the CI for cell10, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.255, stderr 0.024, n = 49). While segmenting epochs for cell21, nothing in the figure changed at print size (coefficient 0.199, stderr 0.033, n = 58).

### Step 27: comparing per-cell orderings

While re-exporting the raw traces for cell24, two cells fell out of the usable range (coefficient 0.189, stderr 0.018, n = 46). While re-exporting the raw traces for cell24, the estimate moved less than one standard error (coefficient 0.190, stderr 0.037, n = 46). While re-exporting the raw traces for cell16, nothing in the figure changed at print size (coefficient 0.225, stderr 0.049, n = 53).

While checking residual autocorrelation for cell13, the estimate moved less than one standard error (coefficient 0.098, stderr 0.039, n = 49). While comparing per-cell orderings for cell01, nothing in the figure changed at print size (coefficient 0.164, stderr 0.024, n = 52). While checking residual autocorrelation for cell14, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.117, stderr 0.027, n = 53). While bootstrapping the CI for cell14, two cells fell out of the usable range (coefficient 0.190, stderr 0.036, n = 45). While comparing per-cell orderings for cell17, two cells fell out of the usable range (coefficient 0.244, stderr 0.026, n = 57).

```python
coefs = fit_per_cell(rows, threshold=0.74)
lo, hi = ci(coefs, seed=27)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 28: comparing per-cell orderings

```python
coefs = fit_per_cell(rows, threshold=0.47)
lo, hi = ci(coefs, seed=70)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While bootstrapping the CI for cell14, the coefficient tracked epoch count more closely than duration (coefficient 0.257, stderr 0.031, n = 41). While auditing the holding potential column for cell13, nothing in the figure changed at print size (coefficient 0.126, stderr 0.036, n = 56). While segmenting epochs for cell10, the estimate moved less than one standard error (coefficient 0.293, stderr 0.038, n = 38). While segmenting epochs for cell15, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.159, stderr 0.020, n = 55). While bootstrapping the CI for cell02, the estimate moved less than one standard error (coefficient 0.193, stderr 0.034, n = 53). While checking residual autocorrelation for cell04, nothing in the figure changed at print size (coefficient 0.161, stderr 0.041, n = 52).

### Step 29: re-running with a tighter segmentation threshold

While comparing per-cell orderings for cell24, the coefficient tracked epoch count more closely than duration (coefficient 0.127, stderr 0.043, n = 40). While re-running with a tighter segmentation threshold for cell18, two cells fell out of the usable range (coefficient 0.193, stderr 0.042, n = 42). While auditing the holding potential column for cell11, the CI narrowed by roughly a tenth (coefficient 0.099, stderr 0.012, n = 38). While segmenting epochs for cell14, nothing in the figure changed at print size (coefficient 0.263, stderr 0.011, n = 48). While re-running with a tighter segmentation threshold for cell07, two cells fell out of the usable range (coefficient 0.107, stderr 0.025, n = 41). While segmenting epochs for cell16, the estimate moved less than one standard error (coefficient 0.165, stderr 0.043, n = 42).

While re-running with a tighter segmentation threshold for cell19, the CI narrowed by roughly a tenth (coefficient 0.128, stderr 0.011, n = 53). While segmenting epochs for cell13, two cells fell out of the usable range (coefficient 0.243, stderr 0.028, n = 43). While bootstrapping the CI for cell22, the CI narrowed by roughly a tenth (coefficient 0.276, stderr 0.035, n = 47). While segmenting epochs for cell15, two cells fell out of the usable range (coefficient 0.120, stderr 0.032, n = 58).

### Step 30: segmenting epochs

While re-running with a tighter segmentation threshold for cell16, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.218, stderr 0.038, n = 46). While comparing per-cell orderings for cell17, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.301, stderr 0.023, n = 48). While re-exporting the raw traces for cell08, nothing in the figure changed at print size (coefficient 0.300, stderr 0.039, n = 46). While checking residual autocorrelation for cell01, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.277, stderr 0.035, n = 55). While auditing the holding potential column for cell09, the estimate moved less than one standard error (coefficient 0.277, stderr 0.046, n = 50). Noted and moved on; it does not change the decision.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell23    0.093  0.031   0.033  0.154  45        4000
cell12    0.290  0.035   0.221  0.358  38        2000
cell05    0.155  0.043   0.071  0.240  46        500
cell22    0.207  0.047   0.115  0.299  39        1000
cell19    0.083  0.039   0.007  0.160  56        2000
cell04    0.106  0.040   0.028  0.184  39        4000
cell22    0.290  0.022   0.247  0.332  48        500
cell13    0.193  0.022   0.150  0.236  47        1000
```

### Step 31: bootstrapping the CI

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell01    0.305  0.013   0.280  0.330  53        2000
cell11    0.292  0.028   0.238  0.347  43        2000
cell11    0.223  0.030   0.165  0.281  50        500
cell01    0.223  0.027   0.170  0.275  40        4000
cell22    0.248  0.037   0.175  0.321  55        2000
cell10    0.179  0.016   0.147  0.210  43        1000
cell20    0.240  0.035   0.171  0.310  42        500
cell19    0.168  0.045   0.080  0.256  49        500
cell08    0.269  0.034   0.202  0.337  39        4000
cell06    0.305  0.035   0.237  0.373  49        500
cell22    0.219  0.037   0.146  0.293  48        2000
cell03    0.309  0.029   0.252  0.365  52        500
cell17    0.220  0.037   0.148  0.292  38        1000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell04    0.184  0.028   0.129  0.239  57        2000
cell21    0.308  0.049   0.211  0.404  57        500
cell16    0.303  0.045   0.213  0.392  49        500
cell13    0.180  0.030   0.121  0.239  47        500
cell14    0.164  0.025   0.116  0.212  56        4000
cell01    0.204  0.039   0.127  0.281  43        500
cell16    0.123  0.013   0.099  0.148  41        2000
cell08    0.249  0.011   0.227  0.271  42        1000
cell13    0.120  0.015   0.090  0.150  40        4000
cell04    0.088  0.032   0.025  0.151  49        4000
```

### Step 32: segmenting epochs

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell22    0.290  0.045   0.201  0.379  58        500
cell17    0.110  0.026   0.060  0.161  51        4000
cell24    0.162  0.026   0.111  0.212  47        1000
cell07    0.108  0.035   0.040  0.176  46        1000
cell14    0.143  0.031   0.082  0.204  40        1000
cell22    0.132  0.037   0.060  0.204  48        500
cell24    0.084  0.046   -0.005  0.174  56        2000
cell03    0.198  0.022   0.155  0.240  44        1000
cell18    0.103  0.022   0.059  0.147  46        500
cell17    0.131  0.033   0.065  0.196  58        2000
cell23    0.153  0.021   0.111  0.195  54        2000
cell24    0.100  0.039   0.023  0.177  57        500
cell14    0.217  0.043   0.134  0.300  54        500
```

While re-running with a tighter segmentation threshold for cell11, two cells fell out of the usable range (coefficient 0.292, stderr 0.034, n = 56). While checking residual autocorrelation for cell19, the estimate moved less than one standard error (coefficient 0.156, stderr 0.028, n = 50). While re-exporting the raw traces for cell14, the estimate moved less than one standard error (coefficient 0.202, stderr 0.028, n = 49). While comparing per-cell orderings for cell24, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.283, stderr 0.017, n = 48). While segmenting epochs for cell10, the coefficient tracked epoch count more closely than duration (coefficient 0.190, stderr 0.041, n = 52). While bootstrapping the CI for cell15, two cells fell out of the usable range (coefficient 0.149, stderr 0.046, n = 47).

```python
coefs = fit_per_cell(rows, threshold=0.43)
lo, hi = ci(coefs, seed=18)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 33: fitting the one-lag kernel

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell22    0.143  0.021   0.102  0.183  38        500
cell20    0.253  0.030   0.194  0.313  56        2000
cell09    0.150  0.014   0.122  0.178  54        2000
cell03    0.119  0.050   0.021  0.217  56        1000
cell24    0.293  0.034   0.226  0.360  58        1000
cell04    0.177  0.034   0.111  0.242  43        500
cell13    0.123  0.037   0.049  0.196  49        4000
cell19    0.133  0.031   0.073  0.194  50        500
cell22    0.135  0.028   0.081  0.190  40        4000
cell19    0.093  0.032   0.031  0.155  39        1000
cell18    0.173  0.041   0.093  0.253  39        2000
cell24    0.181  0.019   0.143  0.220  43        500
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell05    0.259  0.046   0.169  0.350  56        2000
cell13    0.290  0.043   0.206  0.375  41        4000
cell23    0.153  0.029   0.096  0.209  48        1000
cell03    0.296  0.042   0.213  0.378  39        1000
cell17    0.286  0.026   0.235  0.338  42        4000
cell21    0.083  0.050   -0.015  0.180  47        500
cell08    0.229  0.038   0.155  0.302  50        500
cell11    0.226  0.037   0.153  0.299  55        4000
cell08    0.116  0.036   0.045  0.186  54        2000
cell07    0.232  0.047   0.139  0.324  53        2000
cell13    0.193  0.023   0.148  0.238  47        500
cell02    0.133  0.046   0.043  0.222  44        500
```

```python
coefs = fit_per_cell(rows, threshold=0.70)
lo, hi = ci(coefs, seed=39)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While re-running with a tighter segmentation threshold for cell15, nothing in the figure changed at print size (coefficient 0.183, stderr 0.025, n = 51). While re-running with a tighter segmentation threshold for cell02, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.289, stderr 0.010, n = 55). While comparing per-cell orderings for cell13, nothing in the figure changed at print size (coefficient 0.244, stderr 0.012, n = 47). While re-exporting the raw traces for cell23, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.158, stderr 0.023, n = 57). This is the part that will need a real statistical argument.

### Step 34: segmenting epochs

While re-running with a tighter segmentation threshold for cell21, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.305, stderr 0.032, n = 50). While re-running with a tighter segmentation threshold for cell11, the CI narrowed by roughly a tenth (coefficient 0.237, stderr 0.044, n = 50). While re-exporting the raw traces for cell06, nothing in the figure changed at print size (coefficient 0.279, stderr 0.026, n = 51). While fitting the one-lag kernel for cell16, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.125, stderr 0.045, n = 41). Flagging it so it does not get rediscovered next week.

While comparing per-cell orderings for cell05, the CI narrowed by roughly a tenth (coefficient 0.135, stderr 0.011, n = 38). While auditing the holding potential column for cell12, two cells fell out of the usable range (coefficient 0.219, stderr 0.030, n = 39). While re-running with a tighter segmentation threshold for cell16, the coefficient tracked epoch count more closely than duration (coefficient 0.295, stderr 0.036, n = 41). While re-running with a tighter segmentation threshold for cell15, nothing in the figure changed at print size (coefficient 0.183, stderr 0.036, n = 55).

### Step 35: checking residual autocorrelation

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell22    0.114  0.013   0.089  0.139  46        2000
cell09    0.198  0.022   0.155  0.241  42        4000
cell24    0.256  0.042   0.174  0.338  57        4000
cell04    0.269  0.043   0.185  0.354  50        1000
cell07    0.230  0.042   0.147  0.313  44        1000
cell17    0.306  0.024   0.259  0.354  53        4000
cell10    0.128  0.039   0.051  0.205  46        4000
```

```python
coefs = fit_per_cell(rows, threshold=0.44)
lo, hi = ci(coefs, seed=65)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While comparing per-cell orderings for cell03, the estimate moved less than one standard error (coefficient 0.148, stderr 0.035, n = 51). While re-running with a tighter segmentation threshold for cell11, the CI narrowed by roughly a tenth (coefficient 0.173, stderr 0.021, n = 58). While comparing per-cell orderings for cell14, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.240, stderr 0.030, n = 58). While checking residual autocorrelation for cell07, the ordering of cells was preserved (coefficient 0.111, stderr 0.023, n = 39). While bootstrapping the CI for cell09, nothing in the figure changed at print size (coefficient 0.308, stderr 0.015, n = 52).

While re-running with a tighter segmentation threshold for cell13, two cells fell out of the usable range (coefficient 0.166, stderr 0.017, n = 39). While re-running with a tighter segmentation threshold for cell11, two cells fell out of the usable range (coefficient 0.268, stderr 0.036, n = 56). While fitting the one-lag kernel for cell23, the estimate moved less than one standard error (coefficient 0.113, stderr 0.046, n = 47). While re-exporting the raw traces for cell13, the ordering of cells was preserved (coefficient 0.283, stderr 0.042, n = 39).

### Step 36: segmenting epochs

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell03    0.152  0.041   0.072  0.231  58        4000
cell10    0.147  0.019   0.109  0.185  55        4000
cell03    0.162  0.018   0.127  0.196  52        1000
cell24    0.281  0.037   0.208  0.354  50        1000
cell20    0.246  0.033   0.181  0.311  54        4000
cell22    0.094  0.041   0.014  0.175  46        1000
cell09    0.212  0.015   0.183  0.241  38        2000
cell13    0.175  0.020   0.135  0.215  38        4000
cell02    0.179  0.032   0.117  0.241  38        2000
cell10    0.154  0.036   0.084  0.225  47        1000
```

While fitting the one-lag kernel for cell14, the coefficient tracked epoch count more closely than duration (coefficient 0.201, stderr 0.026, n = 50). While re-exporting the raw traces for cell17, two cells fell out of the usable range (coefficient 0.286, stderr 0.023, n = 52). While bootstrapping the CI for cell03, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.267, stderr 0.011, n = 49). While re-exporting the raw traces for cell09, the coefficient tracked epoch count more closely than duration (coefficient 0.309, stderr 0.022, n = 47). Worth noting for the writeup, though not a result on its own.

While segmenting epochs for cell07, the estimate moved less than one standard error (coefficient 0.142, stderr 0.046, n = 54). While segmenting epochs for cell16, nothing in the figure changed at print size (coefficient 0.305, stderr 0.018, n = 41). While checking residual autocorrelation for cell03, the coefficient tracked epoch count more closely than duration (coefficient 0.188, stderr 0.037, n = 40). While checking residual autocorrelation for cell24, the CI narrowed by roughly a tenth (coefficient 0.118, stderr 0.036, n = 50). While fitting the one-lag kernel for cell24, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.273, stderr 0.010, n = 42). While re-running with a tighter segmentation threshold for cell21, the ordering of cells was preserved (coefficient 0.226, stderr 0.045, n = 38).

While re-exporting the raw traces for cell05, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.111, stderr 0.025, n = 56). While re-exporting the raw traces for cell05, the estimate moved less than one standard error (coefficient 0.178, stderr 0.039, n = 57). While auditing the holding potential column for cell23, the coefficient tracked epoch count more closely than duration (coefficient 0.267, stderr 0.045, n = 40). While auditing the holding potential column for cell01, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.284, stderr 0.031, n = 58). While comparing per-cell orderings for cell19, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.176, stderr 0.025, n = 47).

### Step 37: auditing the holding potential column

```python
coefs = fit_per_cell(rows, threshold=0.30)
lo, hi = ci(coefs, seed=32)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While segmenting epochs for cell20, the CI narrowed by roughly a tenth (coefficient 0.098, stderr 0.016, n = 41). While segmenting epochs for cell01, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.172, stderr 0.022, n = 41). While re-running with a tighter segmentation threshold for cell19, the estimate moved less than one standard error (coefficient 0.187, stderr 0.035, n = 57). While auditing the holding potential column for cell03, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.306, stderr 0.041, n = 54). While segmenting epochs for cell07, two cells fell out of the usable range (coefficient 0.241, stderr 0.021, n = 58). Parking this until the re-segmentation lands.

While comparing per-cell orderings for cell03, two cells fell out of the usable range (coefficient 0.271, stderr 0.011, n = 41). While bootstrapping the CI for cell08, nothing in the figure changed at print size (coefficient 0.110, stderr 0.026, n = 45). While fitting the one-lag kernel for cell19, the coefficient tracked epoch count more closely than duration (coefficient 0.193, stderr 0.035, n = 56). While fitting the one-lag kernel for cell18, two cells fell out of the usable range (coefficient 0.251, stderr 0.027, n = 50).

### Step 38: checking residual autocorrelation

While re-running with a tighter segmentation threshold for cell04, the estimate moved less than one standard error (coefficient 0.131, stderr 0.036, n = 38). While re-running with a tighter segmentation threshold for cell14, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.088, stderr 0.016, n = 46). While re-running with a tighter segmentation threshold for cell15, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.197, stderr 0.024, n = 50). While comparing per-cell orderings for cell04, the ordering of cells was preserved (coefficient 0.120, stderr 0.039, n = 49). Noted and moved on; it does not change the decision.

While fitting the one-lag kernel for cell13, the estimate moved less than one standard error (coefficient 0.195, stderr 0.039, n = 52). While segmenting epochs for cell15, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.246, stderr 0.019, n = 57). While checking residual autocorrelation for cell23, the estimate moved less than one standard error (coefficient 0.294, stderr 0.022, n = 58). While segmenting epochs for cell05, the CI narrowed by roughly a tenth (coefficient 0.105, stderr 0.049, n = 41).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell21    0.305  0.010   0.285  0.325  41        2000
cell05    0.234  0.038   0.160  0.308  54        500
cell23    0.111  0.048   0.016  0.205  42        2000
cell24    0.123  0.032   0.060  0.186  39        2000
cell17    0.211  0.040   0.132  0.290  57        500
cell08    0.190  0.022   0.146  0.234  47        4000
cell07    0.303  0.015   0.273  0.333  54        2000
cell05    0.265  0.023   0.220  0.310  58        2000
cell02    0.206  0.020   0.166  0.245  47        1000
cell10    0.248  0.045   0.161  0.336  55        4000
cell05    0.132  0.014   0.104  0.159  49        500
cell19    0.186  0.017   0.151  0.220  47        1000
cell04    0.225  0.011   0.203  0.247  51        2000
cell15    0.278  0.014   0.250  0.306  57        4000
```

While auditing the holding potential column for cell19, two cells fell out of the usable range (coefficient 0.188, stderr 0.020, n = 50). While comparing per-cell orderings for cell20, the CI narrowed by roughly a tenth (coefficient 0.289, stderr 0.029, n = 40). While auditing the holding potential column for cell01, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.297, stderr 0.048, n = 49). While fitting the one-lag kernel for cell13, the CI narrowed by roughly a tenth (coefficient 0.178, stderr 0.022, n = 39). While auditing the holding potential column for cell24, the coefficient tracked epoch count more closely than duration (coefficient 0.154, stderr 0.018, n = 50). While comparing per-cell orderings for cell07, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.085, stderr 0.045, n = 58).

