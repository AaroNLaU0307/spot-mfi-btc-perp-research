# Spot-MFI → BTCUSDT-perp alpha investigation — Research report

**Verdict: `FALSIFIED`.** A self-computed cross-exchange spot Money Flow Index shows a weak,
momentum-signed relationship to Binance perp forward returns in-sample, but the edge **does not
survive out-of-sample, fails every significance test, and never beats buy-and-hold** — despite
sitting on a genuine in-sample parameter plateau. Falsification occurs at the **out-of-sample /
significance / benchmark** stage, not at premise or plateau.

> **Factor caveat (load-bearing):** no Glassnode API key was available, so the factor is a
> **self-computed cross-exchange spot MFI proxy** (14-day, `typical price × volume`, volume-weighted
> across Binance/Coinbase/Kraken/Bitstamp/OKX via ccxt), **not** Glassnode's `spot_money_flow_index`.
> A real key requires re-running the whole pipeline on the genuine series and comparing (see Next steps).

---

## 1. Pre-registration (frozen before any PnL) — [research/PREREGISTRATION.md](../research/PREREGISTRATION.md)
- **H1 (primary): momentum, LONG-only** — long the perp when smoothed MFI is elevated, flat otherwise.
  Direction chosen from the **IC sign**, not PnL.
- Model **M1** = MFI level threshold `T` × smoothing window `W` (2 knobs). M2 z-score band = robustness.
- **CONFIRMED** required ALL of: net OOS Sharpe ≥ 0.5; **beats buy-and-hold**; contiguous plateau;
  DSR > 0.95 + BH-FDR survival; block-bootstrap CI excludes 0 + permutation p < 0.05; positive OOS;
  edge survives realistic cost. Honest prior stated up front: **expect FALSIFIED / INCONCLUSIVE.**

## 2. Data integrity (Phase 0) — [phase0_integrity.md](phase0_integrity.md)
- Panel **2061 daily bars**, 2020-05-11 → 2025-12-31, **0 missing days, 0 NaNs**.
- Spot: Binance/Coinbase/Bitstamp/OKX full; **Kraken joins 2024-07** (API history limit; disclosed,
  never filled). Perp OHLCV + 8h funding from Binance USDⓈ-M REST.
- **Funding ≈ +12.5%/yr paid by longs** — material for a long strategy.
- **Finding:** the cross-exchange MFI is **0.997-correlated with single-Binance MFI** (Binance
  dominates spot volume), so "cross-exchange breadth" adds little and the *divergence* premise is
  partly undercut. Figures: `figures/phase0_*`.

## 3. Factor EDA (Phase 1) — [phase1_eda.md](phase1_eda.md)
- Level IC vs perp forward returns is **positive, rising with horizon** (1d +0.02 → 10d +0.06 →
  **21d +0.16**); peak at 21d. ⇒ **mean-reversion-at-extremes (angle A) is falsified by sign**
  (high MFI → continuation, not reversal).
- **Honest non-overlapping IC is not significant** anywhere (p ≈ 0.30–0.46); naive 10/21d significance
  is an overlap artifact.
- Deciles monotone-ish (top MFI decile highest) and **nearly all positive** (10/10 at the 10d horizon;
  a few tiny negative exceptions elsewhere, e.g. decile 1 at 21d is −0.64% against a +8.31% top decile)
  — a BTC-uptrend confound; low MFI does not predict *meaningfully* negative returns ⇒ **long-only**
  (shorting would fight the trend). MFI level is stationary (ADF p≈0), persistent (ACF₁≈0.95).
  Figures: `figures/phase1_*`.

## 4. Optimisation + walk-forward (Phase 4) — [phase4_optimize.md](phase4_optimize.md)
- Grid **N = 42** (T ∈ {60,65,70,75,80,85,90} × W ∈ {1,2,3,5,7,10}; `config.GRID_LEVEL_THRESHOLDS`).
- In-sample peak **(T=70, W=1) Sharpe 1.07**, and it sits on a **genuine plateau** (3×3
  neighbourhood/peak = 0.85 ≥ 0.80, same-sign) — *not* an isolated spike.
- **Embargoed** (14-bar) anchored walk-forward, 5 splits: **aggregated OOS Sharpe 0.294**,
  ann +4.4%, maxDD −34%. Per-fold OOS Sharpe swings **−0.30 → +1.26**; selected params are unstable
  (60/2, 70/10, 75/1, 70/10, 70/1).
- **Benchmark (same OOS span): BH-spot Sharpe 0.457, BH-perp 0.313 — the strategy beats neither.**
  Figures: `figures/phase4_heatmap_M1.png`, `figures/phase4_oos_equity.png`.
- M2 (z-score) robustness OOS Sharpe 0.72 is higher, but M1 is the pre-registered primary; switching
  would be the overfit the pre-registration forbids. Reported as sensitivity only.

## 5. Statistical validation (Phase 5) — [phase5_validation.md](phase5_validation.md)

Scored against the 7 gates frozen in [research/PREREGISTRATION.md](../research/PREREGISTRATION.md):

| Gate (pre-registered) | Result | Pass? |
|---|---|---|
| 1. Net OOS Sharpe ≥ 0.5 | 0.294 | ❌ |
| 2. Beats buy-and-hold spot OOS | 0.29 vs 0.46 | ❌ |
| 3. Contiguous plateau (not spike) | nbhd/peak 0.85 | ✅ |
| 4. DSR > 0.95 **and** BH-FDR survivor | 0.959 / **0-of-42** *(in-sample)* | ❌ |
| 5. Block-bootstrap 95% CI excludes 0 | **[−0.72, 1.21]** (frac>0 0.71) | ❌ |
| 6. Permutation null p < 0.05 | **p = 0.27** | ❌ |
| 7. Survives realistic cost | breakeven >100 bps | ✅ |

**2 of 7 gates pass; the two out-of-sample significance gates (5, 6) and the benchmark test (2) all
fail.** Gate 4's DSR half passes in-sample (0.959 > 0.95) but BH-FDR survivors = 0/42 sinks the combined
gate — exactly the flattering in-sample artifact the OOS tests exist to catch: in-sample gross Sharpe
1.29 → **OOS 0.29**.

## 6. Cost sensitivity (Phase 6) — [phase6_costs.md](phase6_costs.md)
- Activity at real costs: **30 trades**, avg hold **20.6 days**, turnover **10.6/yr**, exposure **30%**
  of days ⇒ **not fee-sensitive**: breakeven one-way cost **> 100 bps**.
- Gross (no fees, no funding) Sharpe 1.29; funding costs ≈ 0.2 Sharpe (1.290 gross → 1.092 net-of-funding
  at 0 bps fees). Fees are **not** the binding constraint — the OOS/benchmark/significance failure is.
  Figure: `figures/phase6_cost_sensitivity.png`.

## 7. Verdict — `FALSIFIED`
Scored against the frozen decision rule (table above): **2 of 7 gates pass** (plateau, cost-robustness);
**5 of 7 FAIL** — net OOS Sharpe < 0.5, does not beat buy-and-hold, DSR/BH-FDR selection control fails
(BH-FDR 0/42), OOS Sharpe CI includes 0, permutation not significant. The signal is a weak, long-biased
**momentum tilt whose only realised benefit is drawdown reduction**; it is statistically indistinguishable
from luck out-of-sample and adds no risk-adjusted value over simply holding BTC. This matches the
pre-registered honest prior. **No goalposts were moved.**

### Threats to validity (kept honest)
- **Proxy ≠ Glassnode.** But the proxy is 0.997-corr with Binance-spot MFI and the cross-exchange
  breadth the premise leaned on proved negligible, so the *specific* divergence premise is weak here
  regardless. The exact Glassnode series could still differ.
- **Single asset, single regime.** 2020–2025 is one long BTC bull; the all-positive-decile confound
  means any long-biased signal looks "okay" for the wrong reason. Benchmark-relative testing controlled
  for this and the signal still failed.
- **Long-only, level model.** A different construction (divergence variant, short side) is untested.

## 8. Next steps (if revisited)
1. **Re-run on the real Glassnode `spot_money_flow_index`** once a key exists; compare to this proxy.
2. Test **variant C (spot–perp divergence)** explicitly: spot MFI *minus* a perp-derived feature
   (funding or perp momentum) — the one angle not yet adjudicated, and the premise's original intent.
3. Broaden the **universe** (ETH, alts) and **regimes** (include a full bear) to break the uptrend
   confound; consider cross-sectional rather than time-series deployment.
4. If pursued as risk management (not alpha): the drawdown-reduction property is real but should be
   framed and benchmarked as an overlay, not a standalone edge.

---
*Reproduce: `run_00_data.py` → `run_01_eda.py` → `run_04_optimize.py` → `run_05_validate.py` →
`run_06_costs.py`; `python -m pytest -q` (59 pass, full repo suite). Deterministic (seed 7).
See `docs/DECISION_LOG.md`.*

## Post-hoc supplementary validation (added after verdict)

> Computed AFTER the verdict above was already decided by the pre-registered gates. This
> section cannot revise that verdict, strengthen it, or rehabilitate a negative result even if
> a number below looks favourable — it is the deferred "optional, gold standard" PBO/CPCV test,
> closing the one item the original brief left open. See `docs/DECISION_LOG.md` and `src/pbo.py`
> for the exact method (CSCV, Bailey-Borwein-LdP-Zhu 2017) and purge convention.

**PBO (S=16, purge=14):** **0.720** (S-sensitivity range **0.671–0.720** across S={8,12,16}; table below) over 12870/12870 valid combinatorial splits (C(16,8)) — i.e. in 72% of splits, the config picked as best in-sample ranked *below the out-of-sample median* among all frozen configs. High PBO reinforces the verdict above.

S-sensitivity (so the headline isn't S-picked):

| S | splits used | PBO |
|---:|---:|---:|
| 8 | 70/70 | 0.671 |
| 12 | 924/924 | 0.705 |
| 16 | 12870/12870 | 0.720 |

**CPCV OOS-Sharpe distribution** of the per-split IS-selected config (S=16, n=12870): median **0.581**, IQR [0.306, 0.825], range [-0.940, 1.793].
- The single walk-forward path's OOS Sharpe (**0.294**, "base-study WF OOS") sits at the **24th percentile** of this distribution — one chronological draw among many combinatorial train/test partitions, not "the" answer.
- **Caveat (read this before drawing any conclusion from the median):** both this distribution and the walk-forward path re-select the in-sample-best config independently per split/fold — neither is one fixed config's OOS Sharpe evaluated repeatedly (the picked config varies across the 12870 splits here exactly as it varied across the walk-forward's 5 folds). The real asymmetry is combinatorial breadth versus chronological order, not selection-vs-no-selection: most CSCV splits let blocks that are chronologically *after* the walk-forward's test window serve as "training" — an ordering no live sequential strategy could ever trade. The CPCV median is a description of the *selection process's* spread under that broader, partly unrealisable set of partitions, not a higher, more-representative, or more-tradeable Sharpe estimate than the actual walk-forward. It does not revise, soften, or rehabilitate the verdict above; the high PBO alongside it points the same direction the verdict does.

Figures: `figures/pbo_logit_hist_base.png`, `figures/pbo_degradation_scatter_base.png`

**Descriptive-stats extension** (walk-forward OOS net returns; descriptive only, no verdict weight):

| Sortino | Calmar | skew | excess kurtosis | daily VaR 95% | daily CVaR 95% | longest DD (days) |
|---:|---:|---:|---:|---:|---:|---:|
| 0.43 | 0.13 | 0.02 | 18.47 | 1.75% | 3.61% | 858 |
