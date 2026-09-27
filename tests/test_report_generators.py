"""Report generators, run end to end on a small synthetic data cache (no network, no real data).

Pins the labels the generated phase reports carry: the Phase-4 grid (and so the DSR/PSR, BH-FDR and
cost sweep built on it) is scored over the full sample, which contains the walk-forward OOS span, so
it must never be labelled "in-sample". Also pins the program-level configuration count and that the
Phase-6 scripts re-render the report gate tables.

Run: .venv\\Scripts\\python -m pytest tests/test_report_generators.py -q
"""
import importlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import config
from src import gates

N_DAYS = 400


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    """Point config's data/output/figure paths at a temp tree holding a synthetic cache."""
    cache, out = tmp_path / "data_cache", tmp_path / "output"
    fig = out / "figures"
    fig.mkdir(parents=True)
    cache.mkdir()
    monkeypatch.setattr(config, "DATA_CACHE", cache)
    monkeypatch.setattr(config, "OUTPUT_DIR", out)
    monkeypatch.setattr(config, "FIG_DIR", fig)

    rng = np.random.default_rng(0)
    idx = pd.date_range("2021-01-01", periods=N_DAYS, freq="D")
    price = 100 * np.exp(np.cumsum(rng.normal(0.001, 0.02, N_DAYS)))
    panel = pd.DataFrame({"perp_open": price, "perp_close": price,
                          "mfi_xexch": np.clip(50 + 20 * np.sin(np.arange(N_DAYS) / 15)
                                               + rng.normal(0, 5, N_DAYS), 1, 99),
                          "funding": rng.normal(0.0003, 0.0002, N_DAYS)}, index=idx)
    panel.to_parquet(cache / "panel.parquet")

    def grid(thresholds, windows):
        rows = [{"threshold": t, "window": w, "sharpe": rng.normal(0.8, 0.2),
                 "sr_pp": rng.normal(0.04, 0.01), "n_days": N_DAYS - 1,
                 "skew": 0.0, "kurt": 3.0} for t in thresholds for w in windows]
        return pd.DataFrame(rows)

    grid(config.GRID_LEVEL_THRESHOLDS, (1, 2, 3, 5, 7, 10)).to_parquet(cache / "grid_M1.parquet")
    grid(config.GRID_EDGE_THRESHOLDS, config.GRID_EDGE_WINDOWS).to_parquet(cache / "grid_A.parquet")
    oos_idx = idx[100:]
    pos = pd.Series((np.arange(len(oos_idx)) // 20) % 2, index=oos_idx, dtype=float)
    mkt = pd.Series(rng.normal(0.001, 0.02, len(oos_idx)), index=oos_idx)
    oos = pd.DataFrame({"net": pos * mkt - 0.0001, "pos": pos, "market": mkt})
    for name in ("oos_M1.parquet", "oos_A.parquet"):
        oos.to_parquet(cache / name)
    return out


def _run(script: str) -> None:
    importlib.import_module(script).main()


@pytest.mark.parametrize("script, report", [("run_05_validate", "phase5_validation.md"),
                                            ("run_A5_validate", "variantA_phase5.md")])
def test_phase5_reports_label_grid_statistics_full_sample(sandbox, script, report):
    _run(script)
    text = (sandbox / report).read_text(encoding="utf-8")
    assert "Full-sample selection significance" in text
    assert "Best full-sample config" in text
    assert "In-sample selection" not in text and "IS config" not in text
    assert "gross returns" in text                      # the permutation null runs on gross returns


@pytest.mark.parametrize("script, study", [("run_06_costs", "base"), ("run_A6_costs", "variantA")])
def test_phase6_reports_label_full_sample_and_rerender_the_gate_table(sandbox, script, study):
    spec = gates.STUDIES[study]
    for name in (spec["phase4"], spec["phase5"], spec["report"]):   # phases 4-5 as committed
        (sandbox / name).write_text((ROOT / "output" / name).read_text(encoding="utf-8"), encoding="utf-8")
    report_path = sandbox / spec["report"]
    text = report_path.read_text(encoding="utf-8")
    start, end = text.index(gates.MARKER_START) + len(gates.MARKER_START), text.index(gates.MARKER_END)
    report_path.write_text(text[:start] + "\nstale\n" + text[end:], encoding="utf-8")

    _run(script)
    phase6 = (sandbox / spec["phase6"]).read_text(encoding="utf-8")
    assert "Best full-sample config" in phase6 and "in-sample config" not in phase6
    rendered = report_path.read_text(encoding="utf-8")
    assert "\nstale\n" not in rendered
    assert gates.gate_table_for(study, sandbox) in rendered


@pytest.mark.parametrize("script, study", [("run_04_optimize", "base"), ("run_A4_optimize", "variantA")])
def test_phase4_reports_both_benchmarks_and_score_the_registered_one(sandbox, script, study):
    _run(script)
    text = (sandbox / gates.STUDIES[study]["phase4"]).read_text(encoding="utf-8")
    assert "BH spot" not in text
    registered = gates.BENCHMARK_LABELS[gates.STUDIES[study]["benchmark"]]
    assert f"Beats the registered benchmark ({registered})?" in text
    m = gates._PATTERNS["benchmark"].search(text)            # the gate parser reads the new format
    assert m is not None and m.group(1) != m.group(2)
    if study == "base":
        assert "not put through the Phase-5 tests" in text   # M2 is sensitivity only


def test_multiplicity_note_counts_every_evaluated_grid():
    """42 base M1 + 49 base M2 + 36 Variant A configs were all evaluated and walk-forwarded."""
    b2 = importlib.import_module("run_B2_pbo")
    from src import signals
    sizes = {m: len(g1) * len(g2) for m, spec in signals.MODELS.items() for g1, g2 in [spec["grid"]]}
    assert sizes == {"M1_level": 42, "M2_zscore": 49, "M1_edge": 36}
    assert "42 (base M1) + 49 (base M2 robustness) + 36 (Variant A)" in b2.MULTIPLICITY_NOTE
    assert "**127 grid configurations tested in total**" in b2.MULTIPLICITY_NOTE
    assert "78" not in b2.MULTIPLICITY_NOTE
