"""Data-cache hash manifest — written at pull time, verified on every cached read.

No network: the Binance REST call is replaced by a stub returning hand-made klines.

Run: .venv\\Scripts\\python -m pytest tests/test_snapshot.py -q
"""
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config
from src import data_perp, snapshot

DAY_MS = 86_400_000
T0 = int(pd.Timestamp("2020-01-01", tz="UTC").timestamp() * 1000)


@pytest.fixture
def cache(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_CACHE", tmp_path)
    return tmp_path


def _klines(n=3, close0=100.0):
    return [[T0 + i * DAY_MS, close0, close0 + 2, close0 - 2, close0 + i, 10.0, T0 + (i + 1) * DAY_MS - 1,
             1000.0, 5, 0, 0, 0] for i in range(n)]


def test_pull_records_file_hash_rows_range_and_time(cache, monkeypatch):
    monkeypatch.setattr(data_perp, "_get", lambda path, params: _klines())
    df = data_perp.fetch_perp_klines(force=True)
    manifest = json.loads((cache / "MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["schema"] == "data-manifest/v1"
    (entry,) = manifest["files"]
    raw = (cache / "perp_klines.parquet").read_bytes()
    assert entry["file"] == "perp_klines.parquet"
    assert entry["sha256"] == hashlib.sha256(raw).hexdigest()
    assert entry["rows"] == len(df) == 3
    assert (entry["first_ts"], entry["last_ts"]) == ("2020-01-01T00:00:00", "2020-01-03T00:00:00")
    assert pd.Timestamp(entry["pulled_at_utc"]).tzinfo is not None


def test_cached_read_is_verified_against_the_manifest(cache, monkeypatch):
    monkeypatch.setattr(data_perp, "_get", lambda path, params: _klines())
    first = data_perp.fetch_perp_klines(force=True)
    pd.testing.assert_frame_equal(data_perp.fetch_perp_klines(), first)     # unchanged cache loads

    first.assign(close=first["close"] * 1.01).to_parquet(cache / "perp_klines.parquet")
    with pytest.raises(snapshot.SnapshotMismatch, match="sha256"):
        data_perp.fetch_perp_klines()


def test_cache_without_manifest_still_loads(cache):
    df = pd.DataFrame({"funding_rate": [0.0001, 0.0002]},
                      index=pd.to_datetime(["2020-01-01 00:00", "2020-01-01 08:00"]))
    df.to_parquet(cache / "perp_funding.parquet")
    pd.testing.assert_frame_equal(data_perp.fetch_funding(), df)


def test_file_missing_from_an_existing_manifest_fails_closed(cache, monkeypatch):
    monkeypatch.setattr(data_perp, "_get", lambda path, params: _klines())
    data_perp.fetch_perp_klines(force=True)                                  # manifest now exists
    pd.DataFrame({"funding_rate": [0.0001]},
                 index=pd.to_datetime(["2020-01-01"])).to_parquet(cache / "perp_funding.parquet")
    with pytest.raises(snapshot.SnapshotMismatch, match="not in"):
        data_perp.fetch_funding()


def test_write_manifest_registers_an_existing_cache(cache):
    idx = pd.date_range("2020-01-01", periods=4, freq="D")
    pd.DataFrame({"close": [1.0, 2.0, 3.0, 4.0]}, index=idx).to_parquet(cache / "spot_binance.parquet")
    pd.DataFrame({"close": [1.0]}, index=idx[:1]).to_parquet(cache / "panel.parquet")   # derived: skipped
    manifest = snapshot.write_manifest(pulled_at_utc=None)
    assert [e["file"] for e in manifest["files"]] == ["spot_binance.parquet"]
    assert manifest["files"][0]["pulled_at_utc"] is None and manifest["files"][0]["rows"] == 4
    snapshot.verify(cache / "spot_binance.parquet")
