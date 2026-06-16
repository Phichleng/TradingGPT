from __future__ import annotations

from datetime import time

import pandas as pd

from app.domain.interfaces import EngineResult
from app.domain.models import Signal, Zone
from app.engines.primitives import (atr, dealing_range, fib_levels,
                                     is_displacement, swing_points)

KILL_ZONES = {
    "asian": (time(20, 0), time(0, 0)),
    "london": (time(2, 0), time(5, 0)),
    "ny_am": (time(7, 0), time(10, 0)),
    "ny_pm": (time(13, 30), time(16, 0)),
}


def find_fvg(df: pd.DataFrame) -> list[Zone]:
    """3-candle Fair Value Gap. Bullish: low[i] > high[i-2]."""
    zones, h, l = [], df["high"].values, df["low"].values
    for i in range(2, len(df)):
        if l[i] > h[i - 2]:
            zones.append(Zone("fvg", float(l[i]), float(h[i - 2]), i - 2, "bullish"))
        elif h[i] < l[i - 2]:
            zones.append(Zone("fvg", float(l[i - 2]), float(h[i]), i - 2, "bearish"))
    return zones


def find_liquidity_sweep(df: pd.DataFrame, swings) -> list[Signal]:
    sigs = []
    for s in swings:
        after = df.iloc[s.idx + 1:]
        if after.empty:
            continue
        if s.kind == "high":
            hit = after[(after["high"] > s.price) & (after["close"] < s.price)]
            if not hit.empty:
                ts = hit.index[0]
                sigs.append(Signal("liquidity_sweep", df.index.get_loc(ts), ts,
                                   "bearish", 0.85,
                                   {"swept": s.price, "side": "buyside"}))
        else:
            hit = after[(after["low"] < s.price) & (after["close"] > s.price)]
            if not hit.empty:
                ts = hit.index[0]
                sigs.append(Signal("liquidity_sweep", df.index.get_loc(ts), ts,
                                   "bullish", 0.85,
                                   {"swept": s.price, "side": "sellside"}))
    return sigs


def premium_discount(price: float, rng) -> str:
    hi, lo = rng
    return "premium" if price > (hi + lo) / 2 else "discount"


def session_of(ts, tz: str = "America/New_York") -> str | None:
    t = ts.tz_convert(tz).time() if getattr(ts, "tzinfo", None) else ts.time()
    for name, (start, end) in KILL_ZONES.items():
        if start <= end and start <= t < end:
            return name
        if start > end and (t >= start or t < end):
            return name
    return None


class ICTEngine:
    name = "ict"
    WEIGHTS = {
        "structure_align": 20, "fvg": 12, "liquidity_sweep": 18, "ote": 15,
        "displacement": 12, "premium_discount": 8, "killzone": 10, "htf_bias": 5,
    }

    def analyze(self, df: pd.DataFrame, *, context: dict) -> EngineResult:
        swings = swing_points(df)
        a = atr(df)
        fvgs = find_fvg(df)
        sweeps = find_liquidity_sweep(df, swings)
        rng = dealing_range(swings)
        last = float(df["close"].iloc[-1])

        disp = [
            Signal("displacement", i, df.index[i],
                   "bullish" if df["close"].iloc[i] > df["open"].iloc[i] else "bearish",
                   0.7, {})
            for i in range(len(df)) if is_displacement(df, i, a)
        ]

        zone_type, in_ote = None, False
        if rng:
            direction = context.get("htf_bias", "bullish")
            fibs = fib_levels(rng[0], rng[1], direction)
            in_ote = min(fibs.values()) <= last <= max(fibs.values())
            zone_type = premium_discount(last, rng)

        sess = session_of(df.index[-1])
        htf = context.get("htf_bias")

        comp = {
            "structure_align": 1.0 if context.get("structure_status") in
            ("continuation", "shifting") else 0.3,
            "fvg": min(len(fvgs) / 3, 1.0),
            "liquidity_sweep": 1.0 if sweeps else 0.0,
            "ote": 1.0 if in_ote else 0.0,
            "displacement": min(len(disp) / 2, 1.0),
            "premium_discount": 1.0 if (zone_type == "discount" and htf == "bullish")
            or (zone_type == "premium" and htf == "bearish") else 0.4,
            "killzone": 1.0 if sess in ("london", "ny_am") else (0.5 if sess else 0.0),
            "htf_bias": 1.0 if htf else 0.3,
        }
        score = sum(self.WEIGHTS[k] * v for k, v in comp.items())

        return EngineResult(
            score=round(score, 1),
            signals=sweeps + disp,
            zones=fvgs,
            summary={
                "session": sess, "premium_discount": zone_type, "in_ote": in_ote,
                "fvg_count": len(fvgs), "sweeps": len(sweeps),
                "daily_bias": context.get("daily_bias"),
                "weekly_bias": context.get("weekly_bias"),
                "components": comp,
            },
            explanation=f"ICT {score:.0f}/100 | {sess or 'off'} | "
                        f"{zone_type or 'n/a'} | {'OTE' if in_ote else 'no-OTE'}",
        )
