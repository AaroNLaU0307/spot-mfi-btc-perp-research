"""Phase 4 — 2D grid evaluation, plateau (anti-spike) test, and embargoed walk-forward.

Design that avoids leakage and is cheap:
  * Each config's signal is causal (trailing), so we compute each config's FULL-sample daily net
    series ONCE. The full-sample Sharpe grid feeds the heatmap + plateau test; slicing the same
    series to IS/OOS windows feeds the walk-forward. No config is re-fit per split.
  * Walk-forward: select the best config by IS net Sharpe, evaluate on the next OOS block, aggregate
    all OOS blocks into ONE out-of-sample equity curve (the verdict number).
  * Embargo: EMBARGO_BARS (=MFI_PERIOD=14) bars are dropped between each IS end and OOS start, so the
    test block's early bars share no MFI-window inputs with the train block's late bars. This is NOT
    paired with a separate "purge" step: config selection here uses TRAILING in-sample Sharpe over a
    strict anchored prefix, with no forward-looking training labels to purge, so the single embargo
    gap is the whole leakage guarantee (see tests/test_walkforward.py and docs/AUDIT.md). Contrast
    with the combinatorial split boundaries in src/pbo.py, which have many boundaries per split and
    DO perform a genuine purge of train-side rows at each one.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

import config
from . import backtest, performance as perf, signals, stats


def evaluate_grid(panel: pd.DataFrame, model_name: str = "M1_level",
                  cost_mult: float = 1.0) -> tuple[pd.DataFrame, dict]:
    """Full-sample metrics for every config in the model's grid.

    Returns (metrics_df indexed by (p1, p2), {(p1, p2): net_return_series}).
    """
    spec = signals.MODELS[model_name]
    fn = spec["fn"]
    (g1, g2) = spec["grid"]
    p1n, p2n = spec["param_names"]
    mfi = panel["mfi_xexch"]

    rows, series = [], {}
    for p1 in g1:
        for p2 in g2:
            tgt = fn(mfi, p1, p2)
            res = backtest.run_backtest(tgt, panel, cost_mult=cost_mult)
            sr_pp, n_days, skew, kurt = stats.sharpe_moments(res.net)
            m = res.metrics
            rows.append({p1n: p1, p2n: p2, "sharpe": m["sharpe"], "ann_return": m["ann_return"],
                         "max_drawdown": m["max_drawdown"], "exposure": m["exposure"],
                         "n_trades": m["n_trades"], "avg_hold_days": m["avg_hold_days"],
                         "sr_pp": sr_pp, "n_days": n_days, "skew": skew, "kurt": kurt})
            series[(p1, p2)] = res.net
    df = pd.DataFrame(rows).set_index([p1n, p2n])
    return df, series


def sharpe_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Pivot the (p1, p2)-indexed metrics to a 2D Sharpe grid (rows=p1, cols=p2)."""
    return df["sharpe"].unstack()


def _native(x):
    """Unwrap a numpy scalar (e.g. np.int64) to plain Python so reprs/titles print cleanly."""
    return x.item() if hasattr(x, "item") else x


def plateau_metric(mat: pd.DataFrame) -> dict:
    """Is the peak on a contiguous plateau? 3x3 (+/-1 step each dim) neighbourhood must retain
    >= PLATEAU_MIN_FRACTION of the peak Sharpe with the SAME sign. Reports the mean/peak ratio."""
    a = mat.to_numpy(dtype=float)
    if not np.isfinite(a).any():
        return {"is_plateau": False, "reason": "no finite Sharpe"}
    pk = np.unravel_index(np.nanargmax(a), a.shape)
    peak = a[pk]
    i, j = pk
    nb = a[max(0, i - 1):i + 2, max(0, j - 1):j + 2]
    nb = nb[np.isfinite(nb)]
    same_sign = nb[np.sign(nb) == np.sign(peak)]
    ratio = float(np.mean(nb) / peak) if peak != 0 else float("nan")
    same_sign_frac = float(len(same_sign) / len(nb)) if len(nb) else 0.0
    is_plateau = bool(peak > 0 and ratio >= config.PLATEAU_MIN_FRACTION and same_sign_frac >= 0.8)
    return {"is_plateau": is_plateau, "peak_sharpe": float(peak),
            "peak_params": (_native(mat.index[i]), _native(mat.columns[j])),
            "nbhd_mean": float(np.mean(nb)), "nbhd_mean_to_peak": ratio,
            "same_sign_frac": same_sign_frac, "n_neighbours": int(len(nb))}


@dataclass
class WalkForwardResult:
    oos_returns: pd.Series
    splits: list = field(default_factory=list)          # per-split selection + IS/OOS Sharpe
    oos_sharpe: float = float("nan")
    oos_metrics: dict = field(default_factory=dict)


def walk_forward(panel: pd.DataFrame, series: dict, model_name: str = "M1_level",
                 scheme: str = config.WF_SCHEME, n_splits: int = config.WF_N_SPLITS,
                 min_train: int = config.WF_MIN_TRAIN_BARS, embargo: int = config.EMBARGO_BARS,
                 min_trades: int = 5) -> WalkForwardResult:
    """Anchored/rolling embargoed walk-forward over the precomputed config net series."""
    idx = panel.index
    n = len(idx)
    p1n, p2n = signals.MODELS[model_name]["param_names"]
    bounds = np.linspace(min_train, n, n_splits + 1).astype(int)

    oos_parts, splits = [], []
    for k in range(n_splits):
        oos_lo, oos_hi = bounds[k], bounds[k + 1]
        is_hi = oos_lo - embargo                          # embargo gap
        is_lo = 0 if scheme == "anchored" else max(0, is_hi - min_train)
        if is_hi - is_lo < min_train // 2:
            continue
        is_dates = idx[is_lo:is_hi]
        oos_dates = idx[oos_lo:oos_hi]

        # select best config by IS net Sharpe (guard against too-few-trade configs)
        best, best_sr = None, -np.inf
        for key, s in series.items():
            iss = s.reindex(is_dates).dropna()
            if (iss != 0).sum() < min_trades:
                continue
            sr = perf.sharpe_ratio(iss)
            if np.isfinite(sr) and sr > best_sr:
                best_sr, best = sr, key
        if best is None:                                  # fallback: highest IS Sharpe regardless
            best = max(series, key=lambda k_: perf.sharpe_ratio(series[k_].reindex(is_dates).dropna()))
            best_sr = perf.sharpe_ratio(series[best].reindex(is_dates).dropna())

        oos_ret = series[best].reindex(oos_dates).dropna()
        oos_parts.append(oos_ret)
        splits.append({"split": k, "is": (is_dates[0].date(), is_dates[-1].date()),
                       "oos": (oos_dates[0].date(), oos_dates[-1].date()),
                       p1n: best[0], p2n: best[1], "is_sharpe": round(best_sr, 3),
                       "oos_sharpe": round(perf.sharpe_ratio(oos_ret), 3),
                       "oos_ann": round(perf.annual_return(oos_ret), 4)})

    oos = pd.concat(oos_parts).sort_index() if oos_parts else pd.Series(dtype=float)
    return WalkForwardResult(oos_returns=oos, splits=splits,
                             oos_sharpe=perf.sharpe_ratio(oos) if len(oos) else float("nan"),
                             oos_metrics=perf.metrics(oos) if len(oos) else {})
