from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(tags=["backtest"])


class BacktestRequest(BaseModel):
    market: str = "XAUUSD"
    timeframe: str = "60"
    lookback_days: int = Field(30, ge=7, le=60)
    n_forward: int = Field(50, ge=10, le=200)
    step: int = Field(30, ge=5, le=100)


@router.post("/backtest")
def run_backtest(req: BacktestRequest):
    """
    Walk-forward backtest. Downloads up to `lookback_days` of historical candles
    (yfinance limits sub-daily data to 60 days) and simulates trades on rolling windows.
    This endpoint is synchronous and may take 30-90 seconds for large requests.
    """
    from app.backtesting.runner import run_backtest as _run
    return _run(
        market=req.market,
        timeframe=req.timeframe,
        lookback_days=req.lookback_days,
        n_forward=req.n_forward,
        step=req.step,
    )
