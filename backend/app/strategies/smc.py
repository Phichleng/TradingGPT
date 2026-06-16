from __future__ import annotations

import pandas as pd

from app.domain.models import StrategyProposal
from app.strategies.base import no_proposal
from app.strategies.registry import register


@register
class SMCStrategy:
    name = "smc"
    preferred_regimes = {"trending", "reversal"}

    def fitness(self, *, engines, regime, structure) -> float:
        base = engines["smc"].score
        mod = 1.0 if regime["regime"] in self.preferred_regimes else 0.7
        return round(min(base * mod, 100), 1)

    def propose(self, *, df: pd.DataFrame, engines, structure) -> StrategyProposal:
        # TODO Phase 1+: derive entry/SL/TP from this strategy's edge.
        return no_proposal("smc propose() not yet implemented")
