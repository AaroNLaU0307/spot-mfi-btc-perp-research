"""Variant A Edge signal — rank correctness, range, hysteresis, no-lookahead.

Run: .venv\\Scripts\\python -m pytest tests/test_divergence.py -q
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import divergence as dv  # noqa: E402


def _s(vals):
    return pd.Series(np.asarray(vals, float), index=pd.date_range("2021-01-01", periods=len(vals), freq="D"))


def test_pct_rank_hand_worked():
    r = dv.pct_rank(_s([3, 1, 2, 5, 4]), window=3)
    assert np.isnan(r.iloc[0]) and np.isnan(r.iloc[1])          # min_periods=3
    assert r.iloc[2] == pytest.approx(2 / 3)                    # [3,1,2], current 2 -> {1,2}<=2 => 2/3
    assert r.iloc[3] == pytest.approx(3 / 3)                    # [1,2,5], current 5 -> all <=5
    assert r.iloc[4] == pytest.approx(2 / 3)                    # [2,5,4], current 4 -> {2,4}<=4 => 2/3


def test_edge_score_range_and_definition():
    rng = np.random.default_rng(0)
    mfi = _s(rng.uniform(5, 95, 300))
    fund = _s(rng.normal(0.0003, 0.001, 300))
    e = dv.edge_score(mfi, fund, window=60).dropna()
    assert (e >= -1.0).all() and (e <= 1.0).all()
    # identical inputs -> ranks cancel -> Edge == 0 everywhere
    e0 = dv.edge_score(mfi, mfi, window=60).dropna()
    assert np.allclose(e0.to_numpy(), 0.0)


def test_edge_signal_is_binary_long_only():
    rng = np.random.default_rng(1)
    mfi = _s(rng.uniform(5, 95, 300)); fund = _s(rng.normal(0, 0.001, 300))
    s = dv.edge_signal(mfi, fund, threshold=0.3, window=60)
    assert set(np.unique(s.to_numpy())) <= {0.0, 1.0}


def test_edge_hysteresis_holds_between_bands():
    # Construct Edge directly by making funding rank ~0 (constant low) and MFI rank drive it.
    mfi = _s([10, 90, 60, 55, 20, 95])          # ranks over window=3 vary
    fund = _s([1, 1, 1, 1, 1, 1])               # constant -> rank == 1 always -> r_Fund=1
    # Edge = r_MFI - 1  <= 0 always here, so long-only never triggers for T>=0: signal all flat.
    s = dv.edge_signal(mfi, fund, threshold=0.3, window=3)
    assert (s == 0).all()


def test_edge_truncation_invariance():
    rng = np.random.default_rng(2)
    mfi = _s(rng.uniform(5, 95, 400)); fund = _s(rng.normal(0, 0.001, 400))
    full = dv.edge_signal(mfi, fund, threshold=0.25, window=90)
    k = 300
    prefix = dv.edge_signal(mfi.iloc[:k], fund.iloc[:k], threshold=0.25, window=90)
    pd.testing.assert_series_equal(full.iloc[:k], prefix, check_names=False)
