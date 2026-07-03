# PRE-REGISTRATION — frozen 2026-07-01, before any strategy PnL

Committed after Phase-1 factor EDA (IC / deciles / stationarity) and **before** any backtest,
optimisation, or look at strategy returns. Direction is chosen from the IC sign, not from PnL.

## Factor (disclosed proxy)
Self-computed **cross-exchange spot MFI** (14-day; `typical price × volume`; volume-weighted
aggregate of Binance/Coinbase/Kraken/Bitstamp/OKX), lagged ≥1 bar. **NOT** Glassnode's
`spot_money_flow_index`. Phase-0 caveat: the aggregate is ~0.997-correlated with single-Binance MFI
(Binance dominates spot volume), so "cross-exchange breadth" is weak and the spot-vs-perp divergence
premise is partly undercut. To be re-run on the genuine Glassnode series when a key is available.

## Evidence adjudicating the candidate angles (from Phase 1)
- Level IC vs perp forward returns is **POSITIVE and rising with horizon**: 1d +0.021, 5d +0.026,
  10d +0.057, 21d +0.156. Peak |IC| at 21d.
- **Honest (non-overlapping) IC is NOT significant** at any horizon (p ≈ 0.30–0.46); the significant
  naive p at 10/21d is an artifact of overlapping forward returns.
- Deciles: top MFI decile has the highest forward return at every horizon (monotone-ish, weak: decile
  rank↔return corr ≈ +0.37 at 5d). **Nearly all deciles are positive** — 10/10 at the 10d horizon; the
  few negative deciles elsewhere are tiny relative to the top decile (1d: deciles 2,4 at −0.04%,−0.00%
  vs top +0.56%; 5d: decile 5 at −0.06% vs top +2.78%; 21d: decile 1 at −0.64% vs top +8.31%) — a
  BTC-uptrend confound: low MFI does **not** predict meaningfully negative returns.
- MFI level is stationary (ADF p≈0, KPSS p≈0.10) with high persistence (ACF₁≈0.95).

**Verdict on angles:** (A) mean-reversion-at-extremes is **falsified by the IC sign** (high MFI →
continuation up, not reversal — the opposite of the ">80 overbought reverses" convention, and also
opposite Glassnode's erroneous ">80 oversold" text). (C) spot–perp divergence has a **weakened premise**
(Phase-0 breadth finding). ⇒ Primary = **(B) momentum / regime**.

## Primary hypothesis (ONE)
**H1 (momentum, LONG-only):** elevated cross-exchange spot money flow (high MFI) reflects genuine
spot-demand conviction that the perp continues to price in over ~1–3 weeks. Trade it **long-only**,
because the IC is positive AND the decile evidence shows low MFI does not predict declines (shorting the
low-MFI leg would fight BTC's uptrend). Natural holding horizon ≈ 10–21 days (IC decay).

## Model & parameters (2 knobs — kept minimal)
- **Primary model M1 — level threshold, long-only.** Signal = MFI smoothed over a trailing window `W`.
  Enter/hold **long** when `smooth_W(MFI) > T`; exit to **flat** when it falls back below the midline 50.
  Grid: `T ∈ {60,65,70,75,80,85,90}` × `W ∈ {1,2,3,5,7,10}` days (42 configs; `config.GRID_LEVEL_THRESHOLDS`).
- **Robustness model M2 — rolling z-score band, long-only.** Long when `zscore_win(MFI) > Z`; flat when
  `< 0`. Grid: `Z ∈ GRID_Z_THRESHOLDS` × `win ∈ GRID_Z_WINDOWS`. Reported as a sensitivity check, not a
  second bite at the apple.
- Execution: factor lagged ≥1 bar; enter/exit at the **next bar's open**. Single position, constant
  notional, no pyramiding. Vol-targeting only as a robustness variant.
- Exits tested as robustness (not extra optimisation knobs): time-stop at the IC-decay horizon; ATR/vol
  stop. Primary exit is the signal-based midline reversion above.

## Costs (net is the only number that matters)
Taker fees 0.05%/side + slippage 2 bps/side + **actual 8h funding by side/holding** (mean ≈ +12.5%/yr
paid by longs — material for a long-biased strategy). Cost-sensitivity curve + breakeven ceiling reported.

## Benchmark
Buy-and-hold BTCUSDT perp (net of funding) **and** flat. A long-only strategy in a secular bull market
must be judged against passive beta, not zero.

## Decision rule (FROZEN — the verdict cites exactly this)
**CONFIRMED EDGE** requires ALL of:
1. Net (fees+slippage+funding) **annualised OOS Sharpe ≥ 0.5**, and
2. Net OOS Sharpe **> buy-and-hold** Sharpe over the same OOS span (beats passive beta), and
3. Selected params sit on a **contiguous plateau** (3×3 ±1-step neighbourhood retains ≥80% of peak
   Sharpe with the same sign), not an isolated spike, and
4. **DSR > 0.95** (p<0.05) with N = full grid size, and BH-FDR survival at α=0.05 across the grid, and
5. **Stationary-block-bootstrap 95% CI for the OOS Sharpe excludes 0** and factor-permutation null
   p<0.05, and
6. Aggregated **walk-forward OOS equity is positive**, and
7. **Breakeven cost ceiling > modelled round-trip cost** (edge survives realistic costs).

**FALSIFIED** if it fails at the premise (weak/again-benchmark), no plateau (spike only), dies on costs,
non-positive/again-benchmark OOS, or fails significance (DSR/FDR/bootstrap/permutation).
**INCONCLUSIVE** if net-positive and beats benchmark point-estimate but significance is borderline
(e.g., DSR<0.95 while bootstrap CI barely includes 0) — i.e., suggestive but not established.

## Honest prior (stated before results)
Given the non-significant honest-sample IC, the all-decile-positive uptrend confound, and heavy long
funding, the expected outcome is **FALSIFIED or INCONCLUSIVE**. A clean negative is a fully acceptable,
expected result. We will not move the goalposts.
