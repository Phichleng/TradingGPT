from __future__ import annotations

import pandas as pd

from app.domain.interfaces import Strategy  # noqa: F401  (re-export)
from app.domain.models import StrategyProposal


def no_proposal(reason: str = "no setup") -> StrategyProposal:
    return StrategyProposal("none", (0.0, 0.0), 0.0, 0.0, reason)
