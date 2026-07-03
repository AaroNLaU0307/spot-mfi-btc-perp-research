"""Phase 1 — factor exploratory analysis (NO strategy PnL).

Characterises the MFI factor and its predictive structure vs BTCUSDT-perp forward
returns: Information Coefficient across transforms/horizons, decile bucket analysis
(sign + shape), stationarity and autocorrelation. Everything is causal — factor
transforms use TRAILING windows only; the signal is lagged by ``FACTOR_LAG_BARS`` so
the IC reflects tradable timing.

Overlap caveat: forward returns at horizon h > 1 overlap across days, so naive IC
p-values are optimistic. We report a non-overlapping IC (sample every h days) alongside,
and defer the rigorous significance test to Phase 5 (block bootstrap / permutation).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from statsmodels.tsa.stattools import acf, adfuller, kpss

import config


def forward_returns(price: pd.Series, horizons=config.IC_HORIZONS) -> pd.DataFrame:
    """Strictly-forward simple returns: r_h(t) = price(t+h)/price(t) − 1."""
    return pd.DataFrame({h: price.shift(-h) / price - 1.0 for h in horizons})


def transforms(mfi: pd.Series) -> pd.DataFrame:
    """Causal factor transforms (all trailing): raw level, rolling z-score,
    trailing percentile rank, rate-of-change."""
    z = (mfi - mfi.rolling(config.ZSCORE_WINDOW, min_periods=config.ZSCORE_WINDOW).mean()) / \
        mfi.rolling(config.ZSCORE_WINDOW, min_periods=config.ZSCORE_WINDOW).std(ddof=0)
    pctile = mfi.rolling(config.PERCENTILE_WINDOW, min_periods=config.PERCENTILE_WINDOW) \
                .apply(lambda a: (a <= a[-1]).mean(), raw=True)
    roc = mfi - mfi.shift(config.ROC_WINDOW)
    return pd.DataFrame({"level": mfi, "zscore": z, "percentile": pctile, "roc": roc})


def ic_table(signals: pd.DataFrame, fwd: pd.DataFrame,
             lag: int = config.FACTOR_LAG_BARS) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Spearman IC (and naive p-value) for every (transform × horizon). Signal lagged."""
    ic = pd.DataFrame(index=signals.columns, columns=fwd.columns, dtype=float)
    pv = ic.copy()
    for name in signals.columns:
        s = signals[name].shift(lag)
        for h in fwd.columns:
            df = pd.concat([s, fwd[h]], axis=1).dropna()
            if len(df) > 10:
                r, p = spearmanr(df.iloc[:, 0], df.iloc[:, 1])
                ic.loc[name, h], pv.loc[name, h] = r, p
    return ic.astype(float), pv.astype(float)


def ic_nonoverlap(signal: pd.Series, fwd_h: pd.Series, h: int,
                  lag: int = config.FACTOR_LAG_BARS) -> tuple[float, float, int]:
    """IC on non-overlapping samples (every h bars) → honest p-value for horizon h."""
    df = pd.concat([signal.shift(lag), fwd_h], axis=1).dropna()
    df = df.iloc[::h]
    if len(df) < 10:
        return float("nan"), float("nan"), len(df)
    r, p = spearmanr(df.iloc[:, 0], df.iloc[:, 1])
    return float(r), float(p), len(df)


def decile_stats(signal: pd.Series, fwd_h: pd.Series, n: int = config.N_BUCKETS,
                 lag: int = config.FACTOR_LAG_BARS) -> pd.DataFrame:
    """Mean forward return per signal bucket (reveals monotone vs U/inverted-U shape)."""
    df = pd.concat([signal.shift(lag).rename("s"), fwd_h.rename("r")], axis=1).dropna()
    df["bucket"] = pd.qcut(df["s"], n, labels=False, duplicates="drop")
    g = df.groupby("bucket")
    out = g["r"].agg(["mean", "std", "count"])
    out["signal_mid"] = g["s"].median()
    return out


def stationarity(series: pd.Series) -> dict:
    """ADF (H0: unit root) + KPSS (H0: stationary). Both reported; they cross-check."""
    s = series.dropna()
    adf = adfuller(s, autolag="AIC")
    try:
        kp = kpss(s, regression="c", nlags="auto")
        kp_stat, kp_p = float(kp[0]), float(kp[1])
    except Exception:  # noqa: BLE001 - KPSS can raise on some inputs
        kp_stat, kp_p = float("nan"), float("nan")
    return {"adf_stat": float(adf[0]), "adf_p": float(adf[1]),
            "kpss_stat": kp_stat, "kpss_p": kp_p, "n": int(len(s))}


def autocorr(series: pd.Series, nlags: int = 10) -> np.ndarray:
    return acf(series.dropna(), nlags=nlags, fft=True)
