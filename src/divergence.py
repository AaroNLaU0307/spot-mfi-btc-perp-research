"""Variant A — spot-MFI vs funding DIVERGENCE signal.

Edge_t = rank_W(MFI)_t − rank_W(daily_funding)_t  ∈ [−1, 1], where rank_W is the TRAILING percentile
rank over window W (causal). High Edge = spot strong in its own history AND funding low in its own
history = "real spot demand, leverage not crowded".

Funding enters TWICE by design and is NOT netted: here as a SIGNAL input (leverage-crowding
information — a positioning channel orthogonal to the arbitrage-locked price level), and in the
backtester as a REALISED holding cost (longs paid ≈12.5%/yr in the base study).

Rejected constructions (numerically/economically unsound — documented in PREREGISTRATION_variantA):
  * ``MFI − z(funding)``: dimensional mismatch (MFI 0–100 vs z ≈ ±3) → funding barely moves the sum.
  * ``MFI / funding``: funding crosses zero / goes negative → the ratio explodes near 0 and flips sign.
Percentile-rank differencing puts both on a common bounded [0,1] scale, robust to funding's fat tails
and sign changes.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

import config
from . import backtest, signals, stats


def pct_rank(s: pd.Series, window: int) -> pd.Series:
    """Trailing percentile rank ∈ (0, 1]: fraction of the trailing window ≤ the current value.

    Vectorised (sliding-window) — same result as ``rolling(window).apply((a<=a[-1]).mean())`` but
    fast enough for the full grid. First ``window-1`` values are NaN (min_periods=window)."""
    a = s.to_numpy(dtype=float)
    n = len(a)
    out = np.full(n, np.nan)
    if n >= window:
        w = sliding_window_view(a, window)                 # (n-window+1, window), trailing windows
        out[window - 1:] = (w <= w[:, -1][:, None]).mean(axis=1)
    return pd.Series(out, index=s.index, name=s.name)


def edge_score(mfi: pd.Series, funding: pd.Series, window: int) -> pd.Series:
    """Edge = trailing pct-rank(MFI) − trailing pct-rank(funding) ∈ [−1, 1]."""
    return (pct_rank(mfi, window) - pct_rank(funding, window)).rename("edge")


def edge_signal(mfi: pd.Series, funding: pd.Series, threshold: float, window: int,
                exit_threshold: float = config.EDGE_EXIT) -> pd.Series:
    """M1 (long-only, hysteresis): long when Edge > threshold; flat when Edge < exit_threshold."""
    e = edge_score(mfi, funding, window)
    return signals._hysteresis(e > threshold, e < exit_threshold)


def evaluate_edge_grid(panel: pd.DataFrame,
                       thresholds=config.GRID_EDGE_THRESHOLDS, windows=config.GRID_EDGE_WINDOWS,
                       cost_mult: float = 1.0) -> tuple[pd.DataFrame, dict]:
    """Full-sample metrics for every (T, W). Mirrors walkforward.evaluate_grid's output so the
    heatmap / plateau / walk_forward machinery works unchanged. Returns (df, {(T,W): net_series})."""
    mfi, fund = panel["mfi_xexch"], panel["funding"]
    rows, series = [], {}
    for T in thresholds:
        for W in windows:
            tgt = edge_signal(mfi, fund, T, W)
            res = backtest.run_backtest(tgt, panel, cost_mult=cost_mult)
            sr_pp, n_days, skew, kurt = stats.sharpe_moments(res.net)
            m = res.metrics
            rows.append({"threshold": T, "window": W, "sharpe": m["sharpe"], "ann_return": m["ann_return"],
                         "max_drawdown": m["max_drawdown"], "exposure": m["exposure"],
                         "n_trades": m["n_trades"], "avg_hold_days": m["avg_hold_days"],
                         "sr_pp": sr_pp, "n_days": n_days, "skew": skew, "kurt": kurt})
            series[(T, W)] = res.net
    return pd.DataFrame(rows).set_index(["threshold", "window"]), series
