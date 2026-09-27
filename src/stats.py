"""Inference & multiple-testing for the verdict: PSR/DSR, BH-FDR, bootstrap CIs, permutation null.

Provenance
----------
Vendored (copied, adapted and re-tested here; never cross-imported) from
``multi-asset-tsmom-research@b8404e7c14234e92da2e13cc7886fd37888176c4`` (both upstream files last
changed on 2026-06-26, before the copy was made):

    this module                  upstream path :: function
    sharpe_moments               src/xsmom_stats.py :: _per_period_sharpe_moments
    probabilistic_sharpe_ratio   src/xsmom_stats.py :: probabilistic_sharpe_ratio
    expected_max_sharpe          src/xsmom_stats.py :: expected_max_sharpe
    deflated_sharpe_ratio        src/xsmom_stats.py :: deflated_sharpe_ratio
    benjamini_hochberg           src/xsmom_stats.py :: benjamini_hochberg
    bootstrap_sharpe_ci          src/validation.py :: bootstrap_ci

None of the six is identical to its upstream; the formulas (Bailey & López de Prado 2012, 2014;
Benjamini & Hochberg 1995; percentile bootstrap) are the same. Intentional differences:
  * sharpe_moments: returns NaN moments when n < 2 or sd = 0 (upstream: 0 / 3); skew and kurtosis
    are scaled by the ddof=0 standard deviation (upstream: ddof=1).
  * probabilistic_sharpe_ratio, expected_max_sharpe, deflated_sharpe_ratio: take the moments
    (sr, n, skew, kurt), the trial count and the cross-trial Sharpe variance as arguments instead of
    return series and a list of trial Sharpes (the same signatures as
    ``quant-backtest-framework@ad6df24:mtf_smc/robustness/stats.py``, the "MTF Analysis" source in
    docs/DECISION_LOG.md D0.3; not hashed here). PSR returns NaN when its variance term is <= 0
    (upstream floors it at 1e-12); DSR returns a float (upstream: a dict with sr_star and psr_vs0).
  * benjamini_hochberg: returns numpy arrays (upstream: lists), accepts an empty family, and does not
    echo alpha.
  * bootstrap_sharpe_ci: Sharpe only, annualised with config.PERIODS_PER_YEAR = 365 (upstream: sqrt(12)
    on monthly returns); point estimate computed inline.

Written here (no upstream): _stationary_indices, stationary_block_bootstrap_sharpe,
permutation_null_sharpe.

Conventions: BH-FDR at alpha = 0.05 (the default here; run_05/run_A5 pass config.EDGE_FDR_ALPHA = 0.05).
CIs are percentile intervals at config.CI_LEVEL = 95% from config.BOOTSTRAP_N = 10,000 resamples:
iid (bootstrap_sharpe_ci, used by the tests only) or Politis–Romano circular stationary block bootstrap
with mean block config.STATIONARY_BLOCK_MEAN = 21 days (the Phase-5 OOS Sharpe CI). The permutation null
block-permutes the position series (block 21) against fixed market returns on gross returns (no costs);
p = share of null Sharpes >= observed, without a +1 correction. All resampling is seeded with
config.RANDOM_SEED. Sharpe here is PER-PERIOD (daily) unless a ``periods_per_year`` annualiser is
passed; PSR/DSR operate on the per-period Sharpe.

tests/test_stats_provenance.py pins the sha256 of every function's normalised source and records the
upstream hashes: an edit to any function here must update its pinned hash and, if it changes a
difference listed above, this header.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm

import config

_EULER = 0.5772156649015329


# ----------------------------- Sharpe moments ----------------------------- #
def sharpe_moments(returns: pd.Series) -> tuple[float, int, float, float]:
    """(per-period Sharpe, n, skew, kurtosis[non-excess, normal=3]) for PSR/DSR."""
    r = np.asarray(returns.dropna(), float)
    n = len(r)
    sd = r.std(ddof=1) if n > 1 else 0.0
    if n < 2 or sd == 0:
        return float("nan"), n, float("nan"), float("nan")
    sr = r.mean() / sd
    m = r - r.mean()
    skew = float(np.mean(m ** 3) / (r.std(ddof=0) ** 3))
    kurt = float(np.mean(m ** 4) / (r.std(ddof=0) ** 4))
    return float(sr), n, skew, kurt


# ----------------------------- PSR / DSR ----------------------------- #
def probabilistic_sharpe_ratio(sr: float, n: int, skew: float, kurt: float,
                               sr_benchmark: float = 0.0) -> float:
    """PSR: P(true per-period Sharpe > sr_benchmark) given estimate + higher moments."""
    if not (n and n > 1) or not np.isfinite(sr):
        return float("nan")
    denom = 1.0 - skew * sr + (kurt - 1.0) / 4.0 * sr * sr
    if denom <= 0:
        return float("nan")
    z = (sr - sr_benchmark) * np.sqrt(n - 1) / np.sqrt(denom)
    return float(norm.cdf(z))


def expected_max_sharpe(sr_variance: float, n_trials: int) -> float:
    """Expected max of ``n_trials`` i.i.d. Sharpe estimates under the null (the DSR benchmark)."""
    if sr_variance <= 0 or n_trials < 2:
        return 0.0
    z1 = norm.ppf(1.0 - 1.0 / n_trials)
    z2 = norm.ppf(1.0 - 1.0 / (n_trials * np.e))
    return float(np.sqrt(sr_variance) * ((1 - _EULER) * z1 + _EULER * z2))


def deflated_sharpe_ratio(sr: float, n: int, skew: float, kurt: float,
                          n_trials: int, sr_variance: float) -> float:
    """DSR = PSR against the expected-max-Sharpe benchmark over ``n_trials`` configs.

    DSR > 0.95 ⇒ the selected config is significant AFTER accounting for selection across the
    breadth of the search and the return moments."""
    return probabilistic_sharpe_ratio(sr, n, skew, kurt,
                                      sr_benchmark=expected_max_sharpe(sr_variance, n_trials))


# ----------------------------- multiple testing ----------------------------- #
def benjamini_hochberg(pvalues, alpha: float = 0.05) -> dict:
    """BH-FDR. Returns reject mask (original order), BH q-values, and the critical p."""
    p = np.asarray(list(pvalues), dtype=float)
    m = p.size
    if m == 0:
        return {"reject": np.array([], bool), "qvalues": np.array([]), "threshold": 0.0}
    order = np.argsort(p)
    ranked = p[order]
    thresh_line = (np.arange(1, m + 1) / m) * alpha
    below = ranked <= thresh_line
    threshold = float(ranked[np.max(np.where(below)[0])]) if below.any() else -np.inf
    reject = p <= threshold
    q_ranked = np.minimum.accumulate((ranked * m / np.arange(1, m + 1))[::-1])[::-1]
    qvalues = np.empty(m)
    qvalues[order] = np.clip(q_ranked, 0, 1)
    return {"reject": reject, "qvalues": qvalues, "threshold": threshold}


# ----------------------------- IID bootstrap ----------------------------- #
def bootstrap_sharpe_ci(returns: pd.Series, n_boot: int = config.BOOTSTRAP_N,
                        ci: float = config.CI_LEVEL, seed: int = config.RANDOM_SEED,
                        periods_per_year: int = config.PERIODS_PER_YEAR) -> dict:
    """IID bootstrap CI for the annualised Sharpe + fraction of resamples > 0."""
    r = np.asarray(returns.dropna(), float)
    m = len(r)
    if m < 3:
        return {"point": float("nan"), "lo": float("nan"), "hi": float("nan"), "frac_gt_0": float("nan")}
    rng = np.random.default_rng(seed)
    s = r[rng.integers(0, m, size=(n_boot, m))]
    mean = s.mean(axis=1)
    sd = s.std(axis=1, ddof=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        dist = np.where(sd > 0, mean / sd * np.sqrt(periods_per_year), np.nan)
    dist = dist[np.isfinite(dist)]
    lo, hi = np.percentile(dist, [(100 - ci) / 2, 100 - (100 - ci) / 2])
    point = r.mean() / r.std(ddof=1) * np.sqrt(periods_per_year)
    return {"point": float(point), "lo": float(lo), "hi": float(hi), "frac_gt_0": float((dist > 0).mean())}


# ----------------------------- NEW: stationary block bootstrap ----------------------------- #
def _stationary_indices(n: int, mean_block: int, rng: np.random.Generator) -> np.ndarray:
    """Politis–Romano circular stationary-bootstrap indices (geometric block lengths)."""
    p = 1.0 / max(1, mean_block)
    newblock = rng.random(n) < p
    newblock[0] = True
    starts = rng.integers(0, n, size=n)
    last_nb = np.maximum.accumulate(np.where(newblock, np.arange(n), -1))
    offset = np.arange(n) - last_nb
    return (starts[last_nb] + offset) % n


def stationary_block_bootstrap_sharpe(returns: pd.Series,
                                      mean_block: int = config.STATIONARY_BLOCK_MEAN,
                                      n_boot: int = config.BOOTSTRAP_N,
                                      ci: float = config.CI_LEVEL, seed: int = config.RANDOM_SEED,
                                      periods_per_year: int = config.PERIODS_PER_YEAR) -> dict:
    """Politis–Romano stationary block bootstrap CI for the annualised Sharpe.

    Blocks of geometric(1/mean_block) length preserve the daily-return autocorrelation the factor
    induces, so the CI is not artificially tight. ``mean_block`` is chosen a-priori from the
    IC-decay horizon, NOT tuned to the result."""
    r = np.asarray(returns.dropna(), float)
    n = len(r)
    if n < 5:
        return {"point": float("nan"), "lo": float("nan"), "hi": float("nan"),
                "frac_gt_0": float("nan"), "mean_block": mean_block}
    rng = np.random.default_rng(seed)
    dist = np.empty(n_boot)
    for b in range(n_boot):
        rb = r[_stationary_indices(n, mean_block, rng)]
        sd = rb.std(ddof=1)
        dist[b] = rb.mean() / sd * np.sqrt(periods_per_year) if sd > 0 else np.nan
    dist = dist[np.isfinite(dist)]
    lo, hi = np.percentile(dist, [(100 - ci) / 2, 100 - (100 - ci) / 2])
    point = r.mean() / r.std(ddof=1) * np.sqrt(periods_per_year)
    return {"point": float(point), "lo": float(lo), "hi": float(hi),
            "frac_gt_0": float((dist > 0).mean()), "mean_block": mean_block}


# ----------------------------- NEW: permutation null ----------------------------- #
def permutation_null_sharpe(positions: pd.Series, market_ret: pd.Series,
                            n_perm: int = config.PERMUTATION_N, block: int | None = None,
                            seed: int = config.RANDOM_SEED,
                            periods_per_year: int = config.PERIODS_PER_YEAR) -> dict:
    """Block-permutation null: does the strategy Sharpe beat the luck distribution?

    Keeps market returns fixed and block-permutes the POSITION series (contiguous blocks of length
    ``block``, default = ``mean_block``), destroying the factor→return timing while preserving the
    position's holding structure. p = fraction of null Sharpes ≥ observed (one-sided)."""
    block = block or config.STATIONARY_BLOCK_MEAN
    df = pd.concat([positions.rename("pos"), market_ret.rename("mkt")], axis=1).dropna()
    pos, mkt = df["pos"].to_numpy(), df["mkt"].to_numpy()
    n = len(pos)
    if n < 5:
        return {"observed": float("nan"), "p_value": float("nan"), "null_mean": float("nan"), "n": n}

    def _sharpe(x: np.ndarray) -> float:
        sd = x.std(ddof=1)
        return x.mean() / sd * np.sqrt(periods_per_year) if sd > 0 else np.nan

    observed = _sharpe(pos * mkt)
    n_blocks = int(np.ceil(n / block))
    bounds = [(i * block, min((i + 1) * block, n)) for i in range(n_blocks)]
    rng = np.random.default_rng(seed)
    null = np.empty(n_perm)
    for k in range(n_perm):
        order = rng.permutation(n_blocks)
        perm = np.concatenate([pos[bounds[i][0]:bounds[i][1]] for i in order])[:n]
        null[k] = _sharpe(perm * mkt)
    null = null[np.isfinite(null)]
    p = float((null >= observed).mean()) if np.isfinite(observed) else float("nan")
    return {"observed": float(observed), "p_value": p, "null_mean": float(null.mean()),
            "null_p95": float(np.percentile(null, 95)), "n": n}
