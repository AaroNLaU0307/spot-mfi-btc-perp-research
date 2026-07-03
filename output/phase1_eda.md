# Phase 1 — Factor EDA

Self-computed cross-exchange spot MFI proxy vs BTCUSDT-perp forward returns. Signal lagged 1 bar; transforms are trailing/causal. No strategy PnL here.

## Information Coefficient (Spearman rank corr)

IC = corr(signal_t, forward return t→t+h). Sign decides direction; magnitude/decay the horizon.

```
IC:
                1       3       5       10      21
level       0.0209  0.0305  0.0255  0.0574  0.1558
zscore      0.0069  0.0128  0.0123  0.0355  0.1171
percentile -0.0001  0.0017 -0.0084  0.0207  0.1236
roc         0.0056  0.0016 -0.0004 -0.0260 -0.0088

naive p-values:
                1       3       5       10      21
level       0.3440  0.1663  0.2482  0.0094  0.0000
zscore      0.7589  0.5704  0.5845  0.1160  0.0000
percentile  0.9959  0.9433  0.7226  0.3804  0.0000
roc         0.7990  0.9429  0.9873  0.2407  0.6903
```

Non-overlapping IC for the raw MFI **level** (sample every h bars → honest p):

```
  h        IC         p      n
  1    0.0209    0.3440   2059
  3    0.0287    0.4530    686
  5    0.0366    0.4589    411
 10    0.0721    0.3044    205
 21    0.0860    0.3997     98
```

## Decile forward-return shape (raw MFI level)


**1-day forward return by MFI decile** (mean %, count):

```
        signal_mid  mean_%  count
bucket                           
0             23.5   0.125    206
1             33.2   0.046    206
2             39.3  -0.042    206
3             44.3   0.281    206
4             48.8  -0.002    206
5             53.2   0.022    205
6             57.7   0.066    206
7             63.7   0.147    206
8             71.0   0.556    206
9             81.5   0.382    206
```

**5-day forward return by MFI decile** (mean %, count):

```
        signal_mid  mean_%  count
bucket                           
0             23.5   0.748    206
1             33.2   0.275    205
2             39.2   0.572    206
3             44.3   1.723    205
4             48.8   0.164    206
5             53.2  -0.059    205
6             57.7   0.129    205
7             63.7   0.366    206
8             71.1   1.068    205
9             81.5   2.777    206
```

**10-day forward return by MFI decile** (mean %, count):

```
        signal_mid  mean_%  count
bucket                           
0             23.5   0.895    205
1             33.1   1.065    205
2             39.2   0.959    205
3             44.3   2.895    205
4             48.9   0.827    205
5             53.2   1.082    205
6             57.8   0.556    205
7             63.7   0.438    205
8             71.1   2.471    205
9             81.6   4.561    205
```

**21-day forward return by MFI decile** (mean %, count):

```
        signal_mid  mean_%  count
bucket                           
0             23.5   0.730    204
1             33.1  -0.640    204
2             39.2   2.485    204
3             44.3   5.624    204
4             48.9   2.756    204
5             53.4   1.582    203
6             57.8   4.518    204
7             63.8   3.258    204
8             71.1   5.943    204
9             81.6   8.305    204
```

## Stationarity & autocorrelation

```
MFI level : ADF stat=-6.874 p=0.0000 | KPSS stat=0.134 p=0.1000
MFI change: ADF stat=-17.387 p=0.0000 | KPSS stat=0.005 p=0.1000
ACF level lags0-5 : [1.0, 0.95, 0.886, 0.818, 0.748, 0.676]
ACF change lags0-5: [1.0, 0.152, 0.026, 0.037, 0.011, 0.01]
```

## Reading (for pre-registration — direction from IC, not PnL)

- Dominant level-IC sign across horizons: **POSITIVE (momentum: high MFI → higher fwd returns)** (mean IC=0.0580).
- Decile monotonicity at 5d (corr bucket↔mean ret): **+0.372** (non-monotone → check U/∩ extremes).
- Peak |IC| horizon (level): **21d** (IC=0.1558).

> These readings seed `research/PREREGISTRATION.md`. Nothing here looks at strategy returns.