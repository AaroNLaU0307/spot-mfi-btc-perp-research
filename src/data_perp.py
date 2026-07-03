"""Binance USDⓈ-M BTCUSDT perpetual: daily OHLCV + 8h funding (public REST, no key).

This is the TRADED instrument and the return target. Kept strictly separate from the
cross-exchange spot MFI factor so the spot-vs-perp divergence premise is not contaminated
by single-venue overlap.

Endpoints (fapi.binance.com):
  * /fapi/v1/klines      interval=1d  -> [openTime, o, h, l, c, vol, closeTime, quoteVol, ...]
  * /fapi/v1/fundingRate -> [{fundingTime(ms), fundingRate(str), markPrice}], every 8h.
All timestamps UTC; daily bars at 00:00 UTC start-of-period.
"""
from __future__ import annotations

import time

import pandas as pd
import requests

import config

MS_DAY = 86_400_000
_SESSION = requests.Session()
_SESSION.headers.update({"User-Agent": "spot-mfi-research/1.0"})


def _ms(date_str: str) -> int:
    return int(pd.Timestamp(date_str, tz="UTC").timestamp() * 1000)


def _get(path: str, params: dict) -> list | dict:
    """GET with light retry on Binance rate-limit codes; raise with context otherwise."""
    url = config.BINANCE_FAPI_BASE + path
    last = None
    for attempt in range(5):
        r = _SESSION.get(url, params=params, timeout=30)
        if r.status_code == 200:
            return r.json()
        last = r
        if r.status_code in (418, 429):
            time.sleep(1.5 * (attempt + 1))
            continue
        raise RuntimeError(f"{path} HTTP {r.status_code}: {r.text[:160]}")
    raise RuntimeError(f"{path} exhausted retries: HTTP {last.status_code if last else '?'}")


def reachable() -> bool:
    """True if the USDⓈ-M futures host answers (catches geo-block/451 early)."""
    try:
        _get("/fapi/v1/ping", {})
        return True
    except Exception as e:  # noqa: BLE001
        print("perp host NOT reachable:", repr(e)[:160])
        return False


def fetch_perp_klines(*, force: bool = False) -> pd.DataFrame:
    """Daily perp OHLCV over [WARMUP_START, END_DATE]; cached. Naive-UTC day index."""
    cache = config.DATA_CACHE / "perp_klines.parquet"
    if cache.exists() and not force:
        return pd.read_parquet(cache)

    start, end = _ms(config.WARMUP_START), _ms(config.END_DATE) + MS_DAY - 1
    rows: list[list] = []
    cursor = start
    while cursor < end:
        js = _get(config.PERP_KLINES_PATH,
                  {"symbol": config.PERP_SYMBOL, "interval": "1d",
                   "startTime": cursor, "endTime": end, "limit": 1500})
        if not js:
            break
        rows.extend(js)
        last_open = js[-1][0]
        nxt = last_open + MS_DAY
        if nxt <= cursor:
            break
        cursor = nxt
        if len(js) < 1500:
            break

    cols = ["open", "high", "low", "close", "volume", "quote_volume"]
    df = pd.DataFrame([[r[0], r[1], r[2], r[3], r[4], r[5], r[7]] for r in rows],
                      columns=["ts", *cols])
    df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True).dt.tz_localize(None)
    df = (df.drop_duplicates(subset="ts", keep="last").set_index("ts").sort_index()
            .loc[config.WARMUP_START:config.END_DATE].astype(float))
    config.DATA_CACHE.mkdir(parents=True, exist_ok=True)
    df.to_parquet(cache)
    return df


def fetch_funding(*, force: bool = False) -> pd.DataFrame:
    """8h funding-rate history over [WARMUP_START, END_DATE]; cached. Index = funding time (UTC)."""
    cache = config.DATA_CACHE / "perp_funding.parquet"
    if cache.exists() and not force:
        return pd.read_parquet(cache)

    start, end = _ms(config.WARMUP_START), _ms(config.END_DATE) + MS_DAY - 1
    rows: list[dict] = []
    cursor = start
    while cursor < end:
        js = _get(config.PERP_FUNDING_PATH,
                  {"symbol": config.PERP_SYMBOL, "startTime": cursor, "endTime": end, "limit": 1000})
        if not js:
            break
        rows.extend(js)
        last_t = js[-1]["fundingTime"]
        if last_t + 1 <= cursor:
            break
        cursor = last_t + 1
        if len(js) < 1000:
            break

    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=["funding_rate"])
    df["ts"] = pd.to_datetime(df["fundingTime"], unit="ms", utc=True).dt.tz_localize(None)
    df["funding_rate"] = df["fundingRate"].astype(float)
    df = (df.drop_duplicates(subset="ts", keep="last").set_index("ts").sort_index()
            .loc[config.WARMUP_START:config.END_DATE][["funding_rate"]])
    config.DATA_CACHE.mkdir(parents=True, exist_ok=True)
    df.to_parquet(cache)
    return df


def daily_funding(funding_8h: pd.DataFrame) -> pd.Series:
    """Sum the (up to 3) 8h funding rates per UTC day → daily funding rate.

    Sign convention (Binance): rate > 0 ⇒ longs PAY shorts. A long position's daily
    funding COST = +daily_rate; a short's = −daily_rate. Applied in the backtester.
    """
    if funding_8h.empty:
        return pd.Series(dtype=float, name="funding_rate")
    s = funding_8h["funding_rate"].groupby(funding_8h.index.normalize()).sum()
    s.name = "funding_rate"
    return s
