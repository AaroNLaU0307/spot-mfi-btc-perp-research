"""Phase 1 — factor EDA report + figures.

Writes:
  * output/phase1_eda.md                    (IC tables, deciles, stationarity, reading)
  * output/figures/phase1_ic_by_horizon.png
  * output/figures/phase1_deciles.png
  * output/figures/phase1_mfi_hist.png
  * output/figures/phase1_acf.png

Run: .venv\\Scripts\\python run_01_eda.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:                                    # Windows console is cp1252; keep unicode prints safe
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import config
from src import eda


def main() -> None:
    config.FIG_DIR.mkdir(parents=True, exist_ok=True)
    panel = pd.read_parquet(config.DATA_CACHE / "panel.parquet")
    mfi = panel["mfi_xexch"]
    price = panel["perp_close"]

    fwd = eda.forward_returns(price)
    sig = eda.transforms(mfi)
    ic, pv = eda.ic_table(sig, fwd)

    # non-overlapping IC for the raw level (honest p per horizon)
    noov = {h: eda.ic_nonoverlap(sig["level"], fwd[h], h) for h in config.IC_HORIZONS}

    # decile shape for the raw level at a few horizons
    decile_h = [h for h in (1, 5, 10, 21) if h in config.IC_HORIZONS]
    deciles = {h: eda.decile_stats(sig["level"], fwd[h]) for h in decile_h}

    stat_level = eda.stationarity(mfi)
    stat_change = eda.stationarity(mfi.diff())
    acf_level = eda.autocorr(mfi, 10)
    acf_change = eda.autocorr(mfi.diff(), 10)

    # ---------------- figures ---------------- #
    fig, ax = plt.subplots(figsize=(11, 5))
    for name in ic.index:
        ax.plot(list(ic.columns), ic.loc[name].values, marker="o", label=name)
    ax.axhline(0, color="k", lw=0.6)
    ax.set_xlabel("forward horizon (days)"); ax.set_ylabel("Spearman IC (signal lagged)")
    ax.set_title("Phase 1 — Information Coefficient: MFI transforms vs BTCUSDT-perp forward returns")
    ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(config.FIG_DIR / "phase1_ic_by_horizon.png", dpi=120); plt.close(fig)

    fig, axes = plt.subplots(1, len(decile_h), figsize=(4.4 * len(decile_h), 4.2), sharey=False)
    if len(decile_h) == 1:
        axes = [axes]
    for ax, h in zip(axes, decile_h):
        d = deciles[h]
        ax.bar(d.index, d["mean"] * 100, color="#06c")
        ax.axhline(0, color="k", lw=0.6)
        ax.set_title(f"{h}d fwd return by MFI decile")
        ax.set_xlabel("MFI decile (0=low, 9=high)"); ax.set_ylabel("mean fwd return (%)")
    fig.suptitle("Phase 1 — decile forward-return shape (monotone=momentum, U/∩=extremes revert)")
    fig.tight_layout(); fig.savefig(config.FIG_DIR / "phase1_deciles.png", dpi=120); plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(mfi.dropna(), bins=40, color="#093", alpha=0.85)
    for q in (20, 80):
        ax.axvline(q, color="#c02", ls="--", lw=0.8)
    ax.set_xlabel("MFI"); ax.set_ylabel("days")
    ax.set_title("Phase 1 — MFI distribution (80/20 bands)")
    fig.tight_layout(); fig.savefig(config.FIG_DIR / "phase1_mfi_hist.png", dpi=120); plt.close(fig)

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 3.6))
    a1.stem(range(len(acf_level)), acf_level); a1.set_title("ACF — MFI level"); a1.set_xlabel("lag")
    a2.stem(range(len(acf_change)), acf_change); a2.set_title("ACF — MFI change"); a2.set_xlabel("lag")
    fig.tight_layout(); fig.savefig(config.FIG_DIR / "phase1_acf.png", dpi=120); plt.close(fig)

    # ---------------- report ---------------- #
    L: list[str] = []
    W = L.append
    W("# Phase 1 — Factor EDA\n")
    W("Self-computed cross-exchange spot MFI proxy vs BTCUSDT-perp forward returns. Signal lagged "
      f"{config.FACTOR_LAG_BARS} bar; transforms are trailing/causal. No strategy PnL here.\n")

    W("## Information Coefficient (Spearman rank corr)\n")
    W("IC = corr(signal_t, forward return t→t+h). Sign decides direction; magnitude/decay the horizon.\n")
    W("```"); W("IC:\n" + ic.round(4).to_string()); W("\nnaive p-values:\n" + pv.round(4).to_string()); W("```")
    W("\nNon-overlapping IC for the raw MFI **level** (sample every h bars → honest p):\n")
    W("```")
    W(f"{'h':>3} {'IC':>9} {'p':>9} {'n':>6}")
    for h, (r, p, n) in noov.items():
        W(f"{h:>3} {r:>9.4f} {p:>9.4f} {n:>6}")
    W("```")

    W("\n## Decile forward-return shape (raw MFI level)\n")
    for h in decile_h:
        W(f"\n**{h}-day forward return by MFI decile** (mean %, count):\n")
        d = deciles[h].copy()
        d["mean_%"] = (d["mean"] * 100).round(3)
        d["signal_mid"] = d["signal_mid"].round(1)
        W("```"); W(d[["signal_mid", "mean_%", "count"]].to_string()); W("```")

    W("\n## Stationarity & autocorrelation\n")
    W("```")
    W(f"MFI level : ADF stat={stat_level['adf_stat']:.3f} p={stat_level['adf_p']:.4f} | "
      f"KPSS stat={stat_level['kpss_stat']:.3f} p={stat_level['kpss_p']:.4f}")
    W(f"MFI change: ADF stat={stat_change['adf_stat']:.3f} p={stat_change['adf_p']:.4f} | "
      f"KPSS stat={stat_change['kpss_stat']:.3f} p={stat_change['kpss_p']:.4f}")
    W(f"ACF level lags0-5 : {np.round(acf_level[:6], 3).tolist()}")
    W(f"ACF change lags0-5: {np.round(acf_change[:6], 3).tolist()}")
    W("```")

    # ---------------- machine-readable reading of sign/shape ---------------- #
    lvl_ic = ic.loc["level"]
    dominant_sign = "NEGATIVE (mean-reversion: high MFI → lower fwd returns)" if lvl_ic.mean() < 0 \
        else "POSITIVE (momentum: high MFI → higher fwd returns)"
    # decile monotonicity (Spearman of bucket index vs mean return) at 5d if present else first
    hh = 5 if 5 in deciles else decile_h[0]
    dd = deciles[hh]
    mono = float(np.corrcoef(dd.index.to_numpy(), dd["mean"].to_numpy())[0, 1])
    W("\n## Reading (for pre-registration — direction from IC, not PnL)\n")
    W(f"- Dominant level-IC sign across horizons: **{dominant_sign}** (mean IC={lvl_ic.mean():.4f}).")
    W(f"- Decile monotonicity at {hh}d (corr bucket↔mean ret): **{mono:+.3f}** "
      f"({'monotone → momentum' if abs(mono) > 0.6 else 'non-monotone → check U/∩ extremes'}).")
    W(f"- Peak |IC| horizon (level): **{lvl_ic.abs().idxmax()}d** (IC={lvl_ic[lvl_ic.abs().idxmax()]:.4f}).")
    W("\n> These readings seed `research/PREREGISTRATION.md`. Nothing here looks at strategy returns.")

    (config.OUTPUT_DIR / "phase1_eda.md").write_text("\n".join(L), encoding="utf-8")

    # ---------------- console summary ---------------- #
    print("PHASE 1 EDA OK")
    print("IC (rows=transform, cols=horizon):")
    print(ic.round(4).to_string())
    print("\nNon-overlap level IC:", {h: round(v[0], 4) for h, v in noov.items()})
    print("Non-overlap level p :", {h: round(v[1], 4) for h, v in noov.items()})
    print(f"\nDominant level-IC sign: {dominant_sign}")
    print(f"Decile monotonicity @ {hh}d: {mono:+.3f}")
    print(f"Peak |IC| horizon (level): {lvl_ic.abs().idxmax()}d")
    for h in decile_h:
        d = deciles[h]
        print(f"  deciles {h}d mean%:", (d["mean"] * 100).round(2).tolist())
    print("wrote output/phase1_eda.md + 4 figures")


if __name__ == "__main__":
    main()
