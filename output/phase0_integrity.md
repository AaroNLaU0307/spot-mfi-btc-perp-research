# Phase 0 — Data integrity report

**Factor is a SELF-COMPUTED cross-exchange spot MFI proxy, NOT Glassnode's `spot_money_flow_index`.** Reconstruction differences (venue set, USDT-vs-USD, volume quality) are a documented caveat; re-run on the genuine series when a key is available.

- Analysis window: **2020-05-11 → 2025-12-31**  (warm-up from 2019-06-01 feeds trailing windows)
- Panel rows: **2061**   ·   calendar days expected: 2061   ·   missing days: **0**
- MFI period: 14   ·   factor lag: ≥1 bar   ·   execution: next_open

## Raw source coverage

Rows pulled per source (incl. warm-up):

- spot `binance`: 2406 rows  (2019-06-01..2025-12-31)
- spot `coinbase`: 2406 rows  (2019-06-01..2025-12-31)
- spot `kraken`: 540 rows  (2024-07-10..2025-12-31)
- spot `bitstamp`: 2406 rows  (2019-06-01..2025-12-31)
- spot `okx`: 2406 rows  (2019-06-01..2025-12-31)
- perp klines: 2307 rows  (2019-09-08..2025-12-31)
- funding 8h: 6914 rows  (2019-09-10 08:00:00..2025-12-31 16:00:00.001000)

Per-venue / per-year coverage (analysis window):

```
venue  binance  bitstamp  coinbase  kraken  okx
year                                           
2020       1.0       1.0       1.0   0.000  1.0
2021       1.0       1.0       1.0   0.000  1.0
2022       1.0       1.0       1.0   0.000  1.0
2023       1.0       1.0       1.0   0.000  1.0
2024       1.0       1.0       1.0   0.478  1.0
2025       1.0       1.0       1.0   1.000  1.0
```

> Kraken's API serves only the most recent ~720 daily candles, so it contributes only from **2024-07-10**. Handled transparently (no fill); disclosed here and in the venue-composition figure.

## Panel integrity

NaN counts per column (analysis window):

```
mfi_xexch      0
mfi_binance    0
n_venues       0
spot_agg_tp    0
perp_open      0
perp_close     0
funding        0
```

✓ No missing calendar days in the analysis window.

Venue-count distribution across panel days:

```
n_venues
4    1521
5     540
```

## Factor sanity

- MFI range: [7.1, 96.1]   mean 51.7   median 51.1
- Time > 80 (overbought): **6.2%**   ·   time < 20 (oversold): **2.8%**
- Cross-exchange vs single-Binance MFI: corr **0.997**, mean |diff| **0.82** MFI points
- Mean daily funding annualized: **12.48%/yr** (>0 ⇒ longs pay)

## Figures

- `figures/phase0_mfi_vs_price.png` — MFI vs perp price (80/20 bands)
- `figures/phase0_proxy_vs_binance.png` — cross-exchange vs single-Binance MFI + difference
- `figures/phase0_n_venues.png` — venue composition over time
