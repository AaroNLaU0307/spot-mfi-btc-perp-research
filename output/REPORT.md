# Spot-MFI → BTCUSDT-perp alpha investigation — Research report

**Verdict: `FALSIFIED`.** A self-computed cross-exchange spot Money Flow Index shows a weak,
momentum-signed relationship to Binance perp forward returns over the full sample, but the edge **does
not survive out-of-sample, fails the out-of-sample significance tests, and never beats buy-and-hold** —
despite sitting on a plateau of the full-sample parameter grid. Falsification occurs at the
**out-of-sample / significance / benchmark** stage, not at premise or plateau.

> **Factor caveat (load-bearing):** no Glassnode API key was available, so the factor is a
> **self-computed cross-exchange spot MFI proxy** (14-day, `typical price × volume`, volume-weighted
> across Binance/Coinbase/Kraken/Bitstamp/OKX via ccxt), **not** Glassnode's `spot_money_flow_index`.
> A real key requires re-running the whole pipeline on the genuine series and comparing (see Next steps).

---

## 1. Pre-registration — [research/PREREGISTRATION.md](../research/PREREGISTRATION.md)
- **H1 (primary): momentum, LONG-only** — long the perp when smoothed MFI is elevated, flat otherwise.
  Direction chosen from the **IC sign**, not PnL.
- Model **M1** = MFI level threshold `T` × smoothing window `W` (2 knobs). M2 z-score band = robustness.
- **CONFIRMED** required ALL of: net OOS Sharpe ≥ 0.5; **beats buy-and-hold**; contiguous plateau;
  DSR > 0.95 + BH-FDR survival; block-bootstrap CI excludes 0 + permutation p < 0.05; positive OOS;
  edge survives realistic cost. Honest prior stated up front: **expect FALSIFIED / INCONCLUSIVE.**
- The ordering (pre-registration before any PnL) is self-attested: the pre-registration and all results
  were published in one squashed commit. The threshold grid in the pre-registration was edited after the
  results, and three registered robustness checks were not run — see the amendment,
  [research/ERRATUM_2026-09-27.md](../research/ERRATUM_2026-09-27.md) §6.

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
- Full-sample peak **(T=70, W=1) Sharpe 1.07**, and it sits on a **plateau** (3×3
  neighbourhood/peak = 0.85 ≥ 0.80, same-sign) — *not* an isolated spike. The grid is scored over the
  whole 2020-05-11 → 2025-12-31 sample, which contains the entire walk-forward OOS span
  (2021-05-11 → 2025-12-31, 1,696 of the 2,061 days); it is a full-sample statistic, not an in-sample
  one. The per-fold in-sample Sharpes of the selected configs were 1.045–1.764.
- **Embargoed** (14-bar) anchored walk-forward, 5 splits: **aggregated OOS Sharpe 0.294**,
  ann +4.4%, maxDD −34%. Per-fold OOS Sharpe swings **−0.30 → +1.26**; selected params are unstable
  (60/2, 70/10, 75/1, 70/10, 70/1).
- **Benchmark (same OOS span): buy-and-hold perp net of funding (the registered benchmark) 0.313;
  perp price ex-funding 0.457 — the strategy beats neither.** Figures: `figures/phase4_heatmap_M1.png`,
  `figures/phase4_oos_equity.png` (where the price-only series is labelled "BH spot").
- M2 (z-score) robustness OOS Sharpe 0.717 is higher and beats both buy-and-hold series, but M1 is the
  pre-registered primary; switching would be the overfit the pre-registration forbids. Reported as
  sensitivity only — so M2 never went through the Phase-5 bootstrap/permutation tests, and its OOS
  figure is untested.

## 5. Statistical validation (Phase 5) — [phase5_validation.md](phase5_validation.md)

Scored against the seven gates registered in [research/PREREGISTRATION.md](../research/PREREGISTRATION.md)
("Decision rule"):

<!-- gate-table:start (generated by src/gates.py from the phase reports; do not edit) -->
| # | Registered gate | Published statistic | Pass? |
|---|---|---|---|
| 1 | Net OOS Sharpe ≥ 0.5 | 0.294 | FAIL |
| 2 | Net OOS Sharpe > buy-and-hold perp net of funding, same OOS span | 0.294 vs 0.313 (B&H perp price ex-funding: 0.457) | FAIL |
| 3 | Contiguous plateau: 3×3 neighbourhood ≥ 80% of the peak Sharpe, same sign (full-sample grid) | nbhd/peak 0.85, same-sign 1.00 | PASS |
| 4 | DSR > 0.95 (N = grid size) and ≥ 1 BH-FDR survivor at α = 0.05 (full-sample) | DSR 0.959; 0/42 survive | FAIL |
| 5 | Stationary block-bootstrap 95% CI of the OOS Sharpe excludes 0, and permutation null (gross returns) p < 0.05 | CI [-0.720, 1.212]; p = 0.266 | FAIL |
| 6 | Aggregated walk-forward OOS equity positive | ann. return +4.4% | PASS |
| 7 | Breakeven cost > modelled cost (7 bps one-way: fee + slippage) | breakeven > 100 bps one-way | PASS |

**3 of 7 registered gates pass** (3, 6, 7); fail: 1, 2, 4, 5.

*Generated by `src/gates.py` from the statistics published in `phase4_optimize.md`, `phase5_validation.md` and `phase6_costs.md` (at their printed precision); gate list from `research/PREREGISTRATION.md`, thresholds from `config.py`.*
<!-- gate-table:end -->

Gate 4's DSR half passes (0.959 > 0.95) but no config survives BH-FDR (0/42), which sinks the combined
gate. Both halves are full-sample statistics, so they were scored partly on the OOS period; the
out-of-sample gates are the ones that decide: full-sample net Sharpe 1.07 → walk-forward OOS net
Sharpe **0.29**.

## 6. Cost sensitivity (Phase 6) — [phase6_costs.md](phase6_costs.md)
- Activity at real costs: **30 trades**, avg hold **20.6 days**, turnover **10.6/yr**, exposure **30%**
  of days ⇒ **not fee-sensitive**: breakeven one-way cost **> 100 bps**.
- Gross (no fees, no funding) Sharpe 1.29; funding costs ≈ 0.2 Sharpe (1.290 gross → 1.092 net-of-funding
  at 0 bps fees). Fees are **not** the binding constraint — the OOS/benchmark/significance failure is.
  Figure: `figures/phase6_cost_sensitivity.png`.

## 7. Verdict — `FALSIFIED`
Scored against the registered decision rule (§5 table): it passes the plateau, positive-OOS-equity and
cost-ceiling gates and fails the other four — net OOS Sharpe < 0.5, does not beat buy-and-hold,
DSR/BH-FDR selection control fails (BH-FDR 0/42), and the OOS Sharpe CI includes 0 with the
permutation null not significant. The signal is a weak, long-biased
**momentum tilt whose only realised benefit is drawdown reduction**; it is statistically indistinguishable
from luck out-of-sample and adds no risk-adjusted value over simply holding BTC. This matches the
pre-registered honest prior. No decision threshold was changed after the results; the deviations from
the registration are listed in the amendment (§6 of the erratum).

### Threats to validity (kept honest)
- **Proxy ≠ Glassnode.** But the proxy is 0.997-corr with Binance-spot MFI and the cross-exchange
  breadth the premise leaned on proved negligible, so the *specific* divergence premise is weak here
  regardless. The exact Glassnode series could still differ.
- **Single asset, single regime.** 2020–2025 is one long BTC bull; the all-positive-decile confound
  means any long-biased signal looks "okay" for the wrong reason. Benchmark-relative testing controlled
  for this and the signal still failed.
- **Long-only, level model.** A different construction (divergence variant, short side) is untested.
- **The specification saw the OOS period.** The Phase-1 IC, deciles and stationarity checks that fixed
  the direction (long-only momentum) and the grid ranges were computed on the whole panel
  (`run_01_eda.py`), 2020-05-11 → 2025-12-31, which contains the entire walk-forward OOS span. The
  bias favours the hypothesis, so the `FALSIFIED` verdict stands. See
  [research/ERRATUM_2026-09-27.md](../research/ERRATUM_2026-09-27.md).
- **Registered robustness checks not run.** The time-stop and ATR/vol-stop exits and the vol-targeting
  variant registered in the pre-registration were never run.
- **The permutation null runs on gross returns** (observed OOS Sharpe 0.445 vs the net 0.294 in the
  table), so it tests the signal's timing, not the net result.
- **The analysed data cannot be re-pulled.** Kraken's API serves only its latest ~720 daily candles, and
  the cache behind these results is not published; see the README's data section.

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
`run_06_costs.py` (which also regenerates the §5 gate table; `python -m src.gates` does the same from
the committed phase reports alone); `python -m pytest -q`. Deterministic (seed 7).
See `docs/DECISION_LOG.md` and `research/ERRATUM_2026-09-27.md`.*

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
