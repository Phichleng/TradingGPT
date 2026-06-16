from __future__ import annotations

from app.engines.market_structure import MarketStructureEngine
from app.engines.ict import ICTEngine
from app.engines.smc import SMCEngine
from app.engines.crt import CRTEngine
from app.engines.regime import RegimeEngine
from app.selection.selector import StrategySelector
from app.risk.risk_engine import RiskEngine


class AnalysisPipeline:
    """The only component that knows the order of operations."""

    def __init__(self, *, data_provider, retriever=None, llm_engine=None,
                 risk_engine: RiskEngine | None = None, repo=None):
        self.data = data_provider
        self.struct = MarketStructureEngine()
        self.engines = {"ict": ICTEngine(), "smc": SMCEngine(), "crt": CRTEngine()}
        self.regime = RegimeEngine()
        self.selector = StrategySelector()
        self.risk = risk_engine or RiskEngine()
        self.retriever = retriever
        self.llm = llm_engine
        self.repo = repo

    def run(self, market: str, timeframe: str, source: str = "manual") -> dict:
        df = self.data.candles(market, timeframe, n=300)
        dfd = self.data.candles(market, "1d", n=120)
        dfw = self.data.candles(market, "1w", n=60)

        struct = self.struct.analyze(df, context={})
        daily = self.struct.analyze(dfd, context={}).summary["trend"]
        weekly = self.struct.analyze(dfw, context={}).summary["trend"]
        ctx = {**struct.summary, "htf_bias": daily,
               "daily_bias": daily, "weekly_bias": weekly}

        results = {"market_structure": struct}
        results.update({name: eng.analyze(df, context=ctx)
                        for name, eng in self.engines.items()})
        ctx["recent_sweep"] = bool(results["ict"].summary.get("sweeps"))
        regime = self.regime.analyze(df, context=ctx).summary

        sel = self.selector.select(engines={k: v for k, v in results.items()
                                            if k != "market_structure"},
                                   regime=regime, structure=struct.summary, df=df)

        balance = getattr(self.repo, "balance", 10000.0) if self.repo else 10000.0
        risk = self.risk.evaluate(sel["proposal"], balance=balance)

        report = self._assemble(market, timeframe, regime, struct, results, sel, risk)
        if self.llm is not None:
            report["reasoning"] = self.llm.explain(report, retriever=self.retriever)
        if self.repo is not None:
            self.repo.save_analysis(report)

        if report.get("verdict", "").startswith("valid_"):
            try:
                from app.notifications.telegram import trade_signal_alert
                trade_signal_alert(report)
            except Exception:
                pass
            try:
                from app.config import settings
                if settings.paper_trading_enabled:
                    from app.paper_trading.positions import open_position
                    open_position(report)
            except Exception:
                pass

        return report

    @staticmethod
    def _assemble(market, timeframe, regime, struct, results, sel, risk) -> dict:
        p = sel["proposal"]
        return {
            "market": market, "timeframe": timeframe,
            "market_regime": regime["regime"],
            "selected_strategy": sel["selected"],
            "trend": struct.summary["trend"],
            "market_structure": struct.summary["structure_status"],
            "ict_score": results["ict"].score,
            "smc_score": results["smc"].score,
            "crt_score": results["crt"].score,
            "strategy_scores": sel["scores"],
            "entry_zone": list(p.entry_zone) if p else None,
            "stop_loss": p.stop_loss if p else None,
            "take_profit": p.take_profit if p else None,
            "risk_reward": risk.rr,
            "confidence": sel["confidence"],
            "risk_status": "passed" if risk.passed else "rejected",
            "warnings": [] if risk.passed else risk.reasons,
            "verdict": (f"valid_{p.direction}_setup" if (p and risk.passed)
                        else "no_trade"),
            "reasoning": "",
        }
