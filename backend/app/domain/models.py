"""Immutable value objects produced and consumed by the engines.

These are intentionally framework-free (no SQLAlchemy, no Pydantic) so the
engine layer stays pure and trivially unit-testable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class Candle:
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float | None = None


@dataclass(frozen=True)
class Swing:
    idx: int
    ts: datetime
    price: float
    kind: str            # 'high' | 'low'


@dataclass(frozen=True)
class Zone:
    """A price region: FVG, order block, breaker, OTE, CRT range, ..."""
    kind: str            # 'fvg','order_block','breaker','ote','crt_range'
    top: float
    bottom: float
    start_idx: int
    direction: str       # 'bullish' | 'bearish'
    mitigated: bool = False
    meta: dict = field(default_factory=dict)

    def contains(self, price: float) -> bool:
        return self.bottom <= price <= self.top


@dataclass(frozen=True)
class Signal:
    name: str            # 'bos','choch','liquidity_sweep','displacement',...
    idx: int
    ts: datetime
    direction: str
    strength: float      # 0..1
    meta: dict = field(default_factory=dict)


@dataclass
class StrategyProposal:
    direction: str                  # 'long' | 'short' | 'none'
    entry_zone: tuple[float, float]
    stop_loss: float
    take_profit: float
    rationale: str

    @property
    def entry_mid(self) -> float:
        return sum(self.entry_zone) / 2
