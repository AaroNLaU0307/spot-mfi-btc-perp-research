"""Money Flow Index — single-series and cross-exchange aggregate — plus panel assembly.

MFI (Glassnode-compatible definition, 14-day):
    typical price  tp_t = (H + L + C) / 3
    raw money flow rmf_t = tp_t * volume_t
    tp_t up vs tp_{t-1}  -> rmf_t is POSITIVE flow; down -> NEGATIVE flow; equal -> neither
    MFR = sum_{14}(positive) / sum_{14}(negative)
    MFI = 100 - 100/(1 + MFR)   ==   100 * pos / (pos + neg)     [division-safe form used here]

Cross-exchange aggregate (the self-computed proxy for Glassnode's cross-venue series):
    per day, over the venues PRESENT that day,
        agg_vol = Σ_v vol_v            (total BTC volume)
        agg_rmf = Σ_v tp_v * vol_v     (total USD money flow)
        agg_tp  = agg_rmf / agg_vol    (volume-weighted typical price -> defines direction)
    then standard MFI on (agg_tp, agg_vol). Missing venues are simply excluded that day
    (never filled); ``n_venues`` records how many contributed.

DISCLOSURE: this is a SELF-COMPUTED proxy, NOT Glassnode's spot_money_flow_index.
"""
from __future__ import annotations

import pandas as pd

import config


def typical_price(df: pd.DataFrame) -> pd.Series:
    return (df["high"] + df["low"] + df["close"]) / 3.0


def _mfi_core(tp: pd.Series, vol: pd.Series, period: int) -> pd.Series:
    """Standard MFI from a typical-price and volume series (division-safe)."""
    rmf = tp * vol
    d = tp.diff()
    pos = rmf.where(d > 0, 0.0)
    neg = rmf.where(d < 0, 0.0)
    pos14 = pos.rolling(period, min_periods=period).sum()
    neg14 = neg.rolling(period, min_periods=period).sum()
    denom = pos14 + neg14
    mfi = 100.0 * pos14 / denom
    mfi[denom == 0] = float("nan")      # 14 flat days (degenerate) -> undefined
    return mfi.rename("mfi")


def mfi_single(df: pd.DataFrame, period: int = config.MFI_PERIOD) -> pd.Series:
    """MFI computed on a single venue's OHLCV frame."""
    return _mfi_core(typical_price(df), df["volume"], period)


def aggregate_bar(frames: dict[str, pd.DataFrame],
                  venues: list[str] | None = None) -> pd.DataFrame:
    """Cross-exchange aggregate daily bar: volume-weighted typical price + total flow.

    Returns columns: agg_tp, agg_vol, agg_rmf, n_venues (indexed by the union of venue days).
    """
    venues = venues or list(frames)
    vol_cols, rmf_cols = {}, {}
    for v in venues:
        df = frames.get(v)
        if df is None or df.empty:
            continue
        tp = typical_price(df)
        vol_cols[v] = df["volume"]
        rmf_cols[v] = tp * df["volume"]
    if not vol_cols:
        raise ValueError("no venue data to aggregate")
    VOL = pd.DataFrame(vol_cols).sort_index()
    RMF = pd.DataFrame(rmf_cols).sort_index()
    agg_vol = VOL.sum(axis=1, min_count=1)
    agg_rmf = RMF.sum(axis=1, min_count=1)
    agg_tp = agg_rmf / agg_vol
    n_ven = VOL.notna().sum(axis=1).astype(int)
    return pd.DataFrame({"agg_tp": agg_tp, "agg_vol": agg_vol,
                         "agg_rmf": agg_rmf, "n_venues": n_ven})


def cross_exchange_mfi(frames: dict[str, pd.DataFrame],
                       period: int = config.MFI_PERIOD,
                       venues: list[str] | None = None) -> pd.Series:
    """Cross-exchange MFI proxy (the primary factor)."""
    agg = aggregate_bar(frames, venues)
    return _mfi_core(agg["agg_tp"], agg["agg_vol"], period).rename("mfi_xexch")


def assemble_panel(spot_frames: dict[str, pd.DataFrame],
                   perp_klines: pd.DataFrame,
                   daily_funding: pd.Series,
                   period: int = config.MFI_PERIOD) -> pd.DataFrame:
    """Aligned daily panel over the analysis window [START_DATE, END_DATE].

    Columns:
      mfi_xexch     cross-exchange MFI proxy (primary factor; computed over warm-up then clipped)
      mfi_binance   single-venue Binance MFI (for the proxy-vs-single comparison)
      n_venues      venues contributing to the aggregate that day
      spot_agg_tp   aggregate spot typical price (for the MFI-vs-price overlay)
      perp_open     perp open  (next-open execution price)
      perp_close    perp close (daily MTM)
      funding       daily funding rate (Σ of 8h; >0 ⇒ longs pay)
    Factor columns are computed on warm-up history so they are already valid at START_DATE.
    """
    agg = aggregate_bar(spot_frames)
    mfi_x = _mfi_core(agg["agg_tp"], agg["agg_vol"], period)
    mfi_b = mfi_single(spot_frames["binance"], period)

    panel = pd.DataFrame({
        "mfi_xexch": mfi_x,
        "mfi_binance": mfi_b,
        "n_venues": agg["n_venues"],
        "spot_agg_tp": agg["agg_tp"],
        "perp_open": perp_klines["open"],
        "perp_close": perp_klines["close"],
        "funding": daily_funding,
    }).sort_index()
    return panel.loc[config.START_DATE:config.END_DATE]
