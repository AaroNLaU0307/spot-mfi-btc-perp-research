"""Phase 0 — data integrity report + figures.

Loads cached spot/perp data, builds the cross-exchange MFI proxy and the aligned daily
panel, then writes:
  * data_cache/panel.parquet                    (the analysis panel for later phases)
  * output/phase0_integrity.md                  (row counts, ranges, gaps, NaNs, coverage)
  * output/figures/phase0_mfi_vs_price.png      (MFI vs perp price, 80/20 bands)
  * output/figures/phase0_proxy_vs_binance.png  (cross-exchange vs single-Binance MFI)
  * output/figures/phase0_n_venues.png          (venue composition over time)

Run: .venv\\Scripts\\python run_00_data.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

import config
from src import data_perp, data_spot, mfi


def main() -> None:
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    config.FIG_DIR.mkdir(parents=True, exist_ok=True)

    spot = data_spot.load_all_spot(force=False, verbose=False)
    kl = data_perp.fetch_perp_klines()
    fr = data_perp.fetch_funding()
    dfund = data_perp.daily_funding(fr)

    panel = mfi.assemble_panel(spot, kl, dfund)
    panel.to_parquet(config.DATA_CACHE / "panel.parquet")
    cov = data_spot.coverage_by_year(spot)

    # ---- integrity metrics -------------------------------------------------- #
    full_days = pd.date_range(config.START_DATE, config.END_DATE, freq="D")
    missing = full_days.difference(panel.index)
    nan_counts = panel.isna().sum()
    mx = panel["mfi_xexch"]
    corr_proxy_binance = float(panel[["mfi_xexch", "mfi_binance"]].corr().iloc[0, 1])
    mad = float((panel["mfi_xexch"] - panel["mfi_binance"]).abs().mean())
    frac_ob = float((mx > 80).mean())
    frac_os = float((mx < 20).mean())
    nven = panel["n_venues"].value_counts().sort_index()
    kraken_join = spot["kraken"].index.min() if len(spot.get("kraken", [])) else None
    fund_ann = float(panel["funding"].mean() * 365 * 100)

    # ---- figures ------------------------------------------------------------ #
    # 1) MFI vs perp price
    fig, ax1 = plt.subplots(figsize=(13, 5.5))
    ax1.semilogy(panel.index, panel["perp_close"], color="#222", lw=0.9, label="BTCUSDT perp close (log)")
    ax1.set_ylabel("perp close (log)"); ax1.set_xlabel("date (UTC)")
    ax2 = ax1.twinx()
    ax2.plot(panel.index, panel["mfi_xexch"], color="#c02", lw=0.8, alpha=0.85, label="cross-exchange MFI")
    ax2.axhline(80, color="#c02", ls="--", lw=0.7, alpha=0.5)
    ax2.axhline(20, color="#c02", ls="--", lw=0.7, alpha=0.5)
    ax2.set_ylabel("MFI (0-100)"); ax2.set_ylim(0, 100)
    ax1.set_title("Phase 0 — cross-exchange spot MFI (self-computed proxy) vs BTCUSDT perp price")
    fig.tight_layout(); fig.savefig(config.FIG_DIR / "phase0_mfi_vs_price.png", dpi=120); plt.close(fig)

    # 2) proxy vs single-Binance MFI
    fig, (axa, axb) = plt.subplots(2, 1, figsize=(13, 6.5), sharex=True,
                                   gridspec_kw={"height_ratios": [2, 1]})
    axa.plot(panel.index, panel["mfi_xexch"], color="#c02", lw=0.8, label="cross-exchange proxy")
    axa.plot(panel.index, panel["mfi_binance"], color="#06c", lw=0.7, alpha=0.7, label="single-Binance")
    axa.set_ylabel("MFI"); axa.legend(loc="upper left", fontsize=8)
    axa.set_title(f"Phase 0 — cross-exchange vs single-Binance MFI  (corr={corr_proxy_binance:.3f}, "
                  f"mean|diff|={mad:.2f})")
    axb.plot(panel.index, panel["mfi_xexch"] - panel["mfi_binance"], color="#555", lw=0.6)
    axb.axhline(0, color="k", lw=0.5); axb.set_ylabel("proxy − Binance")
    fig.tight_layout(); fig.savefig(config.FIG_DIR / "phase0_proxy_vs_binance.png", dpi=120); plt.close(fig)

    # 3) venue composition
    fig, ax = plt.subplots(figsize=(13, 3.2))
    ax.plot(panel.index, panel["n_venues"], color="#093", lw=1.0, drawstyle="steps-post")
    ax.set_ylabel("# venues"); ax.set_ylim(0, len(config.SPOT_VENUES) + 0.5)
    ax.set_title("Phase 0 — spot venues contributing to the aggregate over time")
    fig.tight_layout(); fig.savefig(config.FIG_DIR / "phase0_n_venues.png", dpi=120); plt.close(fig)

    # ---- markdown report ---------------------------------------------------- #
    lines: list[str] = []
    W = lines.append
    W("# Phase 0 — Data integrity report\n")
    W("**Factor is a SELF-COMPUTED cross-exchange spot MFI proxy, NOT Glassnode's "
      "`spot_money_flow_index`.** Reconstruction differences (venue set, USDT-vs-USD, volume "
      "quality) are a documented caveat; re-run on the genuine series when a key is available.\n")
    W(f"- Analysis window: **{config.START_DATE} → {config.END_DATE}**  (warm-up from "
      f"{config.WARMUP_START} feeds trailing windows)")
    W(f"- Panel rows: **{len(panel)}**   ·   calendar days expected: {len(full_days)}   ·   "
      f"missing days: **{len(missing)}**")
    W(f"- MFI period: {config.MFI_PERIOD}   ·   factor lag: ≥{config.FACTOR_LAG_BARS} bar   ·   "
      f"execution: {config.EXECUTION}\n")

    W("## Raw source coverage\n")
    W("Rows pulled per source (incl. warm-up):\n")
    for v, df in spot.items():
        rng = f"{df.index.min().date()}..{df.index.max().date()}" if len(df) else "EMPTY"
        W(f"- spot `{v}`: {len(df)} rows  ({rng})")
    W(f"- perp klines: {len(kl)} rows  ({kl.index.min().date()}..{kl.index.max().date()})")
    W(f"- funding 8h: {len(fr)} rows  ({fr.index.min()}..{fr.index.max()})\n")
    W("Per-venue / per-year coverage (analysis window):\n")
    W("```")
    W(cov.pivot(index="year", columns="venue", values="coverage").fillna(0.0).to_string())
    W("```")
    if kraken_join is not None:
        W(f"\n> Kraken's API serves only the most recent ~720 daily candles, so it contributes only "
          f"from **{kraken_join.date()}**. Handled transparently (no fill); disclosed here and in the "
          f"venue-composition figure.\n")

    W("## Panel integrity\n")
    W("NaN counts per column (analysis window):\n")
    W("```"); W(nan_counts.to_string()); W("```")
    if len(missing):
        W(f"\n⚠️ Missing calendar days: {len(missing)} — first few: "
          f"{[d.date().isoformat() for d in missing[:5]]}")
    else:
        W("\n✓ No missing calendar days in the analysis window.")
    W("\nVenue-count distribution across panel days:\n")
    W("```"); W(nven.to_string()); W("```")

    W("\n## Factor sanity\n")
    W(f"- MFI range: [{mx.min():.1f}, {mx.max():.1f}]   mean {mx.mean():.1f}   median {mx.median():.1f}")
    W(f"- Time > 80 (overbought): **{frac_ob*100:.1f}%**   ·   time < 20 (oversold): **{frac_os*100:.1f}%**")
    W(f"- Cross-exchange vs single-Binance MFI: corr **{corr_proxy_binance:.3f}**, "
      f"mean |diff| **{mad:.2f}** MFI points")
    W(f"- Mean daily funding annualized: **{fund_ann:.2f}%/yr** (>0 ⇒ longs pay)\n")

    W("## Figures\n")
    W("- `figures/phase0_mfi_vs_price.png` — MFI vs perp price (80/20 bands)")
    W("- `figures/phase0_proxy_vs_binance.png` — cross-exchange vs single-Binance MFI + difference")
    W("- `figures/phase0_n_venues.png` — venue composition over time\n")

    (config.OUTPUT_DIR / "phase0_integrity.md").write_text("\n".join(lines), encoding="utf-8")

    # ---- console summary ---------------------------------------------------- #
    print("PHASE 0 OK")
    print(f"  panel rows={len(panel)}  missing_days={len(missing)}  nan_total={int(nan_counts.sum())}")
    print(f"  MFI range=[{mx.min():.1f},{mx.max():.1f}] mean={mx.mean():.1f}  >80={frac_ob*100:.1f}%  <20={frac_os*100:.1f}%")
    print(f"  proxy-vs-binance corr={corr_proxy_binance:.3f} mean|diff|={mad:.2f}")
    print(f"  n_venues dist: {{{', '.join(f'{k}: {v}' for k, v in nven.items())}}}")
    print(f"  funding annualized={fund_ann:.2f}%/yr")
    print("  wrote output/phase0_integrity.md + 3 figures")


if __name__ == "__main__":
    main()
