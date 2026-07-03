# Variant A · Phase 5 — statistical validation

N configs: **36**. Block length: **21** days.

## In-sample selection significance

- Best IS config (T=0.5, W=252): PSR vs 0 = **0.997**, **DSR (N=36) = 0.961** (PASS vs 0.95)
- BH-FDR survivors across grid: **28/36**

## Out-of-sample honesty (the verdict inputs)

- Aggregated OOS Sharpe = **0.684** · PSR vs 0 = 0.933
- Stationary block-bootstrap 95% CI: **[-0.194, 1.619]** (frac>0 0.94) → **INCLUDES 0**
- Permutation null: observed 0.768 vs null p95 0.902; **p = 0.100** (NOT significant)

## OOS stability by calendar year (diagnostic)
```
ts
2021    0.893
2022    1.407
2023    1.989
2024   -0.993
2025   -0.324
```
An edge should be sign-stable across years; strong-positive-then-negative flips mean the aggregate reflects a few favourable sub-periods (e.g. 2022 drawdown-avoidance), not persistent alpha.
