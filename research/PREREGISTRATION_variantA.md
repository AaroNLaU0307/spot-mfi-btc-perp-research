# PRE-REGISTRATION — Variant A (spot-MFI vs funding divergence). Frozen 2026-07-01, before any PnL.

Committed after Variant-A Phase-1 (funding integrity + joint distribution + Edge honest IC) and
**before** any strategy PnL. Direction is set from the honest IC sign, not from returns. This closes
the spot–perp divergence thesis left unadjudicated by the base study.

## Why funding (not price basis)
The base study found cross-exchange MFI 0.997-correlated with single-Binance MFI, and Binance spot↔perp
are arbitrage-locked — so a *price-basis* divergence is dead. **Funding is a positioning/crowding
channel, orthogonal to price**, so "real spot demand (MFI) vs leveraged greed (funding)" is genuinely
different information. That is why A earns one clean shot and OI/basis do not.

## Factor construction (FIXED)
Both features → common bounded scale via **trailing percentile rank** over window W (causal):
`r_MFI = pct_rank_W(MFI) ∈ [0,1]`, `r_Fund = pct_rank_W(daily_funding) ∈ [0,1]`.
**`Edge_t = r_MFI,t − r_Fund,t ∈ [−1, 1]`.** High Edge = spot strong in its own history AND funding low
= real demand, leverage uncrowded. Daily funding = Σ of the day's 8h payments; lagged ≥1 bar,
next-open execution (same as MFI).

**Funding enters TWICE and is NOT netted:** signal input (crowding info) here; realised holding cost in
the backtester (longs paid ≈12.5%/yr). Deliberate — decide with it, pay it to hold.

**Rejected (unsound) constructions:** `MFI − z(funding)` — dimensional mismatch (MFI 0–100 vs z≈±3), so
funding barely moves the sum; `MFI / funding` — funding crosses zero/goes negative, so the ratio
explodes near 0 and flips sign. Rank-differencing is scale-free and robust to funding's fat tails.

## Phase-1 evidence (already observed — factor only, no PnL)
- corr(MFI, funding) = **+0.32 (Pearson) / +0.35 (Spearman)** — positively coupled as premised.
- Favourable divergence cell (MFI_rank>0.8 & Fund_rank<0.2, trailing W=90): **58 days = 2.8% (SPARSE)**.
- **Edge honest (non-overlapping) IC is ~0 and SMALLER than raw MFI at every horizon** (Edge_W90:
  −0.003, +0.006, +0.017, +0.009, +0.023; all p>0.73). Raw MFI baseline: +0.021…+0.086 (p 0.30–0.46).
- ⇒ **Funding does NOT add predictive information; it degrades the already-insignificant MFI momentum.**

## Primary hypothesis (ONE)
**H1 (divergence long-quality, LONG-only):** long the perp when `Edge > T` (spot strong, funding
uncrowded); flat when `Edge < 0` (hysteresis). Direction **nominally LONG** (Edge_W90 mean honest IC
+0.011 > 0), but **flagged**: the IC is statistically indistinguishable from zero and weaker than the
raw-MFI baseline, so H1 is expected to fail. Holding ≈ IC-decay horizon.

## Model & grid (2 knobs)
- **M1 (primary):** `Edge > T` long, hysteresis exit at 0. Grid `T ∈ {0.1..0.6}` × rank window
  `W ∈ {30,60,90,126,180,252}` (36 configs).
- Robustness (sensitivity ONLY — can never flip the verdict): M2 z-score `z_MFI − z_Fund` (fragile:
  funding fat tails); M3 2D conditional `r_MFI>T_hi & r_Fund<T_lo` (extra parameter → more overfit);
  long-short (short side historically fights the trend).
- Execution: factor lagged ≥1 bar, next-open, single position, constant notional, no pyramiding.

## Costs & benchmark
Fees 0.05%/side + slippage 2bps/side + **realised funding by side/holding**. Benchmark = buy-and-hold
spot (binding — long-only in a bull) and BH-perp.

## Decision rule (FROZEN) — CONFIRMED requires ALL of:
1. Net annualised OOS Sharpe ≥ 0.5, and
2. Beats buy-and-hold spot net Sharpe OOS, and
3. Selected params on a contiguous plateau (3×3 nbhd ≥80% of peak, same sign), and
4. DSR > 0.95 **and** ≥1 config survives BH-FDR across the grid, and
5. Stationary block-bootstrap 95% CI on OOS Sharpe excludes 0, and
6. Factor-permutation null p < 0.05, and
7. Survives realistic costs.

**FALSIFIED** if it fails at premise (sparse cell / no honest IC), no plateau, dies OOS, fails
significance, loses to buy-and-hold, or is eaten by funding. **INCONCLUSIVE** only if net-positive and
beats benchmark point-estimate but significance is borderline.

## Honest prior (before any PnL)
Phase-1 already shows the favourable cell is sparse (2.8%) and Edge's honest IC is ~0 and **weaker** than
the raw MFI that itself failed the base study. **Expected outcome: FALSIFIED.** Running the full battery
anyway is the legitimate, low-cost closeout of the divergence premise. Goalposts will not move; a clean
negative is the deliverable.
