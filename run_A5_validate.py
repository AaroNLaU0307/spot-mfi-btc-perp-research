"""Variant A · Phase 5 — statistical validation of the Edge WF result.

Same battery as the base study (reused stats module): in-sample DSR/PSR (N=grid), BH-FDR across the
grid, stationary block-bootstrap CI on the OOS Sharpe, factor-permutation null. Plus a per-fold
stability read, because the Phase-4 OOS Sharpe mixes strong-positive and strong-negative sub-periods.

Run: .venv\\Scripts\\python run_A5_validate.py
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
    grid = pd.read_parquet(config.DATA_CACHE / "grid_A.parquet")
    oos = pd.read_parquet(config.DATA_CACHE / "oos_A.parquet")
    oos_net, oos_pos, oos_mkt = oos["net"].dropna(), oos["pos"], oos["market"]
    n_configs = len(grid)

    best = grid.loc[grid["sharpe"].idxmax()]
    sr_pp, n_days = float(best["sr_pp"]), int(best["n_days"])
    skew, kurt = float(best["skew"]), float(best["kurt"])
    sr_var = float(np.nanvar(grid["sr_pp"].to_numpy(), ddof=1))
    psr_is = stats.probabilistic_sharpe_ratio(sr_pp, n_days, skew, kurt, 0.0)
    dsr_is = stats.deflated_sharpe_ratio(sr_pp, n_days, skew, kurt, n_configs, sr_var)

    pvals = [1.0 - stats.probabilistic_sharpe_ratio(r.sr_pp, int(r.n_days), r.skew, r.kurt, 0.0)
             if np.isfinite(r.sr_pp) else 1.0 for r in grid.itertuples()]
    bh = stats.benjamini_hochberg(pvals, alpha=0.05)
    n_survive = int(bh["reject"].sum())

    boot = stats.stationary_block_bootstrap_sharpe(oos_net, mean_block=config.STATIONARY_BLOCK_MEAN)
    perm = stats.permutation_null_sharpe(oos_pos, oos_mkt, block=config.STATIONARY_BLOCK_MEAN)
    osr, on, oskew, okurt = stats.sharpe_moments(oos_net)
    psr_oos = stats.probabilistic_sharpe_ratio(osr, on, oskew, okurt, 0.0)
    oos_sharpe = perf.sharpe_ratio(oos_net)

    # per-fold stability: split OOS into calendar-year chunks
    yearly = oos_net.groupby(oos_net.index.year).apply(perf.sharpe_ratio)

    L = []; W = L.append
    W("# Variant A · Phase 5 — statistical validation\n")
    W(f"N configs: **{n_configs}**. Block length: **{config.STATIONARY_BLOCK_MEAN}** days.\n")
    W("## In-sample selection significance\n")
    W(f"- Best IS config (T={best['threshold']}, W={int(best['window'])}): PSR vs 0 = **{psr_is:.3f}**, "
      f"**DSR (N={n_configs}) = {dsr_is:.3f}** ({'PASS' if dsr_is > 0.95 else 'FAIL'} vs 0.95)")
    W(f"- BH-FDR survivors across grid: **{n_survive}/{n_configs}**\n")
    W("## Out-of-sample honesty (the verdict inputs)\n")
    W(f"- Aggregated OOS Sharpe = **{oos_sharpe:.3f}** · PSR vs 0 = {psr_oos:.3f}")
    W(f"- Stationary block-bootstrap 95% CI: **[{boot['lo']:.3f}, {boot['hi']:.3f}]** (frac>0 "
      f"{boot['frac_gt_0']:.2f}) → **{'excludes 0' if boot['lo'] > 0 else 'INCLUDES 0'}**")
    W(f"- Permutation null: observed {perm['observed']:.3f} vs null p95 {perm['null_p95']:.3f}; "
      f"**p = {perm['p_value']:.3f}** ({'significant' if perm['p_value'] < 0.05 else 'NOT significant'})")
    W("\n## OOS stability by calendar year (diagnostic)\n```")
    W(yearly.round(3).to_string()); W("```")
    W("An edge should be sign-stable across years; strong-positive-then-negative flips mean the aggregate "
      "reflects a few favourable sub-periods (e.g. 2022 drawdown-avoidance), not persistent alpha.\n")
    (config.OUTPUT_DIR / "variantA_phase5.md").write_text("\n".join(L), encoding="utf-8")

    print("VARIANT A PHASE 5 OK")
    print(f"  IS PSR={psr_is:.3f} DSR(N={n_configs})={dsr_is:.3f} {'PASS' if dsr_is>0.95 else 'FAIL'} | BH-FDR {n_survive}/{n_configs}")
    print(f"  OOS Sharpe={oos_sharpe:.3f} PSR={psr_oos:.3f}")
    print(f"  OOS block-bootstrap 95% CI=[{boot['lo']:.3f},{boot['hi']:.3f}] frac>0={boot['frac_gt_0']:.2f} "
          f"-> {'excludes0' if boot['lo']>0 else 'INCLUDES0'}")
    print(f"  OOS permutation p={perm['p_value']:.3f} (obs {perm['observed']:.3f} vs null_p95 {perm['null_p95']:.3f})")
    print("  OOS Sharpe by year:")
    print(yearly.round(3).to_string())


if __name__ == "__main__":
    main()
