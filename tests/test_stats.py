"""Statistics module — PSR/DSR/BH-FDR properties + new resamplers.

Run: .venv\\Scripts\\python -m pytest tests/test_stats.py -q
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy.stats import norm

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import stats  # noqa: E402


# ----------------------------- PSR / DSR ----------------------------- #
def test_psr_benchmark_equal_gives_half():
    # sr == benchmark -> z = 0 -> cdf = 0.5, regardless of moments
    assert stats.probabilistic_sharpe_ratio(0.15, 200, 0.0, 3.0, sr_benchmark=0.15) == pytest.approx(0.5)
    assert stats.probabilistic_sharpe_ratio(0.0, 200, 0.0, 3.0, sr_benchmark=0.0) == pytest.approx(0.5)


def test_psr_monotone_in_sharpe_and_matches_gaussian_form():
    lo = stats.probabilistic_sharpe_ratio(0.05, 300, 0.0, 3.0)
    hi = stats.probabilistic_sharpe_ratio(0.20, 300, 0.0, 3.0)
    assert 0.5 < lo < hi < 1.0
    sr, n = 0.2, 300
    denom = np.sqrt(1 + 0.5 * sr ** 2)                      # skew=0, kurt=3
    assert hi == pytest.approx(float(norm.cdf(sr * np.sqrt(n - 1) / denom)), rel=1e-9)


def test_expected_max_sharpe_grows_with_trials_and_variance():
    assert stats.expected_max_sharpe(0.0, 100) == 0.0
    assert stats.expected_max_sharpe(0.01, 2) < stats.expected_max_sharpe(0.01, 100)
    assert stats.expected_max_sharpe(0.005, 50) < stats.expected_max_sharpe(0.02, 50)


def test_dsr_below_psr_when_many_trials():
    sr, n = 0.15, 500
    psr0 = stats.probabilistic_sharpe_ratio(sr, n, 0.0, 3.0, 0.0)
    dsr = stats.deflated_sharpe_ratio(sr, n, 0.0, 3.0, n_trials=42, sr_variance=0.02)
    assert dsr < psr0                                       # deflation raises the bar


# ----------------------------- BH-FDR ----------------------------- #
def test_bh_rejects_only_small_p():
    out = stats.benjamini_hochberg([0.001, 0.5, 0.6, 0.7, 0.8], alpha=0.05)
    assert out["reject"].tolist() == [True, False, False, False, False]


def test_bh_all_reject_on_boundary():
    out = stats.benjamini_hochberg([0.01, 0.02, 0.03, 0.04, 0.05], alpha=0.05)
    assert out["reject"].all()
    assert (out["qvalues"] <= 0.05 + 1e-12).all()


# ----------------------------- bootstraps ----------------------------- #
def test_iid_bootstrap_ci_brackets_point_and_is_deterministic():
    rng = np.random.default_rng(0)
    r = pd.Series(rng.normal(0.001, 0.02, 1000))
    a = stats.bootstrap_sharpe_ci(r, n_boot=2000, seed=7)
    b = stats.bootstrap_sharpe_ci(r, n_boot=2000, seed=7)
    assert a == b                                           # deterministic
    assert a["lo"] < a["point"] < a["hi"]
    assert 0.0 <= a["frac_gt_0"] <= 1.0


def test_stationary_indices_valid_and_deterministic():
    rng1 = np.random.default_rng(3)
    rng2 = np.random.default_rng(3)
    i1 = stats._stationary_indices(500, 10, rng1)
    i2 = stats._stationary_indices(500, 10, rng2)
    assert np.array_equal(i1, i2)
    assert i1.min() >= 0 and i1.max() < 500 and len(i1) == 500


def test_stationary_block_bootstrap_runs():
    rng = np.random.default_rng(1)
    r = pd.Series(rng.normal(0.0008, 0.02, 800))
    out = stats.stationary_block_bootstrap_sharpe(r, mean_block=10, n_boot=1500, seed=7)
    assert np.isfinite(out["lo"]) and np.isfinite(out["hi"]) and out["lo"] < out["hi"]
    assert out["lo"] < out["point"] < out["hi"]


# ----------------------------- permutation null ----------------------------- #
def test_permutation_null_detects_real_timing():
    # positions perfectly long exactly when the market rises -> strong, non-random skill
    rng = np.random.default_rng(5)
    mkt = pd.Series(rng.normal(0.0, 0.02, 600))
    pos = (mkt > 0).astype(float)                           # look-ahead ON PURPOSE (test only)
    out = stats.permutation_null_sharpe(pos, mkt, n_perm=500, block=10, seed=7)
    assert out["p_value"] < 0.05
    assert out["observed"] > out["null_p95"]


def test_permutation_null_constant_signal_not_significant():
    rng = np.random.default_rng(6)
    mkt = pd.Series(rng.normal(0.0005, 0.02, 600))
    pos = pd.Series(np.ones(600), index=mkt.index)          # constant -> permutation-invariant
    out = stats.permutation_null_sharpe(pos, mkt, n_perm=300, block=10, seed=7)
    assert out["p_value"] == pytest.approx(1.0)             # every permutation equals observed
