"""Protocols (structural interfaces) that decouple the orchestrator from
concrete engines, strategies and repositories. Anything that satisfies the
shape can be injected — this is what makes the system modular."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

import pandas as pd

from app.domain.models import Signal, Zone, StrategyProposal


@dataclass
class EngineResult:
    score: float                    # 0..100 (0 means "not a scored engine")
    signals: list[Signal] = field(default_factory=list)
    zones: list[Zone] = field(default_factory=list)
    summary: dict = field(default_factory=dict)
    explanation: str = ""


@runtime_checkable
class Engine(Protocol):
    name: str
    def analyze(self, df: pd.DataFrame, *, context: dict) -> EngineResult: ...


@runtime_checkable
class Strategy(Protocol):
    name: str
    preferred_regimes: set[str]
    def fitness(self, *, engines: dict, regime: dict, structure: dict) -> float: ...
    def propose(self, *, df: pd.DataFrame, engines: dict,
                structure: dict) -> StrategyProposal: ...


class MarketDataProvider(Protocol):
    def candles(self, market: str, timeframe: str, n: int) -> pd.DataFrame: ...
    def pip_size(self, market: str) -> float: ...


class VectorStore(Protocol):
    def search(self, query: str, k: int, filters: dict | None = None) -> list: ...
    def upsert(self, ids: list[str], vectors: list[list[float]],
               payloads: list[dict]) -> None: ...
