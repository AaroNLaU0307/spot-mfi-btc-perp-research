# Phase 5 — Statistical validation

N configs tested (M1 grid): **42**. Block length (a-priori, IC-decay anchored): **21** days.

## In-sample selection significance (DSR/PSR)

- Best IS config (70, 1): per-period SR=0.0560 (ann 1.07), n=2060
- PSR vs 0 = **0.996**
- **DSR (deflated for N=42 trials) = 0.959**  (need > 0.95 for CONFIRMED; PASS)

## Multiple-testing across the grid (BH-FDR)

- Configs surviving BH-FDR at α=0.05: **0/42** (note: long-biased-in-a-bull inflates raw Sharpe>0 p-values; interpret with the benchmark test)

## Out-of-sample honesty (the verdict inputs)

- Aggregated OOS Sharpe (ann) = **0.294**  ·  PSR vs 0 = 0.737
- Stationary block-bootstrap 95% CI for OOS Sharpe: **[-0.720, 1.212]**  (frac>0 0.71) → **INCLUDES 0**
- Permutation null: observed OOS Sharpe 0.445 vs null p95 0.872; **p = 0.266** (NOT significant)
