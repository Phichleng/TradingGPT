from __future__ import annotations

import pandas as pd

from app.domain.models import StrategyProposal
from app.strategies.base import no_proposal
from app.strategies.registry import register


@register
class TrendFollowingStrategy:
    name = "trend_following"
    preferred_regimes = {"trending"}

    def fitness(self, *, engines, regime, structure) -> float:
        base = structure.get("trend_strength", 0.0) * 100
        mod = 1.0 if regime["regime"] in self.preferred_regimes else 0.7
        return round(min(base * mod, 100), 1)

    def propose(self, *, df: pd.DataFrame, engines, structure) -> StrategyProposal:
        # TODO Phase 1+: pullback entry into OB/FVG in the trend direction.
        return no_proposal("trend_following propose() not yet implemented")
