"""Direct chat endpoint — ask Ollama anything about the markets.

If you include a market + timeframe, it runs a live analysis first and gives
Ollama real OHLCV context so answers are grounded in current price action.
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["chat"])

CHAT_SYSTEM = """You are TradingGPT, an expert institutional trading assistant specialising in ICT (Inner Circle Trader), SMC (Smart Money Concepts), and CRT (Candle Range Theory) methodologies.

When market data is provided to you, use it to give specific, grounded analysis. Reference real price levels, scores, and signals from the data.

When no market data is provided, answer from your training knowledge about trading concepts, strategies, and market structure.

Be concise, direct, and actionable. Avoid generic disclaimers. Speak like a professional trader."""


class ChatRequest(BaseModel):
    message: str
    market: str | None = None
    timeframe: str | None = "60"
    include_analysis: bool = True


class ChatResponse(BaseModel):
    reply: str
    market: str | None = None
    analysis_context: dict | None = None


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    from app.llm.client import chat as llm_chat

    context_block = ""
    analysis = None

    if req.market and req.include_analysis:
        try:
            from app.market_data.providers import get_provider
            from app.orchestrator.pipeline import AnalysisPipeline
            from app.strategies.registry import load_all

            load_all()
            pipe = AnalysisPipeline(data_provider=get_provider())
            analysis = pipe.run(req.market, req.timeframe or "60", source="chat")

            ez = analysis.get("entry_zone") or [0, 0]
            context_block = f"""
=== LIVE MARKET CONTEXT: {req.market} {req.timeframe}m ===
Trend: {analysis.get('trend')}
Regime: {analysis.get('market_regime')}
ICT score: {analysis.get('ict_score')}  SMC: {analysis.get('smc_score')}  CRT: {analysis.get('crt_score')}
Selected strategy: {analysis.get('selected_strategy')}
Confidence: {analysis.get('confidence')}%
Verdict: {analysis.get('verdict')}
Entry zone: {ez[0]:.5f} – {ez[1]:.5f}
Stop loss: {analysis.get('stop_loss')}
Take profit: {analysis.get('take_profit')}
Risk-Reward: {analysis.get('risk_reward')}R
Risk status: {analysis.get('risk_status')}
Warnings: {analysis.get('warnings')}
===========================================
"""
        except Exception as exc:
            context_block = f"\n[Could not fetch live data for {req.market}: {exc}]\n"

    user_msg = context_block + req.message

    reply = llm_chat(
        system=CHAT_SYSTEM,
        user=user_msg,
        json_mode=False,
        temperature=0.5,
    )

    return ChatResponse(reply=reply, market=req.market, analysis_context=analysis)
