"""Strategy registry. Concrete strategies register themselves via @register so
the selector can iterate them generically — adding a strategy is a new file."""
from __future__ import annotations

from app.domain.interfaces import Strategy

_REGISTRY: dict[str, Strategy] = {}


def register(cls):
    inst = cls()
    _REGISTRY[inst.name] = inst
    return cls


def all_strategies() -> list[Strategy]:
    return list(_REGISTRY.values())


def get(name: str) -> Strategy | None:
    return _REGISTRY.get(name)


def load_all() -> None:
    """Import side-effect modules so they self-register. Called at startup."""
    from app.strategies import (  # noqa: F401
        ict, smc, crt, trend_following, market_structure,
        pullback, breakout, liquidity_sweep_reversal, session_based,
    )
