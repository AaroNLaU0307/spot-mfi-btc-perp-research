"""Project configuration — single source of truth for the Spot-MFI / BTC-perp study.

Every parameter that drives data, factor, signal, backtest, optimisation and validation
lives here so runs are reproducible and there are no magic numbers buried in modules.
Stdlib-only on import so it loads before third-party deps are installed.

Conventions (mirrors the sibling quant repos):
  * Determinism: all resampling uses RANDOM_SEED.
  * Costs always modelled (fees + slippage + actual funding); gross AND net reported.
  * No look-ahead: factor lagged >= FACTOR_LAG_BARS, signals execute next bar.
  * IS/OOS discipline + pre-registration (research/PREREGISTRATION.md) before optimisation.
  * "We do not tune toward profitability." A clean negative result is a valid outcome.
"""
from __future__ import annotations

from pathlib import Path

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
PROJECT_ROOT = Path(__file__).resolve().parent
DATA_CACHE = PROJECT_ROOT / "data_cache"
OUTPUT_DIR = PROJECT_ROOT / "output"
FIG_DIR = OUTPUT_DIR / "figures"
RESEARCH_DIR = PROJECT_ROOT / "research"
DOCS_DIR = PROJECT_ROOT / "docs"

PREREGISTRATION_MD = RESEARCH_DIR / "PREREGISTRATION.md"
DECISION_LOG_MD = DOCS_DIR / "DECISION_LOG.md"

# --------------------------------------------------------------------------- #
# Backtest period (UTC, daily bars)
# --------------------------------------------------------------------------- #
START_DATE = "2020-05-11"   # per the brief (BTC 3rd-halving era; perp liquid)
END_DATE = "2025-12-31"
# Warm-up history pulled BEFORE START_DATE so trailing transforms (14d MFI, 90d
# z-score, 252d percentile) are already valid on 2020-05-11. Analysis/backtest are
# still restricted to [START_DATE, END_DATE]; warm-up bars only feed lookbacks.
WARMUP_START = "2019-06-01"

# --------------------------------------------------------------------------- #
# Target instrument — Binance USDⓈ-M BTCUSDT perpetual.
# Public market-data endpoints (no key, no geo-block on data host).
# --------------------------------------------------------------------------- #
PERP_SYMBOL = "BTCUSDT"
BINANCE_FAPI_BASE = "https://fapi.binance.com"          # USDⓈ-M futures REST
PERP_KLINES_PATH = "/fapi/v1/klines"                    # interval=1d
PERP_FUNDING_PATH = "/fapi/v1/fundingRate"              # 8h funding history
FUNDING_INTERVALS_PER_DAY = 3                           # 00:00 / 08:00 / 16:00 UTC

# --------------------------------------------------------------------------- #
# Cross-exchange SPOT venues for the self-computed MFI proxy.
#
# IMPORTANT (disclosed in every report): this is a SELF-COMPUTED cross-exchange
# proxy, NOT Glassnode's spot_money_flow_index. It is a faithful reconstruction of
# what Glassnode aggregates (cross-venue USD/USD-related spot money flow), but venue
# selection, USDT-vs-USD quoting and volume quality differ. When a real Glassnode
# key is available the whole pipeline must be re-run on the genuine series and compared.
#
# Venue choice rationale: reputable, low-wash-volume USD/USDT spot venues. MFI is
# volume-weighted, so fake volume corrupts it -> we prefer audited majors and EXCLUDE
# venues notorious for wash trading. Any venue with no/poor coverage in a sub-period
# is DROPPED transparently for that period (never forward-filled / synthesised).
# --------------------------------------------------------------------------- #
SPOT_VENUES: dict[str, dict] = {
    # ccxt_id            symbol        quote   note
    "binance":        {"symbol": "BTC/USDT", "quote": "USDT"},
    "coinbase":       {"symbol": "BTC/USD",  "quote": "USD"},   # Coinbase Exchange/Advanced
    "kraken":         {"symbol": "BTC/USD",  "quote": "USD"},
    "bitstamp":       {"symbol": "BTC/USD",  "quote": "USD"},
    "okx":            {"symbol": "BTC/USDT", "quote": "USDT"},
}
# Minimum fraction of expected daily bars a venue must have IN A YEAR to be counted
# that year (else dropped for that year and disclosed in the coverage table).
VENUE_MIN_YEAR_COVERAGE = 0.80
CCXT_OHLCV_LIMIT = 300           # conservative per-call candle cap (paginated)
CCXT_RATE_LIMIT = True           # enableRateLimit on every ccxt client

# --------------------------------------------------------------------------- #
# MFI factor
# --------------------------------------------------------------------------- #
MFI_PERIOD = 14                  # fixed by definition (Glassnode 14-day)
# Typical price = (H + L + C) / 3 ; raw money flow = typical_price * volume ;
# positive/negative money flow by day-over-day typical-price direction ;
# MFI = 100 - 100 / (1 + 14d positive/negative money-flow ratio).

# --------------------------------------------------------------------------- #
# Look-ahead / publication discipline (applies everywhere).
#   MFI(D) uses data through close-of-D -> known no earlier than D+1 00:00 UTC,
#   plus Glassnode publication lag. Be conservative: lag >= 1 full bar.
# --------------------------------------------------------------------------- #
FACTOR_LAG_BARS = 1              # factor known no earlier than next bar
EXECUTION = "next_open"          # signals execute at the next bar's open

# Walk-forward embargo. MFI(D) depends on D-13..D, so the embargo must be >= the factor window to
# stop train/test sharing input data at a split boundary. This is the ONLY leakage-prevention knob
# the walk-forward needs: config selection uses TRAILING in-sample Sharpe over a strict anchored
# prefix, with no forward-looking training labels to purge, so there is no separate "purge" step
# here (unlike src/pbo.py's combinatorial splits, which have many boundaries per split and DO purge
# train-side rows at each one). Verified by tests/test_walkforward.py; see docs/AUDIT.md.
EMBARGO_BARS = MFI_PERIOD        # 14 bars (>= brief's minimum)

# --------------------------------------------------------------------------- #
# Costs (Binance USDⓈ-M). Net-of-cost is the only number that matters.
# --------------------------------------------------------------------------- #
TAKER_FEE_ONE_WAY = 0.0005       # 0.05% taker; round-trip ~0.10%
SLIPPAGE_BPS_ONE_WAY = 2.0       # a few bps on top of fees (one-way)
# Funding is NOT a constant — pulled from actual history and applied by side &
# holding period. The constants above are fees+slippage only.
# Cost-sensitivity sweep: multipliers on the (fee + slippage) round-trip cost.
COST_MULTIPLIER_GRID = (0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0)

# --------------------------------------------------------------------------- #
# Performance / annualisation. Crypto trades 365 days/yr (no weekend gaps).
# PSR/DSR operate on the PER-PERIOD (daily) Sharpe directly; sqrt-365 is only for
# the annualised reporting number.
# --------------------------------------------------------------------------- #
PERIODS_PER_YEAR = 365
RISK_FREE_ANNUAL = 0.0           # Sharpe uses rf = 0 (disclosed)

# --------------------------------------------------------------------------- #
# EDA (Phase 1) — descriptive only, NO strategy PnL.
# --------------------------------------------------------------------------- #
IC_HORIZONS = (1, 3, 5, 10, 21)  # forward-return horizons (days) for the IC table
N_BUCKETS = 10                   # decile bucket analysis
# Trailing windows for factor transforms (all causal, no full-sample stats).
ZSCORE_WINDOW = 90               # default rolling z-score lookback (EDA default)
PERCENTILE_WINDOW = 252          # trailing window for causal percentile rank (~1y)
ROC_WINDOW = 5                   # rate-of-change horizon for the ROC transform

# --------------------------------------------------------------------------- #
# Optimisation grid (Phase 4). The EXACT model + grid are fixed by the
# pre-registration AFTER Phase-1 EDA (direction/shape decide mean-reversion vs
# momentum). Ranges below are economically-sensible defaults, refined at that point
# and recorded in the decision log. Plateau (anti-luck) requirement enforced.
# --------------------------------------------------------------------------- #
# Threshold model (overbought/oversold on the MFI level):
GRID_LEVEL_THRESHOLDS = (60, 65, 70, 75, 80, 85, 90)   # symmetric OS = 100 - OB
# Rolling z-score band model:
GRID_Z_THRESHOLDS = (0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5)
GRID_Z_WINDOWS = (20, 30, 45, 60, 90, 120, 180)
# Plateau test: 3x3 (+/-1 step per dim) neighbourhood must retain this fraction of
# the peak Sharpe WITH THE SAME SIGN, else the peak is rejected as an isolated spike.
PLATEAU_MIN_FRACTION = 0.80

# --------------------------------------------------------------------------- #
# Variant A — spot-MFI vs funding DIVERGENCE (closes the spot-perp premise).
# Edge_t = trailing_pct_rank_W(MFI) - trailing_pct_rank_W(daily_funding) in [-1, 1].
# Long when Edge > T (spot strong in its own history AND funding low = leverage uncrowded);
# flat when Edge < EDGE_EXIT (hysteresis). Funding is BOTH a signal input (crowding info) AND a
# realised holding cost in the backtester — deliberately NOT netted. Ranges are economically
# sensible defaults refined from the Phase-1 distributions; NOT tuned to PnL.
# --------------------------------------------------------------------------- #
GRID_EDGE_THRESHOLDS = (0.1, 0.2, 0.3, 0.4, 0.5, 0.6)
GRID_EDGE_WINDOWS = (30, 60, 90, 126, 180, 252)     # trailing percentile-rank window (days)
EDGE_EXIT = 0.0                                      # flat when Edge < 0 (spot weaker than funding)

# --------------------------------------------------------------------------- #
# Walk-forward (Phase 4).
# --------------------------------------------------------------------------- #
WF_SCHEME = "anchored"           # "anchored" (expanding IS) | "rolling"
WF_N_SPLITS = 5                  # OOS segments
WF_MIN_TRAIN_BARS = 365          # >= 1y IS before the first OOS evaluation

# --------------------------------------------------------------------------- #
# Statistics / inference (Phase 5). Conventional, NOT tuned.
# --------------------------------------------------------------------------- #
RANDOM_SEED = 7
BOOTSTRAP_N = 10_000             # bootstrap resamples for CIs
PERMUTATION_N = 10_000           # factor-permutation null draws
CI_LEVEL = 95                    # %
# Stationary block bootstrap (Politis-Romano) mean block length (days). A-priori,
# NOT tuned to the result: must exceed the holding horizon / factor-window order so
# each block preserves the daily-return autocorrelation the factor induces. Refined
# to the IC-decay horizon once known; default ~2 weeks of trading.
STATIONARY_BLOCK_MEAN = 21   # anchored a-priori to the ~21d IC-decay / avg-holding horizon

# --------------------------------------------------------------------------- #
# Decision rule (verdict). Pre-registered numeric bar — frozen in
# research/PREREGISTRATION.md before any optimisation. Placeholders here are the
# DEFAULTS the pre-registration will adopt/refine; the verdict cites these.
# --------------------------------------------------------------------------- #
EDGE_MIN_NET_SHARPE = 0.5        # net (annualised) OOS Sharpe floor
EDGE_MAX_DSR_P = 0.05            # DSR significance: require DSR > 0.95 (p < 0.05)
EDGE_REQUIRE_PLATEAU = True      # selected params must sit on a plateau, not a spike
EDGE_REQUIRE_OOS_POSITIVE = True # aggregated walk-forward OOS must be positive
