"""Daily vectorised backtester for a LONG-only single-position perp strategy.

No-lookahead accounting
-----------------------
* TARGET position comes from the signal at the MFI day (info ≤ close of that day).
* Held position over bar t (open_t → open_{t+1}) = ``target.shift(FACTOR_LAG_BARS)`` — i.e. the
  signal from the prior close, executed at THIS bar's open. This bundles the ≥1-bar factor lag with
  next-open execution; nothing uses a return before it is knowable.
* Return earned on bar t = held_position_t × (open_{t+1}/open_t − 1)   [open-to-open].

Costs (net is the only number that matters)
* Transaction: |Δ held position| × (taker fee + slippage) one-way, on the bar the trade occurs.
* Funding: held_position × daily funding (Σ of the 8h rates that day). funding>0 ⇒ a long PAYS.
* ``cost_mult`` scales fee+slippage for the cost-sensitivity sweep (funding is real, not scaled).

Benchmarks returned for the pre-registered "must beat buy-and-hold" test:
* ``bh_perp``  — always-long perp, pays funding (same-instrument passive).
* ``bh_spot``  — price-only open-to-open hold, no funding (the stricter "could've held BTC" bar).
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

import config
from . import performance as perf

_FEE = config.TAKER_FEE_ONE_WAY
_SLIP = config.SLIPPAGE_BPS_ONE_WAY / 1e4


@dataclass
class BacktestResult:
    daily: pd.DataFrame            # gross, txn, funding, net, pos, turnover, oo_ret
    net: pd.Series
    gross: pd.Series
    metrics: dict
    bench: dict                    # {'bh_perp': {...}, 'bh_spot': {...}}


def run_backtest(target_pos: pd.Series, panel: pd.DataFrame, *, cost_mult: float = 1.0,
                 fee: float = _FEE, slippage: float = _SLIP) -> BacktestResult:
    """Backtest a target-position series against the perp panel. Returns net/gross + metrics."""
    df = panel.copy()
    # open-to-open return earned over bar t (needs next open -> last bar drops out)
    oo = df["perp_open"].shift(-1) / df["perp_open"] - 1.0
    pos = target_pos.reindex(df.index).shift(config.FACTOR_LAG_BARS).fillna(0.0)

    turnover = pos.diff().abs()
    turnover.iloc[0] = abs(pos.iloc[0])
    cost_rate = (fee + slippage) * cost_mult

    gross = pos * oo
    txn = turnover * cost_rate
    funding = pos * df["funding"]            # long pays positive funding
    net = gross - txn - funding

    valid = oo.notna()
    daily = pd.DataFrame({"oo_ret": oo, "pos": pos, "turnover": turnover,
                          "gross": gross, "txn": txn, "funding": funding, "net": net})[valid]

    m = perf.metrics(daily["net"])
    n = len(daily)
    entries = int(((daily["pos"].diff() == 1) | ((daily.index == daily.index[0]) & (daily["pos"] == 1))).sum())
    years = n / config.PERIODS_PER_YEAR
    m.update({
        "gross_sharpe": perf.sharpe_ratio(daily["gross"]),
        "exposure": float((daily["pos"] > 0).mean()),
        "n_trades": entries,
        "avg_hold_days": float(daily["pos"].sum() / entries) if entries else float("nan"),
        "turnover_per_year": float(daily["turnover"].sum() / years) if years else float("nan"),
        "total_funding_cost": float(daily["funding"].sum()),
        "total_txn_cost": float(daily["txn"].sum()),
    })

    # benchmarks over the same span
    bh_perp = oo[valid] - df["funding"][valid]
    bh_spot = oo[valid]
    bench = {
        "bh_perp": perf.metrics(bh_perp) | {"kind": "always-long perp, pays funding"},
        "bh_spot": perf.metrics(bh_spot) | {"kind": "price-only open-to-open hold, no funding"},
    }
    return BacktestResult(daily=daily, net=daily["net"], gross=daily["gross"], metrics=m, bench=bench)
