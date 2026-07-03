"""Phase 4 — grid optimisation (Sharpe heatmap + plateau test) + embargoed walk-forward.

Primary model M1 (level threshold × smoothing). M2 (z-score band) is reported as robustness.
Saves for Phase 5: grid metrics, all config net series, and the aggregated OOS (net/pos/market).

Run: .venv\\Scripts\\python run_04_optimize.py
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
from src import performance as perf, signals, walkforward as wf


def _reconstruct_oos_paths(panel, model, splits):
    """Rebuild the aggregated OOS held-position and market-return series from WF selections."""
    spec = signals.MODELS[model]
    fn, (p1n, p2n) = spec["fn"], spec["param_names"]
    oo_market = panel["perp_open"].shift(-1) / panel["perp_open"] - 1.0
    pos_parts, mkt_parts = [], []
    for sp in splits:
        tgt = fn(panel["mfi_xexch"], sp[p1n], sp[p2n])
        held = tgt.shift(config.FACTOR_LAG_BARS)
        lo, hi = pd.Timestamp(sp["oos"][0]), pd.Timestamp(sp["oos"][1])
        pos_parts.append(held.loc[lo:hi])
        mkt_parts.append(oo_market.loc[lo:hi])
    return pd.concat(pos_parts).sort_index(), pd.concat(mkt_parts).sort_index()


def run_model(panel, model_name):
    df, series = wf.evaluate_grid(panel, model_name)
    mat = wf.sharpe_matrix(df)
    plat = wf.plateau_metric(mat)
    wfr = wf.walk_forward(panel, series, model_name)
    return df, series, mat, plat, wfr


def main() -> None:
    config.FIG_DIR.mkdir(parents=True, exist_ok=True)
    panel = pd.read_parquet(config.DATA_CACHE / "panel.parquet")

    # ---------- Primary model M1 ---------- #
    model = "M1_level"
    df, series, mat, plat, wfr = run_model(panel, model)
    p1n, p2n = signals.MODELS[model]["param_names"]
    best_full = tuple(x.item() if hasattr(x, "item") else x for x in df["sharpe"].idxmax())
    n_configs = len(df)

    # benchmarks over the SAME OOS dates
    oos_idx = wfr.oos_returns.index
    oo_market = (panel["perp_open"].shift(-1) / panel["perp_open"] - 1.0).reindex(oos_idx)
    bh_spot_oos = perf.sharpe_ratio(oo_market)
    bh_perp_oos = perf.sharpe_ratio(oo_market - panel["funding"].reindex(oos_idx))

    # reconstruct OOS paths and persist artifacts for Phase 5
    oos_pos, oos_mkt = _reconstruct_oos_paths(panel, model, wfr.splits)
    df.reset_index().to_parquet(config.DATA_CACHE / "grid_M1.parquet")
    pd.DataFrame({f"{k[0]}_{k[1]}": v for k, v in series.items()}).to_parquet(
        config.DATA_CACHE / "series_M1.parquet")
    pd.DataFrame({"net": wfr.oos_returns, "pos": oos_pos.reindex(oos_idx),
                  "market": oos_mkt.reindex(oos_idx)}).to_parquet(config.DATA_CACHE / "oos_M1.parquet")

    # ---------- figures ---------- #
    fig, ax = plt.subplots(figsize=(9, 5.8))
    im = ax.imshow(mat.to_numpy(dtype=float), aspect="auto", origin="lower", cmap="RdYlGn")
    ax.set_xticks(range(len(mat.columns))); ax.set_xticklabels(mat.columns)
    ax.set_yticks(range(len(mat.index))); ax.set_yticklabels(mat.index)
    ax.set_xlabel(f"{p2n} (smoothing window)"); ax.set_ylabel(f"{p1n} (MFI threshold)")
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            v = mat.to_numpy(dtype=float)[i, j]
            if np.isfinite(v):
                ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=7)
    pk = plat.get("peak_params")
    ax.set_title(f"Phase 4 — M1 full-sample net Sharpe heatmap\npeak {pk}, "
                 f"plateau={plat['is_plateau']}, nbhd/peak={plat.get('nbhd_mean_to_peak', float('nan')):.2f}",
                 fontsize=10)
    fig.colorbar(im, ax=ax, label="net Sharpe"); fig.tight_layout()
    fig.savefig(config.FIG_DIR / "phase4_heatmap_M1.png", dpi=120); plt.close(fig)

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(oos_idx, (1 + wfr.oos_returns).cumprod(), color="#c02", lw=1.3,
            label=f"WF OOS strategy (Sharpe {wfr.oos_sharpe:.2f})")
    ax.plot(oos_idx, (1 + oo_market.fillna(0)).cumprod(), color="#888", lw=1.0,
            label=f"BH spot (Sharpe {bh_spot_oos:.2f})")
    ax.plot(oos_idx, (1 + (oo_market - panel['funding'].reindex(oos_idx)).fillna(0)).cumprod(),
            color="#06c", lw=1.0, ls="--", label=f"BH perp net (Sharpe {bh_perp_oos:.2f})")
    ax.set_yscale("log"); ax.set_ylabel("growth of $1 (log)"); ax.legend(fontsize=8)
    ax.set_title("Phase 4 — aggregated walk-forward OOS equity vs buy-and-hold")
    fig.tight_layout(); fig.savefig(config.FIG_DIR / "phase4_oos_equity.png", dpi=120); plt.close(fig)

    # ---------- M2 robustness ---------- #
    df2, series2, mat2, plat2, wfr2 = run_model(panel, "M2_zscore")
    best2 = tuple(x.item() if hasattr(x, "item") else x for x in df2["sharpe"].idxmax())

    # ---------- report ---------- #
    L, Wl = [], None
    Wl = L.append
    Wl("# Phase 4 — Optimisation + embargoed walk-forward\n")
    Wl(f"Model M1 (level×smoothing). Configs tested (N): **{n_configs}**. Cost = fees+slippage+funding.\n")
    Wl("## Full-sample Sharpe grid (heatmap `figures/phase4_heatmap_M1.png`)\n")
    Wl("```"); Wl(mat.round(3).to_string()); Wl("```")
    Wl(f"\n- Peak full-sample config: **{best_full}**  Sharpe **{df['sharpe'].max():.3f}**")
    Wl(f"- Plateau test: **{'PASS' if plat['is_plateau'] else 'FAIL'}** — 3x3 neighbourhood mean/peak = "
       f"**{plat.get('nbhd_mean_to_peak', float('nan')):.2f}** (need ≥{config.PLATEAU_MIN_FRACTION}), "
       f"same-sign frac {plat.get('same_sign_frac', float('nan')):.2f}\n")

    Wl("## Embargoed walk-forward (OOS is the verdict number)\n")
    Wl(f"Scheme **{config.WF_SCHEME}**, {config.WF_N_SPLITS} splits, min-train {config.WF_MIN_TRAIN_BARS}, "
       f"embargo **{config.EMBARGO_BARS}** bars.\n")
    Wl("```")
    Wl(pd.DataFrame(wfr.splits).to_string(index=False))
    Wl("```")
    om = wfr.oos_metrics
    Wl(f"\n**Aggregated OOS:** net Sharpe **{wfr.oos_sharpe:.3f}** · ann_ret {om.get('ann_return', float('nan'))*100:.1f}% · "
       f"maxDD {om.get('max_drawdown', float('nan'))*100:.1f}% · win {om.get('win_rate', float('nan'))*100:.0f}% · "
       f"profit_factor {om.get('profit_factor', float('nan')):.2f}")
    Wl(f"- Benchmark over same OOS span: **BH spot Sharpe {bh_spot_oos:.3f}**, BH perp net Sharpe {bh_perp_oos:.3f}")
    beat = wfr.oos_sharpe > bh_spot_oos
    Wl(f"- Beats buy-and-hold (spot)? **{'YES' if beat else 'NO'}**  "
       f"(pre-registered requirement for CONFIRMED)\n")

    Wl("## M2 robustness (z-score band)\n")
    Wl(f"- Peak full-sample Sharpe **{df2['sharpe'].max():.3f}** at {best2}; "
       f"plateau {'PASS' if plat2['is_plateau'] else 'FAIL'} (nbhd/peak {plat2.get('nbhd_mean_to_peak', float('nan')):.2f})")
    Wl(f"- WF OOS Sharpe **{wfr2.oos_sharpe:.3f}** (vs BH spot {bh_spot_oos:.3f})\n")

    Wl("## Artifacts for Phase 5\n")
    Wl("- `data_cache/grid_M1.parquet` (N-config metrics incl per-period Sharpe moments → DSR/BH-FDR)")
    Wl("- `data_cache/series_M1.parquet` (all config net series → per-config bootstrap p)")
    Wl("- `data_cache/oos_M1.parquet` (aggregated OOS net/pos/market → block-bootstrap CI + permutation)")

    (config.OUTPUT_DIR / "phase4_optimize.md").write_text("\n".join(L), encoding="utf-8")

    # ---------- console ---------- #
    print("PHASE 4 OK")
    print(f"  N configs (M1) = {n_configs}")
    print(f"  peak full-sample: {best_full} Sharpe={df['sharpe'].max():.3f} | plateau={plat['is_plateau']} "
          f"nbhd/peak={plat.get('nbhd_mean_to_peak', float('nan')):.2f}")
    print(f"  WF OOS Sharpe = {wfr.oos_sharpe:.3f} | BH_spot={bh_spot_oos:.3f} BH_perp={bh_perp_oos:.3f} | "
          f"beats_spot={wfr.oos_sharpe > bh_spot_oos}")
    print(f"  OOS ann={om.get('ann_return', float('nan'))*100:.1f}% maxDD={om.get('max_drawdown', float('nan'))*100:.1f}%")
    print("  WF selections:")
    for sp in wfr.splits:
        print(f"    split{sp['split']} IS{sp['is']}->OOS{sp['oos']} pick {p1n}={sp[p1n]},{p2n}={sp[p2n]} "
              f"IS_Sh={sp['is_sharpe']} OOS_Sh={sp['oos_sharpe']}")
    print(f"  M2 WF OOS Sharpe = {wfr2.oos_sharpe:.3f}")


if __name__ == "__main__":
    main()
