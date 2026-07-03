# Decision log

Every design fork and why we took each branch. Append-only; newest at the bottom.

---

## 2026-07-01 — Phase 0 setup

**D0.1 — Prerequisites absent → resolved by user decision.**
The brief assumed `adrs-extension` (library) and a Glassnode API key were installed. Verification found
**neither** on the machine: `adrs-extension` is not pip-installed, not importable (`adrs`/`adrs_extension`
→ NOT FOUND), and absent from all 7 sibling venvs and the whole Desktop; no Glassnode key in any `.env`
or env var (only an unrelated `OPENAI_API_KEY`). Per the brief's STOP rule we halted and asked.
- **Library →** vendor validated utilities from the user's own repos (`multi-asset-tsmom-research`,
  `MTF Analysis`); copy (not cross-import) and re-test. Rationale: lowest bug risk (battle-tested), keeps
  stats conventions comparable to prior work.
- **Data →** no key, so build a **self-computed cross-exchange spot MFI proxy** (NOT single-venue Binance
  spot, which would gut the spot-vs-perp divergence premise since Binance spot/perp are the same venue).

**D0.2 — Network egress verified.** PyPI + Binance(.com & .vision) + Coinbase + Kraken + Bitstamp + OKX
all return HTTP 200; Binance is not geo-blocked here. Cross-exchange pull via `ccxt` is feasible. The
no-fabrication gate passes (real data is reachable).

**D0.3 — Vendor audit (read the source).**
- DSR/PSR/`expected_max_sharpe`/BH-FDR **already exist** in `xsmom_stats.py` and MTF `stats.py`
  (closed-form Bailey-López de Prado). Correcting the prior assumption that DSR was missing — it is NOT.
  Decision: vendor + unit-test rather than clean-room.
- Bootstrap CI, regime/subperiod, Monte-Carlo (shuffle+bootstrap) present (`validation.py`) — reusable,
  adapted to daily.
- **Genuinely new (must build):** (a) a real **purged + embargoed walk-forward optimiser** — the existing
  `walk_forward_by_year` is fixed-param sequential-OOS *consistency*, not parameter selection, and has no
  purge/embargo; (b) **stationary block bootstrap** (Politis-Romano) Sharpe CI; (c) **factor-permutation
  null**; plus all domain code (ccxt ingestion, cross-exchange MFI, signals, daily backtester w/ funding).

**D0.4 — Conventions adopted.** Daily annualisation `PERIODS_PER_YEAR = 365` (crypto, no weekend gap);
`RANDOM_SEED = 7`, `BOOTSTRAP_N = PERMUTATION_N = 10_000`, `CI_LEVEL = 95` (match sibling repos);
`FACTOR_LAG_BARS = 1`, `EXECUTION = next_open`; `EMBARGO_BARS = PURGE_BARS = MFI_PERIOD = 14`.

**D0.5 — Spot venues.** Binance, Coinbase, Kraken, Bitstamp, OKX (reputable, low-wash-volume USD/USDT).
A venue below `VENUE_MIN_YEAR_COVERAGE` in a year is dropped for that year and disclosed; never filled.

---

## 2026-07-01 — Phase 1 EDA + pre-registration

**D1.1 — Direction from IC (not PnL).** Level IC vs perp forward returns is positive and rises with
horizon (1d +0.021 → 21d +0.156), so **(A) mean-reversion-at-extremes is falsified by sign** (high MFI →
continuation, not reversal). Honest non-overlapping IC is **not significant** (p≈0.30–0.46); the naive
10/21d significance is an overlap artifact. Deciles are monotone-ish (top decile highest) and *nearly*
all positive (10/10 at 10d; a few tiny negative exceptions elsewhere, e.g. −0.64% vs a +8.31% top decile
at 21d) → BTC-uptrend confound (shorting low-MFI would fight the trend, and the downside is negligible).

**D1.2 — Primary hypothesis = (B) momentum, LONG-only.** Chosen from the positive IC sign + the decile
asymmetry (low MFI not bearish). Model M1 = MFI-level threshold long-only (grid `T`×smoothing `W`); M2 =
z-score band (robustness). Holding ≈ 10–21d (IC decay). Frozen in `research/PREREGISTRATION.md`.

**D1.3 — Benchmark-aware decision rule.** Because the strategy is long-only in a bull market, CONFIRMED
requires it to **beat buy-and-hold net Sharpe** (not merely beat zero), on top of plateau + DSR/BH-FDR +
block-bootstrap CI + permutation + positive OOS + surviving realistic costs. Honest prior stated up
front: expect **FALSIFIED / INCONCLUSIVE**.

**D1.4 — Windows encoding.** Run scripts `sys.stdout.reconfigure(utf-8)` (console is cp1252); report
files always written UTF-8.

Block length set to **21** (IC-decay anchored). Grid **N=42**. No venue drops (Kraken included where it
has genuine coverage, from 2024-07).

---

## 2026-07-01 — Phases 4–6 + verdict

**D2.1 — Purged walk-forward.** Anchored, 5 splits, embargo=14 (=MFI window). Each config's full-sample
net series is precomputed once (causal) and sliced to IS/OOS — no per-split refit, no leakage. In-sample
peak (T=70,W=1) Sharpe 1.07 on a **plateau** (nbhd/peak 0.85), but **OOS Sharpe 0.294 < BH-spot 0.457**.

**D2.2 — Significance.** In-sample DSR 0.959 (marginal, N=42) but BH-FDR **0/42**; OOS PSR 0.737,
block-bootstrap 95% CI **[−0.72, 1.21]** (includes 0), permutation **p=0.27**. OOS ≈ luck.

**D2.3 — Costs.** Turnover ~10/yr → breakeven **>100 bps** one-way (not fee-sensitive). Gross Sharpe
1.29; funding ~0.2 Sharpe drag. Binding constraint is OOS/benchmark, not cost.

**D2.4 — VERDICT = FALSIFIED.** Plateau ✓ + cost-robust ✓, but fails net-Sharpe≥0.5, beat-benchmark,
DSR/BH-FDR, bootstrap-CI-excludes-0, and permutation. A weak long-biased momentum tilt whose only
realised benefit is drawdown reduction — no risk-adjusted alpha vs holding BTC. Matches the
pre-registered prior; goalposts unmoved. Full report: `output/REPORT.md`.

---

## 2026-07-01 — Variant A (spot-MFI vs funding divergence) — closes the divergence premise

**DA.1 — New factor, reused engine.** `Edge = trailing pct_rank(MFI) − pct_rank(daily funding)`. Reused
backtester / stats / purged-WF unchanged; new code only in `src/divergence.py` (+5 tests) and
`run_A1/A4/A5/A6`. Funding used TWICE (signal input + realised cost), not netted. Pre-registered
percentile-rank construction (rejected `MFI−z(funding)` and `MFI/funding` as unsound).

**DA.2 — Phase-1 premise mostly dead (pre-PnL).** corr(MFI,funding)=+0.32 (Pearson)/+0.35 (Spearman);
favourable divergence cell 2.8% (SPARSE); Edge honest IC ~0 and **weaker than raw MFI** at every horizon
(p>0.73). Funding adds no predictive information.

**DA.3 — Surprise OOS, then debunked.** Purged-WF OOS Sharpe **0.684 beat BH-spot 0.457**, plateau PASS
(0.88), in-sample DSR 0.961 + BH-FDR 28/36 — the best-looking result in the program. BUT block-bootstrap
95% CI **[−0.19, 1.62] includes 0**, permutation **p=0.10**, and OOS Sharpe by year
+0.89/+1.41/+1.99/**−0.99**/**−0.32** (reversed 2024–25). Outperformance = 2022 crash-avoidance
(beta/drawdown timing), not alpha. Fails gates 5 & 6 of 7.

**DA.4 — VERDICT = INCONCLUSIVE, leaning FALSIFIED.** Not a tradeable edge; the only real effect is a
non-persistent defensive/drawdown-avoidance property. Demonstrates how a long-only bull-market posture
manufactures a benchmark-beating in-sample/early-OOS Sharpe that dies under block-bootstrap/permutation/
persistence. Report: `output/REPORT_variantA.md`.

---

## 2026-07-04 — Final pre-publication audit (adversarial pass, both studies)

**AUD.1 — Claim-evidence integrity fixes (Phase A).** Traced every quantitative claim in
README/REPORT*/PREREGISTRATION*/DECISION_LOG to its generating artifact. Found and fixed:
(a) "every decile's mean forward return is positive" was FALSE — 1d/5d/21d each have 1-2 tiny negative
deciles (only 10d is fully positive); reworded to the accurate "nearly all positive, negligible
exceptions" in PREREGISTRATION.md, REPORT.md, and this log's D1.1.
(b) grid-range transcription error — PREREGISTRATION.md/REPORT.md said `T∈{55..85}` but the actually
frozen/executed grid (`config.GRID_LEVEL_THRESHOLDS`) is `{60..90}`; fixed both to match config.py
(source of truth).
(c) REPORT.md's Phase-5 gate table split gate 4 into two rows, making "5 of 7 FAIL" unreconcilable
against the shown table; restructured to one-row-per-pre-registered-gate (matches REPORT_variantA.md's
already-correct format) — count now reconciles exactly (2 pass / 5 fail).
(d) "Turnover ≈10/yr" was real but untraced to any artifact; verified via the unmodified backtest engine
on cached data (10.6/yr base, 11.0/yr Variant A) and added to phase6 reports.
(e) unqualified "+0.35" correlation headline (Spearman; Pearson is +0.32) tightened to show both,
in 3 files. (f) numpy scalar reprs (`np.int64(70)`) were leaking into 2 figure titles (truncating them)
and 2 markdown reports; fixed at the source (`walkforward.plateau_metric`) and regenerated.
Verified clean (no fix needed): verdict wording consistency, gate-4 in-sample labelling, test/grid/row
counts, figure-vs-claim visual match (spot-checked 5 figures incl. the required variantA OOS-equity
2021-23-gap/2024-25-stagnation check).

**AUD.2 — Methodology re-verification (Phase B).** Confirmed in code + added missing tests
(`tests/test_walkforward.py` [8 new], `tests/test_eda.py` [5 new]): purge+embargo gap invariant
(previously untested — `PURGE_BARS` was defined but never wired into any function; confirmed
architecturally redundant with `EMBARGO_BARS` here since IS-selection uses no forward-looking labels,
documented explicitly in config.py), plateau/spike detection, trailing-only EDA transforms, factor-lag
mechanics (already covered via the shared `run_backtest` code path — no duplicate test needed).
Determinism: reran the RNG-dependent stats layer (`run_05/A5_validate.py`) twice back-to-back, bit-
identical outputs; the grid/walk-forward layer has no RNG (confirmed byte-identical across 3 independent
regenerations during AUD.1's fixes). Debris: removed 2 genuine unused imports (`numpy` in
`backtest.py`, `run_00_data.py`) found via an AST-based scan; no TODO/FIXME/commented-out code found.

**AUD.3 — Phase B2: PBO via CSCV + CPCV (the one sanctioned new computation).** New `src/pbo.py`
(Bailey-Borwein-LdP-Zhu 2017), purging `EMBARGO_BARS` at every combinatorial train/test block boundary
(train side only, matching this repo's existing embargo convention). Implementation risk control: 2
mandatory synthetic sanity checks BEFORE reporting any real number — pure-noise matrix -> PBO≈0.5 (30
draws averaged; a single draw showed 0.64-0.74, legitimate small-sample variance from correlated
combinatorial splits sharing one data realisation, NOT a bug, confirmed via 12-draw Monte Carlo probe)
and a planted-dominant-strategy matrix -> PBO<0.10 (got 0.00-0.16 across S=8/12/16) — both pass
(`tests/test_pbo.py`). Sanity tests run at S=8 for CI speed (4min->2.6s suite runtime) after confirming
the property holds at S=16 too during development. Production result (S=16, both studies' frozen
grids): **base study PBO=0.720** (S-sens: S=8:0.671, S=12:0.705, S=16:0.720); **Variant A PBO=0.842**
(S-sens: 0.943/0.790/0.842) — both HIGH, independently corroborating both existing negative verdicts.
Verdicts NOT revised (per the hard rule): appended as clearly-marked "Post-hoc supplementary
validation" sections to both REPORT*.md files, with an explicit caveat guarding against misreading the
CPCV median (base 0.581, above the realised WF path's 0.294) as rehabilitating the FALSIFIED verdict —
most CSCV splits use orderings no live sequential strategy could trade, so the median describes the
selection process's spread, not an achievable Sharpe. Also added: descriptive-stats extension
(Sortino/Calmar/skew/kurtosis/VaR/CVaR/longest-DD, `performance.extended_metrics`, 11 new tests),
program-level multiplicity note, and `docs/TEST_RATIONALE.md` (tests run vs deliberately not run, with
reasons).

**AUD.4 — Final counts.** Test suite 26 -> **59** (13 new in Phase B, 20 new in Phase B2). All prior
"(26 pass)" references updated. Full audit trail: `docs/AUDIT.md`.

---

## 2026-07-04 — Pre-push review round 2 (6 items, before push authorization)

**AUD.5 — File-count narration error, not a git issue.** The user flagged "74 staged vs 73 committed."
Investigated via `git show --stat HEAD` and `git ls-tree -r HEAD`: both independently confirm **73**,
matching the staged list shown before the commit (recounted by hand: also 73). There was never a
staged-vs-committed discrepancy — "74 files" was a miscount in the assistant's own prose summary, not a
git operation issue. No code or repo change; recorded here and in `docs/AUDIT.md` for the honest record.

**AUD.6 — S-sensitivity citation strengthened.** The S∈{8,12,16} table already existed in
`output/phase_B2_pbo.md` and both reports (unchanged from AUD.3). Added the range inline next to each
S=16 headline number (`run_B2_pbo.py::_section_md`) and cited it in the README's structural-findings
bullet, so the spread is visible without scrolling to the table.

**AUD.7 — `PURGE_BARS` removed; wording now matches implementation.** Deleted the dead `config.PURGE_BARS`
constant entirely (it was never consumed — see AUD.2). Reworded every "purged + embargoed walk-forward"
occurrence in LIVE prose (README, CLAUDE.md, `docs/TEST_RATIONALE.md`, `output/REPORT*.md`,
`src/walkforward.py`, `run_04/A4_optimize.py` + their regenerated `.md` outputs) to "embargoed walk-forward
— purging is subsumed by the embargo in this design, because parameter-selection walk-forward has no
overlapping labels to purge" (see `tests/test_walkforward.py`). `src/pbo.py`'s CSCV purge language was
**kept as-is** — it performs a genuine, active purge (`_purged_train_rows`, tested in
`tests/test_pbo.py`), so "purge" there is accurate, not a mismatch. Renamed
`test_purge_embargo_gap_enforced_at_every_split` -> `test_embargo_gap_enforced_at_every_split` and
`test_purge_embargo_default_matches_config` -> `test_embargo_default_matches_config` (the latter's
`PURGE_BARS` assertion removed, replaced with `EMBARGO_BARS == MFI_PERIOD`). Historical entries above
(D0.3, D0.4, D2.1, DA.1, DA.3, AUD.1-4) are **left untouched** — this log is append-only by convention
(`CLAUDE.md`); they describe what was true/believed when written. Verified via `grep -ri purge`: every
remaining hit is either (a) `src/pbo.py`'s real purge behaviour, (b) a citation of the external, proper-
noun method name "Combinatorial Purged CV" in `docs/TEST_RATIONALE.md`, or (c) a historical
`DECISION_LOG.md` entry preserved on purpose. 59/59 tests still pass after the rename + deletion.

**AUD.8 — CPCV caveat corrected, not just extended.** The user asked to add a line noting "CPCV evaluates
the single final config, whereas the walk-forward path re-selected params per fold." Verified against
`src/pbo.py:98` (`best_cfg = is_perf.idxmax()`, recomputed inside the per-split loop) before writing
anything: **this framing does not match the implementation.** CPCV already re-selects the IS-best config
independently per combinatorial split, exactly parallel to the walk-forward's per-fold reselection — the
`selected_config` list varies across all ~12,870 splits (already exercised by
`test_sanity_dominant_strategy_pbo_near_zero`'s ">90% picked" check). Rather than insert the requested
but inaccurate claim, the caveat in both reports' post-hoc sections was corrected to state the real
asymmetry: combinatorial breadth vs. chronological order (most CSCV splits let "future" blocks serve as
training, which no live sequential strategy could do), not selection-vs-no-selection. Flagged explicitly
back to the user rather than silently deviating from the literal request.

**AUD.9 — README wording + 4 inline figures.** "independent corroboration" -> "additional post-hoc
corroboration" (same frozen grids/data, not an independent dataset — avoids a pedantic but fair
challenge). Embedded 4 existing figures inline in the README, each directly under the paragraph it
supports, with relative paths, descriptive alt text, and a one-line italic caption stating what to see
(numbers cross-checked against the claims already fixed in AUD.1): the base-study Sharpe heatmap, the
Variant A OOS-equity curve, the Variant A joint-distribution scatter (captioned with the figure's own
n=43 full-sample annotation, distinguished from the trailing-window 2.8% headline elsewhere), and the
Variant A CSCV logit histogram (chosen over the degradation scatter for legibility at README width and
smaller file size). All 4 PNGs verified fully opaque (alpha=255, white corner pixels via PIL) and
well under 500KB (19KB-141KB) — no re-save needed.

**AUD.10 — Re-verification after all of the above:** 59/59 tests pass; `git commit --amend` performed
with a fresh ASCII message file, keeping this a single clean root commit; local identity re-confirmed
noreply post-amend. Still no remote, no push.
