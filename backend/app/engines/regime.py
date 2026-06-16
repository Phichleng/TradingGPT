from __future__ import annotations

import numpy as np
import pandas as pd

from app.domain.interfaces import EngineResult
from app.engines.primitives import atr


class RegimeEngine:
    name = "regime"

    def analyze(self, df: pd.DataFrame, *, context: dict) -> EngineResult:
        a = atr(df)
        last_close = float(df["close"].iloc[-1])
        atr_pct = float(a.iloc[-1] / last_close) if last_close else 0.0
        vol_med = float((a / df["close"]).median())

        window = df["close"].iloc[-50:]
        if len(window) >= 5:
            x = np.arange(len(window))
            slope = float(np.polyfit(x, window.values, 1)[0])
        else:
            slope = 0.0
        norm_slope = slope / (last_close + 1e-9)

        trend_str = float(context.get("trend_strength", 0.0))
        recent_sweep = bool(context.get("recent_sweep", False))

        if recent_sweep and trend_str < 0.4:
            label = "reversal"
        elif trend_str >= 0.6 and abs(norm_slope) > 1e-4:
            label = "trending"
        elif atr_pct > 1.6 * vol_med:
            label = "breakout"
        else:
            label = "ranging"

        vol = "high_volatility" if atr_pct > 1.3 * vol_med else "low_volatility"
        return EngineResult(
            score=0.0, signals=[], zones=[],
            summary={"regime": label, "volatility": vol,
                     "atr_pct": round(atr_pct, 5), "trend_strength": trend_str},
            explanation=f"regime={label}, {vol}",
        )
