"""Variant A · Phase 0-1 — funding integrity + joint distribution + Edge predictive structure.

NO strategy PnL here. Decides (a) whether the favourable divergence cell is too sparse to matter and
(b) the Edge honest-IC sign/magnitude vs the raw-MFI baseline — which fixes the pre-registered direction.

Writes: output/variantA_phase1_eda.md + figures/variantA_*.png
Run: .venv\\Scripts\\python run_A1_eda.py
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
from scipy.stats import spearmanr

import config
from src import divergence as dv, eda


def _overlap_ic(sig, fwd_h, lag=config.FACTOR_LAG_BARS):
    d = pd.concat([sig.shift(lag), fwd_h], axis=1).dropna()
    return spearmanr(d.iloc[:, 0], d.iloc[:, 1])[0] if len(d) > 10 else float("nan")


def main() -> None:
    config.FIG_DIR.mkdir(parents=True, exist_ok=True)
    panel = pd.read_parquet(config.DATA_CACHE / "panel.parquet")
    mfi, fund, price = panel["mfi_xexch"], panel["funding"], panel["perp_close"]

    # ---------- Phase 0: funding integrity ---------- #
    fstat = {"n": int(fund.notna().sum()), "nan": int(fund.isna().sum()),
             "mean": float(fund.mean()), "std": float(fund.std()), "min": float(fund.min()),
             "max": float(fund.max()), "pct_negative": float((fund < 0).mean()),
             "ann_mean_%": float(fund.mean() * 365 * 100)}

    # ---------- Phase 1 Step 1: joint distribution + cell sparsity ---------- #
    pear = float(mfi.corr(fund))
    spear = float(mfi.corr(fund, method="spearman"))
    rM_full, rF_full = mfi.rank(pct=True), fund.rank(pct=True)
    corr_ranks = float(rM_full.corr(rF_full))
    # trailing ranks at the default signal window (the signal's actual view)
    W0 = 90
    rM, rF = dv.pct_rank(mfi, W0), dv.pct_rank(fund, W0)
    cell = ((rM > 0.8) & (rF < 0.2))
    cell_n, cell_pct = int(cell.sum()), float(cell.mean() * 100)
    cell_full = ((rM_full > 0.8) & (rF_full < 0.2))
    cell_full_n = int(cell_full.sum())

    # ---------- Phase 1 Step 2: predictive structure ---------- #
    fwd = eda.forward_returns(price)
    edges = {W: dv.edge_score(mfi, fund, W) for W in (60, 90, 252)}
    baseline = mfi  # raw MFI level (prior study's factor)

    rows = []
    for name, sig in [("Edge_W60", edges[60]), ("Edge_W90", edges[90]),
                      ("Edge_W252", edges[252]), ("raw_MFI", baseline)]:
        r_noov = {h: eda.ic_nonoverlap(sig, fwd[h], h)[0] for h in config.IC_HORIZONS}
        p_noov = {h: eda.ic_nonoverlap(sig, fwd[h], h)[1] for h in config.IC_HORIZONS}
        r_ov = {h: _overlap_ic(sig, fwd[h]) for h in config.IC_HORIZONS}
        rows.append((name, r_noov, p_noov, r_ov))

    ic_noov = pd.DataFrame({n: r for n, r, _, _ in rows}).T
    ic_p = pd.DataFrame({n: p for n, _, p, _ in rows}).T
    ic_ov = pd.DataFrame({n: r for n, _, _, r in rows}).T

    # decile shape of Edge_W90
    dec = {h: eda.decile_stats(edges[90], fwd[h]) for h in (5, 10, 21)}
    edge90_mean_ic = float(np.mean(list({h: eda.ic_nonoverlap(edges[90], fwd[h], h)[0]
                                         for h in config.IC_HORIZONS}.values())))
    direction = "LONG high-Edge (positive IC)" if edge90_mean_ic > 0 else "IC NEGATIVE — long-high-Edge NOT supported"

    # ---------- figures ---------- #
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(fund.dropna() * 100, bins=60, color="#06c", alpha=0.85)
    ax.axvline(0, color="k", lw=0.8)
    ax.set_xlabel("daily funding (%)"); ax.set_ylabel("days")
    ax.set_title(f"Variant A — daily funding distribution (mean {fstat['ann_mean_%']:.1f}%/yr, "
                 f"{fstat['pct_negative']*100:.0f}% negative)")
    fig.tight_layout(); fig.savefig(config.FIG_DIR / "variantA_funding_dist.png", dpi=120); plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.2, 6))
    hb = ax.hexbin(rM_full, rF_full, gridsize=25, cmap="Blues", mincnt=1)
    ax.add_patch(plt.Rectangle((0.8, 0.0), 0.2, 0.2, fill=False, edgecolor="#c02", lw=2))
    ax.text(0.82, 0.22, f"favourable\ncell\nn={cell_full_n}", color="#c02", fontsize=9)
    ax.set_xlabel("MFI percentile (full-sample)"); ax.set_ylabel("funding percentile (full-sample)")
    ax.set_title(f"Variant A — joint distribution (rank corr {corr_ranks:+.2f})")
    fig.colorbar(hb, ax=ax, label="days"); fig.tight_layout()
    fig.savefig(config.FIG_DIR / "variantA_joint_dist.png", dpi=120); plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(config.IC_HORIZONS)); w = 0.35
    ax.bar(x - w / 2, ic_noov.loc["Edge_W90"].values, w, label="Edge_W90 (honest IC)", color="#c02")
    ax.bar(x + w / 2, ic_noov.loc["raw_MFI"].values, w, label="raw MFI (honest IC)", color="#888")
    ax.axhline(0, color="k", lw=0.7); ax.set_xticks(x); ax.set_xticklabels(config.IC_HORIZONS)
    ax.set_xlabel("forward horizon (days)"); ax.set_ylabel("non-overlapping Spearman IC")
    ax.set_title("Variant A — Edge vs raw-MFI honest IC (does funding add information?)")
    ax.legend(); fig.tight_layout(); fig.savefig(config.FIG_DIR / "variantA_ic_compare.png", dpi=120); plt.close(fig)

    # ---------- report ---------- #
    L = []; W = L.append
    W("# Variant A · Phase 1 — funding feature, joint distribution, Edge predictive structure\n")
    W("Daily funding = Σ of the day's 8h payments (the day's total funding cost to a long). Lagged "
      "≥1 bar, next-open execution (same convention as MFI). No strategy PnL here.\n")
    W("## Phase 0 — funding integrity\n```")
    for k, v in fstat.items():
        W(f"{k:>14}: {v:.6f}" if isinstance(v, float) else f"{k:>14}: {v}")
    W("```")
    W("\n## Phase 1 Step 1 — joint distribution & divergence-cell sparsity\n")
    W(f"- corr(MFI, funding): Pearson **{pear:+.3f}**, Spearman **{spear:+.3f}**  (rank-rank {corr_ranks:+.3f})")
    W(f"- Favourable divergence cell (trailing W={W0}: MFI_rank>0.8 & Fund_rank<0.2): "
      f"**{cell_n} days = {cell_pct:.1f}%** of sample  (full-sample-rank version: {cell_full_n} days)")
    sparse = cell_pct < 5.0
    W(f"- **{'⚠️ SPARSE' if sparse else 'Adequate'}**: the most-informative divergence observations are "
      f"{'rare — this caps how much the premise can deliver and inflates small-sample noise.' if sparse else 'reasonably populated.'}\n")
    W("## Phase 1 Step 2 — Edge predictive structure (honest, non-overlapping IC)\n")
    W("Non-overlapping IC (sample every h bars) — the decisive test:\n```")
    W("IC:\n" + ic_noov.round(4).to_string())
    W("\np-values:\n" + ic_p.round(3).to_string())
    W("\n(overlapping IC, for reference only):\n" + ic_ov.round(4).to_string())
    W("```")
    W(f"\n- Edge_W90 mean honest IC across horizons: **{edge90_mean_ic:+.4f}** → direction: **{direction}**")
    W("- Decile forward-return shape (Edge_W90):")
    for h in (5, 10, 21):
        W(f"  - {h}d: " + str((dec[h]["mean"] * 100).round(2).tolist()))
    W("\n**Crux — does funding add information over raw MFI?** Compare the Edge rows to `raw_MFI` above: "
      "if Edge's honest IC is no larger (or same sign/insignificant), funding does not rescue the signal.\n")
    W("## Figures\n- `figures/variantA_funding_dist.png`\n- `figures/variantA_joint_dist.png`\n"
      "- `figures/variantA_ic_compare.png`")
    (config.OUTPUT_DIR / "variantA_phase1_eda.md").write_text("\n".join(L), encoding="utf-8")

    # ---------- console ---------- #
    print("VARIANT A PHASE 1 OK")
    print(f"  corr(MFI,funding) Pearson={pear:+.3f} Spearman={spear:+.3f} rank-rank={corr_ranks:+.3f}")
    print(f"  favourable cell (W90): {cell_n} days = {cell_pct:.1f}%  {'SPARSE' if sparse else 'ok'}")
    print("  honest non-overlap IC:")
    print(ic_noov.round(4).to_string())
    print("  honest IC p-values:")
    print(ic_p.round(3).to_string())
    print(f"  Edge_W90 mean honest IC = {edge90_mean_ic:+.4f} -> {direction}")


if __name__ == "__main__":
    main()
