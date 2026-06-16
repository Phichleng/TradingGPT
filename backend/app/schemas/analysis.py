from __future__ import annotations

from pydantic import BaseModel


class AnalyzeRequest(BaseModel):
    market: str
    timeframe: str = "15m"


class AnalysisReport(BaseModel):
    market: str
    timeframe: str
    market_regime: str
    selected_strategy: str | None
    trend: str
    market_structure: str
    ict_score: float
    smc_score: float
    crt_score: float
    strategy_scores: dict[str, float]
    entry_zone: list[float] | None
    stop_loss: float | None
    take_profit: float | None
    risk_reward: float | None
    confidence: float
    risk_status: str
    warnings: list[str]
    verdict: str
    reasoning: str
