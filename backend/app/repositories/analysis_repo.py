from __future__ import annotations

from app.config import settings
from app.db.models.tables import AnalysisLog
from app.db.session import SessionLocal


class AnalysisRepo:
    """Thin repo passed into AnalysisPipeline so results land in analysis_logs."""

    @property
    def balance(self) -> float:
        return settings.account_balance

    def save_analysis(self, report: dict) -> None:
        with SessionLocal() as session:
            log = AnalysisLog(
                timeframe=report["timeframe"],
                selected_strategy=report.get("selected_strategy"),
                confidence=report.get("confidence"),
                ict_score=report.get("ict_score"),
                smc_score=report.get("smc_score"),
                crt_score=report.get("crt_score"),
                risk_passed=report.get("risk_status") == "passed",
                report_json=report,
            )
            session.add(log)
            session.commit()
