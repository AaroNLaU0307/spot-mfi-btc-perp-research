"""Walk-forward mechanics — embargo boundary correctness + plateau/spike detection.

These were previously exercised only indirectly (via the full pipeline scripts). This file pins the
two guarantees the verdict actually rests on: (1) no split shares a leakage-adjacent window smaller
than the embargo, (2) the plateau test rejects an isolated spike and accepts a genuine plateau.

Run: .venv\\Scripts\\python -m pytest tests/test_walkforward.py -q
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from src import signals, walkforward as wf  # noqa: E402


def _synthetic_panel_and_series(n=900, seed=0):
    """A small panel + a fake {(p1,p2): net_return_series} dict, enough bars for >=2 WF splits
    at config.WF_MIN_TRAIN_BARS. Mirrors the (threshold, window) key shape of evaluate_grid()."""
    idx = pd.date_range("2020-01-01", periods=n, freq="D")
    panel = pd.DataFrame({"mfi_xexch": 50.0, "funding": 0.0, "perp_open": 100.0}, index=idx)
    rng = np.random.default_rng(seed)
    p1n, p2n = signals.MODELS["M1_level"]["param_names"]
    series = {(p1, p2): pd.Series(rng.normal(0.0005, 0.01, n), index=idx)
              for p1 in (60, 70, 80) for p2 in (1, 3, 5)}
    return panel, series, (p1n, p2n)


# ----------------------------- embargo ----------------------------- #
def test_embargo_gap_enforced_at_every_split():
    """For every split, the bars strictly between IS-end and OOS-start must number >= embargo —
    i.e. no bar is shared or leakage-adjacent across the boundary. This is the walk-forward's whole
    leakage guarantee: config selection uses trailing in-sample Sharpe over a strict anchored prefix
    with no forward-looking training labels, so there is no separate purge step to test here (contrast
    src/pbo.py's combinatorial splits, covered by tests/test_pbo.py's purge-specific tests)."""
    panel, series, _ = _synthetic_panel_and_series()
    embargo = config.EMBARGO_BARS
    result = wf.walk_forward(panel, series, "M1_level", embargo=embargo, min_train=300, n_splits=3)
    assert len(result.splits) >= 1
    idx = panel.index
    pos = {d: i for i, d in enumerate(idx.date)}
    for sp in result.splits:
        is_last_pos = pos[sp["is"][1]]
        oos_first_pos = pos[sp["oos"][0]]
        gap = oos_first_pos - is_last_pos - 1          # bars strictly between IS-end and OOS-start
        assert gap >= embargo, f"split {sp['split']}: gap={gap} < embargo={embargo}"


def test_embargo_default_matches_config():
    """The default embargo used across both studies is config.EMBARGO_BARS (>=14, >=MFI_PERIOD)."""
    assert config.EMBARGO_BARS >= config.MFI_PERIOD
    assert config.EMBARGO_BARS == config.MFI_PERIOD


def test_embargo_widening_increases_the_gap():
    """A larger embargo must produce a strictly larger (or equal, at the boundary) IS/OOS gap —
    guards against the embargo argument being silently ignored."""
    panel, series, _ = _synthetic_panel_and_series()
    idx = panel.index
    pos = {d: i for i, d in enumerate(idx.date)}

    small = wf.walk_forward(panel, series, "M1_level", embargo=14, min_train=300, n_splits=3)
    big = wf.walk_forward(panel, series, "M1_level", embargo=40, min_train=300, n_splits=3)

    def _gap(sp):
        return pos[sp["oos"][0]] - pos[sp["is"][1]] - 1

    assert _gap(big.splits[0]) > _gap(small.splits[0])
    assert _gap(big.splits[0]) >= 40


def test_anchored_scheme_is_never_shifts_left():
    """Anchored scheme: IS start must stay at bar 0 for every split (expanding window)."""
    panel, series, _ = _synthetic_panel_and_series()
    result = wf.walk_forward(panel, series, "M1_level", scheme="anchored", min_train=300, n_splits=3)
    idx = panel.index
    for sp in result.splits:
        assert sp["is"][0] == idx[0].date()


# ----------------------------- plateau / spike ----------------------------- #
def _grid(data, index_vals, col_vals) -> pd.DataFrame:
    return pd.DataFrame(np.asarray(data, dtype=float), index=list(index_vals), columns=list(col_vals))


def test_plateau_detects_genuine_plateau():
    # A 3x3 block of near-equal high Sharpes around the peak (row=3,col=3) -> plateau PASS.
    data = [[0.5, 0.5, 0.5, 0.5, 0.5],
           [0.5, 0.9, 0.9, 0.9, 0.5],
           [0.5, 0.9, 1.0, 0.9, 0.5],
           [0.5, 0.9, 0.9, 0.9, 0.5],
           [0.5, 0.5, 0.5, 0.5, 0.5]]
    mat = _grid(data, index_vals=[1, 2, 3, 4, 5], col_vals=[1, 2, 3, 4, 5])
    out = wf.plateau_metric(mat)
    assert out["is_plateau"] is True
    assert out["peak_params"] == (3, 3)
    assert out["nbhd_mean_to_peak"] >= config.PLATEAU_MIN_FRACTION


def test_plateau_rejects_isolated_spike():
    # A single high value surrounded by near-zero/negative neighbours -> plateau FAIL (spike).
    data = [[-0.1, -0.1, -0.1],
           [-0.1, 2.0, -0.1],
           [-0.1, -0.1, -0.1]]
    mat = _grid(data, index_vals=[1, 2, 3], col_vals=[1, 2, 3])
    out = wf.plateau_metric(mat)
    assert out["is_plateau"] is False


def test_plateau_peak_params_are_native_python_types():
    """Regression guard: peak_params must not leak numpy scalars (they corrupted figure titles —
    see docs/AUDIT.md). int/float grid keys must come back as plain int/float."""
    mat = pd.DataFrame([[0.5, 0.9], [0.6, 1.0]],
                       index=np.array([10, 20], dtype=np.int64),
                       columns=np.array([1, 2], dtype=np.int64))
    out = wf.plateau_metric(mat)
    p1, p2 = out["peak_params"]
    assert type(p1) is int and type(p2) is int
    assert "np.int64" not in repr(out["peak_params"])


def test_plateau_neighbourhood_ratio_is_bounded():
    """The peak is the matrix-wide max, so the neighbourhood mean (which includes the peak cell)
    can never exceed it: nbhd_mean_to_peak <= 1.0 always, for any matrix."""
    rng = np.random.default_rng(3)
    mat = _grid(rng.uniform(-1, 1, (6, 6)), index_vals=range(6), col_vals=range(6))
    out = wf.plateau_metric(mat)
    assert out["nbhd_mean_to_peak"] <= 1.0 + 1e-9
