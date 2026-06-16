from __future__ import annotations

import pandas as pd

from app.strategies.registry import all_strategies


class StrategySelector:
    PROPOSE_THRESHOLD = 50.0

    def select(self, *, engines, regime, structure, df: pd.DataFrame,
               enabled: set[str] | None = None) -> dict:
        scores, proposals = {}, {}
        for strat in all_strategies():
            if enabled and strat.name not in enabled:
                continue
            f = strat.fitness(engines=engines, regime=regime, structure=structure)
            scores[strat.name] = f
            if f >= self.PROPOSE_THRESHOLD:
                proposals[strat.name] = strat.propose(
                    df=df, engines=engines, structure=structure)

        if not scores:
            return {"selected": None, "confidence": 0.0, "margin": 0.0,
                    "scores": {}, "proposal": None, "reasoning_inputs": {}}

        best = max(scores, key=scores.get)
        ordered = sorted(scores.values(), reverse=True)
        margin = ordered[0] - (ordered[1] if len(ordered) > 1 else 0)
        return {
            "selected": best,
            "confidence": round(scores[best], 1),
            "margin": round(margin, 1),
            "scores": scores,
            "proposal": proposals.get(best),
            "reasoning_inputs": {
                "regime": regime, "structure": structure,
                "engine_scores": {k: v.score for k, v in engines.items()},
            },
        }
