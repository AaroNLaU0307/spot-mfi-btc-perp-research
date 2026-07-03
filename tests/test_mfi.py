"""MFI correctness — hand-worked example + cross-exchange aggregation properties.

A wrong factor invalidates the whole study, so the core is pinned to numbers computed by
hand. Run: ``.venv\\Scripts\\python -m pytest tests/test_mfi.py -q``
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import mfi  # noqa: E402


def _ohlcv(closes, vols):
    """Frame with high=low=close so typical price == close (isolates the flow logic)."""
    idx = pd.date_range("2020-01-01", periods=len(closes), freq="D")
    c = np.asarray(closes, float)
    return pd.DataFrame({"high": c, "low": c, "close": c, "volume": np.asarray(vols, float)}, index=idx)


def test_mfi_hand_worked_period3():
    # closes:  10  11   10   12   11   13   (all vol=100)
    # diff:     .  +1   -1   +2   -1   +2
    # rmf pos/neg (=close*100): d1 +1100, d2 -1000, d3 +1200, d4 -1100, d5 +1300
    df = _ohlcv([10, 11, 10, 12, 11, 13], [100] * 6)
    m = mfi.mfi_single(df, period=3)
    # d3 window {d1,d2,d3}: pos=1100+1200=2300, neg=1000 -> 100*2300/3300
    # d4 window {d2,d3,d4}: pos=1200, neg=1000+1100=2100 -> 100*1200/3300
    assert m.iloc[:2].isna().all()                      # min_periods=3
    assert m.iloc[3] == pytest.approx(100 * 2300 / 3300, rel=1e-9)
    assert m.iloc[4] == pytest.approx(100 * 1200 / 3300, rel=1e-9)
    assert (m.dropna() >= 0).all() and (m.dropna() <= 100).all()


def test_mfi_all_up_is_100_all_down_is_0():
    up = _ohlcv([1, 2, 3, 4, 5], [10] * 5)
    dn = _ohlcv([5, 4, 3, 2, 1], [10] * 5)
    assert mfi.mfi_single(up, period=3).iloc[-1] == pytest.approx(100.0)
    assert mfi.mfi_single(dn, period=3).iloc[-1] == pytest.approx(0.0)


def test_single_venue_aggregate_equals_single():
    df = _ohlcv([10, 11, 10, 12, 11, 13, 12, 14], [100, 120, 90, 110, 130, 100, 95, 105])
    frames = {"solo": df}
    agg = mfi.cross_exchange_mfi(frames, period=4)
    single = mfi.mfi_single(df, period=4)
    pd.testing.assert_series_equal(agg.dropna(), single.dropna(), check_names=False)


def test_two_identical_venues_equal_single():
    df = _ohlcv([10, 11, 10, 12, 11, 13, 12, 14], [100, 120, 90, 110, 130, 100, 95, 105])
    frames = {"a": df, "b": df.copy()}
    agg = mfi.cross_exchange_mfi(frames, period=4)          # 2x vol & 2x flow, same tp
    single = mfi.mfi_single(df, period=4)
    pd.testing.assert_series_equal(agg.dropna(), single.dropna(), check_names=False)


def test_volume_weighted_direction():
    # Two venues disagree on direction; the high-volume venue must dominate agg_tp.
    a = _ohlcv([10, 20], [1, 1000])      # big up, huge volume
    b = _ohlcv([10, 9], [1, 1])          # small down, tiny volume
    agg = mfi.aggregate_bar({"a": a, "b": b})
    assert agg["agg_tp"].diff().iloc[1] > 0   # aggregate typical price rose (volume-weighted)
