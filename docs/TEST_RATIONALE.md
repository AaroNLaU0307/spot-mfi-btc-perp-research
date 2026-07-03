# Test-selection rationale

Every statistical test used in this research program, its purpose, and — for tests an interviewer
might expect but won't find here — why it was deliberately left out. Judgement shows up in this table,
not in the raw count of tests run.

## Tests run

| Test | Purpose | Where |
|---|---|---|
| Spearman IC (overlapping + non-overlapping) | Sign/shape of the factor's raw predictive structure, before any strategy is built | Phase 1 EDA, both studies |
| Decile bucket analysis | Reveals monotone (momentum) vs U/∩ (mean-reversion) shape; detects uptrend confounds | Phase 1 EDA, both studies |
| ADF / KPSS | Stationarity of the factor level and its first difference | Phase 1 EDA (base study) |
| Sharpe heatmap + 3×3 plateau/neighbourhood ratio | Anti-spike: rejects a parameter choice that isn't robust to small perturbations | Phase 4, both studies |
| Embargoed walk-forward (anchored, 5 splits, embargo ≥14 bars) | The verdict number — genuine out-of-sample, no train/test boundary leakage. No separate purge step: config selection uses trailing in-sample Sharpe with no forward-looking labels, so the embargo gap is the whole guarantee (see `docs/AUDIT.md`) | Phase 4, both studies |
| Deflated / Probabilistic Sharpe Ratio (Bailey–López de Prado) | Is the in-sample-best config's Sharpe real once deflated for the breadth of the grid searched (N trials)? | Phase 5, both studies |
| Benjamini–Hochberg FDR | Multiple-testing control across every config in the grid | Phase 5, both studies |
| Stationary block bootstrap (Politis–Romano) | OOS Sharpe confidence interval that respects daily-return autocorrelation (does the CI exclude 0?) | Phase 5, both studies |
| Factor-permutation null | Block-shuffles the position series against the fixed market return to build a luck distribution; is the OOS Sharpe outside it? | Phase 5, both studies |
| Cost-sensitivity sweep + breakeven ceiling | Does the edge survive realistic fees/slippage/funding, and how much cost could it absorb? | Phase 6, both studies |
| **PBO via CSCV** (Bailey–Borwein–López de Prado–Zhu) | Probability the *selection process itself* (picking the IS-best config) is overfit, across all C(S,S/2) combinatorial train/test partitions of the grid | Phase B2, post-hoc, both studies |
| **CPCV OOS-Sharpe distribution** | Contextualises the single walk-forward OOS number as one draw among the full combinatorial spread, not "the" answer | Phase B2, post-hoc, both studies |
| Descriptive extension (Sortino, skew, excess kurtosis, VaR/CVaR, longest drawdown) | Fuller risk/return picture. Descriptive only — no verdict weight | Phase B2, post-hoc, both studies |

## Tests considered and deliberately not run

| Test | Why not |
|---|---|
| White's Reality Check / Hansen's SPA | Same purpose as BH-FDR + the factor-permutation null in this design: adjusting a "best-of-many" result for data-snooping. RC/SPA's main added value over BH-FDR is modelling the *cross-config correlation structure* directly — here that structure is already captured two ways: the DSR's deflation term uses the cross-config Sharpe variance, and CSCV/PBO (Phase B2) resamples the actual joint return matrix combinatorially. A third data-snooping correction on top would be duplicative for the marginal information gained. |
| Trade-level (per-trade) bootstrap | Dominated by the stationary block bootstrap for this specific design: a ~11–22 day average holding period on daily bars with a 14–21 day block length already captures the autocorrelation a trade-level resample would target, at much higher trade counts (~30–31 trades total per study) than a per-trade bootstrap could support without extreme resampling noise. |
| Capacity / market-impact modelling | Out of scope at research scale. This is a signal-falsification study, not a live-deployment sizing exercise — capacity only becomes a relevant question once a strategy is confirmed and heading toward real capital, which did not happen in either study (both verdicts are negative). |
| Full k-fold Combinatorial Purged CV (CPCV) with model refitting per fold | The brief's original "gold standard, optional" note. Approximated here via CSCV/PBO (Phase B2), which reuses the frozen grid's pre-computed daily return series rather than refitting a model per combinatorial fold — appropriate because the signal has no fitted parameters beyond the frozen (threshold, window) grid itself; there is no separate "model" to refit. |

## Program-level multiplicity

The two studies form one research family: 2 pre-registered hypotheses, 42 (base) + 36 (Variant A) = 78
grid configurations tested in total. Neither study's within-study BH-FDR/DSR correction accounts for
this program-level breadth. A family-wise correction spanning both hypotheses would only raise the
significance bar further — since both verdicts are already negative (`FALSIFIED` / `INCONCLUSIVE`
leaning `FALSIFIED`) under their own within-study corrections, a program-level correction cannot change
either verdict; it can only strengthen the case for the negative reading. No such computation is needed
to reach that conclusion.
