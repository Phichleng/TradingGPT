"""Walk-forward backtester.

Downloads historical candles and simulates trades by running technical engines
on rolling windows, then checking if SL or TP is hit on the subsequent candles.
No LLM is involved — this tests the pure mechanical edge of the strategy.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Approximate candles per trading day by timeframe (FX/crypto 24h)
_CANDLES_PER_DAY: dict[str, float] = {
    "1": 1440, "5": 288, "15": 96, "30": 48,
    "60": 24, "240": 6, "D": 1, "W": 0.143,
}


def run_backtest(
    market: str,
    timeframe: str,
    lookback_days: int = 60,
    n_window: int = 300,
    n_forward: int = 50,
    step: int = 30,
) -> dict:
    """
    Walk-forward backtest for *market* on *timeframe*.

    Parameters
    ----------
    lookback_days : days of history to download (limited by yfinance: ≤60 for sub-daily)
    n_window      : candles fed to the engines each iteration
    n_forward     : candles to simulate the trade outcome on
    step          : candles to advance the window each iteration
    """
    from app.backtesting.metrics import compute_metrics
    from app.config import settings
    from app.engines.crt import CRTEngine
    from app.engines.ict import ICTEngine
    from app.engines.market_structure import MarketStructureEngine
    from app.engines.regime import RegimeEngine
    from app.engines.smc import SMCEngine
    from app.market_data.providers.yfinance_provider import YFinanceProvider
    from app.risk.risk_engine import RiskConfig, RiskEngine
    from app.selection.selector import StrategySelector
    from app.strategies.registry import load_all

    load_all()

    cpd = _CANDLES_PER_DAY.get(str(timeframe), 24)
    n_total = min(int(lookback_days * cpd) + n_window + n_forward, 5000)

    provider = YFinanceProvider()
    full_df = provider.candles(market, timeframe, n=n_total)

    if len(full_df) < n_window + n_forward:
        return {
            "error": f"Not enough data: got {len(full_df)} candles, need {n_window + n_forward}",
            "market": market, "timeframe": timeframe,
        }

    struct_eng = MarketStructureEngine()
    engines_map = {"ict": ICTEngine(), "smc": SMCEngine(), "crt": CRTEngine()}
    regime_eng = RegimeEngine()
    selector = StrategySelector()
    risk_eng = RiskEngine(RiskConfig(
        risk_per_trade=settings.risk_per_trade,
        min_rr=settings.min_rr,
        daily_loss_limit=settings.daily_loss_limit,
        weekly_loss_limit=settings.weekly_loss_limit,
    ))

    trades: list[dict] = []
    iterations = 0

    for i in range(n_window, len(full_df) - n_forward, step):
        window = full_df.iloc[i - n_window:i]
        future = full_df.iloc[i:i + n_forward]
        iterations += 1

        try:
            struct = struct_eng.analyze(window, context={})
            ctx = {**struct.summary}
            engine_results = {
                name: eng.analyze(window, context=ctx)
                for name, eng in engines_map.items()
            }
            regime = regime_eng.analyze(window, context=ctx).summary

            sel = selector.select(
                engines=engine_results,
                regime=regime,
                structure=struct.summary,
                df=window,
            )

            proposal = sel.get("proposal")
            if proposal is None or proposal.direction == "none":
                continue

            risk = risk_eng.evaluate(proposal, balance=settings.account_balance)
            if not risk.passed:
                continue

            outcome = _simulate_trade(proposal, future)
            if outcome is None:
                continue

            trades.append({
                "ts": str(window.index[-1]),
                "direction": proposal.direction,
                "strategy": sel.get("selected", "?"),
                "rr": float(risk.rr or 0),
                "outcome": outcome,
            })

        except Exception:
            logger.debug("backtest | iter %d failed", i, exc_info=True)

    result = compute_metrics(trades)
    result.update({
        "market": market,
        "timeframe": timeframe,
        "lookback_days": lookback_days,
        "iterations_checked": iterations,
    })
    return result


def _simulate_trade(proposal, future_candles) -> str | None:
    """Returns 'win', 'loss', or None (unresolved within forward window)."""
    sl = float(proposal.stop_loss)
    tp = float(proposal.take_profit)

    for _, row in future_candles.iterrows():
        hi = float(row["high"])
        lo = float(row["low"])

        if proposal.direction == "long":
            if lo <= sl:
                return "loss"
            if hi >= tp:
                return "win"
        else:
            if hi >= sl:
                return "loss"
            if lo <= tp:
                return "win"

    return None
