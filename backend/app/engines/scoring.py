from __future__ import annotations

from app.domain.interfaces import EngineResult


def normalize(engine_results: dict[str, EngineResult]) -> dict[str, float]:
    """Collapse engine results to {'ict': 93.0, 'smc': 85.0, ...} for scored engines."""
    return {name: r.score for name, r in engine_results.items() if r.score > 0}
