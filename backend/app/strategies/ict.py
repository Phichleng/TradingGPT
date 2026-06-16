from __future__ import annotations

import pandas as pd

from app.domain.models import StrategyProposal
from app.engines.primitives import atr, dealing_range, fib_levels, swing_points
from app.strategies.registry import register


@register
class ICTStrategy:
    name = "ict"
    preferred_regimes = {"trending", "reversal", "breakout"}

    def fitness(self, *, engines, regime, structure) -> float:
        base = engines["ict"].score
        s = engines["ict"].summary
        mod = 1.0 if regime["regime"] in self.preferred_regimes else 0.7
        if s.get("sweeps", 0) == 0:
            mod *= 0.85
        if s.get("in_ote"):
            mod = min(mod * 1.1, 1.15)
        return round(min(base * mod, 100), 1)

    def propose(self, *, df: pd.DataFrame, engines, structure) -> StrategyProposal:
        swings = swing_points(df)
        rng = dealing_range(swings)
        bias = structure.get("trend", "bullish")
        if not rng:
            return StrategyProposal("none", (0, 0), 0, 0, "no dealing range")

        range_high, range_low = rng[0], rng[1]
        span = range_high - range_low
        a = float(atr(df).iloc[-1] or 0)

        if bias == "bullish":
            # OTE = 62-79% pullback FROM the swing high (buy the dip into the premium zone)
            # fib_levels with "bearish" measures downward from high:
            #   "0.62" → high - 0.62*span  (38% from low)
            #   "0.79" → high - 0.79*span  (21% from low)
            fibs = fib_levels(range_high, range_low, "bearish")
            entry_lo, entry_hi = sorted((fibs["0.62"], fibs["0.79"]))
            sl = range_low - a               # below swing low
            tp = range_high + span           # 100% expansion above swing high → RR ~4:1
            direction = "long"
        else:
            # OTE = 62-79% bounce FROM the swing low (sell the rally into the discount zone)
            # fib_levels with "bullish" measures upward from low:
            #   "0.62" → low + 0.62*span   (62% from low)
            #   "0.79" → low + 0.79*span   (79% from low)
            fibs = fib_levels(range_high, range_low, "bullish")
            entry_lo, entry_hi = sorted((fibs["0.62"], fibs["0.79"]))
            sl = range_high + a              # above swing high
            tp = range_low - span            # 100% expansion below swing low → RR ~4:1
            direction = "short"

        return StrategyProposal(direction, (entry_lo, entry_hi), sl, tp,
                                "OTE retracement aligned with HTF bias")
