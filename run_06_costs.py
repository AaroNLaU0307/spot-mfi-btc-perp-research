"""Phase 6 — cost sensitivity + breakeven cost ceiling.

Cost-sensitivity is shown on the in-sample best config (clean monotone curve): net Sharpe vs assumed
one-way trading cost (bps), with real funding always applied. Breakeven = cost at which net Sharpe → 0.
The honest OOS headline (already sub-benchmark at realistic cost) is reported alongside.

Run: .venv\\Scripts\\python run_06_costs.py
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
from src import backtest, performance as perf, signals


def main() -> None:
    panel = pd.read_parquet(config.DATA_CACHE / "panel.parquet")
    grid = pd.read_parquet(config.DATA_CACHE / "grid_M1.parquet")
    best = grid.loc[grid["sharpe"].idxmax()]
    T, Wn = int(best["threshold"]), int(best["window"])
    tgt = signals.signal_level_threshold(panel["mfi_xexch"], T, Wn)
    activity = backtest.run_backtest(tgt, panel).metrics  # n_trades/turnover at default (real) costs

    # sweep one-way cost in bps (fold slippage into this single knob); funding stays real
    cost_bps = [0, 2, 5, 7, 10, 15, 20, 30, 50, 75, 100]
    sharpes, anns = [], []
    for c in cost_bps:
        res = backtest.run_backtest(tgt, panel, fee=c / 1e4, slippage=0.0)
        sharpes.append(res.metrics["sharpe"])
        anns.append(res.metrics["ann_return"])
    sharpes, anns = np.array(sharpes), np.array(anns)

    # gross (no fees, no funding) — isolates raw signal timing value
    panel_nf = panel.copy()
    panel_nf["funding"] = 0.0
    gross = backtest.run_backtest(tgt, panel_nf, fee=0.0, slippage=0.0)
    gross_sharpe = gross.metrics["sharpe"]

    # buy-and-hold spot (full sample) reference
    oo = panel["perp_open"].shift(-1) / panel["perp_open"] - 1.0
    bh_spot = perf.sharpe_ratio(oo.dropna())

    # breakeven cost (net Sharpe crosses 0), linear interp on the sweep
    breakeven = float("inf")
    for i in range(len(cost_bps) - 1):
        if sharpes[i] >= 0 >= sharpes[i + 1]:
            x0, x1, y0, y1 = cost_bps[i], cost_bps[i + 1], sharpes[i], sharpes[i + 1]
            breakeven = x0 + (0 - y0) * (x1 - x0) / (y1 - y0)
            break

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(cost_bps, sharpes, marker="o", color="#c02", label=f"best config (T={T},W={Wn}) net Sharpe")
    ax.axhline(0, color="k", lw=0.7)
    ax.axhline(bh_spot, color="#888", ls="--", lw=0.9, label=f"buy-and-hold spot Sharpe ({bh_spot:.2f})")
    ax.axhline(gross_sharpe, color="#093", ls=":", lw=0.9, label=f"gross (no fees/funding) Sharpe ({gross_sharpe:.2f})")
    ax.set_xlabel("assumed one-way cost (bps)"); ax.set_ylabel("net Sharpe (full sample)")
    ax.set_title("Phase 6 — cost sensitivity + breakeven (funding always applied)")
    ax.legend(fontsize=8); fig.tight_layout()
    fig.savefig(config.FIG_DIR / "phase6_cost_sensitivity.png", dpi=120); plt.close(fig)

    L = []
    W = L.append
    W("# Phase 6 — Cost sensitivity & breakeven\n")
    W(f"Best in-sample config: **T={T}, W={Wn}**. Funding always applied (mean ≈ +12.5%/yr paid by longs).\n")
    W("| one-way cost (bps) | net Sharpe | net ann % |")
    W("|---:|---:|---:|")
    for c, s, a in zip(cost_bps, sharpes, anns):
        W(f"| {c} | {s:.3f} | {a*100:.1f} |")
    W(f"\n- **Gross Sharpe (no fees, no funding): {gross_sharpe:.3f}** — raw signal-timing value before any cost.")
    W(f"- Buy-and-hold spot Sharpe (full sample): **{bh_spot:.3f}**.")
    W(f"- Activity at real costs: **{activity['n_trades']} trades**, avg hold **{activity['avg_hold_days']:.1f} days**, "
      f"turnover **{activity['turnover_per_year']:.1f}/yr**, exposure **{activity['exposure']*100:.0f}%** of days.")
    W(f"- **Breakeven one-way cost (net Sharpe → 0): "
      f"{'%.0f bps' % breakeven if np.isfinite(breakeven) else '> 100 bps (fees are not the binding constraint)'}**.")
    W(f"\n**Reading:** turnover is low (~{activity['turnover_per_year']:.0f}/yr), so the strategy is **not** fee-sensitive — the breakeven "
      "fee ceiling is high. The binding constraints are the **funding drag** and, decisively, the **lack "
      "of out-of-sample persistence** (Phase 4–5): the strategy never beats buy-and-hold spot even gross, "
      "and its OOS Sharpe is statistically indistinguishable from zero.\n")
    (config.OUTPUT_DIR / "phase6_costs.md").write_text("\n".join(L), encoding="utf-8")

    print("PHASE 6 OK")
    print(f"  best config T={T},W={Wn}")
    print(f"  gross Sharpe (no fees/funding) = {gross_sharpe:.3f}")
    print(f"  BH spot Sharpe = {bh_spot:.3f}")
    print(f"  n_trades={activity['n_trades']} avg_hold_days={activity['avg_hold_days']:.1f} "
          f"turnover_per_year={activity['turnover_per_year']:.1f} exposure={activity['exposure']*100:.0f}%")
    print(f"  net Sharpe by cost bps {cost_bps}:")
    print("   ", np.round(sharpes, 3).tolist())
    print(f"  breakeven one-way cost = {'%.0f bps' % breakeven if np.isfinite(breakeven) else '>100 bps'}")


if __name__ == "__main__":
    main()
