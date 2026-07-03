"""Phase 5 — statistical validation of the pre-registered M1 result.

Consumes Phase-4 artifacts and runs:
  * DSR / PSR on the in-sample best config (deflated for N=grid trials) — is the IS peak real?
  * BH-FDR across the grid (per-config PSR-based p) — selection control.
  * Stationary block-bootstrap CI on the aggregated OOS Sharpe — does it exclude 0?
  * Factor-permutation null on the OOS signal→return mapping — does OOS beat luck?

Run: .venv\\Scripts\\python run_05_validate.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import numpy as np
import pandas as pd

import config
from src import performance as perf, stats


def main() -> None:
    grid = pd.read_parquet(config.DATA_CACHE / "grid_M1.parquet")
    oos = pd.read_parquet(config.DATA_CACHE / "oos_M1.parquet")
    oos_net, oos_pos, oos_mkt = oos["net"].dropna(), oos["pos"], oos["market"]
    n_configs = len(grid)

    # ---- (1) DSR/PSR on the IS best config ---- #
    best = grid.loc[grid["sharpe"].idxmax()]
    sr_pp, n_days = float(best["sr_pp"]), int(best["n_days"])
    skew, kurt = float(best["skew"]), float(best["kurt"])
    sr_var = float(np.nanvar(grid["sr_pp"].to_numpy(), ddof=1))
    psr_is = stats.probabilistic_sharpe_ratio(sr_pp, n_days, skew, kurt, 0.0)
    dsr_is = stats.deflated_sharpe_ratio(sr_pp, n_days, skew, kurt, n_configs, sr_var)

    # ---- (2) BH-FDR across the grid (PSR-based one-sided p for Sharpe>0) ---- #
    pvals = [1.0 - stats.probabilistic_sharpe_ratio(r.sr_pp, int(r.n_days), r.skew, r.kurt, 0.0)
             if np.isfinite(r.sr_pp) else 1.0 for r in grid.itertuples()]
    bh = stats.benjamini_hochberg(pvals, alpha=0.05)
    n_survive = int(bh["reject"].sum())

    # ---- (3) stationary block-bootstrap CI on OOS Sharpe ---- #
    boot = stats.stationary_block_bootstrap_sharpe(oos_net, mean_block=config.STATIONARY_BLOCK_MEAN)

    # ---- (4) factor-permutation null on OOS ---- #
    perm = stats.permutation_null_sharpe(oos_pos, oos_mkt, block=config.STATIONARY_BLOCK_MEAN)

    # OOS PSR vs 0 (honest series)
    osr, on, oskew, okurt = stats.sharpe_moments(oos_net)
    psr_oos = stats.probabilistic_sharpe_ratio(osr, on, oskew, okurt, 0.0)
    oos_sharpe_ann = perf.sharpe_ratio(oos_net)

    # ---- report ---- #
    L = []
    W = L.append
    W("# Phase 5 — Statistical validation\n")
    W(f"N configs tested (M1 grid): **{n_configs}**. Block length (a-priori, IC-decay anchored): "
      f"**{config.STATIONARY_BLOCK_MEAN}** days.\n")
    W("## In-sample selection significance (DSR/PSR)\n")
    W(f"- Best IS config {tuple(grid.loc[grid['sharpe'].idxmax(), ['threshold', 'window']].astype(int))}: "
      f"per-period SR={sr_pp:.4f} (ann {sr_pp*np.sqrt(config.PERIODS_PER_YEAR):.2f}), n={n_days}")
    W(f"- PSR vs 0 = **{psr_is:.3f}**")
    W(f"- **DSR (deflated for N={n_configs} trials) = {dsr_is:.3f}**  "
      f"(need > 0.95 for CONFIRMED; {'PASS' if dsr_is > 0.95 else 'FAIL'})\n")
    W("## Multiple-testing across the grid (BH-FDR)\n")
    W(f"- Configs surviving BH-FDR at α=0.05: **{n_survive}/{n_configs}** "
      f"(note: long-biased-in-a-bull inflates raw Sharpe>0 p-values; interpret with the benchmark test)\n")
    W("## Out-of-sample honesty (the verdict inputs)\n")
    W(f"- Aggregated OOS Sharpe (ann) = **{oos_sharpe_ann:.3f}**  ·  PSR vs 0 = {psr_oos:.3f}")
    W(f"- Stationary block-bootstrap 95% CI for OOS Sharpe: **[{boot['lo']:.3f}, {boot['hi']:.3f}]**  "
      f"(frac>0 {boot['frac_gt_0']:.2f}) → **{'excludes 0' if boot['lo'] > 0 else 'INCLUDES 0'}**")
    W(f"- Permutation null: observed OOS Sharpe {perm['observed']:.3f} vs null p95 {perm['null_p95']:.3f}; "
      f"**p = {perm['p_value']:.3f}** ({'significant' if perm['p_value'] < 0.05 else 'NOT significant'})\n")

    (config.OUTPUT_DIR / "phase5_validation.md").write_text("\n".join(L), encoding="utf-8")

    print("PHASE 5 OK")
    print(f"  IS best PSR={psr_is:.3f} DSR(N={n_configs})={dsr_is:.3f} {'PASS' if dsr_is>0.95 else 'FAIL'}")
    print(f"  BH-FDR survivors: {n_survive}/{n_configs}")
    print(f"  OOS Sharpe={oos_sharpe_ann:.3f} PSR={psr_oos:.3f}")
    print(f"  OOS block-bootstrap 95% CI=[{boot['lo']:.3f},{boot['hi']:.3f}] frac>0={boot['frac_gt_0']:.2f} "
          f"-> {'excludes0' if boot['lo']>0 else 'INCLUDES0'}")
    print(f"  OOS permutation p={perm['p_value']:.3f} (obs {perm['observed']:.3f} vs null_p95 {perm['null_p95']:.3f})")


if __name__ == "__main__":
    main()
