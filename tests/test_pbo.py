"""PBO / CSCV — structural correctness + the two mandatory synthetic sanity checks.

Per docs/AUDIT.md Phase B2: this is the only genuinely new algorithm added in the audit, so it ships
with unit tests AND two synthetic sanity checks that MUST pass before any real PBO number is reported:
  (a) a pure-noise return matrix -> PBO approx 0.5
  (b) a matrix with one planted dominant strategy -> PBO near 0

Run: .venv\\Scripts\\python -m pytest tests/test_pbo.py -q
"""
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from src import pbo  # noqa: E402


# ----------------------------- structural correctness ----------------------------- #
def test_blocks_partition_covers_every_row_exactly_once():
    blocks = pbo._blocks(103, 8)
    assert len(blocks) == 8
    all_rows = np.concatenate(blocks)
    assert sorted(all_rows.tolist()) == list(range(103))


def test_n_splits_total_matches_binomial_coefficient():
    rng = np.random.default_rng(0)
    mat = pd.DataFrame(rng.normal(0, 0.01, (400, 6)))
    for S in (4, 6, 8):
        out = pbo.cscv_pbo(mat, S=S, embargo=0, min_rows=5)
        assert out["n_splits_total"] == math.comb(S, S // 2)


def test_odd_S_rejected():
    mat = pd.DataFrame(np.zeros((100, 4)))
    with pytest.raises(ValueError):
        pbo.cscv_pbo(mat, S=7)


def test_purge_shrinks_train_rows_at_test_boundaries():
    blocks = pbo._blocks(160, 8)             # 8 blocks of 20 rows each
    # blocks 0,1,2,3 = train; 4,5,6,7 = test -> ONE boundary, between block 3 (train) and block 4 (test)
    rows_purged = pbo._purged_train_rows(blocks, {0, 1, 2, 3}, {4, 5, 6, 7}, embargo=5)
    rows_unpurged = pbo._purged_train_rows(blocks, {0, 1, 2, 3}, {4, 5, 6, 7}, embargo=0)
    assert len(rows_purged) == len(rows_unpurged) - 5     # only block 3's tail (adjacent to block 4) is cut
    assert set(rows_purged) < set(rows_unpurged)


def test_purge_cuts_both_sides_of_a_sandwiched_train_block():
    blocks = pbo._blocks(160, 8)
    # block 3 is TRAIN, sandwiched between test blocks 2 and 4 -> both sides purged.
    rows = pbo._purged_train_rows(blocks, {3}, {2, 4}, embargo=5)
    assert len(rows) == len(blocks[3]) - 10                # 20 - 5 - 5


def test_cpcv_distribution_matches_pbo_result_oos_sharpes():
    rng = np.random.default_rng(1)
    mat = pd.DataFrame(rng.normal(0.0003, 0.01, (600, 10)))
    out = pbo.cscv_pbo(mat, S=8, embargo=0)
    dist = pbo.cpcv_oos_distribution(out)
    assert dist["n"] == len(out["oos_sharpe"])
    assert dist["min"] <= dist["median"] <= dist["max"]
    assert dist["q25"] <= dist["median"] <= dist["q75"]


def test_percentile_of_is_bounded_and_monotone():
    dist = np.array([0.1, 0.2, 0.3, 0.4, 0.5])
    assert pbo.percentile_of(0.05, dist) == 0.0
    assert pbo.percentile_of(0.5, dist) == 100.0
    assert pbo.percentile_of(0.3, dist) == 60.0             # 3 of 5 values <= 0.3


# ----------------------------- MANDATORY sanity checks ----------------------------- #
# Run at S=8 (70 splits/call, ~180x fewer than the production S=16's 12870) so `pytest -q` stays
# fast for a stranger cloning the repo (Phase C). The PBO~0.5-for-noise / PBO~0-for-dominant
# properties being validated are properties of the CSCV algorithm itself, not specific to S=16 —
# confirmed to also hold at S=16 during development (see docs/AUDIT.md); S=16 remains the number
# actually reported for both studies in run_B2_pbo.py.
_SANITY_S = 8


def test_sanity_pure_noise_pbo_near_half():
    """(a) No config has true skill (iid noise, no cross-config or serial structure) -> the
    IS-winner's OOS rank should be uniform, so PBO averaged over independent data draws must sit
    near 0.5. A single draw has real sampling variance (few configs, correlated splits from one
    matrix), so we average over multiple independent draws rather than asserting on one."""
    pbos = []
    for seed in range(30):
        rng = np.random.default_rng(seed)
        mat = pd.DataFrame(rng.normal(0, 0.02, (1500, 20)))
        pbos.append(pbo.cscv_pbo(mat, S=_SANITY_S, embargo=config.EMBARGO_BARS)["pbo"])
    mean_pbo = float(np.mean(pbos))
    assert 0.35 <= mean_pbo <= 0.65, f"mean PBO over {len(pbos)} pure-noise draws = {mean_pbo:.3f}"


def test_sanity_dominant_strategy_pbo_near_zero():
    """(b) One config with a genuinely, substantially higher true mean (same vol) among noise
    configs -> CSCV should reliably pick it in-sample AND rank it near the top out-of-sample,
    every split -> PBO near 0."""
    rng = np.random.default_rng(42)
    T, N = 1500, 20
    mat = pd.DataFrame(rng.normal(0, 0.02, (T, N)), columns=[f"c{i}" for i in range(N)])
    mat["dom"] = rng.normal(0.0025, 0.02, T)          # ~9x the noise configs' implied Sharpe
    out = pbo.cscv_pbo(mat, S=_SANITY_S, embargo=14)
    assert out["pbo"] < 0.10, f"PBO for a planted dominant strategy = {out['pbo']:.3f} (expected < 0.10)"
    assert (np.array(out["selected_config"]) == "dom").mean() > 0.9   # picked as IS-best almost always
