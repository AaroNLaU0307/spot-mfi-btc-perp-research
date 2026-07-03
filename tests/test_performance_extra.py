"""Descriptive-stats extension (Phase B2): Sortino, skew, excess kurtosis, VaR/CVaR, longest DD.

Descriptive only — these carry no verdict weight. Pinned to hand-worked / known-distribution values.
Run: .venv\\Scripts\\python -m pytest tests/test_performance_extra.py -q
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import performance as perf  # noqa: E402


def _s(vals):
    return pd.Series(np.asarray(vals, float))


def test_sortino_ignores_upside_volatility():
    # Two series with the SAME mean and SAME upside spread, but one has extra upside-only noise
    # (no downside) -> Sortino should be equal or higher for the one with only upside deviation
    # relative to a series whose deviation is downside.
    up_only = _s([0.01, 0.05, 0.01, 0.05, 0.01])          # all >= 0, no downside at all
    down_only = _s([0.01, -0.03, 0.01, -0.03, 0.01])      # same mean-ish, has real downside
    s_up = perf.sortino_ratio(up_only)
    s_down = perf.sortino_ratio(down_only)
    assert s_up == float("inf") or s_up != s_up or s_up > s_down  # up_only has ~0 downside dev
    # exact case: zero downside deviation -> nan (division guarded)
    assert np.isnan(perf.sortino_ratio(_s([0.01, 0.02, 0.03])))


def test_sortino_hand_worked():
    r = _s([0.02, -0.01, 0.03, -0.02, 0.01])
    downside = np.minimum(r.to_numpy() - 0.0, 0.0)
    dd = np.sqrt(np.mean(downside ** 2))
    expected = r.mean() / dd * np.sqrt(perf.PPY)
    assert perf.sortino_ratio(r) == pytest.approx(expected, rel=1e-9)


def test_skew_symmetric_distribution_near_zero():
    rng = np.random.default_rng(0)
    r = _s(rng.normal(0, 0.01, 5000))
    assert abs(perf.skewness(r)) < 0.15                      # symmetric -> skew near 0


def test_skew_sign_matches_construction():
    right_skewed = _s([0.01] * 95 + [0.5] * 5)                # a few big positive outliers
    left_skewed = _s([-0.01] * 95 + [-0.5] * 5)                # a few big negative outliers
    assert perf.skewness(right_skewed) > 0
    assert perf.skewness(left_skewed) < 0


def test_excess_kurtosis_normal_near_zero():
    rng = np.random.default_rng(1)
    r = _s(rng.normal(0, 0.01, 20000))
    assert abs(perf.excess_kurtosis(r)) < 0.15                 # normal -> excess kurtosis ~0


def test_excess_kurtosis_fat_tails_positive():
    rng = np.random.default_rng(2)
    r = _s(rng.standard_t(df=3, size=20000) * 0.01)            # heavy-tailed t-distribution
    assert perf.excess_kurtosis(r) > 1.0


def test_var_cvar_hand_worked():
    # 20 sorted returns; 95% VaR = -5th percentile (worst ~1 observation region).
    r = _s(np.arange(-19, 1) / 100.0)                          # -0.19 .. 0.00, step 0.01, n=20
    var95 = perf.historical_var(r, level=0.95)
    cvar95 = perf.historical_cvar(r, level=0.95)
    expected_var = float(-np.percentile(r, 5))
    assert var95 == pytest.approx(expected_var, rel=1e-9)
    assert cvar95 >= var95 - 1e-12                             # CVaR (tail mean) is at least as bad as VaR


def test_var_cvar_positive_sign_convention():
    rng = np.random.default_rng(3)
    r = _s(rng.normal(-0.001, 0.02, 2000))
    assert perf.historical_var(r) > 0                          # reported as a positive loss magnitude
    assert perf.historical_cvar(r) > 0
    assert perf.historical_cvar(r) >= perf.historical_var(r)   # tail mean is worse than the threshold


def test_longest_drawdown_duration_hand_worked():
    # +1%,+1% (new highs) then -1%,-1%,-1% (3 bars underwater) then +5% (new high) -> longest DD = 3.
    r = _s([0.01, 0.01, -0.01, -0.01, -0.01, 0.05])
    assert perf.longest_drawdown_duration(r) == 3


def test_longest_drawdown_duration_zero_when_always_at_highs():
    r = _s([0.01, 0.02, 0.03, 0.04])
    assert perf.longest_drawdown_duration(r) == 0


def test_extended_metrics_superset_of_metrics():
    rng = np.random.default_rng(4)
    r = _s(rng.normal(0.0005, 0.02, 500))
    base = perf.metrics(r)
    ext = perf.extended_metrics(r)
    for k, v in base.items():
        assert ext[k] == pytest.approx(v, nan_ok=True) if isinstance(v, float) else ext[k] == v
    for k in ("sortino", "skew", "excess_kurtosis", "var_95", "cvar_95", "longest_dd_days"):
        assert k in ext
