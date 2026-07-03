# Phase 6 — Cost sensitivity & breakeven

Best in-sample config: **T=70, W=1**. Funding always applied (mean ≈ +12.5%/yr paid by longs).

| one-way cost (bps) | net Sharpe | net ann % |
|---:|---:|---:|
| 0 | 1.092 | 35.5 |
| 2 | 1.086 | 35.2 |
| 5 | 1.076 | 34.8 |
| 7 | 1.070 | 34.5 |
| 10 | 1.060 | 34.1 |
| 15 | 1.044 | 33.4 |
| 20 | 1.027 | 32.7 |
| 30 | 0.995 | 31.3 |
| 50 | 0.930 | 28.5 |
| 75 | 0.848 | 25.1 |
| 100 | 0.765 | 21.8 |

- **Gross Sharpe (no fees, no funding): 1.290** — raw signal-timing value before any cost.
- Buy-and-hold spot Sharpe (full sample): **0.995**.
- Activity at real costs: **30 trades**, avg hold **20.6 days**, turnover **10.6/yr**, exposure **30%** of days.
- **Breakeven one-way cost (net Sharpe → 0): > 100 bps (fees are not the binding constraint)**.

**Reading:** turnover is low (~11/yr), so the strategy is **not** fee-sensitive — the breakeven fee ceiling is high. The binding constraints are the **funding drag** and, decisively, the **lack of out-of-sample persistence** (Phase 4–5): the strategy never beats buy-and-hold spot even gross, and its OOS Sharpe is statistically indistinguishable from zero.
