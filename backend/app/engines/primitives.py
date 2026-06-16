"""Deterministic building blocks shared by every engine. Pure functions of a
candle DataFrame indexed by timestamp with columns open/high/low/close[/volume]."""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.domain.models import Swing


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    tr = pd.concat(
        [h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1
    ).max(axis=1)
    return tr.rolling(period, min_periods=1).mean()


def swing_points(df: pd.DataFrame, left: int = 2, right: int = 2) -> list[Swing]:
    """Fractal swing detection. A swing high is strictly the max of its
    [left, right] window (and symmetrically for lows)."""
    highs, lows = df["high"].values, df["low"].values
    out: list[Swing] = []
    n = len(df)
    for i in range(left, n - right):
        wh = highs[i - left:i + right + 1]
        wl = lows[i - left:i + right + 1]
        if highs[i] == wh.max() and (wh == highs[i]).sum() == 1:
            out.append(Swing(i, df.index[i], float(highs[i]), "high"))
        if lows[i] == wl.min() and (wl == lows[i]).sum() == 1:
            out.append(Swing(i, df.index[i], float(lows[i]), "low"))
    return sorted(out, key=lambda s: s.idx)


def dealing_range(swings: list[Swing], lookback: int = 6):
    recent = swings[-lookback:]
    highs = [s.price for s in recent if s.kind == "high"]
    lows = [s.price for s in recent if s.kind == "low"]
    if not highs or not lows:
        return None
    return (max(highs), min(lows))          # (range_high, range_low)


def fib_levels(range_high: float, range_low: float, direction: str) -> dict:
    rng = range_high - range_low
    if direction == "bullish":
        anchor = range_low
        return {str(l): anchor + rng * l for l in (0.5, 0.62, 0.705, 0.79)}
    anchor = range_high
    return {str(l): anchor - rng * l for l in (0.5, 0.62, 0.705, 0.79)}


def is_displacement(df: pd.DataFrame, i: int, atr_series: pd.Series,
                    mult: float = 1.5) -> bool:
    body = abs(df["close"].iloc[i] - df["open"].iloc[i])
    a = atr_series.iloc[i]
    return bool(a and not np.isnan(a) and body >= mult * a)
