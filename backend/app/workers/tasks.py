from __future__ import annotations

from app.workers.celery_app import celery_app


@celery_app.task(name="analyze_market")
def analyze_market(market: str, timeframe: str, source: str = "webhook") -> dict:
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
    pipe = AnalysisPipeline(data_provider=get_provider(), repo=AnalysisRepo(), llm_engine=llm)
    return pipe.run(market, timeframe, source)
