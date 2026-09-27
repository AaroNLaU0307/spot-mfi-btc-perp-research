"""results/headline.json — schema, and every stat traced to the committed report it cites.

Every stat here is markdown-backed (the data cache is not published, so nothing is recomputed): the
cited line of the artifact must contain the published number(s) that the display rounds, and a
numeric ``value`` must be one of the published numbers on that line.

Run: .venv\\Scripts\\python -m pytest tests/test_headline.py -q
"""
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HEADLINE = json.loads((ROOT / "results" / "headline.json").read_text(encoding="utf-8"))
STATS = [(row["id"], stat) for row in HEADLINE["rows"] for stat in row["stats"]]
_NUM = re.compile(r"-?\d+(?:\.\d+)?")


def _decimals(token: str) -> int:
    return len(token.split(".")[1]) if "." in token else 0


def test_schema_keys():
    assert set(HEADLINE) == {"schema", "repo", "source_commit", "as_of", "rows"}
    assert HEADLINE["schema"] == "headline/v1"
    assert HEADLINE["repo"] == "AaroNLaU0307/spot-mfi-btc-perp-research"
    assert HEADLINE["as_of"] == "2026-09-27"
    assert re.fullmatch(r"[0-9a-f]{40}|PENDING", HEADLINE["source_commit"])
    for row in HEADLINE["rows"]:
        assert set(row) == {"id", "section", "hypothesis", "verdict", "verdict_detail", "mechanism",
                            "stats", "caveats"}
        assert row["section"] in {"archive", "other"}
        assert all(isinstance(c, str) and c for c in row["caveats"])
        for stat in row["stats"]:
            assert set(stat) == {"label", "display", "value", "artifact", "locator", "provenance"}
            assert stat["provenance"] in {"reproduced", "repo-reported, not reproduced",
                                          "predates fix; pending re-run"}
            assert stat["value"] is None or isinstance(stat["value"], (int, float))


@pytest.mark.parametrize("row_id, stat", STATS, ids=[f"{r}:{s['label']}" for r, s in STATS])
def test_stat_is_published_in_its_artifact(row_id, stat):
    path = ROOT / stat["artifact"]
    assert path.is_file(), stat["artifact"]
    lines = path.read_text(encoding="utf-8").splitlines()
    m = re.match(r"line (\d+)", stat["locator"])
    assert m, "locator must start with 'line N'"
    cited = lines[int(m.group(1)) - 1]
    published = _NUM.findall(cited)

    display = stat["display"].replace("−", "-")
    shown = _NUM.findall(display)
    assert shown, "display must contain a number"
    if display not in cited:            # rounded display: consecutive published numbers round to it
        assert any(
            all(round(float(published[k + i]), _decimals(tok)) == float(tok) for i, tok in enumerate(shown))
            for k in range(len(published) - len(shown) + 1)
        ), f"{stat['display']!r} is not a rounding of the numbers on {stat['artifact']}:{m.group(1)}"
    if stat["value"] is not None:
        assert stat["value"] in [float(p) for p in published]
        assert round(stat["value"], _decimals(shown[0])) == float(shown[0])


def test_verdicts_match_the_reports():
    rows = {row["id"]: row for row in HEADLINE["rows"]}
    base = (ROOT / "output" / "REPORT.md").read_text(encoding="utf-8")
    variant = (ROOT / "output" / "REPORT_variantA.md").read_text(encoding="utf-8")
    assert rows["spot-mfi"]["verdict"] == "FALSIFIED" and "## 7. Verdict — `FALSIFIED`" in base
    assert rows["variant-a"]["verdict"] == "INCONCLUSIVE, leaning FALSIFIED"
    assert "## 6. Verdict — `INCONCLUSIVE`, leaning `FALSIFIED`" in variant
