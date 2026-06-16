from __future__ import annotations

import pandas as pd

from app.domain.models import StrategyProposal
from app.strategies.base import no_proposal
from app.strategies.registry import register


@register
class MarketStructureStrategy:
    name = "market_structure"
    preferred_regimes = {"trending", "reversal"}

    def fitness(self, *, engines, regime, structure) -> float:
        base = (80 if structure.get("structure_status") in ("continuation","shifting") else 40)
        mod = 1.0 if regime["regime"] in self.preferred_regimes else 0.7
        return round(min(base * mod, 100), 1)

    def propose(self, *, df: pd.DataFrame, engines, structure) -> StrategyProposal:
        # TODO Phase 1+: derive entry/SL/TP from this strategy's edge.
        return no_proposal("market_structure propose() not yet implemented")
