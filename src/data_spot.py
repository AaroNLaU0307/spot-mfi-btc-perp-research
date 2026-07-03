"""Cross-exchange SPOT BTC daily OHLCV ingestion (ccxt) for the self-computed MFI proxy.

Pulls daily OHLCV from each venue in ``config.SPOT_VENUES`` over [WARMUP_START, END_DATE],
caches one parquet per venue, and reports per-venue/per-year coverage.

Disclosure: the resulting MFI is a SELF-COMPUTED cross-exchange proxy, NOT Glassnode's
``spot_money_flow_index``. See CLAUDE.md / README.md.

Data notes (verified by smoke probe, ccxt 4.5.x):
  * ccxt OHLCV row = ``[ts_ms, open, high, low, close, base_volume]`` (volume in BTC).
  * Daily bars are timestamped at 00:00 UTC start-of-period (Glassnode-compatible).
  * Kraken's OHLC endpoint ignores deep ``since`` and returns only the most recent ~720
    candles, so Kraken coverage starts ~2024-07. Handled transparently (no fill); the
    coverage table discloses which venues contribute in each period.
"""
from __future__ import annotations

import time

import ccxt
import pandas as pd

import config

MS_DAY = 86_400_000
_OHLCV_COLS = ["open", "high", "low", "close", "volume"]


def _client(ex_id: str) -> ccxt.Exchange:
    return getattr(ccxt, ex_id)({"enableRateLimit": config.CCXT_RATE_LIMIT})


def _paginate(ex: ccxt.Exchange, symbol: str, since_ms: int, end_ms: int) -> list[list]:
    """Walk daily candles forward from ``since_ms`` until ``end_ms``.

    Robust to venues that cap candles-per-call (we advance by the last timestamp) and to
    venues that ignore deep ``since`` and only return recent data (the non-progress guard
    stops the loop after one page instead of looping forever).
    """
    out: list[list] = []
    cursor = since_ms
    prev_last: int | None = None
    for _ in range(2000):  # hard guard against infinite loops
        if cursor >= end_ms:
            break
        batch = ex.fetch_ohlcv(symbol, timeframe="1d", since=cursor, limit=1000)
        if not batch:
            break
        out.extend(batch)
        last = batch[-1][0]
        if prev_last is not None and last <= prev_last:
            break  # no forward progress (e.g. Kraken recent-only) -> stop
        prev_last = last
        cursor = last + MS_DAY
    return out


def fetch_venue(ex_id: str, symbol: str, *, force: bool = False) -> pd.DataFrame:
    """Daily OHLCV for one venue over [WARMUP_START, END_DATE]; cached to parquet.

    Returns a frame indexed by naive-UTC day with columns open/high/low/close/volume.
    Empty frame (not an exception) if the venue yields nothing in range.
    """
    cache = config.DATA_CACHE / f"spot_{ex_id}.parquet"
    if cache.exists() and not force:
        return pd.read_parquet(cache)

    since_ms = ccxt.Exchange.parse8601(f"{config.WARMUP_START}T00:00:00Z")
    end_ms = ccxt.Exchange.parse8601(f"{config.END_DATE}T00:00:00Z")
    ex = _client(ex_id)
    ex.load_markets()
    if symbol not in ex.symbols:
        raise ValueError(f"{ex_id}: symbol {symbol} not listed")

    rows = _paginate(ex, symbol, since_ms, end_ms)
    if not rows:
        return pd.DataFrame(columns=_OHLCV_COLS)

    df = pd.DataFrame(rows, columns=["ts", *_OHLCV_COLS])
    df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True).dt.tz_localize(None)
    df = (df.drop_duplicates(subset="ts", keep="last")
            .set_index("ts").sort_index())
    # Inclusive [WARMUP_START, END_DATE]; daily bars at 00:00 UTC.
    df = df.loc[config.WARMUP_START:config.END_DATE]
    df = df[~df.index.duplicated(keep="last")].astype(float)
    config.DATA_CACHE.mkdir(parents=True, exist_ok=True)
    df.to_parquet(cache)
    return df


def load_all_spot(*, force: bool = False, verbose: bool = True) -> dict[str, pd.DataFrame]:
    """Fetch every configured venue. One venue failing is logged, not fatal."""
    frames: dict[str, pd.DataFrame] = {}
    for ex_id, spec in config.SPOT_VENUES.items():
        t0 = time.time()
        try:
            df = fetch_venue(ex_id, spec["symbol"], force=force)
            frames[ex_id] = df
            if verbose:
                if len(df):
                    print(f"  {ex_id:10s} rows={len(df):>5} "
                          f"{df.index.min().date()}..{df.index.max().date()} ({time.time()-t0:.1f}s)")
                else:
                    print(f"  {ex_id:10s} EMPTY ({time.time()-t0:.1f}s)")
        except Exception as e:  # noqa: BLE001 - report and continue
            print(f"  {ex_id:10s} ERROR {repr(e)[:160]}")
    return frames


def coverage_by_year(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Fraction of expected daily bars present per venue per calendar year (analysis window).

    A venue-year below ``config.VENUE_MIN_YEAR_COVERAGE`` is flagged; the MFI aggregation
    simply uses whatever venues are present each day (composition disclosed, never filled).
    """
    years = range(int(config.START_DATE[:4]), int(config.END_DATE[:4]) + 1)
    rows = []
    for ex_id, df in frames.items():
        d = df.loc[config.START_DATE:config.END_DATE] if len(df) else df
        for y in years:
            seg = d.loc[f"{y}-01-01":f"{y}-12-31"] if len(d) else d
            # expected days in the (possibly clipped) analysis window for this year
            lo = max(pd.Timestamp(f"{y}-01-01"), pd.Timestamp(config.START_DATE))
            hi = min(pd.Timestamp(f"{y}-12-31"), pd.Timestamp(config.END_DATE))
            expected = (hi - lo).days + 1 if hi >= lo else 0
            frac = (len(seg) / expected) if expected else float("nan")
            rows.append({"venue": ex_id, "year": y, "bars": len(seg),
                         "expected": expected, "coverage": round(frac, 3) if expected else float("nan"),
                         "med_btc_vol": round(float(seg["volume"].median()), 1) if len(seg) else float("nan")})
    return pd.DataFrame(rows)
