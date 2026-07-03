# Variant A — Spot-MFI vs Funding Divergence — Research report

**Verdict: `INCONCLUSIVE`, weight of evidence leaning `FALSIFIED`. No tradeable divergence edge
established; no capital allocation warranted.** The Edge signal's walk-forward OOS Sharpe (0.68)
*superficially* beat buy-and-hold spot (0.46) and sat on a plateau, but it **fails both out-of-sample
significance gates**, the Phase-1 honest IC was **~0 (funding adds no predictive information)**, and the
outperformance is **2022-crash-avoidance (beta/drawdown timing) that reversed to negative in 2024–25** —
not persistent alpha. This closes the spot–perp divergence thesis left open by the base study.

> Same disclosed proxy caveat as the base study: MFI is a self-computed cross-exchange proxy, not
> Glassnode's series. Funding is real Binance USDⓈ-M history.

---

## 1. Pre-registration — [research/PREREGISTRATION_variantA.md](../research/PREREGISTRATION_variantA.md)
- **H1: divergence long-quality, LONG-only.** `Edge = pct_rank_W(MFI) − pct_rank_W(daily_funding)`;
  long when `Edge > T`, flat when `Edge < 0`. Funding enters **twice, un-netted**: signal input
  (crowding) + realised holding cost. Direction nominally long (from IC sign).
- **Rejected constructions** (documented): `MFI − z(funding)` (dimensional mismatch), `MFI / funding`
  (explodes at funding's zero-crossings). Rank-differencing is scale-free.
- **Honest prior (pre-PnL): expect FALSIFIED** — the favourable cell is sparse and the Edge IC ~0.

## 2. Phase 1 — the premise mostly failed at the factor level — [variantA_phase1_eda.md](variantA_phase1_eda.md)
- **corr(MFI, funding) = +0.32 (Pearson) / +0.35 (Spearman)**: the two are positively coupled —
  strong spot flow AND crowded longs co-occur — so the "real demand vs leveraged greed" **divergence is
  rare**.
- **Favourable cell (MFI_rank>0.8 & Fund_rank<0.2) = 2.8% of days** (SPARSE) — the most informative
  observations are scarce, capping the premise from the start.
- **Edge honest (non-overlapping) IC is ~0 and *smaller* than raw MFI at every horizon** (Edge_W90:
  −0.003…+0.023, all p>0.73; raw MFI +0.02…+0.09). **Funding does not add predictive information; it
  degrades the already-insignificant MFI momentum.** Figures: `variantA_joint_dist.png`,
  `variantA_ic_compare.png`.

## 3. Phase 4 — optimisation + walk-forward — [variantA_phase4.md](variantA_phase4.md)
- Grid **N = 36** (T×W). In-sample peak **(T=0.5, W=252) Sharpe 1.079**, on a **plateau** (nbhd/peak 0.88).
- Embargoed walk-forward (embargo 14): **aggregated OOS Sharpe 0.684**, ann +14.9%, maxDD −26% — and it
  **beats BH-spot (0.457)**. On its face, the strongest result in the whole program.
- **But the OOS is not persistent — Sharpe by year: 2021 +0.89 · 2022 +1.41 · 2023 +1.99 · 2024 −0.99 ·
  2025 −0.32.** The equity curve (`variantA_oos_equity.png`) shows *all* the outperformance was built by
  **sitting flat through the 2022 crash**; from 2024 it stagnates while spot rallies to close the gap.
  Selected params are unstable across folds (0.2/60 → 0.6/180 → 0.6/180 → 0.5/252 → 0.5/180 across the
  5 splits).

## 4. Phase 5 — significance — [variantA_phase5.md](variantA_phase5.md)

| Gate (pre-registered) | Result | Pass? |
|---|---|---|
| 1. Net OOS Sharpe ≥ 0.5 | 0.684 | ✅ |
| 2. Beats buy-and-hold spot OOS | 0.68 vs 0.46 | ✅ |
| 3. Contiguous plateau (not spike) | nbhd/peak 0.88 | ✅ |
| 4. DSR > 0.95 **and** BH-FDR survivor | 0.961 / **28-of-36** *(in-sample)* | ✅ |
| **5. Block-bootstrap 95% CI excludes 0** | **[−0.19, 1.62]** (frac>0 0.94) | ❌ |
| **6. Permutation null p < 0.05** | **p = 0.10** (obs 0.77 < null p95 0.90) | ❌ |
| 7. Survives realistic cost | breakeven >100 bps | ✅ |

**5 of 7 pass, but the two out-of-sample significance gates fail.** The in-sample DSR/BH-FDR passes are
exactly the flattering in-sample artifacts the OOS tests exist to catch (in-sample Sharpe 1.08 → the OOS
aggregate is not distinguishable from luck: permutation p=0.10, CI includes 0).

## 5. Phase 6 — costs — [variantA_phase6.md](variantA_phase6.md)
Turnover low → not fee-sensitive (breakeven >100 bps one-way). Gross Sharpe 1.18 vs BH-spot 0.99.
Binding constraint is significance/persistence, not cost.

## 6. Verdict — `INCONCLUSIVE`, leaning `FALSIFIED`
Against the frozen rule, CONFIRMED requires **all** seven gates; it **fails gates 5 and 6** → **not
CONFIRMED**. Per the pre-registered letter it is **INCONCLUSIVE** (net-positive, beats benchmark
point-estimate, significance borderline — CI barely includes 0, permutation p=0.10). But three
independent facts push the honest reading to **FALSIFIED**:
1. **Premise failed at the factor level** — Edge honest IC ~0 and *weaker* than the raw MFI that already
   failed; funding added no information (pre-registered FALSIFIED trigger).
2. **Not persistent** — OOS Sharpe reversed from strongly positive (2021–23) to negative (2024–25).
3. **Mechanism is not alpha** — the outperformance is 2022 drawdown-avoidance (a long-only defensive
   overlay dodging one crash), fully consistent with a zero rank-IC.

**Bottom line: the spot-MFI-vs-funding divergence is not a tradeable edge.** The one benchmark-beating
number in the program is an artifact of a single crash-avoidance episode, not repeatable signal.

### Why this is a *stronger* negative than the base study
The base study failed cleanly on every OOS metric. Variant A is more instructive: it shows how a
long-only defensive posture in a bull market can *manufacture* a benchmark-beating in-sample+early-OOS
Sharpe that **survives plateau and in-sample DSR yet dies under block-bootstrap, permutation, and
out-of-sample persistence checks.** That is the exact failure mode the falsification battery is built to
expose — a portfolio-worthy demonstration.

## 7. Next steps (if revisited)
1. Re-run on the **real Glassnode `spot_money_flow_index`** (both studies).
2. Frame the drawdown-avoidance property honestly as a **risk overlay** (benchmarked vs vol-targeting),
   not standalone alpha — it is the only real, if non-persistent, effect found.
3. Broaden **universe + regimes** (ETH/alts, a full bear) to break the BTC-uptrend/one-crash confound.

---
*Reproduce: `run_A1_eda.py` → (freeze pre-reg) → `run_A4_optimize.py` → `run_A5_validate.py` →
`run_A6_costs.py`; `python -m pytest -q` (59 pass, full repo suite). Deterministic (seed 7).
See `docs/DECISION_LOG.md`.*

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
