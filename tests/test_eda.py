"""EDA factor transforms — trailing-only (no lookahead) + forward-return correctness.

``eda.transforms()`` builds the zscore/percentile/roc signals fed into the IC table; none of these
had a direct truncation-invariance test (the property that makes them safe to use online). Also
covers ``forward_returns`` (must be strictly forward, never using data at or before t).

Run: .venv\\Scripts\\python -m pytest tests/test_eda.py -q
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import eda  # noqa: E402


def _s(vals):
    return pd.Series(np.asarray(vals, float), index=pd.date_range("2020-01-01", periods=len(vals), freq="D"))


def test_transforms_truncation_invariance():
    """Every column of eda.transforms() must be unaffected by future data (trailing-only)."""
    rng = np.random.default_rng(0)
    mfi = _s(rng.uniform(10, 90, 400))
    full = eda.transforms(mfi)
    k = 300
    prefix = eda.transforms(mfi.iloc[:k])
    pd.testing.assert_frame_equal(full.iloc[:k], prefix, check_names=False)


def test_transforms_columns_and_bounds():
    rng = np.random.default_rng(1)
    mfi = _s(rng.uniform(10, 90, 300))
    t = eda.transforms(mfi)
    assert set(t.columns) == {"level", "zscore", "percentile", "roc"}
    pctl = t["percentile"].dropna()
    assert (pctl >= 0).all() and (pctl <= 1).all()
    pd.testing.assert_series_equal(t["level"], mfi, check_names=False)


def test_forward_returns_strictly_forward():
    price = _s([100, 110, 121, 133.1, 146.41])
    fwd = eda.forward_returns(price, horizons=(1, 2))
    # r_1(t) = price(t+1)/price(t) - 1 = 0.10 for this geometric series; last row is NaN (no t+1).
    assert fwd[1].iloc[0] == pytest.approx(0.10, rel=1e-9)
    assert pd.isna(fwd[1].iloc[-1])
    # r_2(0) = price(2)/price(0) - 1 = 0.21
    assert fwd[2].iloc[0] == pytest.approx(0.21, rel=1e-9)


def test_ic_nonoverlap_uses_lagged_signal():
    """The signal must be lagged before pairing with the forward return (no same-bar peek).
    ic_nonoverlap requires >=10 paired rows (else it returns NaN by design), so use 20 points."""
    idx = pd.date_range("2020-01-01", periods=20, freq="D")
    sig = pd.Series(range(20), index=idx, dtype=float)          # 0,1,2,...,19
    fwd = pd.Series(range(20), index=idx, dtype=float)          # deliberately identical to sig
    r_lag1, _, n = eda.ic_nonoverlap(sig, fwd, h=1, lag=1)
    # With lag=1, sig(t) pairs with fwd(t) using shift(1): sig value at t is the t-1 raw value.
    # Perfect rank correlation should still hold (monotone shift of a monotone series).
    assert r_lag1 == pytest.approx(1.0)
    assert n == 19                                                # one row dropped by the lag


def test_decile_stats_bucket_count_and_no_lookahead():
    rng = np.random.default_rng(2)
    idx = pd.date_range("2020-01-01", periods=500, freq="D")
    sig = pd.Series(rng.uniform(0, 100, 500), index=idx)
    fwd = pd.Series(rng.normal(0, 0.01, 500), index=idx)
    out = eda.decile_stats(sig, fwd, n=10, lag=1)
    assert len(out) <= 10
    assert out["count"].sum() <= 499                              # lag drops the first row
