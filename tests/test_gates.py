"""Registered decision rules — gate lists, thresholds from config, and the generated report tables.

Run: .venv\\Scripts\\python -m pytest tests/test_gates.py -q
"""
import dataclasses
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import config
from src import gates


def _registered_rule(prereg: str) -> list[str]:
    """The numbered items of a pre-registration's "Decision rule" section."""
    text = (ROOT / prereg).read_text(encoding="utf-8")
    section = text.split("## Decision rule", 1)[1].split("\n## ", 1)[0]
    items = re.findall(r"^(\d)\. (.+?)(?=^\d\. |^\*\*|\Z)", section, re.MULTILINE | re.DOTALL)
    return [body for _, body in items]


@pytest.mark.parametrize("study", list(gates.STUDIES))
def test_gate_list_follows_the_preregistration(study):
    registered = _registered_rule(gates.STUDIES[study]["prereg"])
    assert len(registered) == len(gates.STUDIES[study]["gates"]) == 7


def test_base_gate_six_is_the_registered_positive_oos_equity_gate():
    registered = _registered_rule(gates.STUDIES["base"]["prereg"])
    assert "OOS equity is positive" in registered[5]
    assert gates.STUDIES["base"]["gates"][5] == "oos_positive"
    # registered gate 5 is ONE gate: bootstrap CI AND permutation
    assert "bootstrap" in registered[4] and "permutation" in registered[4]
    assert gates.STUDIES["base"]["gates"][4] == "bootstrap_permutation"


def test_base_study_published_statistics_pass_three_of_seven():
    results = gates.evaluate_gates("base", gates.parse_published_stats("base"))
    assert [r.number for r in results if r.passed] == [3, 6, 7]


def test_variant_a_published_statistics_pass_five_of_seven():
    results = gates.evaluate_gates("variantA", gates.parse_published_stats("variantA"))
    assert [r.number for r in results if r.passed] == [1, 2, 3, 4, 7]


def test_published_statistics_are_parsed_from_the_committed_reports():
    s = gates.parse_published_stats("base")
    assert (s.oos_sharpe, s.bh_price, s.bh_perp_net, s.dsr, s.fdr_survivors, s.n_configs) == \
        (0.294, 0.457, 0.313, 0.959, 0, 42)
    assert (s.boot_lo, s.boot_hi, s.perm_p, s.plateau_ratio) == (-0.720, 1.212, 0.266, 0.85)
    assert s.oos_ann_return == pytest.approx(0.044) and s.breakeven_bps == float("inf")


def test_thresholds_are_read_from_config(monkeypatch):
    stats = gates.parse_published_stats("base")
    assert not gates.evaluate_gates("base", stats)[0].passed          # 0.294 < 0.5
    monkeypatch.setattr(config, "EDGE_MIN_NET_SHARPE", 0.25)
    assert gates.evaluate_gates("base", stats)[0].passed
    monkeypatch.setattr(config, "EDGE_MAX_PERMUTATION_P", 0.30)       # p = 0.266, CI still spans 0
    assert not gates.evaluate_gates("base", stats)[4].passed
    stats_ci = dataclasses.replace(stats, boot_lo=0.01)
    assert gates.evaluate_gates("base", stats_ci)[4].passed


def test_breakeven_below_modelled_cost_fails():
    stats = dataclasses.replace(gates.parse_published_stats("base"), breakeven_bps=5.0)
    assert gates.modelled_cost_bps() == pytest.approx(7.0)
    assert not gates.evaluate_gates("base", stats)[6].passed


@pytest.mark.parametrize("study", list(gates.STUDIES))
def test_report_gate_table_is_the_generated_one(study):
    """The table in output/REPORT*.md is exactly what src/gates.py renders — no hand-typed copy."""
    report = (config.OUTPUT_DIR / gates.STUDIES[study]["report"]).read_text(encoding="utf-8")
    block = report.split(gates.MARKER_START, 1)[1].split(gates.MARKER_END, 1)[0]
    assert block.strip("\n") == gates.gate_table_for(study)
    assert report.count("| # | Registered gate |") == 1


def test_update_report_rewrites_only_the_marked_block(tmp_path):
    for study in gates.STUDIES:
        spec = gates.STUDIES[study]
        for key in ("phase4", "phase5", "phase6"):
            (tmp_path / spec[key]).write_text((config.OUTPUT_DIR / spec[key]).read_text(encoding="utf-8"),
                                              encoding="utf-8")
        (tmp_path / spec["report"]).write_text(
            f"# head\n\n{gates.MARKER_START}\nstale table\n{gates.MARKER_END}\n\ntail\n", encoding="utf-8")
        table = gates.update_report(study, tmp_path)
        text = (tmp_path / spec["report"]).read_text(encoding="utf-8")
        assert "stale table" not in text and table in text
        assert text.startswith("# head\n") and text.endswith("\ntail\n")


def test_benchmark_line_round_trips_through_the_parser():
    line = gates.benchmark_line("base", 0.294, 0.457, 0.313)
    assert "Beats the registered benchmark (B&H perp net of funding)? **NO**" in line
    m = gates._PATTERNS["benchmark"].search(line)
    assert (float(m.group(1)), float(m.group(2))) == (0.457, 0.313)
    assert "**YES**" in gates.benchmark_line("variantA", 0.684, 0.457, 0.313)


def test_readme_states_the_generated_base_gate_count():
    results = gates.evaluate_gates("base", gates.parse_published_stats("base"))
    n_pass = sum(r.passed for r in results)
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert f"{n_pass} of the {len(results)} registered gates passed" in readme
