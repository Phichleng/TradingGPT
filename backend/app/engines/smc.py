from __future__ import annotations

import pandas as pd

from app.domain.interfaces import EngineResult
from app.domain.models import Signal, Zone
from app.engines.primitives import atr, is_displacement, swing_points


def order_blocks(df: pd.DataFrame) -> list[Zone]:
    a = atr(df)
    zones = []
    for i in range(2, len(df) - 1):
        if is_displacement(df, i + 1, a):
            up = df["close"].iloc[i + 1] > df["open"].iloc[i + 1]
            down_candle = df["close"].iloc[i] < df["open"].iloc[i]
            up_candle = df["close"].iloc[i] > df["open"].iloc[i]
            if up and down_candle:
                zones.append(Zone("order_block", float(df["high"].iloc[i]),
                                  float(df["low"].iloc[i]), i, "bullish"))
            elif (not up) and up_candle:
                zones.append(Zone("order_block", float(df["high"].iloc[i]),
                                  float(df["low"].iloc[i]), i, "bearish"))
    return zones


def equal_levels(swings, tol: float = 0.0008) -> list[Signal]:
    sigs = []
    highs = [s for s in swings if s.kind == "high"]
    lows = [s for s in swings if s.kind == "low"]
    for arr, side in ((highs, "buyside"), (lows, "sellside")):
        for j in range(1, len(arr)):
            if abs(arr[j].price - arr[j - 1].price) / max(arr[j - 1].price, 1e-9) <= tol:
                sigs.append(Signal("equal_levels", arr[j].idx, arr[j].ts,
                                   "bearish" if side == "buyside" else "bullish",
                                   0.7, {"side": side, "level": arr[j].price}))
    return sigs


class SMCEngine:
    name = "smc"
    WEIGHTS = {"order_block": 25, "breaker": 15, "structure_break": 25,
               "liquidity_pool": 15, "fvg_imbalance": 10, "mitigation": 10}

    def analyze(self, df: pd.DataFrame, *, context: dict) -> EngineResult:
        swings = swing_points(df)
        obs = order_blocks(df)
        eq = equal_levels(swings)
        last = float(df["close"].iloc[-1])
        breakers = [z for z in obs if self._violated_then_returned(df, z)]
        in_ob = any(z.contains(last) for z in obs)

        comp = {
            "order_block": 1.0 if in_ob else (0.5 if obs else 0.0),
            "breaker": min(len(breakers) / 2, 1.0),
            "structure_break": 1.0 if context.get("structure_status") in
            ("continuation", "shifting") else 0.3,
            "liquidity_pool": min(len(eq) / 2, 1.0),
            "fvg_imbalance": min(len(context.get("fvgs", [])) / 3, 1.0),
            "mitigation": 1.0 if any(z.mitigated for z in obs) else 0.3,
        }
        score = sum(self.WEIGHTS[k] * v for k, v in comp.items())
        return EngineResult(
            score=round(score, 1),
            signals=eq,
            zones=obs + breakers,
            summary={"order_blocks": len(obs), "breakers": len(breakers),
                     "equal_levels": len(eq), "price_in_ob": in_ob, "components": comp},
            explanation=f"SMC {score:.0f}/100 | {len(obs)} OB | {len(eq)} liq pools",
        )

    @staticmethod
    def _violated_then_returned(df, z: Zone) -> bool:
        after = df.iloc[z.start_idx + 1:]
        if after.empty:
            return False
        if z.direction == "bullish":
            return bool((after["close"] < z.bottom).any() and (after["close"] > z.bottom).any())
        return bool((after["close"] > z.top).any() and (after["close"] < z.top).any())
