# Prior session 17 of 20

Transcript of an earlier working session on the history-kernel analysis.

### Step 1: segmenting epochs

While segmenting epochs for cell05, the CI narrowed by roughly a tenth (coefficient 0.123, stderr 0.013, n = 48). While checking residual autocorrelation for cell14, the coefficient tracked epoch count more closely than duration (coefficient 0.114, stderr 0.039, n = 55). While segmenting epochs for cell05, the estimate moved less than one standard error (coefficient 0.215, stderr 0.042, n = 44). While auditing the holding potential column for cell01, the coefficient tracked epoch count more closely than duration (coefficient 0.212, stderr 0.048, n = 41). While re-exporting the raw traces for cell04, two cells fell out of the usable range (coefficient 0.089, stderr 0.019, n = 49). This is the part that will need a real statistical argument.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell19    0.255  0.018   0.219  0.292  47        4000
cell23    0.267  0.013   0.242  0.292  46        1000
cell24    0.260  0.049   0.164  0.355  49        2000
cell18    0.242  0.046   0.152  0.331  47        500
cell17    0.204  0.037   0.131  0.278  54        1000
cell07    0.247  0.018   0.212  0.282  40        2000
cell10    0.091  0.034   0.024  0.158  39        2000
cell06    0.089  0.016   0.058  0.120  42        500
cell16    0.273  0.010   0.253  0.292  39        1000
cell14    0.105  0.041   0.025  0.184  45        2000
cell05    0.101  0.033   0.036  0.167  53        500
cell23    0.271  0.028   0.216  0.327  49        4000
```

While segmenting epochs for cell05, the CI narrowed by roughly a tenth (coefficient 0.165, stderr 0.038, n = 46). While checking residual autocorrelation for cell08, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.112, stderr 0.012, n = 54). While re-exporting the raw traces for cell24, two cells fell out of the usable range (coefficient 0.093, stderr 0.014, n = 58). While fitting the one-lag kernel for cell23, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.302, stderr 0.044, n = 49). Worth noting for the writeup, though not a result on its own.

### Step 2: checking residual autocorrelation

While fitting the one-lag kernel for cell03, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.248, stderr 0.022, n = 56). While checking residual autocorrelation for cell21, two cells fell out of the usable range (coefficient 0.184, stderr 0.019, n = 51). While re-exporting the raw traces for cell06, the ordering of cells was preserved (coefficient 0.099, stderr 0.010, n = 58). While comparing per-cell orderings for cell15, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.300, stderr 0.021, n = 52). While re-exporting the raw traces for cell21, the estimate moved less than one standard error (coefficient 0.224, stderr 0.047, n = 38).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell06    0.234  0.011   0.213  0.256  41        1000
cell24    0.132  0.033   0.068  0.196  44        500
cell01    0.144  0.019   0.107  0.181  46        4000
cell07    0.286  0.041   0.207  0.366  53        2000
cell01    0.256  0.028   0.201  0.312  47        500
cell20    0.300  0.026   0.249  0.352  50        1000
cell09    0.276  0.016   0.246  0.307  48        4000
cell05    0.188  0.036   0.118  0.259  57        4000
cell23    0.104  0.027   0.050  0.157  52        2000
cell10    0.095  0.015   0.066  0.124  54        500
cell11    0.200  0.026   0.149  0.251  54        2000
cell22    0.249  0.049   0.152  0.346  42        1000
cell23    0.138  0.014   0.112  0.165  39        2000
```

While comparing per-cell orderings for cell16, the CI narrowed by roughly a tenth (coefficient 0.258, stderr 0.039, n = 47). While comparing per-cell orderings for cell08, two cells fell out of the usable range (coefficient 0.138, stderr 0.030, n = 55). While auditing the holding potential column for cell09, two cells fell out of the usable range (coefficient 0.293, stderr 0.019, n = 39). While bootstrapping the CI for cell16, the ordering of cells was preserved (coefficient 0.153, stderr 0.020, n = 53). While fitting the one-lag kernel for cell17, the CI narrowed by roughly a tenth (coefficient 0.214, stderr 0.014, n = 56).

### Step 3: comparing per-cell orderings

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell14    0.164  0.032   0.100  0.227  47        4000
cell15    0.095  0.024   0.048  0.141  42        500
cell23    0.141  0.013   0.115  0.167  42        2000
cell24    0.300  0.047   0.209  0.392  49        4000
cell05    0.146  0.046   0.056  0.236  45        500
cell24    0.309  0.010   0.288  0.329  41        4000
cell17    0.281  0.041   0.200  0.361  46        2000
cell02    0.112  0.018   0.076  0.149  39        1000
cell24    0.247  0.034   0.181  0.313  51        1000
cell14    0.282  0.045   0.194  0.371  50        2000
cell12    0.293  0.017   0.260  0.327  39        500
cell11    0.256  0.018   0.221  0.291  49        2000
```

While fitting the one-lag kernel for cell01, two cells fell out of the usable range (coefficient 0.298, stderr 0.033, n = 44). While re-exporting the raw traces for cell18, the coefficient tracked epoch count more closely than duration (coefficient 0.264, stderr 0.015, n = 53). While segmenting epochs for cell16, two cells fell out of the usable range (coefficient 0.184, stderr 0.032, n = 47). While fitting the one-lag kernel for cell12, the estimate moved less than one standard error (coefficient 0.124, stderr 0.036, n = 53). Noted and moved on; it does not change the decision.

### Step 4: comparing per-cell orderings

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell22    0.291  0.019   0.254  0.328  39        500
cell24    0.164  0.034   0.098  0.230  42        2000
cell01    0.237  0.029   0.180  0.293  43        1000
cell10    0.285  0.036   0.214  0.357  42        1000
cell01    0.240  0.041   0.160  0.321  53        500
cell07    0.098  0.043   0.013  0.183  43        2000
cell24    0.302  0.044   0.216  0.388  40        2000
cell08    0.154  0.036   0.084  0.225  49        4000
```

While re-exporting the raw traces for cell16, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.196, stderr 0.011, n = 40). While re-exporting the raw traces for cell07, two cells fell out of the usable range (coefficient 0.182, stderr 0.030, n = 45). While re-exporting the raw traces for cell14, the CI narrowed by roughly a tenth (coefficient 0.281, stderr 0.033, n = 38). While fitting the one-lag kernel for cell22, the ordering of cells was preserved (coefficient 0.240, stderr 0.046, n = 51). While checking residual autocorrelation for cell15, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.086, stderr 0.047, n = 40).

```python
coefs = fit_per_cell(rows, threshold=0.44)
lo, hi = ci(coefs, seed=46)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While fitting the one-lag kernel for cell13, the CI narrowed by roughly a tenth (coefficient 0.257, stderr 0.032, n = 52). While fitting the one-lag kernel for cell14, nothing in the figure changed at print size (coefficient 0.196, stderr 0.025, n = 44). While comparing per-cell orderings for cell24, nothing in the figure changed at print size (coefficient 0.210, stderr 0.025, n = 53). While segmenting epochs for cell24, nothing in the figure changed at print size (coefficient 0.197, stderr 0.049, n = 52). While fitting the one-lag kernel for cell24, two cells fell out of the usable range (coefficient 0.297, stderr 0.032, n = 45).

### Step 5: bootstrapping the CI

While checking residual autocorrelation for cell13, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.234, stderr 0.031, n = 54). While fitting the one-lag kernel for cell01, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.122, stderr 0.025, n = 55). While re-exporting the raw traces for cell06, the coefficient tracked epoch count more closely than duration (coefficient 0.144, stderr 0.049, n = 57).

While comparing per-cell orderings for cell15, nothing in the figure changed at print size (coefficient 0.140, stderr 0.028, n = 53). While re-exporting the raw traces for cell16, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.152, stderr 0.029, n = 48). While segmenting epochs for cell23, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.166, stderr 0.012, n = 51).

While re-running with a tighter segmentation threshold for cell03, the coefficient tracked epoch count more closely than duration (coefficient 0.292, stderr 0.043, n = 40). While re-exporting the raw traces for cell15, the estimate moved less than one standard error (coefficient 0.116, stderr 0.020, n = 48). While fitting the one-lag kernel for cell23, the ordering of cells was preserved (coefficient 0.292, stderr 0.047, n = 38). While re-running with a tighter segmentation threshold for cell07, two cells fell out of the usable range (coefficient 0.307, stderr 0.025, n = 55).

While bootstrapping the CI for cell14, nothing in the figure changed at print size (coefficient 0.124, stderr 0.035, n = 53). While bootstrapping the CI for cell02, the CI narrowed by roughly a tenth (coefficient 0.224, stderr 0.018, n = 50). While re-running with a tighter segmentation threshold for cell03, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.168, stderr 0.026, n = 56). While bootstrapping the CI for cell21, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.277, stderr 0.049, n = 46). While checking residual autocorrelation for cell11, the estimate moved less than one standard error (coefficient 0.156, stderr 0.014, n = 43). While segmenting epochs for cell21, the CI narrowed by roughly a tenth (coefficient 0.279, stderr 0.014, n = 57). Worth noting for the writeup, though not a result on its own.

### Step 6: re-running with a tighter segmentation threshold

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell12    0.278  0.036   0.207  0.348  38        4000
cell24    0.189  0.045   0.100  0.277  51        2000
cell20    0.298  0.038   0.223  0.373  48        4000
cell05    0.253  0.030   0.195  0.311  40        2000
cell17    0.259  0.045   0.171  0.348  38        2000
cell07    0.300  0.015   0.271  0.329  53        500
cell02    0.114  0.026   0.062  0.166  48        500
cell09    0.094  0.027   0.041  0.147  54        4000
cell04    0.173  0.031   0.112  0.233  56        500
cell23    0.159  0.028   0.105  0.214  49        4000
```

```python
coefs = fit_per_cell(rows, threshold=0.59)
lo, hi = ci(coefs, seed=81)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While auditing the holding potential column for cell22, the coefficient tracked epoch count more closely than duration (coefficient 0.081, stderr 0.028, n = 45). While bootstrapping the CI for cell21, the CI narrowed by roughly a tenth (coefficient 0.178, stderr 0.048, n = 56). While re-running with a tighter segmentation threshold for cell04, nothing in the figure changed at print size (coefficient 0.096, stderr 0.028, n = 53). While checking residual autocorrelation for cell04, the ordering of cells was preserved (coefficient 0.271, stderr 0.016, n = 49).

### Step 7: bootstrapping the CI

While comparing per-cell orderings for cell14, two cells fell out of the usable range (coefficient 0.276, stderr 0.024, n = 39). While comparing per-cell orderings for cell03, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.232, stderr 0.042, n = 55). While segmenting epochs for cell17, two cells fell out of the usable range (coefficient 0.223, stderr 0.020, n = 49). While auditing the holding potential column for cell18, the ordering of cells was preserved (coefficient 0.265, stderr 0.041, n = 53). This is the part that will need a real statistical argument.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell20    0.240  0.013   0.214  0.266  57        4000
cell12    0.172  0.045   0.084  0.260  51        1000
cell12    0.251  0.041   0.172  0.331  52        1000
cell16    0.089  0.041   0.007  0.170  40        4000
cell17    0.137  0.015   0.107  0.167  48        2000
cell24    0.230  0.016   0.198  0.261  39        2000
cell13    0.130  0.029   0.074  0.186  53        1000
cell21    0.099  0.011   0.079  0.120  41        4000
cell08    0.091  0.027   0.038  0.144  42        4000
cell11    0.106  0.021   0.066  0.146  54        500
```

While checking residual autocorrelation for cell08, the coefficient tracked epoch count more closely than duration (coefficient 0.206, stderr 0.044, n = 56). While re-running with a tighter segmentation threshold for cell24, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.169, stderr 0.038, n = 55). While checking residual autocorrelation for cell07, the coefficient tracked epoch count more closely than duration (coefficient 0.212, stderr 0.012, n = 44). While checking residual autocorrelation for cell06, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.161, stderr 0.037, n = 53). While fitting the one-lag kernel for cell16, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.301, stderr 0.025, n = 49).

While re-running with a tighter segmentation threshold for cell08, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.300, stderr 0.026, n = 39). While comparing per-cell orderings for cell07, the estimate moved less than one standard error (coefficient 0.204, stderr 0.035, n = 43). While checking residual autocorrelation for cell21, the estimate moved less than one standard error (coefficient 0.136, stderr 0.050, n = 46). This is the part that will need a real statistical argument.

### Step 8: auditing the holding potential column

While fitting the one-lag kernel for cell15, nothing in the figure changed at print size (coefficient 0.125, stderr 0.033, n = 58). While checking residual autocorrelation for cell14, the coefficient tracked epoch count more closely than duration (coefficient 0.161, stderr 0.048, n = 50). While comparing per-cell orderings for cell19, the ordering of cells was preserved (coefficient 0.160, stderr 0.046, n = 49). While checking residual autocorrelation for cell10, nothing in the figure changed at print size (coefficient 0.144, stderr 0.017, n = 54). While re-running with a tighter segmentation threshold for cell10, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.228, stderr 0.049, n = 49).

While checking residual autocorrelation for cell06, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.117, stderr 0.046, n = 49). While comparing per-cell orderings for cell19, nothing in the figure changed at print size (coefficient 0.288, stderr 0.018, n = 58). While segmenting epochs for cell17, the coefficient tracked epoch count more closely than duration (coefficient 0.126, stderr 0.045, n = 41). While comparing per-cell orderings for cell05, the CI narrowed by roughly a tenth (coefficient 0.276, stderr 0.031, n = 56). While re-running with a tighter segmentation threshold for cell08, two cells fell out of the usable range (coefficient 0.285, stderr 0.033, n = 54). Worth noting for the writeup, though not a result on its own.

### Step 9: checking residual autocorrelation

While bootstrapping the CI for cell15, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.279, stderr 0.043, n = 46). While re-running with a tighter segmentation threshold for cell08, the coefficient tracked epoch count more closely than duration (coefficient 0.184, stderr 0.041, n = 41). While comparing per-cell orderings for cell22, two cells fell out of the usable range (coefficient 0.107, stderr 0.042, n = 55). While re-running with a tighter segmentation threshold for cell22, two cells fell out of the usable range (coefficient 0.280, stderr 0.011, n = 54). While segmenting epochs for cell01, nothing in the figure changed at print size (coefficient 0.229, stderr 0.027, n = 40).

While segmenting epochs for cell02, the coefficient tracked epoch count more closely than duration (coefficient 0.151, stderr 0.040, n = 53). While bootstrapping the CI for cell23, nothing in the figure changed at print size (coefficient 0.263, stderr 0.034, n = 50). While bootstrapping the CI for cell16, two cells fell out of the usable range (coefficient 0.248, stderr 0.046, n = 42). While segmenting epochs for cell17, the coefficient tracked epoch count more closely than duration (coefficient 0.124, stderr 0.014, n = 41). This is the part that will need a real statistical argument.

While auditing the holding potential column for cell09, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.173, stderr 0.021, n = 52). While comparing per-cell orderings for cell16, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.125, stderr 0.011, n = 41). While bootstrapping the CI for cell19, the ordering of cells was preserved (coefficient 0.085, stderr 0.027, n = 54). While comparing per-cell orderings for cell19, the ordering of cells was preserved (coefficient 0.096, stderr 0.022, n = 49). While re-running with a tighter segmentation threshold for cell07, the estimate moved less than one standard error (coefficient 0.215, stderr 0.024, n = 40). While fitting the one-lag kernel for cell24, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.233, stderr 0.042, n = 51).

While bootstrapping the CI for cell13, the estimate moved less than one standard error (coefficient 0.214, stderr 0.038, n = 46). While comparing per-cell orderings for cell22, the ordering of cells was preserved (coefficient 0.208, stderr 0.034, n = 51). While re-exporting the raw traces for cell15, the ordering of cells was preserved (coefficient 0.176, stderr 0.024, n = 58). While checking residual autocorrelation for cell10, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.097, stderr 0.031, n = 40). While comparing per-cell orderings for cell15, the coefficient tracked epoch count more closely than duration (coefficient 0.300, stderr 0.021, n = 45). While comparing per-cell orderings for cell06, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.304, stderr 0.041, n = 38). This is the part that will need a real statistical argument.

### Step 10: re-exporting the raw traces

While checking residual autocorrelation for cell03, the coefficient tracked epoch count more closely than duration (coefficient 0.268, stderr 0.021, n = 42). While re-exporting the raw traces for cell24, nothing in the figure changed at print size (coefficient 0.162, stderr 0.017, n = 58). While checking residual autocorrelation for cell10, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.264, stderr 0.039, n = 40). This is the part that will need a real statistical argument.

```python
coefs = fit_per_cell(rows, threshold=0.69)
lo, hi = ci(coefs, seed=84)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell02    0.227  0.019   0.190  0.264  54        4000
cell14    0.232  0.040   0.154  0.311  46        4000
cell16    0.301  0.016   0.269  0.333  41        500
cell10    0.130  0.034   0.064  0.196  41        4000
cell20    0.112  0.021   0.072  0.153  38        2000
cell21    0.094  0.032   0.032  0.157  39        2000
cell18    0.223  0.016   0.193  0.254  51        2000
cell03    0.129  0.025   0.079  0.178  39        2000
cell23    0.146  0.030   0.087  0.205  42        2000
cell06    0.155  0.033   0.091  0.219  58        4000
cell06    0.131  0.015   0.101  0.161  49        2000
```

### Step 11: fitting the one-lag kernel

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell20    0.171  0.012   0.148  0.194  53        2000
cell14    0.100  0.022   0.057  0.143  46        4000
cell09    0.082  0.029   0.025  0.139  45        4000
cell04    0.232  0.046   0.142  0.323  44        4000
cell05    0.258  0.010   0.237  0.278  55        500
cell09    0.229  0.048   0.135  0.322  42        2000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell24    0.142  0.022   0.099  0.186  52        1000
cell05    0.263  0.013   0.238  0.288  50        2000
cell15    0.190  0.041   0.110  0.271  53        2000
cell20    0.117  0.025   0.068  0.165  44        2000
cell06    0.148  0.043   0.064  0.232  43        4000
cell01    0.230  0.033   0.165  0.295  57        500
cell19    0.174  0.012   0.150  0.198  55        500
cell10    0.159  0.041   0.079  0.239  48        2000
```

```python
coefs = fit_per_cell(rows, threshold=0.53)
lo, hi = ci(coefs, seed=28)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 12: auditing the holding potential column

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell16    0.127  0.011   0.107  0.148  56        500
cell07    0.228  0.039   0.152  0.304  52        4000
cell01    0.190  0.018   0.154  0.226  44        4000
cell24    0.274  0.012   0.251  0.298  56        1000
cell07    0.163  0.011   0.141  0.184  41        4000
cell04    0.216  0.015   0.186  0.247  42        500
cell19    0.180  0.031   0.119  0.241  57        2000
cell14    0.215  0.025   0.166  0.264  57        4000
cell11    0.237  0.035   0.169  0.305  39        1000
cell14    0.296  0.041   0.216  0.376  58        2000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell18    0.161  0.036   0.090  0.232  53        1000
cell02    0.102  0.044   0.015  0.188  50        1000
cell17    0.276  0.021   0.235  0.317  48        2000
cell13    0.225  0.031   0.163  0.286  51        500
cell06    0.096  0.027   0.044  0.148  45        1000
cell21    0.286  0.015   0.256  0.316  41        500
cell16    0.233  0.036   0.162  0.304  39        2000
cell09    0.263  0.026   0.212  0.315  53        1000
cell16    0.170  0.030   0.112  0.229  49        2000
cell13    0.170  0.040   0.091  0.249  54        1000
cell13    0.137  0.020   0.098  0.175  53        1000
cell23    0.162  0.014   0.135  0.189  44        2000
```

While checking residual autocorrelation for cell24, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.130, stderr 0.034, n = 48). While re-running with a tighter segmentation threshold for cell05, the estimate moved less than one standard error (coefficient 0.207, stderr 0.015, n = 58). While segmenting epochs for cell24, nothing in the figure changed at print size (coefficient 0.089, stderr 0.036, n = 53). While fitting the one-lag kernel for cell02, the estimate moved less than one standard error (coefficient 0.283, stderr 0.039, n = 55). While bootstrapping the CI for cell10, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.235, stderr 0.031, n = 41).

### Step 13: re-exporting the raw traces

While fitting the one-lag kernel for cell18, two cells fell out of the usable range (coefficient 0.167, stderr 0.035, n = 51). While segmenting epochs for cell21, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.108, stderr 0.011, n = 54). While auditing the holding potential column for cell18, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.172, stderr 0.049, n = 47). While bootstrapping the CI for cell11, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.166, stderr 0.026, n = 38).

While segmenting epochs for cell09, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.231, stderr 0.019, n = 38). While re-running with a tighter segmentation threshold for cell11, two cells fell out of the usable range (coefficient 0.310, stderr 0.036, n = 50). While checking residual autocorrelation for cell12, the coefficient tracked epoch count more closely than duration (coefficient 0.247, stderr 0.027, n = 46).

### Step 14: re-running with a tighter segmentation threshold

```python
coefs = fit_per_cell(rows, threshold=0.71)
lo, hi = ci(coefs, seed=49)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```python
coefs = fit_per_cell(rows, threshold=0.42)
lo, hi = ci(coefs, seed=79)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 15: checking residual autocorrelation

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell09    0.153  0.020   0.113  0.193  50        2000
cell11    0.204  0.017   0.171  0.237  45        2000
cell15    0.262  0.041   0.182  0.342  51        500
cell03    0.183  0.035   0.115  0.251  55        1000
cell01    0.083  0.044   -0.003  0.168  54        1000
cell03    0.267  0.013   0.242  0.292  51        500
cell12    0.179  0.039   0.102  0.256  45        1000
cell14    0.174  0.027   0.122  0.227  53        500
cell07    0.282  0.029   0.225  0.340  47        1000
cell08    0.229  0.040   0.150  0.308  51        4000
cell21    0.184  0.037   0.112  0.255  54        4000
cell16    0.083  0.021   0.042  0.124  54        1000
```

While bootstrapping the CI for cell10, the estimate moved less than one standard error (coefficient 0.111, stderr 0.037, n = 50). While re-exporting the raw traces for cell17, two cells fell out of the usable range (coefficient 0.277, stderr 0.022, n = 45). While re-exporting the raw traces for cell19, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.087, stderr 0.030, n = 48). While re-running with a tighter segmentation threshold for cell23, the ordering of cells was preserved (coefficient 0.284, stderr 0.046, n = 53). While auditing the holding potential column for cell24, two cells fell out of the usable range (coefficient 0.173, stderr 0.016, n = 57). Flagging it so it does not get rediscovered next week.

While re-running with a tighter segmentation threshold for cell22, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.148, stderr 0.036, n = 53). While bootstrapping the CI for cell16, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.200, stderr 0.042, n = 55). While re-exporting the raw traces for cell08, the estimate moved less than one standard error (coefficient 0.175, stderr 0.016, n = 44). While checking residual autocorrelation for cell24, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.273, stderr 0.027, n = 54). While re-exporting the raw traces for cell13, the coefficient tracked epoch count more closely than duration (coefficient 0.183, stderr 0.026, n = 58). While auditing the holding potential column for cell13, the estimate moved less than one standard error (coefficient 0.305, stderr 0.036, n = 46). Parking this until the re-segmentation lands.

While segmenting epochs for cell01, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.117, stderr 0.014, n = 54). While segmenting epochs for cell01, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.299, stderr 0.016, n = 46). While re-running with a tighter segmentation threshold for cell01, the ordering of cells was preserved (coefficient 0.230, stderr 0.012, n = 57). While bootstrapping the CI for cell23, nothing in the figure changed at print size (coefficient 0.233, stderr 0.030, n = 45). While auditing the holding potential column for cell20, the estimate moved less than one standard error (coefficient 0.215, stderr 0.038, n = 46). Parking this until the re-segmentation lands.

### Step 16: fitting the one-lag kernel

While fitting the one-lag kernel for cell22, the coefficient tracked epoch count more closely than duration (coefficient 0.126, stderr 0.013, n = 39). While re-running with a tighter segmentation threshold for cell14, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.105, stderr 0.024, n = 41). While auditing the holding potential column for cell14, the ordering of cells was preserved (coefficient 0.147, stderr 0.023, n = 52).

While segmenting epochs for cell06, the CI narrowed by roughly a tenth (coefficient 0.173, stderr 0.026, n = 55). While re-exporting the raw traces for cell06, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.144, stderr 0.028, n = 40). While bootstrapping the CI for cell05, the ordering of cells was preserved (coefficient 0.141, stderr 0.017, n = 58). While checking residual autocorrelation for cell07, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.223, stderr 0.033, n = 51). While re-running with a tighter segmentation threshold for cell18, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.290, stderr 0.049, n = 48). While auditing the holding potential column for cell11, the estimate moved less than one standard error (coefficient 0.137, stderr 0.016, n = 55). Worth noting for the writeup, though not a result on its own.

```python
coefs = fit_per_cell(rows, threshold=0.54)
lo, hi = ci(coefs, seed=37)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While checking residual autocorrelation for cell21, two cells fell out of the usable range (coefficient 0.150, stderr 0.014, n = 40). While checking residual autocorrelation for cell08, the estimate moved less than one standard error (coefficient 0.304, stderr 0.027, n = 42). While checking residual autocorrelation for cell02, the coefficient tracked epoch count more closely than duration (coefficient 0.137, stderr 0.018, n = 40). While re-exporting the raw traces for cell11, nothing in the figure changed at print size (coefficient 0.113, stderr 0.014, n = 47). Parking this until the re-segmentation lands.

### Step 17: fitting the one-lag kernel

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell24    0.146  0.034   0.079  0.214  49        4000
cell01    0.092  0.019   0.054  0.130  40        500
cell11    0.092  0.034   0.026  0.158  51        500
cell14    0.092  0.020   0.052  0.132  46        2000
cell04    0.108  0.024   0.062  0.154  51        1000
cell09    0.243  0.019   0.206  0.280  40        2000
cell06    0.222  0.041   0.141  0.302  57        1000
```

While comparing per-cell orderings for cell19, the ordering of cells was preserved (coefficient 0.295, stderr 0.043, n = 43). While checking residual autocorrelation for cell05, the estimate moved less than one standard error (coefficient 0.147, stderr 0.049, n = 53). While checking residual autocorrelation for cell18, the CI narrowed by roughly a tenth (coefficient 0.270, stderr 0.029, n = 42). While fitting the one-lag kernel for cell21, nothing in the figure changed at print size (coefficient 0.093, stderr 0.015, n = 49). While re-running with a tighter segmentation threshold for cell16, nothing in the figure changed at print size (coefficient 0.193, stderr 0.040, n = 57). While re-running with a tighter segmentation threshold for cell10, the CI narrowed by roughly a tenth (coefficient 0.218, stderr 0.040, n = 50). Noted and moved on; it does not change the decision.

### Step 18: re-exporting the raw traces

While re-exporting the raw traces for cell16, two cells fell out of the usable range (coefficient 0.085, stderr 0.035, n = 45). While checking residual autocorrelation for cell01, nothing in the figure changed at print size (coefficient 0.289, stderr 0.044, n = 45). While comparing per-cell orderings for cell12, two cells fell out of the usable range (coefficient 0.274, stderr 0.012, n = 55). While comparing per-cell orderings for cell12, the estimate moved less than one standard error (coefficient 0.291, stderr 0.033, n = 38).

While auditing the holding potential column for cell10, two cells fell out of the usable range (coefficient 0.160, stderr 0.022, n = 38). While segmenting epochs for cell22, the CI narrowed by roughly a tenth (coefficient 0.109, stderr 0.040, n = 39). While re-running with a tighter segmentation threshold for cell02, the ordering of cells was preserved (coefficient 0.179, stderr 0.027, n = 41). This is the part that will need a real statistical argument.

While bootstrapping the CI for cell21, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.141, stderr 0.013, n = 39). While bootstrapping the CI for cell02, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.285, stderr 0.033, n = 54). While segmenting epochs for cell10, two cells fell out of the usable range (coefficient 0.262, stderr 0.028, n = 39). While checking residual autocorrelation for cell11, the ordering of cells was preserved (coefficient 0.270, stderr 0.045, n = 46). While re-exporting the raw traces for cell06, nothing in the figure changed at print size (coefficient 0.096, stderr 0.013, n = 48). This is the part that will need a real statistical argument.

While segmenting epochs for cell11, two cells fell out of the usable range (coefficient 0.268, stderr 0.035, n = 50). While bootstrapping the CI for cell16, the CI narrowed by roughly a tenth (coefficient 0.242, stderr 0.029, n = 43). While segmenting epochs for cell07, the estimate moved less than one standard error (coefficient 0.201, stderr 0.011, n = 48). While comparing per-cell orderings for cell11, the coefficient tracked epoch count more closely than duration (coefficient 0.120, stderr 0.047, n = 38). While re-exporting the raw traces for cell24, the ordering of cells was preserved (coefficient 0.171, stderr 0.020, n = 54). While auditing the holding potential column for cell23, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.254, stderr 0.017, n = 38).

### Step 19: bootstrapping the CI

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell08    0.239  0.039   0.163  0.315  38        4000
cell09    0.083  0.022   0.039  0.127  41        2000
cell22    0.300  0.042   0.219  0.382  49        1000
cell20    0.188  0.026   0.136  0.239  47        4000
cell21    0.082  0.016   0.051  0.114  39        4000
cell01    0.192  0.039   0.116  0.268  42        2000
cell23    0.246  0.016   0.214  0.277  54        500
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell08    0.106  0.042   0.023  0.189  56        4000
cell23    0.210  0.044   0.124  0.296  41        500
cell24    0.244  0.044   0.159  0.330  57        4000
cell16    0.211  0.026   0.160  0.261  57        4000
cell22    0.205  0.019   0.167  0.242  42        2000
cell05    0.124  0.031   0.063  0.185  49        1000
cell11    0.156  0.015   0.127  0.185  38        4000
cell21    0.285  0.045   0.198  0.372  39        4000
cell01    0.170  0.010   0.150  0.191  50        2000
cell22    0.135  0.020   0.095  0.175  52        4000
cell12    0.274  0.036   0.203  0.344  56        500
cell15    0.132  0.031   0.072  0.193  44        4000
cell03    0.290  0.032   0.228  0.352  52        2000
cell01    0.190  0.022   0.147  0.232  42        4000
```

While re-running with a tighter segmentation threshold for cell23, the coefficient tracked epoch count more closely than duration (coefficient 0.209, stderr 0.037, n = 50). While re-running with a tighter segmentation threshold for cell11, the coefficient tracked epoch count more closely than duration (coefficient 0.094, stderr 0.031, n = 58). While bootstrapping the CI for cell15, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.266, stderr 0.029, n = 51).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell06    0.249  0.049   0.152  0.345  45        1000
cell10    0.138  0.042   0.055  0.222  40        1000
cell21    0.298  0.026   0.247  0.349  56        500
cell11    0.223  0.050   0.126  0.321  58        500
cell09    0.173  0.028   0.118  0.227  42        1000
cell08    0.199  0.050   0.101  0.296  40        4000
cell13    0.124  0.030   0.065  0.183  44        4000
cell23    0.164  0.047   0.072  0.256  55        2000
cell16    0.144  0.013   0.118  0.170  56        1000
cell20    0.304  0.049   0.209  0.400  53        2000
cell08    0.128  0.048   0.034  0.222  52        4000
```

### Step 20: re-exporting the raw traces

While comparing per-cell orderings for cell01, the CI narrowed by roughly a tenth (coefficient 0.181, stderr 0.011, n = 58). While auditing the holding potential column for cell11, the CI narrowed by roughly a tenth (coefficient 0.169, stderr 0.030, n = 56). While auditing the holding potential column for cell11, the ordering of cells was preserved (coefficient 0.209, stderr 0.012, n = 58).

While re-running with a tighter segmentation threshold for cell11, the estimate moved less than one standard error (coefficient 0.305, stderr 0.018, n = 55). While fitting the one-lag kernel for cell13, two cells fell out of the usable range (coefficient 0.161, stderr 0.037, n = 53). While checking residual autocorrelation for cell12, nothing in the figure changed at print size (coefficient 0.233, stderr 0.028, n = 46). While segmenting epochs for cell09, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.133, stderr 0.014, n = 50).

While fitting the one-lag kernel for cell01, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.169, stderr 0.012, n = 46). While auditing the holding potential column for cell08, two cells fell out of the usable range (coefficient 0.152, stderr 0.042, n = 52). While segmenting epochs for cell13, the estimate moved less than one standard error (coefficient 0.310, stderr 0.022, n = 44). While auditing the holding potential column for cell19, the CI narrowed by roughly a tenth (coefficient 0.129, stderr 0.034, n = 56). This is the part that will need a real statistical argument.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell17    0.196  0.037   0.124  0.268  38        2000
cell09    0.232  0.017   0.199  0.265  39        500
cell16    0.144  0.018   0.108  0.180  51        1000
cell23    0.143  0.032   0.080  0.206  53        2000
cell01    0.150  0.039   0.073  0.227  39        2000
cell04    0.137  0.031   0.076  0.199  48        1000
cell24    0.169  0.028   0.113  0.224  53        4000
```

### Step 21: re-running with a tighter segmentation threshold

While checking residual autocorrelation for cell16, nothing in the figure changed at print size (coefficient 0.234, stderr 0.027, n = 46). While comparing per-cell orderings for cell06, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.114, stderr 0.029, n = 55). While auditing the holding potential column for cell05, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.241, stderr 0.015, n = 56). While fitting the one-lag kernel for cell17, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.179, stderr 0.014, n = 55). While fitting the one-lag kernel for cell02, the coefficient tracked epoch count more closely than duration (coefficient 0.080, stderr 0.042, n = 44).

While re-exporting the raw traces for cell14, the CI narrowed by roughly a tenth (coefficient 0.268, stderr 0.046, n = 58). While checking residual autocorrelation for cell05, the coefficient tracked epoch count more closely than duration (coefficient 0.215, stderr 0.027, n = 51). While bootstrapping the CI for cell03, the estimate moved less than one standard error (coefficient 0.103, stderr 0.013, n = 52). Parking this until the re-segmentation lands.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell11    0.133  0.018   0.098  0.169  43        4000
cell20    0.154  0.012   0.130  0.178  39        1000
cell21    0.241  0.010   0.221  0.261  58        1000
cell04    0.279  0.029   0.223  0.335  40        4000
cell11    0.237  0.049   0.140  0.333  49        500
cell09    0.093  0.043   0.010  0.177  53        500
cell16    0.169  0.050   0.071  0.266  38        1000
cell08    0.138  0.012   0.114  0.162  40        500
cell09    0.191  0.019   0.155  0.228  41        1000
cell19    0.194  0.040   0.116  0.271  49        2000
cell11    0.238  0.042   0.155  0.321  52        2000
cell21    0.117  0.029   0.061  0.173  54        4000
```

While comparing per-cell orderings for cell16, nothing in the figure changed at print size (coefficient 0.134, stderr 0.012, n = 52). While fitting the one-lag kernel for cell21, nothing in the figure changed at print size (coefficient 0.287, stderr 0.039, n = 55). While auditing the holding potential column for cell12, the coefficient tracked epoch count more closely than duration (coefficient 0.246, stderr 0.017, n = 54). While segmenting epochs for cell02, two cells fell out of the usable range (coefficient 0.123, stderr 0.024, n = 51).

### Step 22: fitting the one-lag kernel

While re-running with a tighter segmentation threshold for cell24, the estimate moved less than one standard error (coefficient 0.224, stderr 0.039, n = 52). While re-running with a tighter segmentation threshold for cell03, the coefficient tracked epoch count more closely than duration (coefficient 0.113, stderr 0.024, n = 38). While fitting the one-lag kernel for cell23, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.238, stderr 0.036, n = 49). While bootstrapping the CI for cell15, the coefficient tracked epoch count more closely than duration (coefficient 0.276, stderr 0.014, n = 50).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell04    0.285  0.022   0.241  0.329  45        1000
cell02    0.250  0.039   0.173  0.327  44        2000
cell17    0.284  0.039   0.209  0.360  54        4000
cell04    0.212  0.017   0.178  0.246  52        2000
cell11    0.227  0.012   0.203  0.251  54        2000
cell10    0.238  0.030   0.180  0.296  56        1000
cell05    0.168  0.015   0.137  0.198  52        2000
cell16    0.160  0.023   0.116  0.205  58        2000
cell16    0.111  0.037   0.039  0.182  44        4000
cell21    0.254  0.017   0.221  0.286  41        2000
```

While checking residual autocorrelation for cell13, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.127, stderr 0.047, n = 54). While segmenting epochs for cell23, nothing in the figure changed at print size (coefficient 0.307, stderr 0.021, n = 43). While checking residual autocorrelation for cell22, the ordering of cells was preserved (coefficient 0.306, stderr 0.021, n = 38). While re-running with a tighter segmentation threshold for cell08, the estimate moved less than one standard error (coefficient 0.254, stderr 0.048, n = 47).

### Step 23: bootstrapping the CI

While re-exporting the raw traces for cell22, the estimate moved less than one standard error (coefficient 0.247, stderr 0.037, n = 43). While bootstrapping the CI for cell02, the coefficient tracked epoch count more closely than duration (coefficient 0.238, stderr 0.023, n = 44). While comparing per-cell orderings for cell19, the CI narrowed by roughly a tenth (coefficient 0.159, stderr 0.030, n = 58). While bootstrapping the CI for cell23, the coefficient tracked epoch count more closely than duration (coefficient 0.166, stderr 0.017, n = 49). Parking this until the re-segmentation lands.

While re-running with a tighter segmentation threshold for cell08, nothing in the figure changed at print size (coefficient 0.210, stderr 0.026, n = 40). While segmenting epochs for cell08, the coefficient tracked epoch count more closely than duration (coefficient 0.118, stderr 0.043, n = 58). While auditing the holding potential column for cell18, the ordering of cells was preserved (coefficient 0.257, stderr 0.026, n = 53). While re-running with a tighter segmentation threshold for cell05, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.156, stderr 0.038, n = 47). Worth noting for the writeup, though not a result on its own.

While comparing per-cell orderings for cell16, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.123, stderr 0.027, n = 38). While comparing per-cell orderings for cell05, nothing in the figure changed at print size (coefficient 0.141, stderr 0.049, n = 38). While comparing per-cell orderings for cell24, the coefficient tracked epoch count more closely than duration (coefficient 0.277, stderr 0.031, n = 39). While bootstrapping the CI for cell24, the estimate moved less than one standard error (coefficient 0.308, stderr 0.023, n = 46). While bootstrapping the CI for cell05, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.121, stderr 0.041, n = 47). Flagging it so it does not get rediscovered next week.

### Step 24: segmenting epochs

While checking residual autocorrelation for cell21, the estimate moved less than one standard error (coefficient 0.199, stderr 0.038, n = 46). While bootstrapping the CI for cell23, the estimate moved less than one standard error (coefficient 0.219, stderr 0.044, n = 53). While comparing per-cell orderings for cell18, the CI narrowed by roughly a tenth (coefficient 0.212, stderr 0.031, n = 46). While re-exporting the raw traces for cell11, the coefficient tracked epoch count more closely than duration (coefficient 0.145, stderr 0.025, n = 41). While re-running with a tighter segmentation threshold for cell04, the coefficient tracked epoch count more closely than duration (coefficient 0.212, stderr 0.039, n = 42). While checking residual autocorrelation for cell07, the coefficient tracked epoch count more closely than duration (coefficient 0.147, stderr 0.020, n = 56).

While segmenting epochs for cell19, the CI narrowed by roughly a tenth (coefficient 0.163, stderr 0.042, n = 53). While segmenting epochs for cell21, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.235, stderr 0.046, n = 45). While re-running with a tighter segmentation threshold for cell03, the estimate moved less than one standard error (coefficient 0.115, stderr 0.028, n = 43). Worth noting for the writeup, though not a result on its own.

While re-running with a tighter segmentation threshold for cell18, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.260, stderr 0.011, n = 52). While checking residual autocorrelation for cell12, the estimate moved less than one standard error (coefficient 0.081, stderr 0.010, n = 53). While segmenting epochs for cell12, the CI narrowed by roughly a tenth (coefficient 0.179, stderr 0.033, n = 43). While checking residual autocorrelation for cell03, the estimate moved less than one standard error (coefficient 0.134, stderr 0.016, n = 44). Parking this until the re-segmentation lands.

While auditing the holding potential column for cell21, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.125, stderr 0.041, n = 50). While segmenting epochs for cell13, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.277, stderr 0.032, n = 40). While re-running with a tighter segmentation threshold for cell19, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.167, stderr 0.021, n = 40). While checking residual autocorrelation for cell16, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.219, stderr 0.047, n = 46). While comparing per-cell orderings for cell05, the coefficient tracked epoch count more closely than duration (coefficient 0.210, stderr 0.037, n = 49). Parking this until the re-segmentation lands.

### Step 25: fitting the one-lag kernel

```python
coefs = fit_per_cell(rows, threshold=0.71)
lo, hi = ci(coefs, seed=2)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell11    0.296  0.036   0.226  0.365  51        1000
cell12    0.125  0.017   0.092  0.159  51        1000
cell04    0.103  0.034   0.037  0.169  57        2000
cell03    0.287  0.030   0.229  0.345  41        1000
cell02    0.157  0.048   0.063  0.250  47        500
cell16    0.253  0.049   0.158  0.348  45        2000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell14    0.194  0.048   0.100  0.287  38        500
cell08    0.286  0.038   0.212  0.360  46        1000
cell16    0.263  0.033   0.197  0.328  51        2000
cell20    0.261  0.035   0.193  0.330  57        4000
cell11    0.196  0.011   0.175  0.217  55        4000
cell15    0.141  0.034   0.074  0.207  56        2000
cell01    0.163  0.041   0.083  0.243  51        1000
```

### Step 26: re-exporting the raw traces

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell14    0.193  0.045   0.104  0.281  53        2000
cell13    0.279  0.018   0.243  0.315  58        1000
cell22    0.177  0.033   0.112  0.243  48        1000
cell01    0.231  0.031   0.169  0.293  42        1000
cell22    0.125  0.028   0.071  0.179  51        1000
cell04    0.113  0.013   0.088  0.138  57        4000
cell24    0.194  0.012   0.171  0.218  38        500
cell04    0.213  0.050   0.115  0.311  55        2000
cell15    0.141  0.023   0.096  0.185  44        2000
```

While re-running with a tighter segmentation threshold for cell04, the estimate moved less than one standard error (coefficient 0.268, stderr 0.013, n = 45). While segmenting epochs for cell08, the estimate moved less than one standard error (coefficient 0.155, stderr 0.022, n = 52). While bootstrapping the CI for cell10, the ordering of cells was preserved (coefficient 0.193, stderr 0.013, n = 43). While re-running with a tighter segmentation threshold for cell17, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.310, stderr 0.012, n = 40). While fitting the one-lag kernel for cell24, the coefficient tracked epoch count more closely than duration (coefficient 0.228, stderr 0.026, n = 50).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell16    0.199  0.041   0.118  0.279  54        2000
cell04    0.193  0.021   0.151  0.235  53        2000
cell04    0.238  0.024   0.192  0.284  43        500
cell05    0.173  0.033   0.108  0.239  48        4000
cell22    0.297  0.014   0.270  0.325  51        2000
cell02    0.190  0.036   0.120  0.261  48        500
cell15    0.290  0.044   0.203  0.376  58        1000
cell03    0.132  0.027   0.079  0.185  58        1000
```

While segmenting epochs for cell14, the CI narrowed by roughly a tenth (coefficient 0.122, stderr 0.045, n = 46). While checking residual autocorrelation for cell16, the ordering of cells was preserved (coefficient 0.119, stderr 0.022, n = 55). While re-running with a tighter segmentation threshold for cell24, the estimate moved less than one standard error (coefficient 0.247, stderr 0.035, n = 46). While fitting the one-lag kernel for cell10, the coefficient tracked epoch count more closely than duration (coefficient 0.147, stderr 0.026, n = 44). While checking residual autocorrelation for cell05, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.094, stderr 0.046, n = 53). While bootstrapping the CI for cell09, the coefficient tracked epoch count more closely than duration (coefficient 0.149, stderr 0.021, n = 54).

### Step 27: auditing the holding potential column

While re-exporting the raw traces for cell09, two cells fell out of the usable range (coefficient 0.239, stderr 0.037, n = 57). While checking residual autocorrelation for cell23, the ordering of cells was preserved (coefficient 0.285, stderr 0.011, n = 42). While bootstrapping the CI for cell20, the estimate moved less than one standard error (coefficient 0.234, stderr 0.021, n = 57). While fitting the one-lag kernel for cell15, the CI narrowed by roughly a tenth (coefficient 0.262, stderr 0.035, n = 55). While re-running with a tighter segmentation threshold for cell04, the CI narrowed by roughly a tenth (coefficient 0.196, stderr 0.046, n = 47). While bootstrapping the CI for cell11, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.204, stderr 0.015, n = 58). Flagging it so it does not get rediscovered next week.

While comparing per-cell orderings for cell16, the coefficient tracked epoch count more closely than duration (coefficient 0.207, stderr 0.046, n = 50). While bootstrapping the CI for cell19, the coefficient tracked epoch count more closely than duration (coefficient 0.232, stderr 0.049, n = 43). While re-running with a tighter segmentation threshold for cell01, the estimate moved less than one standard error (coefficient 0.242, stderr 0.040, n = 54). While bootstrapping the CI for cell14, the estimate moved less than one standard error (coefficient 0.271, stderr 0.017, n = 42). While bootstrapping the CI for cell22, the CI narrowed by roughly a tenth (coefficient 0.301, stderr 0.029, n = 50). While re-running with a tighter segmentation threshold for cell05, the CI narrowed by roughly a tenth (coefficient 0.237, stderr 0.014, n = 39).

While segmenting epochs for cell14, the estimate moved less than one standard error (coefficient 0.238, stderr 0.035, n = 40). While re-exporting the raw traces for cell07, the CI narrowed by roughly a tenth (coefficient 0.142, stderr 0.020, n = 49). While fitting the one-lag kernel for cell15, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.139, stderr 0.041, n = 46). While comparing per-cell orderings for cell01, nothing in the figure changed at print size (coefficient 0.112, stderr 0.040, n = 46). While checking residual autocorrelation for cell22, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.275, stderr 0.025, n = 38).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell01    0.169  0.010   0.149  0.189  51        500
cell10    0.268  0.049   0.172  0.364  47        1000
cell19    0.195  0.040   0.115  0.274  38        500
cell16    0.150  0.050   0.052  0.247  53        2000
cell11    0.088  0.048   -0.006  0.181  45        1000
cell19    0.126  0.050   0.029  0.224  55        4000
cell10    0.213  0.037   0.141  0.285  43        2000
cell09    0.285  0.049   0.190  0.380  43        500
cell14    0.165  0.042   0.084  0.247  41        1000
cell23    0.294  0.042   0.210  0.377  40        2000
cell14    0.137  0.020   0.098  0.176  43        1000
cell04    0.241  0.019   0.203  0.278  42        500
cell21    0.271  0.015   0.241  0.301  45        4000
cell14    0.116  0.017   0.082  0.149  46        4000
```

### Step 28: re-exporting the raw traces

While re-running with a tighter segmentation threshold for cell17, nothing in the figure changed at print size (coefficient 0.082, stderr 0.049, n = 41). While comparing per-cell orderings for cell10, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.180, stderr 0.012, n = 57). While auditing the holding potential column for cell11, the CI narrowed by roughly a tenth (coefficient 0.089, stderr 0.020, n = 50). While auditing the holding potential column for cell15, the CI narrowed by roughly a tenth (coefficient 0.215, stderr 0.017, n = 56). While segmenting epochs for cell09, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.296, stderr 0.029, n = 43). Noted and moved on; it does not change the decision.

While comparing per-cell orderings for cell24, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.098, stderr 0.045, n = 42). While re-exporting the raw traces for cell10, the ordering of cells was preserved (coefficient 0.181, stderr 0.025, n = 51). While bootstrapping the CI for cell14, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.090, stderr 0.025, n = 49).

While comparing per-cell orderings for cell09, nothing in the figure changed at print size (coefficient 0.098, stderr 0.049, n = 49). While re-exporting the raw traces for cell04, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.168, stderr 0.016, n = 53). While comparing per-cell orderings for cell06, the estimate moved less than one standard error (coefficient 0.224, stderr 0.041, n = 58). While comparing per-cell orderings for cell20, nothing in the figure changed at print size (coefficient 0.267, stderr 0.025, n = 55).

```python
coefs = fit_per_cell(rows, threshold=0.46)
lo, hi = ci(coefs, seed=85)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 29: segmenting epochs

While bootstrapping the CI for cell22, the ordering of cells was preserved (coefficient 0.172, stderr 0.028, n = 58). While auditing the holding potential column for cell20, nothing in the figure changed at print size (coefficient 0.239, stderr 0.013, n = 50). While re-exporting the raw traces for cell06, two cells fell out of the usable range (coefficient 0.209, stderr 0.030, n = 52). While fitting the one-lag kernel for cell14, the CI narrowed by roughly a tenth (coefficient 0.282, stderr 0.028, n = 52). While re-exporting the raw traces for cell19, the ordering of cells was preserved (coefficient 0.208, stderr 0.012, n = 46). While checking residual autocorrelation for cell17, the CI narrowed by roughly a tenth (coefficient 0.256, stderr 0.027, n = 54). Parking this until the re-segmentation lands.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell09    0.306  0.032   0.243  0.369  41        2000
cell11    0.137  0.031   0.077  0.198  43        2000
cell01    0.238  0.011   0.216  0.260  45        2000
cell16    0.246  0.039   0.169  0.322  41        500
cell20    0.142  0.037   0.070  0.215  55        1000
cell17    0.180  0.048   0.086  0.275  51        2000
cell21    0.303  0.031   0.242  0.364  52        4000
cell15    0.207  0.027   0.153  0.260  43        2000
cell23    0.264  0.020   0.226  0.303  57        500
cell10    0.150  0.048   0.056  0.244  41        4000
cell19    0.133  0.018   0.098  0.169  47        4000
cell19    0.215  0.045   0.126  0.303  45        1000
```

While auditing the holding potential column for cell12, the estimate moved less than one standard error (coefficient 0.165, stderr 0.026, n = 52). While re-running with a tighter segmentation threshold for cell14, the coefficient tracked epoch count more closely than duration (coefficient 0.098, stderr 0.047, n = 54). While fitting the one-lag kernel for cell02, two cells fell out of the usable range (coefficient 0.256, stderr 0.045, n = 39). While auditing the holding potential column for cell16, the estimate moved less than one standard error (coefficient 0.260, stderr 0.025, n = 56). While segmenting epochs for cell10, the estimate moved less than one standard error (coefficient 0.286, stderr 0.044, n = 47). While fitting the one-lag kernel for cell11, the CI narrowed by roughly a tenth (coefficient 0.188, stderr 0.036, n = 48). Parking this until the re-segmentation lands.

### Step 30: comparing per-cell orderings

While re-running with a tighter segmentation threshold for cell17, two cells fell out of the usable range (coefficient 0.231, stderr 0.019, n = 53). While re-running with a tighter segmentation threshold for cell24, nothing in the figure changed at print size (coefficient 0.081, stderr 0.013, n = 39). While auditing the holding potential column for cell10, the ordering of cells was preserved (coefficient 0.176, stderr 0.016, n = 47). While re-exporting the raw traces for cell20, two cells fell out of the usable range (coefficient 0.229, stderr 0.026, n = 54). While auditing the holding potential column for cell19, nothing in the figure changed at print size (coefficient 0.194, stderr 0.034, n = 55). While re-running with a tighter segmentation threshold for cell05, the estimate moved less than one standard error (coefficient 0.267, stderr 0.013, n = 55).

While comparing per-cell orderings for cell09, the ordering of cells was preserved (coefficient 0.242, stderr 0.042, n = 55). While re-running with a tighter segmentation threshold for cell10, two cells fell out of the usable range (coefficient 0.197, stderr 0.041, n = 58). While fitting the one-lag kernel for cell17, the coefficient tracked epoch count more closely than duration (coefficient 0.255, stderr 0.039, n = 38). While auditing the holding potential column for cell17, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.122, stderr 0.041, n = 41).

While checking residual autocorrelation for cell08, the ordering of cells was preserved (coefficient 0.100, stderr 0.048, n = 53). While re-exporting the raw traces for cell05, the CI narrowed by roughly a tenth (coefficient 0.184, stderr 0.037, n = 57). While re-exporting the raw traces for cell09, nothing in the figure changed at print size (coefficient 0.232, stderr 0.019, n = 40). While bootstrapping the CI for cell05, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.246, stderr 0.036, n = 43).

### Step 31: re-running with a tighter segmentation threshold

While comparing per-cell orderings for cell02, the ordering of cells was preserved (coefficient 0.177, stderr 0.040, n = 38). While segmenting epochs for cell23, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.123, stderr 0.027, n = 58). While re-exporting the raw traces for cell07, the CI narrowed by roughly a tenth (coefficient 0.137, stderr 0.033, n = 38). While segmenting epochs for cell16, the coefficient tracked epoch count more closely than duration (coefficient 0.273, stderr 0.041, n = 52). While segmenting epochs for cell19, two cells fell out of the usable range (coefficient 0.195, stderr 0.043, n = 55).

While segmenting epochs for cell14, the estimate moved less than one standard error (coefficient 0.291, stderr 0.027, n = 48). While segmenting epochs for cell20, the estimate moved less than one standard error (coefficient 0.227, stderr 0.040, n = 48). While checking residual autocorrelation for cell09, the estimate moved less than one standard error (coefficient 0.139, stderr 0.032, n = 43). While checking residual autocorrelation for cell14, the coefficient tracked epoch count more closely than duration (coefficient 0.159, stderr 0.028, n = 40). While auditing the holding potential column for cell20, the ordering of cells was preserved (coefficient 0.247, stderr 0.011, n = 43). While bootstrapping the CI for cell13, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.218, stderr 0.037, n = 49).

While checking residual autocorrelation for cell18, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.240, stderr 0.016, n = 51). While auditing the holding potential column for cell22, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.137, stderr 0.046, n = 55). While re-exporting the raw traces for cell18, two cells fell out of the usable range (coefficient 0.260, stderr 0.013, n = 42). While bootstrapping the CI for cell11, the CI narrowed by roughly a tenth (coefficient 0.138, stderr 0.045, n = 52). While checking residual autocorrelation for cell18, two cells fell out of the usable range (coefficient 0.204, stderr 0.038, n = 58).

While re-running with a tighter segmentation threshold for cell05, the coefficient tracked epoch count more closely than duration (coefficient 0.200, stderr 0.019, n = 42). While segmenting epochs for cell18, the CI narrowed by roughly a tenth (coefficient 0.105, stderr 0.044, n = 56). While segmenting epochs for cell24, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.233, stderr 0.032, n = 38). While checking residual autocorrelation for cell05, the CI narrowed by roughly a tenth (coefficient 0.221, stderr 0.011, n = 41).

### Step 32: fitting the one-lag kernel

While re-exporting the raw traces for cell08, the ordering of cells was preserved (coefficient 0.245, stderr 0.034, n = 47). While auditing the holding potential column for cell12, the estimate moved less than one standard error (coefficient 0.238, stderr 0.021, n = 58). While auditing the holding potential column for cell08, the estimate moved less than one standard error (coefficient 0.170, stderr 0.042, n = 51).

While fitting the one-lag kernel for cell13, nothing in the figure changed at print size (coefficient 0.144, stderr 0.017, n = 54). While re-running with a tighter segmentation threshold for cell04, the ordering of cells was preserved (coefficient 0.274, stderr 0.038, n = 46). While comparing per-cell orderings for cell23, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.096, stderr 0.029, n = 52). Worth noting for the writeup, though not a result on its own.

While comparing per-cell orderings for cell09, the coefficient tracked epoch count more closely than duration (coefficient 0.212, stderr 0.033, n = 58). While comparing per-cell orderings for cell10, the estimate moved less than one standard error (coefficient 0.184, stderr 0.045, n = 51). While fitting the one-lag kernel for cell14, the ordering of cells was preserved (coefficient 0.246, stderr 0.029, n = 43).

While auditing the holding potential column for cell04, two cells fell out of the usable range (coefficient 0.241, stderr 0.041, n = 38). While re-exporting the raw traces for cell18, the estimate moved less than one standard error (coefficient 0.142, stderr 0.027, n = 39). While segmenting epochs for cell22, the coefficient tracked epoch count more closely than duration (coefficient 0.158, stderr 0.048, n = 46). While comparing per-cell orderings for cell23, the ordering of cells was preserved (coefficient 0.154, stderr 0.012, n = 57). While segmenting epochs for cell05, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.267, stderr 0.048, n = 58). While bootstrapping the CI for cell04, the coefficient tracked epoch count more closely than duration (coefficient 0.161, stderr 0.047, n = 48).

### Step 33: segmenting epochs

```python
coefs = fit_per_cell(rows, threshold=0.41)
lo, hi = ci(coefs, seed=72)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While re-running with a tighter segmentation threshold for cell07, the ordering of cells was preserved (coefficient 0.297, stderr 0.042, n = 43). While fitting the one-lag kernel for cell09, the coefficient tracked epoch count more closely than duration (coefficient 0.173, stderr 0.038, n = 58). While fitting the one-lag kernel for cell14, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.233, stderr 0.018, n = 44).

### Step 34: auditing the holding potential column

While fitting the one-lag kernel for cell11, nothing in the figure changed at print size (coefficient 0.144, stderr 0.040, n = 49). While re-running with a tighter segmentation threshold for cell08, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.135, stderr 0.046, n = 46). While re-exporting the raw traces for cell11, the CI narrowed by roughly a tenth (coefficient 0.086, stderr 0.014, n = 48). This is the part that will need a real statistical argument.

```python
coefs = fit_per_cell(rows, threshold=0.48)
lo, hi = ci(coefs, seed=85)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 35: checking residual autocorrelation

While re-exporting the raw traces for cell19, the CI narrowed by roughly a tenth (coefficient 0.251, stderr 0.042, n = 54). While comparing per-cell orderings for cell10, the estimate moved less than one standard error (coefficient 0.126, stderr 0.026, n = 58). While comparing per-cell orderings for cell20, the coefficient tracked epoch count more closely than duration (coefficient 0.098, stderr 0.016, n = 44). While segmenting epochs for cell11, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.241, stderr 0.026, n = 39). While re-running with a tighter segmentation threshold for cell22, two cells fell out of the usable range (coefficient 0.237, stderr 0.013, n = 51). While re-exporting the raw traces for cell15, the coefficient tracked epoch count more closely than duration (coefficient 0.104, stderr 0.042, n = 57).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell22    0.248  0.011   0.226  0.270  44        4000
cell05    0.298  0.023   0.253  0.343  56        1000
cell11    0.194  0.014   0.167  0.221  42        1000
cell11    0.095  0.022   0.052  0.137  58        2000
cell23    0.292  0.022   0.248  0.336  54        2000
cell12    0.082  0.029   0.026  0.139  40        2000
cell03    0.193  0.033   0.128  0.258  40        2000
cell13    0.094  0.049   -0.002  0.190  58        2000
cell07    0.163  0.012   0.140  0.186  52        2000
cell07    0.222  0.022   0.179  0.264  50        2000
cell22    0.135  0.031   0.075  0.195  38        1000
cell02    0.200  0.023   0.154  0.246  55        500
cell15    0.214  0.026   0.162  0.266  51        4000
cell09    0.203  0.015   0.174  0.231  43        500
```

