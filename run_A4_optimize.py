"""Variant A · Phase 4 — Edge grid (heatmap + plateau) + embargoed walk-forward.

Reuses walkforward.sharpe_matrix / plateau_metric / walk_forward (model-agnostic) with the Edge grid
from divergence.evaluate_edge_grid. Saves Phase-5 artifacts.

Run: .venv\\Scripts\\python run_A4_optimize.py
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
from src import backtest, divergence as dv, performance as perf, walkforward as wf

MODEL = "M1_edge"


def _reconstruct_oos_paths(panel, splits):
    oo_market = panel["perp_open"].shift(-1) / panel["perp_open"] - 1.0
    pos_parts, mkt_parts = [], []
    for sp in splits:
        tgt = dv.edge_signal(panel["mfi_xexch"], panel["funding"], sp["threshold"], sp["window"])
        held = tgt.shift(config.FACTOR_LAG_BARS)
        lo, hi = pd.Timestamp(sp["oos"][0]), pd.Timestamp(sp["oos"][1])
        pos_parts.append(held.loc[lo:hi]); mkt_parts.append(oo_market.loc[lo:hi])
    return pd.concat(pos_parts).sort_index(), pd.concat(mkt_parts).sort_index()


def main() -> None:
    config.FIG_DIR.mkdir(parents=True, exist_ok=True)
    panel = pd.read_parquet(config.DATA_CACHE / "panel.parquet")

    # smoke (one pre-specified central config; engine check, NOT the verdict)
    smoke = backtest.run_backtest(dv.edge_signal(panel["mfi_xexch"], panel["funding"], 0.3, 90), panel)
    print(f"SMOKE Edge(T=0.3,W=90): net_sharpe={smoke.metrics['sharpe']:.3f} "
          f"ann={smoke.metrics['ann_return']*100:.1f}% expo={smoke.metrics['exposure']*100:.0f}% "
          f"trades={smoke.metrics['n_trades']}")

    df, series = dv.evaluate_edge_grid(panel)
    mat = wf.sharpe_matrix(df)
    plat = wf.plateau_metric(mat)
    wfr = wf.walk_forward(panel, series, MODEL)
    n_configs = len(df)
    best_full = tuple(x.item() if hasattr(x, "item") else x for x in df["sharpe"].idxmax())

    oos_idx = wfr.oos_returns.index
    oo_market = (panel["perp_open"].shift(-1) / panel["perp_open"] - 1.0).reindex(oos_idx)
    bh_spot_oos = perf.sharpe_ratio(oo_market)
    bh_perp_oos = perf.sharpe_ratio(oo_market - panel["funding"].reindex(oos_idx))

    oos_pos, oos_mkt = _reconstruct_oos_paths(panel, wfr.splits)
    df.reset_index().to_parquet(config.DATA_CACHE / "grid_A.parquet")
    pd.DataFrame({f"{k[0]}_{k[1]}": v for k, v in series.items()}).to_parquet(
        config.DATA_CACHE / "series_A.parquet")  # per-config net series (parity with series_M1.parquet)
    pd.DataFrame({"net": wfr.oos_returns, "pos": oos_pos.reindex(oos_idx),
                  "market": oos_mkt.reindex(oos_idx)}).to_parquet(config.DATA_CACHE / "oos_A.parquet")

    # heatmap
    fig, ax = plt.subplots(figsize=(9, 5.8))
    im = ax.imshow(mat.to_numpy(dtype=float), aspect="auto", origin="lower", cmap="RdYlGn")
    ax.set_xticks(range(len(mat.columns))); ax.set_xticklabels(mat.columns)
    ax.set_yticks(range(len(mat.index))); ax.set_yticklabels(mat.index)
    ax.set_xlabel("rank window W"); ax.set_ylabel("Edge threshold T")
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            v = mat.to_numpy(dtype=float)[i, j]
            if np.isfinite(v):
                ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=7)
    ax.set_title(f"Variant A — Edge net-Sharpe heatmap\npeak {plat.get('peak_params')}, "
                 f"plateau={plat['is_plateau']}, nbhd/peak={plat.get('nbhd_mean_to_peak', float('nan')):.2f}",
                 fontsize=10)
    fig.colorbar(im, ax=ax, label="net Sharpe"); fig.tight_layout()
    fig.savefig(config.FIG_DIR / "variantA_heatmap.png", dpi=120); plt.close(fig)

    # OOS equity
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(oos_idx, (1 + wfr.oos_returns).cumprod(), color="#c02", lw=1.3,
            label=f"Edge WF OOS (Sharpe {wfr.oos_sharpe:.2f})")
    ax.plot(oos_idx, (1 + oo_market.fillna(0)).cumprod(), color="#888", lw=1.0,
            label=f"BH spot (Sharpe {bh_spot_oos:.2f})")
    ax.set_yscale("log"); ax.set_ylabel("growth of $1 (log)"); ax.legend(fontsize=8)
    ax.set_title("Variant A — walk-forward OOS equity vs buy-and-hold spot")
    fig.tight_layout(); fig.savefig(config.FIG_DIR / "variantA_oos_equity.png", dpi=120); plt.close(fig)

    om = wfr.oos_metrics
    L = []; W = L.append
    W("# Variant A · Phase 4 — Edge optimisation + embargoed walk-forward\n")
    W(f"Configs tested (N): **{n_configs}** (T×W). Smoke Edge(0.3,90) net Sharpe {smoke.metrics['sharpe']:.3f}.\n")
    W("## Full-sample Sharpe grid\n```"); W(mat.round(3).to_string()); W("```")
    W(f"\n- Peak full-sample config **{best_full}** Sharpe **{df['sharpe'].max():.3f}**")
    W(f"- Plateau: **{'PASS' if plat['is_plateau'] else 'FAIL'}** (nbhd/peak "
      f"{plat.get('nbhd_mean_to_peak', float('nan')):.2f}, same-sign {plat.get('same_sign_frac', float('nan')):.2f})\n")
    W(f"## Embargoed walk-forward ({config.WF_SCHEME}, {config.WF_N_SPLITS} splits, embargo "
      f"{config.EMBARGO_BARS})\n```")
    W(pd.DataFrame(wfr.splits).to_string(index=False)); W("```")
    W(f"\n**Aggregated OOS:** net Sharpe **{wfr.oos_sharpe:.3f}** · ann {om.get('ann_return', float('nan'))*100:.1f}% · "
      f"maxDD {om.get('max_drawdown', float('nan'))*100:.1f}% · "
      f"win {om.get('win_rate', float('nan'))*100:.0f}% · PF {om.get('profit_factor', float('nan')):.2f}")
    W(f"- Benchmark OOS: BH spot Sharpe **{bh_spot_oos:.3f}**, BH perp {bh_perp_oos:.3f} → "
      f"beats spot? **{'YES' if wfr.oos_sharpe > bh_spot_oos else 'NO'}**\n")
    W("Artifacts: `data_cache/grid_A.parquet`, `data_cache/oos_A.parquet`. Figures: "
      "`variantA_heatmap.png`, `variantA_oos_equity.png`.")
    (config.OUTPUT_DIR / "variantA_phase4.md").write_text("\n".join(L), encoding="utf-8")

    print("VARIANT A PHASE 4 OK")
    print(f"  N={n_configs} peak {best_full} Sharpe={df['sharpe'].max():.3f} plateau={plat['is_plateau']} "
          f"nbhd/peak={plat.get('nbhd_mean_to_peak', float('nan')):.2f}")
    print(f"  WF OOS Sharpe={wfr.oos_sharpe:.3f} BH_spot={bh_spot_oos:.3f} BH_perp={bh_perp_oos:.3f} "
          f"beats_spot={wfr.oos_sharpe > bh_spot_oos}")
    print(f"  OOS ann={om.get('ann_return', float('nan'))*100:.1f}% maxDD={om.get('max_drawdown', float('nan'))*100:.1f}%")
    for sp in wfr.splits:
        print(f"    split{sp['split']} pick T={sp['threshold']},W={sp['window']} "
              f"IS_Sh={sp['is_sharpe']} OOS_Sh={sp['oos_sharpe']}")


if __name__ == "__main__":
    main()
