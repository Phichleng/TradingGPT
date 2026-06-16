from __future__ import annotations

import pandas as pd

from app.domain.interfaces import EngineResult
from app.domain.models import Signal, Zone


class CRTEngine:
    """Candle Range Theory: a prior range candle defines a box; price
    manipulates one side, expands toward the other, and may return to range."""
    name = "crt"
    WEIGHTS = {"range_defined": 20, "manipulation": 30,
               "expansion": 30, "return_to_range": 20}

    def analyze(self, df: pd.DataFrame, *, context: dict) -> EngineResult:
        crt = context.get("crt_candle") or self._prior_range(df)
        if crt is None:
            return EngineResult(0.0, [], [], {"defined": False}, "CRT n/a")

        hi, lo = crt["high"], crt["low"]
        body = df.iloc[crt["idx"] + 1:]
        swept_high = bool((body["high"] > hi).any()) if not body.empty else False
        swept_low = bool((body["low"] < lo).any()) if not body.empty else False
        manipulated = swept_high or swept_low
        last = float(df["close"].iloc[-1])
        return_to_range = lo <= last <= hi
        expansion = (swept_high and last < lo) or (swept_low and last > hi)
        direction = "bearish" if swept_high else ("bullish" if swept_low else "neutral")

        comp = {
            "range_defined": 1.0,
            "manipulation": 1.0 if manipulated else 0.0,
            "expansion": 1.0 if expansion else (0.5 if manipulated else 0.0),
            "return_to_range": 1.0 if return_to_range else 0.3,
        }
        score = sum(self.WEIGHTS[k] * v for k, v in comp.items())
        sigs = ([Signal("crt_manipulation", crt["idx"], df.index[crt["idx"]],
                        direction, 0.8, {})] if manipulated else [])
        return EngineResult(
            score=round(score, 1),
            signals=sigs,
            zones=[Zone("crt_range", hi, lo, crt["idx"], direction)],
            summary={"crt_high": hi, "crt_low": lo, "manipulated": manipulated,
                     "expansion": expansion, "return_to_range": return_to_range,
                     "direction": direction, "components": comp},
            explanation=f"CRT {score:.0f}/100 | {direction} | "
                        f"{'manip' if manipulated else 'no-manip'}",
        )

    @staticmethod
    def _prior_range(df):
        if len(df) < 3:
            return None
        i = len(df) - 2
        return {"idx": i, "high": float(df["high"].iloc[i]),
                "low": float(df["low"].iloc[i])}
