from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

# Maps TradingView-style timeframe strings to cron triggers that fire just after
# each candle closes (1-min grace so yfinance data is settled).
_TF_TRIGGERS: dict[str, CronTrigger] = {
    "1":   CronTrigger(minute="*"),
    "5":   CronTrigger(minute="0,5,10,15,20,25,30,35,40,45,50,55"),
    "15":  CronTrigger(minute="1,16,31,46"),
    "30":  CronTrigger(minute="1,31"),
    "60":  CronTrigger(minute="1"),
    "240": CronTrigger(hour="0,4,8,12,16,20", minute="1"),
    "D":   CronTrigger(hour="0", minute="5"),
    "W":   CronTrigger(day_of_week="mon", hour="0", minute="10"),
}

scheduler = BackgroundScheduler(timezone="UTC")


def _run_analysis(market: str, timeframe: str) -> None:
    try:
        from app.llm.analysis_engine import LLMAnalysisEngine
        from app.market_data.providers import get_provider
        from app.orchestrator.pipeline import AnalysisPipeline
        from app.repositories.analysis_repo import AnalysisRepo
        from app.strategies.registry import load_all

        load_all()
        try:
            llm = LLMAnalysisEngine()
        except Exception:
            llm = None
        pipe = AnalysisPipeline(
            data_provider=get_provider(), repo=AnalysisRepo(), llm_engine=llm
        )
        result = pipe.run(market, timeframe, source="scheduler")
        logger.info("scheduler | %s/%s → %s (conf=%.0f%%)",
                    market, timeframe, result["verdict"],
                    (result.get("confidence") or 0) * 100)
    except Exception:
        logger.exception("scheduler | %s/%s failed", market, timeframe)


def _monitor_paper_trades() -> None:
    try:
        from app.paper_trading.monitor import check_open_positions
        check_open_positions()
    except Exception:
        logger.exception("scheduler | paper trade monitor failed")


def setup_scheduler(markets: list[str], timeframes: list[str]) -> None:
    for tf in timeframes:
        trigger = _TF_TRIGGERS.get(tf)
        if trigger is None:
            logger.warning("scheduler | unknown timeframe %r — skipping", tf)
            continue
        for market in markets:
            scheduler.add_job(
                _run_analysis,
                trigger=trigger,
                args=[market, tf],
                id=f"{market}_{tf}",
                replace_existing=True,
                misfire_grace_time=120,
            )
            logger.info("scheduler | registered %s/%s", market, tf)

    # Check open paper trades every 5 minutes
    scheduler.add_job(
        _monitor_paper_trades,
        trigger=CronTrigger(minute="*/5"),
        id="paper_trade_monitor",
        replace_existing=True,
        misfire_grace_time=60,
    )
    logger.info("scheduler | registered paper trade monitor (every 5 min)")
