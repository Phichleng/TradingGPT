"""Real OHLCV candles via yfinance (Yahoo Finance). No API key required."""
from __future__ import annotations

import pandas as pd
import yfinance as yf

from app.market_data.provider import BaseProvider

# TradingView symbol → yfinance ticker
_SYMBOL_MAP: dict[str, str] = {
    "XAUUSD": "GC=F",
    "XAGUSD": "SI=F",
    "US30": "YM=F",
    "NAS100": "NQ=F",
    "SPX500": "ES=F",
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "USDJPY": "USDJPY=X",
    "USDCAD": "USDCAD=X",
    "AUDUSD": "AUDUSD=X",
    "BTCUSD": "BTC-USD",
    "ETHUSD": "ETH-USD",
}

# TradingView timeframe → (yfinance interval, period to fetch enough candles)
_TF_MAP: dict[str, tuple[str, str]] = {
    "1":   ("1m",  "7d"),
    "3":   ("2m",  "7d"),
    "5":   ("5m",  "60d"),
    "15":  ("15m", "60d"),
    "30":  ("30m", "60d"),
    "45":  ("60m", "60d"),
    "60":  ("60m", "60d"),
    "120": ("60m", "60d"),
    "240": ("60m", "60d"),
    "D":   ("1d",  "2y"),
    "W":   ("1wk", "5y"),
    "M":   ("1mo", "10y"),
}


class YFinanceProvider(BaseProvider):
    def candles(self, market: str, timeframe: str, n: int = 300) -> pd.DataFrame:
        ticker = _SYMBOL_MAP.get(market.upper(), market)
        interval, period = _TF_MAP.get(str(timeframe), ("1d", "2y"))

        df = yf.download(ticker, period=period, interval=interval,
                         progress=False, auto_adjust=True)
        if df.empty:
            raise ValueError(f"No data returned for {market} ({ticker}) @ {timeframe}")

        # yfinance 1.4+ returns MultiIndex columns even for a single ticker —
        # flatten to plain column names before anything else.
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df.columns = [c.lower() for c in df.columns]
        df.index = pd.to_datetime(df.index, utc=True)
        df = df[["open", "high", "low", "close", "volume"]].dropna()
        return df.tail(n)
