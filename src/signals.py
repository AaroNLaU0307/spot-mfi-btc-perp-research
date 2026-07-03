"""Signal models (pre-registered, LONG-only). Produce a daily TARGET position in {0, 1}.

M1 (primary) — MFI level threshold with hysteresis: go/stay long when smoothed MFI > T; exit to
              flat when it reverts below the midline (50). Knobs: T (threshold), W (smoothing window).
M2 (robustness) — rolling z-score band: long when z(MFI) > Z; flat when z < 0. Knobs: Z, win.

All inputs are trailing/causal. These produce the TARGET at the MFI day; the backtester applies the
≥1-bar factor lag + next-open execution, so nothing here peeks. Long-only per the pre-registration
(positive IC + low-MFI-not-bearish decile evidence).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import config


def _hysteresis(entry: pd.Series, exit_: pd.Series) -> pd.Series:
    """Stateful 0/1: 1 on entry, 0 on exit, hold otherwise. Vectorised via ffill."""
    e = entry.fillna(False).to_numpy(dtype=bool)
    x = exit_.fillna(False).to_numpy(dtype=bool)
    state = np.where(e, 1.0, np.where(x, 0.0, np.nan))
    return pd.Series(state, index=entry.index).ffill().fillna(0.0).rename("target")


def smooth(mfi: pd.Series, window: int) -> pd.Series:
    return mfi if window <= 1 else mfi.rolling(window, min_periods=1).mean()


def signal_level_threshold(mfi: pd.Series, threshold: float, window: int = 1,
                           exit_level: float = 50.0) -> pd.Series:
    """M1: long when smoothed MFI > threshold; flat when it falls back below ``exit_level``."""
    s = smooth(mfi, window)
    return _hysteresis(s > threshold, s < exit_level)


def signal_zscore_band(mfi: pd.Series, z_threshold: float, window: int,
                       exit_z: float = 0.0) -> pd.Series:
    """M2: long when trailing z-score of MFI > z_threshold; flat when z < exit_z."""
    mu = mfi.rolling(window, min_periods=window).mean()
    sd = mfi.rolling(window, min_periods=window).std(ddof=0)
    z = (mfi - mu) / sd
    return _hysteresis(z > z_threshold, z < exit_z)


# Model registry (used by the optimiser); keeps the grid definitions in one place.
MODELS = {
    "M1_level": {
        "fn": signal_level_threshold,
        "param_names": ("threshold", "window"),
        "grid": (config.GRID_LEVEL_THRESHOLDS, (1, 2, 3, 5, 7, 10)),
    },
    "M2_zscore": {
        "fn": signal_zscore_band,
        "param_names": ("z_threshold", "window"),
        "grid": (config.GRID_Z_THRESHOLDS, config.GRID_Z_WINDOWS),
    },
    "M1_edge": {
        # Variant A. The Edge signal needs (MFI, funding) and lives in src/divergence.py;
        # walk_forward only reads param_names + grid, so fn is a marker here (do NOT invoke via
        # the generic fn(mfi, p1, p2) path — use divergence.evaluate_edge_grid).
        "fn": None,
        "param_names": ("threshold", "window"),
        "grid": (config.GRID_EDGE_THRESHOLDS, config.GRID_EDGE_WINDOWS),
    },
}
