# Phase 4 — Optimisation + embargoed walk-forward

Model M1 (level×smoothing). Configs tested (N): **42**. Cost = fees+slippage+funding.

## Full-sample Sharpe grid (heatmap `figures/phase4_heatmap_M1.png`)

```
window        1      2      3      5      7      10
threshold                                          
60         0.739  0.828  0.881  0.714  0.548  0.760
65         0.894  0.852  0.918  0.892  0.712  0.698
70         1.070  0.893  0.829  0.783  0.886  0.877
75         0.931  0.799  0.828  0.910  0.728  0.443
80         0.568  0.557  0.638  0.706  0.890  0.637
85         0.729  0.498  0.428  0.785  0.587  0.483
90         0.749  0.676  0.580  0.611  0.601  0.357
```

- Peak full-sample config: **(70, 1)**  Sharpe **1.070**
- Plateau test: **PASS** — 3x3 neighbourhood mean/peak = **0.85** (need ≥0.8), same-sign frac 1.00

## Embargoed walk-forward (OOS is the verdict number)

Scheme **anchored**, 5 splits, min-train 365, embargo **14** bars.

```
 split                       is                      oos  threshold  window  is_sharpe  oos_sharpe  oos_ann
     0 (2020-05-11, 2021-04-26) (2021-05-11, 2022-04-14)         60       2      1.764      -0.301  -0.1756
     1 (2020-05-11, 2022-03-31) (2022-04-15, 2023-03-19)         70      10      1.277       0.316   0.0323
     2 (2020-05-11, 2023-03-05) (2023-03-20, 2024-02-21)         75       1      1.045       1.256   0.3117
     3 (2020-05-11, 2024-02-07) (2024-02-22, 2025-01-25)         70      10      1.055       0.453   0.0984
     4 (2020-05-11, 2025-01-11) (2025-01-26, 2025-12-31)         70       1      1.200       0.144   0.0100
```

**Aggregated OOS:** net Sharpe **0.294** · ann_ret 4.4% · maxDD -34.2% · win 12% · profit_factor 1.09
- Benchmark over same OOS span: **BH spot Sharpe 0.457**, BH perp net Sharpe 0.313
- Beats buy-and-hold (spot)? **NO**  (pre-registered requirement for CONFIRMED)

## M2 robustness (z-score band)

- Peak full-sample Sharpe **1.359** at (1.25, 90); plateau FAIL (nbhd/peak 0.80)
- WF OOS Sharpe **0.717** (vs BH spot 0.457)

## Artifacts for Phase 5

- `data_cache/grid_M1.parquet` (N-config metrics incl per-period Sharpe moments → DSR/BH-FDR)
- `data_cache/series_M1.parquet` (all config net series → per-config bootstrap p)
- `data_cache/oos_M1.parquet` (aggregated OOS net/pos/market → block-bootstrap CI + permutation)