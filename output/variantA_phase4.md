# Variant A · Phase 4 — Edge optimisation + embargoed walk-forward

Configs tested (N): **36** (T×W). Smoke Edge(0.3,90) net Sharpe 0.697.

## Full-sample Sharpe grid
```
window       30     60     90     126    180    252
threshold                                          
0.1        0.377  0.966  0.840  0.854  0.786  0.699
0.2        0.368  0.966  0.878  0.878  0.815  0.672
0.3        0.517  1.006  0.697  0.834  0.845  0.912
0.4        0.922  0.950  0.927  0.847  1.073  0.687
0.5        1.036  1.018  0.791  0.998  1.060  1.079
0.6        1.006  0.853  0.679  0.928  0.932  0.838
```

- Peak full-sample config **(0.5, 252)** Sharpe **1.079**
- Plateau: **PASS** (nbhd/peak 0.88, same-sign 1.00)

## Embargoed walk-forward (anchored, 5 splits, embargo 14)
```
 split                       is                      oos  threshold  window  is_sharpe  oos_sharpe  oos_ann
     0 (2020-05-11, 2021-04-26) (2021-05-11, 2022-04-14)        0.2      60      1.960       1.229   0.5693
     1 (2020-05-11, 2022-03-31) (2022-04-15, 2023-03-19)        0.6     180      1.575       1.846   0.2930
     2 (2020-05-11, 2023-03-05) (2023-03-20, 2024-02-21)        0.6     180      1.465       1.440   0.2644
     3 (2020-05-11, 2024-02-07) (2024-02-22, 2025-01-25)        0.5     252      1.464      -1.031  -0.1598
     4 (2020-05-11, 2025-01-11) (2025-01-26, 2025-12-31)        0.5     180      1.269      -0.335  -0.0708
```

**Aggregated OOS:** net Sharpe **0.684** · ann 14.9% · maxDD -26.2% · win 10% · PF 1.26
- Benchmark OOS: BH spot Sharpe **0.457**, BH perp 0.313 → beats spot? **YES**

Artifacts: `data_cache/grid_A.parquet`, `data_cache/oos_A.parquet`. Figures: `variantA_heatmap.png`, `variantA_oos_equity.png`.