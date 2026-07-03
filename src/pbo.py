"""Post-hoc supplementary validation — PBO via CSCV, and the CPCV OOS-Sharpe distribution.

Bailey, Borwein, López de Prado & Zhu (2017), "The Probability of Backtest Overfitting" (CSCV method).
This closes the ONE test the original brief deferred as "optional, gold standard" (§7 of the base
brief). It is strictly a POST-HOC, ADDITIONAL diagnostic appended after both studies' verdicts were
already decided by their pre-registered gates — nothing here revises a verdict (see report sections
"Post-hoc supplementary validation (added after verdict)").

Method (CSCV)
-------------
1. Partition the T daily rows of the per-config net-return matrix into S contiguous, (nearly) equal
   blocks, in chronological order.
2. Enumerate every way to choose S/2 of the S blocks as the TRAIN set (the complementary S/2 blocks
   are TEST) — C(S, S/2) combinatorial splits.
3. Purge: wherever a TRAIN block is chronologically adjacent to a TEST block, drop ``embargo`` bars
   from the TRAIN block's side of that boundary (never from the TEST side). This generalises this
   repo's walk-forward embargo convention (``src/walkforward.py``: "drop EMBARGO_BARS bars between
   IS-end and OOS-start so the test block's early bars share no MFI-window inputs with the train
   block's late bars") to the many-boundary combinatorial setting.
4. Per split: the IS-best config (by per-period Sharpe on the purged TRAIN rows) is looked up in the
   TEST-set Sharpe ranking of ALL configs; its relative rank ω = rank/(N+1) becomes a logit
   λ = ln(ω/(1-ω)). PBO = fraction of splits with λ < 0 (the IS-winner sits below the OOS median).
5. The OOS Sharpes of the per-split IS-selected config form the CPCV distribution used to contextualise
   the single walk-forward OOS number (one particular chronological path, not "the" answer).

No new researcher degrees of freedom: this module only re-evaluates the FROZEN grid configs already
scored in Phase 4 (reusing their cached daily net-return series); it introduces no new parameters,
models, signals or data.
"""
from __future__ import annotations

import math
from itertools import combinations

import numpy as np
import pandas as pd

import config

_EPS = 1e-6


def _sharpe_per_column(df: pd.DataFrame, periods_per_year: int = config.PERIODS_PER_YEAR) -> pd.Series:
    """Vectorised per-period Sharpe (annualised) for every column at once."""
    mu = df.mean(axis=0)
    sd = df.std(axis=0, ddof=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        sr = mu / sd * np.sqrt(periods_per_year)
    return sr


def _blocks(n_rows: int, S: int) -> list[np.ndarray]:
    """S contiguous, chronological, nearly-equal partitions of row positions [0, n_rows)."""
    return [np.asarray(b) for b in np.array_split(np.arange(n_rows), S)]


def _purged_train_rows(block_list: list[np.ndarray], train_idx: set[int], test_idx: set[int],
                       embargo: int) -> np.ndarray:
    """Row positions for the TRAIN side, with ``embargo`` bars dropped at every TRAIN/TEST boundary
    (dropped from the TRAIN block only, per this module's documented purge convention)."""
    S = len(block_list)
    rows: list[np.ndarray] = []
    for bi in sorted(train_idx):
        r = block_list[bi]
        if embargo > 0:
            if bi - 1 in test_idx:
                r = r[embargo:]
            if bi + 1 < S and (bi + 1) in test_idx:
                r = r[:-embargo] if len(r) > embargo else r[:0]
        if len(r):
            rows.append(r)
    return np.concatenate(rows) if rows else np.array([], dtype=int)


def cscv_pbo(return_matrix: pd.DataFrame, S: int = 16, embargo: int = config.EMBARGO_BARS,
            min_rows: int = 30) -> dict:
    """CSCV PBO on a T x N matrix (index=chronological dates, columns=config keys, values=daily net
    returns). Returns PBO, the logit array, and the per-split (IS Sharpe, OOS Sharpe-of-selected)
    pairs (the IS-vs-OOS degradation scatter and the CPCV OOS-Sharpe distribution)."""
    if S % 2 != 0:
        raise ValueError("S must be even (CSCV splits into S/2 train / S/2 test)")
    T = len(return_matrix)
    block_list = _blocks(T, S)
    all_blocks = set(range(S))

    logits, is_sr, oos_sr, selected = [], [], [], []
    for train_idx_tuple in combinations(range(S), S // 2):
        train_idx = set(train_idx_tuple)
        test_idx = all_blocks - train_idx
        train_rows = _purged_train_rows(block_list, train_idx, test_idx, embargo)
        test_rows = np.concatenate([block_list[bi] for bi in sorted(test_idx)])
        if len(train_rows) < min_rows or len(test_rows) < min_rows:
            continue

        is_perf = _sharpe_per_column(return_matrix.iloc[train_rows])
        if is_perf.notna().sum() == 0:
            continue
        best_cfg = is_perf.idxmax()

        oos_perf = _sharpe_per_column(return_matrix.iloc[test_rows])
        n_valid = int(oos_perf.notna().sum())
        if n_valid == 0 or pd.isna(oos_perf.get(best_cfg, np.nan)):
            continue
        rank_of_best = oos_perf.rank(method="average")[best_cfg]   # 1..n_valid, ties averaged
        omega = float(np.clip(rank_of_best / (n_valid + 1), _EPS, 1 - _EPS))
        logit = float(np.log(omega / (1 - omega)))

        logits.append(logit)
        is_sr.append(float(is_perf[best_cfg]))
        oos_sr.append(float(oos_perf[best_cfg]))
        selected.append(best_cfg)

    logits_arr = np.asarray(logits)
    return {
        "S": S, "embargo": embargo, "n_splits": len(logits_arr),
        "n_splits_total": math.comb(S, S // 2),
        "pbo": float((logits_arr < 0).mean()) if len(logits_arr) else float("nan"),
        "logits": logits_arr,
        "is_sharpe": np.asarray(is_sr), "oos_sharpe": np.asarray(oos_sr),
        "selected_config": selected,
    }


def cpcv_oos_distribution(pbo_result: dict) -> dict:
    """Summary stats of the CPCV OOS-Sharpe-of-selected distribution (median/IQR/min/max), used to
    locate the single walk-forward OOS number as one draw within the full combinatorial spread."""
    oos = pbo_result["oos_sharpe"]
    if len(oos) == 0:
        return {k: float("nan") for k in ("median", "q25", "q75", "min", "max", "n")}
    return {"median": float(np.median(oos)), "q25": float(np.percentile(oos, 25)),
            "q75": float(np.percentile(oos, 75)), "min": float(oos.min()), "max": float(oos.max()),
            "n": int(len(oos))}


def percentile_of(value: float, distribution: np.ndarray) -> float:
    """Percentile rank of ``value`` within ``distribution`` (0-100), for locating the WF OOS number."""
    d = np.asarray(distribution)
    d = d[np.isfinite(d)]
    if len(d) == 0 or not np.isfinite(value):
        return float("nan")
    return float((d <= value).mean() * 100)
