from __future__ import annotations

from pydantic import BaseModel


class TradingViewAlert(BaseModel):
    secret: str
    market: str
    timeframe: str
    price: float | None = None
    event: str = "alert_fired"
    strategy_hint: str | None = None
    nonce: str
    bar_time: str | None = None
