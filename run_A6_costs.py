"""Variant A · Phase 6 — cost sensitivity + breakeven for the best Edge config.

Run: .venv\\Scripts\\python run_A6_costs.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import config
from src import backtest, divergence as dv, performance as perf


def main() -> None:
    panel = pd.read_parquet(config.DATA_CACHE / "panel.parquet")
    grid = pd.read_parquet(config.DATA_CACHE / "grid_A.parquet")
    best = grid.loc[grid["sharpe"].idxmax()]
    T, Wn = float(best["threshold"]), int(best["window"])
    tgt = dv.edge_signal(panel["mfi_xexch"], panel["funding"], T, Wn)
    activity = backtest.run_backtest(tgt, panel).metrics  # n_trades/turnover at default (real) costs

    cost_bps = [0, 2, 5, 7, 10, 15, 20, 30, 50, 75, 100]
    sharpes = np.array([backtest.run_backtest(tgt, panel, fee=c / 1e4, slippage=0.0).metrics["sharpe"]
                        for c in cost_bps])

    panel_nf = panel.copy(); panel_nf["funding"] = 0.0
    gross_sharpe = backtest.run_backtest(tgt, panel_nf, fee=0.0, slippage=0.0).metrics["sharpe"]
    oo = panel["perp_open"].shift(-1) / panel["perp_open"] - 1.0
    bh_spot = perf.sharpe_ratio(oo.dropna())

    breakeven = float("inf")
    for i in range(len(cost_bps) - 1):
        if sharpes[i] >= 0 >= sharpes[i + 1]:
            breakeven = cost_bps[i] + (0 - sharpes[i]) * (cost_bps[i + 1] - cost_bps[i]) / (sharpes[i + 1] - sharpes[i])
            break

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(cost_bps, sharpes, marker="o", color="#c02", label=f"best Edge (T={T},W={Wn}) net Sharpe")
    ax.axhline(0, color="k", lw=0.7)
    ax.axhline(bh_spot, color="#888", ls="--", lw=0.9, label=f"BH spot Sharpe ({bh_spot:.2f})")
    ax.axhline(gross_sharpe, color="#093", ls=":", lw=0.9, label=f"gross (no fees/funding) ({gross_sharpe:.2f})")
    ax.set_xlabel("assumed one-way cost (bps)"); ax.set_ylabel("net Sharpe (full sample)")
    ax.set_title("Variant A — cost sensitivity + breakeven (funding always applied)")
    ax.legend(fontsize=8); fig.tight_layout()
    fig.savefig(config.FIG_DIR / "variantA_cost_sensitivity.png", dpi=120); plt.close(fig)

    L = []; W = L.append
    W("# Variant A · Phase 6 — cost sensitivity & breakeven\n")
    W(f"Best in-sample config **T={T}, W={Wn}**. Funding always applied.\n")
    W("| one-way cost (bps) | net Sharpe |")
    W("|---:|---:|")
    for c, s in zip(cost_bps, sharpes):
        W(f"| {c} | {s:.3f} |")
    W(f"\n- Gross Sharpe (no fees/funding): **{gross_sharpe:.3f}**  ·  BH spot: **{bh_spot:.3f}**")
    W(f"- Activity at real costs: **{activity['n_trades']} trades**, avg hold **{activity['avg_hold_days']:.1f} days**, "
      f"turnover **{activity['turnover_per_year']:.1f}/yr**, exposure **{activity['exposure']*100:.0f}%** of days.")
    W(f"- Breakeven one-way cost: **{'%.0f bps' % breakeven if np.isfinite(breakeven) else '> 100 bps (not fee-bound)'}**")
    W(f"\n**Reading:** as in the base study, turnover is low (~{activity['turnover_per_year']:.0f}/yr) → not fee-sensitive. Funding is the drag, but "
      "the binding constraint is significance/persistence (Phase 5), not cost.\n")
    (config.OUTPUT_DIR / "variantA_phase6.md").write_text("\n".join(L), encoding="utf-8")

    print("VARIANT A PHASE 6 OK")
    print(f"  best T={T},W={Wn} gross={gross_sharpe:.3f} BH_spot={bh_spot:.3f}")
    print(f"  n_trades={activity['n_trades']} avg_hold_days={activity['avg_hold_days']:.1f} "
          f"turnover_per_year={activity['turnover_per_year']:.1f} exposure={activity['exposure']*100:.0f}%")
    print(f"  net Sharpe by bps {cost_bps}: {np.round(sharpes,3).tolist()}")
    print(f"  breakeven one-way = {'%.0f bps' % breakeven if np.isfinite(breakeven) else '>100 bps'}")


if __name__ == "__main__":
    main()
