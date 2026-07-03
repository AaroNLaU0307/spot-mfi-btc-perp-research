# Final pre-publication audit

Adversarial pass before this repo goes public as a portfolio piece. Stance: a skeptical quant PM /
interviewer looking for a reason to reject the candidate. Priorities, in order: claim–evidence
integrity, reproducibility for a stranger, security/privacy, narrative completeness, polish.

No research was re-run and no result was changed, except Phase B2 (explicitly sanctioned): a post-hoc
PBO/CPCV computation appended after both verdicts, under a hard rule that it cannot revise either one.

---

## Phase A — Claim–evidence integrity

Every quantitative claim in `README.md`, `output/REPORT.md`, `output/REPORT_variantA.md`, both
`research/PREREGISTRATION*.md`, and `docs/DECISION_LOG.md` was traced to its generating artifact
(a `run_*.py` script and the `.md`/`.png` it writes). Mismatches found and fixed:

| # | Finding | Fix |
|---|---|---|
| 1 | "Every decile's mean forward return is positive" was **false** — the 1d, 5d, and 21d decile tables each have 1–2 tiny negative deciles (only the 10d horizon is fully positive); the figure `phase1_deciles.png` itself visibly shows this. | Reworded in `PREREGISTRATION.md`, `REPORT.md`, and `DECISION_LOG.md` D1.1 to "nearly all positive, with tiny negative exceptions" and quantified the exceptions. |
| 2 | Grid-range transcription error: `PREREGISTRATION.md`/`REPORT.md` said `T ∈ {55..85}`, but the frozen/executed grid (`config.GRID_LEVEL_THRESHOLDS`) is `{60..90}` — confirmed against the actual heatmap in `phase4_optimize.md`. | Both docs corrected to match `config.py` (the source of truth); N=42 count was already right. |
| 3 | `REPORT.md`'s Phase-5 table split gate 4 (DSR **and** BH-FDR) into two separate rows, so its own "5 of 7 FAIL" claim didn't reconcile against the table shown. | Restructured to one row per pre-registered gate, mirroring `REPORT_variantA.md`'s already-correct format. Count now reconciles exactly (2 pass / 5 fail). |
| 4 | "Turnover ≈ 10/yr" was a real number but was never persisted to any artifact. | Recomputed via the unmodified `backtest.run_backtest()` on cached data for the actual grid-winning configs (10.6/yr base, 11.0/yr Variant A) and added to both `phase6*.md` reports. |
| 5 | Unqualified "+0.35" correlation headline (it's the Spearman value; Pearson is +0.32). | Tightened to show both explicitly in 3 files. |
| 6 | `numpy` scalar reprs (`np.int64(70)`) were leaking into 2 figure titles — truncating them — and 2 markdown reports. | Fixed at the source (`walkforward.plateau_metric`, `run_04/A4_optimize.py`); 4 artifacts regenerated; confirmed byte-identical underlying numbers. |
| 7 | Stale "(26 pass)" test-count references (suite grew to 39, then 59). | Updated in both reports' reproduce lines. |

**Verified clean (no fix needed):** verdict wording consistency (`FALSIFIED` / `INCONCLUSIVE` leaning
`FALSIFIED` used identically everywhere, with prospective "honest prior" statements correctly
distinguished from the final verdict); gate-4 DSR explicitly labelled "(in-sample)" everywhere a
numeric value appears; row counts (2061), date ranges, and grid counts (N=42/36) all cross-checked
against generated artifacts; 5 figures visually spot-checked against their claims, including the
required check that `variantA_oos_equity.png` actually shows the 2021–23 gap-build and 2024–25
stagnation described in prose.

## Phase B — Methodology re-verification

Re-confirmed each non-negotiable in code and added tests where a guarantee existed but was untested:

- **Factor lag / next-open execution** — already covered: every signal (MFI-level, z-score, Edge) flows
  through the same `backtest.run_backtest()` lag/shift mechanism, and `test_costs_and_lag_hand_worked`
  pins it with a hand-worked example. No duplicate test needed per-signal.
- **Trailing-only transforms** — `signal_level_threshold`/`signal_zscore_band`/`edge_signal` already had
  truncation-invariance tests. Added `tests/test_eda.py` (5 tests) for the previously-untested
  `eda.transforms()` (zscore/percentile/roc).
- **Purge + embargo ≥14 bars** — had **zero** direct tests (`tests/test_walkforward.py` did not exist).
  Added 8 tests: exact IS/OOS gap invariant, config alignment, embargo-widening sensitivity, anchored
  scheme correctness, plateau/spike detection (2 cases), and a regression guard for the numpy-repr bug
  (finding #6 above). Also found `config.PURGE_BARS` was defined but never consumed anywhere in `src/`
  — confirmed this is architecturally sound, not a bug: the walk-forward selects configs from a strict
  anchored IS prefix with no forward-looking training labels, so a single embargo gap ≥ the factor
  window is the whole leakage guarantee; documented explicitly in `config.py` and pinned by
  `test_purge_embargo_default_matches_config`.
- **Costs always modelled** — grepped every `run_backtest()` call site: only 2 use `fee=0` (the
  cost-sensitivity scripts' gross isolate), both clearly assigned to variables/labels named "gross",
  never "net". Default parameters are always the real nonzero costs; funding is summed into net
  unconditionally, not gated by `cost_mult`.
- **Determinism** — reran the RNG-dependent stats layer (`run_05_validate.py`, `run_A5_validate.py`)
  twice back-to-back; diffed all outputs (reports + console logs): bit-identical. The grid/walk-forward
  layer has no RNG at all (pure argmax) and was independently confirmed byte-identical across 3 separate
  regenerations during the Phase A fix cycle.
- **Debris sweep** — no TODO/FIXME/commented-out code found. An AST-based unused-import scan found 2
  genuine unused imports (`numpy` in `src/backtest.py` and `run_00_data.py`) — removed both.

Test count: 26 → 39 (13 new).

## Phase B2 — PBO via CSCV + CPCV (the one sanctioned computation)

New `src/pbo.py` implements PBO via CSCV (Bailey, Borwein, López de Prado & Zhu, 2017), purging
`EMBARGO_BARS` (14) from the train side of every combinatorial train/test block boundary — a direct
generalisation of this repo's existing walk-forward embargo convention to the many-boundary
combinatorial setting.

**Hard rules honoured:** both verdicts were frozen before this phase ran; nothing computed here revises
either one. Every output is appended to a clearly-labelled "Post-hoc supplementary validation (added
after verdict)" section in each report, with an explicit prose guard against misreading the CPCV median
as rehabilitating either verdict (see below).

**Implementation risk control (run and passed *before* any real number was reported):**
- Pure-noise return matrix → PBO ≈ 0.5: a single random-matrix draw showed 0.64–0.74 (legitimate
  small-sample variance — the C(S,S/2) splits of one fixed matrix are correlated observations, not
  independent trials); averaging over 30 independent draws at S=8 gives mean PBO ∈ [0.35, 0.65]. ✅
- Planted-dominant-strategy matrix → PBO near 0: got 0.00–0.16 across S=8/12/16 during development;
  the dominant config is selected as IS-best >90% of the time. ✅
- Both checks live in `tests/test_pbo.py` and run at S=8 in the default suite (70 splits vs. S=16's
  12,870) purely for CI speed — this cut the full `pytest -q` runtime from ~4 minutes to ~2.6 seconds.
  The same property was independently confirmed at the production S=16 during development before this
  speed optimisation was applied, so the weaker-S test is a speed trade, not a weaker guarantee.

**Production result** (S=16, both studies' frozen grids, no new parameters):

| | Base study | Variant A |
|---|---:|---:|
| PBO (S=16) | **0.720** | **0.842** |
| S-sensitivity | S=8: 0.671, S=12: 0.705, S=16: 0.720 | S=8: 0.943, S=12: 0.790, S=16: 0.842 |
| CPCV OOS-Sharpe median | 0.581 | 0.675 |
| WF path percentile | 24th | 51st |

Both PBO values are high, independently corroborating both existing negative verdicts.

**A genuine interpretive subtlety, handled explicitly:** the base study's CPCV median (0.581) sits
*above* its realised walk-forward path (0.294). Read carelessly, this could look like it rehabilitates
the `FALSIFIED` verdict. It does not, and each report's post-hoc section says so explicitly: most CSCV
splits let blocks that are chronologically *after* the walk-forward's test window serve as "training" —
an ordering no live sequential strategy could ever trade. The high PBO alongside the median is the
signal that matters; the median describes the selection process's spread, not an achievable Sharpe.

**Also delivered:** descriptive-stats extension (`performance.extended_metrics`: Sortino, Calmar, skew,
excess kurtosis, daily VaR/CVaR 95%, longest drawdown duration — 11 new tests, descriptive only, no
verdict weight), a program-level multiplicity paragraph (78 configs across 2 hypotheses; a family-wise
correction would only strengthen both negative verdicts), and `docs/TEST_RATIONALE.md` (every test run
and every test deliberately not run, with reasons — linked from the README).

Test count: 39 → 59 (20 new: 9 in `test_pbo.py`, 11 in `test_performance_extra.py`).

## Phase C — Reproducibility from a stranger's machine

- **Fresh-clone test:** copied the repo to a clean directory (excluding `data_cache/`, `.venv/`,
  `__pycache__/`, `.pytest_cache/`), created a brand-new venv, installed strictly from the newly-created
  `requirements.txt` (pinned to the exact versions this project was developed and audited against), and
  ran `pytest -q` with no access to the real `data_cache/`: **59/59 pass, no test skipped or marked** —
  every test uses small synthetic fixtures, none touches the network or the data cache.
  (One environment-specific hiccup during the test: the *initial* clone location had a very deep path
  and hit Windows' long-path limit installing `statsmodels`' bundled test-data files — a property of
  that specific temp directory, not of this repository; a shorter path installed and ran cleanly. Worth
  knowing if a reviewer clones into a deeply-nested directory on Windows without long-path support
  enabled.)
- **Runbook** rewritten to be cross-platform (bash for macOS/Linux, PowerShell for Windows), with the
  Python 3.11+ requirement stated explicitly and every command verified to match an actual file in the
  repo.
- **Data reproducibility path:** the README states plainly that `run_00_data.py` (spot+perp+funding) and
  Variant A's funding step regenerate `data_cache/` from public Binance/Coinbase/Kraken/Bitstamp/OKX
  endpoints, take roughly a minute or two, and need no API key.
- **`CLAUDE.md`** confirmed to exist and updated to mention the Phase B2 addition explicitly (the CSCV
  purge convention now documented alongside the walk-forward embargo it generalises).

## Phase D — README

Rewritten from scratch: title + framing, key findings up top (both studies, with the required
60-second-read structure), the post-hoc PBO/CPCV section, method (extended to cover both studies and
Phase B2), an explicit "Honest scope & limitations" section (proxy-not-Glassnode, Kraken 2024-07
coverage start, bull-regime-heavy sample, single asset, drawdown-avoidance-is-risk-management-not-alpha),
cross-platform run/test instructions, and a short "what I'd do next."

**Spelling-consistency pass:** the project's established house style is British (confirmed by majority
convention across all pre-existing docs, including `CLAUDE.md`'s own "Favour correctness..." line — 22
British-spelled instances vs. 12 American across the original content). Found and fixed a genuine mix of
American-spelled outliers (`realized`, `favorable`, `realization`) scattered across
`output/REPORT_variantA.md`, `research/PREREGISTRATION_variantA.md`, `docs/DECISION_LOG.md`,
`config.py`, and `src/divergence.py`, including a source-of-truth instance in `run_A1_eda.py` that had
propagated into 3 generated downstream files (fixed at the source and regenerated — numbers confirmed
byte-identical). `color=` instances flagged by the sweep are matplotlib keyword arguments, not prose,
and were correctly left untouched (the library requires that exact spelling). Final case-insensitive
sweep across every `.py` and `.md` file: clean. No emoji, no superlative self-praise found.

## Phase E — Security & privacy

- Grepped the entire tree (all extensions, including dotfiles) for API-key patterns, `GLASSNODE`,
  `api_key`, `secret`, `password`, `token`, `bearer`, and `@yahoo`/any email address: every `Glassnode`
  hit is descriptive text disclosing the *absence* of a key (the load-bearing proxy caveat repeated
  throughout); zero actual secrets, zero emails, zero `.env` files anywhere in the tree.
- `.gitignore` was missing `.env*` and IDE directories from the brief's explicit checklist — added both.
  `data_cache/`, `.venv/`, `__pycache__/`, `*.py[cod]`, `.pytest_cache/` were already present.
- Confirmed the exact file set that will be tracked matches the brief's "committed" list precisely:
  `output/` (figures + reports), `research/`, `docs/`, `src/`, `tests/`, `run_*.py`, `config.py`,
  `requirements.txt`, `CLAUDE.md`, `README.md`, plus `.gitignore` and the new `LICENSE`. No stray
  temp/pickle/checkpoint files anywhere.
- Added an MIT `LICENSE` (copyright holder: AaroNLaU0307).

## Round 2 — pre-push review (6 items, before push authorization)

The user reviewed the first commit and requested 6 fixes before authorizing push. None change any
result. Full detail in `docs/DECISION_LOG.md` (AUD.5-AUD.10); summarised here:

1. **File-count reconciliation.** "74 staged vs. 73 committed" was investigated via
   `git show --stat HEAD` and `git ls-tree -r HEAD` (both independently confirm **73**) and a manual
   recount of the staged list shown before the commit (also 73). **There was never a real discrepancy**
   — "74" was a miscount in the assistant's own prose summary. Recorded honestly rather than inventing a
   technical explanation for something that didn't happen.
2. **S-sensitivity citation.** The S∈{8,12,16} table already existed (Phase B2 delivered it originally);
   strengthened by adding the range inline next to each S=16 headline number in both reports and citing
   it in the README's structural-findings bullet, rather than leaving it only in a table below.
3. **Purge wording vs. implementation.** Deleted the dead `config.PURGE_BARS` constant. Reworded every
   "purged + embargoed walk-forward" mention in live prose to "embargoed walk-forward" with an explicit
   note that purging is subsumed by the embargo here (no forward-looking labels to purge). Left
   `src/pbo.py`'s purge language untouched — it performs a genuine, tested purge in the combinatorial
   setting, so that terminology is accurate. Historical `DECISION_LOG.md` entries preserved untouched
   (append-only convention); one new dated entry added instead. Renamed the two tests that referenced
   `PURGE_BARS` directly; `grep -ri purge` now resolves cleanly to either real `pbo.py` behaviour, a
   proper-noun method citation, or a preserved historical entry.
4. **README wording.** "independent corroboration" → "additional post-hoc corroboration" (same frozen
   grids/data, not an independent dataset).
5. **CPCV caveat — verified before writing, then corrected rather than complied literally.** The
   requested addition ("CPCV evaluates the single final config, whereas the walk-forward re-selected
   per fold") does not match `src/pbo.py`'s actual behaviour: `best_cfg = is_perf.idxmax()` is
   recomputed inside the per-split loop, so CPCV already re-selects independently per split, exactly
   parallel to the walk-forward's per-fold reselection. Rather than insert an inaccurate claim into a
   claims-audited document, the caveat was corrected to state the real asymmetry (combinatorial breadth
   vs. chronological order), and this was flagged explicitly back to the user rather than silently
   deviating from the literal request.
6. **Four figures embedded inline in the README** (base-study Sharpe heatmap, Variant A OOS-equity
   curve, Variant A joint-distribution scatter, Variant A CSCV logit histogram), each directly under the
   paragraph it supports, with relative paths, descriptive alt text, and a one-line italic caption whose
   numbers were cross-checked against the already-fixed claims ledger. All 4 PNGs verified fully opaque
   (alpha=255 via PIL, no transparency) and well under the 500KB budget (19-141KB) — no re-save needed.
   The logit histogram was chosen over the degradation scatter for the PBO figure slot: smaller file,
   and a bar-shaped histogram stays legible at reduced width where a 12,870-point scatter would not.

59/59 tests still pass after the `PURGE_BARS` deletion and test renames.

## Residual risks / open items

- The factor remains a **self-computed proxy**, not Glassnode's genuine series — disclosed prominently
  everywhere (this was true before the audit and is a scope decision, not a defect).
- The sample is **bull-regime-heavy** (one 2022 bear) — both reports and the README now say this
  explicitly; it is a genuine scope limitation, not something further doc changes can fix.
- **Windows long-path limitation** noted above under Phase C — informational only, not a repo defect.
- Nothing else outstanding. All findings in this document were fixed, not merely logged.

---

## GO / NO-GO summary

| Check | Status |
|---|---|
| Claims ledger — zero untraceable numbers in any public-facing doc | ✅ GO |
| Fresh-clone `pytest -q` green, no network, no cache | ✅ GO (59/59) |
| README covers both studies, key-findings-first, honest limitations section | ✅ GO |
| README has inline figures with captions consistent with the claims ledger | ✅ GO |
| Phase B2 delivered: PBO + S-sensitivity + CPCV, sanity checks green, verdicts untouched | ✅ GO |
| Descriptive-stats extension, multiplicity note, test-rationale table | ✅ GO |
| Security sweep clean, `LICENSE` added, `.gitignore` correct | ✅ GO |
| Code/prose terminology matches under `grep -ri purge` | ✅ GO |
| Local git identity = noreply, single clean commit (amended once, this round), no push | ✅ GO |

**Recommendation: GO.** Waiting for explicit push authorization before any remote operation — none will
be attempted without it.
