from __future__ import annotations

from fastapi import APIRouter, Query

from app.market_data.providers import get_provider
from app.orchestrator.pipeline import AnalysisPipeline
from app.repositories.analysis_repo import AnalysisRepo
from app.schemas.analysis import AnalyzeRequest
from app.strategies.registry import load_all

router = APIRouter(tags=["analysis"])
load_all()


def _build_pipeline() -> AnalysisPipeline:
    from app.llm.analysis_engine import LLMAnalysisEngine
    try:
        llm = LLMAnalysisEngine()
    except Exception:
        llm = None
    return AnalysisPipeline(data_provider=get_provider(), repo=AnalysisRepo(), llm_engine=llm)


@router.post("/analyze")
def analyze(req: AnalyzeRequest):
    return _build_pipeline().run(req.market, req.timeframe, source="manual")


@router.get("/analysis/latest")
def latest_analyses(limit: int = Query(20, ge=1, le=100)):
    """Return the most recent analysis logs saved by the scheduler or manual calls."""
    from app.db.models.tables import AnalysisLog
    from app.db.session import SessionLocal
    with SessionLocal() as session:
        rows = (session.query(AnalysisLog)
                .order_by(AnalysisLog.requested_at.desc())
                .limit(limit)
                .all())
        return [
            {
                "id": r.id,
                "timeframe": r.timeframe,
                "selected_strategy": r.selected_strategy,
                "confidence": r.confidence,
                "ict_score": r.ict_score,
                "smc_score": r.smc_score,
                "crt_score": r.crt_score,
                "risk_passed": r.risk_passed,
                "verdict": r.report_json.get("verdict"),
                "market": r.report_json.get("market"),
                "trend": r.report_json.get("trend"),
                "reasoning": r.report_json.get("reasoning", ""),
                "requested_at": r.requested_at.isoformat(),
            }
            for r in rows
        ]
