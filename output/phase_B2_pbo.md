# Phase B2 — PBO (CSCV) + CPCV OOS-Sharpe distribution

Post-hoc supplementary validation, added after both verdicts. See each study's appended section in `output/REPORT.md` / `output/REPORT_variantA.md` for the full write-up.

## Base study
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
## Variant A
## Post-hoc supplementary validation (added after verdict)

> Computed AFTER the verdict above was already decided by the pre-registered gates. This
> section cannot revise that verdict, strengthen it, or rehabilitate a negative result even if
> a number below looks favourable — it is the deferred "optional, gold standard" PBO/CPCV test,
> closing the one item the original brief left open. See `docs/DECISION_LOG.md` and `src/pbo.py`
> for the exact method (CSCV, Bailey-Borwein-LdP-Zhu 2017) and purge convention.

**PBO (S=16, purge=14):** **0.842** (S-sensitivity range **0.790–0.943** across S={8,12,16}; table below) over 12870/12870 valid combinatorial splits (C(16,8)) — i.e. in 84% of splits, the config picked as best in-sample ranked *below the out-of-sample median* among all frozen configs. High PBO reinforces the verdict above.

S-sensitivity (so the headline isn't S-picked):

| S | splits used | PBO |
|---:|---:|---:|
| 8 | 70/70 | 0.943 |
| 12 | 924/924 | 0.790 |
| 16 | 12870/12870 | 0.842 |

**CPCV OOS-Sharpe distribution** of the per-split IS-selected config (S=16, n=12870): median **0.675**, IQR [0.406, 0.942], range [-1.230, 2.123].
- The single walk-forward path's OOS Sharpe (**0.684**, "Variant-A WF OOS") sits at the **51st percentile** of this distribution — one chronological draw among many combinatorial train/test partitions, not "the" answer.
- **Caveat (read this before drawing any conclusion from the median):** both this distribution and the walk-forward path re-select the in-sample-best config independently per split/fold — neither is one fixed config's OOS Sharpe evaluated repeatedly (the picked config varies across the 12870 splits here exactly as it varied across the walk-forward's 5 folds). The real asymmetry is combinatorial breadth versus chronological order, not selection-vs-no-selection: most CSCV splits let blocks that are chronologically *after* the walk-forward's test window serve as "training" — an ordering no live sequential strategy could ever trade. The CPCV median is a description of the *selection process's* spread under that broader, partly unrealisable set of partitions, not a higher, more-representative, or more-tradeable Sharpe estimate than the actual walk-forward. It does not revise, soften, or rehabilitate the verdict above; the high PBO alongside it points the same direction the verdict does.

Figures: `figures/pbo_logit_hist_variantA.png`, `figures/pbo_degradation_scatter_variantA.png`

**Descriptive-stats extension** (walk-forward OOS net returns; descriptive only, no verdict weight):

| Sortino | Calmar | skew | excess kurtosis | daily VaR 95% | daily CVaR 95% | longest DD (days) |
|---:|---:|---:|---:|---:|---:|---:|
| 1.09 | 0.57 | 1.27 | 24.92 | 1.12% | 3.07% | 492 |
## Program-level multiplicity

The two studies form one research family: 2 pre-registered hypotheses, 42 (base) + 36 (Variant A) = **78 grid configurations tested in total**. Neither study's within-study BH-FDR/DSR correction accounts for this program-level breadth. A family-wise correction spanning both hypotheses would only raise the significance bar further — since both verdicts are already negative (`FALSIFIED` / `INCONCLUSIVE` leaning `FALSIFIED`) under their own within-study corrections, a program-level correction cannot change either verdict; it can only strengthen the case for the negative reading. No such computation is needed to reach that conclusion. See `docs/TEST_RATIONALE.md` for the full test-selection rationale, including tests considered and deliberately not run.
