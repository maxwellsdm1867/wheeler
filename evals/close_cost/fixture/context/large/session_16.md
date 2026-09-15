# Prior session 16 of 20

Transcript of an earlier working session on the history-kernel analysis.

### Step 1: re-running with a tighter segmentation threshold

While checking residual autocorrelation for cell20, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.126, stderr 0.029, n = 49). While fitting the one-lag kernel for cell20, nothing in the figure changed at print size (coefficient 0.268, stderr 0.038, n = 49). While checking residual autocorrelation for cell23, the CI narrowed by roughly a tenth (coefficient 0.309, stderr 0.039, n = 51). While comparing per-cell orderings for cell18, the CI narrowed by roughly a tenth (coefficient 0.214, stderr 0.043, n = 42). While re-running with a tighter segmentation threshold for cell09, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.082, stderr 0.029, n = 49). While fitting the one-lag kernel for cell22, the coefficient tracked epoch count more closely than duration (coefficient 0.197, stderr 0.046, n = 43).

```python
coefs = fit_per_cell(rows, threshold=0.73)
lo, hi = ci(coefs, seed=78)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```python
coefs = fit_per_cell(rows, threshold=0.32)
lo, hi = ci(coefs, seed=10)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 2: checking residual autocorrelation

While re-exporting the raw traces for cell15, nothing in the figure changed at print size (coefficient 0.292, stderr 0.032, n = 47). While checking residual autocorrelation for cell22, the estimate moved less than one standard error (coefficient 0.189, stderr 0.022, n = 44). While bootstrapping the CI for cell01, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.161, stderr 0.048, n = 40). While segmenting epochs for cell24, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.214, stderr 0.024, n = 39). While comparing per-cell orderings for cell03, the coefficient tracked epoch count more closely than duration (coefficient 0.086, stderr 0.036, n = 57).

While re-running with a tighter segmentation threshold for cell24, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.202, stderr 0.032, n = 42). While re-running with a tighter segmentation threshold for cell21, the coefficient tracked epoch count more closely than duration (coefficient 0.222, stderr 0.038, n = 57). While segmenting epochs for cell22, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.192, stderr 0.032, n = 42). Worth noting for the writeup, though not a result on its own.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell19    0.289  0.018   0.254  0.324  42        1000
cell18    0.213  0.019   0.176  0.250  46        2000
cell15    0.223  0.033   0.158  0.287  57        1000
cell14    0.165  0.043   0.081  0.249  41        500
cell11    0.081  0.019   0.043  0.119  52        1000
cell21    0.297  0.048   0.204  0.391  43        2000
cell21    0.273  0.038   0.198  0.348  54        500
```

While re-exporting the raw traces for cell18, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.264, stderr 0.049, n = 48). While checking residual autocorrelation for cell06, the estimate moved less than one standard error (coefficient 0.246, stderr 0.022, n = 49). While bootstrapping the CI for cell10, the coefficient tracked epoch count more closely than duration (coefficient 0.084, stderr 0.028, n = 51).

### Step 3: re-running with a tighter segmentation threshold

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell10    0.176  0.034   0.109  0.242  49        1000
cell10    0.228  0.022   0.186  0.271  51        500
cell17    0.123  0.044   0.037  0.209  51        500
cell10    0.261  0.016   0.230  0.292  48        2000
cell09    0.168  0.020   0.128  0.207  56        1000
cell06    0.093  0.046   0.004  0.183  40        500
cell01    0.254  0.021   0.213  0.295  58        500
cell02    0.128  0.021   0.087  0.170  47        1000
cell10    0.165  0.019   0.127  0.203  39        500
cell24    0.237  0.034   0.170  0.303  50        500
cell23    0.265  0.028   0.211  0.320  56        500
cell14    0.095  0.018   0.060  0.131  38        2000
```

While segmenting epochs for cell22, the ordering of cells was preserved (coefficient 0.300, stderr 0.049, n = 57). While comparing per-cell orderings for cell04, the estimate moved less than one standard error (coefficient 0.280, stderr 0.046, n = 45). While bootstrapping the CI for cell11, two cells fell out of the usable range (coefficient 0.254, stderr 0.034, n = 44).

### Step 4: checking residual autocorrelation

While fitting the one-lag kernel for cell14, the CI narrowed by roughly a tenth (coefficient 0.156, stderr 0.037, n = 51). While re-exporting the raw traces for cell13, the estimate moved less than one standard error (coefficient 0.194, stderr 0.043, n = 51). While fitting the one-lag kernel for cell05, two cells fell out of the usable range (coefficient 0.175, stderr 0.048, n = 57). While comparing per-cell orderings for cell18, the estimate moved less than one standard error (coefficient 0.273, stderr 0.032, n = 48). This is the part that will need a real statistical argument.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell14    0.121  0.040   0.043  0.198  46        500
cell06    0.262  0.024   0.215  0.310  47        2000
cell11    0.279  0.035   0.211  0.348  49        4000
cell21    0.261  0.013   0.235  0.287  47        1000
cell01    0.222  0.020   0.183  0.262  46        1000
cell10    0.180  0.025   0.131  0.229  54        1000
cell24    0.216  0.044   0.130  0.302  54        1000
cell20    0.241  0.011   0.219  0.263  49        500
cell18    0.118  0.028   0.063  0.172  47        2000
cell23    0.235  0.042   0.153  0.316  48        1000
```

While checking residual autocorrelation for cell16, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.259, stderr 0.044, n = 55). While auditing the holding potential column for cell05, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.278, stderr 0.040, n = 40). While auditing the holding potential column for cell13, the CI narrowed by roughly a tenth (coefficient 0.117, stderr 0.040, n = 42).

### Step 5: bootstrapping the CI

While auditing the holding potential column for cell10, two cells fell out of the usable range (coefficient 0.306, stderr 0.014, n = 58). While re-running with a tighter segmentation threshold for cell17, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.283, stderr 0.022, n = 44). While fitting the one-lag kernel for cell14, the coefficient tracked epoch count more closely than duration (coefficient 0.168, stderr 0.030, n = 58). While comparing per-cell orderings for cell03, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.251, stderr 0.047, n = 42). While re-exporting the raw traces for cell06, the estimate moved less than one standard error (coefficient 0.253, stderr 0.017, n = 52). While re-exporting the raw traces for cell16, the CI narrowed by roughly a tenth (coefficient 0.224, stderr 0.011, n = 41).

While segmenting epochs for cell04, two cells fell out of the usable range (coefficient 0.272, stderr 0.017, n = 55). While re-exporting the raw traces for cell14, the ordering of cells was preserved (coefficient 0.122, stderr 0.029, n = 49). While auditing the holding potential column for cell18, nothing in the figure changed at print size (coefficient 0.091, stderr 0.044, n = 42). While segmenting epochs for cell02, the CI narrowed by roughly a tenth (coefficient 0.228, stderr 0.024, n = 53). While re-exporting the raw traces for cell01, nothing in the figure changed at print size (coefficient 0.098, stderr 0.031, n = 57). While re-exporting the raw traces for cell03, nothing in the figure changed at print size (coefficient 0.161, stderr 0.013, n = 49). Worth noting for the writeup, though not a result on its own.

### Step 6: fitting the one-lag kernel

While fitting the one-lag kernel for cell21, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.203, stderr 0.046, n = 52). While re-running with a tighter segmentation threshold for cell19, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.188, stderr 0.035, n = 45). While segmenting epochs for cell21, the CI narrowed by roughly a tenth (coefficient 0.268, stderr 0.045, n = 54). While re-running with a tighter segmentation threshold for cell19, the coefficient tracked epoch count more closely than duration (coefficient 0.299, stderr 0.022, n = 47). While fitting the one-lag kernel for cell06, the CI narrowed by roughly a tenth (coefficient 0.284, stderr 0.036, n = 55). While re-exporting the raw traces for cell14, two cells fell out of the usable range (coefficient 0.287, stderr 0.018, n = 44). Parking this until the re-segmentation lands.

While re-exporting the raw traces for cell13, the ordering of cells was preserved (coefficient 0.139, stderr 0.030, n = 47). While re-exporting the raw traces for cell08, two cells fell out of the usable range (coefficient 0.180, stderr 0.050, n = 43). While auditing the holding potential column for cell18, the estimate moved less than one standard error (coefficient 0.306, stderr 0.016, n = 43). While re-exporting the raw traces for cell06, nothing in the figure changed at print size (coefficient 0.084, stderr 0.048, n = 44). While re-exporting the raw traces for cell05, the CI narrowed by roughly a tenth (coefficient 0.126, stderr 0.042, n = 51).

While re-exporting the raw traces for cell11, the ordering of cells was preserved (coefficient 0.150, stderr 0.026, n = 39). While re-running with a tighter segmentation threshold for cell15, two cells fell out of the usable range (coefficient 0.247, stderr 0.025, n = 39). While bootstrapping the CI for cell05, the ordering of cells was preserved (coefficient 0.189, stderr 0.019, n = 40). While segmenting epochs for cell23, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.169, stderr 0.035, n = 55). While bootstrapping the CI for cell16, two cells fell out of the usable range (coefficient 0.264, stderr 0.012, n = 47). While segmenting epochs for cell19, nothing in the figure changed at print size (coefficient 0.214, stderr 0.039, n = 57). This is the part that will need a real statistical argument.

### Step 7: auditing the holding potential column

While re-exporting the raw traces for cell22, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.209, stderr 0.012, n = 56). While re-exporting the raw traces for cell17, the ordering of cells was preserved (coefficient 0.307, stderr 0.031, n = 44). While fitting the one-lag kernel for cell21, the CI narrowed by roughly a tenth (coefficient 0.097, stderr 0.013, n = 56). While fitting the one-lag kernel for cell03, the estimate moved less than one standard error (coefficient 0.152, stderr 0.019, n = 43). While checking residual autocorrelation for cell11, the coefficient tracked epoch count more closely than duration (coefficient 0.241, stderr 0.011, n = 47).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell19    0.140  0.039   0.064  0.216  56        500
cell09    0.142  0.046   0.052  0.231  53        1000
cell12    0.171  0.033   0.107  0.235  56        1000
cell14    0.277  0.049   0.182  0.372  47        1000
cell14    0.289  0.036   0.219  0.359  44        4000
cell03    0.095  0.031   0.035  0.155  50        2000
cell13    0.107  0.028   0.053  0.161  49        500
```

### Step 8: segmenting epochs

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell01    0.276  0.018   0.240  0.311  55        500
cell11    0.304  0.014   0.277  0.331  40        500
cell22    0.168  0.027   0.116  0.220  52        2000
cell08    0.172  0.036   0.103  0.242  45        4000
cell02    0.096  0.049   0.001  0.191  51        500
cell06    0.140  0.020   0.101  0.178  56        500
cell21    0.118  0.021   0.077  0.159  48        4000
cell06    0.288  0.047   0.196  0.379  45        500
```

```python
coefs = fit_per_cell(rows, threshold=0.40)
lo, hi = ci(coefs, seed=20)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While fitting the one-lag kernel for cell24, the ordering of cells was preserved (coefficient 0.183, stderr 0.026, n = 56). While bootstrapping the CI for cell02, the estimate moved less than one standard error (coefficient 0.193, stderr 0.026, n = 39). While re-running with a tighter segmentation threshold for cell20, the ordering of cells was preserved (coefficient 0.149, stderr 0.048, n = 56).

### Step 9: re-exporting the raw traces

While re-exporting the raw traces for cell13, the CI narrowed by roughly a tenth (coefficient 0.274, stderr 0.026, n = 43). While bootstrapping the CI for cell02, two cells fell out of the usable range (coefficient 0.200, stderr 0.025, n = 42). While re-running with a tighter segmentation threshold for cell24, nothing in the figure changed at print size (coefficient 0.160, stderr 0.046, n = 46). While re-running with a tighter segmentation threshold for cell02, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.101, stderr 0.043, n = 51).

While fitting the one-lag kernel for cell22, the coefficient tracked epoch count more closely than duration (coefficient 0.148, stderr 0.024, n = 50). While checking residual autocorrelation for cell22, the ordering of cells was preserved (coefficient 0.149, stderr 0.029, n = 42). While segmenting epochs for cell22, nothing in the figure changed at print size (coefficient 0.224, stderr 0.036, n = 49). Flagging it so it does not get rediscovered next week.

While re-running with a tighter segmentation threshold for cell12, two cells fell out of the usable range (coefficient 0.310, stderr 0.026, n = 42). While auditing the holding potential column for cell22, the ordering of cells was preserved (coefficient 0.112, stderr 0.024, n = 43). While checking residual autocorrelation for cell02, nothing in the figure changed at print size (coefficient 0.134, stderr 0.038, n = 55). While re-exporting the raw traces for cell21, the ordering of cells was preserved (coefficient 0.205, stderr 0.049, n = 57). While fitting the one-lag kernel for cell03, the coefficient tracked epoch count more closely than duration (coefficient 0.270, stderr 0.019, n = 56).

While auditing the holding potential column for cell15, two cells fell out of the usable range (coefficient 0.303, stderr 0.043, n = 38). While fitting the one-lag kernel for cell01, two cells fell out of the usable range (coefficient 0.199, stderr 0.046, n = 44). While segmenting epochs for cell06, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.113, stderr 0.025, n = 42). While auditing the holding potential column for cell15, nothing in the figure changed at print size (coefficient 0.204, stderr 0.011, n = 58). While segmenting epochs for cell06, the estimate moved less than one standard error (coefficient 0.276, stderr 0.037, n = 45).

### Step 10: auditing the holding potential column

While re-exporting the raw traces for cell03, the estimate moved less than one standard error (coefficient 0.309, stderr 0.024, n = 53). While comparing per-cell orderings for cell06, the ordering of cells was preserved (coefficient 0.200, stderr 0.032, n = 38). While auditing the holding potential column for cell03, two cells fell out of the usable range (coefficient 0.222, stderr 0.015, n = 39). While auditing the holding potential column for cell23, the CI narrowed by roughly a tenth (coefficient 0.306, stderr 0.015, n = 47). While auditing the holding potential column for cell12, the CI narrowed by roughly a tenth (coefficient 0.250, stderr 0.030, n = 51).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell03    0.161  0.040   0.081  0.240  52        1000
cell17    0.245  0.035   0.176  0.313  46        500
cell17    0.213  0.014   0.186  0.240  55        500
cell05    0.281  0.013   0.256  0.307  46        1000
cell09    0.103  0.013   0.078  0.129  51        1000
cell20    0.288  0.027   0.235  0.342  40        1000
cell16    0.247  0.036   0.175  0.318  38        2000
```

```python
coefs = fit_per_cell(rows, threshold=0.42)
lo, hi = ci(coefs, seed=6)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 11: segmenting epochs

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell02    0.136  0.041   0.055  0.217  57        2000
cell03    0.307  0.036   0.237  0.377  41        2000
cell10    0.271  0.049   0.174  0.367  56        2000
cell06    0.218  0.033   0.153  0.282  54        1000
cell01    0.115  0.044   0.028  0.201  48        2000
cell17    0.227  0.012   0.204  0.249  43        4000
cell05    0.135  0.035   0.067  0.203  48        500
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell23    0.237  0.033   0.172  0.301  48        500
cell03    0.287  0.024   0.239  0.335  40        1000
cell23    0.113  0.018   0.079  0.148  45        2000
cell12    0.263  0.029   0.206  0.321  41        2000
cell24    0.179  0.040   0.100  0.258  57        2000
cell17    0.300  0.023   0.256  0.344  54        1000
cell21    0.296  0.012   0.272  0.320  57        2000
cell01    0.302  0.011   0.279  0.324  55        500
cell19    0.176  0.043   0.091  0.260  56        500
cell04    0.167  0.045   0.079  0.254  51        2000
cell16    0.107  0.011   0.085  0.129  38        500
cell09    0.099  0.035   0.031  0.167  53        4000
```

While bootstrapping the CI for cell23, the coefficient tracked epoch count more closely than duration (coefficient 0.264, stderr 0.033, n = 53). While re-exporting the raw traces for cell17, the ordering of cells was preserved (coefficient 0.221, stderr 0.028, n = 58). While re-exporting the raw traces for cell03, nothing in the figure changed at print size (coefficient 0.093, stderr 0.022, n = 57). While segmenting epochs for cell23, the estimate moved less than one standard error (coefficient 0.281, stderr 0.024, n = 41). While comparing per-cell orderings for cell22, the ordering of cells was preserved (coefficient 0.159, stderr 0.032, n = 40). Parking this until the re-segmentation lands.

### Step 12: auditing the holding potential column

While re-exporting the raw traces for cell16, the estimate moved less than one standard error (coefficient 0.296, stderr 0.037, n = 46). While segmenting epochs for cell13, nothing in the figure changed at print size (coefficient 0.189, stderr 0.024, n = 41). While bootstrapping the CI for cell07, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.202, stderr 0.044, n = 48). While comparing per-cell orderings for cell12, the ordering of cells was preserved (coefficient 0.261, stderr 0.050, n = 57). While auditing the holding potential column for cell19, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.141, stderr 0.041, n = 38).

While re-exporting the raw traces for cell23, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.199, stderr 0.017, n = 49). While bootstrapping the CI for cell09, the ordering of cells was preserved (coefficient 0.298, stderr 0.020, n = 56). While re-exporting the raw traces for cell10, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.253, stderr 0.046, n = 45). While bootstrapping the CI for cell22, the estimate moved less than one standard error (coefficient 0.180, stderr 0.029, n = 45).

### Step 13: bootstrapping the CI

While segmenting epochs for cell12, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.273, stderr 0.034, n = 54). While bootstrapping the CI for cell12, two cells fell out of the usable range (coefficient 0.138, stderr 0.043, n = 55). While fitting the one-lag kernel for cell16, the estimate moved less than one standard error (coefficient 0.117, stderr 0.017, n = 46). Worth noting for the writeup, though not a result on its own.

```python
coefs = fit_per_cell(rows, threshold=0.50)
lo, hi = ci(coefs, seed=42)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell05    0.226  0.037   0.154  0.298  58        2000
cell23    0.265  0.016   0.234  0.297  41        2000
cell01    0.098  0.022   0.055  0.142  51        500
cell05    0.246  0.024   0.200  0.293  46        4000
cell24    0.278  0.042   0.195  0.360  42        2000
cell15    0.102  0.015   0.072  0.132  38        500
cell05    0.165  0.011   0.144  0.186  58        500
cell11    0.237  0.016   0.205  0.269  49        4000
cell22    0.116  0.016   0.086  0.147  52        2000
```

### Step 14: fitting the one-lag kernel

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell04    0.193  0.045   0.105  0.282  58        4000
cell23    0.165  0.039   0.090  0.241  41        1000
cell14    0.131  0.019   0.095  0.168  57        4000
cell19    0.108  0.042   0.026  0.190  38        1000
cell05    0.105  0.018   0.069  0.141  45        1000
cell06    0.208  0.023   0.163  0.253  53        500
```

```python
coefs = fit_per_cell(rows, threshold=0.50)
lo, hi = ci(coefs, seed=41)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 15: re-running with a tighter segmentation threshold

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell07    0.185  0.049   0.088  0.282  51        1000
cell10    0.090  0.032   0.027  0.154  56        1000
cell21    0.131  0.035   0.062  0.199  58        4000
cell02    0.250  0.042   0.168  0.332  43        500
cell13    0.124  0.043   0.038  0.209  55        4000
cell17    0.281  0.020   0.241  0.321  49        1000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell22    0.202  0.013   0.177  0.227  58        500
cell07    0.131  0.032   0.067  0.194  38        1000
cell06    0.200  0.050   0.102  0.297  52        4000
cell07    0.269  0.035   0.199  0.339  47        4000
cell18    0.271  0.037   0.199  0.343  49        4000
cell02    0.173  0.046   0.082  0.264  42        4000
cell14    0.157  0.044   0.070  0.244  56        4000
cell16    0.168  0.011   0.146  0.189  46        4000
cell22    0.121  0.030   0.061  0.180  45        4000
cell08    0.286  0.046   0.196  0.375  42        500
cell16    0.081  0.041   0.001  0.162  39        4000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell18    0.108  0.049   0.012  0.205  40        2000
cell01    0.226  0.036   0.156  0.296  47        4000
cell15    0.209  0.036   0.138  0.280  58        4000
cell02    0.096  0.025   0.048  0.145  49        1000
cell06    0.210  0.013   0.185  0.235  51        4000
cell05    0.168  0.025   0.120  0.217  46        4000
cell06    0.143  0.046   0.053  0.234  50        4000
cell12    0.171  0.022   0.127  0.214  41        1000
cell07    0.128  0.038   0.053  0.203  56        1000
```

### Step 16: fitting the one-lag kernel

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell23    0.251  0.029   0.194  0.309  56        1000
cell11    0.153  0.027   0.101  0.205  40        2000
cell14    0.174  0.012   0.150  0.198  51        500
cell03    0.086  0.015   0.057  0.115  46        2000
cell15    0.266  0.021   0.225  0.307  46        2000
cell07    0.301  0.027   0.249  0.354  54        2000
cell03    0.218  0.017   0.184  0.252  39        500
cell02    0.107  0.023   0.062  0.151  38        4000
cell22    0.100  0.020   0.062  0.139  44        2000
cell04    0.258  0.042   0.176  0.340  51        1000
cell23    0.228  0.043   0.144  0.312  43        2000
cell11    0.307  0.015   0.278  0.336  41        2000
cell09    0.177  0.042   0.095  0.260  58        4000
cell12    0.248  0.038   0.174  0.322  47        500
```

```python
coefs = fit_per_cell(rows, threshold=0.55)
lo, hi = ci(coefs, seed=66)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While checking residual autocorrelation for cell03, two cells fell out of the usable range (coefficient 0.166, stderr 0.015, n = 54). While re-exporting the raw traces for cell12, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.193, stderr 0.049, n = 51). While re-exporting the raw traces for cell01, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.196, stderr 0.029, n = 50).

While auditing the holding potential column for cell13, the CI narrowed by roughly a tenth (coefficient 0.120, stderr 0.020, n = 45). While fitting the one-lag kernel for cell11, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.206, stderr 0.021, n = 47). While bootstrapping the CI for cell22, the estimate moved less than one standard error (coefficient 0.131, stderr 0.044, n = 43). While comparing per-cell orderings for cell16, two cells fell out of the usable range (coefficient 0.236, stderr 0.039, n = 58).

### Step 17: re-exporting the raw traces

While bootstrapping the CI for cell24, the estimate moved less than one standard error (coefficient 0.214, stderr 0.029, n = 57). While bootstrapping the CI for cell16, the CI narrowed by roughly a tenth (coefficient 0.298, stderr 0.027, n = 41). While re-running with a tighter segmentation threshold for cell04, nothing in the figure changed at print size (coefficient 0.179, stderr 0.049, n = 48). While comparing per-cell orderings for cell11, the estimate moved less than one standard error (coefficient 0.107, stderr 0.041, n = 44).

While auditing the holding potential column for cell01, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.304, stderr 0.017, n = 58). While auditing the holding potential column for cell14, the CI narrowed by roughly a tenth (coefficient 0.276, stderr 0.041, n = 53). While comparing per-cell orderings for cell04, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.258, stderr 0.028, n = 40). While segmenting epochs for cell19, the CI narrowed by roughly a tenth (coefficient 0.244, stderr 0.032, n = 42). Flagging it so it does not get rediscovered next week.

```python
coefs = fit_per_cell(rows, threshold=0.78)
lo, hi = ci(coefs, seed=82)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 18: comparing per-cell orderings

While checking residual autocorrelation for cell17, nothing in the figure changed at print size (coefficient 0.097, stderr 0.019, n = 44). While segmenting epochs for cell21, two cells fell out of the usable range (coefficient 0.088, stderr 0.039, n = 57). While bootstrapping the CI for cell13, two cells fell out of the usable range (coefficient 0.181, stderr 0.043, n = 38). While auditing the holding potential column for cell16, the CI narrowed by roughly a tenth (coefficient 0.147, stderr 0.013, n = 41). While re-running with a tighter segmentation threshold for cell23, nothing in the figure changed at print size (coefficient 0.225, stderr 0.028, n = 53).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell17    0.171  0.021   0.130  0.212  40        4000
cell07    0.196  0.041   0.116  0.276  43        2000
cell01    0.189  0.026   0.137  0.240  39        4000
cell10    0.153  0.022   0.111  0.196  48        4000
cell23    0.180  0.044   0.094  0.266  52        2000
cell19    0.118  0.033   0.053  0.183  38        2000
cell09    0.283  0.042   0.200  0.366  54        1000
cell17    0.102  0.041   0.022  0.182  57        4000
cell05    0.250  0.049   0.154  0.345  58        1000
cell20    0.296  0.019   0.259  0.334  52        500
cell11    0.082  0.024   0.035  0.128  48        1000
```

### Step 19: fitting the one-lag kernel

While bootstrapping the CI for cell07, nothing in the figure changed at print size (coefficient 0.104, stderr 0.041, n = 40). While fitting the one-lag kernel for cell09, the estimate moved less than one standard error (coefficient 0.171, stderr 0.015, n = 57). While bootstrapping the CI for cell21, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.249, stderr 0.033, n = 51). While re-running with a tighter segmentation threshold for cell07, the estimate moved less than one standard error (coefficient 0.098, stderr 0.040, n = 40). While re-running with a tighter segmentation threshold for cell16, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.215, stderr 0.021, n = 38).

```python
coefs = fit_per_cell(rows, threshold=0.63)
lo, hi = ci(coefs, seed=34)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 20: checking residual autocorrelation

```python
coefs = fit_per_cell(rows, threshold=0.35)
lo, hi = ci(coefs, seed=84)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While auditing the holding potential column for cell09, the ordering of cells was preserved (coefficient 0.176, stderr 0.036, n = 54). While re-exporting the raw traces for cell01, two cells fell out of the usable range (coefficient 0.251, stderr 0.013, n = 53). While re-running with a tighter segmentation threshold for cell11, the CI narrowed by roughly a tenth (coefficient 0.184, stderr 0.039, n = 39). This is the part that will need a real statistical argument.

### Step 21: bootstrapping the CI

While checking residual autocorrelation for cell09, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.283, stderr 0.014, n = 43). While auditing the holding potential column for cell14, two cells fell out of the usable range (coefficient 0.234, stderr 0.041, n = 40). While bootstrapping the CI for cell02, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.207, stderr 0.019, n = 45).

While comparing per-cell orderings for cell22, the ordering of cells was preserved (coefficient 0.186, stderr 0.020, n = 38). While comparing per-cell orderings for cell07, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.264, stderr 0.014, n = 44). While bootstrapping the CI for cell15, two cells fell out of the usable range (coefficient 0.217, stderr 0.012, n = 38). While comparing per-cell orderings for cell18, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.176, stderr 0.012, n = 48). Flagging it so it does not get rediscovered next week.

While re-exporting the raw traces for cell14, two cells fell out of the usable range (coefficient 0.103, stderr 0.049, n = 51). While bootstrapping the CI for cell21, the CI narrowed by roughly a tenth (coefficient 0.308, stderr 0.050, n = 45). While segmenting epochs for cell15, two cells fell out of the usable range (coefficient 0.189, stderr 0.023, n = 53). While auditing the holding potential column for cell09, nothing in the figure changed at print size (coefficient 0.242, stderr 0.028, n = 45).

### Step 22: fitting the one-lag kernel

While bootstrapping the CI for cell23, the ordering of cells was preserved (coefficient 0.255, stderr 0.021, n = 53). While bootstrapping the CI for cell17, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.263, stderr 0.026, n = 47). While auditing the holding potential column for cell20, two cells fell out of the usable range (coefficient 0.263, stderr 0.028, n = 43). While auditing the holding potential column for cell01, two cells fell out of the usable range (coefficient 0.175, stderr 0.050, n = 55). Parking this until the re-segmentation lands.

```python
coefs = fit_per_cell(rows, threshold=0.45)
lo, hi = ci(coefs, seed=74)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell07    0.271  0.038   0.196  0.345  54        500
cell11    0.199  0.022   0.156  0.242  52        500
cell20    0.110  0.047   0.019  0.202  49        4000
cell08    0.103  0.050   0.005  0.201  42        4000
cell03    0.200  0.041   0.119  0.281  56        2000
cell08    0.123  0.034   0.057  0.189  42        4000
cell04    0.216  0.031   0.156  0.276  51        4000
cell13    0.271  0.037   0.198  0.343  48        2000
cell03    0.189  0.016   0.158  0.220  53        2000
cell02    0.234  0.025   0.184  0.283  49        500
cell09    0.210  0.024   0.163  0.257  38        4000
cell09    0.145  0.032   0.083  0.206  40        4000
cell21    0.309  0.045   0.222  0.397  50        500
```

### Step 23: segmenting epochs

While re-running with a tighter segmentation threshold for cell07, the CI narrowed by roughly a tenth (coefficient 0.192, stderr 0.034, n = 53). While fitting the one-lag kernel for cell04, two cells fell out of the usable range (coefficient 0.082, stderr 0.031, n = 56). While fitting the one-lag kernel for cell24, the ordering of cells was preserved (coefficient 0.168, stderr 0.048, n = 52). While fitting the one-lag kernel for cell18, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.230, stderr 0.016, n = 46). While re-exporting the raw traces for cell12, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.141, stderr 0.045, n = 49). This is the part that will need a real statistical argument.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell21    0.142  0.037   0.069  0.214  52        500
cell09    0.233  0.034   0.165  0.300  44        2000
cell01    0.239  0.026   0.189  0.289  39        2000
cell23    0.155  0.036   0.084  0.225  41        1000
cell13    0.109  0.025   0.061  0.158  44        2000
cell11    0.162  0.038   0.089  0.236  50        500
cell02    0.162  0.035   0.094  0.230  39        500
cell22    0.308  0.033   0.242  0.374  47        1000
cell17    0.106  0.015   0.077  0.135  48        2000
```

### Step 24: re-exporting the raw traces

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell05    0.165  0.045   0.076  0.254  57        1000
cell19    0.108  0.022   0.065  0.150  55        4000
cell21    0.133  0.035   0.065  0.201  56        2000
cell23    0.222  0.028   0.167  0.278  38        2000
cell07    0.134  0.027   0.081  0.186  47        1000
cell17    0.276  0.045   0.188  0.364  57        4000
cell02    0.235  0.018   0.199  0.270  38        4000
cell12    0.179  0.041   0.099  0.259  58        4000
cell16    0.174  0.042   0.091  0.257  53        500
cell18    0.277  0.022   0.233  0.321  40        500
cell18    0.251  0.018   0.216  0.287  42        2000
cell12    0.276  0.022   0.232  0.319  50        4000
```

While checking residual autocorrelation for cell22, nothing in the figure changed at print size (coefficient 0.272, stderr 0.041, n = 55). While re-exporting the raw traces for cell05, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.151, stderr 0.017, n = 48). While segmenting epochs for cell05, nothing in the figure changed at print size (coefficient 0.245, stderr 0.036, n = 56). While segmenting epochs for cell19, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.308, stderr 0.039, n = 53). While re-exporting the raw traces for cell19, nothing in the figure changed at print size (coefficient 0.219, stderr 0.032, n = 39). While segmenting epochs for cell07, the coefficient tracked epoch count more closely than duration (coefficient 0.113, stderr 0.030, n = 47).

While bootstrapping the CI for cell17, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.102, stderr 0.031, n = 58). While bootstrapping the CI for cell05, nothing in the figure changed at print size (coefficient 0.178, stderr 0.032, n = 45). While re-exporting the raw traces for cell17, the coefficient tracked epoch count more closely than duration (coefficient 0.240, stderr 0.031, n = 49). While checking residual autocorrelation for cell13, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.277, stderr 0.025, n = 46). Worth noting for the writeup, though not a result on its own.

While comparing per-cell orderings for cell23, the coefficient tracked epoch count more closely than duration (coefficient 0.172, stderr 0.049, n = 42). While re-exporting the raw traces for cell24, nothing in the figure changed at print size (coefficient 0.123, stderr 0.013, n = 44). While fitting the one-lag kernel for cell10, nothing in the figure changed at print size (coefficient 0.109, stderr 0.012, n = 53). While fitting the one-lag kernel for cell06, the estimate moved less than one standard error (coefficient 0.110, stderr 0.013, n = 40). While re-exporting the raw traces for cell11, two cells fell out of the usable range (coefficient 0.175, stderr 0.047, n = 38). While checking residual autocorrelation for cell03, the CI narrowed by roughly a tenth (coefficient 0.122, stderr 0.036, n = 48).

### Step 25: checking residual autocorrelation

While fitting the one-lag kernel for cell22, the ordering of cells was preserved (coefficient 0.256, stderr 0.012, n = 53). While fitting the one-lag kernel for cell24, the ordering of cells was preserved (coefficient 0.169, stderr 0.027, n = 57). While checking residual autocorrelation for cell14, the CI narrowed by roughly a tenth (coefficient 0.215, stderr 0.026, n = 54). While checking residual autocorrelation for cell13, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.211, stderr 0.012, n = 46). While bootstrapping the CI for cell03, nothing in the figure changed at print size (coefficient 0.280, stderr 0.047, n = 54). While re-running with a tighter segmentation threshold for cell08, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.191, stderr 0.047, n = 58). This is the part that will need a real statistical argument.

```python
coefs = fit_per_cell(rows, threshold=0.70)
lo, hi = ci(coefs, seed=8)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While checking residual autocorrelation for cell21, the estimate moved less than one standard error (coefficient 0.082, stderr 0.026, n = 58). While comparing per-cell orderings for cell13, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.192, stderr 0.026, n = 38). While re-running with a tighter segmentation threshold for cell06, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.147, stderr 0.041, n = 51).

### Step 26: re-exporting the raw traces

While re-exporting the raw traces for cell24, two cells fell out of the usable range (coefficient 0.305, stderr 0.039, n = 50). While comparing per-cell orderings for cell10, the CI narrowed by roughly a tenth (coefficient 0.175, stderr 0.028, n = 56). While fitting the one-lag kernel for cell09, the estimate moved less than one standard error (coefficient 0.305, stderr 0.030, n = 51). While checking residual autocorrelation for cell09, the ordering of cells was preserved (coefficient 0.251, stderr 0.035, n = 47). While fitting the one-lag kernel for cell09, the CI narrowed by roughly a tenth (coefficient 0.218, stderr 0.030, n = 50). While auditing the holding potential column for cell06, nothing in the figure changed at print size (coefficient 0.295, stderr 0.026, n = 39).

```python
coefs = fit_per_cell(rows, threshold=0.32)
lo, hi = ci(coefs, seed=25)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While bootstrapping the CI for cell10, the ordering of cells was preserved (coefficient 0.185, stderr 0.040, n = 45). While comparing per-cell orderings for cell05, the CI narrowed by roughly a tenth (coefficient 0.245, stderr 0.011, n = 53). While fitting the one-lag kernel for cell11, two cells fell out of the usable range (coefficient 0.176, stderr 0.015, n = 52). While re-running with a tighter segmentation threshold for cell06, two cells fell out of the usable range (coefficient 0.283, stderr 0.031, n = 50). While segmenting epochs for cell11, the CI narrowed by roughly a tenth (coefficient 0.166, stderr 0.013, n = 54). While checking residual autocorrelation for cell14, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.161, stderr 0.048, n = 52).

### Step 27: auditing the holding potential column

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell01    0.099  0.027   0.045  0.152  57        4000
cell04    0.140  0.044   0.053  0.227  41        1000
cell22    0.310  0.040   0.232  0.388  48        500
cell01    0.238  0.026   0.186  0.289  49        4000
cell23    0.081  0.028   0.025  0.137  51        4000
cell09    0.089  0.028   0.033  0.144  55        500
cell06    0.129  0.014   0.103  0.156  57        500
cell06    0.224  0.034   0.158  0.289  49        2000
```

While re-running with a tighter segmentation threshold for cell16, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.270, stderr 0.027, n = 56). While comparing per-cell orderings for cell11, the CI narrowed by roughly a tenth (coefficient 0.280, stderr 0.040, n = 57). While segmenting epochs for cell20, nothing in the figure changed at print size (coefficient 0.096, stderr 0.033, n = 47). While segmenting epochs for cell11, the coefficient tracked epoch count more closely than duration (coefficient 0.231, stderr 0.043, n = 42).

While checking residual autocorrelation for cell17, the CI narrowed by roughly a tenth (coefficient 0.108, stderr 0.022, n = 52). While re-exporting the raw traces for cell10, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.185, stderr 0.037, n = 44). While re-exporting the raw traces for cell13, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.118, stderr 0.031, n = 54). Flagging it so it does not get rediscovered next week.

### Step 28: segmenting epochs

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell01    0.173  0.028   0.119  0.227  48        2000
cell19    0.097  0.018   0.062  0.131  41        4000
cell03    0.103  0.022   0.061  0.146  57        4000
cell04    0.140  0.029   0.084  0.196  55        4000
cell16    0.129  0.045   0.041  0.216  54        2000
cell03    0.142  0.038   0.067  0.216  41        500
cell22    0.241  0.030   0.181  0.300  40        500
cell03    0.105  0.030   0.046  0.165  43        2000
cell11    0.194  0.012   0.171  0.217  39        2000
cell20    0.225  0.029   0.168  0.282  50        4000
cell15    0.152  0.030   0.094  0.210  49        1000
cell11    0.128  0.031   0.068  0.188  39        500
cell14    0.157  0.010   0.137  0.178  57        4000
```

```python
coefs = fit_per_cell(rows, threshold=0.79)
lo, hi = ci(coefs, seed=62)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell16    0.160  0.017   0.128  0.193  44        500
cell05    0.251  0.022   0.207  0.294  48        1000
cell18    0.094  0.026   0.043  0.144  47        4000
cell05    0.267  0.041   0.187  0.348  51        2000
cell24    0.226  0.019   0.188  0.263  45        2000
cell20    0.231  0.023   0.186  0.277  42        1000
cell20    0.190  0.042   0.108  0.272  44        2000
cell12    0.171  0.020   0.132  0.210  40        500
cell09    0.106  0.049   0.011  0.202  40        2000
cell18    0.201  0.047   0.109  0.292  55        2000
cell15    0.195  0.038   0.121  0.270  41        4000
```

### Step 29: fitting the one-lag kernel

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell22    0.130  0.044   0.044  0.216  50        2000
cell09    0.286  0.015   0.256  0.316  48        2000
cell11    0.274  0.014   0.246  0.301  48        4000
cell13    0.114  0.031   0.052  0.175  38        500
cell18    0.234  0.037   0.161  0.306  39        1000
cell14    0.217  0.043   0.133  0.301  40        2000
```

While auditing the holding potential column for cell12, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.283, stderr 0.026, n = 44). While fitting the one-lag kernel for cell18, two cells fell out of the usable range (coefficient 0.116, stderr 0.038, n = 57). While fitting the one-lag kernel for cell23, the estimate moved less than one standard error (coefficient 0.295, stderr 0.011, n = 44). While segmenting epochs for cell18, nothing in the figure changed at print size (coefficient 0.290, stderr 0.029, n = 40). While comparing per-cell orderings for cell01, the CI narrowed by roughly a tenth (coefficient 0.195, stderr 0.042, n = 57). This is the part that will need a real statistical argument.

### Step 30: checking residual autocorrelation

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell13    0.081  0.044   -0.005  0.167  50        2000
cell01    0.231  0.049   0.136  0.327  40        2000
cell05    0.120  0.028   0.065  0.175  38        1000
cell10    0.193  0.041   0.112  0.275  58        2000
cell17    0.252  0.048   0.157  0.347  57        2000
cell11    0.309  0.041   0.229  0.389  45        500
cell24    0.309  0.047   0.217  0.401  56        1000
cell01    0.277  0.039   0.202  0.353  44        500
cell08    0.131  0.032   0.069  0.193  46        1000
cell09    0.291  0.018   0.255  0.327  52        1000
cell16    0.160  0.035   0.091  0.230  57        4000
```

While bootstrapping the CI for cell08, the estimate moved less than one standard error (coefficient 0.134, stderr 0.018, n = 51). While re-exporting the raw traces for cell14, the ordering of cells was preserved (coefficient 0.254, stderr 0.035, n = 45). While auditing the holding potential column for cell23, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.087, stderr 0.013, n = 57).

### Step 31: segmenting epochs

While segmenting epochs for cell01, the ordering of cells was preserved (coefficient 0.164, stderr 0.028, n = 42). While re-running with a tighter segmentation threshold for cell06, the estimate moved less than one standard error (coefficient 0.223, stderr 0.039, n = 47). While re-exporting the raw traces for cell14, the coefficient tracked epoch count more closely than duration (coefficient 0.122, stderr 0.038, n = 46).

While re-exporting the raw traces for cell13, nothing in the figure changed at print size (coefficient 0.150, stderr 0.017, n = 41). While auditing the holding potential column for cell20, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.227, stderr 0.029, n = 39). While segmenting epochs for cell19, the CI narrowed by roughly a tenth (coefficient 0.080, stderr 0.013, n = 54). While checking residual autocorrelation for cell14, nothing in the figure changed at print size (coefficient 0.082, stderr 0.020, n = 40). While bootstrapping the CI for cell18, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.148, stderr 0.028, n = 56).

### Step 32: comparing per-cell orderings

While auditing the holding potential column for cell05, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.151, stderr 0.047, n = 50). While fitting the one-lag kernel for cell07, the CI narrowed by roughly a tenth (coefficient 0.124, stderr 0.028, n = 51). While comparing per-cell orderings for cell16, nothing in the figure changed at print size (coefficient 0.162, stderr 0.032, n = 43). While bootstrapping the CI for cell12, two cells fell out of the usable range (coefficient 0.295, stderr 0.025, n = 41). While segmenting epochs for cell15, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.091, stderr 0.020, n = 38). While checking residual autocorrelation for cell04, the coefficient tracked epoch count more closely than duration (coefficient 0.184, stderr 0.048, n = 55). Worth noting for the writeup, though not a result on its own.

While fitting the one-lag kernel for cell04, the CI narrowed by roughly a tenth (coefficient 0.149, stderr 0.026, n = 38). While re-exporting the raw traces for cell22, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.241, stderr 0.025, n = 44). While re-exporting the raw traces for cell20, the coefficient tracked epoch count more closely than duration (coefficient 0.155, stderr 0.038, n = 57).

```python
coefs = fit_per_cell(rows, threshold=0.60)
lo, hi = ci(coefs, seed=75)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While bootstrapping the CI for cell18, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.109, stderr 0.015, n = 44). While segmenting epochs for cell03, the coefficient tracked epoch count more closely than duration (coefficient 0.227, stderr 0.015, n = 49). While fitting the one-lag kernel for cell20, the CI narrowed by roughly a tenth (coefficient 0.101, stderr 0.034, n = 55). Worth noting for the writeup, though not a result on its own.

### Step 33: checking residual autocorrelation

```python
coefs = fit_per_cell(rows, threshold=0.46)
lo, hi = ci(coefs, seed=88)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While re-running with a tighter segmentation threshold for cell10, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.112, stderr 0.044, n = 47). While bootstrapping the CI for cell15, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.199, stderr 0.032, n = 55). While bootstrapping the CI for cell18, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.310, stderr 0.041, n = 45). While auditing the holding potential column for cell08, two cells fell out of the usable range (coefficient 0.272, stderr 0.011, n = 54).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell13    0.172  0.011   0.150  0.194  52        1000
cell04    0.155  0.041   0.075  0.234  39        500
cell06    0.110  0.017   0.076  0.143  45        500
cell03    0.120  0.012   0.097  0.144  45        2000
cell07    0.275  0.048   0.182  0.369  41        500
cell07    0.155  0.041   0.075  0.235  53        500
cell02    0.186  0.027   0.133  0.239  47        1000
cell03    0.123  0.023   0.077  0.169  58        500
cell13    0.308  0.047   0.216  0.399  41        4000
cell17    0.205  0.015   0.176  0.235  55        1000
cell22    0.240  0.028   0.186  0.294  45        2000
cell23    0.083  0.015   0.054  0.111  52        4000
cell05    0.087  0.041   0.007  0.166  43        1000
```

### Step 34: segmenting epochs

While re-exporting the raw traces for cell06, the ordering of cells was preserved (coefficient 0.174, stderr 0.048, n = 39). While checking residual autocorrelation for cell22, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.227, stderr 0.038, n = 47). While auditing the holding potential column for cell12, nothing in the figure changed at print size (coefficient 0.265, stderr 0.028, n = 52). While segmenting epochs for cell07, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.091, stderr 0.027, n = 58). While checking residual autocorrelation for cell13, the CI narrowed by roughly a tenth (coefficient 0.082, stderr 0.014, n = 39). While re-running with a tighter segmentation threshold for cell08, the ordering of cells was preserved (coefficient 0.295, stderr 0.023, n = 48). Noted and moved on; it does not change the decision.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell14    0.221  0.045   0.133  0.309  49        500
cell05    0.251  0.021   0.210  0.291  54        500
cell23    0.246  0.042   0.164  0.327  57        500
cell04    0.140  0.039   0.063  0.217  38        2000
cell20    0.153  0.024   0.105  0.201  38        2000
cell14    0.183  0.016   0.152  0.213  54        4000
cell01    0.090  0.047   -0.003  0.182  50        4000
cell08    0.206  0.041   0.126  0.286  44        2000
cell03    0.124  0.037   0.052  0.196  48        4000
cell24    0.187  0.045   0.099  0.274  47        1000
```

### Step 35: bootstrapping the CI

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell11    0.188  0.020   0.150  0.227  57        2000
cell23    0.201  0.013   0.176  0.227  44        2000
cell17    0.244  0.014   0.216  0.271  51        1000
cell11    0.153  0.044   0.067  0.239  50        1000
cell13    0.226  0.038   0.151  0.300  51        500
cell17    0.289  0.024   0.241  0.337  55        2000
cell17    0.155  0.030   0.096  0.214  49        4000
cell18    0.191  0.021   0.150  0.233  58        2000
cell13    0.150  0.012   0.127  0.173  57        2000
cell13    0.221  0.026   0.171  0.271  49        1000
cell10    0.150  0.041   0.071  0.230  45        2000
```

While comparing per-cell orderings for cell21, two cells fell out of the usable range (coefficient 0.227, stderr 0.022, n = 48). While auditing the holding potential column for cell18, the coefficient tracked epoch count more closely than duration (coefficient 0.285, stderr 0.031, n = 49). While re-running with a tighter segmentation threshold for cell07, the CI narrowed by roughly a tenth (coefficient 0.092, stderr 0.011, n = 48). While segmenting epochs for cell19, two cells fell out of the usable range (coefficient 0.299, stderr 0.030, n = 53). While segmenting epochs for cell15, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.094, stderr 0.049, n = 52). While segmenting epochs for cell20, two cells fell out of the usable range (coefficient 0.194, stderr 0.035, n = 49).

While re-exporting the raw traces for cell15, the estimate moved less than one standard error (coefficient 0.185, stderr 0.048, n = 58). While bootstrapping the CI for cell15, nothing in the figure changed at print size (coefficient 0.306, stderr 0.023, n = 44). While auditing the holding potential column for cell24, the ordering of cells was preserved (coefficient 0.212, stderr 0.019, n = 46). While re-running with a tighter segmentation threshold for cell20, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.131, stderr 0.047, n = 55). While bootstrapping the CI for cell05, the estimate moved less than one standard error (coefficient 0.203, stderr 0.040, n = 42). Noted and moved on; it does not change the decision.

While bootstrapping the CI for cell14, the ordering of cells was preserved (coefficient 0.235, stderr 0.038, n = 48). While fitting the one-lag kernel for cell11, the ordering of cells was preserved (coefficient 0.180, stderr 0.041, n = 55). While checking residual autocorrelation for cell12, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.237, stderr 0.041, n = 55). While checking residual autocorrelation for cell14, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.145, stderr 0.012, n = 44). Flagging it so it does not get rediscovered next week.

### Step 36: re-exporting the raw traces

While checking residual autocorrelation for cell16, the CI narrowed by roughly a tenth (coefficient 0.266, stderr 0.033, n = 57). While comparing per-cell orderings for cell08, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.164, stderr 0.024, n = 48). While re-exporting the raw traces for cell24, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.102, stderr 0.025, n = 48). While fitting the one-lag kernel for cell02, the coefficient tracked epoch count more closely than duration (coefficient 0.129, stderr 0.047, n = 56). While auditing the holding potential column for cell07, the ordering of cells was preserved (coefficient 0.151, stderr 0.026, n = 45).

While checking residual autocorrelation for cell02, the CI narrowed by roughly a tenth (coefficient 0.194, stderr 0.013, n = 39). While checking residual autocorrelation for cell16, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.242, stderr 0.038, n = 46). While checking residual autocorrelation for cell02, the estimate moved less than one standard error (coefficient 0.229, stderr 0.037, n = 57).

While checking residual autocorrelation for cell02, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.275, stderr 0.036, n = 45). While bootstrapping the CI for cell03, nothing in the figure changed at print size (coefficient 0.101, stderr 0.037, n = 52). While re-running with a tighter segmentation threshold for cell15, two cells fell out of the usable range (coefficient 0.231, stderr 0.014, n = 57). While bootstrapping the CI for cell09, the CI narrowed by roughly a tenth (coefficient 0.194, stderr 0.034, n = 50). While bootstrapping the CI for cell06, nothing in the figure changed at print size (coefficient 0.283, stderr 0.032, n = 49).

While segmenting epochs for cell18, the coefficient tracked epoch count more closely than duration (coefficient 0.112, stderr 0.015, n = 39). While checking residual autocorrelation for cell08, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.111, stderr 0.027, n = 38). While re-exporting the raw traces for cell14, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.195, stderr 0.023, n = 53). While fitting the one-lag kernel for cell10, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.247, stderr 0.027, n = 42). While re-exporting the raw traces for cell11, nothing in the figure changed at print size (coefficient 0.278, stderr 0.030, n = 50). While bootstrapping the CI for cell15, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.087, stderr 0.011, n = 47). This is the part that will need a real statistical argument.

### Step 37: comparing per-cell orderings

While auditing the holding potential column for cell12, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.221, stderr 0.038, n = 56). While auditing the holding potential column for cell16, nothing in the figure changed at print size (coefficient 0.217, stderr 0.020, n = 47). While comparing per-cell orderings for cell24, the coefficient tracked epoch count more closely than duration (coefficient 0.300, stderr 0.021, n = 39). While re-exporting the raw traces for cell05, the coefficient tracked epoch count more closely than duration (coefficient 0.174, stderr 0.034, n = 49).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell12    0.193  0.044   0.107  0.279  50        2000
cell11    0.262  0.025   0.213  0.311  55        4000
cell24    0.112  0.012   0.088  0.136  43        4000
cell20    0.258  0.041   0.177  0.339  52        1000
cell24    0.161  0.031   0.100  0.222  45        2000
cell16    0.180  0.034   0.112  0.248  54        500
cell01    0.100  0.044   0.015  0.186  46        2000
cell19    0.104  0.023   0.059  0.149  38        1000
cell21    0.296  0.018   0.261  0.331  46        1000
cell22    0.094  0.036   0.023  0.165  47        4000
cell19    0.128  0.038   0.054  0.202  41        4000
```

### Step 38: re-running with a tighter segmentation threshold

While re-exporting the raw traces for cell18, the coefficient tracked epoch count more closely than duration (coefficient 0.298, stderr 0.019, n = 47). While re-running with a tighter segmentation threshold for cell07, nothing in the figure changed at print size (coefficient 0.245, stderr 0.016, n = 47). While re-running with a tighter segmentation threshold for cell07, nothing in the figure changed at print size (coefficient 0.116, stderr 0.038, n = 55).

While comparing per-cell orderings for cell23, the coefficient tracked epoch count more closely than duration (coefficient 0.286, stderr 0.045, n = 58). While re-running with a tighter segmentation threshold for cell19, the ordering of cells was preserved (coefficient 0.112, stderr 0.025, n = 58). While comparing per-cell orderings for cell24, the CI narrowed by roughly a tenth (coefficient 0.087, stderr 0.046, n = 53). While comparing per-cell orderings for cell09, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.253, stderr 0.014, n = 51). While comparing per-cell orderings for cell12, the ordering of cells was preserved (coefficient 0.215, stderr 0.023, n = 52). While auditing the holding potential column for cell18, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.247, stderr 0.013, n = 41).

While re-running with a tighter segmentation threshold for cell03, two cells fell out of the usable range (coefficient 0.246, stderr 0.024, n = 44). While re-running with a tighter segmentation threshold for cell11, nothing in the figure changed at print size (coefficient 0.222, stderr 0.041, n = 45). While bootstrapping the CI for cell03, the estimate moved less than one standard error (coefficient 0.108, stderr 0.037, n = 49).

While comparing per-cell orderings for cell02, nothing in the figure changed at print size (coefficient 0.281, stderr 0.038, n = 57). While auditing the holding potential column for cell12, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.145, stderr 0.034, n = 56). While bootstrapping the CI for cell06, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.288, stderr 0.016, n = 46). While segmenting epochs for cell17, nothing in the figure changed at print size (coefficient 0.293, stderr 0.049, n = 55). While checking residual autocorrelation for cell14, nothing in the figure changed at print size (coefficient 0.113, stderr 0.027, n = 42). Noted and moved on; it does not change the decision.

### Step 39: checking residual autocorrelation

While re-exporting the raw traces for cell10, the ordering of cells was preserved (coefficient 0.244, stderr 0.014, n = 58). While re-running with a tighter segmentation threshold for cell01, the coefficient tracked epoch count more closely than duration (coefficient 0.293, stderr 0.047, n = 52). While auditing the holding potential column for cell01, two cells fell out of the usable range (coefficient 0.120, stderr 0.030, n = 49). While bootstrapping the CI for cell03, two cells fell out of the usable range (coefficient 0.236, stderr 0.031, n = 43).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell07    0.293  0.032   0.230  0.356  58        2000
cell05    0.170  0.022   0.127  0.214  54        1000
cell12    0.115  0.044   0.029  0.200  49        4000
cell02    0.154  0.043   0.069  0.239  50        1000
cell14    0.187  0.015   0.158  0.216  54        4000
cell21    0.231  0.029   0.173  0.288  53        500
cell07    0.122  0.050   0.025  0.219  47        500
cell24    0.125  0.025   0.075  0.174  40        4000
```

While checking residual autocorrelation for cell16, nothing in the figure changed at print size (coefficient 0.178, stderr 0.038, n = 49). While bootstrapping the CI for cell19, two cells fell out of the usable range (coefficient 0.302, stderr 0.019, n = 40). While re-exporting the raw traces for cell12, the ordering of cells was preserved (coefficient 0.088, stderr 0.025, n = 38). While re-exporting the raw traces for cell22, two cells fell out of the usable range (coefficient 0.119, stderr 0.032, n = 52). While checking residual autocorrelation for cell05, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.083, stderr 0.032, n = 56). While re-exporting the raw traces for cell09, two cells fell out of the usable range (coefficient 0.299, stderr 0.033, n = 43).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell02    0.206  0.022   0.162  0.250  38        1000
cell04    0.169  0.019   0.133  0.206  57        1000
cell18    0.285  0.043   0.201  0.370  43        2000
cell24    0.193  0.038   0.118  0.268  46        1000
cell11    0.100  0.043   0.015  0.186  49        2000
cell10    0.137  0.024   0.089  0.185  54        2000
cell01    0.082  0.032   0.018  0.145  47        2000
cell11    0.117  0.027   0.064  0.170  42        4000
cell08    0.281  0.035   0.212  0.350  49        1000
```

### Step 40: re-running with a tighter segmentation threshold

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell20    0.137  0.041   0.058  0.217  56        500
cell23    0.254  0.029   0.197  0.310  55        4000
cell17    0.112  0.020   0.073  0.150  44        4000
cell23    0.110  0.033   0.046  0.175  56        2000
cell02    0.249  0.012   0.224  0.273  56        500
cell07    0.241  0.048   0.147  0.335  50        1000
cell11    0.188  0.024   0.140  0.235  38        4000
cell19    0.084  0.035   0.015  0.153  55        4000
cell17    0.122  0.034   0.055  0.189  54        500
cell07    0.111  0.017   0.078  0.143  43        1000
cell03    0.301  0.030   0.242  0.360  57        2000
cell18    0.099  0.029   0.042  0.156  38        2000
```

While checking residual autocorrelation for cell19, the coefficient tracked epoch count more closely than duration (coefficient 0.174, stderr 0.029, n = 53). While segmenting epochs for cell07, the coefficient tracked epoch count more closely than duration (coefficient 0.092, stderr 0.049, n = 45). While segmenting epochs for cell08, the coefficient tracked epoch count more closely than duration (coefficient 0.164, stderr 0.044, n = 38). While segmenting epochs for cell15, the CI narrowed by roughly a tenth (coefficient 0.237, stderr 0.019, n = 40). While re-running with a tighter segmentation threshold for cell01, the coefficient tracked epoch count more closely than duration (coefficient 0.252, stderr 0.031, n = 53).

### Step 41: re-exporting the raw traces

```python
coefs = fit_per_cell(rows, threshold=0.66)
lo, hi = ci(coefs, seed=51)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While bootstrapping the CI for cell01, nothing in the figure changed at print size (coefficient 0.153, stderr 0.019, n = 45). While fitting the one-lag kernel for cell12, the ordering of cells was preserved (coefficient 0.306, stderr 0.014, n = 47). While segmenting epochs for cell06, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.107, stderr 0.023, n = 40). While fitting the one-lag kernel for cell16, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.162, stderr 0.028, n = 38). While bootstrapping the CI for cell14, the CI narrowed by roughly a tenth (coefficient 0.178, stderr 0.038, n = 38).

While checking residual autocorrelation for cell09, the CI narrowed by roughly a tenth (coefficient 0.132, stderr 0.032, n = 44). While re-running with a tighter segmentation threshold for cell05, the ordering of cells was preserved (coefficient 0.132, stderr 0.034, n = 43). While re-running with a tighter segmentation threshold for cell16, nothing in the figure changed at print size (coefficient 0.174, stderr 0.041, n = 45).

While re-running with a tighter segmentation threshold for cell15, the estimate moved less than one standard error (coefficient 0.096, stderr 0.011, n = 38). While bootstrapping the CI for cell18, the estimate moved less than one standard error (coefficient 0.299, stderr 0.042, n = 46). While re-exporting the raw traces for cell08, the ordering of cells was preserved (coefficient 0.090, stderr 0.023, n = 55). While checking residual autocorrelation for cell02, the estimate moved less than one standard error (coefficient 0.267, stderr 0.018, n = 42). While checking residual autocorrelation for cell06, two cells fell out of the usable range (coefficient 0.165, stderr 0.026, n = 53). While auditing the holding potential column for cell06, nothing in the figure changed at print size (coefficient 0.247, stderr 0.010, n = 49). Worth noting for the writeup, though not a result on its own.

### Step 42: comparing per-cell orderings

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell12    0.153  0.044   0.066  0.240  39        4000
cell04    0.202  0.037   0.129  0.276  49        2000
cell07    0.179  0.030   0.120  0.238  38        500
cell13    0.260  0.031   0.199  0.320  56        4000
cell05    0.119  0.043   0.034  0.203  50        2000
cell04    0.096  0.017   0.062  0.130  45        1000
cell14    0.215  0.014   0.188  0.242  50        1000
cell20    0.095  0.045   0.006  0.183  56        500
cell05    0.137  0.024   0.091  0.183  49        1000
cell16    0.207  0.025   0.159  0.256  39        4000
cell03    0.306  0.040   0.227  0.385  42        4000
```

While auditing the holding potential column for cell13, the CI narrowed by roughly a tenth (coefficient 0.237, stderr 0.040, n = 43). While comparing per-cell orderings for cell17, the estimate moved less than one standard error (coefficient 0.246, stderr 0.028, n = 40). While re-running with a tighter segmentation threshold for cell13, the ordering of cells was preserved (coefficient 0.179, stderr 0.016, n = 42). While checking residual autocorrelation for cell20, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.229, stderr 0.032, n = 52). While segmenting epochs for cell04, nothing in the figure changed at print size (coefficient 0.148, stderr 0.012, n = 58). While comparing per-cell orderings for cell15, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.292, stderr 0.039, n = 47).

While segmenting epochs for cell09, the CI narrowed by roughly a tenth (coefficient 0.154, stderr 0.021, n = 58). While comparing per-cell orderings for cell10, the CI narrowed by roughly a tenth (coefficient 0.126, stderr 0.037, n = 40). While re-exporting the raw traces for cell14, the CI narrowed by roughly a tenth (coefficient 0.279, stderr 0.014, n = 58). While auditing the holding potential column for cell12, the coefficient tracked epoch count more closely than duration (coefficient 0.271, stderr 0.048, n = 48). While re-exporting the raw traces for cell06, the CI narrowed by roughly a tenth (coefficient 0.310, stderr 0.045, n = 47). While segmenting epochs for cell02, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.112, stderr 0.035, n = 55). Noted and moved on; it does not change the decision.

```python
coefs = fit_per_cell(rows, threshold=0.77)
lo, hi = ci(coefs, seed=8)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

