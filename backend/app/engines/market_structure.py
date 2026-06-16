"""Production-ready Market Structure Engine.

Detects and classifies swing-based market structure:

  Labels  HH (Higher High), HL (Higher Low), LH (Lower High), LL (Lower Low)
  BOS     Break of Structure  — trend-continuation break of a prior swing extreme
  CHOCH   Change of Character — first counter-trend break of a protective level
  MSS     Market Structure Shift — CHOCH confirmed by a subsequent same-direction BOS

Algorithm
---------
1. Fractal swing detection (configurable left/right window).
2. Alternating-swing normalisation: collapse consecutive same-kind swings,
   keeping the most extreme, so the sequence strictly alternates H-L-H-L-...
3. Label each swing HH/HL/LH/LL by comparing with the previous same-kind swing.
4. BOS: for every HH swing, find the first candle that closed above the prior
   swing-high level (window: prev_high.ts … current_HH.ts].
   Symmetric for LL / bearish BOS.
5. CHOCH: for every HL swing, find the first candle that closed below the HL
   price in the window (HL.ts … next_same-kind_swing.ts).
   Symmetric for LH / bullish CHOCH.
6. MSS: if a CHOCH is followed within `mss_window` bar-indices by a BOS in the
   same direction, the CHOCH is upgraded to MSS with higher strength.
7. Structure status is derived from the three most-recent events.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd

from app.domain.enums import StructureStatus, Trend
from app.domain.interfaces import EngineResult
from app.domain.models import Signal, Swing
from app.engines.primitives import atr, swing_points


# ---------------------------------------------------------------------------
# Internal value objects
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LabeledSwing:
    """Swing annotated with its HH/HL/LH/LL market-structure label."""
    idx: int
    ts: datetime
    price: float
    kind: str    # 'high' | 'low'
    label: str   # 'HH' | 'HL' | 'LH' | 'LL'


@dataclass(frozen=True)
class StructureEvent:
    """A detected BOS, CHOCH, or MSS event."""
    event_type: str             # 'BOS' | 'CHOCH' | 'MSS'
    idx: int                    # bar index of the break candle
    ts: datetime
    direction: str              # 'bullish' | 'bearish'
    broken_level: float         # price level that was broken
    source_swing: LabeledSwing  # the swing whose level was broken
    strength: float             # 0..1
    displacement_pct: float     # (break distance) / ATR


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class MarketStructureEngine:
    """Full HH/HL/LH/LL + BOS/CHOCH/MSS market structure engine.

    Parameters
    ----------
    swing_left, swing_right : int
        Half-widths of the fractal pivot window (default 2/2 matches the
        original implementation and the existing test suite).
    trend_lookback : int
        Number of recent labeled swings used to classify trend direction.
    atr_period : int
        ATR smoothing window for displacement scoring.
    confirmation : str
        'close' (default) – break candle must *close* beyond the level.
        'wick'            – high/low wick touch is sufficient (noisier).
    min_displacement_atr : float
        Minimum break distance in ATR multiples; filters micro-breaks.
    mss_window : int
        Max bar-index span after a CHOCH to look for a confirming BOS.
    """

    name = "market_structure"

    def __init__(
        self,
        swing_left: int = 2,
        swing_right: int = 2,
        trend_lookback: int = 8,
        atr_period: int = 14,
        confirmation: str = "close",
        min_displacement_atr: float = 0.05,
        mss_window: int = 50,
    ) -> None:
        if confirmation not in ("close", "wick"):
            raise ValueError("confirmation must be 'close' or 'wick'")
        self._left = swing_left
        self._right = swing_right
        self._lookback = trend_lookback
        self._atr_period = atr_period
        self._confirmation = confirmation
        self._min_disp = min_displacement_atr
        self._mss_window = mss_window

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(self, df: pd.DataFrame, *, context: dict) -> EngineResult:
        """Run full market structure analysis on a OHLCV candle DataFrame."""
        if len(df) < (self._left + self._right + 4):
            return _empty_result()

        atr_s = atr(df, self._atr_period)
        raw = swing_points(df, left=self._left, right=self._right)
        if len(raw) < 3:
            return _empty_result()

        alt = _alternate_swings(raw)
        if len(alt) < 3:
            return _empty_result()

        labeled = _label_swings(alt)
        trend, strength = self._classify_trend(labeled)

        bos_events = self._detect_bos(df, labeled, atr_s)
        choch_events = self._detect_choch(df, labeled, atr_s)
        events = sorted(bos_events + choch_events, key=lambda e: e.idx)
        events = self._upgrade_mss(events)

        signals = [_to_signal(e) for e in events]
        status = _derive_status(events, trend)

        return EngineResult(
            score=0.0,  # feeder engine — not a scored engine
            signals=signals,
            zones=[],
            summary={
                "trend": trend,
                "structure_status": status,
                "trend_strength": round(strength, 4),
                "labeled_swings": [
                    {
                        "idx": s.idx,
                        "price": round(s.price, 5),
                        "kind": s.kind,
                        "label": s.label,
                    }
                    for s in labeled[-10:]
                ],
                "events": [
                    {
                        "type": e.event_type,
                        "idx": e.idx,
                        "direction": e.direction,
                        "level": round(e.broken_level, 5),
                        "strength": round(e.strength, 4),
                        "displacement_atr": round(e.displacement_pct, 3),
                    }
                    for e in events[-6:]
                ],
            },
            explanation=_explain(trend, strength, status, events, labeled),
        )

    # ------------------------------------------------------------------
    # Trend classification
    # ------------------------------------------------------------------

    def _classify_trend(self, labeled: list[LabeledSwing]) -> tuple[str, float]:
        recent = labeled[-self._lookback:]
        bull = sum(1 for s in recent if s.label in ("HH", "HL"))
        bear = sum(1 for s in recent if s.label in ("LH", "LL"))
        total = max(len(recent), 1)
        if bull > bear:
            return Trend.BULLISH.value, bull / total
        if bear > bull:
            return Trend.BEARISH.value, bear / total
        return Trend.RANGING.value, 0.5

    # ------------------------------------------------------------------
    # BOS detection
    # ------------------------------------------------------------------

    def _detect_bos(
        self,
        df: pd.DataFrame,
        labeled: list[LabeledSwing],
        atr_s: pd.Series,
    ) -> list[StructureEvent]:
        """Emit a BOS for every HH (bullish) and LL (bearish) swing.

        The break candle is the first bar whose close (or high/low wick when
        confirmation='wick') crosses the prior same-kind swing's price within
        the half-open window (prev_same.ts, current_swing.ts].
        """
        events: list[StructureEvent] = []

        for i, s in enumerate(labeled):
            if s.label not in ("HH", "LL"):
                continue

            # Most recent prior swing of same kind
            prev = next(
                (labeled[j] for j in range(i - 1, -1, -1) if labeled[j].kind == s.kind),
                None,
            )
            if prev is None:
                continue  # no previous level to break

            level = prev.price
            mask = (df.index > prev.ts) & (df.index <= df.index[s.idx])

            if s.label == "HH":
                col = "high" if self._confirmation == "wick" else "close"
                candidates = df.loc[mask, col]
                candidates = candidates[candidates > level]
                direction = "bullish"
            else:  # LL
                col = "low" if self._confirmation == "wick" else "close"
                candidates = df.loc[mask, col]
                candidates = candidates[candidates < level]
                direction = "bearish"

            if candidates.empty:
                continue

            break_ts = candidates.index[0]
            break_idx = df.index.get_loc(break_ts)
            break_price = float(candidates.iloc[0])
            atr_val = _safe_atr(atr_s, break_idx)
            disp = (break_price - level) if direction == "bullish" else (level - break_price)
            disp_pct = disp / atr_val if atr_val > 0 else 0.0

            if disp_pct < self._min_disp:
                continue

            events.append(StructureEvent(
                event_type="BOS",
                idx=break_idx,
                ts=break_ts,
                direction=direction,
                broken_level=level,
                source_swing=prev,
                strength=_strength(disp_pct, "BOS"),
                displacement_pct=disp_pct,
            ))

        return events

    # ------------------------------------------------------------------
    # CHOCH detection
    # ------------------------------------------------------------------

    def _detect_choch(
        self,
        df: pd.DataFrame,
        labeled: list[LabeledSwing],
        atr_s: pd.Series,
    ) -> list[StructureEvent]:
        """Emit CHOCH events:

        Bearish CHOCH — close below a HL (breaks the protective bullish low).
        Bullish CHOCH — close above a LH (breaks the protective bearish high).

        Scan window for each swing: from the swing's timestamp to the next
        same-kind swing's timestamp (i.e., while this swing is the active
        protective level, before a newer one supersedes it).
        """
        events: list[StructureEvent] = []

        for i, s in enumerate(labeled):
            if s.label not in ("HL", "LH"):
                continue

            # Window: [s.ts, next_same_kind.ts) — active protection window
            next_same = next(
                (labeled[j] for j in range(i + 1, len(labeled)) if labeled[j].kind == s.kind),
                None,
            )
            if next_same is not None:
                # Inclusive upper bound: the CHOCH and its confirming swing can
                # land on the same bar (a massive candle breaks the protective
                # level and forms the new swing in one move).
                mask = (df.index > s.ts) & (df.index <= df.index[next_same.idx])
            else:
                mask = df.index > s.ts

            if s.label == "HL":
                col = "low" if self._confirmation == "wick" else "close"
                candidates = df.loc[mask, col]
                candidates = candidates[candidates < s.price]
                direction = "bearish"
            else:  # LH
                col = "high" if self._confirmation == "wick" else "close"
                candidates = df.loc[mask, col]
                candidates = candidates[candidates > s.price]
                direction = "bullish"

            if candidates.empty:
                continue

            break_ts = candidates.index[0]
            break_idx = df.index.get_loc(break_ts)
            break_price = float(candidates.iloc[0])
            atr_val = _safe_atr(atr_s, break_idx)
            disp = (s.price - break_price) if direction == "bearish" else (break_price - s.price)
            disp_pct = disp / atr_val if atr_val > 0 else 0.0

            if disp_pct < self._min_disp:
                continue

            events.append(StructureEvent(
                event_type="CHOCH",
                idx=break_idx,
                ts=break_ts,
                direction=direction,
                broken_level=s.price,
                source_swing=s,
                strength=_strength(disp_pct, "CHOCH"),
                displacement_pct=disp_pct,
            ))

        return events

    # ------------------------------------------------------------------
    # MSS upgrade
    # ------------------------------------------------------------------

    def _upgrade_mss(self, events: list[StructureEvent]) -> list[StructureEvent]:
        """Upgrade a CHOCH to MSS when a same-direction BOS follows within
        self._mss_window bars.  Higher conviction than a lone CHOCH."""
        result: list[StructureEvent] = []
        upgraded: set[int] = set()

        for i, e in enumerate(events):
            if i in upgraded:
                continue
            if e.event_type != "CHOCH":
                result.append(e)
                continue

            # Search the full event list (not just j > i): a BOS at the same
            # bar index as the CHOCH sorts before it due to stable-sort order
            # (bos_events precede choch_events in the pre-sort concatenation),
            # so limiting to j > i would miss same-bar confirmation.
            confirmed = any(
                k != i
                and events[k].event_type == "BOS"
                and events[k].direction == e.direction
                and 0 <= events[k].idx - e.idx <= self._mss_window
                for k in range(len(events))
            )

            if confirmed:
                result.append(StructureEvent(
                    event_type="MSS",
                    idx=e.idx,
                    ts=e.ts,
                    direction=e.direction,
                    broken_level=e.broken_level,
                    source_swing=e.source_swing,
                    strength=min(1.0, e.strength + 0.1),
                    displacement_pct=e.displacement_pct,
                ))
                upgraded.add(i)
            else:
                result.append(e)

        return result


# ---------------------------------------------------------------------------
# Module-level pure helpers (accessible for unit-testing)
# ---------------------------------------------------------------------------

def _alternate_swings(swings: list[Swing]) -> list[Swing]:
    """Collapse consecutive same-kind swings, keeping the more extreme value.

    Guarantees the result strictly alternates H-L-H-L-...
    """
    if not swings:
        return []
    result: list[Swing] = [swings[0]]
    for s in swings[1:]:
        prev = result[-1]
        if s.kind == prev.kind:
            if (s.kind == "high" and s.price > prev.price) or \
               (s.kind == "low" and s.price < prev.price):
                result[-1] = s
        else:
            result.append(s)
    return result


def _label_swings(swings: list[Swing]) -> list[LabeledSwing]:
    """Assign HH/HL/LH/LL to each swing in an alternating sequence."""
    labeled: list[LabeledSwing] = []
    last_high: Optional[float] = None
    last_low: Optional[float] = None

    for s in swings:
        if s.kind == "high":
            label = "HH" if last_high is None or s.price > last_high else "LH"
            last_high = s.price
        else:
            label = "HL" if last_low is None or s.price > last_low else "LL"
            last_low = s.price
        labeled.append(LabeledSwing(s.idx, s.ts, s.price, s.kind, label))

    return labeled


def _safe_atr(atr_s: pd.Series, idx: int) -> float:
    try:
        val = float(atr_s.iloc[min(idx, len(atr_s) - 1)])
        return val if not np.isnan(val) else 0.0
    except (IndexError, TypeError):
        return 0.0


def _strength(displacement_pct: float, event_type: str) -> float:
    """Map displacement/ATR → strength [0..1] with sqrt diminishing returns."""
    base = 0.55 if event_type == "BOS" else 0.65
    return min(1.0, base + 0.18 * (displacement_pct ** 0.5))


def _to_signal(event: StructureEvent) -> Signal:
    return Signal(
        name=event.event_type.lower(),  # 'bos' | 'choch' | 'mss'
        idx=event.idx,
        ts=event.ts,
        direction=event.direction,
        strength=event.strength,
        meta={
            "broken_level": round(event.broken_level, 5),
            "source_label": event.source_swing.label,
            "displacement_atr": round(event.displacement_pct, 3),
        },
    )


def _derive_status(events: list[StructureEvent], trend: str) -> str:
    if not events:
        return StructureStatus.INTACT.value
    recent = events[-3:]
    if any(e.event_type in ("MSS", "CHOCH") for e in recent):
        return StructureStatus.SHIFTING.value
    in_trend_bos = any(
        e.event_type == "BOS"
        and (
            (trend == Trend.BULLISH.value and e.direction == "bullish")
            or (trend == Trend.BEARISH.value and e.direction == "bearish")
        )
        for e in recent
    )
    if in_trend_bos:
        return StructureStatus.CONTINUATION.value
    return StructureStatus.INTACT.value


def _empty_result() -> EngineResult:
    return EngineResult(
        score=0.0,
        signals=[],
        zones=[],
        summary={
            "trend": Trend.RANGING.value,
            "structure_status": StructureStatus.INTACT.value,
            "trend_strength": 0.0,
            "labeled_swings": [],
            "events": [],
        },
        explanation="Insufficient data for market structure analysis.",
    )


def _explain(
    trend: str,
    strength: float,
    status: str,
    events: list[StructureEvent],
    labeled: list[LabeledSwing],
) -> str:
    n = len(labeled)
    recent = ", ".join(f"{e.event_type}({e.direction[:4]})" for e in events[-3:]) or "none"
    last_label = labeled[-1].label if labeled else "—"
    return (
        f"{trend} trend ({strength:.0%} strength), structure {status}. "
        f"Last swing: {last_label}. Recent events: {recent}. "
        f"{n} swings analysed."
    )
