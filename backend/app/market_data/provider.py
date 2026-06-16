from __future__ import annotations

import pandas as pd

PIP_SIZES = {"XAUUSD": 0.01, "US30": 1.0, "NAS100": 0.25, "SPX500": 0.25,
             "EURUSD": 0.0001, "GBPUSD": 0.0001, "USDJPY": 0.01,
             "BTCUSD": 0.5, "ETHUSD": 0.05}


class BaseProvider:
    def candles(self, market: str, timeframe: str, n: int) -> pd.DataFrame:
        raise NotImplementedError

    def pip_size(self, market: str) -> float:
        return PIP_SIZES.get(market, 0.0001)
