"""Hash manifest of the raw data cache (``data_cache/MANIFEST.json``).

Kraken's public OHLC endpoint serves only its latest ~720 daily candles, so a pull made on another
day returns different Kraken coverage and a different MFI proxy from mid-2024 on. The manifest pins
what was pulled: for every raw cache file, its sha256, row count, first/last index timestamp and the
UTC time it was pulled.

* The pull functions (``data_spot.fetch_venue``, ``data_perp.fetch_perp_klines``,
  ``data_perp.fetch_funding``, all driven by run_00_data.py) call ``record_pull`` for every file they
  download.
* The same functions call ``verify`` before using a cached file. With no manifest there is nothing to
  check (a cache pulled before the manifest existed still loads); once a manifest exists, a raw file
  that is missing from it or whose sha256 differs raises ``SnapshotMismatch``.
* ``python -m src.snapshot [--pulled-at ISO-TIME]`` writes a manifest for a cache pulled before the
  manifest existed; the pull time is recorded as given, or as null (unknown).
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

import config

SCHEMA = "data-manifest/v1"


class SnapshotMismatch(RuntimeError):
    """A cached raw file does not match the data manifest."""


def manifest_path() -> Path:
    return config.DATA_CACHE / "MANIFEST.json"


def raw_files() -> list[Path]:
    """The raw cache files the loaders read, in pull order (existing ones only)."""
    names = [f"spot_{v}.parquet" for v in config.SPOT_VENUES] + ["perp_klines.parquet",
                                                               "perp_funding.parquet"]
    return [config.DATA_CACHE / n for n in names if (config.DATA_CACHE / n).exists()]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def describe(path: Path) -> dict:
    """File name, sha256, row count and first/last index timestamp of one cached parquet."""
    df = pd.read_parquet(path)
    first = df.index.min().isoformat() if len(df) else None
    last = df.index.max().isoformat() if len(df) else None
    return {"file": path.name, "sha256": sha256_file(path), "rows": len(df),
            "first_ts": first, "last_ts": last}


def load_manifest() -> dict | None:
    p = manifest_path()
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def _write(manifest: dict) -> None:
    manifest["files"] = sorted(manifest["files"], key=lambda e: e["file"])
    manifest_path().write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def record_pull(path: Path, pulled_at_utc: str | None = None) -> dict:
    """Add or replace ``path``'s entry in the manifest, stamped with the pull time (default: now)."""
    manifest = load_manifest() or {"schema": SCHEMA, "files": []}
    entry = describe(path) | {"pulled_at_utc": pulled_at_utc or _now_utc()}
    manifest["files"] = [e for e in manifest["files"] if e["file"] != path.name] + [entry]
    _write(manifest)
    return entry


def verify(path: Path) -> None:
    """Raise ``SnapshotMismatch`` unless ``path`` matches its manifest entry (no manifest: no check)."""
    manifest = load_manifest()
    if manifest is None:
        return
    entry = next((e for e in manifest["files"] if e["file"] == path.name), None)
    if entry is None:
        raise SnapshotMismatch(f"{path.name} is not in {manifest_path()}; re-pull it or re-run "
                               "`python -m src.snapshot` to register the current cache")
    digest = sha256_file(path)
    if digest != entry["sha256"]:
        raise SnapshotMismatch(f"{path.name}: sha256 {digest} != manifest {entry['sha256']} "
                               f"(pulled {entry.get('pulled_at_utc')})")


def write_manifest(pulled_at_utc: str | None = None) -> dict:
    """Manifest of every raw file currently in the cache (pull time as given, else unknown)."""
    manifest = {"schema": SCHEMA,
                "files": [describe(p) | {"pulled_at_utc": pulled_at_utc} for p in raw_files()]}
    _write(manifest)
    return manifest


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pulled-at", default=None,
                    help="UTC time the existing cache was pulled (ISO 8601); omitted = unknown")
    args = ap.parse_args()
    manifest = write_manifest(args.pulled_at)
    print(f"wrote {manifest_path()} ({len(manifest['files'])} files)")


if __name__ == "__main__":
    main()
