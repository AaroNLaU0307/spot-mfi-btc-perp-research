# CLAUDE.md — repo conventions (Spot-MFI / BTC-perp alpha investigation)

Concise working agreement. This is a **falsification-oriented** research project: we test whether a
spot money-flow factor has tradeable alpha for BTCUSDT perpetuals. **We do not tune toward
profitability.** A clean negative result is a valid, fully-acceptable outcome. Favour correctness,
statistical honesty and reproducibility over flattering numbers.

## What this project is
Investigate whether a **Spot Money Flow Index (MFI)** signal predicts **Binance USDⓈ-M BTCUSDT
perpetual** returns. The factor is a **self-computed cross-exchange spot MFI proxy** (see below), a
faithful reconstruction of Glassnode's `spot_money_flow_index` — used because no Glassnode API key is
available. Verdict is one of `CONFIRMED EDGE` / `FALSIFIED` / `INCONCLUSIVE`, tied to a pre-registered
decision rule.

## Non-negotiables (a change violating these is wrong, however good the equity curve looks)
1. **No fabrication.** Never synthesise data or fill missing venue bars. If a venue lacks coverage in a
   period it is dropped transparently. If a needed piece exists neither in the vendored code nor as a
   clean standard implementation, STOP and report.
2. **Factor is a disclosed proxy.** Every report states the MFI is self-computed cross-exchange, NOT
   Glassnode's series, and flags that a real key requires a re-run + comparison.
3. **No look-ahead.** MFI(D) uses close-of-D data → known no earlier than D+1 (`FACTOR_LAG_BARS >= 1`).
   Signals execute next bar (`EXECUTION = "next_open"`). All transforms/normalisation use TRAILING
   windows only — never full-sample statistics.
4. **Embargo `>= MFI_PERIOD` (14 bars)** at every walk-forward split boundary (`src/walkforward.py`).
   Not paired with a separate "purge" step here: config selection uses TRAILING in-sample Sharpe over
   a strict anchored prefix, with no forward-looking training labels to purge, so the embargo gap is
   the whole leakage guarantee (see `tests/test_walkforward.py`, `docs/AUDIT.md`). The combinatorial
   (CSCV/PBO) split boundaries in `src/pbo.py` are a different setting — many boundaries per split —
   and DO perform a genuine purge, dropping `EMBARGO_BARS` from the train side of every train/test
   block adjacency (see `tests/test_pbo.py`).
5. **Costs always modelled** — taker fees + slippage + ACTUAL historical funding by side/holding.
   Gross and net both reported; breakeven cost ceiling reported.
6. **Pre-register before you peek.** Freeze hypothesis/direction/model/decision-rule in
   `research/PREREGISTRATION.md` (informed by Phase-1 IC, NOT by PnL) BEFORE any optimisation.
7. **Anti-overfitting.** Plateau (not spike) parameter selection; walk-forward OOS is the verdict;
   multiple-testing correction (DSR/PSR + BH-FDR) over ALL configs tested (count N).
8. **Determinism** — fixed `RANDOM_SEED`; identical input + config ⇒ identical output.

## Vendored code — read before reuse
Per the project decision, validated utilities are **vendored** (copied, not cross-imported) from the
sibling repos and re-tested here:
- `src/stats.py` ← PSR / DSR / `expected_max_sharpe` / BH-FDR from
  `multi-asset-tsmom-research/src/xsmom_stats.py` and `MTF Analysis/.../robustness/stats.py`,
  plus NEW stationary block bootstrap + factor-permutation null (not present upstream).
- `src/performance.py` ← metrics from `multi-asset-tsmom-research/src/performance.py`, adapted to
  daily (`PERIODS_PER_YEAR = 365`).
Read the source of anything vendored and confirm what it actually does; note any change and re-test.

## Stack & layout
- Python 3.11+ (dev on 3.13), `.venv` per project; `pandas`/`numpy`/`scipy`/`statsmodels`/`matplotlib`,
  `ccxt` (spot ingestion), `requests` (Binance perp REST), `pytest`.
- `config.py` (root, no magic numbers) · `src/` (package) · `run_*.py` (entry scripts at root) ·
  `tests/` · `data_cache/` (gitignored) · `output/` (figures + reports) · `research/` (pre-registration)
  · `docs/` (decision log).
- English throughout; type hints + docstrings on public functions; single responsibility per module.

## Testing
- `python -m pytest -q` must pass before anything is "done".
- Always test the fragile pieces: MFI computation vs a hand-worked example; no-look-ahead/factor-lag;
  truncation-invariance of signals; embargo boundary correctness (walk-forward) and purge boundary
  correctness (CSCV); PSR/DSR against known values.

## Workflow
- `win32` / PowerShell; use the `.venv` interpreter for Python.
- Not a git repo until scaffolding is signed off; keep a clean commit history. **Commit/push only when
  asked.** Maintain `docs/DECISION_LOG.md` at every design fork.
