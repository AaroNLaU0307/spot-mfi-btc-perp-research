"""Backtester mechanics + no-lookahead, and signal truncation-invariance.

Run: .venv\\Scripts\\python -m pytest tests/test_backtest.py -q
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from src import backtest, signals  # noqa: E402


def _panel(opens, funding, mfi=None):
    idx = pd.date_range("2021-01-01", periods=len(opens), freq="D")
    return pd.DataFrame({
        "perp_open": np.asarray(opens, float),
        "funding": np.asarray(funding, float),
        "mfi_xexch": np.asarray(mfi if mfi is not None else [50.0] * len(opens), float),
    }, index=idx)


def test_costs_and_lag_hand_worked():
    # +10%/bar opens; constant-long target; fee+slip = 0.0007; funding 0.001/day.
    panel = _panel([100, 110, 121, 133.1, 146.41], [0.001] * 5)
    target = pd.Series(1.0, index=panel.index)
    res = backtest.run_backtest(target, panel)
    net = res.net.to_numpy()
    # bar0 is flat (position lagged in): net=0. bar1 pays entry txn + funding.
    assert net[0] == pytest.approx(0.0)
    assert net[1] == pytest.approx(0.1 - 0.0007 - 0.001, rel=1e-9)
    assert net[2] == pytest.approx(0.1 - 0.001, rel=1e-9)          # no txn (no turnover)
    assert len(res.net) == 4                                        # last bar drops (no next open)
    # benchmark bh_perp = oo - funding
    assert res.bench["bh_perp"]["ann_return"] == pytest.approx(
        backtest.perf.metrics(pd.Series([0.099, 0.099, 0.099, 0.099]))["ann_return"], rel=1e-9)


def test_flat_signal_zero_pnl():
    panel = _panel([100, 101, 102, 103, 104], [0.001] * 5)
    res = backtest.run_backtest(pd.Series(0.0, index=panel.index), panel)
    assert (res.net.abs() < 1e-12).all()
    assert res.metrics["n_trades"] == 0
    assert res.metrics["exposure"] == 0.0


def test_long_gross_equals_price_return_when_held():
    panel = _panel([100, 105, 100, 110, 121], [0.0] * 5)
    res = backtest.run_backtest(pd.Series(1.0, index=panel.index), panel)
    oo = panel["perp_open"].shift(-1) / panel["perp_open"] - 1.0
    held = res.daily["pos"] > 0
    # where held with zero funding/first-bar, gross == open-to-open return
    assert np.allclose(res.daily.loc[held, "gross"], (res.daily.loc[held, "pos"] * oo.reindex(res.daily.index))[held])


def test_signal_truncation_invariance():
    # Trailing-only signal ⇒ computing on a prefix matches the full series on the overlap.
    rng = np.random.default_rng(0)
    mfi = pd.Series(rng.uniform(10, 90, 400), index=pd.date_range("2020-01-01", periods=400, freq="D"))
    full = signals.signal_level_threshold(mfi, threshold=70, window=3)
    k = 250
    prefix = signals.signal_level_threshold(mfi.iloc[:k], threshold=70, window=3)
    pd.testing.assert_series_equal(full.iloc[:k], prefix, check_names=False)


def test_hysteresis_holds_between_bands():
    # entry when >70, exit when <50; a mid value (60) must HOLD the prior state.
    mfi = pd.Series([40, 75, 60, 55, 45, 60, 80],
                    index=pd.date_range("2021-01-01", periods=7, freq="D"))
    s = signals.signal_level_threshold(mfi, threshold=70, window=1)
    assert s.tolist() == [0, 1, 1, 1, 0, 0, 1]     # 60→hold long, 45→exit, 60→stay flat, 80→re-enter
