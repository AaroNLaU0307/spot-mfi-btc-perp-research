# Variant A · Phase 6 — cost sensitivity & breakeven

Best in-sample config **T=0.5, W=252**. Funding always applied.

| one-way cost (bps) | net Sharpe |
|---:|---:|
| 0 | 1.118 |
| 2 | 1.106 |
| 5 | 1.090 |
| 7 | 1.079 |
| 10 | 1.062 |
| 15 | 1.034 |
| 20 | 1.006 |
| 30 | 0.949 |
| 50 | 0.836 |
| 75 | 0.693 |
| 100 | 0.550 |

- Gross Sharpe (no fees/funding): **1.175**  ·  BH spot: **0.995**
- Activity at real costs: **31 trades**, avg hold **11.2 days**, turnover **11.0/yr**, exposure **17%** of days.
- Breakeven one-way cost: **> 100 bps (not fee-bound)**

**Reading:** as in the base study, turnover is low (~11/yr) → not fee-sensitive. Funding is the drag, but the binding constraint is significance/persistence (Phase 5), not cost.
