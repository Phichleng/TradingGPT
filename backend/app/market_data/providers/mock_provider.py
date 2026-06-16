"""Deterministic synthetic candles for local dev and tests (no network)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.market_data.provider import BaseProvider


class MockProvider(BaseProvider):
    def candles(self, market: str, timeframe: str, n: int = 300) -> pd.DataFrame:
        rng = np.random.default_rng(abs(hash((market, timeframe))) % (2**32))
        drift = 0.0006
        steps = rng.normal(drift, 0.004, n).cumsum()
        base = 2000.0 if market == "XAUUSD" else 100.0
        close = base * (1 + steps)
        high = close * (1 + np.abs(rng.normal(0, 0.002, n)))
        low = close * (1 - np.abs(rng.normal(0, 0.002, n)))
        open_ = np.r_[close[0], close[:-1]]
        idx = pd.date_range("2025-01-01", periods=n, freq="15min", tz="UTC")
        return pd.DataFrame(
            {"open": open_, "high": high, "low": low, "close": close,
             "volume": rng.integers(100, 1000, n)}, index=idx)
