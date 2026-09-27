"""Pin the source of every statistics helper in src/stats.py, and record its upstream.

Each function's source (``inspect.getsource``, trailing whitespace stripped) is hashed with sha256.
A silent edit fails here; an intended edit updates the pinned hash (and the module's provenance
header if it changes a listed difference).

Upstream hashes are of the same normalised source of the corresponding function in
``multi-asset-tsmom-research@b8404e7c14234e92da2e13cc7886fd37888176c4`` (read with ``git show``).
None of the vendored functions is identical to its upstream; each difference is listed in the
src/stats.py docstring, which this test checks.

Run: .venv\\Scripts\\python -m pytest tests/test_stats_provenance.py -q
"""
import hashlib
import inspect
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import stats

UPSTREAM_SHA = "b8404e7c14234e92da2e13cc7886fd37888176c4"

PINNED = {
    "sharpe_moments": "950f9c87ed06dbd9c086ec54f19a827ce3a525783a3559358b9165f9e1c6c946",
    "probabilistic_sharpe_ratio": "15d8744643a6cdfb8e26c2e48713d827cc057e3201f8be80be0554db9dedba1b",
    "expected_max_sharpe": "668635cd173df3eabdb62a677d619159d9e1a3d3ae1421bb0fb555792b2e1166",
    "deflated_sharpe_ratio": "58bdd65e0fdbdf41e65ff81cac255ba7b4b690e0db5a64b22965ff224b2aaf82",
    "benjamini_hochberg": "61f07ce5254878e6cae7ad41a1d765988a06609ee84ef62eae1a293c2c364fd6",
    "bootstrap_sharpe_ci": "beffe6b7284fa09c31be195184868eaa7a4e29d29ef748c7b86e53c85055cae3",
    "_stationary_indices": "683d262aa75df7bd4194bb87332fe443cda1edae42e78a5a6373f623fd10f934",
    "stationary_block_bootstrap_sharpe": "1deb396c1670786d19a4a4193940a2bad4baacd9e68d4ac4e635ad9c8127efdb",
    "permutation_null_sharpe": "734288f7452593f99b667b37b8db5351476ab3f8674fab9c6d39cacc1e90d60a",
}

# local function -> (upstream path, upstream function, sha256 of its normalised source)
UPSTREAM = {
    "sharpe_moments": ("src/xsmom_stats.py", "_per_period_sharpe_moments",
                       "897f14d8b131a84dd561451bd1bc7eae95ff96c63877c0c895e64c3b94abb40c"),
    "probabilistic_sharpe_ratio": ("src/xsmom_stats.py", "probabilistic_sharpe_ratio",
                                   "f4d5667ad64a1886949e3aae09274eb9fdfb468046dc36d8669b6c39a8bd6d7d"),
    "expected_max_sharpe": ("src/xsmom_stats.py", "expected_max_sharpe",
                            "70366e46becab8a6d1e62f7d6b4f5411e4c8aba41953d4068015abc211a43c43"),
    "deflated_sharpe_ratio": ("src/xsmom_stats.py", "deflated_sharpe_ratio",
                              "382a84b652a70f9223b9aa9977c7a870b866c7a9c7a69564329939dbb008f4be"),
    "benjamini_hochberg": ("src/xsmom_stats.py", "benjamini_hochberg",
                           "f771d541e068aa7d4110f40edd6d33ea733c8e7fc24904ad7434a76e533cc3dd"),
    "bootstrap_sharpe_ci": ("src/validation.py", "bootstrap_ci",
                            "df91388430ef1c20ed4a166112ae9697ce58b2bb68575b848ce5a1e34f26f9b6"),
}


def _normalised_sha256(source: str) -> str:
    lines = [line.rstrip() for line in source.splitlines()]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def _module_functions() -> dict:
    return {name: fn for name, fn in inspect.getmembers(stats, inspect.isfunction)
            if fn.__module__ == stats.__name__}


def test_every_helper_is_pinned():
    assert set(_module_functions()) == set(PINNED)


@pytest.mark.parametrize("name", sorted(PINNED))
def test_helper_source_matches_pinned_hash(name):
    assert _normalised_sha256(inspect.getsource(_module_functions()[name])) == PINNED[name], (
        f"src/stats.py::{name} changed: update PINNED here and, if needed, the provenance header")


@pytest.mark.parametrize("name", sorted(UPSTREAM))
def test_vendored_helper_is_identical_upstream_or_its_difference_is_listed(name):
    path, upstream_fn, upstream_hash = UPSTREAM[name]
    header = stats.__doc__
    assert UPSTREAM_SHA in header and f"{path} :: {upstream_fn}" in header
    if PINNED[name] != upstream_hash:
        differences = header.split("Intentional differences:", 1)[1].split("Written here", 1)[0]
        assert f"{name}" in differences


def test_header_states_bh_level_and_ci_method():
    header = stats.__doc__
    assert "alpha = 0.05" in header
    assert "percentile intervals" in header and "stationary block bootstrap" in header
    assert inspect.signature(stats.benjamini_hochberg).parameters["alpha"].default == 0.05
