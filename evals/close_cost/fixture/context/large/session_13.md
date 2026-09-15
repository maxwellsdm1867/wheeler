# Prior session 13 of 20

Transcript of an earlier working session on the history-kernel analysis.

### Step 1: fitting the one-lag kernel

While bootstrapping the CI for cell23, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.198, stderr 0.042, n = 53). While re-running with a tighter segmentation threshold for cell20, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.247, stderr 0.035, n = 58). While comparing per-cell orderings for cell02, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.262, stderr 0.042, n = 40). While bootstrapping the CI for cell16, the CI narrowed by roughly a tenth (coefficient 0.300, stderr 0.043, n = 54). While re-exporting the raw traces for cell13, the estimate moved less than one standard error (coefficient 0.244, stderr 0.032, n = 53). This is the part that will need a real statistical argument.

While comparing per-cell orderings for cell05, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.269, stderr 0.023, n = 38). While checking residual autocorrelation for cell11, the CI narrowed by roughly a tenth (coefficient 0.249, stderr 0.042, n = 45). While fitting the one-lag kernel for cell14, the estimate moved less than one standard error (coefficient 0.257, stderr 0.011, n = 56). While checking residual autocorrelation for cell10, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.214, stderr 0.021, n = 50).

While segmenting epochs for cell19, the estimate moved less than one standard error (coefficient 0.284, stderr 0.035, n = 51). While re-exporting the raw traces for cell08, the coefficient tracked epoch count more closely than duration (coefficient 0.120, stderr 0.014, n = 55). While comparing per-cell orderings for cell16, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.102, stderr 0.030, n = 43).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell22    0.189  0.044   0.103  0.276  45        2000
cell20    0.160  0.049   0.064  0.256  56        500
cell14    0.230  0.027   0.176  0.283  38        500
cell14    0.290  0.025   0.241  0.339  38        4000
cell12    0.217  0.034   0.151  0.283  41        1000
cell16    0.272  0.020   0.233  0.311  45        2000
cell16    0.120  0.039   0.044  0.196  49        1000
cell20    0.125  0.029   0.068  0.182  48        2000
cell22    0.113  0.030   0.054  0.172  49        4000
cell04    0.110  0.040   0.032  0.188  52        4000
cell02    0.101  0.047   0.008  0.193  38        1000
cell12    0.275  0.019   0.238  0.311  56        500
```

### Step 2: auditing the holding potential column

```python
coefs = fit_per_cell(rows, threshold=0.34)
lo, hi = ci(coefs, seed=43)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```python
coefs = fit_per_cell(rows, threshold=0.75)
lo, hi = ci(coefs, seed=98)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 3: bootstrapping the CI

While segmenting epochs for cell18, nothing in the figure changed at print size (coefficient 0.275, stderr 0.023, n = 50). While segmenting epochs for cell01, the CI narrowed by roughly a tenth (coefficient 0.152, stderr 0.044, n = 52). While re-exporting the raw traces for cell15, the coefficient tracked epoch count more closely than duration (coefficient 0.201, stderr 0.034, n = 41). While auditing the holding potential column for cell21, the CI narrowed by roughly a tenth (coefficient 0.205, stderr 0.027, n = 39). While auditing the holding potential column for cell10, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.096, stderr 0.043, n = 57).

While fitting the one-lag kernel for cell07, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.258, stderr 0.011, n = 58). While auditing the holding potential column for cell01, nothing in the figure changed at print size (coefficient 0.309, stderr 0.012, n = 58). While re-exporting the raw traces for cell21, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.110, stderr 0.027, n = 58). While re-exporting the raw traces for cell06, the CI narrowed by roughly a tenth (coefficient 0.218, stderr 0.028, n = 50).

While re-running with a tighter segmentation threshold for cell15, the coefficient tracked epoch count more closely than duration (coefficient 0.102, stderr 0.027, n = 57). While fitting the one-lag kernel for cell21, two cells fell out of the usable range (coefficient 0.263, stderr 0.036, n = 52). While re-running with a tighter segmentation threshold for cell23, the coefficient tracked epoch count more closely than duration (coefficient 0.285, stderr 0.046, n = 53). While auditing the holding potential column for cell11, the ordering of cells was preserved (coefficient 0.117, stderr 0.049, n = 54). While checking residual autocorrelation for cell12, the coefficient tracked epoch count more closely than duration (coefficient 0.170, stderr 0.040, n = 52).

### Step 4: bootstrapping the CI

While auditing the holding potential column for cell24, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.248, stderr 0.039, n = 57). While fitting the one-lag kernel for cell10, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.112, stderr 0.032, n = 45). While bootstrapping the CI for cell10, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.090, stderr 0.038, n = 57).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell09    0.192  0.044   0.107  0.278  54        2000
cell08    0.278  0.011   0.256  0.300  45        500
cell05    0.285  0.018   0.249  0.321  50        1000
cell17    0.100  0.025   0.052  0.149  44        500
cell11    0.303  0.020   0.264  0.342  57        1000
cell17    0.300  0.023   0.255  0.345  50        500
cell14    0.302  0.045   0.214  0.391  55        4000
cell09    0.191  0.039   0.115  0.268  49        500
cell02    0.127  0.047   0.035  0.219  42        1000
cell17    0.130  0.012   0.105  0.154  41        1000
cell08    0.165  0.022   0.122  0.209  48        2000
```

### Step 5: comparing per-cell orderings

While segmenting epochs for cell17, the coefficient tracked epoch count more closely than duration (coefficient 0.226, stderr 0.033, n = 51). While auditing the holding potential column for cell23, the estimate moved less than one standard error (coefficient 0.113, stderr 0.024, n = 57). While checking residual autocorrelation for cell24, the coefficient tracked epoch count more closely than duration (coefficient 0.274, stderr 0.047, n = 44).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell04    0.134  0.041   0.053  0.214  38        2000
cell23    0.223  0.040   0.145  0.300  41        2000
cell03    0.259  0.027   0.205  0.313  38        500
cell07    0.241  0.027   0.188  0.294  44        500
cell05    0.176  0.047   0.085  0.267  46        500
cell11    0.258  0.013   0.232  0.285  53        2000
cell19    0.088  0.027   0.034  0.141  54        4000
cell02    0.196  0.027   0.142  0.250  46        500
cell21    0.247  0.028   0.192  0.301  53        4000
cell09    0.263  0.044   0.176  0.350  54        4000
cell02    0.104  0.018   0.070  0.139  45        1000
cell21    0.196  0.023   0.151  0.241  55        1000
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell20    0.260  0.046   0.171  0.350  42        1000
cell02    0.134  0.028   0.078  0.189  38        500
cell09    0.222  0.026   0.170  0.273  58        500
cell12    0.202  0.035   0.133  0.272  56        4000
cell13    0.190  0.041   0.110  0.271  51        500
cell19    0.109  0.014   0.081  0.137  49        4000
cell16    0.157  0.047   0.065  0.248  40        2000
cell01    0.257  0.027   0.205  0.309  55        500
```

### Step 6: checking residual autocorrelation

While fitting the one-lag kernel for cell22, nothing in the figure changed at print size (coefficient 0.104, stderr 0.047, n = 58). While checking residual autocorrelation for cell01, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.100, stderr 0.022, n = 57). While comparing per-cell orderings for cell09, nothing in the figure changed at print size (coefficient 0.181, stderr 0.033, n = 47). While checking residual autocorrelation for cell19, the coefficient tracked epoch count more closely than duration (coefficient 0.147, stderr 0.025, n = 54). While segmenting epochs for cell17, two cells fell out of the usable range (coefficient 0.228, stderr 0.029, n = 48). Worth noting for the writeup, though not a result on its own.

While bootstrapping the CI for cell16, nothing in the figure changed at print size (coefficient 0.193, stderr 0.027, n = 46). While fitting the one-lag kernel for cell09, the ordering of cells was preserved (coefficient 0.146, stderr 0.020, n = 42). While re-running with a tighter segmentation threshold for cell03, the estimate moved less than one standard error (coefficient 0.129, stderr 0.023, n = 39). While auditing the holding potential column for cell15, the coefficient tracked epoch count more closely than duration (coefficient 0.153, stderr 0.044, n = 40). While re-running with a tighter segmentation threshold for cell07, two cells fell out of the usable range (coefficient 0.132, stderr 0.015, n = 51). While checking residual autocorrelation for cell06, two cells fell out of the usable range (coefficient 0.169, stderr 0.039, n = 56).

While bootstrapping the CI for cell09, nothing in the figure changed at print size (coefficient 0.280, stderr 0.017, n = 38). While comparing per-cell orderings for cell21, nothing in the figure changed at print size (coefficient 0.240, stderr 0.045, n = 40). While bootstrapping the CI for cell24, the estimate moved less than one standard error (coefficient 0.114, stderr 0.031, n = 43). While comparing per-cell orderings for cell21, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.190, stderr 0.029, n = 50). While checking residual autocorrelation for cell04, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.211, stderr 0.046, n = 46).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell01    0.155  0.028   0.100  0.211  56        2000
cell22    0.134  0.013   0.108  0.159  39        4000
cell23    0.146  0.044   0.060  0.232  49        4000
cell05    0.116  0.032   0.052  0.179  48        500
cell13    0.252  0.045   0.164  0.339  58        2000
cell20    0.168  0.046   0.077  0.259  55        500
cell04    0.151  0.017   0.117  0.185  56        4000
cell21    0.101  0.022   0.058  0.144  55        1000
cell19    0.100  0.012   0.077  0.122  56        2000
```

### Step 7: comparing per-cell orderings

```python
coefs = fit_per_cell(rows, threshold=0.40)
lo, hi = ci(coefs, seed=68)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell04    0.239  0.015   0.209  0.269  38        1000
cell04    0.218  0.035   0.150  0.287  49        2000
cell13    0.112  0.025   0.062  0.161  44        500
cell23    0.186  0.034   0.120  0.252  48        500
cell11    0.086  0.020   0.046  0.126  53        500
cell20    0.272  0.015   0.242  0.302  45        2000
cell14    0.270  0.048   0.176  0.364  54        4000
cell09    0.216  0.031   0.154  0.277  49        2000
```

### Step 8: fitting the one-lag kernel

While auditing the holding potential column for cell08, the estimate moved less than one standard error (coefficient 0.087, stderr 0.038, n = 44). While checking residual autocorrelation for cell21, the CI narrowed by roughly a tenth (coefficient 0.161, stderr 0.029, n = 48). While bootstrapping the CI for cell16, two cells fell out of the usable range (coefficient 0.222, stderr 0.042, n = 55). While auditing the holding potential column for cell18, two cells fell out of the usable range (coefficient 0.153, stderr 0.018, n = 49). While bootstrapping the CI for cell14, the coefficient tracked epoch count more closely than duration (coefficient 0.280, stderr 0.010, n = 57).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell23    0.081  0.010   0.062  0.101  51        2000
cell05    0.248  0.049   0.153  0.343  50        2000
cell11    0.273  0.012   0.249  0.296  42        2000
cell11    0.196  0.031   0.135  0.256  48        500
cell01    0.214  0.024   0.168  0.261  38        1000
cell23    0.279  0.029   0.223  0.335  38        4000
cell16    0.105  0.010   0.085  0.125  53        2000
```

```python
coefs = fit_per_cell(rows, threshold=0.40)
lo, hi = ci(coefs, seed=81)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 9: fitting the one-lag kernel

While re-running with a tighter segmentation threshold for cell15, nothing in the figure changed at print size (coefficient 0.241, stderr 0.014, n = 49). While auditing the holding potential column for cell12, the coefficient tracked epoch count more closely than duration (coefficient 0.278, stderr 0.028, n = 47). While segmenting epochs for cell23, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.089, stderr 0.027, n = 38). While re-running with a tighter segmentation threshold for cell17, the CI narrowed by roughly a tenth (coefficient 0.268, stderr 0.039, n = 42).

While re-running with a tighter segmentation threshold for cell24, two cells fell out of the usable range (coefficient 0.169, stderr 0.034, n = 50). While fitting the one-lag kernel for cell12, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.189, stderr 0.044, n = 49). While re-exporting the raw traces for cell11, nothing in the figure changed at print size (coefficient 0.116, stderr 0.016, n = 43). While re-running with a tighter segmentation threshold for cell14, the CI narrowed by roughly a tenth (coefficient 0.101, stderr 0.025, n = 55). While bootstrapping the CI for cell15, the estimate moved less than one standard error (coefficient 0.200, stderr 0.017, n = 52). While segmenting epochs for cell24, the ordering of cells was preserved (coefficient 0.175, stderr 0.032, n = 46).

While comparing per-cell orderings for cell15, the estimate moved less than one standard error (coefficient 0.255, stderr 0.036, n = 46). While auditing the holding potential column for cell05, the ordering of cells was preserved (coefficient 0.253, stderr 0.039, n = 41). While bootstrapping the CI for cell16, the coefficient tracked epoch count more closely than duration (coefficient 0.160, stderr 0.046, n = 38). While segmenting epochs for cell03, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.217, stderr 0.012, n = 52). While auditing the holding potential column for cell19, the estimate moved less than one standard error (coefficient 0.132, stderr 0.043, n = 50).

### Step 10: re-exporting the raw traces

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell12    0.243  0.025   0.194  0.292  49        2000
cell12    0.140  0.046   0.050  0.229  43        500
cell13    0.090  0.044   0.004  0.177  42        2000
cell08    0.287  0.048   0.193  0.380  43        1000
cell06    0.147  0.017   0.113  0.181  53        2000
cell06    0.105  0.028   0.050  0.159  52        2000
cell16    0.177  0.038   0.102  0.253  38        500
cell08    0.113  0.020   0.073  0.153  44        500
cell03    0.269  0.035   0.200  0.338  46        4000
```

While segmenting epochs for cell11, the estimate moved less than one standard error (coefficient 0.118, stderr 0.029, n = 44). While auditing the holding potential column for cell19, nothing in the figure changed at print size (coefficient 0.104, stderr 0.014, n = 41). While auditing the holding potential column for cell13, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.141, stderr 0.036, n = 39). While bootstrapping the CI for cell02, the CI narrowed by roughly a tenth (coefficient 0.253, stderr 0.040, n = 44). While fitting the one-lag kernel for cell19, the ordering of cells was preserved (coefficient 0.155, stderr 0.016, n = 54).

While re-running with a tighter segmentation threshold for cell18, nothing in the figure changed at print size (coefficient 0.200, stderr 0.039, n = 54). While auditing the holding potential column for cell06, the ordering of cells was preserved (coefficient 0.192, stderr 0.017, n = 39). While checking residual autocorrelation for cell06, two cells fell out of the usable range (coefficient 0.279, stderr 0.019, n = 52). Parking this until the re-segmentation lands.

### Step 11: re-exporting the raw traces

```python
coefs = fit_per_cell(rows, threshold=0.72)
lo, hi = ci(coefs, seed=42)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell03    0.197  0.025   0.149  0.245  41        4000
cell01    0.297  0.029   0.240  0.353  46        1000
cell10    0.156  0.025   0.107  0.204  44        1000
cell03    0.222  0.041   0.141  0.302  55        500
cell17    0.166  0.017   0.133  0.199  41        2000
cell09    0.288  0.027   0.235  0.340  43        500
cell15    0.108  0.023   0.062  0.154  56        500
cell09    0.186  0.047   0.093  0.278  50        2000
cell10    0.261  0.049   0.165  0.358  55        2000
cell14    0.142  0.050   0.045  0.240  51        4000
cell18    0.118  0.047   0.025  0.210  44        1000
```

While re-exporting the raw traces for cell15, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.175, stderr 0.017, n = 58). While comparing per-cell orderings for cell16, nothing in the figure changed at print size (coefficient 0.285, stderr 0.033, n = 57). While auditing the holding potential column for cell10, the CI narrowed by roughly a tenth (coefficient 0.153, stderr 0.042, n = 43). While auditing the holding potential column for cell05, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.253, stderr 0.047, n = 50). While segmenting epochs for cell14, the coefficient tracked epoch count more closely than duration (coefficient 0.089, stderr 0.018, n = 54).

### Step 12: re-running with a tighter segmentation threshold

While checking residual autocorrelation for cell20, the coefficient tracked epoch count more closely than duration (coefficient 0.290, stderr 0.020, n = 56). While auditing the holding potential column for cell19, the estimate moved less than one standard error (coefficient 0.279, stderr 0.025, n = 56). While checking residual autocorrelation for cell24, two cells fell out of the usable range (coefficient 0.291, stderr 0.022, n = 58). While re-running with a tighter segmentation threshold for cell12, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.227, stderr 0.034, n = 38).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell04    0.136  0.014   0.109  0.163  42        4000
cell09    0.083  0.016   0.053  0.114  47        500
cell05    0.194  0.035   0.125  0.263  44        2000
cell20    0.233  0.029   0.176  0.289  38        500
cell02    0.245  0.029   0.188  0.301  39        2000
cell06    0.178  0.034   0.111  0.245  39        2000
cell12    0.239  0.040   0.161  0.317  48        1000
cell17    0.158  0.048   0.064  0.253  52        4000
cell23    0.299  0.030   0.241  0.357  46        500
cell05    0.182  0.039   0.106  0.257  52        1000
cell05    0.128  0.021   0.087  0.169  44        2000
cell06    0.174  0.041   0.093  0.256  55        2000
```

While comparing per-cell orderings for cell07, nothing in the figure changed at print size (coefficient 0.168, stderr 0.023, n = 40). While re-exporting the raw traces for cell08, two cells fell out of the usable range (coefficient 0.269, stderr 0.031, n = 47). While fitting the one-lag kernel for cell22, two cells fell out of the usable range (coefficient 0.284, stderr 0.016, n = 55).

```python
coefs = fit_per_cell(rows, threshold=0.47)
lo, hi = ci(coefs, seed=77)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 13: bootstrapping the CI

```python
coefs = fit_per_cell(rows, threshold=0.49)
lo, hi = ci(coefs, seed=33)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While comparing per-cell orderings for cell03, the estimate moved less than one standard error (coefficient 0.271, stderr 0.024, n = 50). While checking residual autocorrelation for cell04, two cells fell out of the usable range (coefficient 0.176, stderr 0.048, n = 47). While comparing per-cell orderings for cell20, nothing in the figure changed at print size (coefficient 0.116, stderr 0.013, n = 44). While checking residual autocorrelation for cell04, two cells fell out of the usable range (coefficient 0.088, stderr 0.023, n = 57).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell08    0.289  0.016   0.258  0.321  58        1000
cell01    0.094  0.050   -0.003  0.191  43        1000
cell05    0.162  0.015   0.133  0.191  49        1000
cell15    0.292  0.015   0.263  0.322  40        1000
cell02    0.153  0.041   0.072  0.233  52        1000
cell19    0.248  0.042   0.165  0.330  44        4000
cell16    0.169  0.017   0.135  0.203  54        1000
cell09    0.133  0.017   0.099  0.167  53        4000
cell01    0.112  0.024   0.065  0.158  52        2000
cell09    0.150  0.025   0.101  0.199  53        4000
cell17    0.216  0.018   0.180  0.252  44        4000
cell13    0.182  0.027   0.129  0.236  53        500
cell11    0.085  0.036   0.013  0.157  45        4000
```

### Step 14: auditing the holding potential column

While checking residual autocorrelation for cell15, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.154, stderr 0.027, n = 52). While segmenting epochs for cell20, the coefficient tracked epoch count more closely than duration (coefficient 0.167, stderr 0.024, n = 54). While segmenting epochs for cell19, nothing in the figure changed at print size (coefficient 0.228, stderr 0.041, n = 42). While comparing per-cell orderings for cell02, the CI narrowed by roughly a tenth (coefficient 0.277, stderr 0.017, n = 53).

While comparing per-cell orderings for cell19, the estimate moved less than one standard error (coefficient 0.154, stderr 0.028, n = 56). While bootstrapping the CI for cell19, nothing in the figure changed at print size (coefficient 0.214, stderr 0.050, n = 55). While re-exporting the raw traces for cell17, nothing in the figure changed at print size (coefficient 0.125, stderr 0.016, n = 51).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell08    0.300  0.014   0.273  0.327  44        500
cell03    0.123  0.034   0.056  0.190  46        4000
cell20    0.166  0.032   0.103  0.230  57        4000
cell05    0.236  0.044   0.150  0.321  43        500
cell09    0.132  0.043   0.048  0.217  49        4000
cell05    0.221  0.042   0.139  0.304  43        2000
cell24    0.249  0.024   0.202  0.296  46        4000
cell14    0.143  0.028   0.089  0.197  48        2000
```

### Step 15: auditing the holding potential column

While checking residual autocorrelation for cell12, two cells fell out of the usable range (coefficient 0.284, stderr 0.024, n = 49). While bootstrapping the CI for cell16, the ordering of cells was preserved (coefficient 0.232, stderr 0.018, n = 49). While re-running with a tighter segmentation threshold for cell02, two cells fell out of the usable range (coefficient 0.272, stderr 0.025, n = 44). While comparing per-cell orderings for cell13, the estimate moved less than one standard error (coefficient 0.198, stderr 0.028, n = 42). While re-running with a tighter segmentation threshold for cell14, the ordering of cells was preserved (coefficient 0.096, stderr 0.032, n = 48). While re-running with a tighter segmentation threshold for cell06, the estimate moved less than one standard error (coefficient 0.141, stderr 0.044, n = 58).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell10    0.187  0.031   0.126  0.248  40        1000
cell12    0.213  0.022   0.169  0.257  40        1000
cell19    0.083  0.035   0.013  0.152  50        500
cell10    0.198  0.012   0.175  0.221  46        2000
cell16    0.279  0.047   0.188  0.371  48        1000
cell09    0.102  0.022   0.060  0.145  41        500
cell16    0.202  0.050   0.104  0.300  43        1000
cell04    0.128  0.034   0.061  0.194  45        1000
cell08    0.252  0.027   0.199  0.305  47        1000
cell05    0.304  0.018   0.268  0.340  38        1000
cell14    0.264  0.045   0.177  0.352  42        4000
cell21    0.118  0.012   0.094  0.142  53        1000
cell07    0.136  0.043   0.051  0.222  40        500
```

```python
coefs = fit_per_cell(rows, threshold=0.63)
lo, hi = ci(coefs, seed=97)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While auditing the holding potential column for cell15, the ordering of cells was preserved (coefficient 0.291, stderr 0.016, n = 46). While re-exporting the raw traces for cell09, the ordering of cells was preserved (coefficient 0.160, stderr 0.010, n = 45). While comparing per-cell orderings for cell24, nothing in the figure changed at print size (coefficient 0.159, stderr 0.039, n = 44). While re-running with a tighter segmentation threshold for cell23, nothing in the figure changed at print size (coefficient 0.209, stderr 0.040, n = 54). While checking residual autocorrelation for cell14, the estimate moved less than one standard error (coefficient 0.166, stderr 0.037, n = 50). Parking this until the re-segmentation lands.

### Step 16: comparing per-cell orderings

While re-running with a tighter segmentation threshold for cell15, two cells fell out of the usable range (coefficient 0.266, stderr 0.015, n = 54). While bootstrapping the CI for cell13, the coefficient tracked epoch count more closely than duration (coefficient 0.273, stderr 0.032, n = 49). While bootstrapping the CI for cell08, the estimate moved less than one standard error (coefficient 0.202, stderr 0.047, n = 40). While re-exporting the raw traces for cell19, the ordering of cells was preserved (coefficient 0.213, stderr 0.022, n = 50).

While fitting the one-lag kernel for cell01, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.249, stderr 0.041, n = 48). While auditing the holding potential column for cell01, two cells fell out of the usable range (coefficient 0.211, stderr 0.037, n = 55). While auditing the holding potential column for cell06, two cells fell out of the usable range (coefficient 0.250, stderr 0.039, n = 51). While segmenting epochs for cell23, the estimate moved less than one standard error (coefficient 0.299, stderr 0.037, n = 55). While re-running with a tighter segmentation threshold for cell15, the CI narrowed by roughly a tenth (coefficient 0.145, stderr 0.047, n = 42). While bootstrapping the CI for cell06, the ordering of cells was preserved (coefficient 0.081, stderr 0.017, n = 45).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell05    0.250  0.049   0.155  0.346  46        4000
cell21    0.123  0.036   0.052  0.194  45        2000
cell19    0.152  0.040   0.073  0.232  56        1000
cell02    0.300  0.035   0.231  0.370  52        4000
cell08    0.186  0.037   0.114  0.257  38        500
cell16    0.106  0.015   0.077  0.136  58        500
cell10    0.233  0.045   0.146  0.321  51        500
cell15    0.291  0.028   0.235  0.346  49        2000
cell10    0.093  0.022   0.049  0.136  41        2000
cell07    0.285  0.036   0.214  0.357  52        1000
cell17    0.142  0.048   0.049  0.235  51        1000
cell03    0.256  0.020   0.217  0.296  47        4000
```

### Step 17: bootstrapping the CI

While auditing the holding potential column for cell14, two cells fell out of the usable range (coefficient 0.129, stderr 0.027, n = 45). While bootstrapping the CI for cell15, the CI narrowed by roughly a tenth (coefficient 0.298, stderr 0.019, n = 53). While fitting the one-lag kernel for cell06, the ordering of cells was preserved (coefficient 0.205, stderr 0.043, n = 38). While fitting the one-lag kernel for cell15, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.192, stderr 0.036, n = 46). While segmenting epochs for cell10, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.129, stderr 0.050, n = 45).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell21    0.173  0.039   0.097  0.248  44        4000
cell18    0.274  0.012   0.251  0.297  48        500
cell07    0.301  0.014   0.273  0.328  38        4000
cell13    0.133  0.022   0.091  0.176  54        1000
cell15    0.252  0.026   0.201  0.303  53        2000
cell02    0.176  0.024   0.130  0.222  42        4000
cell14    0.125  0.041   0.044  0.206  56        2000
cell05    0.186  0.047   0.094  0.278  54        2000
```

### Step 18: auditing the holding potential column

While checking residual autocorrelation for cell09, the coefficient tracked epoch count more closely than duration (coefficient 0.304, stderr 0.047, n = 39). While re-exporting the raw traces for cell16, nothing in the figure changed at print size (coefficient 0.213, stderr 0.029, n = 58). While auditing the holding potential column for cell03, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.193, stderr 0.020, n = 53). While fitting the one-lag kernel for cell04, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.143, stderr 0.039, n = 43). This is the part that will need a real statistical argument.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell04    0.121  0.035   0.052  0.190  45        500
cell06    0.084  0.024   0.037  0.131  51        1000
cell05    0.296  0.033   0.230  0.361  55        4000
cell24    0.123  0.037   0.051  0.195  40        2000
cell16    0.218  0.020   0.178  0.258  53        4000
cell15    0.238  0.036   0.168  0.308  54        2000
cell08    0.218  0.017   0.184  0.251  58        4000
cell02    0.217  0.011   0.195  0.239  55        1000
cell19    0.183  0.016   0.153  0.214  39        500
cell03    0.164  0.049   0.069  0.260  47        1000
cell21    0.150  0.044   0.064  0.237  54        1000
cell02    0.202  0.028   0.147  0.257  51        1000
cell02    0.226  0.022   0.184  0.269  58        500
```

```python
coefs = fit_per_cell(rows, threshold=0.64)
lo, hi = ci(coefs, seed=78)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 19: re-exporting the raw traces

While auditing the holding potential column for cell16, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.205, stderr 0.025, n = 57). While bootstrapping the CI for cell20, nothing in the figure changed at print size (coefficient 0.140, stderr 0.013, n = 51). While re-exporting the raw traces for cell16, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.130, stderr 0.012, n = 54). While comparing per-cell orderings for cell09, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.291, stderr 0.038, n = 51). While auditing the holding potential column for cell02, two cells fell out of the usable range (coefficient 0.244, stderr 0.012, n = 51). While auditing the holding potential column for cell11, the coefficient tracked epoch count more closely than duration (coefficient 0.089, stderr 0.034, n = 49).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell04    0.291  0.012   0.268  0.314  53        500
cell19    0.282  0.019   0.244  0.321  56        1000
cell09    0.204  0.039   0.127  0.281  54        500
cell21    0.081  0.012   0.057  0.106  56        2000
cell08    0.215  0.039   0.139  0.291  54        1000
cell13    0.280  0.012   0.256  0.303  46        2000
cell13    0.110  0.040   0.032  0.188  56        1000
cell21    0.090  0.038   0.016  0.164  48        500
cell20    0.195  0.037   0.123  0.267  55        4000
cell08    0.143  0.037   0.070  0.215  40        4000
cell10    0.159  0.037   0.086  0.232  47        500
cell12    0.220  0.039   0.143  0.298  50        500
```

While segmenting epochs for cell19, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.208, stderr 0.024, n = 55). While re-exporting the raw traces for cell05, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.161, stderr 0.038, n = 47). While fitting the one-lag kernel for cell05, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.240, stderr 0.013, n = 58). While segmenting epochs for cell10, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.309, stderr 0.028, n = 39). While checking residual autocorrelation for cell21, nothing in the figure changed at print size (coefficient 0.119, stderr 0.046, n = 57). While comparing per-cell orderings for cell04, two cells fell out of the usable range (coefficient 0.201, stderr 0.049, n = 47).

While checking residual autocorrelation for cell14, two cells fell out of the usable range (coefficient 0.085, stderr 0.034, n = 46). While re-exporting the raw traces for cell13, two cells fell out of the usable range (coefficient 0.081, stderr 0.025, n = 44). While comparing per-cell orderings for cell12, the CI narrowed by roughly a tenth (coefficient 0.197, stderr 0.038, n = 47). While fitting the one-lag kernel for cell14, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.275, stderr 0.040, n = 55). This is the part that will need a real statistical argument.

### Step 20: checking residual autocorrelation

While checking residual autocorrelation for cell23, the CI narrowed by roughly a tenth (coefficient 0.253, stderr 0.034, n = 48). While re-exporting the raw traces for cell22, the estimate moved less than one standard error (coefficient 0.175, stderr 0.010, n = 58). While bootstrapping the CI for cell04, the CI narrowed by roughly a tenth (coefficient 0.219, stderr 0.016, n = 40). While comparing per-cell orderings for cell07, the ordering of cells was preserved (coefficient 0.190, stderr 0.031, n = 49). While re-exporting the raw traces for cell02, the ordering of cells was preserved (coefficient 0.171, stderr 0.027, n = 47). While re-running with a tighter segmentation threshold for cell18, the coefficient tracked epoch count more closely than duration (coefficient 0.272, stderr 0.046, n = 38). Parking this until the re-segmentation lands.

While comparing per-cell orderings for cell23, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.295, stderr 0.046, n = 56). While fitting the one-lag kernel for cell10, the CI narrowed by roughly a tenth (coefficient 0.114, stderr 0.048, n = 53). While segmenting epochs for cell04, two cells fell out of the usable range (coefficient 0.162, stderr 0.044, n = 44).

### Step 21: auditing the holding potential column

While segmenting epochs for cell07, two cells fell out of the usable range (coefficient 0.301, stderr 0.040, n = 38). While checking residual autocorrelation for cell10, two cells fell out of the usable range (coefficient 0.208, stderr 0.014, n = 48). While bootstrapping the CI for cell04, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.211, stderr 0.021, n = 56). While fitting the one-lag kernel for cell22, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.232, stderr 0.018, n = 39). While re-exporting the raw traces for cell19, the CI narrowed by roughly a tenth (coefficient 0.256, stderr 0.043, n = 42).

While auditing the holding potential column for cell20, two cells fell out of the usable range (coefficient 0.260, stderr 0.016, n = 42). While segmenting epochs for cell18, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.278, stderr 0.036, n = 57). While auditing the holding potential column for cell17, the ordering of cells was preserved (coefficient 0.186, stderr 0.039, n = 53). While bootstrapping the CI for cell24, the estimate moved less than one standard error (coefficient 0.290, stderr 0.015, n = 58). While fitting the one-lag kernel for cell09, the CI narrowed by roughly a tenth (coefficient 0.294, stderr 0.026, n = 43). Worth noting for the writeup, though not a result on its own.

While segmenting epochs for cell07, the estimate moved less than one standard error (coefficient 0.098, stderr 0.050, n = 51). While auditing the holding potential column for cell22, the estimate moved less than one standard error (coefficient 0.107, stderr 0.032, n = 38). While re-exporting the raw traces for cell14, the CI narrowed by roughly a tenth (coefficient 0.223, stderr 0.012, n = 51). While checking residual autocorrelation for cell02, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.091, stderr 0.039, n = 58). While bootstrapping the CI for cell24, nothing in the figure changed at print size (coefficient 0.176, stderr 0.044, n = 42).

### Step 22: auditing the holding potential column

While comparing per-cell orderings for cell06, the estimate moved less than one standard error (coefficient 0.182, stderr 0.025, n = 41). While checking residual autocorrelation for cell21, the CI narrowed by roughly a tenth (coefficient 0.246, stderr 0.014, n = 42). While bootstrapping the CI for cell22, the CI narrowed by roughly a tenth (coefficient 0.139, stderr 0.016, n = 57). While segmenting epochs for cell08, the CI narrowed by roughly a tenth (coefficient 0.191, stderr 0.020, n = 46). While segmenting epochs for cell03, two cells fell out of the usable range (coefficient 0.237, stderr 0.013, n = 38). While bootstrapping the CI for cell10, two cells fell out of the usable range (coefficient 0.249, stderr 0.016, n = 45).

```python
coefs = fit_per_cell(rows, threshold=0.73)
lo, hi = ci(coefs, seed=89)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 23: checking residual autocorrelation

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell01    0.220  0.020   0.180  0.259  50        1000
cell23    0.234  0.030   0.174  0.293  42        2000
cell12    0.090  0.027   0.038  0.142  51        1000
cell13    0.118  0.039   0.041  0.196  41        500
cell14    0.267  0.012   0.243  0.291  54        1000
cell08    0.200  0.027   0.147  0.254  43        500
cell22    0.128  0.028   0.074  0.182  47        4000
cell17    0.194  0.026   0.144  0.244  49        500
cell01    0.239  0.012   0.215  0.263  40        4000
cell21    0.261  0.024   0.213  0.308  43        500
cell18    0.247  0.025   0.197  0.296  52        2000
cell06    0.206  0.043   0.122  0.289  58        1000
cell13    0.196  0.050   0.098  0.294  48        2000
cell20    0.116  0.049   0.020  0.213  46        2000
```

While auditing the holding potential column for cell08, nothing in the figure changed at print size (coefficient 0.227, stderr 0.050, n = 46). While checking residual autocorrelation for cell14, the estimate moved less than one standard error (coefficient 0.179, stderr 0.019, n = 46). While re-running with a tighter segmentation threshold for cell18, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.216, stderr 0.041, n = 38). While auditing the holding potential column for cell14, two cells fell out of the usable range (coefficient 0.095, stderr 0.011, n = 42).

### Step 24: re-running with a tighter segmentation threshold

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell06    0.190  0.014   0.163  0.217  53        2000
cell17    0.082  0.021   0.041  0.122  47        500
cell13    0.108  0.044   0.021  0.195  48        1000
cell19    0.197  0.012   0.175  0.220  56        500
cell21    0.247  0.031   0.185  0.308  50        4000
cell10    0.239  0.019   0.201  0.277  49        2000
cell07    0.219  0.021   0.177  0.260  52        4000
```

While re-exporting the raw traces for cell15, the coefficient tracked epoch count more closely than duration (coefficient 0.162, stderr 0.020, n = 58). While bootstrapping the CI for cell07, nothing in the figure changed at print size (coefficient 0.295, stderr 0.033, n = 40). While fitting the one-lag kernel for cell05, the estimate moved less than one standard error (coefficient 0.091, stderr 0.018, n = 57).

While bootstrapping the CI for cell07, the CI narrowed by roughly a tenth (coefficient 0.119, stderr 0.028, n = 52). While comparing per-cell orderings for cell15, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.099, stderr 0.036, n = 52). While segmenting epochs for cell04, two cells fell out of the usable range (coefficient 0.272, stderr 0.047, n = 48). While re-running with a tighter segmentation threshold for cell07, two cells fell out of the usable range (coefficient 0.099, stderr 0.013, n = 52). Noted and moved on; it does not change the decision.

### Step 25: checking residual autocorrelation

While fitting the one-lag kernel for cell05, the ordering of cells was preserved (coefficient 0.128, stderr 0.046, n = 40). While comparing per-cell orderings for cell16, two cells fell out of the usable range (coefficient 0.111, stderr 0.041, n = 47). While bootstrapping the CI for cell05, nothing in the figure changed at print size (coefficient 0.087, stderr 0.045, n = 50).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell09    0.211  0.037   0.140  0.283  52        4000
cell11    0.171  0.047   0.079  0.262  48        500
cell13    0.134  0.039   0.058  0.210  56        500
cell13    0.170  0.032   0.108  0.232  58        2000
cell04    0.235  0.038   0.160  0.310  57        500
cell04    0.112  0.012   0.089  0.136  51        1000
```

```python
coefs = fit_per_cell(rows, threshold=0.45)
lo, hi = ci(coefs, seed=7)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While segmenting epochs for cell01, the coefficient tracked epoch count more closely than duration (coefficient 0.194, stderr 0.018, n = 45). While checking residual autocorrelation for cell16, the estimate moved less than one standard error (coefficient 0.274, stderr 0.026, n = 45). While fitting the one-lag kernel for cell04, the estimate moved less than one standard error (coefficient 0.094, stderr 0.036, n = 50).

### Step 26: auditing the holding potential column

While re-exporting the raw traces for cell03, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.082, stderr 0.021, n = 57). While re-running with a tighter segmentation threshold for cell06, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.152, stderr 0.044, n = 41). While auditing the holding potential column for cell15, the estimate moved less than one standard error (coefficient 0.296, stderr 0.049, n = 50). While auditing the holding potential column for cell16, the CI narrowed by roughly a tenth (coefficient 0.276, stderr 0.019, n = 51). While re-running with a tighter segmentation threshold for cell13, the CI narrowed by roughly a tenth (coefficient 0.240, stderr 0.047, n = 42). While checking residual autocorrelation for cell05, the ordering of cells was preserved (coefficient 0.113, stderr 0.014, n = 53). Noted and moved on; it does not change the decision.

While re-running with a tighter segmentation threshold for cell24, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.267, stderr 0.036, n = 47). While segmenting epochs for cell07, the coefficient tracked epoch count more closely than duration (coefficient 0.265, stderr 0.031, n = 40). While checking residual autocorrelation for cell03, the CI narrowed by roughly a tenth (coefficient 0.181, stderr 0.024, n = 51). While re-running with a tighter segmentation threshold for cell19, the coefficient tracked epoch count more closely than duration (coefficient 0.215, stderr 0.041, n = 39). While re-exporting the raw traces for cell13, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.112, stderr 0.032, n = 38).

While re-running with a tighter segmentation threshold for cell21, two cells fell out of the usable range (coefficient 0.269, stderr 0.040, n = 44). While segmenting epochs for cell04, the CI narrowed by roughly a tenth (coefficient 0.188, stderr 0.014, n = 39). While bootstrapping the CI for cell21, the CI narrowed by roughly a tenth (coefficient 0.275, stderr 0.030, n = 55). While fitting the one-lag kernel for cell22, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.215, stderr 0.034, n = 41). While re-running with a tighter segmentation threshold for cell01, two cells fell out of the usable range (coefficient 0.089, stderr 0.030, n = 38). Worth noting for the writeup, though not a result on its own.

```python
coefs = fit_per_cell(rows, threshold=0.61)
lo, hi = ci(coefs, seed=62)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

### Step 27: re-exporting the raw traces

While fitting the one-lag kernel for cell06, two cells fell out of the usable range (coefficient 0.252, stderr 0.039, n = 48). While comparing per-cell orderings for cell17, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.132, stderr 0.042, n = 50). While re-running with a tighter segmentation threshold for cell24, the estimate moved less than one standard error (coefficient 0.165, stderr 0.022, n = 42). While segmenting epochs for cell23, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.271, stderr 0.036, n = 54). While auditing the holding potential column for cell05, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.243, stderr 0.012, n = 57). While segmenting epochs for cell16, two cells fell out of the usable range (coefficient 0.177, stderr 0.025, n = 47). Parking this until the re-segmentation lands.

While bootstrapping the CI for cell13, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.257, stderr 0.045, n = 49). While segmenting epochs for cell03, the coefficient tracked epoch count more closely than duration (coefficient 0.117, stderr 0.015, n = 41). While comparing per-cell orderings for cell04, the ordering of cells was preserved (coefficient 0.137, stderr 0.014, n = 44). While re-exporting the raw traces for cell11, two cells fell out of the usable range (coefficient 0.147, stderr 0.021, n = 48). While segmenting epochs for cell03, nothing in the figure changed at print size (coefficient 0.214, stderr 0.025, n = 55).

### Step 28: checking residual autocorrelation

While fitting the one-lag kernel for cell11, the estimate moved less than one standard error (coefficient 0.157, stderr 0.025, n = 42). While fitting the one-lag kernel for cell10, two cells fell out of the usable range (coefficient 0.280, stderr 0.030, n = 41). While bootstrapping the CI for cell02, nothing in the figure changed at print size (coefficient 0.235, stderr 0.045, n = 50). While bootstrapping the CI for cell04, the CI narrowed by roughly a tenth (coefficient 0.271, stderr 0.033, n = 44). While bootstrapping the CI for cell21, the ordering of cells was preserved (coefficient 0.268, stderr 0.038, n = 50). Flagging it so it does not get rediscovered next week.

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell07    0.294  0.019   0.257  0.332  54        2000
cell02    0.255  0.013   0.229  0.282  52        2000
cell02    0.246  0.013   0.220  0.272  56        1000
cell17    0.144  0.032   0.082  0.205  55        2000
cell12    0.250  0.011   0.229  0.271  44        500
cell17    0.243  0.018   0.208  0.278  56        4000
cell23    0.269  0.039   0.192  0.347  43        1000
cell19    0.236  0.016   0.204  0.267  55        500
cell16    0.179  0.031   0.118  0.241  51        1000
```

### Step 29: re-exporting the raw traces

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell02    0.115  0.046   0.025  0.206  44        1000
cell10    0.200  0.046   0.110  0.290  56        2000
cell24    0.207  0.023   0.162  0.251  54        4000
cell19    0.087  0.022   0.045  0.130  42        2000
cell06    0.280  0.023   0.236  0.325  42        2000
cell14    0.154  0.038   0.079  0.229  53        2000
cell08    0.221  0.018   0.185  0.256  38        500
cell10    0.091  0.041   0.011  0.171  56        4000
cell15    0.244  0.021   0.203  0.284  41        1000
cell08    0.102  0.031   0.041  0.162  42        2000
cell15    0.234  0.041   0.153  0.315  39        500
cell11    0.160  0.029   0.103  0.217  52        1000
```

While re-exporting the raw traces for cell01, the estimate moved less than one standard error (coefficient 0.279, stderr 0.049, n = 51). While re-exporting the raw traces for cell17, the CI narrowed by roughly a tenth (coefficient 0.099, stderr 0.037, n = 56). While checking residual autocorrelation for cell03, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.093, stderr 0.024, n = 47). While fitting the one-lag kernel for cell23, the ordering of cells was preserved (coefficient 0.193, stderr 0.016, n = 43). While auditing the holding potential column for cell12, the estimate moved less than one standard error (coefficient 0.221, stderr 0.040, n = 57). While comparing per-cell orderings for cell12, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.273, stderr 0.019, n = 45). Flagging it so it does not get rediscovered next week.

While comparing per-cell orderings for cell11, the CI narrowed by roughly a tenth (coefficient 0.250, stderr 0.026, n = 50). While checking residual autocorrelation for cell23, the coefficient tracked epoch count more closely than duration (coefficient 0.248, stderr 0.016, n = 49). While bootstrapping the CI for cell01, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.135, stderr 0.023, n = 39). While re-running with a tighter segmentation threshold for cell14, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.299, stderr 0.014, n = 57). While auditing the holding potential column for cell20, the estimate moved less than one standard error (coefficient 0.285, stderr 0.030, n = 47). This is the part that will need a real statistical argument.

While re-running with a tighter segmentation threshold for cell23, nothing in the figure changed at print size (coefficient 0.187, stderr 0.042, n = 58). While fitting the one-lag kernel for cell20, the ordering of cells was preserved (coefficient 0.204, stderr 0.032, n = 39). While segmenting epochs for cell08, the ordering of cells was preserved (coefficient 0.173, stderr 0.038, n = 40). While re-running with a tighter segmentation threshold for cell22, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.297, stderr 0.045, n = 47). While auditing the holding potential column for cell14, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.282, stderr 0.016, n = 47). Worth noting for the writeup, though not a result on its own.

### Step 30: checking residual autocorrelation

While re-exporting the raw traces for cell18, two cells fell out of the usable range (coefficient 0.186, stderr 0.018, n = 55). While fitting the one-lag kernel for cell08, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.179, stderr 0.035, n = 52). While re-running with a tighter segmentation threshold for cell24, the ordering of cells was preserved (coefficient 0.263, stderr 0.044, n = 50).

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell09    0.307  0.031   0.247  0.368  46        1000
cell12    0.123  0.044   0.037  0.210  45        4000
cell22    0.150  0.023   0.105  0.194  47        2000
cell18    0.281  0.048   0.187  0.376  51        500
cell05    0.251  0.025   0.203  0.299  49        4000
cell09    0.192  0.033   0.127  0.256  43        500
```

### Step 31: re-running with a tighter segmentation threshold

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell10    0.239  0.014   0.212  0.266  52        4000
cell15    0.204  0.039   0.127  0.281  52        4000
cell22    0.182  0.043   0.097  0.267  40        1000
cell03    0.205  0.022   0.161  0.248  56        1000
cell04    0.153  0.020   0.115  0.192  39        2000
cell17    0.255  0.049   0.160  0.350  40        4000
cell19    0.231  0.014   0.203  0.259  44        4000
cell04    0.130  0.036   0.059  0.200  45        2000
cell04    0.226  0.034   0.160  0.292  41        4000
cell11    0.265  0.035   0.197  0.334  46        2000
cell21    0.306  0.013   0.282  0.331  45        500
cell05    0.248  0.021   0.206  0.289  47        500
```

```python
coefs = fit_per_cell(rows, threshold=0.31)
lo, hi = ci(coefs, seed=79)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While bootstrapping the CI for cell01, nothing in the figure changed at print size (coefficient 0.262, stderr 0.048, n = 53). While checking residual autocorrelation for cell15, nothing in the figure changed at print size (coefficient 0.088, stderr 0.021, n = 48). While re-exporting the raw traces for cell15, the estimate moved less than one standard error (coefficient 0.194, stderr 0.040, n = 55). While segmenting epochs for cell17, the CI narrowed by roughly a tenth (coefficient 0.100, stderr 0.043, n = 55). While segmenting epochs for cell13, the coefficient tracked epoch count more closely than duration (coefficient 0.185, stderr 0.034, n = 41).

### Step 32: segmenting epochs

While re-running with a tighter segmentation threshold for cell22, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.274, stderr 0.024, n = 48). While re-running with a tighter segmentation threshold for cell07, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.224, stderr 0.029, n = 47). While re-exporting the raw traces for cell04, the coefficient tracked epoch count more closely than duration (coefficient 0.100, stderr 0.022, n = 40). While segmenting epochs for cell06, the estimate moved less than one standard error (coefficient 0.142, stderr 0.028, n = 45).

While comparing per-cell orderings for cell03, the ordering of cells was preserved (coefficient 0.205, stderr 0.012, n = 49). While checking residual autocorrelation for cell10, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.174, stderr 0.036, n = 39). While comparing per-cell orderings for cell20, the coefficient tracked epoch count more closely than duration (coefficient 0.299, stderr 0.030, n = 46). While checking residual autocorrelation for cell09, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.111, stderr 0.012, n = 40). While segmenting epochs for cell04, the CI narrowed by roughly a tenth (coefficient 0.134, stderr 0.016, n = 40). Parking this until the re-segmentation lands.

### Step 33: auditing the holding potential column

```
cell      coef    stderr   lo      hi      n_epochs  resamples
cell07    0.127  0.023   0.082  0.172  43        2000
cell24    0.177  0.046   0.086  0.267  42        1000
cell09    0.097  0.049   0.001  0.193  45        2000
cell19    0.218  0.044   0.131  0.304  40        1000
cell09    0.302  0.049   0.205  0.399  58        4000
cell01    0.084  0.021   0.042  0.125  47        500
cell08    0.144  0.046   0.055  0.233  53        500
cell04    0.131  0.020   0.091  0.170  56        1000
cell02    0.109  0.011   0.088  0.130  43        1000
cell18    0.147  0.024   0.099  0.195  51        2000
```

While comparing per-cell orderings for cell16, the estimate moved less than one standard error (coefficient 0.098, stderr 0.028, n = 39). While re-running with a tighter segmentation threshold for cell13, two cells fell out of the usable range (coefficient 0.275, stderr 0.011, n = 56). While re-running with a tighter segmentation threshold for cell21, two cells fell out of the usable range (coefficient 0.242, stderr 0.042, n = 43). While fitting the one-lag kernel for cell17, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.117, stderr 0.050, n = 51). While comparing per-cell orderings for cell15, the ordering of cells was preserved (coefficient 0.247, stderr 0.014, n = 42).

### Step 34: comparing per-cell orderings

While segmenting epochs for cell13, the estimate moved less than one standard error (coefficient 0.230, stderr 0.037, n = 55). While re-exporting the raw traces for cell20, two cells fell out of the usable range (coefficient 0.298, stderr 0.023, n = 49). While bootstrapping the CI for cell23, the coefficient tracked epoch count more closely than duration (coefficient 0.218, stderr 0.034, n = 56). While bootstrapping the CI for cell05, nothing in the figure changed at print size (coefficient 0.171, stderr 0.038, n = 57). While re-running with a tighter segmentation threshold for cell11, the coefficient tracked epoch count more closely than duration (coefficient 0.278, stderr 0.033, n = 48).

While auditing the holding potential column for cell12, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.167, stderr 0.023, n = 56). While comparing per-cell orderings for cell10, the CI narrowed by roughly a tenth (coefficient 0.243, stderr 0.043, n = 45). While segmenting epochs for cell21, two cells fell out of the usable range (coefficient 0.089, stderr 0.042, n = 52). While re-exporting the raw traces for cell04, the coefficient tracked epoch count more closely than duration (coefficient 0.171, stderr 0.020, n = 57). While segmenting epochs for cell05, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.162, stderr 0.022, n = 54).

### Step 35: fitting the one-lag kernel

While segmenting epochs for cell15, the coefficient tracked epoch count more closely than duration (coefficient 0.081, stderr 0.024, n = 39). While comparing per-cell orderings for cell02, the coefficient tracked epoch count more closely than duration (coefficient 0.118, stderr 0.023, n = 44). While comparing per-cell orderings for cell16, the coefficient tracked epoch count more closely than duration (coefficient 0.099, stderr 0.044, n = 40).

While checking residual autocorrelation for cell22, the estimate moved less than one standard error (coefficient 0.106, stderr 0.035, n = 46). While auditing the holding potential column for cell10, the CI narrowed by roughly a tenth (coefficient 0.256, stderr 0.041, n = 55). While auditing the holding potential column for cell02, the ordering of cells was preserved (coefficient 0.136, stderr 0.048, n = 45). While checking residual autocorrelation for cell08, the estimate moved less than one standard error (coefficient 0.128, stderr 0.031, n = 50). While segmenting epochs for cell14, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.182, stderr 0.015, n = 50). While re-exporting the raw traces for cell06, two cells fell out of the usable range (coefficient 0.227, stderr 0.046, n = 54).

While segmenting epochs for cell24, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.180, stderr 0.034, n = 57). While fitting the one-lag kernel for cell11, nothing in the figure changed at print size (coefficient 0.084, stderr 0.042, n = 44). While bootstrapping the CI for cell17, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.238, stderr 0.024, n = 53). While segmenting epochs for cell23, two cells fell out of the usable range (coefficient 0.175, stderr 0.025, n = 57). Worth noting for the writeup, though not a result on its own.

### Step 36: fitting the one-lag kernel

While checking residual autocorrelation for cell06, the ordering of cells was preserved (coefficient 0.174, stderr 0.023, n = 42). While checking residual autocorrelation for cell20, two cells fell out of the usable range (coefficient 0.212, stderr 0.015, n = 47). While re-running with a tighter segmentation threshold for cell09, the CI narrowed by roughly a tenth (coefficient 0.086, stderr 0.043, n = 39). While checking residual autocorrelation for cell13, the coefficient tracked epoch count more closely than duration (coefficient 0.097, stderr 0.040, n = 55). While comparing per-cell orderings for cell12, the ordering of cells was preserved (coefficient 0.307, stderr 0.025, n = 42). While re-running with a tighter segmentation threshold for cell04, two cells fell out of the usable range (coefficient 0.147, stderr 0.044, n = 58).

While comparing per-cell orderings for cell23, the coefficient tracked epoch count more closely than duration (coefficient 0.283, stderr 0.019, n = 58). While auditing the holding potential column for cell08, two cells fell out of the usable range (coefficient 0.102, stderr 0.044, n = 44). While re-running with a tighter segmentation threshold for cell20, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.156, stderr 0.044, n = 57). While segmenting epochs for cell06, the estimate moved less than one standard error (coefficient 0.145, stderr 0.016, n = 44). While segmenting epochs for cell12, two cells fell out of the usable range (coefficient 0.119, stderr 0.038, n = 50). Flagging it so it does not get rediscovered next week.

While checking residual autocorrelation for cell06, two cells fell out of the usable range (coefficient 0.291, stderr 0.015, n = 44). While checking residual autocorrelation for cell24, the CI narrowed by roughly a tenth (coefficient 0.084, stderr 0.044, n = 56). While fitting the one-lag kernel for cell14, two cells fell out of the usable range (coefficient 0.153, stderr 0.012, n = 41). While auditing the holding potential column for cell03, two cells fell out of the usable range (coefficient 0.109, stderr 0.021, n = 58). While re-running with a tighter segmentation threshold for cell02, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.081, stderr 0.031, n = 47). While comparing per-cell orderings for cell16, the CI narrowed by roughly a tenth (coefficient 0.180, stderr 0.047, n = 55).

### Step 37: auditing the holding potential column

While fitting the one-lag kernel for cell19, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.165, stderr 0.025, n = 49). While checking residual autocorrelation for cell21, the ordering of cells was preserved (coefficient 0.302, stderr 0.015, n = 49). While re-exporting the raw traces for cell20, the estimate moved less than one standard error (coefficient 0.209, stderr 0.050, n = 48). While re-exporting the raw traces for cell06, the ordering of cells was preserved (coefficient 0.293, stderr 0.042, n = 47).

```python
coefs = fit_per_cell(rows, threshold=0.74)
lo, hi = ci(coefs, seed=81)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While re-running with a tighter segmentation threshold for cell16, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.205, stderr 0.026, n = 47). While segmenting epochs for cell22, two cells fell out of the usable range (coefficient 0.143, stderr 0.019, n = 47). While fitting the one-lag kernel for cell16, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.121, stderr 0.045, n = 50). While re-exporting the raw traces for cell17, the CI narrowed by roughly a tenth (coefficient 0.257, stderr 0.041, n = 49). While comparing per-cell orderings for cell11, the estimate moved less than one standard error (coefficient 0.159, stderr 0.012, n = 42). While checking residual autocorrelation for cell22, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.135, stderr 0.030, n = 39).

While auditing the holding potential column for cell10, the CI narrowed by roughly a tenth (coefficient 0.172, stderr 0.037, n = 52). While auditing the holding potential column for cell23, two cells fell out of the usable range (coefficient 0.144, stderr 0.045, n = 45). While comparing per-cell orderings for cell13, the CI narrowed by roughly a tenth (coefficient 0.284, stderr 0.024, n = 43). While auditing the holding potential column for cell23, the ordering of cells was preserved (coefficient 0.172, stderr 0.013, n = 54). While comparing per-cell orderings for cell21, two cells fell out of the usable range (coefficient 0.148, stderr 0.015, n = 51). While auditing the holding potential column for cell18, two cells fell out of the usable range (coefficient 0.118, stderr 0.044, n = 44). Parking this until the re-segmentation lands.

### Step 38: fitting the one-lag kernel

While fitting the one-lag kernel for cell06, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.097, stderr 0.035, n = 56). While bootstrapping the CI for cell09, the estimate moved less than one standard error (coefficient 0.108, stderr 0.014, n = 54). While comparing per-cell orderings for cell21, the coefficient tracked epoch count more closely than duration (coefficient 0.262, stderr 0.036, n = 49). While segmenting epochs for cell11, the estimate moved less than one standard error (coefficient 0.277, stderr 0.018, n = 52).

While auditing the holding potential column for cell06, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.308, stderr 0.043, n = 58). While segmenting epochs for cell01, the pooled estimate shrank, as it always does with unequal counts (coefficient 0.140, stderr 0.039, n = 51). While comparing per-cell orderings for cell10, the CI narrowed by roughly a tenth (coefficient 0.163, stderr 0.036, n = 53). While comparing per-cell orderings for cell20, the CI narrowed by roughly a tenth (coefficient 0.238, stderr 0.028, n = 41).

While fitting the one-lag kernel for cell17, nothing in the figure changed at print size (coefficient 0.224, stderr 0.011, n = 42). While re-running with a tighter segmentation threshold for cell02, the estimate moved less than one standard error (coefficient 0.164, stderr 0.017, n = 43). While fitting the one-lag kernel for cell03, the CI narrowed by roughly a tenth (coefficient 0.206, stderr 0.037, n = 56). While auditing the holding potential column for cell04, the CI narrowed by roughly a tenth (coefficient 0.229, stderr 0.047, n = 43). While segmenting epochs for cell13, the residual at lag 2 stayed indistinguishable from zero (coefficient 0.240, stderr 0.038, n = 50). Flagging it so it does not get rediscovered next week.

While auditing the holding potential column for cell09, the CI narrowed by roughly a tenth (coefficient 0.171, stderr 0.029, n = 51). While comparing per-cell orderings for cell24, the ordering of cells was preserved (coefficient 0.193, stderr 0.027, n = 56). While segmenting epochs for cell19, two cells fell out of the usable range (coefficient 0.294, stderr 0.046, n = 55).

### Step 39: comparing per-cell orderings

While auditing the holding potential column for cell01, nothing in the figure changed at print size (coefficient 0.150, stderr 0.011, n = 55). While fitting the one-lag kernel for cell03, nothing in the figure changed at print size (coefficient 0.099, stderr 0.033, n = 52). While fitting the one-lag kernel for cell14, nothing in the figure changed at print size (coefficient 0.108, stderr 0.048, n = 54).

```python
coefs = fit_per_cell(rows, threshold=0.48)
lo, hi = ci(coefs, seed=90)
print(f"{len(coefs)} cells, width {hi - lo:.4f}")
```

While segmenting epochs for cell19, the ordering of cells was preserved (coefficient 0.152, stderr 0.049, n = 40). While auditing the holding potential column for cell18, the coefficient tracked epoch count more closely than duration (coefficient 0.171, stderr 0.046, n = 55). While auditing the holding potential column for cell02, the coefficient tracked epoch count more closely than duration (coefficient 0.242, stderr 0.046, n = 40). While fitting the one-lag kernel for cell24, nothing in the figure changed at print size (coefficient 0.280, stderr 0.036, n = 56). While comparing per-cell orderings for cell18, the coefficient tracked epoch count more closely than duration (coefficient 0.269, stderr 0.028, n = 49).

