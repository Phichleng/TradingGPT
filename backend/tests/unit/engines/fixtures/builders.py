"""Helpers to build hand-crafted candle scenarios for deterministic tests."""
from __future__ import annotations

import pandas as pd


def make_candles(rows: list[tuple], start="2025-01-01", freq="15min"):
    """rows = list of (open, high, low, close[, volume])."""
    idx = pd.date_range(start, periods=len(rows), freq=freq, tz="UTC")
    cols = ["open", "high", "low", "close", "volume"]
    data = {c: [] for c in cols}
    for r in rows:
        r = list(r) + [None] * (5 - len(r))
        for c, v in zip(cols, r):
            data[c].append(v)
    return pd.DataFrame(data, index=idx)



def from_close_path(closes: list[float], wick: float = 0.2,
                    start="2025-01-01", freq="15min"):
    """Build candles from a close path with symmetric wicks derived from each
    candle's own close, so swing highs/lows are unique local extrema."""
    rows = [(c, c + wick, c - wick, c) for c in closes]
    return make_candles(rows, start=start, freq=freq)
