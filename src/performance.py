"""Performance metrics on a daily return series (rf = 0, disclosed).

Vendored from ``multi-asset-tsmom-research/src/performance.py`` and adapted to DAILY crypto
(``PERIODS_PER_YEAR = 365`` — no weekend gap). Sharpe uses arithmetic mean/vol; ann_return is
geometric (CAGR). Kept dependency-free beyond numpy/pandas.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import config

PPY = config.PERIODS_PER_YEAR


def equity_curve(returns: pd.Series) -> pd.Series:
    return (1.0 + returns.fillna(0.0)).cumprod()


def drawdown_curve(returns: pd.Series) -> pd.Series:
    eq = equity_curve(returns)
    return eq / eq.cummax() - 1.0


def max_drawdown(returns: pd.Series) -> float:
    return float(drawdown_curve(returns).min()) if len(returns.dropna()) else float("nan")


def sharpe_ratio(returns: pd.Series, periods_per_year: int = PPY) -> float:
    r = returns.dropna()
    sd = r.std(ddof=1)
    return float(r.mean() / sd * np.sqrt(periods_per_year)) if sd > 0 and len(r) > 1 else float("nan")


def annual_return(returns: pd.Series, periods_per_year: int = PPY) -> float:
    r = returns.dropna()
    if len(r) == 0:
        return float("nan")
    return float((1.0 + r).prod() ** (periods_per_year / len(r)) - 1.0)


def annual_vol(returns: pd.Series, periods_per_year: int = PPY) -> float:
    r = returns.dropna()
    return float(r.std(ddof=1) * np.sqrt(periods_per_year)) if len(r) > 1 else float("nan")


def profit_factor(returns: pd.Series) -> float:
    r = returns.dropna()
    pos, neg = r[r > 0].sum(), -r[r < 0].sum()
    return float(pos / neg) if neg > 0 else float("inf") if pos > 0 else float("nan")


def metrics(returns: pd.Series, periods_per_year: int = PPY) -> dict[str, float]:
    """Standard summary. ``exposure`` and turnover are added by the backtester (position-aware)."""
    r = returns.dropna()
    n = len(r)
    if n == 0:
        keys = ["n", "ann_return", "ann_vol", "sharpe", "max_drawdown", "calmar", "win_rate", "profit_factor"]
        return {k: float("nan") for k in keys}
    mdd = max_drawdown(r)
    ann = annual_return(r, periods_per_year)
    return {
        "n": n,
        "ann_return": ann,
        "ann_vol": annual_vol(r, periods_per_year),
        "sharpe": sharpe_ratio(r, periods_per_year),
        "max_drawdown": mdd,
        "calmar": float(ann / abs(mdd)) if mdd < 0 else float("nan"),
        "win_rate": float((r > 0).mean()),
        "profit_factor": profit_factor(r),
    }


# --------------------------------------------------------------------------- #
# Descriptive-stats extension (Phase B2 supplementary — descriptive only, no verdict weight).
# --------------------------------------------------------------------------- #
def sortino_ratio(returns: pd.Series, periods_per_year: int = PPY, mar: float = 0.0) -> float:
    """Sortino ratio: excess mean return over the downside deviation (returns below ``mar``,
    MAR=0 by default, matching this project's rf=0 Sharpe convention). Downside deviation uses
    ALL observations (min(r-mar,0)) per the standard Sortino (1994) definition, not just losers."""
    r = returns.dropna()
    if len(r) < 2:
        return float("nan")
    downside = np.minimum(r - mar, 0.0)
    dd = np.sqrt(np.mean(downside ** 2))
    if dd == 0:
        return float("nan")
    return float((r.mean() - mar) / dd * np.sqrt(periods_per_year))


def skewness(returns: pd.Series) -> float:
    r = returns.dropna()
    sd = r.std(ddof=0)
    return float(np.mean((r - r.mean()) ** 3) / sd ** 3) if sd > 0 and len(r) > 2 else float("nan")


def excess_kurtosis(returns: pd.Series) -> float:
    """Fisher (excess) kurtosis: 0 for a normal distribution, >0 = fat-tailed."""
    r = returns.dropna()
    sd = r.std(ddof=0)
    return float(np.mean((r - r.mean()) ** 4) / sd ** 4 - 3.0) if sd > 0 and len(r) > 3 else float("nan")


def historical_var(returns: pd.Series, level: float = 0.95) -> float:
    """Historical (empirical) daily VaR at ``level`` confidence, reported as a POSITIVE loss
    magnitude: the loss not exceeded on ``level`` of days (e.g. VaR_95 = 0.03 means a 3% daily
    loss or worse happens on ~5% of days)."""
    r = returns.dropna()
    if len(r) < 2:
        return float("nan")
    return float(-np.percentile(r, (1 - level) * 100))


def historical_cvar(returns: pd.Series, level: float = 0.95) -> float:
    """Historical CVaR / expected shortfall at ``level``: mean loss magnitude in the worst
    ``1-level`` tail. Positive number, same sign convention as ``historical_var``."""
    r = returns.dropna()
    if len(r) < 2:
        return float("nan")
    thresh = np.percentile(r, (1 - level) * 100)
    tail = r[r <= thresh]
    return float(-tail.mean()) if len(tail) else float("nan")


def longest_drawdown_duration(returns: pd.Series) -> int:
    """Longest run (in bars) that the equity curve stays strictly below its running peak —
    i.e. the worst-case time-to-new-high. 0 if the equity curve never sits below its peak."""
    r = returns.dropna()
    if len(r) == 0:
        return 0
    eq = equity_curve(r)
    underwater = eq < eq.cummax()
    if not underwater.any():
        return 0
    # length of the longest consecutive True run
    grp = (~underwater).cumsum()
    run_lengths = underwater.groupby(grp).sum()
    return int(run_lengths.max())


def extended_metrics(returns: pd.Series, periods_per_year: int = PPY) -> dict[str, float]:
    """``metrics()`` plus the Phase-B2 descriptive extension. Descriptive only — carries no
    weight in any verdict (verdicts were already decided by the pre-registered gates)."""
    m = metrics(returns, periods_per_year)
    r = returns.dropna()
    m.update({
        "sortino": sortino_ratio(r, periods_per_year),
        "skew": skewness(r),
        "excess_kurtosis": excess_kurtosis(r),
        "var_95": historical_var(r, 0.95),
        "cvar_95": historical_cvar(r, 0.95),
        "longest_dd_days": longest_drawdown_duration(r),
    })
    return m
